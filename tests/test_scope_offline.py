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
    assert texts[1].startswith("always @(posedge clk or negedge rst_n) if (!rst_n) y <= 0;") and texts[1].endswith("else y <= y;")
    assert texts[2].startswith("always @(posedge clk) begin : blk case (s)") and texts[2].endswith("end")
    assert "sub u1 [1:0]" in texts[5]


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
    body = SC.V.module_spans(text)[0][3]                                                 # comment-stripped module text: the candidate's form
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
    assert sorted(spliced) == sorted(n for n in spans if n != "eth_txcounters") and set(SC.V.module_names(full)) == set(spans)
    assert SC.verify(text, full, region) == [] and full.startswith(only_region.rstrip())              # the other modules are D's own text
    assert SC.splice(text, text, region) == (text, [])                                                # a complete answer: nothing spliced
    other_only = "\n".join(lines[spans["eth_random"][0] - 1:spans["eth_random"][1]])
    assert SC.splice(text, other_only, region) == (other_only, [])                                   # the region module is absent: not a rewrite of the region
    block_region = {"module": "eth_txcounters", "kind": "blocks", "items": [0], "registers": ["NibCnt"]}
    assert SC.splice(text, only_region, block_region) == (only_region, [])                            # block-level scope: no splicing
    assert SC.splice(text, only_region, None) == (only_region, [])
