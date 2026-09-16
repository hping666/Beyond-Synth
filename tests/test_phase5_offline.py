"""Offline tests of the Phase 5 launch tooling (scripts/phase5_main.py; decisions 2026-09-15 item 6): the probe rule and
the large-tier assignment, the run matrix, the caps (go / no-go in both directions), and the driver's refusal of an arm
without a definition."""
import copy
import json

import pytest

from src import config as C
from src.db import core as db

import scripts.phase5_main as PM


@pytest.fixture
def env(tmp_path):
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    cfg["exp5"]["starting_points"] = {"small": ["s1", "s2"], "medium": ["m1"], "large": ["l1"]}
    cfg["scale"]["arms"] = ["B0", "B1_E4", "B2", "M", "DrRTL_reimpl"]
    cfg["scale"]["seeds"] = 2
    cfg["llm"]["second_model"] = {"model": "gpt-5.6-terra", "arms": ["M", "B2"], "scope": "all_phase5_starting_points"}
    cfg["exp5"]["correctness_probe"]["designs"] = ["p1", "p2", "p3"]
    cfg["exp5"]["correctness_probe"]["min_proven"] = 5
    return cfg, conn


def probe_runs(conn, proven_by_model_design, status="done"):
    for model, byd in proven_by_model_design.items():
        for did, n in byd.items():
            rid = f"probe_{model[-5:]}_{did}"
            db.insert(conn, "runs", {"run_id": rid, "exp": "phase5_probe", "arm": "M", "design_id": did, "seed": 1, "llm_model": model, "status": status})
            for i in range(n):
                db.insert(conn, "candidates", {"cand_id": f"{rid}_c{i}", "run_id": rid, "design_id": did, "verdict": "proven", "label": "retained"})


def test_probe_rule_and_large_tier_assignment(env):
    cfg, conn = env
    probe_runs(conn, {"gpt-5.6-terra": {"p1": 2, "p2": 0, "p3": 6}, "gpt-5.6-sol": {"p1": 0, "p2": 0, "p3": 1}})
    proven, qual, finished, zero, n = PM.probe_verdicts(cfg, conn)
    assert qual == {"gpt-5.6-terra": True, "gpt-5.6-sol": False} and finished and not zero and n == 6
    assert PM.large_tier_model(cfg, qual)[0] == "gpt-5.6-terra"
    assert PM.large_tier_model(cfg, {"gpt-5.6-terra": False, "gpt-5.6-sol": True})[0] == "gpt-5.6-sol"          # sol carries the large tier only when terra does not qualify
    m, note = PM.large_tier_model(cfg, {"gpt-5.6-terra": False, "gpt-5.6-sol": False})
    assert m == "gpt-5.6-terra" and "no probe model reached" in note


