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
from src.search import scope as SC
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
    cfg["search"]["map_prior_file"] = None   # the Phase 4 prior is tested on its own; the driver tests start without it
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


def finish_eq(conn, cfg, tmp_path, cand_id, design_id="rtllm_d", verdict="proven", extra_rec=None):
    """The test plays the equivalence runner: a record under the content-addressed directory the runner would use
    (results/raw/<design>/EQ/<hash>) and the job marked done."""
    from src.equiv.run_equiv import equiv_extra, equiv_hash
    jid0 = conn.execute("SELECT eq_job_id FROM candidates WHERE cand_id=?", (cand_id,)).fetchone()[0]
    p = json.loads(conn.execute("SELECT payload_json FROM jobs WHERE job_id=?", (jid0,)).fetchone()[0])
    d = Path(cfg["project"]["results_dir"]) / "raw" / design_id / "EQ" / equiv_hash(p["d_rtl"], p["c_rtl"], p["top"], cfg, equiv_extra(cfg, p, True))
    d.mkdir(parents=True, exist_ok=True)
    rec = {"cand_id": cand_id, "verdict": verdict, "v1_status": "ok", "v2_status": "identical", "v2_cycles": 100,
           "latency_offset_json": "{}", "v3_status": verdict, "v3_seconds": 5.0, "v4_status": "not_run", "seconds": 8.0, "proven_by": "seq" if verdict == "proven" else None}
    rec.update(extra_rec or {})
    (d / "equiv.json").write_text(json.dumps(rec))
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
    # the second candidate is falsified -> nonequiv, no credit, one repair call (4: unusable); now generation 2 is due and built (calls 5, 6)
    finish_eq(conn, cfg, tmp_path, pending[1], verdict="falsified")
    saved_state = json.loads(run.state_path.read_text())
    run.step()
    assert dict(conn.execute("SELECT * FROM diagnoses WHERE cand_id=?", (pending[1],)).fetchone())["label"] == "nonequiv"
    assert run.state["gen"] == 2 and run.state["calls"] == 6 and run.dir.exists() and str(run.dir).startswith(str(tmp_path))   # run directory under the configured results_dir
    # G5 item 1 (ii): the falsified candidate got one repair call (call 4, the unusable answer): recorded, no candidate, the budget charged;
    # generation 2 then had two calls left (5, 6). An unusable answer itself is never repaired.
    rep = run.state["repairs"]
    assert len(rep) == 1 and rep[0]["of"] == pending[1] and rep[0]["failure"] == "falsified" and rep[0]["unusable"] and rep[0]["cand_id"] is None
    assert (Path(run.dir) / f"unusable_repair_{pending[1]}.json").exists() and not (Path(run.dir) / "unusable_g2_0.json").exists()
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


def test_resume_is_idempotent_after_a_crash_between_diagnosis_and_state_save(env):
    """A previous attempt diagnosed a candidate (diagnoses row exists) and submitted E4 jobs but died before saving the
    state: the resumed run syncs from the rows instead of inserting twice; two identical answers in one generation give
    two distinct duplicate rows; candidate rows unknown to the state are marked aborted."""
    cfg, conn, q, tmp_path = env
    from src.search.driver import SearchRun
    tr = FakeTransport()
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=7, model="gpt-5.6-luna", K=2, N=3, queue=q, transport=tr)
    run.step()
    snapshot = run.state_path.read_text()                     # the state as persisted after generation 1
    pending = [cid for cid, c in run.state["cands"].items() if c.get("state") != "final"]
    finish_eq(conn, cfg, tmp_path, pending[0], verdict="proven")
    run.step()                                                # E4 submitted (state saved)
    saved_after_e4 = run.state_path.read_text()
    finish_e4(conn, pending[0], 90.0)
    run.step()                                                # diagnosed: diagnoses row exists, state saved ...
    run.state_path.write_text(saved_after_e4)                 # ... but pretend the process died before that save
    db.insert(conn, "candidates", {"cand_id": "corphan", "run_id": run.run_id, "design_id": "rtllm_d", "gen": 2, "arm": "M", "llm_model": "gpt-5.6-luna", "rtl_path": "/x"})
    run2 = SearchRun.resume(cfg, conn, run.run_id, queue=q, transport=tr)
    assert conn.execute("SELECT label FROM candidates WHERE cand_id='corphan'").fetchone()[0] == "aborted"
    run2.step()                                               # no UNIQUE error: the diagnosis row is reused, the archive and the credit rebuilt
    assert conn.execute("SELECT COUNT(*) FROM diagnoses WHERE cand_id=?", (pending[0],)).fetchone()[0] == 1
    assert run2.state["cands"][pending[0]]["label"] == "retained" and run2.archive.members[0]["cand_id"] == pending[0] and run2.bandit.reward["b"] == 1.0
    # identical answers twice in one generation: call 2 and call 3 of the fake are the same RTL; a second run's generation
    # gets distinct duplicate ids (dup<gen>_<index>)
    dups = [r[0] for r in conn.execute("SELECT cand_id FROM candidates WHERE run_id=? AND label='duplicate'", (run.run_id,))]
    assert dups and all("_dup" in d for d in dups) and len(dups) == len(set(dups))


def test_driver_b0_arm_uses_y_fitness_and_scalar_feedback(env):
    """spec 05 §5 / PLAN 4.1: arm B0 evaluates proven candidates under Y (queue kind yosys, config Y), needs no floor, labels
    any positive gain `improved` (credit 1, archive) and anything else `no_gain` (credit 0); the feedback block carries the
    numbers only and no diagnosis row is written (the M3 diagnosis at E4 belongs to the analysis). Both directions."""
    cfg, conn, q, tmp_path = env
    from src.search.driver import SearchRun
    db.insert(conn, "evaluations", {"design_id": "rtllm_d", "is_baseline": 1, "config": "Y", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 80.0, "cells": 18, "wns_ns": 0.2, "tns_ns": 0.0,
                                    "power_default_mw": 0.8, "status": "ok", "raw_dir": "/x/base_y", "hist_json": json.dumps({"DFF_X1": 4, "NAND2_X1": 14})})
    tr = FakeTransport()
    run = SearchRun.create(cfg, conn, exp="smoke", arm="B0", design_id="rtllm_d", seed=1, model="gpt-5.6-luna", K=1, N=3, queue=q, transport=tr)
    assert run.fit_cfg == "Y" and run.scalar and run.floor == {} and "Yosys" not in run.system and "compile_ultra" not in run.system   # tool-neutral objective (decision 2026-09-15 item 3 (i))
    assert "Yosys + OpenSTA (Y) result" in run.prefix and "noise floor" not in run.prefix
    assert run.step() == "running"
    cands = [r[0] for r in conn.execute("SELECT cand_id FROM candidates WHERE run_id=? AND eq_job_id IS NOT NULL ORDER BY gen, cand_id", (run.run_id,))]
    assert len(cands) == 2                                  # v1, v2 (the duplicate of v2 needs no evaluation)
    for cid in cands:
        finish_eq(conn, cfg, tmp_path, cid)
    run.process_verdicts()
    jobs = {r[0]: (r[1], r[2]) for r in conn.execute("SELECT c.cand_id, j.kind, j.config FROM candidates c JOIN jobs j ON j.job_id=c.e4_job_id WHERE c.run_id=?", (run.run_id,))}
    assert all(v == ("yosys", "Y") for v in jobs.values()) and set(jobs) == set(cands)   # the fitness job is a Yosys job, never a DC seat
    better, worse = cands
    for cid, area in ((better, 72.0), (worse, 88.0)):
        jid = conn.execute("SELECT e4_job_id FROM candidates WHERE cand_id=?", (cid,)).fetchone()[0]
        conn.execute("UPDATE jobs SET state='done' WHERE job_id=?", (jid,))
        db.insert(conn, "evaluations", {"design_id": "rtllm_d", "cand_id": cid, "is_baseline": 0, "config": "Y", "lib": "nangate45", "clock_ns": 1.0, "area_um2": area, "cells": 18,
                                        "wns_ns": 0.2, "tns_ns": 0.0, "power_default_mw": 0.8, "status": "ok", "raw_dir": f"/y/{cid}", "hist_json": json.dumps({"DFF_X1": 4})})
    run.process_verdicts()
    rows = {r[0]: (r[1], r[2], r[3]) for r in conn.execute("SELECT cand_id, label, in_archive, accepted FROM candidates WHERE run_id=?", (run.run_id,))}
    assert rows[better] == ("improved", 1, 1) and rows[worse] == ("no_gain", 0, 0)
    assert conn.execute("SELECT COUNT(*) FROM diagnoses WHERE cand_id IN (?, ?)", (better, worse)).fetchone()[0] == 0   # no M3 verdict at search time
    fb = run.state["feedback"][better]
    assert fb["caliber"] == "Y" and fb["diagnosis"] == "improved" and fb["evidence"]["dA_pct"] == -10.0 and "rung" not in fb
    assert run.state["cands"][better]["credit"] == 1 and run.state["cands"][worse]["credit"] == 0
    assert [m["cand_id"] for m in run.archive.members] == [better]
    run.save_state()                                                       # what step() does after every verdict
    run2 = SearchRun.resume(cfg, conn, run.run_id, queue=q, transport=tr)   # resumption keeps the scalar verdicts
    assert [m["cand_id"] for m in run2.archive.members] == [better] and run2.state["cands"][worse]["label"] == "no_gain"


