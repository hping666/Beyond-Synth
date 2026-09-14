"""Offline tests of residual-guided evolution (spec 05; DECISIONS 2026-09-14): archive / bandit / prescreen rules, the
prompt assembly, and the run driver with a fake LLM transport and a real (daemon-less) queue whose verdicts the test
supplies: generations are built from arrived verdicts, late verdicts update archive and credit, a resumed run continues
from the persisted state, the produced class is credited (not the requested one), duplicates and identical texts get
their labels without evaluation, and the run stops at K generations."""
import copy
import json
import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import config as C
from src.db import core as db
from src.search.archive import Archive, crowding_distance, dominates, pareto_front
from src.search.bandit import ClassBandit
from src.search.prescreen import decide


def test_pareto_archive_rules():
    a = {"cand_id": "a", "gains": {"area": 0.10, "wns": 0.0, "power": 0.05}}
    b = {"cand_id": "b", "gains": {"area": 0.05, "wns": 0.0, "power": 0.02}}
    c = {"cand_id": "c", "gains": {"area": 0.02, "wns": 0.10, "power": 0.0}}
    assert dominates(a, b) and not dominates(b, a) and not dominates(a, c) and not dominates(c, a)
    assert {x["cand_id"] for x in pareto_front([a, b, c])} == {"a", "c"}
    arch = Archive(2)
    assert arch.add(a) and arch.add(c) and not arch.add(b)          # b is dominated: never enters
    d = {"cand_id": "d", "gains": {"area": 0.06, "wns": 0.05, "power": 0.02}}
    arch.add(d)                                                       # three non-dominated members, size 2: the boundary members stay
    assert len(arch.members) == 2 and {m["cand_id"] for m in arch.members} == {"a", "c"}
    dist = crowding_distance([a, c, d])
    assert dist["a"] == float("inf") and dist["c"] == float("inf") and dist["d"] < float("inf")
    rng = random.Random(1)
    assert arch.select_parent(rng)["cand_id"] in ("a", "c") and Archive(3).select_parent(rng) is None
    assert Archive.from_json(arch.to_json()).members == arch.members


def test_bandit_drifts_to_the_rewarded_class_and_credits_the_produced_class():
    b = ClassBandit(["a", "b", "c1", "d", "free"], c_ucb=0.5, softmax_temp=0.3)
    rng = random.Random(0)
    for _ in range(40):
        b.credit("d", 1)
        b.credit("a", 0)
    p = b.probs()
    assert p["d"] > p["a"] and p["d"] == max(p.values())
    assert b.credit("c2", 1) is False                # not an arm: ignored
    draws = b.draw(rng, 200)
    assert draws.count("d") > draws.count("a")
    b2 = ClassBandit.from_json(b.to_json())
    assert b2.n == b.n and b2.reward == b.reward and abs(b2.probs()["d"] - p["d"]) < 1e-12
    prior = ClassBandit(["a", "b"], prior={"b": 0.9})
    assert prior.probs()["b"] > prior.probs()["a"]   # the map prior initialises the preference


def test_prescreen_decisions():
    rng = random.Random(3)
    assert decide(None, "b", 0.9, 0.1, rng) == "evaluate" and decide({"b": 0.5}, "b", 0.9, 0.1, rng) == "evaluate"
    outcomes = [decide({"b": 0.95}, "b", 0.9, 0.1, rng) for _ in range(2000)]
    assert 150 < outcomes.count("audit") < 260 and outcomes.count("evaluate") == 0   # ≈10 % audited, the rest prescreened
    assert decide({"b": 0.95}, "d", 0.9, 0.1, rng) == "evaluate"                       # another class has no prior


# ----------------------------------------------------------------------------- the driver with fakes
RTL_D = "module d(input clk, input rst_n, input [3:0] x, output reg [3:0] y);\n  always @(posedge clk or negedge rst_n) if (!rst_n) y <= 0; else y <= x + 4'd1;\nendmodule\n"


def rewrite(tag):
    return "module d(input clk, input rst_n, input [3:0] x, output reg [3:0] y);\n  wire [3:0] t_%s = x + 4'd1;\n  always @(posedge clk or negedge rst_n) if (!rst_n) y <= 0; else y <= t_%s;\nendmodule\n" % (tag, tag)


