#!/usr/bin/env python3
"""DECISION 2026-09-18 (d) B3 / (e) 3: proportional VC Formal seat shares for the long-pole lanes. For every design still running or
queued in the search, the remaining proof work = proofs per call × mean proof minutes × remaining run-equivalents (measured on the
design's own records); lanes (config queue.lanes.vcf) get shares proportional to their remaining seat-hours, the rest goes to the
window designs, so that every lane and the rest finish at the same time; the total never exceeds the pool cap. A lane with no
work keeps 0 (its share is released). `--apply` writes the shares into config/experiments.yaml (the `share:` values only) and
prints the table; without it the table is printed only. The daemon holds its config from start-up: restart it after --apply
(`scripts/queue/daemon.py stop` / `start`; recovery adopts the live drivers).
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
    held = {}   # runs whose search job carries `hold` are not dispatchable (router until C3, LSTM until the small tier): they are outside the split
    for r in conn.execute("SELECT design_id, COUNT(*) FROM jobs WHERE kind='search' AND state='queued' AND payload_json LIKE '%\"hold\"%' GROUP BY design_id"):
        held[r[0]] = int(r[1])
    queued_now = {r[0]: int(r[1]) for r in conn.execute("SELECT design_id, COUNT(*) FROM jobs WHERE kind='vcf' AND state IN ('queued','backoff') GROUP BY design_id")}
    for d in tiers:
        runs = [dict(r) for r in conn.execute("SELECT status, llm_calls FROM runs WHERE exp=? AND design_id=? AND status!='superseded' AND COALESCE(excluded_from_tables,0)=0", (exp, d))]
        rem = max(0, sum(1 for r in runs if r["status"] == "created") - held.get(d, 0)) + sum(max(0.0, 1 - int(r["llm_calls"] or 0) / 60) for r in runs if r["status"] == "running")
        # 2026-09-20 17:2x: a run that has spent all 60 calls contributes 0 to `rem` although its candidates still wait for verdicts —
        # the lane was then given 0 seats and its queued proofs could never drain (cktevo_risc__cpu: 6 running runs, 62 queued proofs,
        # a 61-hour wait on the one seat it kept). The proofs already in the queue are counted as work of their own.
        q_now = queued_now.get(d, 0)
        if rem <= 0 and q_now <= 0:
            continue
        hv_now = int((cfg.get("equiv") or {}).get("harness_version", 1) or 1)
        xs = []
        if hv_now >= 2:   # DECISION 2026-09-19 (j) item 3: once a design has 20 proofs under the current harness version, only those count
            xs = [(P(r[1]) - P(r[0])).total_seconds() / 60 for r in conn.execute("SELECT j.started_at, j.finished_at FROM jobs j JOIN candidates x ON x.cand_id=j.cand_id WHERE j.kind='vcf' AND j.design_id=? AND j.state='done' "
                                                                                 "AND x.harness_version=? AND j.started_at IS NOT NULL AND j.finished_at IS NOT NULL ORDER BY j.finished_at DESC LIMIT 400", (d, hv_now))]
            if len(xs) < 20:
                xs = []
        if not xs:
            xs = [(P(r[1]) - P(r[0])).total_seconds() / 60 for r in conn.execute("SELECT started_at, finished_at FROM jobs WHERE kind='vcf' AND design_id=? AND state='done' AND started_at IS NOT NULL AND finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 400", (d,))]
        calls = sum(int(r["llm_calls"] or 0) for r in runs)
        proofs = conn.execute("SELECT count(*) FROM jobs j JOIN candidates x ON x.cand_id=j.cand_id JOIN runs r ON r.run_id=x.run_id WHERE j.kind='vcf' AND r.exp=? AND r.status!='superseded' AND r.design_id=?", (exp, d)).fetchone()[0]
        ppc = (proofs / calls) if calls else None
        mean = statistics.mean(xs) if xs else None
        queued_hours = (q_now * mean / 60) if (mean is not None and len(xs) >= 20) else None
        future_hours = (rem * ppc * 60 * mean / 60) if (ppc is not None and mean is not None and len(xs) >= 20) else None
        out[d] = {"hours": (None if (queued_hours is None and future_hours is None) else (queued_hours or 0.0) + (future_hours or 0.0)),
                  "queued_proofs": q_now, "queued_hours": (round(queued_hours, 1) if queued_hours is not None else None), "runs_left": round(rem, 1),
                  "mean_min": round(mean, 1) if mean is not None else None, "proofs_per_call": round(ppc, 2) if ppc is not None else None, "proofs": len(xs), "tier": tiers[d]}
    # DECISION 2026-09-18 (g) item 2: a proxy for the seat-hours per run of a design without enough proofs under the current harness
    # (config queue.lane_hours_per_run_override: {design: hours}) — used until the design has 20 finished proofs under harness_version 2
    hv = int((cfg.get("equiv") or {}).get("harness_version", 1) or 1)
    for d, h in ((cfg["queue"].get("lane_hours_per_run_override") or {}).items()):
        if d in out:
            n_v2 = conn.execute("SELECT count(*) FROM candidates WHERE design_id=? AND harness_version=? AND v3_status IS NOT NULL", (d, hv)).fetchone()[0] if hv >= 2 else 0
            if n_v2 < 20:
                out[d]["hours"] = out[d]["runs_left"] * float(h) + (out[d].get("queued_hours") or 0.0)
                out[d]["proxy"] = True
    # a design with fewer than 20 finished proofs (a corrected harness, a tier not started) takes its tier's median seat-hours per run
    for tier in {v["tier"] for v in out.values()}:
        known = [v["hours"] / v["runs_left"] for v in out.values() if v["tier"] == tier and v["hours"] is not None and v["runs_left"] > 0]
        fallback = statistics.median(known) if known else 2.0
        for d, v in out.items():
            if v["tier"] == tier and v["hours"] is None:
                v["hours"] = v["runs_left"] * fallback + (v.get("queued_proofs", 0) * 0.5)   # a queued proof without a measured mean: half an hour each
                v["estimated"] = True
    return out


def shares(cfg, hours, cap, min_seats=1):
    """Integer seats per lane and for the rest that make the finish times (remaining seat-hours / seats) agree as closely as the
    integers allow (DECISION 2026-09-18 (f) item 2: within 2 hours where possible): the allocation with the smallest spread of finish
    times among those summing to `cap`, every lane with work getting at least `min_seats`; a lane without work gets 0."""
    import itertools
    lanes = {n: s for n, s in ((cfg["queue"].get("lanes") or {}).get("vcf") or {}).items() if not s.get("leftover")}   # (g) item 1: the small tier's leftover lane is outside the equalisation
    leftover_designs = {d for s in ((cfg["queue"].get("lanes") or {}).get("vcf") or {}).values() if s.get("leftover") for d in (s.get("designs") or [])}
    lane_hours = {name: sum(hours.get(d, {}).get("hours", 0.0) for d in (spec.get("designs") or [])) for name, spec in lanes.items()}
    lane_designs = {d for spec in lanes.values() for d in (spec.get("designs") or [])}
    others = sum(v["hours"] for d, v in hours.items() if d not in lane_designs and d not in leftover_designs)
    active = [n for n, h in lane_hours.items() if h > 0]
    total = sum(lane_hours[n] for n in active) + others
    if total <= 0:
        return {name: 0 for name in lanes}, cap, lane_hours, others
    ideal = {n: cap * lane_hours[n] / total for n in active}
    ranges = [range(max(min_seats, int(ideal[n]) - 2), int(ideal[n]) + 4) for n in active]
    best, best_spread = None, None
    for combo in itertools.product(*ranges) if active else [()]:
        rest = cap - sum(combo)
        if rest < (min_seats if others > 0 else 0):
            continue
        finishes = [lane_hours[n] / s for n, s in zip(active, combo)] + ([others / rest] if others > 0 and rest > 0 else [])
        spread = (max(finishes) - min(finishes)) if finishes else 0.0
        if best is None or spread < best_spread - 1e-9:
            best, best_spread = combo, spread
    out = {name: 0 for name in ((cfg["queue"].get("lanes") or {}).get("vcf") or {})}   # leftover lanes keep share 0 (they take what the others cannot fill)
    for n, s in zip(active, best or ()):
        out[n] = s
    rest = cap - sum(out.values())
    return out, rest, lane_hours, others


def apply(cfg_path, new_shares, state_path=None):
    """Writes the shares into the config (share: values only) and the change into results/queue/lane_shares.json — {at, previous,
    current} — so that idle-seat-minute accounting (src.jobqueue.core.idle_seat_minutes) uses the share in force at each minute
    of its window instead of reading the past hour against the new shares (the re-balance artefact of 2026-09-19 14:11 / 2026-09-20 07:56)."""
    text = open(cfg_path).read()
    previous = {}
    for name, n in new_shares.items():
        pat = re.compile(r"(^\s+%s:\s*\{designs:\s*\[[^\]]*\],\s*share:\s*)(\d+)" % re.escape(name), re.M)
        m = pat.search(text)
        if m:
            previous[name] = int(m.group(2))
        text, k = pat.subn(lambda m: m.group(1) + str(n), text)
        if k != 1 and n:
            raise SystemExit(f"lane {name}: share line not found in {cfg_path}")
    open(cfg_path, "w").write(text)
    sp = state_path or os.path.join(C.results_dir(C.load()), "queue", "lane_shares.json")
    try:
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        with open(sp, "w") as f:
            json.dump({"at": datetime.datetime.now().isoformat(timespec="minutes"), "previous": previous, "current": dict(new_shares)}, f, indent=1)
    except OSError:
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-seats", type=int, default=1)
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    cap = int(cfg["queue"].get("vcf_seats_target") or cfg["queue"]["vcf_seats_max"])
    hours = remaining_seat_hours(cfg, conn)
    new, rest, lane_hours, others = shares(cfg, hours, cap, a.min_seats)
    all_lanes = (cfg["queue"].get("lanes") or {}).get("vcf") or {}
    lanes = {n: s for n, s in all_lanes.items() if not s.get("leftover")}
    leftover = {n: s for n, s in all_lanes.items() if s.get("leftover")}
    print(f"{datetime.datetime.now().isoformat(timespec='minutes')} remaining proof seat-hours: " + ", ".join(f"{n} {lane_hours[n]:.0f}" for n in lanes) + f", others (medium window) {others:.0f}; cap {cap}")
    print("shares: " + ", ".join(f"{n} {lanes[n].get('share')} -> {new[n]}" for n in lanes) + f"; others {rest}")
    fin = {n: (lane_hours[n] / new[n] if new[n] else None) for n in lanes}
    fin["others"] = others / rest if rest else None
    print("implied finish (h): " + ", ".join(f"{n} {v:.1f}" if v is not None else f"{n} -" for n, v in fin.items()) + f"; spread {max(v for v in fin.values() if v is not None) - min(v for v in fin.values() if v is not None):.1f} h")
    lane_runs = {n: sum(hours.get(d, {}).get("runs_left", 0) for d in lanes[n]["designs"]) for n in lanes}
    lane_designs = {x for s in all_lanes.values() for x in s["designs"]}
    print("remaining runs per lane: " + ", ".join(f"{n} {lane_runs[n]:.1f}" for n in lanes) + f"; others {sum(v['runs_left'] for d, v in hours.items() if d not in lane_designs):.0f}")
    for n, s in leftover.items():
        h = sum(hours.get(d, {}).get("hours", 0.0) for d in s["designs"]); r = sum(hours.get(d, {}).get("runs_left", 0) for d in s["designs"])
        med = max(v for v in fin.values() if v is not None) if any(v is not None for v in fin.values()) else 0.0
        print(f"leftover lane {n}: {r:.0f} runs, {h:.0f} seat-h (estimates), seats only as the medium lanes leave them; with every seat after the medium tier ends ≈ {med:.1f} h + {h / cap:.1f} h = {med + h / cap:.1f} h at the latest")
    top = sorted(((d, v["hours"]) for d, v in hours.items()), key=lambda x: -x[1])[:8]
    print("largest remaining per design: " + ", ".join(f"{d} {h:.0f} h" for d, h in top))
    if a.apply:
        apply(os.path.join(ROOT, "config", "experiments.yaml"), new)
        print("applied to config/experiments.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
