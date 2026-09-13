"""Bidirectional tests of the LLM candidate handling (src/search/candidates.py): JSON answers with or without a
fence parse, garbage is refused, a rewrite that renames the module is refused, files and sidecars are stored."""
import json

import pytest

from src.search import candidates as CA

RTL = "module accu(input clk, input [7:0] a, output reg [7:0] y);\n  always @(posedge clk) y <= a;\nendmodule\n"


def test_parse_answer_and_top_check():
    rtl, note = CA.parse_answer(json.dumps({"rtl": RTL, "note": "moved a register"}))
    assert rtl == RTL and note == "moved a register"
    rtl2, _ = CA.parse_answer("```json\n" + json.dumps({"rtl": RTL, "note": "x"}) + "\n```")
    assert rtl2 == RTL
    rtl3, _ = CA.parse_answer("Sure, here it is:\n" + json.dumps({"rtl": RTL.replace("\n", "\r\n"), "note": "x"}) + "\nHope this helps")
    assert rtl3 == RTL
    assert CA.check_top(RTL, "accu") == ["accu"]
    with pytest.raises(CA.BadAnswer):
        CA.check_top(RTL.replace("module accu", "module accu2"), "accu")
    for bad in ("no json here", "{\"note\": \"only a note\"}", "{\"rtl\": 42}", "{broken json"):
        with pytest.raises(CA.BadAnswer):
            CA.parse_answer(bad)


def test_store_and_prefix(tmp_path):
    design = {"design_id": "rtllm_accu", "top": "accu", "files": ["rtl/accu.v"], "_dir": str(tmp_path / "d")}
    (tmp_path / "d" / "rtl").mkdir(parents=True)
    (tmp_path / "d" / "rtl" / "accu.v").write_text(RTL)
    cid, path = CA.store("run_x", design, RTL.rstrip("\n"), {"model": "m"}, root=tmp_path / "cands")
    assert cid == CA.cand_id_of(RTL.rstrip("\n")) and path.read_text() == RTL
    side = json.loads(path.with_suffix(".json").read_text())
    assert side["design_id"] == "rtllm_accu" and side["model"] == "m" and side["cand_id"] == cid
    prefix = CA.prompt_prefix(design, "SYSTEM")
    assert prefix.startswith("SYSTEM") and RTL in prefix and "`accu`" in prefix
