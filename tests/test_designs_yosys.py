"""Bidirectional tests of the Yosys interface probe (src/designs/yosys_probe.py): clock ports come from flip-flop
clock pins through the hierarchy (not from names), asynchronous resets carry their polarity, combinational designs
report no clock, and unparsable RTL raises. Yosys is open source and always installed; skipped only when missing."""
import os

import pytest

from src import config as C
from src.designs import yosys_probe as YP
from src.equiv.ports import PortError

CFG = C.load()
pytestmark = pytest.mark.skipif(not os.path.exists(CFG["tools"]["yosys"]["bin"]), reason="yosys binary missing")

TWO_CLOCKS = """
module sub(input WB_CLK_I, input [7:0] d, output reg [7:0] q);
  always @(posedge WB_CLK_I) q <= d;
endmodule
module top(input MTxClk, input WB_CLK_I, input clk_en, input rst_n, input [7:0] d, output reg [7:0] q1, output [7:0] q2);
  always @(posedge MTxClk or negedge rst_n) if (!rst_n) q1 <= 0; else if (clk_en) q1 <= d;
  sub u(.WB_CLK_I(WB_CLK_I), .d(d), .q(q2));
endmodule
"""
COMB = "module top(input clk, input [7:0] a, output [7:0] y); assign y = a + clk; endmodule\n"  # clk is data here


def test_clocks_and_async_reset_found_by_use(tmp_path):
    f = tmp_path / "t.v"
    f.write_text(TWO_CLOCKS)
    r = YP.probe([f], "top", CFG, workdir=tmp_path / "w")
    assert r["clock_ports"] == ["MTxClk", "WB_CLK_I"] and "clk_en" not in r["clock_ports"]
    assert r["async_resets"] == {"rst_n": "low"} and r["n_ff_bits"] == 16
    assert r["ports"]["d"] == {"dir": "input", "width": 8} and r["ports"]["q2"]["dir"] == "output"


def test_combinational_design_has_no_clock_even_if_a_port_is_called_clk(tmp_path):
    f = tmp_path / "c.v"
    f.write_text(COMB)
    r = YP.probe([f], "top", CFG, workdir=tmp_path / "w")
    assert r["clock_ports"] == [] and r["n_ff_bits"] == 0 and r["async_resets"] == {}


def test_active_high_reset_and_parse_error(tmp_path):
    f = tmp_path / "h.v"
    f.write_text("module top(input clk, input rst, input d, output reg q); always @(posedge clk or posedge rst) if (rst) q <= 0; else q <= d; endmodule\n")
    r = YP.probe([f], "top", CFG, workdir=tmp_path / "w")
    assert r["clock_ports"] == ["clk"] and r["async_resets"] == {"rst": "high"}
    bad = tmp_path / "bad.v"
    bad.write_text("module top(input clk); always @(posedge clk) begin endmodule\n")
    with pytest.raises(PortError):
        YP.probe([bad], "top", CFG, workdir=tmp_path / "w2")
