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
    cand("c_inc", "r_b2", "inconclusive", None, 0, None, gen=2, extra={"class_final": "c1"})                                 # inconclusive proof of a c1 candidate (D2 table)
    db.insert(conn, "runs", {"run_id": "r_b0", "exp": "phase5", "arm": "B0", "design_id": "l1", "seed": 1, "llm_model": "gpt-5.6-terra", "status": "running", "started_at": "t", "llm_calls": 10})
    cand("c_b0p", "r_b0", None, None, 0, None)                                                                              # a row with nothing decided yet: reads `pending`, never 0 (D1)
    db.insert(conn, "jobs", {"job_id": "jv1", "kind": "vcf", "pool": "vcf", "design_id": "l1", "cand_id": "c_ret", "state": "done", "priority": 0, "payload_json": "{}",
                             "submitted_at": "2026-09-18T01:00:00", "started_at": "2026-09-18T01:12:00"})
    db.insert(conn, "jobs", {"job_id": "jv2", "kind": "vcf", "pool": "vcf", "design_id": "l1", "cand_id": "c_conv", "state": "done", "priority": 0, "payload_json": "{}",
                             "submitted_at": "2026-09-18T01:00:00", "started_at": "2026-09-18T01:20:00"})
    import datetime
    now = datetime.datetime.now().isoformat(timespec="seconds")
    (tmp_path / "results" / "queue").mkdir(parents=True, exist_ok=True)
    (tmp_path / "results" / "queue" / "load.log").write_text(f"{now} 100.0 1 1 search=1\n{now} 101.0 1 1 search=1\n")
    cfg["exp5"]["design_notes"] = {"l1": "harness limit (test)", "s1": "not on this tier"}
    cfg["exp5"]["disclosures"] = ["disclosure one"]
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
    # DECISION 2026-09-18 D1 / D2: pending accounting, incomplete rows, the retained list, inconclusive by class / design, verification conditions
    assert gb["pending_by"] == {"verdict": 1} and gb["incomplete"] and not gm["incomplete"] and data["pending_total"] == {"large": 2} and gb["inconclusive"] == 1
    assert data["groups"]["large|gpt-5.6-terra|B0"]["pending_by"] == {"verdict": 1} and data["designs"]["large|gpt-5.6-terra|B0|l1"]["pending"] == 1
    rl = {x["cand_id"]: x for x in data["retained_list"]}
    assert set(rl) == {"c_ret", "c_b2"} and rl["c_ret"]["label"] == "retained" and rl["c_ret"]["class_final"] == "b" and rl["c_ret"]["gains"]["area"] == 0.08 and rl["c_ret"]["stored_label"] == "retained"
    assert data["inconclusive"] == {"by_class": {"large|c1": 1}, "by_design": {"large|l1": 1}}
    cm = data["conditions"]["large|gpt-5.6-terra|M"]
    assert cm["proofs"] == 2 and cm["vcf_wait_median_min"] == 16.0 and cm["load_median"] == 100.5 and cm["load_samples"] == 2
    s = P5.pending_summary(cfg, conn, ["large"])
    assert s["pending"] == {"verdict": 2} and not s["complete"] and s["open_jobs"] == {}
    assert P5.pending_kind({"label": "prescreened", "verdict": None}, lambda: False) == "sim"
    assert P5.pending_kind({"label": "prescreened", "verdict": None, "v1_status": "ok", "v2_status": "identical"}, lambda: False) == "e4"
    assert P5.pending_kind({"label": "prescreened", "verdict": None, "v1_status": "ok", "v2_status": "identical"}, lambda: True) == "proof"
    assert P5.pending_kind({"label": "prescreened", "verdict": "rejected", "v1_status": "rejected", "v2_status": "compile_failed"}, lambda: False) is None
    assert P5.pending_kind({"label": None, "verdict": "proven"}, lambda: False) == "e4" and P5.pending_kind({"label": None, "verdict": "proven"}, lambda: True) is None
    assert P5.pending_kind({"label": "duplicate", "verdict": None}, lambda: False) is None and P5.pending_kind({"label": "aborted", "verdict": None}, lambda: False) is None
    assert abs(gb["usd"] - 0.06) < 1e-9 and gm["usd"] == 1.5                                                                # a running run's spend from its candidate rows; a finished run's from the row
    assert data["designs"]["large|gpt-5.6-terra|M|l1"]["best_retained_area_gain"] == 0.08 and data["correctness"]["large|gpt-5.6-terra|l1"]["proven"] == 3
    assert "large|gpt-5.6-terra|M" in data["curves"] and data["curves"]["large|gpt-5.6-terra|M"]["by_calls"][0]["mean_best_gain"] == 0.08
    assert not [r for r in data["runs"] if r["run_id"] in ("r_old", "r_med")]                                                # superseded runs and other tiers stay out
    assert not [k for k in data["groups"] if k.startswith("medium")]
    R = load_report()
    out = tmp_path / "reports"
    assert R.phase5(cfg, stage="A", out_dir=str(out), conn=conn) == 0
    text = (out / "phase5_stage_A.md").read_text()
    assert "Stage A" in text and "| gpt-5.6-terra (main) | M | 1/1 | 5 | 0 | 1 | 2 (0.033) |" in text and "8.00 %" in text and "block-level" in text and "improved: 1" in text
    assert "— interim" in text and "2 evaluations pending" in text and "| gpt-5.6-terra (main) | B0 | 0/1 † | 1 | 1 (verdict 1) | 0 | pending | 0 | 0 | 0 | pending | pending |" in text   # D1: never 0 on an incomplete row
    assert "| gpt-5.6-terra (main) | B2 | 0/1 † | 3 | 1 (verdict 1) | 0 | 1 (0.033) † |" in text and "| gpt-5.6-terra | B0 † | pending | pending |" in text
    assert "| l1 | harness limit | 5.00 % † | 8.00 % |" in text and "| large | gpt-5.6-terra | l1 (harness limit) |" in text        # §2 / §5: a design under a harness limit never reads 0 or pending on an empty row (5c / 5d)
    assert "LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): none" in text                                    # a harness limit is not an LLM limit
    cfg["exp5"]["design_notes"] = {}
    assert R.phase5(cfg, stage="A", out_dir=str(out), conn=conn) == 0 and "| l1 | pending | 5.00 % † | 8.00 % |" in (out / "phase5_stage_A.md").read_text()   # without the note: B0 pending, B2 interim, M final
    cfg["exp5"]["design_notes"] = {"l1": "harness limit (test)", "s1": "not on this tier"}
    assert "| l1 | large | harness limit (test) |" in text and "not on this tier" not in text and "- disclosure one" in text     # §0a notes (reported tiers only) and disclosures
    assert "| c_ret | retained | retained | b |" in text and "by class: c1: 1; by design: l1: 1" in text                          # §2a retained list, §5a inconclusive
    assert "| large | gpt-5.6-terra | M | 2 | 16.0 / 19.6 | 100.5 | 2 (100 %) |" in text                                                  # §7b verification conditions
    assert R.phase5(cfg, stage="A", out_dir=str(out), conn=conn, final=True) == 0 and "— final" in (out / "phase5_stage_A.md").read_text()
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
    # DECISION 2026-09-18 D2 / D3: the runs being done is not enough — pending evaluations and open visible jobs hold the final report back
    cfg["exp5"]["starting_points"] = {"large": ["l1"], "medium": [], "small": ["s1"]}
    ok, s = ST.evaluation_complete(cfg, conn, ["large"])
    assert ok and s["pending"] == {} and s["open_jobs"] == {}
    db.insert(conn, "candidates", {"cand_id": "cp", "run_id": "a", "design_id": "l1", "gen": 1, "arm": "M", "llm_model": "m", "verdict": "proven"})
    ok, s = ST.evaluation_complete(cfg, conn, ["large"])
    assert not ok and s["pending"] == {"e4": 1}                                       # a proven candidate without its E4 record
    db.insert(conn, "evaluations", {"design_id": "l1", "cand_id": "cp", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 1.0, "status": "ok", "raw_dir": "/x"})
    assert ST.evaluation_complete(cfg, conn, ["large"])[0]
    db.insert(conn, "jobs", {"job_id": "js", "kind": "sim", "pool": "local", "design_id": "l1", "cand_id": "cp", "state": "queued", "priority": 0, "payload_json": "{}", "submitted_at": "t"})
    ok, s = ST.evaluation_complete(cfg, conn, ["large"])
    assert not ok and s["open_jobs"] == {"sim": 1}                                     # an open visible job on the tier's design
    conn.execute("UPDATE jobs SET state='done' WHERE job_id='js'"); conn.commit()
    assert ST.evaluation_complete(cfg, conn, ["large"])[0] and ST.evaluation_complete(cfg, conn, ["small"])[0]
    # DECISION 2026-09-18 (d) D3: a prescreened candidate's missing offline simulation holds the final report back; once simulated and E4-evaluated,
    # its offline-pool proof is reported pending but does not
    db.insert(conn, "candidates", {"cand_id": "cpre", "run_id": "a", "design_id": "l1", "gen": 1, "arm": "M", "llm_model": "m", "label": "prescreened", "prescreened": 1})
    ok, s = ST.evaluation_complete(cfg, conn, ["large"])
    assert not ok and s["pending"] == {"sim": 1} and s["blocking"] == {"sim": 1}
    conn.execute("UPDATE candidates SET v1_status='ok', v2_status='identical' WHERE cand_id='cpre'"); conn.commit()
    db.insert(conn, "evaluations", {"design_id": "l1", "cand_id": "cpre", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 1.0, "status": "ok", "raw_dir": "/y"})
    ok, s = ST.evaluation_complete(cfg, conn, ["large"])
    assert ok and s["pending"] == {"proof": 1} and s["blocking"] == {}


