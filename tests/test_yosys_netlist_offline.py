"""Bidirectional tests of the Yosys runner's structural-netlist rule (2026-09-14: `$display` survived as `$print` cells
and unmapped latches as `always @*` blocks, both unreadable by OpenSTA): the checker catches behavioural lines and passes
a gate-level netlist; with the real Yosys, `delete t:$print` plus the library latch techmap turn a design with a
`$display` and a latch into a structural netlist, and the same design without them does not."""
import os
import subprocess
from pathlib import Path

import pytest

from src import config as C
from src.eval import yosys as Y

CFG = C.load()
YOSYS = CFG["tools"]["yosys"]["bin"]
LIB = CFG["libs"]["nangate45"]
RTL = """module top(input clk, input en, input [3:0] d, output reg [3:0] q, output reg [3:0] l);
  always @(posedge clk) begin
    q <= d;
    if (d == 4'd3) $display("three");
  end
  always @* if (en) l = d;
endmodule
"""


def test_checker_both_directions(tmp_path):
    good = tmp_path / "good.v"
    good.write_text("module top(input a, output y);\n  wire n;\n  INV_X1 u0 (.A(a), .ZN(n));\n  BUF_X1 u1 (.A(n), .Z(y));\nendmodule\n")
    assert Y.structural_netlist_problems(good) == []
    bad = tmp_path / "bad.v"
    bad.write_text("module top(input a, output reg y);\n  always @*\n    if (a) y = 1'b0;\n  initial y = 0;\n  always @(posedge a) $write(\"x\");\nendmodule\n")
    probs = Y.structural_netlist_problems(bad)
    assert len(probs) == 3 and probs[0].startswith("line 2:") and "initial" in probs[1] and "$write" in probs[2]
    assert Y.structural_netlist_problems(tmp_path / "missing.v")[0].startswith("netlist unreadable")
    expr = tmp_path / "expr.v"
    expr.write_text("module top(input c, input a, input b, output y, output z, output w);\n  wire n;\n  assign n = a;\n  assign z = 1'b0;\n  assign y = c ? a : b;\n  assign w = a & ~b;\nendmodule\n")
    probs = Y.structural_netlist_problems(expr)
    assert len(probs) == 2 and "c ? a : b" in probs[0] and "a & ~b" in probs[1]   # wire-to-wire and constant assigns pass, expressions do not


@pytest.mark.skipif(not os.path.exists(YOSYS) or not LIB.get("latch_map") or not os.path.exists(LIB["latch_map"]), reason="yosys or the ORFS latch map missing")
def test_nodisplay_and_latch_map_give_a_structural_netlist(tmp_path):
    rtl = tmp_path / "top.v"
    rtl.write_text(RTL)
    lib = LIB["liberty"]

    def run(read_opts, latch):
        out = tmp_path / f"net_{len(read_opts)}_{int(latch)}.v"
        steps = [f"read_verilog {read_opts} {rtl}", "hierarchy -check -top top", "synth -top top"]
        if latch:
            steps += ["delete t:$print", f"techmap -map {LIB['latch_map']}"]
        steps += [f"dfflibmap -liberty {lib}", f"abc -liberty {lib}", "opt_clean -purge", f"write_verilog -noattr {out}"]
        p = subprocess.run([YOSYS, "-q", "-p", "; ".join(steps)], capture_output=True, text=True, timeout=300)
        assert p.returncode == 0, p.stderr[-500:]
        return Y.structural_netlist_problems(out)

    assert run("-nodisplay", True) == []                                   # the fix: nothing behavioural left
    without = run("", False)
    assert any("always" in x for x in without)                              # without: the latch (and the print) survive as always blocks


@pytest.mark.skipif(not os.path.exists(YOSYS) or not os.path.exists(CFG["tools"]["opensta"]["bin"]) or not LIB.get("liberty") or not os.path.exists(LIB["liberty"]),
                    reason="yosys / opensta / liberty missing")
def test_runner_end_to_end_reports_area_timing_and_power(tmp_path):
    """The Y runner on the display-plus-latch design: status ok, area and cells, WNS parsed, OpenSTA power (mW) present
    (the third component of the Y-caliber fitness), and the print / latch constructs gone."""
    rtl = tmp_path / "top.v"
    rtl.write_text(RTL)
    rec = Y.run_yosys(tmp_path / "job", [rtl], "top", "nangate45", CFG["configs"]["Y"]["script"], 1.0, "clk", CFG, timeout_sec=300)
    assert rec["status"] == "ok", rec.get("error")
    m = rec["metrics"]
    assert m["area"] > 0 and m["cells"] > 0 and m.get("wns_ns") is not None
    assert m.get("power_default_mw") is not None and m["power_default_mw"] > 0
    assert Y.structural_netlist_problems(rec["netlist"]) == [] and any(k.startswith("DLH") or k.startswith("DLL") for k in rec["hist"])
