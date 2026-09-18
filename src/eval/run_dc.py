"""Queue runner for DC evaluations:  python -m src.eval.run_dc --job <job_id>

Payload (jobs.payload_json): {design_id, rtl: [paths], top, config, clock_ns?, clk_port?, cand_id?, pert_id?,
is_baseline?, saif?, saif_instance?, sverilog?, incdirs?, force_rerun?, design?: {phi_main_ns_*}}
Exit codes follow scripts/queue/core.py: 0 ok, 75 license seat unavailable (backoff, no attempt counted),
1 failure (the queue retries once; on the last attempt the record is ingested as eval_failed).
"""
import argparse
import json
import sys

from src import config as C
from src.db import core as db, ingest
from src.eval.service import evaluate

EX_TEMPFAIL = 75
RUNNER_TIMEOUT_FRACTION = 0.85  # the tool's own timeout fires before the queue kills the job, so the record says timeout / inconclusive


def runner_timeout(job):
    return float(job["timeout_sec"]) * RUNNER_TIMEOUT_FRACTION if job["timeout_sec"] else None



def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    job = conn.execute("SELECT * FROM jobs WHERE job_id=?", (a.job,)).fetchone()
    if job is None:
        print(f"job {a.job} not found", file=sys.stderr)
        return 1
    p = json.loads(job["payload_json"])
    config = p.get("config") or job["config"]  # payload first, else the job row's selector column
    meta = evaluate(cfg, conn, p["design_id"], p["rtl"], p["top"], config, clock_ns=p.get("clock_ns"),
                    design=p.get("design"), clk_port=p.get("clk_port", "clk"), cand_id=p.get("cand_id"),
                    pert_id=p.get("pert_id"), is_baseline=p.get("is_baseline", 0), saif=p.get("saif"),
                    saif_instance=p.get("saif_instance"), sverilog=p.get("sverilog", False), incdirs=p.get("incdirs"),
                    force_rerun=p.get("force_rerun", False), timeout_sec=runner_timeout(job),
                    extra_meta={k: int(p[k]) for k in ("offline_eval", "prescreened_offline") if p.get(k)})
    print(json.dumps({k: meta.get(k) for k in ("design_id", "config", "status", "error", "raw_dir", "dc_seconds", "cached", "eval_id")}))
    if meta["status"] == "ok":
        return 0
    if meta["status"] == "license_failed":
        return EX_TEMPFAIL
    last_attempt = int(job["attempts"]) >= int(cfg["queue"]["retries"])
    if last_attempt:
        meta["failed_status"] = meta.get("status")  # analyze_failed / link_failed / timeout ... kept for the reports
        meta["status"] = "eval_failed"
        with open(f"{meta['raw_dir']}/meta.json", "w") as f:
            json.dump(meta, f, indent=1, sort_keys=True, default=str)
        try:
            ingest.ingest_evaluation(conn, meta)
        except Exception as e:  # recorded in the job log; the raw directory keeps the evidence
            print(f"eval_failed record not ingested: {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
