"""Diagnoser M3 (docs/spec/04-classifier-diagnoser.md §B): from a candidate's E4 record, the design's E4 baseline,
the noise floor sigma_D and (optionally) lower-rung records, derive the five-way label retained / absorbed / noise /
harmful / tradeoff (or nonequiv when V3 did not prove the candidate), the rung and capability attribution, the
evidence and the feedback block (§B.3). Records are the evaluation dicts of src/eval (metrics, hist, resources,
path_endpoints, log_summary) as stored by meta.json / the evaluations table; sigma values are the noise_floor
rows (relative, wns relative to the clock period)."""
import json

METRICS = ("area", "wns", "power")


def relative_gains(base, cand, clock_ns):
    """Gain vector (positive = better) relative to the baseline: area and power relative, wns in clock periods."""
    bm, cm = base.get("metrics") or base, cand.get("metrics") or cand
    g = {}
    ba, ca = bm.get("area", bm.get("area_um2")), cm.get("area", cm.get("area_um2"))
    if ba and ca is not None:
        g["area"] = (float(ba) - float(ca)) / float(ba)
    bw, cw = bm.get("wns_ns"), cm.get("wns_ns")
    if bw is not None and cw is not None and clock_ns:
        g["wns"] = (float(cw) - float(bw)) / float(clock_ns)
    bp, cp = bm.get("power_saif_mw") or bm.get("power_default_mw"), cm.get("power_saif_mw") or cm.get("power_default_mw")
    if bp and cp is not None:
        g["power"] = (float(bp) - float(cp)) / float(bp)
    return g


def weighted_jaccard(h1, h2):
    keys = set(h1 or {}) | set(h2 or {})
    if not keys:
        return 1.0
    num = sum(min(float((h1 or {}).get(k, 0)), float((h2 or {}).get(k, 0))) for k in keys)
    den = sum(max(float((h1 or {}).get(k, 0)), float((h2 or {}).get(k, 0))) for k in keys)
    return num / den if den else 1.0


def endpoints_coincide(base, cand, top_n=3):
    """The most critical endpoints (register / port names) of both records agree, when both records carry them."""
    b = [e[1] for e in (base.get("path_endpoints") or [])[:top_n]]
    c = [e[1] for e in (cand.get("path_endpoints") or [])[:top_n]]
    if not b or not c:
        return None
    return bool(set(b) & set(c))


def converged(base, cand, sigma_area, jaccard_min):
    """Fingerprint convergence (§B.1): histogram Jaccard >= threshold, area delta within 1 sigma, endpoints coincide."""
    jac = weighted_jaccard(base.get("hist"), cand.get("hist"))
    g = relative_gains(base, cand, None)
    within = abs(g.get("area", 0.0)) <= float(sigma_area or 0.0) if "area" in g else True
    ends = endpoints_coincide(base, cand)
    ok = jac >= float(jaccard_min) and within and (ends is not False)
    return ok, {"fp_jaccard": round(jac, 4), "area_within_sigma": within, "endpoints_coincide": ends}


def resource_diff(base, cand):
    rb, rc = base.get("resources") or {}, cand.get("resources") or {}
    missing = sorted(set(rb.get("dw_modules") or []) - set(rc.get("dw_modules") or []))
    return {"missing_resources": missing,
            "datapath_blocks": [rb.get("datapath_blocks"), rc.get("datapath_blocks")],
            "shared_resources": [rb.get("shared_resources"), rc.get("shared_resources")]}


def log_diff(base, cand):
    cb, cc = ((base.get("log_summary") or {}).get("counts") or {}), ((cand.get("log_summary") or {}).get("counts") or {})
    keys = sorted(set(cb) | set(cc))
    return {k: [cb.get(k), cc.get(k)] for k in keys if cb.get(k) != cc.get(k)}


def identical_fingerprint(a, b):
    """The two records synthesised to the same netlist for our purposes: equal cell histogram, area and cell count."""
    ma, mb = a.get("metrics") or a, b.get("metrics") or b
    area_a, area_b = ma.get("area", ma.get("area_um2")), mb.get("area", mb.get("area_um2"))
    cells_a, cells_b = ma.get("cells", ma.get("leaf_cells")), mb.get("cells", mb.get("leaf_cells"))
    if area_a is None or area_b is None or abs(float(area_a) - float(area_b)) > 1e-6:
        return False
    if cells_a is not None and cells_b is not None and cells_a != cells_b:
        return False
    return (a.get("hist") or {}) == (b.get("hist") or {})


