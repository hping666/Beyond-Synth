#!/usr/bin/env python3
"""DECISION 2026-09-18 (d) F3: the completion alert of the hourly check. Computes the complete-design set (src.analysis.phase5
.completion_view), compares it with the last recorded one (reports/data/phase5_complete_designs.json) and, when it changed, prints
the "New complete designs since last render" line first, appends it to STATUS.md and records the new set. Exit 0 always.
    .venv/bin/python scripts/phase5_alerts.py [--dry-run]"""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
from src import config as C  # noqa: E402
from src.analysis import phase5 as P5  # noqa: E402
from src.db import core as db  # noqa: E402


def post_slack(cfg, text):
    """DECISION 2026-09-18 (e) item 4: post the alert line to the Slack incoming webhook whose URL sits in the environment variable named by
    config alerts.slack_webhook_env; the URL itself is never printed or written anywhere. -> a one-line status."""
    import json as _json
    import urllib.request
    name = ((cfg.get("alerts") or {}).get("slack_webhook_env") or "").strip()
    if not name:
        return "slack: no webhook variable configured (alerts.slack_webhook_env)"
    url = os.environ.get(name)
    if not url:
        return f"slack: variable {name} not set in this environment"
    try:
        req = urllib.request.Request(url, data=_json.dumps({"text": text}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return f"slack: posted (HTTP {resp.status})"
    except Exception as e:   # the alert must never fail the check; the URL is not part of the message
        return f"slack: post failed ({type(e).__name__})"


SLOT_STATE = os.path.join(ROOT, "results", "queue", "slot_guard_state.json")


BASELINE_WINDOW = ("2026-09-18T05:49", "2026-09-19T02:09")   # DECISION 2026-09-19 (k) item 2: each row's baseline for the relative revert


def slot_report(cfg, conn, write=True, restart=None):
    """DECISION 2026-09-19 (j) 1c / 1d and (k) 1–3: the hourly slot figures — runs generating / waiting / queued, the unverified-at-build
    fraction per lane, per arm-model row and per design (last hour), the estimated proof-queue wait per lane, the idle seat-minutes
    per lane in the last hour — and the relative revert rule: a row more than 20 points worse than its own baseline (05:49–02:09) for
    three consecutive hourly checks flips queue.count_waiting_runs to true and restarts the daemon. -> lines to print."""
    import json as _json
    from src.jobqueue.core import idle_seat_minutes, proof_wait_estimate, search_slot_state, unverified_at_build
    g = cfg["queue"].get("admission_guard") or {}
    thr = float(g.get("unverified_at_build_max", 0.35)); wmax = float(g.get("proof_wait_max_min", 60))
    slots = search_slot_state(conn, cfg)
    rows = unverified_at_build(conn, cfg, minutes=int(g.get("window_min", 60)), tier=g.get("tier", "medium"), by="row")
    lanes_f = unverified_at_build(conn, cfg, minutes=int(g.get("window_min", 60)), tier=g.get("tier", "medium"), by="lane")
    designs_f = unverified_at_build(conn, cfg, minutes=int(g.get("window_min", 60)), tier=g.get("tier", "medium"), by="design")
    waits = proof_wait_estimate(conn, cfg)
    idle = idle_seat_minutes(conn, cfg, hours=1.0)
    lines = [f"search slots: generating {slots['generating']} (max {cfg['queue'].get('generating_max')}), waiting for verdicts {slots['waiting']}, queued {slots['queued']}; counting waiting runs: {bool(cfg['queue'].get('count_waiting_runs'))}",
             "per lane (last hour): " + ", ".join(f"{n}: unverified-at-build {lanes_f[n]:.0%}" if n in lanes_f else f"{n}: no generation" for n in waits) ,
             "estimated proof-queue wait per lane (min): " + ", ".join(f"{n} {v['wait_min']:.0f} ({v['queued']} queued, {v['seats']} seats, {v['mean_min']:.0f} min mean){' PAUSED' if (v['wait_min'] > wmax or (lanes_f.get(n) or 0) > thr) else ''}" for n, v in waits.items()),
             "idle seat-minutes per lane (last hour): " + ", ".join(f"{n} {v['idle_min']:.0f} of {v['seats'] * 60}" if v["idle_min"] is not None else f"{n} occupied {v['occupied_min']:.0f} (leftover)" for n, v in idle.items()),
             "unverified-at-build per row: " + (", ".join(f"{k} {v:.0%}" for k, v in sorted(rows.items())) or "no generation built"),
             "unverified-at-build per design: " + (", ".join(f"{k.split('_')[-1]} {v:.0%}" for k, v in sorted(designs_f.items())) or "-")]
    try:
        st = _json.load(open(SLOT_STATE))
    except (OSError, ValueError):
        st = {"consecutive": {}, "reverted": False}
    if "baseline" not in st:
        st["baseline"] = unverified_at_build(conn, cfg, tier=g.get("tier", "medium"), by="row", since=BASELINE_WINDOW[0], until=BASELINE_WINDOW[1])
    base = st["baseline"]
    for k in set(rows) | set(st["consecutive"]):
        worse = k in rows and (rows[k] - float(base.get(k, rows[k]))) > 0.20
        st["consecutive"][k] = (st["consecutive"].get(k, 0) + 1) if worse else 0
    over = [k for k, n in st["consecutive"].items() if n >= 3]
    lines.append("baseline (05:49–02:09) per row: " + ", ".join(f"{k} {v:.0%}" for k, v in sorted(base.items())))
    if over and not cfg["queue"].get("count_waiting_runs") and write:
        path = os.path.join(ROOT, "config", "experiments.yaml")
        text = open(path).read().replace("  count_waiting_runs: false", "  count_waiting_runs: true", 1)
        open(path, "w").write(text)
        st["reverted"] = True
        lines.append(f"REVERT (k 2): rows more than 20 points worse than their baseline for three consecutive checks: {', '.join(over)} -> queue.count_waiting_runs set to true" + (", daemon restarted" if restart and restart() else ", restart the daemon"))
    if write:
        st["at"] = __import__("datetime").datetime.now().isoformat(timespec="minutes")
        _json.dump(st, open(SLOT_STATE, "w"), indent=1)
    lines.append("consecutive hourly checks more than 20 points worse than the baseline: " + (", ".join(f"{k} {n}" for k, n in sorted(st["consecutive"].items()) if n) or "none"))
    try:
        pool_lines = [l for l in open(os.path.join(ROOT, "results", "queue", "offline_pool.log")).read().splitlines() if "compress_logs" in l or "pass:" in l]
        lines.append("offline pool: " + (pool_lines[-1][:150] if pool_lines else "no log line"))
        comp = [l for l in pool_lines if "compress_logs" in l]
        if comp:
            lines.append("last compression: " + comp[-1][:150])
    except OSError:
        pass
    return lines


def restart_daemon():
    import subprocess, time
    d = os.path.join(ROOT, "scripts", "queue", "daemon.py")
    subprocess.run([sys.executable, d, "stop"], check=False, capture_output=True); time.sleep(4)
    subprocess.Popen(["setsid", sys.executable, d, "start"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return True


def main(argv=None):
    dry = "--dry-run" in (argv or sys.argv[1:])
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    if "--slots" in (argv or sys.argv[1:]):
        for l in slot_report(cfg, conn, write=not dry, restart=None if dry else restart_daemon):
            print(l)
        return 0
    new, line, view = P5.completion_alert(cfg, conn, write=not dry)
    r = view["reachability"]
    if line:
        print(line)
        if not dry:
            print(post_slack(cfg, line))
    else:
        print(f"No new complete design ({len(view['complete'])} complete: " + (", ".join(view["complete"]) or "none") + f"; tally {r['wins']} wins, {r['lost']} lost, {r['undecided']} undecided; {r['wins_still_needed']} wins still needed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
