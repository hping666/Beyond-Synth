"""Scope-limited rewriting (G5 decisions item 1, correctness aid (i); src/search/scope.py): the statement-level item
scanner on synthetic and staged Verilog, the region selection from critical endpoints (module on multi-module designs,
always blocks on single-module ones, fallbacks), the textual verification in both directions, the prompt text, and the
repair evidence texts of the three repairable failure types."""
import json
from pathlib import Path

import pytest

from src.search import scope as SC

ROOT = Path(__file__).resolve().parent.parent

SYN = """// header comment
module top #(parameter W = 4) (input clk, input rst_n, input [W-1:0] a, output reg [W-1:0] y, output z);
  reg [W-1:0] s; wire [W-1:0] t;            // declarations are free
  localparam IDLE = 2'b00, RUN = 2'b01;
  integer i;
  assign t = a + {{(W-1){1'b0}}, 1'b1};
  always @(posedge clk or negedge rst_n)
    if (!rst_n) y <= 0;
    else if (a[0]) y <= t;
    else y <= y;                             /* single-statement if/else chain */
  always @(posedge clk) begin : blk
    case (s)
      IDLE: s <= (a[1] ? RUN : IDLE);
      RUN, 2'b10: begin s <= IDLE; end
      default: s <= s;
    endcase
    for (i = 0; i < W; i = i + 1) if (a[i]) s[i] <= 1'b1;
  end
  function [W-1:0] inc; input [W-1:0] v; begin inc = v + 1; end endfunction
  sub #(.N(W)) u0 (.clk(clk), .d(y), .q(z));
  sub u1 [1:0] (.clk(clk), .d(y), .q());
endmodule

module sub #(parameter N = 4) (input clk, input [N-1:0] d, output reg q);
  always @(posedge clk) q <= ^d;
endmodule
"""


def test_scanner_finds_statement_items_and_their_targets():
    d = SC.parse_design(SYN)
    assert list(d) == ["top", "sub"]
    kinds = [(it["kind"], it["targets"]) for it in d["top"]["items"]]
    assert kinds == [("assign", ["t"]), ("always", ["y"]), ("always", ["s"]), ("function", ["inc"]), ("inst", ["u0"]), ("inst", ["u1"])]
    assert d["top"]["instances"] == {"u0": "sub", "u1": "sub"}
    assert d["sub"]["items"][0]["kind"] == "always" and d["sub"]["items"][0]["targets"] == ["q"]
    lines = [it["line"] for it in d["top"]["items"]]
    assert lines == sorted(lines) and lines[1] == 7                      # the y block starts on line 7 of the text
    texts = [it["text"] for it in d["top"]["items"]]
    assert texts[1].startswith(SC.canonical("always @(posedge clk or negedge rst_n) if (!rst_n) y <= 0;")) and texts[1].endswith(SC.canonical("else y <= y;"))
    assert texts[2].startswith(SC.canonical("always @(posedge clk) begin : blk case (s)")) and texts[2].endswith("end")
    assert SC.canonical("sub u1 [1:0]") in texts[5]


@pytest.mark.parametrize("did, files", [("cktevo/ethmac__eth_txethmac", None), ("drrtl/i2c", None), ("rtlopt/fsm_encode", None), ("cktevo/mem_ctrl__mc_obct_top", None), ("rtllm/counter_12", None)])
def test_scanner_handles_the_staged_designs(did, files):
    """Every module parses, items never overlap and appear in text order (the same check passed on all 593 staged modules)."""
    dj = ROOT / "data" / "designs" / did / "design.json"
    if not dj.exists():
        pytest.skip("design not staged")
    d = json.loads(dj.read_text())
    text = "\n\n".join((dj.parent / f).read_text(errors="replace") for f in d["files"])
    des = SC.parse_design(text)
    assert d["top"] in des and sum(len(m["items"]) for m in des.values()) > 0
    for m in des.values():
        it = m["items"]
        assert all(it[i]["start"] >= it[i - 1]["end"] for i in range(1, len(it)))


