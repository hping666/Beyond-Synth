#!/usr/bin/env python3
"""Queue daemon (CLAUDE.md rule 9). Library module; CLI wrapper: scripts/queue/daemon.py. Run with the project venv python:

    .venv/bin/python scripts/queue/daemon.py start      # detach (own session, log in results/queue/daemon.log)
    .venv/bin/python scripts/queue/daemon.py stop       # SIGTERM; running jobs keep running and are recovered later
    .venv/bin/python scripts/queue/daemon.py status     # pools, caps, backoff
    .venv/bin/python scripts/queue/daemon.py tick       # one scheduling round in the foreground (debugging)

The daemon sources ~/.config/beyond-synth/env.sh (OPENAI_API_KEY, if present) and the EDA env.sh once at start
and hands that environment to every job; it never prints the environment. State lives in the `jobs` and
`queue_state` tables, so `start` after a crash or `stop` resumes where the previous daemon left off.
"""
import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[0] = ROOT

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.jobqueue.core import Queue, _alive  # noqa: E402

SECRETS_FILE = os.path.expanduser("~/.config/beyond-synth/env.sh")


def queue_dir(cfg):
    return os.path.join(C.results_dir(cfg), "queue")


def pid_file(cfg):
    return os.path.join(queue_dir(cfg), "daemon.pid")


def log_file(cfg):
    return os.path.join(queue_dir(cfg), "daemon.log")


def read_pid(cfg):
    try:
        with open(pid_file(cfg)) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def build_env(cfg):
    """Environment for jobs: secrets file (if present) + EDA env.sh, captured once; never logged."""
    files = [SECRETS_FILE, cfg["project"]["eda_env"]]
    parts = [f"if [ -f {shlex.quote(f)} ]; then . {shlex.quote(f)}; fi" for f in files]
    dump = f"exec {shlex.quote(sys.executable)} -c 'import json, os, sys; json.dump(dict(os.environ), sys.stdout)'"
    out = subprocess.run(["bash", "-c", "; ".join(parts + [dump])], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def run_foreground(cfg):
    os.makedirs(queue_dir(cfg), exist_ok=True)
    with open(pid_file(cfg), "w") as f:
        f.write(str(os.getpid()))
    env = build_env(cfg)
    conn = db.connect(cfg=cfg)
    q = Queue(cfg, conn, os.path.join(queue_dir(cfg), "logs"), env=env, python=sys.executable)
    stop = {"flag": False}

    def on_signal(signum, frame):
        stop["flag"] = True

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    q.log(f"daemon started pid={os.getpid()} caps={q.caps} openai_key={'configured' if env.get('OPENAI_API_KEY') else 'not configured'}")
    poll = float(cfg["queue"]["poll_sec"])
    while not stop["flag"]:
        try:
            q.tick()
        except Exception as e:  # keep the daemon alive; the error is in the log
            q.log(f"tick error: {e!r}")
        time.sleep(poll)
    q.log("daemon stopping; running jobs keep running and are recovered by the next start")
    return 0


def start(cfg, foreground=False):
    if foreground:
        return run_foreground(cfg)
    pid = read_pid(cfg)
    if pid and _alive(pid):
        print(f"daemon already running pid={pid}")
        return 0
    os.makedirs(queue_dir(cfg), exist_ok=True)
    with open(log_file(cfg), "ab") as log:
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "start", "--foreground"], cwd=ROOT,
                             stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             start_new_session=True, close_fds=True)
    time.sleep(1.5)
    if p.poll() is not None:
        print(f"daemon exited immediately with {p.returncode}; see {log_file(cfg)}")
        return 1
    print(f"daemon launched pid={p.pid} log={log_file(cfg)}")
    return 0


def stop(cfg):
    pid = read_pid(cfg)
    if not pid or not _alive(pid):
        print("daemon not running")
        return 0
    os.kill(pid, signal.SIGTERM)
    for _ in range(100):
        if not _alive(pid):
            print(f"daemon pid={pid} stopped")
            return 0
        time.sleep(0.1)
    print(f"daemon pid={pid} did not exit within 10 s")
    return 1


def status(cfg):
    pid = read_pid(cfg)
    print(f"daemon: {'running pid=%d' % pid if pid and _alive(pid) else 'not running'}")
    q = Queue(cfg, db.connect(cfg=cfg), os.path.join(queue_dir(cfg), "logs"), env={})
    for pool, s in q.stats().items():
        print(f"  {pool:6s} cap={s['cap']:3d} running={s['running']:3d} waiting={s['waiting']:4d} done={s['done']:5d} "
              f"failed={s['failed']:4d} backoff={s['backoff_remaining_sec']:.0f}s (level {s['backoff_level']})")
    return 0


def tick(cfg):
    q = Queue(cfg, db.connect(cfg=cfg), os.path.join(queue_dir(cfg), "logs"), env=build_env(cfg), python=sys.executable)
    q.tick()
    return status(cfg)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["start", "stop", "status", "tick"])
    ap.add_argument("--foreground", action="store_true", help="(internal) run the loop in this process")
    a = ap.parse_args(argv)
    cfg = C.load()
    return {"start": lambda: start(cfg, a.foreground), "stop": lambda: stop(cfg),
            "status": lambda: status(cfg), "tick": lambda: tick(cfg)}[a.action]()


if __name__ == "__main__":
    sys.exit(main())
