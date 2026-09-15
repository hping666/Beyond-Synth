"""Bidirectional tests of the M6 rule classifier, rules version 2 (spec 04 §A; DECISIONS 2026-09-14 pre-Phase-4 task a)
on synthetic rewrites of one design (Yosys word-level statistics): combinational rewrite -> (a), register renaming /
restructuring -> (b), width reduction -> (b), added registers with the same latency -> (c1), a lock-step offset -> (c2),
an operator family gained -> (d), a collapsed carry chain -> (d); and the negative direction: a wide text diff without
operator or topology evidence never yields (d), an operator family lost is not (d), a loop variable is not a register."""
import os
from pathlib import Path

import pytest

from src import config as C
from src.classify import rules as R
from src.designs import yosys_probe as YP

CFG = C.load()
pytestmark = pytest.mark.skipif(not os.path.exists(CFG["tools"]["yosys"]["bin"]), reason="yosys binary missing")

D = """module top(input clk, input rst_n, input [7:0] a, input [7:0] b, output reg [8:0] y);
  reg [7:0] ra, rb;
  wire [8:0] s = ra + rb;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin ra <= 0; rb <= 0; y <= 0; end
    else begin ra <= a; rb <= b; y <= s; end
  end
endmodule
"""
A = D.replace("wire [8:0] s = ra + rb;", "wire [8:0] s = rb + ra + 9'd0;")
B = D.replace("reg [7:0] ra, rb;", "reg [7:0] ra;\n  reg [7:0] rb;").replace("ra <= a; rb <= b; y <= s;", "rb <= b; ra <= a; y <= s;").replace("ra, rb", "ra;\n  reg [7:0] rb")
C1 = """module top(input clk, input rst_n, input [7:0] a, input [7:0] b, output reg [8:0] y);
  reg [8:0] rs;
  wire [8:0] s = a + b;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin rs <= 0; y <= 0; end
    else begin rs <= s; y <= rs; end
  end
endmodule
"""   # the operand registers moved behind the adder (retiming): same latency, 25 -> 18 bits, 3 -> 2 register cells
WIDTH = D.replace("reg [7:0] ra, rb;", "reg [3:0] ra, rb;").replace("ra <= a; rb <= b;", "ra <= a[3:0]; rb <= b[3:0];")   # narrower operand registers, same cells
MUL = D.replace("wire [8:0] s = ra + rb;", "wire [8:0] s = ra * rb;")                                                # operator family gained
# a hand-built 8-bit ripple adder (carry chain of 8 full adders) versus the behavioural `+`: the longest path collapses
RIPPLE_D = """module top(input [7:0] a, input [7:0] b, output [8:0] y);
  wire [8:0] c; assign c[0] = 1'b0;
  genvar i;
  generate for (i = 0; i < 8; i = i + 1) begin : g
    assign y[i] = a[i] ^ b[i] ^ c[i];
    assign c[i+1] = (a[i] & b[i]) | (a[i] & c[i]) | (b[i] & c[i]);
  end endgenerate
  assign y[8] = c[8];
endmodule
"""
RIPPLE_C = "module top(input [7:0] a, input [7:0] b, output [8:0] y);\n  assign y = {1'b0, a} + {1'b0, b};\nendmodule\n"
LOOP_D = """module top(input clk, input rst, input [3:0] din, output reg [3:0] q);
  reg [3:0] mem [0:3]; integer i;
  always @(posedge clk) begin
    if (rst) begin for (i = 0; i < 4; i = i + 1) mem[i] <= 4'h0; q <= 4'h0; end
    else begin mem[0] <= din; mem[1] <= mem[0]; mem[2] <= mem[1]; mem[3] <= mem[2]; q <= mem[3]; end
  end
endmodule
"""   # a 4-deep shift chain through a small memory, reset by a `for` loop whose 32-bit loop variable is a register before opt
LOOP_C = LOOP_D.replace("integer i;", "").replace("for (i = 0; i < 4; i = i + 1) mem[i] <= 4'h0;", "mem[0] <= 4'h0; mem[1] <= 4'h0; mem[2] <= 4'h0; mem[3] <= 4'h0;")
# a wide recode of the same registers: the same next-state logic written through renamed wires and a case
WIDE_A = """module top(input clk, input rst_n, input [7:0] a, input [7:0] b, output reg [8:0] y);
  reg [7:0] ra, rb;
  wire [8:0] sum_wide = {1'b0, ra} + {1'b0, rb};
  wire [8:0] pick = sum_wide;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin ra <= 8'd0; rb <= 8'd0; y <= 9'd0; end
    else begin
      case (1'b1)
        1'b1: begin ra <= a; rb <= b; y <= pick; end
        default: begin ra <= ra; rb <= rb; y <= y; end
      endcase
    end
  end
endmodule
"""


def w(p, text):
    p.write_text(text)
    return p


def feats(tmp_path, cand_text, offsets=None, d_text=D):
    tmp_path.mkdir(parents=True, exist_ok=True)
    d = w(tmp_path / "d.v", d_text)
    c = w(tmp_path / "c.v", cand_text)
    return R.features([d], [c], "top", CFG, workdir=tmp_path / "wd", offsets=offsets)


