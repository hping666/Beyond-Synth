#!/usr/bin/env python3
"""C2 interim evidence report (REQUEST 2026-09-20 (f), v2 under REQUEST 2026-09-20 (g)) — read-only.

Writes reports/c2_interim_<date>.md and reports/data/c2_interim.json. Uniform caliber: equal LLM calls per run
(scale.budget.llm_calls_per_run), rule A at E4 with each design's frozen phase4 floor, per-metric verdicts, the materiality
count beside every retention figure. v2: every tally and arm table is split by model (main model = the tier's
exp5.model_assignment.all_arms, never mixed with the contrast model); the pre-registered caliber (geometric mean over seeds,
2 σ_D separation, equal visible DC hours) is reported beside the visible-layer proxy; designs where no arm produced a proven
candidate are excluded from the denominator; the power basis is given both on the search basis and on the offline SAIF
baselines of REQUEST (e) item 2. Nothing is altered and the hidden database is not read.

  python3 scripts/report_c2.py [--date YYYY-MM-DD]
"""
import argparse
import collections
import copy
import datetime
import glob
import importlib.util
import json
import math
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.analysis import phase5 as P5  # noqa: E402
from src.diagnose import m3  # noqa: E402

_c1 = importlib.util.spec_from_file_location("report_c1", os.path.join(ROOT, "scripts", "report_c1.py"))
C1 = importlib.util.module_from_spec(_c1)
_c1.loader.exec_module(C1)
_rp = importlib.util.spec_from_file_location("report_phase", os.path.join(ROOT, "scripts", "report_phase.py"))
RP = importlib.util.module_from_spec(_rp)
_rp.loader.exec_module(RP)

METRICS = ("area", "power", "wns")
BASES = ("search", "offline_saif")
MODES = (("decided", "as_run", ("area",), "rule A as run (all three metrics), arms separated on area — the decided tally rule (DECISION 2026-09-19 (m) 4 / (n) 2)"),
         ("as_run", "as_run", METRICS, "rule A as run, arms separated on any metric"),
         ("saif_any", "saif_any", None, "(i) any metric, power only where both records carry SAIF power"),
         ("area", "area", ("area",), "(ii) area only (rule A on area alone)"),
         ("wns", "wns", ("wns",), "(iii) WNS only (rule A on WNS alone)"))
LABEL_MODES = ("as_run", "saif_any", "area", "wns")
ARMS = ("B0", "B1_E4", "B2", "DrRTL_reimpl", "M")
SOURCES = {}


def src(name, text):
    SOURCES[name] = text
    return text


def pct(x, nd=1):
    return "pending" if x is None else f"{100 * float(x):.{nd}f} %"


def num(x, nd=2):
    return "pending" if x is None else f"{float(x):.{nd}f}"


def rate(n, d):
    return (n / d) if d else None


def gmean_ratio(xs):
    """Geometric mean of the gain ratios: exp(mean(log(1+g))) − 1 (defined when a seed found nothing, unlike the plain
    geometric mean, which is then 0; both are reported)."""
    xs = [x for x in xs if x is not None]
    if not xs or any(1.0 + float(x) <= 0 for x in xs):
        return None
    return math.exp(sum(math.log(1.0 + float(x)) for x in xs) / len(xs)) - 1.0


def gmean_strict(xs):
    xs = [float(x) for x in xs if x is not None]
    if not xs:
        return None
    if any(x <= 0 for x in xs):
        return 0.0
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def strip_metrics(rec, keep):
    r = copy.deepcopy(rec)
    m = r.get("metrics") or {}
    if "area" not in keep:
        m["area"] = m["area_um2"] = None
    if "wns" not in keep:
        m["wns_ns"] = None
    if "power" not in keep:
        m["power_saif_mw"] = m["power_default_mw"] = None
    return r