def test_long_proofs_first_on_arithmetic_designs(env, monkeypatch):
    """DECISIONS 2026-09-14 item 2: on an arithmetic design the (c1) / (d) proofs are issued first within a generation and
    get one queue-priority step more; on other designs (and for other classes) nothing changes."""
    cfg, conn, q, tmp_path = env
    from src.search import driver as DR
    from src.search.driver import SearchRun
    cfg["search"]["long_proof_first"] = {"classes": ["c1", "d"], "design_patterns": ["rtllm_d"], "priority_boost": 1}
    monkeypatch.setattr(DR.M6, "classify", lambda feat, **k: {"class_rule": "d", "rules": ["stub"], "confidence": 0.8, "needs_review": False})
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=3, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    assert run.arith_design is True
    run.step()
    prios = [r[0] for r in conn.execute("SELECT j.priority FROM candidates c JOIN jobs j ON j.job_id=c.eq_job_id WHERE c.run_id=?", (run.run_id,))]
    assert prios and all(p == run.priority + 1 for p in prios)                       # produced class (d) on an arithmetic design: boosted
    cfg["search"]["long_proof_first"] = {"classes": ["c1", "d"], "design_patterns": ["pipe"], "priority_boost": 1}
    run2 = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=4, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    assert run2.arith_design is False
    run2.step()
    prios2 = [r[0] for r in conn.execute("SELECT j.priority FROM candidates c JOIN jobs j ON j.job_id=c.eq_job_id WHERE c.run_id=?", (run2.run_id,))]
    assert prios2 and all(p == run2.priority for p in prios2)                         # not an arithmetic design: no boost


def test_fitness_job_carries_the_design_include_directories(env, monkeypatch):
    """2026-09-14: the fitness job of a candidate lists the design's include directories (cktevo candidates `include D's files)."""
    cfg, conn, q, tmp_path = env
    from src.designs import catalog as K
    from src.search.driver import SearchRun
    d = K.load_design(tmp_path / "designs" / "rtllm" / "d" / "design.json") if (tmp_path / "designs" / "rtllm" / "d" / "design.json").exists() else None
    assert d is not None
    d["incdirs"] = ["rtl"]
    K.write_design(d)
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=5, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    run.step()
    cands = [r[0] for r in conn.execute("SELECT cand_id FROM candidates WHERE run_id=? AND eq_job_id IS NOT NULL", (run.run_id,))]
    for cid in cands:
        finish_eq(conn, cfg, tmp_path, cid)
    run.process_verdicts()
    for cid in cands:
        p = json.loads(conn.execute("SELECT j.payload_json FROM candidates c JOIN jobs j ON j.job_id=c.e4_job_id WHERE c.cand_id=?", (cid,)).fetchone()[0])
        assert p["incdirs"] == [str(tmp_path / "designs" / "rtllm" / "d" / "rtl")]


def test_static_complement_text_is_literature_only_and_versioned():
    """G5 decisions item 2 (i): the B1@E4 block is written from the literature's own guidance (Dr. RTL's "already done by
    synthesis" category, the RTL-OPT pattern list), never from this project's map: the body carries no map prior, no
    Experiment-1 retention rates and no rewrite-class letters of the map; the front matter (sources, version) is stripped."""
    from src.search import prompts as PR
    text, version = PR.load_static_complement()
    assert version == "1" and text.startswith("Static guidance from the RTL-optimization literature")
    assert "---" not in text and "sources:" not in text and "arXiv" not in text          # the front matter never reaches the model
    for forbidden in ("Map prior", "Experiment 1", "absorbed %", "class (a)", "class (c1)", "retention", "retained"):
        assert forbidden not in text
    assert "%" not in text                                                                   # no rates of any kind
    for part in ("A. The synthesizer already does these", "B. Directions the literature found", "C. Do not do these"):
        assert part in text
    for pattern in ("Bit-width optimization", "Precomputation and LUT conversion", "Operator strength reduction", "Control simplification", "Resource sharing", "State encoding optimization"):
        assert pattern in text                                                               # RTL-OPT §3.2, the six patterns
    assert "XOR" in text and "counter's direction" in text                                   # Dr. RTL Fig. 7: already done by synthesis / breaks equivalence


