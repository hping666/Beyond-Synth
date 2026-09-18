"""DECISION 2026-09-18 (f) item 1: the harness_version 2 source rewrite locates x / z literals with the Pyverilog AST and rewrites
only value positions (continuous / procedural right-hand sides, reset values); case items, casez / casex patterns, comparisons and
any '?' literal are never touched; an ambiguous line is left alone and reported; designs outside the list get byte-identical
copies. Both directions."""
from pathlib import Path

from src.equiv import xz_rewrite as X

RTL = """module t(input clk, input resetn, input rd, input en, input [3:0] sel, input [7:0] din, output reg [7:0] dout, output [7:0] bus, output reg [1:0] code, output reg flag);
  assign bus = en ? din : 8'bzzzzzzzz;                 // continuous: value position
  always @(posedge clk) begin
    if (!resetn) begin
      dout <= 8'bz;                                    // reset value
      flag <= 1'bx;                                    // reset value (x)
    end else begin
      if (rd) dout <= din; else dout <= 8'bzz;         // procedural
      if (sel == 4'b1xx0) flag <= 1'b1;                // comparison: never rewritten
      casez (sel)
        4'b1z??: code <= 2'd1;                         // casez pattern with z and ?: never rewritten
        4'b0zz0: code <= 2'd2;                         // casez pattern: never rewritten
        default: code <= 2'bx;                         // value position inside a case item body: rewritten
      endcase
      dout <= 4'b1?01 + din;                           // '?' in a value position: never rewritten
    end
  end
endmodule
"""


def test_value_positions_only(tmp_path):
    f = tmp_path / "t.v"; f.write_text(RTL)
    plan = X.analyze([f], rst_port="resetn")
    assert plan["errors"] == []
    assert plan["counts"] == {"continuous": 1, "procedural": 2, "reset_value": 2}          # 8'bzzzzzzzz; 8'bzz and 2'bx; 8'bz and 1'bx
    assert plan["skipped"]["comparison"] == 1 and plan["skipped"]["pattern"] == 1 and plan["skipped"]["question"] == 2   # 4'b1xx0; 4'b0zz0; 4'b1z?? and 4'b1?01
    paths, rep = X.rewrite_copies([f], tmp_path / "out", rst_port="resetn")
    out = Path(paths[0]).read_text()
    assert "8'b00000000" in out and "dout <= 8'b0;" in out and "flag <= 1'b0;" in out and "dout <= 8'b00;" in out and "code <= 2'b0;" in out
    assert "4'b1xx0" in out and "4'b1z??" in out and "4'b0zz0" in out and "4'b1?01" in out             # untouched
    assert rep["rewritten"] == {"t.v": 5} and rep["ambiguous"] == [] and rep["skipped"]["question"] == 2 and rep["skipped"]["pattern"] == 1
    assert f.read_text() == RTL                                                                       # the source is never modified
    # the other direction: a design outside the list is copied byte for byte
    same = X.identical_copies([f], tmp_path / "same")
    assert Path(same[0]).read_bytes() == f.read_bytes()


def test_ambiguous_line_is_left_alone(tmp_path):
    f = tmp_path / "a.v"
    f.write_text("module a(input [3:0] s, output reg [3:0] y);\n  always @* begin if (s == 4'bx1x1) y = 4'bx1x1; else y = 4'd0; end\nendmodule\n")
    paths, rep = X.rewrite_copies([f], tmp_path / "out")
    assert rep["ambiguous"] and Path(paths[0]).read_text() == f.read_text()                            # the same literal in a comparison and a value position: untouched, reported