def _design(did):
    dj = ROOT / "data" / "designs" / did / "design.json"
    if not dj.exists():
        pytest.skip("design not staged")
    d = json.loads(dj.read_text())
    text = "\n\n".join((dj.parent / f).read_text(errors="replace") for f in d["files"])
    return d, text, SC.parse_design(text)


def test_region_on_a_multi_module_design_is_the_module_of_the_critical_endpoints():
    d, text, des = _design("cktevo/ethmac__eth_txethmac")
    crit = {"critical": {"endpoint": "txcounters1/NibCnt_reg[13]", "startpoint": "MinFL[4]"}, "endpoints": [["MinFL[4]", "txcounters1/NibCnt_reg[13]", 0.01], ["MinFL[4]", "txcounters1/NibCnt_reg[11]", 0.01], ["x", "txcrc/Crc_reg[3]", 0.2]]}
    r = SC.select_region(des, d["top"], crit)
    assert r["module"] == "eth_txcounters" and r["kind"] == "module" and r["registers"] == ["NibCnt"] and r["items"] == []
    assert "rewrite only module `eth_txcounters`" in SC.region_text(des, r, d["top"]) and "NibCnt" in SC.region_text(des, r, d["top"])
    # with the per-block rule on a multi-module design the always block inside the module is the region
    r2 = SC.select_region(des, d["top"], crit, multi_module="block")
    assert r2["module"] == "eth_txcounters" and r2["kind"] == "blocks" and all("NibCnt" in des["eth_txcounters"]["items"][i]["targets"] for i in r2["items"])
    # unknown instance path -> the top module
    r3 = SC.select_region(des, d["top"], {"critical": {"endpoint": "nowhere/Foo_reg[1]"}, "endpoints": []})
    assert r3["module"] == d["top"] and r3["kind"] == "module"


def test_region_on_a_single_module_design_is_the_always_block_of_the_endpoint_register():
    d, text, des = _design("rtlopt/fsm_encode")
    crit = {"critical": {"endpoint": "reg1_reg[6]"}, "endpoints": [["current_state_reg[7]", "reg1_reg[6]", 0.15]]}
    r = SC.select_region(des, d["top"], crit)
    assert r["kind"] == "blocks" and r["registers"] == ["reg1"] and len(r["items"]) == 1
    blk = des["fsm_encode"]["items"][r["items"][0]]
    assert blk["kind"] == "always" and "reg1" in blk["targets"]
    txt = SC.region_text(des, r, d["top"])
    assert f"rewrite only the always block at line {blk['line']}" in txt and "textually unchanged" in txt
    # DC-generated register names (retimed) map to no block: the whole module, reason recorded
    r2 = SC.select_region(des, d["top"], {"critical": {"endpoint": "R_2"}, "endpoints": [["row_adr[1]", "R_2", 0.02]]})
    assert r2["kind"] == "module" and r2["registers"] == [] and "no always block" in r2["reason"]
    assert SC.select_region(des, d["top"], None)["kind"] == "module"                        # no path data at all
    assert SC.select_region(des, d["top"], crit, single_module="module")["kind"] == "module"   # configured whole-module scope