def test_driver_b1_arm_carries_the_static_complement_and_the_others_do_not(env):
    """spec 05 §2 / §5: arm B1@E4 uses E4 fitness with scalar feedback plus the static complement text in place of the
    map-prior table; arms M, B2 and B0 never see that text (M keeps the prior table). Both directions; the run row records
    the static text's version in prompt_version."""
    cfg, conn, q, tmp_path = env
    from src.search import prompts as PR
    from src.search.driver import SearchRun
    static, version = PR.load_static_complement()
    db.insert(conn, "evaluations", {"design_id": "rtllm_d", "is_baseline": 1, "config": "Y", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 80.0, "cells": 18, "wns_ns": 0.2, "tns_ns": 0.0,
                                    "power_default_mw": 0.8, "status": "ok", "raw_dir": "/x/base_y", "hist_json": json.dumps({"DFF_X1": 4, "NAND2_X1": 14})})
    b1 = SearchRun.create(cfg, conn, exp="smoke", arm="B1_E4", design_id="rtllm_d", seed=1, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    assert b1.fit_cfg == "E4" and b1.scalar and b1.floor == {} and b1.static_text == static and b1.static_version == "1"
    assert static.strip() in b1.prefix and "Map prior" not in b1.prefix and "No map prior" not in b1.prefix
    assert b1.prefix.index("Synopsys DC full-effort (E4) result") < b1.prefix.index("Static guidance")   # the block sits where M's prior table sits
    assert conn.execute("SELECT prompt_version FROM runs WHERE run_id=?", (b1.run_id,)).fetchone()[0].endswith(f"+sc{version}")
    for seed, arm in enumerate(("M", "B2", "B0"), start=2):   # distinct seeds: run ids are stamped to the second
        run = SearchRun.create(cfg, conn, exp="smoke", arm=arm, design_id="rtllm_d", seed=seed, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
        assert run.static_text is None and "Static guidance" not in run.prefix
        assert "+sc" not in conn.execute("SELECT prompt_version FROM runs WHERE run_id=?", (run.run_id,)).fetchone()[0]
    assert "No map prior" in SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=5, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport()).prefix
    assert b1.step() == "running"                                              # the B1 prompt is accepted by the driver end to end
    assert conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND eq_job_id IS NOT NULL", (b1.run_id,)).fetchone()[0] >= 1


@pytest.mark.parametrize("population", [False, True])
def test_latency_mapped_c2_candidates_are_map_objects_but_not_population_members(env, population):
    """spec 03 §2 / config equiv.c2_population: a candidate proven through the SEQ latency mapping (constant output offsets,
    class c2) is evaluated at E4 and diagnosed like any proven candidate, but with c2_population false it never enters the
    archive, is never accepted and earns no bandit credit; with the switch on it is treated as any retained candidate."""
    cfg, conn, q, tmp_path = env
    cfg["equiv"]["c2_population"] = population
    from src.search.driver import SearchRun
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=3 + int(population), model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    assert run.step() == "running"
    cid = conn.execute("SELECT cand_id FROM candidates WHERE run_id=? AND eq_job_id IS NOT NULL ORDER BY cand_id", (run.run_id,)).fetchone()[0]
    finish_eq(conn, cfg, tmp_path, cid, verdict="proven", extra_rec={"v2_status": "offset", "latency_offset_json": '{"q": 1}', "latency_mapped": True, "proven_by": "seq"})
    run.process_verdicts()
    c = run.state["cands"][cid]
    assert c["class_final"] == "c2" and c["latency_mapped"] is True and run.state["pending"][cid] == "e4"   # evaluated at E4 like any proven candidate
    assert conn.execute("SELECT class_final, verdict FROM candidates WHERE cand_id=?", (cid,)).fetchone()[:] == ("c2", "proven")
    finish_e4(conn, cid, 90.0)                                                                             # 10 % smaller: retained by the diagnosis
    run.process_verdicts()
    d = dict(conn.execute("SELECT * FROM diagnoses WHERE cand_id=?", (cid,)).fetchone())
    row = conn.execute("SELECT label, in_archive, accepted FROM candidates WHERE cand_id=?", (cid,)).fetchone()[:]
    assert d["label"] == "retained"                                                                        # the map sees a retained (c2) object either way
    if population:
        assert row == ("retained", 1, 1) and d["credit"] == 1 and [m["cand_id"] for m in run.archive.members] == [cid]
    else:
        assert row == ("retained", 0, 0) and d["credit"] == 0 and run.archive.members == [] and run.state["retained"] == 0


RTL_D2 = ("module d2(input clk, input rst_n, input [3:0] x, output reg [3:0] y, output reg [3:0] z);\n"
          "  always @(posedge clk or negedge rst_n) if (!rst_n) y <= 0; else y <= x + 4'd1;\n"
          "  always @(posedge clk or negedge rst_n) if (!rst_n) z <= 0; else z <= x - 4'd1;\n"
          "endmodule\n")


class ListTransport:
    """Answers the given texts in order (each a rewrite's RTL); further calls repeat the last one with a new tag."""
    def __init__(self, rtls):
        self.rtls, self.calls = list(rtls), 0

    def create(self, **kw):
        self.calls += 1
        rtl = self.rtls[min(self.calls, len(self.rtls)) - 1]
        text = json.dumps(rtl) if isinstance(rtl, dict) else json.dumps({"rtl": rtl, "note": f"answer {self.calls}"})   # a dict is answered verbatim (e.g. a skill-learning answer)

        class R:
            pass
        r = R()
        r.output_text, r.id, r.status, r.service_tier = text, f"resp{self.calls}", "completed", "flex"
        r.usage = SimpleNamespace(input_tokens=100, output_tokens=50, input_tokens_details=SimpleNamespace(cached_tokens=0, cache_write_tokens=0), output_tokens_details=None)
        return r


def _add_design_d2(env):
    cfg, conn, q, tmp_path = env
    from src.designs import catalog as K
    ddir = tmp_path / "designs" / "rtllm" / "d2"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "d2.v").write_text(RTL_D2)
    d = {"design_id": "rtllm_d2", "suite": "rtllm", "name": "d2", "top": "d2", "files": ["rtl/d2.v"], "clk_ports": ["clk"], "rst_port": "rst_n", "rst_sense": "low",
         "sverilog": False, "incdirs": [], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/d2.v": K.sha256_of(ddir / "rtl" / "d2.v")}, "loc": 4, "tags": ["rtllm"], "notes": [], "_dir": str(ddir)}
    K.write_design(d)
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('rtllm_d2','rtllm','d2','x',4,1,'dev',1.0,'t','g','c')")
    crit = {"critical": {"endpoint": "y_reg[3]", "startpoint": "x[0]"}, "endpoints": [["x[0]", "y_reg[3]", 0.1], ["x[1]", "y_reg[2]", 0.2]]}
    db.insert(conn, "evaluations", {"design_id": "rtllm_d2", "is_baseline": 1, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 100.0, "cells": 20, "wns_ns": 0.1, "tns_ns": 0.0,
                                    "power_saif_mw": 1.0, "status": "ok", "raw_dir": "/x/base2", "hist_json": json.dumps({"DFF_X1": 8, "NAND2_X1": 12}), "crit_path_json": json.dumps(crit)})
    from src.noise import stats as S
    S.upsert_floor(conn, [{"design_id": "rtllm_d2", "config": "E4", "metric": m, "sigma_robust": 0.0, "sigma_std": 0.0, "q95_abs": 0.0, "max_abs": 0.0, "n": 4, "abs_unit_value": None,
                           "t_d": t, "floor_class": "quiet", "floor_source": "measured", "pooled_min": t} for m, t in (("area", 0.003), ("wns", 0.001), ("power_saif", 0.014))])


def test_scope_limited_rewriting_names_the_region_and_restores_changes_outside_it(env):
    """G5 item 1 (i) as amended on the evening of 2026-09-15 (item 2): the suffix names the always block holding the critical
    endpoint register (y); an answer that changes the other block (z) is spliced — the z block restored from D, the y rewrite
    kept — issued into the pipeline and flagged (`scope_json.violations`, `state.scope_violations`), never discarded; an
    answer that changes only the y block is issued normally without a flag."""
    cfg, conn, q, tmp_path = env
    _add_design_d2(env)
    from src.search.driver import SearchRun
    bad = RTL_D2.replace("z <= x - 4'd1", "z <= x + 4'd3")                     # touches only the z block: outside the scope -> restored, D again
    mixed = RTL_D2.replace("y <= x + 4'd1", "y <= x + 4'd2").replace("z <= x - 4'd1", "z <= x + 4'd3")   # y rewritten, z touched -> z restored, issued with the flag
    good = RTL_D2.replace("y <= x + 4'd1", "y <= {x[3:1], ~x[0]}")            # touches only the y block
    tr = ListTransport([bad, mixed, good])
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d2", seed=1, model="gpt-5.6-luna", K=1, N=3, queue=q, transport=tr)
    assert run.scope_on and run.repair_max == 1
    region, text = run.region_for(None)
    assert region["kind"] == "blocks" and region["registers"] == ["y"] and region["module"] == "d2" and "rewrite only the always block at line 2" in text
    assert run.step() == "running" and run.state["calls"] == 3
    rows = {r["cand_id"]: dict(r) for r in conn.execute("SELECT * FROM candidates WHERE run_id=?", (run.run_id,))}
    from src.analysis.repair import scope_flagged
    viol = sorted([r for r in rows.values() if scope_flagged(r["scope_json"])], key=lambda r: r["label"] or "")
    ok = [r for r in rows.values() if not scope_flagged(r["scope_json"])]
    assert len(viol) == 2 and len(ok) == 1 and ok[0]["eq_job_id"] and ok[0]["label"] is None
    issued, identical = viol[0], viol[1]
    assert issued["eq_job_id"] and issued["label"] is None                                              # the mixed answer runs the pipeline on the spliced text
    assert identical["label"] == "absorbed_identical" and identical["eq_job_id"] is None                # the z-only answer is D after the restoration: no evaluation, flag kept
    assert conn.execute("SELECT COUNT(*) FROM diagnoses WHERE label='scope_violation'").fetchone()[0] == 0
    sj = json.loads(issued["scope_json"])
    assert sj["violations"][0]["kind"] == "always" and sj["violations"][0]["line"] == 3 and sj["region"]["registers"] == ["y"]
    assert sj["spliced"]["restored_items"][0]["targets"] == ["z"]
    stored = Path(issued["rtl_path"]).read_text()
    assert "z <= x - 4'd1" in stored and "z <= x + 4'd3" not in stored and "y <= x + 4'd2" in stored   # D's z block restored, the y rewrite kept
    assert json.loads(ok[0]["scope_json"])["region"]["kind"] == "blocks" and run.state["scope_violations"] == 2
    assert run.state["cands"][issued["cand_id"]]["scope_flag"] and not run.state["cands"][ok[0]["cand_id"]]["scope_flag"]
    assert conn.execute("SELECT SUM" + "(" + SC.SCOPE_FLAG_SQL + ") FROM candidates WHERE run_id=?", (run.run_id,)).fetchone()[0] == 2
    req = json.loads(Path(sorted((tmp_path / "results" / "llm" / run.run_id).glob("c*.json"))[0]).read_text())
    assert "Scope of this rewrite" in req["request"]["input"] and "textually unchanged" in req["request"]["input"]
    # switched off: the same answers are all issued and no scope text is sent
    cfg["exp5"]["correctness_aids"]["scope_limited_rewriting"] = False
    run2 = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d2", seed=2, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=ListTransport([bad, good]))
    assert run2.region_for(None) == (None, None) and run2.step() == "running"
    assert conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND eq_job_id IS NOT NULL", (run2.run_id,)).fetchone()[0] == 2   # no scope: the z edit is a candidate of its own
    req2 = json.loads(Path(sorted((tmp_path / "results" / "llm" / run2.run_id).glob("c*.json"))[0]).read_text())
    assert "Scope of this rewrite" not in req2["request"]["input"]


def test_repair_call_after_a_lockstep_mismatch_is_budgeted_and_never_repeated(env):
    """G5 item 1 (ii): a sim_fail verdict triggers one repair call carrying the mismatch (cycle, signals) and the failed RTL;
    the answer is a new candidate (repair_of = the failed one, same parent and class) that enters the pipeline; the call is
    charged to the equal-call budget (generation 2 gets one call fewer); the repair's own failure is not repaired again; an
    inconclusive verdict gets no repair; with the budget exhausted the repair is skipped and counted."""
    cfg, conn, q, tmp_path = env
    from src.analysis.repair import repair_table, repair_yield
    from src.search.driver import SearchRun
    tr = ListTransport([rewrite("a1"), rewrite("a2"), rewrite("fix1"), rewrite("g2")])
    run = SearchRun.create(cfg, conn, exp="smoke", arm="B2", design_id="rtllm_d", seed=1, model="gpt-5.6-luna", K=2, N=2, queue=q, transport=tr)
    assert run.step() == "running" and run.state["calls"] == 2
    c1, c2 = [r[0] for r in conn.execute("SELECT cand_id FROM candidates WHERE run_id=? ORDER BY cand_id", (run.run_id,))]
    mism = {"y": {"c": "0101", "d": "0110", "first_cycle": 17}}
    finish_eq(conn, cfg, tmp_path, c1, verdict="sim_fail", extra_rec={"v2_status": "sim_fail", "v3_status": None, "v2": {"first_mismatch": 17, "mismatches": mism}, "v2_detail": json.dumps(mism)})
    finish_eq(conn, cfg, tmp_path, c2, verdict="inconclusive", extra_rec={"v3_status": "inconclusive"})
    run.step()
    assert run.state["calls"] == 3                                                # exactly one repair call (the inconclusive one gets none)
    rep = run.state["repairs"]
    assert len(rep) == 1 and rep[0]["of"] == c1 and rep[0]["failure"] == "sim_fail" and rep[0]["cand_id"]
    fix = dict(conn.execute("SELECT * FROM candidates WHERE cand_id=?", (rep[0]["cand_id"],)).fetchone())
    assert fix["repair_of"] == c1 and fix["parent_id"] is None and fix["class_requested"] == dict(conn.execute("SELECT class_requested FROM candidates WHERE cand_id=?", (c1,)).fetchone())["class_requested"]
    assert fix["eq_job_id"] and run.state["cands"][c1]["repaired_by"] == fix["cand_id"] and run.state["cands"][fix["cand_id"]]["repair_of"] == c1
    req = json.loads(Path(sorted((tmp_path / "results" / "llm" / run.run_id).glob("c*.json"))[2]).read_text())
    failed_rtl = Path(dict(conn.execute("SELECT rtl_path FROM candidates WHERE cand_id=?", (c1,)).fetchone())["rtl_path"]).read_text().strip()
    inp = req["request"]["input"]
    assert "cycle 17" in inp and "output y: original 0110, rewrite 0101" in inp and failed_rtl in inp and req["tag"].endswith(f"repair:{c1}:sim_fail")
    assert conn.execute("SELECT llm_calls FROM runs WHERE run_id=?", (run.run_id,)).fetchone()[0] == 3
    # the repair fails too: no second repair; generation 2 has one call left (budget 4 - 3)
    finish_eq(conn, cfg, tmp_path, fix["cand_id"], verdict="falsified", extra_rec={"v3_status": "falsified", "v3": {"properties": {"_map_output_y": "falsified"}, "cex_depths": {"_map_output_y": 2}}})
    run.step()
    assert len(run.state["repairs"]) == 1 and run.state["calls"] == 4 and run.state["gen"] == 2
    gen2 = [c for c in run.state["cands"].values() if c["gen"] == 2 and not c.get("repair_of")]
    assert len(gen2) == 1
    # budget exhausted: a further failure is not repaired but counted
    finish_eq(conn, cfg, tmp_path, gen2[0]["cand_id"], verdict="rejected", extra_rec={"v1_status": "rejected", "v1_detail": "yosys: syntax error", "v2_status": None, "v3_status": None})
    run.step()
    assert run.state["calls"] == 4 and run.state.get("repairs_skipped_budget") == 1 and len(run.state["repairs"]) == 1
    y = repair_yield(conn, exp="smoke", run_ids=[run.run_id])
    assert y["by_failure"]["sim_fail"]["attempted"] == 1 and y["by_failure"]["sim_fail"]["proven"] == 0 and y["calls_repair"] == 1
    assert y["unrepaired"] == {"falsified": 1, "rejected": 1}                     # the repair's own failure and the budget-blocked one
    assert any(row.startswith("| sim_fail | 1 | 0 |") for row in repair_table(y))
    # switched off: no repair at all
    cfg["exp5"]["correctness_aids"]["repair_attempts"] = 0
    run3 = SearchRun.create(cfg, conn, exp="smoke", arm="B2", design_id="rtllm_d", seed=3, model="gpt-5.6-luna", K=1, N=1, queue=q, transport=ListTransport([rewrite("b1")]))
    run3.step()
    cid3 = conn.execute("SELECT cand_id FROM candidates WHERE run_id=?", (run3.run_id,)).fetchone()[0]
    finish_eq(conn, cfg, tmp_path, cid3, verdict="sim_fail", extra_rec={"v2_status": "sim_fail", "v3_status": None, "v2": {"first_mismatch": 1, "mismatches": mism}})
    run3.step()
    assert run3.state["calls"] == 1 and not run3.state.get("repairs")


def test_repaired_candidate_that_is_proven_and_retained_counts_in_the_yield(env):
    cfg, conn, q, tmp_path = env
    from src.analysis.repair import repair_yield
    from src.search.driver import SearchRun
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=7, model="gpt-5.6-luna", K=2, N=1, queue=q, transport=ListTransport([rewrite("z1"), rewrite("z2")]))   # budget 2: one call for the candidate, one for its repair
    run.step()
    c1 = conn.execute("SELECT cand_id FROM candidates WHERE run_id=?", (run.run_id,)).fetchone()[0]
    finish_eq(conn, cfg, tmp_path, c1, verdict="rejected", extra_rec={"v1_status": "rejected", "v1_detail": "x.v:3: ERROR: syntax error", "v2_status": None, "v3_status": None})
    run.step()
    fix = run.state["repairs"][0]["cand_id"]
    finish_eq(conn, cfg, tmp_path, fix, verdict="proven")
    run.step()
    finish_e4(conn, fix, 90.0)
    assert run.step() == "done"
    y = repair_yield(conn, exp="smoke", run_ids=[run.run_id])
    assert y["by_failure"]["rejected"] == {"attempted": 1, "proven": 1, "accepted": 1, "retained": 1, "scope_violation": 0}
    assert conn.execute("SELECT label, accepted, repair_of FROM candidates WHERE cand_id=?", (fix,)).fetchone()[:] == ("retained", 1, c1)


