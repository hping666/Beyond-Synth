"""Bidirectional tests of the evaluation service's routing rules (src/eval/service.py, CLAUDE.md rule 3): hidden
configurations only through the hidden database and raw tree, visible ones never there; knee-sweep configurations
only for original designs with an explicit clock; clock ports normalised. The DC runner is replaced by a fake."""
import copy
import json
from pathlib import Path

import pytest

from src import config as C
from src.db import core as db
from src.eval import service as SV


def fake_run_dc(job_dir, rtl_files, top, lib, compile_cmd, clock_ns, clk_port, cfg, **kw):
    (Path(job_dir) / "outputs" / "reports").mkdir(parents=True, exist_ok=True)
    return {"tool": "dc", "tool_version": "fake", "lib": lib, "clock_ns": float(clock_ns), "status": "ok", "error": None,
            "checks": {"fake": True}, "metrics": {"area": 1.0, "cells": 1, "wns_ns": 0.1, "tns_ns": 0.0},
            "dc_seconds": 1.0, "compile": compile_cmd, "clk_port_seen": clk_port}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    monkeypatch.setattr(SV, "run_dc", fake_run_dc)
    rtl = tmp_path / "d.v"
    rtl.write_text("module d(input clk, output y); assign y = clk; endmodule\n")
    vis = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    hid = db.connect(path=str(tmp_path / "results" / "hidden" / "hidden.sqlite"))
    return cfg, rtl, vis, hid


def count(conn):
    return conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]


def test_visible_config_records_visibly_and_normalises_clock_ports(setup):
    cfg, rtl, vis, hid = setup
    meta = SV.evaluate(cfg, vis, "d1", [rtl], "d", "E4", clock_ns=2.0, clk_port=["wclk", "rclk"])
    assert meta["status"] == "ok" and meta["clk_port"] == "wclk rclk" and meta["clk_port_seen"] == "wclk rclk"
    assert "/raw/d1/E4/" in meta["raw_dir"] and "/hidden/" not in meta["raw_dir"] and meta["eval_id"]
    assert count(vis) == 1 and count(hid) == 0
    assert SV.evaluate(cfg, vis, "d1", [rtl], "d", "E4", clock_ns=2.0, clk_port="wclk rclk")["cached"]  # same inputs
    with pytest.raises(SV.HiddenConfigError):
        SV.evaluate(cfg, hid, "d1", [rtl], "d", "E4", clock_ns=2.0)
    assert count(hid) == 0


def test_hidden_config_only_through_the_hidden_database(setup):
    cfg, rtl, vis, hid = setup
    with pytest.raises(SV.HiddenConfigError):
        SV.evaluate(cfg, vis, "d1", [rtl], "d", "H1")
    assert not list(Path(cfg["project"]["results_dir"]).rglob("meta.json"))
    meta = SV.evaluate(cfg, hid, "d1", [rtl], "d", "H1")
    assert meta["status"] == "ok" and "/hidden/raw/d1/H1/" in meta["raw_dir"]
    assert hid.execute("SELECT config FROM evaluations").fetchone()[0] == "H1" and count(vis) == 0
    assert SV.db_is_hidden(hid) and not SV.db_is_hidden(vis)
    for name, c in cfg["configs"].items():
        if isinstance(c, dict) and name.startswith("H"):
            assert c.get("hidden"), name


def test_knee_configs_reject_candidates_and_need_an_explicit_clock(setup):
    cfg, rtl, vis, hid = setup
    with pytest.raises(ValueError, match="original designs only"):
        SV.evaluate(cfg, vis, "d1", [rtl], "d", "K_asap7", clock_ns=0.5, cand_id="c1")
    with pytest.raises(ValueError, match="original designs only"):
        SV.evaluate(cfg, vis, "d1", [rtl], "d", "K_sky130hd", clock_ns=5.0, pert_id="p1")
    with pytest.raises(ValueError, match="knee-sweep"):
        SV.evaluate(cfg, vis, "d1", [rtl], "d", "K_asap7")
    meta = SV.evaluate(cfg, vis, "d1", [rtl], "d", "K_asap7", clock_ns=0.5)
    assert meta["status"] == "ok" and meta["lib"] == "asap7" and meta["config"] == "K_asap7" and "/raw/d1/K_asap7/" in meta["raw_dir"]
    for name in ("K_asap7", "K_sky130hd"):
        assert cfg["configs"][name]["compile"] == cfg["configs"]["E4"]["compile"] and not cfg["configs"][name].get("hidden")
        assert name not in cfg["exp1"]["configs"] and name not in cfg["exp1"].get("supplementary", []) and name not in cfg["noise"]["configs"]
    assert cfg["knee"]["configs"] == {"nangate45": "E4", "asap7": "K_asap7", "sky130hd": "K_sky130hd"}


