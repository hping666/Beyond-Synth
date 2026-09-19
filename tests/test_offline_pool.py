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
    cfg["offline_pool"] = {"slots": 3, "priority": 1, "load_over_baseline": 0.10, "vcf_wait_q95_max_min": 20.0}
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
    assert items == {"b0_proven": "b0_e4", "m_pre": "prescreened", "med_b0": "b0_e4", "m_timeout": "e4_late"}   # every tier's finished B0 runs (DECISION (d) B5); existing E4 records and unproven B0 skipped; a proven candidate without any E4 attempt: e4_late ((m) 3)
    assert [it["cand_id"] for it in mod.scope(cfg, conn)] == ["med_b0", "m_timeout", "b0_proven", "m_pre"]   # (m) 1: medium B0 first, then the E4 gaps, then large B0, then prescreened
    db.insert(conn, "evaluations", {"design_id": "L1", "cand_id": "m_timeout", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "status": "eval_failed", "raw_dir": "/x/t", "dc_seconds": 1020.0})
    assert {it["cand_id"]: it["group"] for it in mod.scope(cfg, conn, include_e4_timeouts=True)}["m_timeout"] == "e4_timeout"   # a failed attempt on record: retry with the long guard
    conn.execute("DELETE FROM evaluations WHERE cand_id='m_timeout'"); conn.commit()
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
    assert counts == {"sim_running": 1, "e4_running": 2, "done": 1}   # the medium-tier B0 candidate is in scope (DECISION (d) B5) and, with M1 absent from the stubbed catalog, ends at once; the E4 gap gets its E4
    jobs = {r["cand_id"]: dict(r) for r in conn.execute("SELECT * FROM jobs")}
    assert jobs["m_pre"]["kind"] == "sim" and jobs["m_pre"]["pool"] == "local" and json.loads(jobs["m_pre"]["payload_json"])["prescreened_offline"] is True
    assert jobs["b0_proven"]["kind"] == "dc" and jobs["b0_proven"]["priority"] == 1 < cfg["search"]["job_priority"] and json.loads(jobs["b0_proven"]["payload_json"])["offline_eval"] == 1
    # throttle: load above baseline + 10 % pauses (logged), back below resumes (logged); a long medium-tier VC Formal wait pauses too
    monkeypatch.setattr(mod, "load1", lambda: 111.0)
    assert mod.throttle(cfg, conn, st)[0] is False and st["paused"] and "PAUSE" in open(tmp_path / "pool.log").read()
    monkeypatch.setattr(mod, "load1", lambda: 105.0)
    assert mod.throttle(cfg, conn, st)[0] is True and not st["paused"] and "RESUME" in open(tmp_path / "pool.log").read()
    monkeypatch.setattr(mod, "medium_vcf_wait_q95", lambda cfg_, conn_, hours=1.0: 25.0)
    assert mod.throttle(cfg, conn, st)[0] is True                                            # DECISION 2026-09-18 (b) item 3: load only; the VC Formal wait is logged, not applied
    monkeypatch.setattr(mod, "load1", lambda: 140.0)
    assert mod.throttle(cfg, conn, st)[0] is False
    # a paused pool submits nothing
    st["cands"]["extra"] = {"cand_id": "extra", "group": "b0_e4", "run_id": "rb0", "design_id": "L1", "rtl_path": str(rtl), "model": "m", "arm": "B0", "stage": "e4", "sim_job": None, "e4_job": None, "result": None}
    counts = mod.once(cfg, conn, st, queue=q)
    assert counts["e4"] == 1 and st["paused"]
    # the sim finished with V2 passing -> the E4 follows with the record's SAIF; a rejected sim ends the candidate
    monkeypatch.setattr(mod, "load1", lambda: 100.0)
    monkeypatch.setattr(mod, "medium_vcf_wait_q95", lambda cfg_, conn_, hours=1.0: 0.0)
    conn.execute("UPDATE jobs SET state='done' WHERE cand_id='m_pre'"); conn.commit()
    monkeypatch.setattr(mod, "sim_record", lambda cfg_, pl: {"verdict": "not_run", "v1_status": "ok", "v2_status": "identical", "saif_c": str(rtl)})
    counts = mod.once(cfg, conn, st, queue=q)
    assert st["cands"]["m_pre"]["stage"] == "e4_running" and json.loads(conn.execute("SELECT payload_json FROM jobs WHERE cand_id='m_pre' AND kind='dc'").fetchone()[0])["saif"] == str(rtl)
    st["cands"]["m_pre"].update(stage="sim_running")
    monkeypatch.setattr(mod, "sim_record", lambda cfg_, pl: {"verdict": "rejected", "v1_status": "rejected", "v2_status": None})
    mod.once(cfg, conn, st, queue=q)
    assert st["cands"]["m_pre"]["stage"] == "done" and st["cands"]["m_pre"]["result"].startswith("rejected")


