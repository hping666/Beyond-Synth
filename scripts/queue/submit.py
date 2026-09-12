#!/usr/bin/env python3
"""Submit jobs to the queue from a YAML file.

    .venv/bin/python scripts/queue/submit.py jobs.yaml [--dry-run]

jobs.yaml:
    jobs:
      - kind: shell                 # shell | dc | pt | vcf | sim | yosys | orfs | llm
        payload: {cmd: "echo hello"}
        priority: 5                 # higher runs first (default 0)
        timeout_sec: 60             # default from config: timeouts by kind
      - kind: dc
        design_id: rtllm_accu
        config: E4
        payload: {rtl: data/designs/rtllm/accu/accu.v, top: accu}
Only selectors and payloads live here; rung commands, constraints and caps come from config/experiments.yaml.
"""
import argparse
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[0] = ROOT

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from scripts.queue.core import Queue, POOL_OF_KIND  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("yaml_file")
    ap.add_argument("--dry-run", action="store_true", help="validate and print, insert nothing")
    a = ap.parse_args(argv)
    cfg = C.load()
    with open(a.yaml_file) as f:
        spec = yaml.safe_load(f) or {}
    jobs = spec.get("jobs") or []
    if not isinstance(jobs, list) or not jobs:
        print("no jobs found (expected a top-level list `jobs:`)", file=sys.stderr)
        return 2
    q = Queue(cfg, db.connect(cfg=cfg), os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    ids = []
    for i, j in enumerate(jobs):
        kind = j.get("kind")
        pool = j.get("pool") or (j.get("payload") or {}).get("pool") or POOL_OF_KIND.get(kind)
        if pool not in q.caps:
            print(f"job {i}: unknown kind/pool {kind!r}/{pool!r}", file=sys.stderr)
            return 2
        line = (f"[{i}] kind={kind} pool={pool} priority={j.get('priority', 0)} design={j.get('design_id')} "
                f"config={j.get('config')} timeout={j.get('timeout_sec', 'default')} payload={j.get('payload')}")
        if a.dry_run:
            print("DRY-RUN " + line)
            continue
        jid = q.submit(kind, j.get("payload") or {}, design_id=j.get("design_id"), cand_id=j.get("cand_id"),
                       config=j.get("config"), priority=j.get("priority", 0), timeout_sec=j.get("timeout_sec"), pool=pool)
        ids.append(jid)
        print(f"{jid} " + line)
    if not a.dry_run:
        print(f"submitted {len(ids)} job(s); the daemon dispatches them (scripts/queue/daemon.py status)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
