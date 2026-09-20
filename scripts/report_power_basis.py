#!/usr/bin/env python3
"""REQUEST 2026-09-20 (e) — power basis on the designs whose D has no SAIF power at E4: the Phase 5 Section III tables
(reports/paper_sec3.md §G and the C1 report's Phase 5 tables) recomputed (item 1) in two versions — (a) area + WNS only on those
designs and SAIF-basis power elsewhere, (b) per metric everywhere — with the count of currently retained candidates on those designs
that are power-only and become noise under (a); the class-(b) flip-flop-count sub-population with its retention (item 4); mc_rf's D
outlier across the rungs (item 5). Read-only: the frozen phase4 floors, the verdict definitions and every record are unchanged;
nothing is read from the hidden database. Rule A throughout (src.analysis.phase5.uniform_diagnosis on the candidate's E4 record).

  python3 scripts/report_power_basis.py [--basis search|offline_saif] [--limit N]

--basis offline_saif (item 2, once the offline pool has made D's SAIF-basis E4 record, evaluations.offline_baseline = 1): D's SAIF
power replaces the default-activity baseline in every comparison and the report lists, per design, how many candidate power verdicts
change against the search basis. Outputs reports/paper_sec3_power_basis[_saif].md and reports/data/paper_sec3_power_basis[_saif].json.
"""
import argparse
import collections
import copy
import datetime
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.analysis import phase5 as P5  # noqa: E402
from src.diagnose import m3  # noqa: E402

_spec = importlib.util.spec_from_file_location("report_c1", os.path.join(ROOT, "scripts", "report_c1.py"))
C1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C1)

METRICS = ("area", "power", "wns")
VERSIONS = (("current", "rule A as reported (all metrics, the search's power basis)"),
            ("a", "(a) power excluded on the default-basis designs; elsewhere power only when both records carry SAIF power"),
            ("area", "(b) area only"), ("wns", "(b) WNS only"), ("power", "(b) power only (basis marked)"))
LABELS = ("retained", "tradeoff", "absorbed_identical", "absorbed", "noise", "harmful", "fragile")
CLASSES = ("a", "b", "c1", "c2", "d", "free", "?")
SOURCES = {}


def src(name, text):
    SOURCES[name] = text
    return text


def pct(x, nd=1):
    return "—" if x is None else f"{100 * float(x):.{nd}f} %"


def rate(n, d):
    return (n / d) if d else None


# ----------------------------------------------------------------------------- relabeling
def strip_metrics(rec, keep):
    """A copy of a diagnoser record with every metric outside `keep` removed (the gain vector then has only the kept metrics)."""
    r = copy.deepcopy(rec)
    m = r.get("metrics") or {}
    if "area" not in keep:
        m["area"] = None
        m["area_um2"] = None
    if "wns" not in keep:
        m["wns_ns"] = None
    if "power" not in keep:
        m["power_saif_mw"] = None
        m["power_default_mw"] = None
    return r


def diag(designs, d, base, rec):
    out = m3.diagnose(base, rec, d["sigma"], d["phi"], v3_status="proven", k_sigma=designs.k_sigma, thresholds=d["thresholds"], floor_class=d["floor_class"])
    ev = out.get("evidence") or {}
    return {"label": out.get("label"), "gains": ev.get("gains") or {}, "basis": ev.get("power_basis")}


