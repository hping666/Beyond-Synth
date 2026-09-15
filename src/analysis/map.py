"""Map v1 (docs/spec/08-analysis.md §1, PLAN 4.4): pure functions over object rows — cells class × configuration
(retention rate against that configuration's rule-A threshold, retained magnitude, absorption rung and attribution
distributions), retention curves from E1 to E4, non-monotone cases, the literature re-evaluation table (PLAN 4.7)
and the static-rule misclassification rates (PLAN 4.8). Readers of the results database build the object rows
(scripts/phase4_exp1.py collect); nothing here touches the hidden database (rule 3): hidden columns are appended by
scripts/report_hidden.py after Phase 5.

Object row: {"cand_id", "design_id", "cls" (M6 class a/b/c1/c2/d or None), "subtags": [...], "role" (b0 | reference | llm),
             "label" (M3 label at E4 or None), "rung", "attribution",
             "gains": {config: {"area": g, "wns": g, "power": g}}      # relative gains vs D under that configuration (positive = better)
             "t_d": {config: {"area": t, "wns": t, "power": t}}}       # rule-A thresholds of D under that configuration (missing -> None)
"""
import math

CLASSES = ("a", "b", "c1", "c2", "d")
METRICS = ("area", "wns", "power")
LADDER = ("E1", "E1d", "E2", "E3", "E2g", "E4")
RETAINED_LABELS = ("retained", "tradeoff")
ABSORBED_LABELS = ("absorbed", "absorbed_identical", "noise", "duplicate")
FORBIDDEN_BY_RULE_R = ("a", "b")     # "no syntactic / coding optimizations": classes (a) and (b) are what the rule forbids
ALLOWED_BY_RULE_R = ("c1", "c2", "d")


