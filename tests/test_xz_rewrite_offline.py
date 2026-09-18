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
      code <= {2{1'bz}};                               // reset value inside a replication (tv80 line 100 pattern)
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
    assert plan["counts"] == {"continuous": 1, "procedural": 2, "reset_value": 3}          # 8'bzzzzzzzz; 8'bzz and 2'bx; 8'bz, 1'bx and {2{1'bz}}
    assert plan["skipped"]["comparison"] == 1 and plan["skipped"]["pattern"] == 1 and plan["skipped"]["question"] == 2   # 4'b1xx0; 4'b0zz0; 4'b1z?? and 4'b1?01
    paths, rep = X.rewrite_copies([f], tmp_path / "out", rst_port="resetn")
    out = Path(paths[0]).read_text()
    assert "8'b00000000" in out and "dout <= 8'b0;" in out and "flag <= 1'b0;" in out and "dout <= 8'b00;" in out and "code <= 2'b0;" in out and "code <= {2{1'b0}};" in out
    assert "4'b1xx0" in out and "4'b1z??" in out and "4'b0zz0" in out and "4'b1?01" in out             # untouched
    assert rep["rewritten"] == {"t.v": 6} and rep["ambiguous"] == [] and rep["skipped"]["question"] == 2 and rep["skipped"]["pattern"] == 1
    assert f.read_text() == RTL                                                                       # the source is never modified
    # the other direction: a design outside the list is copied byte for byte
    same = X.identical_copies([f], tmp_path / "same")
    assert Path(same[0]).read_bytes() == f.read_bytes()


def test_ambiguous_line_is_left_alone(tmp_path):
    f = tmp_path / "a.v"
    f.write_text("module a(input [3:0] s, output reg [3:0] y);\n  always @* begin if (s == 4'bx1x1) y = 4'bx1x1; else y = 4'd0; end\nendmodule\n")
    paths, rep = X.rewrite_copies([f], tmp_path / "out")
    assert rep["ambiguous"] and Path(paths[0]).read_text() == f.read_text()                            # the same literal in a comparison and a value position: untouched, reported


RTL2 = """module u(input clk, input rstn, input [3:0] a, input sel, output reg [7:0] y, output [3:0] w);
  parameter P = 4'bx1x1;                                 // parameter: never rewritten
  localparam L = 8'hzz;                                  // localparam: never rewritten
  reg [3:0] init = 4'bzz00;                              // declaration initializer: not a value position of the rule (untouched)
  function [3:0] f; input [3:0] v; f = v ^ 4'b0001; endfunction
  assign w = sel ? f(4'bzz10) : {2'bx, a[1:0]};           // ternary, function argument, concatenation: value positions
  always @(posedge clk) begin
    case (a)
      4'b1x00: y <= 8'd1;                                // plain case item: a pattern, never rewritten
      default: y <= 8'd0;
    endcase
    casex (a)
      4'b1xz0: y <= 8'd2;                                // casex pattern: never rewritten
      default: y <= {4{2'bz1}};                          // replication value: rewritten
    endcase
  end
endmodule
"""


def test_classifier_covers_every_literal_context(tmp_path):
    """DECISION 2026-09-18 (h) item 2: replication, concatenation, ternaries and function arguments are value positions; declaration
    initializers, parameters, localparams and the items of case, casez and casex are not; each is exercised."""
    f = tmp_path / "u.v"; f.write_text(RTL2)
    plan = X.analyze([f], rst_port="rstn")
    assert plan["errors"] == []
    assert plan["counts"] == {"continuous": 2, "procedural": 1, "reset_value": 0}     # 4'bzz10 (a function argument in the ternary) and 2'bx (a concatenation) on the assign; {4{2'bz1}}
    assert plan["skipped"]["pattern"] == 2 and plan["skipped"]["question"] == 0 and plan["skipped"]["other"] == 3   # case + casex items; parameter, localparam, initializer
    paths, rep = X.rewrite_copies([f], tmp_path / "out", rst_port="rstn")
    out = Path(paths[0]).read_text()
    assert "f(4'b0010)" in out and "{2'b0, a[1:0]}" in out and "{4{2'b01}}" in out                      # rewritten
    assert "parameter P = 4'bx1x1;" in out and "localparam L = 8'hzz;" in out and "init = 4'bzz00;" in out   # untouched
    assert "4'b1x00: y" in out and "4'b1xz0: y" in out and rep["ambiguous"] == []                      # patterns untouched
