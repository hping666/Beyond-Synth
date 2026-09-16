"""Offline tests of the Phase 5 visible-layer report (src/analysis/phase5.collect, scripts/report_phase.py phase5; user decision
2026-09-16: staged reports A / B / C by tier). A fake results database: two runs on a large design, candidates with verdicts,
E4 records and stored labels; the collector re-labels every proven candidate under rule A with the design's floor (both
directions: a real gain is retained, a converged netlist is not), counts the funnel, builds the curves; the renderer writes
the stage file and, for stage C, reports/phase5.md — without ever touching a hidden database."""
import copy
import importlib.util
import json
from pathlib import Path

from src import config as C
from src.analysis import phase5 as P5
from src.db import core as db


def load_report():
    spec = importlib.util.spec_from_file_location("report_phase", str(Path(C.ROOT) / "scripts" / "report_phase.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_collect_and_render_stage_a(tmp_path, monkeypatch):
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"small": ["s1"], "medium": ["m1"], "large": ["l1"]}
    cfg["scale"]["seeds"] = 1
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('l1','x','l1','p',1,1,'held',1.0,'t','g','c')")
    for metric, t in (("area", 0.01), ("wns", 0.005), ("power_saif", 0.02)):
        db.insert(conn, "noise_floor", {"design_id": "l1", "config": "E4", "metric": metric, "sigma_robust": 0.002, "t_d": t, "floor_class": "quiet", "floor_source": "measured", "floor_version": cfg["noise"].get("floor_version")})
    base_hist = json.dumps({"NAND2_X1": 100, "DFF_X1": 20})
    db.insert(conn, "evaluations", {"design_id": "l1", "is_baseline": 1, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 100.0, "cells": 120, "wns_ns": 0.05, "tns_ns": 0.0, "power_saif_mw": 1.0, "dc_seconds": 100.0, "status": "ok", "raw_dir": "/v/base", "hist_json": base_hist})
    db.insert(conn, "runs", {"run_id": "r_m", "exp": "phase5", "arm": "M", "design_id": "l1", "seed": 1, "llm_model": "gpt-5.6-terra", "status": "done", "started_at": "t", "llm_calls": 60, "spent_usd": 1.5, "spent_vcf_hours": 0.5, "spent_dc_hours": 0.2, "gens_done": 12})
    db.insert(conn, "runs", {"run_id": "r_b2", "exp": "phase5", "arm": "B2", "design_id": "l1", "seed": 1, "llm_model": "gpt-5.6-terra", "status": "running", "started_at": "t", "llm_calls": 30, "spent_usd": 0.0, "gens_done": 6})
    db.insert(conn, "runs", {"run_id": "r_old", "exp": "phase5", "arm": "M", "design_id": "l1", "seed": 1, "llm_model": "gpt-5.6-terra", "status": "superseded", "started_at": "t"})
    db.insert(conn, "runs", {"run_id": "r_med", "exp": "phase5", "arm": "M", "design_id": "m1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "running", "started_at": "t", "llm_calls": 5})

    def cand(cid, run, verdict=None, label=None, accepted=0, e4=None, gen=1, extra=None):
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": run, "design_id": "l1", "gen": gen, "arm": "M" if run == "r_m" else "B2", "llm_model": "gpt-5.6-terra", "verdict": verdict, "label": label,
                                       "accepted": accepted, "class_requested": "b", "class_final": "b", "cost_usd": 0.02, "time_to_verdict_s": 120.0, "v3_seconds": 60.0, **(extra or {})})
        if e4:
            area, hist = e4
            db.insert(conn, "evaluations", {"design_id": "l1", "cand_id": cid, "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": area, "cells": 100, "wns_ns": 0.05, "tns_ns": 0.0, "power_saif_mw": 1.0, "dc_seconds": 90.0, "status": "ok", "raw_dir": f"/v/{cid}", "hist_json": json.dumps(hist)})
    cand("c_ret", "r_m", "proven", "retained", 1, (92.0, {"NAND2_X1": 70, "DFF_X1": 20}))                       # 8 % smaller, a different netlist: retained
    cand("c_conv", "r_m", "proven", "absorbed", 0, (99.9, {"NAND2_X1": 100, "DFF_X1": 20, "INV_X1": 1}))       # converged fingerprint, no gain: absorbed / noise, never retained
    cand("c_sim", "r_m", "sim_fail", "nonequiv", 0, None, extra={"repair_of": None, "scope_json": json.dumps({"region": {"kind": "blocks"}, "violations": [{"kind": "always"}]})})
    cand("c_rep", "r_m", "rejected", "nonequiv", 0, None, gen=2, extra={"repair_of": "c_sim", "scope_json": json.dumps({"region": {"kind": "blocks"}, "violations": []})})
    cand("c_dup", "r_m", None, "duplicate", 0, None, gen=2)
    cand("c_b2", "r_b2", "proven", "improved", 1, (95.0, {"NAND2_X1": 80, "DFF_X1": 20}), extra={"latency_offset_json": json.dumps({"y": 2})})   # B2's own label improved; uniform: retained (5 % > t_d 1 %); latency-mapped
    cand("c_b2p", "r_b2", None, None, 0, None, gen=2)                                                                       # pending
    (tmp_path / "results" / "candidates" / "r_m").mkdir(parents=True)
    (tmp_path / "results" / "candidates" / "r_m" / "unusable_g1_3.json").write_text("{}")
    data = P5.collect(cfg, conn, tiers=["large"])
    gm, gb = data["groups"]["large|gpt-5.6-terra|M"], data["groups"]["large|gpt-5.6-terra|B2"]
    assert gm["runs"] == 1 and gm["done"] == 1 and gm["cands"] == 5 and gm["unusable"] == 1 and gm["proven"] == 2 and gm["sim_fail"] == 1 and gm["rejected"] == 1 and gm["duplicate"] == 1
    assert gm["uniform"]["retained"] == 1 and gm["uniform"].get("retained", 0) + sum(v for k, v in gm["uniform"].items() if k in ("absorbed", "noise", "absorbed_identical")) == 2
    assert gm["retained"] == 1 and gm["runs_with_retained"] == 1 and abs(gm["best_gain_mean"] - 0.08) < 1e-6 and gm["accepted"] == 1
    assert gm["scope_flags"] == 1 and gm["block_answers"] == 2 and gm["block_flags"] == 1 and gm["repairs"] == 1 and gm["repairs_proven"] == 0
    assert gm["stored"] == {"retained": 1, "absorbed": 1, "nonequiv": 2} and gm["classes"] == {"b": 4} and gm["ttv"]["n"] == 4
    assert gb["runs"] == 1 and gb["done"] == 0 and gb["proven"] == 1 and gb["latency_mapped"] == 1 and gb["pending"] == 1 and gb["uniform"] == {"retained": 1} and gb["stored"] == {"improved": 1}
    assert abs(gb["usd"] - 0.04) < 1e-9 and gm["usd"] == 1.5                                                                # a running run's spend from its candidate rows; a finished run's from the row
    assert data["designs"]["large|gpt-5.6-terra|M|l1"]["best_retained_area_gain"] == 0.08 and data["correctness"]["large|gpt-5.6-terra|l1"]["proven"] == 3
    assert "large|gpt-5.6-terra|M" in data["curves"] and data["curves"]["large|gpt-5.6-terra|M"]["by_calls"][0]["mean_best_gain"] == 0.08
    assert not [r for r in data["runs"] if r["run_id"] in ("r_old", "r_med")]                                                # superseded runs and other tiers stay out
    assert not [k for k in data["groups"] if k.startswith("medium")]
    R = load_report()
    out = tmp_path / "reports"
    assert R.phase5(cfg, stage="A", out_dir=str(out), conn=conn) == 0
    text = (out / "phase5_stage_A.md").read_text()
    assert "Stage A" in text and "| gpt-5.6-terra (main) | M | 1/1 | 5 | 1 | 2 (0.033) |" in text and "8.00 %" in text and "block-level" in text and "improved: 1" in text
    assert "Visible layer only" in text and not (out / "phase5.md").exists() and (out / "data" / "phase5_visible_A.json").exists()
    assert R.phase5(cfg, stage="C", out_dir=str(out), conn=conn) == 0 and (out / "phase5.md").exists() and "Success criteria" in (out / "phase5.md").read_text()


def test_tier_complete_both_directions(tmp_path, monkeypatch):
    """scripts/phase5_stages.py: a tier is complete only when every planned run of it is done; superseded rows and other tiers do not count."""
    spec = importlib.util.spec_from_file_location("phase5_stages", str(Path(C.ROOT) / "scripts" / "phase5_stages.py"))
    ST = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ST)
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    plan = [{"tier": "large", "model": "m", "arm": "M", "design_id": "l1", "seed": 1}, {"tier": "large", "model": "m", "arm": "B2", "design_id": "l1", "seed": 1},
            {"tier": "small", "model": "m", "arm": "M", "design_id": "s1", "seed": 1}]
    db.insert(conn, "runs", {"run_id": "a", "exp": "phase5", "arm": "M", "design_id": "l1", "seed": 1, "llm_model": "m", "status": "done"})
    db.insert(conn, "runs", {"run_id": "b", "exp": "phase5", "arm": "B2", "design_id": "l1", "seed": 1, "llm_model": "m", "status": "running"})
    assert not ST.tier_complete(cfg, conn, "large", plan=plan)
    conn.execute("UPDATE runs SET status='done' WHERE run_id='b'"); conn.commit()
    assert ST.tier_complete(cfg, conn, "large", plan=plan) and not ST.tier_complete(cfg, conn, "small", plan=plan) and not ST.tier_complete(cfg, conn, "medium", plan=plan)
    db.insert(conn, "runs", {"run_id": "c", "exp": "phase5", "arm": "M", "design_id": "s1", "seed": 1, "llm_model": "m", "status": "superseded"})
    assert not ST.tier_complete(cfg, conn, "small", plan=plan)