def test_driver_slims_finished_candidates_unless_accepted(env, monkeypatch):
    """Tiered retention in the run (G5 item 5 (ii)): after the final label a non-accepted candidate loses its regenerable
    artifacts (equivalence VCD / trace / ports, E4 netlist and ddc) while its records stay; an accepted (archived) candidate
    keeps everything; the classifier workdir goes for every candidate right after classification."""
    cfg, conn, q, tmp_path = env
    cfg["retention"].update(tiered=True, tiered_audit_frac=0.0)
    from src.search.driver import SearchRun
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=9, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=ListTransport([rewrite("k1"), rewrite("k2")]))
    run.step()
    cands = [r[0] for r in conn.execute("SELECT cand_id FROM candidates WHERE run_id=? ORDER BY cand_id", (run.run_id,))]
    for cid in cands:
        (run.dir / f"m6_{cid}" / "c").mkdir(parents=True, exist_ok=True)   # would have been created by Yosys; removed after classification in production
    good, bad = cands
    finish_eq(conn, cfg, tmp_path, good, verdict="proven")
    finish_eq(conn, cfg, tmp_path, bad, verdict="proven")
    for cid in cands:
        eq_dir = Path(conn.execute("SELECT payload_json FROM jobs WHERE job_id=(SELECT eq_job_id FROM candidates WHERE cand_id=?)", (cid,)).fetchone()[0] and run.eq_record(cid)[1])
        (eq_dir / "v2_sim").mkdir(exist_ok=True)
        (eq_dir / "v2_sim" / "trace.txt").write_text("t" * 100)
        (eq_dir / "v2_sim" / "sim.vcd.gz").write_text("v" * 100)
    run.process_verdicts()
    for cid, area in ((good, 90.0), (bad, 100.0)):
        raw = tmp_path / "results" / "raw" / "rtllm_d" / "E4" / f"fake_{cid}"
        (raw / "outputs" / "reports").mkdir(parents=True)
        (raw / "outputs" / "reports" / "netlist.v").write_text("n" * 100)
        (raw / "outputs" / "reports" / "qor.rpt").write_text("q")
        (raw / "meta.json").write_text(json.dumps({"status": "ok", "cand_id": cid}))
        jid = conn.execute("SELECT e4_job_id FROM candidates WHERE cand_id=?", (cid,)).fetchone()[0]
        conn.execute("UPDATE jobs SET state='done' WHERE job_id=?", (jid,))
        db.insert(conn, "evaluations", {"design_id": "rtllm_d", "cand_id": cid, "is_baseline": 0, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": area, "cells": 20,
                                        "wns_ns": 0.1, "tns_ns": 0.0, "power_saif_mw": 1.0, "dc_seconds": 60.0, "status": "ok", "raw_dir": str(raw), "hist_json": json.dumps({"DFF_X1": 4, "NAND2_X1": 16})})
    run.process_verdicts()
    labels = {r[0]: (r[1], r[2]) for r in conn.execute("SELECT cand_id, label, in_archive FROM candidates WHERE run_id=?", (run.run_id,))}
    assert labels[good] == ("retained", 1) and labels[bad][1] == 0
    g_eq, b_eq = Path(run.eq_record(good)[1]), Path(run.eq_record(bad)[1])
    assert not (g_eq / "v2_sim" / "trace.txt").exists() and not (g_eq / "v2_sim" / "sim.vcd.gz").exists() and (g_eq / "equiv.json").exists()   # accepted: the record and its evidence stay, the regenerable lock-step files go too (storage decision 2026-09-15 (C))
    assert not (b_eq / "v2_sim" / "trace.txt").exists() and not (b_eq / "v2_sim" / "sim.vcd.gz").exists() and (b_eq / "equiv.json").exists()   # slimmed, record kept
    g_raw, b_raw = tmp_path / "results/raw/rtllm_d/E4" / f"fake_{good}", tmp_path / "results/raw/rtllm_d/E4" / f"fake_{bad}"
    assert (g_raw / "outputs/reports/netlist.v").exists() and not (b_raw / "outputs/reports/netlist.v").exists() and (b_raw / "outputs/reports/qor.rpt").exists() and (b_raw / "meta.json").exists()
    assert json.loads((b_raw / "meta.json").read_text())["slimmed"]["categories"] == ["netlist"]
    assert run.state["cands"][good]["slimmed"]["kept_full"] is True and run.state["cands"][bad]["slimmed"]["kept_full"] is False
    assert not (run.dir / f"m6_{bad}").exists()
    run.save_state()
    run2 = SearchRun.resume(cfg, conn, run.run_id, queue=q, transport=ListTransport([]))
    run2.slim_finished()                                                                                                    # idempotent across resumption
    assert (g_eq / "equiv.json").exists() and run2.state["cands"][good]["slimmed"]["kept_full"] is True