def test_operational_changes_section_agreement_exposure_reuse_and_hourly_ratio(tmp_path, monkeypatch):
    """User follow-up 2026-09-16 (items 1 and 5): the report's §7a — provisional-versus-final agreement, the exposure window of
    positive provisional feedback (calls whose prompt carried a positive pending block, the candidates behind them, their proofs
    since), cross-run verdict reuse, the hourly proven-to-inconclusive ratio since the throttle (both directions: a negative
    pending block and a call outside the window are not exposures; a decided record without `reused_from` is not a reuse)."""
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["events"] = {"hidden_throttle_at": "2026-09-16T14:30", "scheduling_change_at": "2026-09-16T15:14", "provisional_fix_at": "2026-09-16T16:03"}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    db.insert(conn, "runs", {"run_id": "r1", "exp": "phase5", "arm": "M", "design_id": "l1", "seed": 1, "llm_model": "gpt-5.6-terra", "status": "running", "started_at": "t", "llm_calls": 10})
    rows = [("p_ret", "[provisional retained: equivalence pending]", "proven", "retained"), ("p_abs", "[provisional absorbed: equivalence pending]", "proven", "duplicate"),
            ("p_fal", "[provisional improved: equivalence pending]", "falsified", "nonequiv"), ("p_pen", "[provisional tradeoff: equivalence pending]", None, None),
            ("p_wh", "[provisional retained: equivalence pending, withheld]", None, None), ("plain", "no marker", "proven", "absorbed")]
    for cid, note, verdict, label in rows:
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": "r1", "design_id": "l1", "gen": 1, "arm": "M", "note": note, "verdict": verdict, "label": label})
        if label:
            db.insert(conn, "diagnoses", {"cand_id": cid, "run_id": "r1", "label": label, "credit": 0})
    ag = P5.provisional_agreement(conn)
    assert ag["n_provisional"] == 5 and ag["proven_final"] == 2 and ag["agree"] == 1 and ag["agree_rate"] == 0.5 and ag["not_proven"] == 1 and ag["pending"] == 2 and ag["withheld"] == 1
    assert ag["disagree"] == [{"cand_id": "p_abs", "provisional": "absorbed", "final": "duplicate"}] and ag["by_label"]["retained"] == 2
    # exposure: the run's state names its positively labelled provisional candidates; two calls in the window carry a positive block, one a negative one, one is after the fix
    st = {"cands": {"p_ret": {"provisional": {"label": "retained", "at": "2026-09-16T15:20:00"}, "seq_job_id": "jp"}, "p_pen": {"provisional": {"label": "tradeoff", "at": "2026-09-16T15:50:00"}},
                    "p_abs": {"provisional": {"label": "absorbed", "at": "2026-09-16T15:20:00"}}}, "feedback": {}}
    (tmp_path / "results" / "candidates" / "r1").mkdir(parents=True)
    (tmp_path / "results" / "candidates" / "r1" / "state.json").write_text(json.dumps(st))
    db.insert(conn, "jobs", {"job_id": "jp", "kind": "vcf", "pool": "vcf", "state": "done", "cand_id": "p_ret", "priority": 4, "attempts": 0, "payload_json": "{}", "submitted_at": "2026-09-16T15:15:00", "started_at": "2026-09-16T15:16:00", "finished_at": "2026-09-16T15:40:00"})
    ldir = tmp_path / "results" / "llm" / "r1"
    ldir.mkdir(parents=True)
    block = lambda diag: "```json\n" + json.dumps({"class": "b", "diagnosis": diag, "equivalence": "pending"}) + "\n```"
    calls = [("c1", "2026-09-16T15:30:00", block("retained")),                       # p_ret's block, before its proof: an exposure
             ("c2", "2026-09-16T15:45:00", block("retained") + "\n" + block("absorbed")),   # after p_ret's proof (15:40): the final block, not provisional; the absorbed one is negative
             ("c3", "2026-09-16T15:55:00", block("tradeoff")),                       # p_pen's block: an exposure
             ("c4", "2026-09-16T16:10:00", block("tradeoff")),                       # after the fix: outside the window
             ("c5", "2026-09-16T15:35:00", "no feedback here")]
    for cid, at, text in calls:
        (ldir / f"{cid}.json").write_text(json.dumps({"call_id": cid, "at": at, "request": {"input": "verdicts:\n" + text + "\nInstruction"}}))
    ex = P5.provisional_exposure(cfg, conn)
    assert ex["window"] == ["2026-09-16T15:14", "2026-09-16T16:03"] and ex["calls"] == 3 and ex["blocks"] == 3 and ex["runs"] == {"r1": 3}
    assert ex["cand_ids"] == ["p_pen", "p_ret"] and ex["fate"] == {"proven": 1, "pending": 1} and ex["unmatched_blocks"] == 1
    # reuse: one proof record copied from a decided full record, one ordinary split proof, one old record before the change
    eq = tmp_path / "results" / "raw" / "l1" / "EQ"
    for name, rec in (("h1", {"verdict": "falsified", "sim_record": "/s", "reused_from": "/old"}), ("h2", {"verdict": "proven", "sim_record": "/s"}), ("h3", {"verdict": "proven"})):
        (eq / name).mkdir(parents=True)
        (eq / name / "equiv.json").write_text(json.dumps(rec))
    import os, time
    old = time.mktime(time.strptime("2026-09-16T10:00", "%Y-%m-%dT%H:%M"))
    os.utime(eq / "h3" / "equiv.json", (old, old))
    ru = P5.verdict_reuse(cfg, conn)
    assert ru["records_scanned"] == 2 and ru["reused"] == 1 and ru["split_proofs"] == 2 and ru["by_verdict"] == {"falsified": 1} and ru["sim_record_missing"] == 0
    # hourly ratio since the throttle: jobs on the vcf pool by the candidate's verdict
    for i, (cid, fin) in enumerate((("p_ret", "2026-09-16T14:50:00"), ("p_fal", "2026-09-16T14:55:00"), ("plain", "2026-09-16T15:10:00"), ("p_abs", "2026-09-16T15:20:00"))):
        db.insert(conn, "jobs", {"job_id": f"jh{i}", "kind": "vcf", "pool": "vcf", "state": "done", "cand_id": cid, "priority": 4, "attempts": 0, "payload_json": "{}", "submitted_at": "2026-09-16T14:00:00", "started_at": "2026-09-16T14:30:00", "finished_at": fin})
    db.insert(conn, "candidates", {"cand_id": "inc", "run_id": "r1", "design_id": "l1", "gen": 1, "arm": "M", "verdict": "inconclusive"})
    db.insert(conn, "jobs", {"job_id": "jinc", "kind": "vcf", "pool": "vcf", "state": "done", "cand_id": "inc", "priority": 4, "attempts": 0, "payload_json": "{}", "submitted_at": "2026-09-16T14:00:00", "started_at": "2026-09-16T14:30:00", "finished_at": "2026-09-16T15:30:00"})
    db.insert(conn, "jobs", {"job_id": "jold", "kind": "vcf", "pool": "vcf", "state": "done", "cand_id": "plain", "priority": 4, "attempts": 0, "payload_json": "{}", "submitted_at": "2026-09-16T13:00:00", "started_at": "2026-09-16T13:30:00", "finished_at": "2026-09-16T14:00:00"})   # before the throttle
    hr = P5.hourly_proof_ratio(cfg, conn)
    assert [(h["hour"], h["finished"], h["proven"], h["inconclusive"], h["falsified"], h["ratio"]) for h in hr["hours"]] == [("2026-09-16T14", 2, 1, 0, 1, None), ("2026-09-16T15", 4, 3, 1, 0, 3.0)]   # hour 15 includes p_ret's proof job (jp, 15:40)
    # the section renders from collect()'s data
    ops = P5.operations(cfg, conn)
    assert set(ops) == {"events", "agreement", "exposure", "reuse", "hourly"} and "error" not in ops["exposure"]
    R = load_report()
    text = "\n".join(R.phase5_ops_section(ops))
    assert "## 7a." in text and "1 of 2 proven candidates with a final diagnosis agree (50.0 %)" in text and "3 LLM calls carried 3 positive pending blocks" in text
    assert "2 candidates behind them — proofs since: pending 1, proven 1" in text and "1 proofs copied from a decided record" in text and "| 2026-09-16T15 | 4 | 3 | 1 | 3.0 |" in text
    assert "not computed" in "\n".join(R.phase5_ops_section({"events": {}, "agreement": {"error": "boom"}}))


