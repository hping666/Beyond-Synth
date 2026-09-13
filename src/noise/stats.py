"""Noise-floor statistics (docs/spec/02-noise-floor.md §4): relative deviations of the proven perturbations from
the baseline, the robust standard deviation 1.4826 x MAD, the plain standard deviation, q95 and max of |delta|,
and the `noise_floor` rows (one per design, configuration and metric)."""
import math
import statistics

from src.db import core as db

METRICS = ("area", "wns", "tns", "power_saif")
COLUMNS = {"area": "area_um2", "wns": "wns_ns", "tns": "tns_ns", "power_saif": "power_saif_mw"}
MAD_TO_SIGMA = 1.4826


def deviations(metric, base, values, clock_ns=None):
    """delta_i = (m_i - m_D) / m_D; for wns (and tns) the denominator is the clock period (spec 02 §4)."""
    out = []
    for v in values:
        if v is None or base is None:
            continue
        if metric in ("wns", "tns"):
            if not clock_ns:
                continue
            out.append((float(v) - float(base)) / float(clock_ns))
        else:
            if float(base) == 0:
                continue
            out.append((float(v) - float(base)) / float(base))
    return out


def mad(xs):
    if not xs:
        return None
    med = statistics.median(xs)
    return statistics.median([abs(x - med) for x in xs])


