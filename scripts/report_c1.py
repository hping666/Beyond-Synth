#!/usr/bin/env python3
"""C1 interim evidence report (REQUEST 2026-09-20; read-only, visible layer only — never opens results/hidden).

Writes reports/c1_interim_<date>.md and reports/data/c1_interim.json from the visible results database, the frozen
phase data files (reports/data/phase2_noise_floor.json, phase4_exp1.json, phase4_rtlopt_setting.json,
phase3_m6_agreement.json) and the phase reports it cites. Every number carries its source; evaluation that is not
complete is marked "pending". Uniform caliber: rule A with each design's frozen floor (floor_version phase4), per-metric
verdicts (area, WNS at Φ_main, power), the materiality row (area 1 %, power 2 %, WNS 1 % of the period) beside every
retention figure. Usage: report_c1.py [--date YYYY-MM-DD] [--out PATH] [--json PATH]. Run under nice so that the
Phase 5 pipeline is not slowed: nice -n 19 .venv/bin/python3 scripts/report_c1.py
"""
import argparse
import collections
import datetime
import json
import os
import re
import statistics
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.analysis import phase5 as P5  # noqa: E402
from src.noise import stats as S  # noqa: E402

CLASSES = ("a", "b", "c1", "c2", "d")
LABELS = ("retained", "tradeoff", "absorbed_identical", "absorbed", "noise", "harmful", "fragile")
FAMILY = {"cktevo": "CktEvo", "drrtl": "Dr.RTL", "rtlopt": "RTL-OPT", "rtlrewriter": "RTLRewriter", "rtllm": "RTLLM"}
SOURCES = []   # every query / collector call behind a table, in order (appendix §7)


def src(name, text):
    SOURCES.append({"table": name, "source": text})
    return text


def family(design_id):
    return FAMILY.get(design_id.split("_", 1)[0], design_id.split("_", 1)[0])


def pct(x, nd=1):
    return "-" if x is None else f"{100.0 * x:.{nd}f} %"


def rate(n, d):
    return None if not d else n / d


