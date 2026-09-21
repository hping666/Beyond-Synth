#!/usr/bin/env python3
"""Pause every running experiment process of the project and record the state (user instruction 2026-09-20 12:35 / 22:20:
pause once Stage B and Stage C have produced their reports, without waiting for a confirmation).

Order (DECISIONS 2026-09-20 12:40): the stages loop, the offline pool, the hidden loop, the queue daemon, the load logger.
Nothing is cancelled: queued jobs stay queued, running jobs are left to finish (the daemon recovers them on the next start),
the pool's state file keeps every candidate's stage, and the hidden registrations stay queued behind their zero-seat ceiling.
A snapshot of what was running goes to reports/data/pause_state_<timestamp>.json and a section to STATUS.md.

  python3 scripts/pause_experiments.py            # dry run: what would be stopped
  python3 scripts/pause_experiments.py --apply
  python3 scripts/pause_experiments.py --apply --wait-for-markers   # wait for both stage markers first
"""
import argparse
import collections
import datetime
import json
import os
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402

# (name, pid file, stop command) in the order they are stopped
TARGETS = [
    ("stages loop", "phase5_stages.pid", [sys.executable, os.path.join(ROOT, "scripts", "phase5_stages.py"), "stop"]),
    ("offline pool", "offline_pool.pid", [sys.executable, os.path.join(ROOT, "scripts", "offline_pool.py"), "stop"]),
    ("hidden loop", "hidden_loop.pid", [sys.executable, os.path.join(ROOT, "scripts", "hidden_loop.py"), "stop"]),
    ("queue daemon", "daemon.pid", [sys.executable, os.path.join(ROOT, "scripts", "queue", "daemon.py"), "stop"]),
    ("load logger", "load_logger.pid", None),   # no stop command: SIGTERM to the pid
]
MARKERS = [os.path.join(ROOT, "reports", "data", "phase5_stage_B.done"), os.path.join(ROOT, "reports", "data", "phase5_stage_C.done")]
RESUME = ["setsid .venv/bin/python3 scripts/queue/daemon.py start",
          ".venv/bin/python3 scripts/offline_pool.py start",
          ".venv/bin/python3 scripts/phase5_stages.py start",
          ".venv/bin/python3 scripts/hidden_loop.py start",
          "the 18 held drrtl_LSTM search jobs (Stage A) need their `hold` payload flag removed — a separate decision"]


def alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def pid_of(cfg, name):
    p = os.path.join(C.results_dir(cfg), "queue", name)
    try:
        with open(p) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    return pid if alive(pid) else None


def snapshot(cfg, conn):
    from src.analysis import phase5 as P5
    tier_of = P5.tier_of_design(cfg)
    runs = collections.defaultdict(collections.Counter)
    for r in conn.execute("SELECT design_id, status, COUNT(*) n FROM runs WHERE exp='phase5' AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0 GROUP BY 1,2"):
        runs[tier_of.get(r[0], "?")][r[1]] += r[2]
    jobs = {f"{r[0]}|{r[1]}": r[2] for r in conn.execute("SELECT kind, state, COUNT(*) FROM jobs WHERE state IN ('queued','running','backoff') GROUP BY 1,2")}
    pool = {}
    try:
        with open(os.path.join(C.results_dir(cfg), "queue", "offline_pool_state.json")) as f:
            st = json.load(f)
        g = collections.defaultdict(collections.Counter)
        for v in (st.get("cands") or {}).values():
            g[v.get("group")][v.get("stage")] += 1
        pool = {k: dict(v) for k, v in g.items()}
    except (OSError, ValueError):
        pool = {"error": "state file unreadable"}
    held = conn.execute("SELECT COUNT(*) FROM jobs WHERE kind='search' AND state='queued' AND payload_json LIKE '%\"hold\"%'").fetchone()[0]
    return {"at": datetime.datetime.now().isoformat(timespec="seconds"), "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(),
            "runs_by_tier": {k: dict(v) for k, v in runs.items()}, "open_jobs": jobs, "offline_pool_groups": pool,
            "held_search_jobs": held, "stage_markers": {os.path.basename(m): os.path.exists(m) for m in MARKERS},
            "processes": {name: pid_of(cfg, pidfile) for name, pidfile, _ in TARGETS}, "resume": RESUME}


def stop_all(cfg, apply):
    out = []
    for name, pidfile, cmd in TARGETS:
        pid = pid_of(cfg, pidfile)
        if pid is None:
            out.append({"target": name, "pid": None, "action": "not running"})
            continue
        if not apply:
            out.append({"target": name, "pid": pid, "action": "would stop"})
            continue
        if cmd:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=300)
            note = (r.stdout or r.stderr).strip().splitlines()[-1][:120] if (r.stdout or r.stderr).strip() else ""
        else:
            os.kill(pid, signal.SIGTERM)
            note = "SIGTERM"
        for _ in range(30):
            if not alive(pid):
                break
            time.sleep(1)
        out.append({"target": name, "pid": pid, "action": "stopped" if not alive(pid) else "still alive after 30 s", "note": note})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--wait-for-markers", action="store_true", help="wait until both stage markers exist before stopping")
    ap.add_argument("--poll", type=int, default=120)
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    if a.wait_for_markers:
        while not all(os.path.exists(m) for m in MARKERS):
            time.sleep(a.poll)
    snap = snapshot(cfg, conn)
    snap["stopped"] = stop_all(cfg, a.apply)
    snap["applied"] = bool(a.apply)
    path = os.path.join(ROOT, "reports", "data", f"pause_state_{datetime.datetime.now():%Y%m%d_%H%M%S}.json")
    if a.apply:
        with open(path, "w") as f:
            json.dump(snap, f, indent=1, default=str)
        snap["snapshot_file"] = path
        lines = [f"\n## Experiments paused {snap['at']} (user instruction 2026-09-20 12:35 / 22:20)\n",
                 f"Stopped, in order: " + "; ".join(f"{x['target']} ({x['action']}{', pid ' + str(x['pid']) if x['pid'] else ''})" for x in snap["stopped"]) + ".",
                 f"State at the pause: runs {snap['runs_by_tier']}; open jobs {snap['open_jobs']}; offline-pool groups {snap['offline_pool_groups']}; held search jobs {snap['held_search_jobs']} "
                 f"(Stage A's drrtl_LSTM runs); stage markers {snap['stage_markers']}. Nothing was cancelled: queued jobs stay queued and the pool's state file keeps every candidate's stage. "
                 f"Snapshot: {os.path.relpath(path, ROOT)}.",
                 "Resume: " + "; ".join(RESUME) + ".\n"]
        with open(os.path.join(ROOT, "STATUS.md"), "a") as f:
            f.write("\n".join(lines) + "\n")
    print(json.dumps(snap, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