def test_verify_accepts_changes_inside_the_region_and_rejects_changes_outside_it():
    d, text, des = _design("rtlopt/fsm_encode")
    crit = {"critical": {"endpoint": "reg1_reg[6]"}, "endpoints": [["current_state_reg[7]", "reg1_reg[6]", 0.15]]}
    r = SC.select_region(des, d["top"], crit)
    items = des["fsm_encode"]["items"]
    m = des["fsm_encode"]
    body = SC.V.blank_comments(text)[m["start"]:m["end"]]                                # the module text with comments blanked: item offsets address it
    tgt = items[r["items"][0]]
    inside = body[:tgt["start"]] + body[tgt["start"]:tgt["end"]].replace("<=", "<= 1'b0 |", 1) + body[tgt["end"]:]
    assert SC.verify(text, inside, r) == []                                              # the named block may change
    assert SC.verify(text, text, r) == []                                                # the unchanged design passes
    assert SC.verify(text, "  " + body.replace("\n", "\n   ") + "\n", r) == []          # whitespace never counts
    other = next(i for i, it in enumerate(items) if i not in r["items"] and it["kind"] == "always")
    o = items[other]
    outside = body[:o["start"]] + body[o["start"]:o["end"]].replace("=", "= 1'b0 |", 1) + body[o["end"]:]
    v = SC.verify(text, outside, r)
    assert len(v) == 1 and v[0]["kind"] == "always" and v[0]["line"] == o["line"] and v[0]["problem"] == "changed or removed"
    removed = body[:o["start"]] + body[o["end"]:]
    assert [x["problem"] for x in SC.verify(text, removed, r)] == ["changed or removed"]
    a, b = items[0], items[1]                                                            # the two leading always blocks swapped: moved
    swapped = body[:a["start"]] + body[b["start"]:b["end"]] + "\n" + body[a["end"]:b["start"]] + body[a["start"]:a["end"]] + body[b["end"]:]
    probs = {x["problem"] for x in SC.verify(text, swapped, r)}
    assert probs and probs <= {"moved", "changed or removed"}
    # module-level region on a multi-module design: the other modules must be present and unchanged
    d2, text2, des2 = _design("cktevo/ethmac__eth_txethmac")
    r2 = {"module": "eth_txcounters", "kind": "module", "items": [], "registers": ["NibCnt"]}
    assert SC.verify(text2, text2, r2) == []
    dropped = "\n\n".join(s[3] for s in SC.V.module_spans(text2) if s[0] != "eth_random")
    v2 = SC.verify(text2, dropped, r2)
    assert v2 and v2[0]["module"] == "eth_random" and v2[0]["problem"] == "module missing from the answer"
    sub_changed = text2.replace("module eth_txcounters", "module eth_txcounters // free").replace("Reset)\n    begin\n      NibCnt", "Reset)\n    begin\n      NibCnt", 1)
    assert SC.verify(text2, sub_changed, r2) == []                                       # comments and the region module never count


def test_failure_evidence_texts():
    f, t = SC.failure_evidence({"verdict": "rejected", "v1_detail": "candidate does not elaborate: yosys exit 1: x.v:48: ERROR: syntax error"})
    assert f == "rejected" and "syntax error" in t
    f, t = SC.failure_evidence({"verdict": "sim_fail", "v2": {"first_mismatch": 164, "mismatches": {"ResetCollision": {"c": "0", "d": "1", "first_cycle": 164}}}})
    assert f == "sim_fail" and "cycle 164" in t and "ResetCollision" in t and "original 1, rewrite 0" in t
    f, t = SC.failure_evidence({"verdict": "sim_fail", "v2_detail": json.dumps({"q": {"c": "x", "d": "0", "first_cycle": 3}}), "v2": {}})
    assert f == "sim_fail" and "output q" in t
    f, t = SC.failure_evidence({"verdict": "falsified", "v3": {"properties": {"_map_output_MTxD": "falsified", "_map_output_TxDone": "proven"}, "cex_depths": {"_map_output_MTxD": 1}}})
    assert f == "falsified" and "MTxD" in t and "TxDone" not in t and "1 cycles" in t
    assert SC.failure_evidence({"verdict": "inconclusive"}) == (None, None) and SC.failure_evidence({"verdict": "proven"}) == (None, None)