def test_map_prior_loads_for_arm_m_only_and_feeds_prescreen_prompt_and_bandit(env, tmp_path):
    """spec 05 §1 / §3 (Phase 4 output, `search.map_prior_file`): arm M loads the absorbed / retained tables — the prompt shows
    the prior table, the prescreen sees the absorbed probabilities, the bandit starts from the retained rates as
    pseudo-counts; the baseline arms and a missing file give no prior (both directions)."""
    cfg, conn, q, tmp_path2 = env
    from src.search.driver import SearchRun
    prior_file = tmp_path / "map_prior.json"
    prior_file.write_text(json.dumps({"basis": "test", "absorbed": {"a": 0.94, "b": 0.51, "c1": 0.0, "d": 0.06}, "retained": {"a": 0.06, "b": 0.49, "c1": 1.0, "d": 0.94}, "n": {"a": 33}}))
    cfg["search"]["map_prior_file"] = str(prior_file)
    m = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=11, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    assert m.prior == {"a": 0.94, "b": 0.51, "c1": 0.0, "d": 0.06} and m.prior_retained["c1"] == 1.0 and m.map_prior_meta["basis"] == "test"
    assert "Map prior (fraction of rewrites of each class absorbed by the synthesizer, from Experiment 1):" in m.prefix and "- class a: absorbed 94 %" in m.prefix
    assert m.bandit.prior == {"a": 0.06, "b": 0.49, "c1": 1.0, "d": 0.94, "free": 0.0} and m.bandit.probs()["c1"] > m.bandit.probs()["a"]
    m.save_state()
    m2 = SearchRun.resume(cfg, conn, m.run_id, queue=q, transport=FakeTransport())
    assert m2.bandit.prior == m.bandit.prior and m2.prior == m.prior                                     # persisted with the state
    db.insert(conn, "evaluations", {"design_id": "rtllm_d", "is_baseline": 1, "config": "Y", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 80.0, "cells": 18, "wns_ns": 0.2, "tns_ns": 0.0,
                                    "power_default_mw": 0.8, "status": "ok", "raw_dir": "/x/base_y", "hist_json": json.dumps({"DFF_X1": 4, "NAND2_X1": 14})})
    for seed, arm in ((12, "B0"), (13, "B1_E4"), (14, "B2")):
        b = SearchRun.create(cfg, conn, exp="smoke", arm=arm, design_id="rtllm_d", seed=seed, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
        assert b.prior is None and b.prior_retained is None and all(v == 0.0 for v in b.bandit.prior.values()) and "Map prior" not in b.prefix
    cfg["search"]["map_prior_file"] = str(tmp_path / "missing.json")
    m3 = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=15, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    assert m3.prior is None and "No map prior" in m3.prefix
    cfg["search"]["map_prior_file"] = str(prior_file)
    cfg["search"]["bandit"]["init_from_map_prior"] = False
    m4 = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=16, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    assert m4.prior is None and all(v == 0.0 for v in m4.bandit.prior.values())                           # the switch turns the prior off


def test_phase4_map_prior_file_matches_the_map_and_the_probe_script_lists_its_runs(env):
    """The committed prior file is derived from the B0 map at E4 (absorbed = 1 - retention); the probe script refuses a
    model without prices and creates the 12 runs of the probe configuration otherwise (not submitted)."""
    cfg, conn, q, tmp_path = env
    import scripts.phase5_probe as PB
    prior = json.loads((Path(C.ROOT) / "reports" / "data" / "map_prior_phase4.json").read_text())
    data = json.loads((Path(C.ROOT) / "reports" / "data" / "phase4_exp1.json").read_text())
    for cls, v in prior["retained"].items():
        assert abs(v - data["map_b0"][cls]["E4"]["retention_rate"]) < 1e-3 and abs(prior["absorbed"][cls] + v - 1.0) < 1e-6
    cfg["exp5"]["correctness_probe"] = dict(cfg["exp5"]["correctness_probe"], designs=["rtllm_d"], seeds=1, K=1, N=1, models=["gpt-5.6-terra", "gpt-5.6-sol"])
    cfg["search"]["map_prior_file"] = None
    PB.cmd_create(cfg, conn, do_submit=False)
    rows = [dict(r) for r in conn.execute("SELECT * FROM runs WHERE exp='phase5_probe'")]
    assert sorted(r["llm_model"] for r in rows) == ["gpt-5.6-sol", "gpt-5.6-terra"] and all(r["arm"] == "M" and r["status"] == "created" for r in rows)
    assert conn.execute("SELECT COUNT(*) FROM jobs WHERE kind='search'").fetchone()[0] == 0                # not submitted
    PB.cmd_create(cfg, conn, do_submit=False)
    assert conn.execute("SELECT COUNT(*) FROM runs WHERE exp='phase5_probe'").fetchone()[0] == 2           # idempotent
    cfg["llm"]["prices_usd_per_1m"]["flex"].pop("gpt-5.6-sol")
    with pytest.raises(SystemExit):
        PB.cmd_create(cfg, conn, do_submit=False)


DC_WORDS = ("Synopsys", "Design Compiler", "compile_ultra", "-retime", "-gate_clock", "DesignWare", "E4", "synthesizer already did", "map prior", "Map prior", "Static guidance")


def test_b0_prefix_has_no_dc_derived_line_and_a_tool_neutral_objective(env):
    """Decision 2026-09-15 item 3 (i): arm B0 is the literature caliber — its prefix carries the Y-caliber summary of D and a
    tool-neutral objective sentence, never the DC E4 summary, the compile_ultra wording, the DC log line, the DesignWare
    line, the map prior or the static block (both directions: the same design's M prefix carries the E4 lines)."""
    cfg, conn, q, tmp_path = env
    from src.search.driver import SearchRun
    db.insert(conn, "evaluations", {"design_id": "rtllm_d", "is_baseline": 1, "config": "Y", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 80.0, "cells": 18, "wns_ns": 0.2, "tns_ns": 0.0,
                                    "power_default_mw": 0.8, "status": "ok", "raw_dir": "/x/base_y", "hist_json": json.dumps({"DFF_X1": 4, "NAND2_X1": 14}),
                                    "log_summary_json": json.dumps({"datapath_blocks": None, "icg_count": None, "log": None, "registers": 4}), "resources_json": "{}",
                                    "crit_path_json": json.dumps({"critical": {"endpoint": "y_reg[0]", "startpoint": "x[0]"}, "endpoints": None})})
    conn.execute("UPDATE evaluations SET log_summary_json=?, resources_json=? WHERE design_id='rtllm_d' AND config='E4' AND is_baseline=1",
                 (json.dumps({"datapath_blocks": 1, "icg_count": 2, "registers": 4, "log": {"counts": {"clock_gating": 3, "retime": 1, "warning": 1}, "samples": {"clock_gating": ["Information: Performing clock-gating on design d. (PWR-730)"], "warning": ["Warning:  /home/hping/Beyond-Synth/results/raw/rtllm_d/E4/abc/inputs/rtl/d.v:2: DEFAULT branch of CASE statement cannot be reached. (ELAB-311)"]}}}),
                  json.dumps({"dw_modules": ["DW01_add"]})))
    b0 = SearchRun.create(cfg, conn, exp="smoke", arm="B0", design_id="rtllm_d", seed=21, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    for w in DC_WORDS:
        assert w not in b0.prefix, w
    assert "so that logic synthesis produces a smaller, faster or lower-power netlist" in b0.prefix and "Yosys + OpenSTA (Y) result" in b0.prefix and "cell mix" in b0.prefix
    assert "/home/" not in b0.prefix and "No map prior" not in b0.prefix
    m = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=22, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    assert "Synopsys DC full-effort (E4) result" in m.prefix and "compile_ultra -retime -gate_clock" in m.prefix and "DesignWare components inferred: DW01_add" in m.prefix
    b2 = SearchRun.create(cfg, conn, exp="smoke", arm="B2", design_id="rtllm_d", seed=23, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
    assert "Synopsys DC full-effort (E4) result" in b2.prefix and "No map prior" not in b2.prefix and "Static guidance" not in b2.prefix


def test_e4_summary_log_line_has_counts_and_message_types_but_no_raw_messages(env):
    """Decision 2026-09-15 item 3 (ii): the E4 summary's synthesizer line carries the log counts and the normalised message
    types (identifier x count), never the raw DC messages or a file path; identical for every arm that receives the E4
    summary (M, B1@E4, B2)."""
    cfg, conn, q, tmp_path = env
    from src.search import prompts as PR
    from src.search.driver import SearchRun
    ls = {"datapath_blocks": 0, "icg_count": 4, "registers": 79.0, "shared_resources": None,
          "log": {"counts": {"clock_gating": 8, "datapath": 0, "error": 0, "retime": 1, "sharing": 0, "ungroup": 6, "warning": 1},
                  "samples": {"clock_gating": ["Information: Performing clock-gating with positive edge logic: 'integrated' and negative edge logic: 'or'. (PWR-1047)", "Information: Skipping clock gating on design encoder, since there are no registers. (PWR-806)"],
                              "retime": ["Information: Retiming is enabled. SVF file must be used for formal verification. (OPT-1210)"],
                              "ungroup": ["Information: Ungrouping hierarchy SCR before Pass 1 (OPT-776)", "Information: Ungrouping 4 of 11 hierarchies before Pass 1 (OPT-775)"],
                              "warning": ["Warning:  /home/hping/Beyond-Synth/results/raw/drrtl_pcie/E4/e1d8/inputs/rtl/pcie.v:854: DEFAULT branch of CASE statement cannot be reached. (ELAB-311)"]}}}
    line = PR.synth_log_line(ls)
    assert line.startswith("- what the synthesizer already did: clock_gating 8, retime 1, ungroup 6, warning 1; message types ELAB-311 x1, OPT-1210 x1, OPT-775 x1, OPT-776 x1, PWR-1047 x1, PWR-806 x1")
    assert line.endswith("; integrated clock-gating cells 4, datapath blocks 0, registers 79")
    assert "/home/" not in line and "pcie.v" not in line and "Skipping" not in line and "Information" not in line
    assert PR.synth_log_line({"datapath_blocks": None, "icg_count": None, "log": None, "registers": None}) is None   # a Yosys row: nothing to say
    assert PR.synth_log_line({"registers": 3}) == "- what the synthesizer already did: no log categories; registers 3"
    conn.execute("UPDATE evaluations SET log_summary_json=? WHERE design_id='rtllm_d' AND config='E4' AND is_baseline=1", (json.dumps(ls),))
    prefixes = {}
    for seed, arm in ((31, "M"), (32, "B1_E4"), (33, "B2")):
        run = SearchRun.create(cfg, conn, exp="smoke", arm=arm, design_id="rtllm_d", seed=seed, model="gpt-5.6-luna", K=1, N=2, queue=q, transport=FakeTransport())
        prefixes[arm] = run.prefix
        assert line in run.prefix and "/home/" not in run.prefix and "Skipping" not in run.prefix, arm
    def e4_block(p):   # the summary block without the noise-floor line (arm M carries a floor, the scalar arms do not)
        blk = p[p.index("Synopsys DC full-effort"):p.index("\n\n", p.index("Synopsys DC full-effort"))]
        return "\n".join(l for l in blk.splitlines() if not l.startswith("- noise floor"))
    assert e4_block(prefixes["M"]) == e4_block(prefixes["B1_E4"]) == e4_block(prefixes["B2"])


def test_disk_guard_pauses_submissions_and_resumes(env, monkeypatch):
    """Decision 2026-09-15 item 1: below `retention.min_free_gb` the run submits nothing (no LLM call, no job), its status is
    paused_disk and the state records it; when space returns the run resumes and continues (both directions)."""
    cfg, conn, q, tmp_path = env
    from src.eval import retention as R
    from src.search.driver import SearchRun
    cfg["retention"]["min_free_gb"] = 15
    free = {"gb": 10.0}
    monkeypatch.setattr(R, "free_gb", lambda path=None: free["gb"])
    tr = FakeTransport()
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d", seed=41, model="gpt-5.6-luna", K=2, N=2, queue=q, transport=tr)
    assert run.step() == "paused_disk" and run.state["calls"] == 0 and tr.calls == 0
    assert run.state["paused_disk"]["free_gb"] == 10.0 and run.state["paused_disk"]["threshold_gb"] == 15.0
    assert conn.execute("SELECT status FROM runs WHERE run_id=?", (run.run_id,)).fetchone()[0] == "paused_disk"
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0 and conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run.run_id,)).fetchone()[0] == 0
    assert run.step() == "paused_disk" and tr.calls == 0                                   # still paused, still nothing submitted
    free["gb"] = 40.0
    assert run.step() == "running" and run.state["paused_disk"] is None and tr.calls == 2   # space returned: the generation is built
    assert conn.execute("SELECT status FROM runs WHERE run_id=?", (run.run_id,)).fetchone()[0] == "running"
    assert conn.execute("SELECT COUNT(*) FROM jobs WHERE state='queued'").fetchone()[0] >= 1
    ok, f, thr = R.disk_ok(cfg)
    assert ok and f == 40.0 and thr == 15.0
    cfg["retention"]["min_free_gb"] = 0
    assert R.disk_ok(cfg)[0] is True                                                        # threshold 0: the guard never holds


def test_module_scope_answers_with_only_the_region_module_are_spliced_and_issued(env):
    """Operator decision 2026-09-15: on a multi-module design the model may return only the region module; the driver
    splices D's other modules in, the top-module check passes, the candidate is issued with the spliced modules recorded;
    an answer without the region module stays unusable; a returned other module that differs is still a violation."""
    cfg, conn, q, tmp_path = env
    from src.designs import catalog as K
    from src.search.driver import SearchRun
    two = ("module sub(input clk, input [3:0] a, output reg [3:0] s);\n  always @(posedge clk) s <= a + 4'd1;\nendmodule\n\n"
           "module d3(input clk, input rst_n, input [3:0] x, output [3:0] y);\n  wire [3:0] s;\n  sub u0(.clk(clk), .a(x), .s(s));\n  assign y = s;\nendmodule\n")
    ddir = tmp_path / "designs" / "rtllm" / "d3"
    (ddir / "rtl").mkdir(parents=True)
    (ddir / "rtl" / "d3.v").write_text(two)
    d = {"design_id": "rtllm_d3", "suite": "rtllm", "name": "d3", "top": "d3", "files": ["rtl/d3.v"], "clk_ports": ["clk"], "rst_port": "rst_n", "rst_sense": "low",
         "sverilog": False, "incdirs": [], "tb": None, "reference": None, "source": {"url": "u", "commit": "c", "license": "l", "paths": []},
         "sha256": {"rtl/d3.v": K.sha256_of(ddir / "rtl" / "d3.v")}, "loc": 9, "tags": ["rtllm"], "notes": [], "_dir": str(ddir)}
    K.write_design(d)
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, created_at, git_sha, cfg_hash) VALUES ('rtllm_d3','rtllm','d3','x',9,1,'dev',1.0,'t','g','c')")
    crit = {"critical": {"endpoint": "u0/s_reg[0]", "startpoint": "x[0]"}, "endpoints": [["x[0]", "u0/s_reg[0]", 0.1]]}
    db.insert(conn, "evaluations", {"design_id": "rtllm_d3", "is_baseline": 1, "config": "E4", "lib": "nangate45", "clock_ns": 1.0, "area_um2": 100.0, "cells": 20, "wns_ns": 0.1, "tns_ns": 0.0,
                                    "power_saif_mw": 1.0, "status": "ok", "raw_dir": "/x/base3", "hist_json": json.dumps({"DFF_X1": 4}), "crit_path_json": json.dumps(crit)})
    from src.noise import stats as S
    S.upsert_floor(conn, [{"design_id": "rtllm_d3", "config": "E4", "metric": m, "sigma_robust": 0.0, "sigma_std": 0.0, "q95_abs": 0.0, "max_abs": 0.0, "n": 4, "abs_unit_value": None,
                           "t_d": t, "floor_class": "quiet", "floor_source": "measured", "pooled_min": t} for m, t in (("area", 0.003), ("wns", 0.001), ("power_saif", 0.014))])
    region_only = "module sub(input clk, input [3:0] a, output reg [3:0] s);\n  always @(posedge clk) s <= {a[3:1], ~a[0]};\nendmodule\n"
    top_only = "module d3(input clk, input rst_n, input [3:0] x, output [3:0] y);\n  assign y = x;\nendmodule\n"
    changed_other = region_only + "\nmodule d3(input clk, input rst_n, input [3:0] x, output [3:0] y);\n  wire [3:0] s;\n  sub u0(.clk(clk), .a(x), .s(s));\n  assign y = ~s;\nendmodule\n"
    run = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d3", seed=1, model="gpt-5.6-luna", K=1, N=3, queue=q, transport=ListTransport([region_only, top_only, changed_other]))
    region, text = run.region_for(None)
    assert region["kind"] == "module" and region["module"] == "sub" and "you may return only this module" in text
    assert run.step() == "running"
    rows = {r["cand_id"]: dict(r) for r in conn.execute("SELECT * FROM candidates WHERE run_id=?", (run.run_id,))}
    from src.analysis.repair import scope_flagged
    issued = [r for r in rows.values() if r["eq_job_id"]]
    dups = [r for r in rows.values() if r["label"] == "duplicate"]
    assert len(issued) == 1 and len(dups) == 1 and len(rows) == 2                                  # region-only: issued (D's top added); changed-other: after D's top is restored it is the same file -> duplicate, flag kept; top-only lacks the region module: unusable
    sj = json.loads(issued[0]["scope_json"])
    assert sj["spliced"]["added_modules"] == ["d3"] and set(sj["region"]["registers"]) == {"s"} and not scope_flagged(issued[0]["scope_json"])   # an omission is restored, not flagged
    stored = Path(issued[0]["rtl_path"]).read_text()
    assert "module d3(" in stored and "assign y = s;" in stored and "~a[0]" in stored                # the full file: the rewritten sub plus D's top
    sj2 = json.loads(dups[0]["scope_json"])
    assert sj2["spliced"]["restored_modules"] == ["d3"] and sj2["violations"][0]["module"] == "d3"   # the changed top was restored from D before the duplicate check
    unusable = list(run.dir.glob("unusable_*.json"))
    assert len(unusable) == 1 and "does not contain the region module sub" in json.loads(unusable[0].read_text())["unusable"]
    assert run.state["scope_violations"] == 1                                                       # only the answer that changed the top module is flagged
    superseded = SearchRun.create(cfg, conn, exp="smoke", arm="M", design_id="rtllm_d3", seed=2, model="gpt-5.6-luna", K=1, N=1, queue=q, transport=ListTransport([region_only]))
    conn.execute("UPDATE runs SET status='superseded' WHERE run_id=?", (superseded.run_id,))
    assert superseded.run(sleep=lambda s: None) == "superseded" and superseded.state["calls"] == 0     # a stopped run never continues when its job is retried


