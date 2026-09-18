#!/usr/bin/env python3
"""LLM call health over the last N minutes (user decision 2026-09-18: the global concurrency cap is tuned on this): calls,
their durations, the wait for a global slot (recorded per call since 03:58 on 2026-09-18), retries (transient errors, 429s)
and failed calls.    .venv/bin/python scripts/llm_health.py [--minutes 60]"""
import argparse
import datetime
import json
import os
import statistics
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
from src import config as C  # noqa: E402


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, int(p * len(xs)) - 1))] if xs else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--minutes", type=float, default=60)
    a = ap.parse_args(argv)
    cfg = C.load()
    since = (datetime.datetime.now() - datetime.timedelta(minutes=a.minutes)).isoformat(timespec="seconds")
    root = os.path.join(C.results_dir(cfg), "llm")
    secs, waits, attempts, errors, retried, r429 = [], [], [], 0, 0, 0
    n = 0
    for rid in os.listdir(root):
        d = os.path.join(root, rid)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.startswith("c") or not f.endswith(".json"):
                continue
            path = os.path.join(d, f)
            try:
                if datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds") < since:
                    continue
                rec = json.load(open(path))
            except (OSError, ValueError):
                continue
            if rec.get("error") and not rec.get("at"):
                errors += 1
                r429 += int("429" in str(rec.get("error")))
                continue
            if str(rec.get("at", "")) < since:
                continue
            n += 1
            secs.append(float(rec.get("seconds") or 0))
            if rec.get("slot_wait_s") is not None:
                waits.append(float(rec["slot_wait_s"]))
            if rec.get("attempts"):
                attempts.append(int(rec["attempts"]))
            if rec.get("last_error"):
                retried += 1
                r429 += int("429" in str(rec["last_error"]))
    cap = (cfg["llm"].get("parallel") or {}).get("global_max")
    print(f"last {a.minutes:.0f} min: {n} calls ({n / max(a.minutes, 1) * 60:.0f} per hour), cap {cap}")
    if secs:
        print(f"  call time incl. any wait: median {statistics.median(secs) / 60:.1f} min, p90 {q(secs, 0.9) / 60:.1f} min")
    if waits:
        print(f"  slot wait ({len(waits)} calls with the field): median {statistics.median(waits) / 60:.2f} min, p90 {q(waits, 0.9) / 60:.2f} min, max {max(waits) / 60:.1f} min, share waiting > 10 s: {100 * sum(1 for w in waits if w > 10) / len(waits):.0f} %")
        net = [s - w for s, w in zip(secs[-len(waits):], waits)]
        print(f"  request time without the wait: median {statistics.median(net) / 60:.1f} min, p90 {q(net, 0.9) / 60:.1f} min")
    else:
        print("  slot wait: no call carries the field yet (recorded from 2026-09-18 03:58)")
    print(f"  retried calls (a transient error before success): {retried}, of which 429: {r429}; failed calls (no answer after the retries): {errors}"
          + (f"; attempts per call: mean {statistics.mean(attempts):.2f}, max {max(attempts)}" if attempts else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
