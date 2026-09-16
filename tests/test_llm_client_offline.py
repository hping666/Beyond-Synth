"""Bidirectional tests of the LLM client (spec 05 §8): requests saved with token counts, costs accumulated in the
budget ledger per service tier, the hard stop at the phase cap, unknown prices refused, transient failures
retried, no key leak."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import config as C
from src.db import core as db
from src.search import llm as L


def fake_response(inp=1000, cached=400, out=200, reasoning=50, writes=100, text="module x; endmodule", tier="default"):
    usage = SimpleNamespace(input_tokens=inp, output_tokens=out, total_tokens=inp + out,
                            input_tokens_details=SimpleNamespace(cached_tokens=cached, cache_write_tokens=writes),
                            output_tokens_details=SimpleNamespace(reasoning_tokens=reasoning))
    return SimpleNamespace(id="resp_1", status="completed", output_text=text, usage=usage, service_tier=tier)


class FakeTransport:
    def __init__(self, fail_first=0, served_tier=None):
        self.calls, self.fail_first, self.served_tier = [], fail_first, served_tier

    def create(self, **kw):
        self.calls.append(kw)
        if self.fail_first > 0:
            self.fail_first -= 1
            raise RuntimeError("rate limited")
        return fake_response(tier=self.served_tier or kw.get("service_tier", "default"))


@pytest.fixture
def env(tmp_path):
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["llm"]["prices_usd_per_1m"] = {"standard": {"m1": {"input": 2.0, "cached_input": 0.5, "cache_write": 2.5, "output": 8.0}, "m_tbd": {"input": "TBD", "cached_input": 0.5, "output": 8.0}},
                                       "flex": {"m1": {"input": 1.0, "cached_input": 0.25, "cache_write": 1.25, "output": 4.0}}, "batch": {}}
    cfg["llm"]["service_tier_search"] = "default"
    cfg["llm"]["budget_usd"]["phase3_calibration"] = 0.01
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    return cfg, conn


def test_call_saves_request_counts_tokens_and_bills_the_ledger(env):
    cfg, conn = env
    tr = FakeTransport()
    c = L.LLMClient(cfg, conn, "phase3_calibration", "run_t", transport=tr, sleep=lambda s: None)
    r = c.call("m1", "STABLE PREFIX", "variable suffix", tag="gen1")
    assert r["text"].startswith("module") and r["usage"] == {"input_tokens": 1000, "cached_tokens": 400, "cache_write_tokens": 100, "output_tokens": 200, "reasoning_tokens": 50}
    assert abs(r["cost_usd"] - ((500 * 2.0 + 400 * 0.5 + 100 * 2.5 + 200 * 8.0) / 1e6)) < 1e-12  # cached and cache-write tokens at their own rates
    assert abs(L.cost_usd({"input": 1.0, "cached_input": 0.1, "output": 4.0}, {"input_tokens": 10, "cached_tokens": 0, "cache_write_tokens": 5, "output_tokens": 0}) - 10 / 1e6) < 1e-15  # no cache-write price -> input rate
    kw = tr.calls[0]
    assert kw["instructions"] == "STABLE PREFIX" and kw["input"] == "variable suffix" and kw["store"] is False and kw["prompt_cache_key"]
    assert kw["max_output_tokens"] == cfg["llm"]["max_output_tokens"] and kw["reasoning"] == {"effort": cfg["llm"]["reasoning_effort"]} and "temperature" not in kw
    saved = json.loads(Path(r["path"]).read_text())
    assert saved["usage"] == r["usage"] and saved["cost_usd"] == r["cost_usd"] and saved["model"] == "m1" and saved["tier"] == "standard" and "OPENAI" not in json.dumps(saved)
    assert abs(L.spent_usd(conn, "phase3_calibration") - r["cost_usd"]) < 1e-12
    row = conn.execute("SELECT kind, unit, phase, run_id FROM budget_ledger").fetchone()
    assert tuple(row) == ("llm", "usd", "phase3_calibration", "run_t")
    real = C.load()["llm"]["prices_usd_per_1m"]
    assert set(real) == {"standard", "flex", "batch"} and all(set(real[t]) >= set(C.load()["llm"]["candidates"]) for t in real)
    assert real["flex"]["gpt-5.6-terra"]["input"] == 0.5 * real["standard"]["gpt-5.6-terra"]["input"]


def test_billing_follows_the_served_tier(env):
    cfg, conn = env
    flex = L.LLMClient(cfg, conn, "phase4_generation", "run_f", transport=FakeTransport(), sleep=lambda s: None)
    r = flex.call("m1", "p", "s", service_tier="flex")
    assert r["tier"] == "flex" and abs(r["cost_usd"] - ((500 * 1.0 + 400 * 0.25 + 100 * 1.25 + 200 * 4.0) / 1e6)) < 1e-12
    fallback = L.LLMClient(cfg, conn, "phase4_generation", "run_g", transport=FakeTransport(served_tier="default"), sleep=lambda s: None)
    r2 = fallback.call("m1", "p", "s", service_tier="flex")  # requested flex, served at standard -> standard rates
    assert r2["tier"] == "standard" and abs(r2["cost_usd"] - 2 * r["cost_usd"]) < 1e-15
    with pytest.raises(L.PriceUnknown):
        flex.call("m1", "p", "s", service_tier="batch")  # no batch price in this test table
    assert L.LLMClient.tier_of("priority") == "standard" and L.LLMClient.tier_of(None) == "standard" and L.LLMClient.tier_of("Flex") == "flex"


def test_hard_stop_at_the_phase_cap(env):
    cfg, conn = env
    c = L.LLMClient(cfg, conn, "phase3_calibration", "run_t", transport=FakeTransport(), sleep=lambda s: None)
    n = 0
    with pytest.raises(L.BudgetExceeded):
        for _ in range(100):
            c.call("m1", "p", "s")
            n += 1
    assert n >= 1 and L.spent_usd(conn, "phase3_calibration") >= 0.95 * 0.01 and L.spent_usd(conn, "phase3_calibration") < 0.01 + 0.005
    other = L.LLMClient(cfg, conn, "phase4_generation", "run_u", transport=FakeTransport(), sleep=lambda s: None)
    assert other.call("m1", "p", "s")["cost_usd"] > 0  # another phase's cap is untouched


def test_unknown_price_and_retries(env):
    cfg, conn = env
    c = L.LLMClient(cfg, conn, "phase3_calibration", "run_t", transport=FakeTransport(), sleep=lambda s: None)
    with pytest.raises(L.PriceUnknown):
        c.call("m_tbd", "p", "s")
    with pytest.raises(L.PriceUnknown):
        c.call("nope", "p", "s")
    assert conn.execute("SELECT COUNT(*) FROM budget_ledger").fetchone()[0] == 0
    tr = FakeTransport(fail_first=2)
    r = L.LLMClient(cfg, conn, "phase3_calibration", "run_t", transport=tr, sleep=lambda s: None).call("m1", "p", "s", retries=3)
    assert r["status"] == "completed" and len(tr.calls) == 3
    tr = FakeTransport(fail_first=5)
    with pytest.raises(RuntimeError):
        L.LLMClient(cfg, conn, "phase3_calibration", "run_t", transport=tr, sleep=lambda s: None).call("m1", "p", "s", retries=2)
    assert conn.execute("SELECT COUNT(*) FROM budget_ledger").fetchone()[0] == 1  # the failed call is not billed


def test_real_transport_needs_the_key_in_the_environment(monkeypatch, env):
    cfg, conn = env
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="not set"):
        L.OpenAITransport("OPENAI_API_KEY")


def test_transient_failures_back_off_exponentially_and_request_errors_do_not_retry(env):
    """2026-09-15 (probe): a 429 with a status code is retried with the configured exponential backoff (15, 30, 60 s ...) until it
    succeeds; a 4xx request error raises at once without a wait (both directions)."""
    cfg, conn = env[0], env[1]
    cfg["llm"]["retry"] = {"attempts": 6, "base_sec": 15, "max_sec": 480}

    class Err(Exception):
        def __init__(self, code):
            super().__init__(f"code {code}")
            self.status_code = code

    class T:
        def __init__(self, codes):
            self.codes, self.calls = list(codes), 0

        def create(self, **kw):
            self.calls += 1
            if self.codes:
                raise Err(self.codes.pop(0))
            return fake_response()
    slept = []
    c = L.LLMClient(cfg, conn, "phase3_calibration", "run_r", transport=T([429, 503, 429]), sleep=slept.append)
    r = c.call("m1", "p", "s")
    assert r["text"] and slept == [15.0, 30.0, 60.0]
    slept.clear()
    bad = L.LLMClient(cfg, conn, "phase3_calibration", "run_r2", transport=T([400]), sleep=slept.append)
    with pytest.raises(Err):
        bad.call("m1", "p", "s")
    assert slept == [] and L.transient_error(Err(429)) and L.transient_error(Err(500)) and not L.transient_error(Err(404)) and L.transient_error(RuntimeError("x")) and not L.transient_error(ValueError("x"))
