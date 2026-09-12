#!/usr/bin/env python3
"""Phase 1.1: stage the design sets from the pinned upstream checkouts into data/designs/<suite>/ (src/designs/stage.py).

    .venv/bin/python scripts/stage_designs.py [--suite rtllm drrtl rtlopt cktevo rtlrewriter]

Writes per suite: <design>/design.json (+ rtl/, tb/, reference/, samples/ copies, gitignored), index.json, SOURCE.md,
and for cktevo POOL.json (every module of every repository with its closure and exclusion reasons).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402

from src import config as C  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.designs import stage as S  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", nargs="+", default=list(S.STAGERS), choices=list(S.STAGERS))
    a = ap.parse_args(argv)
    cfg = C.load()
    total = 0
    for suite in a.suite:
        designs, skipped = S.STAGERS[suite](cfg)
        S.write_suite_index(cfg, suite, designs, skipped)
        print(f"{suite:12s} staged {len(designs):3d}  skipped {len(skipped):2d}  -> {K.DESIGNS_DIR / suite}")
        for n, why in skipped:
            print(f"    skipped {n}: {why}")
        total += len(designs)
    print(f"total staged: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
