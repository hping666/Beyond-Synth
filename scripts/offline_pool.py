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
import shutil
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
    o.setdefault("slots_when_idle", 12); o.setdefault("idle_dc_seats_for_extra", 12)
    o.setdefault("b0_tier_order", ["medium", "small", "large"])   # DECISION 2026-09-19 (m) 1 / (q) 1
    o.setdefault("group_order", ["resim", "b0_e4:medium", "b0_e4:small", "b0_e4:large", "e4_timeout", "e4_late", "prescreened", "reverify", "reproof"])
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
def scope(cfg, conn, include_e4_timeouts=True):
    """-> the candidates the pool evaluates, in the pool's order — DECISION 2026-09-19 (m) 1: medium-tier B0 E4 first, then the proven
    candidates of finished runs without an E4 record on every tier (an E4 that failed or timed out: group `e4_timeout`, re-run with
    the long guard and the e4_rerun flag; an E4 never submitted: group `e4_late`), then large-tier B0 E4, prescreened sims and the
    rest (config offline_pool.group_order with keys "group" or "group:tier"; within a group medium, large, small). Records that
    already exist are skipped. Other groups: resim ((m) 2: the sim jobs that crashed on the 2026-09-18 10:41 edit, marker
    "[resim pending" on the candidate — sim, then E4 and the proof in parallel, at the run pipeline's priorities), prescreened,
    reverify ((d) D2), reproof. `include_e4_timeouts` is kept for the callers; the retry group is always in scope ((m) 3: every
    proven candidate gets an E4 record or a retry regardless of its run's state)."""
    o = settings(cfg)
    tiers = tier_of_design(cfg)
    tier_rank = {t: i for i, t in enumerate(o["b0_tier_order"])}
    out = []

    def has_ok_e4(cid):
        return conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' LIMIT 1", (cid,)).fetchone() is not None

    def item(r, group, **extra):
        return {"cand_id": r["cand_id"], "group": group, "run_id": r["run_id"], "design_id": r["design_id"], "rtl_path": r["rtl_path"], "model": r["llm_model"], "arm": r["arm"],
                "tier": tiers.get(r["design_id"], "?"), **extra}
    # (m) 2: re-simulation of the crashed sim jobs (marker on the candidate; the failed job's payload is reused)
    for r in conn.execute(f"SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, r.llm_model, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          f"WHERE r.exp=? AND c.note LIKE '%[resim pending%' AND c.verdict IS NULL ORDER BY c.cand_id", (o["exp"],)):
        j = conn.execute("SELECT payload_json FROM jobs WHERE kind='sim' AND cand_id=? AND state='failed' ORDER BY finished_at DESC LIMIT 1", (r["cand_id"],)).fetchone()
        if j is None:
            continue
        out.append(item(r, "resim", sim_payload_src=json.loads(j["payload_json"])))
    # (i) proven B0 candidates without a visible E4 record — DECISION 2026-09-18 (d) B5: every tier, continuously as runs finish;
    #     a candidate of a superseded run is not evaluated here (D2 covers those)
    for r in conn.execute(f"SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, r.llm_model, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          f"WHERE r.exp=? AND r.status='done' AND r.arm='B0' AND c.verdict IN ('proven','proven_sim_only') AND c.e4_failure IS NULL ORDER BY c.cand_id", (o["exp"],)):
        if has_ok_e4(r["cand_id"]):
            continue
        if conn.execute("SELECT COUNT(*) FROM evaluations WHERE cand_id=? AND config='E4' AND status != 'ok'", (r["cand_id"],)).fetchone()[0] >= int(o.get("e4_max_attempts", 3)):
            continue
        out.append(item(r, "b0_e4"))
    # (m) 3: proven candidates of finished runs, any arm but B0, not prescreened, not identical-text / duplicate / aborted, without an ok E4 record:
    #     an E4 that was tried (an evaluation record of any status or a DC job) is retried with the long guard; one never submitted is run
    for r in conn.execute(f"SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, r.llm_model, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          f"WHERE r.exp=? AND r.status='done' AND r.arm!='B0' AND COALESCE(c.prescreened,0)=0 AND c.verdict='proven' AND c.e4_failure IS NULL "
                          f"AND COALESCE(c.label,'') NOT IN ('duplicate','aborted','absorbed_identical') ORDER BY c.cand_id", (o["exp"],)):   # (n) 1: a terminal DC rejection is not retried
        if has_ok_e4(r["cand_id"]):
            continue
        if conn.execute("SELECT COUNT(*) FROM evaluations WHERE cand_id=? AND config='E4' AND status != 'ok'", (r["cand_id"],)).fetchone()[0] >= int(o.get("e4_max_attempts", 3)):
            continue   # retries exhausted: reported as such, an operator decision
        tried = conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config='E4' LIMIT 1", (r["cand_id"],)).fetchone() or \
            conn.execute("SELECT 1 FROM jobs WHERE cand_id=? AND pool='dc' LIMIT 1", (r["cand_id"],)).fetchone()
        out.append(item(r, "e4_timeout" if tried else "e4_late"))
    # REQUEST 2026-09-20 (e) item 2 (PLAN 6.10): D's SAIF-basis E4 baseline for the designs whose evaluator baseline carries no SAIF power —
    #     one D-vs-D lock-step simulation (V1 + V2 under the deterministic stimulus) -> D's SAIF -> one E4 run of D at Φ_main with SAIF
    #     power, stored with offline_baseline = 1 and is_baseline = 0 (never read by the running evaluators; uniform_diagnosis reads it on request)
    if o.get("d_saif_baselines"):
        for did in d_saif_designs(cfg, conn):
            out.append({"cand_id": f"d_saif:{did}", "group": "d_saif", "run_id": None, "design_id": did, "rtl_path": None, "model": None, "arm": None, "tier": tiers.get(did, "?")})
    # (ii) prescreened M candidates (every tier: the large tier's 636 and the 5 of the replaced thresholds run, item 1c): sim first, then E4
    for r in conn.execute(f"SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, r.llm_model, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          f"WHERE r.exp=? AND (r.status!='superseded' OR r.superseded_reason='harness_fix') AND COALESCE(c.prescreened,0)=1 ORDER BY c.cand_id", (o["exp"],)):   # (d) D2: LSTM's prescreened candidates stay in scope after the supersession
        if has_ok_e4(r["cand_id"]):
            continue
        out.append(item(r, "prescreened"))
    # REQUEST 2026-09-20 (e) item 3 (PLAN 6.9): the pooled-floor designs' text-level perturbations (and P0 on the listed designs) —
    #     a SEQ proof under harness_version 2 for every entry not proven, E4 at Φ_main for every proven entry without an ok E4 record;
    #     only once the pool's proofs are open (after the small tier's search runs)
    if o.get("floor6_enabled") and o.get("proofs_enabled"):
        out += floor6_items(cfg, conn, o, tiers)
    # (iv) DECISION 2026-09-18 (d) D2: the stored candidates of the runs superseded by the harness fix — simulation and E4 now under the
    #      corrected harness (simple_spi with force_rerun: its record hash did not change), the proof only when the pool's proofs are enabled
    force = set(o.get("reverify_force_rerun") or [])
    for r in conn.execute(f"SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, r.llm_model, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          f"WHERE r.exp=? AND r.superseded_reason='harness_fix' AND COALESCE(c.prescreened,0)=0 AND COALESCE(c.label,'') NOT IN ('duplicate','aborted') "
                          f"AND c.rtl_path IS NOT NULL ORDER BY c.design_id, c.cand_id", (o["exp"],)):
        out.append(item(r, "reverify", force_rerun=r["design_id"] in force))
    # (v) 2026-09-18 11:2x: candidates whose proof job failed for an operator cause (a transient syntax error in seq_tcl.py, 10:41) — marked
    #     "[reproof pending" in their note; the proof is resubmitted from the failed job's payload, then E4 on proven (this group is not gated by proofs_enabled)
    for r in conn.execute(f"SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, r.llm_model, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          f"WHERE r.exp=? AND c.note LIKE '%[reproof pending%' AND c.verdict='error' ORDER BY c.cand_id", (o["exp"],)):
        j = conn.execute("SELECT payload_json FROM jobs WHERE kind='vcf' AND cand_id=? AND state='failed' ORDER BY finished_at DESC LIMIT 1", (r["cand_id"],)).fetchone()
        if j is None:
            continue
        out.append(item(r, "reproof", proof_payload=json.loads(j["payload_json"])))
    order = list(o["group_order"])

    def key(it):
        g, tr = it["group"], it.get("tier", "?")
        idx = order.index(f"{g}:{tr}") if f"{g}:{tr}" in order else (order.index(g) if g in order else len(order))
        return (idx, tier_rank.get(tr, 9), it["cand_id"])
    out.sort(key=key)
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
            "note": (f"offline pool (DECISION 2026-09-18 (d) D2) re-verification {cand['cand_id']}" if cand.get("group") == "reverify" else f"offline pool (DECISION 2026-09-18 item 1) prescreened {cand['cand_id']}"),
            "offline": True, "prescreened_offline": cand.get("group") != "reverify", "offline_pool": True, "reverify": cand.get("group") == "reverify", "force_rerun": bool(cand.get("force_rerun"))}


def d_saif_designs(cfg, conn):
    """REQUEST 2026-09-20 (e) item 2: the Phase 5 designs whose evaluator baseline has no SAIF power (src.analysis.phase5
    default_power_basis_designs) and that have no ok offline SAIF baseline record yet."""
    from src.analysis import phase5 as P5
    out = []
    for did in P5.default_power_basis_designs(cfg, conn):
        if conn.execute("SELECT 1 FROM evaluations WHERE design_id=? AND config='E4' AND offline_baseline=1 AND status='ok' AND power_saif_mw IS NOT NULL LIMIT 1", (did,)).fetchone():
            continue
        out.append(did)
    return out


def d_saif_sim_payload(cfg, design):
    """The D-vs-D lock-step simulation (kind sim: V1 + V2 only) whose record carries D's SAIF (saif_d, instance bs_lockstep/u_d)."""
    from src.designs import catalog as K
    d_rtl = [str(p) for p in K.abs_paths(design, design["files"])]
    return {"design_id": design["design_id"], "cand_id": None, "d_rtl": d_rtl, "c_rtl": list(d_rtl), "top": design["top"], "clk": (design.get("clk_ports") or [None])[0],
            "rst": design.get("rst_port"), "rst_sense": design.get("rst_sense"), "sverilog": design.get("sverilog", False), "incdirs": [str(p) for p in K.abs_paths(design, design["incdirs"])],
            "note": f"offline pool (REQUEST 2026-09-20 (e) 2, PLAN 6.10): D-vs-D lock-step simulation of {design['design_id']} for D's SAIF", "offline": True, "offline_pool": True, "d_saif": True}


def register_d_saif(cfg, design_id, rec):
    """The D-vs-D record's SAIF of D copied to data/perturbations/<design_id>/saif/D.saif and registered in saif.json as the design's
    SAIF (status d_vs_d): the input of D's SAIF-basis E4 record and of the phase6 floor runs (PLAN 6.9 / 6.10). -> path or None."""
    from src.noise import generate as G
    src_path = rec.get("saif_d")
    if not src_path or not Path(src_path).exists() or Path(src_path).stat().st_size == 0:
        return None
    out = Path(G.PERT_DIR) / design_id / "saif"
    out.mkdir(parents=True, exist_ok=True)
    dst = out / "D.saif"
    shutil.copyfile(src_path, dst)
    sj = out.parent / "saif.json"
    try:
        s = json.loads(sj.read_text()) if sj.exists() else None
    except (OSError, ValueError):
        s = None
    s = s or {"design_id": design_id, "design": None, "perturbations": {}, "missing": []}
    s["design"] = {"saif": str(dst), "instance": "bs_lockstep/u_d", "source_record": rec.get("raw_dir"), "status": "d_vs_d"}
    s["missing"] = [m for m in (s.get("missing") or []) if m != "design"]
    sj.write_text(json.dumps(s, indent=1, sort_keys=True) + "\n")
    return str(dst)


def d_saif_e4_job(cfg, conn, design, saif):
    """E4 of D at Φ_main with D's SAIF: an additional baseline record flagged offline_baseline = 1; is_baseline stays 0 so that no
    evaluator query (is_baseline = 1) can pick it up (REQUEST 2026-09-20 (e) item 2)."""
    from src.designs import jobs as J
    o = settings(cfg)
    phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (design["design_id"],)).fetchone()[0]
    j = J.dc_job(cfg, design, "E4", float(phi), int(o["priority"]))
    j["payload"].update(is_baseline=0, offline_baseline=1, offline_pool=True, saif=str(saif), saif_instance="bs_lockstep/u_d")
    return j


def floor6_items(cfg, conn, o, tiers):
    """REQUEST 2026-09-20 (e) item 3 (PLAN 6.9): for every pooled-floor design of the frozen table (src.analysis.phase5
    pooled_floor_designs) the manifest's text-level perturbations (P1_text, P2_text; no Pyverilog dependency) and, on the designs of
    offline_pool.floor6_p0_designs, the P0 round trip: entries not proven get a SEQ proof under the current harness (harness_version 2:
    its own record hash), proven entries without an ok E4 record at Φ_main get the E4 run. Nothing here waits for a proven P0."""
    from src.analysis import phase5 as P5
    from src.designs import catalog as K
    from src.noise import gate as GT
    out = []
    p0_designs = set(o.get("floor6_p0_designs") or [])
    catalog = {d["design_id"]: d for d in K.load_all()}
    for did in P5.pooled_floor_designs(cfg, conn):
        m = GT.manifest_of(did)
        design = catalog.get(did)
        if not m or design is None:
            continue
        phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (did,)).fetchone()
        if not phi or phi[0] is None:
            continue
        entries = [dict(e) for e in (m.get("perturbations") or []) if e.get("ptype") in ("P1_text", "P2_text")]
        if did in p0_designs and m.get("roundtrip"):
            entries.append({"pert_id": m["roundtrip"]["pert_id"], "path": m["roundtrip"]["path"], "ptype": "P0_roundtrip"})
        for e in entries:
            row = conn.execute("SELECT seq_status FROM perturbations WHERE pert_id=?", (e["pert_id"],)).fetchone()
            status = row["seq_status"] if row else None
            paths = [str(Path(C.ROOT) / pth) for pth in (e.get("paths") or [e["path"]])]
            if status in ("proven", "proven_rename"):
                if conn.execute("SELECT 1 FROM evaluations WHERE pert_id=? AND config='E4' AND status='ok' AND abs(clock_ns-?)<1e-6 LIMIT 1", (e["pert_id"], float(phi[0]))).fetchone():
                    continue
                stage = "e4"
            else:   # a record under the current harness (its own hash) decides: falsified / rejected / sim_fail is final, proven goes to E4, none -> proof
                rec = proof_record(cfg, floor6_proof_payload(cfg, design, {"pert_id": e["pert_id"], "paths": paths, "ptype": e["ptype"]}))
                if rec and rec.get("verdict") in ("falsified", "rejected", "sim_fail"):
                    continue
                stage = "e4" if rec and rec.get("verdict") == "proven" else "proof"
            out.append({"cand_id": f"floor6:{e['pert_id']}", "group": "floor6", "run_id": None, "design_id": did, "rtl_path": None, "model": None, "arm": None, "tier": tiers.get(did, "?"),
                        "pert_id": e["pert_id"], "ptype": e["ptype"], "paths": paths, "start_stage": stage, "seq_status_at_scope": status})
    return out


def floor6_proof_payload(cfg, design, cand):
    """The gate's vcf payload (src/noise/gate.gate_jobs) for one perturbation entry: the perturbation is the candidate side."""
    from src.designs import catalog as K
    return {"design_id": design["design_id"], "d_rtl": [str(p) for p in K.abs_paths(design, design["files"])], "top": design["top"],
            "clk": (design.get("clk_ports") or [None])[0], "rst": design.get("rst_port"), "rst_sense": design.get("rst_sense"), "sverilog": bool(design.get("sverilog", False)),
            "incdirs": [str(p) for p in K.abs_paths(design, design["incdirs"])], "cand_id": cand["pert_id"], "c_rtl": list(cand["paths"]),
            "note": f"perturbation {cand['ptype']} (offline pool floor6, REQUEST 2026-09-20 (e) 3 / PLAN 6.9)", "offline_pool": True, "floor6": True}


def floor6_e4_job(cfg, conn, design, cand, saif=None):
    """E4 of one proven perturbation at Φ_main (evaluations.pert_id set, is_baseline 0), with the record's SAIF of the candidate side
    when it exists — as scripts/phase2_noise.py cmd_submit builds the noise jobs."""
    from src.designs import jobs as J
    from src.designs import catalog as K
    o = settings(cfg)
    phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (design["design_id"],)).fetchone()[0]
    j = J.dc_job(cfg, design, "E4", float(phi), int(o["priority"]))
    j["payload"].update(rtl=list(cand["paths"]), incdirs=[str(p) for p in K.abs_paths(design, design["incdirs"])], is_baseline=0, pert_id=cand["pert_id"], offline_pool=True)
    if saif and Path(saif).exists():
        j["payload"].update(saif=str(saif), saif_instance="bs_lockstep/u_c")
    return j


