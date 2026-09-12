#!/usr/bin/env python3
"""Apply the retention policy (config `retention`) to existing evaluation directories:
remove outputs/dc_work and outputs/mw_design of records whose meta.json says status ok. Idempotent.

    .venv/bin/python scripts/prune_scratch.py [--dry-run] [--root results/raw]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.eval.service import SCRATCH_DIRS, prune_scratch  # noqa: E402


def du(path):
    return sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="default: <results_dir>/raw")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    root = Path(a.root) if a.root else Path(C.results_dir(cfg)) / "raw"
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
