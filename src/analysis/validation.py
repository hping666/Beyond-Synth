"""PLAN 4.6 / 4.9 helpers (docs/spec/04-classifier-diagnoser.md §B.5): the deterministic stratified sample of diagnoses
for the manual diagnoser check (`exp1.manual_check_per_class` per label, round-robin over designs, seeded), the
single-flag reproduction of `absorbed` objects (D compiled with one transformation alone — the configurations declaring
`single_flag`: E1d designware, E2g gate_clock, E2r retime as an alias of E3 — against the object's plain-compile netlist
C@E1, with the design's rule-A E1 band as the area tolerance), and the choice of the two objects of the motivating figure
(the largest E1 gain the ladder recovers, the largest E4 gain that survives). Pure functions over rows, plus readers of the
visible database only (rule 3)."""
import random

from src.analysis import objects as O
from src.diagnose import m3
from src.search.driver import record_from_row

RECOVERED_LABELS = ("absorbed", "absorbed_identical", "noise")
FIGURE_CONFIGS = ("E1", "E1d", "E2", "E3", "E2g", "E4", "Y", "O0", "O1", "O2")


def single_flag_rungs(cfg):
    """{flag: config} from the configurations declaring `single_flag`; an alias (E2r -> E3) maps its flag to the target."""
    out = {}
    configs = {k: v for k, v in (cfg.get("configs") or {}).items() if isinstance(v, dict)}
    for name, c in configs.items():
        if c.get("single_flag") and not c.get("alias_of"):
            out[c["single_flag"]] = name
    for name, c in configs.items():
        if c.get("single_flag") and c.get("alias_of"):
            out.setdefault(c["single_flag"], c["alias_of"])
    return out


def stratified_sample(rows, n, seed, key="design_id"):
    """Up to n rows: round-robin over the strata (sorted by `key`), a seeded shuffle inside each stratum -> deterministic
    for a given seed, every stratum represented before any stratum gets a second row."""
    rnd = random.Random(int(seed))
    strata = {}
    for r in sorted(rows, key=lambda r: (str(r.get(key)), str(r.get("cand_id")))):
        strata.setdefault(str(r.get(key)), []).append(r)
    keys = sorted(strata)
    for k in keys:
        rnd.shuffle(strata[k])
    out = []
    while len(out) < n and any(strata[k] for k in keys):
        for k in keys:
            if strata[k] and len(out) < n:
                out.append(strata[k].pop())
    return out


def single_flag_reproduction(cfg, conn, cand_id, design_id, phi):
    """spec 04 §B.5: does D under one flag alone converge (m3.converged: histogram Jaccard >= diag.fp_jaccard, area within
    the E1 rule-A band of the design, critical endpoints coincide) with the object's plain-compile netlist C@E1?
    -> {flag: {converged, fp_jaccard, area_within_sigma, endpoints_coincide, config} | None (no baseline)}, plus "none"
    for D@E1 itself (already converged with a plain compile: the rewrite changes nothing the tool sees); None without C@E1."""
    c_e1 = O.object_row_eval(conn, cand_id, "E1", phi)
    if c_e1 is None:
        return None
    cand = record_from_row(c_e1)
    t_d, fl = O.thresholds(conn, design_id, "E1", cfg["noise"].get("floor_version"))
    band = t_d.get("area")
    if band is None:
        band = float((fl.get("area") or {}).get("sigma_robust") or 0.0)
    jac = float(cfg["diag"]["fp_jaccard"])
    out = {}
    for flag, config in sorted(single_flag_rungs(cfg).items()):
        b = O.baseline_row(conn, design_id, config, phi)
        if b is None:
            out[flag] = None
            continue
        ok, ev = m3.converged(record_from_row(b), cand, band, jac)
        out[flag] = {"converged": bool(ok), "config": config, **ev}
    b1 = O.baseline_row(conn, design_id, "E1", phi)
    if b1 is not None:
        ok, ev = m3.converged(record_from_row(b1), cand, band, jac)
        out["none"] = {"converged": bool(ok), "config": "E1", **ev}
    return out


def reproduction_summary(rows):
    """rows: [{cand_id, design_id, label, rung, repro: {flag: {...}|None}}] -> counts per flag (evaluated / converged) and
    the number of absorbed objects reproduced by at least one single flag."""
    by_flag, any_flag = {}, 0
    for r in rows:
        hit = False
        for flag, v in (r.get("repro") or {}).items():
            if v is None:
                continue
            e = by_flag.setdefault(flag, {"config": v.get("config"), "evaluated": 0, "converged": 0})
            e["evaluated"] += 1
            e["converged"] += int(bool(v.get("converged")))
            hit = hit or (flag != "none" and bool(v.get("converged")))
        any_flag += int(hit)
    for e in by_flag.values():
        e["rate"] = (e["converged"] / e["evaluated"]) if e["evaluated"] else None
    return {"n": len(rows), "by_flag": dict(sorted(by_flag.items())), "reproduced_by_a_single_flag": any_flag,
            "rate_any_flag": (any_flag / len(rows)) if rows else None}


def pick_motivating(objs, metric="area"):
    """The two objects of the motivating figure: the largest E1 gain among objects the ladder recovers (absorbed /
    absorbed_identical / noise at E4) and the largest E4 gain among the retained ones; None when no candidate exists."""
    def g(o, c):
        return ((o.get("gains") or {}).get(c) or {}).get(metric)
    rec = [o for o in objs if o.get("label") in RECOVERED_LABELS and g(o, "E1") is not None and g(o, "E4") is not None]
    ret = [o for o in objs if o.get("label") == "retained" and g(o, "E1") is not None and g(o, "E4") is not None]
    return {"recovered": max(rec, key=lambda o: g(o, "E1"), default=None), "retained": max(ret, key=lambda o: g(o, "E4"), default=None)}


def motivating_md(picks, configs=FIGURE_CONFIGS):
    """Markdown block of the figure (included by reports/phase4.md): the relative gains of both objects along the ladder."""
    L = ["## 10. Motivating figure (PLAN 4.9): the same rewrite along the ladder", "",
         "Two Phase 4 objects chosen by the data: the largest plain-compile (E1) gain that the full-effort flow recovers on its own, and the largest gain that survives E4 (retained). "
         "Positive = better than D under that configuration (relative); t_D is the rule-A threshold of the design at E4.", "",
         "| object | design | class | E4 label / rung | " + " | ".join(f"{c} area / wns / power" for c in configs) + " | t_D(E4) area |",
         "|---|---|---|---|" + "---|" * (len(configs) + 1)]
    for kind in ("recovered", "retained"):
        o = picks.get(kind)
        if not o:
            L.append(f"| {kind}: none | - | - | - | " + " | ".join("-" for _ in configs) + " | - |")
            continue
        cells = []
        for c in configs:
            gg = (o.get("gains") or {}).get(c)
            cells.append("-" if not gg else " / ".join("-" if gg.get(m) is None else f"{100 * gg[m]:+.1f} %" for m in ("area", "wns", "power")))
        t = ((o.get("t_d") or {}).get("E4") or {}).get("area")
        L.append(f"| {kind}: {o['cand_id']} | {o['design_id']} | {o.get('cls') or '?'} | {o.get('label')} / {o.get('rung') or '-'} | " + " | ".join(cells) + f" | {'-' if t is None else f'{100 * t:.2f} %'} |")
    L += ["", "The recovered object shows the gain a plain compile reports vanishing under `compile_ultra -retime -gate_clock` (the synthesizer obtains it on its own); "
          "the retained object keeps its gain there — the complement the ladder search aims at (PROPOSAL §1)."]
    return "\n".join(L) + "\n"
