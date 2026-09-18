#!/usr/bin/env python3
"""Offline evaluation pool (DECISION 2026-09-18 item 1): sim + E4 only, no proofs, no LLM calls.

Scope (config `offline_pool`): (i) E4 for the proven B0 candidates of the large tier — the Y caliber never synthesized them at
E4 — recorded as visible E4 records with offline_eval = 1; (ii) V1 → lock-step testbench (V2, the `sim` job) → E4 for the
prescreened M candidates of the large tier, recorded with prescreened_offline = 1 (their proofs wait for a separate go);
(iii) only when `--include-e4-timeouts` (user's go): E4 again for the proven large-tier candidates whose visible E4 timed out.
Same E4 flow, constraints (Phi_main) and settings as the visible runs (`designs.jobs.dc_job`, config E4); candidates are
evaluated exactly as stored under results/candidates. Sims go to the local pool, E4 to the dc pool at priority
`offline_pool.priority` (1, below every search job) — idle DC seats only. At most `slots` offline jobs are in flight.
Auto-throttle: pause when the 1-minute load exceeds the baseline by more than `load_over_baseline` (10 %) or the medium-tier
VC Formal queue wait (q95 over the last hour) exceeds `vcf_wait_q95_max_min` (20 min); resume when both clear; every pause and
resume is logged (results/queue/offline_pool.log). State: results/queue/offline_pool_state.json (per candidate: group, stage, jobs).

    .venv/bin/python scripts/offline_pool.py plan [--include-e4-timeouts]          # scope counts and projected DC hours
    .venv/bin/python scripts/offline_pool.py start --baseline <load1> [--slots 8]  # detached loop
    .venv/bin/python scripts/offline_pool.py once | status | stop | report
"""
import argparse
import datetime
import json
import os
import signal
import subprocess
import sys
import time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402

PID = os.path.join(ROOT, "results", "queue", "offline_pool.pid")
LOG = os.path.join(ROOT, "results", "queue", "offline_pool.log")
STATE = os.path.join(ROOT, "results", "queue", "offline_pool_state.json")
LARGE = None   # filled from the plan


def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}\n")


def settings(cfg):
    o = dict(cfg.get("offline_pool") or {})
    o.setdefault("slots", 8); o.setdefault("priority", 1); o.setdefault("load_over_baseline", 0.10); o.setdefault("vcf_wait_q95_max_min", 20.0)
    o.setdefault("poll_sec", 60); o.setdefault("exp", "phase5"); o.setdefault("tier", "large"); o.setdefault("rerun_guard_sec", 3600)
    return o


def tier_of_design(cfg):
    sp = (cfg.get("exp5") or {}).get("starting_points") or {}
    return {d: t for t, ds in sp.items() for d in (ds or [])}


def load_state():
    try:
        return json.loads(open(STATE).read())
    except (OSError, ValueError):
        return {"cands": {}, "paused": False, "baseline": None, "started_at": None}


def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    os.replace(tmp, STATE)


