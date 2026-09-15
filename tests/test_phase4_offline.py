"""Offline tests of the Phase 4 helpers (scripts/phase4_exp1.py): the object's top module guess, the equivalence payload of
a literature object (D's top, the object's own top as c_top), the baseline configurations the map needs, and the ladder
job payloads (files, top, kind by tool) on a temporary database."""
import json
import sys
from pathlib import Path

from src import config as C
from src.db import core as db

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import phase4_exp1 as X  # noqa: E402


def test_guess_top_and_payload(tmp_path):
    a = tmp_path / "a.v"
    a.write_text("module add_sub_ref(input x, output y);\n  assign y = x;\nendmodule\n")
    b = tmp_path / "b.v"
    b.write_text("module helper(input x, output y); assign y = x; endmodule\nmodule example(input x, output y); helper h(.x(x), .y(y)); endmodule\n")
    assert X.guess_top([a], "add_sub") == "add_sub_ref"          # D's name absent: the object's own module
    assert X.guess_top([b], "example") == "example"              # D's name present: keep it
    assert X.guess_top([b], "other") == "helper"                 # neither: the first declared module
    d = {"design_id": "rtlopt_add_sub", "top": "add_sub", "files": ["rtl/add_sub.v"], "incdirs": [], "clk_ports": [], "rst_port": None, "rst_sense": None, "sverilog": False, "_dir": str(tmp_path)}
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "add_sub.v").write_text("module add_sub(input x, output y); assign y = x; endmodule\n")
    p = X.eq_payload_for(d, "cid1", [str(a)], "add_sub_ref", "n")
    assert p["top"] == "add_sub" and p["c_top"] == "add_sub_ref" and p["c_rtl"] == [str(a)] and p["clk"] is None and p["cand_id"] == "cid1"
    assert X.eq_payload_for(d, "cid2", [str(b)], "add_sub", "n")["c_top"] is None   # same name as D: no override


