#!/usr/bin/env python3
"""Host load log (DECISION 2026-09-18 item 5c: per-row median host load during the runs needs a record; the host has no sysstat):
one line per minute — ISO time, 1 / 5 / 15-minute load, running search / dc / vcf / pt jobs — appended to results/queue/load.log.
    .venv/bin/python scripts/load_logger.py start | stop | status"""
import os
import signal
import sys
import time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
PID = os.path.join(ROOT, "results", "queue", "load_logger.pid")
LOG = os.path.join(ROOT, "results", "queue", "load.log")


def running():
    try:
        pid = int(open(PID).read().strip()); os.kill(pid, 0); return pid
    except (OSError, ValueError):
        return None


def loop():
    from src import config as C
    from src.db import core as db
    with open(PID, "w") as f:
        f.write(str(os.getpid()))
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda s, f: stop.__setitem__("flag", True))
    conn = db.connect(cfg=C.load())
    while not stop["flag"]:
        try:
            l1, l5, l15 = open("/proc/loadavg").read().split()[:3]
            n = {p: c for p, c in conn.execute("SELECT pool, COUNT(*) FROM jobs WHERE state='running' GROUP BY pool")}
            with open(LOG, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {l1} {l5} {l15} search={n.get('search', 0)} dc={n.get('dc', 0)} vcf={n.get('vcf', 0)} pt={n.get('pt', 0)} local={n.get('local', 0)}\n")
        except Exception as e:   # the log must go on
            with open(LOG, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} error {type(e).__name__}: {e}\n")
        for _ in range(60):
            if stop["flag"]:
                break
            time.sleep(1)
    try:
        os.remove(PID)
    except OSError:
        pass


def main(argv=None):
    what = (argv or sys.argv[1:] or ["status"])[0]
    if what == "_run":
        loop(); return 0
    if what == "start":
        if running():
            print(f"load logger already running pid {running()}"); return 0
        import subprocess
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "_run"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
        time.sleep(1); print(f"load logger started pid {p.pid}; log {LOG}"); return 0
    if what == "stop":
        pid = running()
        if pid: os.kill(pid, signal.SIGTERM); print(f"stop sent to {pid}")
        else: print("not running")
        return 0
    print(f"load logger: {'running pid %d' % running() if running() else 'not running'} (log {LOG})"); return 0


if __name__ == "__main__":
    sys.exit(main())
