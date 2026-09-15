#!/usr/bin/env python3
"""Apply the retention policy (config `retention`) to existing evaluation directories:
remove outputs/dc_work and outputs/mw_design of records whose meta.json says status ok. Idempotent.

    .venv/bin/python scripts/prune_scratch.py [--dry-run] [--root results/raw]
    .venv/bin/python scripts/prune_scratch.py --tiered [--apply] [--exp phase3 phase4]   # G5 item 5 (ii): the tiered policy on earlier records

--tiered (dry run unless --apply; the user decides, DECISIONS 2026-09-15): for every candidate evaluation record whose candidate
is neither accepted (accepted / in_archive), nor a literature object, nor in the audit sample, nor a failed record, the
regenerable artifacts are removed (src/eval/retention.py: VCDs, traces, port JSONs, VC Formal databases and learnt data,
VCS builds, SAIFs; netlists, ddc, SAIFs and RTL copies of DC / Yosys records), plus the M6 workdirs of every run
(features are archived in the database). Records, rows, perturbation and baseline records are never touched.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.eval import retention as RET  # noqa: E402
from src.eval.service import SCRATCH_DIRS, prune_scratch  # noqa: E402


def du(path):
    return sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())


def tiered(cfg, conn, root, cand_root, apply=False, exps=None, log=print):
    """The tiered policy on existing records. -> summary dict (bytes by category, records, kept counts)."""
    kept_ids, lit_ids = set(), set()
    q = "SELECT c.cand_id, c.accepted, c.in_archive, r.arm, r.exp FROM candidates c LEFT JOIN runs r ON r.run_id = c.run_id"
    for cid, acc, arch, arm, exp in conn.execute(q):
        if arm == "literature":
            lit_ids.add(cid)
        if acc or arch:
            kept_ids.add(cid)
    exps = set(exps or [])
    run_exp = {r[0]: r[1] for r in conn.execute("SELECT run_id, exp FROM runs")}
    cand_run = {r[0]: r[1] for r in conn.execute("SELECT cand_id, run_id FROM candidates")}
    summary = {"records": 0, "slimmed": 0, "kept_accepted": 0, "kept_audit": 0, "kept_literature": 0, "kept_failed": 0, "skipped_exp": 0, "no_candidate": 0, "freed": {}, "m6_bytes": 0, "m6_dirs": 0}

    def reason(cid, status):
        if cid in lit_ids:
            return "kept_literature"
        if cid in kept_ids:
            return "kept_accepted"
        if status not in ("ok", "proven", "falsified", "sim_fail", "rejected", "inconclusive", "proven_sim_only"):
            return "kept_failed"
        if RET.is_audit_sample(cid, float((cfg.get("retention") or {}).get("tiered_audit_frac") or 0.0)):
            return "kept_audit"
        if exps and run_exp.get(cand_run.get(cid)) not in exps:
            return "skipped_exp"
        return None

    for rec_file in sorted(list(root.glob("*/*/*/meta.json")) + list(root.glob("*/EQ/*/equiv.json"))):
        try:
            rec = json.loads(rec_file.read_text())
        except json.JSONDecodeError:
            continue
        cid = rec.get("cand_id")
        if not cid:
            continue
        cid = str(cid)
        if cid.endswith(tuple(f"_env{k}" for k in range(10))):
            base = cid.rsplit("_env", 1)[0]
        else:
            base = cid
        if base not in cand_run:
            summary["no_candidate"] += 1
            continue
        summary["records"] += 1
        status = rec.get("verdict") if rec_file.name == "equiv.json" else rec.get("status")
        why = reason(base, status)
        if why:
            summary[why] += 1
            continue
        if rec_file.name == "equiv.json":
            freed = RET.slim_eq_record(rec_file.parent, cfg, dry_run=not apply)
        else:
            freed = RET.slim_dc_record(rec_file.parent, cfg, dry_run=not apply)
        if freed:
            summary["slimmed"] += 1
            for k, v in freed.items():
                summary["freed"][k] = summary["freed"].get(k, 0) + v
    if cand_root and cand_root.exists():
        for m6 in sorted(cand_root.glob("*/m6_*")):
            run_id = m6.parent.name
            if exps and run_exp.get(run_id) not in exps:
                continue
            b = RET.slim_m6_workdir(m6, cfg, dry_run=not apply)
            if b:
                summary["m6_bytes"] += b
                summary["m6_dirs"] += 1
    total = sum(summary["freed"].values()) + summary["m6_bytes"]
    log(f"{'freed' if apply else 'would free'} {total / 1e9:.2f} GB: " + ", ".join(f"{k} {v / 1e9:.2f}" for k, v in sorted(summary["freed"].items(), key=lambda kv: -kv[1]))
        + f"; M6 workdirs {summary['m6_dirs']} ({summary['m6_bytes'] / 1e9:.2f} GB)")
    log(f"records of candidates: {summary['records']}; slimmed: {summary['slimmed']}; kept: accepted {summary['kept_accepted']}, audit sample {summary['kept_audit']}, "
        f"literature {summary['kept_literature']}, failed {summary['kept_failed']}; other experiments skipped: {summary['skipped_exp']}; records without a candidate row: {summary['no_candidate']}")
    summary["total_bytes"] = total
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="default: <results_dir>/raw")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tiered", action="store_true", help="the tiered retention of G5 item 5 (ii) on existing records (dry run unless --apply)")
    ap.add_argument("--apply", action="store_true", help="with --tiered: actually delete (the user's decision)")
    ap.add_argument("--exp", nargs="*", default=None, help="with --tiered: only candidates of these experiments (default: all)")
    a = ap.parse_args(argv)
    cfg = C.load()
    root = Path(a.root) if a.root else Path(C.results_dir(cfg)) / "raw"
    if a.tiered:
        from src.db import core as db
        if not RET.enabled(cfg):
            print("config retention.tiered is off: nothing to do")
            return 1
        conn = db.connect(cfg=cfg)
        tiered(cfg, conn, root, Path(C.results_dir(cfg)) / "candidates", apply=a.apply, exps=a.exp)
        return 0
    n_ok = n_pruned = n_kept = 0
    freed = 0
    for meta in root.glob("*/*/*/meta.json"):
        job = meta.parent
        try:
            status = json.loads(meta.read_text()).get("status")
        except json.JSONDecodeError:
            continue
        scratch = [job / "outputs" / d for d in SCRATCH_DIRS if (job / "outputs" / d).is_dir()]
        if status != "ok":
            n_kept += bool(scratch)
            continue
        n_ok += 1
        if not scratch:
            continue
        size = sum(du(s) for s in scratch)
        if a.dry_run:
            print(f"would prune {size / 2**20:6.1f} MB  {job}")
        else:
            prune_scratch(job, cfg)
            n_pruned += 1
        freed += size
    print(f"ok records: {n_ok}; pruned: {n_pruned}; failed records with scratch kept: {n_kept}; "
          f"{'would free' if a.dry_run else 'freed'} {freed / 2**20:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