def floor6_record_saif(cfg, design_id, pert_id):
    """The SAIF of the candidate side of the perturbation's latest equivalence record (saif_c), or None."""
    raw = Path(C.results_dir(cfg)) / "raw" / design_id / "EQ"
    best = None
    for eq in raw.glob("*/equiv.json"):
        try:
            rec = json.loads(eq.read_text())
        except (OSError, ValueError):
            continue
        if rec.get("cand_id") == pert_id and rec.get("saif_c") and (best is None or eq.stat().st_mtime > best[0]):
            best = (eq.stat().st_mtime, rec["saif_c"])
    return best[1] if best and Path(best[1]).exists() else None


def e4_job(cfg, conn, design, cand, saif=None):
    from src.designs import jobs as J
    from src.designs import catalog as K
    o = settings(cfg)
    phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (cand["design_id"],)).fetchone()[0]
    pri = int(cfg["search"].get("job_priority", 4)) if cand.get("group") == "resim" else int(o["priority"])   # (m) 2: the run pipeline's priority
    j = J.dc_job(cfg, design, "E4", float(phi), pri)
    j["payload"].update(rtl=[cand["rtl_path"]], incdirs=[str(p) for p in K.abs_paths(design, design["incdirs"])], is_baseline=0, cand_id=cand["cand_id"], offline_pool=True)
    if cand["group"] == "prescreened":
        j["payload"]["prescreened_offline"] = 1
    elif cand["group"] == "reverify":   # DECISION 2026-09-18 (d) D2: the C1-map record of a superseded run's candidate
        j["payload"]["offline_eval"] = 1
        j["payload"]["reverify"] = 1
    elif cand["group"] == "reproof":    # the run's own fitness record, made by the pool because the run's proof job failed on an operator edit
        j["payload"]["reproof"] = 1
    elif cand["group"] == "resim":      # DECISION 2026-09-19 (m) 2: the run's own fitness record, made by the pool after the re-simulation
        j["payload"]["resim"] = 1
    elif cand["group"] in ("e4_timeout", "e4_late"):   # DECISION 2026-09-18 (b) item 4 / 2026-09-19 (m) 3: the re-run gets a 3600 s dc_shell guard and the e4_rerun flag
        j["payload"]["e4_rerun"] = 1
        j["payload"]["force_rerun"] = True   # the failed record of the same inputs is cached; the re-run gets its own directory
        j["timeout_sec"] = int(o.get("rerun_guard_sec", 3600)) + 180
    else:
        j["payload"]["offline_eval"] = 1
    if saif and Path(saif).exists():
        j["payload"].update(saif=saif, saif_instance="bs_lockstep/u_c")
    return j


