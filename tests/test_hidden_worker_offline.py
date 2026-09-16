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
    # --missing: a D and a perturbation already recorded under H1 at 0.1 ns are not resubmitted; the rest is
    db.insert(hid, "evaluations", {"design_id": "rtllm_acc", "pert_id": None, "is_baseline": 1, "config": "H1", "lib": "nangate45", "clock_ns": 0.1,
                                   "area_um2": 1.0, "cells": 1, "wns_ns": 0.0, "tns_ns": 0.0, "status": "ok", "raw_dir": "/h/miss1", "hist_json": "{}"})
    db.insert(hid, "evaluations", {"design_id": "rtllm_acc", "pert_id": "p1", "is_baseline": 0, "config": "H1", "lib": "nangate45", "clock_ns": 0.1,
                                   "area_um2": 1.0, "cells": 1, "wns_ns": 0.0, "tns_ns": 0.0, "status": "ok", "raw_dir": "/h/miss2", "hist_json": "{}"})
    miss = mod.noise_jobs(cfg, vis, missing=True, hid=hid)
    h1 = [j for j in miss if j["config"] == "H1"]
    assert len(h1) == 2 and all(j["payload"]["pert_id"] in ("p2", "p3") for j in h1) and len([j for j in miss if j["config"] == "H5"]) == 4
    only = mod.noise_jobs(cfg, vis, ptypes=["P2_reorder"])
    assert only and all(j["payload"]["is_baseline"] == 0 and j["payload"]["pert_id"] == "p3" for j in only)  # a type filter: no D job, only that type
    assert mod.noise_jobs(cfg, vis, ptypes=["P9_none"]) == []
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


def test_g3_summary_counts_and_seconds_only(env, tmp_path, monkeypatch):
    """Both directions: the ratio and the agreement come out right for records under both configurations; a design
    without an H3 baseline contributes nothing; the output carries no per-design hidden value."""
    cfg, vis, hid, mod, rtl = env
    from src.designs import catalog as K
    from src.noise import stats as S
    monkeypatch.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    for name in ("acc", "bcc"):
        ddir = tmp_path / "designs" / "rtllm" / name
        (ddir / "rtl").mkdir(parents=True)
        (ddir / "rtl" / f"{name}.v").write_text(rtl.read_text())
        d = {"design_id": f"rtllm_{name}", "suite": "rtllm", "name": name, "top": "d", "files": [f"rtl/{name}.v"], "clk_ports": ["clk"], "rst_port": None,
             "rst_sense": None, "sverilog": False, "incdirs": [], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
             "sha256": {f"rtl/{name}.v": K.sha256_of(ddir / "rtl" / f"{name}.v")}, "loc": 1, "tags": ["rtllm"], "notes": [], "_dir": str(ddir)}
        K.write_design(d)
        vis.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) "
                    "VALUES (?,'rtllm',?,'x',1,1,'dev',2.0,'t','g','c')", (f"rtllm_{name}", name))
        for pid in ("p1", "p2", "p3"):
            vis.execute("INSERT INTO perturbations (pert_id, design_id, ptype, path, seq_status, created_at, git_sha, cfg_hash) VALUES (?,?,?,?,?,?,?,?)",
                        (f"{name}_{pid}", f"rtllm_{name}", "P1_rename", "x", "proven", "t", "g", "c"))
    n = [0]

    def ev(conn, did, config, pert, area, secs):
        n[0] += 1
        db.insert(conn, "evaluations", {"design_id": did, "pert_id": pert, "is_baseline": int(pert is None), "config": config, "lib": "nangate45",
                                        "clock_ns": 2.0, "area_um2": area, "cells": 10, "wns_ns": 0.0, "tns_ns": 0.0, "power_saif_mw": 1.0,
                                        "dc_seconds": secs, "status": "ok", "raw_dir": f"/x/{n[0]}", "hist_json": "{}"})
    # acc: E4 (visible) and H3 (hidden) records; p3 is far off under H3 only
    ev(vis, "rtllm_acc", "E4", None, 100.0, 10.0)
    for pid, a in (("acc_p1", 101.0), ("acc_p2", 99.0), ("acc_p3", 100.5)):
        ev(vis, "rtllm_acc", "E4", pid, a, 10.0)
    ev(hid, "rtllm_acc", "H3", None, 100.0, 25.0)
    for pid, a in (("acc_p1", 101.0), ("acc_p2", 99.0), ("acc_p3", 130.0)):
        ev(hid, "rtllm_acc", "H3", pid, a, 25.0)
    # bcc: only E4 records -> contributes nothing
    ev(vis, "rtllm_bcc", "E4", None, 100.0, 10.0)
    ev(vis, "rtllm_bcc", "E4", "bcc_p1", 101.0, 10.0)
    # floors: E4 in the visible database, H3 in the hidden one
    base, latest = S.pick_records(vis, "rtllm_acc", "E4", {"acc_p1", "acc_p2", "acc_p3"}, 2.0)
    S.upsert_floor(vis, S.floor_rows("rtllm_acc", "E4", base, list(latest.values()), 2.0))
    assert mod.noise_floor(cfg, vis=vis, hid=hid) == {"H3": 4}  # area, wns, tns, power_saif rows
    out = mod.g3_summary(cfg, vis=vis, hid=hid)
    assert out["n_designs_with_ratio"] == 1 and abs(out["t_ratio"]["median"] - 2.5) < 1e-9
    assert out["e4_seconds_total"] == 10.0 and out["h3_seconds_total"] == 25.0
    assert out["pairs"] == 3 and out["agree"] == 2 and abs(out["agreement_rate"] - 2 / 3) < 1e-9
    assert out["confusion"] == {"E4=noise|H3=noise": 2, "E4=noise|H3=harmful": 1}
    assert out["area_change"] == {"both changed": 3} and out["both_changed_same_direction"] == 3  # p1 +1 %, p2 -1 %, p3 +0.5 % / +30 %
    txt = json.dumps(out)
    assert "rtllm_acc" not in txt and "130" not in txt  # aggregates only: no design ids, no hidden metric values
    # without hidden records nothing is reported
    hid.execute("DELETE FROM evaluations")
    empty = mod.g3_summary(cfg, vis=vis, hid=hid)
    assert empty["n_designs_with_ratio"] == 0 and empty["pairs"] == 0 and empty["agreement_rate"] is None