def quantile(xs, q):
    xs = sorted(x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x)))
    if not xs:
        return None
    pos = (len(xs) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def retained_under(obj, config, metric="area"):
    """True / False / None: the object's gain under `config` exceeds D's rule-A threshold for that configuration
    (a strict comparison; None when the object has no record or D has no threshold under that configuration)."""
    g = ((obj.get("gains") or {}).get(config) or {}).get(metric)
    t = ((obj.get("t_d") or {}).get(config) or {}).get(metric)
    if g is None or t is None:
        return None
    return float(g) > float(t)


def cell(objs, cls, config, metric="area"):
    """One map cell: objects of class `cls` with a record under `config`."""
    rows = [o for o in objs if o.get("cls") == cls]
    verdicts = [(o, retained_under(o, config, metric)) for o in rows]
    known = [(o, r) for o, r in verdicts if r is not None]
    retained = [o for o, r in known if r]
    mags = [float(o["gains"][config][metric]) for o in retained]
    out = {"n": len(rows), "n_evaluated": len(known), "n_retained": len(retained),
           "retention_rate": (len(retained) / len(known)) if known else None,
           "magnitude_median": quantile(mags, 0.5), "magnitude_iqr": ((quantile(mags, 0.75) - quantile(mags, 0.25)) if len(mags) >= 2 else None)}
    if config == "E4":
        rungs, attrs = {}, {}
        for o in rows:
            if o.get("label") in ("absorbed", "absorbed_identical"):
                rungs[o.get("rung") or "?"] = rungs.get(o.get("rung") or "?", 0) + 1
                attrs[o.get("attribution") or "?"] = attrs.get(o.get("attribution") or "?", 0) + 1
        out["absorption_rung"] = dict(sorted(rungs.items()))
        out["attribution"] = dict(sorted(attrs.items()))
        labels = {}
        for o in rows:
            labels[o.get("label") or "?"] = labels.get(o.get("label") or "?", 0) + 1
        out["labels"] = dict(sorted(labels.items()))
    return out


def build_map(objs, configs=LADDER, metric="area"):
    return {cls: {config: cell(objs, cls, config, metric) for config in configs} for cls in CLASSES}


def retention_curves(objs, configs=LADDER, metric="area"):
    """{class: [(config, retention_rate, n_evaluated)]} along the ladder order."""
    return {cls: [(config, cell(objs, cls, config, metric)["retention_rate"], cell(objs, cls, config, metric)["n_evaluated"]) for config in configs] for cls in CLASSES}


def non_monotone(objs, order=("E1", "E2", "E3", "E4"), metric="area"):
    """Objects whose gain re-exceeds the band at a higher rung after having been inside it at a lower rung
    (spec 08 §1: retention is not monotone along the ladder). -> [(cand_id, pattern)] and the fraction among objects
    evaluated under every rung of `order`."""
    cases, n = [], 0
    for o in objs:
        pattern = [retained_under(o, c, metric) for c in order]
        if any(p is None for p in pattern):
            continue
        n += 1
        if any(pattern[i] is False and any(pattern[j] for j in range(i + 1, len(pattern))) for i in range(len(pattern) - 1)):
            cases.append((o["cand_id"], "".join("R" if p else "-" for p in pattern)))
    return {"cases": cases, "n_evaluated_on_all": n, "fraction": (len(cases) / n) if n else None}


def literature_table(objs, configs=LADDER, metric="area"):
    """PLAN 4.7: for the literature pairs (role `reference`, grouped by suite prefix of the design id) the number of pairs
    whose optimized version is better than D under each rung — raw (any positive gain) and retained (above the rule-A
    threshold of that rung)."""
    out = {}
    for o in objs:
        if o.get("role") != "reference":
            continue
        suite = o["design_id"].split("_", 1)[0]
        e = out.setdefault(suite, {"pairs": 0, "proven": 0, "better": {c: 0 for c in configs}, "retained": {c: 0 for c in configs}, "evaluated": {c: 0 for c in configs}})
        e["pairs"] += 1
        if not o.get("proven", True):
            continue
        e["proven"] += 1
        for c in configs:
            g = ((o.get("gains") or {}).get(c) or {}).get(metric)
            if g is None:
                continue
            e["evaluated"][c] += 1
            e["better"][c] += int(float(g) > 0)
            r = retained_under(o, c, metric)
            e["retained"][c] += int(bool(r))
    return out


def misclassification_rates(objs, config="E4", metric="area"):
    """PLAN 4.8: with the static rule R ("no syntactic / coding optimizations, only architectural rewrites": classes (a) and
    (b) forbidden, (c1) / (c2) / (d) allowed), P(retained | forbidden by R) and P(absorbed | allowed by R) at E4, from the
    M3 labels (retained / tradeoff count as retained; absorbed / absorbed_identical / noise / duplicate as absorbed)."""
    forb = [o for o in objs if o.get("cls") in FORBIDDEN_BY_RULE_R and o.get("label")]
    allow = [o for o in objs if o.get("cls") in ALLOWED_BY_RULE_R and o.get("label")]
    p_ret_forb = (sum(1 for o in forb if o["label"] in RETAINED_LABELS) / len(forb)) if forb else None
    p_abs_allow = (sum(1 for o in allow if o["label"] in ABSORBED_LABELS) / len(allow)) if allow else None
    return {"n_forbidden": len(forb), "n_allowed": len(allow), "p_retained_given_forbidden": p_ret_forb, "p_absorbed_given_allowed": p_abs_allow,
            "forbidden_classes": list(FORBIDDEN_BY_RULE_R), "allowed_classes": list(ALLOWED_BY_RULE_R)}


def shape(map_cells, min_n=10):
    """One word for the map (PLAN Phase 4 acceptance): `concentrated` when the E4 retention rate differs by class (max −
    min ≥ 0.3 over classes with ≥ min_n evaluated objects), `near_zero` when every class retains < 10 %, else `diffuse`."""
    rates = {cls: c["E4"]["retention_rate"] for cls, c in map_cells.items() if c.get("E4") and (c["E4"]["n_evaluated"] or 0) >= min_n and c["E4"]["retention_rate"] is not None}
    if not rates:
        return "undetermined", rates
    if max(rates.values()) < 0.10:
        return "near_zero", rates
    if max(rates.values()) - min(rates.values()) >= 0.30:
        return "concentrated", rates
    return "diffuse", rates
