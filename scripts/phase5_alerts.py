#!/usr/bin/env python3
"""DECISION 2026-09-18 (d) F3: the completion alert of the hourly check. Computes the complete-design set (src.analysis.phase5
.completion_view), compares it with the last recorded one (reports/data/phase5_complete_designs.json) and, when it changed, prints
the "New complete designs since last render" line first, appends it to STATUS.md and records the new set. Exit 0 always.
    .venv/bin/python scripts/phase5_alerts.py [--dry-run]"""
import json
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
from src import config as C  # noqa: E402
from src.analysis import phase5 as P5  # noqa: E402
from src.db import core as db  # noqa: E402


def post_slack(cfg, text):
    """DECISION 2026-09-18 (e) item 4: post the alert line to the Slack incoming webhook whose URL sits in the environment variable named by
    config alerts.slack_webhook_env; the URL itself is never printed or written anywhere. -> a one-line status."""
    import json as _json
    import urllib.request
    name = ((cfg.get("alerts") or {}).get("slack_webhook_env") or "").strip()
    if not name:
        return "slack: no webhook variable configured (alerts.slack_webhook_env)"
    url = os.environ.get(name)
    if not url:
        return f"slack: variable {name} not set in this environment"
    try:
        req = urllib.request.Request(url, data=_json.dumps({"text": text}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return f"slack: posted (HTTP {resp.status})"
    except Exception as e:   # the alert must never fail the check; the URL is not part of the message
        return f"slack: post failed ({type(e).__name__})"


SLOT_STATE = os.path.join(ROOT, "results", "queue", "slot_guard_state.json")


BASELINE_WINDOW = ("2026-09-18T05:49", "2026-09-19T02:09")   # DECISION 2026-09-19 (k) item 2: each row's baseline for the relative revert


def slot_report(cfg, conn, write=True, restart=None):
    """DECISION 2026-09-19 (j) 1c / 1d and (k) 1–3: the hourly slot figures — runs generating / waiting / queued, the unverified-at-build
    fraction per lane, per arm-model row and per design (last hour), the estimated proof-queue wait per lane, the idle seat-minutes
    per lane in the last hour — and, per design, the unverified-at-build fraction of the runs admitted after the (j) switch against
    the runs admitted before it (DECISION 2026-09-19 (l) 1). The relative revert rule of (k) 2 (a row more than 20 points worse than
    its own baseline for three consecutive checks flips queue.count_waiting_runs and restarts the daemon) runs only with
    queue.admission_guard.auto_revert true; it is suspended by (l) 1. -> lines to print."""
    import json as _json
    from src.jobqueue.core import admission_cohorts, idle_seat_minutes, proof_wait_estimate, queued_runs_by_lane, search_slot_state, unverified_at_build
    g = cfg["queue"].get("admission_guard") or {}
    thr = float(g.get("unverified_at_build_max", 0.35)); wmax = float(g.get("proof_wait_max_min", 60))
    slots = search_slot_state(conn, cfg)
    rows = unverified_at_build(conn, cfg, minutes=int(g.get("window_min", 60)), tier=g.get("tier", "medium"), by="row")
    lanes_f = unverified_at_build(conn, cfg, minutes=int(g.get("window_min", 60)), tier=g.get("tier", "medium"), by="lane")
    designs_f = unverified_at_build(conn, cfg, minutes=int(g.get("window_min", 60)), tier=g.get("tier", "medium"), by="design")
    waits = proof_wait_estimate(conn, cfg)
    idle = idle_seat_minutes(conn, cfg, hours=1.0)
    by_lane = {k: float(v) for k, v in (g.get("proof_wait_max_min_by_lane") or {}).items()}   # DECISION 2026-09-19 (m) 7
    lines = [f"search slots: generating {slots['generating']} (max {cfg['queue'].get('generating_max')}), waiting for verdicts {slots['waiting']}, queued {slots['queued']}; counting waiting runs: {bool(cfg['queue'].get('count_waiting_runs'))}",
             "per lane (last hour): " + ", ".join(f"{n}: unverified-at-build {lanes_f[n]:.0%}" if n in lanes_f else f"{n}: no generation" for n in waits) ,
             "estimated proof-queue wait per lane (min): " + ", ".join(f"{n} {v['wait_min']:.0f} ({v['queued']} queued, {v['seats']} seats, {v['mean_min']:.0f} min mean){' PAUSED' if (v['wait_min'] > by_lane.get(n, wmax) or (lanes_f.get(n) or 0) > thr) else ''}" for n, v in waits.items())
             + (" — thresholds raised (m 7): " + ", ".join(f"{k} {v:.0f} min" for k, v in sorted(by_lane.items())) if by_lane else ""),
             "idle seat-minutes per lane (last hour): " + ", ".join(f"{n} {v['idle_min']:.0f} of {v['seats'] * 60}" if v["idle_min"] is not None else f"{n} occupied {v['occupied_min']:.0f} (leftover)" for n, v in idle.items()),
             "unverified-at-build per row: " + (", ".join(f"{k} {v:.0%}" for k, v in sorted(rows.items())) or "no generation built"),
             "unverified-at-build per design: " + (", ".join(f"{k.split('_')[-1]} {v:.0%}" for k, v in sorted(designs_f.items())) or "-")]
    # DECISION 2026-09-19 (m) 7: idle seat-minutes in a lane that has queued runs -> its proof-wait threshold becomes 1.5 x its mean proof time
    qr = queued_runs_by_lane(conn, cfg)
    raised = {}
    for n, v in idle.items():
        if v.get("idle_min") is not None and v["idle_min"] > 0.5 and qr.get(n, 0) > 0:
            mean = float((waits.get(n) or {}).get("mean_min") or 0.0)
            cur, new = by_lane.get(n, wmax), round(1.5 * mean, 1)
            if new > cur:
                raised[n] = (v["idle_min"], qr[n], mean, cur, new)
    if raised:
        applied = ""
        if write:
            set_lane_thresholds(os.path.join(ROOT, "config", "experiments.yaml"), {n: v[4] for n, v in raised.items()})
            applied = " — config updated" + (", daemon restarted" if (restart and restart()) else ", restart the daemon")
        lines.append("lane guardrail (DECISION 2026-09-19 (m) 7): " + "; ".join(f"{n}: {i:.0f} idle seat-minutes in the last hour with {q} queued runs, mean proof {m:.0f} min -> proof-wait threshold {c:.0f} -> {nw:.0f} min"
                                                                          for n, (i, q, m, c, nw) in raised.items()) + (applied or " (dry run: not applied)"))
    try:   # DECISION 2026-09-19 (m) 1: the pool's throughput and the medium-tier B0 E4 ETA against the Stage B proof ETA
        lines.append(pool_progress_line(cfg, conn))
    except Exception as e:   # the report must never fail on the projection
        lines.append(f"offline pool progress: unavailable ({type(e).__name__}: {e})")
    auto = bool(g.get("auto_revert", False))   # DECISION 2026-09-19 (l) item 1: the (k)-2 automatic revert is suspended unless re-enabled
    if auto:
        try:
            st = _json.load(open(SLOT_STATE))
        except (OSError, ValueError):
            st = {"consecutive": {}, "reverted": False}
        if "baseline" not in st:
            st["baseline"] = unverified_at_build(conn, cfg, tier=g.get("tier", "medium"), by="row", since=BASELINE_WINDOW[0], until=BASELINE_WINDOW[1])
        base = st["baseline"]
        for k in set(rows) | set(st["consecutive"]):
            worse = k in rows and (rows[k] - float(base.get(k, rows[k]))) > 0.20
            st["consecutive"][k] = (st["consecutive"].get(k, 0) + 1) if worse else 0
        over = [k for k, n in st["consecutive"].items() if n >= 3]
        lines.append("baseline (05:49–02:09) per row: " + ", ".join(f"{k} {v:.0%}" for k, v in sorted(base.items())))
        if over and not cfg["queue"].get("count_waiting_runs") and write:
            path = os.path.join(ROOT, "config", "experiments.yaml")
            text = open(path).read().replace("  count_waiting_runs: false", "  count_waiting_runs: true", 1)
            open(path, "w").write(text)
            st["reverted"] = True
            lines.append(f"REVERT (k 2): rows more than 20 points worse than their baseline for three consecutive checks: {', '.join(over)} -> queue.count_waiting_runs set to true" + (", daemon restarted" if restart and restart() else ", restart the daemon"))
        if write:
            st["at"] = __import__("datetime").datetime.now().isoformat(timespec="minutes")
            _json.dump(st, open(SLOT_STATE, "w"), indent=1)
        lines.append("consecutive hourly checks more than 20 points worse than the baseline: " + (", ".join(f"{k} {n}" for k, n in sorted(st["consecutive"].items()) if n) or "none"))
    else:
        lines.append("automatic revert suspended (DECISION 2026-09-19 (l) 1): Heng decides from the admission-cohort line below")
    split = str(g.get("admission_split") or "2026-09-19T02:09")
    coh = admission_cohorts(conn, cfg, split, tier=g.get("tier", "medium"))
    def _c(e):
        return f"{e['frac']:.0%} ({e['gens']} gens / {e['runs']} runs)" if e else "no runs"
    lines.append(f"unverified-at-build per design, runs admitted after {split[11:16]} vs before (every generation built; before cohort's builds before {split[11:16]} in brackets): "
                 + (", ".join(f"{d.split('_')[-1]}: after {_c(v['after'])} vs before {_c(v['before'])}" + (f" [{v['before_builds_before_split']['frac']:.0%}]" if v.get("before_builds_before_split") else "") for d, v in sorted(coh.items())) or "no generation built"))
    try:
        pool_lines = [l for l in open(os.path.join(ROOT, "results", "queue", "offline_pool.log")).read().splitlines() if "compress_logs" in l or "pass:" in l]
        lines.append("offline pool: " + (pool_lines[-1][:150] if pool_lines else "no log line"))
        comp = [l for l in pool_lines if "compress_logs" in l]
        if comp:
            lines.append("last compression: " + comp[-1][:150])
    except OSError:
        pass
    return lines


def set_lane_thresholds(path, updates):
    """DECISION 2026-09-19 (m) 7: merge {lane: minutes} into queue.admission_guard.proof_wait_max_min_by_lane in the config file (the
    guard line is a flow mapping; the key is added when absent). The daemon reads it at start."""
    import re
    text = open(path).read()
    m = re.search(r"proof_wait_max_min_by_lane: \{([^}]*)\}", text)
    cur = {}
    if m:
        for part in m.group(1).split(","):
            if ":" in part:
                k, v = part.split(":", 1)
                cur[k.strip()] = float(v)
    cur.update({k: float(v) for k, v in updates.items()})
    inner = ", ".join(f"{k}: {v:g}" for k, v in sorted(cur.items()))
    if m:
        text = text[:m.start()] + f"proof_wait_max_min_by_lane: {{{inner}}}" + text[m.end():]
    else:
        g = re.search(r"^(\s*)admission_guard: \{(.*)\}", text, re.M)
        assert g, "admission_guard flow mapping not found"
        text = text[:g.start()] + f"{g.group(1)}admission_guard: {{{g.group(2)}, proof_wait_max_min_by_lane: {{{inner}}}}}" + text[g.end():]
    open(path, "w").write(text)
    return cur


def pool_progress(cfg, conn, state_path=None):
    """DECISION 2026-09-19 (m) 1: the offline pool's E4 throughput — E4 records of B0 candidates (pool work by construction) and of the
    pool's other entries written in the last hour and the last 3 hours — and the ETA of the medium-tier B0 E4: the pool's waiting
    medium B0 entries plus the candidates expected from the medium B0 runs not yet done (the mean proven-B0 count per finished
    run), at the 3-hour rate. -> dict."""
    import datetime as _dt
    tiers = P5.tier_of_design(cfg)
    try:
        st = json.load(open(state_path or os.path.join(ROOT, "results", "queue", "offline_pool_state.json")))
    except (OSError, ValueError):
        st = {"cands": {}}
    pool_cands = set((st.get("cands") or {}).keys())
    now = _dt.datetime.now()

    def count(hours):
        lo = (now - _dt.timedelta(hours=hours)).isoformat(timespec="seconds")
        out = {"medium_b0": 0, "large_b0": 0, "other": 0}
        for cid, d, arm in conn.execute("SELECT e.cand_id, c.design_id, r.arm FROM evaluations e JOIN candidates c ON c.cand_id=e.cand_id JOIN runs r ON r.run_id=c.run_id "
                                        "WHERE e.config='E4' AND e.created_at > ? AND e.cand_id IS NOT NULL AND r.exp='phase5'", (lo,)):
            if arm == "B0":
                out["medium_b0" if tiers.get(d) == "medium" else "large_b0"] += 1
            elif cid in pool_cands:
                out["other"] += 1
        return out
    h1, h3 = count(1), count(3)
    waiting = sum(1 for c in (st.get("cands") or {}).values() if c.get("group") == "b0_e4" and tiers.get(c.get("design_id")) == "medium" and c.get("stage") in ("e4", "e4_running"))
    med = [d for d, t in tiers.items() if t == "medium"]
    marks = ",".join("?" * len(med)) or "''"
    # DECISION 2026-09-19 (n) 3: once the medium-tier proofs have drained, the throughput is re-estimated over the time since the drain
    open_proofs = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE kind='vcf' AND state IN ('queued', 'running') AND design_id IN ({marks})", med).fetchone()[0] if med else 0
    eta_state_path = os.path.join(os.path.dirname(state_path) if state_path else os.path.join(ROOT, "results", "queue"), "pool_eta_state.json")
    try:
        es = json.load(open(eta_state_path))
    except (OSError, ValueError):
        es = {}
    drained_at = es.get("proofs_drained_at")
    if open_proofs == 0 and not drained_at:
        drained_at = now.isoformat(timespec="minutes"); es["proofs_drained_at"] = drained_at
        try:
            json.dump(es, open(eta_state_path, "w"))
        except OSError:
            pass
    since_drain_min = None
    if drained_at:
        since_drain_min = max(0.0, (now - _dt.datetime.fromisoformat(drained_at)).total_seconds() / 60.0)
    unfinished = conn.execute(f"SELECT COUNT(*) FROM runs WHERE exp='phase5' AND arm='B0' AND status IN ('created', 'running') AND superseded_by IS NULL AND design_id IN ({marks})", med).fetchone()[0] if med else 0
    done_runs = conn.execute(f"SELECT COUNT(*) FROM runs WHERE exp='phase5' AND arm='B0' AND status='done' AND design_id IN ({marks})", med).fetchone()[0] if med else 0
    proven = conn.execute(f"SELECT COUNT(*) FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase5' AND r.arm='B0' AND r.status='done' AND c.verdict='proven' AND r.design_id IN ({marks})", med).fetchone()[0] if med else 0
    expected = (proven / done_runs * unfinished) if done_runs else 0.0
    if since_drain_min is not None and since_drain_min >= 10.0:
        window_h = min(3.0, since_drain_min / 60.0)
        rate = count(window_h)["medium_b0"] / window_h
        basis = f"re-estimated over the {since_drain_min:.0f} min since the medium proofs drained at {drained_at} (DECISION 2026-09-19 (n) 3)"
    else:
        rate = h3["medium_b0"] / 3.0
        basis = ("medium proofs drained at " + drained_at + ", re-estimate at the next check" if drained_at else "last 3 h")
    eta_h = ((waiting + expected) / rate) if rate > 0 else None
    return {"h1": h1, "h3": h3, "rate_per_h": round(rate, 1), "rate_basis": basis, "open_medium_proofs": open_proofs, "proofs_drained_at": drained_at,
            "waiting": waiting, "expected": round(expected, 1), "unfinished_runs": unfinished, "eta_hours": (round(eta_h, 1) if eta_h is not None else None),
            "eta": (now + _dt.timedelta(hours=eta_h)).isoformat(timespec="minutes") if eta_h is not None else None}


def stage_b_proof_eta(cfg, conn):
    """DECISION 2026-09-19 (m) 1: the Stage B proof ETA under the current lane shares — the latest implied finish (remaining proof
    seat-hours / seats) over the medium lanes and the window (scripts/rebalance_lanes.remaining_seat_hours). -> hours from now or None."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("rebalance_lanes", os.path.join(os.path.dirname(os.path.abspath(__file__)), "rebalance_lanes.py"))
    RB = importlib.util.module_from_spec(spec); spec.loader.exec_module(RB)
    hours = RB.remaining_seat_hours(cfg, conn)
    lanes = (cfg["queue"].get("lanes") or {}).get("vcf") or {}
    cap = int(cfg["queue"].get("vcf_seats_target") or cfg["queue"].get("vcf_seats_max") or 50)
    lane_designs = {d for s in lanes.values() for d in (s.get("designs") or [])}
    fins, reserved = [], 0
    for n, s in lanes.items():
        if s.get("leftover"):
            continue
        share = int(s.get("share") or 0); reserved += share
        h = sum(((hours.get(d) or {}).get("hours") or 0.0) for d in (s.get("designs") or []))
        if h > 0 and share > 0:
            fins.append(h / share)
    rest = cap - reserved
    others = sum((v.get("hours") or 0.0) for d, v in hours.items() if d not in lane_designs and v.get("tier") == "medium")
    if others > 0 and rest > 0:
        fins.append(others / rest)
    return max(fins) if fins else None


def pool_progress_line(cfg, conn):
    import datetime as _dt
    pp = pool_progress(cfg, conn)
    sb = stage_b_proof_eta(cfg, conn)
    sb_txt = f"{(_dt.datetime.now() + _dt.timedelta(hours=sb)).isoformat(timespec='minutes')} ({sb:.1f} h)" if sb is not None else "unknown"
    verdict = ("" if pp["eta_hours"] is None or sb is None else
               (" — the B0 E4 ETA is LATER than the Stage B proof ETA: Stage B final waits for it (D3)" if pp["eta_hours"] > sb else " — the B0 E4 ETA is earlier than the Stage B proof ETA"))
    if pp.get("open_medium_proofs") == 0:
        sb_txt = f"drained ({pp.get('proofs_drained_at')})"
        verdict = ""
    return (f"offline pool (m 1 / n 3): E4 records last hour — medium B0 {pp['h1']['medium_b0']}, large B0 {pp['h1']['large_b0']}, other pool groups {pp['h1']['other']}; rate {pp['rate_per_h']}/h medium B0 ({pp['rate_basis']}); "
            f"medium B0 E4 waiting {pp['waiting']} (+ about {pp['expected']:.0f} from {pp['unfinished_runs']} medium B0 runs not done) -> ETA " + (f"{pp['eta']} ({pp['eta_hours']} h)" if pp["eta"] else "unknown (no throughput)")
            + f"; Stage B proof ETA {sb_txt}" + verdict)


def restart_daemon():
    import subprocess, time
    d = os.path.join(ROOT, "scripts", "queue", "daemon.py")
    subprocess.run([sys.executable, d, "stop"], check=False, capture_output=True); time.sleep(4)
    subprocess.Popen(["setsid", sys.executable, d, "start"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return True


def main(argv=None):
    dry = "--dry-run" in (argv or sys.argv[1:])
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    if "--slots" in (argv or sys.argv[1:]):
        for l in slot_report(cfg, conn, write=not dry, restart=None if dry else restart_daemon):
            print(l)
        return 0
    new, line, view = P5.completion_alert(cfg, conn, write=not dry)
    r = view["reachability"]
    if line:
        print(line)
        if not dry:
            print(post_slack(cfg, line))
    else:
        print(f"No new complete design ({len(view['complete'])} complete: " + (", ".join(view["complete"]) or "none") + f"; {len(view.get('preliminary') or [])} B0 pending: " + (", ".join(view.get("preliminary") or []) or "none")
              + f"; tally {r['wins']} wins, {r.get('ties', 0)} ties, {r.get('partial', 0)} partial, {r['lost']} lost, {r['undecided']} undecided; {r['wins_still_needed']} wins still needed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
