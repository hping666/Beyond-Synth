"""Queue runner for one residual-guided evolution run:  python -m src.search.run_search --job <job_id>
Payload: {run_id}. The run resumes from its state file and the database (spec 05 §7), polls the queue for verdicts and
returns when every generation is built and every verdict has arrived. Exit 0 when the run finished, 1 on an error, 76 after a
code roll (SIGUSR1: the state is saved and the queue restarts the run under the new code without an attempt), 75 when
the API account has no credits (2026-09-16): the run keeps its state with status paused_quota and the queue's backoff retries
it later, so it resumes by itself once the account is topped up."""
import argparse
import json
import sys
import traceback

from src import config as C
from src.db import core as db
from src.search.driver import SearchRun
from src.search.llm import QuotaExhausted

EX_TEMPFAIL = 75
EX_RESTART = 76   # the run left for a code roll (SIGUSR1): the queue requeues it as a resumption without an attempt (2026-09-16)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    job = conn.execute("SELECT * FROM jobs WHERE job_id=?", (a.job,)).fetchone()
    p = json.loads(job["payload_json"])
    try:
        run = SearchRun.resume(cfg, conn, p["run_id"])
        status = run.run()
        print(json.dumps({"run_id": p["run_id"], "status": status, "gens": run.state["gen"], "calls": run.state["calls"], "retained": run.state["retained"]}))
        if status == "rolled":
            return EX_RESTART
        return 0 if status == "done" else 1
    except QuotaExhausted as e:
        conn.execute("UPDATE runs SET status='paused_quota' WHERE run_id=?", (p["run_id"],))
        print(json.dumps({"run_id": p["run_id"], "status": "paused_quota", "error": f"{type(e).__name__}: {e}"[:300]}))
        return EX_TEMPFAIL
    except Exception as e:
        traceback.print_exc()
        conn.execute("UPDATE runs SET status='failed' WHERE run_id=?", (p["run_id"],))
        print(json.dumps({"run_id": p["run_id"], "status": "failed", "error": f"{type(e).__name__}: {e}"[:300]}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
