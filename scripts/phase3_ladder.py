#!/usr/bin/env python3
"""Ladder and hidden runs on the Phase 3 candidates (DECISIONS 2026-09-14, pre-Phase-4 c): every E4-evaluated candidate of
the calibration runs is synthesised under the visible rungs E1, E1d, E2, E3, E2g (queue kind dc, missing records only)
and under the hidden configurations H1, H2a, H2b, H3, H5 through the hidden worker (queue kind dc_hidden, hidden
database only; rule 3). No LLM cost: this is the RTLLM contrast layer of the map.

    .venv/bin/python scripts/phase3_ladder.py submit [--configs E1 E1d E2 E3 E2g] [--hidden] [--priority 1] --submit
    .venv/bin/python scripts/phase3_ladder.py status
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.designs import jobs as J  # noqa: E402

VISIBLE = ["E1", "E1d", "E2", "E3", "E2g"]


def e4_candidates(conn):
    """[(row)] E4-evaluated candidates of the non-superseded Phase 3 runs with their SAIF (from the equivalence record)."""
    out = []
    for c in conn.execute("SELECT c.cand_id, c.design_id, c.rtl_path, c.eq_job_id FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          "WHERE r.exp='phase3' AND r.status != 'superseded' AND c.e4_job_id IS NOT NULL AND c.label IS NOT NULL AND c.label != 'aborted' ORDER BY c.cand_id"):
        st = Path(C.ROOT) / "results" / "candidates" / conn.execute("SELECT run_id FROM candidates WHERE cand_id=?", (c["cand_id"],)).fetchone()[0] / "state.json"
        saif = None
        if st.exists():
            rec_dir = (json.loads(st.read_text()).get("cands") or {}).get(c["cand_id"], {}).get("eq_record")
            if rec_dir and (Path(rec_dir) / "equiv.json").exists():
                saif = json.loads((Path(rec_dir) / "equiv.json").read_text()).get("saif_c")
        out.append({"cand_id": c["cand_id"], "design_id": c["design_id"], "rtl_path": c["rtl_path"], "saif": saif if saif and Path(saif).exists() else None})
    return out


def visible_jobs(cfg, conn, configs, priority):
    designs = {d["design_id"]: d for d in K.load_all()}
    jobs = []
    for c in e4_candidates(conn):
        d = designs[c["design_id"]]
        phi = float(conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (c["design_id"],)).fetchone()[0])
        for config in configs:
            if conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config=? AND status='ok' AND abs(clock_ns-?)<1e-6 LIMIT 1", (c["cand_id"], config, phi)).fetchone():
                continue
            j = J.dc_job(cfg, d, config, phi, priority)
            j["payload"].update(rtl=[c["rtl_path"]], incdirs=[str(p) for p in K.abs_paths(d, d["incdirs"])], is_baseline=0, cand_id=c["cand_id"])
            if c["saif"]:
                j["payload"].update(saif=c["saif"], saif_instance="bs_lockstep/u_c")
            j["cand_id"] = c["cand_id"]
            jobs.append(j)
    return jobs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["submit", "status"])
    ap.add_argument("--configs", nargs="*", default=None)
    ap.add_argument("--hidden", action="store_true", help="also the hidden configurations through scripts/hidden_worker.py --submit-candidates")
    ap.add_argument("--priority", type=int, default=1)
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    if a.what == "status":
        cands = e4_candidates(conn)
        print(f"{len(cands)} E4-evaluated Phase 3 candidates ({sum(1 for c in cands if c['saif'])} with SAIF)")
        for config in VISIBLE:
            n = sum(1 for c in cands if conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config=? AND status='ok' LIMIT 1", (c["cand_id"], config)).fetchone())
            print(f"  {config}: {n} recorded")
        return 0
    configs = a.configs or VISIBLE
    jobs = visible_jobs(cfg, conn, configs, a.priority)
    print(f"{len(jobs)} visible ladder jobs ({', '.join(configs)}) for the Phase 3 candidates (missing records only)")
    if a.submit:
        from src.jobqueue.core import Queue
        q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
        for j in jobs:
            q.submit(j["kind"], j["payload"], design_id=j["design_id"], cand_id=j["cand_id"], config=j["config"], priority=j["priority"], timeout_sec=j["timeout_sec"])
        print(f"submitted {len(jobs)} dc jobs")
    if a.hidden:
        import subprocess
        cmd = [sys.executable, os.path.join(ROOT, "scripts", "hidden_worker.py"), "--submit-candidates", "--exp", "phase3", "--priority", str(a.priority - 1)] + ([] if a.submit else ["--dry-run"])
        print(subprocess.run(cmd, capture_output=True, text=True).stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
