"""Queue runner for LLM batch tasks (kind `llm`, local pool):  python -m src.search.run_llm --job <job_id>
Payload: {task, ...}. Tasks: `m6_review` (src/classify/review.py: {exp, limit}). The daemon supplies the API key
(it sources the secrets file itself); every call goes through the LLM client and its budget ledger. Exit 0 when the
task finished, 1 on an error."""
import argparse
import json
import sys
import traceback

from src import config as C
from src.db import core as db

TASKS = {}


def _m6_review(cfg, conn, p):
    from src.classify.review import run_review
    return run_review(cfg, conn, p.get("exp", "phase3"), p.get("limit"), log=print, shard=p.get("shard"), shards=p.get("shards"))


TASKS["m6_review"] = _m6_review


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    job = conn.execute("SELECT * FROM jobs WHERE job_id=?", (a.job,)).fetchone()
    p = json.loads(job["payload_json"])
    task = p.get("task")
    if task not in TASKS:
        print(json.dumps({"job": a.job, "status": "failed", "error": f"unknown llm task {task!r}"}))
        return 1
    try:
        out = TASKS[task](cfg, conn, p)
        print(json.dumps({"job": a.job, "task": task, "status": "done", "result": out}, default=str))
        return 0
    except Exception as e:
        traceback.print_exc()
        print(json.dumps({"job": a.job, "task": task, "status": "failed", "error": f"{type(e).__name__}: {e}"[:300]}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
