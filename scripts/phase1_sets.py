#!/usr/bin/env python3
"""Assign the design sets (docs/PLAN.md 1.4 / 1.5) from the inventory and the E4 trial (src/designs/sets.py).

    .venv/bin/python scripts/phase1_sets.py cktevo    # the ~30-module CktEvo set from the pool (tag cktevo_set)
    .venv/bin/python scripts/phase1_sets.py split     # dev (RTLLM, seeded stratified sample) / held; writes config lists
    .venv/bin/python scripts/phase1_sets.py sky130    # cktevo_sky130 tags after the sky130hd knee sweep

Eligibility for any set: e4_synthesizable = 1, single clock (no multi_clock tag) and readable by Yosys (no
yosys_failed tag: V1 / the Y rung need it). rtlrewriter is calibration-only and gets no split. The lists are written
into config/experiments.yaml (design_sets.suites.<suite>.dev / held / sky130_subset), the designs table (`split`,
`tags`) and design.json (`tags`).
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
from src.designs import sets as S  # noqa: E402

SET_TAGS = ("cktevo_set", "cktevo_sky130")


def eligible(designs, rows):
    out = []
    for d in designs:
        r = rows.get(d["design_id"])
        if r and r["e4_synthesizable"] == 1 and "multi_clock" not in d["tags"] and "yosys_failed" not in d["tags"]:
            out.append(d)
    return out


def retag(conn, d, add=(), remove=()):
    tags = [t for t in d["tags"] if t not in remove] + [t for t in add if t not in d["tags"]]
    d["tags"] = tags
    K.write_design(d)
    conn.execute("UPDATE designs SET tags=?, git_sha=?, cfg_hash=? WHERE design_id=?", (json.dumps(tags), C.git_sha(), C.cfg_hash(), d["design_id"]))


def write_config(edits):
    """Rewrite the list fields in place and validate: a config that no longer loads would kill every queue runner
    (DECISIONS 2026-09-12), so the previous text is restored on any error."""
    p = Path(C.CONFIG_PATH)
    before = p.read_text()
    text = before
    for suite, field, values in edits:
        text = S.set_yaml_list(text, suite, field, values)
    p.write_text(text)
    C.cfg_hash.cache_clear()
    try:
        cfg = C.load(str(p))
        for suite, field, values in edits:
            assert cfg["design_sets"]["suites"][suite][field] == list(values), (suite, field)
    except Exception:
        p.write_text(before)
        C.cfg_hash.cache_clear()
        raise


def cmd_cktevo(cfg, conn, rows):
    params = cfg["design_sets"]["suites"]["cktevo"]
    pool = eligible(K.load_all("cktevo"), rows)
    chosen = S.select_cktevo_set(pool, int(params["target_count"]), int(params["max_per_repo"]))
    ids = {d["design_id"] for d in chosen}
    for d in K.load_all("cktevo"):
        retag(conn, d, add=(["cktevo_set"] if d["design_id"] in ids else []), remove=([] if d["design_id"] in ids else ["cktevo_set"]))
    print(f"cktevo pool eligible {len(pool)} → set {len(chosen)} (target {params['target_count']}, ≤{params['max_per_repo']} per repository):")
    for d in chosen:
        print(f"  {d['design_id']:40s} loc={d['loc']}")
    write_config([("cktevo", "held", sorted(ids))])
    return 0


def cmd_split(cfg, conn, rows):
    sp = cfg["design_sets"]["split"]
    dev_suite = sp["dev_suite"]
    dev_pool = eligible(K.load_all(dev_suite), rows)
    dev = S.stratified_sample(dev_pool, int(sp["dev_count"]), int(sp["seed"]))
    dev_ids = {d["design_id"] for d in dev}
    edits, summary = [], {}
    for suite in ("rtllm", "drrtl", "rtlopt", "cktevo"):
        designs = K.load_all(suite)
        held = []
        for d in designs:
            r = rows.get(d["design_id"])
            ok = d in eligible([d], rows) and (suite != "cktevo" or "cktevo_set" in d["tags"])
            split = "dev" if d["design_id"] in dev_ids else ("held" if ok else None)
            if split == "held":
                held.append(d["design_id"])
            conn.execute("UPDATE designs SET split=?, git_sha=?, cfg_hash=? WHERE design_id=?", (split, C.git_sha(), C.cfg_hash(), d["design_id"]))
        edits.append((suite, "held", sorted(held)))
        if suite == dev_suite:
            edits.append((suite, "dev", sorted(dev_ids)))
        summary[suite] = {"dev": sum(1 for d in designs if d["design_id"] in dev_ids), "held": len(held), "excluded": len(designs) - len(held) - sum(1 for d in designs if d["design_id"] in dev_ids)}
    conn.execute("UPDATE designs SET split=NULL WHERE suite='rtlrewriter'")
    write_config(edits)
    print(f"dev ({dev_suite}, {len(dev)} designs, seed {sp['seed']}, stratified by {sp['stratify_by']}): {' '.join(sorted(dev_ids))}")
    for suite, s in summary.items():
        print(f"  {suite:8s} dev={s['dev']:3d} held={s['held']:3d} excluded(not eligible / not in set)={s['excluded']:3d}")
    return 0


def cmd_sky130(cfg, conn, rows):
    n = int(cfg["design_sets"]["sky130_subset_count"])
    cands = []
    for d in K.load_all("cktevo"):
        r = rows.get(d["design_id"])
        if "cktevo_set" not in d["tags"] or not r or r["phi_main_ns_sky130hd"] is None:
            continue
        table = json.loads(r["knee_table_json"] or "{}").get("sky130hd") or {}
        if table.get("fallback"):
            continue
        cands.append(d)
    chosen = S.select_sky130_subset(cands, n)
    ids = {d["design_id"] for d in chosen}
    for d in K.load_all("cktevo"):
        retag(conn, d, add=(["cktevo_sky130"] if d["design_id"] in ids else []), remove=([] if d["design_id"] in ids else ["cktevo_sky130"]))
    write_config([("cktevo", "sky130_subset", sorted(ids))])
    print(f"cktevo_sky130 subset ({len(chosen)} of {len(cands)} candidates with a met sky130hd knee): {' '.join(sorted(ids))}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["cktevo", "split", "sky130"])
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    rows = {r["design_id"]: dict(r) for r in conn.execute("SELECT * FROM designs")}
    return {"cktevo": cmd_cktevo, "split": cmd_split, "sky130": cmd_sky130}[a.what](cfg, conn, rows)


if __name__ == "__main__":
    sys.exit(main())