def test_complete_designs_tally_reachability_and_alert_both_directions(tmp_path, monkeypatch):
    """DECISION 2026-09-18 (d) F2 / F3: a design is complete when every planned row × seed is done with nothing pending (an offline
    proof does not hold it back); M exceeds when its mean best retained gain beats both B1_E4 and B2 by more than the floor; the
    alert fires once per new complete design and appends the line to STATUS.md."""
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"small": [], "medium": ["m1"], "large": []}
    cfg["scale"]["seeds"] = 1
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('m1','x','m1','p',1,1,'held',1.0,'t','g','c')")
    for metric, td in (("area", 0.01), ("wns", 0.005), ("power_saif", 0.02)):
        db.insert(conn, "noise_floor", {"design_id": "m1", "config": "E4", "metric": metric, "sigma_robust": 0.002, "t_d": td, "floor_class": "quiet", "floor_source": "measured", "floor_version": cfg["noise"].get("floor_version"), "n": 8})
    base_hist = json.dumps({"NAND2_X1": 100, "DFF_X1": 20})
    db.insert(conn, "evaluations", {"design_id": "m1", "is_baseline": 1, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 100.0, "cells": 120, "wns_ns": 0.05, "tns_ns": 0.0, "power_saif_mw": 1.0, "dc_seconds": 60, "status": "ok", "raw_dir": "/x/base", "hist_json": base_hist})
    plan = [{"tier": "medium", "model": "gpt-5.6-luna", "arm": a, "design_id": "m1", "seed": 1} for a in ("M", "B1_E4", "B2", "B0")]
    def run(rid, arm, status="done"):
        db.insert(conn, "runs", {"run_id": rid, "exp": "phase5", "arm": arm, "design_id": "m1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": status, "started_at": "t", "llm_calls": 60})
    def cand(cid, rid, area, verdict="proven", label=None):
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": rid, "design_id": "m1", "gen": 1, "arm": "M", "llm_model": "gpt-5.6-luna", "verdict": verdict, "label": label, "class_final": "b"})
        if verdict == "proven" and area is not None:
            db.insert(conn, "evaluations", {"design_id": "m1", "cand_id": cid, "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": area, "cells": 100, "wns_ns": 0.05, "tns_ns": 0.0, "power_saif_mw": 1.0, "dc_seconds": 60, "status": "ok", "raw_dir": f"/x/{cid}", "hist_json": json.dumps({"NAND2_X1": 70, "DFF_X1": 20})})
    run("r_m", "M"); run("r_b1", "B1_E4"); run("r_b2", "B2", status="running")
    cand("c_m", "r_m", 92.0); cand("c_b1", "r_b1", 98.0); cand("c_b2", "r_b2", 97.0)
    cd = P5.complete_designs(cfg, conn, plan=plan)
    assert cd["complete"] == [] and cd["rows"]["m1"]["gpt-5.6-luna|B2"] == {"done": 0, "planned": 1, "pending": 0}   # B2 still running
    conn.execute("UPDATE runs SET status='done' WHERE run_id='r_b2'"); conn.commit()
    cand("c_pend", "r_b2", None, verdict=None)                                                        # a verdict pending holds the design back
    assert P5.complete_designs(cfg, conn, plan=plan)["complete"] == [] and P5.complete_designs(cfg, conn, plan=plan)["rows"]["m1"]["gpt-5.6-luna|B2"]["pending"] == 1
    conn.execute("UPDATE candidates SET verdict='rejected' WHERE cand_id='c_pend'"); conn.commit()
    cand("c_pre", "r_m", None, verdict=None, label="prescreened"); conn.execute("UPDATE candidates SET v1_status='ok', v2_status='identical' WHERE cand_id='c_pre'")
    db.insert(conn, "evaluations", {"design_id": "m1", "cand_id": "c_pre", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 99.0, "cells": 100, "wns_ns": 0.05, "tns_ns": 0.0, "power_saif_mw": 1.0, "dc_seconds": 60, "status": "ok", "raw_dir": "/x/p", "hist_json": base_hist})
    conn.commit()
    monkeypatch.setattr(P5, "complete_designs", lambda cfg, conn, exp="phase5", plan=None, _cd=P5.complete_designs: _cd(cfg, conn, exp, plan=plan if plan is not None else [dict(x) for x in [{"tier": "medium", "model": "gpt-5.6-luna", "arm": a, "design_id": "m1", "seed": 1} for a in ("M", "B1_E4", "B2", "B0")]]))
    run("r_b0", "B0"); cand("c_b0", "r_b0", 99.0)                                                    # DECISION 2026-09-19 (l) 3: B0 proven, its offline E4 not yet in -> B0 pending
    ev_b0 = {k: v for k, v in dict(conn.execute("SELECT * FROM evaluations WHERE cand_id='c_b0'").fetchone()).items() if k not in {r[1] for r in conn.execute("PRAGMA table_info(evaluations)") if r[5]}}
    conn.execute("DELETE FROM evaluations WHERE cand_id='c_b0'"); conn.commit()
    cd = P5.complete_designs(cfg, conn, plan=plan)
    assert cd["complete"] == [] and cd["preliminary"] == ["m1"] and cd["blockers"]["m1"] == {"b0_e4": 1, "proof": 1} and cd["runs_done"]["m1"] is True
    view_p = P5.completion_view(cfg, conn)
    assert view_p["preliminary"] == ["m1"] and view_p["comparisons"]["m1"]["b0_pending"] is True and view_p["tally"]["wins"] == ["m1"] and view_p["reachability"]["preliminary"] == 1 and view_p["reachability"]["remaining_designs"] == 0
    new_p, line_p, _ = P5.completion_alert(cfg, conn, state_path=tmp_path / "prelim.json", write=False)
    assert new_p == ["m1"] and "B0 pending" in line_p and "tally 1 wins, 0 ties, 0 partial, 0 losses of 1 complete designs (visible layer; 1 of them B0 pending)" in line_p
    sec = "\n".join(load_report().phase5_completion_section(cfg, view_p, ["medium"], {"m1": "medium"}))
    assert "B0 pending: 1 — m1" in sec and "| gpt-5.6-luna | B0 | 1 | 1 | pending | pending | pending | pending (B0 offline E4) |" in sec and "on 1 of 1 complete designs (visible layer; ties 0, partial 0, M loses 0; 1 of them B0 pending)" in sec and "| gpt-5.6-luna | M | 1 | 2 | 1 | 1 | 0 |" in sec
    db.insert(conn, "evaluations", ev_b0); conn.commit()                                              # B0's E4 in -> the design moves to the full table
    assert P5.complete_designs(cfg, conn, plan=plan)["complete"] == ["m1"] and P5.complete_designs(cfg, conn, plan=plan)["preliminary"] == []   # an offline proof pending (D3) does not hold it back
    view = P5.completion_view(cfg, conn)
    comp = view["comparisons"]["m1"]
    assert comp["model"] == "gpt-5.6-luna" and abs(comp["rows"]["gpt-5.6-luna|M"]["best_gain_mean"] - 0.08) < 1e-6 and comp["m_exceeds"] is True   # 8 % vs 2 % / 3 %, floor 1 %
    assert view["tally"]["wins"] == ["m1"] and view["reachability"]["wins"] == 1 and view["reachability"]["wins_still_needed"] == 17 and view["reachability"]["remaining_designs"] == 0 and not view["reachability"]["reachable"]
    state = tmp_path / "complete.json"; status = tmp_path / "STATUS.md"; status.write_text("# S\n")
    monkeypatch.setattr(C, "ROOT", str(tmp_path))
    new, line, _ = P5.completion_alert(cfg, conn, state_path=state, write=True)
    assert new == ["m1"] and line.startswith("New complete designs since last render") and "tally 1 wins, 0 ties, 0 partial, 0 losses of 1 complete designs" in line and "m1" in status.read_text()
    new2, line2, _ = P5.completion_alert(cfg, conn, state_path=state, write=True)
    assert new2 == [] and line2 is None and status.read_text().count("New complete designs") == 1     # fires once
    # the other direction of the tally: M no better than the floor over B1_E4 / B2
    conn.execute("UPDATE evaluations SET area_um2=98.5 WHERE cand_id='c_m'"); conn.commit()
    view2 = P5.completion_view(cfg, conn)
    assert view2["comparisons"]["m1"]["m_exceeds"] is False and view2["tally"]["losses"] == ["m1"]


