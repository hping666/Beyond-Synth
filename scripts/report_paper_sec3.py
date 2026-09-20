#!/usr/bin/env python3
"""Data for paper Section III "Measuring Retained Gain" (REQUEST 2026-09-20 (c); read-only, visible layer only — never opens
results/hidden). Writes reports/data/paper_sec3.json and reports/paper_sec3.md. Every number carries its source query or
collector call and its n; floor_version phase4 throughout; duplicates collapsed as in spec 04 §B step 3 (a candidate whose E4
fingerprint equals an earlier candidate's of the same run carries label `duplicate` and is never counted).
Sections: A Table I (noise floor, frozen phase4 table); B Fig. 3 (Phase 4 objects: survival per class and level); C O1 absorption
attribution; D O2 object details; E O3 static rule and predictor; F O5 RTL-OPT / RTLRewriter; G Phase 5 additions; H caveat numbers.
Run under nice: nice -n 19 .venv/bin/python3 scripts/report_paper_sec3.py
"""
import argparse
import collections
import datetime
import importlib.util
import json
import math
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.analysis import phase5 as P5  # noqa: E402
from src.analysis import objects as OBJ  # noqa: E402
from src.analysis import map as MAP  # noqa: E402

_spec = importlib.util.spec_from_file_location("report_c1", os.path.join(ROOT, "scripts", "report_c1.py"))
C1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C1)

LEVELS = ("E1", "E1d", "E2", "E2g", "E3", "E4")
CLASSES = ("a", "b", "c1", "c2", "d")
SOURCES = []


def src(name, text):
    SOURCES.append({"table": name, "source": text})
    return text


def pct(x, nd=1):
    return "-" if x is None else f"{100.0 * x:.{nd}f} %"


def rate(n, d):
    return None if not d else n / d