# ----------------------------------------------------------------------------- scope
def scope(cfg, conn, include_e4_timeouts=False):
    """-> list of {cand_id, group, run_id, design_id, rtl_path, model, arm} for the candidates the pool evaluates (records that
    already exist are skipped)."""
    o = settings(cfg)
    tiers = tier_of_design(cfg)
    designs = [d for d, t in tiers.items() if t == o["tier"]]
    marks = ",".join("?" * len(designs))
    out = []
    # (i) proven B0 candidates without a visible E4 record
    for r in conn.execute(f"SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, r.llm_model, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          f"WHERE r.exp=? AND r.status!='superseded' AND r.arm='B0' AND c.verdict IN ('proven','proven_sim_only') AND c.design_id IN ({marks}) ORDER BY c.cand_id", (o["exp"], *designs)):
        if conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' LIMIT 1", (r["cand_id"],)).fetchone():
            continue
        out.append({"cand_id": r["cand_id"], "group": "b0_e4", "run_id": r["run_id"], "design_id": r["design_id"], "rtl_path": r["rtl_path"], "model": r["llm_model"], "arm": r["arm"]})
    # (ii) prescreened M candidates (every tier: the large tier's 636 and the 5 of the replaced thresholds run, item 1c): sim first, then E4
    for r in conn.execute(f"SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, r.llm_model, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          f"WHERE r.exp=? AND r.status!='superseded' AND COALESCE(c.prescreened,0)=1 ORDER BY c.cand_id", (o["exp"],)):
        if conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' LIMIT 1", (r["cand_id"],)).fetchone():
            continue
        out.append({"cand_id": r["cand_id"], "group": "prescreened", "run_id": r["run_id"], "design_id": r["design_id"], "rtl_path": r["rtl_path"], "model": r["llm_model"], "arm": r["arm"]})
    # (iii) proven candidates whose visible E4 failed (timeouts) — only on the user's go
    if include_e4_timeouts:
        for r in conn.execute(f"SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, r.llm_model, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                              f"WHERE r.exp=? AND r.status!='superseded' AND c.label IS NULL AND COALESCE(c.prescreened,0)=0 AND c.verdict IN ('proven','proven_sim_only') AND c.design_id IN ({marks}) ORDER BY c.cand_id", (o["exp"], *designs)):
            if conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' LIMIT 1", (r["cand_id"],)).fetchone():
                continue
            out.append({"cand_id": r["cand_id"], "group": "e4_timeout", "run_id": r["run_id"], "design_id": r["design_id"], "rtl_path": r["rtl_path"], "model": r["llm_model"], "arm": r["arm"]})
    return out


def e4_seconds(conn, design_id):
    r = conn.execute("SELECT AVG(dc_seconds) FROM evaluations WHERE design_id=? AND config='E4' AND status='ok' AND cand_id IS NOT NULL", (design_id,)).fetchone()
    return float(r[0] or 0.0)


def projection(cfg, conn, items):
    hours = {}
    for it in items:
        hours[it["group"]] = hours.get(it["group"], 0.0) + e4_seconds(conn, it["design_id"]) / 3600.0
    return hours


# ----------------------------------------------------------------------------- jobs
def eq_record_dir(cfg, conn, cand):
    """The candidate's equivalence record (the run's state file, as the hidden worker reads it) -> dir or None."""
    st = Path(C.ROOT) / "results" / "candidates" / cand["run_id"] / "state.json"
    if not st.exists():
        return None
    try:
        return ((json.loads(st.read_text()).get("cands") or {}).get(cand["cand_id"]) or {}).get("eq_record")
    except (OSError, ValueError):
        return None


def sim_payload(cfg, design, cand):
    from src.designs import catalog as K
    return {"design_id": cand["design_id"], "cand_id": cand["cand_id"], "d_rtl": [str(p) for p in K.abs_paths(design, design["files"])], "c_rtl": [cand["rtl_path"]],
            "top": design["top"], "clk": (design.get("clk_ports") or [None])[0], "rst": design.get("rst_port"), "rst_sense": design.get("rst_sense"),
            "sverilog": design.get("sverilog", False), "incdirs": [str(p) for p in K.abs_paths(design, design["incdirs"])],
            "note": f"offline pool (DECISION 2026-09-18 item 1) prescreened {cand['cand_id']}", "offline": True, "prescreened_offline": True, "offline_pool": True}


def e4_job(cfg, conn, design, cand, saif=None):
    from src.designs import jobs as J
    from src.designs import catalog as K
    o = settings(cfg)
    phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (cand["design_id"],)).fetchone()[0]
    j = J.dc_job(cfg, design, "E4", float(phi), int(o["priority"]))
    j["payload"].update(rtl=[cand["rtl_path"]], incdirs=[str(p) for p in K.abs_paths(design, design["incdirs"])], is_baseline=0, cand_id=cand["cand_id"], offline_pool=True)
    if cand["group"] == "prescreened":
        j["payload"]["prescreened_offline"] = 1
    elif cand["group"] == "e4_timeout":   # DECISION 2026-09-18 (b) item 4: the re-run gets a 3600 s dc_shell guard and the e4_rerun flag
        j["payload"]["e4_rerun"] = 1
        j["payload"]["force_rerun"] = True   # the failed record of the same inputs is cached; the re-run gets its own directory
        j["timeout_sec"] = int(o.get("rerun_guard_sec", 3600)) + 180
    else:
        j["payload"]["offline_eval"] = 1
    if saif and Path(saif).exists():
        j["payload"].update(saif=saif, saif_instance="bs_lockstep/u_c")
    return j


def sim_record(cfg, payload):
    from src.equiv.run_equiv import equiv_extra, equiv_hash
    try:
        h = equiv_hash(payload["d_rtl"], payload["c_rtl"], payload["top"], cfg, equiv_extra(cfg, payload, False))
    except OSError:
        return None
    root = Path(C.results_dir(cfg)) / "raw" / payload["design_id"] / "EQ"
    for eq in sorted(root.glob(f"{h}*/equiv.json")):
        try:
            return json.loads(eq.read_text())
        except (OSError, ValueError):
            continue
    return None


# ----------------------------------------------------------------------------- throttle
def load1():
    return float(open("/proc/loadavg").read().split()[0])


def medium_vcf_wait_q95(cfg, conn, hours=1.0):
    tiers = tier_of_design(cfg)
    lo = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat(timespec="seconds")
    w = sorted((x or 0) / 60.0 for d, x in conn.execute("SELECT design_id, strftime('%s', started_at) - strftime('%s', submitted_at) FROM jobs WHERE pool='vcf' AND started_at > ?", (lo,)) if tiers.get(d) == "medium")
    return w[min(len(w) - 1, max(0, int(0.95 * len(w)) - 1))] if w else 0.0


def throttle(cfg, conn, st):
    o = settings(cfg)
    l1, q95 = load1(), medium_vcf_wait_q95(cfg, conn)
    base = st.get("baseline") or l1
    over = l1 > base * (1.0 + float(o["load_over_baseline"]))   # DECISION 2026-09-18 (b) item 3: load only (the pool submits no proofs; q95 is logged, not applied)
    if over and not st.get("paused"):
        st["paused"] = True; log(f"PAUSE load1 {l1:.0f} (baseline {base:.0f}), medium VC Formal wait q95 {q95:.1f} min")
    elif not over and st.get("paused"):
        st["paused"] = False; log(f"RESUME load1 {l1:.0f} (baseline {base:.0f}), medium VC Formal wait q95 {q95:.1f} min")
    return not st["paused"], l1, q95


# ----------------------------------------------------------------------------- one pass
def once(cfg, conn, st, include_e4_timeouts=False, queue=None):
    from src.designs import catalog as K
    from src.jobqueue.core import Queue
    o = settings(cfg)
    q = queue or Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    designs = {d["design_id"]: d for d in K.load_all()}
    cands = st.setdefault("cands", {})
    for it in scope(cfg, conn, include_e4_timeouts):
        cands.setdefault(it["cand_id"], {**it, "stage": "sim" if it["group"] == "prescreened" else "e4", "sim_job": None, "e4_job": None, "result": None})
    # progress of submitted jobs
    for cid, c in cands.items():
        if c["stage"] == "sim_running":
            js = q.get(c["sim_job"])
            if js and js["state"] in ("done", "failed"):
                rec = sim_record(cfg, c["sim_payload"])
                if rec is None:
                    c.update(stage="done", result="sim job failed (no record)")
                elif rec.get("verdict") == "not_run" or rec.get("verdict") in ("proven_sim_only",):
                    c.update(stage="e4", sim_result=rec.get("v2_status"), saif=rec.get("saif_c"))
                else:
                    c.update(stage="done", result=f"{rec.get('verdict')} ({rec.get('v1_status')}/{rec.get('v2_status')})", sim_result=rec.get("verdict"))
        elif c["stage"] == "e4_running":
            js = q.get(c["e4_job"])
            if js and js["state"] in ("done", "failed"):
                ev = conn.execute("SELECT status, dc_seconds, raw_dir FROM evaluations WHERE cand_id=? AND config='E4' ORDER BY eval_id DESC LIMIT 1", (cid,)).fetchone()
                c.update(stage="done", result=f"E4 {ev['status']}" if ev else f"E4 job {js['state']}", dc_seconds=(ev["dc_seconds"] if ev else None))
                if ev and ev["raw_dir"]:   # the same tiered retention as the visible runs: full artifacts for accepted / audit candidates, the parsed record and reports otherwise
                    try:
                        from src.eval import retention as RET
                        row = conn.execute("SELECT accepted, in_archive FROM candidates WHERE cand_id=?", (cid,)).fetchone()
                        res = RET.slim_candidate(cfg, cid, bool(row and (row[0] or row[1])), fit_dirs=[ev["raw_dir"]])
                        c["slimmed"] = {"kept_full": res["kept_full"], "bytes": sum(res["freed"].values())}
                    except Exception as e:   # retention must never stop the pool
                        c["slimmed"] = f"failed: {type(e).__name__}: {e}"[:120]
    ok, l1, q95 = throttle(cfg, conn, st)
    submitted = 0
    if ok:
        inflight = sum(1 for c in cands.values() if c["stage"] in ("sim_running", "e4_running"))
        for cid, c in cands.items():
            if inflight + submitted >= int(o["slots"]):
                break
            d = designs.get(c["design_id"])
            if d is None:
                c.update(stage="done", result="design not in the catalog"); continue
            if c["stage"] == "sim":
                pl = sim_payload(cfg, d, c)
                jid = q.submit("sim", pl, design_id=c["design_id"], cand_id=cid, config="EQ", priority=int(o["priority"]), timeout_sec=int(cfg["timeouts"]["sim"]) * 60 + 300)
                c.update(stage="sim_running", sim_job=jid, sim_payload=pl); submitted += 1
            elif c["stage"] == "e4":
                saif = c.get("saif")
                if saif is None and c["group"] != "prescreened":
                    rd = eq_record_dir(cfg, conn, c)
                    if rd and (Path(rd) / "equiv.json").exists():
                        try:
                            saif = json.loads((Path(rd) / "equiv.json").read_text()).get("saif_c")
                        except (OSError, ValueError):
                            saif = None
                j = e4_job(cfg, conn, d, c, saif=saif)
                jid = q.submit(j["kind"], j["payload"], design_id=c["design_id"], cand_id=cid, config="E4", priority=j["priority"], timeout_sec=j["timeout_sec"])
                c.update(stage="e4_running", e4_job=jid); submitted += 1
    counts = {}
    for c in cands.values():
        counts[c["stage"]] = counts.get(c["stage"], 0) + 1
    log(f"pass: load1 {l1:.0f} q95 {q95:.1f} min {'paused' if st.get('paused') else 'active'}; submitted {submitted}; stages {counts}")
    save_state(st)
    return counts


def loop(cfg, baseline, include_e4_timeouts):
    with open(PID, "w") as f:
        f.write(str(os.getpid()))
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda s, f: stop.__setitem__("flag", True))
    st = load_state()
    if baseline is not None:
        st["baseline"] = float(baseline)
    st.setdefault("started_at", datetime.datetime.now().isoformat(timespec="seconds"))
    conn = db.connect(cfg=cfg)
    log(f"offline pool started pid {os.getpid()} baseline {st.get('baseline')} slots {settings(cfg)['slots']} e4_timeouts {include_e4_timeouts}")
    while not stop["flag"]:
        try:
            counts = once(cfg, conn, st, include_e4_timeouts)
            if counts and all(k == "done" for k in counts):
                log("every candidate of the scope is done; the pool stops"); break
        except Exception as e:   # the loop must go on
            log(f"pass failed: {type(e).__name__}: {e}")
        for _ in range(int(settings(cfg)["poll_sec"])):
            if stop["flag"]:
                break
            time.sleep(1)
    log("offline pool stopped")
    try:
        os.remove(PID)
    except OSError:
        pass


def running():
    try:
        pid = int(open(PID).read().strip()); os.kill(pid, 0); return pid
    except (OSError, ValueError):
        return None


# ----------------------------------------------------------------------------- report (item 1e)
def report(cfg, conn):
    from src.analysis import phase5 as P5
    from src.diagnose import m3
    from src.search.driver import record_from_row
    st = load_state()
    cands = st.get("cands", {})
    designs = P5._Designs(cfg, conn)
    L = ["# Offline pool report (DECISION 2026-09-18 item 1)", "", f"Generated {datetime.datetime.now().isoformat(timespec='minutes')}; state {STATE}; baseline load {st.get('baseline')}; started {st.get('started_at')}.", ""]
    L += ["## B0: rule-A labels of the proven large-tier candidates at E4 (offline_eval = 1); the hidden-configuration certification of these candidates is sealed until the Phase 5 completion marker", "",
          "| design | proven B0 candidates | E4 records | retained | tradeoff | absorbed_identical | absorbed | noise | harmful | pending |", "|---|---|---|---|---|---|---|---|---|---|"]
    tiers = tier_of_design(cfg)
    for d in sorted(x for x, t in tiers.items() if t == settings(cfg)["tier"]):
        rows = conn.execute("SELECT c.* FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase5' AND r.status!='superseded' AND r.arm='B0' AND c.design_id=? AND c.verdict IN ('proven','proven_sim_only')", (d,)).fetchall()
        labels = {}; n_e4 = 0
        for c in rows:
            u = P5.uniform_diagnosis(designs, conn, dict(c))
            if u is None:
                labels["pending"] = labels.get("pending", 0) + 1; continue
            n_e4 += 1; labels[u[0]] = labels.get(u[0], 0) + 1
        L.append(f"| {d} | {len(rows)} | {n_e4} | " + " | ".join(str(labels.get(k, 0)) if k != 'pending' else str(labels.get('pending', 0)) for k in ("retained", "tradeoff", "absorbed_identical", "absorbed", "noise", "harmful", "pending")) + " |")
    L += ["", "## Prescreened M candidates (prescreened_offline = 1): sim outcome and the provisional E4 label (no proof: every label is provisional)", "",
          "| model | design | candidates | failed V1 | failed testbench / V2 | E4 done | E4 pending | retained | tradeoff | absorbed_identical | absorbed | noise | harmful | provisionally retained or tradeoff |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    by = {}
    for cid, c in cands.items():
        if c["group"] != "prescreened":
            continue
        k = (c["model"], c["design_id"]); b = by.setdefault(k, {"n": 0, "v1": 0, "v2": 0, "e4": 0, "pending": 0, "labels": {}})
        b["n"] += 1
        sr = str(c.get("sim_result") or c.get("result") or "")
        if sr.startswith("rejected"): b["v1"] += 1
        elif sr.startswith("sim_fail") or sr.startswith("error"): b["v2"] += 1
        ev = conn.execute("SELECT * FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (cid,)).fetchone()
        if ev is None:
            if not (sr.startswith("rejected") or sr.startswith("sim_fail") or sr.startswith("error")):
                b["pending"] += 1
            continue
        b["e4"] += 1
        dd = designs.get(c["design_id"])
        if dd and dd["base"] and dd["phi"] is not None:
            out = m3.diagnose(dd["base"], record_from_row(ev), dd["sigma"], dd["phi"], v3_status="proven", k_sigma=designs.k_sigma, thresholds=dd["thresholds"], floor_class=dd["floor_class"])
            lab = out.get("label"); b["labels"][lab] = b["labels"].get(lab, 0) + 1
    for (m, d), b in sorted(by.items()):
        lb = b["labels"]
        L.append(f"| {m} | {d} | {b['n']} | {b['v1']} | {b['v2']} | {b['e4']} | {b['pending']} | " + " | ".join(str(lb.get(k, 0)) for k in ("retained", "tradeoff", "absorbed_identical", "absorbed", "noise", "harmful")) + f" | {lb.get('retained', 0) + lb.get('tradeoff', 0)} |")
    hours = {}
    for cid, c in cands.items():
        ev = conn.execute("SELECT dc_seconds FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' AND (offline_eval=1 OR prescreened_offline=1) ORDER BY eval_id DESC LIMIT 1", (cid,)).fetchone()
        if ev and ev[0]:
            hours[c["group"]] = hours.get(c["group"], 0.0) + float(ev[0]) / 3600.0
    L += ["", f"DC hours actually used by the offline E4 runs so far: { {k: round(v, 1) for k, v in hours.items()} } (projection at planning time in the offline pool log).", ""]
    text = "\n".join(L)
    out = Path(C.ROOT) / "reports" / "phase5_offline_pool.md"
    out.write_text(text)
    print(text)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["plan", "start", "once", "status", "stop", "report", "_run"])
    ap.add_argument("--baseline", type=float, default=None)
    ap.add_argument("--slots", type=int, default=None)
    ap.add_argument("--include-e4-timeouts", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    if a.slots:
        cfg.setdefault("offline_pool", {})["slots"] = a.slots
    conn = db.connect(cfg=cfg)
    if a.what == "plan":
        items = scope(cfg, conn, a.include_e4_timeouts)
        by = {}
        for it in items:
            by[it["group"]] = by.get(it["group"], 0) + 1
        proj = projection(cfg, conn, items)
        print(json.dumps({"candidates": by, "projected_e4_hours": {k: round(v, 1) for k, v in proj.items()}, "slots": settings(cfg)["slots"], "priority": settings(cfg)["priority"]}, indent=1))
        log(f"plan: {by}, projected E4 hours {dict((k, round(v, 1)) for k, v in proj.items())}")
        return 0
    if a.what == "_run":
        loop(cfg, a.baseline, a.include_e4_timeouts); return 0
    if a.what == "start":
        if running():
            print(f"offline pool already running pid {running()}"); return 0
        args = [sys.executable, os.path.abspath(__file__), "_run"] + (["--baseline", str(a.baseline)] if a.baseline is not None else []) + (["--slots", str(a.slots)] if a.slots else []) + (["--include-e4-timeouts"] if a.include_e4_timeouts else [])
        p = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
        time.sleep(1.5); print(f"offline pool started pid {p.pid}; log {LOG}"); return 0
    if a.what == "once":
        st = load_state()
        if a.baseline is not None:
            st["baseline"] = a.baseline
        print(json.dumps(once(cfg, conn, st, a.include_e4_timeouts))); return 0
    if a.what == "status":
        st = load_state(); counts = {}
        for c in st.get("cands", {}).values():
            counts[c["stage"]] = counts.get(c["stage"], 0) + 1
        print(f"offline pool: {'running pid %d' % running() if running() else 'not running'}; paused {st.get('paused')}; baseline {st.get('baseline')}; stages {counts}")
        return 0
    if a.what == "stop":
        pid = running()
        if pid:
            os.kill(pid, signal.SIGTERM); print(f"stop sent to {pid}")
        else:
            print("not running")
        return 0
    if a.what == "report":
        return report(cfg, conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
