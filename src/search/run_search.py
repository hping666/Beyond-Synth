"""Queue runner for one residual-guided evolution run:  python -m src.search.run_search --job <job_id>
Payload: {run_id}. The run resumes from its state file and the database (spec 05 §7), polls the queue for verdicts and
returns when every generation is built and every verdict has arrived. Exit 0 when the run finished, 1 on an error."""
import argparse
import json
import sys
import traceback

from src import config as C
from src.db import core as db
from src.search.driver import SearchRun


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
        return 0 if status == "done" else 1
    except Exception as e:
        traceback.print_exc()
        conn.execute("UPDATE runs SET status='failed' WHERE run_id=?", (p["run_id"],))
        print(json.dumps({"run_id": p["run_id"], "status": "failed", "error": f"{type(e).__name__}: {e}"[:300]}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