def test_splice_takes_the_omitted_modules_from_the_original():
    """Operator decision 2026-09-15 (after the probe): with a module-level region an answer may return only the rewritten
    module; the modules it leaves out come verbatim from D. The region module itself must be present; block-level regions
    and complete answers are untouched (both directions)."""
    d, text, des = _design("cktevo/ethmac__eth_txethmac")
    region = {"module": "eth_txcounters", "kind": "module", "items": [], "registers": ["NibCnt"]}
    spans = {n: (f, l) for n, f, l, _ in SC.V.module_spans(text)}
    lines = text.splitlines()
    only_region = "\n".join(lines[spans["eth_txcounters"][0] - 1:spans["eth_txcounters"][1]]).replace("NibCnt <= NibCnt + 1", "NibCnt <= NibCnt + 1'b1")
    full, spliced = SC.splice(text, only_region, region)
    assert sorted(spliced["added_modules"]) == sorted(n for n in spans if n != "eth_txcounters") and set(SC.V.module_names(full)) == set(spans)
    assert spliced["restored_modules"] == [] and spliced["violations"] == []                            # omissions are allowed by the prompt: restored, not flagged
    assert SC.verify(text, full, region) == [] and full.startswith(only_region.rstrip())              # the other modules are D's own text
    assert SC.splice(text, text, region) == (text, {})                                                # a complete answer: nothing spliced, no flag
    other_only = "\n".join(lines[spans["eth_random"][0] - 1:spans["eth_random"][1]])
    t3, i3 = SC.splice(text, other_only, region)
    assert t3 == other_only and not i3.get("added_modules") and i3.get("region_missing") == "eth_txcounters"   # the region module is absent: not a rewrite of the region (the driver treats it as unusable)
    block_region = {"module": "eth_txcounters", "kind": "blocks", "items": [0], "registers": ["NibCnt"]}
    t4, i4 = SC.splice(text, only_region, block_region)
    assert t4 == only_region and i4["restored_items"] == [] and i4["added_items"] == [] and i4["violations"] == []   # block-level scope restores items of the region module only (single-module designs)
    assert SC.splice(text, only_region, None) == (only_region, {})


D_TWO_BLOCKS = """// header comment
module top(input clk, input rst_n, input [3:0] a, output reg [3:0] y, output reg [3:0] z);
  wire [3:0] t;
  assign t = a + 4'd1;   // helper
  always @(posedge clk or negedge rst_n)
    if (!rst_n) y <= 4'd0;
    else        y <= t;      /* y block */
  always @(posedge clk or negedge rst_n)
    if (!rst_n) z <= 4'd0;
    else        z <= a ^ 4'b1010;
  assign_never_here: ;
endmodule
"""


def test_canonical_comparison_ignores_whitespace_and_comments_but_not_tokens():
    """Decision 2026-09-15 evening (item 2) after the smoke runs: a reformatted but token-identical block outside the region is no
    violation (spacing around operators, line breaks, comments, case-item alignment); a dropped `begin`/`end` pair or any other
    token change still is (both directions)."""
    d = D_TWO_BLOCKS.replace("  assign_never_here: ;\n", "")
    region = {"module": "top", "kind": "blocks", "items": [1], "registers": ["y"]}   # item 0 = the assign of t, 1 = y block, 2 = z block
    items = SC.parse_design(d)["top"]["items"]
    assert [it["targets"] for it in items] == [["t"], ["y"], ["z"]]
    reformatted = d.replace("if (!rst_n) z <= 4'd0;\n    else        z <= a ^ 4'b1010;", "if(!rst_n)z<=4'd0; else z <= a^4'b1010; // rewritten spacing")
    reformatted = reformatted.replace("assign t = a + 4'd1;   // helper", "assign t=a+4'd1;")
    assert SC.verify(d, reformatted, region) == []
    changed = d.replace("z <= a ^ 4'b1010;", "z <= a ^ 4'b1011;")
    v = SC.verify(d, changed, region)
    assert len(v) == 1 and v[0]["targets"] == ["z"] and v[0]["problem"] == "changed or removed"
    wrapped = d.replace("else        z <= a ^ 4'b1010;", "else begin z <= a ^ 4'b1010; end")
    assert len(SC.verify(d, wrapped, region)) == 1                                  # begin/end are tokens: a textual change of the block
    assert SC.verify(d, d.replace("y <= t;", "y <= t + 4'd0;"), region) == []      # the region itself may change