def test_verification_conditions_by_load(tmp_path, monkeypatch):
    """DECISION 2026-09-18 (h) item 1: per design and class, the inconclusive share of finished proofs started at a 1-minute load above
    100 and at or below 100 (the load sample nearest before the start, within two minutes); proofs started before the log, or without
    a sample nearby, are left out. Both directions."""
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"small": [], "medium": ["m1"], "large": []}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    db.insert(conn, "runs", {"run_id": "r", "exp": "phase5", "arm": "M", "design_id": "m1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    (tmp_path / "results" / "queue").mkdir(parents=True, exist_ok=True)
    (tmp_path / "results" / "queue" / "load.log").write_text("2026-09-18T10:00:00 120.0 1 1 x\n2026-09-18T10:01:00 90.0 1 1 x\n2026-09-18T10:02:00 130.0 1 1 x\n")
    proofs = [("c1", "b", "proven", "2026-09-18T10:00:30"), ("c2", "b", "inconclusive", "2026-09-18T10:00:40"), ("c3", "b", "proven", "2026-09-18T10:01:20"),
              ("c4", "a", "inconclusive", "2026-09-18T10:02:10"), ("c5", "a", "proven", "2026-09-18T09:30:00"), ("c6", "b", "proven", "2026-09-18T10:20:00")]   # c5 before the log, c6 no sample within 2 min
    for cid, cls, verdict, start in proofs:
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": "r", "design_id": "m1", "gen": 1, "arm": "M", "llm_model": "gpt-5.6-luna", "verdict": verdict, "class_final": cls})
        db.insert(conn, "jobs", {"job_id": f"j{cid}", "kind": "vcf", "pool": "vcf", "design_id": "m1", "cand_id": cid, "state": "done", "priority": 0, "payload_json": "{}", "submitted_at": start, "started_at": start, "finished_at": start})
    vc = P5.verification_conditions(cfg, conn, tiers=["medium"])
    assert vc["n"] == 4 and vc["from"] == "2026-09-18T10:00:00"
    assert vc["rows"]["m1"]["b"] == {"above": [1, 1], "below": [1, 0]} and vc["rows"]["m1"]["a"] == {"above": [0, 1], "below": [0, 0]}


def test_relative_revert_suspended_cohort_line_and_latency_bound_marking(tmp_path, monkeypatch):
    """DECISION 2026-09-19 (k) items 2 and 3 and (l) item 1: the automatic revert is suspended by default (three checks with a row 40
    points worse do nothing; the config keeps count_waiting_runs false); with auto_revert true it fires for that row only (a row at
    100 % with a 100 % baseline never triggers). The hourly line compares, per design, the runs admitted after the split with those
    admitted before (a design with one cohort shows "no runs" for the other). A design whose median proof latency exceeds the
    generation window carries the proof-latency-bound wording in §0a, others do not. Both directions."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("phase5_alerts", str(Path(C.ROOT) / "scripts" / "phase5_alerts.py"))
    AL = importlib.util.module_from_spec(spec); spec.loader.exec_module(AL)
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": [], "medium": ["m1", "m2"], "small": []}
    cfg["queue"]["lanes"] = {"vcf": {}}; cfg["queue"]["count_waiting_runs"] = False
    cfg["queue"]["admission_guard"] = {"unverified_at_build_max": 0.35, "proof_wait_max_min": 60, "window_min": 60, "tier": "medium", "auto_revert": False, "admission_split": "2026-09-19T02:09"}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    (tmp_path / "results" / "queue").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(AL, "SLOT_STATE", str(tmp_path / "slot_state.json"))
    monkeypatch.setattr(AL, "ROOT", str(tmp_path))
    (tmp_path / "config").mkdir(); (tmp_path / "config" / "experiments.yaml").write_text("queue:\n  count_waiting_runs: false\n")
    # two rows: A (design m1, admitted before the split) was at 100 % in the baseline window and stays there; B (design m2, admitted after) was at 20 % and is now at 60 %
    def gen(rid, design, model, arm, gen_no, pending_frac, built, started):
        if not conn.execute("SELECT 1 FROM runs WHERE run_id=?", (rid,)).fetchone():
            db.insert(conn, "runs", {"run_id": rid, "exp": "phase5", "arm": arm, "design_id": design, "seed": 1, "llm_model": model, "status": "running", "started_at": started})
        ids = [f"{rid}_g{gen_no - 1}_{k}" for k in range(5)]
        for cid in ids:
            db.insert(conn, "candidates", {"cand_id": cid, "run_id": rid, "design_id": design, "gen": gen_no - 1, "arm": arm, "llm_model": model})
        db.insert(conn, "gen_summary", {"run_id": rid, "gen": gen_no, "pending_json": json.dumps(ids[:int(5 * pending_frac)]), "built_at": built})
    import datetime
    now = datetime.datetime.now().isoformat(timespec="seconds")
    gen("rA", "m1", "luna", "A", 2, 1.0, "2026-09-18T12:00:00", "2026-09-18T11:00:00")    # baseline A = 100 %
    gen("rB", "m2", "luna", "B", 2, 0.2, "2026-09-18T12:00:00", "2026-09-19T02:30:00")    # baseline B = 20 %
    gen("rA", "m1", "luna", "A", 3, 1.0, now, None); gen("rB", "m2", "luna", "B", 3, 0.6, now, None)   # now: A 100 % (no worse), B 60 % (+40 points)
    restarted = []
    for k in range(3):
        lines = AL.slot_report(cfg, conn, write=True, restart=lambda: restarted.append(1) or True)
    assert not any("REVERT" in l for l in lines) and restarted == [] and any("automatic revert suspended" in l for l in lines)
    assert "count_waiting_runs: false" in (tmp_path / "config" / "experiments.yaml").read_text() and not (tmp_path / "slot_state.json").exists()
    coh = [l for l in lines if l.startswith("unverified-at-build per design, runs admitted after 02:09 vs before")]
    assert len(coh) == 1 and "m1: after no runs vs before 100% (2 gens / 1 runs) [100%]" in coh[0] and "m2: after 40% (2 gens / 1 runs) vs before no runs" in coh[0]
    # re-enabled: the revert fires for B only, after three checks
    cfg["queue"]["admission_guard"]["auto_revert"] = True
    for k in range(3):
        lines = AL.slot_report(cfg, conn, write=True, restart=lambda: restarted.append(1) or True)
    assert any("REVERT" in l and "luna|B" in l and "luna|A" not in l for l in lines) and restarted == [1]
    assert "count_waiting_runs: true" in (tmp_path / "config" / "experiments.yaml").read_text()
    st = json.loads((tmp_path / "slot_state.json").read_text())
    assert st["consecutive"]["luna|B"] == 3 and st["consecutive"]["luna|A"] == 0 and abs(st["baseline"]["luna|A"] - 1.0) < 1e-9 and abs(st["baseline"]["luna|B"] - 0.2) < 1e-9
    # §0a wording for a proof-latency-bound design only
    R = load_report()
    sec = "\n".join(R.phase5_notes_section(cfg, ["medium"], {"m1": "medium", "m2": "medium"}, latency_bound={"m1": 3000.0}))
    assert "| m1 | medium |" in sec and "proof-latency-bound search (median proof latency 50 min" in sec and "parents were D" in sec and "| m2 |" not in sec


def test_pending_kind_failed_job_and_identical_text_both_directions():
    """DECISION 2026-09-19 (l) 2: an identical-text candidate (absorbed_identical) is never evaluated itself and counts as complete; a
    nonequiv label without a verdict is a failed evaluation job (reported as failed_job, blocking until decided); every failed
    verdict is complete; a proven candidate waits for E4 only while it has none."""
    yes, no = (lambda: True), (lambda: False)
    assert P5.pending_kind({"label": "absorbed_identical", "verdict": None}, no) is None
    assert P5.pending_kind({"label": "nonequiv", "verdict": None}, no) == "failed_job"
    assert P5.pending_kind({"label": "nonequiv", "verdict": "falsified"}, no) is None and P5.pending_kind({"label": "nonequiv", "verdict": "error"}, no) is None
    assert P5.pending_kind({"label": None, "verdict": None}, no) == "verdict"
    assert P5.pending_kind({"label": "improved", "verdict": "proven"}, no) == "e4" and P5.pending_kind({"label": "improved", "verdict": "proven"}, yes) is None


def test_latency_bound_wording_follows_the_archive_data():
    """DECISION 2026-09-19 (k) 3 / (l) 4: the decided wording where the archive stayed empty at every generation build of every arm; the
    measured share of empty-archive builds otherwise; the tier note under the tables lists both kinds and only the tier's designs."""
    R = load_report()
    tier_of = {"a": "large", "b": "large", "c": "medium"}
    lb = {"a": {"median_s": 3000.0, "empty": {"B0-terra": [10, 10], "M-luna": [4, 4]}}, "b": {"median_s": 1900.0, "empty": {"B0-terra": [8, 35], "M-luna": [27, 29]}}, "c": {"median_s": 3060.0, "empty": {"B0-luna": [5, 5]}}}
    sec = "\n".join(R.phase5_notes_section({"exp5": {}}, ["large"], tier_of, latency_bound=lb))
    assert "| a | large | proof-latency-bound search (median proof latency 50 min above the 1 800 s generation window): on this design the archive stayed empty during generation for all arms; parents were D; the search reduces to E4-guided one-shot rewriting |" in sec
    assert "| b | large | proof-latency-bound search (median proof latency 32 min" in sec and "the archive was empty at 35 of 64 generation builds (B0-terra 8/35, M-luna 27/29); parents were D at those builds" in sec and "wording qualified to the data" in sec
    assert "| c |" not in sec
    note = R.latency_note_lines(lb, "large", tier_of)
    assert len(note) == 2 and "on a the archive stayed empty during generation for all arms" in note[0] and "on b at 35 of 64 generation builds (B0-terra 8/35, M-luna 27/29) the archive was empty at that share of generation builds only" in note[0] and "on c" not in note[0]
    assert R.latency_note_lines(lb, "small", tier_of) == [] and R.latency_note_lines({"c": 3060.0}, "medium", tier_of)[0].startswith("Note (DECISION 2026-09-19 (k) 3 / (l) 4): on c the archive stayed empty")


def test_completion_section_lists_what_blocks_the_all_done_designs():
    """DECISION 2026-09-19 (l) 2: every design whose planned runs are all done appears with its open proofs and what blocks "complete";
    the B0-pending design is marked; the sentence on the absent completion alert names the blockers; designs with open runs stay in
    the incomplete table only."""
    R = load_report()
    view = {"complete": [], "preliminary": ["d2"],
            "rows": {"d1": {"gpt-5.6-luna|M": {"done": 3, "planned": 3, "pending": 9}}, "d2": {"gpt-5.6-luna|B0": {"done": 3, "planned": 3, "pending": 5}}, "d3": {"gpt-5.6-luna|M": {"done": 1, "planned": 3, "pending": 0}}},
            "blockers": {"d1": {"failed_job": 7, "e4_late": 2}, "d2": {"b0_e4": 5}, "d3": {}}, "runs_done": {"d1": True, "d2": True, "d3": False}, "open_proofs": {"d1": 4},
            "comparisons": {"d2": {"rows": {"gpt-5.6-luna|B0": {"runs": 3, "cands": 9, "proven": 5, "retained": 0, "tradeoff": 0, "best_gain_mean": None, "best_gain_max": None}}, "model": "gpt-5.6-luna", "m_exceeds": None, "t_d_area": 0.01}},
            "tally": {"wins": [], "ties": ["d2"], "losses": [], "undecided": []},
            "reachability": {"total_designs": 3, "criterion_wins": 2, "wins": 0, "ties": 1, "lost": 0, "undecided": 0, "remaining_designs": 2, "wins_still_needed": 2, "reachable": True, "preliminary": 1}}
    view["comparisons"]["d2"]["m_outcome"] = "tie"
    sec = "\n".join(R.phase5_completion_section({"exp5": {"mechanism_notes": ["note X about M's archive"]}}, view, ["medium"], {"d1": "medium", "d2": "medium", "d3": "medium"}))
    assert "M: tie — no arm separates from the others on this design)" in sec and "Ties — no arm separates from the others on this design: d2." in sec and "ties 1, partial 0, M loses 0" in sec   # DECISION 2026-09-19 (m) 4 / (n) 2
    assert "- Mechanism note (C2): note X about M's archive" in sec and "the mean over seeds of each run's best retained area gain is the primary statistic (the tally rule of F2), with the max over seeds alongside; §2 shows the max over seeds only" in sec.splitlines()[0]   # (m) 5 / 6, (n) 4: stated once, in the header
    assert "| d1 | medium | 3 / 3 | 4 | E4 never submitted for 2 candidates (run finished before the proof returned; pool group e4_late); failed evaluation jobs 7 (sim jobs of the 2026-09-18 10:41 operator edit; re-run not yet decided) |" in sec
    assert "| d2 | medium | 3 / 3 | 0 | B0 offline E4 5 (offline pool) — B0 pending |" in sec
    assert "No design is complete, so no completion alert has fired: the 2 designs with every run done are held by B0 offline E4 5, E4 never submitted for 2 candidates, failed evaluation jobs 7." in sec
    assert "| d3 | medium | M-luna 1/3 |" in sec and "| d1 | medium | M-luna" not in sec
    assert "| gpt-5.6-luna | B0 | 3 | 9 | pending | pending | pending | pending (B0 offline E4) |" in sec and "on 0 of 1 complete designs (visible layer; ties 1, partial 0, M loses 0; 1 of them B0 pending)" in sec


def test_tally_categories_win_tie_loss_both_directions():
    """DECISION 2026-09-19 (m) 4: M wins when its mean best retained gain exceeds both B1_E4's and B2's by more than the floor, loses when
    worse than either by more than the floor, ties otherwise (within the floor of both — btb, decoder_8bit — or separated from one
    baseline only); None with a row missing. m_exceeds stays True only for a win."""
    def comp(m, b1, b2, t=0.01):
        return {"rows": {f"gpt-5.6-luna|{a}": {"best_gain_mean": v} for a, v in (("M", m), ("B1_E4", b1), ("B2", b2))}, "t_d_area": t}
    assert P5.m_outcome(comp(0.05, 0.03, 0.02), "gpt-5.6-luna") == "win"
    assert P5.m_outcome(comp(0.0191, 0.0212, 0.0197, 0.0028), "gpt-5.6-luna") == "tie"      # btb: within the floor of both
    assert P5.m_outcome(comp(0.0032, 0.0032, 0.0032, 0.0028), "gpt-5.6-luna") == "tie"      # decoder_8bit: equal
    assert P5.m_outcome(comp(0.01, 0.03, 0.01), "gpt-5.6-luna") == "loss"                   # worse than B1_E4 by more than the floor
    assert P5.m_outcome(comp(0.03, 0.01, 0.025), "gpt-5.6-luna") == "partial"               # DECISION 2026-09-19 (n) 2: separated from B1_E4 only, within the floor of B2
    assert P5.m_outcome(comp(0.03, 0.025, 0.01), "gpt-5.6-luna") == "partial" and P5.m_outcome(comp(0.03, 0.025, 0.021), "gpt-5.6-luna") == "tie"
    assert P5.m_outcome({"rows": {"gpt-5.6-luna|M": {"best_gain_mean": 0.1}}, "t_d_area": 0.01}, "gpt-5.6-luna") is None
    assert P5.m_exceeds(comp(0.05, 0.03, 0.02), "gpt-5.6-luna") is True and P5.m_exceeds(comp(0.0191, 0.0212, 0.0197, 0.0028), "gpt-5.6-luna") is False and P5.m_exceeds(comp(0.01, 0.03, 0.01), "gpt-5.6-luna") is False


def test_lane_threshold_raise_and_pool_progress_line(tmp_path, monkeypatch):
    """DECISION 2026-09-19 (m) 7: a lane with idle seat-minutes in the last hour and queued runs gets its proof-wait threshold raised to
    1.5 x its mean proof time (config merged, daemon restarted); a lane without queued runs, or without idle seat-minutes, does not;
    a dry run applies nothing. (m) 1: the pool progress line renders on an empty database ("unknown") and with records."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("phase5_alerts", str(Path(C.ROOT) / "scripts" / "phase5_alerts.py"))
    AL = importlib.util.module_from_spec(spec); spec.loader.exec_module(AL)
    from src.jobqueue import core as core
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": [], "medium": ["m1"], "small": []}
    cfg["queue"]["lanes"] = {"vcf": {"spi": {"designs": ["m1"], "share": 15}, "uart": {"designs": [], "share": 5}}}
    cfg["queue"]["admission_guard"] = {"unverified_at_build_max": 0.35, "proof_wait_max_min": 60, "window_min": 60, "tier": "medium", "auto_revert": False, "admission_split": "2026-09-19T02:09", "proof_wait_max_min_by_lane": {}}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    (tmp_path / "results" / "queue").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(AL, "SLOT_STATE", str(tmp_path / "slot_state.json")); monkeypatch.setattr(AL, "ROOT", str(tmp_path))
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "experiments.yaml").write_text("queue:\n  count_waiting_runs: false\n  admission_guard: {unverified_at_build_max: 0.35, proof_wait_max_min: 60, auto_revert: false}\n")
    monkeypatch.setattr(core, "idle_seat_minutes", lambda conn, cfg, hours=1.0: {"spi": {"seats": 15, "occupied_min": 800, "idle_min": 100.0}, "uart": {"seats": 5, "occupied_min": 300, "idle_min": 0.0}})
    monkeypatch.setattr(core, "queued_runs_by_lane", lambda conn, cfg: {"spi": 3, "uart": 2})
    monkeypatch.setattr(core, "proof_wait_estimate", lambda conn, cfg, design_id=None, hours=6: {"spi": {"wait_min": 70.0, "queued": 10, "seats": 15, "mean_min": 57.0}, "uart": {"wait_min": 700.0, "queued": 100, "seats": 5, "mean_min": 20.0}})
    monkeypatch.setattr(core, "search_slot_state", lambda conn, cfg: {"generating": 1, "waiting": 2, "queued": 3})
    monkeypatch.setattr(core, "unverified_at_build", lambda *a, **k: {})
    monkeypatch.setattr(core, "admission_cohorts", lambda *a, **k: {})
    restarted = []
    lines = AL.slot_report(cfg, conn, write=False, restart=lambda: restarted.append(1) or True)
    g = [l for l in lines if l.startswith("lane guardrail")]
    assert len(g) == 1 and "spi: 100 idle seat-minutes in the last hour with 3 queued runs, mean proof 57 min -> proof-wait threshold 60 -> 86 min" in g[0] and "uart" not in g[0] and "(dry run: not applied)" in g[0] and restarted == []
    lines = AL.slot_report(cfg, conn, write=True, restart=lambda: restarted.append(1) or True)
    assert restarted == [1] and "proof_wait_max_min_by_lane: {spi: 85.5}" in (tmp_path / "config" / "experiments.yaml").read_text()
    assert any(l.startswith("offline pool (m 1 / n 3):") and ("-> ETA drained" in l or "unknown (no throughput)" in l) for l in lines), [l for l in lines if "offline pool" in l]
    # the other direction: the raised lane at its new threshold is not raised again (a drift of the mean below one minute changes nothing and restarts nothing); uart with idle minutes but no queued runs is left alone
    cfg["queue"]["admission_guard"]["proof_wait_max_min_by_lane"] = {"spi": 85.0}
    monkeypatch.setattr(core, "idle_seat_minutes", lambda conn, cfg, hours=1.0: {"spi": {"seats": 15, "occupied_min": 800, "idle_min": 100.0}, "uart": {"seats": 5, "occupied_min": 200, "idle_min": 100.0}})
    monkeypatch.setattr(core, "queued_runs_by_lane", lambda conn, cfg: {"spi": 3})
    lines = AL.slot_report(cfg, conn, write=True, restart=lambda: restarted.append(1) or True)
    assert not any(l.startswith("lane guardrail") for l in lines) and restarted == [1]
    wl = [l for l in lines if l.startswith("estimated proof-queue wait per lane")][0]
    assert "PAUSED" not in wl.split("spi 70")[1].split("uart")[0] and "PAUSED" in wl.split("uart 700")[1].split(" — ")[0] and "thresholds raised (m 7): spi 85 min" in wl   # spi at 70 min is below its raised threshold; uart above the default
    # the merge keeps other lanes' values
    assert AL.set_lane_thresholds(str(tmp_path / "config" / "experiments.yaml"), {"uart": 30}) == {"spi": 85.5, "uart": 30.0}
    # pool progress with records: 3 medium B0 E4 records in the last hour, 6 waiting -> rate 1/h, ETA 6 h
    import datetime
    now = datetime.datetime.now().isoformat(timespec="seconds")
    db.insert(conn, "runs", {"run_id": "rb0", "exp": "phase5", "arm": "B0", "design_id": "m1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    state = {"cands": {}}
    for k in range(9):
        db.insert(conn, "candidates", {"cand_id": f"c{k}", "run_id": "rb0", "design_id": "m1", "gen": 1, "arm": "B0", "verdict": "proven"})
        if k < 3:
            db.insert(conn, "evaluations", {"design_id": "m1", "cand_id": f"c{k}", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "status": "ok", "raw_dir": f"/x/{k}", "dc_seconds": 60.0, "created_at": now})
        else:
            state["cands"][f"c{k}"] = {"group": "b0_e4", "design_id": "m1", "stage": "e4"}
    (tmp_path / "pool_state.json").write_text(json.dumps(state))
    pp = AL.pool_progress(cfg, conn, state_path=str(tmp_path / "pool_state.json"))
    assert pp["h1"]["medium_b0"] == 3 and pp["waiting"] == 6 and pp["rate_per_h"] == 1.0 and pp["eta_hours"] == 6.0 and pp["unfinished_runs"] == 0


def test_dc_rejection_is_terminal_and_listed(tmp_path):
    """DECISION 2026-09-19 (n) 1: a proven candidate whose E4 failed terminally (candidates.e4_failure) is resolved for completeness and
    listed per design in §0a with its DC error id; one without the marker still waits for E4. Both directions."""
    no = lambda: False
    assert P5.pending_kind({"label": None, "verdict": "proven", "e4_failure": "DC rejected (ELAB-366)"}, no) is None
    assert P5.pending_kind({"label": None, "verdict": "proven", "e4_failure": None}, no) == "e4"
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": [], "medium": ["m1", "m2"], "small": []}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    db.insert(conn, "runs", {"run_id": "r1", "exp": "phase5", "arm": "B2", "design_id": "m1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    db.insert(conn, "candidates", {"cand_id": "c_rej", "run_id": "r1", "design_id": "m1", "gen": 1, "arm": "B2", "verdict": "proven", "e4_failure": "DC rejected (ELAB-366)"})
    db.insert(conn, "candidates", {"cand_id": "c_rej2", "run_id": "r1", "design_id": "m1", "gen": 1, "arm": "B2", "verdict": "proven", "e4_failure": "DC rejected (VER-262)"})
    db.insert(conn, "candidates", {"cand_id": "c_wait", "run_id": "r1", "design_id": "m1", "gen": 1, "arm": "B2", "verdict": "proven"})
    s = P5.pending_summary(cfg, conn, ["medium"])
    assert s["pending"] == {"e4": 1} and not s["complete"]                     # the terminal ones are resolved; c_wait still holds
    rej = P5.dc_rejected(conn, cfg)
    assert rej == {"m1": [("c_rej", "B2", "DC rejected (ELAB-366)"), ("c_rej2", "B2", "DC rejected (VER-262)")]}
    R = load_report()
    sec = "\n".join(R.phase5_notes_section(cfg, ["medium"], {"m1": "medium", "m2": "medium"}, dc_rejected=rej))
    assert "| m1 | medium | evaluation failed (DC rejected): 2 proven candidates (ELAB-366, VER-262; B2 2) — rejected by DC at elaboration, terminal, counted as resolved (DECISION 2026-09-19 (n) 1) |" in sec and "| m2 |" not in sec


def test_pool_progress_reestimates_after_the_proof_drain(tmp_path, monkeypatch):
    """DECISION 2026-09-19 (n) 3: while medium proofs are open the rate is the 3-hour rate; once none is queued or running the drain time is
    recorded and, from ten minutes on, the rate is re-estimated over the time since the drain; the line says so and reads 'drained'."""
    import importlib.util, datetime
    spec = importlib.util.spec_from_file_location("phase5_alerts", str(Path(C.ROOT) / "scripts" / "phase5_alerts.py"))
    AL = importlib.util.module_from_spec(spec); spec.loader.exec_module(AL)
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": [], "medium": ["m1"], "small": []}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    db.insert(conn, "runs", {"run_id": "rb0", "exp": "phase5", "arm": "B0", "design_id": "m1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    now = datetime.datetime.now()
    state = {"cands": {}}
    for k in range(8):
        db.insert(conn, "candidates", {"cand_id": f"c{k}", "run_id": "rb0", "design_id": "m1", "gen": 1, "arm": "B0", "verdict": "proven"})
        if k < 4:   # four records: two in the last 20 min, two 2 h ago (the insert helper stamps created_at itself, so it is set afterwards)
            db.insert(conn, "evaluations", {"design_id": "m1", "cand_id": f"c{k}", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "status": "ok", "raw_dir": f"/x/{k}", "dc_seconds": 60.0})
            conn.execute("UPDATE evaluations SET created_at=? WHERE cand_id=?", ((now - datetime.timedelta(minutes=(15 if k < 2 else 120))).isoformat(timespec="seconds"), f"c{k}")); conn.commit()
        else:
            state["cands"][f"c{k}"] = {"group": "b0_e4", "design_id": "m1", "stage": "e4"}
    sp = tmp_path / "pool_state.json"; sp.write_text(json.dumps(state))
    db.insert(conn, "jobs", {"job_id": "p1", "kind": "vcf", "pool": "vcf", "design_id": "m1", "state": "queued", "priority": 4, "payload_json": "{}", "submitted_at": "t"})
    pp = AL.pool_progress(cfg, conn, state_path=str(sp))
    assert pp["open_medium_proofs"] == 1 and pp["proofs_drained_at"] is None and pp["rate_basis"] == "last 3 h" and abs(pp["rate_per_h"] - 4 / 3) < 0.05 and pp["waiting"] == 4
    conn.execute("UPDATE jobs SET state='done' WHERE job_id='p1'"); conn.commit()
    pp = AL.pool_progress(cfg, conn, state_path=str(sp))                          # first check after the drain: recorded, re-estimate announced for the next check
    assert pp["open_medium_proofs"] == 0 and pp["proofs_drained_at"] and "re-estimate at the next check" in pp["rate_basis"]
    es = json.loads((tmp_path / "pool_eta_state.json").read_text()); es["proofs_drained_at"] = (now - datetime.timedelta(minutes=30)).isoformat(timespec="minutes")
    (tmp_path / "pool_eta_state.json").write_text(json.dumps(es))
    pp = AL.pool_progress(cfg, conn, state_path=str(sp))                          # 30 min after the drain: the two recent records over 30 min -> 4/h
    import re
    assert re.search(r"re-estimated over the 3[01] min since the medium proofs drained", pp["rate_basis"]) and abs(pp["rate_per_h"] - 4.0) < 0.15 and abs(pp["eta_hours"] - 1.0) < 0.05
    monkeypatch.setattr(AL, "ROOT", str(tmp_path))
    monkeypatch.setattr(AL, "pool_progress", lambda cfg, conn, state_path=None: pp)
    monkeypatch.setattr(AL, "stage_b_proof_eta", lambda cfg, conn: 5.0)
    line = AL.pool_progress_line(cfg, conn)
    assert "Stage B proof ETA drained (" in line and "LATER" not in line and re.search(r"rate (3\.[5-9]|4\.[0-4])/h medium B0 \(re-estimated over the 3[01] min", line)


def test_stage_b_completeness_considers_the_medium_tier_only(tmp_path, monkeypatch):
    """DECISION 2026-09-19 (o) item 1: Stage B's final waits for the medium tier's items only — a large-tier candidate pending E4 does not
    hold it; a medium-tier one does. Stage A keeps the large tier, Stage C every tier."""
    spec = importlib.util.spec_from_file_location("phase5_stages", str(Path(C.ROOT) / "scripts" / "phase5_stages.py"))
    ST = importlib.util.module_from_spec(spec); spec.loader.exec_module(ST)
    assert ST.COMPLETENESS_TIERS == {"A": ["large"], "B": ["medium"], "C": ["small"]}   # DECISION 2026-09-19 (p) 1
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": ["l1"], "medium": ["m1"], "small": []}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    db.insert(conn, "runs", {"run_id": "rl", "exp": "phase5", "arm": "M", "design_id": "l1", "seed": 1, "llm_model": "m", "status": "done"})
    db.insert(conn, "runs", {"run_id": "rm", "exp": "phase5", "arm": "M", "design_id": "m1", "seed": 1, "llm_model": "m", "status": "done"})
    db.insert(conn, "candidates", {"cand_id": "cl", "run_id": "rl", "design_id": "l1", "gen": 1, "arm": "M", "llm_model": "m", "verdict": "proven"})   # large-tier E4 pending
    ok_b, s = ST.evaluation_complete(cfg, conn, ST.COMPLETENESS_TIERS["B"])
    assert ok_b and s["pending"] == {}
    assert not ST.evaluation_complete(cfg, conn, ST.COMPLETENESS_TIERS["A"])[0] and ST.evaluation_complete(cfg, conn, ST.COMPLETENESS_TIERS["C"])[0]   # C: the small tier only (empty here)
    db.insert(conn, "candidates", {"cand_id": "cm", "run_id": "rm", "design_id": "m1", "gen": 1, "arm": "M", "llm_model": "m", "verdict": "proven"})   # medium-tier E4 pending
    ok_b, s = ST.evaluation_complete(cfg, conn, ST.COMPLETENESS_TIERS["B"])
    assert not ok_b and s["pending"] == {"e4": 1}


def test_synthesis_rejected_subcategory_in_the_verdict_mix(tmp_path, monkeypatch):
    """DECISION 2026-09-19 (o) item 2: a candidate with a terminal DC rejection is counted per arm-model row (with design and DC error id)
    and per design in the correctness data; a row without one reads 0."""
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": [], "medium": ["m1", "m2"], "small": []}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    for d in ("m1", "m2"):
        conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES (?,'x',?,'p',1,1,'held',1.0,'t','g','c')", (d, d))
    db.insert(conn, "runs", {"run_id": "r1", "exp": "phase5", "arm": "B2", "design_id": "m1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t", "llm_calls": 60})
    db.insert(conn, "runs", {"run_id": "r2", "exp": "phase5", "arm": "M", "design_id": "m2", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t", "llm_calls": 60})
    db.insert(conn, "candidates", {"cand_id": "c1", "run_id": "r1", "design_id": "m1", "gen": 1, "arm": "B2", "llm_model": "gpt-5.6-luna", "verdict": "proven", "e4_failure": "DC rejected (ELAB-366)"})
    db.insert(conn, "candidates", {"cand_id": "c2", "run_id": "r1", "design_id": "m1", "gen": 1, "arm": "B2", "llm_model": "gpt-5.6-luna", "verdict": "proven", "e4_failure": "DC rejected (ELAB-366)"})
    db.insert(conn, "candidates", {"cand_id": "c3", "run_id": "r2", "design_id": "m2", "gen": 1, "arm": "M", "llm_model": "gpt-5.6-luna", "verdict": "falsified", "label": "nonequiv"})
    data = P5.collect(cfg, conn, tiers=["medium"])
    assert data["groups"]["medium|gpt-5.6-luna|B2"]["synth_rejected"] == {"m1|ELAB-366": 2} and data["groups"]["medium|gpt-5.6-luna|M"]["synth_rejected"] == {}
    assert data["correctness"]["medium|gpt-5.6-luna|m1"]["synth_rejected"] == 2 and data["correctness"]["medium|gpt-5.6-luna|m2"]["synth_rejected"] == 0
    R = load_report()
    out = tmp_path / "reports"; out.mkdir()
    monkeypatch.setattr(P5, "completion_view", lambda cfg, conn, exp="phase5": {"complete": [], "preliminary": [], "rows": {}, "blockers": {}, "runs_done": {}, "open_proofs": {}, "comparisons": {}, "tally": {"wins": [], "ties": [], "partials": [], "losses": [], "undecided": []},
                                                                                 "reachability": {"total_designs": 2, "criterion_wins": 18, "wins": 0, "ties": 0, "partial": 0, "lost": 0, "undecided": 0, "remaining_designs": 2, "wins_still_needed": 18, "reachable": False, "preliminary": 0}})
    assert R.phase5(cfg, stage="B", out_dir=str(out), conn=conn) == 0
    txt = (out / "phase5_stage_B.md").read_text()
    assert "| formal-accepted, synthesis-rejected (DC error id; DECISION 2026-09-19 (o) 2) |" in txt
    row_b2 = [l for l in txt.splitlines() if l.startswith("| gpt-5.6-luna | B2 |") and "ELAB-366" in l]
    assert row_b2 and "| 2 (m1 ELAB-366 ×2) |" in row_b2[0]
    row_m = [l for l in txt.splitlines() if l.startswith("| gpt-5.6-luna | M | 0 | 1 |")]
    assert row_m and "| 0 | 0 | 0 | -" in row_m[0]


def test_phase5_completion_condition_both_directions(tmp_path, monkeypatch):
    """DECISION 2026-09-19 (p) item 1: the Phase 5 completion condition is met only when every tier's planned runs are done, nothing is
    pending including an offline-pool proof, no visible job is open and the offline pool has no unfinished entry (await_proof included)."""
    spec = importlib.util.spec_from_file_location("phase5_stages", str(Path(C.ROOT) / "scripts" / "phase5_stages.py"))
    ST = importlib.util.module_from_spec(spec); spec.loader.exec_module(ST)
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": ["l1"], "medium": ["m1"], "small": ["s1"]}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    plan = [{"tier": t, "model": "m", "arm": "M", "design_id": d, "seed": 1} for t, d in (("large", "l1"), ("medium", "m1"), ("small", "s1"))]
    for rid, d in (("rl", "l1"), ("rm", "m1"), ("rs", "s1")):
        db.insert(conn, "runs", {"run_id": rid, "exp": "phase5", "arm": "M", "design_id": d, "seed": 1, "llm_model": "m", "status": "done"})
    pool = tmp_path / "pool_state.json"; pool.write_text(json.dumps({"cands": {}}))
    e1 = tmp_path / "e1_ab.done"
    met, detail = ST.phase5_completion_condition(cfg, conn, pool_state_path=str(pool), plan=plan, e1_marker=str(e1))
    assert not met and detail["e1_ab_done"] is False                                   # DECISION 2026-09-19 (q) 2: the E1 (a) / (b) report must be issued
    e1.write_text("{}")
    met, detail = ST.phase5_completion_condition(cfg, conn, pool_state_path=str(pool), plan=plan, e1_marker=str(e1))
    assert met and detail["runs_done"] and detail["pending"] == {} and detail["pool_unfinished"] == {} and detail["e1_ab_done"]
    # a prescreened candidate whose offline proof is still pending holds the condition (not the Stage C final)
    db.insert(conn, "candidates", {"cand_id": "cp", "run_id": "rs", "design_id": "s1", "gen": 1, "arm": "M", "llm_model": "m", "label": "prescreened", "prescreened": 1, "v1_status": "ok", "v2_status": "identical"})
    db.insert(conn, "evaluations", {"design_id": "s1", "cand_id": "cp", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 1.0, "status": "ok", "raw_dir": "/x"})
    met, detail = ST.phase5_completion_condition(cfg, conn, pool_state_path=str(pool), plan=plan, e1_marker=str(e1))
    assert not met and detail["pending"] == {"proof": 1} and ST.evaluation_complete(cfg, conn, ST.COMPLETENESS_TIERS["C"])[0]
    conn.execute("UPDATE candidates SET verdict='proven' WHERE cand_id='cp'"); conn.commit()
    assert ST.phase5_completion_condition(cfg, conn, pool_state_path=str(pool), plan=plan, e1_marker=str(e1))[0]
    # a prescreened pool entry still unfinished holds it; a D2 re-verification entry (group reverify) does not (DECISION 2026-09-19 (q) 2)
    pool.write_text(json.dumps({"cands": {"x": {"group": "prescreened", "stage": "e4_running"}}}))
    met, detail = ST.phase5_completion_condition(cfg, conn, pool_state_path=str(pool), plan=plan, e1_marker=str(e1))
    assert not met and detail["pool_unfinished"] == {"e4_running": 1}
    pool.write_text(json.dumps({"cands": {"x": {"group": "reverify", "stage": "await_proof"}}}))
    met, detail = ST.phase5_completion_condition(cfg, conn, pool_state_path=str(pool), plan=plan, e1_marker=str(e1))
    assert met and detail["pool_unfinished"] == {}
    # a planned run not done holds it
    conn.execute("UPDATE runs SET status='running' WHERE run_id='rs'"); conn.commit()
    assert not ST.phase5_completion_condition(cfg, conn, pool_state_path=str(pool), plan=plan, e1_marker=str(e1))[0]


def test_pool_progress_with_a_drained_backlog(tmp_path, monkeypatch):
    """The medium B0 E4 backlog at zero: no ETA is computed from a stale 3-hour rate; the line reads 'drained', names the candidates still
    expected from the B0 runs not done, and no longer compares against the proof path as LATER."""
    import importlib.util, datetime
    spec = importlib.util.spec_from_file_location("phase5_alerts", str(Path(C.ROOT) / "scripts" / "phase5_alerts.py"))
    AL = importlib.util.module_from_spec(spec); spec.loader.exec_module(AL)
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"large": [], "medium": ["m1"], "small": []}
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    db.insert(conn, "runs", {"run_id": "rb0", "exp": "phase5", "arm": "B0", "design_id": "m1", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    db.insert(conn, "runs", {"run_id": "rb1", "exp": "phase5", "arm": "B0", "design_id": "m1", "seed": 2, "llm_model": "gpt-5.6-luna", "status": "running", "started_at": "t"})
    for k in range(4):
        db.insert(conn, "candidates", {"cand_id": f"c{k}", "run_id": "rb0", "design_id": "m1", "gen": 1, "arm": "B0", "verdict": "proven"})
        db.insert(conn, "evaluations", {"design_id": "m1", "cand_id": f"c{k}", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "status": "ok", "raw_dir": f"/x/{k}", "dc_seconds": 60.0})
        conn.execute("UPDATE evaluations SET created_at=? WHERE cand_id=?", ((datetime.datetime.now() - datetime.timedelta(hours=6)).isoformat(timespec="seconds"), f"c{k}")); conn.commit()
    sp = tmp_path / "pool_state.json"; sp.write_text(json.dumps({"cands": {}}))
    db.insert(conn, "jobs", {"job_id": "p1", "kind": "vcf", "pool": "vcf", "design_id": "m1", "state": "queued", "priority": 4, "payload_json": "{}", "submitted_at": "t"})   # medium proofs still open
    pp = AL.pool_progress(cfg, conn, state_path=str(sp))
    assert pp["waiting"] == 0 and pp["eta"] is None and pp["expected"] == 4.0 and pp["rate_basis"].startswith("backlog drained; about 4 more from 1 medium B0 run not done")
    monkeypatch.setattr(AL, "ROOT", str(tmp_path)); monkeypatch.setattr(AL, "pool_progress", lambda cfg, conn, state_path=None: pp); monkeypatch.setattr(AL, "stage_b_proof_eta", lambda cfg, conn: 5.0)
    line = AL.pool_progress_line(cfg, conn)
    assert "-> ETA drained" in line and "LATER" not in line and "the B0 E4 backlog is drained: Stage B final follows the proof path" in line