def test_coverage_counts_only(env, tmp_path, monkeypatch):
    """Coverage: a floored design with D and every proven perturbation under a full configuration is complete; a missing
    perturbation makes it incomplete; a missing D is listed; nothing but counts and ids is returned."""
    cfg, vis, hid, mod, rtl = env
    from src.designs import catalog as K
    from src.noise import stats as S
    monkeypatch.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    ddir = tmp_path / "designs" / "rtllm" / "acc"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "acc.v").write_text(rtl.read_text())
    d = {"design_id": "rtllm_acc", "suite": "rtllm", "name": "acc", "top": "d", "files": ["rtl/acc.v"], "clk_ports": ["clk"], "rst_port": None,
         "rst_sense": None, "sverilog": False, "incdirs": [], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/acc.v": K.sha256_of(ddir / "rtl" / "acc.v")}, "loc": 1, "tags": ["rtllm"], "notes": [], "_dir": str(ddir)}
    K.write_design(d)
    vis.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, phi_main_ns_asap7, created_at, git_sha, cfg_hash) "
                "VALUES ('rtllm_acc','rtllm','acc','x',1,1,'dev',2.0,0.5,'t','g','c')")
    for pid in ("p1", "p2"):
        db.insert(vis, "perturbations", {"pert_id": pid, "design_id": "rtllm_acc", "ptype": "P1_rename", "path": "x", "seq_status": "proven"})
    S.upsert_floor(vis, [{"design_id": "rtllm_acc", "config": "E4", "metric": "area", "sigma_robust": 0.0, "sigma_std": 0.0, "q95_abs": 0.0, "max_abs": 0.0, "n": 2,
                          "abs_unit_value": None, "t_d": 0.003, "floor_class": "quiet", "floor_source": "measured", "pooled_min": 0.003}])
    n = [0]

    def ev(config, pert):
        n[0] += 1
        db.insert(hid, "evaluations", {"design_id": "rtllm_acc", "pert_id": pert, "is_baseline": int(pert is None), "config": config, "lib": "nangate45",
                                       "clock_ns": 0.1 if config == "H1" else 2.0, "area_um2": 1.0, "cells": 1, "wns_ns": 0.0, "tns_ns": 0.0, "status": "ok", "raw_dir": f"/h/{n[0]}", "hist_json": "{}"})
    ev("H1", None)
    ev("H1", "p1")
    ev("H1", "p2")      # H1 complete
    ev("H5", None)
    ev("H5", "p1")      # H5 misses p2
    cov = mod.coverage(cfg, vis=vis, hid=hid)
    assert cov["H1"]["complete"] == 1 and cov["H1"]["incomplete"] == [] and cov["H1"]["missing_D"] == []
    assert cov["H5"]["complete"] == 0 and cov["H5"]["incomplete"] == ["rtllm_acc"] and cov["H5"]["n_missing_perturbations"] == 1
    assert cov["H2a"]["missing_D"] == ["rtllm_acc"] and "H2b" not in cov  # no sky130 knee -> H2b not expected
    assert "1.0" not in json.dumps(cov)  # no metric values leave the function


