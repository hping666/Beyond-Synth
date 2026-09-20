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
    ast, directives, _ = V.parse_files([src])
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
    ast, _, _ = V.parse_files([write(tmp_path, "n.v", NO_SITES)])
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


def test_normalisation_splits_signed_declarations_and_refuses_reg_initialisers(tmp_path):
    text = ("module top (\n    input clk,\n    input signed [7:0] a, b,\n    output reg signed [7:0] z\n);\n"
            "    wire signed [15:0] t, u;\n    assign t = a * b + (1<<7);\n    assign u = t;\n"
            "    always @(posedge clk) z <= u[15:8];\nendmodule\n")
    norm, notes = V.normalise_text(text)
    assert "input signed [7:0] a, input signed [7:0] b," in norm and "wire signed [15:0] t; wire signed [15:0] u;" in norm and len(notes) == 2
    ast, directives, notes2 = V.parse_files([write(tmp_path, "mul.v", text)])
    out = V.emit(ast, directives)
    assert out.count("signed") == 5 and notes2 == notes  # every name keeps `signed` after the re-print
    assert equivalent(tmp_path, text, out, "signed") == "equivalent"
    plain = "module p(input [3:0] a, b, output [3:0] y); assign y = a & b; endmodule\n"
    assert V.normalise_text(plain) == (plain, [])  # unsigned multi-name declarations are left alone
    with pytest.raises(V.Unsupported):
        V.normalise_text("module r(input clk, output reg q); reg [3:0] data = 'd0; always @(posedge clk) q <= data[0]; endmodule\n")
    assert V.normalise_text("module w(input a, output y); wire t = a; assign y = t; endmodule\n")[0]  # wire initialisers are legal continuous assignments


def test_p4_never_turns_an_async_reset_if_into_a_ternary(tmp_path):
    text = ("module top(input clk, input rst_n, input d, output reg q, output reg r);\n"
            "  always @(posedge clk or negedge rst_n) begin\n    if (!rst_n) q <= 1'b0; else q <= d;\n  end\n"
            "  always @(posedge clk) begin\n    if (d) r <= 1'b1; else r <= 1'b0;\n  end\nendmodule\n")
    ast, directives, _ = V.parse_files([write(tmp_path, "ar.v", text)])
    kinds = set()
    for k in range(6):
        new_ast, details = P.p4_ctrl(ast, "s", k, max_sites=3)
        out = V.emit(new_ast, directives)
        assert "if(!rst_n)" in out.replace(" ", "") or "if(!rst_n)" in out  # the async reset stays an if
        kinds |= set(details["ctrl_sites"])
        assert equivalent(tmp_path, text, out, f"ar{k}") == "equivalent"
    assert kinds == {"if_to_ternary"}  # only the synchronous block was rewritten


def test_text_level_p1_renamer_renames_internals_only(tmp_path):
    """DECISIONS 2026-09-14 G1.2: the text renamer changes internal identifiers everywhere they occur, never ports, module
    or instance names, named port connections, escaped identifiers or keywords; the result stays equivalent (Yosys self-test)."""
    from src.noise import rename_text as RT
    from src.noise import vast as V
    src = tmp_path / "top.v"
    src.write_text("""module leaf(input a, input b, output y);
  wire t; assign t = a & b; assign y = t;
endmodule
module top(input clk, input a, input b, output reg q, output y2);
  wire t;               // same name as leaf's internal t
  reg [1:0] cnt;
  wire \\weird.name ;
  assign \\weird.name = a;
  leaf u0(.a(a), .b(b), .y(t));    // named connections: .a .b .y stay
  always @(posedge clk) begin cnt <= cnt + 2'd1; q <= t ^ cnt[0]; end
  assign y2 = \\weird.name ;
endmodule
""")
    ast, directives, notes = V.parse_files([str(src)], workdir=tmp_path / "w")
    table = RT.identifier_table(ast)
    assert set(table) == {"t", "cnt"}   # ports, module / instance names excluded; the escaped name is not in the table (Pyverilog keeps it apart)
    variants = RT.text_variants([str(src)], ast, "seed", 2)
    assert len(variants) == 2 and variants[0][1] != variants[1][1] and set(variants[0][1]) == {"t", "cnt"}
    k, mapping, texts = variants[0]
    new = texts[str(src)]
    assert "wire t;" not in new and f"wire {mapping['t']};" in new and f"reg [1:0] {mapping['cnt']};" in new
    assert ".y(" + mapping["t"] + ")" in new and ".a(a)" in new and "leaf u0(" in new and "module top(" in new
    assert "\\weird.name" in new and "posedge clk" in new and "output reg q" in new
    assert new.count(mapping["cnt"]) == 4 and "cnt" not in new.replace(mapping["cnt"], "")  # declaration, cnt <= cnt + 1, cnt[0]
    # equivalence of the renamed text (licence-free self-test on the synthetic design)
    from src.equiv.yosys_equiv import yosys_equiv
    out = tmp_path / "renamed.v"
    out.write_text(new)
    assert yosys_equiv([str(src)], [str(out)], "top", C.load(), workdir=tmp_path / "yeq") == "equivalent"
    broken = out.with_name("broken.v")
    broken.write_text(new.replace("^ " + mapping["cnt"] + "[0]", "| " + mapping["cnt"] + "[0]"))   # a real change must not pass
    assert yosys_equiv([str(src)], [str(broken)], "top", C.load(), workdir=tmp_path / "yeq2") != "equivalent"


