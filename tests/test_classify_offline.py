"""Bidirectional tests of the M6 rule classifier (spec 04 §A) on synthetic rewrites of one design (Yosys probe for
flip-flop counts): combinational rewrite -> (a), register renaming / restructuring -> (b), added registers with the
same latency -> (c1), a lock-step offset -> (c2), a wide rewrite -> (d)."""
import os
from pathlib import Path

import pytest

from src import config as C
from src.classify import rules as R

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
C1 = D.replace("output reg [8:0] y", "output reg [8:0] y").replace("wire [8:0] s = ra + rb;", "reg [8:0] s;\n  always @(*) s = ra + rb;\n  reg [7:0] rc;") \
      .replace("ra <= a; rb <= b; y <= s;", "ra <= a; rb <= b; rc <= a; y <= s;")
DD = """module top(input clk, input rst_n, input [7:0] a, input [7:0] b, output reg [8:0] y);
  reg [8:0] acc; reg [3:0] cnt; reg [7:0] sa; reg [7:0] sb; wire [8:0] m = {1'b0, sa} + {1'b0, sb};
  always @(posedge clk or negedge rst_n) if (!rst_n) begin acc <= 0; cnt <= 0; sa <= 0; sb <= 0; y <= 0; end
    else begin cnt <= cnt + 1; sa <= a ^ b; sb <= a & b; acc <= m; y <= acc + cnt; end
endmodule
"""


def w(p, text):
    p.write_text(text)
    return p


def feats(tmp_path, cand_text, offsets=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    d = w(tmp_path / "d.v", D)
    c = w(tmp_path / "c.v", cand_text)
    return R.features([d], [c], "top", CFG, workdir=tmp_path / "wd", offsets=offsets)


def test_classes_from_rules(tmp_path):
    fa = feats(tmp_path / "a", A)
    assert fa["ff_d"] == fa["ff_c"] == 25 and R.classify(fa)["class_rule"] == "a" and not R.classify(fa)["needs_review"]
    fb = feats(tmp_path / "b", B)
    rb = R.classify(fb)
    assert fb["ff_c"] == 25 and rb["class_rule"] == "a"  # same registers, only the declaration style and order changed
    fc = feats(tmp_path / "c", C1)
    rc = R.classify(fc)
    assert fc["ff_c"] == 33 and rc["class_rule"] == "c1" and rc["needs_review"]
    fc2 = feats(tmp_path / "c2", A, offsets={"y": 1})
    assert R.classify(fc2)["class_rule"] == "c2" and not R.classify(fc2)["needs_review"]
    fd = feats(tmp_path / "dd", DD)
    rd = R.classify(fd, d_diff_min=0.25)  # the threshold is calibrated in Phase 3/4; the mechanism is what is tested
    assert fd["diff_ratio"] >= 0.25 and rd["class_rule"] == "d" and rd["needs_review"]
    assert R.classify(fd, d_diff_min=0.9)["class_rule"] == "c1"  # below the threshold the register change decides


def test_text_features():
    assert R.register_names(D) == {"ra", "rb"} and R.seq_targets(D) == {"ra", "rb", "y"}
    assert R.register_names("module m; reg [3:0] q [0:7]; reg x; endmodule") == {"q", "x"}
    assert R.diff_ratio(D, D) == 0.0 and 0 < R.diff_ratio(D, A) < 0.2 and R.diff_ratio(D, DD) > 0.25
    assert R.diff_ratio("", "") == 0.0
    b_rules = R.classify({"ff_d": 8, "ff_c": 8, "regs_d": ["r1"], "regs_c": ["s1"], "targets_d": ["r1"], "targets_c": ["s1"], "diff_ratio": 0.1, "max_offset": 0})
    assert b_rules["class_rule"] == "b"