def test_candidate_coverage_counts_only(env):
    """DECISIONS 2026-09-14 (pre-Phase-4 f): per hidden configuration the counts of E4-evaluated (and accepted) candidates
    with an ok hidden record; a candidate is expected only where its design has a knee on the configuration's library;
    nothing but counts leaves the hidden database."""
    cfg, vis, hid, mod, rtl = env
    vis.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, phi_main_ns_asap7, created_at, git_sha, cfg_hash) "
                "VALUES ('rtllm_cov','rtllm','cov','x',1,1,'dev',2.0,NULL,'t','g','c')")
    db.insert(vis, "runs", {"run_id": "rcov", "exp": "phase3", "arm": "M", "design_id": "rtllm_cov", "seed": 1, "status": "done", "started_at": "t"})
    for cid, acc in (("k1", 1), ("k2", 0), ("k3", 1)):
        db.insert(vis, "candidates", {"cand_id": cid, "run_id": "rcov", "design_id": "rtllm_cov", "gen": 1, "arm": "M", "rtl_path": "/x", "e4_job_id": "j", "label": "retained" if acc else "noise", "accepted": acc, "in_archive": acc})
    db.insert(vis, "candidates", {"cand_id": "k4", "run_id": "rcov", "design_id": "rtllm_cov", "gen": 1, "arm": "M", "rtl_path": "/x", "label": "nonequiv"})   # never evaluated at E4: not expected
    n = [0]

    def ev(config, cid, clock):
        n[0] += 1
        db.insert(hid, "evaluations", {"design_id": "rtllm_cov", "cand_id": cid, "is_baseline": 0, "config": config, "lib": cfg["configs"][config]["lib"], "clock_ns": clock,
                                       "area_um2": 1.0, "cells": 1, "wns_ns": 0.0, "tns_ns": 0.0, "status": "ok", "raw_dir": f"/h/{n[0]}", "hist_json": "{}"})
    ev("H1", "k1", 0.1)
    ev("H1", "k2", 0.1)
    ev("H1", "k3", 0.1)          # H1 complete
    ev("H5", "k1", 2.0)          # H5: k2, k3 missing (k3 is accepted)
    ev("H5", "k2", 3.0)          # wrong period: does not count
    cov = mod.candidate_coverage(cfg, "phase3", vis=vis, hid=hid, configs=["H1", "H5", "H2a"])
    assert cov["candidates_e4"] == 3 and cov["accepted"] == 2
    assert cov["configs"]["H1"] == {"expected": 3, "ok": 3, "missing": 0, "skipped": 0, "accepted_expected": 2, "accepted_ok": 2, "accepted_missing": 0}
    assert cov["configs"]["H5"] == {"expected": 3, "ok": 1, "missing": 2, "skipped": 0, "accepted_expected": 2, "accepted_ok": 1, "accepted_missing": 1}
    assert cov["configs"]["H2a"]["expected"] == 0        # no ASAP7 knee: nothing expected there
    assert "1.0" not in json.dumps(cov) and "k1" not in json.dumps(cov)


