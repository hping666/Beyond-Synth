"""Bidirectional tests for the Phase 1 design-set code (src/designs/): Verilog helpers, RTLLM canonical-top
renaming, Dr.RTL / RTL-OPT staging, the RTLRewriter role rule, CktEvo pool selection, catalogue validation,
inventory application, designs-table upsert and job generation. Synthetic sources only (no Yosys, no DC)."""
import copy
import json
from pathlib import Path

import pytest

from src import config as C
from src.db import core as db
from src.designs import catalog as K
from src.designs import cktevo as CK
from src.designs import inventory as I
from src.designs import jobs as J
from src.designs import rtlrewriter as RW
from src.designs import stage as S
from src.designs import verilog as V

COMB = "input [7:0] a, output [7:0] y"
SEQ = "input clk, input [7:0] a, output reg [7:0] y"


def w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def module(name, ports=SEQ, body=None, lines=0):
    if body is None:
        body = "  always @(posedge clk) y <= a;\n" if "clk" in ports else "  assign y = a;\n"
    return f"module {name}({ports});\n{body}" + "  // pad\n" * lines + "endmodule\n"


def quiet(m):
    pass


@pytest.fixture
def env(tmp_path, monkeypatch):
    cfg = copy.deepcopy(C.load())
    monkeypatch.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    src = tmp_path / "src"
    for suite in cfg["design_sets"]["sources"]:
        cfg["design_sets"]["sources"][suite]["local"] = str(src / suite)
    return cfg, src


# ----------------------------------------------------------------------------- verilog helpers
def test_verilog_helpers_find_modules_instances_ports_and_flags():
    text = ("// module comment_only\nmodule top(input clk, input [3:0] a, b, output y);\n  sub #(.W(4)) u0 (.a(a));\n"
            "  leaf u1(.x(b));\n  always @(posedge clk) if (a) y <= 1; else y <= 0;\n  /* module fake */\nendmodule\n"
            "module leaf(input x); initial $display(1); #5 ; endmodule\n")
    assert V.module_names(text) == ["top", "leaf"]
    spans = V.module_spans(text)
    assert [s[0] for s in spans] == ["top", "leaf"] and spans[0][1] == 2 and spans[1][2] == 8
    assert V.instantiated_modules(spans[0][3]) == {"sub", "leaf"}
    ports = V.declared_ports(spans[0][3])
    assert ("clk", "input", False) in ports and ("a", "input", True) in ports and ("b", "input", True) in ports and ("y", "output", False) in ports
    f = V.flags(text)
    assert f["initial"] and f["sysfunc"] and f["delay"] and not f["include"] and not f["ifdef"]
    assert not V.flags("module x(input a); assign b = a; endmodule")["initial"]
    assert V.rename_identifier("module verified_accu(); verified_accu2 x; endmodule", "verified_accu", "accu") == "module accu(); verified_accu2 x; endmodule"
    assert V.instantiated_modules("always @(posedge clk) begin if (x) y <= f(z); end endcase if (q) r(") == set()