def sync_candidate_row(conn, cand_id, rec, sim_job):
    """The offline simulation's outcome written into the prescreened candidate's row the way the search would have (DECISION
    2026-09-18 D2: the row shows V1 / V2 and, on a failure, the verdict; a passed simulation leaves the verdict NULL — the
    proof is reported as pending until it is run). Idempotent: rows that already carry a V2 status are left alone."""
    row = conn.execute("SELECT v2_status, verdict FROM candidates WHERE cand_id=?", (cand_id,)).fetchone()
    if row is None or row["v2_status"] is not None or row["verdict"] is not None:
        return False
    passed = rec.get("verdict") in ("not_run", "proven_sim_only")
    verdict = None if passed else rec.get("verdict")
    note = (f" [offline sim {time.strftime('%Y-%m-%d')}: V1 {rec.get('v1_status')}, V2 {rec.get('v2_status')}; proof pending (DECISION 2026-09-18 D2)]" if passed
            else f" [offline sim {time.strftime('%Y-%m-%d')}: {rec.get('verdict')} (V1 {rec.get('v1_status')} / V2 {rec.get('v2_status')})]")
    conn.execute("UPDATE candidates SET v1_status=?, v2_status=?, v2_cycles=?, verdict=?, eq_job_id=COALESCE(eq_job_id, ?), note=COALESCE(note, '') || ? WHERE cand_id=?",
                 (rec.get("v1_status"), rec.get("v2_status"), rec.get("v2_cycles"), verdict, sim_job, note, cand_id))
    return True


