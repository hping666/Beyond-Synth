#!/usr/bin/env python3
"""Generate (and optionally submit) the Phase 1 EDA jobs from the staged catalogue (src/designs/jobs.py).

    .venv/bin/python scripts/phase1_jobs.py trial [--suite ...] [--submit] [--priority N]
    .venv/bin/python scripts/phase1_jobs.py knee  [--suite ...] [--libs nangate45 asap7 sky130hd] [--only-e4-ok] [--submit]

trial: E4 at the loosest knee period on Nangate45 for every staged design (PLAN 1.2 synthesizability).
knee : every knee period per library (config knee.periods_ns, knee.configs); multi_clock designs are skipped.
The YAML goes to results/queue/jobs/; --submit inserts the jobs into the queue for the daemon.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import datetime  # noqa: E402
from pathlib import Path  # noqa: E402

import yaml  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.designs import jobs as J  # noqa: E402
from src.jobqueue.core import Queue  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["trial", "knee", "knee-ext"])
    ap.add_argument("--suite", nargs="*", default=None)
    ap.add_argument("--design", nargs="*", default=None, help="restrict to these design_ids")
    ap.add_argument("--tag", nargs="*", default=None, help="restrict to designs carrying every one of these tags (e.g. cktevo_set)")
    ap.add_argument("--libs", nargs="*", default=None)
    ap.add_argument("--only-e4-ok", action="store_true", help="knee: only designs with designs.e4_synthesizable = 1")
    ap.add_argument("--priority", type=int, default=0)
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    designs = [d for d in K.load_all() if (not a.suite or d["suite"] in a.suite) and (not a.design or d["design_id"] in a.design)
               and (not a.tag or all(t in d["tags"] for t in a.tag))]
    conn = db.connect(cfg=cfg)
    if a.only_e4_ok:
        ok = {r[0] for r in conn.execute("SELECT design_id FROM designs WHERE e4_synthesizable = 1")}
        designs = [d for d in designs if d["design_id"] in ok]
    if a.what == "knee-ext":  # DECISIONS 2026-09-14: tighter periods only where Phi_main is the tightest swept period
        need = J.designs_at_tightest_period(cfg, conn)
        if a.libs:
            need = {lib: ids for lib, ids in need.items() if lib in a.libs}
        print({lib: len(ids) for lib, ids in need.items()})
        jobs = J.knee_ext_jobs(cfg, designs, need, priority=a.priority)
    else:
        jobs = J.trial_jobs(cfg, designs, priority=a.priority) if a.what == "trial" else J.knee_jobs(cfg, designs, libs=a.libs, priority=a.priority)
    out = Path(C.results_dir(cfg)) / "queue" / "jobs" / f"phase1_{a.what}_{datetime.datetime.now():%Y%m%d_%H%M%S}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump({"jobs": jobs}, sort_keys=False))
    print(f"{len(jobs)} {a.what} jobs for {len(designs)} designs -> {out}")
    if a.submit:
        q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
        ids = [q.submit(j["kind"], j["payload"], design_id=j["design_id"], config=j["config"], priority=j["priority"],
                        timeout_sec=j["timeout_sec"]) for j in jobs]
        print(f"submitted {len(ids)} jobs (first {ids[0] if ids else '-'}); the daemon dispatches them: scripts/status.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
