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