def test_e4_timeout_reruns_get_the_long_guard_and_the_flag(tmp_path, monkeypatch):
    """DECISION 2026-09-18 (b) item 4: a timeout re-run's E4 job carries e4_rerun = 1 and a 3600 s guard (+ margin); a B0 job keeps the design's timeout."""
    mod = load_pool()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('L1','x','l1','p',1,1,'held',1.0,'t','g','c')")
    from src.designs import catalog as K
    monkeypatch.setattr(K, "abs_paths", lambda d, paths: [tmp_path / p for p in paths])
    design = {"design_id": "L1", "top": "l1", "files": ["c.v"], "incdirs": [], "clk_ports": ["clk"], "sverilog": False, "loc": 1}
    j = mod.e4_job(cfg, conn, design, {"cand_id": "x", "group": "e4_timeout", "design_id": "L1", "rtl_path": str(tmp_path / "c.v")})
    assert j["payload"]["e4_rerun"] == 1 and j["payload"]["force_rerun"] is True and j["timeout_sec"] == 3600 + 180 and "offline_eval" not in j["payload"]
    j2 = mod.e4_job(cfg, conn, design, {"cand_id": "y", "group": "b0_e4", "design_id": "L1", "rtl_path": str(tmp_path / "c.v")})
    assert j2["payload"]["offline_eval"] == 1 and "e4_rerun" not in j2["payload"] and j2["timeout_sec"] != 3600 + 180