def test_text_scanner_identifier_table_needs_no_parser_and_matches_the_ast_table(tmp_path):
    """REQUEST 2026-09-20 (e) item 3 (harness note): the text renamer's identifier table comes from the parser-free scanner —
    on a design Pyverilog can read, it equals the AST table; on one Pyverilog cannot read (a SystemVerilog `interface`-free
    construct the front end rejects: a `[` in an unexpected place), it still yields the internal names; ports, module / instance /
    function names, named connections, macros and escaped identifiers are never in it (both directions)."""
    from src.noise import rename_text as RT
    from src.noise import textscan as TS
    from src.noise import vast as V
    src = tmp_path / "top.v"
    src.write_text("""`define W 2
module leaf #(parameter N = 1) (input a, input b, output y);
  wire t; assign t = a & b; assign y = t;
  function [1:0] f2; input [1:0] q; reg [1:0] loc; begin loc = q; f2 = loc; end endfunction
endmodule
module top(input clk, input a, input b, output reg q, output y2);
  wire t;               // same name as leaf's internal t
  reg [`W-1:0] cnt;
  localparam K = 3;
  wire \\weird.name ;
  assign \\weird.name = a;
  leaf #(.N(K)) u0(.a(a), .b(b), .y(t));    // named connections: .a .b .y stay; u0 and leaf protected
  always @(posedge clk) begin cnt <= cnt + 2'd1; q <= t ^ cnt[0]; end
  assign y2 = \\weird.name ;
endmodule
""")
    table = TS.identifier_table([src.read_text()])
    assert set(table) == {"t", "cnt", "K"}, table                 # nets, registers and the localparam; ports, names, function locals and N (a named parameter connection .N(K)) excluded
    ast, _d, _n = V.parse_files([str(src)], workdir=tmp_path / "w")
    assert set(RT.identifier_table(ast)) - {"N"} == set(table)     # the Pyverilog-based table of the earlier path, minus N: it lists the parameter although `#(.N(K))` references it by name (an exposure of the old path; the text scanner protects named connections of both kinds)
    k, mapping, texts = RT.text_variants([str(src)], None, "seed", 1)[0]
    new = texts[str(src)]
    assert "module top(" in new and "module leaf" in new and "leaf #(.N(" in new and "u0(.a(a), .b(b), .y(" in new and "\\weird.name" in new and "`W-1" in new
    assert f"wire {mapping['t']};" in new and f"reg [`W-1:0] {mapping['cnt']};" in new and f"localparam {mapping['K']} = 3;" in new
    from src.equiv.yosys_equiv import yosys_equiv
    out = tmp_path / "renamed.v"; out.write_text(new)
    assert yosys_equiv([str(src)], [str(out)], "top", C.load(), workdir=tmp_path / "yeq") == "equivalent"
    # a design the parser rejects still gets a table (the earlier pipeline stopped here)
    bad = tmp_path / "bad.v"
    bad.write_text("module bad(input clk, input [3:0] a, output reg [3:0] y);\n  reg [3:0] s;\n  always @(posedge clk) begin s <= a; y <= s; end\n  wire [3:0] z = a[3:0] [0 +: 4];\nendmodule\n")
    import pytest
    with pytest.raises(Exception):
        V.parse_files([str(bad)], workdir=tmp_path / "wb")
    assert set(TS.identifier_table([bad.read_text()])) == {"s", "z"}