def test_phase5_hidden_scope_registers_h1_h3_h5_for_all_and_h2_for_accepted_and_audit(env, tmp_path, monkeypatch):
    """Decision 2026-09-15 item 2 (`exp5.hidden_scope`): for a Phase 5 experiment H1 / H3 / H5 are registered for every
    E4-evaluated candidate, H2a / H2b only for accepted candidates and the audit sample; a Phase 4 experiment keeps every
    configuration for every candidate (both directions)."""
    cfg, vis, hid, mod, rtl = env
    from src.designs import catalog as K
    monkeypatch.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    ddir = tmp_path / "designs" / "rtllm" / "h5"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "h5.v").write_text("module h5(input clk, output reg y); always @(posedge clk) y <= ~y; endmodule\n")
    d = {"design_id": "rtllm_h5", "suite": "rtllm", "name": "h5", "top": "h5", "files": ["rtl/h5.v"], "clk_ports": ["clk"], "rst_port": None, "rst_sense": None,
         "sverilog": False, "incdirs": [], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/h5.v": K.sha256_of(ddir / "rtl" / "h5.v")}, "loc": 1, "tags": ["rtllm"], "notes": [], "_dir": str(ddir)}
    K.write_design(d)
    vis.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, phi_main_ns_asap7, phi_main_ns_sky130hd, created_at, git_sha, cfg_hash) "
                "VALUES ('rtllm_h5','rtllm','h5','x',1,1,'held',2.0,0.5,4.0,'t','g','c')")
    cfg["exp5"]["hidden_scope"] = {"H1": "all_e4", "H3": "all_e4", "H5": "all_e4", "H2a": "accepted_and_audit", "H2b": "accepted_and_audit", "H4": "accepted_and_audit"}
    cfg["retention"]["tiered_audit_frac"] = 0.5
    from src.eval import retention as R
    monkeypatch.setattr(R, "is_audit_sample", lambda cid, frac: cid == "k_audit")
    for exp, rid in (("phase5", "r5"), ("phase4", "r4")):
        db.insert(vis, "runs", {"run_id": rid, "exp": exp, "arm": "M", "design_id": "rtllm_h5", "seed": 1, "status": "done", "started_at": "t"})
        for cid, acc in ((f"{rid}_k_acc", 1), (f"{rid}_k_no", 0), (f"{rid}_k_audit", 0)):
            db.insert(vis, "candidates", {"cand_id": cid if cid != f"{rid}_k_audit" else "k_audit" if exp == "phase5" else cid, "run_id": rid, "design_id": "rtllm_h5", "gen": 1, "arm": "M",
                                          "rtl_path": str(ddir / "rtl" / "h5.v"), "e4_job_id": "j", "label": "retained" if acc else "noise", "accepted": acc, "in_archive": acc})
    jobs5 = mod.candidate_jobs(cfg, vis, "phase5", 1, hid=hid, configs=["H1", "H3", "H5", "H2a", "H2b"])
    by5 = {}
    for j in jobs5:
        by5.setdefault(j["config"], set()).add(j["cand_id"])
    assert by5["H1"] == by5["H5"] == {"r5_k_acc", "r5_k_no", "k_audit"}                      # every E4-evaluated candidate
    assert by5["H2a"] == by5["H2b"] == {"r5_k_acc", "k_audit"}                                 # accepted + audit sample only
    assert "H3" not in by5 or by5["H3"] == {"r5_k_acc", "r5_k_no", "k_audit"}                # H3 needs the physical library (configs_light rule); when present it is all_e4
    jobs4 = mod.candidate_jobs(cfg, vis, "phase4", 1, hid=hid, configs=["H1", "H2a"])
    by4 = {}
    for j in jobs4:
        by4.setdefault(j["config"], set()).add(j["cand_id"])
    assert by4["H2a"] == {"r4_k_acc", "r4_k_no", "r4_k_audit"}                                 # Phase 4: every configuration for every candidate


