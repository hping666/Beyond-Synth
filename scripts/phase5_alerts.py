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


def main(argv=None):
    dry = "--dry-run" in (argv or sys.argv[1:])
    cfg = C.load()
    conn = db.connect(cfg=cfg)
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