def proof_record(cfg, payload):
    """The proof record of a `vcf` job payload (the split pipeline's V3 stage: a sim_record payload) -> dict or None."""
    from src.equiv.run_equiv import equiv_extra, equiv_hash
    try:
        h = equiv_hash(payload["d_rtl"], payload["c_rtl"], payload["top"], cfg, equiv_extra(cfg, payload, True))
    except (OSError, KeyError):
        return None
    root = Path(C.results_dir(cfg)) / "raw" / payload["design_id"] / "EQ"
    for eq in sorted(root.glob(f"{h}*/equiv.json")):
        try:
            return json.loads(eq.read_text())
        except (OSError, ValueError):
            continue
    return None


def write_reproof(conn, cand_id, rec, job_id):
    """The re-proof's outcome into the candidate row (the row held `error` from the failed job): V3 fields, verdict, harness version, a note."""
    conn.execute("UPDATE candidates SET v3_status=?, v3_seconds=?, verdict=?, proven_by=?, counterexample_path=?, harness_version=?, eq_job_id=?, "
                 "note=COALESCE(note,'') || ? WHERE cand_id=?",
                 (rec.get("v3_status"), rec.get("v3_seconds"), rec.get("verdict"), rec.get("proven_by"), rec.get("counterexample_path"), rec.get("harness_version"), job_id,
                  f" [re-proven {time.strftime('%Y-%m-%d %H:%M')} by the offline pool: {rec.get('verdict')} (harness_version {rec.get('harness_version')})]", cand_id))
    conn.commit()