def test_library_dont_use_cells_reach_dc(setup, monkeypatch):
    """sky130hd multi-power-domain cells are excluded (DC MV-090 without UPF, DECISIONS 2026-09-12); Nangate45 has none."""
    from src.eval import dc as DC
    cfg, rtl, vis, hid = setup
    assert SV.resolve_config(cfg, "K_sky130hd", None, 5.0)["dont_use"] == cfg["libs"]["sky130hd"]["dont_use"]
    assert SV.resolve_config(cfg, "E4", None, 2.0)["dont_use"] == []
    seen = {}

    def fake_run(argv, cwd=None, env=None, **kw):
        seen["env"] = dict(env)
        raise RuntimeError("stop here")

    monkeypatch.setattr(SV, "run_dc", DC.run_dc)
    monkeypatch.setattr(DC.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        SV.evaluate(cfg, vis, "d1", [rtl], "d", "K_sky130hd", clock_ns=5.0, do_ingest=False)
    assert seen["env"]["EVAL_DONT_USE"] == "sky130_fd_sc_hd__lpflow_* sky130_fd_sc_hd__probe_p_8 sky130_fd_sc_hd__probec_p_8"
    with pytest.raises(RuntimeError):
        SV.evaluate(cfg, vis, "d1", [rtl], "d", "E4", clock_ns=2.0, do_ingest=False)
    assert seen["env"]["EVAL_DONT_USE"] == ""


def test_source_evaluation_prefers_the_record_at_the_period(setup):
    """2026-09-15: a signoff configuration reads the E4 record at its own period; D's E4 baselines exist at several knee-sweep
    periods, so the latest record is not necessarily the right one (both directions)."""
    cfg, rtl, vis, hid = setup
    for i, clock in enumerate((0.5, 0.35)):   # the later record is the tighter sweep period
        db.insert(vis, "evaluations", {"design_id": "d1", "cand_id": None, "pert_id": None, "is_baseline": 1, "config": "E4", "lib": "nangate45", "clock_ns": clock,
                                       "area_um2": 1.0, "cells": 1, "wns_ns": 0.0, "tns_ns": 0.0, "status": "ok", "raw_dir": f"/v/e4_{i}", "hist_json": "{}"})
    assert SV.source_evaluation(vis, "d1", None, None, "E4_netlist")["raw_dir"] == "/v/e4_1"                      # latest without a period
    assert SV.source_evaluation(vis, "d1", None, None, "E4_netlist", clock_ns=0.5)["raw_dir"] == "/v/e4_0"       # the record at Phi_main
    assert SV.source_evaluation(vis, "d1", None, None, "E4_netlist", clock_ns=0.35)["raw_dir"] == "/v/e4_1"
    assert SV.source_evaluation(vis, "d1", None, None, "E4_netlist", clock_ns=1.0) is None                        # no record at that period
    assert SV.source_evaluation(vis, "d1", "c9", None, "E4_netlist", clock_ns=0.5) is None                        # another object


def test_offline_pool_flags_reach_the_evaluations_row(setup):
    """DECISION 2026-09-18 item 1: an evaluation run by the offline pool carries offline_eval / prescreened_offline from the payload
    through meta.json into the evaluations row; ordinary evaluations stay at 0 (both directions)."""
    cfg, rtl, vis, hid = setup
    meta = SV.evaluate(cfg, vis, "d1", [rtl], "d", "E4", clock_ns=3.0, cand_id="c_off", extra_meta={"offline_eval": 1})
    row = vis.execute("SELECT offline_eval, prescreened_offline FROM evaluations WHERE eval_id=?", (meta["eval_id"],)).fetchone()
    assert tuple(row) == (1, 0) and json.loads((Path(meta["raw_dir"]) / "meta.json").read_text())["offline_eval"] == 1
    meta2 = SV.evaluate(cfg, vis, "d1", [rtl], "d", "E4", clock_ns=4.0, cand_id="c_pre", extra_meta={"prescreened_offline": 1})
    assert tuple(vis.execute("SELECT offline_eval, prescreened_offline FROM evaluations WHERE eval_id=?", (meta2["eval_id"],)).fetchone()) == (0, 1)
    meta3 = SV.evaluate(cfg, vis, "d1", [rtl], "d", "E4", clock_ns=5.0, cand_id="c_plain")
    assert tuple(vis.execute("SELECT offline_eval, prescreened_offline FROM evaluations WHERE eval_id=?", (meta3["eval_id"],)).fetchone()) == (0, 0)