class FakeTransport:
    """Answers one rewrite per call, tagged by the call number; call 3 repeats call 2 (a duplicate); call 4 is unusable."""
    def __init__(self):
        self.calls = 0

    def create(self, **kw):
        self.calls += 1
        n = self.calls
        if n == 4:
            text = "sorry, no"
        elif n == 3:
            text = json.dumps({"rtl": rewrite("v2"), "note": "same again"})
        else:
            text = json.dumps({"rtl": rewrite(f"v{n}"), "note": f"rewrite {n}"})

        class R:
            pass
        r = R()
        r.output_text, r.id, r.status, r.service_tier = text, f"resp{n}", "completed", "flex"
        r.usage = SimpleNamespace(input_tokens=100, output_tokens=50, input_tokens_details=SimpleNamespace(cached_tokens=0, cache_write_tokens=0), output_tokens_details=None)
        return r


@pytest.fixture
def env(tmp_path, monkeypatch):
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["search"]["gen_wait_sec"] = 10 ** 9
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    from src.designs import catalog as K
    from src.search import candidates as CA
    from src.search import driver as DR
    from src.search import llm as L
    monkeypatch.setattr(K, "DESIGNS_DIR", tmp_path / "designs")
    monkeypatch.setattr(CA, "CAND_DIR", tmp_path / "cands")
    monkeypatch.setattr(L, "LLM_DIR", tmp_path / "llm", raising=False)
    ddir = tmp_path / "designs" / "rtllm" / "d"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "d.v").write_text(RTL_D)
    d = {"design_id": "rtllm_d", "suite": "rtllm", "name": "d", "top": "d", "files": ["rtl/d.v"], "clk_ports": ["clk"], "rst_port": "rst_n", "rst_sense": "low",
         "sverilog": False, "incdirs": [], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/d.v": K.sha256_of(ddir / "rtl" / "d.v")}, "loc": 3, "tags": ["rtllm"], "notes": [], "_dir": str(ddir)}
    K.write_design(d)
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('rtllm_d','rtllm','d','x',3,1,'dev',1.0,'t','g','c')")
    db.insert(conn, "evaluations", {"design_id": "rtllm_d", "is_baseline": 1, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 100.0, "cells": 20, "wns_ns": 0.1, "tns_ns": 0.0,
                                    "power_saif_mw": 1.0, "status": "ok", "raw_dir": "/x/base", "hist_json": json.dumps({"DFF_X1": 4, "NAND2_X1": 16})})
    from src.noise import stats as S
    S.upsert_floor(conn, [{"design_id": "rtllm_d", "config": "E4", "metric": m, "sigma_robust": 0.0, "sigma_std": 0.0, "q95_abs": 0.0, "max_abs": 0.0, "n": 4, "abs_unit_value": None,
                           "t_d": t, "floor_class": "quiet", "floor_source": "measured", "pooled_min": t} for m, t in (("area", 0.003), ("wns", 0.001), ("power_saif", 0.014))])
    # M6 features need Yosys; replace with a stub that reads the class from the candidate text
    monkeypatch.setattr(DR.M6, "features", lambda *a, **k: {"regs_d": set(), "regs_c": set(), "targets_d": set(), "targets_c": set(), "ff_d": 4, "ff_c": 4, "max_offset": 0, "diff_ratio": 0.1})
    monkeypatch.setattr(DR.M6, "classify", lambda feat, **k: {"class_rule": "b", "rules": ["stub"], "confidence": 0.8, "needs_review": False})
    from src.jobqueue.core import Queue
    q = Queue(cfg, conn, str(tmp_path / "results" / "queue" / "logs"), env={}, log=lambda m: None)
    return cfg, conn, q, tmp_path


def finish_eq(conn, cfg, tmp_path, cand_id, design_id="rtllm_d", verdict="proven"):
    """The test plays the equivalence runner: a record under the content-addressed directory the runner would use
    (results/raw/<design>/EQ/<hash>) and the job marked done."""
    from src.equiv.run_equiv import equiv_hash
    jid0 = conn.execute("SELECT eq_job_id FROM candidates WHERE cand_id=?", (cand_id,)).fetchone()[0]
    p = json.loads(conn.execute("SELECT payload_json FROM jobs WHERE job_id=?", (jid0,)).fetchone()[0])
    extra = {"stages": "full", "clk": p.get("clk"), "rst": p.get("rst"), "rst_sense": p.get("rst_sense"), "sverilog": p.get("sverilog", False), "sim_seed": p.get("sim_seed"), "c_top": p.get("c_top")}
    d = Path(cfg["project"]["results_dir"]) / "raw" / design_id / "EQ" / equiv_hash(p["d_rtl"], p["c_rtl"], p["top"], cfg, extra)
    d.mkdir(parents=True, exist_ok=True)
    (d / "equiv.json").write_text(json.dumps({"cand_id": cand_id, "verdict": verdict, "v1_status": "ok", "v2_status": "identical", "v2_cycles": 100,
                                              "latency_offset_json": "{}", "v3_status": verdict, "v3_seconds": 5.0, "v4_status": "not_run", "seconds": 8.0, "proven_by": "seq" if verdict == "proven" else None}))
    jid = conn.execute("SELECT eq_job_id FROM candidates WHERE cand_id=?", (cand_id,)).fetchone()[0]
    conn.execute("UPDATE jobs SET state='done' WHERE job_id=?", (jid,))


def finish_e4(conn, cand_id, area, hist=None, design_id="rtllm_d"):
    jid = conn.execute("SELECT e4_job_id FROM candidates WHERE cand_id=?", (cand_id,)).fetchone()[0]
    conn.execute("UPDATE jobs SET state='done' WHERE job_id=?", (jid,))
    db.insert(conn, "evaluations", {"design_id": design_id, "cand_id": cand_id, "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": area, "cells": 20,
                                    "wns_ns": 0.1, "tns_ns": 0.0, "power_saif_mw": 1.0, "dc_seconds": 60.0, "status": "ok", "raw_dir": f"/x/{cand_id}", "hist_json": json.dumps(hist or {"DFF_X1": 4, "NAND2_X1": 15})})


def test_driver_generations_verdicts_credit_and_resumption(env):
    cfg, conn, q, tmp_path = env
    from src.search.driver import SearchRun
    tr = FakeTransport()
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=1, model="gpt-5.6-luna", K=2, N=3, queue=q, transport=tr)
    assert run.step() == "running"                     # generation 1 issued: 3 calls -> candidates v1, v2 and the duplicate of v2
    cands = {r["cand_id"]: dict(r) for r in conn.execute("SELECT * FROM candidates WHERE run_id=?", (run.run_id,))}
    labels = sorted((c["label"] or "pending") for c in cands.values())
    assert labels == ["duplicate", "pending", "pending"] and run.state["gen"] == 1 and run.state["calls"] == 3
    pending = [cid for cid, c in cands.items() if not c["label"]]
    assert all(cands[c]["eq_job_id"] for c in pending) and all(cands[c]["class_requested"] in cfg["search"]["bandit"]["arms"] for c in pending)
    assert run.step() == "running" and run.state["gen"] == 1      # nothing arrived: no new generation (gen_wait is huge)
    # one verdict arrives: proven -> E4 job; the other stays pending; the generation is not due yet
    finish_eq(conn, cfg, tmp_path, pending[0], verdict="proven")
    run.step()
    assert run.state["pending"][pending[0]] == "e4" and conn.execute("SELECT e4_job_id FROM candidates WHERE cand_id=?", (pending[0],)).fetchone()[0]
    # its E4 record: 10 % smaller -> retained, archive, credit on the produced class b (the stub), not the requested class
    finish_e4(conn, pending[0], 90.0)
    run.step()
    d1 = dict(conn.execute("SELECT * FROM diagnoses WHERE cand_id=?", (pending[0],)).fetchone())
    assert d1["label"] == "retained" and d1["credit"] == 1 and d1["credited_class"] == "b"
    assert run.archive.members[0]["cand_id"] == pending[0] and run.bandit.n["b"] >= 1 and run.bandit.reward["b"] == 1.0
    # the second candidate is falsified -> nonequiv, no credit; now generation 2 is due and built (calls 4: unusable, 5, 6)
    finish_eq(conn, cfg, tmp_path, pending[1], verdict="falsified")
    saved_state = json.loads(run.state_path.read_text())
    run.step()
    assert dict(conn.execute("SELECT * FROM diagnoses WHERE cand_id=?", (pending[1],)).fetchone())["label"] == "nonequiv"
    assert run.state["gen"] == 2 and run.state["calls"] == 6 and (tmp_path / "cands" / run.run_id).exists()
    assert (Path(run.dir) / "unusable_g2_0.json").exists()   # the unusable answer is recorded, not repaired
    gen2 = [c for c in run.state["cands"].values() if c["gen"] == 2 and c.get("state") != "final"]
    assert len(gen2) == 2 and all(c["parent_id"] == pending[0] for c in gen2)   # the retained candidate is the parent
    # resumption: a new driver object continues from the state file and the database, with the verdicts arriving later
    run2 = SearchRun.resume(cfg, conn, run.run_id, queue=q, transport=tr)
    assert run2.state["gen"] == 2 and run2.archive.members == run.archive.members and run2.bandit.n == run.bandit.n
    for c in gen2:
        finish_eq(conn, cfg, tmp_path, c["cand_id"], verdict="proven")
    run2.step()
    finish_e4(conn, gen2[0]["cand_id"], 100.0, hist={"DFF_X1": 4, "NAND2_X1": 16})   # D's netlist exactly: absorbed_identical, stored with a legal attribution
    finish_e4(conn, gen2[1]["cand_id"], 99.9, hist={"DFF_X1": 4, "NAND2_X1": 16})    # within the floor, fingerprint converged: absorbed
    assert run2.step() == "done"                                    # K = 2 generations built, nothing pending
    d2 = {r["cand_id"]: dict(r) for r in conn.execute("SELECT * FROM diagnoses WHERE run_id=?", (run.run_id,))}
    assert d2[gen2[0]["cand_id"]]["label"] == "absorbed_identical" and d2[gen2[0]["cand_id"]]["attribution"] == "measured"
    assert d2[gen2[1]["cand_id"]]["label"] in ("absorbed", "noise")
    row = dict(conn.execute("SELECT * FROM runs WHERE run_id=?", (run.run_id,)).fetchone())
    assert row["status"] == "done" and row["llm_calls"] == 6 and row["gens_done"] == 2 and row["spent_usd"] > 0
    labels = {r["cand_id"]: r["label"] for r in conn.execute("SELECT cand_id, label FROM candidates WHERE run_id=?", (run.run_id,))}
    assert sorted(labels.values()).count("retained") == 1 and "nonequiv" in labels.values()
    gs = [dict(r) for r in conn.execute("SELECT * FROM gen_summary WHERE run_id=? ORDER BY gen", (run.run_id,))]
    assert [g["gen"] for g in gs] == [1, 2] and gs[1]["retained_count_cum"] == 1 and json.loads(gs[0]["pending_json"])