def test_block_level_splice_restores_out_of_scope_items_and_keeps_the_rewrite():
    """Decision 2026-09-15 evening (item 2): the model's rewrite of the scoped block is kept, every other item is restored from D
    (changed in place, dropped ones appended before endmodule), the model's additions stay, and the violations are returned as
    the warning flag; an answer without violations comes back unchanged; the spliced text passes an order-free verification."""
    d = D_TWO_BLOCKS.replace("  assign_never_here: ;\n", "")
    region = {"module": "top", "kind": "blocks", "items": [1], "registers": ["y"]}
    c = d.replace("y <= t;", "y <= a + 4'd1;")                                           # the scoped rewrite
    c = c.replace("z <= a ^ 4'b1010;", "z <= a ^ 4'b1011;")                               # an out-of-scope change
    c = c.replace("  assign t = a + 4'd1;   // helper\n", "  wire [3:0] helper2;\n  assign helper2 = a & 4'd3;\n")   # the assign of t dropped, a new declaration and a new assign added
    text, info = SC.splice(d, c, region)
    assert {v["targets"][0] for v in info["violations"]} == {"t", "z"}
    assert info["restored_items"][0]["targets"] == ["z"] and info["added_items"][0]["targets"] == ["t"]
    assert "y <= a + 4'd1;" in text and "z <= a ^ 4'b1010;" in text and "z <= a ^ 4'b1011;" not in text
    assert "helper2 = a & 4'd3" in text and "wire [3:0] t;" in text and "t = a + 4'd1" in text and text.count("endmodule") == 1
    assert SC.verify(d, text, region, ordered=False) == [] and SC.verify(d, text, region) != []   # only the order differs after the append
    assert SC.parse_design(text)["top"]["instances"] == {} and text.index("endmodule") > text.index("t = a + 4'd1")
    same, info2 = SC.splice(d, c.replace("z <= a ^ 4'b1011;", "z <= a ^ 4'b1010;").replace("  wire [3:0] helper2;\n  assign helper2 = a & 4'd3;\n", "  assign t = a + 4'd1;\n"), region)
    assert info2 == {} and "y <= a + 4'd1;" in same
    assert SC.splice(d, c, None) == (c, {})
    swapped = d.replace("  assign t = a + 4'd1;   // helper\n", "").replace("endmodule", "  assign t = a + 4'd1;\nendmodule")   # the assign moved to the end: no edit, no flag
    assert SC.splice(d, swapped, region) == (swapped, {}) and SC.verify(d, swapped, region) != []


def test_module_level_splice_restores_changed_modules_and_adds_omitted_ones():
    """Module-level regions: a module outside the region that the answer changed is replaced by D's text, an omitted one is
    appended, the region module keeps the rewrite; the violations are the warning flag."""
    d = "module top(input a, output y, output z);\n  wire m; sub u(.a(a), .y(m));\n  other o(.a(m), .z(z));\n  assign y = m;\nendmodule\n" \
        "module sub(input a, output y);\n  assign y = ~a;   // sub\nendmodule\n" \
        "module other(input a, output z);\n  assign z = a;\nendmodule\n"
    region = {"module": "sub", "kind": "module", "items": [], "registers": ["y"]}
    c = "module top(input a, output y, output z);\n  wire m; sub u(.a(a), .y(m));\n  other o(.a(m), .z(z));\n  assign y = m | 1'b0;\nendmodule\n" \
        "module sub(input a, output y);\n  assign y = !a;\nendmodule\n"                         # top changed, other omitted, sub rewritten
    text, info = SC.splice(d, c, region)
    assert info["restored_modules"] == ["top"] and info["added_modules"] == ["other"] and [v["module"] for v in info["violations"]] == ["top"]   # the changed module is the flag, the omitted one is not
    assert "assign y = m;" in text and "m | 1'b0" not in text and "assign y = !a;" in text and "module other" in text
    assert SC.verify(d, text, region) == []
