"""LLM client (docs/spec/05-search.md §8, PLAN 3.1): OpenAI Responses API with a cache-friendly prefix, fixed
sampling parameters from config (`llm`), every request and response saved to disk under results/llm/<run_id>/,
token counts and dollar cost recorded in the budget ledger, and a hard stop when a phase's cap is reached.

The API key is read from the environment variable named in config (`llm.api_key_env`) at call time and is never
written anywhere. Prices per million tokens come from config `llm.prices_usd_per_1m[tier][model] = {input,
cached_input, cache_write, output}` with tier = standard / flex / batch; a call is billed at the tier the response
reports (a flex request may be served at standard rates); a model without a price entry cannot be called. The transport is injectable
so that the accounting is testable without the network."""
import datetime
import fcntl
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src import config as C
from src.db import core as db


class BudgetExceeded(RuntimeError):
    pass


class QuotaExhausted(RuntimeError):
    """The API account has no credits (429 insufficient_quota / credit_balance_exhausted, 2026-09-16): not a transient failure —
    the run pauses (exit 75, the queue's backoff) instead of failing, and resumes from its state once the account is topped up."""


def quota_exhausted(e):
    code = getattr(e, "status_code", None)
    text = str(e)
    return (code == 429 or code is None) and ("insufficient_quota" in text or "credit_balance_exhausted" in text or "no credits remaining" in text)


class PriceUnknown(ValueError):
    pass


def spent_usd(conn, phase):
    row = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM budget_ledger WHERE kind='llm' AND unit='usd' AND phase=?", (phase,)).fetchone()
    return float(row[0] or 0.0)


def cost_usd(prices, usage):
    """usage: {input_tokens, cached_tokens, cache_write_tokens, output_tokens}; cached tokens are billed at the cached
    rate, cache writes at the cache-write rate (the input rate for models without a separate one), the rest at the input rate."""
    cached = int(usage.get("cached_tokens") or 0)
    writes = int(usage.get("cache_write_tokens") or 0)
    fresh = max(0, int(usage.get("input_tokens") or 0) - cached - writes)
    write_rate = prices["input"] if prices.get("cache_write") is None else prices["cache_write"]  # no surcharge -> input rate
    return (fresh * float(prices["input"]) + cached * float(prices["cached_input"]) + writes * float(write_rate)
            + int(usage.get("output_tokens") or 0) * float(prices["output"])) / 1e6


