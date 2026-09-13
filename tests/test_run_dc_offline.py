"""The queue runner for DC jobs (src/eval/run_dc.py) takes the configuration from the payload, or from the job
row's selector column when the payload lacks it (regression: the first Phase 1 trial jobs failed with KeyError)."""
import json

from src import config as C
from src.db import core as db
from src.eval import run_dc as R
from src.jobqueue.core import Queue


def test_runner_reads_config_from_payload_or_job_row(tmp_path, monkeypatch):
    cfg = C.load()
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={}, log=lambda m: None)
    seen = []

    def fake_evaluate(cfg_, conn_, design_id, rtl, top, config, **kw):
        seen.append((design_id, config, kw.get("clk_port"), kw.get("is_baseline")))
        return {"design_id": design_id, "config": config, "status": "ok", "error": None, "raw_dir": str(tmp_path), "dc_seconds": 1, "cached": False, "eval_id": 1}

    monkeypatch.setattr(R, "evaluate", fake_evaluate)
    monkeypatch.setattr(R.db, "connect", lambda cfg=None: conn)
    j1 = q.submit("dc", {"design_id": "d1", "rtl": ["x.v"], "top": "t", "config": "E4", "clock_ns": 4.0, "clk_port": None, "is_baseline": 1}, design_id="d1", config="E4")
    j2 = q.submit("dc", {"design_id": "d2", "rtl": ["x.v"], "top": "t", "clock_ns": 4.0, "clk_port": "a b"}, design_id="d2", config="K_asap7")
    assert R.main(["--job", j1]) == 0 and R.main(["--job", j2]) == 0
    assert seen == [("d1", "E4", None, 1), ("d2", "K_asap7", "a b", 0)]
    assert R.main(["--job", "jnope"]) == 1
    assert json.loads(conn.execute("SELECT payload_json FROM jobs WHERE job_id=?", (j1,)).fetchone()[0])["config"] == "E4"


def test_runner_timeout_keeps_a_margin_below_the_queue_timeout():
    assert R.runner_timeout({"timeout_sec": 1000.0}) == 850.0 and R.runner_timeout({"timeout_sec": None}) is None
    from src.equiv import run_equiv as RE
    assert RE.runner_timeout({"timeout_sec": 1800.0}) == 1530.0