# ----------------------------------------------------------------------------- RTLLM
def test_rtllm_staging_renames_to_the_testbench_name_and_keeps_matching_names(env):
    cfg, src = env
    r = src / "rtllm"
    w(r / "A/accu/verified_accu.v", module("verified_accu"))
    w(r / "A/accu/testbench.v", "module tb;\n reg clk; wire [7:0] y;\n accu dut(.clk(clk), .a(8'd1), .y(y));\nendmodule\n")
    w(r / "A/accu/ref.dat", "1\n")
    w(r / "A/pipe/verified_pipe64.v", module("verified_pipe64") + module("helper", "input x, output z", "  assign z = x;\n"))
    w(r / "A/pipe/testbench.v", "module tb;\n pipe_x dut(.clk(1'b0), .a(8'd0), .y());\nendmodule\n")
    w(r / "A/plain/verified_plain.v", module("plain"))
    w(r / "A/plain/testbench.v", "module tb; plain dut(); endmodule")
    w(r / "A/bad/verified_bad.v", module("verified_bad") + module("verified_bad2"))
    w(r / "A/bad/testbench.v", "module tb; zz dut(); endmodule")
    designs, skipped = S.stage_rtllm(cfg, log=quiet)
    ids = {d["design_id"]: d for d in designs}
    assert set(ids) == {"rtllm_accu", "rtllm_pipe", "rtllm_plain"} and [n for n, _ in skipped] == ["bad"]
    accu = ids["rtllm_accu"]
    assert accu["top"] == "accu" and "module accu(" in (Path(accu["_dir"]) / "rtl/accu.v").read_text()
    assert accu["tb"] == {"files": ["tb/testbench.v"], "top": "tb", "data": ["tb/ref.dat"]} and accu["clk_ports"] == ["clk"]
    assert accu["notes"] and "renamed" in accu["notes"][0] and accu["source"]["paths"] == ["A/accu/verified_accu.v"]
    pipe = ids["rtllm_pipe"]
    txt = (Path(pipe["_dir"]) / "rtl/pipe.v").read_text()
    assert pipe["top"] == "pipe_x" and "verified_pipe64" not in txt and "module helper" in txt
    assert ids["rtllm_plain"]["top"] == "plain" and not ids["rtllm_plain"]["notes"]
    # catalogue round trip and both directions of validation
    d = K.load_design(accu["_dir"])
    assert K.validate(d) and d["sha256"]["rtl/accu.v"] == K.sha256_of(Path(d["_dir"]) / "rtl/accu.v")
    (Path(accu["_dir"]) / "rtl/accu.v").write_text("module accu(); endmodule\n")
    with pytest.raises(K.CatalogError, match="sha256"):
        K.validate(d)
    bad = dict(d)
    bad.pop("clk_ports")
    with pytest.raises(K.CatalogError, match="missing keys"):
        K.validate(bad, check_files=False)
    assert [x["design_id"] for x in K.load_all("rtllm")] == ["rtllm_accu", "rtllm_pipe", "rtllm_plain"]


# ----------------------------------------------------------------------------- Dr.RTL
def test_drrtl_staging_uses_design_all_json(env):
    cfg, src = env
    r = src / "drrtl"
    w(r / "syn_flow/design_all.json", json.dumps({"x": ["xtop", "clk", "rst_n", "v"], "y": ["ytop", "clk", "rstA", "sv"],
                                                  "missing": ["m", "clk", "rst", "v"], "wrongtop": ["nope", "clk", "rst", "v"]}))
    w(r / "rtl_dataset/x.v0.v", module("xtop", "input clk, input rst_n, input [7:0] a, output reg [7:0] y"))
    w(r / "rtl_dataset/y.v0.sv", module("ytop", "input clk, input rstA, input [7:0] a, output reg [7:0] y"))
    w(r / "rtl_dataset/wrongtop.v0.v", module("other"))
    w(r / "syn_flow_eda/tb/x.v", "module tb; xtop dut(); endmodule")
    designs, skipped = S.stage_drrtl(cfg, log=quiet)
    ids = {d["name"]: d for d in designs}
    assert set(ids) == {"x", "y"} and sorted(n for n, _ in skipped) == ["missing", "wrongtop"]
    assert ids["x"]["rst_port"] == "rst_n" and ids["x"]["rst_sense"] == "low" and ids["x"]["tb"]["files"] == ["tb/x.v"] and not ids["x"]["sverilog"]
    assert ids["y"]["rst_sense"] == "high" and ids["y"]["sverilog"] and any("guessed" in n for n in ids["y"]["notes"]) and ids["y"]["files"] == ["rtl/y.sv"]
    assert ids["y"]["tb"] is None and ids["y"]["clk_ports"] == ["clk"]