def classify_e4_failure(cfg, conn, cand_id, job_id):
    """DECISION 2026-09-19 (n) 1: after a failed pool E4 job, read the DC error id from the job log's result line; an id of a rejection
    class (config offline_pool.dc_reject_prefixes: ELAB, VER, LINK — elaboration, unsupported construct, link) is terminal: the row gets
    candidates.e4_failure = "DC rejected (ID)" and is counted as resolved; anything else (a timeout, a licence or host failure) is left
    for a retry. -> ("rejected", id) | ("retry", id or None)."""
    import re as _re
    o = settings(cfg)
    prefixes = tuple(o.get("dc_reject_prefixes") or ["ELAB", "VER", "LINK"])
    row = conn.execute("SELECT log_path FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    txt = ""
    if row and row["log_path"] and os.path.exists(row["log_path"]):
        try:
            txt = open(row["log_path"], errors="replace").read()[-20000:]
        except OSError:
            txt = ""
    ids = _re.findall(r"\(([A-Z]{2,5}-\d+)\)", txt)
    rid = ids[-1] if ids else None
    if rid and rid.split("-")[0] in prefixes and "exceeded" not in txt:
        conn.execute("UPDATE candidates SET e4_failure=?, note=COALESCE(note,'') || ? WHERE cand_id=?",
                     (f"DC rejected ({rid})", f" [evaluation failed (DC rejected): {rid}, terminal — DECISION 2026-09-19 (n) 1]", cand_id))
        conn.commit()
        return "rejected", rid
    return "retry", rid


def sync_resim_row(conn, cand_id, rec, sim_job, passed):
    """DECISION 2026-09-19 (m) 2: the re-simulation's outcome into the candidate's row as the run would have written it — V1 / V2 fields;
    a failure keeps the nonequiv label with the verdict; a pass clears the label (the proof and E4 decide) and leaves the verdict NULL."""
    note = (f" [re-simulated {time.strftime('%Y-%m-%d %H:%M')} (DECISION 2026-09-19 (m) 2; the sim job crashed on the 2026-09-18 10:41 edit): V1 {rec.get('v1_status')}, V2 {rec.get('v2_status')}; "
            + ("proof and E4 submitted" if passed else str(rec.get("verdict"))) + "]")
    conn.execute("UPDATE candidates SET v1_status=?, v2_status=?, v2_cycles=?, verdict=?, label=?, eq_job_id=?, note=COALESCE(note,'') || ? WHERE cand_id=?",
                 (rec.get("v1_status"), rec.get("v2_status"), rec.get("v2_cycles"), None if passed else rec.get("verdict"), None if passed else "nonequiv", sim_job, note, cand_id))
    conn.commit()


def write_resim_proof(conn, cand_id, rec, job_id):
    """DECISION 2026-09-19 (m) 2: the re-run proof's outcome into the candidate's row (a proof job without a record is an evaluation error);
    anything but proven restores the nonequiv label; a proven candidate keeps no arm label (uniform rule A labels it in the reports)."""
    rec = rec or {"verdict": "error", "v3_status": "error"}
    conn.execute("UPDATE candidates SET v3_status=?, v3_seconds=?, verdict=?, proven_by=?, counterexample_path=?, harness_version=?, eq_job_id=?, "
                 "label=CASE WHEN ?='proven' THEN label ELSE 'nonequiv' END, note=COALESCE(note,'') || ? WHERE cand_id=?",
                 (rec.get("v3_status"), rec.get("v3_seconds"), rec.get("verdict"), rec.get("proven_by"), rec.get("counterexample_path"), rec.get("harness_version"), job_id, rec.get("verdict"),
                  f" [re-proven {time.strftime('%Y-%m-%d %H:%M')} (DECISION 2026-09-19 (m) 2): {rec.get('verdict')} (harness_version {rec.get('harness_version')})]", cand_id))
    conn.commit()


def sim_record_dir(cfg, payload):
    """The directory of the simulation record of a `sim` payload, or None."""
    from src.equiv.run_equiv import equiv_extra, equiv_hash
    try:
        h = equiv_hash(payload["d_rtl"], payload["c_rtl"], payload["top"], cfg, equiv_extra(cfg, payload, False))
    except (OSError, KeyError):
        return None
    root = Path(C.results_dir(cfg)) / "raw" / payload["design_id"] / "EQ"
    for eq in sorted(root.glob(f"{h}*/equiv.json")):
        return eq.parent
    return None


def slim_sim_record(cfg, payload):
    """2026-09-18 19:5x: the pool's simulation records keep their VCS build (simv, csrc, daidir) and traces until slimmed — the
    driver slims its own candidates' records, the pool must slim the ones it makes (spikeNeuron8_H7: 440 MB per record)."""
    d = sim_record_dir(cfg, payload)
    if d is None:
        return None
    try:
        from src.eval import retention as RET
        return RET.slim_eq_record(str(d), cfg)
    except Exception as e:   # slimming must never stop the pool
        return f"failed: {type(e).__name__}: {e}"[:120]


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
    order = []   # DECISION 2026-09-19 (m) 1: submissions follow the scope's order, not the state file's insertion order
    reopened = []
    for it in scope(cfg, conn, include_e4_timeouts):
        order.append(it["cand_id"])
        # 2026-09-21: a candidate whose E4 failed once was left at stage `done` in the state file, so the scope could list it again
        # (no ok record, retries left) while the pool never resubmitted it — nine medium-tier B0 candidates sat like that since
        # 2026-09-18/19 and kept Stage B out of its final report. An entry that reached `done` through a non-terminal E4 failure is
        # re-opened, at most `reopen_max` times and never past the attempt cap of the scope.
        c0 = cands.get(it["cand_id"])
        if (c0 is not None and c0.get("stage") == "done" and c0.get("e4_job") and "DC rejected" not in str(c0.get("result") or "")
                and int(c0.get("reopened") or 0) < int(o.get("reopen_max", 2))):
            ok = conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' LIMIT 1", (it["cand_id"],)).fetchone()
            bad = conn.execute("SELECT COUNT(*) FROM evaluations WHERE cand_id=? AND config='E4' AND status != 'ok'", (it["cand_id"],)).fetchone()[0]
            if not ok and bad < int(o.get("e4_max_attempts", 3)):
                c0.update({k: v for k, v in it.items() if k != "stage"})   # refresh the item's fields (rtl_path, group, run_id) from the scope
                c0.update(stage="e4", e4_job=None, result=None, reopened=int(c0.get("reopened") or 0) + 1)
                reopened.append(it["cand_id"])
        cands.setdefault(it["cand_id"], {**it, "stage": it.get("start_stage") or ("sim" if it["group"] in ("prescreened", "reverify", "resim", "d_saif") else ("proof" if it["group"] == "reproof" else "e4")), "sim_job": None, "e4_job": None, "proof_job": None, "result": None})
    seen = set(order)
    order += [cid for cid in cands if cid not in seen]
    # progress of submitted jobs
    for cid, c in cands.items():
        if c.get("group") == "floor6":   # REQUEST 2026-09-20 (e) item 3: proof under harness_version 2 -> perturbations row -> E4 of the proven entry
            if c["stage"] == "proof_running":
                js = q.get(c["proof_job"])
                if js and js["state"] in ("done", "failed"):
                    rec = proof_record(cfg, c["proof_payload"])
                    d = designs.get(c["design_id"])
                    if d is not None:
                        try:
                            from src.noise import gate as GT
                            GT.collect(conn, cfg, [d]); conn.commit()
                        except Exception as e:   # the row update must never stop the pool; the record stays on disk
                            c["collect_error"] = f"{type(e).__name__}: {e}"[:120]
                    row = conn.execute("SELECT seq_status FROM perturbations WHERE pert_id=?", (c["pert_id"],)).fetchone()
                    status = row["seq_status"] if row else ((rec or {}).get("verdict") or "error")
                    c["proof_result"] = status
                    if status in ("proven", "proven_rename"):
                        c.update(stage="e4", saif=(rec or {}).get("saif_c") or floor6_record_saif(cfg, c["design_id"], c["pert_id"]))
                    else:
                        c.update(stage="done", result=f"proof {status}")
            elif c["stage"] == "e4_running":
                js = q.get(c["e4_job"])
                if js and js["state"] in ("done", "failed"):
                    ev = conn.execute("SELECT status, dc_seconds, power_saif_mw FROM evaluations WHERE pert_id=? AND config='E4' ORDER BY eval_id DESC LIMIT 1", (c["pert_id"],)).fetchone()
                    c.update(stage="done", result=(f"E4 {ev['status']} ({'with' if ev['power_saif_mw'] is not None else 'without'} SAIF power)" if ev else f"E4 job {js['state']} (no record)"), dc_seconds=(ev["dc_seconds"] if ev else None))
            continue
        if c.get("group") == "d_saif":   # REQUEST 2026-09-20 (e) item 2: D-vs-D sim -> D's SAIF registered -> E4 of D with SAIF (offline_baseline = 1)
            if c["stage"] == "sim_running":
                js = q.get(c["sim_job"])
                if js and js["state"] in ("done", "failed"):
                    rec = sim_record(cfg, c["sim_payload"])
                    if rec is None:
                        c.update(stage="done", result="D-vs-D simulation job failed (no record)")
                    elif rec.get("verdict") in ("not_run", "proven_sim_only"):
                        saif = register_d_saif(cfg, c["design_id"], rec)
                        if saif:
                            c.update(stage="e4", sim_result=rec.get("v2_status"), saif=saif)
                        else:
                            c.update(stage="done", result=f"D-vs-D simulation passed ({rec.get('v2_status')}) but the record carries no SAIF of D (saif_d)", sim_result=rec.get("v2_status"))
                    else:
                        c.update(stage="done", result=f"D-vs-D simulation {rec.get('verdict')} ({rec.get('v1_status')}/{rec.get('v2_status')})", sim_result=rec.get("verdict"))
                    c["synced"] = True
                    if rec is not None:
                        c["sim_slimmed"] = str(slim_sim_record(cfg, c["sim_payload"]))[:120]   # D's SAIF was copied out; the build artefacts go
            elif c["stage"] == "e4_running":
                js = q.get(c["e4_job"])
                if js and js["state"] in ("done", "failed"):
                    ev = conn.execute("SELECT status, dc_seconds, power_saif_mw, eval_id FROM evaluations WHERE design_id=? AND config='E4' AND offline_baseline=1 ORDER BY eval_id DESC LIMIT 1", (c["design_id"],)).fetchone()
                    if ev is None:
                        c.update(stage="done", result=f"E4 job {js['state']} (no record)")
                    else:
                        c.update(stage="done", result=f"E4 {ev['status']} (eval {ev['eval_id']}, {'with' if ev['power_saif_mw'] is not None else 'without'} SAIF power)", dc_seconds=ev["dc_seconds"])
            continue
        if c["stage"] == "sim_running":
            js = q.get(c["sim_job"])
            if js and js["state"] in ("done", "failed") and c.get("group") == "resim":   # DECISION 2026-09-19 (m) 2: sim -> E4 and the proof in parallel
                rec = sim_record(cfg, c["sim_payload"])
                if rec is None:
                    c.update(stage="done", result="re-simulation job failed (no record)")
                elif rec.get("verdict") in ("not_run", "proven_sim_only"):
                    sync_resim_row(conn, cid, rec, c["sim_job"], True)
                    c.update(stage="e4_proof", sim_result=rec.get("v2_status"), saif=rec.get("saif_c"), sim_record=rec)
                else:
                    sync_resim_row(conn, cid, rec, c["sim_job"], False)
                    c.update(stage="done", result=f"re-simulation {rec.get('verdict')} ({rec.get('v1_status')}/{rec.get('v2_status')})", sim_result=rec.get("verdict"))
                    c["sim_slimmed"] = str(slim_sim_record(cfg, c["sim_payload"]))[:120]
                c["synced"] = True
            elif js and js["state"] in ("done", "failed"):
                rec = sim_record(cfg, c["sim_payload"])
                if rec is None:
                    c.update(stage="done", result="sim job failed (no record)")
                elif rec.get("verdict") == "not_run" or rec.get("verdict") in ("proven_sim_only",):
                    c.update(stage="e4", sim_result=rec.get("v2_status"), saif=rec.get("saif_c"))
                else:
                    c.update(stage="done", result=f"{rec.get('verdict')} ({rec.get('v1_status')}/{rec.get('v2_status')})", sim_result=rec.get("verdict"))
                if rec is not None and c.get("group") != "reverify":   # a superseded run's candidate keeps its harness-version-1 row (C4); the pool state holds the re-simulation
                    sync_candidate_row(conn, cid, rec, c.get("sim_job"))
                c["synced"] = True
                if rec is not None and c.get("saif") is None:   # the record's build artefacts go once its result is read; a record still needed for E4 (its SAIF) is slimmed after E4
                    c["sim_slimmed"] = str(slim_sim_record(cfg, c["sim_payload"]))[:120]
        elif c["stage"] == "proof_running":
            js = q.get(c["proof_job"])
            if js and js["state"] in ("done", "failed"):
                rec = proof_record(cfg, c["proof_payload"])
                if rec is None:
                    c.update(stage="done", result="proof job failed (no record)")
                else:
                    write_reproof(conn, cid, rec, c["proof_job"])
                    if rec.get("verdict") == "proven":
                        c.update(stage="e4", proof_result="proven", saif=rec.get("saif_c"))
                    else:
                        c.update(stage="done", result=f"reproof {rec.get('verdict')}", proof_result=rec.get("verdict"))
        elif c["stage"] == "e4_proof_running":   # (m) 2: both jobs of the run pipeline in flight
            if c.get("proof_result") is None:
                js = q.get(c["proof_job"])
                if js and js["state"] in ("done", "failed"):
                    rec = proof_record(cfg, c["proof_payload"])
                    write_resim_proof(conn, cid, rec, c["proof_job"])
                    c["proof_result"] = (rec or {}).get("verdict") or "error"
            if c.get("e4_result") is None:
                js = q.get(c["e4_job"])
                if js and js["state"] in ("done", "failed"):
                    ev = conn.execute("SELECT status, dc_seconds FROM evaluations WHERE cand_id=? AND config='E4' ORDER BY eval_id DESC LIMIT 1", (cid,)).fetchone()
                    c["e4_result"] = (f"E4 {ev['status']}" if ev else f"E4 job {js['state']}"); c["dc_seconds"] = ev["dc_seconds"] if ev else None
                    if not ev or ev["status"] != "ok":
                        kind, rid = classify_e4_failure(cfg, conn, cid, c["e4_job"])
                        c["e4_result"] = f"E4 DC rejected ({rid}), terminal" if kind == "rejected" else f"{c['e4_result']} ({rid or 'no DC error id'}; retry)"
            if c.get("proof_result") is not None and c.get("e4_result") is not None:
                c.update(stage="done", result=f"resim: proof {c['proof_result']}, {c['e4_result']}")
                if c.get("sim_payload") and not c.get("sim_slimmed"):
                    c["sim_slimmed"] = str(slim_sim_record(cfg, c["sim_payload"]))[:120]
        elif c["stage"] == "e4_running":
            js = q.get(c["e4_job"])
            if js and js["state"] in ("done", "failed"):
                ev = conn.execute("SELECT status, dc_seconds, raw_dir FROM evaluations WHERE cand_id=? AND config='E4' ORDER BY eval_id DESC LIMIT 1", (cid,)).fetchone()
                c.update(stage=("await_proof" if c.get("group") == "reverify" else "done"), result=f"E4 {ev['status']}" if ev else f"E4 job {js['state']}", dc_seconds=(ev["dc_seconds"] if ev else None))
                if not ev or ev["status"] != "ok":   # DECISION 2026-09-19 (n) 1: a DC rejection is terminal, anything else waits for a retry
                    kind, rid = classify_e4_failure(cfg, conn, cid, c["e4_job"])
                    c["result"] = f"E4 DC rejected ({rid}), terminal" if kind == "rejected" else f"{c['result']} ({rid or 'no DC error id'}; retry)"
                if c.get("sim_payload") and not c.get("sim_slimmed"):
                    c["sim_slimmed"] = str(slim_sim_record(cfg, c["sim_payload"]))[:120]
                if ev and ev["raw_dir"]:   # the same tiered retention as the visible runs: full artifacts for accepted / audit candidates, the parsed record and reports otherwise
                    try:
                        from src.eval import retention as RET
                        row = conn.execute("SELECT accepted, in_archive FROM candidates WHERE cand_id=?", (cid,)).fetchone()
                        res = RET.slim_candidate(cfg, cid, bool(row and (row[0] or row[1])), fit_dirs=[ev["raw_dir"]])
                        c["slimmed"] = {"kept_full": res["kept_full"], "bytes": sum(res["freed"].values())}
                    except Exception as e:   # retention must never stop the pool
                        c["slimmed"] = f"failed: {type(e).__name__}: {e}"[:120]
    for cid, c in cands.items():   # entries simulated before the row sync existed (2026-09-18): synced once from their records
        if c.get("sim_payload") and not c.get("synced") and c["stage"] in ("e4", "e4_running", "done") and c.get("group") != "d_saif":
            rec = sim_record(cfg, c["sim_payload"])
            if rec is not None:
                sync_candidate_row(conn, cid, rec, c.get("sim_job"))
            c["synced"] = True
    ok, l1, q95 = throttle(cfg, conn, st)
    submitted = 0
    slots = int(o["slots"])
    idle_dc = int(cfg["queue"].get("dc_seats_target") or cfg["queue"].get("dc_seats_max") or 0) - conn.execute("SELECT COUNT(*) FROM jobs WHERE state='running' AND pool='dc'").fetchone()[0]
    if idle_dc > int(o.get("idle_dc_seats_for_extra", 12)):   # DECISION 2026-09-18 (d) B5 / 2026-09-19 (m) 1: up to slots_when_idle (16) while more than 12 DC seats sit idle
        slots = max(slots, int(o.get("slots_when_idle", 12)))
    st["slots_now"] = slots
    if ok:
        inflight = sum(1 for c in cands.values() if c["stage"] in ("sim_running", "e4_running", "e4_proof_running"))
        proof_inflight = sum(1 for c in cands.values() if c["stage"] == "proof_running")
        for cid in order:
            c = cands[cid]
            if c["stage"] == "proof":   # proofs take VC Formal seats, not the pool's DC / sim slots: their own small cap (offline_pool.proof_slots)
                if proof_inflight >= int(o.get("proof_slots", 4)):
                    continue
                proof_inflight += 1
            elif inflight + submitted >= slots:
                continue   # the DC / sim slots are full: skip, but keep scanning for proof entries (they have their own cap)
            d = designs.get(c["design_id"])
            if d is None:
                c.update(stage="done", result="design not in the catalog"); continue
            if c.get("group") == "floor6":   # REQUEST 2026-09-20 (e) item 3
                if c["stage"] == "proof":
                    pl = floor6_proof_payload(cfg, d, c)
                    jid = q.submit("vcf", pl, design_id=c["design_id"], cand_id=c["pert_id"], config="EQ", priority=int(o["priority"]), timeout_sec=int(cfg["timeouts"]["seq_min"]) * 60 + 900)
                    c.update(stage="proof_running", proof_job=jid, proof_payload=pl); submitted += 1
                elif c["stage"] == "e4":
                    saif = c.get("saif") or floor6_record_saif(cfg, c["design_id"], c["pert_id"])
                    j = floor6_e4_job(cfg, conn, d, c, saif=saif)
                    jid = q.submit(j["kind"], j["payload"], design_id=c["design_id"], cand_id=None, config="E4", priority=j["priority"], timeout_sec=j["timeout_sec"])
                    c.update(stage="e4_running", e4_job=jid, saif=saif); submitted += 1
                continue
            if c.get("group") == "d_saif":   # REQUEST 2026-09-20 (e) item 2
                if c["stage"] == "sim":
                    pl = d_saif_sim_payload(cfg, d)
                    jid = q.submit("sim", pl, design_id=c["design_id"], cand_id=None, config="EQ", priority=int(o["priority"]), timeout_sec=int(cfg["timeouts"]["sim"]) * 60 + 300)
                    c.update(stage="sim_running", sim_job=jid, sim_payload=pl); submitted += 1
                elif c["stage"] == "e4":
                    j = d_saif_e4_job(cfg, conn, d, c["saif"])
                    jid = q.submit(j["kind"], j["payload"], design_id=c["design_id"], cand_id=None, config="E4", priority=j["priority"], timeout_sec=j["timeout_sec"])
                    c.update(stage="e4_running", e4_job=jid); submitted += 1
                continue
            if c["stage"] == "sim" and c.get("group") == "resim":   # (m) 2: the crashed job's payload, at the run pipeline's priority, not niced
                pl = dict(c["sim_payload_src"]); pl["note"] = f"{pl.get('note', '')} [resim (DECISION 2026-09-19 (m) 2)]"; pl["resim"] = 1
                jid = q.submit("sim", pl, design_id=c["design_id"], cand_id=cid, config="EQ", priority=int(cfg["search"].get("job_priority", 4)), timeout_sec=int(cfg["timeouts"]["sim"]) * 60 + 300)
                c.update(stage="sim_running", sim_job=jid, sim_payload=pl); submitted += 1
            elif c["stage"] == "sim":
                pl = sim_payload(cfg, d, c)
                jid = q.submit("sim", pl, design_id=c["design_id"], cand_id=cid, config="EQ", priority=int(o["priority"]), timeout_sec=int(cfg["timeouts"]["sim"]) * 60 + 300)
                c.update(stage="sim_running", sim_job=jid, sim_payload=pl); submitted += 1
            elif c["stage"] == "e4_proof":   # (m) 2: E4 and the SEQ proof in parallel, as the run would (the proof takes no DC slot; it enters the normal VC Formal queue)
                j = e4_job(cfg, conn, d, c, saif=c.get("saif"))
                ejid = q.submit(j["kind"], j["payload"], design_id=c["design_id"], cand_id=cid, config="E4", priority=j["priority"], timeout_sec=j["timeout_sec"])
                pl = dict(c["sim_payload"], sim_record=c["sim_record"]); pl["note"] = f"{pl.get('note', '')} proof"
                cap = conn.execute("SELECT seq_cap_min FROM candidates WHERE cand_id=?", (cid,)).fetchone()
                cap = int((cap[0] if cap and cap[0] else 0) or cfg["timeouts"]["seq_min"])
                pri = int(cfg["search"].get("job_priority", 4)) + int((cfg["search"].get("early") or {}).get("priority_undiagnosed") or 0)
                pjid = q.submit("vcf", pl, design_id=c["design_id"], cand_id=cid, config="EQ", priority=pri, timeout_sec=cap * 60 + 900)
                c.update(stage="e4_proof_running", e4_job=ejid, proof_job=pjid, proof_payload=pl); submitted += 1
            elif c["stage"] == "proof":
                pl = dict(c["proof_payload"]); pl["note"] = f"offline pool reproof {cid} (proof job failed on an operator edit, 2026-09-18 10:41)"; pl["offline_pool"] = True
                jid = q.submit("vcf", pl, design_id=c["design_id"], cand_id=cid, config="EQ", priority=int(o.get("reproof_priority", 8)), timeout_sec=int(cfg["timeouts"]["seq_min"]) * 60 + 900)
                c.update(stage="proof_running", proof_job=jid); submitted += 1
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
    log(f"pass: load1 {l1:.0f} q95 {q95:.1f} min {'paused' if st.get('paused') else 'active'}; submitted {submitted}; stages {counts}"
        + (f"; re-opened after a non-terminal E4 failure: {len(reopened)} {reopened[:6]}" if reopened else ""))
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
    passes = 0
    while not stop["flag"]:
        try:
            passes += 1
            if passes % 60 == 1:   # 2026-09-18 19:5x: compress the ingested DC logs about once an hour from here (the session's hourly check missed 13 hours: 28 GB of thresholds logs)
                try:
                    import subprocess as _sp
                    r = _sp.run([sys.executable, os.path.join(ROOT, "scripts", "compress_logs.py"), "--apply"], capture_output=True, text=True, timeout=3300)
                    log(f"compress_logs: {(r.stdout.strip().splitlines() or ['no output'])[-1][:160]}")
                except Exception as e:
                    log(f"compress_logs failed: {type(e).__name__}: {e}")
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
