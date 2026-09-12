"""Bidirectional tests of the perturbation generator (src/noise/): every transform applies to a synthetic design
that offers sites, re-parses, is deterministic, and is proven equivalent to the original by Yosys (no license);
designs without sites raise NotApplicable; a deliberately broken 'transform' is caught by the same Yosys check
(so the check itself is not vacuous). generate() writes the files and the manifest."""
import copy
import os
from pathlib import Path

import pytest

from src import config as C
from src.equiv.yosys_equiv import yosys_equiv
from src.noise import generate as G
from src.noise import perturb as P
from src.noise import vast as V

CFG = C.load()
pytestmark = pytest.mark.skipif(not os.path.exists(CFG["tools"]["yosys"]["bin"]), reason="yosys binary missing")

DESIGN = """`timescale 1ns/1ps
module leaf(input [3:0] a, output [3:0] y);
  assign y = ~(a & 4'd5);
endmodule
module top(input clk, input rst_n, input [7:0] d, input [1:0] sel, input go, output reg [7:0] q, output reg [7:0] r, output [3:0] s);
  reg [7:0] acc;
  reg [7:0] stage;
  wire [7:0] masked;
  wire [3:0] low;
  localparam [7:0] LIM = 8'd200;
  assign masked = ~(d & 8'hf0) | d[3:0];
  assign low = masked[3:0];
  leaf u_leaf(.a(low), .y(s));
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      acc <= 8'd0;
      stage <= 8'd0;
    end else begin
      stage <= go ? d : stage;
      acc <= acc + stage;
    end
  end
  always @(posedge clk) begin
    case (sel)
      2'd0: q <= acc;
      2'd1, 2'd2: q <= masked;
      default: q <= LIM;
    endcase
    if (go) r <= acc; else r <= 8'd0;
  end
endmodule
"""
NO_SITES = "module top(input a, output y); assign y = a; endmodule\n"


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return p


def equivalent(tmp_path, gold_text, gate_text, tag):
    return yosys_equiv([write(tmp_path, f"{tag}_gold.v", gold_text)], [write(tmp_path, f"{tag}_gate.v", gate_text)], "top", CFG,
                       workdir=tmp_path / f"{tag}_wd")


@pytest.fixture
def parsed(tmp_path):
    src = write(tmp_path, "design.v", DESIGN)
    ast, directives = V.parse_files([src])
    return ast, directives


def test_yosys_equiv_check_is_not_vacuous(tmp_path):
    assert equivalent(tmp_path, DESIGN, DESIGN, "same") == "equivalent"
    broken = DESIGN.replace("acc <= acc + stage;", "acc <= acc - stage;")
    assert equivalent(tmp_path, DESIGN, broken, "broken") == "not_proven"


@pytest.mark.parametrize("ptype", P.TYPES)
def test_each_transform_applies_reparses_and_stays_equivalent(parsed, tmp_path, ptype):
    ast, directives = parsed
    before = V.emit(ast, directives)
    new_ast, details = P.TRANSFORMS[ptype](ast, "seed", 0)
    text = V.emit(new_ast, directives)
    assert details and text != before, ptype
    assert V.emit(ast, directives) == before  # the input AST is untouched (deep copy)
    V.parse_files([write(tmp_path, f"{ptype}.v", text)])  # re-parses
    if ptype == "P1_rename":
        # Yosys equiv_make pairs state by name, so a renamed design is checked by inverting the mapping instead
        back = text
        for mapping in details["renamed"].values():
            for old_name, new_name in mapping.items():
                back = back.replace(new_name, old_name)
        assert back == before
    else:
        assert equivalent(tmp_path, DESIGN, text, ptype) == "equivalent", text
    again = V.emit(P.TRANSFORMS[ptype](ast, "seed", 0)[0], directives)
    assert again == text  # deterministic
    other = V.emit(P.TRANSFORMS[ptype](ast, "seed", 1)[0], directives)
    assert other != text or ptype == "P2_reorder"  # a different k gives a different rewrite (P2 with two sites may repeat)


def test_p1_keeps_ports_instances_and_module_names(parsed):
    ast, directives = parsed
    new_ast, details = P.p1_rename(ast, "seed", 0)
    text = V.emit(new_ast, directives)
    for kept in ("module top", "module leaf", "u_leaf", "clk", "rst_n", "input [7:0] d", "output reg [7:0] q", "output [3:0] s"):
        assert kept in text, kept
    mapping = details["renamed"]["top"]
    assert set(mapping) == {"acc", "stage", "masked", "low", "LIM"} and all(v not in DESIGN for v in mapping.values())
    assert "acc" not in text.replace("u_leaf", "")


def test_not_applicable_on_designs_without_sites(tmp_path):
    ast, _ = V.parse_files([write(tmp_path, "n.v", NO_SITES)])
    for ptype in P.TYPES:
        with pytest.raises(P.NotApplicable):
            P.TRANSFORMS[ptype](ast, "seed", 0)


def test_p3_and_p4_site_kinds(parsed):
    ast, _ = parsed
    kinds = set()
    for k in range(6):
        kinds |= set(P.p3_expr(ast, "s", k, max_sites=6)[1]["expr_sites"])
    assert kinds == {"const", "demorgan", "partselect"}
    kinds = set()
    for k in range(6):
        kinds |= set(P.p4_ctrl(ast, "s", k, max_sites=3)[1]["ctrl_sites"])
    assert {"case_to_if", "ternary_to_if", "if_to_ternary"} <= kinds
    assert P._const_swap("8'd200") == "8'hc8" and P._const_swap("8'hf0") == "8'd240" and P._const_swap("4'b1010") is None
    assert P._const_swap("'d3") == "'h3"


def test_generate_writes_files_and_manifest(tmp_path, monkeypatch):
    cfg = copy.deepcopy(CFG)
    cfg["noise"]["n_per_type"] = 2
    ddir = tmp_path / "designs" / "synth" / "top"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "top.v").write_text(DESIGN)
    d = {"design_id": "synth_top", "suite": "synth", "name": "top", "top": "top", "files": ["rtl/top.v"], "incdirs": [], "_dir": str(ddir)}
    m = G.generate(d, cfg, out_root=tmp_path / "perts")
    assert m["error"] is None and m["roundtrip"]["pert_id"].startswith("p") and (tmp_path / "perts" / "synth_top" / "roundtrip.v").exists()
    assert len(m["perturbations"]) == 8 and {p["ptype"] for p in m["perturbations"]} == set(P.TYPES) and not m["not_applicable"]
    ids = [p["pert_id"] for p in m["perturbations"]]
    assert len(set(ids)) == len(ids) and all((Path(C.ROOT) / p["path"]).exists() or (tmp_path / "perts" / "synth_top" / Path(p["path"]).name).exists() for p in m["perturbations"])
    (ddir / "rtl" / "top.v").write_text(NO_SITES)
    m2 = G.generate(d, cfg, out_root=tmp_path / "perts2")
    assert not m2["perturbations"] and set(m2["not_applicable"]) == set(P.TYPES)
    (ddir / "rtl" / "top.v").write_text("module top(input a, output y); assign y = a endmodule\n")
    assert G.generate(d, cfg, out_root=tmp_path / "perts3")["error"].startswith("parse:")
