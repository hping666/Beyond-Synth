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
    extra = {"stages": "full" if stages_full else "v1v2", "clk": p.get("clk"), "rst": p.get("rst"),
             "rst_sense": p.get("rst_sense"), "sverilog": p.get("sverilog", False)}
    h = equiv_hash(p["d_rtl"], p["c_rtl"], p["top"], cfg, extra)
    root = Path(C.results_dir(cfg)) / "raw" / p["design_id"] / "EQ" / h
    job_dir, cached = job_directory(root, force_rerun=p.get("force_rerun", False))
    if cached and (job_dir / "equiv.json").exists():
        rec = json.loads((job_dir / "equiv.json").read_text())
        rec["cached"] = True
    else:
        job_dir.mkdir(parents=True, exist_ok=True)
        rec = check_equivalence(job_dir, p["d_rtl"], p["c_rtl"], p["top"], cfg, clk=p.get("clk"), rst=p.get("rst"),
                                rst_sense=p.get("rst_sense"), sverilog=p.get("sverilog", False), incdirs=p.get("incdirs"),
                                run_v3=stages_full, timeout_sec=job["timeout_sec"])
        rec.update(design_id=p["design_id"], cand_id=p.get("cand_id"), input_hash=h, raw_dir=str(job_dir),
                   git_sha=C.git_sha(), cfg_hash=C.cfg_hash(), job_id=a.job, kind=job["kind"])
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