# ----------------------------------------------------------------------------- shared helpers
def rule_a_from_e4(designs, conn, cand_id, design_id):
    """Rule-A label from the candidate's E4 record without the proof (for prescreened candidates: reported 'proof pending').
    Mirrors src.analysis.phase5.uniform_diagnosis."""
    d = designs.get(design_id)
    if not d["base"] or d["phi"] is None:
        return None
    ev = conn.execute("SELECT * FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (cand_id,)).fetchone()
    if ev is None:
        return None
    out = P5.m3.diagnose(d["base"], P5.record_from_row(ev), d["sigma"], d["phi"], v3_status="proven", k_sigma=designs.k_sigma, thresholds=d["thresholds"], floor_class=d["floor_class"])
    return out.get("label"), (out.get("evidence") or {}).get("gains") or {}


def material(gains, mat):
    """Per-metric materiality verdict of a gain vector: which metrics improve by more than the materiality threshold and which
    worsen by more than it. -> (improved metrics, worsened metrics)."""
    up = [m for m in ("area", "power", "wns") if gains.get(m) is not None and float(gains[m]) > mat[m]]
    down = [m for m in ("area", "power", "wns") if gains.get(m) is not None and float(gains[m]) < -mat[m]]
    return up, down


def norm_subtag(s):
    """The rules-v2 evidence tag behind a candidate's sub-tag string, normalised to a small vocabulary."""
    s = str(s)
    if s.startswith("operator family gained"):
        m = re.search(r"gained: ([a-z, ]+) \(", s)
        return "operator family gained: " + (m.group(1).strip() if m else "?")
    if s.startswith("register names or clocked targets changed"):
        return "registers renamed / retargeted, count and latency unchanged"
    if s.startswith("flip-flop bits, register names and clocked targets unchanged") or s.startswith("flip-flop count, register names"):
        return "state elements unchanged"
    if s.startswith("flip-flop bits") and "same register cells" in s:
        return "register widths changed, same cells"
    if s.startswith("flip-flop bits") and "register cells" in s:
        return "flip-flop count and register cells changed"
    if s.startswith("flip-flop bits"):
        return "flip-flop count changed, latency unchanged"
    if s.startswith("longest combinational path"):
        return "combinational depth ratio >= threshold"
    if s.startswith("text differs widely") or s.startswith("but the text differs widely"):
        return "wide text difference without operator / topology evidence"
    if s.startswith("sequential structure changed"):
        return "sequential structure changed"
    if s in ("class_rule", "error") or s.startswith("m6 failed") or s.startswith("mN failed"):
        return None
    return s[:60]


# ----------------------------------------------------------------------------- §1 floors and ladder
def section_floors(cfg, conn, held, exp1):
    fv = cfg["noise"]["floor_version"]
    out = {"floor_version": fv, "k_sigma": cfg["noise"]["k_sigma"], "materiality": cfg["noise"]["materiality"]}
    p2 = json.load(open(os.path.join(ROOT, "reports", "data", "phase2_noise_floor.json")))
    out["pooled_min_E4"] = p2["pooled_min"]["E4"]
    out["pooled_min_source"] = src("floor pooled minima", "reports/data/phase2_noise_floor.json pooled_min[E4] (design-weighted pooled q90, DECISIONS 2026-09-14 rule A; frozen floor_version phase4, G4.3)")
    out["summary_t_d_E4"] = p2["summary_t_d"]["E4"]
    out["floor_classes_all_E4"] = p2["floor_classes"]["E4"]
    # floor classes of the 30 held Phase 5 designs and the 10 Exp1 designs (E4 area row of the frozen table; pooled = no measured floor)
    classes = {}
    q = src("floor classes per design set", "SELECT design_id, metric, floor_class, floor_source, t_d FROM noise_floor WHERE config='E4' AND floor_version=? (frozen phase4 table), one row per design and metric; designs without a row carry the pooled minimum (floor_source pooled)")
    for name, ds in (("held30", held), ("exp1", exp1)):
        cnt = collections.Counter()
        t_area = []
        per = {}
        for d in ds:
            rows = {r["metric"]: dict(r) for r in conn.execute("SELECT design_id, metric, floor_class, floor_source, t_d FROM noise_floor WHERE config='E4' AND floor_version=? AND design_id=?", (fv, d))}
            a = rows.get("area")
            cls = (a or {}).get("floor_class") or "pooled"
            cnt[cls] += 1
            per[d] = {"class": cls, "t_d_area": (a or {}).get("t_d"), "t_d_power": (rows.get("power_saif") or {}).get("t_d"), "t_d_wns": (rows.get("wns") or {}).get("t_d")}
            if a and a.get("t_d") is not None:
                t_area.append(float(a["t_d"]))
        classes[name] = {"counts": dict(cnt), "n": len(ds), "t_d_area_median": (statistics.median(t_area) if t_area else None), "t_d_area_max": (max(t_area) if t_area else None), "per_design": per}
    out["floor_classes"] = classes
    # |delta| quantiles by configuration and metric over every (design, perturbation) pair of the 40 designs with records
    q = src("|delta| quantiles", "SELECT e.design_id, e.config, e.pert_id, p.ptype, e.area_um2, e.wns_ns, e.power_saif_mw, e.clock_ns FROM evaluations e JOIN perturbations p ON p.pert_id=e.pert_id WHERE e.status='ok' AND e.config IN ('E1','E2','E3','E4') AND e.design_id IN (held 30 + Exp1 10); baseline: the design's is_baseline=1 record of the same config and clock; |delta| relative for area and power, WNS in clock periods")
    marks = ",".join("?" * len(held + exp1))
    base = {}
    for r in conn.execute(f"SELECT design_id, config, clock_ns, area_um2, wns_ns, power_saif_mw FROM evaluations WHERE is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' AND config IN ('E1','E2','E3','E4') AND design_id IN ({marks}) ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC", held + exp1):
        base.setdefault((r["design_id"], r["config"], round(float(r["clock_ns"]), 4)), dict(r))
    deltas = collections.defaultdict(list)
    heavy = []
    n_pairs = collections.Counter()
    for r in conn.execute(f"SELECT e.design_id, e.config, e.pert_id, p.ptype, e.area_um2, e.wns_ns, e.power_saif_mw, e.clock_ns FROM evaluations e JOIN perturbations p ON p.pert_id=e.pert_id WHERE e.status='ok' AND e.config IN ('E1','E2','E3','E4') AND e.design_id IN ({marks})", held + exp1):
        b = base.get((r["design_id"], r["config"], round(float(r["clock_ns"]), 4)))
        if not b or not b["area_um2"]:
            continue
        n_pairs[r["config"]] += 1
        da = abs(float(r["area_um2"]) - float(b["area_um2"])) / float(b["area_um2"])
        deltas[(r["config"], "area")].append(da)
        if b["wns_ns"] is not None and r["wns_ns"] is not None and r["clock_ns"]:
            deltas[(r["config"], "wns")].append(abs(float(r["wns_ns"]) - float(b["wns_ns"])) / float(r["clock_ns"]))
        if b["power_saif_mw"] and r["power_saif_mw"] is not None:
            deltas[(r["config"], "power")].append(abs(float(r["power_saif_mw"]) - float(b["power_saif_mw"])) / float(b["power_saif_mw"]))
        if r["config"] == "E4" and da > 0.01:
            heavy.append({"design_id": r["design_id"], "ptype": r["ptype"], "abs_delta_area": round(da, 4), "over_5pct": da > 0.05})
    qs = {}
    for (cfg_, met), xs in sorted(deltas.items()):
        xs = sorted(xs)
        qs[f"{cfg_}|{met}"] = {"n": len(xs), "q90": round(P5._q(xs, 0.90), 5), "q95": round(P5._q(xs, 0.95), 5), "q99": round(P5._q(xs, 0.99), 5), "max": round(xs[-1], 5)}
    out["delta_quantiles"] = qs
    out["delta_pairs_per_config"] = dict(n_pairs)
    out["designs_with_perturbation_records"] = len({k[0] for k in base if k[1] == "E4"} & {r[0] for r in conn.execute(f"SELECT DISTINCT design_id FROM evaluations WHERE pert_id IS NOT NULL AND config='E4' AND status='ok' AND design_id IN ({marks})", held + exp1)})
    out["heavy_tail_E4"] = {"over_1pct": sorted(heavy, key=lambda x: -x["abs_delta_area"]), "n_over_1pct": len(heavy), "n_over_5pct": sum(1 for h in heavy if h["over_5pct"]),
                            "by_ptype_over_1pct": dict(collections.Counter(h["ptype"] for h in heavy)), "by_design_over_1pct": dict(collections.Counter(h["design_id"] for h in heavy))}
    # ladder facts (restated from the Phase 0 / Phase 2 reports)
    out["ladder_facts"] = {
        "source": src("ladder facts", "reports/phase0.md 'Addendum (G0 follow-up, 2026-09-12)' (four-design probe, reports/data/phase0_ladder_probe_{1,2}.json) and reports/phase2.md §2c (127 set designs with every rung at Φ_main)"),
        "E1_to_E2": "the large step everywhere on the four probe designs: −6 % to −37 % area (datapath blocks, DesignWare Foundation auto-added, ungrouping, boundary optimisation, area strategy)",
        "no_op_flags": "-timing_high_effort_script / -area_high_effort_script are documented as kept for backward compatibility and ignored: E2t bit-identical to E2 on all four designs; compile_timing_high_effort is not an application variable in wire-load mode (OPT-1346) — E2t dropped from the ladder",
        "designware": "compile with DesignWare Foundation (E1d) differs from compile with the standard synthetic library only (E1) by 3–6 % on every probe design, in both directions (the divider gets worse) — the DesignWare choice is a capability of its own (rung E1d)",
        "retiming": "-retime (E2 → E3) acts only on near-critical pipelined designs (register counts change, area ±2 %), not on combinational or slack-rich designs",
        "gate_clock": "-gate_clock is the dominant E3 → E4 effect where enable registers exist (adder_pipe_64bit −6 %, 4 ICGs)",
        "non_monotone_counts": {"E1->E2": {"area_grows": 15, "wns_drops": 46}, "E2->E3": {"area_grows": 36, "wns_drops": 18}, "E3->E4": {"area_grows": 5, "wns_drops": 20}, "E1->E4": {"area_grows": 10, "wns_drops": 43}, "designs": 127,
                               "note": "WNS compared at Φ_main; once a rung meets timing, area recovery legitimately trades slack (reports/phase2.md §2c)"},
    }
    return out


# ----------------------------------------------------------------------------- Phase 5 candidate scan (rule A at E4)
def scan_phase5(cfg, conn, held):
    """Every non-superseded Phase 5 candidate of the started tiers with its rule-A label at E4 (uniform_diagnosis) where the E4
    record exists; proven-without-E4 marked pending; prescreened class-(a) candidates with sim + E4 done labelled 'proof pending'."""
    tier_of = P5.tier_of_design(cfg)
    designs = P5._Designs(cfg, conn)
    rows = []
    q = src("Phase 5 candidate scan", "SELECT c.cand_id, c.design_id, c.class_final, c.subtags_json, c.label, c.verdict, c.harness_version, c.prescreened, c.v1_status, c.v2_status, c.e4_failure, r.arm, r.llm_model, r.run_id, r.seed, r.status FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase5' AND r.status != 'superseded' AND COALESCE(r.excluded_from_tables,0)=0; rule-A label = src.analysis.phase5.uniform_diagnosis (m3.diagnose on the E4 record with the design's frozen floor)")
    for c in conn.execute("SELECT c.cand_id, c.design_id, c.class_final, c.subtags_json, c.label, c.verdict, c.harness_version, c.prescreened, c.v1_status, c.v2_status, c.e4_failure, r.arm, r.llm_model, r.run_id, r.seed, r.status "
                          "FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase5' AND r.status != 'superseded' AND COALESCE(r.excluded_from_tables,0)=0"):
        c = dict(c)
        c["tier"] = tier_of.get(c["design_id"])
        if c["tier"] is None:
            continue
        try:
            tags = json.loads(c.get("subtags_json") or "[]")
        except (ValueError, TypeError):
            tags = []
        c["tags"] = sorted({t for t in (norm_subtag(s) for s in tags if isinstance(s, (str, int, float))) if t})
        c["ulabel"], c["gains"], c["state"] = None, {}, None
        if c["verdict"] == "proven":
            ud = P5.uniform_diagnosis(designs, conn, c)
            if ud:
                c["ulabel"], c["gains"] = ud[0], ud[1]
                c["state"] = "evaluated"
            elif c.get("e4_failure"):
                c["state"] = "dc_rejected"
            else:
                c["state"] = "e4_pending"
        elif int(c.get("prescreened") or 0) and c["verdict"] is None and c.get("v1_status") == "ok" and c.get("v2_status") and c["v2_status"] not in P5.SIM_FAILED:
            r = rule_a_from_e4(designs, conn, c["cand_id"], c["design_id"])
            if r:
                c["ulabel"], c["gains"], c["state"] = r[0], r[1], "proof_pending"
            else:
                c["state"] = "prescreened_e4_pending"
        elif int(c.get("prescreened") or 0) and c["verdict"] is None:
            c["state"] = "prescreened_sim_pending"
        rows.append(c)
    return rows, designs


def class_label_table(rows, mat, label_key="ulabel", cls_key="class_final", gains_key="gains"):
    """class × label counts with the retention rate per class and the materiality row (retained candidates whose gain beats the
    materiality threshold on at least one metric with none below it, and per metric)."""
    tab = {}
    for cls in CLASSES + ("free", "?"):
        rs = [r for r in rows if (r.get(cls_key) or "?") == cls and r.get(label_key)]
        if not rs:
            continue
        cnt = collections.Counter(r[label_key] for r in rs)
        ret = [r for r in rs if r[label_key] == "retained"]
        mat_any = mat_area = mat_power = mat_wns = 0
        for r in ret:
            up, down = material(r.get(gains_key) or {}, mat)
            mat_any += int(bool(up) and not down)
            mat_area += int("area" in up); mat_power += int("power" in up); mat_wns += int("wns" in up)
        tab[cls] = {"n": len(rs), "labels": {l: cnt.get(l, 0) for l in LABELS if cnt.get(l)}, "retained": len(ret), "retention_rate": rate(len(ret), len(rs)),
                    "material": {"any": mat_any, "area": mat_area, "power": mat_power, "wns": mat_wns, "rate_any": rate(mat_any, len(rs))}}
    return tab


# ----------------------------------------------------------------------------- §2 map
def section_map(cfg, conn, p5rows, held, exp1):
    mat = {"area": cfg["noise"]["materiality"]["area"], "power": cfg["noise"]["materiality"]["power_saif"], "wns": cfg["noise"]["materiality"]["wns"]}
    out = {"materiality": mat, "floor_version": cfg["noise"]["floor_version"], "equiv_version": cfg["equiv"].get("version")}
    p4 = json.load(open(os.path.join(ROOT, "reports", "data", "phase4_exp1.json")))
    out["phase4_source"] = src("Phase 4 objects", "reports/data/phase4_exp1.json objects[] (cand_id, design_id, cls, role b0 / reference / llm, verdict, label = rule A at E4 under the frozen phase4 floors, rung / attribution for absorbed, gains per rung E1 / E1d / E2 / E3 / E2g / E4); generated 2026-09-15, floor_version phase4")
    objs = [dict(o, gains=(o.get("gains") or {}).get("E4") or {}) for o in p4["objects"] if o.get("verdict") == "proven" and o.get("label") and o["label"] != "duplicate" and (o.get("gains") or {}).get("E4")]
    out["phase4"] = {"n_proven_with_e4": len(objs), "by_role": {}, "by_family": {}, "absorbed_rungs": dict(collections.Counter(o.get("rung") or "?" for o in objs if o.get("label") == "absorbed"))}
    for role, label in (("b0", "Phase 4 B0 candidates (Exp1 designs)"), ("reference", "literature pairs (RTL-OPT / RTLRewriter references)"), ("llm", "RTLRewriter LLM samples")):
        rs = [o for o in objs if o.get("role") == role]
        out["phase4"]["by_role"][role] = {"title": label, "table": class_label_table(rs, mat, label_key="label", cls_key="cls")}
    for fam in sorted({family(o["design_id"]) for o in objs}):
        rs = [o for o in objs if family(o["design_id"]) == fam]
        out["phase4"]["by_family"][fam] = class_label_table(rs, mat, label_key="label", cls_key="cls")
    out["phase4"]["shape"] = p4.get("shape")
    out["phase4"]["map_e4_by_class"] = {cls: p4["map"][cls]["E4"] for cls in p4["map"]}
    out["phase4"]["map_materiality_e4_by_class"] = {cls: p4["map_materiality"][cls]["E4"] for cls in p4["map_materiality"]}
    # Phase 5: by tier and arm; pending counts
    tiers = sorted({r["tier"] for r in p5rows}, key=lambda t: {"large": 0, "medium": 1, "small": 2}.get(t, 3))
    out["phase5"] = {"tiers": {}, "runs": {}, "pending": {}}
    runs_q = src("Phase 5 run counts", "SELECT design_id, arm, status, COUNT(*) FROM runs WHERE exp='phase5' AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0 GROUP BY design_id, arm, status")
    tier_of = P5.tier_of_design(cfg)
    rc = collections.defaultdict(collections.Counter)
    for r in conn.execute("SELECT design_id, arm, status, COUNT(*) AS n FROM runs WHERE exp='phase5' AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0 GROUP BY design_id, arm, status"):
        rc[tier_of.get(r["design_id"])][r["status"]] += r["n"]
    for t in tiers:
        rs = [r for r in p5rows if r["tier"] == t]
        by_arm = {}
        for arm in sorted({r["arm"] for r in rs}):
            ra = [r for r in rs if r["arm"] == arm]
            by_arm[arm] = {"table": class_label_table([r for r in ra if r["state"] == "evaluated"], mat),
                           "proven": sum(1 for r in ra if r["verdict"] == "proven"), "evaluated": sum(1 for r in ra if r["state"] == "evaluated"),
                           "e4_pending": sum(1 for r in ra if r["state"] == "e4_pending"), "dc_rejected": sum(1 for r in ra if r["state"] == "dc_rejected"),
                           "harness": {"v1": sum(1 for r in ra if r["verdict"] == "proven" and (r.get("harness_version") or 1) == 1), "v2": sum(1 for r in ra if r["verdict"] == "proven" and (r.get("harness_version") or 1) >= 2)}}
        pre = [r for r in rs if r["state"] == "proof_pending"]
        out["phase5"]["tiers"][t] = {"by_arm": by_arm, "runs": dict(rc.get(t, {})), "all_arms": class_label_table([r for r in rs if r["state"] == "evaluated"], mat),
                                     "prescreened_proof_pending": {"n": len(pre), "table": class_label_table(pre, mat)},
                                     "prescreened_sim_pending": sum(1 for r in rs if r["state"] == "prescreened_sim_pending"), "prescreened_e4_pending": sum(1 for r in rs if r["state"] == "prescreened_e4_pending")}
    out["phase5"]["by_family"] = {}
    for fam in sorted({family(r["design_id"]) for r in p5rows}):
        out["phase5"]["by_family"][fam] = class_label_table([r for r in p5rows if family(r["design_id"]) == fam and r["state"] == "evaluated"], mat)
    # sub-tags (rules-v2 evidence tags) among retained versus trade-off, Phase 5 evaluated candidates
    tag_tab = collections.defaultdict(collections.Counter)
    for r in p5rows:
        if r["state"] == "evaluated" and r["ulabel"] in ("retained", "tradeoff", "absorbed_identical", "noise", "harmful"):
            for tg in (r["tags"] or ["(no evidence tag)"]):
                tag_tab[tg][r["ulabel"]] += 1
    out["phase5"]["evidence_tags"] = {k: dict(v) for k, v in sorted(tag_tab.items(), key=lambda kv: -sum(kv[1].values()))}
    out["phase5"]["subtag_note"] = ("The semantic sub-tags requested (bit-width, precomputation / LUT, strength reduction, control simplification, resource sharing, state encoding, clock gating) are not recorded as data: candidates carry the rules-v2 evidence tags (operator family gained, flip-flop / register changes, combinational depth, text-diff width) that drive the class decision. A semantic tagging pass is pending (Phase 6 item).")
    # RTLLM contrast (never pooled)
    c3 = p4.get("contrast_phase3") or {}
    out["rtllm_contrast"] = {"source": src("RTLLM contrast", "reports/data/phase4_exp1.json contrast_phase3 (666 E4-diagnosed Phase 3 calibration candidates of 5 RTLLM dev designs, run-time M3 verdicts under the Phase 3 floors; reports/phase4.md §8)"),
                             "shape": c3.get("shape"), "map_e4_by_class": {cls: (c3.get("map") or {}).get(cls, {}).get("E4") for cls in (c3.get("map") or {})},
                             "map_materiality_e4_by_class": {cls: (c3.get("map_materiality") or {}).get(cls, {}).get("E4") for cls in (c3.get("map_materiality") or {})},
                             "harmful_by_class": c3.get("harmful_by_class"), "objects": c3.get("objects")}
    out["rung_attribution_note"] = "Rung attribution (E1 / E1d / E2 / E2g / E3) exists for the Phase 4 objects only (ladder runs on every object, reports/phase4.md §2); the ladder runs on the Phase 5 accepted candidates are a Phase 6 item (config exp5.ladder_on_accepted = phase6)."
    return out


# ----------------------------------------------------------------------------- §3 literature caliber vs E4
def section_literature(cfg, conn, p5rows):
    out = {}
    # (a) B0: own Yosys-caliber labels against rule A at E4
    b0 = [r for r in p5rows if r["arm"] == "B0" and r["verdict"] == "proven"]
    out["b0_source"] = src("B0 own labels vs rule A", "candidates.label of the B0 arm (improved / no_gain: the run's Y-caliber fitness, Yosys + OpenSTA, spec 05 §5) against the rule-A E4 label of the same proven candidate (uniform_diagnosis); proven candidates without an E4 record are pending (offline pool)")
    per_tier = {}
    for t in sorted({r["tier"] for r in b0}, key=lambda t: {"large": 0, "medium": 1, "small": 2}.get(t, 3)):
        rs = [r for r in b0 if r["tier"] == t]
        cross = collections.Counter((r.get("label") or "none", r["ulabel"] or r["state"]) for r in rs)
        imp = [r for r in rs if r.get("label") == "improved" and r["state"] == "evaluated"]
        imp_lab = collections.Counter(r["ulabel"] for r in imp)
        per_design = {}
        for d in sorted({r["design_id"] for r in rs}):
            rd = [r for r in rs if r["design_id"] == d]
            ev = [r for r in rd if r["state"] == "evaluated"]
            per_design[d] = {"proven": len(rd), "evaluated": len(ev), "pending": sum(1 for r in rd if r["state"] == "e4_pending"), "dc_rejected": sum(1 for r in rd if r["state"] == "dc_rejected"),
                             "yosys_improved": sum(1 for r in rd if r.get("label") == "improved"),
                             "improved_at_e4": dict(collections.Counter(r["ulabel"] for r in ev if r.get("label") == "improved")),
                             "no_gain_at_e4": dict(collections.Counter(r["ulabel"] for r in ev if r.get("label") == "no_gain"))}
        per_tier[t] = {"proven": len(rs), "evaluated": sum(1 for r in rs if r["state"] == "evaluated"), "pending": sum(1 for r in rs if r["state"] == "e4_pending"),
                       "cross": {f"{k[0]}|{k[1]}": v for k, v in sorted(cross.items())},
                       "yosys_improved_evaluated": len(imp), "improved_at_e4": dict(imp_lab),
                       "improved_share": {l: rate(imp_lab.get(l, 0), len(imp)) for l in ("retained", "tradeoff", "absorbed_identical", "absorbed", "noise", "harmful")},
                       "per_design": per_design}
    out["b0"] = per_tier
    # (b) Phase 4 literature restated
    p4 = json.load(open(os.path.join(ROOT, "reports", "data", "phase4_exp1.json")))
    rs = json.load(open(os.path.join(ROOT, "reports", "data", "phase4_rtlopt_setting.json")))
    out["phase4_literature"] = {"source": src("Phase 4 literature", "reports/data/phase4_exp1.json literature (better = the optimized version's area below D's under the rung; retained = above D's rule-A threshold there; reports/phase4.md §4) and reports/data/phase4_rtlopt_setting.json (reports/phase4.md §4d)"),
                                "rtlopt": p4["literature"]["rtlopt"], "rtlrewriter": p4["literature"]["rtlrewriter"],
                                "rtlopt_reconciliation": {"paper_claim": rs.get("authors_count"), "released_reports": rs.get("authors_released_reports"), "counts_by_setting": rs.get("counts_by_setting"), "pairs": rs.get("pairs")}}
    e1a = conn.execute("SELECT COUNT(*), COUNT(DISTINCT design_id), SUM(is_baseline) FROM evaluations WHERE config='E1_authors' AND status='ok'").fetchone()
    out["phase4_literature"]["e1_authors_records"] = {"records": e1a[0], "designs": e1a[1], "baselines": e1a[2],
                                                      "complete": "33 of 34 pairs (rtlopt_mux_dead's reference does not link under DC, LINK-3: 'missing 1' in counts_by_setting)" if (rs.get("counts_by_setting") or {}).get("E1_authors", {}).get("missing") == 1 else "see counts_by_setting"}
    # the 25 non-equivalent literature objects by cause (parsed from reports/phase4.md §4a)
    causes = collections.Counter()
    roles = collections.Counter()
    try:
        txt = open(os.path.join(ROOT, "reports", "phase4.md")).read()
        sec = txt.split("## 4a.")[1].split("**Objects whose synthesis evaluation failed**")[0]
        for line in sec.splitlines():
            if line.startswith("| rtl") and line.count("|") >= 7:
                cells = [x.strip() for x in line.strip().strip("|").split("|")]
                roles[cells[1]] += 1
                cause = cells[5]
                key = ("genuine functional difference" if cause.startswith("genuine functional difference") else "all-zero initial-state assumption likely" if cause.startswith("all-zero") else
                       "does not elaborate in the V1 port check (tool boundary)" if "does not elaborate" in cause else "port mismatch" if cause.startswith("port mismatch") else
                       "undecided (bounded proof reached its cap)" if cause.startswith("undecided") else cause[:50])
                causes[key] += 1
    except (OSError, IndexError):
        pass
    out["phase4_literature"]["non_equivalent"] = {"n": sum(roles.values()), "by_role": dict(roles), "by_cause": dict(causes), "source": src("non-equivalent literature objects", "reports/phase4.md §4a table (25 objects; probable cause column), DECISIONS 2026-09-14 item 3")}
    # (c) Dr.RTL shared designs
    shared = ["drrtl_aes", "drrtl_tv80", "drrtl_LSTM", "drrtl_i2c", "drrtl_pcie", "drrtl_datapath"]
    notes = (cfg.get("exp5") or {}).get("design_notes") or {}
    rows = {}
    for d in shared:
        rd = [r for r in p5rows if r["design_id"] == d and r["state"] == "evaluated"]
        by_arm = {}
        for arm in sorted({r["arm"] for r in rd}):
            ra = [r for r in rd if r["arm"] == arm]
            best = {}
            for m in ("area", "power", "wns"):
                vals = [float(r["gains"].get(m) or 0.0) for r in ra if r["ulabel"] == "retained" and r["gains"].get(m) is not None]
                best[m] = max(vals) if vals else None
            by_arm[arm] = {"proven_evaluated": len(ra), "retained": sum(1 for r in ra if r["ulabel"] == "retained"), "best_retained_gain": best}
        allobjs = [o for o in p4["objects"] if o["design_id"] == d]
        p4objs = [o for o in allobjs if o.get("verdict") == "proven" and (o.get("gains") or {}).get("E4")]
        p4best = None
        if allobjs:
            vals = [float(o["gains"]["E4"].get("area") or 0.0) for o in p4objs if o.get("label") == "retained"]
            p4best = {"objects": len(p4objs), "all_objects": len(allobjs), "verdicts": dict(collections.Counter(o.get("verdict") for o in allobjs)), "retained": len(vals), "best_area": (max(vals) if vals else None)}
        rows[d] = {"phase5_by_arm": by_arm, "phase4_b0": p4best, "note": notes.get(d), "status": ("Phase 5 large tier" if d in ("drrtl_aes", "drrtl_tv80", "drrtl_LSTM") else "Exp1 design (Phase 4 B0 objects only)"),
                   "paper": "pending — the paper's per-design numbers are not in the released repository (data/sources/Dr_RTL: rtl_dataset, syn_flow); transcription from arXiv:2604.14989 is the open item"}
    out["drrtl"] = {"source": src("Dr.RTL shared designs", "Phase 5 candidate scan (rule A at E4, uniform_diagnosis) by arm on drrtl_aes / tv80 / LSTM; reports/data/phase4_exp1.json B0 objects on drrtl_i2c / pcie / datapath; config exp5.design_notes"),
                    "rows": rows, "reference_row": "PLAN 5.4: the user-run original Dr.RTL reference row (Claude Code + Claude Opus, 5 Dr.RTL designs, VC Formal SEQ) is triggered manually — not started as of this report (no entry in DECISIONS / STATUS beyond the plan)"}
    return out


# ----------------------------------------------------------------------------- §4 what survives
def section_survives(cfg, conn, p5rows, view, exp1):
    mat = {"area": cfg["noise"]["materiality"]["area"], "power": cfg["noise"]["materiality"]["power_saif"], "wns": cfg["noise"]["materiality"]["wns"]}
    out = {"source": src("best retained gain per design", "Phase 5 candidate scan: per run the max over its rule-A retained candidates of each metric's gain (0 when none), then the mean over the design's seeds of that arm-model row and the max; Stage A = large tier (every run done), Stage B = complete or B0-pending designs (src.analysis.phase5.completion_view); Exp1 = Phase 4 B0 objects (max over objects, no seeds)")}
    tier_of = P5.tier_of_design(cfg)
    complete = set(view.get("complete") or []) | set(view.get("preliminary") or [])
    per_design = {}
    designs = sorted({r["design_id"] for r in p5rows if r["tier"] == "large" or r["design_id"] in complete}, key=lambda d: (tier_of.get(d), d))
    for d in designs:
        rd = [r for r in p5rows if r["design_id"] == d]
        by_row = {}
        for key in sorted({(r["llm_model"], r["arm"]) for r in rd}, key=lambda k: (k[1], k[0])):
            rr = [r for r in rd if (r["llm_model"], r["arm"]) == key]
            runs = sorted({r["run_id"] for r in rr})
            per_run = {m: [] for m in ("area", "power", "wns")}
            mat_runs = 0
            pending = sum(1 for r in rr if r["state"] in ("e4_pending",))
            for rid in runs:
                ret = [r for r in rr if r["run_id"] == rid and r["state"] == "evaluated" and r["ulabel"] == "retained"]
                for m in per_run:
                    per_run[m].append(max([float(r["gains"].get(m) or 0.0) for r in ret if r["gains"].get(m) is not None] or [0.0]))
                mat_runs += int(any(material(r["gains"], mat)[0] and not material(r["gains"], mat)[1] for r in ret))
            by_row[f"{key[0]}|{key[1]}"] = {"runs": len(runs), "pending_e4": pending,
                                            "mean": {m: (statistics.mean(v) if v else None) for m, v in per_run.items()}, "max": {m: (max(v) if v else None) for m, v in per_run.items()},
                                            "runs_with_material_retention": mat_runs}
        per_design[d] = {"tier": tier_of.get(d), "status": ("complete" if d in (view.get("complete") or []) else "B0 pending" if d in (view.get("preliminary") or []) else "runs done, evaluations pending" if tier_of.get(d) == "large" else "incomplete"),
                         "rows": by_row, "any_retained": any(r["state"] == "evaluated" and r["ulabel"] == "retained" for r in rd)}
    out["phase5_designs"] = per_design
    out["designs_with_retained"] = {t: {"with": sum(1 for d, v in per_design.items() if v["tier"] == t and v["any_retained"]), "listed": sum(1 for v in per_design.values() if v["tier"] == t)} for t in ("large", "medium")}
    # Exp1 designs from the Phase 4 objects
    p4 = json.load(open(os.path.join(ROOT, "reports", "data", "phase4_exp1.json")))
    ex = {}
    for d in exp1:
        objs = [o for o in p4["objects"] if o["design_id"] == d and o.get("role") == "b0" and o.get("verdict") == "proven" and (o.get("gains") or {}).get("E4")]
        ret = [o for o in objs if o.get("label") == "retained"]
        best = {m: (max([float(o["gains"]["E4"].get(m) or 0.0) for o in ret if o["gains"]["E4"].get(m) is not None] or [0.0]) if ret else None) for m in ("area", "power", "wns")}
        ex[d] = {"proven_with_e4": len(objs), "retained": len(ret), "best_retained_gain": best, "material_any": sum(1 for o in ret if material(o["gains"]["E4"], mat)[0] and not material(o["gains"]["E4"], mat)[1])}
    out["exp1_b0"] = ex
    out["exp1_designs_with_retained"] = sum(1 for v in ex.values() if v["retained"])
    # shares of harmful and absorbed_identical among evaluated proven candidates per arm (Phase 5) and concentration by evidence tag
    by_arm = {}
    for arm in sorted({r["arm"] for r in p5rows}):
        ev = [r for r in p5rows if r["arm"] == arm and r["state"] == "evaluated"]
        cnt = collections.Counter(r["ulabel"] for r in ev)
        by_arm[arm] = {"evaluated": len(ev), "harmful": cnt.get("harmful", 0), "absorbed_identical": cnt.get("absorbed_identical", 0), "retained": cnt.get("retained", 0), "tradeoff": cnt.get("tradeoff", 0),
                       "harmful_share": rate(cnt.get("harmful", 0), len(ev)), "absorbed_identical_share": rate(cnt.get("absorbed_identical", 0), len(ev))}
    out["shares_by_arm"] = by_arm
    tags = collections.defaultdict(lambda: {"retained": 0, "tradeoff": 0})
    for r in p5rows:
        if r["state"] == "evaluated" and r["ulabel"] in ("retained", "tradeoff"):
            for tg in (r["tags"] or ["(no evidence tag)"]):
                tags[tg][r["ulabel"]] += 1
    out["retained_vs_tradeoff_by_tag"] = dict(sorted(tags.items(), key=lambda kv: -(kv[1]["retained"] + kv[1]["tradeoff"])))
    notes = (cfg.get("exp5") or {}).get("design_notes") or {}
    out["large_three"] = {"drrtl_LSTM": notes.get("drrtl_LSTM"), "cktevo_hsm__hsm": notes.get("cktevo_hsm__hsm"), "drrtl_tv80": notes.get("drrtl_tv80") + "; D-vs-D proven under harness_version 2 (DECISION 2026-09-18 C2)" if notes.get("drrtl_tv80") else None,
                          "e1_note": "E1 (a) / (b) re-prove the harness_version-1 falsified records of router and tv80 under harness_version 2 in the offline pool after the small tier (DECISION 2026-09-18 (d) E1, (g) 4): a flip to proven adds candidates to those designs' E4 evaluation and can add retained ones."}
    return out


# ----------------------------------------------------------------------------- §5 denominators
def section_denominators(cfg, conn, p5rows):
    out = {}
    tier_of = P5.tier_of_design(cfg)
    q = src("proven rates per design and class", "Phase 5 candidate scan: candidates with a verdict (proven / falsified / inconclusive / sim_fail / rejected / error) per design and class_final; proven rate = proven / with verdict")
    per = {}
    for d in sorted({r["design_id"] for r in p5rows}, key=lambda d: (tier_of.get(d), d)):
        rd = [r for r in p5rows if r["design_id"] == d and r["verdict"]]
        row = {"tier": tier_of.get(d), "with_verdict": len(rd), "proven": sum(1 for r in rd if r["verdict"] == "proven"), "inconclusive": sum(1 for r in rd if r["verdict"] == "inconclusive"),
               "by_class": {}}
        for cls in CLASSES:
            rc = [r for r in rd if r["class_final"] == cls]
            if rc:
                row["by_class"][cls] = {"n": len(rc), "proven": sum(1 for r in rc if r["verdict"] == "proven"), "inconclusive": sum(1 for r in rc if r["verdict"] == "inconclusive")}
        per[d] = row
    out["per_design"] = per
    # inconclusive share per class with the harness split
    q = src("inconclusive share per class, v1 / v2", "candidates with a verdict per class_final and harness_version (NULL or 1 = harness_version 1, 2 = corrected V3 initial-state handling, DECISION 2026-09-18 C1–C4)")
    hv = {}
    for cls in CLASSES:
        for v in ("v1", "v2"):
            rc = [r for r in p5rows if r["class_final"] == cls and r["verdict"] in ("proven", "inconclusive") and ((r.get("harness_version") or 1) >= 2) == (v == "v2")]
            if rc:
                hv[f"{cls}|{v}"] = {"finished": len(rc), "inconclusive": sum(1 for r in rc if r["verdict"] == "inconclusive"), "share": rate(sum(1 for r in rc if r["verdict"] == "inconclusive"), len(rc))}
    out["inconclusive_by_class_harness"] = hv
    try:
        vc = P5.verification_conditions(cfg, conn)
        agg = collections.defaultdict(lambda: {"above": [0, 0], "below": [0, 0]})
        for d, byc in (vc.get("rows") or {}).items():
            for cls, v in byc.items():
                for side in ("above", "below"):
                    agg[cls][side][0] += v[side][0]; agg[cls][side][1] += v[side][1]
        out["inconclusive_by_load"] = {"threshold": vc.get("threshold"), "n": vc.get("n"), "from": vc.get("from"),
                                       "by_class": {cls: {side: {"proven": v[side][0], "inconclusive": v[side][1], "share": rate(v[side][1], v[side][0] + v[side][1])} for side in ("above", "below")} for cls, v in agg.items()},
                                       "source": src("inconclusive share by load", "src.analysis.phase5.verification_conditions (1-minute host load at the proof's start above / at or below 100, DECISION 2026-09-18 (h) 1; §7c of the stage reports)")}
    except Exception as e:
        out["inconclusive_by_load"] = {"error": f"{type(e).__name__}: {e}"}
    out["dc_rejected"] = {d: [(c, a, t) for c, a, t in v] for d, v in P5.dc_rejected(conn, cfg).items()}
    out["dc_rejected_source"] = src("formal-accepted, synthesis-rejected", "candidates.e4_failure (DECISION 2026-09-19 (n) 1: terminal DC rejections with the DC error id) via src.analysis.phase5.dc_rejected")
    out["prescreen"] = {"source": src("prescreen and superseded runs", "candidates.prescreened = 1 per design (large-tier M, DECISION 2026-09-18 (b) 1c); runs with status superseded or superseded_by set per design and reason"),
                        "prescreened_by_design": {r[0]: r[1] for r in conn.execute("SELECT c.design_id, COUNT(*) FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase5' AND COALESCE(c.prescreened,0)=1 GROUP BY 1")},
                        "superseded_runs": {r[0]: {"n": r[2], "reason": r[1]} for r in conn.execute("SELECT design_id, COALESCE(superseded_reason, 'superseded'), COUNT(*) FROM runs WHERE exp='phase5' AND (status='superseded' OR superseded_by IS NOT NULL) GROUP BY 1, 2")}}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("report_phase", os.path.join(ROOT, "scripts", "report_phase.py"))
        RP = importlib.util.module_from_spec(spec); spec.loader.exec_module(RP)
        lb = RP.proof_latency_bound(conn, cfg)
        out["proof_latency_bound"] = {d: {"median_min": round(v["median_s"] / 60.0, 1), "empty_archive_builds": sum(x for x, _ in v["empty"].values()), "builds": sum(n for _, n in v["empty"].values())} for d, v in lb.items()}
        out["proof_latency_bound_source"] = src("proof-latency-bound designs", "scripts/report_phase.proof_latency_bound (median proof latency over the finished Phase 5 proofs above the 1 800 s generation window; archive-at-build from gen_summary.archive_json; DECISION 2026-09-19 (k) 3, (l) 4)")
    except Exception as e:
        out["proof_latency_bound"] = {"error": f"{type(e).__name__}: {e}"}
    return out


# ----------------------------------------------------------------------------- §6 missing
def section_missing(cfg, conn, view, p5rows):
    tier_of = P5.tier_of_design(cfg)
    b0_pending = collections.Counter(r["tier"] for r in p5rows if r["arm"] == "B0" and r["state"] == "e4_pending")
    pre = collections.Counter(r["state"] for r in p5rows if int(r.get("prescreened") or 0))
    items = [
        {"item": "hidden-layer retention column (H1 / H2a / H2b / H3 / H5 / H4 on accepted and audit candidates)", "owner": "hidden worker; scripts/report_hidden.py", "stage": "sealed until PHASE5_COMPLETE: yes (spec 06, DECISION 2026-09-19 (p) / (q))", "status": "sealed; bulk execution starts when the small tier's search runs finish"},
        {"item": "large-tier B0 offline E4", "owner": "offline pool (b0_e4 group)", "stage": "Stage A completeness", "status": f"proven B0 without E4: large {b0_pending.get('large', 0)}, medium {b0_pending.get('medium', 0)}, small {b0_pending.get('small', 0)} (pending)"},
        {"item": "prescreened candidates' simulation, E4 and proofs (large-tier M)", "owner": "offline pool (prescreened group; proofs after the small tier, DECISION 2026-09-18 (d) B5 / (q) 2)", "stage": "Phase 5 completion condition", "status": f"sim pending {pre.get('prescreened_sim_pending', 0)}, E4 pending {pre.get('prescreened_e4_pending', 0)}, proof pending {pre.get('proof_pending', 0)}"},
        {"item": "E1 (a) / (b) reconciliation (router and tv80 harness_version-1 falsified records re-proven under v2)", "owner": "offline pool after the small tier; operator report (marker reports/data/phase5_e1_ab.done)", "stage": "before PHASE5_COMPLETE (DECISION 2026-09-19 (q) 2)", "status": "pending"},
        {"item": "Phase 6 ladder runs on the Phase 5 accepted candidates and the final map with rung attribution", "owner": "Phase 6 (config exp5.ladder_on_accepted = phase6)", "stage": "Phase 6", "status": "not started"},
        {"item": "E1_authors reproduction of the RTL-OPT pairs", "owner": "Phase 4 §4d", "stage": "done for 33 of 34 pairs", "status": "rtlopt_mux_dead's reference does not link under DC (LINK-3); no further run planned"},
        {"item": "RTLLM contrast finalisation (rules-v2 classes with the LLM review on the Phase 3 candidates, ladder rungs E1d / E2g)", "owner": "Phase 6 / paper", "stage": "contrast table only, never pooled", "status": "E1d / E2g rungs not run on the Phase 3 candidates (n = 0 in reports/phase4.md §8)"},
        {"item": "semantic sub-tags of the map (bit-width, precomputation / LUT, strength reduction, control simplification, resource sharing, state encoding, clock gating)", "owner": "Phase 6 tagging pass", "stage": "Phase 6", "status": "not recorded; rules-v2 evidence tags stand in"},
        {"item": "Dr.RTL paper per-design numbers for the shared designs; the user-run original Dr.RTL reference row (PLAN 5.4)", "owner": "human (transcription; the reference row is triggered manually)", "stage": "paper", "status": "not started"},
    ]
    return {"items": items, "completion": {"complete": view.get("complete"), "preliminary": view.get("preliminary"), "tally": {k: len(v) for k, v in (view.get("tally") or {}).items()}}}


# ----------------------------------------------------------------------------- §7 definitions
def section_definitions(cfg):
    m6 = json.load(open(os.path.join(ROOT, "reports", "data", "phase3_m6_agreement.json")))
    defs = {
        "labels": {
            "absorbed_identical": "E4 fingerprint identical to D's (equal cell histogram, area and cell count): the synthesizer already produces D's netlist (spec 04 §B step 2)",
            "duplicate": "E4 fingerprint identical to an earlier candidate's of the same run (spec 04 §B step 3); never counted in the map",
            "retained": "some component g > t_D and none < −t_D (rule A band; spec 04 §B step 4); on a spread / offset design a retained candidate must also beat the envelope of its own surface perturbations (arm M's extra check; the uniform caliber stops at rule A)",
            "absorbed": "fingerprint converged at E4 with a lower rung where D reaches the candidate's PPA: rung attribution compares the candidate with D under the same rung (spec 04 §B step 5; Phase 4 objects only)",
            "noise": "fingerprint not converged and every component within the band (step 6)",
            "harmful": "some component g < −t_D and none > t_D (step 7); sub-label blocks_synthesis when the resource diff shows DesignWare / datapath extraction in D absent from C",
            "tradeoff": "some component > t_D and some < −t_D, dimensions named (step 8)",
            "fragile": "retained by rule A but not above the envelope of the candidate's own perturbations on a spread / offset design (arm M only)",
        },
        "rule_A": "t_D = max(2.0 × σ_robust, the design's own max |δ| including P0, the pooled q90); designs without a measured floor carry the pooled minimum (floor_source pooled); frozen as floor_version phase4 (DECISIONS 2026-09-14, G4.3); gains relative to D: area and power relative, WNS in clock periods at Φ_main (src/diagnose/m3.relative_gains)",
        "materiality": "area 1 %, power 2 %, WNS 1 % of the period (config noise.materiality) — reported beside every retention figure, never used as a verdict",
        "classes": "rules v2 (src/classify/rules.py, spec 04 §A; docs/spec/04-classifier-diagnoser.md): (a) same registers and stored values; (b) latency-preserving refactor with unchanged register count; (c1) latency-preserving refactor with changed register count; (c2) output-timing change (latency mapping); (d) operator family gained (multiply / divide, add / subtract, variable shift in C's word-level RTLIL histogram absent from D's) or a longest-combinational-path ratio ≥ 3.0",
        "classes_validation_60": {"source": "reports/data/phase3_m6_agreement.json and reports/phase3.md §6a (60 candidates read by hand, seed 2)", "n": m6.get("n"), "human_class_counts": m6.get("human_class_counts"), "rules": m6.get("rules")},
    }
    return defs


# ----------------------------------------------------------------------------- rendering
def _lab_cells(t):
    return " | ".join(f"{cls}: n {v['n']}, " + ", ".join(f"{l} {n}" for l, n in v["labels"].items()) + f"; retention {pct(v['retention_rate'])}; material {v['material']['any']} ({pct(v['material']['rate_any'])}; area {v['material']['area']}, power {v['material']['power']}, WNS {v['material']['wns']})" for cls, v in t.items())


def render_class_table(L, title, t, note=None):
    L += [f"**{title}**", "", "| class | n (proven, E4 in) | retained | tradeoff | absorbed_identical | absorbed | noise | harmful | retention rate | material (any / area / power / WNS) |", "|---|---|---|---|---|---|---|---|---|---|"]
    tot = {"n": 0, "retained": 0, "material": 0}
    for cls in CLASSES + ("free", "?"):
        v = t.get(cls)
        if not v:
            continue
        lb = v["labels"]
        L.append(f"| {cls} | {v['n']} | {lb.get('retained', 0)} | {lb.get('tradeoff', 0)} | {lb.get('absorbed_identical', 0)} | {lb.get('absorbed', 0)} | {lb.get('noise', 0)} | {lb.get('harmful', 0)} | {pct(v['retention_rate'])} | "
                 f"{v['material']['any']} ({pct(v['material']['rate_any'])}) / {v['material']['area']} / {v['material']['power']} / {v['material']['wns']} |")
        tot["n"] += v["n"]; tot["retained"] += v["retained"]; tot["material"] += v["material"]["any"]
    if tot["n"]:
        L.append(f"| all | {tot['n']} | {tot['retained']} | | | | | | {pct(rate(tot['retained'], tot['n']))} | {tot['material']} ({pct(rate(tot['material'], tot['n']))}) / / / |")
    if note:
        L.append(f"\n{note}")
    L.append("")


def render(data):
    v = data["versions"]
    L = [f"# C1 interim evidence report — {data['date']} (visible layer only; interim)", "",
         f"Generated {data['generated_at']} by scripts/report_c1.py (git {v['git_sha']}, cfg {v['cfg_hash']}); floor_version **{v['floor_version']}**, equiv_version **{v['equiv_version']}**, harness_version now **{v['harness_version']}** (v1 / v2 split wherever both exist); "
         f"data: reports/data/c1_interim.json. No record, default or configuration was altered; results/hidden was not read. Rule A with each design's frozen floor throughout; per-metric verdicts (area, WNS at Φ_main in clock periods, power); the materiality row (area {pct(data['map']['materiality']['area'], 0)}, power {pct(data['map']['materiality']['power'], 0)}, WNS {pct(data['map']['materiality']['wns'], 0)} of the period) beside every retention figure. "
         f"'pending' marks evaluation that is not complete. Phase 5 state at generation: runs {data['phase5_runs']}.", ""]
    # §0 summary
    L += ["## 0. Plain-language summary", ""] + data["summary"] + [""]
    # §1
    f = data["floors"]
    L += ["## 1. The residual definition and the noise floor", "",
          f"Floor as frozen for Phase 5 (floor_version {f['floor_version']}, rule A, k_σ {f['k_sigma']}). Source: {f['pooled_min_source']}.", "",
          "| E4 | pooled minimum | median t_D (148 set designs) | max t_D |", "|---|---|---|---|"]
    for m, key in (("area", "area"), ("power", "power_saif"), ("WNS (of the period)", "wns")):
        s = f["summary_t_d_E4"].get(key) or {}
        L.append(f"| {m} | {pct(f['pooled_min_E4'].get(key), 2)} | {pct(s.get('median'), 2)} | {pct(s.get('max'), 1)} |")
    L += ["", "Floor classes at E4 (area row of the frozen table; pooled = no measured floor, the pooled minimum applies):", "", "| design set | n | quiet | spread | offset | pooled | median t_D area (measured) | max |", "|---|---|---|---|---|---|---|---|"]
    for name, title in (("held30", "30 Phase 5 designs"), ("exp1", "10 Exp1 designs")):
        c = f["floor_classes"][name]
        L.append(f"| {title} | {c['n']} | {c['counts'].get('quiet', 0)} | {c['counts'].get('spread', 0)} | {c['counts'].get('offset', 0)} | {c['counts'].get('pooled', 0)} | {pct(c['t_d_area_median'], 2)} | {pct(c['t_d_area_max'], 1)} |")
    L.append(f"| all set designs (reports/phase2.md §2) | 179 | {f['floor_classes_all_E4'].get('quiet')} | {f['floor_classes_all_E4'].get('spread')} | {f['floor_classes_all_E4'].get('offset')} | {f['floor_classes_all_E4'].get('pooled')} | | |")
    L += ["", f"|δ| of the perturbations against D by configuration and metric over the 40 designs ({f['designs_with_perturbation_records']} of them with perturbation records at E4; the others carry the pooled floor). Source: {[s['source'] for s in SOURCES if s['table'] == '|delta| quantiles'][0]}", "",
          "| config | metric | n pairs | q90 | q95 | q99 | max |", "|---|---|---|---|---|---|---|"]
    for k, q in f["delta_quantiles"].items():
        cfg_, met = k.split("|")
        L.append(f"| {cfg_} | {met} | {q['n']} | {pct(q['q90'], 2)} | {pct(q['q95'], 2)} | {pct(q['q99'], 2)} | {pct(q['max'], 2)} |")
    h = f["heavy_tail_E4"]
    L += ["", f"Heavy tail at E4: {h['n_over_1pct']} perturbation records move area by more than 1 % ({h['n_over_5pct']} by more than 5 %); by type {h['by_ptype_over_1pct']}; by design {h['by_design_over_1pct']}.",
          f"Retained verdicts so far on offset designs (flagged): {data['retained_on_offset']['n']} of {data['retained_on_offset']['retained_total']} rule-A retained Phase 5 candidates ({data['retained_on_offset']['designs']}).", "",
          "Ladder facts restated (" + f["ladder_facts"]["source"] + "):", ""]
    for k in ("E1_to_E2", "no_op_flags", "designware", "retiming", "gate_clock"):
        L.append(f"- {k.replace('_', ' ')}: {f['ladder_facts'][k]}")
    nm = f["ladder_facts"]["non_monotone_counts"]
    L += [f"- non-monotone D across the rungs ({nm['designs']} designs): " + "; ".join(f"{k}: area grows on {v['area_grows']}, WNS drops on {v['wns_drops']}" for k, v in nm.items() if isinstance(v, dict)) + f". {nm['note']}", ""]
    # §2
    mp = data["map"]
    L += ["## 2. The map: rewrite class × verdict (interim aggregate)", "",
          f"Every E4-evaluated proven candidate available today, rule A with the frozen floors; the materiality column counts retained candidates whose gain exceeds the materiality threshold on at least one metric with none below it (any) and per metric. {mp['rung_attribution_note']}", "",
          f"### 2.1 Phase 4 objects (source: {mp['phase4_source']}; {mp['phase4']['n_proven_with_e4']} proven objects with an E4 record, duplicates excluded)", ""]
    for role in ("b0", "reference", "llm"):
        r = mp["phase4"]["by_role"][role]
        render_class_table(L, r["title"], r["table"])
    L.append(f"Absorbed objects by attributed rung (Phase 4): {mp['phase4']['absorbed_rungs']}. Map shape on B0 objects (reports/phase4.md §2): **{(mp['phase4'].get('shape') or {}).get('shape')}**, E4 retention by class {json.dumps((mp['phase4'].get('shape') or {}).get('e4_retention_by_class'))}.")
    L.append("")
    L += ["By design family (Phase 4 objects, every role):", ""]
    for fam, t in mp["phase4"]["by_family"].items():
        render_class_table(L, fam, t)
    L += ["### 2.2 Phase 5 candidates by tier and arm (rule A at E4; B0 where its offline E4 is in, otherwise pending)", ""]
    for t, tv in mp["phase5"]["tiers"].items():
        L += [f"#### {t} tier — runs: " + ", ".join(f"{k} {v}" for k, v in sorted(tv['runs'].items())), ""]
        for arm, av in tv["by_arm"].items():
            hv = av["harness"]
            render_class_table(L, f"{t} / {arm}: proven {av['proven']} (harness v1 {hv['v1']} / v2 {hv['v2']}), E4 in {av['evaluated']}, E4 pending {av['e4_pending']}" + (f", DC-rejected (terminal) {av['dc_rejected']}" if av["dc_rejected"] else ""), av["table"])
        render_class_table(L, f"{t} tier, all arms", tv["all_arms"])
        if tv["prescreened_proof_pending"]["n"]:
            render_class_table(L, f"{t} tier, prescreened class-(a) candidates with simulation and E4 done — proof pending ({tv['prescreened_proof_pending']['n']}; not pooled with the proven ones)", tv["prescreened_proof_pending"]["table"])
        if tv["prescreened_sim_pending"] or tv["prescreened_e4_pending"]:
            L.append(f"Prescreened candidates still pending: simulation {tv['prescreened_sim_pending']}, E4 {tv['prescreened_e4_pending']}.\n")
    L += ["By design family (Phase 5, every arm, evaluated candidates):", ""]
    for fam, t in mp["phase5"]["by_family"].items():
        render_class_table(L, fam, t)
    L += ["Evidence tags (rules v2) among the evaluated Phase 5 candidates by rule-A label:", "", "| evidence tag | retained | tradeoff | absorbed_identical | noise | harmful |", "|---|---|---|---|---|---|"]
    for tg, cnt in list(mp["phase5"]["evidence_tags"].items())[:16]:
        L.append(f"| {tg} | {cnt.get('retained', 0)} | {cnt.get('tradeoff', 0)} | {cnt.get('absorbed_identical', 0)} | {cnt.get('noise', 0)} | {cnt.get('harmful', 0)} |")
    L += ["", mp["phase5"]["subtag_note"], "", "### 2.3 RTLLM contrast (dev designs; never pooled with the map)", "", f"Source: {mp['rtllm_contrast']['source']}. Shape: {json.dumps(mp['rtllm_contrast'].get('shape'))}.", "",
          "| class | E4 retention rate (n) | under materiality |", "|---|---|---|"]
    for cls, c in (mp["rtllm_contrast"].get("map_e4_by_class") or {}).items():
        m = (mp["rtllm_contrast"].get("map_materiality_e4_by_class") or {}).get(cls) or {}
        L.append(f"| {cls} | {pct((c or {}).get('retention_rate'))} ({(c or {}).get('n_evaluated')}) | {pct(m.get('retention_rate'))} ({m.get('n_evaluated')}) |")
    L.append("")
    # §3
    lt = data["literature"]
    L += ["## 3. The literature's caliber versus E4", "", f"### 3a. B0 arm: Yosys-caliber labels against rule A at E4 (source: {lt['b0_source']})", "",
          "| tier | proven | E4 in | E4 pending | Yosys 'improved' with E4 | of which retained | tradeoff | absorbed_identical | noise | harmful |", "|---|---|---|---|---|---|---|---|---|---|"]
    for t, tv in lt["b0"].items():
        sh = tv["improved_share"]
        L.append(f"| {t} | {tv['proven']} | {tv['evaluated']} | {tv['pending']} | {tv['yosys_improved_evaluated']} | {tv['improved_at_e4'].get('retained', 0)} ({pct(sh['retained'])}) | {tv['improved_at_e4'].get('tradeoff', 0)} ({pct(sh['tradeoff'])}) | {tv['improved_at_e4'].get('absorbed_identical', 0)} ({pct(sh['absorbed_identical'])}) | {tv['improved_at_e4'].get('noise', 0)} ({pct(sh['noise'])}) | {tv['improved_at_e4'].get('harmful', 0)} ({pct(sh['harmful'])}) |")
    L += ["", "| tier | design | proven | E4 in | pending | DC-rejected | Yosys improved | improved at E4 (rule A) | no_gain at E4 (rule A) |", "|---|---|---|---|---|---|---|---|---|"]
    for t, tv in lt["b0"].items():
        for d, dv in tv["per_design"].items():
            L.append(f"| {t} | {d} | {dv['proven']} | {dv['evaluated']} | {dv['pending']} | {dv['dc_rejected']} | {dv['yosys_improved']} | {dv['improved_at_e4']} | {dv['no_gain_at_e4']} |")
    pl = lt["phase4_literature"]
    L += ["", f"### 3b. Phase 4 literature re-evaluation restated (source: {pl['source']})", "",
          "| suite | pairs | proven | better at E1 | retained at E1 | better at E4 | retained at E4 | evaluated |", "|---|---|---|---|---|---|---|---|"]
    for s in ("rtlopt", "rtlrewriter"):
        r = pl[s]
        L.append(f"| {s} | {r['pairs']} | {r['proven']} | {r['better']['E1']} | {r['retained']['E1']} | {r['better']['E4']} | {r['retained']['E4']} | {r['evaluated']['E4']} |")
    rc = pl["rtlopt_reconciliation"]
    L += ["", f"RTL-OPT reconciliation (reports/phase4.md §4d): paper claim {rc['paper_claim']}; the authors' released reports {rc['released_reports'].get('better_by_area')} of {rc['released_reports'].get('n')} better by area at their plain-compile / 0.1 ns setting; "
          f"E1_authors (their settings reproduced on this DC): {rc['counts_by_setting']['E1_authors']}; E2_1ns (the paper's Table 1 setting as described): {rc['counts_by_setting']['E2_1ns']}. E1_authors is {pl['e1_authors_records']['complete']} ({pl['e1_authors_records']['records']} records over {pl['e1_authors_records']['designs']} designs).",
          f"Non-equivalent literature objects (excluded from every count; {pl['non_equivalent']['source']}): {pl['non_equivalent']['n']} — by role {pl['non_equivalent']['by_role']}; by probable cause {pl['non_equivalent']['by_cause']}.",
          "add_sub (reports/phase4.md §4d): the reference is +93.7 % area at E2 / E4 against −19.6 % in the authors' released reports and −15.1 % under E1_authors; RTLRewriter's E1 → E4 drop (24 → 10 better) includes the memory_sharing pairs (reports/phase4.md §4).", "",
          f"### 3c. Dr.RTL shared designs (source: {lt['drrtl']['source']})", "",
          "| design | status | note | our arms at E4, rule A: proven (E4 in) / retained / best retained gain area · power · WNS | Phase 4 B0 | paper |", "|---|---|---|---|---|---|"]
    for d, r in lt["drrtl"]["rows"].items():
        arms = "; ".join(f"{a}: {v['proven_evaluated']} / {v['retained']} / {pct(v['best_retained_gain']['area'])} · {pct(v['best_retained_gain']['power'])} · {pct(v['best_retained_gain']['wns'])}" for a, v in r["phase5_by_arm"].items()) or "-"
        p4 = r["phase4_b0"]
        p4txt = "-" if not p4 else (f"objects {p4['objects']}, retained {p4['retained']}, best area {pct(p4['best_area'])}" if p4["objects"] else f"{p4['all_objects']} objects, none proven with an E4 record (verdicts {p4['verdicts']})")
        L.append(f"| {d} | {r['status']} | {r['note'] or '-'} | {arms} | {p4txt} | {r['paper']} |")
    L += ["", f"Reference row: {lt['drrtl']['reference_row']}.", ""]
    # §4
    sv = data["survives"]
    L += ["## 4. What survives on human-written RTL", "", f"Source: {sv['source']}. Per row: mean over seeds of the run's best retained gain per metric (the tally rule), max alongside; 'runs with material retention' = runs with a retained candidate above the materiality threshold on some metric and below on none.", "",
          "| design | tier | status | model | arm | runs | E4 pending | area mean / max | power mean / max | WNS mean / max | runs with material retention |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for d, dv in sv["phase5_designs"].items():
        for k, rv in dv["rows"].items():
            m, a = k.split("|")
            L.append(f"| {d} | {dv['tier']} | {dv['status']} | {m.split('-')[-1]} | {a} | {rv['runs']} | {rv['pending_e4']} | {pct(rv['mean']['area'], 2)} / {pct(rv['max']['area'], 2)} | {pct(rv['mean']['power'], 2)} / {pct(rv['max']['power'], 2)} | {pct(rv['mean']['wns'], 2)} / {pct(rv['max']['wns'], 2)} | {rv['runs_with_material_retention']} |")
    L += ["", f"Designs with any rule-A retained candidate: large {sv['designs_with_retained']['large']['with']} of {sv['designs_with_retained']['large']['listed']}; medium (complete or B0 pending) {sv['designs_with_retained']['medium']['with']} of {sv['designs_with_retained']['medium']['listed']}; Exp1 (Phase 4 B0 objects) {sv['exp1_designs_with_retained']} of {len(sv['exp1_b0'])}.", "",
          "| Exp1 design (Phase 4 B0 objects, max over objects) | proven with E4 | retained | best area | best power | best WNS | material |", "|---|---|---|---|---|---|---|"]
    for d, e in sv["exp1_b0"].items():
        L.append(f"| {d} | {e['proven_with_e4']} | {e['retained']} | {pct(e['best_retained_gain']['area'], 2)} | {pct(e['best_retained_gain']['power'], 2)} | {pct(e['best_retained_gain']['wns'], 2)} | {e['material_any']} |")
    L += ["", "| arm (Phase 5, evaluated proven candidates) | evaluated | retained | tradeoff | harmful (share) | absorbed_identical (share) |", "|---|---|---|---|---|---|"]
    for a, s in sv["shares_by_arm"].items():
        L.append(f"| {a} | {s['evaluated']} | {s['retained']} | {s['tradeoff']} | {s['harmful']} ({pct(s['harmful_share'])}) | {s['absorbed_identical']} ({pct(s['absorbed_identical_share'])}) |")
    L += ["", "| evidence tag | retained | tradeoff |", "|---|---|---|"]
    for tg, c in list(sv["retained_vs_tradeoff_by_tag"].items())[:12]:
        L.append(f"| {tg} | {c['retained']} | {c['tradeoff']} |")
    lt3 = sv["large_three"]
    L += ["", f"The three large designs: LSTM — {lt3['drrtl_LSTM']}; hsm — {lt3['cktevo_hsm__hsm']}; tv80 — {lt3['drrtl_tv80']}. {lt3['e1_note']}", ""]
    # §5
    dn = data["denominators"]
    L += ["## 5. Denominators and their caveats", "", "| design | tier | with verdict | proven | inconclusive | per class: n / proven / inconclusive |", "|---|---|---|---|---|---|"]
    for d, r in dn["per_design"].items():
        L.append(f"| {d} | {r['tier']} | {r['with_verdict']} | {r['proven']} ({pct(rate(r['proven'], r['with_verdict']))}) | {r['inconclusive']} ({pct(rate(r['inconclusive'], r['with_verdict']))}) | " + "; ".join(f"{c}: {v['n']} / {v['proven']} / {v['inconclusive']}" for c, v in r["by_class"].items()) + " |")
    L += ["", "Inconclusive share per class, finished proofs (proven or inconclusive), by harness version:", "", "| class | v1 finished | v1 inconclusive | v2 finished | v2 inconclusive |", "|---|---|---|---|---|"]
    for cls in CLASSES:
        a, b = dn["inconclusive_by_class_harness"].get(f"{cls}|v1"), dn["inconclusive_by_class_harness"].get(f"{cls}|v2")
        if a or b:
            L.append(f"| {cls} | {(a or {}).get('finished', 0)} | {pct((a or {}).get('share'))} | {(b or {}).get('finished', 0)} | {pct((b or {}).get('share'))} |")
    il = dn.get("inconclusive_by_load") or {}
    if "by_class" in il:
        L += ["", f"Inconclusive share by 1-minute host load at the proof's start (threshold {il['threshold']}; {il['n']} proofs since {il['from']}):", "", "| class | load above: proven / inconclusive (share) | load at or below: proven / inconclusive (share) |", "|---|---|---|"]
        for cls, v in il["by_class"].items():
            L.append(f"| {cls} | {v['above']['proven']} / {v['above']['inconclusive']} ({pct(v['above']['share'])}) | {v['below']['proven']} / {v['below']['inconclusive']} ({pct(v['below']['share'])}) |")
    L += ["", "Formal-accepted, synthesis-rejected (terminal, DECISION 2026-09-19 (n) 1): " + ("; ".join(f"{d}: {len(v)} ({', '.join(sorted({t for _, _, t in v}))})" for d, v in dn["dc_rejected"].items()) or "none") + ".",
          f"Prescreened candidates (large-tier M): {dn['prescreen']['prescreened_by_design']}; superseded runs: {dn['prescreen']['superseded_runs']}.",
          "Proof-latency-bound designs (median proof latency above the 1 800 s generation window; empty-archive builds / builds): " + ("; ".join(f"{d} {v['median_min']} min ({v['empty_archive_builds']} / {v['builds']})" for d, v in dn["proof_latency_bound"].items() if isinstance(v, dict) and "median_min" in v) or str(dn["proof_latency_bound"])) + ".", "",
          "How each caveat bounds a C1 number (direction of bias):",
          "- Inconclusive proofs (SEQ class cap, CPU contention): candidates without a verdict are neither retained nor absorbed; every retention rate is over proven candidates only, so the rates describe the provable subset — on SPI / simple_spi / tv80 (85–99 % inconclusive in class b) the map is nearly empty and says nothing about those designs; harness_version 2 changed verdicts on router only (v1 falsified records under E1 reconciliation).",
          "- Synthesis-rejected candidates (formal-accepted): 8 proven candidates that DC rejects are terminal and count as resolved, not as retained or harmful — a small downward bias on the proven denominator of eth_cop, sub_32bit, mc_adr_sel, UART, thresholds.",
          "- Prescreen (large-tier M): 641 class-(a) candidates were routed to the offline pool without a search-time proof; their E4 labels are provisional ('proof pending') and are not pooled with the proven ones — the large-tier M row is incomplete until their proofs run after the small tier.",
          "- Superseded runs (LSTM harness defect, router formal step, simple_spi include file, replaced thresholds run): their stored candidates are out of every table; the repeats are counted as they finish — LSTM's are held until the small tier, so the large tier's Dr.RTL rows are incomplete.",
          "- Proof-latency-bound designs: the search reduced to E4-guided one-shot rewriting where the archive stayed empty (tv80, cpu; partly aes, SPI, simple_spi) — arm differences on those designs measure one-shot rewriting, not search.",
          "- B0's offline E4: B0 rows are pending wherever their pool E4 is not in; the large tier's aes B0 (107 proven without E4 at generation time) is the largest gap.", ""]
    # §6
    ms = data["missing"]
    L += ["## 6. Missing for C1", "", "| item | owner | stage | status |", "|---|---|---|---|"]
    for it in ms["items"]:
        L.append(f"| {it['item']} | {it['owner']} | {it['stage']} | {it['status']} |")
    L += ["", f"Completion at generation: complete {ms['completion']['complete']}, B0 pending {ms['completion']['preliminary']}, tally {ms['completion']['tally']}.", ""]
    # §7
    df = data["definitions"]
    L += ["## 7. Appendix: definitions and sources", "", "Labels (docs/spec/04-classifier-diagnoser.md §B; src/diagnose/m3.diagnose):", ""]
    for k, vtxt in df["labels"].items():
        L.append(f"- **{k}** — {vtxt}")
    L += ["", f"Rule A: {df['rule_A']}", f"Materiality: {df['materiality']}", f"Classes: {df['classes']}", "",
          f"Rules-v2 validation on {df['classes_validation_60']['n']} hand-read candidates ({df['classes_validation_60']['source']}): human class counts {df['classes_validation_60']['human_class_counts']}; rules {json.dumps(df['classes_validation_60']['rules'])[:600]}", "",
          "Queries and collector calls behind the tables (in order of first use):", ""]
    for s in data["sources"]:
        L.append(f"- {s['table']}: `{s['source']}`")
    L.append("")
    return "\n".join(L)


def summary_lines(data):
    mp, lt, sv = data["map"], data["literature"], data["survives"]
    p4b0 = mp["phase4"]["by_role"]["b0"]["table"]
    tot_n = sum(v["n"] for v in p4b0.values()); tot_r = sum(v["retained"] for v in p4b0.values()); tot_m = sum(v["material"]["any"] for v in p4b0.values())
    p5 = mp["phase5"]["tiers"]
    p5n = sum(v["all_arms"].get(c, {}).get("n", 0) for v in p5.values() for c in CLASSES + ("free", "?"))
    p5r = sum(v["all_arms"].get(c, {}).get("retained", 0) for v in p5.values() for c in CLASSES + ("free", "?"))
    p5m = sum(v["all_arms"].get(c, {}).get("material", {}).get("any", 0) for v in p5.values() for c in CLASSES + ("free", "?"))
    b0 = lt["b0"]
    b0imp = sum(v["yosys_improved_evaluated"] for v in b0.values()); b0ret = sum(v["improved_at_e4"].get("retained", 0) for v in b0.values()); b0abs = sum(v["improved_at_e4"].get("absorbed_identical", 0) + v["improved_at_e4"].get("noise", 0) for v in b0.values()); b0harm = sum(v["improved_at_e4"].get("harmful", 0) for v in b0.values())
    b0pend = sum(v["pending"] for v in b0.values())
    rl = lt["phase4_literature"]
    return [
        f"1. **Supportable today.** The residual is defined against a measured floor: at E4 the pooled minimum is {pct(data['floors']['pooled_min_E4']['area'], 2)} area / {pct(data['floors']['pooled_min_E4']['power_saif'], 1)} power / {pct(data['floors']['pooled_min_E4']['wns'], 2)} WNS of the period; {data['floors']['floor_classes']['held30']['counts'].get('pooled', 0)} of the 30 Phase 5 designs carry the pooled floor (no measured perturbations at E4), {data['floors']['floor_classes']['held30']['counts'].get('offset', 0)} of them are offset designs (retained verdicts there are flagged: {data['retained_on_offset']['n']} so far, all on mc_adr_sel).",
        f"2. **Supportable.** The ladder is real but not monotone: E1 → E2 is the large step (−6 % to −37 % area on the probe), the high-effort flags are no-ops, DesignWare is a capability of its own (3–6 % either way), retiming and clock gating act only where their structures exist; D's area grows on 10 of 127 designs from E1 to E4.",
        f"3. **Supportable (interim).** Rule A at E4 on the Phase 4 B0 objects (10 human-written designs): {tot_r} of {tot_n} proven objects retained ({pct(rate(tot_r, tot_n))}), {tot_m} of them above the materiality threshold; map shape '{(mp['phase4'].get('shape') or {}).get('shape')}' with E4 retention by class {json.dumps((mp['phase4'].get('shape') or {}).get('e4_retention_by_class'))} — class (a) rewrites are absorbed, (c1) / (d) survive.",
        f"4. **Supportable (interim, incomplete).** Phase 5 so far: {p5r} of {p5n} evaluated proven candidates retained ({pct(rate(p5r, p5n))}), {p5m} above materiality, across {sum(len(v['by_arm']) for v in p5.values())} tier-arm rows; the large tier's runs are done, the medium tier stands at " + ", ".join(f"{v} {k}" for k, v in sorted(data['phase5_runs'].get('medium', {}).items())) + f" (interim), B0's offline E4 is in for all but {b0pend} proven B0 candidates.",
        f"5. **Supportable.** The literature's caliber: of B0's Yosys-'improved' candidates with an E4 record, {b0ret} of {b0imp} are retained at E4 ({pct(rate(b0ret, b0imp))}), {b0abs} are absorbed_identical or noise, {b0harm} harmful; on the literature pairs, RTL-OPT better at E1 {rl['rtlopt']['better']['E1']} → retained at E4 {rl['rtlopt']['retained']['E4']} of {rl['rtlopt']['proven']} proven pairs, RTLRewriter {rl['rtlrewriter']['better']['E1']} → {rl['rtlrewriter']['retained']['E4']} of {rl['rtlrewriter']['proven']}; under the authors' released RTL-OPT setting (plain compile, 0.1 ns) reproduced on this DC 25 of 33 pairs are better, under the paper's described setting (compile_ultra, 1 ns) 13.",
        f"6. **Not yet.** Whether retained gains survive the hidden configurations (C1's certification column) — sealed until PHASE5_COMPLETE; the final map with rung attribution on Phase 5 candidates (Phase 6 ladder runs); the Dr.RTL per-design comparison (paper numbers not transcribed; the reference row not run); the large-tier M row (641 prescreened candidates await their proofs after the small tier).",
        f"7. **Not yet.** Retention on the proof-latency-bound and verification-limited designs (SPI, simple_spi, tv80, cpu; hsm): the proven denominators there are too small, and E1 (a) / (b) may still flip router's and tv80's v1-falsified records.",
        "8. **Three items that would change the picture most.** (i) The hidden-layer column on the accepted candidates (turns visible retention into certified retention or not); (ii) the large-tier prescreened simulations, E4 and proofs plus E1 (a) / (b) (fills the large tier's M and Dr.RTL rows, the designs where the caliber argument is strongest); (iii) the Phase 6 ladder runs on the Phase 5 accepted candidates (rung attribution of what survives — today only the Phase 4 objects carry it).",
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    held = [d for ds in cfg["exp5"]["starting_points"].values() for d in ds]
    exp1 = json.load(open(os.path.join(ROOT, "reports", "data", "phase4_exp1.json")))["designs"]
    data = {"date": a.date, "generated_at": datetime.datetime.now().isoformat(timespec="minutes"),
            "versions": {"git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(), "floor_version": cfg["noise"]["floor_version"], "equiv_version": cfg["equiv"].get("version"), "harness_version": cfg["equiv"].get("harness_version")}}
    data["phase5_runs"] = {}
    tier_of = P5.tier_of_design(cfg)
    for r in conn.execute("SELECT design_id, status, COUNT(*) AS n FROM runs WHERE exp='phase5' AND status != 'superseded' AND COALESCE(excluded_from_tables,0)=0 GROUP BY design_id, status"):
        data["phase5_runs"].setdefault(tier_of.get(r["design_id"], "?"), {}).setdefault(r["status"], 0)
        data["phase5_runs"][tier_of.get(r["design_id"], "?")][r["status"]] += r["n"]
    data["floors"] = section_floors(cfg, conn, held, exp1)
    p5rows, designs = scan_phase5(cfg, conn, held)
    fl = {d: v["class"] for d, v in data["floors"]["floor_classes"]["held30"]["per_design"].items()}
    ret = [r for r in p5rows if r["state"] == "evaluated" and r["ulabel"] == "retained"]
    on_off = [r for r in ret if fl.get(r["design_id"]) == "offset"]
    data["retained_on_offset"] = {"n": len(on_off), "retained_total": len(ret), "designs": dict(collections.Counter(r["design_id"] for r in on_off))}
    data["map"] = section_map(cfg, conn, p5rows, held, exp1)
    data["literature"] = section_literature(cfg, conn, p5rows)
    view = P5.completion_view(cfg, conn)
    data["survives"] = section_survives(cfg, conn, p5rows, view, exp1)
    data["denominators"] = section_denominators(cfg, conn, p5rows)
    data["missing"] = section_missing(cfg, conn, view, p5rows)
    data["definitions"] = section_definitions(cfg)
    data["sources"] = SOURCES
    data["summary"] = summary_lines(data)
    out = a.out or os.path.join(ROOT, "reports", f"c1_interim_{a.date}.md")
    js = a.json or os.path.join(ROOT, "reports", "data", "c1_interim.json")
    os.makedirs(os.path.dirname(js), exist_ok=True)
    with open(js, "w") as f:
        json.dump(data, f, indent=1, default=str)
    with open(out, "w") as f:
        f.write(render(data))
    print(f"written {out} and {js}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
