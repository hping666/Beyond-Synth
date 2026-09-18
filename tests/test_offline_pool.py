"""Offline evaluation pool (DECISION 2026-09-18 item 1): scope, sim -> E4 chaining, throttle, priority below every search job."""
import copy
import importlib.util
import json
from pathlib import Path

from src import config as C
from src.db import core as db


def load_pool():
    spec = importlib.util.spec_from_file_location("offline_pool", str(Path(C.ROOT) / "scripts" / "offline_pool.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_scope_chaining_and_throttle(tmp_path, monkeypatch):
    mod = load_pool()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": ["L1"], "medium": ["M1"], "small": []}
    cfg["offline_pool"] = {"slots": 2, "priority": 1, "load_over_baseline": 0.10, "vcf_wait_q95_max_min": 20.0}
    monkeypatch.setattr(mod, "STATE", str(tmp_path / "state.json"))
    monkeypatch.setattr(mod, "LOG", str(tmp_path / "pool.log"))
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('L1','x','l1','p',1,1,'held',1.0,'t','g','c')")
    db.insert(conn, "runs", {"run_id": "rb0", "exp": "phase5", "arm": "B0", "design_id": "L1", "seed": 1, "llm_model": "gpt-5.6-terra", "status": "done", "started_at": "t"})
    db.insert(conn, "runs", {"run_id": "rm", "exp": "phase5", "arm": "M", "design_id": "L1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    db.insert(conn, "runs", {"run_id": "rmed", "exp": "phase5", "arm": "B0", "design_id": "M1", "seed": 1, "llm_model": "gpt-5.6-terra", "status": "done", "started_at": "t"})
    rtl = tmp_path / "c.v"; rtl.write_text("module l1(input clk, output reg y); always @(posedge clk) y <= ~y; endmodule\n")
    db.insert(conn, "candidates", {"cand_id": "b0_proven", "run_id": "rb0", "design_id": "L1", "gen": 1, "arm": "B0", "rtl_path": str(rtl), "verdict": "proven", "label": "improved"})
    db.insert(conn, "candidates", {"cand_id": "b0_with_e4", "run_id": "rb0", "design_id": "L1", "gen": 1, "arm": "B0", "rtl_path": str(rtl), "verdict": "proven", "label": "improved"})
    db.insert(conn, "evaluations", {"design_id": "L1", "cand_id": "b0_with_e4", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 1.0, "status": "ok", "raw_dir": "/x/e4", "dc_seconds": 120.0})
    db.insert(conn, "candidates", {"cand_id": "b0_falsified", "run_id": "rb0", "design_id": "L1", "gen": 1, "arm": "B0", "rtl_path": str(rtl), "verdict": "falsified", "label": "nonequiv"})
    db.insert(conn, "candidates", {"cand_id": "m_pre", "run_id": "rm", "design_id": "L1", "gen": 1, "arm": "M", "rtl_path": str(rtl), "prescreened": 1, "label": "prescreened"})
    db.insert(conn, "candidates", {"cand_id": "m_timeout", "run_id": "rm", "design_id": "L1", "gen": 1, "arm": "M", "rtl_path": str(rtl), "verdict": "proven", "label": None, "note": "[E4 evaluation failed]"})
    db.insert(conn, "candidates", {"cand_id": "med_b0", "run_id": "rmed", "design_id": "M1", "gen": 1, "arm": "B0", "rtl_path": str(rtl), "verdict": "proven", "label": "improved"})
    items = {it["cand_id"]: it["group"] for it in mod.scope(cfg, conn)}
    assert items == {"b0_proven": "b0_e4", "m_pre": "prescreened"}                          # large tier only; existing E4 records, unproven B0 and the timeout skipped
    assert {it["cand_id"]: it["group"] for it in mod.scope(cfg, conn, include_e4_timeouts=True)}["m_timeout"] == "e4_timeout"
    assert mod.projection(cfg, conn, mod.scope(cfg, conn))["b0_e4"] == 120.0 / 3600
    # one pass: the design catalog and the queue are stubbed; the sim goes first for the prescreened one, E4 at once for B0, both at priority 1 below the search's 4
    from src.designs import catalog as K
    monkeypatch.setattr(K, "load_all", lambda: [{"design_id": "L1", "top": "l1", "files": ["c.v"], "incdirs": [], "clk_ports": ["clk"], "rst_port": None, "rst_sense": None, "sverilog": False, "loc": 1, "_dir": str(tmp_path)}])
    monkeypatch.setattr(K, "abs_paths", lambda d, paths: [tmp_path / p for p in paths])
    from src.jobqueue.core import Queue
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={}, log=lambda m: None)
    monkeypatch.setattr(mod, "load1", lambda: 100.0)
    st = mod.load_state(); st["baseline"] = 100.0
    counts = mod.once(cfg, conn, st, queue=q)
    assert counts == {"sim_running": 1, "e4_running": 1}
    jobs = {r["cand_id"]: dict(r) for r in conn.execute("SELECT * FROM jobs")}
    assert jobs["m_pre"]["kind"] == "sim" and jobs["m_pre"]["pool"] == "local" and json.loads(jobs["m_pre"]["payload_json"])["prescreened_offline"] is True
    assert jobs["b0_proven"]["kind"] == "dc" and jobs["b0_proven"]["priority"] == 1 < cfg["search"]["job_priority"] and json.loads(jobs["b0_proven"]["payload_json"])["offline_eval"] == 1
    # throttle: load above baseline + 10 % pauses (logged), back below resumes (logged); a long medium-tier VC Formal wait pauses too
    monkeypatch.setattr(mod, "load1", lambda: 111.0)
    assert mod.throttle(cfg, conn, st)[0] is False and st["paused"] and "PAUSE" in open(tmp_path / "pool.log").read()
    monkeypatch.setattr(mod, "load1", lambda: 105.0)
    assert mod.throttle(cfg, conn, st)[0] is True and not st["paused"] and "RESUME" in open(tmp_path / "pool.log").read()
    monkeypatch.setattr(mod, "medium_vcf_wait_q95", lambda cfg_, conn_, hours=1.0: 25.0)
    assert mod.throttle(cfg, conn, st)[0] is False
    # a paused pool submits nothing
    st["cands"]["extra"] = {"cand_id": "extra", "group": "b0_e4", "run_id": "rb0", "design_id": "L1", "rtl_path": str(rtl), "model": "m", "arm": "B0", "stage": "e4", "sim_job": None, "e4_job": None, "result": None}
    counts = mod.once(cfg, conn, st, queue=q)
    assert counts["e4"] == 1 and st["paused"]
    # the sim finished with V2 passing -> the E4 follows with the record's SAIF; a rejected sim ends the candidate
    monkeypatch.setattr(mod, "medium_vcf_wait_q95", lambda cfg_, conn_, hours=1.0: 0.0)
    conn.execute("UPDATE jobs SET state='done' WHERE cand_id='m_pre'"); conn.commit()
    monkeypatch.setattr(mod, "sim_record", lambda cfg_, pl: {"verdict": "not_run", "v1_status": "ok", "v2_status": "identical", "saif_c": str(rtl)})
    counts = mod.once(cfg, conn, st, queue=q)
    assert st["cands"]["m_pre"]["stage"] == "e4_running" and json.loads(conn.execute("SELECT payload_json FROM jobs WHERE cand_id='m_pre' AND kind='dc'").fetchone()[0])["saif"] == str(rtl)
    st["cands"]["m_pre"].update(stage="sim_running")
    monkeypatch.setattr(mod, "sim_record", lambda cfg_, pl: {"verdict": "rejected", "v1_status": "rejected", "v2_status": None})
    mod.once(cfg, conn, st, queue=q)
    assert st["cands"]["m_pre"]["stage"] == "done" and st["cands"]["m_pre"]["result"].startswith("rejected")
