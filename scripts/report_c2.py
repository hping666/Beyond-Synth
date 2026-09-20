#!/usr/bin/env python3
"""REQUEST 2026-09-20 (f) — C2 interim evidence report (read-only): reports/c2_interim_<date>.md and reports/data/c2_interim.json.

Uniform caliber throughout: equal LLM calls per run (config scale.budget.llm_calls_per_run), rule A with each design's frozen
phase4 floor (src.analysis.phase5.uniform_diagnosis on the candidate's E4 record), per-metric verdicts, the materiality count
beside every retention figure (config noise.materiality). Every table states n, the completion state and the harness / prescreen
configuration of the runs behind it; an incomplete row prints "pending", never 0. No record, default or configuration is altered
and nothing is read from the hidden database.

  python3 scripts/report_c2.py [--date YYYY-MM-DD]
"""
import argparse
import collections
import copy
import datetime
import importlib.util
import json
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
# key -> (label mode = the metric subset rule A is applied with, metric set of the comparison, description)
MODES = (("decided", "as_run", ("area",), "the decided tally rule: rule A as run (all three metrics), the arms separated on area (DECISION 2026-09-19 (m) 4 / (n) 2)"),
         ("as_run", "as_run", METRICS, "rule A as run (all three metrics), the arms separated on any metric"),
         ("saif_any", "saif_any", None, "(i) any metric, power only where both records carry SAIF power (excluded on the default-basis designs), rule A applied on the same subset"),
         ("area", "area", ("area",), "(ii) area only: rule A on area alone, the arms separated on area"),
         ("wns", "wns", ("wns",), "(iii) WNS only: rule A on WNS alone, the arms separated on WNS"))
LABEL_MODES = ("as_run", "saif_any", "area", "wns")
LABELS = ("retained", "tradeoff", "absorbed_identical", "absorbed", "noise", "harmful", "fragile")
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
def dc_hours_by_run(conn, exp="phase5"):
    """Visible DC hours per run in one pass (the same quantity as src.analysis.phase5.run_dc_hours: the ok evaluations of the run's
    candidates and of their envelope records <cand>_env*, which carry no candidates row) — per-run LIKE joins scan the whole
    evaluations table, so the attribution is built once."""
    run_of = {r[0]: r[1] for r in conn.execute("SELECT c.cand_id, c.run_id FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp=?", (exp,))}
    out = collections.Counter()
    for cid, sec in conn.execute("SELECT cand_id, dc_seconds FROM evaluations WHERE status='ok' AND cand_id IS NOT NULL AND dc_seconds IS NOT NULL"):
        rid = run_of.get(cid)
        if rid is None and "_env" in cid:
            rid = run_of.get(cid.split("_env", 1)[0])
        if rid is not None:
            out[rid] += float(sec)
    return {k: v / 3600.0 for k, v in out.items()}


