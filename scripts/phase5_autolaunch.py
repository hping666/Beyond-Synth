#!/usr/bin/env python3
"""Detached watcher for the pre-authorised Phase 5 launch (decision 2026-09-15 item 6): every `--interval` minutes check the
probe; when every probe run has finished, write the probe report (reports/data/phase5_probe_report.md), run
`phase5_main.py launch` (which writes reports/data/phase5_prelaunch.md and launches only on GO), start the hidden-layer
loop on GO, and exit. On NO-GO it records the reason and exits without launching (the user decides). Log under
results/queue/phase5_autolaunch.log; pid file next to it.
    .venv/bin/python scripts/phase5_autolaunch.py start [--interval 10] | stop | status | once
"""
import os
import signal
import subprocess
import sys
import time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
import argparse  # noqa: E402
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402

PID = os.path.join(ROOT, "results", "queue", "phase5_autolaunch.pid")
LOG = os.path.join(ROOT, "results", "queue", "phase5_autolaunch.log")
PY = sys.executable


def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n")


def probe_finished(conn):
    rows = conn.execute("SELECT status FROM runs WHERE exp='phase5_probe' AND status != 'superseded'").fetchall()
    return bool(rows) and all(r[0] in ("done", "failed") for r in rows), len(rows)


def once():
    """One check: -> 'waiting' | 'launched' | 'no-go' | 'launched-before'."""
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    if conn.execute("SELECT COUNT(*) FROM runs WHERE exp='phase5' AND status != 'superseded'").fetchone()[0]:
        return "launched-before"
    fin, n = probe_finished(conn)
    if not fin:
        return "waiting"
    rep = subprocess.run([PY, os.path.join(ROOT, "scripts", "phase5_probe.py"), "status"], capture_output=True, text=True)
    os.makedirs(os.path.join(ROOT, "reports", "data"), exist_ok=True)
    with open(os.path.join(ROOT, "reports", "data", "phase5_probe_report.md"), "w") as f:
        f.write(f"# Probe report ({time.strftime('%Y-%m-%d %H:%M')}; decision 2026-09-15 item 5)\n\n```text\n{rep.stdout}\n```\n")
    log("probe finished; report written; running phase5_main.py launch")
    r = subprocess.run([PY, os.path.join(ROOT, "scripts", "phase5_main.py"), "launch"], capture_output=True, text=True)
    log(f"launch rc={r.returncode}: {(r.stdout + r.stderr)[-1500:]}")
    if r.returncode == 0:
        h = subprocess.run([PY, os.path.join(ROOT, "scripts", "hidden_loop.py"), "start", "--exp", "phase5"], capture_output=True, text=True)
        log(f"hidden loop: {(h.stdout + h.stderr).strip()[-300:]}")
        return "launched"
    return "no-go"


def loop(interval_min):
    with open(PID, "w") as f:
        f.write(str(os.getpid()))
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda s, fr: stop.__setitem__("flag", True))
    log(f"autolaunch watcher started pid {os.getpid()} interval {interval_min} min")
    while not stop["flag"]:
        try:
            state = once()
        except Exception as e:   # a transient database error must not end the watch
            log(f"check failed: {type(e).__name__}: {e}")
            state = "waiting"
        log(f"state {state}")
        if state != "waiting":
            break
        for _ in range(int(interval_min * 60)):
            if stop["flag"]:
                break
            time.sleep(1)
    log("autolaunch watcher stopped")
    try:
        os.remove(PID)
    except OSError:
        pass


def running():
    try:
        pid = int(open(PID).read().strip())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["start", "stop", "status", "once", "_run"])
    ap.add_argument("--interval", type=int, default=10)
    a = ap.parse_args(argv)
    if a.what == "once":
        print(once())
        return 0
    if a.what == "_run":
        loop(a.interval)
        return 0
    if a.what == "status":
        pid = running()
        print(f"autolaunch watcher: {'running pid ' + str(pid) if pid else 'not running'} (log {LOG})")
        if os.path.exists(LOG):
            print(open(LOG).read()[-600:])
        return 0
    if a.what == "stop":
        pid = running()
        if pid:
            os.kill(pid, signal.SIGTERM)
            print(f"stop signal sent to pid {pid}")
        else:
            print("not running")
        return 0
    if running():
        print(f"already running pid {running()}")
        return 0
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    subprocess.Popen(["setsid", PY, os.path.abspath(__file__), "_run", "--interval", str(a.interval)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(1)
    print(f"autolaunch watcher started ({'pid ' + str(running()) if running() else 'starting'}); log {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
