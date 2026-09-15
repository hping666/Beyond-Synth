"""Object rows of the Phase 4 map from the results database (spec 08, PLAN 4.3–4.5): gains of every Phase 4 object
against its D under each visible configuration, the rule-A thresholds of D under each configuration (frozen floor
version), the M3 diagnosis at E4 with the lower rungs for the absorption attribution, and the predictor features.
Reads the visible database only (rule 3)."""
import json

from src.diagnose import m3
from src.noise import stats as S
from src.search.driver import record_from_row

LADDER = ("E1", "E1d", "E2", "E3", "E2g", "E4")
LOWER_FOR_ATTRIBUTION = ("E1", "E2", "E3")
METRIC_COLS = {"area": "area_um2", "wns": "wns_ns", "power": "power_saif_mw"}


def baseline_row(conn, design_id, config, clock_ns):
    return conn.execute("SELECT * FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' "
                        "AND abs(clock_ns-?)<1e-6 ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (design_id, config, float(clock_ns))).fetchone()


def object_row_eval(conn, cand_id, config, clock_ns):
    return conn.execute("SELECT * FROM evaluations WHERE cand_id=? AND config=? AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1",
                        (cand_id, config, float(clock_ns))).fetchone()


def thresholds(conn, design_id, config, floor_version):
    """{metric: t_d} of D under `config` from the frozen floor table (None when D has no floor there)."""
    fl = S.latest_floor(conn, design_id, config, floor_version) or S.latest_floor(conn, design_id, config)
    out = {}
    for metric, key in (("area", "area"), ("wns", "wns"), ("power", "power_saif")):
        r = fl.get(key) or {}
        out[metric] = float(r["t_d"]) if r.get("t_d") is not None else None
    return out, fl


def phase4_candidates(conn, exp="phase4"):
    return [dict(r) for r in conn.execute("SELECT c.*, r.arm AS run_arm, r.floor_version AS run_floor_version FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                                          "WHERE r.exp=? AND r.status != 'superseded' AND c.rtl_path IS NOT NULL AND c.label IS NOT NULL AND c.label != 'aborted' ORDER BY c.run_id, c.cand_id", (exp,))]


def build_object_rows(cfg, conn, exp="phase4", configs=LADDER):
    """[object row] for src/analysis/map.py: gains and thresholds per configuration, the M6 class, the M3 label at E4
    (from the diagnoses table; None until `diagnose_objects` ran) and the role."""
    floor_version = cfg["noise"].get("floor_version")
    rows = []
    phi = {}
    for c in phase4_candidates(conn, exp):
        did = c["design_id"]
        if did not in phi:
            phi[did] = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (did,)).fetchone()[0]
        if phi[did] is None:
            continue
        gains, t_d = {}, {}
        for config in configs:
            base = baseline_row(conn, did, config, phi[did])
            ev = object_row_eval(conn, c["cand_id"], config, phi[did])
            t_d[config], _ = thresholds(conn, did, config, floor_version)
            if base is None or ev is None:
                continue
            g = m3.relative_gains(record_from_row(base), record_from_row(ev), float(phi[did]))
            gains[config] = {m: (float(g[m]) if g.get(m) is not None else None) for m in ("area", "wns", "power")}
        d = conn.execute("SELECT label, rung, attribution, capability, evidence_json FROM diagnoses WHERE cand_id=?", (c["cand_id"],)).fetchone()
        ev = json.loads(d["evidence_json"] or "{}") if d and d["evidence_json"] else {}
        role = "b0" if c["run_arm"] == "B0" else ("reference" if (c.get("note") or "").startswith("reference") else "llm" if (c.get("note") or "").startswith("llm") else c["run_arm"])
        proven = c.get("verdict") in ("proven", "proven_sim_only")
        rows.append({"cand_id": c["cand_id"], "design_id": did, "run_id": c["run_id"], "cls": c.get("class_final"), "subtags": [], "role": role, "proven": proven,
                     "verdict": c.get("verdict"), "label": d["label"] if d else None, "rung": d["rung"] if d else None, "attribution": d["attribution"] if d else None,
                     "capability": d["capability"] if d else None, "blocks_synthesis": bool(ev.get("missing_resources")), "missing_resources": ev.get("missing_resources") or [],
                     "gains": gains, "t_d": t_d, "features": json.loads(c["features_json"]) if c.get("features_json") else {}})
    return rows


def diagnose_objects(cfg, conn, exp="phase4", dry_run=False):
    """PLAN 4.3: the M3 diagnosis at E4 of every proven Phase 4 object that has an E4 record and no diagnosis yet, with the
    frozen floors (thresholds of the design's floor version) and the lower rungs E1 / E2 / E3 for the absorption rung.
    The acceptance envelope of C2.1(d) is a search-time mechanism and is not applied here (the flag stays in the
    evidence). -> {diagnosed, skipped_no_e4, skipped_not_proven, existing, labels}"""
    floor_version = cfg["noise"].get("floor_version")
    out = {"diagnosed": 0, "skipped_no_e4": 0, "skipped_not_proven": 0, "existing": 0, "labels": {}}
    seen = {}
    for c in phase4_candidates(conn, exp):
        if conn.execute("SELECT 1 FROM diagnoses WHERE cand_id=?", (c["cand_id"],)).fetchone():
            out["existing"] += 1
            continue
        if c.get("verdict") not in ("proven", "proven_sim_only"):
            out["skipped_not_proven"] += 1
            continue
        did = c["design_id"]
        phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (did,)).fetchone()[0]
        base = baseline_row(conn, did, "E4", phi)
        ev = object_row_eval(conn, c["cand_id"], "E4", phi)
        if base is None or ev is None:
            out["skipped_no_e4"] += 1
            continue
        t_d, fl = thresholds(conn, did, "E4", floor_version)
        sigma = {m: float((fl.get(k) or {}).get("sigma_robust") or 0.0) for m, k in (("area", "area"), ("wns", "wns"), ("power", "power_saif"))}
        floor_class = next((r.get("floor_class") for r in fl.values() if r.get("floor_class")), None)
        lower = {}
        for config in LOWER_FOR_ATTRIBUTION:
            b, e = baseline_row(conn, did, config, phi), object_row_eval(conn, c["cand_id"], config, phi)
            if b is not None and e is not None:
                s_cfg = thresholds(conn, did, config, floor_version)[1]
                lower[config] = (record_from_row(b), record_from_row(e), float((s_cfg.get("area") or {}).get("sigma_robust") or sigma["area"] or 0.0))
        fps = seen.setdefault(c["run_id"], {})
        cand = record_from_row(ev)
        diag = m3.diagnose(record_from_row(base), cand, sigma, float(phi), v3_status="proven", k_sigma=float(cfg["noise"]["k_sigma"]),
                           fp_jaccard=float(cfg["diag"]["fp_jaccard"]), lower_rungs=lower or None, thresholds=t_d if all(v is not None for v in t_d.values()) else None,
                           floor_class=floor_class, run_fingerprints=fps)
        fps[c["cand_id"]] = {"metrics": {"area": cand["metrics"]["area"], "cells": cand["metrics"]["cells"]}, "hist": cand["hist"]}
        label = diag["label"]
        out["labels"][label] = out["labels"].get(label, 0) + 1
        out["diagnosed"] += 1
        if dry_run:
            continue
        attribution = diag.get("attribution") if diag.get("attribution") in ("measured", "prior") else None
        from src.db import core as db
        db.insert(conn, "diagnoses", {"cand_id": c["cand_id"], "run_id": c["run_id"], "label": label, "rung": diag.get("rung"), "capability": diag.get("capability"),
                                      "attribution": attribution, "fp_jaccard": (diag.get("evidence") or {}).get("fp_jaccard"), "offset_design": int(bool(diag.get("offset_design"))),
                                      "duplicate_of": diag.get("duplicate_of"), "envelope_json": None, "evidence_json": json.dumps(diag.get("evidence"), default=str),
                                      "feedback_json": json.dumps({"diagnosis": label, "analysis": "phase4 objects (PLAN 4.3)", "envelope_required": bool(diag.get("envelope_required"))}),
                                      "credit": 0, "credited_class": c.get("class_final"), "floor_version": floor_version})
        conn.execute("UPDATE candidates SET label=? WHERE cand_id=? AND label IN ('object','improved','no_gain')", (label, c["cand_id"]))
        conn.commit()
    return out


def predictor_rows(cfg, conn, objs):
    """Feature rows of spec 08 §2 from the object rows plus the E1 fingerprint convergence (m3.converged with D's E1
    sigma) and the archived M6 features (flip-flop delta, diff ratio); target = retained or tradeoff at E4."""
    floor_version = cfg["noise"].get("floor_version")
    rows = []
    for o in objs:
        if o.get("label") is None or o.get("label") == "nonequiv":
            continue
        did = o["design_id"]
        phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (did,)).fetchone()[0]
        b1, e1 = baseline_row(conn, did, "E1", phi), object_row_eval(conn, o["cand_id"], "E1", phi)
        conv = None
        if b1 is not None and e1 is not None:
            s1 = thresholds(conn, did, "E1", floor_version)[1]
            conv = m3.converged(record_from_row(b1), record_from_row(e1), float((s1.get("area") or {}).get("sigma_robust") or 0.0), float(cfg["diag"]["fp_jaccard"]))[0]
        f = o.get("features") or {}
        rows.append({"cand_id": o["cand_id"], "design_id": did, "cls": o.get("cls"),
                     "g_e1": ((o["gains"].get("E1") or {}).get("area")), "g_e2": ((o["gains"].get("E2") or {}).get("area")),
                     "fp_conv_e1": (1 if conv else 0) if conv is not None else 0,
                     "dff_delta": (int(f.get("ff_c") or 0) - int(f.get("ff_d") or 0)) if f else 0, "diff_ratio": f.get("diff_ratio") if f else 0.0,
                     "retained_e4": int(o["label"] in ("retained", "tradeoff"))})
    return rows