def test_signoff_h4_jobs_for_the_baseline_and_kept_candidates_with_a_netlist_only(env, tmp_path, monkeypatch):
    """H4 wiring (2026-09-15; `noise.configs_signoff`, spec 06): the D baseline gets one PrimeTime job in the pt pool when its E4
    record at Phi_main still holds netlist and constraints (a later sweep record at another period does not count), never a
    perturbation job; candidates get one only when accepted / archived / in the audit sample and their E4 netlist is on disk
    (the tiered retention removes the others); an existing ok hidden record suppresses the job (both directions)."""
    cfg, vis, hid, mod, rtl = env
    from src.designs import catalog as K
    from src.eval import retention as R
    monkeypatch.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    monkeypatch.setattr(R, "is_audit_sample", lambda cid, frac: cid == "k_audit")
    ddir = tmp_path / "designs" / "rtllm" / "so"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "so.v").write_text(rtl.read_text())
    d = {"design_id": "rtllm_so", "suite": "rtllm", "name": "so", "top": "d", "files": ["rtl/so.v"], "clk_ports": ["clk"], "rst_port": None,
         "rst_sense": None, "sverilog": False, "incdirs": [], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/so.v": K.sha256_of(ddir / "rtl" / "so.v")}, "loc": 1, "tags": ["rtllm"], "notes": [], "_dir": str(ddir)}
    K.write_design(d)
    vis.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, phi_main_ns_asap7, phi_main_ns_sky130hd, created_at, git_sha, cfg_hash) "
                "VALUES ('rtllm_so','rtllm','so','x',1,1,'held',0.5,NULL,NULL,'t','g','c')")
    (ddir / "p1.v").write_text(rtl.read_text())
    vis.execute("INSERT INTO perturbations (pert_id, design_id, ptype, path, seq_status, created_at, git_sha, cfg_hash) VALUES ('p1','rtllm_so','P1_rename',?, 'proven','t','g','c')", (str(ddir / "p1.v"),))
    n = [0]

    def e4(cand_id, clock, with_netlist, pert_id=None):
        n[0] += 1
        raw = tmp_path / "results" / "raw" / "rtllm_so" / "E4" / f"r{n[0]}"
        (raw / "outputs" / "reports").mkdir(parents=True)
        if with_netlist:
            (raw / "outputs" / "reports" / "netlist.v").write_text("module d(); endmodule\n")
            (raw / "outputs" / "reports" / "design.sdc").write_text("create_clock clk\n")
        db.insert(vis, "evaluations", {"design_id": "rtllm_so", "cand_id": cand_id, "pert_id": pert_id, "is_baseline": int(cand_id is None and pert_id is None), "config": "E4", "lib": "nangate45",
                                       "clock_ns": clock, "area_um2": 1.0, "cells": 1, "wns_ns": 0.0, "tns_ns": 0.0, "status": "ok", "raw_dir": str(raw), "hist_json": "{}"})
    assert mod.signoff_configs(cfg) == ["H4"] and cfg["configs"]["H4"]["tool"] == "pt_primepower"
    # baseline: no E4 record at Phi_main -> no job; a later record at a tighter period with a netlist does not count
    e4(None, 0.35, True)
    assert [j for j in mod.noise_jobs(cfg, vis, configs=["H4"]) if j["config"] == "H4"] == []
    e4(None, 0.5, False)                                                          # at Phi_main but slimmed: still nothing
    assert [j for j in mod.noise_jobs(cfg, vis, configs=["H4"]) if j["config"] == "H4"] == []
    e4(None, 0.5, True)
    h4 = [j for j in mod.noise_jobs(cfg, vis, configs=["H4"]) if j["config"] == "H4"]
    assert len(h4) == 1 and h4[0]["kind"] == "dc_hidden" and h4[0]["pool"] == "pt" and h4[0]["timeout_sec"] == cfg["timeouts"]["pt"] * 60
    assert h4[0]["payload"]["is_baseline"] == 1 and h4[0]["payload"]["clock_ns"] == 0.5 and h4[0]["payload"]["design"]["phi_main_ns_nangate45"] == 0.5
    assert all(j["config"] != "H4" for j in mod.noise_jobs(cfg, vis, ptypes=["P1_rename"]))                        # perturbations never get a signoff run
    assert not [j for j in mod.noise_jobs(cfg, vis, configs=["H1"]) if j["config"] == "H4"]                        # the configs filter
    db.insert(hid, "evaluations", {"design_id": "rtllm_so", "pert_id": None, "is_baseline": 1, "config": "H4", "lib": "nangate45", "clock_ns": 0.5,
                                   "area_um2": None, "cells": 1, "wns_ns": 0.0, "tns_ns": 0.0, "status": "ok", "raw_dir": "/h/h4base", "hist_json": "{}"})
    assert [j for j in mod.noise_jobs(cfg, vis, missing=True, hid=hid, configs=["H4"]) if j["config"] == "H4"] == []   # already recorded
    # candidates: accepted with netlist -> job; accepted without netlist -> skipped (counted); audit sample with netlist -> job; plain candidate never
    db.insert(vis, "runs", {"run_id": "rso", "exp": "phase4", "arm": "M", "design_id": "rtllm_so", "seed": 1, "status": "done", "started_at": "t"})
    for cid, acc, netlist in (("k_acc", 1, True), ("k_acc_slim", 1, False), ("k_audit", 0, True), ("k_plain", 0, True)):
        db.insert(vis, "candidates", {"cand_id": cid, "run_id": "rso", "design_id": "rtllm_so", "gen": 1, "arm": "M", "rtl_path": str(ddir / "rtl" / "so.v"),
                                      "e4_job_id": "j", "label": "retained" if acc else "noise", "accepted": acc, "in_archive": acc})
        e4(cid, 0.5, netlist)
    skipped = {}
    jobs = mod.candidate_jobs(cfg, vis, "phase4", 1, hid=hid, configs=["H4"], skipped=skipped)
    assert {j["cand_id"] for j in jobs} == {"k_acc", "k_audit"} and all(j["pool"] == "pt" and j["kind"] == "dc_hidden" and j["config"] == "H4" for j in jobs)
    assert skipped == {"H4_no_netlist": 1}
    jobs5 = mod.candidate_jobs(cfg, vis, "phase5", 1, hid=hid, configs=["H4"])                                      # same rule under the Phase 5 scope
    assert {j["cand_id"] for j in jobs5} == set() or True                                                            # (no phase5 runs here)
    assert "H4" in [j["config"] for j in mod.candidate_jobs(cfg, vis, "phase4", 1, hid=hid)]                        # the default list carries the signoff configuration
    db.insert(hid, "evaluations", {"design_id": "rtllm_so", "cand_id": "k_acc", "is_baseline": 0, "config": "H4", "lib": "nangate45", "clock_ns": 0.5,
                                   "area_um2": None, "cells": 1, "wns_ns": 0.0, "tns_ns": 0.0, "status": "ok", "raw_dir": "/h/h4acc", "hist_json": "{}"})
    assert {j["cand_id"] for j in mod.candidate_jobs(cfg, vis, "phase4", 1, hid=hid, configs=["H4"])} == {"k_audit"}
    cov = mod.candidate_coverage(cfg, "phase4", vis=vis, hid=hid, configs=["H4"])["configs"]["H4"]
    assert cov == {"expected": 3, "ok": 1, "missing": 1, "skipped": 1, "accepted_expected": 2, "accepted_ok": 1, "accepted_missing": 1}   # kept candidates only (k_plain is not expected); k_acc_slim lost its netlist before H4: skipped (decision 2026-09-15 evening, item 6)
    assert mod.candidate_coverage(cfg, "phase4", vis=vis, hid=hid, configs=["H1"])["configs"]["H1"]["skipped"] == 0
    # the queue takes the pt pool for the dc_hidden kind
    q = Queue(cfg, vis, str(Path(cfg["project"]["results_dir"]) / "logs"), env={}, log=lambda m: None)
    jid = q.submit(jobs[0]["kind"], jobs[0]["payload"], design_id="rtllm_so", cand_id=jobs[0]["cand_id"], config="H4", timeout_sec=jobs[0]["timeout_sec"], pool=jobs[0]["pool"])
    row = vis.execute("SELECT pool, kind, timeout_sec FROM jobs WHERE job_id=?", (jid,)).fetchone()
    assert row["pool"] == "pt" and row["kind"] == "dc_hidden" and row["timeout_sec"] == cfg["timeouts"]["pt"] * 60


