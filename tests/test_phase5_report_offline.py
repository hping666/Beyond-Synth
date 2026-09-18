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
    plan = [{"tier": "medium", "model": "gpt-5.6-luna", "arm": a, "design_id": "m1", "seed": 1} for a in ("M", "B1_E4", "B2")]
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
    assert P5.complete_designs(cfg, conn, plan=plan)["complete"] == ["m1"]                           # an offline proof pending (D3) does not hold it back
    monkeypatch.setattr(P5, "complete_designs", lambda cfg, conn, exp="phase5", plan=None, _cd=P5.complete_designs: _cd(cfg, conn, exp, plan=plan if plan is not None else [dict(x) for x in [{"tier": "medium", "model": "gpt-5.6-luna", "arm": a, "design_id": "m1", "seed": 1} for a in ("M", "B1_E4", "B2")]]))
    view = P5.completion_view(cfg, conn)
    comp = view["comparisons"]["m1"]
    assert comp["model"] == "gpt-5.6-luna" and abs(comp["rows"]["gpt-5.6-luna|M"]["best_gain_mean"] - 0.08) < 1e-6 and comp["m_exceeds"] is True   # 8 % vs 2 % / 3 %, floor 1 %
    assert view["tally"]["wins"] == ["m1"] and view["reachability"]["wins"] == 1 and view["reachability"]["wins_still_needed"] == 17 and view["reachability"]["remaining_designs"] == 0 and not view["reachability"]["reachable"]
    state = tmp_path / "complete.json"; status = tmp_path / "STATUS.md"; status.write_text("# S\n")
    monkeypatch.setattr(C, "ROOT", str(tmp_path))
    new, line, _ = P5.completion_alert(cfg, conn, state_path=state, write=True)
    assert new == ["m1"] and line.startswith("New complete designs since last render") and "1 of 1 complete designs" in line and "m1" in status.read_text()
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
