#!/usr/bin/env python3
"""Phase 5 certification loop (spec 06 §2; decision 2026-09-15 item 2): every `--interval` minutes register the hidden-layer
jobs of the Phase 5 candidates through scripts/hidden_worker.py --submit-candidates --exp phase5 (H1 / H3 / H5 for every
E4-evaluated candidate, H2a / H2b / H4 for accepted candidates and the audit sample, per config exp5.hidden_scope) and of the
probe's candidates (exp phase5_probe; decision 2026-09-15 evening, item 4). Detached from
the session (setsid), a pid file under results/queue/, a log next to it; idempotent submissions (missing records only).
    .venv/bin/python scripts/hidden_loop.py start [--interval 30] [--exp phase5]
    .venv/bin/python scripts/hidden_loop.py stop | status | once
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

PID = os.path.join(ROOT, "results", "queue", "hidden_loop.pid")
LOG = os.path.join(ROOT, "results", "queue", "hidden_loop.log")


def once(exps, priority=1):
    """One registration pass per experiment (decision 2026-09-15 evening, item 4: the probe's candidates as well as Phase 5's)."""
    rc_all, out_all = 0, []
    for exp in ([exps] if isinstance(exps, str) else exps):
        cmd = [sys.executable, os.path.join(ROOT, "scripts", "hidden_worker.py"), "--submit-candidates", "--exp", exp, "--priority", str(priority)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        rc_all = rc_all or r.returncode
        out_all.append(f"[{exp}] " + (r.stdout + r.stderr).strip())
    return rc_all, "\n".join(out_all)


def loop(exp, interval_min):
    with open(PID, "w") as f:
        f.write(str(os.getpid()))
    stop = {"flag": False}

    def on_signal(signum, frame):
        stop["flag"] = True
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    with open(LOG, "a") as log:
        log.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} hidden loop started pid {os.getpid()} exp {exp if isinstance(exp, str) else ' '.join(exp)} interval {interval_min} min\n")
        log.flush()
        while not stop["flag"]:
            rc, out = once(exp)
            log.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} rc={rc} {out[-400:]}\n")
            log.flush()
            for _ in range(int(interval_min * 60)):
                if stop["flag"]:
                    break
                time.sleep(1)
        log.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} hidden loop stopped\n")
    try:
        os.remove(PID)
    except OSError:
        pass


def running():
    if not os.path.exists(PID):
        return None
    try:
        pid = int(open(PID).read().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["start", "stop", "status", "once", "_run"])
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--exp", nargs="*", default=["phase5", "phase5_probe"], help="experiments to register (decision 2026-09-15 evening, item 4: Phase 5 and the probe)")
    a = ap.parse_args(argv)
    C.load()
    if a.what == "once":
        rc, out = once(a.exp)
        print(out)
        return rc
    if a.what == "_run":
        loop(a.exp, a.interval)
        return 0
    if a.what == "status":
        pid = running()
        print(f"hidden loop: {'running pid ' + str(pid) if pid else 'not running'} (log {LOG})")
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
    subprocess.Popen(["setsid", sys.executable, os.path.abspath(__file__), "_run", "--interval", str(a.interval), "--exp", *a.exp],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(1)
    print(f"hidden loop started ({'pid ' + str(running()) if running() else 'pid file not yet written'}); log {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