def scan(cfg, conn, designs, complete_set, exp="phase5"):
    """Every non-superseded, non-excluded run of `exp` with its candidates. On the complete designs every proven candidate with an
    E4 record is labelled under each mode (m3.diagnose with the metric subset); elsewhere only the as-run label is taken."""
    src("run scan", "SELECT * FROM runs WHERE exp='phase5' AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0; per run its candidates (SELECT * FROM candidates WHERE run_id=?); "
                    "labels from src.analysis.phase5.uniform_diagnosis (rule A at E4, frozen phase4 floors) and, for the metric modes, src.diagnose.m3.diagnose on the same E4 record with the other metrics removed")
    tier_of = P5.tier_of_design(cfg)
    dc_h = dc_hours_by_run(conn, exp)
    runs, cands = [], []
    for r in conn.execute("SELECT * FROM runs WHERE exp=? AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0 ORDER BY created_at", (exp,)):
        r = dict(r)
        r["tier"] = tier_of.get(r["design_id"])
        if r["tier"] is None:
            continue
        r["row"] = f"{r['arm']}|{r['llm_model']}"
        r["dc_h"] = dc_h.get(r["run_id"], 0.0)
        rdir = os.path.join(C.results_dir(cfg), "candidates", r["run_id"])
        r["unusable"] = len([f for f in os.listdir(rdir) if f.startswith("unusable_")]) if os.path.isdir(rdir) else 0
        runs.append(r)
        full = r["design_id"] in complete_set
        d = designs.get(r["design_id"])
        for c in conn.execute("SELECT * FROM candidates WHERE run_id=? ORDER BY gen, created_at", (r["run_id"],)):
            c = dict(c)
            c.update(run=r["run_id"], tier=r["tier"], arm=r["arm"], model=r["llm_model"], design_id=r["design_id"], row=r["row"], labels={}, gains={})
            try:
                c["tags"] = sorted({t for t in (C1.norm_subtag(x) for x in json.loads(c.get("subtags_json") or "[]") if isinstance(x, str)) if t})
            except (ValueError, TypeError):
                c["tags"] = []
            if c.get("verdict") == "proven" and d and d["base"] and d["phi"] is not None:
                ev = conn.execute("SELECT * FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (c["cand_id"],)).fetchone()
                if ev is not None:
                    rec = P5.record_from_row(ev)
                    def lab(keep):
                        o = m3.diagnose(d["base"], strip_metrics(rec, keep) if keep else rec, d["sigma"], d["phi"], v3_status="proven",
                                        k_sigma=designs.k_sigma, thresholds=d["thresholds"], floor_class=d["floor_class"])
                        return o.get("label"), ((o.get("evidence") or {}).get("gains") or {}), (o.get("evidence") or {}).get("power_basis")
                    l0, g0, basis = lab(None)
                    c["labels"]["as_run"], c["gains"]["as_run"], c["power_basis"] = l0, g0, basis
                    if full:
                        if l0 in ("absorbed_identical", "duplicate"):
                            for mode in LABEL_MODES[1:]:
                                c["labels"][mode], c["gains"][mode] = l0, g0
                        else:
                            keep_any = {"area", "wns"} | ({"power"} if basis == "saif" else set())
                            for mode, keep in (("saif_any", keep_any), ("area", {"area"}), ("wns", {"wns"})):
                                c["labels"][mode], c["gains"][mode] = lab(keep)[:2]
            cands.append(c)
    return runs, cands


# ----------------------------------------------------------------------------- 1. completion
def section_completion(cfg, conn, cd, view, tier_of):
    src("1 completion", "src.analysis.phase5.complete_designs (planned rows x seeds from scripts/phase5_main.plan against runs.status='done'; pending candidates by kind from pending_kind; an offline proof of a "
                        "prescreened candidate does not block, DECISION 2026-09-18 D3) and completion_view; queued / running runs from the runs table")
    rows = {}
    for d in sorted(cd["rows"], key=lambda x: ({"large": 0, "medium": 1, "small": 2}.get(tier_of.get(x), 3), x)):
        planned = sum(v["planned"] for v in cd["rows"][d].values())
        done = sum(v["done"] for v in cd["rows"][d].values())
        st = collections.Counter(r[0] for r in conn.execute("SELECT status FROM runs WHERE exp='phase5' AND design_id=? AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0", (d,)))
        bl = cd["blockers"].get(d) or {}
        rows[d] = {"tier": tier_of.get(d), "planned": planned, "done": done, "running": st.get("running", 0), "queued": st.get("created", 0),
                   "blockers": bl, "state": ("complete" if d in cd["complete"] else "B0 pending" if d in cd["preliminary"] else "incomplete"),
                   "proofs": bl.get("verdict", 0) + bl.get("proof", 0), "e4": bl.get("e4_retry", 0) + bl.get("e4_late", 0) + bl.get("e4_exhausted", 0), "b0_e4": bl.get("b0_e4", 0)}
    return {"designs": rows, "complete": cd["complete"], "preliminary": cd["preliminary"],
            "incomplete": [d for d in rows if rows[d]["state"] == "incomplete"], "criterion": view.get("criterion")}


# ----------------------------------------------------------------------------- 2. criterion
def best_per_run(cands, runs, design, mode):
    """{row: {metric: [best gain per run]}} — per run the largest gain of that metric over the candidates labelled retained under
    `mode` (0.0 when the run has none), in the order of the run ids; only runs with status done."""
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    by_run = collections.defaultdict(list)
    for c in cands:
        if c["design_id"] == design:
            by_run[c["run"]].append(c)
    for r in runs:
        if r["design_id"] != design or r["status"] != "done":
            continue
        ret = [c for c in by_run.get(r["run_id"], []) if c["labels"].get(mode) == "retained"]
        for m in METRICS:
            out[r["row"]][m].append(max([float(c["gains"][mode].get(m) or 0.0) for c in ret if c["gains"][mode].get(m) is not None] or [0.0]))
    return out


def outcome_of(means, t_d, metrics, model):
    """win / tie / partial / loss of M against both baselines under `metrics` (DECISION 2026-09-19 (m) 4 / (n) 2 generalised from
    area to a metric set): loss when a baseline exceeds M by more than the floor on some metric, win when M exceeds both on some
    metric without being below either on any, partial when it separates from exactly one, tie otherwise."""
    m = means.get(f"M|{model}")
    b1, b2 = means.get(f"B1_E4|{model}"), means.get(f"B2|{model}")
    if not (m and b1 and b2):
        return None, {}
    seps = {}
    for name, b in (("B1_E4", b1), ("B2", b2)):
        seps[name] = {k: (m[k] - b[k]) for k in metrics if m.get(k) is not None and b.get(k) is not None}
    if not any(seps.values()):
        return None, seps
    def above(s):
        return any(v > float(t_d.get(k) or 0.0) for k, v in s.items())
    def below(s):
        return any(v < -float(t_d.get(k) or 0.0) for k, v in s.items())
    if below(seps["B1_E4"]) or below(seps["B2"]):
        return "loss", seps
    n = int(above(seps["B1_E4"])) + int(above(seps["B2"]))
    return ("win" if n == 2 else "partial" if n == 1 else "tie"), seps


def section_criterion(cfg, conn, runs, cands, designs, complete, tier_of, default_basis, exclude=()):
    src("2 criterion", "docs/PROPOSAL.md §7.2 (verbatim); per design the mean over seeds of each row's best retained gain per metric "
                       "(0 for a run without a retained candidate), against the design's frozen rule-A floor per metric (noise_floor, floor_version phase4); "
                       "the model of the tier from config exp5.model_assignment.all_arms")
    ma = cfg["exp5"].get("model_assignment") or {}
    out = {"per_mode": {}, "designs": {}}
    for mode, label_mode, mset, desc in MODES:
        tally = collections.Counter()
        per_design = {}
        for d in complete:
            if d in exclude:
                continue
            model = (ma.get(tier_of.get(d)) or {}).get("all_arms") or cfg["llm"]["selected"]
            bp = best_per_run(cands, runs, d, label_mode)
            means = {row: {m: (statistics.mean(v[m]) if v[m] else None) for m in METRICS} for row, v in bp.items()}
            t_d = designs.get(d)["thresholds"]
            metrics = mset or tuple(m for m in METRICS if m != "power" or d not in default_basis)
            o, seps = outcome_of(means, t_d, metrics, model)
            tally[o or "undecided"] += 1
            per_design[d] = {"model": model, "outcome": o, "means": means, "separations": seps, "metrics": list(metrics), "t_d": t_d,
                             "runs": {row: len(v["area"]) for row, v in bp.items()}}
        out["per_mode"][mode] = {"description": desc, "tally": dict(tally), "designs": per_design}
    total = sum(len(v) for v in (cfg["exp5"].get("starting_points") or {}).values())
    counted = len([d for d in complete if d not in exclude])
    need = int(round(0.6 * total))
    wins = out["per_mode"]["decided"]["tally"].get("win", 0)   # the decided tally rule; the three readings of the request are printed beside it
    out["reachability"] = {"designs_total": total, "decided": counted, "wins_so_far": wins, "wins_needed": need, "tally_basis": "the decided rule (rule A as run, area separation); the three readings are in item 2",
                           "wins_still_available": total - counted, "reachable": (total - counted + wins) >= need,
                           "note": "the criterion is stated under the hidden configurations; this is its visible-layer proxy (DECISION 2026-09-18 (d) F2), the hidden layer stays sealed until the Phase 5 completion marker"}
    diff = {}
    for d in complete:
        if d in exclude:
            continue
        os_ = {mode: (out["per_mode"][mode]["designs"].get(d) or {}).get("outcome") for mode, _lm, _ms, _de in MODES}
        if len({v for v in os_.values() if v is not None}) > 1:
            diff[d] = os_
    out["decided_differently"] = diff
    out["criterion_text"] = ("C2: under hidden configurations at equal DC hours, M's geometric-mean gain exceeds B2's by more than 2σ_D on ≥ 60% of designs; M has an advantage of the same order over "
                             "B1@E4 (otherwise the static prompt suffices); on Dr.RTL's 20 designs, M is not below Dr.RTL, or reaches the same level with ≤ 1/3 of the DC hours.")
    out["criterion_source"] = "docs/PROPOSAL.md §7.2 'Success criteria', first bullet (verbatim)"
    return out


# ----------------------------------------------------------------------------- 3. arm comparison
def arm_table(cfg, runs, cands, designs, which, mat, mode="as_run"):
    src("3 arm comparison", "per arm-model row over the runs of the given designs: runs done, LLM calls (runs.llm_calls, budget scale.budget.llm_calls_per_run), USD (runs.spent_usd), visible DC hours "
                            "(evaluations.dc_seconds of the run's candidates), candidates, unusable answers (results/candidates/<run>/unusable_*.json), duplicates (label duplicate), inconclusive verdicts, "
                            "proven, retained / trade-off by rule A at E4, and the best retained gain per metric per run (mean over seeds, max alongside)")
    rows = collections.defaultdict(lambda: {"runs": 0, "runs_done": 0, "calls": 0, "usd": 0.0, "dc_h": 0.0, "cands": 0, "unusable": 0, "duplicate": 0, "inconclusive": 0,
                                            "proven": 0, "retained": 0, "tradeoff": 0, "material": 0, "runs_with_retained": 0, "best": collections.defaultdict(list), "designs": set()})
    by_run = collections.defaultdict(list)
    for c in cands:
        by_run[c["run"]].append(c)
    for r in runs:
        if r["design_id"] not in which:
            continue
        g = rows[r["row"]]
        g["runs"] += 1
        g["designs"].add(r["design_id"])
        if r["status"] != "done":
            continue
        g["runs_done"] += 1
        g["calls"] += int(r["llm_calls"] or 0)
        g["usd"] += float(r["spent_usd"] or 0.0)
        g["dc_h"] += float(r["dc_h"] or 0.0)
        g["unusable"] += int(r["unusable"] or 0)
        ret = []
        for c in by_run.get(r["run_id"], []):
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
                lab = c["labels"].get(mode)
                if lab == "retained":
                    g["retained"] += 1
                    ret.append(c)
                    up, down = C1.material(c["gains"].get(mode) or {}, mat)
                    g["material"] += int(bool(up) and not down)
                elif lab == "tradeoff":
                    g["tradeoff"] += 1
        g["runs_with_retained"] += int(bool(ret))
        for m in METRICS:
            g["best"][m].append(max([float(c["gains"][mode].get(m) or 0.0) for c in ret if c["gains"][mode].get(m) is not None] or [0.0]))
    out = {}
    for row, g in rows.items():
        n = g["runs_done"]
        out[row] = {"runs": g["runs"], "runs_done": n, "designs": len(g["designs"]), "calls": g["calls"], "usd": round(g["usd"], 2), "dc_h": round(g["dc_h"], 1),
                    "cands": g["cands"], "unusable": g["unusable"], "duplicate": g["duplicate"], "inconclusive": g["inconclusive"], "proven": g["proven"],
                    "proven_per_call": rate(g["proven"], g["calls"]), "retained": g["retained"], "tradeoff": g["tradeoff"], "material": g["material"],
                    "retained_per_run": rate(g["retained"], n), "runs_with_retained": g["runs_with_retained"], "share_runs_with_retained": rate(g["runs_with_retained"], n),
                    "retained_per_100_calls": (100.0 * g["retained"] / g["calls"]) if g["calls"] else None,
                    "retained_per_usd": rate(g["retained"], g["usd"]) if g["usd"] else None, "retained_per_dc_hour": rate(g["retained"], g["dc_h"]) if g["dc_h"] else None,
                    "best_mean": {m: (statistics.mean(v) if v else None) for m, v in g["best"].items()},
                    "best_max": {m: (max(v) if v else None) for m, v in g["best"].items()}}
    return out


# ----------------------------------------------------------------------------- 4. large tier / prescreen
def section_large(cfg, conn, runs, cands, designs, complete, mat):
    src("4 large tier", "arm table of the large-tier complete designs (a) over the run's own candidates as the Stage A tables build it (prescreened candidates carry label 'prescreened', no verdict, and are "
                        "not counted) and (b) with the offline pool's evaluation of the prescreened candidates added as provisional rows (sim + E4 done, proof pending: report_c1.rule_a_from_e4 on the E4 record); "
                        "(c) the prescreen-off large-tier M runs (runs.prescreen_on = 0)")
    large = [d for d in complete if P5.tier_of_design(cfg).get(d) == "large"]
    a = arm_table(cfg, runs, cands, designs, set(large), mat)
    pre = collections.defaultdict(lambda: {"n": 0, "sim_failed": 0, "e4_pending": 0, "retained": 0, "tradeoff": 0, "other": collections.Counter()})
    for c in cands:
        if not int(c.get("prescreened") or 0) or c["design_id"] not in large:
            continue
        g = pre[c["row"]]
        g["n"] += 1
        if c.get("verdict") and c["verdict"] != "proven":
            g["sim_failed"] += 1
            continue
        r = C1.rule_a_from_e4(designs, conn, c["cand_id"], c["design_id"])
        if not r:
            g["e4_pending"] += 1
            continue
        lab = r[0]
        if lab == "retained":
            g["retained"] += 1
        elif lab == "tradeoff":
            g["tradeoff"] += 1
        else:
            g["other"][lab] += 1
    b = {}
    for row, g in a.items():
        p = pre.get(row) or {}
        b[row] = dict(g)
        if p:
            b[row] = dict(g, retained=g["retained"] + p["retained"], tradeoff=g["tradeoff"] + p["tradeoff"],
                          retained_per_run=rate(g["retained"] + p["retained"], g["runs_done"]), provisional=p["retained"] + p["tradeoff"])
    off = [{"run_id": r["run_id"], "design": r["design_id"], "model": r["llm_model"], "status": r["status"], "calls": r["llm_calls"]}
           for r in runs if r["tier"] == "large" and r["arm"] == "M" and not int(r.get("prescreen_on") or 0)]
    ordering = lambda tab: [k for k, _ in sorted(((k, v["retained_per_run"] or 0.0) for k, v in tab.items()), key=lambda kv: -kv[1])]
    return {"designs": large, "a_as_run": a, "b_with_prescreened": b, "prescreened": {k: {kk: (dict(vv) if isinstance(vv, collections.Counter) else vv) for kk, vv in v.items()} for k, v in pre.items()},
            "c_prescreen_off_runs": off, "ordering_a": ordering(a), "ordering_b": ordering(b),
            "ordering_changes": ordering(a) != ordering(b),
            "proof_note": "the provisional counts are E4 labels without a proof; a prescreened candidate enters the tables only if its SEQ proof comes back proven — to change the ordering, enough of "
                          "M's provisionally retained candidates would have to be proven to move M's retained-per-run past the next row, and none of them counts until then"}


# ----------------------------------------------------------------------------- 5. mechanism
def section_mechanism(cfg, conn, runs, cands, complete, tier_of):
    src("5 mechanism", "fate shares over the proven candidates of the complete designs (rule A at E4); calls per retained candidate from runs.llm_calls; parents from candidates.parent_id (NULL = D) with the "
                       "archive members of the generation (gen_summary.archive_json); unverified-at-build from gen_summary.pending_json against the previous generation's candidates (src.jobqueue.core.unverified_at_build); "
                       "the generation of each retained candidate from candidates.gen; the feedback strings from diagnoses.feedback_json of earlier candidates of the same run")
    by_row = collections.defaultdict(lambda: {"proven": 0, "fate": collections.Counter(), "retained_gen": collections.Counter(), "retained": 0, "calls": 0,
                                              "parents_d": 0, "parents_archive": 0, "with_feedback": 0})
    for r in runs:
        if r["design_id"] in complete and r["status"] == "done":
            by_row[r["row"]]["calls"] += int(r["llm_calls"] or 0)
    diag_earlier = collections.defaultdict(list)   # run -> [(gen, diagnosis)]
    runs_complete = {r["run_id"] for r in runs if r["design_id"] in complete}
    for c in cands:
        if c["design_id"] not in complete:
            continue
        if c.get("label") in ("duplicate", "aborted"):
            continue
        g = by_row[c["row"]]
        if c.get("parent_id"):
            g["parents_archive"] += 1
        else:
            g["parents_d"] += 1
        lab = c["labels"].get("as_run")
        if c.get("verdict") == "proven" and lab:
            g["proven"] += 1
            g["fate"][lab] += 1
            if lab in ("absorbed", "absorbed_identical", "noise", "harmful"):
                diag_earlier[c["run"]].append((int(c.get("gen") or 0), lab))
            if lab == "retained":
                g["retained"] += 1
                g["retained_gen"][int(c.get("gen") or 0)] += 1
    for c in cands:
        if (c["design_id"] in complete and c["arm"] == "M" and c["labels"].get("as_run") == "retained"
                and c.get("label") not in ("duplicate", "aborted")):   # the same population as the retained count above
            if any(gen < int(c.get("gen") or 0) for gen, _ in diag_earlier.get(c["run"], [])):
                by_row[c["row"]]["with_feedback"] += 1
    from src.jobqueue.core import unverified_at_build
    unv = {}
    for t in ("large", "medium", "small"):
        try:
            unv[t] = unverified_at_build(conn, cfg, minutes=10 ** 7, tier=t, by="row")
        except Exception as e:
            unv[t] = f"{type(e).__name__}: {e}"[:80]
    out = {"rows": {}, "unverified_at_build_by_tier_row": unv}
    for row, g in by_row.items():
        tot = sum(g["fate"].values())
        first = g["retained_gen"].get(1, 0)
        out["rows"][row] = {"proven": g["proven"], "fate": dict(g["fate"]), "fate_share": {k: rate(v, tot) for k, v in g["fate"].items()},
                            "calls": g["calls"], "calls_per_retained": (g["calls"] / g["retained"]) if g["retained"] else None,
                            "parents_D": g["parents_d"], "parents_archived": g["parents_archive"],
                            "share_parent_D": rate(g["parents_d"], g["parents_d"] + g["parents_archive"]),
                            "retained": g["retained"], "retained_gen1": first, "retained_later": g["retained"] - first,
                            "share_retained_gen1": rate(first, g["retained"]), "retained_after_verdict_feedback": (g["with_feedback"] if row.startswith("M|") else None),
                            "share_retained_after_verdict_feedback": (rate(g["with_feedback"], g["retained"]) if row.startswith("M|") else None)}
    return out


# ----------------------------------------------------------------------------- 7. per design
def section_designs(cfg, conn, runs, cands, designs, crit, complete, tier_of, default_basis):
    src("7 per design", "the design's floor row (noise_floor, floor_version phase4: floor_class, t_d per metric), the power basis of D's E4 baseline (evaluations.power_saif_mw of is_baseline=1 at Φ_main), "
                        "proven rate over the design's candidates, each row's best retained gain per metric (mean over seeds, max), the outcome of item 2, and the class / evidence tags of the retained candidates "
                        "whose gain decided the design")
    out = {}
    for d in complete:
        dd = designs.get(d)
        cd = [c for c in cands if c["design_id"] == d and c.get("label") not in ("duplicate", "aborted")]
        prov = sum(1 for c in cd if c.get("verdict") == "proven")
        info = crit["per_mode"]["as_run"]["designs"].get(d) or {}
        best = {}
        for row, means in (info.get("means") or {}).items():
            best[row] = {"mean": means, "max": {m: max([float(c["gains"]["as_run"].get(m) or 0.0) for c in cd if c["row"] == row and c["labels"].get("as_run") == "retained" and c["gains"]["as_run"].get(m) is not None] or [0.0]) for m in METRICS}}
        deciders = []
        model = info.get("model")
        for c in sorted([c for c in cd if c["row"] == f"M|{model}" and c["labels"].get("as_run") == "retained"], key=lambda x: -(x["gains"]["as_run"].get("area") or 0.0))[:3]:
            deciders.append({"cand_id": c["cand_id"], "class": c.get("class_final"), "tags": c["tags"], "gains": {m: c["gains"]["as_run"].get(m) for m in METRICS}, "gen": c.get("gen")})
        out[d] = {"tier": tier_of.get(d), "family": C1.family(d), "floor_class": (dd or {}).get("floor_class"), "t_d": (dd or {}).get("thresholds"),
                  "power_basis": ("default" if d in default_basis else "saif"), "candidates": len(cd), "proven": prov, "proven_rate": rate(prov, len(cd)),
                  "best": best, "outcome": info.get("outcome"), "deciders": deciders}
    return out


# ----------------------------------------------------------------------------- render
def render(data):
    v = data["versions"]
    mat = data["materiality"]
    L = [f"# C2 interim evidence report — {data['date']} (visible layer only; interim)", "",
         f"Generated {data['generated_at']} by scripts/report_c2.py (git {v['git_sha']}, cfg {v['cfg_hash']}); floor_version **{v['floor_version']}**, equiv_version {v['equiv_version']}, harness_version {v['harness_version']}; "
         f"uniform caliber: equal LLM calls ({v['calls_per_run']} per run), rule A at E4 with each design's frozen floor, per-metric verdicts; materiality area > {pct(mat['area'], 0)}, power > {pct(mat['power'], 0)}, "
         f"WNS > {pct(mat['wns'], 0)} of the period. No record, default or configuration was altered; results/hidden was not read. Data: reports/data/c2_interim.json.", ""]
    L += ["## 0. Plain-language summary", ""] + data["summary"] + [""]
    # 1
    c = data["completion"]
    L += ["## 1. Completion state", "",
          f"Complete designs {len(c['complete'])}, B0 pending (complete except B0's offline E4, DECISION 2026-09-19 (l) 3) {len(c['preliminary'])}, incomplete {len(c['incomplete'])} of {data['reachability']['designs_total']} planned designs.", "",
          "| design | tier | state | runs done / planned | running | queued | candidates pending a verdict or sim | E4 pending (retries) | B0 offline E4 |", "|---|---|---|---|---|---|---|---|---|"]
    for d, e in data["completion"]["designs"].items():
        L.append(f"| {d} | {e['tier']} | {e['state']} | {e['done']} / {e['planned']} | {e['running']} | {e['queued']} | "
                 f"{e['blockers'].get('verdict', 0) + e['blockers'].get('sim', 0) + e['blockers'].get('failed_job', 0) or ('0' if e['state'] != 'incomplete' else 'pending')} | {e['e4'] or 0} | {e['b0_e4'] or 0} |")
    L += ["", "Every later table is split into the complete designs (including B0 pending) and, where shown, the incomplete ones marked informational; no arm comparison is drawn on an incomplete design.", ""]
    # 2
    cr = data["criterion"]
    L += ["## 2. The pre-registered criterion", "", f"Verbatim ({cr['criterion_source']}):", "", f"> {cr['criterion_text']}", "",
          f"Visible-layer proxy on the complete designs (the hidden-configuration form stays sealed). {cr['reachability']['note']}", ""]
    for i, (mode, _lm, _ms, desc) in enumerate(MODES):
        mm = cr["per_mode"][mode]
        t = mm["tally"]
        L += [f"### 2.{i + 1} {desc}", "",
              f"Tally: wins {t.get('win', 0)}, ties {t.get('tie', 0)}, partial {t.get('partial', 0)}, losses {t.get('loss', 0)}, undecided {t.get('undecided', 0)} of {sum(t.values())} complete designs.", "",
              "| design | model | outcome | M − B1_E4 (area / power / WNS) | M − B2 (area / power / WNS) | floor t_D (area / power / WNS) |", "|---|---|---|---|---|---|"]
        for d, e in mm["designs"].items():
            s1, s2, td = e["separations"].get("B1_E4", {}), e["separations"].get("B2", {}), e["t_d"]
            f = lambda s: " / ".join((pct(s.get(m), 2) if s.get(m) is not None else "—") for m in METRICS)
            L.append(f"| {d} | {e['model']} | **{e['outcome'] or 'undecided'}** | {f(s1)} | {f(s2)} | {' / '.join(pct(td.get(m), 2) for m in METRICS)} |")
        L.append("")
    r = cr["reachability"]
    L += [f"**Reachability** ({r['tally_basis']}): {r['decided']} of {r['designs_total']} designs decided, wins so far {r['wins_so_far']}, wins needed {r['wins_needed']} (60 % of {r['designs_total']}), "
          f"wins still available {r['wins_still_available']}; criterion still reachable: {'yes' if r['reachable'] else 'no'}.", ""]
    if cr["decided_differently"]:
        L += ["Designs decided differently by the three ways:", ""] + [f"- {d}: " + ", ".join(f"{k} {vv or 'undecided'}" for k, vv in o.items()) for d, o in cr["decided_differently"].items()] + [""]
    else:
        L += ["No design is decided differently by the three ways.", ""]
    # 3
    L += ["## 3. Arm comparison on the complete designs (equal calls)", ""]
    for name, tab in (("pooled over the complete designs", data["arms"]["pooled"]),) + tuple((f"{t} tier", data["arms"]["by_tier"][t]) for t in ("large", "medium", "small") if data["arms"]["by_tier"].get(t)):
        L += [f"### {name}", "", "| row | runs | designs | calls | candidates | unusable | duplicates | inconclusive | proven | proven/call | retained (material) | retained/run | runs with ≥ 1 retained | best retained area mean (max) | best power | best WNS | retained/100 calls | retained/USD | retained/DC h |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for row in sorted(tab, key=lambda k: (ARMS.index(k.split("|")[0]) if k.split("|")[0] in ARMS else 9, k)):
            e = tab[row]
            L.append(f"| {row} | {e['runs_done']} of {e['runs']} | {e['designs']} | {e['calls']} | {e['cands']} | {e['unusable']} | {e['duplicate']} | {e['inconclusive']} | {e['proven']} | {num(e['proven_per_call'], 3)} | "
                     f"{e['retained']} ({e['material']}) | {num(e['retained_per_run'])} | {e['runs_with_retained']} = {pct(e['share_runs_with_retained'])} | {pct(e['best_mean']['area'], 2)} ({pct(e['best_max']['area'], 2)}) | "
                     f"{pct(e['best_mean']['power'], 2)} ({pct(e['best_max']['power'], 2)}) | {pct(e['best_mean']['wns'], 2)} ({pct(e['best_max']['wns'], 2)}) | {num(e['retained_per_100_calls'])} | {num(e['retained_per_usd'])} | {num(e['retained_per_dc_hour'])} |")
        L.append("")
    missing_tiers = [t for t in ("large", "medium", "small") if not data["arms"]["by_tier"].get(t)]
    if missing_tiers:
        L += ["Tiers without a single complete design, whose rows are therefore **pending** and appear nowhere above: " + ", ".join(missing_tiers) + ".", ""]
    L += ["Large-tier M ran with the candidate prescreen on (`search.arms.M.prescreen: true` until 2026-09-18 06:25; 30 of 36 runs, 636 candidates never evaluated); medium- and small-tier M ran with it off. "
          "The prescreened candidates are not in the rows above; item 4 adds them as provisional rows.", ""]
    # 4
    lg = data["large"]
    L += ["## 4. Large tier and the prescreen caveat", "",
          f"Complete large-tier designs: {', '.join(lg['designs']) or 'none'} (the other large designs are incomplete and are not compared here). Prescreened candidates on them: {lg['prescreened_total']} of "
          f"{lg['prescreened_all_large']} in the whole tier — the rest sit on drrtl_aes, cktevo_nn_engine__spikeNeuron8_H7 and the superseded drrtl_LSTM runs, which are incomplete.", "",
          "| row | (a) retained / run as run | (b) with the prescreened candidates' provisional E4 labels | prescreened candidates | provisionally retained | provisionally trade-off | sim failed | E4 pending |", "|---|---|---|---|---|---|---|---|"]
    for row in sorted(lg["a_as_run"], key=lambda k: (ARMS.index(k.split("|")[0]) if k.split("|")[0] in ARMS else 9, k)):
        a, b = lg["a_as_run"][row], lg["b_with_prescreened"].get(row, {})
        p = lg["prescreened"].get(row) or {}
        L.append(f"| {row} | {num(a['retained_per_run'])} ({a['retained']} of {a['runs_done']} runs) | {num(b.get('retained_per_run'))} ({b.get('retained', a['retained'])}) | {p.get('n', 0)} | "
                 f"{p.get('retained', 0)} | {p.get('tradeoff', 0)} | {p.get('sim_failed', 0)} | {p.get('e4_pending', 0)} |")
    L += ["", f"Ordering by retained/run — (a) {' > '.join(lg['ordering_a'])}; (b) {' > '.join(lg['ordering_b'])}. **The ordering changes between (a) and (b): {'yes' if lg['ordering_changes'] else 'no'}.**", "",
          lg["proof_note"], "",
          f"(c) Prescreen-off large-tier M runs: {len(lg['c_prescreen_off_runs'])} — " + (", ".join(f"{x['design']} {x['model']} ({x['status']})" for x in lg["c_prescreen_off_runs"]) or "none") + ".", ""]
    # 5
    mech = data["mechanism"]
    L += ["## 5. Mechanism evidence (complete designs)", "", "| row | proven | retained | trade-off | absorbed_identical | absorbed | noise | harmful | calls per retained | parents = D | parents archived | retained in gen 1 | retained later | retained after a verdict feedback (M) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in sorted(mech["rows"], key=lambda k: (ARMS.index(k.split("|")[0]) if k.split("|")[0] in ARMS else 9, k)):
        e = mech["rows"][row]
        f = e["fate"]
        sh = lambda k: f"{f.get(k, 0)} = {pct(e['fate_share'].get(k))}" if f.get(k) else "0"
        L.append(f"| {row} | {e['proven']} | {sh('retained')} | {sh('tradeoff')} | {sh('absorbed_identical')} | {sh('absorbed')} | {sh('noise')} | {sh('harmful')} | {num(e['calls_per_retained'])} | "
                 f"{e['parents_D']} = {pct(e['share_parent_D'])} | {e['parents_archived']} | {e['retained_gen1']} = {pct(e['share_retained_gen1'])} | {e['retained_later']} | {(str(e['retained_after_verdict_feedback']) + ' = ' + pct(e['share_retained_after_verdict_feedback'])) if e['retained_after_verdict_feedback'] is not None else '—'} |")
    L += ["", "Unverified-at-build (share of the previous generation's candidates without a verdict when the next generation was built), per tier and row: "
          + "; ".join(f"{t}: " + ", ".join(f"{k} {pct(vv)}" for k, vv in sorted(x.items())) if isinstance(x, dict) else f"{t}: {x}" for t, x in mech["unverified_at_build_by_tier_row"].items()), ""]
    # 6
    pb = data["latency_bound"]
    L += ["## 6. Proof-latency-bound designs", "", f"Designs whose median proof latency exceeds the {pb['window_s']} s generation window (DECISION 2026-09-19 (k) 3): {len(pb['designs'])}.", "",
          "| design | tier | median proof latency (min) | empty-archive builds | complete |", "|---|---|---|---|---|"]
    for d, e in pb["designs"].items():
        L.append(f"| {d} | {e['tier']} | {num(e['median_min'], 0)} | {e['empty']} | {e['complete']} |")
    t2 = pb["tally_excluding"]
    t3 = pb["tally_excluding_as_run"]
    L += ["", f"Tally on the complete designs with these excluded ({pb['n_after']} designs), decided rule: wins {t2.get('win', 0)}, ties {t2.get('tie', 0)}, partial {t2.get('partial', 0)}, losses {t2.get('loss', 0)}, "
          f"undecided {t2.get('undecided', 0)}; reading it on any metric: wins {t3.get('win', 0)}, ties {t3.get('tie', 0)}, partial {t3.get('partial', 0)}, losses {t3.get('loss', 0)}.", ""]
    # 7
    L += ["## 7. Per-design detail (complete designs)", "", "| design | tier | family | floor class | t_D area / power / WNS | power basis | candidates | proven | outcome | M best area (mean / max) | B1_E4 | B2 | deciding retained candidates (class, tags) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d, e in data["designs"].items():
        model = (data["criterion"]["per_mode"]["as_run"]["designs"].get(d) or {}).get("model")
        g = lambda row: e["best"].get(f"{row}|{model}") or {}
        f = lambda row: f"{pct((g(row).get('mean') or {}).get('area'), 2)} / {pct((g(row).get('max') or {}).get('area'), 2)}"
        dec = "; ".join(f"{x['class']} ({', '.join(x['tags'][:2]) or 'no tag'}, gen {x['gen']}, area {pct(x['gains'].get('area'), 2)})" for x in e["deciders"]) or "none"
        L.append(f"| {d} | {e['tier']} | {e['family']} | {e['floor_class'] or 'pooled'} | {' / '.join(pct((e['t_d'] or {}).get(m), 2) for m in METRICS)} | {e['power_basis']} | {e['candidates']} | {e['proven']} = {pct(e['proven_rate'])} | "
                 f"{e['outcome'] or 'undecided'} | {f('M')} | {f('B1_E4')} | {f('B2')} | {dec} |")
    L.append("")
    # 8
    mc = data["model_contrast"]
    L += ["## 8. Model contrast on the same designs", "", "| arm | designs | luna runs | terra runs | proven/call luna | terra | retained/run luna | terra | best area luna | terra | USD luna | terra |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, e in mc.items():
        l, t = e.get("gpt-5.6-luna") or {}, e.get("gpt-5.6-terra") or {}
        L.append(f"| {arm} | {e['designs']} | {l.get('runs_done', 0)} | {t.get('runs_done', 0)} | {num(l.get('proven_per_call'), 3)} | {num(t.get('proven_per_call'), 3)} | {num(l.get('retained_per_run'))} | {num(t.get('retained_per_run'))} | "
                 f"{pct((l.get('best_mean') or {}).get('area'), 2)} | {pct((t.get('best_mean') or {}).get('area'), 2)} | {num(l.get('usd'))} | {num(t.get('usd'))} |")
    L += ["", "## 9. What is still missing for C2", ""] + [f"- **{x['item']}** — {x['detail']} (owner: {x['owner']}; stage: {x['stage']})" for x in data["missing"]] + [""]
    L += ["## S. Sources", ""] + [f"- **{k}**: {t}" for k, t in data["sources"].items()] + [""]
    return "\n".join(L)


def summary_lines(data):
    cr, r = data["criterion"], data["criterion"]["reachability"]
    t = cr["per_mode"]["as_run"]["tally"]
    ta, ts, tw = cr["per_mode"]["decided"]["tally"], cr["per_mode"]["saif_any"]["tally"], cr["per_mode"]["wns"]["tally"]
    tar = cr["per_mode"]["area"]["tally"]
    pooled = data["arms"]["pooled"]
    m_rows = {k: v for k, v in pooled.items() if k.startswith("M|")}
    best_m = max(m_rows.items(), key=lambda kv: kv[1]["retained_per_run"] or 0) if m_rows else (None, {})
    b1 = pooled.get("B1_E4|gpt-5.6-luna") or pooled.get("B1_E4|gpt-5.6-terra") or {}
    b2 = pooled.get("B2|gpt-5.6-luna") or pooled.get("B2|gpt-5.6-terra") or {}
    return [
        f"1. C2 can be read today on {r['decided']} of {r['designs_total']} designs ({len(data['completion']['complete'])} complete, {len(data['completion']['preliminary'])} complete except B0's offline E4); the other {len(data['completion']['incomplete'])} are still running or queued.",
        f"2. Tally of the pre-registered comparison (visible-layer proxy; the decided rule is the area separation): wins {ta.get('win', 0)}, ties {ta.get('tie', 0)}, partial {ta.get('partial', 0)}, losses {ta.get('loss', 0)}, undecided {ta.get('undecided', 0)}; "
        f"reading it on any metric with SAIF-basis power: wins {ts.get('win', 0)}, ties {ts.get('tie', 0)}, partial {ts.get('partial', 0)}, losses {ts.get('loss', 0)}; on area alone: wins {tar.get('win', 0)}, ties {tar.get('tie', 0)}, partial {tar.get('partial', 0)}; on WNS alone: wins {tw.get('win', 0)}, ties {tw.get('tie', 0)}, partial {tw.get('partial', 0)}, losses {tw.get('loss', 0)}.",
        f"3. Under the decided rule M wins on {ta.get('win', 0)} of the decided designs, ties on {ta.get('tie', 0)}, is partial on {ta.get('partial', 0)} and loses on {ta.get('loss', 0)}; every separation is printed against the design's floor in item 2.",
        f"4. Reachability: {r['wins_needed']} wins are needed (60 % of {r['designs_total']}), {r['wins_so_far']} are in, {r['wins_still_available']} designs are still open — the criterion is {'still arithmetically reachable' if r['reachable'] else 'no longer reachable'}.",
        f"5. The three ways of reading the comparison (any metric with SAIF-basis power, area only, WNS only) decide {len(cr['decided_differently'])} design(s) differently.",
        f"6. On {data['zero_proven']['n']} of the {r['decided']} decided designs no arm produced a single proven candidate ({', '.join(data['zero_proven']['designs'])}), so their tie is a tie at zero retention.",
        f"7. At equal calls on the complete designs, retained per run: " + ", ".join(f"{k} {num(v['retained_per_run'])}" for k, v in sorted(pooled.items(), key=lambda kv: -(kv[1]['retained_per_run'] or 0))[:4]) + ".",
        f"8. Search precision (share of proven candidates labelled retained) is printed per row in item 5; the mechanism figures do not depend on the criterion.",
        f"9. Large-tier M ran with the candidate prescreen (636 candidates never evaluated); adding their offline E4 labels {'changes' if data['large']['ordering_changes'] else 'does not change'} the large-tier ordering by retained per run — their proofs are still pending.",
        f"10. C2 cannot yet say anything about the hidden configurations (sealed until the completion marker), the small tier (not started), or the Phase 6 ablations (not run).",
        f"11. The three things that would change the picture most: (a) the medium tier's remaining designs completing ({len(data['completion']['incomplete'])} open); (b) the proofs of the {data['large']['prescreened_all_large']} prescreened large-tier candidates ({data['large']['prescreened_total']} of them on the complete large designs); (c) the hidden-configuration evaluation, which is what the criterion is actually stated over.",
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    tier_of = P5.tier_of_design(cfg)
    designs = P5._Designs(cfg, conn)
    mat = {"area": cfg["noise"]["materiality"]["area"], "power": cfg["noise"]["materiality"]["power_saif"], "wns": cfg["noise"]["materiality"]["wns"]}
    default_basis = P5.default_power_basis_designs(cfg, conn)
    cd = P5.complete_designs(cfg, conn)
    view = P5.completion_view(cfg, conn)
    complete = cd["complete"] + cd["preliminary"]
    runs, cands = scan(cfg, conn, designs, set(complete))
    data = {"date": a.date, "generated_at": datetime.datetime.now().isoformat(timespec="minutes"), "materiality": mat, "default_power_basis": default_basis,
            "versions": {"git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(), "floor_version": cfg["noise"]["floor_version"], "equiv_version": cfg["equiv"].get("version"),
                         "harness_version": cfg["equiv"].get("harness_version"), "calls_per_run": cfg["scale"]["budget"]["llm_calls_per_run"]}}
    data["completion"] = section_completion(cfg, conn, cd, view, tier_of)
    data["criterion"] = section_criterion(cfg, conn, runs, cands, designs, complete, tier_of, default_basis)
    data["reachability"] = data["criterion"]["reachability"]
    data["arms"] = {"pooled": arm_table(cfg, runs, cands, designs, set(complete), mat),
                    "by_tier": {t: arm_table(cfg, runs, cands, designs, {d for d in complete if tier_of.get(d) == t}, mat) for t in ("large", "medium", "small") if any(tier_of.get(d) == t for d in complete)}}
    data["large"] = section_large(cfg, conn, runs, cands, designs, complete, mat)
    data["large"]["prescreened_total"] = sum(v["n"] for v in data["large"]["prescreened"].values())
    data["large"]["prescreened_all_large"] = conn.execute("SELECT COUNT(*) FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase5' AND COALESCE(c.prescreened,0)=1").fetchone()[0]
    data["mechanism"] = section_mechanism(cfg, conn, runs, cands, set(complete), tier_of)
    lb = RP.proof_latency_bound(conn, cfg)
    lbd = {}
    for d, val in sorted(lb.items()):
        med = float(val["median_s"]) if isinstance(val, dict) else float(val)
        e, tot, per = RP.archive_empty_summary(val)
        lbd[d] = {"tier": tier_of.get(d), "median_min": med / 60.0, "empty": (f"{e} of {tot} ({per})" if tot else "all builds"), "complete": d in complete}
    ex = section_criterion(cfg, conn, runs, cands, designs, complete, tier_of, default_basis, exclude=set(lbd))
    data["latency_bound"] = {"window_s": 1800, "designs": lbd, "tally_excluding": ex["per_mode"]["decided"]["tally"],
                             "tally_excluding_as_run": ex["per_mode"]["as_run"]["tally"], "n_after": sum(ex["per_mode"]["decided"]["tally"].values())}
    zp = [d for d in complete if not any(c["design_id"] == d and c.get("verdict") == "proven" for c in cands)]
    data["zero_proven"] = {"n": len(zp), "designs": zp}
    data["designs"] = section_designs(cfg, conn, runs, cands, designs, data["criterion"], complete, tier_of, default_basis)
    mc = {}
    for arm in ARMS:
        rows = {k.split("|")[1]: v for k, v in data["arms"]["pooled"].items() if k.split("|")[0] == arm}
        if len(rows) > 1:
            mc[arm] = dict(rows, designs=max(v["designs"] for v in rows.values()))
    data["model_contrast"] = mc
    pend_pre = sum(v["n"] for v in data["large"]["prescreened"].values())
    data["missing"] = [
        {"item": "incomplete designs", "detail": f"{len(data['completion']['incomplete'])} of the 30 designs still have runs running or queued (medium and the whole small tier)", "owner": "queue / lanes", "stage": "Stage B, then Stage C"},
        {"item": "the prescreened candidates' proofs", "detail": f"{pend_pre} prescreened large-tier candidates have sim + E4 but no SEQ proof; the pool's proofs open after the small tier's search runs (offline_pool.proofs_enabled)", "owner": "offline pool", "stage": "after Stage C's runs"},
        {"item": "replacement runs", "detail": "the 6 LSTM M runs (harness_fix, prescreen off) are created but not launched; simple_spi and router carry harness-version-1 records whose D2 re-verification waits for the pool's proofs", "owner": "queue", "stage": "Stage B / C"},
        {"item": "the small tier", "detail": "126 runs queued, no candidate evaluated yet — every small-tier row prints pending", "owner": "queue", "stage": "Stage C"},
        {"item": "hidden-configuration evaluation", "detail": "the criterion is stated over the hidden configurations (H1, H2a, H2b, H3, H4, H5); the results are sealed until PHASE5_COMPLETE and are read only by scripts/report_hidden.py", "owner": "operator after the marker", "stage": "after Phase 5"},
        {"item": "Phase 6 ablations", "detail": "no map prior and the verdict-synchronous cadence are listed in PLAN 6.1 / config ablations.variants but not implemented or run", "owner": "Phase 6", "stage": "Phase 6"},
        {"item": "SAIF baselines of the 13 default-basis designs", "detail": "done for all 13 (evaluations.offline_baseline = 1, REQUEST (e) item 2); the power figures of this report still use the search basis, the SAIF-basis recomputation is reports/paper_sec3_power_basis_saif.md", "owner": "operator", "stage": "reported beside, not in place of"},
    ]
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
