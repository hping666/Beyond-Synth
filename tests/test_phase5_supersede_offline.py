"""DECISION 2026-09-18 (d) D1: scripts/phase5_supersede.py keeps the old run (status superseded, reason, the new run id), creates
the repeat with the same arm / model / design / seed and submits its search job (held when asked); a run already superseded is
skipped; queued jobs of the old run are withdrawn. Both directions."""
import copy
import importlib.util
import json
import os
from pathlib import Path

from src import config as C
from src.db import core as db
from src.jobqueue.core import Queue


def load_mod():
    spec = importlib.util.spec_from_file_location("phase5_supersede", str(Path(C.ROOT) / "scripts" / "phase5_supersede.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_supersede_and_repeat(tmp_path, monkeypatch):
    mod = load_mod()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('drrtl_LSTM','drrtl','LSTM','p',1,1,'held',1.0,'t','g','c')")
    db.insert(conn, "evaluations", {"design_id": "drrtl_LSTM", "is_baseline": 1, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 100.0, "cells": 120, "wns_ns": 0.05, "tns_ns": 0.0, "power_saif_mw": 1.0, "dc_seconds": 60, "status": "ok", "raw_dir": "/x/base", "hist_json": json.dumps({"NAND2_X1": 100})})
    for metric, td in (("area", 0.01), ("wns", 0.005), ("power_saif", 0.02)):
        db.insert(conn, "noise_floor", {"design_id": "drrtl_LSTM", "config": "E4", "metric": metric, "sigma_robust": 0.002, "t_d": td, "floor_class": "quiet", "floor_source": "measured", "floor_version": cfg["noise"].get("floor_version"), "n": 8})
    db.insert(conn, "runs", {"run_id": "r_old", "exp": "phase5", "arm": "B2", "design_id": "drrtl_LSTM", "seed": 2, "llm_model": "gpt-5.6-terra", "status": "done", "started_at": "t", "llm_calls": 60})
    old_job = q.submit("search", {"run_id": "r_old"}, design_id="drrtl_LSTM", config="search", priority=3)
    res = mod.supersede(cfg, conn, ["r_old"], "harness_fix", 8600, hold="after C3", queue=q)
    assert len(res) == 1 and res[0][0] == "r_old" and res[0][1] and res[0][2]
    old = dict(conn.execute("SELECT * FROM runs WHERE run_id='r_old'").fetchone())
    assert old["status"] == "superseded" and old["superseded_reason"] == "harness_fix" and old["superseded_by"] == res[0][1] and old["excluded_from_tables"] == 1
    new = dict(conn.execute("SELECT * FROM runs WHERE run_id=?", (res[0][1],)).fetchone())
    assert (new["arm"], new["design_id"], new["seed"], new["llm_model"], new["status"]) == ("B2", "drrtl_LSTM", 2, "gpt-5.6-terra", "created")
    job = dict(conn.execute("SELECT * FROM jobs WHERE job_id=?", (res[0][2],)).fetchone())
    p = json.loads(job["payload_json"])
    assert job["kind"] == "search" and job["state"] == "queued" and job["priority"] == 8600 and p["run_id"] == res[0][1] and p["repeat_of"] == "r_old" and p["hold"] == "after C3"   # the repeat itself stays queued (2026-09-18 10:5x: a first version withdrew it with the old run's jobs)
    assert conn.execute("SELECT state FROM jobs WHERE job_id=?", (old_job,)).fetchone()[0] == "failed"         # the old run's queued job is withdrawn
    # the other direction: an already superseded run is skipped, nothing new is created
    n_runs = conn.execute("SELECT count(*) FROM runs").fetchone()[0]
    assert mod.supersede(cfg, conn, ["r_old"], "harness_fix", 8600, queue=q) == [] and conn.execute("SELECT count(*) FROM runs").fetchone()[0] == n_runs
    # dry run: nothing changes
    db.insert(conn, "runs", {"run_id": "r_two", "exp": "phase5", "arm": "M", "design_id": "drrtl_LSTM", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "running", "started_at": "t", "llm_calls": 7})
    assert mod.supersede(cfg, conn, ["r_two"], "harness_fix", 8600, queue=q, dry_run=True) == [("r_two", None, None)]
    assert conn.execute("SELECT status FROM runs WHERE run_id='r_two'").fetchone()[0] == "running"