def _usage_dict(resp):
    u = getattr(resp, "usage", None)
    if u is None:
        return {"input_tokens": 0, "cached_tokens": 0, "cache_write_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
    det_in = getattr(u, "input_tokens_details", None)
    det_out = getattr(u, "output_tokens_details", None)
    return {"input_tokens": int(getattr(u, "input_tokens", 0) or 0),
            "cached_tokens": int(getattr(det_in, "cached_tokens", 0) or 0) if det_in else 0,
            "cache_write_tokens": int(getattr(det_in, "cache_write_tokens", 0) or 0) if det_in else 0,
            "output_tokens": int(getattr(u, "output_tokens", 0) or 0),
            "reasoning_tokens": int(getattr(det_out, "reasoning_tokens", 0) or 0) if det_out else 0}


TRANSIENT_NAMES = {"RateLimitError", "APIConnectionError", "APITimeoutError", "InternalServerError", "RuntimeError", "ConnectionError", "TimeoutError"}


def transient_error(e):
    """A failure worth waiting for (2026-09-15): a 429 / 408 / 409 / 5xx status, or a connection / timeout class; a 4xx request
    error (bad request, authentication, not found) is never retried."""
    code = getattr(e, "status_code", None)
    if code is not None:
        try:
            code = int(code)
        except (TypeError, ValueError):
            return False
        return code in (408, 409, 429) or code >= 500
    return type(e).__name__ in TRANSIENT_NAMES


class OpenAITransport:
    """Real transport: one Responses API call. Constructed lazily so that tests never import network code."""

    def __init__(self, api_key_env):
        key = os.environ.get(api_key_env)
        if not key:
            raise RuntimeError(f"{api_key_env} is not set in the environment (source the secrets file first)")
        import openai
        self.client = openai.OpenAI(api_key=key)

    def create(self, **kw):
        return self.client.responses.create(**kw)


class LLMClient:
    def __init__(self, cfg, conn, phase, run_id, transport=None, sleep=time.sleep):
        self._slots = None
        self.cfg, self.conn, self.phase, self.run_id = cfg, conn, phase, run_id
        self.llm = cfg["llm"]
        self.cap = float(self.llm["budget_usd"][phase])
        self.stop_at = self.cap * float(self.llm["hard_stop_fraction"])
        self._transport = transport
        self.sleep = sleep
        self.dir = Path(C.results_dir(cfg)) / "llm" / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.calls = 0

    @property
    def transport(self):
        if self._transport is None:
            self._transport = OpenAITransport(self.llm["api_key_env"])
        return self._transport

    @staticmethod
    def tier_of(service_tier):
        """Price tier for a requested or reported service tier: flex -> flex, batch -> batch, anything else standard."""
        s = (service_tier or "default").lower()
        return "flex" if s == "flex" else "batch" if s == "batch" else "standard"

    def prices_for(self, model, tier="standard"):
        table = (self.llm.get("prices_usd_per_1m") or {}).get(tier) or {}
        p = table.get(model)
        if not p or any(C.is_tbd(p.get(k)) or p.get(k) is None for k in ("input", "cached_input", "output")):
            raise PriceUnknown(f"no {tier} price for model {model!r} in config llm.prices_usd_per_1m (input / cached_input / output per 1M tokens)")
        return p

    def check_budget(self):
        spent = spent_usd(self.conn, self.phase)
        if spent >= self.stop_at:
            raise BudgetExceeded(f"phase {self.phase}: {spent:.2f} USD spent, hard stop at {self.stop_at:.2f} of the {self.cap:.2f} cap (config llm.budget_usd)")
        return spent

    def prepare(self, model, prefix, suffix, *, tag="", max_output_tokens=None, reasoning_effort=None, temperature=None, service_tier=None):
        """The bookkeeping before a request (calling thread): price known, budget not exhausted, the request, the call id."""
        requested_tier = service_tier or self.llm.get("service_tier_search") or "default"
        self.prices_for(model, self.tier_of(requested_tier))  # refuse before the call when the price is unknown
        self.check_budget()
        cache_key = hashlib.sha256(prefix.encode()).hexdigest()[:32]
        kw = {"model": model, "instructions": prefix, "input": suffix, "store": False, "prompt_cache_key": cache_key,
              "max_output_tokens": int(max_output_tokens or self.llm["max_output_tokens"]),
              "service_tier": requested_tier}
        effort = reasoning_effort or self.llm.get("reasoning_effort")
        if effort:
            kw["reasoning"] = {"effort": effort}
        temp = self.llm.get("temperature") if temperature is None else temperature
        if temp is not None and not effort:
            kw["temperature"] = float(temp)  # reasoning models fix their own sampling temperature
        self.calls += 1
        call_id = f"c{self.calls:05d}_{datetime.datetime.now():%H%M%S}"
        return {"model": model, "kw": kw, "call_id": call_id, "tag": tag, "requested_tier": requested_tier}

    def request(self, spec, retries=None, slots=None):
        """The network part (any thread): the request with the retry rule (`llm.retry`: transient failures back off exponentially,
        request errors raise at once, an exhausted account raises QuotaExhausted); one of the global slots is held meanwhile.
        -> spec with resp, last_error, t0, seconds."""
        kw, call_id, tag = spec["kw"], spec["call_id"], spec["tag"]
        t0 = time.time()
        last_error = None
        rp = self.llm.get("retry") or {}
        if retries is None:
            retries = int(rp.get("attempts", 3))
        base, cap = float(rp.get("base_sec", 2.0)), float(rp.get("max_sec", 480.0))
        slot = slots.acquire() if slots is not None else None
        try:
            for attempt in range(retries + 1):
                try:
                    resp = self.transport.create(**kw)
                    break
                except Exception as e:  # transient failures (rate limits, connection, 5xx): exponential backoff, then give up loudly; request errors: at once
                    last_error = e
                    if quota_exhausted(e):
                        (self.dir / f"{call_id}.json").write_text(json.dumps({"call_id": call_id, "tag": tag, "request": kw, "error": f"{type(e).__name__}: {e}"[:500], "attempts": attempt + 1, "quota_exhausted": True}, indent=1, default=str))
                        raise QuotaExhausted(f"{type(e).__name__}: {e}"[:300]) from e
                    if attempt == retries or not transient_error(e):
                        (self.dir / f"{call_id}.json").write_text(json.dumps({"call_id": call_id, "tag": tag, "request": kw, "error": f"{type(e).__name__}: {e}"[:500],
                                                                              "attempts": attempt + 1}, indent=1, default=str))
                        raise
                    self.sleep(min(cap, base * (2 ** attempt)))
        finally:
            if slot is not None:
                slots.release(slot)
        return dict(spec, resp=resp, last_error=last_error, t0=t0, seconds=round(time.time() - t0, 2))

    def finish(self, done):
        """The bookkeeping after a request (calling thread): the record file and the budget ledger. -> the call's result."""
        resp, kw, call_id, tag, model = done["resp"], done["kw"], done["call_id"], done["tag"], done["model"]
        usage = _usage_dict(resp)
        used_tier = self.tier_of(getattr(resp, "service_tier", None) or done["requested_tier"])  # flex may fall back to standard
        prices = self.prices_for(model, used_tier)
        cost = cost_usd(prices, usage)
        text = getattr(resp, "output_text", None) or ""
        rec = {"call_id": call_id, "tag": tag, "run_id": self.run_id, "phase": self.phase, "model": model, "tier": used_tier, "request": kw,
               "response_id": getattr(resp, "id", None), "status": getattr(resp, "status", None), "text": text, "usage": usage,
               "cost_usd": cost, "seconds": done["seconds"], "at": db.now(), "last_error": str(done["last_error"]) if done["last_error"] else None}
        path = self.dir / f"{call_id}.json"
        path.write_text(json.dumps(rec, indent=1, default=str))
        db.insert(self.conn, "budget_ledger", {"ts": db.now(), "phase": self.phase, "kind": "llm", "amount": cost, "unit": "usd",
                                               "run_id": self.run_id, "note": f"{model} {call_id} {tag}"[:120]})
        return {"call_id": call_id, "text": text, "usage": usage, "cost_usd": cost, "tier": used_tier, "response_id": rec["response_id"],
                "status": rec["status"], "path": str(path)}

    def call(self, model, prefix, suffix, *, tag="", max_output_tokens=None, reasoning_effort=None, temperature=None,
             service_tier=None, retries=None):
        """prefix: the stable, cacheable part (system + design context); suffix: the variable part.
        -> dict(call_id, text, usage, cost_usd, response_id, status, path)."""
        spec = self.prepare(model, prefix, suffix, tag=tag, max_output_tokens=max_output_tokens, reasoning_effort=reasoning_effort,
                            temperature=temperature, service_tier=service_tier)
        return self.finish(self.request(spec, retries=retries, slots=self.slots()))

    def slots(self):
        """The global concurrency cap on LLM requests across every run (user follow-up 2026-09-16, item 2: `llm.parallel.global_max`,
        lock files under <results>/queue/llm_slots); None when the parallel block is off."""
        par = self.llm.get("parallel") or {}
        if not par.get("enabled"):
            return None
        if self._slots is None:
            self._slots = Slots(Path(C.results_dir(self.cfg)) / "queue" / "llm_slots", int(par.get("global_max") or 8), sleep=self.sleep)
        return self._slots

    def call_many(self, specs, *, max_workers=None):
        """The calls of one generation issued concurrently (user follow-up 2026-09-16, item 2): specs = list of dicts of call()
        keyword arguments (model, prefix, suffix, tag, ...). Call ids, record files and the ledger stay on the calling thread and
        in the order of `specs`; the requests run in threads, each holding one of the global slots; the retry rule is the
        sequential one. A QuotaExhausted from any request is raised once the others have ended (their answers are recorded); any
        other failure is raised the same way. -> the results in the order of specs."""
        prepared = [self.prepare(sp["model"], sp["prefix"], sp["suffix"], tag=sp.get("tag", ""), max_output_tokens=sp.get("max_output_tokens"),
                                 reasoning_effort=sp.get("reasoning_effort"), temperature=sp.get("temperature"), service_tier=sp.get("service_tier")) for sp in specs]
        par = self.llm.get("parallel") or {}
        workers = max(1, min(len(prepared), int(max_workers or par.get("global_max") or 8)))
        slots = self.slots()
        outcomes = [None] * len(prepared)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(self.request, p, slots=slots) for p in prepared]
            for i, f in enumerate(futs):
                try:
                    outcomes[i] = ("ok", f.result())
                except BaseException as e:   # noqa: BLE001 — recorded per call; raised below after every request has ended
                    outcomes[i] = ("err", e)
        results = [self.finish(o[1]) if o[0] == "ok" else None for o in outcomes]
        errors = [o[1] for o in outcomes if o[0] == "err"]
        if errors:
            quota = [e for e in errors if isinstance(e, QuotaExhausted)]
            raise (quota or errors)[0]
        return results


class Slots:
    """A cross-process semaphore: `n` lock files; a holder keeps an flock on one of them for the duration of its request and the
    slot returns to the pool when the lock is released or the process dies (user follow-up 2026-09-16, item 2)."""
    def __init__(self, directory, n, sleep=time.sleep, poll_sec=0.5):
        self.dir, self.n, self.sleep, self.poll_sec = Path(directory), max(1, int(n)), sleep, float(poll_sec)
        self.dir.mkdir(parents=True, exist_ok=True)

    def acquire(self):
        while True:
            for k in range(self.n):
                fd = os.open(str(self.dir / f"slot_{k}"), os.O_CREAT | os.O_RDWR, 0o644)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return fd
                except OSError:
                    os.close(fd)
            self.sleep(self.poll_sec)

    def release(self, fd):
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
