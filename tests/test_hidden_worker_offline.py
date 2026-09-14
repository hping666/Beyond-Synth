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