def test_text_level_p2_reorder_permutes_runs_only_and_stays_equivalent(tmp_path):
    """REQUEST 2026-09-20 (e) item 3 (PLAN 6.9): P2_text permutes consecutive assigns and consecutive always blocks with begin ... end
    inside a module; declarations, instances and generate blocks are barriers; an always body without begin, a generate-if or a
    directive inside the body makes the scanner refuse the module (untouched). The result is equivalent (Yosys self-test); a real
    change is caught."""
    from src.noise import reorder_text as RO
    from src.noise import textscan as TS
    from src.noise import vast as V
    src = tmp_path / "top.v"
    src.write_text("""module top(input clk, input rst, input [3:0] a, input [3:0] b, output reg [3:0] q, output reg [3:0] r, output [3:0] s, output [3:0] u, output [3:0] v);
  wire [3:0] w1, w2;   // declarations stay first
  assign w1 = a & b;   // run of three assigns
  assign w2 = a | b;
  assign s = w1 ^ w2;
  reg [3:0] t;
  always @(posedge clk or posedge rst) begin   // run of two always blocks
    if (rst) q <= 4'd0; else q <= w1;
  end
  always @(posedge clk) begin
    case (a) 4'd0: t <= b; default: t <= a; endcase
    r <= t;
  end
  assign u = t + 4'd1; assign v = ~t;
endmodule
""")
    r = V.rng("seed", RO.PTYPE, 0)
    details = {}
    new = RO.reorder_text(src.read_text(), r, details, "top.v")
    assert details["top"]["assign_runs"] == 2 and details["top"]["always_runs"] == 1 and details["top"]["items_moved"] >= 2 and "refused" not in details
    orig = src.read_text()
    assert new != orig and len(new) == len(orig)
    for stmt in ("assign w1 = a & b;", "assign w2 = a | b;", "assign s = w1 ^ w2;", "assign u = t + 4'd1;", "assign v = ~t;", "if (rst) q <= 4'd0; else q <= w1;", "r <= t;"):
        assert new.count(stmt) == 1, stmt                                                        # every item survives exactly once
    assert new.index("wire [3:0] w1, w2;") < new.index("assign") < new.index("reg [3:0] t;") < new.index("always")   # barriers keep their place
    assert new.index("assign u") > new.rindex("always") and new.index("assign v") > new.rindex("always")
    from src.equiv.yosys_equiv import yosys_equiv
    out = tmp_path / "reordered.v"; out.write_text(new)
    assert yosys_equiv([str(src)], [str(out)], "top", C.load(), workdir=tmp_path / "yeq") == "equivalent"
    broken = tmp_path / "broken.v"; broken.write_text(new.replace("assign u = t + 4'd1;", "assign u = t + 4'd2;"))
    assert yosys_equiv([str(src)], [str(broken)], "top", C.load(), workdir=tmp_path / "yeq2") != "equivalent"   # a real change is caught
    # always bodies without begin (an if / else chain, a case, a single assignment) are delimited and reordered among always blocks
    text = ("module m2(input clk, input rst, input [3:0] a, input [3:0] b, output reg [3:0] q, output reg [3:0] p, output reg [3:0] o);\n"
            "  always @(posedge clk) if (rst) q <= 4'd0; else if (a[0]) q <= a; else q <= b;\n"
            "  always @(posedge clk) case (a) 4'd1: p <= b; default: p <= a; endcase\n"
            "  always @(posedge clk) o <= a ^ b;\nendmodule\n")
    d = {}
    new2 = RO.reorder_text(text, V.rng("s", RO.PTYPE, 1), d, "m2")
    assert d["m2"]["always_runs"] == 1 and "refused" not in d and new2 != text and all(new2.count(x) == 1 for x in ("else q <= b;", "endcase", "o <= a ^ b;"))
    (tmp_path / "m2.v").write_text(text); (tmp_path / "m2r.v").write_text(new2)
    assert yosys_equiv([str(tmp_path / "m2.v")], [str(tmp_path / "m2r.v")], "m2", C.load(), workdir=tmp_path / "yeq3") == "equivalent"
    # inside an always block of nothing but nonblocking assignments to distinct registers, the statements are permuted
    text = "module m3(input clk, input [3:0] a, output reg [3:0] x, output reg [3:0] y, output reg [3:0] z);\n  always @(posedge clk) begin\n    x <= a;\n    y <= x;\n    z <= y ^ x;\n  end\nendmodule\n"
    d = {}
    new3 = RO.reorder_text(text, V.rng("s", RO.PTYPE, 0), d, "m3")
    assert d["m3"]["nba_blocks"] == 1 and new3 != text and new3.index("z <= y ^ x;") != text.index("z <= y ^ x;") or new3.index("x <= a;") != text.index("x <= a;")
    (tmp_path / "m3.v").write_text(text); (tmp_path / "m3r.v").write_text(new3)
    assert yosys_equiv([str(tmp_path / "m3.v")], [str(tmp_path / "m3r.v")], "m3", C.load(), workdir=tmp_path / "yeq4") == "equivalent"
    text_b = text.replace("z <= y ^ x;", "z <= y ^ x;\n    x <= z;")                                   # a repeated target: the block is not touched
    d = {}
    assert RO.reorder_text(text_b, V.rng("s", RO.PTYPE, 0), d, "m3") == text_b
    # refusals: a timing control in a procedural statement, a directive in the body, a generate-if; each leaves the module untouched
    for body, why in (("always @(posedge clk) #1 q <= a;\n  assign s = a; assign u = b;", "timing control"),
                      ("`ifdef X\n  assign s = a;\n  `endif\n  assign u = b;", "directive"),
                      ("if (1) begin : g assign s = a; end\n  assign u = b; assign v = a;", "if")):
        text = f"module m(input clk, input [3:0] a, input [3:0] b, output reg [3:0] q, output [3:0] s, output [3:0] u, output [3:0] v);\n  {body}\nendmodule\n"
        d = {}
        assert RO.reorder_text(text, V.rng("s", RO.PTYPE, 0), d, "m") == text and "m" in d.get("refused", {}), why
    # a generate for with begin ... end is a barrier; assigns inside it are not top-level items
    gen = "module g(input [3:0] a, output [3:0] s, output [3:0] u);\n  genvar i;\n  for (i = 0; i < 4; i = i + 1) begin : L assign s[i] = a[i]; end\n  assign u = a;\nendmodule\n"
    items = TS.module_items(TS.mask(gen), gen.index(";") + 1, gen.index("endmodule"))
    assert [k for k, _s, _e in items] == ["other", "other", "assign"]
    (tmp_path / "g.v").write_text(gen)
    import pytest
    from src.noise import perturb as P
    with pytest.raises(P.NotApplicable):
        RO.text_variants([str(tmp_path / "g.v")], "s", 1)                                          # one top-level assign: nothing to permute


