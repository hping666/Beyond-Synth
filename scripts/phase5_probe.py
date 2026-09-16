#!/usr/bin/env python3
"""The large-design correctness probe (G5 decisions item 1, DECISIONS 2026-09-15): gpt-5.6-terra and gpt-5.6-sol on the three
large Exp1 designs, 2 seeds x K = 6 x N = 5 each, arm M with the correctness aids, exp `phase5_probe` (budget
llm.budget_usd.phase5_probe = 120 USD). Decision rule: a model with at least `min_proven` proven candidates on a design
carries the large tier for arms M and B2 in Phase 5; sol is never the main model.
    .venv/bin/python scripts/phase5_probe.py create [--submit]      # the 12 runs (config exp5.correctness_probe)
    .venv/bin/python scripts/phase5_probe.py status                 # per run and per (model, design): calls, candidates, proven, the decision
Starts only after the tiered prune and the user's review of the B1 prefix (decision 2026-09-15 item 6).
"""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
import argparse  # noqa: E402
import json  # noqa: E402
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402

EXP = "phase5_probe"


def probe_cfg(cfg):
    return cfg["exp5"]["correctness_probe"]


def existing_runs(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM runs WHERE exp=? ORDER BY run_id", (EXP,))]


def cmd_create(cfg, conn, do_submit):
    from src.jobqueue.core import Queue
    from src.search.driver import SearchRun
    pc = probe_cfg(cfg)
    for model in pc["models"]:
        for tier in ("standard", "flex"):
            if model not in (cfg["llm"].get("prices_usd_per_1m") or {}).get(tier, {}):
                raise SystemExit(f"{model}: no {tier} price in llm.prices_usd_per_1m (decision 2026-09-15 item 4: re-check the live page first)")
    have = {(r["llm_model"], r["design_id"], int(r["seed"])) for r in existing_runs(conn) if r["status"] != "superseded"}
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    created = []
    for model in pc["models"]:
        for did in pc["designs"]:
            for seed in range(1, int(pc["seeds"]) + 1):
                if (model, did, seed) in have:
                    continue
                run = SearchRun.create(cfg, conn, exp=EXP, arm=str(pc.get("arm") or "M"), design_id=did, seed=seed, model=model, K=int(pc["K"]), N=int(pc["N"]), queue=q,
                                       note=f"correctness probe (G5 item 1): {model} on {did} seed {seed}")
                created.append(run.run_id)
                if do_submit:
                    q.submit("search", {"run_id": run.run_id}, design_id=did, config="search", priority=3, timeout_sec=24 * 3600)
    print(f"{len(created)} probe runs created ({'submitted' if do_submit else 'not submitted'}); arm {pc.get('arm') or 'M'}, K {pc['K']} x N {pc['N']}, cap {cfg['llm']['budget_usd']['phase5_probe']} USD")
    for r in created:
        print("  " + r)
    return 0


def cmd_status(cfg, conn):
    pc = probe_cfg(cfg)
    rows = [r for r in existing_runs(conn) if r["status"] != "superseded"]
    superseded = [r for r in existing_runs(conn) if r["status"] == "superseded"]
    if superseded:
        print(f"({len(superseded)} superseded runs not shown: the first launch, stopped after the scope-splice fix)")
    by = {}
    for r in rows:
        n = conn.execute("SELECT COUNT(*), SUM(verdict='proven'), SUM(verdict='sim_fail'), SUM(verdict='falsified'), SUM(verdict='rejected'), SUM(verdict='inconclusive'), SUM(label='scope_violation'), SUM(repair_of IS NOT NULL) FROM candidates WHERE run_id=?", (r["run_id"],)).fetchone()
        print(f"{r['run_id']:44s} {r['llm_model']:14s} {r['design_id']:34s} {r['status']:8s} gens {r['gens_done'] or 0} calls {r['llm_calls'] or 0} usd {float(r['spent_usd'] or 0):.2f} cands {n[0]} proven {n[1] or 0} sim_fail {n[2] or 0} falsified {n[3] or 0} rejected {n[4] or 0} inconclusive {n[5] or 0} scope_violation {n[6] or 0} repairs {n[7] or 0}")
        k = (r["llm_model"], r["design_id"])
        by.setdefault(k, {"runs": 0, "proven": 0, "cands": 0, "done": 0})
        by[k]["runs"] += 1
        by[k]["proven"] += int(n[1] or 0)
        by[k]["cands"] += int(n[0])
        by[k]["done"] += int(r["status"] == "done")
    spent = conn.execute("SELECT COALESCE(SUM(amount),0) FROM budget_ledger WHERE phase=? AND kind='llm'", (EXP,)).fetchone()[0]
    print(f"probe spend {float(spent):.2f} of {cfg['llm']['budget_usd']['phase5_probe']} USD")
    for (model, did), v in sorted(by.items()):
        verdict = "carries the large tier" if v["proven"] >= int(pc["min_proven"]) else ("below min_proven" if v["done"] == v["runs"] else "pending")
        print(f"  {model:14s} {did:34s} runs {v['runs']} done {v['done']} candidates {v['cands']} proven {v['proven']} -> {verdict} (rule: >= {pc['min_proven']} proven on the design)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["create", "status"])
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    if a.what == "create":
        return cmd_create(cfg, conn, a.submit)
    return cmd_status(cfg, conn)


if __name__ == "__main__":
    sys.exit(main())