def quantile(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def summarize(deltas):
    """-> dict(sigma_robust, sigma_std, q95_abs, max_abs, n) or None when fewer than 2 deviations exist."""
    if len(deltas) < 2:
        return None
    absd = [abs(x) for x in deltas]
    return {"sigma_robust": MAD_TO_SIGMA * mad(deltas), "sigma_std": statistics.pstdev(deltas),
            "q95_abs": quantile(absd, 0.95), "max_abs": max(absd), "n": len(deltas)}


GAIN_SIGN = {"area": -1.0, "power_saif": -1.0, "wns": 1.0, "tns": 1.0}  # gain g = sign * delta (lower area / power, higher slack)


def conclusion(deltas, sigmas, k):
    """Four-way conclusion of one candidate (or perturbation) against the floor (PROPOSAL §C1, spec 02 §4):
    deltas / sigmas: {metric: value}; metrics without both are ignored. 'retained' = some gain > k*sigma and none
    < -k*sigma; 'trade-off' = some > and some <; 'harmful' = some < and none >; 'noise' otherwise; None when no metric
    can be judged."""
    up = down = judged = 0
    for m, d in deltas.items():
        s = sigmas.get(m)
        if d is None or s is None:
            continue
        judged += 1
        g = GAIN_SIGN.get(m, -1.0) * float(d)
        thr = float(k) * float(s)
        if g > thr:
            up += 1
        elif g < -thr:
            down += 1
    if not judged:
        return None
    if up and not down:
        return "retained"
    if up and down:
        return "trade-off"
    if down:
        return "harmful"
    return "noise"


def pick_records(conn, design_id, config, proven, clock_ns=None, eps=1e-6):
    """The baseline record and the {pert_id: record} of the proven perturbations to compute sigma_D from: status ok,
    at clock_ns when given; a record with SAIF power (power_saif_mw not null) is preferred over one without, the
    latest among equals (the noise runs were first submitted without SAIF, spec 02 §4 needs power_saif)."""
    clk = "" if clock_ns is None else " AND abs(clock_ns-?)<?"
    args = () if clock_ns is None else (float(clock_ns), eps)
    base = conn.execute("SELECT * FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL "
                        f"AND status='ok'{clk} ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (design_id, config, *args)).fetchone()
    latest = {}
    for x in conn.execute("SELECT * FROM evaluations WHERE design_id=? AND config=? AND pert_id IS NOT NULL AND status='ok'"
                          f"{clk} ORDER BY (power_saif_mw IS NOT NULL), eval_id", (design_id, config, *args)):
        if x["pert_id"] in proven:
            latest[x["pert_id"]] = dict(x)  # the last row wins: SAIF-backed, then latest
    return (dict(base) if base is not None else None), latest


def floor_rows(design_id, config, baseline, pert_records, clock_ns):
    """baseline / pert_records: dicts with the evaluations columns; -> [noise_floor row dicts]."""
    rows = []
    for metric, col in COLUMNS.items():
        base = baseline.get(col)
        vals = [r.get(col) for r in pert_records]
        s = summarize(deviations(metric, base, vals, clock_ns))
        if s is None:
            continue
        unit = None
        if metric == "area" and baseline.get("cells"):
            unit = s["sigma_robust"] * float(baseline["cells"])  # absolute threshold in cells for small designs
        rows.append({"design_id": design_id, "config": config, "metric": metric, **s, "abs_unit_value": unit})
    return rows


def upsert_floor(conn, rows):
    for row in rows:
        row = dict(row)
        row.update(db.stamp())
        cols = list(row)
        conn.execute(f"INSERT INTO noise_floor ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)}) "
                     f"ON CONFLICT(design_id, config, metric, cfg_hash) DO UPDATE SET sigma_robust=excluded.sigma_robust, "
                     f"sigma_std=excluded.sigma_std, q95_abs=excluded.q95_abs, max_abs=excluded.max_abs, n=excluded.n, "
                     f"abs_unit_value=excluded.abs_unit_value, git_sha=excluded.git_sha, created_at=excluded.created_at", tuple(row.values()))
    return len(rows)


# ----------------------------------------------------------------------------- G1 analysis helpers (report)
def proven_by_design(conn):
    out = {}
    for r in conn.execute("SELECT design_id, pert_id FROM perturbations WHERE seq_status IN ('proven', 'proven_rename')"):
        out.setdefault(r["design_id"], set()).add(r["pert_id"])
    return out


def floor_analysis(conn, designs, configs, proven, k, eps=1e-6):
    """designs: [{design_id, phi}] -> per (config, metric): designs with a floor (n >= 2), how many have a zero robust /
    plain sigma, the pooled quantiles of |delta| over every perturbation record, and the distribution of the proposed
    threshold t_D = max(k * sigma_robust, max|delta|_D, pooled q95) with the number of designs above the pooled minimum."""
    pooled, per_design = {}, {}
    for d in designs:
        did, phi = d["design_id"], d["phi"]
        for config in configs:
            base, latest = pick_records(conn, did, config, proven.get(did, set()), phi, eps)
            if base is None or not latest:
                continue
            for m in METRICS:
                col = COLUMNS[m]
                dl = deviations(m, base.get(col), [x.get(col) for x in latest.values()], phi)
                if not dl:
                    continue
                pooled.setdefault((config, m), []).extend(abs(x) for x in dl)
                s = summarize(dl)
                if s:
                    per_design[(config, m, did)] = (s["sigma_robust"], s["sigma_std"], s["max_abs"])
    out = {}
    for (config, m), v in pooled.items():
        q95 = quantile(v, 0.95)
        rows = [(sr, ss, mx) for (c, mm, _), (sr, ss, mx) in per_design.items() if c == config and mm == m]
        ts = sorted(max(k * sr, mx, q95) for sr, ss, mx in rows)
        out[(config, m)] = {"records": len(v), "frac_zero": sum(1 for x in v if x == 0) / len(v),
                            "pooled": {"q90": quantile(v, 0.90), "q95": q95, "q99": quantile(v, 0.99), "max": max(v)},
                            "designs": len(rows), "zero_robust": sum(1 for sr, _, _ in rows if sr == 0), "zero_std": sum(1 for _, ss, _ in rows if ss == 0),
                            "max_abs_gt": {"1pct": sum(1 for _, _, mx in rows if mx > 0.01), "5pct": sum(1 for _, _, mx in rows if mx > 0.05)},
                            "t_proposed": ({"median": quantile(ts, 0.5), "q75": quantile(ts, 0.75), "q95": quantile(ts, 0.95), "max": ts[-1],
                                            "above_pooled_min": sum(1 for x in ts if x > q95 + 1e-12)} if ts else None)}
    return out


def ptype_change_rates(conn, designs, configs, proven, eps=1e-6):
    """-> per (config, ptype): records and how many changed the area or the cell count of D (the netlist is not identical)."""
    ptype_of = {r["pert_id"]: r["ptype"] for r in conn.execute("SELECT pert_id, ptype FROM perturbations")}
    out = {}
    for d in designs:
        did, phi = d["design_id"], d["phi"]
        for config in configs:
            base, latest = pick_records(conn, did, config, proven.get(did, set()), phi, eps)
            if base is None:
                continue
            for pid, rec in latest.items():
                e = out.setdefault((config, ptype_of.get(pid, "?")), {"n": 0, "changed": 0})
                e["n"] += 1
                if rec.get("area_um2") is None or base.get("area_um2") is None:
                    continue
                if abs(float(rec["area_um2"]) - float(base["area_um2"])) > 1e-6 or rec.get("cells") != base.get("cells"):
                    e["changed"] += 1
    return out


def monotonicity(conn, designs, configs, eps=1e-6):
    """Baseline D across the rungs in `configs` order: per consecutive step (and first -> last) how many designs gain area
    or lose WNS; -> {'n': designs with every rung, 'steps': {(a, b): {'area_up': .., 'wns_down': ..}}}."""
    steps = list(zip(configs, configs[1:])) + ([(configs[0], configs[-1])] if len(configs) > 2 else [])
    res = {s: {"area_up": 0, "wns_down": 0} for s in steps}
    n = 0
    for d in designs:
        v = {}
        for c in configs:
            b, _ = pick_records(conn, d["design_id"], c, set(), d["phi"], eps)
            if b:
                v[c] = b
        if len(v) < len(configs):
            continue
        n += 1
        for a, b in steps:
            if v[b].get("area_um2") is not None and v[a].get("area_um2") is not None and float(v[b]["area_um2"]) > float(v[a]["area_um2"]) * (1 + 1e-4):
                res[(a, b)]["area_up"] += 1
            if (v[b].get("wns_ns") or 0) < (v[a].get("wns_ns") or 0) - 1e-6:
                res[(a, b)]["wns_down"] += 1
    return {"n": n, "steps": res}
