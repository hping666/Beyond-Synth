#!/usr/bin/env python3
"""Phase 2.2 / 2.3 for the visible configurations (docs/spec/02-noise-floor.md §3–§4): run every original design
D (is_baseline = 1) and its SEQ-proven perturbations under `noise.configs` that are not hidden (E1, E2, E3, E4) at
the design's knee period, then compute sigma_D per configuration and metric into the `noise_floor` table.
Hidden configurations (H1, H2a, H2b, H5, H3) are run and summarised only by scripts/hidden_worker.py (rule 3).

    .venv/bin/python scripts/phase2_noise.py submit  [--suite ...] [--design ...] [--configs E1 E2 E3 E4] [--submit] [--priority N]
    .venv/bin/python scripts/phase2_noise.py collect [--suite ...] [--design ...]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import statistics  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.designs import jobs as J  # noqa: E402
from src.noise import stats as S  # noqa: E402

EPS = 1e-6


def visible_noise_configs(cfg):
    return [c for c in cfg["noise"]["configs"] if not cfg["configs"][c].get("hidden")]


def phi_of(row, lib="nangate45"):
    return row.get(f"phi_main_ns_{lib}") if row else None


def selected(conn, a):
    rows = {r["design_id"]: dict(r) for r in conn.execute("SELECT * FROM designs")}
    out = []
    for d in K.load_all():
        if a.suite and d["suite"] not in a.suite:
            continue
        if a.design and d["design_id"] not in a.design:
            continue
        r = rows.get(d["design_id"]) or {}
        eligible = r.get("e4_synthesizable") == 1 and "multi_clock" not in d["tags"] and "yosys_failed" not in d["tags"]
        if (r.get("split") in ("dev", "held") or (d["suite"] == "rtlrewriter" and eligible)) and phi_of(r) is not None:
            out.append((d, r))
    return out


def proven_perturbations(conn, design_id):
    return [dict(r) for r in conn.execute("SELECT pert_id, ptype, path FROM perturbations WHERE design_id=? AND seq_status IN ('proven', 'proven_rename') ORDER BY ptype, pert_id", (design_id,))]


def cmd_submit(cfg, conn, a):
    configs = a.configs or visible_noise_configs(cfg)
    for c in configs:
        if cfg["configs"][c].get("hidden"):
            raise SystemExit(f"{c} is hidden: run it through scripts/hidden_worker.py (CLAUDE.md rule 3)")
    from src.noise import saif as SF
    jobs, no_saif = [], 0
    for d, r in selected(conn, a):
        phi = float(phi_of(r))
        perts = proven_perturbations(conn, d["design_id"])
        sf = SF.load_saif(d["design_id"]) or {}
        d_saif = (sf.get("design") or {})
        if a.ptype:
            perts = [p for p in perts if p["ptype"] in a.ptype]

        def have(config, pert_id):
            if not a.missing:
                return False
            if pert_id is None:
                q = "SELECT 1 FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' AND abs(clock_ns-?)<? LIMIT 1"
                return conn.execute(q, (d["design_id"], config, phi, EPS)).fetchone() is not None
            q = "SELECT 1 FROM evaluations WHERE design_id=? AND config=? AND pert_id=? AND status='ok' AND abs(clock_ns-?)<? LIMIT 1"
            return conn.execute(q, (d["design_id"], config, pert_id, phi, EPS)).fetchone() is not None
        for config in configs:
            if not a.ptype and not have(config, None):  # a type filter adds perturbations to an existing batch: D was already run
                jb = J.dc_job(cfg, d, config, phi, a.priority)
                if d_saif.get("saif"):
                    jb["payload"].update(saif=d_saif["saif"], saif_instance=d_saif["instance"])
                else:
                    no_saif += 1
                jobs.append(jb)
            for p in perts:
                if have(config, p["pert_id"]):
                    continue
                j = J.dc_job(cfg, d, config, phi, a.priority)
                j["payload"].update(rtl=[str(Path(ROOT) / p["path"])], incdirs=[], is_baseline=0, pert_id=p["pert_id"])
                ps = (sf.get("perturbations") or {}).get(p["pert_id"]) or {}
                if ps.get("saif"):
                    j["payload"].update(saif=ps["saif"], saif_instance=ps["instance"])
                else:
                    no_saif += 1
                j["cand_id"] = None
                jobs.append(j)
    if no_saif:
        print(f"warning: {no_saif} jobs without SAIF (run scripts/phase2_saif.py build first for power_saif)")
    print(f"{len(jobs)} noise jobs ({', '.join(configs)}) for {len(selected(conn, a))} designs")
    out = Path(C.results_dir(cfg)) / "queue" / "jobs" / f"phase2_noise_{datetime.datetime.now():%Y%m%d_%H%M%S}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    import yaml
    out.write_text(yaml.safe_dump({"jobs": jobs}, sort_keys=False))
    if a.submit:
        from src.jobqueue.core import Queue
        q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
        for j in jobs:
            q.submit(j["kind"], j["payload"], design_id=j["design_id"], config=j["config"], priority=j["priority"], timeout_sec=j["timeout_sec"])
        print(f"submitted {len(jobs)} jobs")
    return 0


def cmd_collect(cfg, conn, a):
    configs = visible_noise_configs(cfg)
    report = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "configs": configs, "designs": {}, "per_config": {}}
    n_rows = 0
    # rule A (DECISIONS 2026-09-14): the pooled minimum per configuration and metric is computed over every set design's
    # perturbation records first; designs without a measured floor get pooled rows (floor_source = pooled)
    nz = cfg["noise"]
    k, q, quiet = float(nz["k_sigma"]), float(nz.get("pooled_quantile", 0.90)), float(nz.get("quiet_max_abs", 0.001))
    all_sets = [(d, r) for d, r in selected(conn, argparse.Namespace(suite=None, design=None)) if r.get("split") in ("dev", "held")]
    proven_all = S.proven_by_design(conn)
    weighting = nz.get("pooled_weighting", "design")
    set_list = [{"design_id": d["design_id"], "phi": float(phi_of(r))} for d, r in all_sets]
    pooled = {config: S.pooled_minimum(conn, set_list, config, proven_all, q, EPS, weighting) for config in configs}
    report["pooled_min"] = pooled
    report["pooled_min_record_weighted"] = {config: S.pooled_minimum(conn, set_list, config, proven_all, q, EPS, "record") for config in configs}  # sensitivity only
    report["pooled_weighting"] = weighting
    for d, r in selected(conn, a):
        phi = float(phi_of(r))
        proven = {p["pert_id"] for p in proven_perturbations(conn, d["design_id"])}
        entry = {"phi": phi, "proven": len(proven), "configs": {}}
        for config in configs:
            base, latest = S.pick_records(conn, d["design_id"], config, proven, phi, EPS)
            if base is None or len(latest) < 2:
                rows = S.pooled_rows(d["design_id"], config, pooled[config]) if (nz.get("pooled_floor_for_missing") and r.get("split") in ("dev", "held")) else []
                n_rows += S.upsert_floor(conn, rows)
                entry["configs"][config] = {"baseline": base is not None, "perturbations": len(latest), "rows": len(rows), "floor_source": "pooled" if rows else None,
                                            "t_d": {row["metric"]: row["t_d"] for row in rows}}
                continue
            rows = S.floor_rows(d["design_id"], config, base, list(latest.values()), phi, pooled[config], k, quiet)
            n_rows += S.upsert_floor(conn, rows)
            entry["configs"][config] = {"baseline": True, "perturbations": len(latest), "rows": len(rows), "floor_source": "measured",
                                        "floor_class": rows[0]["floor_class"] if rows else None,
                                        "sigma": {row["metric"]: row["sigma_robust"] for row in rows}, "t_d": {row["metric"]: row["t_d"] for row in rows}}
            for row in rows:
                report["per_config"].setdefault(config, {}).setdefault(row["metric"], []).append(row["sigma_robust"])
                report.setdefault("per_config_t_d", {}).setdefault(config, {}).setdefault(row["metric"], []).append(row["t_d"])
        report["designs"][d["design_id"]] = entry
    summary = {}
    for config, metrics in report["per_config"].items():
        summary[config] = {m: {"n": len(v), "median": statistics.median(v), "q75": S.quantile(v, 0.75), "max": max(v)} for m, v in metrics.items() if v}
    report["summary"] = summary
    report["summary_t_d"] = {config: {m: {"n": len(v), "median": statistics.median(v), "q75": S.quantile(v, 0.75), "max": max(v)} for m, v in metrics.items() if v}
                             for config, metrics in report.get("per_config_t_d", {}).items()}
    classes = {}
    for did, e in report["designs"].items():
        for config, c in e["configs"].items():
            key = c.get("floor_class") or ("pooled" if c.get("floor_source") == "pooled" else "none")
            classes.setdefault(config, {}).setdefault(key, 0)
            classes[config][key] += 1
    report["floor_classes"] = classes
    out = Path(ROOT) / "reports" / "data" / "phase2_noise_floor.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + "\n")
    warn = float(cfg["noise"]["sigma_median_warn_pct"]) / 100.0
    for config, ms in sorted(summary.items()):
        for m, s in sorted(ms.items()):
            flag = "  <-- above the G1 warning level" if m == "area" and s["median"] > warn else ""
            print(f"  {config:4s} {m:10s} n={s['n']:3d} median sigma={s['median']:.4f} q75={s['q75']:.4f} max={s['max']:.4f}{flag}")
    print(f"{n_rows} noise_floor rows written; report {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["submit", "collect"])
    ap.add_argument("--suite", nargs="*", default=None)
    ap.add_argument("--design", nargs="*", default=None)
    ap.add_argument("--configs", nargs="*", default=None)
    ap.add_argument("--ptype", nargs="*", default=None, help="only these perturbation types, without the D baseline (adds to an existing batch)")
    ap.add_argument("--missing", action="store_true", help="only D / perturbation runs without an ok record at Phi_main (adds to an existing batch)")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--priority", type=int, default=0)
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    return cmd_submit(cfg, conn, a) if a.what == "submit" else cmd_collect(cfg, conn, a)


if __name__ == "__main__":
    sys.exit(main())