def test_identical_text_and_prescreen_labels_without_evaluation(env, monkeypatch):
    cfg, conn, q, tmp_path = env
    from src.search.driver import SearchRun

    class Identical:
        calls = 0

        def create(self, **kw):
            self.calls += 1

            class R:
                pass
            r = R()
            r.output_text = json.dumps({"rtl": RTL_D, "note": "unchanged"}) if self.calls == 1 else json.dumps({"rtl": rewrite("p"), "note": "x"})
            r.id, r.status, r.service_tier = f"r{self.calls}", "completed", "flex"
            r.usage = SimpleNamespace(input_tokens=10, output_tokens=5, input_tokens_details=SimpleNamespace(cached_tokens=0, cache_write_tokens=0), output_tokens_details=None)
            return r
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=2, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=Identical())
    run.prior = {"b": 0.95}          # a map prior that calls class b absorbed: the second answer is prescreened (or audited)
    monkeypatch.setattr("src.search.driver.prescreen_decide", lambda *a, **k: "prescreened")
    run.step()
    labels = {r["cand_id"]: r["label"] for r in conn.execute("SELECT cand_id, label FROM candidates WHERE run_id=?", (run.run_id,))}
    assert sorted(labels.values()) == ["absorbed_identical", "prescreened"]
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0       # nothing was submitted for either
    assert run.step() == "done"


def test_auroc_helper():
    import importlib.util
    spec = importlib.util.spec_from_file_location("p3", str(Path(C.ROOT) / "scripts" / "phase3_calibrate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.auroc([0.9, 0.8], [0.1, 0.2]) == 1.0 and mod.auroc([0.1], [0.9]) == 0.0 and mod.auroc([0.5], [0.5]) == 0.5
    assert abs(mod.auroc([0.9, 0.3], [0.5, 0.1]) - 0.75) < 1e-12 and mod.auroc([], [0.1]) is None


def test_candidate_ids_are_per_run_and_keep_the_content_hash():
    from src.search import candidates as CA
    rtl = "module d(input a, output y); assign y = a; endmodule\n"
    assert CA.cand_id_of(rtl) == CA.cand_id_of(rtl) and CA.cand_id_of(rtl, "run1") != CA.cand_id_of(rtl, "run2") != CA.cand_id_of(rtl)
    assert CA.cand_id_of(rtl, "run1") == CA.cand_id_of(rtl, "run1")
