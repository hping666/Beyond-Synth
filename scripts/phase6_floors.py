#!/usr/bin/env python3
"""PLAN 6.9 / REQUEST 2026-09-20 (e) item 3: measured noise floors (floor_version phase6) for the pooled-floor designs of the frozen
phase4 table from their SEQ-proven perturbations at Φ_main under E4 — the text-level renames and reorders (P1_text / P2_text, no
Pyverilog dependency) and any other proven perturbation of the design, P0 included when proven but never required (harness note:
the floor computation is not conditional on a proven round trip). Rule A as in Phase 2 (src/noise/stats.floor_rows): t_D =
max(k_σ · σ_robust, max |δ| of the design's own proven perturbations, the frozen pooled minimum of the phase4 table). The baseline
for power is D's SAIF-basis offline record (evaluations.offline_baseline = 1, item 2) when it exists, else the search baseline
(then no SAIF power floor). Writes only new noise_floor rows under floor_version phase6 (append-only); the phase4 rows are untouched.

  python3 scripts/phase6_floors.py [--designs ID ...] [--dry-run] [--min-perturbations 2]
"""
import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.analysis import phase5 as P5  # noqa: E402
from src.noise import stats as S  # noqa: E402

FLOOR_VERSION = "phase6"
EPS = 1e-6


def frozen_pooled_min(conn, fv, config="E4"):
    """The pooled minima of the frozen table (one value per metric, the same on every design)."""
    out = {}
    for r in conn.execute("SELECT metric, MAX(pooled_min) AS v FROM noise_floor WHERE floor_version=? AND config=? AND pooled_min IS NOT NULL GROUP BY metric", (fv, config)):
        out[r["metric"]] = float(r["v"])
    return out


def baseline_for(conn, design_id, phi):
    """D's E4 record at Φ_main: the offline SAIF-basis baseline when it exists (item 2), else the evaluators' baseline."""
    off = conn.execute("SELECT * FROM evaluations WHERE design_id=? AND config='E4' AND offline_baseline=1 AND is_baseline=0 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' "
                       "AND power_saif_mw IS NOT NULL AND abs(clock_ns-?)<? ORDER BY eval_id DESC LIMIT 1", (design_id, phi, EPS)).fetchone()
    if off is not None:
        return dict(off), "offline_saif"
    base = conn.execute("SELECT * FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' AND abs(clock_ns-?)<? "
                        "ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (design_id, phi, EPS)).fetchone()
    return (dict(base) if base is not None else None), "search"


def compute(cfg, conn, designs=None, min_perts=2, dry_run=False):
    nz = cfg["noise"]
    fv = nz.get("floor_version")
    k, quiet = float(nz["k_sigma"]), float(nz.get("quiet_max_abs", 0.001))
    pooled = frozen_pooled_min(conn, fv)
    report = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "floor_version": FLOOR_VERSION, "frozen_table": fv, "pooled_min_frozen": pooled, "k_sigma": k, "designs": {}}
    for did in (designs or P5.pooled_floor_designs(cfg, conn)):
        row = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (did,)).fetchone()
        phi = float(row[0]) if row and row[0] is not None else None
        entry = {"phi": phi, "rows": 0, "floor_source": None}
        if phi is None:
            entry["reason"] = "no Φ_main"
            report["designs"][did] = entry
            continue
        proven = {r[0]: r[1] for r in conn.execute("SELECT pert_id, ptype FROM perturbations WHERE design_id=? AND seq_status IN ('proven','proven_rename')", (did,))}
        base, basis = baseline_for(conn, did, phi)
        _b, latest = S.pick_records(conn, did, "E4", set(proven), phi, EPS)
        entry.update(proven=len(proven), proven_by_type={t: sum(1 for x in proven.values() if x == t) for t in sorted(set(proven.values()))}, records=len(latest),
                     records_by_type={t: sum(1 for pid in latest if proven.get(pid) == t) for t in sorted(set(proven.values()))}, baseline_basis=basis,
                     p0_status=(conn.execute("SELECT seq_status FROM perturbations WHERE design_id=? AND ptype='P0_roundtrip'", (did,)).fetchone() or [None])[0])
        if base is None or len(latest) < int(min_perts):
            entry["reason"] = "no baseline" if base is None else f"{len(latest)} proven perturbation record(s) at E4 / Φ_main, {min_perts} needed"
            report["designs"][did] = entry
            continue
        rows = S.floor_rows(did, "E4", base, list(latest.values()), phi, pooled, k, quiet)
        entry.update(rows=len(rows), floor_source="measured", floor_class=(rows[0]["floor_class"] if rows else None),
                     t_d={r["metric"]: r["t_d"] for r in rows}, sigma={r["metric"]: r["sigma_robust"] for r in rows}, max_abs={r["metric"]: r["max_abs"] for r in rows})
        frozen = S.latest_floor(conn, did, "E4", fv)
        entry["frozen_t_d"] = {m: (frozen.get(m) or {}).get("t_d") for m in ("area", "power_saif", "wns")}
        if not dry_run and rows:
            S.upsert_floor(conn, rows, FLOOR_VERSION)
            conn.commit()
        report["designs"][did] = entry
    return report


def render(rep):
    L = [f"# Phase 6 floors (PLAN 6.9; REQUEST 2026-09-20 (e) item 3) — floor_version {rep['floor_version']}", "",
         f"Generated {rep['generated_at']}; rule A with k_σ {rep['k_sigma']} and the frozen pooled minima of the {rep['frozen_table']} table "
         f"(area {rep['pooled_min_frozen'].get('area')}, power {rep['pooled_min_frozen'].get('power_saif')}, WNS {rep['pooled_min_frozen'].get('wns')}); the round trip P0 is used when proven, never required. "
         "Baseline: D's SAIF-basis offline E4 record where it exists (item 2), else the search baseline. Rows written under floor_version phase6 only; the phase4 table is unchanged.", "",
         "| design | proven perturbations (by type) | E4 records | P0 | baseline | class | t_D area | t_D power | t_D WNS | frozen phase4 t_D area / power / WNS | note |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    pct = lambda x: "—" if x is None else f"{100 * float(x):.3f} %"
    for d, e in rep["designs"].items():
        td, fz = e.get("t_d") or {}, e.get("frozen_t_d") or {}
        L.append(f"| {d} | {e.get('proven', 0)} ({', '.join(f'{t} {n}' for t, n in (e.get('proven_by_type') or {}).items())}) | {e.get('records', 0)} | {e.get('p0_status')} | {e.get('baseline_basis')} | {e.get('floor_class') or '—'} | "
                 f"{pct(td.get('area'))} | {pct(td.get('power_saif'))} | {pct(td.get('wns'))} | {pct(fz.get('area'))} / {pct(fz.get('power_saif'))} / {pct(fz.get('wns'))} | {e.get('reason') or ('measured' if e.get('rows') else '')} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--designs", nargs="*", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-perturbations", type=int, default=2)
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    rep = compute(cfg, conn, a.designs, a.min_perturbations, a.dry_run)
    os.makedirs(os.path.join(ROOT, "reports", "data"), exist_ok=True)
    with open(os.path.join(ROOT, "reports", "data", "phase6_floors.json"), "w") as f:
        json.dump(rep, f, indent=1, default=str)
    with open(os.path.join(ROOT, "reports", "phase6_floors.md"), "w") as f:
        f.write(render(rep))
    print(render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
