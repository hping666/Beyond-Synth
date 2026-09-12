#!/usr/bin/env python3
"""Consistent snapshot of the visible results database (sqlite backup API, safe under WAL) into
results/snapshots/results_<timestamp>_<git sha>.sqlite (gitignored; DECISIONS: snapshots stay out of git).

    .venv/bin/python scripts/snapshot.py [--out DIR]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import datetime  # noqa: E402
import sqlite3  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402


def snapshot(src_path, out_dir, tag=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"results_{datetime.datetime.now():%Y%m%d_%H%M%S}_{tag or C.git_sha()}.sqlite"
    dst = out_dir / name
    src = sqlite3.connect(str(src_path))
    dest = sqlite3.connect(str(dst))
    with dest:
        src.backup(dest)
    src.close()
    dest.close()
    return dst


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    cfg = C.load()
    dst = snapshot(db.db_path(cfg), a.out or os.path.join(C.results_dir(cfg), "snapshots"))
    print(f"snapshot: {dst} ({dst.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
