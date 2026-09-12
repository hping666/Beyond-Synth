#!/usr/bin/env python3
"""The only writer of the hidden results database (docs/spec/06-hidden-layer.md, spec 07; CLAUDE.md rule 3).
Phase 5 adds the certification loop (H1-H5 for archived candidates and the 10% rejected sample). Today:

    .venv/bin/python scripts/hidden_worker.py --migrate-phase0

moves the Phase 0 smoke records of hidden configurations (produced before src/eval/service.py routed hidden
configurations) out of the visible database and raw tree into the hidden ones. Only counts are printed, never metrics.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402


def hidden_db_path(cfg):
    return os.path.join(C.results_dir(cfg), "hidden", "hidden.sqlite")


def hidden_configs(cfg):
    return sorted(n for n, c in cfg["configs"].items() if isinstance(c, dict) and c.get("hidden"))


def _fix_meta(job_dir):
    m = Path(job_dir) / "meta.json"
    if m.exists():
        try:
            meta = json.loads(m.read_text())
        except json.JSONDecodeError:
            return
        meta["raw_dir"] = str(job_dir)
        m.write_text(json.dumps(meta, indent=1, sort_keys=True, default=str))


def migrate_phase0(cfg):
    names = hidden_configs(cfg)
    vis = db.connect(cfg=cfg)
    hid = db.connect(path=hidden_db_path(cfg))
    raw_root = Path(C.results_dir(cfg)) / "raw"
    hid_root = Path(C.results_dir(cfg)) / "hidden" / "raw"
    moved_rows = moved_dirs = 0
    marks = ",".join("?" for _ in names)
    for r in vis.execute(f"SELECT * FROM evaluations WHERE config IN ({marks}) ORDER BY eval_id", names).fetchall():
        r = dict(r)
        eval_id = r.pop("eval_id")
        old = Path(r["raw_dir"])
        try:
            rel = old.resolve().relative_to(raw_root.resolve())
        except ValueError:
            rel = None
        new = (hid_root / rel) if rel else old
        if rel and old.exists():
            new.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old), str(new))
            _fix_meta(new)
            moved_dirs += 1
        r["raw_dir"] = str(new)
        cols = list(r)
        hid.execute(f"INSERT OR IGNORE INTO evaluations ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})", tuple(r.values()))
        vis.execute("DELETE FROM evaluations WHERE eval_id=?", (eval_id,))
        moved_rows += 1
    for design_dir in sorted(p for p in raw_root.glob("*") if p.is_dir()):
        for name in names:
            src = design_dir / name
            if not src.is_dir():
                continue
            for job in sorted(src.iterdir()):
                new = hid_root / design_dir.name / name / job.name
                new.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(job), str(new))
                _fix_meta(new)
                moved_dirs += 1
            if not any(src.iterdir()):
                src.rmdir()
    print(f"hidden configurations {names}: {moved_rows} evaluation rows and {moved_dirs} raw directories moved into the hidden tree")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--migrate-phase0", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    if a.migrate_phase0:
        return migrate_phase0(cfg)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