# ----------------------------------------------------------------------------- RTL-OPT
def test_rtlopt_staging_pairs_start_and_reference(env):
    cfg, src = env
    b = src / "rtlopt/benchmark"
    w(b / "foo/foo.v", module("foo", COMB))
    w(b / "foo_ref/foo_ref.v", module("foo_ref", COMB))
    w(b / "lone/lone.v", module("lone"))
    w(b / "badref/badref.v", module("badref"))
    w(b / "badref_ref/badref_ref.v", module("other"))
    designs, skipped = S.stage_rtlopt(cfg, log=quiet)
    assert [d["design_id"] for d in designs] == ["rtlopt_foo"] and sorted(n for n, _ in skipped) == ["badref", "lone"]
    d = designs[0]
    assert d["clk_ports"] == [] and d["reference"]["top"] == "foo_ref" and d["reference"]["files"] == ["reference/foo_ref.v"]
    assert "pair" in d["tags"] and d["sha256"]["reference/foo_ref.v"] and d["loc"] == 3


# ----------------------------------------------------------------------------- CktEvo
def test_cktevo_pool_rules_and_staging(env):
    cfg, src = env
    r = src / "cktevo/benchmark/r1"
    w(r / "top.v", '`include "timescale.v"\n' + module("top", SEQ, "  wire [7:0] m;\n  mid u0(.clk(clk), .a(a), .y(m));\n  leaf u1(.x(m[0]));\n  always @(posedge clk) y <= m;\n", lines=120))
    w(r / "mid.v", module("mid", SEQ, "  leaf u1(.x(a[0]));\n  always @(posedge clk) y <= a;\n", lines=110))
    w(r / "leaf.v", module("leaf", "input x", "", lines=5))
    w(r / "tb.v", "module tb;\n initial begin $finish; end\nendmodule\n")
    w(r / "timescale.v", "`timescale 1ns/1ps\n")
    w(r / "dup_a.v", module("dup", lines=150))
    w(r / "dup_b.v", module("dup", lines=150))
    w(r / "big.v", module("big", SEQ, "  dup u(.clk(clk), .a(a), .y(y));\n", lines=2000))
    w(r / "vendor.v", module("vend", SEQ, "  vendor_ram u(.clk(clk));\n", lines=120))
    params = cfg["design_sets"]["suites"]["cktevo"]
    params.update(loc_min=100, closure_loc_max=300)
    scan = CK.scan_repo(r)
    assert [h.name for h in scan["headers"]] == ["timescale.v"] and list(scan["duplicates"]) == ["dup"]
    pool = {p["module"]: p for p in CK.select_pool(scan, params)}
    assert pool["top"]["excluded"] == [] and pool["top"]["closure_modules"] == ["top", "leaf", "mid"]
    assert pool["mid"]["excluded"] == [] and "own_loc" in pool["leaf"]["excluded"][0]
    assert any("testbench" in x for x in pool["tb"]["excluded"])
    assert any("duplicate" in x for x in pool["dup"]["excluded"]) and any("closure_loc" in x for x in pool["big"]["excluded"])
    assert pool["vend"]["excluded"] == [] and pool["vend"]["unknown"] == ["vendor_ram"]  # flagged, decided by Yosys / DC
    designs, skipped = S.stage_cktevo(cfg, log=quiet)
    ids = {d["name"]: d for d in designs}
    assert set(ids) == {"r1__top", "r1__mid", "r1__vend"} and not skipped
    t = ids["r1__top"]
    assert t["files"] == ["rtl/top.v", "rtl/leaf.v", "rtl/mid.v"] and t["includes"] == ["rtl/timescale.v"] and t["incdirs"] == ["rtl"]
    assert t["top"] == "top" and t["clk_ports"] == ["clk"] and "rtl/timescale.v" in t["sha256"] and "r1" in t["tags"]
    assert any("unresolved" in n for n in ids["r1__vend"]["notes"])
    pool_json = json.loads((K.DESIGNS_DIR / "cktevo/POOL.json").read_text())
    assert {p["module"] for p in pool_json["repos"]["r1"]} == set(pool) and pool_json["params"] == {"loc_min": 100, "closure_loc_max": 300}