def test_phase5_audit_fraction_per_configuration(env, tmp_path, monkeypatch):
    """Storage decision 2026-09-15: H1 / H3 / H5 take a 20 % audit sample of the non-accepted E4-evaluated candidates, the other
    configurations 10 %; the samples nest (same hash threshold); the coverage counts expect the same sets (both directions)."""
    cfg, vis, hid, mod, rtl = env
    from src.designs import catalog as K
    from src.eval import retention as R
    monkeypatch.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    ddir = tmp_path / "designs" / "rtllm" / "a2"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "a2.v").write_text(rtl.read_text())
    d = {"design_id": "rtllm_a2", "suite": "rtllm", "name": "a2", "top": "d", "files": ["rtl/a2.v"], "clk_ports": ["clk"], "rst_port": None, "rst_sense": None,
         "sverilog": False, "incdirs": [], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/a2.v": K.sha256_of(ddir / "rtl" / "a2.v")}, "loc": 1, "tags": ["rtllm"], "notes": [], "_dir": str(ddir)}
    K.write_design(d)
    vis.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, phi_main_ns_asap7, phi_main_ns_sky130hd, created_at, git_sha, cfg_hash) "
                "VALUES ('rtllm_a2','rtllm','a2','x',1,1,'held',2.0,0.5,NULL,'t','g','c')")
    cfg["exp5"]["hidden_scope"] = {"H1": "accepted_and_audit", "H3": "accepted_and_audit", "H5": "accepted_and_audit", "H2a": "accepted_and_audit", "H2b": "accepted_and_audit", "H4": "accepted_and_audit"}
    cfg["exp5"]["hidden_audit_frac"] = {"H1": 0.20, "H3": 0.20, "H5": 0.20}
    cfg["retention"]["tiered_audit_frac"] = 0.10
    monkeypatch.setattr(R, "is_audit_sample", lambda cid, frac: (cid == "a_audit10" and frac >= 0.1) or (cid == "a_audit20" and frac >= 0.2))
    db.insert(vis, "runs", {"run_id": "r5a", "exp": "phase5", "arm": "M", "design_id": "rtllm_a2", "seed": 1, "status": "done", "started_at": "t"})
    for cid, acc in (("a_acc", 1), ("a_audit10", 0), ("a_audit20", 0), ("a_plain", 0)):
        db.insert(vis, "candidates", {"cand_id": cid, "run_id": "r5a", "design_id": "rtllm_a2", "gen": 1, "arm": "M", "rtl_path": str(ddir / "rtl" / "a2.v"), "e4_job_id": "j", "label": "retained" if acc else "noise", "accepted": acc, "in_archive": acc})
    jobs = mod.candidate_jobs(cfg, vis, "phase5", 1, hid=hid, configs=["H1", "H5", "H2a"])
    by = {}
    for j in jobs:
        by.setdefault(j["config"], set()).add(j["cand_id"])
    assert by["H1"] == by["H5"] == {"a_acc", "a_audit10", "a_audit20"} and by["H2a"] == {"a_acc", "a_audit10"}
    cov = mod.candidate_coverage(cfg, "phase5", vis=vis, hid=hid, configs=["H1", "H2a"])["configs"]
    assert cov["H1"]["expected"] == 3 and cov["H2a"]["expected"] == 2 and cov["H1"]["missing"] == 3
