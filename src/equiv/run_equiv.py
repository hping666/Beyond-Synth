"""Queue runner for the equivalence stack:  python -m src.equiv.run_equiv --job <job_id>

Job kinds (scripts/queue): `sim` runs V1 + V2 only (local pool, VCS), `vcf` runs V1 -> V2 -> V3 (vcf pool,
VCS + VC Formal SEQ). Payload (jobs.payload_json):
    {design_id, cand_id, d_rtl: [paths], c_rtl: [paths], top, clk?, rst?, rst_sense?, sverilog?, incdirs?, note?}
The record is written to results/raw/<design_id>/EQ/<hash>/equiv.json (content-addressed like evaluations,
append-only: an existing directory gets a -rN sibling). The search layer (Phase 3) copies the fields into the
`candidates` table; this runner never touches that table.
Exit codes follow src/jobqueue/core.py: 0 the stack produced a verdict (any verdict), 75 a license seat was
unavailable, 1 the stack itself failed.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from src import config as C
from src.db import core as db
from src.equiv.stack import check_equivalence
from src.eval import parse as P
from src.eval.service import job_directory

EX_TEMPFAIL = 75
RUNNER_TIMEOUT_FRACTION = 0.85  # the tool's own timeout fires before the queue kills the job, so the record says timeout / inconclusive


def runner_timeout(job):
    return float(job["timeout_sec"]) * RUNNER_TIMEOUT_FRACTION if job["timeout_sec"] else None



def equiv_hash(d_files, c_files, top, cfg, extra):
    h = hashlib.sha256()
    for f in list(d_files) + ["|"] + list(c_files):
        if f == "|":
            h.update(b"|")
            continue
        h.update(Path(f).name.encode() + b"\0" + Path(f).read_bytes() + b"\0")
    h.update(top.encode())
    h.update(json.dumps(cfg["sim"], sort_keys=True, default=str).encode())
    h.update(json.dumps(extra, sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]


def equiv_extra(cfg, payload, stages_full=True):
    """The `extra` part of the record hash: the stage set, the control ports, the seed and the candidate top; the latency
    mapping switch is included only when it is on, so that every earlier record keeps its hash (2026-09-15)."""
    p = payload
    stages = "v3" if p.get("sim_record") else ("full" if stages_full else "v1v2")   # DECISIONS 2026-09-16 (scheduling change): a proof continuing from a V1/V2 record has its own hash
    extra = {"stages": stages, "clk": p.get("clk"), "rst": p.get("rst"), "rst_sense": p.get("rst_sense"),
             "sverilog": p.get("sverilog", False), "sim_seed": p.get("sim_seed"), "c_top": p.get("c_top")}
    if (cfg.get("equiv") or {}).get("seq_latency_mapping", False):
        extra["latency_mapping"] = True
    return extra


def load_record(rec_dir):
    """The equivalence record under `rec_dir` (None when absent or unreadable)."""
    f = Path(rec_dir) / "equiv.json"
    try:
        return json.loads(f.read_text())
    except (OSError, json.JSONDecodeError):
        return None


REUSABLE_VERDICTS = ("proven", "falsified", "rejected", "sim_fail")   # decided by the stack itself; inconclusive / error / proven_sim_only are run again


def full_record(cfg, payload, eq_root):
    """The `full` (V1 + V2 + V3 in one job) record of the same pair when one exists with a decided verdict: a V3 job of the
    split pipeline copies it instead of proving the same RTL a second time (the same frozen stack; the record keeps the
    `reused_from` pointer). None otherwise."""
    p = {k: v for k, v in payload.items() if k != "sim_record"}
    try:
        h = equiv_hash(p["d_rtl"], p["c_rtl"], p["top"], cfg, equiv_extra(cfg, p, True))
    except OSError:
        return None
    for eq in sorted(Path(eq_root).glob(f"{h}*/equiv.json")):
        rec = load_record(eq.parent)
        if rec and rec.get("verdict") in REUSABLE_VERDICTS and not rec.get("sim_record"):
            return rec
    return None


def stamp_version(rec, cfg):
    """`equiv_version` = config equiv.version (decision 2026-09-15 evening, item 5: the stack frozen for Phase 5 and stamped on
    every record); not part of the record hash, so earlier records under the same stack stay cached."""
    v = (cfg.get("equiv") or {}).get("version")
    if v:
        rec["equiv_version"] = str(v)
    return rec


def _license_problem(rec):
    texts = []
    v2 = rec.get("v2") or {}
    v3 = rec.get("v3") or {}
    for wd in (v2.get("workdir"), v3.get("workdir")):
        if not wd:
            continue
        for name in ("vcs_console.log", "vcf_console.log", "vcf.log"):
            p = Path(wd) / name
            if p.exists():
                texts.append(p.read_text(errors="replace")[-20000:])
    return any(P.license_failure(t) for t in texts)


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
    stages_full = job["kind"] == "vcf"
    extra = equiv_extra(cfg, p, stages_full)
    h = equiv_hash(p["d_rtl"], p["c_rtl"], p["top"], cfg, extra)
    root = Path(C.results_dir(cfg)) / "raw" / p["design_id"] / "EQ" / h
    job_dir, cached = job_directory(root, force_rerun=p.get("force_rerun", False))
    if cached and (job_dir / "equiv.json").exists():
        rec = json.loads((job_dir / "equiv.json").read_text())
        rec["cached"] = True
    else:
        job_dir.mkdir(parents=True, exist_ok=True)
        sim_rec, full_rec = None, None
        if p.get("sim_record"):   # the split pipeline (DECISIONS 2026-09-16): V1 / V2 come from the `sim` job's record; a full record of the same pair (an earlier run, the same stack) is reused when it decided
            sim_rec = load_record(p["sim_record"])
            full_rec = full_record(cfg, p, root.parent)
        if full_rec is not None:
            rec = dict(full_rec, reused_from=full_rec.get("raw_dir"), cached=False)
        else:
            rec = check_equivalence(job_dir, p["d_rtl"], p["c_rtl"], p["top"], cfg, clk=p.get("clk"), rst=p.get("rst"),
                                    rst_sense=p.get("rst_sense"), sverilog=p.get("sverilog", False), incdirs=p.get("incdirs"),
                                    run_v3=stages_full, timeout_sec=runner_timeout(job), design_id=p["design_id"], sim_seed=p.get("sim_seed"), c_top=p.get("c_top"),
                                    sim_record=sim_rec)
            if p.get("sim_record") and sim_rec is None:
                rec["sim_record_missing"] = p["sim_record"]   # the record was gone (retention / relocation): the whole stack ran in this job
        rec.update(design_id=p["design_id"], cand_id=p.get("cand_id"), input_hash=h, raw_dir=str(job_dir),
                   git_sha=C.git_sha(), cfg_hash=C.cfg_hash(), job_id=a.job, kind=job["kind"])
        stamp_version(rec, cfg)
        (job_dir / "equiv.json").write_text(json.dumps(rec, indent=1, sort_keys=True, default=str))
    print(json.dumps({k: rec.get(k) for k in ("design_id", "cand_id", "verdict", "v1_status", "v2_status", "v3_status",
                                               "v3_seconds", "raw_dir", "cached")}))
    if rec.get("verdict") in ("error", None) or rec.get("v2_status") in ("compile_failed", "run_failed", "timeout"):
        if _license_problem(rec):
            return EX_TEMPFAIL
        return 1 if rec.get("verdict") in ("error", None) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
