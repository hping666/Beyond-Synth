"""Bidirectional tests of the M6 LLM review (spec 04 §A.2 step 2; DECISIONS 2026-09-14 item 1): answer parsing (valid,
missing, unknown class), the final-class rule ((a)/(b)/(c1)/(c2) from the review replace the rule class, an LLM (d)
does not), the selection of the review set (low confidence / flagged wide rewrite / nonequiv (b)-(c1) / redundant
register; confident candidates and reviewed ones excluded), and the review loop with a fake transport (rows updated,
budget charged, unusable answers recorded, resumable)."""
import copy
import json
from types import SimpleNamespace

import pytest

from src import config as C
from src.classify import review as R
from src.db import core as db


def test_parse_and_final_class():
    ans = R.parse_answer('Sure. {"class": "(c1)", "subtags": ["pipelining"], "basis": "registers moved", "confidence": 0.8}')
    assert ans == {"class": "c1", "subtags": ["pipelining"], "basis": "registers moved", "confidence": 0.8}
    assert R.parse_answer('{"class": "d", "confidence": 3}')["confidence"] == 1.0
    for bad in ("no json here", '{"class": "e"}', '{"class": '):
        with pytest.raises(ValueError):
            R.parse_answer(bad)
    assert R.final_class("a", "b") == "b" and R.final_class("c1", "c2") == "c2" and R.final_class("b", "b") == "b"
    assert R.final_class("b", "d") == "b" and R.final_class("a", "d") == "a"      # (d) stays tool-defined


class Transport:
    """Answers class (b) for every review call; the third call is unusable text."""
    def __init__(self):
        self.calls = 0

    def create(self, **kw):
        self.calls += 1
        text = "not an answer" if self.calls == 3 else '{"class": "b", "subtags": ["state_encoding"], "basis": "re-encoded", "confidence": 0.9}'
        return SimpleNamespace(id=f"r{self.calls}", status="completed", output_text=text, service_tier="flex",
                               usage=SimpleNamespace(input_tokens=50, output_tokens=20, input_tokens_details=SimpleNamespace(cached_tokens=0, cache_write_tokens=0), output_tokens_details=None))


@pytest.fixture
def env(tmp_path, monkeypatch):
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    from src.designs import catalog as K
    monkeypatch.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    ddir = tmp_path / "designs" / "rtllm" / "d"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "d.v").write_text("module d(input clk, input a, output reg y); always @(posedge clk) y <= a; endmodule\n")
    d = {"design_id": "rtllm_d", "suite": "rtllm", "name": "d", "top": "d", "files": ["rtl/d.v"], "clk_ports": ["clk"], "rst_port": None, "rst_sense": None,
         "sverilog": False, "incdirs": [], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/d.v": K.sha256_of(ddir / "rtl" / "d.v")}, "loc": 1, "tags": ["rtllm"], "notes": [], "_dir": str(ddir)}
    K.write_design(d)
    db.insert(conn, "runs", {"run_id": "r1", "exp": "phase3", "arm": "M", "design_id": "rtllm_d", "seed": 1, "llm_model": "gpt-5.6-luna", "status": "done", "started_at": "t"})
    c = tmp_path / "c.v"
    c.write_text("module d(input clk, input a, output reg y); always @(posedge clk) y <= ~~a; endmodule\n")

    def cand(cid, cls, conf, rules, verdict="proven", ff=(4, 4), label="retained", class_llm=None):
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": "r1", "design_id": "rtllm_d", "gen": 1, "arm": "M", "rtl_path": str(c), "class_rule": cls, "class_final": cls,
                                       "confidence": conf, "subtags_json": json.dumps(rules), "rules_version": 2, "verdict": verdict, "label": label, "class_llm": class_llm,
                                       "features_json": json.dumps({"ff_d": ff[0], "ff_c": ff[1]})})
    cand("low", "a", 0.6, ["text differs widely (ratio 0.7) without operator or topology evidence -> review"])
    cand("nonequiv_c1", "c1", 0.7, ["flip-flop bits 16 -> 8 and register cells 8 -> 2"], verdict="sim_fail", ff=(16, 8), label="nonequiv")
    cand("redundant", "c1", 0.7, ["flip-flop bits 25 -> 24 and register cells 8 -> 7"], ff=(25, 24))
    cand("confident", "a", 0.85, ["flip-flop bits, register names and clocked targets unchanged"])
    cand("done", "b", 0.6, ["-> review"], class_llm="b")
    cand("dup", "b", 0.6, ["-> review"], label="duplicate")
    return cfg, conn


