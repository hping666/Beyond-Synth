#!/usr/bin/env python3
"""SAIF activity files for the noise runs (src/noise/saif.py) and the equivalence-scratch retention.

    .venv/bin/python scripts/phase2_saif.py build [--suite ...] [--design ...] [--jobs 8]
    .venv/bin/python scripts/phase2_saif.py prune [--suite ...] [--design ...]   # VCD (once SAIF exists) + VCS builds
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.noise import saif as S  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["build", "prune"])
    ap.add_argument("--suite", nargs="*", default=None)
    ap.add_argument("--design", nargs="*", default=None)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    rows = {r["design_id"]: dict(r) for r in conn.execute("SELECT design_id, split, e4_synthesizable FROM designs")}
    designs = []
    for d in K.load_all():
        if a.suite and d["suite"] not in a.suite:
            continue
        if a.design and d["design_id"] not in a.design:
            continue
        r = rows.get(d["design_id"]) or {}
        eligible = r.get("e4_synthesizable") == 1 and "multi_clock" not in d["tags"] and "yosys_failed" not in d["tags"]
        if r.get("split") in ("dev", "held") or (d["suite"] == "rtlrewriter" and eligible):
            designs.append(d)
    if a.what == "build":
        out = S.build_all(designs, conn, cfg, workers=a.jobs)
        n_d = sum(1 for r in out.values() if (r.get("design") or {}).get("saif"))
        n_p = sum(len(r.get("perturbations") or {}) for r in out.values())
        n_miss = sum(len(r.get("missing") or []) for r in out.values())
        print(f"{len(designs)} designs: {n_d} design SAIFs, {n_p} perturbation SAIFs, {n_miss} without a VCD")
        return 0
    freed = 0
    for d in designs:
        freed += S.prune_eq_scratch(cfg, d["design_id"], conn)
    print(f"pruned {freed / 1e9:.1f} GB of equivalence scratch (VCDs with SAIF, VCS builds) for {len(designs)} designs")
    # the non-proven rule (DECISIONS 2026-09-14, user): every design directory that holds equivalence records
    tot = {"freed": 0, "vcd_deleted": 0, "vcd_compressed": 0, "builds": 0}
    raw_root = Path(C.results_dir(cfg)) / "raw"
    for dd in sorted(p for p in raw_root.iterdir() if (p / "EQ").is_dir()):
        r = S.prune_nonproven_scratch(cfg, dd.name, log=print)
        for k in tot:
            tot[k] += r[k]
    print(f"non-proven records: freed {tot['freed'] / 1e9:.1f} GB (falsified VCDs deleted {tot['vcd_deleted']}, kept VCDs compressed {tot['vcd_compressed']}, VCS builds removed {tot['builds']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
