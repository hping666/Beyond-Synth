"""Bidirectional tests of the hidden worker (scripts/hidden_worker.py, CLAUDE.md rule 3): the dc_hidden runner
records through the hidden database and looks up netlist sources in the visible one; a visible configuration is
refused; noise jobs carry the knee periods and the proven perturbations; the hidden noise floor is written into
the hidden database only. The DC evaluation is replaced by a fake."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

from src import config as C
from src.db import core as db
from src.eval import service as SV
from src.jobqueue.core import POOL_OF_KIND, RUNNER_OF_KIND, Queue


def load_worker():
    spec = importlib.util.spec_from_file_location("hidden_worker", str(Path(C.ROOT) / "scripts" / "hidden_worker.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def env(tmp_path):
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    vis = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    mod = load_worker()
    hid = db.connect(path=mod.hidden_db_path(cfg))
    rtl = tmp_path / "d.v"
    rtl.write_text("module d(input clk, output y); assign y = clk; endmodule\n")
    return cfg, vis, hid, mod, rtl


def test_queue_kind_and_command(tmp_path):
    assert POOL_OF_KIND["dc_hidden"] == "dc" and RUNNER_OF_KIND["dc_hidden"] == "scripts.hidden_worker"
    cfg = C.load()
    q = Queue(cfg, db.connect(path=str(tmp_path / "q.sqlite")), str(tmp_path / "logs"), env={}, log=lambda m: None)
    cmd = q._command_for({"kind": "dc_hidden", "job_id": "j1"}, {})
    assert "-m scripts.hidden_worker --job j1" in cmd and q.default_timeout("dc_hidden") == q.default_timeout("dc")


def test_runner_records_hidden_and_refuses_visible(env, monkeypatch):
    cfg, vis, hid, mod, rtl = env
    q = Queue(cfg, vis, str(Path(cfg["project"]["results_dir"]) / "logs"), env={}, log=lambda m: None)
    seen = {}

    def fake_evaluate(cfg_, conn, design_id, rtl_files, top, config, **kw):
        seen.update(conn=conn, config=config, source=kw.get("source_conn"), pert=kw.get("pert_id"), design=kw.get("design"))
        return {"design_id": design_id, "config": config, "status": "ok", "raw_dir": str(Path(cfg_["project"]["results_dir"]) / "hidden" / "raw" / "x"), "dc_seconds": 1, "cached": False}

    payload = {"design_id": "d1", "rtl": [str(rtl)], "top": "d", "config": "H1", "clk_port": "clk", "is_baseline": 0, "pert_id": "p1",
               "design": {"phi_main_ns_nangate45": 2.0}}
    jid = q.submit("dc_hidden", payload, design_id="d1", config="H1")
    monkeypatch.setattr(mod, "evaluate", fake_evaluate)
    assert mod.run_job(cfg, jid, vis=vis, hid=hid) == 0
    assert SV.db_is_hidden(seen["conn"]) and not SV.db_is_hidden(seen["source"]) and seen["config"] == "H1" and seen["pert"] == "p1"
    monkeypatch.setattr(mod, "evaluate", SV.evaluate)  # the real service refuses a visible configuration on the hidden DB
    jid2 = q.submit("dc_hidden", dict(payload, config="E4", clock_ns=2.0), design_id="d1", config="E4")
    assert mod.run_job(cfg, jid2, vis=vis, hid=hid) == 1
    assert vis.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0] == 0 and hid.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0] == 0
    assert mod.run_job(cfg, "jnope", vis=vis, hid=hid) == 1


def test_noise_jobs_and_hidden_floor(env, tmp_path, monkeypatch):
    cfg, vis, hid, mod, rtl = env
    from src.designs import catalog as K
    monkeypatch.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    ddir = tmp_path / "designs" / "rtllm" / "acc"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "acc.v").write_text(rtl.read_text())
    d = {"design_id": "rtllm_acc", "suite": "rtllm", "name": "acc", "top": "d", "files": ["rtl/acc.v"], "clk_ports": ["clk"], "rst_port": None,
         "rst_sense": None, "sverilog": False, "incdirs": [], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/acc.v": K.sha256_of(ddir / "rtl" / "acc.v")}, "loc": 1, "tags": ["rtllm"], "notes": [], "_dir": str(ddir)}
    K.write_design(d)
    vis.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, phi_main_ns_asap7, phi_main_ns_sky130hd, created_at, git_sha, cfg_hash) "
                "VALUES ('rtllm_acc','rtllm','acc','x',1,1,'dev',2.0,0.5,NULL,'t','g','c')")
    for pid, ptype, status in (("p1", "P1_rename", "proven"), ("p2", "P1_rename", "proven"), ("p3", "P2_reorder", "proven"), ("p4", "P3_expr", "falsified")):
        (ddir / f"{pid}.v").write_text("module d(input clk, output y); assign y = clk; endmodule\n")
        vis.execute("INSERT INTO perturbations (pert_id, design_id, ptype, path, seq_status, created_at, git_sha, cfg_hash) VALUES (?,?,?,?,?,?,?,?)",
                    (pid, "rtllm_acc", ptype, str((ddir / f"{pid}.v").relative_to(C.ROOT)) if str(ddir).startswith(C.ROOT) else str(ddir / f"{pid}.v"), status, "t", "g", "c"))
    jobs = mod.noise_jobs(cfg, vis)
    by_cfg = {}
    for j in jobs:
        by_cfg.setdefault(j["config"], []).append(j)
    assert set(by_cfg) == {"H1", "H2a", "H5", "H3"}  # no sky130 knee -> no H2b; H3 from configs_light
    assert len(by_cfg["H1"]) == 4 and len(by_cfg["H5"]) == 4  # D + 3 proven perturbations, never the falsified one
    assert len(by_cfg["H3"]) == 3  # D + one perturbation per type (P1, P2)
    assert all(j["kind"] == "dc_hidden" and j["payload"]["design"]["phi_main_ns_asap7"] == 0.5 for j in jobs)
    assert [j["payload"]["is_baseline"] for j in by_cfg["H1"]] == [1, 0, 0, 0] and by_cfg["H2a"][0]["payload"]["clock_ns"] == 0.5
    # hidden floor: baseline + perturbation rows in the hidden DB only
    def ev(pert, area):
        row = {"design_id": "rtllm_acc", "pert_id": pert, "is_baseline": int(pert is None), "config": "H1", "lib": "nangate45", "clock_ns": 0.1,
               "area_um2": area, "cells": 10, "wns_ns": 0.0, "tns_ns": 0.0, "status": "ok", "raw_dir": f"/x/{pert}", "hist_json": "{}"}
        db.insert(hid, "evaluations", row)
    ev(None, 100.0)
    ev("p1", 101.0)
    ev("p2", 99.0)
    ev("p4", 500.0)  # falsified: must be ignored
    written = mod.noise_floor(cfg, vis=vis, hid=hid)
    assert written == {"H1": 3}
    r = hid.execute("SELECT sigma_robust, n FROM noise_floor WHERE metric='area'").fetchone()
    assert r["n"] == 2 and abs(r["sigma_robust"] - 1.4826 * 0.01) < 1e-9
    assert vis.execute("SELECT COUNT(*) FROM noise_floor").fetchone()[0] == 0
