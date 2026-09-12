#!/usr/bin/env python3
"""Consistency checks of the visible results database (docs/spec/07-results-db.md).

    .venv/bin/python scripts/db_check.py

Checks: every evaluations row's raw directory and meta.json exist and carry the same status; every perturbation
file exists; every design row with a split has the inventory columns and (once the sweeps ran) Phi_main; failed
queue jobs are counted. Exit 1 when a hard check fails.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import json  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402


def check(conn, root=None):
    root = Path(root or C.ROOT)
    problems, warnings, counts = [], [], {}
    rows = conn.execute("SELECT eval_id, design_id, config, status, raw_dir FROM evaluations").fetchall()
    counts["evaluations"] = len(rows)
    for r in rows:
        meta = Path(r["raw_dir"]) / "meta.json"
        if not meta.exists():
            problems.append(f"evaluation {r['eval_id']} ({r['design_id']} {r['config']}): meta.json missing at {r['raw_dir']}")
            continue
        try:
            st = json.loads(meta.read_text()).get("status")
        except json.JSONDecodeError:
            problems.append(f"evaluation {r['eval_id']}: unreadable meta.json")
            continue
        if st != r["status"]:
            problems.append(f"evaluation {r['eval_id']}: status {r['status']} in the DB but {st} on disk")
    perts = conn.execute("SELECT pert_id, design_id, path FROM perturbations").fetchall()
    counts["perturbations"] = len(perts)
    for p in perts:
        if not (root / p["path"]).exists() and not Path(p["path"]).exists():
            problems.append(f"perturbation {p['pert_id']} of {p['design_id']}: file missing {p['path']}")
    designs = conn.execute("SELECT * FROM designs").fetchall()
    counts["designs"] = len(designs)
    for d in designs:
        if d["split"] in ("dev", "held"):
            for col in ("suite", "path", "loc", "tb_available", "e4_synthesizable"):
                if d[col] is None:
                    problems.append(f"design {d['design_id']} ({d['split']}): {col} is NULL")
            if d["phi_main_ns_nangate45"] is None:
                warnings.append(f"design {d['design_id']} ({d['split']}): no Phi_main(nangate45) yet")
    counts["jobs_failed"] = conn.execute("SELECT COUNT(*) FROM jobs WHERE state='failed'").fetchone()[0]
    counts["jobs_active"] = conn.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','running','backoff')").fetchone()[0]
    return problems, warnings, counts


def main(argv=None):
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    problems, warnings, counts = check(conn)
    print("counts:", counts)
    for w in warnings[:20]:
        print("warning:", w)
    if len(warnings) > 20:
        print(f"... {len(warnings) - 20} more warnings")
    for p in problems[:50]:
        print("PROBLEM:", p)
    print(f"{len(problems)} problems, {len(warnings)} warnings")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