def test_plan_matrix_and_undefined_arms(env):
    cfg, conn = env
    probe_runs(conn, {"gpt-5.6-terra": {"p1": 0, "p2": 0, "p3": 0}, "gpt-5.6-sol": {"p1": 0, "p2": 0, "p3": 7}})
    cfg["scale"]["arms"] = ["B0", "B1_E4", "B2", "M", "DrRTL_reimpl", "Undefined_arm"]
    pl = PM.plan(cfg, conn)
    assert pl["skipped_arms"] == ["Undefined_arm"]                                                                 # no driver definition: not launched (DrRTL_reimpl is defined since 2026-09-15)
    runs = pl["runs"]
    from collections import Counter
    # decision 2026-09-15 evening item 3 (exp5.model_assignment): large tier = terra on every arm + luna on M (contrast); small / medium = luna on every arm + terra on M / B2 (second); sol never
    assert Counter(r["model"] for r in runs) == {"gpt-5.6-luna": 3 * 2 * 5 + 1 * 2 * 1, "gpt-5.6-terra": 1 * 2 * 5 + 3 * 2 * 2}
    assert Counter(r["role"] for r in runs) == {"main": 4 * 2 * 5, "second": 3 * 2 * 2, "contrast": 1 * 2 * 1}
    large = [r for r in runs if r["tier"] == "large"]
    assert {(r["model"], r["role"]) for r in large if r["arm"] == "B0"} == {("gpt-5.6-terra", "main")}
    assert {(r["model"], r["role"]) for r in large if r["arm"] == "M"} == {("gpt-5.6-terra", "main"), ("gpt-5.6-luna", "contrast")}
    assert {(r["model"], r["role"]) for r in runs if r["tier"] == "small" and r["arm"] == "B2"} == {("gpt-5.6-luna", "main"), ("gpt-5.6-terra", "second")}
    assert not [r for r in runs if r["model"] == "gpt-5.6-sol"] and pl["probe"]["zero"] is False
    assert pl["assignment"]["large"]["all_arms"] == "gpt-5.6-terra" and PM.tier_assignment(cfg, "medium")["second"] == {"gpt-5.6-terra": ["M", "B2"]}
    cfg2 = copy.deepcopy(cfg)
    cfg2["exp5"].pop("model_assignment")                                                                             # without the assignment: the pre-amendment rule (main model everywhere, second model on its arms)
    assert Counter(r["model"] for r in PM.plan(cfg2, conn)["runs"]) == {"gpt-5.6-luna": 4 * 2 * 5, "gpt-5.6-terra": 4 * 2 * 2}
    text = PM.prelaunch(cfg, conn, write=False)[4]
    assert "| model | B0 |" in text and "| large | gpt-5.6-terra | main |" in text and "| large | gpt-5.6-luna | contrast |" in text and "vcf_seats_target = dc_seats_target" in text


def test_prelaunch_caps_in_both_directions(env, monkeypatch, tmp_path):
    cfg, conn = env
    probe_runs(conn, {"gpt-5.6-terra": {"p1": 0, "p2": 0, "p3": 6}, "gpt-5.6-sol": {"p1": 0, "p2": 0, "p3": 0}})
    monkeypatch.setattr(PM, "per_call_stats", lambda cfg, conn: {("gpt-5.6-luna", t): {"usd_per_call": 0.01, "vcf_s_per_call": 60.0, "proven_per_call": 0.3, "accepted_per_call": 0.1, "e4_s_per_proven": 100.0} for t in ("small", "medium", "large")})
    monkeypatch.setattr(PM, "projection", lambda cfg, conn, pl: {"llm_usd": 50.0, "vcf_hours": 100.0, "dc_hours": 200.0, "disk_gb": 10.0, "by_model": {"gpt-5.6-luna": {"runs": len(pl["runs"]), "usd": 50.0}}, "sources": {}, "t_e4_by_tier": {}, "runs": len(pl["runs"]), "calls": 60 * len(pl["runs"])})
    monkeypatch.setattr(PM.shutil, "disk_usage", lambda p: type("U", (), {"free": 80e9, "total": 1e12, "used": 9e11})())
    go, pl, pr, checks, text = PM.prelaunch(cfg, conn, write=False)
    assert go and "**GO**" in text and all(v[2] for v in checks.values())
    cfg["exp5"]["launch_caps"]["vcf_hours"] = 50                                                                   # one projection outside its cap: no-go
    go2, _, _, checks2, text2 = PM.prelaunch(cfg, conn, write=False)
    assert not go2 and "NO-GO" in text2 and not checks2["vcf_hours"][2]
    cfg["exp5"]["launch_caps"]["vcf_hours"] = 4200
    monkeypatch.setattr(PM.shutil, "disk_usage", lambda p: type("U", (), {"free": 25e9, "total": 1e12, "used": 9e11})())   # 25 - 20 < 10 GB projected
    assert not PM.prelaunch(cfg, conn, write=False)[0]
    monkeypatch.setattr(PM.shutil, "disk_usage", lambda p: type("U", (), {"free": 80e9, "total": 1e12, "used": 9e11})())
    conn.execute("UPDATE runs SET status='running' WHERE exp='phase5_probe'")                                    # the probe still running: no-go
    go3, _, _, _, text3 = PM.prelaunch(cfg, conn, write=False)
    assert not go3 and "probe not finished" in text3
    conn.execute("UPDATE runs SET status='done' WHERE exp='phase5_probe'")
    conn.execute("DELETE FROM candidates")                                                                       # zero proven for both models everywhere: no-go
    go4, _, _, _, text4 = PM.prelaunch(cfg, conn, write=False)
    assert not go4 and "zero proven" in text4


