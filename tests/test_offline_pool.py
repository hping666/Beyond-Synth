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
    assert items == {"b0_proven": "b0_e4", "m_pre": "prescreened", "med_b0": "b0_e4"}        # every tier's finished B0 runs (DECISION (d) B5); existing E4 records, unproven B0 and the timeout skipped
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
    assert counts == {"sim_running": 1, "e4_running": 1, "done": 1}   # the medium-tier B0 candidate is in scope (DECISION (d) B5) and, with M1 absent from the stubbed catalog, ends at once
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
    assert items == [("c_rl", "b0_e4", "large"), ("c_rm", "b0_e4", "medium"), ("c_rs", "b0_e4", "small")]   # every tier, in order; the running run's candidate not yet
    conn.execute("UPDATE runs SET status='done' WHERE run_id='rm_run'"); conn.commit()
    assert [it["cand_id"] for it in mod.scope(cfg, conn)] == ["c_rl", "c_rm", "c_rm_run", "c_rs"]
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
    assert st["slots_now"] == 12                                         # 20 idle seats: the pool may use 12


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
