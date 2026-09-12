#!/usr/bin/env python3
"""The only reader of the hidden results database (docs/spec/06-hidden-layer.md, CLAUDE.md rule 3).

    .venv/bin/python scripts/report_hidden.py [--check]

Refuses to open the hidden database until STATUS.md carries the Phase 5 completion marker
(`PHASE5_COMPLETE: yes`, written by the human at the end of Phase 5). --check only reports whether the marker is
present. The certification report itself (retained-gain curves under H1-H5, reverse-error sample, sigma_D under the
hidden configurations) is implemented in Phase 5; until then this script never touches the file.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402

MARKER = re.compile(r"^PHASE5_COMPLETE:\s*yes\s*$", re.M)


def phase5_complete(status_path=None):
    p = Path(status_path or (Path(C.ROOT) / "STATUS.md"))
    return bool(p.exists() and MARKER.search(p.read_text()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only report whether the completion marker is present")
    ap.add_argument("--status-file", default=None)
    a = ap.parse_args(argv)
    ok = phase5_complete(a.status_file)
    print(f"Phase 5 completion marker in STATUS.md: {'present' if ok else 'absent'}")
    if a.check:
        return 0
    if not ok:
        print("refusing to read the hidden database before Phase 5 is complete (spec 06)", file=sys.stderr)
        return 3
    print("hidden report: not implemented before Phase 5", file=sys.stderr)
    return 4


if __name__ == "__main__":
    sys.exit(main())