def test_text_generators_keep_existing_entries_and_top_up(tmp_path, monkeypatch):
    """The text-level generators keep the manifest's existing entries of their type (their SEQ records stay valid) and add new
    variants up to n with k continuing after the highest existing one; a Pyverilog-unreadable design gets both types."""
    from src.noise import generate as G
    d_dir = tmp_path / "designs" / "x" / "d1"; (d_dir / "rtl").mkdir(parents=True)
    (d_dir / "rtl" / "d1.v").write_text("module d1(input clk, input [3:0] a, output reg [3:0] q, output [3:0] s, output [3:0] u);\n  reg [3:0] t;\n  wire [3:0] z = a[3:0] [0 +: 4];\n"
                                        "  assign s = a; assign u = ~a;\n  always @(posedge clk) begin t <= a; end\n  always @(posedge clk) begin q <= t; end\nendmodule\n")
    design = {"design_id": "x_d1", "top": "d1", "files": ["rtl/d1.v"], "incdirs": [], "_dir": str(d_dir)}
    monkeypatch.setattr(G.K, "abs_paths", lambda d, paths: [Path(d["_dir"]) / p for p in paths])
    cfg = copy.deepcopy(C.load()); cfg["noise"]["n_per_type"] = 4
    m = G.generate_text_p1(design, cfg, n_per_type=2, out_root=tmp_path / "pert")
    assert m["p1_text"]["n"] == 2 and [e["k"] for e in m["perturbations"]] == [0, 1] and m["error"] is None
    m = G.generate_text_p1(design, cfg, n_per_type=4, out_root=tmp_path / "pert")
    ks = [e["k"] for e in m["perturbations"] if e["ptype"] == "P1_text"]
    assert ks == [0, 1, 2, 3] and m["p1_text"]["n"] == 4                                   # the first two kept, two added
    m = G.generate_text_p2(design, cfg, n_per_type=3, out_root=tmp_path / "pert")
    p2 = [e for e in m["perturbations"] if e["ptype"] == "P2_text"]
    assert 1 <= len(p2) <= 3 and all(e["details"]["reordered"]["d1"]["assign_runs"] == 1 and e["details"]["reordered"]["d1"]["always_runs"] == 1 for e in p2) and len([e for e in m["perturbations"] if e["ptype"] == "P1_text"]) == 4
    assert len({e["pert_id"] for e in m["perturbations"]}) == len(m["perturbations"])       # distinct texts only