def versions_of(designs, conn, row, default_basis):
    """{version: {label, gains, basis}} of one evaluated candidate; absorbed_identical / duplicate (the netlist is D's or an earlier
    candidate's) keep their label in every version."""
    d = designs.get(row["design_id"])
    ev = conn.execute("SELECT * FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (row["cand_id"],)).fetchone()
    if ev is None or not d["base"]:
        return None
    rec = P5.record_from_row(ev)
    cur = diag(designs, d, d["base"], rec)
    out = {"current": cur}
    if cur["label"] in ("absorbed_identical", "duplicate"):
        for v, _ in VERSIONS[1:]:
            out[v] = dict(cur)
        return out
    if cur["basis"] == "saif" and row["design_id"] not in default_basis:
        out["a"] = dict(cur)
    else:
        out["a"] = diag(designs, d, d["base"], strip_metrics(rec, {"area", "wns"}))
    for m in METRICS:
        out[m] = diag(designs, d, d["base"], strip_metrics(rec, {m}))
    return out


# ----------------------------------------------------------------------------- tables
def material(gains, mat):
    return C1.material(gains or {}, mat)


def class_table(rows, v, mat):
    t = {}
    for cls in CLASSES:
        rc = [r for r in rows if (r.get("class_final") or "?") == cls]
        if not rc:
            continue
        cnt = collections.Counter(r["v"][v]["label"] for r in rc)
        ret = [r for r in rc if r["v"][v]["label"] == "retained"]
        surv = [r for r in rc if r["v"][v]["label"] in ("retained", "tradeoff")]
        m_any = sum(1 for r in ret if material(r["v"][v]["gains"], mat)[0] and not material(r["v"][v]["gains"], mat)[1])
        t[cls] = {"n": len(rc), "labels": {l: cnt[l] for l in LABELS if cnt.get(l)}, "retained": len(ret), "retained_rate": rate(len(ret), len(rc)),
                  "survival": len(surv), "survival_rate": rate(len(surv), len(rc)), "material_any": m_any, "material_rate": rate(m_any, len(rc)),
                  "material_per_metric": {m: sum(1 for r in ret if m in material(r["v"][v]["gains"], mat)[0]) for m in METRICS}}
    return t


def family_table(rows, v, mat):
    fam = {}
    for f in ("Dr.RTL", "CktEvo", "RTL-OPT"):
        rf = [r for r in rows if C1.family(r["design_id"]) == f]
        ret = [r for r in rf if r["v"][v]["label"] == "retained"]
        fam[f] = {"evaluated": len(rf), "retained": len(ret), "retained_rate": rate(len(ret), len(rf)),
                  "material": sum(1 for r in ret if material(r["v"][v]["gains"], mat)[0] and not material(r["v"][v]["gains"], mat)[1]),
                  "designs": len({r["design_id"] for r in rf})}
    return fam


def per_design_table(rows, tier_of, default_basis, mat):
    out = {}
    for d in sorted({r["design_id"] for r in rows}, key=lambda x: ({"large": 0, "medium": 1, "small": 2}.get(tier_of.get(x), 3), x)):
        rd = [r for r in rows if r["design_id"] == d]
        by_arm = {}
        for arm in sorted({r["arm"] for r in rd}):
            ra = [r for r in rd if r["arm"] == arm]
            e = {"evaluated": len(ra)}
            for v, _ in VERSIONS:
                ret = [r for r in ra if r["v"][v]["label"] == "retained"]
                e[v] = {"retained": len(ret), "material": sum(1 for r in ret if material(r["v"][v]["gains"], mat)[0] and not material(r["v"][v]["gains"], mat)[1])}
            e["power_basis"] = dict(collections.Counter(str(r["v"]["power"]["basis"]) for r in ra))
            by_arm[arm] = e
        out[d] = {"tier": tier_of.get(d), "default_basis": d in default_basis, "by_arm": by_arm,
                  "totals": {v: sum(a[v]["retained"] for a in by_arm.values()) for v, _ in VERSIONS}, "evaluated": len(rd)}
    return out


def b0_tables(rows5, ev_rows, conn, designs):
    """The B0 Yosys-vs-E4 any-metric cross of §G (candidates.label = the run's Y-caliber verdict against the rule-A label) under the
    current rule and under (a); per metric from the (b) versions."""
    src("B0 Yosys vs E4", "candidates.label of the B0 arm (improved = a positive Y-caliber component, Yosys + OpenSTA, spec 05 §5) against the rule-A label of the same proven candidate's E4 record under each version; proven candidates without an E4 record are pending (e4_pending / dc_rejected as in paper_sec3.md §G)")
    b0 = [r for r in rows5 if r["arm"] == "B0" and r["verdict"] == "proven" and r["state"] in ("evaluated", "e4_pending", "dc_rejected")]
    byid = {r["cand_id"]: r for r in ev_rows}
    out = {"n_b0_proven": len(b0)}
    for v in ("current", "a"):
        cross = collections.Counter()
        for r in b0:
            lab = byid[r["cand_id"]]["v"][v]["label"] if r["cand_id"] in byid else r["state"]
            cross[(r.get("label") or "none", lab)] += 1
        out[v] = {f"{k[0]}|{k[1]}": n for k, n in sorted(cross.items())}
    per_metric = {}
    for m in METRICS:
        c = collections.Counter()
        for r in b0:
            if r["cand_id"] not in byid:
                c["pending"] += 1
                continue
            vm = byid[r["cand_id"]]["v"][m]
            key = f"{r.get('label') or 'none'} -> {vm['label']}" + (f" ({vm['basis']})" if m == "power" else "")
            c[key] += 1
        per_metric[m] = dict(sorted(c.items()))
    out["per_metric"] = per_metric
    return out


def power_only_losses(ev_rows, default_basis, mat):
    """Currently retained candidates on the default-basis designs whose only metric above the floor is power: under (a) they are
    noise (or absorbed). Per design and per arm, with the material subset (power gain above 2 %)."""
    per_design, per_arm, per_design_arm = collections.Counter(), collections.Counter(), collections.defaultdict(collections.Counter)
    mat_n = 0
    to = collections.Counter()
    n_ret = 0
    for r in ev_rows:
        if r["design_id"] not in default_basis:
            continue
        if r["v"]["current"]["label"] != "retained":
            continue
        n_ret += 1
        if r["v"]["a"]["label"] != "retained":
            per_design[r["design_id"]] += 1
            per_arm[r["arm"]] += 1
            per_design_arm[r["design_id"]][r["arm"]] += 1
            to[r["v"]["a"]["label"]] += 1
            if "power" in material(r["v"]["current"]["gains"], mat)[0]:
                mat_n += 1
    return {"retained_on_default_basis_designs": n_ret, "power_only": sum(per_design.values()), "becomes": dict(to), "material_power": mat_n,
            "per_design": dict(sorted(per_design.items())), "per_arm": dict(sorted(per_arm.items())),
            "per_design_arm": {d: dict(c) for d, c in sorted(per_design_arm.items())}}


def default_pairs_elsewhere(ev_rows, default_basis):
    """Candidates on SAIF-basis designs whose own record carries no SAIF power (the pair falls to the default basis): under (a) power
    is excluded for them too. Per design: pairs, currently retained, and how many of those stay retained under (a)."""
    out = {}
    for r in ev_rows:
        if r["design_id"] in default_basis or r["v"]["current"]["basis"] != "default":
            continue
        e = out.setdefault(r["design_id"], {"default_pairs": 0, "retained_current": 0, "retained_a": 0})
        e["default_pairs"] += 1
        e["retained_current"] += int(r["v"]["current"]["label"] == "retained")
        e["retained_a"] += int(r["v"]["a"]["label"] == "retained")
    return dict(sorted(out.items()))


# ----------------------------------------------------------------------------- item 4: class definitions and the re-encoding sub-population
def item4(conn, ev_rows):
    src("item 4", "rules v2 as implemented (src/classify/rules.py classify(); docs/spec/04 §A.1): Phase 4 objects from reports/data/phase4_exp1.json objects[] (verdict proven / proven_sim_only, label = rule A at E4 under the frozen floors) joined with candidates.subtags_json; Phase 5 evaluated candidates from the scan with their normalised evidence tags (report_c1.norm_subtag)")
    p4 = json.load(open(os.path.join(ROOT, "reports", "data", "phase4_exp1.json")))
    objs = [o for o in p4["objects"] if o.get("verdict") in ("proven", "proven_sim_only") and o.get("label") and o["label"] != "duplicate" and (o.get("gains") or {}).get("E4")]

    def kinds(tags):
        return {C1.norm_subtag(t) for t in tags if isinstance(t, str)}
    p4_rows = []
    for o in objs:
        r = conn.execute("SELECT subtags_json, class_final, class_rule FROM candidates WHERE cand_id=?", (o["cand_id"],)).fetchone()
        try:
            tags = json.loads(r["subtags_json"] or "[]") if r else []
        except (ValueError, TypeError):
            tags = []
        p4_rows.append({"cls": o.get("cls"), "label": o.get("label"), "tags": kinds(tags), "design_id": o["design_id"], "cand_id": o["cand_id"]})
    WID, CELLS = "register widths changed, same cells", "flip-flop count and register cells changed"

    def sub(rows, cls_key, lab_key):
        b = [r for r in rows if r[cls_key] == "b"]
        b_re = [r for r in b if WID in r["tags"]]
        b_same = [r for r in b if WID not in r["tags"]]
        c1 = [r for r in rows if r[cls_key] == "c1"]
        c1_cells = [r for r in c1 if CELLS in r["tags"]]
        f = lambda rs: {"n": len(rs), "retained": sum(1 for r in rs if r[lab_key] == "retained"), "retained_rate": rate(sum(1 for r in rs if r[lab_key] == "retained"), len(rs))}
        return {"b_all": f(b), "b_reencoding_ff_count_changed": f(b_re), "b_ff_count_unchanged": f(b_same), "c1_all": f(c1), "c1_with_cells_tag": f(c1_cells)}
    out = {"rules_v2": {
        "b": "class (b), latency-preserving coding / structural refactor: V2 identical every cycle (no lock-step offset), no (d) evidence (no operator family gained, combinational depth ratio below classify.d_depth_ratio), and either the register names / clocked targets change with the flip-flop bit count unchanged, or the flip-flop bits change while the number of register cells is unchanged (bit widths may change inside the same cells) — evidence tag \"flip-flop bits N -> M in the same register cells (widths), latency unchanged\"",
        "c1": "class (c1), latency-preserving sequential restructuring: V2 identical every cycle, no (d) evidence, and the flip-flop bits AND the number of register cells both change (ff_c != ff_d and reg_cells_c != reg_cells_d, registers cross logic, are duplicated, merged or removed) — evidence tag \"flip-flop bits N -> M and register cells K -> L with identical latency (no offset)\"",
        "counting": "flip-flop bits and register cells counted by Yosys after `proc; flatten; opt` (memories included); precedence in classify(): offset > 0 -> c2; operator family gained or depth ratio -> d; bits and registers unchanged -> a; bits and cells changed -> c1; else b",
        "source": "src/classify/rules.py classify() (RULES_VERSION 2, DECISIONS 2026-09-14 / 2026-09-15); docs/spec/04-classifier-diagnoser.md §A.1"},
        "phase4_objects": {"n": len(p4_rows), **sub(p4_rows, "cls", "label")},
        "phase5_evaluated": {"all": {"n": len(ev_rows), **sub([{"cls": r.get("class_final"), "label": r["v"]["current"]["label"], "tags": set(r["tags"] or [])} for r in ev_rows], "cls", "label")}}}
    for t in ("large", "medium", "small"):
        rt = [{"cls": r.get("class_final"), "label": r["v"]["current"]["label"], "tags": set(r["tags"] or [])} for r in ev_rows if r["tier"] == t]
        out["phase5_evaluated"][t] = {"n": len(rt), **sub(rt, "cls", "label")}
    fsm = {}
    for cid in ("c634baa4b8fa859", "c92a0b6177cf6f6"):
        r = conn.execute("SELECT design_id, class_final, subtags_json, label FROM candidates WHERE cand_id=?", (cid,)).fetchone()
        if r:
            fsm[cid] = {"design_id": r["design_id"], "class_final": r["class_final"], "tags": sorted(kinds(json.loads(r["subtags_json"] or "[]"))), "in_reencoding_subpopulation": WID in kinds(json.loads(r["subtags_json"] or "[]"))}
    out["fsm_objects"] = fsm
    return out


# ----------------------------------------------------------------------------- item 5: mc_rf across the rungs
def item5(conn, design="cktevo_mem_ctrl__mc_rf"):
    src("item 5", f"evaluations of {design} at Φ_main (designs.phi_main_ns_nangate45): D = is_baseline 1, pert_id / cand_id NULL, status ok (SAIF-backed record preferred, latest among equals); perturbations = status ok records joined with perturbations.seq_status in (proven, proven_rename); one record per (perturbation, config) counted — distinct areas with their counts")
    phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (design,)).fetchone()[0]
    out = {"design": design, "phi": phi, "configs": {}}
    for cfgn in ("E1", "E2", "E3", "E4"):
        b = conn.execute("SELECT eval_id, area_um2, cells, power_saif_mw, power_default_mw FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' "
                         "AND abs(clock_ns-?)<1e-6 ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (design, cfgn, phi)).fetchone()
        recs = [dict(r) for r in conn.execute("SELECT e.pert_id, e.area_um2, e.cells, p.ptype, p.seq_status FROM evaluations e JOIN perturbations p ON p.pert_id=e.pert_id WHERE e.design_id=? AND e.config=? AND e.status='ok' "
                                              "AND abs(e.clock_ns-?)<1e-6 AND p.seq_status IN ('proven','proven_rename') ORDER BY e.eval_id", (design, cfgn, phi))]
        latest = {}
        for r in recs:
            latest[r["pert_id"]] = r   # the latest record per perturbation
        recs = list(latest.values())
        if b is None:
            out["configs"][cfgn] = {"baseline": None, "n_records": len(recs)}
            continue
        ba = float(b["area_um2"])
        areas = collections.Counter(round(float(r["area_um2"]), 3) for r in recs)
        deltas = [(float(r["area_um2"]) - ba) / ba for r in recs]
        same_as_d = sum(1 for r in recs if abs(float(r["area_um2"]) - ba) < 1e-6)
        out["configs"][cfgn] = {"baseline": {"eval_id": b["eval_id"], "area_um2": ba, "cells": b["cells"], "power_saif_mw": b["power_saif_mw"]},
                                "n_records": len(recs), "records_at_d_area": same_as_d, "d_unique": same_as_d == 0,
                                "distinct_areas": [{"area_um2": a, "n": n, "delta_vs_d": (a - ba) / ba} for a, n in sorted(areas.items(), key=lambda kv: -kv[0])],
                                "delta_min": min(deltas) if deltas else None, "delta_max": max(deltas) if deltas else None,
                                "all_above_d": bool(deltas) and min(deltas) > 0}
    e4 = out["configs"].get("E4") or {}
    if e4.get("baseline"):
        ba = e4["baseline"]["area_um2"]
        plateau_hi = [x for x in e4["distinct_areas"] if abs(x["area_um2"] - 2816.4) < 1.0]
        out["e4_plateaus"] = {"at_2816_4": sum(x["n"] for x in plateau_hi), "at_17_4_pct": sum(x["n"] for x in e4["distinct_areas"] if abs(x["delta_vs_d"] - 0.174) < 0.002),
                              "between": sum(x["n"] for x in e4["distinct_areas"] if abs(x["area_um2"] - 2816.4) >= 1.0 and abs(x["delta_vs_d"] - 0.174) >= 0.002), "n_records_plus_d": e4["n_records"] + 1}
    return out


# ----------------------------------------------------------------------------- render
def render(data):
    v = data["versions"]
    mat = data["materiality"]
    dp = data["default_power_basis"]
    L = [f"# Power basis and per-metric retention — Phase 5 Section III tables recomputed ({data['date']}; visible layer only; interim)", "",
         f"Generated {data['generated_at']} by scripts/report_power_basis.py (git {v['git_sha']}, cfg {v['cfg_hash']}); floor_version **{v['floor_version']}**, equiv_version {v['equiv_version']}, "
         f"harness_version {v['harness_version']}; baseline basis **{data['basis']}**" + (f"; floors: **{data['floor_version_preferred']}** where measured, the frozen table elsewhere ({sum(1 for x in (data.get('floors_used') or {}).values() if x['floor_version'] == data['floor_version_preferred'])} designs on the preferred table)" if data.get("floor_version_preferred") else "") +
         f". REQUEST 2026-09-20 (e) items 1, 4, 5. Rule A on each candidate's E4 record (uniform_diagnosis); duplicates collapsed "
         f"(spec 04 §B step 3); every retention figure carries its materiality count (area > {pct(mat['area'], 0)}, power > {pct(mat['power'], 0)}, WNS > {pct(mat['wns'], 0)} of the period). "
         f"No record, default or configuration was altered; results/hidden was not read. Phase 5 state at generation: runs {data['phase5_runs']}; evaluated (proven with E4) {data['n_evaluated']}, "
         f"pending E4 {data['n_e4_pending']}, DC rejected {data['n_dc_rejected']}, duplicates collapsed {data['n_duplicates']}.", ""]
    L += ["## 0a. Power basis marks (item 1)", "",
          f"Designs whose D has no SAIF power at E4 (the evaluators' baseline, is_baseline = 1 at Φ_main): **{len(dp)}** — " + ", ".join(dp) + ".", "",
          f"For each of them: *{P5.DEFAULT_POWER_NOTE}* (m3.power_basis compares default with default; the candidates' SAIF figures on these designs have no D counterpart).", "",
          f"The pooled-floor designs of the frozen table (PLAN 6.9, item 3 of the request): {len(data['pooled_floor_designs'])} — " + ", ".join(data["pooled_floor_designs"]) + ". "
          f"The two lists differ by one design each: {', '.join(sorted(set(data['pooled_floor_designs']) - set(dp))) or 'none'} has a measured floor basis question only on power (D carries SAIF power); "
          f"{', '.join(sorted(set(dp) - set(data['pooled_floor_designs']))) or 'none'} has a measured floor (its P1_text perturbations) but no D SAIF.", ""]
    L += ["## 1. Versions", ""] + [f"- **{k}** — {desc}" for k, desc in VERSIONS] + ["",
          "Under (a) a candidate whose only metric above its floor was power is labelled by area and WNS alone (noise, or absorbed when its E4 fingerprint converges with D's); a trade-off whose only metric below the floor was power becomes retained. "
          "Under (b) each metric is judged alone: retained = that metric above t_D, harmful = below −t_D, noise otherwise, absorbed when the fingerprint converges; absorbed_identical (D's netlist) keeps its label in every version. "
          "The power-only column marks the basis of each pair: saif (both records SAIF-backed), default (DC default activity on both), None (no power comparison possible).", ""]

    def class_block(title, tabs):
        L.append(f"### {title}")
        L.append("")
        L.append("| class | n | " + " | ".join(f"retained {k} (material)" for k, _ in VERSIONS) + " | labels under (a) |")
        L.append("|---|---|" + "---|" * len(VERSIONS) + "---|")
        classes = [c for c in CLASSES if any(c in tabs[k] for k, _ in VERSIONS)]
        for cls in classes:
            cells = []
            for k, _ in VERSIONS:
                t = tabs[k].get(cls)
                cells.append("—" if not t else f"{t['retained']} / {t['n']} = {pct(t['retained_rate'])} ({t['material_any']})")
            ta = tabs["a"].get(cls) or {}
            L.append(f"| {cls} | {(tabs['current'].get(cls) or {}).get('n', 0)} | " + " | ".join(cells) + " | " + ", ".join(f"{l} {n}" for l, n in (ta.get("labels") or {}).items()) + " |")
        L.append("")
    L += ["## 2. Class × verdict per tier and pooled (paper_sec3.md §G (i); C1 §2.2)", ""]
    for t in ("large", "medium", "small"):
        if data["class_tables"]["by_tier"].get(t) and data["class_tables"]["by_tier"][t]["current"]:
            class_block(f"{t} tier (evaluated {data['class_tables']['n_by_tier'][t]})", data["class_tables"]["by_tier"][t])
    class_block(f"pooled over the started tiers (evaluated {data['n_evaluated']})", data["class_tables"]["pooled"])
    L += ["## 3. The family table (paper_sec3.md §G (ii))", "",
          "| family | designs | evaluated | " + " | ".join(f"retained {k} (material)" for k, _ in VERSIONS) + " |", "|---|---|---|" + "---|" * len(VERSIONS)]
    for f in ("Dr.RTL", "CktEvo", "RTL-OPT"):
        cur = data["families"]["current"][f]
        L.append(f"| {f} | {cur['designs']} | {cur['evaluated']} | " + " | ".join(f"{data['families'][k][f]['retained']} = {pct(data['families'][k][f]['retained_rate'])} ({data['families'][k][f]['material']})" for k, _ in VERSIONS) + " |")
    L += ["", "## 4. Per-design retained counts (C1 §4 rows; every evaluated design, by arm)", "",
          "| design | tier | basis | arm | evaluated | " + " | ".join(f"retained {k}" for k, _ in VERSIONS) + " | power pairs by basis |", "|---|---|---|---|---|" + "---|" * len(VERSIONS) + "---|"]
    for d, e in data["per_design"].items():
        for arm, a in e["by_arm"].items():
            L.append(f"| {d} | {e['tier']} | {'default' if e['default_basis'] else 'saif'} | {arm} | {a['evaluated']} | " + " | ".join(f"{a[k]['retained']} ({a[k]['material']})" for k, _ in VERSIONS) +
                     f" | {', '.join(f'{b} {n}' for b, n in sorted(a['power_basis'].items()))} |")
        L.append(f"| {d} | {e['tier']} | | **all arms** | {e['evaluated']} | " + " | ".join(str(e['totals'][k]) for k, _ in VERSIONS) + " | |")
    po = data["power_only_losses"]
    L += ["", "## 5. Retained candidates on the default-basis designs that are power-only (item 1: become noise under (a))", "",
          f"Currently retained on the {len(dp)} default-basis designs: {po['retained_on_default_basis_designs']}; power-only among them: **{po['power_only']}** "
          f"(under (a): {', '.join(f'{l} {n}' for l, n in po['becomes'].items()) or 'none'}); with a power gain above the materiality threshold: {po['material_power']}.", "",
          ]
    if po["per_arm"]:
        L += ["| design | " + " | ".join(sorted(po["per_arm"])) + " | total |", "|---|" + "---|" * len(po["per_arm"]) + "---|"]
        for d, c in po["per_design_arm"].items():
            L.append(f"| {d} | " + " | ".join(str(c.get(a, 0)) for a in sorted(po["per_arm"])) + f" | {sum(c.values())} |")
        L.append("| **per arm** | " + " | ".join(str(po["per_arm"][a]) for a in sorted(po["per_arm"])) + f" | {po['power_only']} |")
    else:
        L.append("(none)")
    dpe = data["default_pairs_elsewhere"]
    L += ["", f"Default-basis pairs on SAIF-basis designs (the candidate's own record carries no SAIF power; power excluded for them under (a) as well): {sum(e['default_pairs'] for e in dpe.values())} pairs on {len(dpe)} designs, "
          f"currently retained {sum(e['retained_current'] for e in dpe.values())}, retained under (a) {sum(e['retained_a'] for e in dpe.values())}.", ""]
    if dpe:
        L += ["| design | default-basis pairs | retained (current) | retained (a) |", "|---|---|---|---|"] + [f"| {d} | {e['default_pairs']} | {e['retained_current']} | {e['retained_a']} |" for d, e in dpe.items()] + [""]
    b0 = data["b0"]
    L += ["## 6. B0: Yosys-caliber label against rule A at E4 (paper_sec3.md §G (iii))", "", f"Proven B0 candidates {b0['n_b0_proven']} (E4 pending / DC rejected rows stay as states).", "",
          "| Y label \\| E4 label | current | (a) |", "|---|---|---|"]
    keys = sorted(set(b0["current"]) | set(b0["a"]))
    for k in keys:
        L.append(f"| {k} | {b0['current'].get(k, 0)} | {b0['a'].get(k, 0)} |")
    L += ["", "Per metric (version (b)): Y label -> rule-A label on that metric alone.", ""]
    for m in METRICS:
        L.append(f"- **{m}**: " + ", ".join(f"{k} {n}" for k, n in b0["per_metric"][m].items()))
    if data.get("saif_changes"):
        sc = data["saif_changes"]
        L += ["", "## 7. Candidate power verdicts on the SAIF basis versus the search basis (item 2)", "",
              "| design | evaluated | power label changed | retained current -> retained (SAIF basis) | power-only under SAIF |", "|---|---|---|---|---|"]
        for d, e in sc.items():
            L.append(f"| {d} | {e['evaluated']} | {e['power_label_changed']} | {e['retained_current']} -> {e['retained_saif']} | {e['power_only_saif']} |")
    i4 = data["item4"]
    L += ["", "## 8. Class definitions and the re-encoding sub-population (item 4)", "", f"- (b): {i4['rules_v2']['b']}", f"- (c1): {i4['rules_v2']['c1']}", f"- counting: {i4['rules_v2']['counting']}", f"- source: {i4['rules_v2']['source']}", "",
          "| population | n | class (b) all | (b) with flip-flop count changed (re-encodings) | (b) flip-flop count unchanged | (c1) all |", "|---|---|---|---|---|---|"]

    def row(name, s):
        f = lambda x: f"{x['retained']} / {x['n']} = {pct(x['retained_rate'])}"
        return f"| {name} | {s['n']} | {f(s['b_all'])} | {f(s['b_reencoding_ff_count_changed'])} | {f(s['b_ff_count_unchanged'])} | {f(s['c1_all'])} |"
    L.append(row("Phase 4 objects (proven, with E4)", i4["phase4_objects"]))
    L.append(row("Phase 5 evaluated, all started tiers", i4["phase5_evaluated"]["all"]))
    for t in ("large", "medium", "small"):
        if i4["phase5_evaluated"].get(t, {}).get("n"):
            L.append(row(f"Phase 5 evaluated, {t} tier", i4["phase5_evaluated"][t]))
    L += ["", "Retained = rule A at E4 (the frozen phase4 floors), current version. The two FSM objects of the addendum: " +
          "; ".join(f"{o['design_id']} ({cid}): class {o['class_final']}, in the re-encoding sub-population: {o['in_reencoding_subpopulation']}" for cid, o in i4["fsm_objects"].items()) + ".", ""]
    i5 = data["item5"]
    L += ["## 9. mc_rf: D's E4 result across the rungs (item 5)", "", f"Design {i5['design']} at Φ_main = {i5['phi']} ns.", "",
          "| rung | D area µm² (cells) | proven-perturbation records | records at D's area | D unique | δ range of the records vs D | distinct areas (n) |", "|---|---|---|---|---|---|---|"]
    for cfgn, e in i5["configs"].items():
        if not e.get("baseline"):
            L.append(f"| {cfgn} | — | {e['n_records']} | | | | |")
            continue
        b = e["baseline"]
        da = "; ".join(f"{x['area_um2']:.1f} ({x['n']}, {pct(x['delta_vs_d'], 2)})" for x in e["distinct_areas"])
        L.append(f"| {cfgn} | {b['area_um2']:.1f} ({b['cells']}) | {e['n_records']} | {e['records_at_d_area']} | {'yes' if e['d_unique'] else 'no'} | {pct(e['delta_min'], 2)} … {pct(e['delta_max'], 2)} | {da} |")
    if i5.get("e4_plateaus"):
        p = i5["e4_plateaus"]
        L += ["", f"E4: {p['n_records_plus_d']} records including D; within 1 µm² of 2 816.4 µm²: {p['at_2816_4']}; on the 17.4 % plateau: {p['at_17_4_pct']}; between: {p['between']}.", ""]
    L += ["## S. Sources", ""] + [f"- **{k}**: {t}" for k, t in data["sources"].items()] + [""]
    return "\n".join(L)


# ----------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--basis", choices=["search", "offline_saif"], default="search")
    ap.add_argument("--floor-version", default=None, help="item 3 sensitivity: prefer this floor table per design (phase6 where measured), the frozen table elsewhere")
    ap.add_argument("--limit", type=int, default=None, help="smoke test: relabel only the first N evaluated candidates")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    mat = {"area": cfg["noise"]["materiality"]["area"], "power": cfg["noise"]["materiality"]["power_saif"], "wns": cfg["noise"]["materiality"]["wns"]}
    held = [d for ds in cfg["exp5"]["starting_points"].values() for d in ds]
    tier_of = P5.tier_of_design(cfg)
    default_basis = P5.default_power_basis_designs(cfg, conn)
    data = {"date": a.date, "generated_at": datetime.datetime.now().isoformat(timespec="minutes"), "basis": a.basis, "materiality": mat,
            "versions": {"git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(), "floor_version": cfg["noise"]["floor_version"], "equiv_version": cfg["equiv"].get("version"), "harness_version": cfg["equiv"].get("harness_version")},
            "default_power_basis": default_basis, "pooled_floor_designs": P5.pooled_floor_designs(cfg, conn)}
    runs = collections.defaultdict(collections.Counter)
    for r in conn.execute("SELECT design_id, status, COUNT(*) AS n FROM runs WHERE exp='phase5' AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0 GROUP BY design_id, status"):
        runs[tier_of.get(r["design_id"], "?")][r["status"]] += r["n"]
    data["phase5_runs"] = {t: dict(c) for t, c in runs.items()}
    src("Phase 5 scan", "scripts/report_c1.scan_phase5: every non-superseded Phase 5 candidate of the started tiers; evaluated = proven with an ok E4 record; duplicates (label duplicate) collapsed")
    rows5, _ = C1.scan_phase5(cfg, conn, held)
    designs = P5._Designs(cfg, conn, basis=a.basis, floor_version=a.floor_version)
    data["floor_version_preferred"] = a.floor_version
    ev_rows = [r for r in rows5 if r["state"] == "evaluated"]
    if a.limit:
        ev_rows = ev_rows[:a.limit]
    out_rows = []
    for r in ev_rows:
        vs = versions_of(designs, conn, r, default_basis)
        if vs is None:
            continue
        r = dict(r)
        r["v"] = vs
        out_rows.append(r)
    ev_rows = out_rows
    data.update(n_evaluated=len(ev_rows), n_e4_pending=sum(1 for r in rows5 if r["state"] == "e4_pending"), n_dc_rejected=sum(1 for r in rows5 if r["state"] == "dc_rejected"),
                n_duplicates=sum(1 for r in rows5 if r["state"] == "duplicate"))
    src("class tables", "class_final × rule-A label per version; retained rate = retained / evaluated of the class; material = retained candidates with a gain above the materiality threshold on some metric of the version and none below")
    data["class_tables"] = {"by_tier": {t: {k: class_table([r for r in ev_rows if r["tier"] == t], k, mat) for k, _ in VERSIONS} for t in ("large", "medium", "small")},
                            "n_by_tier": {t: sum(1 for r in ev_rows if r["tier"] == t) for t in ("large", "medium", "small")},
                            "pooled": {k: class_table(ev_rows, k, mat) for k, _ in VERSIONS}}
    data["families"] = {k: family_table(ev_rows, k, mat) for k, _ in VERSIONS}
    data["per_design"] = per_design_table(ev_rows, tier_of, default_basis, mat)
    data["b0"] = b0_tables(rows5, ev_rows, conn, designs)
    data["power_only_losses"] = power_only_losses(ev_rows, default_basis, mat)
    data["default_pairs_elsewhere"] = default_pairs_elsewhere(ev_rows, default_basis)
    if a.basis == "offline_saif":   # item 2: against the search basis, per design
        search = P5._Designs(cfg, conn, basis="search")
        sc = {}
        for r in ev_rows:
            d = r["design_id"]
            if designs.get(d).get("basis") != "offline_saif":
                continue
            base_s = search.get(d)["base"]
            ev = conn.execute("SELECT * FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (r["cand_id"],)).fetchone()
            rec = P5.record_from_row(ev)
            cur_s = diag(search, search.get(d), base_s, rec)
            pw_s = diag(search, search.get(d), base_s, strip_metrics(rec, {"power"}))
            e = sc.setdefault(d, {"evaluated": 0, "power_label_changed": 0, "retained_current": 0, "retained_saif": 0, "power_only_saif": 0})
            e["evaluated"] += 1
            e["power_label_changed"] += int(pw_s["label"] != r["v"]["power"]["label"])
            e["retained_current"] += int(cur_s["label"] == "retained")
            e["retained_saif"] += int(r["v"]["current"]["label"] == "retained")
            e["power_only_saif"] += int(r["v"]["current"]["label"] == "retained" and r["v"]["a"]["label"] != "retained")
        data["saif_changes"] = dict(sorted(sc.items()))
        data["offline_baselines"] = {d: designs.get(d).get("base_eval_id") for d in default_basis if designs.get(d).get("basis") == "offline_saif"}
    if a.floor_version:   # item 3: which designs carry the preferred (measured) floor and their thresholds
        data["floors_used"] = {d: {"floor_version": designs.get(d).get("floor_version"), "t_d": designs.get(d)["thresholds"]} for d in sorted({r["design_id"] for r in ev_rows})}
    data["item4"] = item4(conn, ev_rows)
    data["item5"] = item5(conn)
    data["sources"] = SOURCES
    suffix = ("_saif" if a.basis == "offline_saif" else "") + (f"_{a.floor_version}" if a.floor_version else "")
    js = os.path.join(ROOT, "reports", "data", f"paper_sec3_power_basis{suffix}.json")
    md = os.path.join(ROOT, "reports", f"paper_sec3_power_basis{suffix}.md")
    slim = dict(data)
    with open(js, "w") as fh:
        json.dump(slim, fh, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    with open(md, "w") as fh:
        fh.write(render(data))
    print(f"written {md} and {js}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
