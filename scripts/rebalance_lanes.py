#!/usr/bin/env python3
"""DECISION 2026-09-18 (d) B3 / (e) 3: proportional VC Formal seat shares for the long-pole lanes. For every design still running or
queued in the search, the remaining proof work = proofs per call × mean proof minutes × remaining run-equivalents (measured on the
design's own records); lanes (config queue.lanes.vcf) get shares proportional to their remaining seat-hours, the rest goes to the
window designs, so that every lane and the rest finish at the same time; the total never exceeds the pool cap. A lane with no
work keeps 0 (its share is released). `--apply` writes the shares into config/experiments.yaml (the `share:` values only) and
prints the table; without it the table is printed only. The daemon reads the config on every dispatch: no restart needed.
    .venv/bin/python scripts/rebalance_lanes.py [--apply] [--min-seats 4]"""
import argparse
import datetime
import json
import os
import re
import statistics
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402

P = datetime.datetime.fromisoformat


def remaining_seat_hours(cfg, conn, exp="phase5"):
    """-> {design_id: {"hours": h, "runs_left": n, "mean_min": m, "proofs_per_call": p}} over every design with runs not yet done."""
    tiers = {d: t for t, ds in (cfg["exp5"].get("starting_points") or {}).items() for d in ds}
    out = {}
    for d in tiers:
        runs = [dict(r) for r in conn.execute("SELECT status, llm_calls FROM runs WHERE exp=? AND design_id=? AND status!='superseded' AND COALESCE(excluded_from_tables,0)=0", (exp, d))]
        rem = sum(1 for r in runs if r["status"] == "created") + sum(max(0.0, 1 - int(r["llm_calls"] or 0) / 60) for r in runs if r["status"] == "running")
        if rem <= 0:
            continue
        xs = [(P(r[1]) - P(r[0])).total_seconds() / 60 for r in conn.execute("SELECT started_at, finished_at FROM jobs WHERE kind='vcf' AND design_id=? AND state='done' AND started_at IS NOT NULL AND finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 400", (d,))]
        calls = sum(int(r["llm_calls"] or 0) for r in runs)
        proofs = conn.execute("SELECT count(*) FROM jobs j JOIN candidates x ON x.cand_id=j.cand_id JOIN runs r ON r.run_id=x.run_id WHERE j.kind='vcf' AND r.exp=? AND r.status!='superseded' AND r.design_id=?", (exp, d)).fetchone()[0]
        ppc = (proofs / calls) if calls else None
        mean = statistics.mean(xs) if xs else None
        out[d] = {"hours": (rem * ppc * 60 * mean / 60) if (ppc is not None and mean is not None and len(xs) >= 20) else None, "runs_left": round(rem, 1),
                  "mean_min": round(mean, 1) if mean is not None else None, "proofs_per_call": round(ppc, 2) if ppc is not None else None, "proofs": len(xs), "tier": tiers[d]}
    # a design with fewer than 20 finished proofs (a corrected harness, a tier not started) takes its tier's median seat-hours per run
    for tier in {v["tier"] for v in out.values()}:
        known = [v["hours"] / v["runs_left"] for v in out.values() if v["tier"] == tier and v["hours"] is not None and v["runs_left"] > 0]
        fallback = statistics.median(known) if known else 2.0
        for d, v in out.items():
            if v["tier"] == tier and v["hours"] is None:
                v["hours"] = v["runs_left"] * fallback
                v["estimated"] = True
    return out


def shares(cfg, hours, cap, min_seats=4):
    lanes = (cfg["queue"].get("lanes") or {}).get("vcf") or {}
    lane_hours = {name: sum(hours.get(d, {}).get("hours", 0.0) for d in (spec.get("designs") or [])) for name, spec in lanes.items()}
    lane_designs = {d for spec in lanes.values() for d in (spec.get("designs") or [])}
    others = sum(v["hours"] for d, v in hours.items() if d not in lane_designs)
    total = sum(lane_hours.values()) + others
    if total <= 0:
        return {name: 0 for name in lanes}, cap, lane_hours, others
    out = {}
    for name, h in lane_hours.items():
        out[name] = 0 if h <= 0 else max(min_seats, int(round(cap * h / total)))
    rest = cap - sum(out.values())
    if rest < min_seats and others > 0:   # keep the window designs alive: take the deficit from the largest lane
        big = max(out, key=lambda n: out[n])
        out[big] -= (min_seats - rest)
        rest = min_seats
    return out, rest, lane_hours, others


def apply(cfg_path, new_shares):
    text = open(cfg_path).read()
    for name, n in new_shares.items():
        pat = re.compile(r"(^\s+%s:\s*\{designs:\s*\[[^\]]*\],\s*share:\s*)(\d+)" % re.escape(name), re.M)
        text, k = pat.subn(lambda m: m.group(1) + str(n), text)
        if k != 1:
            raise SystemExit(f"lane {name}: share line not found in {cfg_path}")
    open(cfg_path, "w").write(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-seats", type=int, default=4)
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    cap = int(cfg["queue"].get("vcf_seats_target") or cfg["queue"]["vcf_seats_max"])
    hours = remaining_seat_hours(cfg, conn)
    new, rest, lane_hours, others = shares(cfg, hours, cap, a.min_seats)
    lanes = (cfg["queue"].get("lanes") or {}).get("vcf") or {}
    print(f"{datetime.datetime.now().isoformat(timespec='minutes')} remaining proof seat-hours: " + ", ".join(f"{n} {lane_hours[n]:.0f}" for n in lanes) + f", others {others:.0f}; cap {cap}")
    print("shares: " + ", ".join(f"{n} {lanes[n].get('share')} -> {new[n]}" for n in lanes) + f"; others {rest}")
    top = sorted(((d, v["hours"]) for d, v in hours.items()), key=lambda x: -x[1])[:8]
    print("largest remaining per design: " + ", ".join(f"{d} {h:.0f} h" for d, h in top))
    if a.apply:
        apply(os.path.join(ROOT, "config", "experiments.yaml"), new)
        print("applied to config/experiments.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