def test_driver_refuses_an_arm_without_a_definition(tmp_path, monkeypatch):
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    from src.search.driver import SearchRun
    db.insert(conn, "runs", {"run_id": "rX", "exp": "phase5", "arm": "Undefined_arm", "design_id": "rtllm_d", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "created"})
    with pytest.raises(ValueError, match="no definition"):
        SearchRun(cfg, conn, "rX")


def test_disk_reserve_and_scope_report(env, monkeypatch):
    """Storage decision 2026-09-15: the disk cap is free space minus the margin minus the reserve; the scope report counts block-level
    flags per arm for generation 1 and overall (both directions: module-level regions and unflagged answers do not count as flags)."""
    cfg, conn = env
    cfg["exp5"]["launch_caps"]["disk_margin_gb"], cfg["exp5"]["launch_caps"]["disk_reserve_gb"] = 20, 5
    cp = PM.caps(cfg)
    assert cp["disk_reserve_gb"] == 5.0 and cp["disk_margin_gb"] == 20.0
    import shutil
    monkeypatch.setattr(shutil, "disk_usage", lambda p: type("U", (), {"free": 80e9, "total": 1e12, "used": 9e11})())
    monkeypatch.setattr(PM, "projection", lambda cfg_, conn_, pl: {"llm_usd": 1.0, "vcf_hours": 1.0, "dc_hours": 1.0, "disk_gb": 54.0, "by_model": {}, "sources": {}, "runs": 0, "calls": 0})
    go, pl, pr, checks, text = PM.prelaunch(cfg, conn, write=False)
    assert abs(checks["disk_gb"][1] - 55.0) < 1e-6 and checks["disk_gb"][2] and "Stamps: equiv_version" in text
    monkeypatch.setattr(PM, "projection", lambda cfg_, conn_, pl: {"llm_usd": 1.0, "vcf_hours": 1.0, "dc_hours": 1.0, "disk_gb": 56.0, "by_model": {}, "sources": {}, "runs": 0, "calls": 0})
    assert not PM.prelaunch(cfg, conn, write=False)[3]["disk_gb"][2]
    db.insert(conn, "runs", {"run_id": "r5s", "exp": "phase5", "arm": "M", "design_id": "d", "seed": 1, "llm_model": "m", "status": "running"})
    db.insert(conn, "runs", {"run_id": "r5b", "exp": "phase5", "arm": "B2", "design_id": "d", "seed": 1, "llm_model": "m", "status": "running"})
    blocks = lambda v: json.dumps({"region": {"kind": "blocks", "module": "d"}, "violations": v})
    for cid, rid, gen, sj in (("s1", "r5s", 1, blocks([{"kind": "always"}])), ("s2", "r5s", 1, blocks([])), ("s3", "r5s", 2, blocks([{"kind": "assign"}])),
                              ("s4", "r5s", 1, json.dumps({"region": {"kind": "module", "module": "sub"}, "violations": [{"module": "top"}]})), ("b1", "r5b", 1, blocks([]))):
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": rid, "design_id": "d", "gen": gen, "arm": "M" if rid == "r5s" else "B2", "scope_json": sj})
    out, lines = PM.scope_report(conn, "phase5")
    assert out["M"] == {"gen1_issued": 2, "gen1_flagged": 1, "all_issued": 3, "all_flagged": 2} and out["B2"] == {"gen1_issued": 1, "gen1_flagged": 0, "all_issued": 1, "all_flagged": 0}
    assert any("| M | 2 | 1 | 50 % | 3 | 2 | 67 % |" in ln for ln in lines)
