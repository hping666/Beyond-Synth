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
    assert Counter(r["model"] for r in runs) == {"gpt-5.6-luna": 4 * 2 * 5, "gpt-5.6-terra": 2 * 2 * 3, "gpt-5.6-sol": 2 * 2 * 1}   # 4 designs x 2 seeds x 5 arms; terra M / B2 on the 3 non-large designs; sol on the large one
    assert {r["model"] for r in runs if r["tier"] == "large" and r["arm"] in ("M", "B2") and r["model"] != "gpt-5.6-luna"} == {"gpt-5.6-sol"}
    assert pl["probe"]["zero"] is False


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
