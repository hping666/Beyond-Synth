"""Independent re-derivation of an E4 diagnosis from the raw DC reports (PLAN 4.6 manual diagnoser check): area from
area.rpt (`Total cell area`), slack from qor.rpt (`Critical Path Slack`), leaf cells from qor.rpt, power from the
`Total` line of power_saif.rpt, the critical endpoints from timing.rpt and the cell histogram from the instances of
netlist.v (the database histogram comes from refs.rpt, so the netlist is an independent source). The label follows
spec 04 §B.2 with the same band (rule-A t_D) and convergence rule, re-implemented here without src/diagnose so that an
ingest, baseline or clock mistake shows up as a disagreement. Reads report files only (rule 3: no hidden paths)."""
import re
from pathlib import Path

POWER_UNIT_TO_MW = {"W": 1000.0, "mW": 1.0, "uW": 1e-3, "nW": 1e-6, "pW": 1e-9}
VERILOG_KEYWORDS = {"module", "endmodule", "input", "output", "inout", "wire", "reg", "assign", "always", "initial", "begin", "end", "tri", "supply0", "supply1", "specify"}


def _read(raw_dir, name):
    p = Path(raw_dir or "") / "outputs" / "reports" / name
    return p.read_text(errors="replace") if p.exists() else None


def parse_area(text):
    m = re.search(r"^Total cell area:\s+([-\d.]+)", text or "", re.M)
    return float(m.group(1)) if m else None


def parse_slack(text):
    m = re.search(r"Critical Path Slack:\s+(-?[\d.]+)", text or "")
    return float(m.group(1)) if m else None


def parse_leaf_cells(text):
    m = re.search(r"Leaf Cell Count:\s+(\d+)", text or "")
    return int(m.group(1)) if m else None


def parse_power_mw(text):
    """The last `Total ... <value> <unit>` line of a DC power report -> mW."""
    val = None
    for line in (text or "").splitlines():
        m = re.match(r"^Total\s+.*?([-\d.]+(?:e[-+]?\d+)?)\s*(W|mW|uW|nW|pW)\s*$", line.strip())
        if m:
            val = float(m.group(1)) * POWER_UNIT_TO_MW[m.group(2)]
    return val


def parse_endpoints(text, top_n=3):
    """[(startpoint, endpoint, slack)] of the first `top_n` paths of a timing report."""
    out, start, end = [], None, None
    for line in (text or "").splitlines():
        s = line.strip()
        if s.startswith("Startpoint:"):
            start = s.split(":", 1)[1].split()[0]
        elif s.startswith("Endpoint:"):
            end = s.split(":", 1)[1].split()[0]
        elif s.startswith("slack (") and start and end:
            m = re.search(r"(-?[\d.]+)\s*$", s)
            out.append((start, end, float(m.group(1)) if m else None))
            start = end = None
            if len(out) >= top_n:
                break
    return out


def parse_netlist_hist(text):
    """{cell type: count} from the instance lines of a gate-level netlist (modules defined in the file excluded)."""
    if not text:
        return None
    modules = set(re.findall(r"^\s*module\s+([A-Za-z_]\w*)", text, re.M))
    hist = {}
    for typ, _inst in re.findall(r"^\s*([A-Za-z_]\w*)\s+(\\?[\w$.\[\]]+)\s*\(", text, re.M):
        if typ in modules or typ in VERILOG_KEYWORDS:
            continue
        hist[typ] = hist.get(typ, 0) + 1
    return hist


def record_from_reports(raw_dir):
    """Metrics, histogram and endpoints of one E4 record from its report files; None when the area is unreadable."""
    area = parse_area(_read(raw_dir, "area.rpt"))
    if area is None:
        return None
    qor = _read(raw_dir, "qor.rpt")
    return {"area": area, "cells": parse_leaf_cells(qor), "wns_ns": parse_slack(qor), "power_saif_mw": parse_power_mw(_read(raw_dir, "power_saif.rpt")),
            "power_default_mw": parse_power_mw(_read(raw_dir, "power_default.rpt")),
            "hist": parse_netlist_hist(_read(raw_dir, "netlist.v")) or {}, "endpoints": parse_endpoints(_read(raw_dir, "timing.rpt"))}


def weighted_jaccard(h1, h2):
    keys = set(h1) | set(h2)
    if not keys:
        return 1.0
    num = sum(min(h1.get(k, 0), h2.get(k, 0)) for k in keys)
    den = sum(max(h1.get(k, 0), h2.get(k, 0)) for k in keys)
    return num / den if den else 1.0


def identical(a, b):
    return abs(a["area"] - b["area"]) <= 1e-6 and (a["cells"] is None or b["cells"] is None or a["cells"] == b["cells"]) and a["hist"] == b["hist"]


def independent_diagnosis(d_rec, c_rec, clock_ns, t_d, sigma_area, jaccard_min=0.95, duplicate_rec=None):
    """spec 04 §B.2 re-derived from report-level records (record_from_reports): gains (positive = better), the band
    (t_D per metric; missing -> no verdict on that metric), identical -> absorbed_identical, identical to the earlier
    candidate -> duplicate, up-only -> retained, converged -> absorbed, inside the band -> noise, down-only -> harmful,
    else tradeoff. -> {label, gains, jaccard, endpoints_coincide, area_within_sigma, up, down}"""
    g = {}
    if d_rec["area"]:
        g["area"] = (d_rec["area"] - c_rec["area"]) / d_rec["area"]
    if d_rec["wns_ns"] is not None and c_rec["wns_ns"] is not None and clock_ns:
        g["wns"] = (c_rec["wns_ns"] - d_rec["wns_ns"]) / float(clock_ns)
    basis = "saif" if d_rec.get("power_saif_mw") is not None and c_rec.get("power_saif_mw") is not None else ("default" if d_rec.get("power_default_mw") is not None and c_rec.get("power_default_mw") is not None else None)
    if basis:   # the same basis on both sides, as m3.power_basis (a SAIF figure is never compared with a default-activity one)
        bp, cp = d_rec[f"power_{basis}_mw"], c_rec[f"power_{basis}_mw"]
        if bp:
            g["power"] = (bp - cp) / bp
    band = {m: (float(t_d[m]) if (t_d or {}).get(m) is not None else None) for m in g}
    up = [m for m in g if band[m] is not None and g[m] > band[m]]
    down = [m for m in g if band[m] is not None and g[m] < -band[m]]
    jac = weighted_jaccard(d_rec["hist"], c_rec["hist"])
    ends_d = [e[1] for e in d_rec["endpoints"][:3]]
    ends_c = [e[1] for e in c_rec["endpoints"][:3]]
    ends = (bool(set(ends_d) & set(ends_c))) if ends_d and ends_c else None
    within = abs(g.get("area", 0.0)) <= float(band.get("area") if band.get("area") is not None else (sigma_area or 0.0))   # the rule-A band, as m3 since 2026-09-15
    conv = jac >= float(jaccard_min) and within and ends is not False
    out = {"gains": {m: round(v, 5) for m, v in g.items()}, "band": band, "power_basis": basis, "jaccard": round(jac, 4), "endpoints_coincide": ends, "area_within_sigma": within, "up": up, "down": down}
    if identical(d_rec, c_rec):
        out["label"] = "absorbed_identical"
    elif duplicate_rec is not None and identical(duplicate_rec, c_rec):
        out["label"] = "duplicate"
    elif up and not down:
        out["label"] = "retained"
    elif conv:
        out["label"] = "absorbed"
    elif not up and not down:
        out["label"] = "noise"
    elif down and not up:
        out["label"] = "harmful"
    else:
        out["label"] = "tradeoff"
    return out
