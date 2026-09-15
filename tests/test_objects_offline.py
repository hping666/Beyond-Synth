"""Bidirectional tests of src/analysis/objects.py (2026-09-15): the rule-A thresholds fall back per metric to the pooled
minimum of the configuration when the design has no measured component (no floor row at all, or no power floor), and
stay None only without a pooled minimum; `diagnose_objects` diagnoses a proven object once, skips it afterwards, and
re-derives it with force (replacing the row and the candidate label), passing the partial thresholds instead of a zero
band."""
import json

from src import config as C
from src.analysis import objects as O
from src.db import core as db
from src.noise import stats as S


def floor_row(design_id, config, metric, t_d, pooled):
    return {"design_id": design_id, "config": config, "metric": metric, "sigma_robust": 0.0, "sigma_std": 0.0, "q95_abs": 0.0, "max_abs": 0.0, "n": 4, "abs_unit_value": None,
            "t_d": t_d, "floor_class": "quiet", "floor_source": "measured", "pooled_min": pooled}


def test_thresholds_fall_back_to_the_pooled_minimum(tmp_path):
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    S.upsert_floor(conn, [floor_row("a", "E4", "area", 0.005, 0.003), floor_row("a", "E4", "wns", 0.002, 0.001), floor_row("a", "E4", "power_saif", 0.03, 0.022)], floor_version="phase4")
    S.upsert_floor(conn, [floor_row("b", "E4", "area", 0.004, 0.003), floor_row("b", "E4", "wns", 0.002, 0.001)], floor_version="phase4")   # b: no power floor (D without SAIF)
    assert O.pooled_minimum_floor(conn, "E4", "phase4") == {"area": 0.003, "wns": 0.001, "power_saif": 0.022}
    assert O.thresholds(conn, "a", "E4", "phase4")[0] == {"area": 0.005, "wns": 0.002, "power": 0.03}          # measured wins
    assert O.thresholds(conn, "b", "E4", "phase4")[0] == {"area": 0.004, "wns": 0.002, "power": 0.022}         # power from the pooled minimum
    assert O.thresholds(conn, "c", "E4", "phase4")[0] == {"area": 0.003, "wns": 0.001, "power": 0.022}         # no floor row at all: pooled minimum throughout
    assert O.thresholds(conn, "c", "E1", "phase4")[0] == {"area": None, "wns": None, "power": None}            # no pooled minimum for E1: None


def _design(conn, did="rtllm_x", phi=2.0):
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                 (did, "rtllm", "x", "x", 1, 1, "held", phi, "t", "g", "c"))


def _ev(conn, did, config, area, power_saif, power_default, hist, cand_id=None, is_baseline=0, clock=2.0):
    db.insert(conn, "evaluations", {"design_id": did, "cand_id": cand_id, "is_baseline": is_baseline, "config": config, "lib": "nangate45", "clock_ns": clock, "area_um2": area, "cells": sum(hist.values()),
                                    "wns_ns": 0.1, "tns_ns": 0.0, "power_saif_mw": power_saif, "power_default_mw": power_default, "status": "ok", "raw_dir": f"/x/{config}/{cand_id or 'd'}",
                                    "hist_json": json.dumps(hist), "created_at": "t"})


def test_diagnose_objects_once_skip_and_force(tmp_path):
    cfg = C.load()
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    _design(conn)
    S.upsert_floor(conn, [floor_row("rtllm_x", "E4", "area", 0.005, 0.003), floor_row("rtllm_x", "E4", "wns", 0.002, 0.001), floor_row("rtllm_x", "E4", "power_saif", 0.03, 0.022)], floor_version=cfg["noise"]["floor_version"])
    _ev(conn, "rtllm_x", "E4", 100.0, None, 4.0, {"NAND2_X1": 20, "DFF_X1": 10}, is_baseline=1)                     # D without SAIF power
    db.insert(conn, "runs", {"run_id": "b0x", "exp": "phase4", "arm": "B0", "design_id": "rtllm_x", "seed": 1, "status": "done", "started_at": "t"})
    db.insert(conn, "candidates", {"cand_id": "obj", "run_id": "b0x", "design_id": "rtllm_x", "gen": 1, "arm": "B0", "rtl_path": "x.v", "label": "improved", "verdict": "proven", "class_final": "b"})
    _ev(conn, "rtllm_x", "E4", 99.0, 0.5, 3.9, {"NAND2_X1": 19, "DFF_X1": 10}, cand_id="obj")                        # 1 % smaller; SAIF power on C only
    out = O.diagnose_objects(cfg, conn, "phase4")
    assert out["diagnosed"] == 1 and out["labels"] == {"retained": 1}
    d = conn.execute("SELECT label, evidence_json FROM diagnoses WHERE cand_id='obj'").fetchone()
    ev = json.loads(d[1])
    assert d[0] == "retained" and ev["power_basis"] == "default" and round(ev["gains"]["power"], 5) == 0.025 and ev["band"] == {"area": 0.005, "wns": 0.002, "power": 0.03}   # not 4.0 vs 0.5
    assert conn.execute("SELECT label FROM candidates WHERE cand_id='obj'").fetchone()[0] == "retained"
    again = O.diagnose_objects(cfg, conn, "phase4")
    assert again["diagnosed"] == 0 and again["existing"] == 1                                                         # idempotent
    conn.execute("UPDATE evaluations SET area_um2=100.0, cells=30, hist_json=? WHERE cand_id='obj'", (json.dumps({"NAND2_X1": 20, "DFF_X1": 10}),))   # the record changes (a rule or ingest fix)
    dry = O.diagnose_objects(cfg, conn, "phase4", dry_run=True, force=True)
    assert dry["diagnosed"] == 1 and dry["labels"] == {"absorbed_identical": 1} and conn.execute("SELECT label FROM diagnoses WHERE cand_id='obj'").fetchone()[0] == "retained"   # dry run writes nothing
    forced = O.diagnose_objects(cfg, conn, "phase4", force=True)
    assert forced["replaced"] == 1 and forced["labels"] == {"absorbed_identical": 1}
    assert conn.execute("SELECT COUNT(*) FROM diagnoses WHERE cand_id='obj'").fetchone()[0] == 1
    assert conn.execute("SELECT label FROM candidates WHERE cand_id='obj'").fetchone()[0] == "absorbed_identical"
