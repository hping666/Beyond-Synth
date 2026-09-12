#!/usr/bin/env python3
"""Collect the Phase 1 EDA results into the designs table (docs/PLAN.md 1.2 / 1.3).

    .venv/bin/python scripts/phase1_collect.py trial   # designs.e4_synthesizable / e4_fail_reason from the E4 trial
    .venv/bin/python scripts/phase1_collect.py knee    # designs.phi_main_ns_<lib> / knee_table_json from the sweeps

trial: a design is synthesizable when an ok E4 baseline record exists at the trial period (loosest knee period on
Nangate45); otherwise the reason comes from the eval_failed record's meta.json or from the failed queue job.
knee : per library the ok baseline records of the sweep configuration (config knee.configs) at the sweep periods
form the (T, area, WNS, TNS) curve; src/eval/knee.choose_knee picks Φ_main (config knee.slack_tol / area_tol);
multi_clock designs are skipped. Both write a JSON next to the report data (reports/data/phase1_<what>.json).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.designs import jobs as J  # noqa: E402
from src.eval.knee import choose_knee  # noqa: E402

EPS = 1e-6


def baseline_rows(conn, design_id, config):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND cand_id IS NULL AND pert_id IS NULL "
        "ORDER BY eval_id", (design_id, config))]


def failure_reason(conn, design_id, config, rows):
    for r in reversed(rows):
        if r["status"] == "eval_failed":
            meta = Path(r["raw_dir"]) / "meta.json"
            if meta.exists():
                m = json.loads(meta.read_text())
                return f"{m.get('status')}: {(m.get('error') or '')[:300]}".strip(": ")
            return "eval_failed"
    job = conn.execute("SELECT error, state FROM jobs WHERE design_id=? AND config=? AND kind='dc' ORDER BY submitted_at DESC LIMIT 1",
                       (design_id, config)).fetchone()
    if job is None:
        return "not run"
    if job["state"] in ("queued", "running", "backoff"):
        return "pending"
    return f"job {job['state']}: {(job['error'] or '')[:300]}"


def collect_trial(cfg, conn):
    lib = "nangate45"
    config, period = cfg["knee"]["configs"][lib], J.trial_period(cfg, lib)
    out, per_suite = [], {}
    for d in K.load_all():
        rows = baseline_rows(conn, d["design_id"], config)
        ok = [r for r in rows if r["status"] == "ok" and abs(float(r["clock_ns"]) - period) < EPS]
        rec = {"design_id": d["design_id"], "suite": d["suite"], "loc": d["loc"], "tags": d["tags"]}
        if ok:
            r = ok[-1]
            rec.update(e4_synthesizable=1, e4_fail_reason=None, area_um2=r["area_um2"], cells=r["cells"], wns_ns=r["wns_ns"],
                       tns_ns=r["tns_ns"], dc_seconds=r["dc_seconds"], registers=json.loads(r["log_summary_json"] or "{}").get("registers"))
        else:
            reason = failure_reason(conn, d["design_id"], config, rows)
            undecided = reason in ("pending", "not run")
            rec.update(e4_synthesizable=(None if undecided else 0), e4_fail_reason=(None if undecided else reason), pending=undecided)
        conn.execute("UPDATE designs SET e4_synthesizable=?, e4_fail_reason=?, git_sha=?, cfg_hash=? WHERE design_id=?",
                     (rec["e4_synthesizable"], rec["e4_fail_reason"], C.git_sha(), C.cfg_hash(), d["design_id"]))
        s = per_suite.setdefault(d["suite"], {"designs": 0, "ok": 0, "failed": 0, "pending": 0, "dc_seconds": 0.0})
        s["designs"] += 1
        s["ok" if rec["e4_synthesizable"] == 1 else "failed" if rec["e4_synthesizable"] == 0 else "pending"] += 1
        s["dc_seconds"] += float(rec.get("dc_seconds") or 0)
        out.append(rec)
    report = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "config": config, "clock_ns": period,
              "per_suite": per_suite, "designs": out}
    path = Path(ROOT) / "reports" / "data" / "phase1_trial.json"
    path.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + "\n")
    for suite, s in sorted(per_suite.items()):
        print(f"  {suite:12s} designs={s['designs']:3d} ok={s['ok']:3d} failed={s['failed']:3d} pending={s['pending']:3d} dc_hours={s['dc_seconds'] / 3600:.2f}")
    for rec in out:
        if rec["e4_synthesizable"] == 0:
            print(f"    FAILED {rec['design_id']}: {rec['e4_fail_reason']}")
    print(f"report: {path}")
    return 0


def collect_knee(cfg, conn):
    knee = cfg["knee"]
    out, per_lib = [], {}
    for d in K.load_all():
        if "multi_clock" in d["tags"]:
            continue
        rec = {"design_id": d["design_id"], "suite": d["suite"], "libs": {}}
        table = {}
        for lib, config in knee["configs"].items():
            periods = [float(p) for p in knee["periods_ns"][lib]]
            rows = [r for r in baseline_rows(conn, d["design_id"], config) if r["status"] == "ok"]
            pts = []
            for T in periods:
                hits = [r for r in rows if abs(float(r["clock_ns"]) - T) < EPS]
                if hits:
                    r = hits[-1]
                    pts.append({"T": T, "area": r["area_um2"], "wns": r["wns_ns"], "tns": r["tns_ns"], "cells": r["cells"], "dc_seconds": r["dc_seconds"]})
            entry = {"points": pts, "complete": len(pts) == len(periods), "phi": None, "fallback": None}
            if pts:
                try:
                    phi, fb = choose_knee(pts, knee["slack_tol"], knee["area_tol"])
                    entry.update(phi=phi, fallback=fb)
                except ValueError as e:
                    entry["error"] = str(e)
            table[lib] = entry
            rec["libs"][lib] = {"phi": entry["phi"], "fallback": entry["fallback"], "points": len(pts), "complete": entry["complete"]}
            s = per_lib.setdefault(lib, {"designs": 0, "complete": 0, "with_phi": 0, "fallback": 0, "phi_hist": {}})
            s["designs"] += 1
            s["complete"] += int(entry["complete"])
            if entry["phi"] is not None:
                s["with_phi"] += 1
                s["fallback"] += int(bool(entry["fallback"]))
                s["phi_hist"][str(entry["phi"])] = s["phi_hist"].get(str(entry["phi"]), 0) + 1
        if any(e["phi"] is not None for e in table.values()):
            conn.execute("UPDATE designs SET phi_main_ns_nangate45=?, phi_main_ns_asap7=?, phi_main_ns_sky130hd=?, knee_table_json=?, "
                         "git_sha=?, cfg_hash=? WHERE design_id=?",
                         (table.get("nangate45", {}).get("phi"), table.get("asap7", {}).get("phi"), table.get("sky130hd", {}).get("phi"),
                          json.dumps(table, sort_keys=True), C.git_sha(), C.cfg_hash(), d["design_id"]))
        rec["table"] = table
        out.append(rec)
    report = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "params": {k: knee[k] for k in ("periods_ns", "slack_tol", "area_tol", "configs")},
              "per_lib": per_lib, "designs": out}
    path = Path(ROOT) / "reports" / "data" / "phase1_knee.json"
    path.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + "\n")
    for lib, s in sorted(per_lib.items()):
        print(f"  {lib:10s} designs={s['designs']:3d} complete={s['complete']:3d} with_phi={s['with_phi']:3d} fallback={s['fallback']:3d} "
              f"phi_hist={dict(sorted(s['phi_hist'].items(), key=lambda kv: -float(kv[0])))}")
    print(f"report: {path}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["trial", "knee"])
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    return collect_trial(cfg, conn) if a.what == "trial" else collect_knee(cfg, conn)


if __name__ == "__main__":
    sys.exit(main())
