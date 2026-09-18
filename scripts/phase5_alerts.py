#!/usr/bin/env python3
"""DECISION 2026-09-18 (d) F3: the completion alert of the hourly check. Computes the complete-design set (src.analysis.phase5
.completion_view), compares it with the last recorded one (reports/data/phase5_complete_designs.json) and, when it changed, prints
the "New complete designs since last render" line first, appends it to STATUS.md and records the new set. Exit 0 always.
    .venv/bin/python scripts/phase5_alerts.py [--dry-run]"""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
from src import config as C  # noqa: E402
from src.analysis import phase5 as P5  # noqa: E402
from src.db import core as db  # noqa: E402


def main(argv=None):
    dry = "--dry-run" in (argv or sys.argv[1:])
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    new, line, view = P5.completion_alert(cfg, conn, write=not dry)
    r = view["reachability"]
    if line:
        print(line)
    else:
        print(f"No new complete design ({len(view['complete'])} complete: " + (", ".join(view["complete"]) or "none") + f"; tally {r['wins']} wins, {r['lost']} lost, {r['undecided']} undecided; {r['wins_still_needed']} wins still needed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
