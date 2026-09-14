#!/usr/bin/env python3
"""Phase 3 — LLM calibration (docs/PLAN.md Phase 3; config llm.calibration): the four candidate models run residual-guided
evolution (minimal skeleton: no synthesis-rung screening, full E4, no map prior yet) on the calibration designs with
K generations x N candidates and two seeds; every run is one `search` queue job (rule 9). Collect reports per model
the pass rates, the class distribution and the requested -> produced confusion matrix, the retention fraction (headline
and materiality row, proven_sim_only apart), the best retained gain per design (offset designs flagged), LLM calls /
dollars / DC hours / VC Formal hours per retained candidate, time-to-verdict distributions and inconclusive rates per
class, and applies the decision rule of config llm.calibration.decision.

    .venv/bin/python scripts/phase3_calibrate.py designs                    # the calibration set (dev designs only, rule 4)
    .venv/bin/python scripts/phase3_calibrate.py smoke  --model gpt-5.6-luna --design rtllm_accu [--K 1 --N 2] --submit
    .venv/bin/python scripts/phase3_calibrate.py submit [--models ...] [--seeds 1 2] [--K 6 --N 5] --submit
    .venv/bin/python scripts/phase3_calibrate.py status
    .venv/bin/python scripts/phase3_calibrate.py collect
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import statistics  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.noise import stats as S  # noqa: E402
from src.search.driver import SearchRun  # noqa: E402

CATEGORY_HINTS = {"arith": ("adder", "sub", "mult", "multi", "div", "accu", "comparator", "fixed", "float", "alu"), "memory": ("RAM", "fifo", "FIFO", "LIFO", "reg", "buffer"),
                  "control": ("fsm", "counter", "detect", "traffic", "light", "signal", "freq", "pulse", "sequence"), "misc": ()}


def calibration_designs(cfg, conn, n=None):
    """Deterministic calibration set from the dev split only (CLAUDE.md rule 4): designs with a measured E4 floor and an
    E4 baseline at Phi, one per category first (arithmetic / memory / control / misc), the largest by LOC first."""
    n = int(n or cfg["llm"]["calibration"]["designs"])
    rows = [dict(r) for r in conn.execute("SELECT d.design_id, d.loc FROM designs d WHERE d.split='dev' AND d.phi_main_ns_nangate45 IS NOT NULL AND EXISTS "
                                          "(SELECT 1 FROM noise_floor n WHERE n.design_id=d.design_id AND n.config='E4' AND n.metric='area' AND n.floor_source='measured') AND EXISTS "
                                          "(SELECT 1 FROM evaluations e WHERE e.design_id=d.design_id AND e.config='E4' AND e.is_baseline=1 AND e.status='ok' AND abs(e.clock_ns-d.phi_main_ns_nangate45)<1e-6) "
                                          "ORDER BY d.loc DESC, d.design_id")]

    def cat(did):
        name = did.split("_", 1)[1] if "_" in did else did
        for c, hints in CATEGORY_HINTS.items():
            if any(h.lower() in name.lower() for h in hints):
                return c
        return "misc"
    chosen, seen_cat = [], set()
    for r in rows:
        c = cat(r["design_id"])
        if c not in seen_cat:
            chosen.append(r["design_id"])
            seen_cat.add(c)
        if len(chosen) >= n:
            break
    for r in rows:
        if len(chosen) >= n:
            break
        if r["design_id"] not in chosen:
            chosen.append(r["design_id"])
    return chosen[:n]


def submit_runs(cfg, conn, designs, models, seeds, K, N, exp, do_submit, note=""):
    from src.jobqueue.core import Queue
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    runs = []
    for model in models:
        for did in designs:
            for seed in seeds:
                run = SearchRun.create(cfg, conn, exp=exp, arm="M", design_id=did, seed=seed, model=model, K=K, N=N, queue=q, note=note)
                runs.append(run.run_id)
                if do_submit:
                    q.submit("search", {"run_id": run.run_id}, design_id=did, config="search", priority=3, timeout_sec=12 * 3600)
    print(f"{len(runs)} runs ({len(models)} models x {len(designs)} designs x {len(seeds)} seeds, K={K}, N={N}, exp={exp})" + (" submitted" if do_submit else " created (not submitted)"))
    return runs


def auroc(scores_pos, scores_neg):
    """Area under the ROC curve of a score that should be higher for positives (ties count half); None when a class is empty."""
    if not scores_pos or not scores_neg:
        return None
    wins = 0.0
    for p in scores_pos:
        for n in scores_neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(scores_pos) * len(scores_neg))


def y_jobs(cfg, conn, do_submit):
    """Y (Yosys + OpenSTA) evaluations of every E4-evaluated Phase 3 candidate and of D at Phi_main, for AUROC(Y -> E4
    retention) (PLAN 3 acceptance; DECISIONS 2026-09-14 G3.1). Missing records only; `yosys` jobs on the local pool."""
    from src.designs import catalog as K
    from src.designs import jobs as J
    from src.jobqueue.core import Queue
    designs = {d["design_id"]: d for d in K.load_all()}
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    jobs = []
    seen_design = set()
    for c in conn.execute("SELECT c.cand_id, c.design_id, c.rtl_path FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase3' AND c.e4_job_id IS NOT NULL"):
        d = designs[c["design_id"]]
        phi = float(conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (c["design_id"],)).fetchone()[0])
        if c["design_id"] not in seen_design:
            seen_design.add(c["design_id"])
            if conn.execute("SELECT 1 FROM evaluations WHERE design_id=? AND config='Y' AND is_baseline=1 AND status='ok' AND abs(clock_ns-?)<1e-6 LIMIT 1", (c["design_id"], phi)).fetchone() is None:
                j = J.dc_job(cfg, d, "Y", phi, 3)
                j["kind"] = "yosys"
                jobs.append(j)
        if conn.execute("SELECT 1 FROM evaluations WHERE design_id=? AND cand_id=? AND config='Y' AND status='ok' LIMIT 1", (c["design_id"], c["cand_id"])).fetchone():
            continue
        j = J.dc_job(cfg, d, "Y", phi, 3)
        j["kind"] = "yosys"
        j["payload"].update(rtl=[c["rtl_path"]], incdirs=[], is_baseline=0, cand_id=c["cand_id"])
        j["cand_id"] = c["cand_id"]
        jobs.append(j)
    print(f"{len(jobs)} Y jobs (candidates of the Phase 3 runs and their baselines, missing records only)")
    if do_submit:
        for j in jobs:
            q.submit(j["kind"], j["payload"], design_id=j["design_id"], cand_id=j.get("cand_id"), config="Y", priority=j["priority"], timeout_sec=j["timeout_sec"])
        print(f"submitted {len(jobs)} yosys jobs")
    return jobs


def y_auroc(cfg, conn):
    """AUROC of the Y area gain (and of the best-of-three-components Y gain) for E4 retention over the diagnosed candidates."""
    pos, neg, pos3, neg3 = [], [], [], []
    for c in conn.execute("SELECT c.cand_id, c.design_id, c.label FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase3' AND c.label IN ('retained','absorbed','absorbed_identical','noise','harmful','tradeoff','fragile','duplicate')"):
        phi = float(conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (c["design_id"],)).fetchone()[0])
        base = conn.execute("SELECT area_um2, wns_ns, power_default_mw FROM evaluations WHERE design_id=? AND config='Y' AND is_baseline=1 AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY eval_id DESC LIMIT 1", (c["design_id"], phi)).fetchone()
        cand = conn.execute("SELECT area_um2, wns_ns, power_default_mw FROM evaluations WHERE design_id=? AND cand_id=? AND config='Y' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (c["design_id"], c["cand_id"])).fetchone()
        if base is None or cand is None or not base["area_um2"]:
            continue
        g_area = (float(base["area_um2"]) - float(cand["area_um2"])) / float(base["area_um2"])
        g_wns = ((float(cand["wns_ns"] or 0) - float(base["wns_ns"] or 0)) / phi) if phi else 0.0
        g_pow = ((float(base["power_default_mw"]) - float(cand["power_default_mw"])) / float(base["power_default_mw"])) if base["power_default_mw"] and cand["power_default_mw"] else 0.0
        (pos if c["label"] == "retained" else neg).append(g_area)
        (pos3 if c["label"] == "retained" else neg3).append(max(g_area, g_wns, g_pow))
    return {"n_retained": len(pos), "n_other": len(neg), "auroc_area": auroc(pos, neg), "auroc_best_component": auroc(pos3, neg3)}


def cmd_sample(cfg, conn, n=40, seed=1):
    """PLAN 3.5: a stratified sample of diagnosed candidates for the manual verification (reading both netlists and logs):
    up to n candidates spread over the labels, deterministic; the checklist lists the evidence and the raw directories."""
    import random
    rows = [dict(r) for r in conn.execute("SELECT c.cand_id, c.run_id, c.design_id, c.llm_model, c.class_requested, c.class_final, c.rtl_path, d.label, d.rung, d.evidence_json "
                                          "FROM candidates c JOIN diagnoses d ON d.cand_id=c.cand_id JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase3' ORDER BY c.cand_id")]
    by = {}
    for r in rows:
        by.setdefault(r["label"], []).append(r)
    rng = random.Random(seed)
    labels = sorted(by)
    quota = {lab: max(1, n // len(labels)) for lab in labels} if labels else {}
    sample = []
    for lab in labels:
        pool = by[lab][:]
        rng.shuffle(pool)
        sample += pool[:quota[lab]]
    rest = [r for lab in labels for r in by[lab] if r not in sample]
    rng.shuffle(rest)
    sample += rest[:max(0, n - len(sample))]
    out = Path(C.ROOT) / "reports" / "data" / "phase3_manual_sample.json"
    out.write_text(json.dumps({"seed": seed, "n": len(sample), "labels": {lab: len(v) for lab, v in by.items()}, "sample": sample}, indent=1, default=str) + "\n")
    md = [f"# Phase 3 manual verification sample ({len(sample)} of {len(rows)} diagnosed candidates, seed {seed})", "",
          "| # | design | model | requested -> produced | label (rung) | E4 raw dir | candidate RTL | agree? | note |", "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(sample, 1):
        raw = conn.execute("SELECT raw_dir FROM evaluations WHERE cand_id=? AND config='E4' ORDER BY eval_id DESC LIMIT 1", (r["cand_id"],)).fetchone()
        md.append(f"| {i} | {r['design_id']} | {r['llm_model']} | {r['class_requested']} -> {r['class_final']} | {r['label']} ({r['rung'] or '-'}) | {raw[0] if raw else '-'} | {r['rtl_path']} |  |  |")
    (Path(C.ROOT) / "reports" / "data" / "phase3_manual_sample.md").write_text("\n".join(md) + "\n")
    print(f"{len(sample)} sampled from {len(rows)} diagnosed candidates over labels {dict((lab, len(v)) for lab, v in by.items())}; wrote {out} and the .md checklist")
    return 0


def cmd_status(cfg, conn):
    for r in conn.execute("SELECT run_id, design_id, llm_model, seed, status, gens_done, llm_calls, spent_usd, spent_dc_hours FROM runs WHERE exp IN ('phase3','smoke') ORDER BY started_at"):
        n = conn.execute("SELECT COUNT(*), SUM(label='retained'), SUM(label IS NULL) FROM candidates WHERE run_id=?", (r["run_id"],)).fetchone()
        print(f"{r['run_id']:44s} {r['design_id']:28s} {r['llm_model']:14s} s{r['seed']} {r['status']:8s} gens {r['gens_done']} calls {r['llm_calls']} "
              f"usd {r['spent_usd'] or 0:.3f} dc_h {r['spent_dc_hours'] or 0:.2f} cands {n[0]} retained {n[1] or 0} pending {n[2] or 0}")
    print("phase3 LLM spend:", round(conn.execute("SELECT COALESCE(SUM(amount),0) FROM budget_ledger WHERE phase='phase3_calibration' AND kind='llm'").fetchone()[0], 3), "USD")
    return 0


def cmd_collect(cfg, conn):
    mat = cfg["noise"]["materiality"]
    runs = [dict(r) for r in conn.execute("SELECT * FROM runs WHERE exp='phase3'")]
    per_model = {}
    for run in runs:
        m = per_model.setdefault(run["llm_model"], {"runs": 0, "designs": set(), "calls": 0, "usd": 0.0, "dc_h": 0.0, "vcf_h": 0.0, "cands": 0, "unusable": 0,
                                                    "v1_ok": 0, "v3_proven": 0, "proven_sim_only": 0, "inconclusive": 0, "labels": {}, "classes": {}, "confusion": {},
                                                    "retained_material": 0, "best_gain": {}, "ttv": {}, "inconclusive_by_class": {}, "n_by_class": {}, "offset_retained": 0, "absorbed_response": [0, 0]})
        m["runs"] += 1
        m["designs"].add(run["design_id"])
        m["calls"] += int(run["llm_calls"] or 0)
        m["usd"] += float(run["spent_usd"] or 0)
        m["dc_h"] += float(run["spent_dc_hours"] or 0)
        m["vcf_h"] += float(run["spent_vcf_hours"] or 0)
        m["unusable"] += len(list((Path(C.ROOT) / "results" / "candidates" / run["run_id"]).glob("unusable_*.json")))
        floor = S.latest_floor(conn, run["design_id"], "E4")
        offset = any(r.get("floor_class") == "offset" for r in floor.values())
        base = conn.execute("SELECT area_um2, wns_ns, power_saif_mw, power_default_mw FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND status='ok' ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (run["design_id"],)).fetchone()
        for c in conn.execute("SELECT c.*, d.label AS dlabel, d.evidence_json FROM candidates c LEFT JOIN diagnoses d ON d.cand_id=c.cand_id WHERE c.run_id=?", (run["run_id"],)):
            c = dict(c)
            m["cands"] += 1
            m["v1_ok"] += int(c.get("v1_status") == "ok")
            m["v3_proven"] += int(c.get("verdict") == "proven")
            m["proven_sim_only"] += int(c.get("verdict") == "proven_sim_only")
            m["inconclusive"] += int(c.get("v3_status") == "inconclusive")
            cls = c.get("class_final") or "?"
            m["classes"][cls] = m["classes"].get(cls, 0) + 1
            key = f"{c.get('class_requested')}->{cls}"
            m["confusion"][key] = m["confusion"].get(key, 0) + 1
            m["n_by_class"][cls] = m["n_by_class"].get(cls, 0) + 1
            if c.get("v3_status") == "inconclusive":
                m["inconclusive_by_class"][cls] = m["inconclusive_by_class"].get(cls, 0) + 1
            if c.get("time_to_verdict_s") is not None:
                m["ttv"].setdefault(cls, []).append(float(c["time_to_verdict_s"]))
            lab = c.get("label") or c.get("dlabel") or "pending"
            m["labels"][lab] = m["labels"].get(lab, 0) + 1
            ev = json.loads(c.get("evidence_json") or "{}") if c.get("evidence_json") else {}
            g = ev.get("gains") or {}
            if lab == "retained":
                if offset:
                    m["offset_retained"] += 1
                best = m["best_gain"].setdefault(run["design_id"], {"area": 0.0, "offset_design": offset})
                best["area"] = max(best["area"], float(g.get("area") or 0.0))
            # materiality sensitivity row: a fixed threshold instead of rule A
            if c.get("verdict") == "proven" and g:
                up = [k for k in g if float(g[k]) > float(mat.get({"power": "power_saif"}.get(k, k), 1.0))]
                down = [k for k in g if float(g[k]) < -float(mat.get({"power": "power_saif"}.get(k, k), 1.0))]
                m["retained_material"] += int(bool(up) and not down)
            # response to "absorbed" feedback: a child of an absorbed parent that is not absorbed itself
            if c.get("parent_id"):
                pl = conn.execute("SELECT label FROM candidates WHERE cand_id=?", (c["parent_id"],)).fetchone()
                if pl and pl[0] in ("absorbed", "absorbed_identical"):
                    m["absorbed_response"][1] += 1
                    m["absorbed_response"][0] += int(lab not in ("absorbed", "absorbed_identical", "duplicate"))
    out = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "models": {}}
    for model, m in per_model.items():
        retained = m["labels"].get("retained", 0)
        ttv = {cls: {"n": len(v), "median": statistics.median(v), "q95": S.quantile(v, 0.95), "max": max(v)} for cls, v in m["ttv"].items() if v}
        out["models"][model] = {**{k: v for k, v in m.items() if k not in ("designs", "ttv")}, "designs": sorted(m["designs"]), "retained": retained,
                                "retained_per_usd": (retained / m["usd"]) if m["usd"] else None, "retained_per_dc_hour": (retained / m["dc_h"]) if m["dc_h"] else None,
                                "llm_calls_per_retained": (m["calls"] / retained) if retained else None, "time_to_verdict": ttv,
                                "inconclusive_rate_by_class": {cls: m["inconclusive_by_class"].get(cls, 0) / n for cls, n in m["n_by_class"].items() if n}}
    dec = cfg["llm"]["calibration"]["decision"]
    scored = {mo: (v.get("retained_per_usd") or 0.0) for mo, v in out["models"].items()}
    best_gain_by_model = {mo: max((b["area"] for b in v["best_gain"].values()), default=0.0) for mo, v in out["models"].items()}
    strongest = max(best_gain_by_model.values(), default=0.0)
    eligible = [mo for mo, v in out["models"].items() if best_gain_by_model[mo] >= float(dec["floor_best_gain_ratio"]) * strongest
                and (not dec.get("require_c1_or_d_retained") or any(k.endswith("c1") or k.endswith("d") for k in v["confusion"] if v["labels"].get("retained")))]
    out["decision"] = {"primary_metric": dec["primary_metric"], "scores": scored, "best_gain_by_model": best_gain_by_model, "eligible": eligible,
                       "recommended": max(eligible, key=lambda mo: scored[mo]) if eligible else None,
                       "note": "recommendation by config llm.calibration.decision; the user confirms at G4 (config llm.selected stays TBD until then)"}
    out["y_auroc"] = y_auroc(cfg, conn)
    p = Path(C.ROOT) / "reports" / "data" / "phase3_calibration.json"
    p.write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    for mo, v in sorted(out["models"].items()):
        print(f"{mo:14s} runs {v['runs']} cands {v['cands']} unusable {v['unusable']} v3 proven {v['v3_proven']} sim_only {v['proven_sim_only']} inconclusive {v['inconclusive']} "
              f"retained {v['retained']} (material {v['retained_material']}) usd {v['usd']:.2f} dc_h {v['dc_h']:.2f} calls/retained {v['llm_calls_per_retained']}")
    print("decision:", out["decision"]["recommended"], "eligible:", out["decision"]["eligible"])
    print(f"wrote {p}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["designs", "smoke", "submit", "status", "collect", "yruns", "sample"])
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--design", nargs="*", default=None)
    ap.add_argument("--seeds", nargs="*", type=int, default=None)
    ap.add_argument("--K", type=int, default=None)
    ap.add_argument("--N", type=int, default=None)
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    cal = cfg["llm"]["calibration"]
    if a.what == "designs":
        print(calibration_designs(cfg, conn))
        return 0
    if a.what == "status":
        return cmd_status(cfg, conn)
    if a.what == "collect":
        return cmd_collect(cfg, conn)
    if a.what == "yruns":
        y_jobs(cfg, conn, a.submit)
        return 0
    if a.what == "sample":
        return cmd_sample(cfg, conn)
    if a.what == "smoke":
        designs = a.design or calibration_designs(cfg, conn)[:1]
        submit_runs(cfg, conn, designs, [a.model or cfg["llm"]["candidates"][0]], a.seeds or [1], a.K or 1, a.N or 2, "smoke", a.submit, note="smoke")
        return 0
    designs = a.design or calibration_designs(cfg, conn)
    submit_runs(cfg, conn, designs, a.models or cfg["llm"]["candidates"], a.seeds or list(range(1, int(cal["seeds"]) + 1)), a.K or int(cal["K"]), a.N or int(cal["N"]), "phase3", a.submit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