# ----------------------------------------------------------------------------- RTLRewriter
def test_rtlrewriter_roles_and_staging(env):
    cfg, src = env
    s, lg = src / "rtlrewriter/short_benchmark", src / "rtlrewriter/long_benchmark"
    w(s / "datapath/loop/loop_raw.v", module("loop", COMB))
    w(s / "datapath/loop/loop.v", module("loop", COMB))
    for n in ("basic.v", "basic_optimized.v", "add_gpt4.v", "add_ours.v", "optimized1.v"):
        w(s / "basic/add" / n, module("add", COMB))
    w(s / "fsm/ex1/ex1_state.v", module("ex1"))
    w(s / "fsm/ex1/ex1_state_optimized.v", module("ex1"))
    w(s / "fsm/ex1/ex1_state_test.v", "module t; ex1 dut(); endmodule")
    w(s / "mux/none/only_gpt4.v", module("m", COMB))
    w(s / "mux/red/red_redundancy.v", module("red", COMB))
    w(s / "mux/red/red.v", module("red", COMB))
    w(s / "mux/red/red_redundancy_improve.v", module("red", COMB))
    w(lg / "cpu/ALURaw.v", module("ALU_raw", COMB))
    w(lg / "cpu/ALU.v", module("ALU", COMB))
    w(lg / "cpu/Controller.v", module("Controller", COMB))
    w(lg / "cpu/PipelineCPURaw.v", module("PipelineCPU_raw", SEQ, "  ALU_raw a(.a(a), .y(y));\n  Controller c(.a(a), .y());\n"))
    w(lg / "cpu/PipelineCPU.v", module("PipelineCPU", SEQ, "  ALU a(.a(a), .y(y));\n  Controller c(.a(a), .y());\n"))
    w(lg / "cpu/RegFileRaw.v", module("RegFile", COMB))
    w(lg / "cpu/RegFile.v", module("RegFile", COMB))
    cases = {c["case"]: c for c in RW.short_cases(src / "rtlrewriter")}
    assert cases["loop"]["roles"] == {"loop_raw.v": "original", "loop.v": "expert"}
    assert cases["add"]["roles"] == {"basic.v": "original", "basic_optimized.v": "expert", "add_gpt4.v": "llm", "add_ours.v": "tool", "optimized1.v": "expert"}
    assert cases["ex1"]["roles"] == {"ex1_state.v": "original", "ex1_state_optimized.v": "expert", "ex1_state_test.v": "testbench"}
    assert cases["red"]["roles"] == {"red_redundancy.v": "original", "red.v": "expert", "red_redundancy_improve.v": "expert"}
    pairs = RW.long_pairs(src / "rtlrewriter")
    assert [(p[0], p[1]) for p in pairs] == [("cpu", "ALU"), ("cpu", "PipelineCPU"), ("cpu", "RegFile")]
    designs, skipped = S.stage_rtlrewriter(cfg, log=quiet)
    ids = {d["name"]: d for d in designs}
    assert ids["datapath__loop"]["files"] == ["rtl/loop_raw.v"] and ids["datapath__loop"]["reference"]["files"] == ["reference/loop.v"]
    add = ids["basic__add"]
    assert add["top"] == "add" and sorted(x["role"] for x in add["samples"]) == ["expert", "llm", "tool"] and add["tb"] is None
    assert add["reference"]["files"] == ["reference/basic_optimized.v"] and "calibration_only" in add["tags"]
    assert ids["fsm__ex1"]["tb"]["files"] == ["tb/ex1_state_test.v"] and ids["fsm__ex1"]["clk_ports"] == ["clk"]
    assert [n for n, _ in skipped] == ["mux__none"]
    cpu = ids["long_cpu__PipelineCPU"]
    assert cpu["top"] == "PipelineCPU_raw" and cpu["files"] == ["rtl/PipelineCPURaw.v", "rtl/ALURaw.v", "rtl/Controller.v"]
    assert cpu["reference"]["files"] == ["reference/PipelineCPU.v", "reference/ALU.v", "reference/Controller.v"] and cpu["reference"]["top"] == "PipelineCPU"
    rf = ids["long_cpu__RegFile"]
    assert rf["top"] == "RegFile" and rf["files"] == ["rtl/RegFileRaw.v"] and rf["reference"]["files"] == ["reference/RegFile.v"]


