"""Bidirectional tests of the PLAN 4.6 / 4.9 helpers (src/analysis/validation.py): the single-flag configurations read
from the config (alias resolved), the deterministic stratified sample (every design represented first, seed-stable,
n above the total returns everything), the single-flag reproduction on a temporary database (a flag whose D netlist
matches C@E1 converges, a different netlist does not, a missing baseline is None, no C@E1 record -> None), the summary
counts, and the motivating-figure picks (largest recovered E1 gain, largest retained E4 gain, None when absent)."""
import json

from src import config as C
from src.analysis import validation as V
from src.db import core as db


def test_single_flag_rungs_from_config():
    assert V.single_flag_rungs(C.load()) == {"designware": "E1d", "gate_clock": "E2g", "retime": "E3"}
    assert V.single_flag_rungs({"configs": {"X": {"tool": "dc"}}}) == {}


def test_stratified_sample_round_robin_and_determinism():
    rows = [{"cand_id": f"c{i}", "design_id": d} for i, d in enumerate(["d1"] * 5 + ["d2"] * 1 + ["d3"] * 2)]
    s = V.stratified_sample(rows, 5, seed=1)
    counts = {}
    for r in s:
        counts[r["design_id"]] = counts.get(r["design_id"], 0) + 1
    assert counts == {"d1": 2, "d2": 1, "d3": 2} and len({r["cand_id"] for r in s}) == 5
    assert [r["cand_id"] for r in V.stratified_sample(rows, 5, seed=1)] == [r["cand_id"] for r in s]      # seed-stable
    assert len(V.stratified_sample(rows, 50, seed=3)) == 8 and V.stratified_sample([], 5, seed=1) == []


def _ev(conn, design_id, config, hist, area, cand_id=None, is_baseline=0):
    db.insert(conn, "evaluations", {"design_id": design_id, "cand_id": cand_id, "is_baseline": is_baseline, "config": config, "lib": "nangate45", "clock_ns": 2.0,
                                    "area_um2": area, "cells": sum(hist.values()), "wns_ns": 0.1, "tns_ns": 0.0, "status": "ok", "raw_dir": f"/x/{config}/{cand_id or 'd'}",
                                    "hist_json": json.dumps(hist), "created_at": "t"})


def test_single_flag_reproduction_and_summary(tmp_path):
    cfg = C.load()
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    from src.noise import stats as S
    S.upsert_floor(conn, [{"design_id": "d", "config": "E1", "metric": "area", "sigma_robust": 0.0, "sigma_std": 0.0, "q95_abs": 0.0, "max_abs": 0.0, "n": 4, "abs_unit_value": None,
                           "t_d": 0.01, "floor_class": "quiet", "floor_source": "measured", "pooled_min": 0.01}])
    _ev(conn, "d", "E1", {"NAND2_X1": 20, "DFF_X1": 4}, 100.0, is_baseline=1)
    _ev(conn, "d", "E2g", {"NAND2_X1": 20, "DFF_X1": 4, "CLKGATE_X1": 1}, 100.5, is_baseline=1)     # D with -gate_clock alone
    _ev(conn, "d", "E1d", {"NAND2_X1": 8, "DFF_X1": 4}, 60.0, is_baseline=1)                        # D with DesignWare: another netlist
    _ev(conn, "d", "E1", {"NAND2_X1": 20, "DFF_X1": 4, "CLKGATE_X1": 1}, 100.4, cand_id="c_gate")   # the hand-gated rewrite compiled plainly
    rep = V.single_flag_reproduction(cfg, conn, "c_gate", "d", 2.0)
    assert rep["gate_clock"]["converged"] is True and rep["gate_clock"]["config"] == "E2g"
    assert rep["designware"]["converged"] is False and rep["retime"] is None                          # E3 baseline missing
    assert rep["none"]["converged"] is False                                                           # not already there with a plain compile
    assert V.single_flag_reproduction(cfg, conn, "unknown", "d", 2.0) is None
    summ = V.reproduction_summary([{"cand_id": "c_gate", "design_id": "d", "label": "absorbed", "rung": "E4", "repro": rep},
                                  {"cand_id": "c2", "design_id": "d", "label": "absorbed", "rung": "E4", "repro": {"gate_clock": {"converged": False, "config": "E2g"}, "none": {"converged": True, "config": "E1"}}}])
    assert summ["n"] == 2 and summ["reproduced_by_a_single_flag"] == 1 and summ["rate_any_flag"] == 0.5
    assert summ["by_flag"]["gate_clock"] == {"config": "E2g", "evaluated": 2, "converged": 1, "rate": 0.5} and summ["by_flag"]["retime"]["evaluated"] == 0 if "retime" in summ["by_flag"] else True


def test_pick_motivating_and_markdown():
    objs = [{"cand_id": "a", "design_id": "d", "cls": "a", "label": "absorbed_identical", "rung": "E4", "gains": {"E1": {"area": 0.30, "wns": 0.0, "power": 0.1}, "E4": {"area": 0.0, "wns": 0.0, "power": 0.0}}, "t_d": {"E4": {"area": 0.003}}},
            {"cand_id": "b", "design_id": "d", "cls": "b", "label": "noise", "rung": None, "gains": {"E1": {"area": 0.10, "wns": 0.0, "power": 0.0}, "E4": {"area": 0.001, "wns": 0.0, "power": 0.0}}, "t_d": {}},
            {"cand_id": "r1", "design_id": "d", "cls": "d", "label": "retained", "rung": None, "gains": {"E1": {"area": 0.05, "wns": 0.0, "power": 0.0}, "E4": {"area": 0.04, "wns": 0.0, "power": 0.0}}, "t_d": {}},
            {"cand_id": "r2", "design_id": "d", "cls": "c1", "label": "retained", "rung": None, "gains": {"E1": {"area": 0.20, "wns": 0.0, "power": 0.0}, "E4": {"area": 0.12, "wns": None, "power": 0.0}}, "t_d": {}},
            {"cand_id": "x", "design_id": "d", "cls": "a", "label": "retained", "rung": None, "gains": {"E4": {"area": 0.50, "wns": 0.0, "power": 0.0}}, "t_d": {}}]   # no E1 record: not eligible
    picks = V.pick_motivating(objs)
    assert picks["recovered"]["cand_id"] == "a" and picks["retained"]["cand_id"] == "r2"
    assert V.pick_motivating([o for o in objs if o["label"] != "retained"])["retained"] is None
    md = V.motivating_md(picks)
    assert "recovered: a" in md and "retained: r2" in md and "+30.0 %" in md and "0.30 %" in md and "retained: none" not in md
    assert "recovered: none" in V.motivating_md({"recovered": None, "retained": None})