def test_review_set_and_run(env):
    cfg, conn = env
    rows = R.review_set(conn, cfg, "phase3")
    assert [r["cand_id"] for r in rows] == ["low", "nonequiv_c1", "redundant"]        # confident, reviewed and duplicate candidates excluded
    assert rows[0]["why"] == ["low_confidence", "wide_rewrite_without_evidence"] and rows[1]["why"] == ["nonequiv_timing_change"] and rows[2]["why"] == ["redundant_register"]
    prefix, suffix = R.prompt_parts({"design_id": "rtllm_d", "top": "d", "files": ["rtl/d.v"], "_dir": str(conn.execute("SELECT 1").fetchone() and __import__('pathlib').Path(rows[0]['rtl_path']).parent / 'designs' / 'rtllm' / 'd')}, rows[1])
    assert "Original design" in prefix and "NOT equivalent" in suffix and "class c1" in suffix
    out = R.run_review(cfg, conn, "phase3", transport=Transport(), log=lambda m: None)
    assert out["selected"] == 3 and out["reviewed"] == 2 and out["unusable"] == 1 and out["changed"] == 2
    got = {r[0]: (r[1], r[2]) for r in conn.execute("SELECT cand_id, class_llm, class_final FROM candidates")}
    assert got["low"] == ("b", "b") and got["nonequiv_c1"] == ("b", "b") and got["redundant"] == (None, "c1")   # the unusable answer leaves the rule class
    assert got["confident"] == (None, "a") and got["done"] == ("b", "b")
    rec = json.loads(conn.execute("SELECT review_json FROM candidates WHERE cand_id='low'").fetchone()[0])
    assert rec["class_rule"] == "a" and rec["class_llm"] == "b" and rec["subtags"] == ["state_encoding"] and rec["cost_usd"] > 0
    err = json.loads(conn.execute("SELECT review_json FROM candidates WHERE cand_id='redundant'").fetchone()[0])
    assert "error" in err and err["why"] == ["redundant_register"]
    assert conn.execute("SELECT COUNT(*) FROM budget_ledger WHERE kind='llm' AND phase='phase3_calibration'").fetchone()[0] == 3
    again = R.run_review(cfg, conn, "phase3", transport=Transport(), log=lambda m: None)      # resumable: only the unusable one is retried
    assert again["selected"] == 1 and again["reviewed"] == 1
    assert conn.execute("SELECT class_llm, class_final FROM candidates WHERE cand_id='redundant'").fetchone()[1] == "b"


def test_shards_and_concurrent_skip(env):
    cfg, conn = env
    all_rows = R.review_set(conn, cfg, "phase3")
    s0 = R.review_set(conn, cfg, "phase3", shard=0, shards=2)
    s1 = R.review_set(conn, cfg, "phase3", shard=1, shards=2)
    assert {r["cand_id"] for r in s0} | {r["cand_id"] for r in s1} == {r["cand_id"] for r in all_rows} and len(s0) == 2 and len(s1) == 1 and not ({r["cand_id"] for r in s0} & {r["cand_id"] for r in s1})

    class Concurrent(Transport):
        """While answering the first call, another shard reviews `redundant` (the second row of shard 0)."""
        def create(self, **kw):
            conn.execute("UPDATE candidates SET class_llm='a', class_final='a' WHERE cand_id='redundant'")
            return super().create(**kw)
    out = R.run_review(cfg, conn, "phase3", transport=Concurrent(), log=lambda m: None, shard=0, shards=2)
    assert out["selected"] == 2 and out["reviewed"] == 1 and out.get("skipped_meanwhile") == 1   # `low` reviewed, `redundant` skipped: no double call