# ----------------------------------------------------------------------------- inventory, designs table, jobs
def test_inventory_application_designs_table_and_job_payloads(env, tmp_path):
    cfg, src = env
    b = src / "rtlopt/benchmark"
    w(b / "foo/foo.v", module("foo", COMB))
    w(b / "foo_ref/foo_ref.v", module("foo_ref", COMB))
    d = S.stage_rtlopt(cfg, log=quiet)[0][0]
    inv = {"loc": 3, "n_files": 1, "tb_available": 0, "sdc_available": 0, "flags": {"initial": False}, "yosys_ok": 1,
           "yosys_error": None, "ports": {"a": {"dir": "input", "width": 8}}, "ports_hash": "abc", "sverilog": True,
           "clk_ports": ["wclk", "rclk"], "rst_port": "rst", "rst_sense": "high", "n_inputs": 1, "n_outputs": 0, "in_bits": 8, "out_bits": 0}
    d = I.apply_inventory(d, inv)
    assert d["tags"] == ["rtlopt", "pair", "sverilog_only", "multi_clock"] and d["sverilog"] and d["clk_ports"] == ["wclk", "rclk"] and d["rst_sense"] == "high"
    d = I.apply_inventory(d, {**inv, "clk_ports": [], "rst_port": None, "rst_sense": None})
    assert d["tags"] == ["rtlopt", "pair", "no_clock"] and d["clk_ports"] == []
    assert d["rst_port"] == "rst" and d["rst_sense"] == "high"  # a reset the probe cannot see (synchronous, odd name) is kept
    d = I.apply_inventory(d, {"loc": 3, "n_files": 1, "tb_available": 0, "sdc_available": 0, "flags": {}, "yosys_ok": 0,
                              "yosys_error": "boom", "ports": None, "ports_hash": None})
    assert d["tags"] == ["rtlopt", "pair", "yosys_failed"] and K.load_design(d["_dir"])["inventory"]["yosys_error"] == "boom"
    row = I.designs_row(d)
    assert row["ports_hash"] is None and json.loads(row["tags"]) == d["tags"] and row["source_url"].startswith("https://") and row["path"].endswith("designs/rtlopt/foo")
    conn = db.connect(path=str(tmp_path / "db.sqlite"))
    assert I.upsert_design(conn, row)["loc"] == 3
    conn.execute("UPDATE designs SET e4_synthesizable=1, phi_main_ns_nangate45=1.4 WHERE design_id=?", (row["design_id"],))
    got = I.upsert_design(conn, {**row, "loc": 99})
    assert got["loc"] == 99 and got["e4_synthesizable"] == 1 and got["phi_main_ns_nangate45"] == 1.4
    assert conn.execute("SELECT COUNT(*) FROM designs").fetchone()[0] == 1
    # jobs
    j = J.trial_jobs(cfg, [d])[0]
    assert j["kind"] == "dc" and j["config"] == "E4" and j["payload"]["config"] == "E4"  # the runner reads the payload's config
    assert j["payload"]["clk_port"] is None and j["payload"]["is_baseline"] == 1
    assert j["payload"]["clock_ns"] == max(cfg["knee"]["periods_ns"]["nangate45"]) and j["timeout_sec"] == cfg["timeouts"]["dc_small"] * 60
    assert j["payload"]["rtl"] == [str(Path(d["_dir"]) / "rtl/foo.v")] and j["payload"]["top"] == "foo"
    d["clk_ports"], d["tags"] = ["wclk", "rclk"], ["rtlopt", "multi_clock"]
    assert J.dc_job(cfg, d, "E4", 1.0)["payload"]["clk_port"] == "wclk rclk"
    assert J.knee_jobs(cfg, [d], libs=["asap7"]) == []
    d["tags"] = ["rtlopt"]
    ks = J.knee_jobs(cfg, [d], libs=["asap7"])
    assert len(ks) == len(cfg["knee"]["periods_ns"]["asap7"]) and {k["config"] for k in ks} == {"K_asap7"}
    assert [k["payload"]["clock_ns"] for k in ks] == [float(p) for p in cfg["knee"]["periods_ns"]["asap7"]]
    assert J.timeout_for(cfg, 4000) == cfg["timeouts"]["dc_large"] * 60 and J.timeout_for(cfg, 1000) == cfg["timeouts"]["dc_medium"] * 60
