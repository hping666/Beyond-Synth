#!/usr/bin/env python3
"""Exp1 (Phase 4) design set and the Phase 5 exclusion (DECISIONS 2026-09-14, C1 scope): CktEvo 5 + Dr.RTL 3 + RTL-OPT 2,
all held, chosen deterministically among designs with a measured E4 floor and an E4 baseline at Phi_main — CktEvo one
per repository first (largest by LOC), Dr.RTL and RTL-OPT largest by LOC first, offset designs last. The list is written
into config `exp1.designs` and `design_sets.phase5_excluded` (rule 11: lists live only in config).

    .venv/bin/python scripts/phase4_sets.py designs [--write]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import re  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402


def candidates(conn, suite):
    rows = [dict(r) for r in conn.execute(
        "SELECT d.design_id, d.loc, (SELECT n.floor_class FROM noise_floor n WHERE n.design_id=d.design_id AND n.config='E4' AND n.metric='area' AND n.floor_source='measured' ORDER BY n.created_at DESC LIMIT 1) AS floor_class "
        "FROM designs d WHERE d.suite=? AND d.split='held' AND d.phi_main_ns_nangate45 IS NOT NULL AND EXISTS "
        "(SELECT 1 FROM noise_floor n WHERE n.design_id=d.design_id AND n.config='E4' AND n.metric='area' AND n.floor_source='measured') AND EXISTS "
        "(SELECT 1 FROM evaluations e WHERE e.design_id=d.design_id AND e.config='E4' AND e.is_baseline=1 AND e.status='ok' AND abs(e.clock_ns-d.phi_main_ns_nangate45)<1e-6) "
        "ORDER BY d.loc DESC, d.design_id", (suite,))]
    return sorted(rows, key=lambda r: (r["floor_class"] == "offset", -int(r["loc"] or 0), r["design_id"]))


def select(conn, cfg):
    quota = cfg["exp1"]["b0_designs"]
    chosen = []
    ck = candidates(conn, "cktevo")
    seen_repo = set()
    for r in ck:                                   # one per repository first
        repo = r["design_id"].split("__")[0]
        if repo in seen_repo:
            continue
        seen_repo.add(repo)
        chosen.append(r["design_id"])
        if len(chosen) >= quota["cktevo_held"]:
            break
    for r in ck:
        if len(chosen) >= quota["cktevo_held"]:
            break
        if r["design_id"] not in chosen:
            chosen.append(r["design_id"])
    for suite, key in (("drrtl", "drrtl_held"), ("rtlopt", "rtlopt_held")):
        chosen += [r["design_id"] for r in candidates(conn, suite)[:quota[key]]]
    return chosen


def write_config(cfg_path, designs):
    text = open(cfg_path).read()
    text2 = re.sub(r"^(  designs: )\[.*?\](\s+# filled by scripts/phase4_sets.py.*)$", lambda m: f"{m.group(1)}[{', '.join(designs)}]{m.group(2)}", text, count=1, flags=re.M)
    text2 = re.sub(r"^(  phase5_excluded: )\[.*?\](\s+# filled by scripts/phase4_sets.py.*)$", lambda m: f"{m.group(1)}[{', '.join(designs)}]{m.group(2)}", text2, count=1, flags=re.M)
    assert text2 != text, "config anchors not found"
    open(cfg_path, "w").write(text2)
    cfg = C.load()
    assert cfg["exp1"]["designs"] == designs and cfg["design_sets"]["phase5_excluded"] == designs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["designs"])
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    designs = select(conn, cfg)
    for d in designs:
        r = conn.execute("SELECT loc FROM designs WHERE design_id=?", (d,)).fetchone()
        print(f"  {d:40s} loc {r[0]}")
    print(f"{len(designs)} Exp1 designs")
    if a.write:
        write_config(os.path.join(ROOT, "config", "experiments.yaml"), designs)
        print("written to config exp1.designs and design_sets.phase5_excluded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