def q(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    pos = (len(xs) - 1) * p
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def weighted_quantile(pairs, p):
    """pairs = [(value, weight)]: the smallest value whose cumulative weight share reaches p (design-weighted pooling)."""
    pairs = sorted((v, w) for v, w in pairs if v is not None)
    tot = sum(w for _, w in pairs)
    if not tot:
        return None
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc / tot >= p - 1e-12:
            return v
    return pairs[-1][0]


# ----------------------------------------------------------------------------- A. Table I
def section_a(cfg, conn):
    fv = cfg["noise"]["floor_version"]
    out = {"floor_version": fv, "quiet_max_abs": cfg["noise"].get("quiet_max_abs"), "k_sigma": cfg["noise"]["k_sigma"]}
    out["definitions"] = {"source": "docs/spec/02-noise-floor.md (floor class) and reports/phase2.md §2 (rule A)",
                          "floor_class": "quiet (every |δ_area| ≤ noise.quiet_max_abs), offset (median |δ| above that and MAD ≈ 0: every perturbation shifted together), spread otherwise; stored next to the floor. A retained gain on an offset design is flagged",
                          "rule_A": "t_D = max(2.0 × σ_robust, the design's own max |δ| incl. P0, pooled q90); designs without a measured floor carry the pooled minimum (floor_source = pooled)",
                          "quiet_max_abs_value": cfg["noise"].get("quiet_max_abs")}
    src("A frozen floor table", f"SELECT design_id, floor_source, floor_class, t_d, pooled_min FROM noise_floor WHERE floor_version='{fv}' AND config='E4' AND metric='area' (one row per design; the table the Phase 5 experiments use)")
    rows = [dict(r) for r in conn.execute("SELECT design_id, floor_source, floor_class, t_d, pooled_min FROM noise_floor WHERE floor_version=? AND config='E4' AND metric='area'", (fv,))]
    out["designs_in_table"] = len(rows)
    out["measured"] = sum(1 for r in rows if r["floor_source"] == "measured")
    out["pooled"] = sum(1 for r in rows if r["floor_source"] != "measured")
    out["classes"] = dict(collections.Counter((r["floor_class"] or "pooled") for r in rows))
    out["pooled_min"] = {m: r[1] for m, r in [(m, conn.execute("SELECT metric, MAX(pooled_min) FROM noise_floor WHERE floor_version=? AND config='E4' AND metric=? AND pooled_min IS NOT NULL", (fv, m)).fetchone()) for m in ("area", "power_saif", "wns", "tns")]}
    src("A pooled minima", f"SELECT metric, MAX(pooled_min) FROM noise_floor WHERE floor_version='{fv}' AND config='E4' GROUP BY metric (the same value on every design row of the configuration and metric)")
    designs = [r["design_id"] for r in rows]
    marks = ",".join("?" * len(designs))
    # perturbation records of the table's designs at E1..E4 against the design's baseline of the same config and clock
    src("A perturbation records", "SELECT e.design_id, e.config, e.pert_id, p.ptype, e.area_um2, e.cells, e.wns_ns, e.power_saif_mw, e.clock_ns FROM evaluations e JOIN perturbations p ON p.pert_id=e.pert_id WHERE e.status='ok' AND e.config IN ('E1','E2','E3','E4') AND e.design_id IN (frozen-table designs); baseline = is_baseline=1, pert_id IS NULL, cand_id IS NULL, same config and clock")
    base = {}
    for r in conn.execute(f"SELECT design_id, config, clock_ns, area_um2, cells, wns_ns, power_saif_mw FROM evaluations WHERE is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' AND config IN ('E1','E2','E3','E4') AND design_id IN ({marks}) ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC", designs):
        base.setdefault((r["design_id"], r["config"], round(float(r["clock_ns"]), 4)), dict(r))
    recs = collections.defaultdict(list)   # config -> [(design, ptype, d_area, d_cells, area_rel, power_rel)]
    for r in conn.execute(f"SELECT e.design_id, e.config, e.pert_id, p.ptype, e.area_um2, e.cells, e.wns_ns, e.power_saif_mw, e.clock_ns FROM evaluations e JOIN perturbations p ON p.pert_id=e.pert_id WHERE e.status='ok' AND e.config IN ('E1','E2','E3','E4') AND e.design_id IN ({marks})", designs):
        b = base.get((r["design_id"], r["config"], round(float(r["clock_ns"]), 4)))
        if not b or not b["area_um2"]:
            continue
        area_rel = (float(r["area_um2"]) - float(b["area_um2"])) / float(b["area_um2"])
        prel = ((float(r["power_saif_mw"]) - float(b["power_saif_mw"])) / float(b["power_saif_mw"])) if (b["power_saif_mw"] and r["power_saif_mw"] is not None) else None
        recs[r["config"]].append({"design": r["design_id"], "ptype": r["ptype"], "area_rel": area_rel, "cells_same": (r["cells"] == b["cells"]), "area_same": abs(float(r["area_um2"]) - float(b["area_um2"])) < 1e-6, "power_rel": prel})
    e4 = recs["E4"]
    out["records"] = {c: len(v) for c, v in recs.items()}
    out["designs_with_records_E4"] = len({x["design"] for x in e4})
    out["unchanged_E4"] = {"n": len(e4), "unchanged": sum(1 for x in e4 if x["area_same"] and x["cells_same"]), "share": rate(sum(1 for x in e4 if x["area_same"] and x["cells_same"]), len(e4)), "phase2": "88 % (reports/phase2.md §6 G1, 99 designs)"}
    ren = {}
    for c in ("E1", "E4"):
        rr = [x for x in recs[c] if x["ptype"] == "P1_rename"]
        ren[c] = {"n": len(rr), "changed": sum(1 for x in rr if not (x["area_same"] and x["cells_same"])), "share": rate(sum(1 for x in rr if not (x["area_same"] and x["cells_same"])), len(rr))}
    out["rename_changes"] = {**ren, "phase2": "E1 29 %, E4 5 % (reports/phase2.md §6 G1)"}
    by_design_max = collections.defaultdict(float)
    for x in e4:
        by_design_max[x["design"]] = max(by_design_max[x["design"]], abs(x["area_rel"]))
    out["tail_designs_E4"] = {"designs_with_records": len(by_design_max), "over_1pct": sum(1 for v in by_design_max.values() if v > 0.01), "over_5pct": sum(1 for v in by_design_max.values() if v > 0.05), "max": max(by_design_max.values()) if by_design_max else None,
                              "phase2": "18 of 99 > 1 %, 9 > 5 %, max 18.7 % (reports/phase2.md §6 G1)"}
    abs_area = [(abs(x["area_rel"]), x["design"]) for x in e4]
    per_design_n = collections.Counter(d for _, d in abs_area)
    out["pooled_quantiles_E4_area"] = {"design_weighted": {p: weighted_quantile([(v, 1.0 / per_design_n[d]) for v, d in abs_area], p) for p in (0.90, 0.95, 0.99)},
                                       "record_weighted": {p: q([v for v, _ in abs_area], p) for p in (0.90, 0.95, 0.99)}, "n_records": len(abs_area), "n_designs": len(per_design_n),
                                       "note": "design-weighted: each design's records weighted 1 / n_design (reports/data/phase2_noise_floor.json pooled_weighting = design); the frozen pooled minimum is the design-weighted q90 of the phase4 snapshot"}
    big = max(e4, key=lambda x: abs(x["area_rel"])) if e4 else None
    out["largest_effect_E4"] = ({"design": big["design"], "ptype": big["ptype"], "area_rel": big["area_rel"], "power_rel": big["power_rel"]} if big else None)
    out["largest_effect_phase2"] = "mc_rf +18.7 % area and +64 % power from the re-print P0 (reports/phase2.md §6 G1)"
    tail = [x for x in e4 if abs(x["area_rel"]) > 0.01]
    out["tail_records_E4"] = {"n_over_1pct": len(tail), "by_ptype": dict(collections.Counter(x["ptype"] for x in tail)), "by_ptype_all_records": dict(collections.Counter(x["ptype"] for x in e4)),
                              "by_family": {fam: dict(collections.Counter(x["ptype"] for x in tail if C1.family(x["design"]) == fam)) for fam in sorted({C1.family(x["design"]) for x in tail})},
                              "records_by_family": dict(collections.Counter(C1.family(x["design"]) for x in e4))}
    p2 = json.load(open(os.path.join(ROOT, "reports", "data", "phase2_noise_floor.json")))
    out["phase2_snapshot"] = {"source": "reports/data/phase2_noise_floor.json (generated 2026-09-14, 148 set designs at E4)", "pooled_min_E4": p2["pooled_min"]["E4"], "floor_classes_E4": p2["floor_classes"]["E4"], "summary_t_d_E4": p2["summary_t_d"]["E4"]}
    return out


# ----------------------------------------------------------------------------- B. Fig. 3
def phase4_objects(conn, fv):
    p4 = json.load(open(os.path.join(ROOT, "reports", "data", "phase4_exp1.json")))
    objs = [o for o in p4["objects"] if o.get("verdict") == "proven" and o.get("label") and o["label"] != "duplicate" and (o.get("gains") or {}).get("E4")]
    thr = {}
    for o in objs:
        for lv in LEVELS:
            key = (o["design_id"], lv)
            if key not in thr:
                try:
                    thr[key] = OBJ.thresholds(conn, o["design_id"], lv, fv)[0]
                except Exception:
                    thr[key] = {}
        o["t_d"] = {lv: thr[(o["design_id"], lv)] for lv in LEVELS}
        row = conn.execute("SELECT class_final FROM candidates WHERE cand_id=?", (o["cand_id"],)).fetchone()
        o["cls_db"] = row[0] if row else None
    return p4, objs


def survival(o, lv, mode, mat):
    """None when the object has no record at the level; 'rule_a_any': some metric above t and none below (retained or trade-off);
    'area_only': area gain above t_area (the §2 map cell); 'mat_area': area gain > 1 %; 'mat_any': some metric above materiality."""
    g = (o.get("gains") or {}).get(lv)
    if not g or g.get("area") is None:
        return None
    t = (o.get("t_d") or {}).get(lv) or {}
    if mode == "area_only":
        return None if t.get("area") is None else float(g["area"]) > float(t["area"])
    if mode == "rule_a_any":
        if t.get("area") is None:
            return None
        ups = [m for m in ("area", "wns", "power") if g.get(m) is not None and t.get(m) is not None and float(g[m]) > float(t[m])]
        return bool(ups)
    if mode == "mat_area":
        return float(g["area"]) > mat["area"]
    if mode == "mat_any":
        return any(g.get(m) is not None and float(g[m]) > mat[m] for m in ("area", "wns", "power"))
    raise ValueError(mode)


def matrix(objs, mode, mat):
    out = {}
    for cls in CLASSES:
        rows = [o for o in objs if o.get("cls") == cls]
        out[cls] = {}
        for lv in LEVELS:
            vs = [survival(o, lv, mode, mat) for o in rows]
            known = [v for v in vs if v is not None]
            out[cls][lv] = {"n": len(known), "survive": sum(1 for v in known if v), "rate": rate(sum(1 for v in known if v), len(known))}
    return out


def section_b(cfg, conn, p4, objs):
    mat = {"area": cfg["noise"]["materiality"]["area"], "power": cfg["noise"]["materiality"]["power_saif"], "wns": cfg["noise"]["materiality"]["wns"]}
    src("B Fig. 3 matrices", "reports/data/phase4_exp1.json objects[] (proven, label not duplicate, E4 gains present; n = 255) with per-level thresholds from src.analysis.objects.thresholds(conn, design, level, 'phase4'); survival modes: rule_a_any (some metric above t, the label retained or trade-off), area_only (the §2 map cell: area gain above t_area), mat_area (area gain > 1 %), mat_any (some metric above materiality)")
    b0 = [o for o in objs if o.get("role") == "b0"]
    out = {"n_objects": len(objs), "n_b0": len(b0), "labels": dict(collections.Counter(o["label"] for o in objs)),
           "panels": {"b0": {m: matrix(b0, m, mat) for m in ("rule_a_any", "area_only", "mat_area", "mat_any")},
                      "all": {m: matrix(objs, m, mat) for m in ("rule_a_any", "area_only", "mat_area", "mat_any")}}}
    lab = collections.defaultdict(collections.Counter)
    for o in objs:
        lab[(o.get("role") == "b0", o["cls"])][o["label"]] += 1
    out["labels_e4"] = {"b0": {cls: dict(lab[(True, cls)]) for cls in CLASSES}, "all": {cls: dict(collections.Counter(o["label"] for o in objs if o["cls"] == cls)) for cls in CLASSES}}
    out["phase4_md"] = {"b0_E4_area_only": {"a": "6 % (33)", "b": "49 % (84)", "c1": "100 % (19)", "d": "94 % (32)"}, "all_E4_area_only": {"a": "16 % (75) in §2; 15 % in §11", "b": "43 % (109)", "c1": "88 % (24)", "d": "73 % (45)"},
                        "materiality_E4_area": {"a": "21 % (75)", "b": "39 % (109)", "c1": "88 % (24)", "d": "69 % (45)"}, "source": "reports/phase4.md §2 tables and §11 'Map shape'"}
    on_all = [o for o in objs if all((o.get("gains") or {}).get(lv, {}).get("area") is not None for lv in ("E1", "E2", "E3", "E4"))]
    out["evaluated_on_all_four_rungs"] = len(on_all)
    out["diagnosed_count_note"] = (f"{len(objs)} diagnosed objects with an E4 record (labels retained / trade-off / absorbed_identical / absorbed / noise / harmful), {len(on_all)} of them with a record at every rung E1–E4; "
                                   f"objects lacking a rung: {[(o['cand_id'], o['design_id'], o['label']) for o in objs if o not in on_all]}")
    diff = [(o["cand_id"], o["design_id"], o["cls"], o["cls_db"], o["label"]) for o in objs if o.get("cls_db") and o["cls_db"] != o["cls"]]
    out["class_final_differs_from_json"] = diff
    return out


# ----------------------------------------------------------------------------- C. O1
def section_c(cfg, conn, p4, objs):
    src("C absorption attribution", "reports/data/phase4_diagnoser_sample.json reproduction.rows (74 absorbed objects: D compiled with one flag alone — E1d designware, E2g gate_clock, E3 retime — or with a plain compile E1, against the object's plain-compile netlist C@E1; spec 04 §B.5) and phase4_exp1.json objects (label, rung, class); permanence = src.analysis.map.non_monotone over E1–E4 (reports/phase4.md §3)")
    rep = json.load(open(os.path.join(ROOT, "reports", "data", "phase4_diagnoser_sample.json")))["reproduction"]
    rows = rep["rows"]
    cls_of = {o["cand_id"]: o["cls"] for o in p4["objects"]}
    cats = {"plain_compile": [], "single_flag": [], "compile_ultra_only": []}
    flags = collections.Counter()
    for r in rows:
        rp = r.get("repro") or {}
        none_conv = bool((rp.get("none") or {}).get("converged"))
        single = [f for f in ("designware", "gate_clock", "retime") if (rp.get(f) or {}).get("converged")]
        for f in single:
            flags[f] += 1
        if none_conv:
            cats["plain_compile"].append(r["cand_id"])
        elif single:
            cats["single_flag"].append(r["cand_id"])
        else:
            cats["compile_ultra_only"].append(r["cand_id"])
    out = {"n_absorbed": len(rows), "by_label": dict(collections.Counter(r["label"] for r in rows)), "categories": {k: len(v) for k, v in cats.items()}, "single_flag_counts_any_order": dict(flags),
           "single_flag_exclusive_of_plain": dict(collections.Counter(f for r in rows if not ((r.get("repro") or {}).get("none") or {}).get("converged") for f in ("designware", "gate_clock", "retime") if ((r.get("repro") or {}).get(f) or {}).get("converged"))),
           "by_class": {cls: dict(collections.Counter(("plain" if r["cand_id"] in cats["plain_compile"] else "single" if r["cand_id"] in cats["single_flag"] else "ultra") for r in rows if cls_of.get(r["cand_id"]) == cls)) for cls in CLASSES},
           "phase4_md": "28 plain compile, 14 single flag (designware 14, gate_clock 4, retime 4, some by several), 32 full-effort only (reports/phase4.md §9 / §11)"}
    nm = MAP.non_monotone(objs)
    out["permanence"] = {"violations": len(nm["cases"]), "n": nm["n_evaluated_on_all"], "share": nm["fraction"], "patterns": dict(collections.Counter(c[1] for c in nm["cases"])),
                         "definition": "an object inside the band at a lower rung and above it at a higher one (area gain against the rung's t_D), over objects with a record at every rung E1–E4"}
    a_all = [o for o in objs if o["cls"] == "a"]
    a_abs = [o for o in a_all if o["label"] in ("absorbed", "absorbed_identical")]
    a_on_all = [o for o in a_all if all((o.get("gains") or {}).get(lv, {}).get("area") is not None for lv in ("E1", "E2", "E3", "E4"))]
    out["class_a"] = {"absorbed_or_identical": len(a_abs), "identical": sum(1 for o in a_abs if o["label"] == "absorbed_identical"), "converged": sum(1 for o in a_abs if o["label"] == "absorbed"),
                      "n_with_e4": len(a_all), "n_on_all_rungs": len(a_on_all), "not_on_all_rungs": [(o["cand_id"], o["design_id"], o["label"]) for o in a_all if o not in a_on_all],
                      "note": "47 of 75 = class-(a) objects with an E4 record; a denominator of 73 counts only those with a record at every rung E1–E4 (the map's non-monotone denominator)"}
    return out


# ----------------------------------------------------------------------------- D. O2
def section_d(cfg, conn, p4, objs):
    mat = {"area": cfg["noise"]["materiality"]["area"], "power": cfg["noise"]["materiality"]["power_saif"], "wns": cfg["noise"]["materiality"]["wns"]}
    src("D best objects", "reports/data/phase4_exp1.json objects (role b0, label retained or trade-off; the object with the largest E4 area gain of the design), gains per level; per-level rule-A verdict from the gains and the level's thresholds (retained: some metric above t and none below; trade-off: some above and some below; noise: all within; harmful: some below, none above); E1d / E2g carry no measured floor: verdict under the materiality thresholds there")
    out = {"designs": {}}
    for des in ("rtlopt_ticket_machine", "rtlopt_fsm_encode", "drrtl_i2c"):
        cand = [o for o in objs if o["design_id"] == des and o.get("role") == "b0" and o["label"] in ("retained", "tradeoff")]
        if not cand:
            out["designs"][des] = None
            continue
        best = max(cand, key=lambda o: (o["gains"].get("E4") or {}).get("area") or -9)
        levels = {}
        for lv in LEVELS:
            g = (best.get("gains") or {}).get(lv) or {}
            t = (best.get("t_d") or {}).get(lv) or {}
            band = {m: (float(t[m]) if t.get(m) is not None else mat[m]) for m in ("area", "wns", "power")}
            ups = [m for m in band if g.get(m) is not None and float(g[m]) > band[m]]
            downs = [m for m in band if g.get(m) is not None and float(g[m]) < -band[m]]
            verdict = ("no record" if not g else "retained" if ups and not downs else "tradeoff" if ups and downs else "harmful" if downs else "noise")
            levels[lv] = {"gains": {m: (round(float(g[m]), 4) if g.get(m) is not None else None) for m in ("area", "wns", "power")}, "band": {m: round(band[m], 4) for m in band}, "band_source": ("rule A" if t.get("area") is not None else "materiality"), "verdict": verdict}
        out["designs"][des] = {"cand_id": best["cand_id"], "label_E4": best["label"], "cls": best["cls"], "levels": levels}
    c3 = p4.get("contrast_phase3") or {}
    out["rtllm_d"] = {"source": "reports/data/phase4_exp1.json contrast_phase3.d_by_design (run-time M3 verdicts of the Phase 3 calibration candidates; reports/phase4.md §8)", "d_by_design": c3.get("d_by_design"),
                      "identical_adder_16bit": ((c3.get("d_by_design") or {}).get("rtllm_adder_16bit") or {}).get("absorbed_identical"), "class_d_total": sum(sum(v.values()) for v in (c3.get("d_by_design") or {}).values())}
    return out


# ----------------------------------------------------------------------------- E. O3
def section_e(cfg, conn, p4, objs):
    src("E static rule and predictor", "src.analysis.map.misclassification_rates on the 255 objects — rule R forbids classes a / b and allows c1 / c2 / d; retained = label retained or trade-off; absorbed = absorbed, absorbed_identical, noise or duplicate — on (i) the class of phase4_exp1.json (the map's class_final at generation) and (ii) candidates.class_final as stored now; predictor AUROC from phase4_exp1.json predictor (leave-one-design-out logistic model, n = 255, 129 retained)")
    j = p4["misclassification"]
    mc_json = MAP.misclassification_rates(objs)
    objs_db = [dict(o, cls=o.get("cls_db") or o["cls"]) for o in objs]
    mc_db = MAP.misclassification_rates(objs_db)
    out = {"json": j, "recomputed_json_class": mc_json, "recomputed_db_class_final": mc_db,
           "predictor": {"with_class": {k: v for k, v in p4["predictor"]["with_class"].items() if k in ("n", "n_pos", "auroc", "precision_at_85", "miss_rate_at_85")},
                         "class_blind": {k: v for k, v in p4["predictor"]["class_blind"].items() if k in ("n", "n_pos", "auroc", "precision_at_85", "miss_rate_at_85")}},
           "phase4_md": {"static_rule": "P(retained | forbidden) 37 % (n 183), P(absorbed | allowed) 6 % (n 72) — reports/phase4.md §11", "predictor_§6": "with class 0.710, class-blind 0.733 (reports/phase4.md §6, lines 205–206)", "predictor_§11": "0.717 with the class features and 0.733 without (reports/phase4.md §11)"},
           "which_applies": "reports/data/phase4_exp1.json (the file the map is built from) holds AUROC 0.7103 with the class features and 0.7334 without; §6 of phase4.md quotes 0.710 / 0.733 from it; the 0.717 of §11 is not in the data file — the version consistent with the map is 0.733 / 0.710"}
    return out


# ----------------------------------------------------------------------------- F. O5
def section_f(cfg, conn, p4, objs):
    src("F RTL-OPT released reports", "data/sources/RTL-OPT/Results/RTL-OPT_DC/<pair>/report/area.rpt and <pair>_ref/report/area.rpt, 'Total cell area' (the authors' released DC runs: plain compile at 0.1 ns, their Nangate45 typical.db); reports/data/phase4_rtlopt_setting.json rows (authors_released, E1_authors, E2_1ns per proven pair); reports/data/phase4_exp1.json literature")
    root = os.path.join(ROOT, "data", "sources", "RTL-OPT", "Results", "RTL-OPT_DC")
    areas = {}
    if os.path.isdir(root):
        for d in sorted(os.listdir(root)):
            p = os.path.join(root, d, "report", "area.rpt")
            if os.path.exists(p):
                m = re.search(r"Total cell area:\s+([0-9.]+)", open(p, errors="replace").read())
                if m:
                    areas[d] = float(m.group(1))
    pairs = sorted({d[:-4] for d in areas if d.endswith("_ref")} & {d for d in areas if not d.endswith("_ref")})
    released = {"pairs_with_reports": len(pairs), "ref_smaller": sum(1 for p in pairs if areas[p + "_ref"] < areas[p]), "same": sum(1 for p in pairs if areas[p + "_ref"] == areas[p]), "ref_larger": sum(1 for p in pairs if areas[p + "_ref"] > areas[p])}
    rs = json.load(open(os.path.join(ROOT, "reports", "data", "phase4_rtlopt_setting.json")))
    rows = rs["rows"]
    ratios = []
    ratios_e1a = []
    for r in rows:
        ar = (r.get("authors_released") or {}).get("d_area")
        if ar and r.get("d_area"):
            ratios.append((r["design_id"], ar / float(r["d_area"])))
        e1a = ((r.get("settings") or {}).get("E1_authors") or {}).get("d_area")
        if ar and e1a:
            ratios_e1a.append((r["design_id"], ar / float(e1a)))
    out = {"released_all_pairs": released, "released_proven_pairs": rs.get("authors_released_reports"), "paper_claim": rs.get("authors_count"),
           "baseline_area_ratio_released_over_ours_E2_1ns": {"n": len(ratios), "min": min(v for _, v in ratios) if ratios else None, "median": statistics.median(v for _, v in ratios) if ratios else None, "max": max(v for _, v in ratios) if ratios else None,
                                                             "extremes": sorted(ratios, key=lambda x: x[1])[:2] + sorted(ratios, key=lambda x: -x[1])[:2]},
           "baseline_area_ratio_released_over_E1_authors": {"n": len(ratios_e1a), "min": min(v for _, v in ratios_e1a) if ratios_e1a else None, "median": statistics.median(v for _, v in ratios_e1a) if ratios_e1a else None, "max": max(v for _, v in ratios_e1a) if ratios_e1a else None},
           "counts_by_setting": rs.get("counts_by_setting"), "mux_dead": "rtlopt_mux_dead's reference does not link under DC (LINK-3): the 'missing 1' of every setting; the released reports carry it (their DC T-2022.03 links it)",
           "rtlrewriter": p4["literature"]["rtlrewriter"], "rtlopt": p4["literature"]["rtlopt"]}
    ms = [o for o in p4["objects"] if "memory_sharing" in o["design_id"]]
    out["memory_sharing"] = [{"design": o["design_id"], "role": o["role"], "verdict": o["verdict"], "label": o["label"], "gains": {lv: {m: round(v, 4) for m, v in (o["gains"].get(lv) or {}).items()} for lv in LEVELS}} for o in ms]
    return out


# ----------------------------------------------------------------------------- G. Phase 5
def section_g(cfg, conn, rows5):
    mat = {"area": cfg["noise"]["materiality"]["area"], "power": cfg["noise"]["materiality"]["power_saif"], "wns": cfg["noise"]["materiality"]["wns"]}
    src("G Phase 5 scan", "scripts/report_c1.scan_phase5 (every non-superseded Phase 5 candidate; rule A at E4 via src.analysis.phase5.uniform_diagnosis; duplicates collapsed: label duplicate never counted); evaluated = proven with an E4 record")
    ev = [r for r in rows5 if r["state"] == "evaluated"]
    dup = sum(1 for r in rows5 if r["state"] == "duplicate")
    out = {"n_evaluated": len(ev), "n_duplicates_collapsed": dup, "n_proven_pending_e4": sum(1 for r in rows5 if r["state"] == "e4_pending"), "n_dc_rejected": sum(1 for r in rows5 if r["state"] == "dc_rejected")}

    def table(rs):
        t = {}
        for cls in CLASSES + ("free", "?"):
            rc = [r for r in rs if (r.get("class_final") or "?") == cls]
            if not rc:
                continue
            cnt = collections.Counter(r["ulabel"] for r in rc)
            ret = [r for r in rc if r["ulabel"] == "retained"]
            surv = [r for r in rc if r["ulabel"] in ("retained", "tradeoff")]
            m_any = sum(1 for r in ret if C1.material(r["gains"], mat)[0] and not C1.material(r["gains"], mat)[1])
            t[cls] = {"n": len(rc), "labels": dict(cnt), "survival": len(surv), "survival_rate": rate(len(surv), len(rc)), "retained": len(ret), "retained_rate": rate(len(ret), len(rc)),
                      "material_any": m_any, "material_rate": rate(m_any, len(rc)), "material_per_metric": {m: sum(1 for r in ret if m in C1.material(r["gains"], mat)[0]) for m in ("area", "power", "wns")}}
        return t
    out["by_tier"] = {t: table([r for r in ev if r["tier"] == t]) for t in ("large", "medium", "small")}
    out["pooled"] = table(ev)
    fam = {}
    for f in ("Dr.RTL", "CktEvo", "RTL-OPT"):
        rf = [r for r in ev if C1.family(r["design_id"]) == f]
        ret = [r for r in rf if r["ulabel"] == "retained"]
        fam[f] = {"proven_evaluated": len(rf), "retained": len(ret), "retained_rate": rate(len(ret), len(rf)), "material": sum(1 for r in ret if C1.material(r["gains"], mat)[0] and not C1.material(r["gains"], mat)[1]), "designs": len({r["design_id"] for r in rf})}
    med_ret = [r for r in ev if r["tier"] == "medium" and r["ulabel"] == "retained"]
    out["families"] = {"table": fam, "medium_retained_from_rtlopt": {"n": sum(1 for r in med_ret if C1.family(r["design_id"]) == "RTL-OPT"), "of": len(med_ret), "share": rate(sum(1 for r in med_ret if C1.family(r["design_id"]) == "RTL-OPT"), len(med_ret))}}
    # (iii) B0: Yosys-improved -> E4, any metric and per metric
    src("G B0 Yosys vs E4", "candidates.label of the B0 arm (improved = any positive Y-caliber component); per metric: the candidate's Y record (evaluations config Y, same clock as the design's Y baseline) against the Y baseline — area gain (base − cand) / base, delay gain (cand WNS − base WNS) / clock — crossed with the rule-A E4 gains of the same candidate against the design's frozen t_D per metric")
    b0 = [r for r in rows5 if r["arm"] == "B0" and r["verdict"] == "proven" and r["state"] in ("evaluated", "e4_pending", "dc_rejected")]
    ybase = {}
    for r in conn.execute("SELECT design_id, clock_ns, area_um2, wns_ns FROM evaluations WHERE config='Y' AND is_baseline=1 AND status='ok' ORDER BY eval_id DESC"):
        ybase.setdefault(r["design_id"], dict(r))
    designs = P5._Designs(cfg, conn)
    per_metric = collections.Counter()
    per_design = collections.defaultdict(collections.Counter)
    anym = collections.Counter()
    for r in b0:
        d = r["design_id"]
        anym[(r.get("label") or "none", r["ulabel"] or r["state"])] += 1
        yb = ybase.get(d)
        yr = conn.execute("SELECT area_um2, wns_ns, clock_ns FROM evaluations WHERE cand_id=? AND config='Y' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (r["cand_id"],)).fetchone()
        if not yb or not yr or not yb["area_um2"]:
            per_metric["no_y_record"] += 1
            continue
        y_area = (float(yb["area_um2"]) - float(yr["area_um2"])) / float(yb["area_um2"])
        y_wns = ((float(yr["wns_ns"]) - float(yb["wns_ns"])) / float(yr["clock_ns"])) if (yr["wns_ns"] is not None and yb["wns_ns"] is not None and yr["clock_ns"]) else None
        th = designs.get(d)["thresholds"]
        g = r.get("gains") or {}
        e4_area = (g.get("area") is not None and th.get("area") is not None and float(g["area"]) > float(th["area"])) if r["state"] == "evaluated" else None
        e4_wns = (g.get("wns") is not None and th.get("wns") is not None and float(g["wns"]) > float(th["wns"])) if r["state"] == "evaluated" else None
        for name, yimp, e4ok in (("area", y_area > 0, e4_area), ("delay", (y_wns is not None and y_wns > 0), e4_wns)):
            if yimp:
                key = f"{name}: Y improved -> E4 " + ("retained on that metric" if e4ok else "pending" if e4ok is None else "not above t_D")
                per_metric[key] += 1
                per_design[d][key] += 1
    out["b0_yosys_vs_e4"] = {"any_metric_cross": {f"{k[0]}|{k[1]}": v for k, v in sorted(anym.items())}, "per_metric": dict(per_metric), "n_b0_proven": len(b0),
                             "per_design": {d: dict(per_design[d]) for d in ("drrtl_router", "drrtl_UART", "drrtl_communication", "cktevo_risc__cpu", "rtlopt_calculation")}}
    # (iv) large tier class (a) row and WNS material per arm
    la = [r for r in ev if r["tier"] == "large" and r["class_final"] == "a"]
    out["large_class_a"] = {"n": len(la), "retained": sum(1 for r in la if r["ulabel"] == "retained"), "harmful": sum(1 for r in la if r["ulabel"] == "harmful"), "harmful_share": rate(sum(1 for r in la if r["ulabel"] == "harmful"), len(la)), "labels": dict(collections.Counter(r["ulabel"] for r in la))}
    out["large_wns_material_by_arm"] = {arm: {"retained": sum(1 for r in ev if r["tier"] == "large" and r["arm"] == arm and r["ulabel"] == "retained"), "wns_material": sum(1 for r in ev if r["tier"] == "large" and r["arm"] == arm and r["ulabel"] == "retained" and "wns" in C1.material(r["gains"], mat)[0])} for arm in sorted({r["arm"] for r in ev if r["tier"] == "large"})}
    return out


# ----------------------------------------------------------------------------- H. caveats
def section_h(cfg, conn, rows5, a):
    mat = {"area": cfg["noise"]["materiality"]["area"], "power": cfg["noise"]["materiality"]["power_saif"], "wns": cfg["noise"]["materiality"]["wns"]}
    src("H caveats", "noise_floor (frozen phase4, E4 area row: floor_source / floor_class per design) joined with the Phase 5 scan; ICG insertion: log_summary_json.icg_count of the candidate's E4 record against the design's E4 baseline record; proof coverage: candidates with a verdict per design")
    fv = cfg["noise"]["floor_version"]
    held = [d for ds in cfg["exp5"]["starting_points"].values() for d in ds]
    ev = [r for r in rows5 if r["state"] == "evaluated"]
    fl = {}
    for d in held:
        row = conn.execute("SELECT floor_source, floor_class FROM noise_floor WHERE floor_version=? AND config='E4' AND metric='area' AND design_id=?", (fv, d)).fetchone()
        fl[d] = {"source": (row["floor_source"] if row else "pooled"), "class": (row["floor_class"] if row else None)}
    pooled = [d for d in held if fl[d]["source"] != "measured"]
    out = {"pooled_floor_designs": {"n": len(pooled), "of": len(held), "designs": {d: {"retained": sum(1 for r in ev if r["design_id"] == d and r["ulabel"] == "retained"), "evaluated": sum(1 for r in ev if r["design_id"] == d)} for d in pooled}},
           "offset_designs": {d: {"retained": sum(1 for r in ev if r["design_id"] == d and r["ulabel"] == "retained"), "evaluated": sum(1 for r in ev if r["design_id"] == d)} for d in held if fl[d]["class"] == "offset"}}
    base_icg = {}
    n_pow = n_icg = 0
    examples = collections.Counter()
    for r in ev:
        if r["ulabel"] != "retained" or "power" not in C1.material(r["gains"], mat)[0]:
            continue
        n_pow += 1
        d = r["design_id"]
        if d not in base_icg:
            b = conn.execute("SELECT log_summary_json FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' ORDER BY eval_id DESC LIMIT 1", (d,)).fetchone()
            try:
                base_icg[d] = (json.loads(b["log_summary_json"] or "{}") or {}).get("icg_count") if b else None
            except (ValueError, TypeError):
                base_icg[d] = None
        c = conn.execute("SELECT log_summary_json FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (r["cand_id"],)).fetchone()
        try:
            ci = (json.loads(c["log_summary_json"] or "{}") or {}).get("icg_count") if c else None
        except (ValueError, TypeError):
            ci = None
        if ci is not None and base_icg.get(d) is not None and int(ci) > int(base_icg[d]):
            n_icg += 1
            examples[d] += 1
    out["icg_insertion"] = {"retained_with_material_power_gain": n_pow, "with_more_icgs_than_D": n_icg, "share": rate(n_icg, n_pow), "by_design": dict(examples),
                            "note": "request (b) item 5 is not in this session's record; computed here as retained candidates with a power gain above 2 % whose E4 netlist carries more clock-gating cells than D's E4 netlist"}
    cov = {}
    for d in ("drrtl_SPI", "drrtl_simple_spi", "drrtl_tv80", "cktevo_hsm__hsm"):
        rd = [r for r in rows5 if r["design_id"] == d and r["verdict"]]
        cov[d] = {"with_verdict": len(rd), "proven": sum(1 for r in rd if r["verdict"] == "proven"), "inconclusive": sum(1 for r in rd if r["verdict"] == "inconclusive"), "evaluated": sum(1 for r in ev if r["design_id"] == d), "retained": sum(1 for r in ev if r["design_id"] == d and r["ulabel"] == "retained")}
    out["proof_coverage_designs"] = cov
    return out


# ----------------------------------------------------------------------------- render
def render(data):
    a, b, c, d, e, f, g, h = (data[k] for k in "abcdefgh")
    L = [f"# Data for paper Section III — Measuring Retained Gain ({data['date']}; visible layer only; interim)", "",
         f"Generated {data['generated_at']} by scripts/report_paper_sec3.py (git {data['git_sha']}, cfg {data['cfg_hash']}); floor_version **{a['floor_version']}**; duplicates collapsed as in spec 04 §B step 3; data reports/data/paper_sec3.json; every table's source in §S. Phase 5 is interim (runs at generation: {data['phase5_runs']}).", ""]
    # A
    L += ["## A. Table I — noise floor on the frozen phase4 floor table", "",
          f"Definitions ({a['definitions']['source']}): floor class — {a['definitions']['floor_class']} (noise.quiet_max_abs = {a['definitions']['quiet_max_abs_value']}); rule A — {a['definitions']['rule_A']}.", "",
          "| quantity | frozen phase4 table (this value) | n | Phase 2 value (99 designs) where it differs |", "|---|---|---|---|",
          f"| designs with a measured floor / on the pooled minimum | {a['measured']} / {a['pooled']} | {a['designs_in_table']} designs | Phase 2 snapshot (148 set designs): measured {a['phase2_snapshot']['floor_classes_E4'].get('quiet', 0) + a['phase2_snapshot']['floor_classes_E4'].get('spread', 0) + a['phase2_snapshot']['floor_classes_E4'].get('offset', 0)}, pooled {a['phase2_snapshot']['floor_classes_E4'].get('pooled')}; G1 (99 designs): floors for 99 of 128 |",
          f"| floor classes quiet / spread / offset | {a['classes'].get('quiet', 0)} / {a['classes'].get('spread', 0)} / {a['classes'].get('offset', 0)} (pooled {a['classes'].get('pooled', 0)}) | {a['measured']} measured | 72 / 21 / 6 of 99 (reports/phase2.md §6 G1) |",
          f"| perturbation records leaving E4 area and cell count unchanged | {pct(a['unchanged_E4']['share'])} | {a['unchanged_E4']['n']} records, {a['designs_with_records_E4']} designs | {a['unchanged_E4']['phase2']} |",
          f"| netlists changed by renaming alone (P1_rename) at E1 / at E4 | {pct(a['rename_changes']['E1']['share'])} / {pct(a['rename_changes']['E4']['share'])} | {a['rename_changes']['E1']['n']} / {a['rename_changes']['E4']['n']} rename records | {a['rename_changes']['phase2']} |",
          f"| designs with a perturbation moving E4 area by > 1 % / > 5 % | {a['tail_designs_E4']['over_1pct']} / {a['tail_designs_E4']['over_5pct']} (max {pct(a['tail_designs_E4']['max'])}) | {a['tail_designs_E4']['designs_with_records']} designs with records | {a['tail_designs_E4']['phase2']} |",
          f"| design-weighted pooled q90 / q95 / q99 of \\|δ_area\\| at E4 | {pct(a['pooled_quantiles_E4_area']['design_weighted'][0.9], 2)} / {pct(a['pooled_quantiles_E4_area']['design_weighted'][0.95], 2)} / {pct(a['pooled_quantiles_E4_area']['design_weighted'][0.99], 2)} (record-weighted {pct(a['pooled_quantiles_E4_area']['record_weighted'][0.9], 2)} / {pct(a['pooled_quantiles_E4_area']['record_weighted'][0.95], 2)} / {pct(a['pooled_quantiles_E4_area']['record_weighted'][0.99], 2)}) | {a['pooled_quantiles_E4_area']['n_records']} records, {a['pooled_quantiles_E4_area']['n_designs']} designs | frozen pooled minimum (design-weighted q90 of the phase4 snapshot) {pct(a['pooled_min'].get('area'), 3)} |",
          f"| pooled minima area / power / WNS (exact) | {a['pooled_min'].get('area'):.7f} = {pct(a['pooled_min'].get('area'), 2)} / {a['pooled_min'].get('power_saif'):.7f} = {pct(a['pooled_min'].get('power_saif'), 2)} / {a['pooled_min'].get('wns'):.7f} = {pct(a['pooled_min'].get('wns'), 3)} of the period | frozen table | Phase 2 snapshot identical ({a['phase2_snapshot']['pooled_min_E4']}); G1 text (99 designs): 0.29 % / 1.4 % / 0.07 % |",
          f"| largest single effect at E4 | {a['largest_effect_E4']['design']} ({a['largest_effect_E4']['ptype']}): area {pct(a['largest_effect_E4']['area_rel'])}, power {pct(a['largest_effect_E4']['power_rel'])} | 1 record | {a['largest_effect_phase2']} |", "",
          f"E4 tail (records with |δ_area| > 1 %) by perturbation type over the whole frozen table: {a['tail_records_E4']['by_ptype']} of {a['tail_records_E4']['n_over_1pct']} tail records (all E4 records by type {a['tail_records_E4']['by_ptype_all_records']}); per design family: {a['tail_records_E4']['by_family']} (records per family {a['tail_records_E4']['records_by_family']}).", ""]
    # B
    L += ["## B. Fig. 3 — survival per class and level (Phase 4 objects)", "",
          f"{b['n_objects']} diagnosed objects with an E4 record ({b['labels']}), {b['n_b0']} in the B0 layer; {b['evaluated_on_all_four_rungs']} with a record at every rung E1–E4. {b['diagnosed_count_note']}.", ""]
    for panel, title in (("b0", "Panel 1 — B0 layer"), ("all", "Panel 2 — all diagnosed objects")):
        for mode, mt in (("rule_a_any", "survival = retained or trade-off at the level (some metric above the level's rule-A t_D)"), ("area_only", "the §2 map cell: area gain above t_D at the level"), ("mat_any", "materiality: some metric above 1 % area / 2 % power / 1 % WNS"), ("mat_area", "materiality, area only (> 1 %)")):
            L += [f"**{title} — {mt}** (cells: survive / n)", "", "| class | " + " | ".join(LEVELS) + " |", "|---|" + "---|" * len(LEVELS)]
            for cls in CLASSES:
                cells = []
                for lv in LEVELS:
                    v = b["panels"][panel][mode][cls][lv]
                    cells.append(f"{v['survive']} / {v['n']} ({pct(v['rate'], 0)})" if v["n"] else "-")
                L.append(f"| {cls} | " + " | ".join(cells) + " |")
            L.append("")
    L += [f"Reconciliation with reports/phase4.md ({b['phase4_md']['source']}): the §2 map counts area gain above t_D only (mode 'area_only'): B0 layer at E4 {b['phase4_md']['b0_E4_area_only']}, all objects {b['phase4_md']['all_E4_area_only']}, materiality (area > 1 %) {b['phase4_md']['materiality_E4_area']} — reproduced above; the 'retained or trade-off' survival counts any metric above the band and is therefore higher where WNS or power carries the gain. §11's '15 %' for class (a) is 12 / 75 = 16.0 % in §2 and in the data (11 retained + 4 trade-off labels; 12 objects above t_area).",
          f"Objects whose stored class_final differs from the class in phase4_exp1.json: {b['class_final_differs_from_json'] or 'none'}.", ""]
    # C
    L += ["## C. O1 — absorption attribution over the 74 absorbed objects", "",
          f"n = {c['n_absorbed']} ({c['by_label']}). Exclusive categories in order: plain compile (converged with C@E1 under E1) {c['categories']['plain_compile']}; single capability (not plain, reproduced by one flag alone) {c['categories']['single_flag']} — flags among these {c['single_flag_exclusive_of_plain']}; only compile_ultra as a whole (no single option reproduces) {c['categories']['compile_ultra_only']}. Any-order single-flag counts (overlapping, incl. objects also plain-compile) {c['single_flag_counts_any_order']}. By class: {c['by_class']}. phase4.md: {c['phase4_md']}.",
          f"Permanence: {c['permanence']['violations']} of {c['permanence']['n']} objects ({pct(c['permanence']['share'])}) violate it — {c['permanence']['definition']}; patterns (E1 E2 E3 E4, R = above the band) {c['permanence']['patterns']}.",
          f"Class (a): {c['class_a']['absorbed_or_identical']} objects collapse to D's E4 netlist ({c['class_a']['identical']}) or converge ({c['class_a']['converged']}); denominator {c['class_a']['n_with_e4']} class-(a) objects with an E4 record, {c['class_a']['n_on_all_rungs']} with a record at every rung ({c['class_a']['note']}); the class-(a) objects without a record at some rung: {c['class_a']['not_on_all_rungs']}.", ""]
    # D
    L += ["## D. O2 — object details", ""]
    for des, v in d["designs"].items():
        if not v:
            L += [f"{des}: no retained or trade-off B0 object.", ""]
            continue
        L += [f"**{des}** — best object {v['cand_id']} (class {v['cls']}, E4 label {v['label_E4']})", "", "| level | area gain | WNS gain (periods) | power gain | band (area / WNS / power; source) | verdict |", "|---|---|---|---|---|---|"]
        for lv in LEVELS:
            x = v["levels"][lv]
            gg = x["gains"]
            L.append(f"| {lv} | {pct(gg['area'], 2)} | {pct(gg['wns'], 2)} | {pct(gg['power'], 2)} | {pct(x['band']['area'], 2)} / {pct(x['band']['wns'], 2)} / {pct(x['band']['power'], 2)}; {x['band_source']} | {x['verdict']} |")
        L.append("")
    L += [f"RTLLM class (d): {d['rtllm_d']['identical_adder_16bit']} of {d['rtllm_d']['class_d_total']} class-(d) candidates are absorbed_identical, all on rtllm_adder_16bit (hand-written adders identical to DC's inferred adder); by design {d['rtllm_d']['d_by_design']}. Source: {d['rtllm_d']['source']}.", ""]
    # E
    L += ["## E. O3 — static rule R and the predictor", "",
          f"phase4_exp1.json: P(retained | forbidden a/b) = {pct(e['json']['p_retained_given_forbidden'])} (n {e['json']['n_forbidden']}), P(absorbed | allowed c1/c2/d) = {pct(e['json']['p_absorbed_given_allowed'])} (n {e['json']['n_allowed']}).",
          f"Recomputed on the JSON classes: {pct(e['recomputed_json_class']['p_retained_given_forbidden'])} (n {e['recomputed_json_class']['n_forbidden']}) / {pct(e['recomputed_json_class']['p_absorbed_given_allowed'])} (n {e['recomputed_json_class']['n_allowed']}); on candidates.class_final as stored now: {pct(e['recomputed_db_class_final']['p_retained_given_forbidden'])} (n {e['recomputed_db_class_final']['n_forbidden']}) / {pct(e['recomputed_db_class_final']['p_absorbed_given_allowed'])} (n {e['recomputed_db_class_final']['n_allowed']}). phase4.md §11 quotes {e['phase4_md']['static_rule']}.",
          f"Predictor (leave-one-design-out): with the class features AUROC {e['predictor']['with_class']['auroc']:.3f}, class-blind {e['predictor']['class_blind']['auroc']:.3f} (n {e['predictor']['with_class']['n']}, {e['predictor']['with_class']['n_pos']} retained; precision at 85 % recall {pct(e['predictor']['with_class']['precision_at_85'], 0)} / {pct(e['predictor']['class_blind']['precision_at_85'], 0)}). {e['which_applies']}.", ""]
    # F
    fr = f["released_all_pairs"]; br = f["baseline_area_ratio_released_over_ours_E2_1ns"]; be = f["baseline_area_ratio_released_over_E1_authors"]
    L += ["## F. O5 — RTL-OPT and RTLRewriter", "",
          f"Authors' released RTL-OPT reports: {fr['ref_smaller']} of {fr['pairs_with_reports']} pairs have the reference smaller than the start ({fr['same']} same, {fr['ref_larger']} larger); over the proven 34 pairs: {f['released_proven_pairs'].get('better_by_area')} of {f['released_proven_pairs'].get('n')}; the paper's claim: {f['paper_claim']}.",
          f"Baseline (start) areas, released over ours: against our E2_1ns D area min {br['min']:.2f}×, median {br['median']:.2f}×, max {br['max']:.2f}× (n {br['n']}; extremes {[(dname, round(v, 2)) for dname, v in br['extremes']]}); against our E1_authors D area (their settings on this DC) min {be['min']:.2f}×, median {be['median']:.2f}×, max {be['max']:.2f}× (n {be['n']}).",
          f"E1_authors column: {f['counts_by_setting']['E1_authors']}; E2_1ns: {f['counts_by_setting']['E2_1ns']}; {f['mux_dead']}.",
          f"RTLRewriter: {f['rtlrewriter']['pairs']} pairs, {f['rtlrewriter']['proven']} proven, better at E1 {f['rtlrewriter']['better']['E1']} → better at E4 {f['rtlrewriter']['better']['E4']}, retained at E4 **{f['rtlrewriter']['retained']['E4']}** (evaluated {f['rtlrewriter']['evaluated']['E4']}). memory_sharing: " + "; ".join(f"{m['design']} ({m['role']}, {m['verdict']}, E4 label {m['label']}): E1 area {pct(m['gains']['E1'].get('area'), 2)}, E4 area {pct(m['gains']['E4'].get('area'), 2)}" for m in f["memory_sharing"]) + ".", ""]
    # G
    L += ["## G. Phase 5 additions (E4 verdicts, rule A; no rung attribution; duplicates collapsed)", "",
          f"Evaluated proven candidates {g['n_evaluated']} (duplicates collapsed {g['n_duplicates_collapsed']}; proven with E4 pending {g['n_proven_pending_e4']}; DC-rejected terminal {g['n_dc_rejected']}).", ""]
    for tier, tab in list(g["by_tier"].items()) + [("pooled", g["pooled"])]:
        L += [f"**{tier}** — class × verdict", "", "| class | n | retained | tradeoff | absorbed_identical | absorbed | noise | harmful | survival (ret.+trade-off) | retained only | material any (area / power / WNS) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for cls, v in tab.items():
            lb = v["labels"]; mm = v["material_per_metric"]
            L.append(f"| {cls} | {v['n']} | {lb.get('retained', 0)} | {lb.get('tradeoff', 0)} | {lb.get('absorbed_identical', 0)} | {lb.get('absorbed', 0)} | {lb.get('noise', 0)} | {lb.get('harmful', 0)} | {v['survival']} ({pct(v['survival_rate'])}) | {v['retained']} ({pct(v['retained_rate'])}) | {v['material_any']} ({pct(v['material_rate'])}) ({mm['area']} / {mm['power']} / {mm['wns']}) |")
        L.append("")
    ft = g["families"]["table"]; mr = g["families"]["medium_retained_from_rtlopt"]
    L += ["| family | designs | proven (E4 in) | retained | retained rate | material |", "|---|---|---|---|---|---|"]
    for fam, v in ft.items():
        L.append(f"| {fam} | {v['designs']} | {v['proven_evaluated']} | {v['retained']} | {pct(v['retained_rate'])} | {v['material']} |")
    L += ["", f"Share of medium-tier retained candidates on RTL-OPT designs: {mr['n']} of {mr['of']} ({pct(mr['share'])}).", "",
          f"B0 (n proven {g['b0_yosys_vs_e4']['n_b0_proven']}): Yosys label × rule-A E4 label {g['b0_yosys_vs_e4']['any_metric_cross']}; per metric {g['b0_yosys_vs_e4']['per_metric']}.", "",
          "| design | per-metric outcomes (Y improved → E4) |", "|---|---|"]
    for des, v in g["b0_yosys_vs_e4"]["per_design"].items():
        L.append(f"| {des} | {v or 'no B0 candidate with a Y record'} |")
    la = g["large_class_a"]
    L += ["", f"Large tier, class (a): {la['retained']} of {la['n']} retained; harmful {la['harmful']} ({pct(la['harmful_share'])}); labels {la['labels']}. Large-tier WNS-material retained candidates per arm: {g['large_wns_material_by_arm']}.", ""]
    # H
    L += ["## H. Caveat numbers", "",
          f"Designs on the pooled floor: {h['pooled_floor_designs']['n']} of {h['pooled_floor_designs']['of']} — retained / evaluated per design {h['pooled_floor_designs']['designs']}.",
          f"Offset designs: {h['offset_designs']}.",
          f"ICG insertion: {h['icg_insertion']['with_more_icgs_than_D']} of {h['icg_insertion']['retained_with_material_power_gain']} retained candidates with a material power gain carry more clock-gating cells than D ({pct(h['icg_insertion']['share'])}); by design {h['icg_insertion']['by_design']}. {h['icg_insertion']['note']}.",
          f"Proof coverage: {h['proof_coverage_designs']}.", ""]
    # sources
    L += ["## S. Sources", ""] + [f"- {s['table']}: `{s['source']}`" for s in data["sources"]] + [""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a_ = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    fv = cfg["noise"]["floor_version"]
    data = {"date": a_.date, "generated_at": datetime.datetime.now().isoformat(timespec="minutes"), "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash()}
    tier_of = P5.tier_of_design(cfg)
    runs = collections.defaultdict(collections.Counter)
    for r in conn.execute("SELECT design_id, status, COUNT(*) AS n FROM runs WHERE exp='phase5' AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0 GROUP BY design_id, status"):
        runs[tier_of.get(r["design_id"], "?")][r["status"]] += r["n"]
    data["phase5_runs"] = {t: dict(v) for t, v in runs.items()}
    data["a"] = section_a(cfg, conn)
    p4, objs = phase4_objects(conn, fv)
    data["b"] = section_b(cfg, conn, p4, objs)
    data["c"] = section_c(cfg, conn, p4, objs)
    data["d"] = section_d(cfg, conn, p4, objs)
    data["e"] = section_e(cfg, conn, p4, objs)
    data["f"] = section_f(cfg, conn, p4, objs)
    held = [d for ds in cfg["exp5"]["starting_points"].values() for d in ds]
    rows5, _ = C1.scan_phase5(cfg, conn, held)
    data["g"] = section_g(cfg, conn, rows5)
    data["h"] = section_h(cfg, conn, rows5, data["a"])
    data["sources"] = SOURCES
    js = os.path.join(ROOT, "reports", "data", "paper_sec3.json")
    md = os.path.join(ROOT, "reports", "paper_sec3.md")
    with open(js, "w") as fh:
        json.dump(data, fh, indent=1, default=str)
    with open(md, "w") as fh:
        fh.write(render(data))
    print(f"written {md} and {js}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