def test_drrtl_reimpl_arm_prompts_skill_library_and_in_run_skill_learning(env):
    """PLAN 5.2 (2026-09-15): the Dr. RTL re-implementation arm keeps B2's E4 scalar fitness and archive, but its prefix is
    the Dr. RTL optimizer role plus the released skill library (no map prior, no static block), each call carries the
    timing-analysis block of the K worst paths with a rotating diversity strategy instead of a class instruction, and after a
    built round one skill-extraction call distils the round into learned skills that later calls receive; the calls count
    against the run's equal-call budget; with skill learning off no such call is made (both directions)."""
    cfg, conn, q, tmp_path = env
    from src.search import prompts as PR
    from src.search.driver import SearchRun
    crit = {"critical": {"startpoint": "x[0]", "endpoint": "y_reg[3]", "slack": 0.02, "arrival": 0.9, "required": 0.92, "points": [["U1/A", "NAND2_X1"], ["y_reg[3]/D", "DFF_X1"]]},
            "endpoints": [["x[0]", "y_reg[3]", 0.02], ["x[1]", "y_reg[2]", 0.05]]}
    conn.execute("UPDATE evaluations SET crit_path_json=? WHERE design_id='rtllm_d' AND config='E4' AND is_baseline=1", (json.dumps(crit),))
    skills_answer = {"skills": [{"pattern": "adder feeding a register", "strategy": "precompute the constant increment", "confidence": "high", "basis": "a1 improved area"}]}
    tr = ListTransport([rewrite("a1"), rewrite("a2"), skills_answer, rewrite("b1")])
    run = SearchRun.create(cfg, conn, exp="smoke", arm="DrRTL_reimpl", design_id="rtllm_d", seed=1, model="gpt-5.6-luna", K=2, N=2, queue=q, transport=tr)
    assert run.drrtl and run.scalar and run.fit_cfg == "E4" and run.floor == {} and "RTL Optimization Agent" in run.system
    assert "Learned RTL optimization skills (cross-design library" in run.prefix and "High-confidence" in run.prefix and "Do not use" in run.prefix
    assert "Map prior" not in run.prefix and "Static guidance" not in run.prefix and "No map prior" not in run.prefix
    assert run.step() == "running" and run.state["calls"] == 2
    req = json.loads(Path(sorted((tmp_path / "results" / "llm" / run.run_id).glob("c*.json"))[0]).read_text())
    inp = req["request"]["input"]
    assert "Timing analysis of the current design" in inp and "path 1: x[0] -> y_reg[3], slack 0.02 ns" in inp and "cells on the path: NAND2_X1 -> DFF_X1" in inp
    assert "path selection: top_slack; optimization focus: combinational" in inp and "Instruction (class" not in inp and "Apply a learned skill" in inp
    cands = [r[0] for r in conn.execute("SELECT cand_id FROM candidates WHERE run_id=? ORDER BY cand_id", (run.run_id,))]
    assert all(conn.execute("SELECT class_requested FROM candidates WHERE cand_id=?", (c,)).fetchone()[0] == "free" for c in cands)
    assert run.state["cands"][cands[0]]["drrtl_strategy"] in (cfg["search"]["drrtl"]["strategies"])
    for cid, area in zip(cands, (90.0, 100.0)):
        finish_eq(conn, cfg, tmp_path, cid, verdict="proven")
    run.process_verdicts()
    for cid, area in zip(cands, (90.0, 100.0)):
        finish_e4(conn, cid, area)
    assert run.step() == "running"                                                # round 1 built -> the skill call (call 3), then round 2 with the one call left (call 4)
    assert run.state["calls"] == 4 and tr.calls == 4 and run.state["skill_learning_due"] == 2   # round 2 is marked but never distilled: the equal-call budget is spent
    assert run.state["drrtl_skill_calls"][0]["gen"] == 1 and "precompute the constant increment" in run.state["drrtl_skills"]
    skill_req = json.loads(Path(sorted((tmp_path / "results" / "llm" / run.run_id).glob("c*.json"))[2]).read_text())
    assert skill_req["tag"].endswith("skills:g1") and "group-relative" in skill_req["request"]["input"] and "round_mean_dA_pct" in skill_req["request"]["input"]
    gen2_req = json.loads(Path(sorted((tmp_path / "results" / "llm" / run.run_id).glob("c*.json"))[3]).read_text())
    assert "Skills learned in this run so far" in gen2_req["request"]["input"] and "[high] pattern: adder feeding a register" in gen2_req["request"]["input"]
    assert conn.execute("SELECT llm_calls FROM runs WHERE run_id=?", (run.run_id,)).fetchone()[0] == 4
    last = [r[0] for r in conn.execute("SELECT cand_id FROM candidates WHERE run_id=? AND gen=2", (run.run_id,))]
    for cid in last:
        finish_eq(conn, cfg, tmp_path, cid, verdict="proven")
    run.process_verdicts()
    for cid in last:
        finish_e4(conn, cid, 97.0)
    assert run.step() == "done" and tr.calls == 4 and run.state["calls"] == 4                  # no skill call beyond the budget once the last round is in
    # skill learning off: no extra call
    cfg["search"]["drrtl"]["skill_learning"] = False
    tr2 = ListTransport([rewrite("c1"), rewrite("c2"), rewrite("c3"), rewrite("c4")])
    run2 = SearchRun.create(cfg, conn, exp="smoke", arm="DrRTL_reimpl", design_id="rtllm_d", seed=2, model="gpt-5.6-luna", K=2, N=2, queue=q, transport=tr2)
    run2.step()
    c2 = [r[0] for r in conn.execute("SELECT cand_id FROM candidates WHERE run_id=? ORDER BY cand_id", (run2.run_id,))]
    for cid in c2:
        finish_eq(conn, cfg, tmp_path, cid, verdict="proven")
    run2.process_verdicts()
    for cid in c2:
        finish_e4(conn, cid, 95.0)
    run2.step()
    assert run2.state["calls"] == 4 and not run2.state.get("drrtl_skill_calls") and not run2.state.get("skill_learning_due")


