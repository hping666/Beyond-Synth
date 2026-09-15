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
    finally:
        monkey.undo()