def test_baseline_configs_and_ladder_jobs(tmp_path):
    cfg = C.load()
    assert set(X.baseline_configs(cfg)) == {"E1d", "E2g", "Y", "O0", "O1", "O2", "Ycoevo"}
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    from src.designs import catalog as K
    import pytest
    ddir = tmp_path / "designs" / "rtlopt" / "p"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "p.v").write_text("module p(input clk, input a, output reg y); always @(posedge clk) y <= a; endmodule\n")
    ref = ddir / "reference" / "p_ref.v"
    ref.parent.mkdir()
    ref.write_text("module p_ref(input clk, input a, output reg y); always @(posedge clk) y <= a; endmodule\n")
    d = {"design_id": "rtlopt_p", "suite": "rtlopt", "name": "p", "top": "p", "files": ["rtl/p.v"], "clk_ports": ["clk"], "rst_port": None, "rst_sense": None, "sverilog": False, "incdirs": [],
         "tb": None, "reference": {"files": ["reference/p_ref.v"], "top": "p_ref", "note": "expert"}, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/p.v": K.sha256_of(ddir / "rtl" / "p.v"), "reference/p_ref.v": K.sha256_of(ref)}, "loc": 1, "tags": ["rtlopt", "pair"], "notes": [], "_dir": str(ddir)}
    monkey = pytest.MonkeyPatch()
    monkey.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    try:
        K.write_design(d)
        conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('rtlopt_p','rtlopt','p','x',1,1,'held',1.0,'t','g','c')")
        db.insert(conn, "runs", {"run_id": "lit_rtlopt_p", "exp": "phase4", "arm": X.LIT_ARM, "design_id": "rtlopt_p", "seed": 0, "status": "done", "started_at": "t"})
        db.insert(conn, "candidates", {"cand_id": "obj1", "run_id": "lit_rtlopt_p", "design_id": "rtlopt_p", "gen": 0, "arm": X.LIT_ARM, "rtl_path": str(ref), "top": "p_ref",
                                       "rtl_files_json": json.dumps([str(ref), str(ref)]), "label": "object", "verdict": "proven", "class_final": "b"})
        db.insert(conn, "candidates", {"cand_id": "obj2", "run_id": "lit_rtlopt_p", "design_id": "rtlopt_p", "gen": 0, "arm": X.LIT_ARM, "rtl_path": str(ref), "label": "object", "verdict": "falsified"})
        objs = X.phase4_objects(conn)
        assert [o["cand_id"] for o in objs] == ["obj1"]                      # proven objects only
        assert len(X.phase4_objects(conn, proven_only=False)) == 2
        jobs = X.ladder_jobs(cfg, conn, ["E1", "E4", "Y"], 1)
        assert [j["config"] for j in jobs] == ["E1", "E4", "Y"] and [j["kind"] for j in jobs] == ["dc", "dc", "yosys"]
        assert all(j["payload"]["top"] == "p_ref" and j["payload"]["rtl"] == [str(ref), str(ref)] and j["payload"]["cand_id"] == "obj1" and j["payload"]["is_baseline"] == 0 for j in jobs)
        db.insert(conn, "evaluations", {"design_id": "rtlopt_p", "cand_id": "obj1", "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 1.0, "status": "ok", "raw_dir": "/x"})
        assert [j["config"] for j in X.ladder_jobs(cfg, conn, ["E1", "E4", "Y"], 1)] == ["E1", "Y"]   # missing records only
        # 2026-09-15: a pair whose latest record is a deterministic failure (the tool rejects the RTL) is not re-submitted
        # unless retry_failed; a license failure is re-submitted; the skip is counted per configuration
        raw1 = tmp_path / "raw_e1"
        raw1.mkdir()
        (raw1 / "meta.json").write_text(json.dumps({"status": "eval_failed", "failed_status": "analyze_failed", "error": "Error: x.v:29: Syntax error at or near token (VER-294)"}))
        db.insert(conn, "evaluations", {"design_id": "rtlopt_p", "cand_id": "obj1", "config": "E1", "lib": "nangate45", "clock_ns": 1.0, "status": "eval_failed", "raw_dir": str(raw1), "created_at": "t"})
        raw2 = tmp_path / "raw_y"
        raw2.mkdir()
        (raw2 / "meta.json").write_text(json.dumps({"status": "eval_failed", "failed_status": "license_failed"}))
        db.insert(conn, "evaluations", {"design_id": "rtlopt_p", "cand_id": "obj1", "config": "Y", "lib": "nangate45", "clock_ns": 1.0, "status": "eval_failed", "raw_dir": str(raw2), "created_at": "t"})
        assert [j["config"] for j in X.baseline_jobs(cfg, conn, ["rtlopt_p"], 1, configs=["E1", "E4", "Y"])] == ["E1", "E4", "Y"]   # no D baseline in this database: all missing
        skipped = {}
        jobs = X.ladder_jobs(cfg, conn, ["E1", "E4", "Y"], 1, skipped=skipped)
        assert [j["config"] for j in jobs] == ["Y"] and skipped == {"E1": 1}
        assert [j["config"] for j in X.ladder_jobs(cfg, conn, ["E1", "E4", "Y"], 1, retry_failed=True)] == ["E1", "Y"]
    finally:
        monkey.undo()


def test_ladder_jobs_carry_the_design_include_directories(tmp_path):
    """2026-09-14: candidates of designs with `include files (cktevo) failed every evaluation because the jobs carried no
    include directories; the ladder payload must list the design's incdirs (absolute)."""
    cfg = C.load()
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    from src.designs import catalog as K
    import pytest
    ddir = tmp_path / "designs" / "cktevo" / "inc"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "inc.v").write_text('`include "defs.v"\nmodule inc(input clk, input a, output reg y); always @(posedge clk) y <= a ^ `K; endmodule\n')
    (ddir / "rtl" / "defs.v").write_text("`define K 1'b1\n")
    d = {"design_id": "cktevo_inc", "suite": "cktevo", "name": "inc", "top": "inc", "files": ["rtl/inc.v"], "clk_ports": ["clk"], "rst_port": None, "rst_sense": None, "sverilog": False,
         "incdirs": ["rtl"], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/inc.v": K.sha256_of(ddir / "rtl" / "inc.v")}, "loc": 2, "tags": ["cktevo"], "notes": [], "_dir": str(ddir)}
    monkey = pytest.MonkeyPatch()
    monkey.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    try:
        K.write_design(d)
        conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('cktevo_inc','cktevo','inc','x',2,1,'held',1.0,'t','g','c')")
        db.insert(conn, "runs", {"run_id": "rb0", "exp": "phase4", "arm": "B0", "design_id": "cktevo_inc", "seed": 1, "status": "done", "started_at": "t"})
        db.insert(conn, "candidates", {"cand_id": "k1", "run_id": "rb0", "design_id": "cktevo_inc", "gen": 1, "arm": "B0", "rtl_path": str(tmp_path / "k1.v"), "label": "improved", "verdict": "proven"})
        jobs = X.ladder_jobs(cfg, conn, ["E1"], 1)
        assert jobs and jobs[0]["payload"]["incdirs"] == [str(ddir / "rtl")]
    finally:
        monkey.undo()


def test_eval_failed_objects_and_categories(tmp_path):
    """Hygiene of the synthesis evaluations (2026-09-15): an object whose only record under a configuration failed is listed
    with the category of the tool error; a failed record followed by an ok one (a recovered evaluation) is not; an unknown
    error is `other (<status>)`; a candidate without a verdict whose fitness evaluation failed is listed too (the hygiene
    command files it under the fitness failures, not the objects)."""
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    db.insert(conn, "runs", {"run_id": "b0r", "exp": "phase4", "arm": "B0", "design_id": "drrtl_i2c", "seed": 1, "status": "done", "started_at": "t"})

    def cand(cid, verdict):
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": "b0r", "design_id": "drrtl_i2c", "gen": 1, "arm": "B0", "rtl_path": "x.v", "label": "improved", "verdict": verdict})

    def ev(cid, config, status, error=None, failed_status="analyze_failed"):
        raw = tmp_path / cid / f"{config}_{status}"
        raw.mkdir(parents=True)
        if status != "ok":
            (raw / "meta.json").write_text(json.dumps({"status": "eval_failed", "failed_status": failed_status, "error": error}))
        db.insert(conn, "evaluations", {"design_id": "drrtl_i2c", "cand_id": cid, "config": config, "lib": "nangate45", "clock_ns": 1.0, "status": status, "raw_dir": str(raw), "created_at": "t"})
    cand("rej", "proven")
    ev("rej", "E1", "eval_failed", "Error: x.v:29: Syntax error at or near token '|'. (VER-294)")
    ev("rej", "E4", "eval_failed", "Error: x.v:29: Syntax error at or near token '|'. (VER-294)")
    cand("rec", "proven")
    ev("rec", "E4", "eval_failed", "Error: Can't open include file")
    ev("rec", "E4", "ok")
    cand("unk", "proven")
    ev("unk", "E2", "eval_failed", "something new", failed_status="timeout")
    cand("fit", None)
    ev("fit", "Y", "eval_failed", "behavioural constructs in the Yosys netlist (OpenSTA cannot read them): line 799", failed_status="netlist_not_structural")
    cand("fine", "proven")
    ev("fine", "E4", "ok")
    rows = [dict(r) for r in conn.execute("SELECT c.cand_id, c.design_id, c.verdict, c.note, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id")]
    got = {r["cand_id"]: r for r in X.eval_failed_objects(C.load(), conn, rows)}
    assert set(got) == {"rej", "unk", "fit"}                                   # recovered and clean evaluations are not failures
    assert got["rej"]["configs"] == ["E1", "E4"] and got["rej"]["category"] == "DC syntax error (VER-294)" and got["rej"]["role"] == "B0 candidate" and got["rej"]["failed_status"] == ["analyze_failed"]
    assert got["unk"]["category"] == "other (timeout)"
    assert got["fit"]["configs"] == ["Y"] and got["fit"]["category"].startswith("Yosys")
    assert X.failure_category({"failed_status": "link_failed", "error": "Error: Width mismatch on port 'in' (LINK-3)"}) == ("link_failed", "DC link: port width mismatch (LINK-3)")
    assert X.failure_category({}) == ("?", "other (?)")



def test_duplicates_report_counts_by_design_generation_gap_and_across_runs(tmp_path):
    """G5 item 4 (d): duplicates (same RTL text within a run) by design and generation, the generation gap to the repeated
    answer, and identical rewrites of different runs of one design (same content hash); literature objects never count."""
    import json
    from src.db import core as db
    import scripts.phase4_exp1 as P4
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    for rid, arm in (("r1", "B0"), ("r2", "B0"), ("lit", P4.LIT_ARM)):
        db.insert(conn, "runs", {"run_id": rid, "exp": "phase4", "arm": arm, "design_id": "dA", "seed": 1, "status": "done"})
    rows = [("a", "r1", "dA", 1, None, "h1"), ("b", "r1", "dA", 2, "duplicate", "h1"), ("c", "r1", "dA", 3, None, "h3"), ("c2", "r1", "dA", 3, "duplicate", "h3"),
            ("x", "r2", "dA", 1, None, "h1"), ("y", "r2", "dA", 2, None, "h9"), ("l1", "lit", "dA", 0, None, "h1")]
    for cid, rid, did, gen, label, ch in rows:
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": rid, "design_id": did, "gen": gen, "label": label, "content_hash": ch, "arm": "B0" if rid != "lit" else P4.LIT_ARM})
    db.insert(conn, "diagnoses", {"cand_id": "b", "label": "duplicate", "evidence_json": json.dumps({"duplicate_of": "a"}), "credit": 0})
    db.insert(conn, "diagnoses", {"cand_id": "c2", "label": "duplicate", "evidence_json": json.dumps({"duplicate_of": "c"}), "credit": 0})
    out = P4.collect_duplicates(conn, "phase4")
    assert out["n_duplicates"] == 2 and out["n_candidates"] == 7 and out["by_arm"] == {"B0": 2}
    assert out["by_design"]["dA"] == {"candidates": 7, "duplicates": 2, "share": round(2 / 7, 4)}
    assert out["by_gen"]["2"]["duplicates"] == 1 and out["by_gen"]["3"] == {"candidates": 2, "duplicates": 1, "share": 0.5}
    assert out["gap_to_original"] == {"0": 1, "1": 1} and out["runs_with_duplicates"] == 1 and out["max_per_run"] == 2
    assert out["cross_run_identical"] == {"groups": 1, "runs_involved": 2, "by_design": {"dA": 1}}   # a (r1) and x (r2) share h1; the literature object does not count
