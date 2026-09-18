#!/usr/bin/env python3
"""DECISION 2026-09-18 (d) D1: supersede runs and repeat them. Each named run is kept (status `superseded`, `superseded_reason`,
`superseded_by` = the new run), and a new run with the same arm / model / design / seed is created and submitted as a search job
(priority as given; `--hold REASON` keeps the new job from starting until the flag is removed). Records are never deleted.
    .venv/bin/python scripts/phase5_supersede.py --reason harness_fix --priority 8600 [--hold "..."] [--dry-run] RUN_ID [RUN_ID ...]
    .venv/bin/python scripts/phase5_supersede.py --reason harness_fix --design drrtl_LSTM --status done ...   (select by design and status)"""
import argparse
import json
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402


def supersede(cfg, conn, run_ids, reason, priority, hold=None, queue=None, dry_run=False, exp="phase5"):
    """-> [(old run id, new run id, job id)] — the old run superseded (a running one: its driver stops at its next step), the new one created and submitted."""
    from src.jobqueue.core import Queue
    from src.search.driver import SearchRun
    q = queue or Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    K, N = int(cfg["scale"]["K"]), int(cfg["scale"]["N"])
    out = []
    for rid in run_ids:
        r = conn.execute("SELECT * FROM runs WHERE run_id=?", (rid,)).fetchone()
        if r is None:
            raise SystemExit(f"unknown run {rid}")
        if r["status"] == "superseded":
            print(f"{rid}: already superseded ({r['superseded_reason']}) -> skipped"); continue
        if dry_run:
            out.append((rid, None, None)); print(f"{rid}: would supersede ({r['arm']} / {r['llm_model']} / {r['design_id']} / seed {r['seed']}, status {r['status']}, {r['llm_calls']} calls)"); continue
        run = SearchRun.create(cfg, conn, exp=r["exp"], arm=r["arm"], design_id=r["design_id"], seed=int(r["seed"]), model=r["llm_model"], K=K, N=N, queue=q,
                               note=f"repeat of {rid} ({reason}, DECISION 2026-09-18 (d) D1)")
        conn.execute("UPDATE runs SET status='superseded', superseded_reason=?, superseded_by=?, excluded_from_tables=1 WHERE run_id=?", (reason, run.run_id, rid))
        payload = {"run_id": run.run_id, "repeat_of": rid, "reason": reason}
        if hold:
            payload["hold"] = hold
        jid = q.submit("search", payload, design_id=r["design_id"], config="search", priority=int(priority), timeout_sec=48 * 3600)
        for j in conn.execute("SELECT job_id FROM jobs WHERE kind='search' AND state IN ('queued','backoff') AND job_id != ? AND payload_json LIKE ?", (jid, f'%"run_id": "{rid}"%')).fetchall():   # the old run's own jobs only (the repeat names it under repeat_of)
            conn.execute("UPDATE jobs SET state='failed', error=? , finished_at=? WHERE job_id=? AND state IN ('queued','backoff')", (f"not run: run superseded ({reason})", db.now(), j[0]))
        conn.commit()
        out.append((rid, run.run_id, jid))
        print(f"{rid} -> {run.run_id} (job {jid}, priority {priority}{', held' if hold else ''})")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--reason", required=True)
    ap.add_argument("--priority", type=int, default=8600)
    ap.add_argument("--hold", default=None)
    ap.add_argument("--design", default=None)
    ap.add_argument("--status", default=None, help="with --design: select the design's runs in this status (e.g. done)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    ids = list(a.runs)
    if a.design:
        qy = "SELECT run_id FROM runs WHERE exp='phase5' AND design_id=? AND status!='superseded'" + (" AND status=?" if a.status else "") + " ORDER BY run_id"
        ids += [r[0] for r in conn.execute(qy, (a.design, a.status) if a.status else (a.design,))]
    if not ids:
        print("no runs selected"); return 1
    res = supersede(cfg, conn, ids, a.reason, a.priority, hold=a.hold, dry_run=a.dry_run)
    print(json.dumps({"superseded": len([x for x in res if x[1]]), "reason": a.reason, "dry_run": a.dry_run}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