def diagnose(base, cand, sigma, clock_ns, *, v3_status="proven", k_sigma=2.0, fp_jaccard=0.95, lower_rungs=None, prior=None,
             thresholds=None, floor_class=None, run_fingerprints=None, envelope=None):
    """sigma: {metric: sigma_robust} for the E4 floor of this design (area, wns, power, all relative); thresholds: the
    rule-A t_D per metric (DECISIONS 2026-09-14; when given it replaces k_sigma * sigma as the band).
    lower_rungs: {rung: (base_rec, cand_rec, sigma_area)} for E_s / E2 / E3 / single-flag runs, lowest first; every
    comparison is made between the candidate and D under that same rung, never against a higher rung (G1.4).
    run_fingerprints: {cand_id: record} of the earlier E4-evaluated candidates of the run (duplicate detection).
    floor_class / envelope: on a spread or offset design a retained candidate must beat the envelope of its own surface
    perturbations at E4 (list of gain dicts, C2.1(d)); otherwise the label is fragile.
    -> dict(label, rung, capability, attribution, sublabel, offset_design, duplicate_of, evidence)"""
    out = {"label": None, "rung": None, "capability": None, "attribution": None, "sublabel": None,
           "offset_design": floor_class == "offset", "duplicate_of": None}
    if v3_status != "proven":
        out.update(label="nonequiv", evidence={"v3_status": v3_status})
        return out
    g = relative_gains(base, cand, clock_ns)
    band = {m: (float(thresholds[m]) if thresholds and thresholds.get(m) is not None else float(k_sigma) * float(sigma.get(m) or 0.0)) for m in g}
    up = [m for m in g if g[m] > band[m]]
    down = [m for m in g if g[m] < -band[m]]
    conv, fp = converged(base, cand, sigma.get("area"), fp_jaccard)
    rd, ld = resource_diff(base, cand), log_diff(base, cand)
    mb, mc = base.get("metrics") or {}, cand.get("metrics") or {}
    extra_regs = (mc.get("registers") or 0) - (mb.get("registers") or 0)
    evidence = {"gains": {m: round(v, 5) for m, v in g.items()}, "band": {m: round(v, 5) for m, v in band.items()}, **fp,
                "log_diff": ld, "missing_resources": rd["missing_resources"], "extra_regs": extra_regs,
                "icg": [mb.get("icg_count"), mc.get("icg_count")], "floor_class": floor_class}
    out["evidence"] = evidence
    if identical_fingerprint(base, cand):
        out.update(label="absorbed_identical", rung="E4", attribution="identical")
        return out
    for cid, rec in (run_fingerprints or {}).items():
        if identical_fingerprint(rec, cand):
            out.update(label="duplicate", duplicate_of=cid)
            return out
    if up and not down:
        out.update(label="retained", rung="E4")
        if floor_class in ("spread", "offset"):
            if envelope is None:
                out["envelope_required"] = True  # the search runs the candidate's own perturbations before accepting
            else:
                env_max = {m: max((e.get(m, 0.0) for e in envelope), default=0.0) for m in up}
                evidence["envelope_max"] = {m: round(v, 5) for m, v in env_max.items()}
                if any(g[m] <= env_max[m] for m in up):
                    out.update(label="fragile", sublabel="gain inside the candidate's own perturbation envelope")
    elif conv:
        rung, capability, attribution = "after_Es", None, "prior"
        for r, (b_r, c_r, s_r) in (lower_rungs or {}).items():
            ok, _ = converged(b_r, c_r, s_r, fp_jaccard)
            if ok:
                rung, attribution = r, "measured"
                capability = (prior or {}).get("capability_of_rung", {}).get(r)
                break
        out.update(label="absorbed", rung=rung, capability=capability or (prior or {}).get("capability"), attribution=attribution)
    elif not up and not down:
        out.update(label="noise")
    elif down and not up:
        out.update(label="harmful", sublabel="blocks_synthesis" if rd["missing_resources"] or
                   (rd["datapath_blocks"][0] or 0) > (rd["datapath_blocks"][1] or 0) else None)
    else:
        out.update(label="tradeoff", sublabel=f"up={','.join(up)} down={','.join(down)}")
    return out


def feedback_block(diag, cls, subtags, prior=None):
    """§B.3: evidence only; suggestions come from the prior table."""
    ev = diag.get("evidence") or {}
    g = ev.get("gains") or {}
    return {"class": cls, "subtags": list(subtags or []), "diagnosis": diag["label"], "rung": diag.get("rung"),
            "capability": diag.get("capability"), "attribution": diag.get("attribution"),
            "evidence": {"dA_pct": round(-100 * g.get("area", 0.0), 2), "dWNS_T": round(g.get("wns", 0.0), 4),
                         "dP_pct": round(-100 * g.get("power", 0.0), 2) if "power" in g else None,
                         "sigma2_pct": round(100 * (ev.get("band") or {}).get("area", 0.0), 2),
                         "fp_jaccard": ev.get("fp_jaccard"), "log_diff": ev.get("log_diff"),
                         "missing_resources": ev.get("missing_resources"), "extra_regs": ev.get("extra_regs")},
            "prior": prior or {}}


def screened_out_block(rung, fp_converged):
    return {"diagnosis": "screened_out", "rung": rung, "fp_converged": bool(fp_converged)}


def credit(diag, pareto_improves_parent):
    """§B.4: the class bandit is credited only for retained, or tradeoff with a Pareto improvement over the parent; the
    credit goes to the produced class (the caller passes class_final), never to fragile / duplicate / absorbed_identical."""
    return 1 if diag["label"] == "retained" or (diag["label"] == "tradeoff" and pareto_improves_parent) else 0


def to_json(diag):
    return json.dumps(diag, sort_keys=True, default=str)