# ----------------------------------------------------------------------------- scan
def scan(cfg, conn, dcache, complete_set, exp="phase5"):
    """Runs and candidates; on the complete designs every proven candidate with an E4 record is labelled under each metric mode
    and under both power bases (search = the evaluators' baseline, offline_saif = the offline SAIF baseline of REQUEST (e) 2)."""
    src("run scan", "runs (exp phase5, status != superseded, excluded_from_tables = 0) with their candidates; labels from src.diagnose.m3.diagnose on the candidate's latest ok E4 record against D's E4 baseline "
                    "(search basis: is_baseline = 1 at Φ_main; offline_saif basis: offline_baseline = 1 where it exists), with the frozen phase4 thresholds; the metric modes remove the other metrics from the record")
    tier_of = P5.tier_of_design(cfg)
    dc_by_run, dc_by_cand = dc_hours(conn, exp)
    runs, cands = [], []
    for r in conn.execute("SELECT * FROM runs WHERE exp=? AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0 ORDER BY created_at", (exp,)):
        r = dict(r)
        r["tier"] = tier_of.get(r["design_id"])
        if r["tier"] is None:
            continue
        r["row"] = f"{r['arm']}|{r['llm_model']}"
        r["dc_h"] = dc_by_run.get(r["run_id"], 0.0)
        rdir = os.path.join(C.results_dir(cfg), "candidates", r["run_id"])
        r["unusable"] = len([f for f in os.listdir(rdir) if f.startswith("unusable_")]) if os.path.isdir(rdir) else 0
        runs.append(r)
        full = r["design_id"] in complete_set
        for c in conn.execute("SELECT * FROM candidates WHERE run_id=? ORDER BY gen, created_at", (r["run_id"],)):
            c = dict(c)
            c.update(run=r["run_id"], tier=r["tier"], arm=r["arm"], model=r["llm_model"], design_id=r["design_id"], row=r["row"],
                     dc_s=dc_by_cand.get(c["cand_id"], 0.0), lab={b: {} for b in BASES}, g={b: {} for b in BASES})
            try:
                c["tags"] = sorted({t for t in (C1.norm_subtag(x) for x in json.loads(c.get("subtags_json") or "[]") if isinstance(x, str)) if t})
            except (ValueError, TypeError):
                c["tags"] = []
            if c.get("verdict") == "proven":
                ev = conn.execute("SELECT * FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (c["cand_id"],)).fetchone()
                if ev is not None:
                    rec = P5.record_from_row(ev)
                    for b in BASES:
                        d = dcache[b].get(c["design_id"])
                        if not d or not d["base"] or d["phi"] is None:
                            continue
                        def lab(keep):
                            o = m3.diagnose(d["base"], strip_metrics(rec, keep) if keep else rec, d["sigma"], d["phi"], v3_status="proven",
                                            k_sigma=dcache[b].k_sigma, thresholds=d["thresholds"], floor_class=d["floor_class"])
                            return o.get("label"), ((o.get("evidence") or {}).get("gains") or {}), (o.get("evidence") or {}).get("power_basis")
                        l0, g0, basis = lab(None)
                        c["lab"][b]["as_run"], c["g"][b]["as_run"] = l0, g0
                        if b == "search":
                            c["power_basis"] = basis
                        if full:
                            if l0 in ("absorbed_identical", "duplicate"):
                                for mode in LABEL_MODES[1:]:
                                    c["lab"][b][mode], c["g"][b][mode] = l0, g0
                            else:
                                keep_any = {"area", "wns"} | ({"power"} if basis == "saif" else set())
                                for mode, keep in (("saif_any", keep_any), ("area", {"area"}), ("wns", {"wns"})):
                                    c["lab"][b][mode], c["g"][b][mode] = lab(keep)[:2]
            cands.append(c)
    return runs, cands


def dc_hours(conn, exp="phase5"):
    """(per run, per candidate) visible DC hours / seconds: the ok evaluations of the run's candidates and of their envelope
    records <cand>_env* (one pass; the per-run LIKE join of src.analysis.phase5.run_dc_hours scans the whole table)."""
    run_of = {r[0]: r[1] for r in conn.execute("SELECT c.cand_id, c.run_id FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp=?", (exp,))}
    per_run, per_cand = collections.Counter(), collections.Counter()
    for cid, sec in conn.execute("SELECT cand_id, dc_seconds FROM evaluations WHERE status='ok' AND cand_id IS NOT NULL AND dc_seconds IS NOT NULL"):
        base = cid if cid in run_of else (cid.split("_env", 1)[0] if "_env" in cid else None)
        rid = run_of.get(base) if base else None
        if rid is not None:
            per_run[rid] += float(sec)
            per_cand[base] += float(sec)
    return {k: v / 3600.0 for k, v in per_run.items()}, dict(per_cand)


def run_curve(cands_of_run, basis="search", mode="as_run"):
    """[(cumulative DC hours, best retained gain per metric so far, retained count so far)] in the candidates' own order."""
    cum, best, n, out = 0.0, {m: 0.0 for m in METRICS}, 0, []
    for c in cands_of_run:
        cum += float(c.get("dc_s") or 0.0) / 3600.0
        if c["lab"].get(basis, {}).get(mode) == "retained":
            n += 1
            for m in METRICS:
                v = c["g"][basis][mode].get(m)
                if v is not None:
                    best[m] = max(best[m], float(v))
        out.append((cum, dict(best), n))
    return out


def at_budget(curve, hours):
    """The best-so-far gains and retained count at `hours` of visible DC (the state after the last candidate within budget)."""
    b, n = {m: 0.0 for m in METRICS}, 0
    for cum, best, k in curve:
        if cum > hours:
            break
        b, n = best, k
    return b, n


# ----------------------------------------------------------------------------- rows and completeness
def row_completeness(cfg, conn, cd, tier_of):
    src("1 row completeness", "src.analysis.phase5.complete_designs: the planned arm-model rows x seeds of every design (scripts/phase5_main.plan) against the runs with status done, and the candidates still pending "
                              "a verdict, a simulation or an E4 record per row")
    ma = cfg["exp5"].get("model_assignment") or {}
    main = {t: (ma.get(t) or {}).get("all_arms") for t in ("large", "medium", "small")}
    out = {"main_model": main, "designs": {}}
    for d, rows in cd["rows"].items():
        t = tier_of.get(d)
        mm = main.get(t)
        rr = {f"{row.split('|')[1]}|{row.split('|')[0]}": dict(v, complete=(v["done"] >= v["planned"] and not v["pending"])) for row, v in rows.items()}   # complete_designs keys are model|arm
        main_rows = {row: v for row, v in rr.items() if row.split("|")[1] == mm}
        out["designs"][d] = {"tier": t, "main_model": mm, "rows": rr,
                             "main_rows_complete": sum(1 for v in main_rows.values() if v["complete"]), "main_rows": len(main_rows),
                             "all_main_complete": bool(main_rows) and all(v["complete"] for v in main_rows.values()),
                             "missing_main_rows": sorted(row for row, v in main_rows.items() if not v["complete"])}
    per_tier = {}
    for t in ("large", "medium", "small"):
        ds = [d for d, e in out["designs"].items() if e["tier"] == t]
        rows = collections.Counter()
        tot = collections.Counter()
        for d in ds:
            for row, v in out["designs"][d]["rows"].items():
                tot[row] += 1
                rows[row] += int(v["complete"])
        per_tier[t] = {"designs": len(ds), "rows_complete": {row: [rows[row], tot[row]] for row in sorted(tot)}}
    out["per_tier"] = per_tier
    return out


def best_per_run(cands, runs, design, basis, mode, budget=None):
    """{row: {"per_run": [{metric: gain}], "dc_h": [hours per run], "retained": [n per run]}} over the design's done runs; with
    `budget` the values are read off each run's DC-hour curve at that budget instead of at the end of the run."""
    by_run = collections.defaultdict(list)
    for c in cands:
        if c["design_id"] == design:
            by_run[c["run"]].append(c)
    out = collections.defaultdict(lambda: {"per_run": [], "dc_h": [], "retained": []})
    for r in runs:
        if r["design_id"] != design or r["status"] != "done":
            continue
        cs = by_run.get(r["run_id"], [])
        curve = run_curve(cs, basis, mode)
        if budget is None:
            best = {m: max([float(c["g"][basis][mode].get(m) or 0.0) for c in cs if c["lab"].get(basis, {}).get(mode) == "retained" and c["g"][basis][mode].get(m) is not None] or [0.0]) for m in METRICS}
            n = sum(1 for c in cs if c["lab"].get(basis, {}).get(mode) == "retained")
        else:
            best, n = at_budget(curve, budget)
        g = out[r["row"]]
        g["per_run"].append(best)
        g["dc_h"].append(float(r["dc_h"] or 0.0))
        g["retained"].append(n)
    return out


def outcome_of(agg, thr, metrics, model, key="mean"):
    """win / tie / partial / loss of M|model against B1_E4|model and B2|model on `metrics` with the separation threshold `thr`
    per metric: loss when a baseline is ahead by more than the threshold on some metric, win when M is ahead of both, partial
    when it separates from exactly one, tie otherwise; None when a row is missing."""
    m = agg.get(f"M|{model}")
    b1, b2 = agg.get(f"B1_E4|{model}"), agg.get(f"B2|{model}")
    if not (m and b1 and b2):
        return None, {}, "a row is missing"
    seps = {}
    for name, b in (("B1_E4", b1), ("B2", b2)):
        seps[name] = {k: (m[key][k] - b[key][k]) for k in metrics if m[key].get(k) is not None and b[key].get(k) is not None}
    if not any(seps.values()):
        return None, seps, "no metric comparable"
    above = lambda s: any(v > float(thr.get(k) or 0.0) for k, v in s.items())
    below = lambda s: any(v < -float(thr.get(k) or 0.0) for k, v in s.items())
    if below(seps["B1_E4"]) or below(seps["B2"]):
        return "loss", seps, ""
    n = int(above(seps["B1_E4"])) + int(above(seps["B2"]))
    return ("win" if n == 2 else "partial" if n == 1 else "tie"), seps, ""


# ----------------------------------------------------------------------------- 2/3. tallies
def sigma_table(conn, cfg, designs):
    """{design: {metric: (sigma_robust, 2 sigma, floor_source)}} from the frozen floor table; pooled rows have no sigma_D."""
    src("sigma_D", "noise_floor (floor_version phase4, config E4): sigma_robust per metric with floor_source; a pooled row has no measured sigma_D (the design has no proven perturbation set)")
    out = {}
    for d in designs:
        rows = {r["metric"]: dict(r) for r in conn.execute("SELECT metric, sigma_robust, floor_source, n FROM noise_floor WHERE design_id=? AND config='E4' AND floor_version=?", (d, cfg["noise"]["floor_version"]))}
        out[d] = {"source": (rows.get("area") or {}).get("floor_source"), "n": (rows.get("area") or {}).get("n"),
                  "sigma": {m: (rows.get(k) or {}).get("sigma_robust") for m, k in (("area", "area"), ("power", "power_saif"), ("wns", "wns"))}}
        out[d]["two_sigma"] = {m: (None if v is None else 2.0 * float(v)) for m, v in out[d]["sigma"].items()}
    return out


def decidability(cands, complete, tier_of):
    """Per design: 'no proven candidate' (excluded by construction), 'all arms identical' (every row's best retained gain equal),
    or decidable."""
    out = {}
    for d in complete:
        cs = [c for c in cands if c["design_id"] == d and c.get("label") not in ("duplicate", "aborted")]
        prov = [c for c in cs if c.get("verdict") == "proven"]
        ret = [c for c in prov if c["lab"]["search"].get("as_run") == "retained"]
        best = collections.defaultdict(float)
        for c in ret:
            best[c["row"]] = max(best[c["row"]], float(c["g"]["search"]["as_run"].get("area") or 0.0))
        vals = sorted(set(round(v, 6) for v in best.values()))
        if not prov:
            state, note = "not decidable: no arm produced a proven candidate", ""
        elif ret and len(vals) == 1 and vals[0] > 0:
            cls = collections.Counter((c.get("class_final") or "?") for c in ret if abs(float(c["g"]["search"]["as_run"].get("area") or 0.0) - vals[0]) < 1e-9)
            state, note = "all arms identical", f"every row's best retained area gain is {100 * vals[0]:.2f} %; deciding candidates by class: " + ", ".join(f"{k} {v}" for k, v in cls.most_common())
        else:
            state, note = "decidable", ""
        out[d] = {"state": state, "note": note, "proven": len(prov), "retained": len(ret), "candidates": len(cs), "tier": tier_of.get(d)}
    return out


def tallies(cfg, conn, runs, cands, dcache, complete, tier_of, sigmas, decid, default_basis):
    """Per model (main and contrast) and per power basis: the visible-layer proxy (mean of the per-run best, t_D separation) and
    the pre-registered caliber (geometric mean over seeds, 2 σ_D, equal visible DC hours). Only decidable designs enter a tally."""
    src("2 tallies", "per design and arm-model row the per-run best retained gain per metric (0 for a run without one); the proxy takes their mean over seeds against the design's rule-A t_D, the pre-registered caliber "
                     "the geometric mean of the gain ratios (exp(mean(log(1+g))) − 1; the plain geometric mean is printed beside it and is 0 as soon as a seed found nothing) against 2 σ_D of the design's perturbation set, "
                     "read at the smaller of M's and the baseline's mean visible DC hours per run")
    ma = cfg["exp5"].get("model_assignment") or {}
    models = sorted({r["llm_model"] for r in runs})
    out = {}
    for basis in BASES:
        for model in models:
            for mode, label_mode, mset, desc in MODES:
                key = f"{basis}|{model}|{mode}"
                tally, per_design = collections.Counter(), {}
                for d in complete:
                    if decid[d]["state"].startswith("not decidable"):
                        continue
                    thr = dcache[basis].get(d)["thresholds"]
                    metrics = mset or tuple(m for m in METRICS if m != "power" or d not in default_basis)
                    bp = best_per_run(cands, runs, d, basis, label_mode)
                    agg = {row: {"mean": {m: (statistics.mean([x[m] for x in v["per_run"]]) if v["per_run"] else None) for m in METRICS},
                                 "runs": len(v["per_run"]), "dc_h": (statistics.mean(v["dc_h"]) if v["dc_h"] else None)} for row, v in bp.items()}
                    o, seps, why = outcome_of(agg, thr, metrics, model)
                    tally[o or "undecided"] += 1
                    per_design[d] = {"outcome": o, "why": why, "separations": seps, "t_d": thr, "rows": {r: {"mean": a["mean"], "runs": a["runs"], "dc_h": a["dc_h"]} for r, a in agg.items()}}
                out[key] = {"description": desc, "tally": dict(tally), "designs": per_design, "model": model, "basis": basis, "mode": mode}
    # pre-registered caliber (decided metric set: area, as the decided rule; the other metrics printed)
    pre = {}
    for basis in BASES:
        for model in models:
            tally, per_design = collections.Counter(), {}
            for d in complete:
                if decid[d]["state"].startswith("not decidable"):
                    continue
                s2 = sigmas[d]["two_sigma"]
                if sigmas[d]["source"] != "measured":
                    tally["undecided (no σ_D: pooled floor)"] += 1
                    per_design[d] = {"outcome": None, "why": "no σ_D: the design has no proven perturbation set, its floor row is the pooled minimum", "sigma_source": sigmas[d]["source"]}
                    continue
                bp_full = best_per_run(cands, runs, d, basis, "as_run")
                dc = {row: (statistics.mean(v["dc_h"]) if v["dc_h"] else None) for row, v in bp_full.items()}
                m_dc = dc.get(f"M|{model}")
                budgets = {}
                for base in ("B1_E4", "B2"):
                    b_dc = dc.get(f"{base}|{model}")
                    budgets[base] = (min(m_dc, b_dc) if (m_dc is not None and b_dc is not None) else None)
                rows_at = {}
                for base, bud in budgets.items():
                    if bud is None:
                        continue
                    bp = best_per_run(cands, runs, d, basis, "as_run", budget=bud)
                    rows_at[base] = {row: {"gm": {m: gmean_ratio([x[m] for x in v["per_run"]]) for m in METRICS},
                                          "gm_strict": {m: gmean_strict([x[m] for x in v["per_run"]]) for m in METRICS},
                                          "runs": len(v["per_run"])} for row, v in bp.items()}
                res, seps = [], {}
                for base, tab in rows_at.items():
                    m, b = tab.get(f"M|{model}"), tab.get(f"{base}|{model}")
                    if not (m and b):
                        continue
                    seps[base] = {k: (m["gm"][k] - b["gm"][k]) for k in METRICS if m["gm"].get(k) is not None and b["gm"].get(k) is not None}
                    res.append((base, seps[base]))
                if len(res) < 2:
                    tally["undecided (a row is missing)"] += 1
                    per_design[d] = {"outcome": None, "why": "a baseline row of the main model is missing", "dc_h": dc}
                    continue
                above = lambda s: any(v > float(s2.get(k) or 0.0) for k, v in s.items() if k == "area")
                below = lambda s: any(v < -float(s2.get(k) or 0.0) for k, v in s.items() if k == "area")
                if any(below(s) for _b, s in res):
                    o = "loss"
                else:
                    n = sum(int(above(s)) for _b, s in res)
                    o = "win" if n == 2 else "partial" if n == 1 else "tie"
                tally[o] += 1
                per_design[d] = {"outcome": o, "separations": seps, "two_sigma": s2, "dc_h": dc, "budgets": budgets,
                                 "gm_at_budget": {b: {r: v["gm"] for r, v in tab.items()} for b, tab in rows_at.items()},
                                 "gm_strict_at_budget": {b: {r: v["gm_strict"] for r, v in tab.items()} for b, tab in rows_at.items()}}
            pre[f"{basis}|{model}"] = {"tally": dict(tally), "designs": per_design, "model": model, "basis": basis}
    return out, pre


# ----------------------------------------------------------------------------- 3/8. arm tables
def arm_table(cfg, runs, cands, which, mat, basis="search", mode="as_run", model=None, budget=None):
    src("3 arm table", "per arm-model row over the runs of the given designs: runs done, calls (runs.llm_calls), USD (runs.spent_usd), visible DC hours (evaluations.dc_seconds of the run's candidates and their envelope "
                       "records), candidates, unusable answers (results/candidates/<run>/unusable_*.json), duplicates, inconclusive verdicts, proven, retained / trade-off by rule A at E4, best retained gain per metric per run "
                       "(mean over seeds, max), and the same counts read at the common DC budget (the smallest mean DC hours per run among the rows of the scope)")
    rows = collections.defaultdict(lambda: {"runs": 0, "runs_done": 0, "calls": 0, "usd": 0.0, "dc_h": [], "cands": 0, "unusable": 0, "duplicate": 0, "inconclusive": 0,
                                            "proven": 0, "retained": 0, "tradeoff": 0, "material": 0, "runs_with_retained": 0, "best": collections.defaultdict(list),
                                            "designs": set(), "ret_budget": [], "best_budget": collections.defaultdict(list)})
    by_run = collections.defaultdict(list)
    for c in cands:
        by_run[c["run"]].append(c)
    for r in runs:
        if r["design_id"] not in which or (model and r["llm_model"] != model):
            continue
        g = rows[r["row"]]
        g["runs"] += 1
        g["designs"].add(r["design_id"])
        if r["status"] != "done":
            continue
        g["runs_done"] += 1
        g["calls"] += int(r["llm_calls"] or 0)
        g["usd"] += float(r["spent_usd"] or 0.0)
        g["dc_h"].append(float(r["dc_h"] or 0.0))
        g["unusable"] += int(r["unusable"] or 0)
        cs = by_run.get(r["run_id"], [])
        ret = []
        for c in cs:
            if c.get("label") == "duplicate":
                g["duplicate"] += 1
                continue
            if c.get("label") == "aborted":
                continue
            g["cands"] += 1
            if c.get("verdict") == "inconclusive":
                g["inconclusive"] += 1
            if c.get("verdict") == "proven":
                g["proven"] += 1
                lab = c["lab"].get(basis, {}).get(mode)
                if lab == "retained":
                    g["retained"] += 1
                    ret.append(c)
                    up, down = C1.material(c["g"][basis].get(mode) or {}, mat)
                    g["material"] += int(bool(up) and not down)
                elif lab == "tradeoff":
                    g["tradeoff"] += 1
        g["runs_with_retained"] += int(bool(ret))
        for m in METRICS:
            g["best"][m].append(max([float(c["g"][basis][mode].get(m) or 0.0) for c in ret if c["g"][basis][mode].get(m) is not None] or [0.0]))
        if budget is not None:
            b, n = at_budget(run_curve(cs, basis, mode), budget)
            g["ret_budget"].append(n)
            for m in METRICS:
                g["best_budget"][m].append(b.get(m, 0.0))
    out = {}
    for row, g in rows.items():
        n, calls, dch = g["runs_done"], g["calls"], sum(g["dc_h"])
        out[row] = {"runs": g["runs"], "runs_done": n, "designs": len(g["designs"]), "calls": calls, "usd": round(g["usd"], 2), "dc_h": round(dch, 1),
                    "dc_h_per_run": (statistics.mean(g["dc_h"]) if g["dc_h"] else None), "cands": g["cands"], "unusable": g["unusable"], "duplicate": g["duplicate"],
                    "duplicate_share_of_candidates": rate(g["duplicate"], g["cands"] + g["duplicate"]), "duplicate_share_of_calls": rate(g["duplicate"], calls),
                    "inconclusive": g["inconclusive"], "proven": g["proven"], "retained": g["retained"], "tradeoff": g["tradeoff"], "material": g["material"],
                    "candidates_per_call": rate(g["cands"] + g["duplicate"], calls), "proven_per_call": rate(g["proven"], calls), "retained_per_call": rate(g["retained"], calls),
                    "retained_per_run": rate(g["retained"], n), "runs_with_retained": g["runs_with_retained"], "share_runs_with_retained": rate(g["runs_with_retained"], n),
                    "retained_per_100_calls": (100.0 * g["retained"] / calls) if calls else None, "retained_per_usd": rate(g["retained"], g["usd"]) if g["usd"] else None,
                    "retained_per_dc_hour": rate(g["retained"], dch) if dch else None,
                    "best_mean": {m: (statistics.mean(v) if v else None) for m, v in g["best"].items()},
                    "best_max": {m: (max(v) if v else None) for m, v in g["best"].items()},
                    "at_budget": ({"budget_h": budget, "retained_per_run": (statistics.mean(g["ret_budget"]) if g["ret_budget"] else None),
                                   "retained_per_dc_hour": (rate(sum(g["ret_budget"]), budget * n) if budget and n else None),
                                   "best_mean": {m: (statistics.mean(v) if v else None) for m, v in g["best_budget"].items()}} if budget is not None else None)}
    return out


# ----------------------------------------------------------------------------- 4. duplicates and archive
def section_duplicates(cfg, conn, runs, cands, complete):
    src("4 duplicates", "candidates with label 'duplicate' (the run detected the same rewrite again: an identical E4 fingerprint of an earlier candidate of the same run, diagnoses.duplicate_of) against the run's calls; "
                        "archive size per generation from gen_summary.archive_json (members); the correlation is Pearson's r over (run, generation) pairs between the archive size at a build and the duplicate share of the "
                        "candidates issued in that generation")
    gen_of = {r[0]: r[1] for r in conn.execute("SELECT cand_id, gen FROM candidates")}
    dup_of = {r[0]: r[1] for r in conn.execute("SELECT cand_id, duplicate_of FROM diagnoses WHERE duplicate_of IS NOT NULL")}
    per_row = collections.defaultdict(lambda: {"cands": 0, "duplicate": 0, "calls": 0, "earlier_gen": 0, "same_gen": 0, "unknown": 0})
    per_row_design = collections.defaultdict(lambda: collections.defaultdict(lambda: {"cands": 0, "duplicate": 0}))
    for r in runs:
        if r["design_id"] in complete and r["status"] == "done":
            per_row[r["row"]]["calls"] += int(r["llm_calls"] or 0)
    for c in cands:
        if c["design_id"] not in complete:
            continue
        g, gd = per_row[c["row"]], per_row_design[c["row"]][c["design_id"]]
        g["cands"] += 1
        gd["cands"] += 1
        if c.get("label") == "duplicate":
            g["duplicate"] += 1
            gd["duplicate"] += 1
            src_id = dup_of.get(c["cand_id"])
            g0, g1 = gen_of.get(src_id), int(c.get("gen") or 0)
            g["earlier_gen" if (g0 is not None and g0 < g1) else "same_gen" if g0 == g1 else "unknown"] += 1
    arch = collections.defaultdict(list)
    pairs = collections.defaultdict(list)
    gen_cands = collections.defaultdict(lambda: [0, 0])
    for c in cands:
        if c["design_id"] in complete:
            k = (c["run"], int(c.get("gen") or 0))
            gen_cands[k][0] += 1
            gen_cands[k][1] += int(c.get("label") == "duplicate")
    run_row = {r["run_id"]: r["row"] for r in runs}
    for rid, gen, aj in conn.execute("SELECT g.run_id, g.gen, g.archive_json FROM gen_summary g JOIN runs r ON r.run_id=g.run_id WHERE r.exp='phase5' AND r.status!='superseded' AND COALESCE(r.excluded_from_tables,0)=0"):
        if rid not in run_row:
            continue
        try:
            n = len((json.loads(aj or "{}") or {}).get("members") or [])
        except (ValueError, TypeError):
            continue
        row = run_row[rid]
        arch[row].append(n)
        tot, dup = gen_cands.get((rid, gen), [0, 0])
        if tot:
            pairs[row].append((n, dup / tot))
            pairs["ALL"].append((n, dup / tot))
            pairs["M" if row.startswith("M|") else "baselines"].append((n, dup / tot))
    def pearson(xy):
        if len(xy) < 3:
            return None
        xs, ys = [p[0] for p in xy], [p[1] for p in xy]
        mx, my = statistics.mean(xs), statistics.mean(ys)
        sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
        if not sx or not sy:
            return None
        return sum((x - mx) * (y - my) for x, y in xy) / (len(xy) * sx * sy)
    return {"rows": {row: dict(g, duplicate_share_of_candidates=rate(g["duplicate"], g["cands"]), duplicate_share_of_calls=rate(g["duplicate"], g["calls"]),
                               archive_mean=(statistics.mean(arch[row]) if arch.get(row) else None), archive_max=(max(arch[row]) if arch.get(row) else None),
                               correlation_archive_vs_duplicate=pearson(pairs.get(row, [])), n_generation_builds=len(pairs.get(row, [])))
                     for row, g in per_row.items()},
            "per_design": {row: {d: dict(v, share=rate(v["duplicate"], v["cands"])) for d, v in sorted(dd.items())} for row, dd in per_row_design.items()},
            "correlation_all": pearson(pairs.get("ALL", [])), "correlation_M": pearson(pairs.get("M", [])), "correlation_baselines": pearson(pairs.get("baselines", [])),
            "archive_rule": "M admits a candidate to the archive only when rule A labels it retained (src/search/driver.py: `if label == 'retained' ...archive.add`); the scalar arms admit any candidate with a positive "
                            "component of their fitness (`scalar_improved`: any gain > 0), so their archives fill faster"}


# ----------------------------------------------------------------------------- 5. failure forensics
def section_failures(cfg, conn, cands, designs=("drrtl_arm_cpu2", "cktevo_hsm__hsm")):
    src("5 failure forensics", "candidates.verdict per arm (rejected = V1, sim_fail = V2, falsified = V3, inconclusive = SEQ inconclusive) and the equivalence records under results/raw/<design>/EQ/*/equiv.json: v1_detail for the "
                               "V1 rejections, v2_detail ({signal: {c, d, first_cycle}}) for the lock-step mismatches; the D-vs-D record is the run of REQUEST (e) item 2 (d_saif group: c_rtl = d_rtl, same harness, same stimulus)")
    out = {}
    for d in designs:
        cs = [c for c in cands if c["design_id"] == d]
        cids = {c["cand_id"] for c in cs}
        by_arm = collections.defaultdict(collections.Counter)
        for c in cs:
            by_arm[c["arm"]][c.get("verdict") or "(none)"] += 1
        sig, cyc, v1 = collections.Counter(), [], collections.Counter()
        n_rec = 0
        dvd = []
        for f in glob.glob(os.path.join(C.results_dir(cfg), "raw", d, "EQ", "*", "equiv.json")):
            try:
                r = json.load(open(f))
            except (OSError, ValueError):
                continue
            if r.get("cand_id") not in cids:
                if r.get("cand_id") is None:
                    dvd.append({"verdict": r.get("verdict"), "v1": r.get("v1_status"), "v2": r.get("v2_status"), "cycles": r.get("v2_cycles"), "seed": r.get("sim_seed"), "harness_version": r.get("harness_version")})
                continue
            n_rec += 1
            if r.get("v1_status") and r["v1_status"] != "ok":
                v1[str(r.get("v1_detail") or r["v1_status"])[:70]] += 1
            try:
                det = json.loads(r.get("v2_detail") or "{}")
            except (ValueError, TypeError):
                det = {}
            if isinstance(det, dict) and det:
                fc = [v.get("first_cycle") for v in det.values() if isinstance(v, dict) and v.get("first_cycle") is not None]
                if fc:
                    cyc.append(min(fc))
                for s in det:
                    sig[s] += 1
        out[d] = {"candidates": len(cs), "by_arm": {a: dict(v) for a, v in by_arm.items()}, "verdicts": dict(collections.Counter(c.get("verdict") or "(none)" for c in cs)),
                  "records": n_rec, "top_signals": sig.most_common(3), "v1_top": v1.most_common(3),
                  "first_mismatch_cycle": {"n": len(cyc), "min": (min(cyc) if cyc else None), "median": (statistics.median(cyc) if cyc else None), "max": (max(cyc) if cyc else None),
                                           "le_10": sum(1 for x in cyc if x <= 10), "le_100": sum(1 for x in cyc if x <= 100)},
                  "d_vs_d": dvd, "sim_settings": {"random_cycles": cfg["sim"]["random_cycles"], "seed": cfg["sim"]["seed"], "reset_cycles": cfg["sim"]["reset_cycles"]}}
    return out


# ----------------------------------------------------------------------------- 6/7. mechanism and per design
def section_mechanism(cfg, conn, runs, cands, complete):
    src("mechanism", "over the candidates of the complete designs (duplicates and aborted rows excluded, as in the retention counts): the rule-A fate of the proven ones, the parent of every candidate (candidates.parent_id "
                     "NULL = D itself), the generation of each retained candidate, and — for M only — whether a verdict-derived feedback (a candidate of the SAME run and design diagnosed absorbed / noise / harmful) preceded it "
                     "in an earlier generation; unverified-at-build from gen_summary.pending_json (src.jobqueue.core.unverified_at_build)")
    by_row = collections.defaultdict(lambda: {"proven": 0, "fate": collections.Counter(), "retained_gen": collections.Counter(), "retained": 0, "calls": 0,
                                              "parents_d": 0, "parents_archive": 0, "counted": 0, "with_feedback": 0})
    for r in runs:
        if r["design_id"] in complete and r["status"] == "done":
            by_row[r["row"]]["calls"] += int(r["llm_calls"] or 0)
    diag_earlier = collections.defaultdict(list)
    for c in cands:
        if c["design_id"] not in complete or c.get("label") in ("duplicate", "aborted"):
            continue
        g = by_row[c["row"]]
        g["counted"] += 1
        g["parents_archive" if c.get("parent_id") else "parents_d"] += 1
        lab = c["lab"]["search"].get("as_run")
        if c.get("verdict") == "proven" and lab:
            g["proven"] += 1
            g["fate"][lab] += 1
            if lab in ("absorbed", "absorbed_identical", "noise", "harmful"):
                diag_earlier[c["run"]].append(int(c.get("gen") or 0))
            if lab == "retained":
                g["retained"] += 1
                g["retained_gen"][int(c.get("gen") or 0)] += 1
    for c in cands:
        if (c["design_id"] in complete and c["arm"] == "M" and c.get("label") not in ("duplicate", "aborted")
                and c["lab"]["search"].get("as_run") == "retained" and any(g < int(c.get("gen") or 0) for g in diag_earlier.get(c["run"], []))):
            by_row[c["row"]]["with_feedback"] += 1
    from src.jobqueue.core import unverified_at_build
    unv = {}
    for t in ("large", "medium", "small"):
        try:
            unv[t] = unverified_at_build(conn, cfg, minutes=10 ** 7, tier=t, by="row")
        except Exception as e:
            unv[t] = f"{type(e).__name__}: {e}"[:80]
    out = {"rows": {}, "unverified_at_build_by_tier_row": unv,
           "feedback_scope": "the feedback and the retained candidate are always in the same run, hence on the same design and with the same arm and model; only generations strictly earlier than the retained candidate's count"}
    for row, g in by_row.items():
        tot = sum(g["fate"].values())
        first = g["retained_gen"].get(1, 0)
        out["rows"][row] = {"counted_candidates": g["counted"], "proven": g["proven"], "fate": dict(g["fate"]), "fate_share": {k: rate(v, tot) for k, v in g["fate"].items()},
                            "calls": g["calls"], "calls_per_retained": (g["calls"] / g["retained"]) if g["retained"] else None,
                            "parents_D": g["parents_d"], "parents_archived": g["parents_archive"], "parent_denominator": g["counted"],
                            "share_parent_D": rate(g["parents_d"], g["counted"]), "retained": g["retained"], "retained_gen1": first, "retained_later": g["retained"] - first,
                            "share_retained_gen1": rate(first, g["retained"]),
                            "retained_after_verdict_feedback": (g["with_feedback"] if row.startswith("M|") else None),
                            "share_retained_after_verdict_feedback": (rate(g["with_feedback"], g["retained"]) if row.startswith("M|") else None)}
    return out


def section_designs(cfg, conn, runs, cands, dcache, tal, complete, tier_of, default_basis, sigmas, decid):
    src("7 per design", "per design: tier, family, floor class and t_D per metric (frozen phase4 table), σ_D, the power basis of D's E4 baseline, the proven rate, each row's best retained gain per metric (mean over seeds and "
                        "max) on both power bases, the outcome, and the class and evidence tags of the retained candidates that decided it")
    ma = cfg["exp5"].get("model_assignment") or {}
    out = {}
    for d in complete:
        model = (ma.get(tier_of.get(d)) or {}).get("all_arms") or cfg["llm"]["selected"]
        dd = dcache["search"].get(d)
        cs = [c for c in cands if c["design_id"] == d and c.get("label") not in ("duplicate", "aborted")]
        prov = sum(1 for c in cs if c.get("verdict") == "proven")
        best = {}
        for basis in BASES:
            info = (tal[f"{basis}|{model}|decided"]["designs"].get(d) or {})
            best[basis] = {"outcome": info.get("outcome"), "rows": {r: v["mean"] for r, v in (info.get("rows") or {}).items()}}
        deciders = []
        for c in sorted([c for c in cs if c["row"] == f"M|{model}" and c["lab"]["search"].get("as_run") == "retained"], key=lambda x: -(x["g"]["search"]["as_run"].get("area") or 0.0))[:3]:
            deciders.append({"cand_id": c["cand_id"], "class": c.get("class_final"), "tags": c["tags"][:2], "area": c["g"]["search"]["as_run"].get("area"), "gen": c.get("gen")})
        out[d] = {"tier": tier_of.get(d), "family": C1.family(d), "model": model, "floor_class": (dd or {}).get("floor_class"), "t_d": (dd or {}).get("thresholds"),
                  "sigma": sigmas[d]["sigma"], "sigma_source": sigmas[d]["source"], "power_basis": ("default" if d in default_basis else "saif"),
                  "candidates": len(cs), "proven": prov, "proven_rate": rate(prov, len(cs)), "state": decid[d]["state"], "note": decid[d]["note"],
                  "best": best, "deciders": deciders,
                  "outcome_changes_with_saif": (best["search"]["outcome"] != best["offline_saif"]["outcome"])}
    return out


# ----------------------------------------------------------------------------- render
def render(data):
    v, mat = data["versions"], data["materiality"]
    main_models = data["rows"]["main_model"]
    L = [f"# C2 interim evidence report v2 — {data['date']} (visible layer only; interim)", "",
         f"Generated {data['generated_at']} by scripts/report_c2.py (git {v['git_sha']}, cfg {v['cfg_hash']}); floor_version **{v['floor_version']}**, equiv_version {v['equiv_version']}, harness_version {v['harness_version']}; "
         f"equal LLM calls ({v['calls_per_run']} per run), rule A at E4 with each design's frozen floor, per-metric verdicts; materiality area > {pct(mat['area'], 0)}, power > {pct(mat['power'], 0)}, WNS > {pct(mat['wns'], 0)}. "
         f"Main model per tier: large {main_models.get('large')}, medium {main_models.get('medium')}, small {main_models.get('small')}; the other model is reported as the contrast and never mixed into a tally. "
         f"No record, default or configuration was altered; results/hidden was not read. Data: reports/data/c2_interim.json.", ""]
    L += ["## 0. Plain-language summary", ""] + data["summary"] + [""]
    # 1
    c = data["completion"]
    L += ["## 1. Completion state and row completeness", "",
          f"Complete designs {len(c['complete'])}, B0 pending {len(c['preliminary'])}, incomplete {len(c['incomplete'])} of {data['reachability']['designs_total']} planned designs. "
          f"Designs with every main-model row complete: **{data['rows']['n_all_main_complete']}**.", "",
          "| design | tier | state | main model | main rows complete | missing main rows | runs done / planned | pending candidates | B0 offline E4 |", "|---|---|---|---|---|---|---|---|---|"]
    for d, e in data["completion"]["designs"].items():
        rc = data["rows"]["designs"].get(d) or {}
        miss = ", ".join(rc.get("missing_main_rows") or []) or "—"
        L.append(f"| {d} | {e['tier']} | {e['state']} | {rc.get('main_model')} | {rc.get('main_rows_complete')} of {rc.get('main_rows')} | {miss} | {e['done']} / {e['planned']} | "
                 f"{(e['blockers'].get('verdict', 0) + e['blockers'].get('sim', 0) + e['blockers'].get('failed_job', 0)) or ('0' if e['state'] != 'incomplete' else 'pending')} | {e['b0_e4'] or 0} |")
    L += ["", "Rows complete per tier (arm-model row: designs with that row complete of the designs that plan it):", ""]
    for t, e in data["rows"]["per_tier"].items():
        L.append(f"- **{t}** ({e['designs']} designs): " + ", ".join(f"{row} {n} / {tot}" for row, (n, tot) in e["rows_complete"].items()))
    L += ["", "## 2. Decidability of the complete designs", "", "| design | state | candidates | proven | retained | note |", "|---|---|---|---|---|---|"]
    for d, e in data["decidability"].items():
        L.append(f"| {d} | {e['state']} | {e['candidates']} | {e['proven']} | {e['retained']} | {e['note'] or '—'} |")
    L += ["", f"Designs excluded from every tally's denominator (no arm produced a proven candidate): {data['excluded_designs'] or 'none'}. "
          f"Designs where every arm reaches the same best retained gain: {data['identical_designs'] or 'none'}. Decidable designs: {data['decidable']}.", ""]
    # 3 criterion
    cr = data["criterion"]
    L += ["## 3. The pre-registered criterion", "", f"Verbatim ({cr['criterion_source']}):", "", f"> {cr['criterion_text']}", "", cr["reachability"]["note"], ""]
    sec = 0
    for basis in BASES:
        for model in data["models"]:
            key = f"{basis}|{model}"
            if key not in data["pre_registered"]:
                continue
            pr = data["pre_registered"][key]
            tiers_main = [t for t, m in main_models.items() if m == model]
            role = ("the tier plan's all-arms model in " + ", ".join(tiers_main) if tiers_main else "contrast model") +                    ("; this report's main model" if model == data["headline_model"] else "; reported as the contrast, never mixed into another model's tally")
            sec += 1
            L += [f"### 3.{sec} {basis} basis, {model} ({role})", "",
                  "**(a) visible-layer proxy, mean-of-best, t_D separation** — " + "; ".join(f"{mode}: " + ", ".join(f"{k} {n}" for k, n in sorted(data['tallies'][f'{basis}|{model}|{mode}']['tally'].items())) for mode, _lm, _ms, _d in MODES), "",
                  "**(b) pre-registered caliber** (geometric mean of the gain ratios over seeds, 2 σ_D separation, read at the smaller of M's and the baseline's mean visible DC hours per run): "
                  + ", ".join(f"{k} {n}" for k, n in sorted(pr["tally"].items())), "",
                  "| design | σ_D area (2 σ_D) | M / B1_E4 / B2 DC h per run | budget h (B1 / B2) | gm area M / B1_E4 / B2 | outcome (b) | outcome (a, decided rule) |", "|---|---|---|---|---|---|---|"]
            for d, e in pr["designs"].items():
                a = data["tallies"][f"{basis}|{model}|decided"]["designs"].get(d) or {}
                if e.get("outcome") is None and e.get("why"):
                    L.append(f"| {d} | — | — | — | — | undecided: {e['why']} | {a.get('outcome') or 'undecided'} |")
                    continue
                dc = e.get("dc_h") or {}
                gm = (e.get("gm_at_budget") or {}).get("B1_E4") or {}
                f = lambda row: pct((gm.get(f"{row}|{model}") or {}).get("area"), 2)
                s_area = data["designs"][d]["sigma"].get("area")
                zero = " (σ_D = 0: quiet floor class, so any non-zero separation decides in this caliber)" if (s_area is not None and float(s_area) == 0.0) else ""
                L.append(f"| {d} | {pct(s_area, 3)}{zero} ({pct((e.get('two_sigma') or {}).get('area'), 3)}) | "
                         f"{num(dc.get(f'M|{model}'))} / {num(dc.get(f'B1_E4|{model}'))} / {num(dc.get(f'B2|{model}'))} | "
                         f"{num((e.get('budgets') or {}).get('B1_E4'))} / {num((e.get('budgets') or {}).get('B2'))} | {f('M')} / {f('B1_E4')} / {f('B2')} | **{e['outcome']}** | {a.get('outcome') or 'undecided'} |")
            L.append("")
    r = cr["reachability"]
    L += [f"**Reachability** ({r['tally_basis']}): {r['decided']} of {r['designs_total']} designs decidable and decided, wins so far {r['wins_so_far']}, wins needed {r['wins_needed']} (60 % of {r['designs_total']}), "
          f"designs still open {r['wins_still_available']}; arithmetically reachable: {'yes' if r['reachable'] else 'no'}.", ""]
    if cr["decided_differently"]:
        L += ["Designs decided differently by the readings (main model, search basis):", ""] + [f"- {d}: " + ", ".join(f"{k} {vv or 'undecided'}" for k, vv in o.items()) for d, o in cr["decided_differently"].items()] + [""]
    if data["saif_changes"]:
        L += ["Designs whose outcome changes when the offline SAIF baselines replace the search basis: " + ", ".join(data["saif_changes"]) + ".", ""]
    else:
        L += ["No design's outcome changes when the offline SAIF baselines replace the search basis.", ""]
    # 4 arm tables
    L += ["## 4. Arm comparison on the decidable complete designs (equal calls and equal DC hours)", ""]
    for scope, tab in data["arms"].items():
        if not tab["rows"]:
            continue
        L += [f"### {scope} (n = {tab['n_designs']} designs, {tab['model']}; common DC budget {num(tab['budget_h'])} h per run)", "",
              "| row | runs | calls | cand/call | proven/call | retained/call | retained | retained/run | runs with ≥ 1 | best area mean (max) | best power | best WNS | retained/100 calls | retained/USD | retained/DC h | DC h/run | at equal DC: retained/run | at equal DC: best area | at equal DC: retained/DC h |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for row in sorted(tab["rows"], key=lambda k: (ARMS.index(k.split("|")[0]) if k.split("|")[0] in ARMS else 9, k)):
            e = tab["rows"][row]
            ab = e.get("at_budget") or {}
            L.append(f"| {row} | {e['runs_done']} of {e['runs']} | {e['calls']} | {num(e['candidates_per_call'], 3)} | {num(e['proven_per_call'], 3)} | {num(e['retained_per_call'], 3)} | {e['retained']} ({e['material']}) | "
                     f"{num(e['retained_per_run'])} | {e['runs_with_retained']} | {pct(e['best_mean']['area'], 2)} ({pct(e['best_max']['area'], 2)}) | {pct(e['best_mean']['power'], 2)} | {pct(e['best_mean']['wns'], 2)} | "
                     f"{num(e['retained_per_100_calls'])} | {num(e['retained_per_usd'])} | {num(e['retained_per_dc_hour'])} | {num(e['dc_h_per_run'])} | {num(ab.get('retained_per_run'))} | {pct((ab.get('best_mean') or {}).get('area'), 2)} | {num(ab.get('retained_per_dc_hour'))} |")
        L.append("")
    L += [data["arms_note"], ""]
    # 5 duplicates
    du = data["duplicates"]
    L += ["## 5. Duplicates and the archive", "", "| row | candidates | duplicates | share of candidates | share of calls | of which: earlier generation | same generation | archive mean (max) | r(archive size, duplicate share of the generation) | generation builds |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for row in sorted(du["rows"], key=lambda k: (ARMS.index(k.split("|")[0]) if k.split("|")[0] in ARMS else 9, k)):
        e = du["rows"][row]
        L.append(f"| {row} | {e['cands']} | {e['duplicate']} | {pct(e['duplicate_share_of_candidates'])} | {pct(e['duplicate_share_of_calls'])} | {e['earlier_gen']} | {e['same_gen']} | "
                 f"{num(e['archive_mean'])} ({e['archive_max'] if e['archive_max'] is not None else 'pending'}) | {num(e['correlation_archive_vs_duplicate'])} | {e['n_generation_builds']} |")
    L += ["", "Every candidate row corresponds to one LLM call, so the duplicate share of the candidates and of the calls coincide except where a call produced no candidate row (an unusable answer).", "",
          f"{du['archive_rule']}. Correlation across all (run, generation) pairs: r = {num(du['correlation_all'])}; M rows only r = {num(du['correlation_M'])}; baseline rows r = {num(du['correlation_baselines'])} "
          f"(Pearson, archive size at the build against the duplicate share of the candidates issued in that generation).", ""]
    # 6 failures
    L += ["## 6. Designs where no arm produced a proven candidate", ""]
    for d, e in data["failures"].items():
        fm = e["first_mismatch_cycle"]
        L += [f"### {d} — {e['candidates']} candidates, verdicts " + ", ".join(f"{k} {n}" for k, n in sorted(e["verdicts"].items(), key=lambda kv: -kv[1])), "",
              "| arm | " + " | ".join(sorted({k for v in e["by_arm"].values() for k in v})) + " |", "|---|" + "---|" * len({k for v in e["by_arm"].values() for k in v})]
        keys = sorted({k for v in e["by_arm"].values() for k in v})
        for arm, v in sorted(e["by_arm"].items()):
            L.append(f"| {arm} | " + " | ".join(str(v.get(k, 0)) for k in keys) + " |")
        L += ["", f"Lock-step mismatches: {fm['n']} records with a mismatch; first mismatch cycle min {fm['min']}, median {fm['median']}, max {fm['max']} ({fm['le_10']} at cycle ≤ 10, {fm['le_100']} at ≤ 100). "
              f"Most frequent mismatching signals: " + ", ".join(f"{s} ({n})" for s, n in e["top_signals"]) + ".", "",
              "Most frequent V1 rejections: " + "; ".join(f"{t} ({n})" for t, n in e["v1_top"]) + ".", "",
              f"D-vs-D self-check (REQUEST (e) item 2, the same harness, the same stimulus: {e['sim_settings']['random_cycles']} random cycles after {e['sim_settings']['reset_cycles']} reset cycles, seed {e['sim_settings']['seed']}): "
              + ("; ".join(f"verdict {x['verdict']}, V1 {x['v1']}, V2 {x['v2']}, {x['cycles']} cycles, seed {x['seed']}, harness_version {x['harness_version']}" for x in e["d_vs_d"]) or "no record") + ".", ""]
    # 7 mechanism
    mech = data["mechanism"]
    L += ["## 7. Mechanism evidence (decidable complete designs)", "", "| row | candidates counted | proven | retained | trade-off | absorbed_identical | absorbed | noise | harmful | calls per retained | parents = D (of counted) | parents archived | retained in gen 1 | retained later | retained after a verdict feedback (M) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in sorted(mech["rows"], key=lambda k: (ARMS.index(k.split("|")[0]) if k.split("|")[0] in ARMS else 9, k)):
        e = mech["rows"][row]
        f = e["fate"]
        sh = lambda k: f"{f.get(k, 0)} = {pct(e['fate_share'].get(k))}" if f.get(k) else "0"
        L.append(f"| {row} | {e['counted_candidates']} | {e['proven']} | {sh('retained')} | {sh('tradeoff')} | {sh('absorbed_identical')} | {sh('absorbed')} | {sh('noise')} | {sh('harmful')} | {num(e['calls_per_retained'])} | "
                 f"{e['parents_D']} of {e['parent_denominator']} = {pct(e['share_parent_D'])} | {e['parents_archived']} | {e['retained_gen1']} = {pct(e['share_retained_gen1'])} | {e['retained_later']} | "
                 f"{(str(e['retained_after_verdict_feedback']) + ' = ' + pct(e['share_retained_after_verdict_feedback'])) if e['retained_after_verdict_feedback'] is not None else '—'} |")
    L += ["", f"Scope of the feedback column: {mech['feedback_scope']}.", "",
          "Unverified-at-build per tier and row: " + "; ".join((f"{t}: " + ", ".join(f"{k} {pct(vv)}" for k, vv in sorted(x.items()))) if isinstance(x, dict) else f"{t}: {x}" for t, x in mech["unverified_at_build_by_tier_row"].items()), ""]
    # 8 latency bound
    pb = data["latency_bound"]
    L += ["## 8. Proof-latency-bound designs", "", f"Designs whose median proof latency exceeds the {pb['window_s']} s generation window (DECISION 2026-09-19 (k) 3): {len(pb['designs'])}.", "",
          "| design | tier | median proof latency (min) | proofs measured | empty-archive builds | proven candidates | reading |", "|---|---|---|---|---|---|---|"]
    for d, e in pb["designs"].items():
        L.append(f"| {d} | {e['tier']} | {num(e['median_min'], 0)} | {e['n_proofs']} | {e['empty']} | {e['proven']} | {e['reading']} |")
    t2, t3 = pb["tally_excluding"], pb["tally_excluding_as_run"]
    L += ["", f"Tally on the decidable designs with these excluded ({pb['n_after']} designs), decided rule: " + ", ".join(f"{k} {n}" for k, n in sorted(t2.items()))
          + "; any-metric reading: " + ", ".join(f"{k} {n}" for k, n in sorted(t3.items())) + ".", ""]
    # 9 per design
    L += ["## 9. Per-design detail (complete designs; both power bases)", "", "| design | tier | family | state | floor class | t_D area / power / WNS | σ_D area | power basis | candidates | proven | outcome (search) | outcome (SAIF) | M best area (search) | B1_E4 | B2 | deciding retained candidates |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d, e in data["designs"].items():
        model = e["model"]
        g = lambda basis, row: pct((e["best"][basis]["rows"].get(f"{row}|{model}") or {}).get("area"), 2)
        dec = "; ".join(f"{x['class']} ({', '.join(x['tags']) or 'no tag'}, gen {x['gen']}, area {pct(x['area'], 2)})" for x in e["deciders"]) or "none"
        L.append(f"| {d} | {e['tier']} | {e['family']} | {e['state']} | {e['floor_class'] or 'pooled'} | {' / '.join(pct((e['t_d'] or {}).get(m), 2) for m in METRICS)} | "
                 f"{pct(e['sigma'].get('area'), 3) if e['sigma_source'] == 'measured' else 'no σ_D (pooled)'} | {e['power_basis']} | {e['candidates']} | {e['proven']} = {pct(e['proven_rate'])} | "
                 f"{e['best']['search']['outcome'] or 'undecided'} | {e['best']['offline_saif']['outcome'] or 'undecided'} | {g('search', 'M')} | {g('search', 'B1_E4')} | {g('search', 'B2')} | {dec} |")
    L += ["", "## 10. What is still missing for C2", ""] + [f"- **{x['item']}** — {x['detail']} (owner: {x['owner']}; stage: {x['stage']})" for x in data["missing"]] + [""]
    L += ["## S. Sources", ""] + [f"- **{k}**: {t}" for k, t in data["sources"].items()] + [""]
    return "\n".join(L)


def summary_lines(data):
    cr = data["criterion"]
    r = cr["reachability"]
    main = data["main_model_headline"]
    pooled = (data["arms"].get(data["headline_scope"]) or {}).get("rows") or {}
    order = sorted(((k, v["retained_per_run"] or 0.0) for k, v in pooled.items()), key=lambda kv: -kv[1])
    L = [
        f"1. {len(data['completion']['complete'])} designs are complete and {len(data['completion']['preliminary'])} are complete except B0's offline E4; {data['rows']['n_all_main_complete']} have every row of their own "
        f"tier's all-arms model complete, and {len(data['decidable_under_model'].get(data['headline_model']) or [])} design(s) have the three comparison rows (M, B1_E4, B2) complete under {data['headline_model']}.",
        main,
        f"3. Excluded by construction (no arm produced a proven candidate): {', '.join(data['excluded_designs']) or 'none'}. All arms identical: {', '.join(data['identical_designs']) or 'none'}. "
        f"Decidable designs: {', '.join(data['decidable']) or 'none'}.",
        f"4. Pre-registered caliber (geometric mean over seeds, 2 σ_D, equal visible DC hours), main-model rows: "
        + "; ".join(f"{k} {n}" for k, n in sorted((data['pre_registered'].get(data['headline_pre_key']) or {"tally": {}})['tally'].items())) + ".",
        f"5. σ_D exists (a measured perturbation set) on {data['sigma_measured']} of the 30 designs; on the other {30 - data['sigma_measured']} the floor row is the pooled minimum, so the pre-registered separation cannot be "
        f"formed and the design stays undecided in that caliber.",
        f"6. Reachability: {r['wins_needed']} wins needed (60 % of {r['designs_total']}), {r['wins_so_far']} in, {r['wins_still_available']} designs still open — arithmetically {'reachable' if r['reachable'] else 'not reachable'}.",
        f"7. At equal calls on the decidable designs, retained per run: " + (", ".join(f"{k} {num(v)}" for k, v in order[:4]) if order else "pending") + ".",
        f"8. Duplicate answers consume " + ", ".join(f"{k} {pct(v['duplicate_share_of_calls'])}" for k, v in sorted(data['duplicates']['rows'].items()) if k.startswith('M|'))
        + " of M's calls on the decidable designs, against " + ", ".join(f"{k} {pct(v['duplicate_share_of_calls'])}" for k, v in sorted(data['duplicates']['rows'].items()) if not k.startswith('M|')) + ".",
        f"9. M's archive holds {num((data['duplicates']['rows'].get(data['headline_m_row']) or {}).get('archive_mean'))} members at a generation build against 2.3–2.6 for the baselines; the correlation between archive size and the "
        f"duplicate share of the next generation is r = {num(data['duplicates']['correlation_M'])} for M rows and {num(data['duplicates']['correlation_baselines'])} for the baselines.",
        f"10. C2 cannot yet say anything about the hidden configurations (sealed), the small tier (no completed run) or the Phase 6 ablations (not run); the three things that would change the picture most are the remaining "
        f"medium designs ({len(data['completion']['incomplete'])} open), the proofs of the {data['prescreened_all']} prescreened candidates, and the hidden-configuration evaluation.",
    ]
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    tier_of = P5.tier_of_design(cfg)
    dcache = {"search": P5._Designs(cfg, conn), "offline_saif": P5._Designs(cfg, conn, basis="offline_saif")}
    mat = {"area": cfg["noise"]["materiality"]["area"], "power": cfg["noise"]["materiality"]["power_saif"], "wns": cfg["noise"]["materiality"]["wns"]}
    default_basis = P5.default_power_basis_designs(cfg, conn)
    cd = P5.complete_designs(cfg, conn)
    complete = cd["complete"] + cd["preliminary"]
    held = [d for ds in cfg["exp5"]["starting_points"].values() for d in ds]
    runs, cands = scan(cfg, conn, dcache, set(complete))
    models = sorted({r["llm_model"] for r in runs})
    data = {"date": a.date, "generated_at": datetime.datetime.now().isoformat(timespec="minutes"), "materiality": mat, "default_power_basis": default_basis, "models": models,
            "versions": {"git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(), "floor_version": cfg["noise"]["floor_version"], "equiv_version": cfg["equiv"].get("version"),
                         "harness_version": cfg["equiv"].get("harness_version"), "calls_per_run": cfg["scale"]["budget"]["llm_calls_per_run"]}}
    # 1 completion and rows
    view = P5.completion_view(cfg, conn)
    comp = {"designs": {}, "complete": cd["complete"], "preliminary": cd["preliminary"]}
    for d in sorted(cd["rows"], key=lambda x: ({"large": 0, "medium": 1, "small": 2}.get(tier_of.get(x), 3), x)):
        st = collections.Counter(r[0] for r in conn.execute("SELECT status FROM runs WHERE exp='phase5' AND design_id=? AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0", (d,)))
        bl = cd["blockers"].get(d) or {}
        comp["designs"][d] = {"tier": tier_of.get(d), "planned": sum(v["planned"] for v in cd["rows"][d].values()), "done": sum(v["done"] for v in cd["rows"][d].values()),
                              "running": st.get("running", 0), "queued": st.get("created", 0), "blockers": bl,
                              "state": ("complete" if d in cd["complete"] else "B0 pending" if d in cd["preliminary"] else "incomplete"),
                              "b0_e4": bl.get("b0_e4", 0)}
    comp["incomplete"] = [d for d, e in comp["designs"].items() if e["state"] == "incomplete"]
    data["completion"] = comp
    data["rows"] = row_completeness(cfg, conn, cd, tier_of)
    data["rows"]["n_all_main_complete"] = sum(1 for e in data["rows"]["designs"].values() if e["all_main_complete"])
    # 2 decidability
    decid = decidability(cands, complete, tier_of)
    data["decidability"] = decid
    data["excluded_designs"] = [d for d, e in decid.items() if e["state"].startswith("not decidable")]
    data["identical_designs"] = [d for d, e in decid.items() if e["state"] == "all arms identical"]
    data["decidable"] = [d for d, e in decid.items() if e["state"] != "not decidable: no arm produced a proven candidate"]
    sigmas = sigma_table(conn, cfg, held)
    data["sigma_measured"] = sum(1 for d in held if sigmas[d]["source"] == "measured")
    # 3 tallies, both bases and both models
    tal, pre = tallies(cfg, conn, runs, cands, dcache, complete, tier_of, sigmas, decid, default_basis)
    data["tallies"], data["pre_registered"] = tal, pre
    # which designs are decidable under which model (the three comparison rows complete)
    need_rows = ("M", "B1_E4", "B2")
    dec_under = {}
    for model in models:
        ds = []
        for d in data["decidable"]:
            rows = data["rows"]["designs"][d]["rows"]
            if all(rows.get(f"{arm}|{model}", {}).get("complete") for arm in need_rows):
                ds.append(d)
        dec_under[model] = ds
    data["decidable_under_model"] = dec_under
    main_model_large = data["rows"]["main_model"].get("large")
    headline_model = main_model_large
    data["headline_model"] = headline_model
    data["headline_pre_key"] = f"search|{headline_model}"
    data["headline_m_row"] = f"M|{headline_model}"
    t_dec = tal[f"search|{headline_model}|decided"]["tally"]
    proto = (f"In the medium and small tiers the plan assigns {headline_model} only to M and B2 (config exp5.model_assignment.<tier>.second), so B0-{headline_model.split('-')[-1]}, "
             f"B1_E4-{headline_model.split('-')[-1]} and DrRTL_reimpl-{headline_model.split('-')[-1]} have no planned runs there at all; only the large tier runs every arm with {headline_model}.")
    if not dec_under.get(headline_model):
        data["main_model_headline"] = f"2. **No design is decidable under the main model ({headline_model}) yet**: the three comparison rows (M, B1_E4, B2) of that model are complete on none of the decidable designs. " + proto
    else:
        data["main_model_headline"] = (f"2. Decidable under the main model ({headline_model}): {', '.join(dec_under[headline_model])} ({len(dec_under[headline_model])} design(s)); tally under the decided rule " +
                                       ", ".join(f"{k} {n}" for k, n in sorted(t_dec.items())) + " (undecided rows are designs without the three {headline_model} rows). ".replace("{headline_model}", headline_model) + proto)
    total = len(held)
    need = int(round(0.6 * total))
    wins = t_dec.get("win", 0)
    data["criterion"] = {
        "criterion_text": ("C2: under hidden configurations at equal DC hours, M's geometric-mean gain exceeds B2's by more than 2σ_D on ≥ 60% of designs; M has an advantage of the same order over B1@E4 (otherwise the static "
                           "prompt suffices); on Dr.RTL's 20 designs, M is not below Dr.RTL, or reaches the same level with ≤ 1/3 of the DC hours."),
        "criterion_source": "docs/PROPOSAL.md §7.2 'Success criteria', first bullet (verbatim)",
        "reachability": {"designs_total": total, "decided": len(data["decidable"]), "wins_so_far": wins, "wins_needed": need, "wins_still_available": total - len(data["decidable"]),
                         "reachable": (total - len(data["decidable"]) + wins) >= need, "tally_basis": f"decided rule, main model {headline_model}, search basis, decidable designs only",
                         "note": "the criterion is stated under the hidden configurations at equal DC hours; this report gives its visible-layer proxy (DECISION 2026-09-18 (d) F2) and, beside it, the pre-registered caliber on "
                                 "the visible layer — the hidden layer stays sealed until the Phase 5 completion marker"}}
    diff = {}
    for d in data["decidable"]:
        os_ = {mode: (tal[f"search|{(cfg['exp5'].get('model_assignment') or {}).get(tier_of.get(d), {}).get('all_arms') or cfg['llm']['selected']}|{mode}"]["designs"].get(d) or {}).get("outcome") for mode, _l, _m, _de in MODES}
        if len({v for v in os_.values() if v is not None}) > 1:
            diff[d] = os_
    data["criterion"]["decided_differently"] = diff
    saif_changes = []
    for d in data["decidable"]:
        model = (cfg["exp5"].get("model_assignment") or {}).get(tier_of.get(d), {}).get("all_arms") or cfg["llm"]["selected"]
        o1 = (tal[f"search|{model}|decided"]["designs"].get(d) or {}).get("outcome")
        o2 = (tal[f"offline_saif|{model}|decided"]["designs"].get(d) or {}).get("outcome")
        if o1 != o2:
            saif_changes.append(f"{d} ({o1 or 'undecided'} → {o2 or 'undecided'})")
    data["saif_changes"] = saif_changes
    # 4 arm tables per tier and model, on the decidable designs
    dec_set = set(data["decidable"])
    arms = {}
    for t in ("large", "medium", "small"):
        ds = {d for d in dec_set if tier_of.get(d) == t}
        for model in models:
            rows_pre = arm_table(cfg, runs, cands, ds, mat, model=model)
            if not rows_pre:
                continue
            budget = min([v["dc_h_per_run"] for v in rows_pre.values() if v["dc_h_per_run"]], default=None)
            arms[f"{t} tier, {model}"] = {"rows": arm_table(cfg, runs, cands, ds, mat, model=model, budget=budget), "n_designs": len(ds), "model": model, "budget_h": budget}
    for model in models:
        rows_pre = arm_table(cfg, runs, cands, dec_set, mat, model=model)
        budget = min([v["dc_h_per_run"] for v in rows_pre.values() if v["dc_h_per_run"]], default=None)
        arms[f"pooled decidable designs, {model}"] = {"rows": arm_table(cfg, runs, cands, dec_set, mat, model=model, budget=budget), "n_designs": len(dec_set), "model": model, "budget_h": budget}
    data["arms"] = arms
    data["headline_scope"] = f"pooled decidable designs, {headline_model}"
    data["arms_note"] = ("Rows are never mixed across models. In the large tier the plan runs every arm with " + str(data["rows"]["main_model"].get("large")) + " and M also with the contrast model; in the medium and small tiers "
                         "every arm runs with " + str(data["rows"]["main_model"].get("medium")) + " and only M and B2 also with the contrast model (config exp5.model_assignment), so B0, B1_E4 and DrRTL_reimpl have no rows of the "
                         "contrast model there at all. Large-tier M ran with the candidate prescreen on until 2026-09-18 06:25; medium and small M did not. The columns 'at equal DC' read every row's curve at the common budget "
                         "(the smallest mean visible DC hours per run among the rows of the scope).")
    # 5 duplicates
    data["duplicates"] = section_duplicates(cfg, conn, runs, cands, dec_set)
    # 6 failures
    data["failures"] = section_failures(cfg, conn, cands, tuple(data["excluded_designs"]) or ("drrtl_arm_cpu2", "cktevo_hsm__hsm"))
    # 7 mechanism
    data["mechanism"] = section_mechanism(cfg, conn, runs, cands, dec_set)
    # 8 latency bound
    lb = RP.proof_latency_bound(conn, cfg)
    lbd = {}
    for d, val in sorted(lb.items()):
        med = float(val["median_s"]) if isinstance(val, dict) else float(val)
        e, tot, per = RP.archive_empty_summary(val)
        prov = sum(1 for c in cands if c["design_id"] == d and c.get("verdict") == "proven")
        n_pr = sum(1 for c in cands if c["design_id"] == d and c.get("v3_seconds") is not None)
        lbd[d] = {"tier": tier_of.get(d), "median_min": med / 60.0, "empty": (f"{e} of {tot}" if tot else "all builds"), "complete": d in complete, "proven": prov, "n_proofs": n_pr,
                  "reading": ("no candidate of this design was ever proven, so the archive could not fill whatever the proof latency was — the latency bound is not what kept the search from evolving here"
                              if prov == 0 else "proofs return after the generation window, so a build often had no verified parent yet")}
    ex_tal, _ex_pre = tallies(cfg, conn, runs, cands, dcache, [d for d in complete if d not in lbd], tier_of, sigmas, decid, default_basis)
    data["latency_bound"] = {"window_s": 1800, "designs": lbd, "tally_excluding": ex_tal[f"search|{headline_model}|decided"]["tally"],
                             "tally_excluding_as_run": ex_tal[f"search|{headline_model}|as_run"]["tally"],
                             "n_after": sum(ex_tal[f"search|{headline_model}|decided"]["tally"].values())}
    # 9 per design
    data["designs"] = section_designs(cfg, conn, runs, cands, dcache, tal, complete, tier_of, default_basis, sigmas, decid)
    data["prescreened_all"] = conn.execute("SELECT COUNT(*) FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase5' AND COALESCE(c.prescreened,0)=1").fetchone()[0]
    data["missing"] = [
        {"item": "incomplete designs", "detail": f"{len(comp['incomplete'])} of the {total} designs still have runs running or queued", "owner": "queue / lanes", "stage": "Stage B, then Stage C"},
        {"item": "main-model rows in the medium tier", "detail": f"the plan assigns {headline_model} only to M and B2 in the medium and small tiers, so a {headline_model}-only comparison against B1_E4 is impossible there by "
                                                                 "construction (config exp5.model_assignment)", "owner": "protocol", "stage": "stated, not fixable after the fact"},
        {"item": "the prescreened candidates' proofs", "detail": f"{data['prescreened_all']} prescreened candidates have sim + E4 but no SEQ proof; the pool's proofs open after the small tier's search runs", "owner": "offline pool", "stage": "after Stage C's runs"},
        {"item": "replacement runs", "detail": "the 6 LSTM M runs (harness_fix, prescreen off) are created but not launched; simple_spi and router carry harness-version-1 records whose re-verification waits for the pool's proofs", "owner": "queue", "stage": "Stage B / C"},
        {"item": "the small tier", "detail": "126 runs queued, no completed run — every small-tier row prints pending", "owner": "queue", "stage": "Stage C"},
        {"item": "σ_D on 13 designs", "detail": "the pooled-floor designs have no measured perturbation set, so the pre-registered 2 σ_D separation cannot be formed; PLAN 6.9 (floor6 group) measures them", "owner": "offline pool", "stage": "after Stage C's runs"},
        {"item": "hidden-configuration evaluation", "detail": "the criterion is stated over the hidden configurations at equal DC hours; the results are sealed until PHASE5_COMPLETE and are read only by scripts/report_hidden.py", "owner": "operator after the marker", "stage": "after Phase 5"},
        {"item": "Phase 6 ablations", "detail": "no map prior and the verdict-synchronous cadence are listed in PLAN 6.1 / config ablations.variants but not implemented or run", "owner": "Phase 6", "stage": "Phase 6"},
    ]
    data["reachability"] = data["criterion"]["reachability"]
    data["sources"] = SOURCES
    data["summary"] = summary_lines(data)
    md = os.path.join(ROOT, "reports", f"c2_interim_{a.date}.md")
    js = os.path.join(ROOT, "reports", "data", "c2_interim.json")
    with open(js, "w") as f:
        json.dump(data, f, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    with open(md, "w") as f:
        f.write(render(data))
    print(f"written {md} and {js}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