def test_sync_candidate_row_both_directions(tmp_path):
    """DECISION 2026-09-18 D2: the offline simulation's outcome is written into the prescreened candidate's row — a passed
    simulation leaves the verdict NULL (proof pending) and records V1 / V2; a failed one records the verdict; a row that
    already carries a V2 status is never overwritten."""
    mod = load_pool()
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    db.insert(conn, "runs", {"run_id": "rm", "exp": "phase5", "arm": "M", "design_id": "L1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    for cid in ("cp", "cf", "cx"):
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": "rm", "design_id": "L1", "gen": 1, "arm": "M", "llm_model": "gpt-5.6-luna", "label": "prescreened", "note": "n"})
    assert mod.sync_candidate_row(conn, "cp", {"verdict": "not_run", "v1_status": "ok", "v2_status": "identical", "v2_cycles": 20000}, "js1")
    row = dict(conn.execute("SELECT * FROM candidates WHERE cand_id='cp'").fetchone())
    assert row["verdict"] is None and row["v1_status"] == "ok" and row["v2_status"] == "identical" and row["v2_cycles"] == 20000 and row["eq_job_id"] == "js1" and "proof pending" in row["note"]
    assert not mod.sync_candidate_row(conn, "cp", {"verdict": "rejected", "v1_status": "rejected", "v2_status": "compile_failed"}, "js9")   # idempotent: never overwritten
    assert dict(conn.execute("SELECT * FROM candidates WHERE cand_id='cp'").fetchone())["v2_status"] == "identical"
    assert mod.sync_candidate_row(conn, "cf", {"verdict": "rejected", "v1_status": "rejected", "v2_status": "compile_failed"}, "js2")
    row = dict(conn.execute("SELECT * FROM candidates WHERE cand_id='cf'").fetchone())
    assert row["verdict"] == "rejected" and row["v2_status"] == "compile_failed" and "rejected" in row["note"]
    assert conn.execute("SELECT count(*) FROM candidates WHERE v2_status IS NULL").fetchone()[0] == 1                            # cx untouched


def test_b0_scope_covers_every_tier_in_order_and_idle_seats_widen_the_pool(tmp_path, monkeypatch):
    """DECISION 2026-09-18 (d) B5: proven B0 candidates of every finished run, large first (with the prescreened group), then
    medium, then small — a running run's candidates wait until it finishes; with more than 12 idle DC seats the pool may use 12
    slots instead of 8. Both directions."""
    mod = load_pool()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": ["L1"], "medium": ["M1"], "small": ["S1"]}
    cfg["offline_pool"] = {"slots": 8, "priority": 1, "load_over_baseline": 0.10}
    cfg["queue"]["dc_seats_target"] = 30
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    for d in ("L1", "M1", "S1"):
        conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES (?,'x',?,'p',1,1,'held',1.0,'t','g','c')", (d, d))
    rtl = tmp_path / "c.v"; rtl.write_text("module m; endmodule")
    for rid, d, status in (("rl", "L1", "done"), ("rm", "M1", "done"), ("rs", "S1", "done"), ("rm_run", "M1", "running")):
        db.insert(conn, "runs", {"run_id": rid, "exp": "phase5", "arm": "B0", "design_id": d, "seed": 1, "llm_model": "gpt-5.6-luna", "status": status, "started_at": "t"})
        db.insert(conn, "candidates", {"cand_id": f"c_{rid}", "run_id": rid, "design_id": d, "gen": 1, "arm": "B0", "rtl_path": str(rtl), "verdict": "proven"})
    items = [(it["cand_id"], it["group"], it.get("tier")) for it in mod.scope(cfg, conn)]
    assert items == [("c_rm", "b0_e4", "medium"), ("c_rl", "b0_e4", "large"), ("c_rs", "b0_e4", "small")]   # every tier; medium first (DECISION 2026-09-19 (m) 1); the running run's candidate not yet
    conn.execute("UPDATE runs SET status='done' WHERE run_id='rm_run'"); conn.commit()
    assert [it["cand_id"] for it in mod.scope(cfg, conn)] == ["c_rm", "c_rm_run", "c_rl", "c_rs"]
    # the slot rule: 8 slots while 12 or fewer DC seats idle, 12 when more are idle
    st = {"cands": {}, "paused": False, "baseline": 100.0}
    monkeypatch.setattr(mod, "STATE", str(tmp_path / "state.json")); monkeypatch.setattr(mod, "LOG", str(tmp_path / "pool.log"))
    monkeypatch.setattr(mod, "throttle", lambda cfg, conn, st: (False, 50.0, 0.0))    # paused: nothing submitted, the slot count is still computed
    for k in range(20):
        db.insert(conn, "jobs", {"job_id": f"dc{k}", "kind": "dc", "pool": "dc", "design_id": "L1", "state": "running", "priority": 0, "payload_json": "{}", "submitted_at": "t", "started_at": "t"})
    mod.once(cfg, conn, st, False)
    assert st["slots_now"] == 8                                          # 30 - 20 = 10 idle seats: not more than 12
    conn.execute("UPDATE jobs SET state='done' WHERE job_id IN ('dc0','dc1','dc2','dc3','dc4','dc5','dc6','dc7','dc8','dc9')"); conn.commit()
    mod.once(cfg, conn, st, False)
    assert st["slots_now"] == 12                                         # 20 idle seats: the pool may use 12 (the default)
    cfg["offline_pool"]["slots_when_idle"] = 16                          # DECISION 2026-09-19 (m) 1
    mod.once(cfg, conn, st, False)
    assert st["slots_now"] == 16


def test_reverify_group_sim_then_e4_then_awaits_the_proof(tmp_path, monkeypatch):
    """DECISION 2026-09-18 (d) D2: the stored candidates of runs superseded by the harness fix are re-simulated (force_rerun where the
    record hash did not change) and, on a pass, evaluated at E4 under the C1-map flag; the proof waits (await_proof) while the pool's
    proofs are disabled; duplicates, aborted rows and prescreened candidates (their own group) stay out; the v1 row is not rewritten."""
    mod = load_pool()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": ["L1"], "medium": ["drrtl_simple_spi"], "small": []}
    cfg["offline_pool"] = {"slots": 4, "priority": 1, "load_over_baseline": 0.10, "reverify_force_rerun": ["drrtl_simple_spi"], "proofs_enabled": False}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('drrtl_simple_spi','drrtl','simple_spi','p',1,1,'held',1.0,'t','g','c')")
    rtl = tmp_path / "c.v"; rtl.write_text("module m; endmodule")
    db.insert(conn, "runs", {"run_id": "r_sup", "exp": "phase5", "arm": "B2", "design_id": "drrtl_simple_spi", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "superseded", "started_at": "t", "superseded_reason": "harness_fix"})
    db.insert(conn, "runs", {"run_id": "r_other", "exp": "phase5", "arm": "B2", "design_id": "drrtl_simple_spi", "seed": 2, "llm_model": "gpt-5.6-luna", "status": "superseded", "started_at": "t", "superseded_reason": "duplicate driver"})
    db.insert(conn, "candidates", {"cand_id": "c_rej", "run_id": "r_sup", "design_id": "drrtl_simple_spi", "gen": 1, "arm": "B2", "rtl_path": str(rtl), "verdict": "rejected", "label": "nonequiv", "v1_status": "rejected", "v2_status": "compile_failed"})
    db.insert(conn, "candidates", {"cand_id": "c_dup", "run_id": "r_sup", "design_id": "drrtl_simple_spi", "gen": 1, "arm": "B2", "rtl_path": str(rtl), "label": "duplicate"})
    db.insert(conn, "candidates", {"cand_id": "c_pre", "run_id": "r_sup", "design_id": "drrtl_simple_spi", "gen": 1, "arm": "B2", "rtl_path": str(rtl), "label": "prescreened", "prescreened": 1})
    db.insert(conn, "candidates", {"cand_id": "c_oth", "run_id": "r_other", "design_id": "drrtl_simple_spi", "gen": 1, "arm": "B2", "rtl_path": str(rtl), "verdict": "rejected"})
    items = {it["cand_id"]: it for it in mod.scope(cfg, conn)}
    assert set(items) == {"c_rej", "c_pre"} and items["c_rej"]["group"] == "reverify" and items["c_rej"]["force_rerun"] is True and items["c_pre"]["group"] == "prescreened"
    monkeypatch.setattr(mod, "STATE", str(tmp_path / "state.json")); monkeypatch.setattr(mod, "LOG", str(tmp_path / "pool.log"))
    monkeypatch.setattr(mod, "throttle", lambda cfg, conn, st: (True, 50.0, 0.0))
    monkeypatch.setattr("src.designs.catalog.load_all", lambda: [{"design_id": "drrtl_simple_spi", "top": "simple_spi_top", "files": ["rtl/simple_spi.v"], "clk_ports": ["clk_i"], "rst_port": "rst_i", "rst_sense": "low", "incdirs": ["rtl"], "_dir": str(Path(C.ROOT) / "data/designs/drrtl/simple_spi"), "sverilog": False}])
    submitted = {}
    class FakeQ:
        def submit(self, kind, payload, **kw):
            jid = f"j_{len(submitted)}"; submitted[jid] = (kind, payload, kw); return jid
        def get(self, jid):
            return {"state": "done"} if jid in submitted else None
    st = {"cands": {}, "paused": False, "baseline": 100.0}
    mod.once(cfg, conn, st, False, queue=FakeQ())
    sim = [v for v in submitted.values() if v[0] == "sim" and v[1]["cand_id"] == "c_rej"]
    assert len(sim) == 1 and sim[0][1]["reverify"] is True and sim[0][1]["force_rerun"] is True
    pre = [v for v in submitted.values() if v[0] == "sim" and v[1]["cand_id"] == "c_pre"]
    assert len(pre) == 1 and pre[0][1]["reverify"] is False and pre[0][1]["prescreened_offline"] is True   # the prescreened candidate of the superseded run keeps its own group
    assert st["cands"]["c_rej"]["stage"] == "sim_running"
    monkeypatch.setattr(mod, "sim_record", lambda cfg, payload: {"verdict": "not_run", "v1_status": "ok", "v2_status": "identical", "v2_cycles": 20000, "saif_c": None})
    mod.once(cfg, conn, st, False, queue=FakeQ())
    assert st["cands"]["c_rej"]["stage"] == "e4_running"
    e4 = [v for v in submitted.values() if v[0] == "dc"]
    assert e4 and e4[-1][1]["reverify"] == 1 and e4[-1][1]["offline_eval"] == 1
    row = dict(conn.execute("SELECT verdict, v2_status FROM candidates WHERE cand_id='c_rej'").fetchone())
    assert row == {"verdict": "rejected", "v2_status": "compile_failed"}                              # the harness-version-1 row stays (C4)
    db.insert(conn, "evaluations", {"design_id": "drrtl_simple_spi", "cand_id": "c_rej", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 1.0, "status": "ok", "raw_dir": "/x/r", "dc_seconds": 10})
    monkeypatch.setattr("src.eval.retention.slim_candidate", lambda *a, **k: {"kept_full": False, "freed": {}})
    mod.once(cfg, conn, st, False, queue=FakeQ())
    assert st["cands"]["c_rej"]["stage"] == "await_proof"                                          # the proof waits for the pool's proofs to be enabled


def test_reproof_group_resubmits_the_failed_proof_and_writes_the_row(tmp_path, monkeypatch):
    """2026-09-18 11:2x: a candidate whose proof job failed for an operator cause (note "[reproof pending") is re-proven by the pool
    from the failed job's payload — regardless of proofs_enabled — the verdict is written into its row, and a proven candidate goes on
    to E4; a candidate without the marker, or without a failed proof job, is not touched. Both directions."""
    mod = load_pool()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": [], "medium": ["drrtl_SPI"], "small": []}
    cfg["offline_pool"] = {"slots": 4, "priority": 1, "load_over_baseline": 0.10, "proofs_enabled": False}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('drrtl_SPI','drrtl','SPI','p',1,1,'held',1.0,'t','g','c')")
    rtl = tmp_path / "c.v"; rtl.write_text("module m; endmodule")
    db.insert(conn, "runs", {"run_id": "r1", "exp": "phase5", "arm": "M", "design_id": "drrtl_SPI", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "running", "started_at": "t"})
    db.insert(conn, "candidates", {"cand_id": "c_err", "run_id": "r1", "design_id": "drrtl_SPI", "gen": 1, "arm": "M", "rtl_path": str(rtl), "verdict": "error", "v3_status": "error", "note": "n [reproof pending: x]"})
    db.insert(conn, "candidates", {"cand_id": "c_err2", "run_id": "r1", "design_id": "drrtl_SPI", "gen": 1, "arm": "M", "rtl_path": str(rtl), "verdict": "error", "v3_status": "error", "note": "n"})
    payload = {"design_id": "drrtl_SPI", "cand_id": "c_err", "d_rtl": [str(rtl)], "c_rtl": [str(rtl)], "top": "m", "clk": "clk", "rst": None, "rst_sense": None, "sim_record": {"v1_status": "ok"}}
    db.insert(conn, "jobs", {"job_id": "jf", "kind": "vcf", "pool": "vcf", "design_id": "drrtl_SPI", "cand_id": "c_err", "state": "failed", "priority": 6, "payload_json": json.dumps(payload), "submitted_at": "t", "finished_at": "t", "exit_code": 1})
    items = {it["cand_id"]: it for it in mod.scope(cfg, conn)}
    assert set(items) == {"c_err"} and items["c_err"]["group"] == "reproof" and items["c_err"]["proof_payload"]["cand_id"] == "c_err"   # c_err2 has no marker
    monkeypatch.setattr(mod, "STATE", str(tmp_path / "state.json")); monkeypatch.setattr(mod, "LOG", str(tmp_path / "pool.log"))
    monkeypatch.setattr(mod, "throttle", lambda cfg, conn, st: (True, 50.0, 0.0))
    monkeypatch.setattr("src.designs.catalog.load_all", lambda: [{"design_id": "drrtl_SPI", "top": "m", "files": ["c.v"], "clk_ports": ["clk"], "rst_port": None, "rst_sense": None, "incdirs": [], "_dir": str(tmp_path), "sverilog": False}])
    monkeypatch.setattr("src.designs.catalog.abs_paths", lambda d, paths: [tmp_path / p for p in paths])
    submitted = {}
    class FakeQ:
        def submit(self, kind, payload, **kw):
            jid = f"j_{len(submitted)}"; submitted[jid] = (kind, payload, kw); return jid
        def get(self, jid):
            return {"state": "done"} if jid in submitted else None
    st = {"cands": {}, "paused": False, "baseline": 100.0}
    mod.once(cfg, conn, st, False, queue=FakeQ())
    proofs = [v for v in submitted.values() if v[0] == "vcf"]
    assert len(proofs) == 1 and proofs[0][1]["cand_id"] == "c_err" and proofs[0][1]["sim_record"] == {"v1_status": "ok"} and proofs[0][2]["priority"] == 8   # resubmitted although proofs_enabled is false
    assert st["cands"]["c_err"]["stage"] == "proof_running"
    monkeypatch.setattr(mod, "proof_record", lambda cfg, payload: {"verdict": "proven", "v3_status": "proven", "v3_seconds": 12.0, "proven_by": "seq", "harness_version": 1, "saif_c": None})
    mod.once(cfg, conn, st, False, queue=FakeQ())
    row = dict(conn.execute("SELECT verdict, v3_status, harness_version, note FROM candidates WHERE cand_id='c_err'").fetchone())
    assert row["verdict"] == "proven" and row["v3_status"] == "proven" and row["harness_version"] == 1 and "re-proven" in row["note"]
    assert st["cands"]["c_err"]["stage"] == "e4_running" and [v for v in submitted.values() if v[0] == "dc"][-1][1]["reproof"] == 1   # proven -> E4 with the reproof flag
    assert dict(conn.execute("SELECT verdict FROM candidates WHERE cand_id='c_err2'").fetchone())["verdict"] == "error"                   # untouched


def test_pool_slims_its_simulation_records(tmp_path, monkeypatch):
    """2026-09-18 19:5x: the VCS build of a pool simulation record (simv, csrc, daidir) is removed once the result is read (a record whose
    SAIF is still needed for E4 is slimmed after E4); the parsed record stays. Both directions."""
    mod = load_pool()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    payload = {"design_id": "D1", "d_rtl": [str(tmp_path / "d.v")], "c_rtl": [str(tmp_path / "c.v")], "top": "t", "clk": "clk", "rst": None, "rst_sense": None}
    (tmp_path / "d.v").write_text("module t; endmodule"); (tmp_path / "c.v").write_text("module t; endmodule")
    from src.equiv.run_equiv import equiv_extra, equiv_hash
    h = equiv_hash(payload["d_rtl"], payload["c_rtl"], "t", cfg, equiv_extra(cfg, payload, False))
    rec = tmp_path / "results" / "raw" / "D1" / "EQ" / h
    (rec / "v2_sim" / "csrc").mkdir(parents=True); (rec / "v2_sim" / "csrc" / "x.o").write_bytes(b"0" * 1000)
    (rec / "v2_sim" / "simv").write_bytes(b"0" * 1000); (rec / "v2_sim" / "simv.daidir").mkdir(); (rec / "v2_sim" / "simv.daidir" / "a").write_bytes(b"0" * 100)
    (rec / "equiv.json").write_text(json.dumps({"verdict": "not_run", "v1_status": "ok", "v2_status": "identical"}))
    assert mod.sim_record_dir(cfg, payload) == rec
    res = mod.slim_sim_record(cfg, payload)
    assert not (rec / "v2_sim" / "simv").exists() and not (rec / "v2_sim" / "csrc").exists() and (rec / "equiv.json").exists() and res is not None
    assert mod.sim_record_dir(cfg, {**payload, "top": "other"}) is None and mod.slim_sim_record(cfg, {**payload, "top": "other"}) is None   # no record: nothing to slim


def test_resim_group_runs_sim_then_e4_and_proof_in_parallel_and_writes_the_row(tmp_path, monkeypatch):
    """DECISION 2026-09-19 (m) 2: a candidate marked "[resim pending" whose sim job failed is re-simulated from the failed job's payload at
    the run pipeline's priority (first in the pool's order); a passing simulation clears the nonequiv label, submits E4 and the proof
    in parallel (the proof at the run's proof priority, with the sim record), and the proof's verdict is written into the row; a
    failing simulation writes the verdict and keeps nonequiv. Both directions."""
    mod = load_pool()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": [], "medium": ["drrtl_arm_cpu2"], "small": []}
    cfg["offline_pool"] = {"slots": 4, "priority": 1, "load_over_baseline": 0.10, "proofs_enabled": False}
    cfg["search"]["job_priority"] = 4; cfg["search"].setdefault("early", {})["priority_undiagnosed"] = 2
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('drrtl_arm_cpu2','drrtl','arm_cpu2','p',1,1,'held',1.0,'t','g','c')")
    rtl = tmp_path / "c.v"; rtl.write_text("module m; endmodule")
    db.insert(conn, "runs", {"run_id": "r1", "exp": "phase5", "arm": "B2", "design_id": "drrtl_arm_cpu2", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    db.insert(conn, "runs", {"run_id": "rb0", "exp": "phase5", "arm": "B0", "design_id": "drrtl_arm_cpu2", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    for cid in ("c_pass", "c_fail", "c_other"):
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": "r1", "design_id": "drrtl_arm_cpu2", "gen": 1, "arm": "B2", "rtl_path": str(rtl), "label": "nonequiv", "seq_cap_min": 30,
                                       "note": "n [resim pending (DECISION 2026-09-19 (m) 2)]" if cid != "c_other" else "n"})
        payload = {"design_id": "drrtl_arm_cpu2", "cand_id": cid, "d_rtl": [str(rtl)], "c_rtl": [str(rtl)], "top": "m", "clk": "clk", "rst": None, "rst_sense": None, "sverilog": False, "incdirs": [], "note": f"search r1 g1 d"}
        db.insert(conn, "jobs", {"job_id": f"jf_{cid}", "kind": "sim", "pool": "local", "design_id": "drrtl_arm_cpu2", "cand_id": cid, "state": "failed", "priority": 4, "payload_json": json.dumps(payload), "submitted_at": "t", "finished_at": "t", "exit_code": 1})
    db.insert(conn, "candidates", {"cand_id": "c_b0", "run_id": "rb0", "design_id": "drrtl_arm_cpu2", "gen": 1, "arm": "B0", "rtl_path": str(rtl), "verdict": "proven", "label": "improved"})
    items = [(it["cand_id"], it["group"]) for it in mod.scope(cfg, conn)]
    assert items == [("c_fail", "resim"), ("c_pass", "resim"), ("c_b0", "b0_e4")]   # resim first; c_other has no marker
    monkeypatch.setattr(mod, "STATE", str(tmp_path / "state.json")); monkeypatch.setattr(mod, "LOG", str(tmp_path / "pool.log"))
    monkeypatch.setattr(mod, "throttle", lambda cfg, conn, st: (True, 50.0, 0.0))
    monkeypatch.setattr(mod, "slim_sim_record", lambda cfg, payload: "stub")
    monkeypatch.setattr("src.designs.catalog.load_all", lambda: [{"design_id": "drrtl_arm_cpu2", "top": "m", "files": ["c.v"], "clk_ports": ["clk"], "rst_port": None, "rst_sense": None, "incdirs": [], "_dir": str(tmp_path), "sverilog": False}])
    monkeypatch.setattr("src.designs.catalog.abs_paths", lambda d, paths: [tmp_path / p for p in paths])
    submitted = {}
    class FakeQ:
        def submit(self, kind, payload, **kw):
            jid = f"j_{len(submitted)}"; submitted[jid] = (kind, payload, kw); return jid
        def get(self, jid):
            return {"state": "done"} if jid in submitted else None
    st = {"cands": {}, "paused": False, "baseline": 100.0}
    mod.once(cfg, conn, st, queue=FakeQ())
    sims = {v[1]["cand_id"]: v for v in submitted.values() if v[0] == "sim"}
    assert set(sims) == {"c_pass", "c_fail"} and sims["c_pass"][2]["priority"] == 4 and sims["c_pass"][1]["resim"] == 1 and "resim" in sims["c_pass"][1]["note"]   # the run pipeline's priority, from the failed job's payload
    assert st["cands"]["c_pass"]["stage"] == "sim_running" and st["cands"]["c_b0"]["stage"] == "e4_running"
    records = {"c_pass": {"verdict": "not_run", "v1_status": "ok", "v2_status": "identical", "v2_cycles": 20000, "saif_c": None}, "c_fail": {"verdict": "sim_fail", "v1_status": "ok", "v2_status": "mismatch", "v2_cycles": 12}}
    monkeypatch.setattr(mod, "sim_record", lambda cfg, payload: records[payload["cand_id"]])
    mod.once(cfg, conn, st, queue=FakeQ())
    rows = {r["cand_id"]: dict(r) for r in conn.execute("SELECT cand_id, v1_status, v2_status, verdict, label, note FROM candidates")}
    assert rows["c_fail"]["verdict"] == "sim_fail" and rows["c_fail"]["label"] == "nonequiv" and rows["c_fail"]["v2_status"] == "mismatch" and st["cands"]["c_fail"]["stage"] == "done"
    assert rows["c_pass"]["verdict"] is None and rows["c_pass"]["label"] is None and rows["c_pass"]["v2_status"] == "identical" and "re-simulated" in rows["c_pass"]["note"]
    assert st["cands"]["c_pass"]["stage"] == "e4_proof_running"
    e4 = [v for v in submitted.values() if v[0] == "dc" and v[1]["cand_id"] == "c_pass"]; pf = [v for v in submitted.values() if v[0] == "vcf" and v[1]["cand_id"] == "c_pass"]
    assert len(e4) == 1 and e4[0][1]["resim"] == 1 and e4[0][2]["priority"] == 4 and "offline_eval" not in e4[0][1]
    assert len(pf) == 1 and pf[0][1]["sim_record"] == records["c_pass"] and pf[0][2]["priority"] == 6 and pf[0][2]["timeout_sec"] == 30 * 60 + 900   # the run's proof priority and cap
    monkeypatch.setattr(mod, "proof_record", lambda cfg, payload: {"verdict": "proven", "v3_status": "proven", "v3_seconds": 100.0, "proven_by": "seq", "harness_version": 2})
    db.insert(conn, "evaluations", {"design_id": "drrtl_arm_cpu2", "cand_id": "c_pass", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "status": "ok", "raw_dir": "/x/e4", "dc_seconds": 60.0})
    mod.once(cfg, conn, st, queue=FakeQ())
    row = dict(conn.execute("SELECT verdict, v3_status, harness_version, label, note FROM candidates WHERE cand_id='c_pass'").fetchone())
    assert row["verdict"] == "proven" and row["v3_status"] == "proven" and row["harness_version"] == 2 and row["label"] is None and "re-proven" in row["note"]
    assert st["cands"]["c_pass"]["stage"] == "done" and st["cands"]["c_pass"]["result"] == "resim: proof proven, E4 ok"


def test_submissions_follow_the_scope_order_not_the_state_file(tmp_path, monkeypatch):
    """DECISION 2026-09-19 (m) 1: with one free slot, the pool submits the first entry of the scope's order (medium B0) even when the
    state file lists a large-tier entry first; the other direction: with two slots both go."""
    mod = load_pool()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": ["L1"], "medium": ["M1"], "small": []}
    cfg["offline_pool"] = {"slots": 1, "priority": 1, "load_over_baseline": 0.10}
    cfg["queue"]["dc_seats_target"] = 10   # 10 idle DC seats: not more than 12, so the slot count stays at 1
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    for d in ("L1", "M1"):
        conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES (?,'x',?,'p',1,1,'held',1.0,'t','g','c')", (d, d))
    rtl = tmp_path / "c.v"; rtl.write_text("module m; endmodule")
    for rid, d in (("rl", "L1"), ("rm", "M1")):
        db.insert(conn, "runs", {"run_id": rid, "exp": "phase5", "arm": "B0", "design_id": d, "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
        db.insert(conn, "candidates", {"cand_id": f"c_{rid}", "run_id": rid, "design_id": d, "gen": 1, "arm": "B0", "rtl_path": str(rtl), "verdict": "proven"})
    monkeypatch.setattr(mod, "STATE", str(tmp_path / "state.json")); monkeypatch.setattr(mod, "LOG", str(tmp_path / "pool.log"))
    monkeypatch.setattr(mod, "throttle", lambda cfg, conn, st: (True, 50.0, 0.0))
    monkeypatch.setattr("src.designs.catalog.load_all", lambda: [{"design_id": d, "top": "m", "files": ["c.v"], "clk_ports": ["clk"], "rst_port": None, "rst_sense": None, "incdirs": [], "_dir": str(tmp_path), "sverilog": False} for d in ("L1", "M1")])
    monkeypatch.setattr("src.designs.catalog.abs_paths", lambda d, paths: [tmp_path / p for p in paths])
    submitted = []
    class FakeQ:
        def submit(self, kind, payload, **kw):
            submitted.append(payload["cand_id"]); return f"j{len(submitted)}"
        def get(self, jid):
            return {"state": "running"}
    st = {"cands": {"c_rl": {"cand_id": "c_rl", "group": "b0_e4", "run_id": "rl", "design_id": "L1", "rtl_path": str(rtl), "model": "gpt-5.6-luna", "arm": "B0", "tier": "large", "stage": "e4", "sim_job": None, "e4_job": None, "proof_job": None, "result": None}},
          "paused": False, "baseline": 100.0}   # the state file already lists the large-tier entry first
    mod.once(cfg, conn, st, queue=FakeQ())
    assert submitted == ["c_rm"] and st["cands"]["c_rm"]["stage"] == "e4_running" and st["cands"]["c_rl"]["stage"] == "e4"   # medium first, whatever the state file's order
    cfg["offline_pool"]["slots"] = 2
    mod.once(cfg, conn, st, queue=FakeQ())
    assert submitted == ["c_rm", "c_rl"]


def test_e4_failure_classification_terminal_or_retry_and_scope_skips(tmp_path, monkeypatch):
    """DECISION 2026-09-19 (n) 1: a failed pool E4 whose job log carries a DC rejection id (ELAB / VER / LINK) marks the row terminal
    (candidates.e4_failure) and the scope never retries it; a timeout or an unknown failure is left for a retry, at most three attempts;
    the scope also skips candidates with three failed attempts. Both directions."""
    mod = load_pool()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": [], "medium": ["M1"], "small": []}
    cfg["offline_pool"] = {"slots": 4, "priority": 1, "load_over_baseline": 0.10}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('M1','x','m1','p',1,1,'held',1.0,'t','g','c')")
    rtl = tmp_path / "c.v"; rtl.write_text("module m; endmodule")
    db.insert(conn, "runs", {"run_id": "r1", "exp": "phase5", "arm": "B2", "design_id": "M1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    for cid in ("c_rej", "c_tmo", "c_exh"):
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": "r1", "design_id": "M1", "gen": 1, "arm": "B2", "rtl_path": str(rtl), "verdict": "proven"})
    for k in range(3):   # three failed attempts on c_exh
        db.insert(conn, "evaluations", {"design_id": "M1", "cand_id": "c_exh", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "status": "eval_failed", "raw_dir": f"/x/{k}", "dc_seconds": 10.0})
    db.insert(conn, "evaluations", {"design_id": "M1", "cand_id": "c_rej", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "status": "eval_failed", "raw_dir": "/x/r", "dc_seconds": 10.0})
    db.insert(conn, "evaluations", {"design_id": "M1", "cand_id": "c_tmo", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "status": "eval_failed", "raw_dir": "/x/t", "dc_seconds": 1020.0})
    (tmp_path / "rej.log").write_text('.venv/bin/python3 -m src.eval.run_dc\n{"status": "eval_failed", "error": "Error: ... Net x is driven by more than one source. (ELAB-366)", "raw_dir": "/x/r"}\n')
    (tmp_path / "tmo.log").write_text('.venv/bin/python3 -m src.eval.run_dc\n{"status": "timeout", "error": "dc_shell exceeded 1020 s", "raw_dir": "/x/t"}\n')
    db.insert(conn, "jobs", {"job_id": "j_rej", "kind": "dc", "pool": "dc", "design_id": "M1", "cand_id": "c_rej", "state": "failed", "priority": 1, "payload_json": "{}", "submitted_at": "t", "log_path": str(tmp_path / "rej.log")})
    db.insert(conn, "jobs", {"job_id": "j_tmo", "kind": "dc", "pool": "dc", "design_id": "M1", "cand_id": "c_tmo", "state": "failed", "priority": 1, "payload_json": "{}", "submitted_at": "t", "log_path": str(tmp_path / "tmo.log")})
    assert mod.classify_e4_failure(cfg, conn, "c_rej", "j_rej") == ("rejected", "ELAB-366")
    assert mod.classify_e4_failure(cfg, conn, "c_tmo", "j_tmo") == ("retry", None)
    row = dict(conn.execute("SELECT e4_failure, note FROM candidates WHERE cand_id='c_rej'").fetchone())
    assert row["e4_failure"] == "DC rejected (ELAB-366)" and "terminal" in row["note"]
    assert dict(conn.execute("SELECT e4_failure FROM candidates WHERE cand_id='c_tmo'").fetchone())["e4_failure"] is None
    items = {it["cand_id"]: it["group"] for it in mod.scope(cfg, conn)}
    assert items == {"c_tmo": "e4_timeout"}                                        # the terminal one and the exhausted one are out of scope
    # the pool's own completion path: a failed E4 job with a rejection id ends the entry as terminal, a timeout as a retry
    monkeypatch.setattr(mod, "STATE", str(tmp_path / "state.json")); monkeypatch.setattr(mod, "LOG", str(tmp_path / "pool.log"))
    class FakeQ:
        def submit(self, kind, payload, **kw):
            return "j_new"
        def get(self, jid):
            return {"state": "failed"}
    conn.execute("UPDATE candidates SET e4_failure=NULL WHERE cand_id='c_rej'"); conn.commit()
    st = {"cands": {"c_rej": {"cand_id": "c_rej", "group": "e4_timeout", "run_id": "r1", "design_id": "M1", "rtl_path": str(rtl), "model": "gpt-5.6-luna", "arm": "B2", "tier": "medium", "stage": "e4_running", "e4_job": "j_rej", "sim_job": None, "proof_job": None, "result": None},
                    "c_tmo": {"cand_id": "c_tmo", "group": "e4_timeout", "run_id": "r1", "design_id": "M1", "rtl_path": str(rtl), "model": "gpt-5.6-luna", "arm": "B2", "tier": "medium", "stage": "e4_running", "e4_job": "j_tmo", "sim_job": None, "proof_job": None, "result": None}},
          "paused": True, "baseline": 100.0}
    monkeypatch.setattr(mod, "throttle", lambda cfg, conn, st: (False, 50.0, 0.0))
    monkeypatch.setattr("src.designs.catalog.load_all", lambda: [])
    mod.once(cfg, conn, st, queue=FakeQ())
    assert st["cands"]["c_rej"]["result"] == "E4 DC rejected (ELAB-366), terminal" and st["cands"]["c_tmo"]["result"].endswith("(no DC error id; retry)")
    assert dict(conn.execute("SELECT e4_failure FROM candidates WHERE cand_id='c_rej'").fetchone())["e4_failure"] == "DC rejected (ELAB-366)"