def test_structural_classes_from_rules(tmp_path):
    fa = feats(tmp_path / "a", A)
    ra = R.classify(fa, CFG)
    assert fa["ff_d"] == fa["ff_c"] == 25 and ra["class_rule"] == "a" and not ra["needs_review"] and ra["rules_version"] == 2
    fb = feats(tmp_path / "b", B)
    assert fb["ff_c"] == 25 and R.classify(fb, CFG)["class_rule"] == "a"  # same registers, only the declaration style and order changed
    fc = feats(tmp_path / "c", C1)
    rc = R.classify(fc, CFG)
    assert fc["ff_c"] == 18 and fc["ff_cells_c"] == fc["ff_cells_d"] - 1 and rc["class_rule"] == "c1"
    fw = feats(tmp_path / "w", WIDTH)
    rw = R.classify(fw, CFG)
    assert fw["ff_c"] == 17 and fw["ff_cells_c"] == fw["ff_cells_d"] and rw["class_rule"] == "b"  # narrower registers, same cells: bit width, not retiming
    fc2 = feats(tmp_path / "c2", A, offsets={"y": 1})
    assert R.classify(fc2, CFG)["class_rule"] == "c2" and not R.classify(fc2, CFG)["needs_review"]


def test_d_requires_operator_or_topology_evidence(tmp_path):
    fm = feats(tmp_path / "mul", MUL)
    rm = R.classify(fm, CFG)
    assert fm["ops_d"] == ["add"] and fm["ops_c"] == ["mul"] and rm["class_rule"] == "d" and "operator family gained: mul" in rm["rules"][0]
    # the same operator family lost (the `+` removed) is ordinary recoding, not (d)
    fl = feats(tmp_path / "lost", D.replace("wire [8:0] s = ra + rb;", "wire [8:0] s = {ra[7] ^ rb[7], ra ^ rb};"))
    assert fl["ops_c"] == [] and R.classify(fl, CFG)["class_rule"] == "a"
    fr = feats(tmp_path / "ripple", RIPPLE_C, d_text=RIPPLE_D)
    rr = R.classify(fr, CFG)
    assert fr["ff_d"] == fr["ff_c"] == 0 and R.depth_ratio(fr) >= 3.0 and rr["class_rule"] == "d"  # combinational designs reach (d)
    assert R.classify(fr, CFG, d_depth_ratio=1e9)["class_rule"] == "d"                              # ... also via the `+` gained
    assert R.classify({**fr, "ops_c": fr["ops_d"]}, CFG, d_depth_ratio=1e9)["class_rule"] == "a"    # neither evidence: not (d)
    # a wide text diff alone never yields (d) any more: the recode keeps its structural class and is flagged for review
    fwide = feats(tmp_path / "wide", WIDE_A)
    rwide = R.classify(fwide, CFG, d_diff_min=0.2)
    assert fwide["diff_ratio"] >= 0.2 and rwide["class_rule"] == "a" and rwide["needs_review"] and any("review" in s for s in rwide["rules"])
    v1_style = {"ff_d": 8, "ff_c": 12, "ff_cells_d": 2, "ff_cells_c": 3, "regs_d": ["r1"], "regs_c": ["s1", "s2"], "targets_d": ["r1"], "targets_c": ["s1", "s2"],
                "diff_ratio": 0.9, "max_offset": 0, "ops_d": ["add"], "ops_c": ["add"], "depth_d": 4, "depth_c": 5}
    assert R.classify(v1_style, CFG)["class_rule"] == "c1"   # rules v1 said (d) here on the diff ratio alone


def test_loop_variable_is_not_a_register_and_targets_cover_blocking_assignments(tmp_path):
    f = feats(tmp_path / "loop", LOOP_C, d_text=LOOP_D)
    assert f["ff_d"] == f["ff_c"] == 20 and f["ff_cells_d"] == f["ff_cells_c"]      # 4 x 4 memory bits + q; the 32-bit `integer i` is not counted
    assert YP.probe([tmp_path / "loop" / "d.v"], "top", CFG, workdir=tmp_path / "probe")["n_ff_bits"] == 52   # the inventory probe (no opt) still sees it
    assert f["targets_d"] == f["targets_c"] == ["mem", "q"] and R.classify(f, CFG)["class_rule"] == "a"


def test_text_features():
    assert R.register_names(D) == {"ra", "rb"} and R.seq_targets(D) == {"ra", "rb", "y"}
    assert R.register_names("module m; reg [3:0] q [0:7]; reg x; endmodule") == {"q", "x"}
    assert R.seq_targets("module m; always @(posedge clk) begin if (cnt <= 4'd7) x = 1; else x = 0; end endmodule") == {"x"}  # `<=` in a condition is a comparison
    assert R.diff_ratio(D, D) == 0.0 and 0 < R.diff_ratio(D, A) < 0.2
    assert R.diff_ratio("", "") == 0.0
    assert R.families_present({"$add": 2, "$mux": 5}, R.DEFAULTS["operator_families"]) == ["add"]
    assert R.families_present({"$mux": 5}, R.DEFAULTS["operator_families"]) == []
    b_rules = R.classify({"ff_d": 8, "ff_c": 8, "ff_cells_d": 1, "ff_cells_c": 1, "regs_d": ["r1"], "regs_c": ["s1"], "targets_d": ["r1"], "targets_c": ["s1"],
                          "diff_ratio": 0.1, "max_offset": 0, "ops_d": [], "ops_c": [], "depth_d": 2, "depth_c": 2}, CFG)
    assert b_rules["class_rule"] == "b" and not b_rules["needs_review"]
