#!/usr/bin/env python3
"""Phase 5 starting points (G5 decisions item 1, DECISIONS 2026-09-15): 30 held designs stratified by tier — 18 medium
(module-level CktEvo and mid-size Dr.RTL / RTL-OPT designs), 6 small human-written, 6 large multi-module — drawn with a
seed from the held pool (config `design_sets.pool_suites`, the ten Exp1 designs excluded, an E4 floor of the current
version required), balanced over the suites of each tier. The tier of a design follows `exp5.tier_rule` (E4 baseline cell
count and the number of modules of its RTL). The selection is written into config `exp5.starting_points` (rule 11: the
list lives in config) and printed.
    .venv/bin/python scripts/phase5_sets.py [--write] [--seed N]
"""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.designs import verilog as V  # noqa: E402


def module_count(d):
    return sum(len(V.module_names(Path(d["_dir"], f).read_text(errors="replace"))) for f in d["files"])


def tier_of(cells, modules, rule):
    """large = multi-module designs of at least `large_multimodule_min_cells` (G5: "6 large multi-module"); small = one
    module below `small_max_cells`; single-module designs of `large_min_cells` or more are neither mid-size nor multi-module
    and stay out of the draw (`large_single`); medium = the rest."""
    if cells is None:
        return None
    if modules >= 2 and cells >= int(rule["large_multimodule_min_cells"]):
        return "large"
    if modules == 1 and cells >= int(rule["large_min_cells"]):
        return "large_single"
    if modules == 1 and cells < int(rule["small_max_cells"]):
        return "small"
    return "medium"


def pool(cfg, conn):
    """[(design_id, suite, cells, modules, tier)] of the eligible held designs."""
    rule = cfg["exp5"]["tier_rule"]
    suites = set(cfg["design_sets"].get("pool_suites") or ["cktevo", "drrtl", "rtlopt"])
    excluded = set(cfg["design_sets"].get("phase5_excluded") or [])
    fv = cfg["noise"].get("floor_version")
    cat = {d["design_id"]: d for d in K.load_all()}
    out = []
    for r in conn.execute("SELECT design_id, suite, tags FROM designs WHERE split='held' AND e4_synthesizable=1 ORDER BY design_id"):
        did, suite = r[0], r[1]
        if suite not in suites or did in excluded or did not in cat:
            continue
        tags = json.loads(r[2] or "[]")
        if "multi_clock" in tags:
            continue
        cells = conn.execute("SELECT cells FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' ORDER BY eval_id DESC LIMIT 1", (did,)).fetchone()
        floor = conn.execute("SELECT 1 FROM noise_floor WHERE design_id=? AND config='E4' AND metric='area' AND floor_version=? LIMIT 1", (did, fv)).fetchone()
        if cells is None or floor is None:
            continue
        modules = module_count(cat[did])
        out.append((did, suite, int(cells[0]), modules, tier_of(int(cells[0]), modules, rule)))
    return out


def select(cfg, conn, seed):
    """Seeded stratified draw: per tier the quota of `exp5.tiers`, round-robin over the suites (each suite's candidates
    shuffled with the seed) so that no suite dominates a tier; large: multi-module designs first."""
    rows = pool(cfg, conn)
    rng = random.Random(int(seed))
    chosen = {}
    for tier, quota in cfg["exp5"]["tiers"].items():
        cands = [r for r in rows if r[4] == tier]
        by_suite = {}
        for r in cands:
            by_suite.setdefault(r[1], []).append(r)
        for s in by_suite:
            rng.shuffle(by_suite[s])
        suites = sorted(by_suite)
        rng.shuffle(suites)
        picked = []
        while len(picked) < int(quota) and any(by_suite[s] for s in suites):
            for s in suites:
                if by_suite[s] and len(picked) < int(quota):
                    picked.append(by_suite[s].pop(0))
        chosen[tier] = picked
    return rows, chosen


def write_config(chosen):
    """Write `exp5.starting_points` (tier -> [design_id]) into config/experiments.yaml under the exp5 section."""
    p = Path(ROOT) / "config" / "experiments.yaml"
    text = p.read_text()
    block = "  starting_points:                          # filled by scripts/phase5_sets.py (seed exp5.seed; DECISIONS 2026-09-15)\n"
    for tier in ("small", "medium", "large"):
        block += f"    {tier}: [{', '.join(r[0] for r in chosen.get(tier, []))}]\n"
    if re.search(r"^  starting_points:.*\n(?:    (?:small|medium|large): \[.*\]\n)+", text, re.M):
        text = re.sub(r"^  starting_points:.*\n(?:    (?:small|medium|large): \[.*\]\n)+", block, text, count=1, flags=re.M)
    else:
        text = text.replace("  tiers: {medium: 18, small: 6, large: 6}", "  tiers: {medium: 18, small: 6, large: 6}\n" + block.rstrip("\n"), 1)
    p.write_text(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="write exp5.starting_points into config/experiments.yaml")
    ap.add_argument("--seed", type=int, default=None, help="default exp5.seed")
    ap.add_argument("--pool", action="store_true", help="also list the whole pool by tier")
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    seed = a.seed if a.seed is not None else int(cfg["exp5"].get("seed", 1))
    rows, chosen = select(cfg, conn, seed)
    by_tier = {}
    for r in rows:
        by_tier.setdefault(r[4], []).append(r)
    print(f"pool: {len(rows)} eligible held designs (suites {sorted({r[1] for r in rows})}); by tier " + ", ".join(f"{t} {len(v)}" for t, v in sorted(by_tier.items())) + f"; seed {seed}")
    if a.pool:
        for tier, v in sorted(by_tier.items()):
            print(f"  [{tier}] " + ", ".join(f"{r[0]}({r[2]}c,{r[3]}m)" for r in sorted(v, key=lambda r: r[2])))
    for tier in ("small", "medium", "large"):
        print(f"{tier} ({len(chosen.get(tier, []))} of {cfg['exp5']['tiers'][tier]}):")
        for did, suite, cells, modules, _ in chosen.get(tier, []):
            print(f"  {did:40s} {suite:8s} cells {cells:6d} modules {modules}")
    if a.write:
        write_config(chosen)
        cfg2 = C.load()
        assert all(cfg2["exp5"]["starting_points"][t] == [r[0] for r in chosen[t]] for t in chosen)
        print("written to config exp5.starting_points")
    return 0


if __name__ == "__main__":
    sys.exit(main())