def test_drrtl_paths_block_selection_strategies():
    from src.search import prompts as PR
    cp = {"critical": {"startpoint": "a", "endpoint": "u0/r_reg[1]", "slack": 0.01}, "endpoints": [["a", "u0/r_reg[1]", 0.01], ["b", "u1/s_reg[0]", 0.02], ["c", "u0/r_reg[2]", 0.03], ["d", "u1/s_reg[1]", 0.04]]}
    top = PR.drrtl_paths_block(cp, {"paths": "top_slack", "focus": "mixed"}, 2)
    assert "path 1: a -> u0/r_reg[1], slack 0.01 ns" in top and "path 2: b" in top and "path 3" not in top
    mod = PR.drrtl_paths_block(cp, {"paths": "module", "focus": "combinational"}, 10)
    assert "u0/r_reg[1]" in mod and "u0/r_reg[2]" in mod and "u1/s_reg" not in mod                      # the instance holding the worst path
    clu = PR.drrtl_paths_block(cp, {"paths": "endpoint_cluster", "focus": "mixed"}, 10)
    assert "u0/r_reg" in clu or "u1/s_reg" in clu
    rnd = PR.drrtl_paths_block(cp, {"paths": "random", "focus": "mixed"}, 2, rng=random.Random(3))
    assert rnd.count("- path ") == 2
    assert "no path data is available" in PR.drrtl_paths_block(None, {"paths": "top_slack"}, 5)
