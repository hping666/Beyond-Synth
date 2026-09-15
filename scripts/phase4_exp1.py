#!/usr/bin/env python3
"""Phase 4 — Exp1 (docs/PLAN.md 4.1–4.3; DECISIONS 2026-09-14 C1 scope): the objects of the map and their runs.

    .venv/bin/python scripts/phase4_exp1.py baselines [--submit] [--priority 1]   # missing D baselines at Phi_main: Y, E1d, E2g, O0-O2, Ycoevo (Exp1 + calibration designs)
    .venv/bin/python scripts/phase4_exp1.py generate  [--design ...] [--submit]   # B0 runs (Y-caliber fitness, llm.selected) on config exp1.designs, one `search` job each
    .venv/bin/python scripts/phase4_exp1.py smoke --design <id> [--K 1 --N 2] [--submit]   # rule 7: one B0 run first
    .venv/bin/python scripts/phase4_exp1.py status
    .venv/bin/python scripts/phase4_exp1.py topup [--submit]             # more B0 runs (next seeds) for designs below exp1.candidates_per_design proven candidates
    .venv/bin/python scripts/phase4_exp1.py objects [--submit]          # literature objects (RTL-OPT / RTLRewriter references, LLM samples): runs + candidates, M6, equivalence jobs
    .venv/bin/python scripts/phase4_exp1.py verdicts                    # ingest the objects' equivalence verdicts
    .venv/bin/python scripts/phase4_exp1.py ladder [--hidden] [--submit] [--priority 1]   # E1, E1d, E2, E3, E4, E2g, Y, O0-O2, Ycoevo (+ hidden) on every proven object
    .venv/bin/python scripts/phase4_exp1.py diagnose [--dry-run]         # M3 at E4 with the frozen floors and the lower rungs (PLAN 4.3)
    .venv/bin/python scripts/phase4_exp1.py collect                      # reports/data/phase4_exp1.json (map, curves, literature table, misclassification, predictor)
    .venv/bin/python scripts/phase4_exp1.py snapshot [--name ...]        # results/snapshots/phase4-<date>/ (evaluations, candidates, diagnoses, map)

Every candidate of every B0 run is SEQ-checked by the driver and evaluated under Y (the run's fitness); the ladder
(E1, E1d, E2, E3, E4, E2g, the supplementary Yosys configurations and the hidden configurations) runs afterwards on
every proven object (PLAN 4.2, `phase4_exp1.py ladder`), and the M3 diagnosis at E4 with the phase-4 floors is the
analysis step (PLAN 4.3). The 10 Exp1 designs never serve as Phase 5 starting points (config design_sets)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.designs import jobs as J  # noqa: E402


def calibration_designs(cfg, conn):
    from scripts.phase3_calibrate import calibration_designs as cal
    return cal(cfg, conn)


def baseline_configs(cfg):
    """D baselines the map needs besides the noise-run rungs E1–E4: the attribution rungs, Y and the supplementary Yosys runs."""
    visible = [c for c in cfg["exp1"]["configs"] if not cfg["configs"][c].get("hidden")]
    return [c for c in visible if c not in ("E1", "E2", "E3", "E4")] + ["Y"] + list(cfg["exp1"].get("supplementary") or [])


def baseline_jobs(cfg, conn, designs, priority=1, configs=None):
    """Missing D baselines of `designs` under `configs` (default baseline_configs: the attribution rungs and the Yosys runs)."""
    cat = {d["design_id"]: d for d in K.load_all()}
    jobs = []
    for did in designs:
        d = cat[did]
        phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (did,)).fetchone()[0]
        if phi is None:
            continue
        for config in (configs or baseline_configs(cfg)):
            have = conn.execute("SELECT power_default_mw FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY eval_id DESC LIMIT 1", (did, config, float(phi))).fetchone()
            refresh = have is not None and cfg["configs"][config].get("tool") == "yosys_opensta" and have[0] is None
            if have is not None and not refresh:
                continue   # a Yosys record without OpenSTA power predates report_power (2026-09-14) and is refreshed (append-only: a newer -rN record, the cache bypassed)
            if conn.execute("SELECT 1 FROM jobs WHERE design_id=? AND config=? AND cand_id IS NULL AND state IN ('queued','running') LIMIT 1", (did, config)).fetchone():
                continue   # already in the queue
            j = J.dc_job(cfg, d, config, float(phi), priority)
            if cfg["configs"][config].get("tool") == "yosys_opensta":
                j["kind"] = "yosys"
            if refresh:
                j["payload"]["force_rerun"] = True
            jobs.append(j)
    return jobs


def cmd_baselines(cfg, conn, do_submit, priority, objects=False):
    """Missing D baselines for the Exp1 and calibration designs; with --objects also for every design that has a proven
    Phase 4 object (the literature designs: 2026-09-15, 76 of 83 such designs lacked E1d / E2g / Y / O0-O2 / Ycoevo
    baselines, so the map columns and the single-flag reproduction were B0-only), including E1 / E2 / E3 where missing."""
    from src.jobqueue.core import Queue
    designs = list(cfg["exp1"]["designs"]) + [d for d in calibration_designs(cfg, conn) if d not in cfg["exp1"]["designs"]]
    configs = None
    if objects:
        extra = [r[0] for r in conn.execute("SELECT DISTINCT c.design_id FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase4' AND r.status != 'superseded' "
                                            "AND c.verdict IN ('proven','proven_sim_only') ORDER BY c.design_id")]
        designs += [d for d in extra if d not in designs]
        configs = ["E1", "E2", "E3"] + baseline_configs(cfg)
    jobs = baseline_jobs(cfg, conn, designs, priority, configs=configs)
    by = {}
    for j in jobs:
        by[(j["kind"], j["config"])] = by.get((j["kind"], j["config"]), 0) + 1
    print(f"{len(jobs)} missing baseline jobs for {len(designs)} designs: {dict(sorted(by.items()))}")
    if do_submit:
        q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
        for j in jobs:
            q.submit(j["kind"], j["payload"], design_id=j["design_id"], config=j["config"], priority=j["priority"], timeout_sec=j["timeout_sec"])
        print(f"submitted {len(jobs)} jobs")
    return 0


def create_runs(cfg, conn, designs, exp, K, N, seed, do_submit, note=""):
    from src.jobqueue.core import Queue
    from src.search.driver import SearchRun
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    model = cfg["llm"]["selected"]
    runs = []
    for did in designs:
        run = SearchRun.create(cfg, conn, exp=exp, arm="B0", design_id=did, seed=int(seed), model=model, K=int(K), N=int(N), queue=q, note=note)
        runs.append(run.run_id)
        if do_submit:
            q.submit("search", {"run_id": run.run_id}, design_id=did, config="search", priority=3, timeout_sec=12 * 3600)
    print(f"{len(runs)} B0 runs ({model}, K={K}, N={N}, seed={seed}, exp={exp}, floor_version={cfg['noise'].get('floor_version')})" + (" submitted" if do_submit else " created (not submitted)"))
    for r in runs:
        print("  " + r)
    return runs


def cmd_status(cfg, conn):
    for r in conn.execute("SELECT run_id, design_id, arm, status, gens_done, llm_calls, spent_usd, floor_version FROM runs WHERE exp IN ('phase4','smoke') AND arm='B0' AND status != 'superseded' ORDER BY started_at"):
        n = conn.execute("SELECT COUNT(*), SUM(verdict IN ('proven','proven_sim_only')), SUM(label='improved'), SUM(label IS NULL) FROM candidates WHERE run_id=?", (r["run_id"],)).fetchone()
        print(f"{r['run_id']:44s} {r['design_id']:34s} {r['status']:8s} gens {r['gens_done']} calls {r['llm_calls']} usd {r['spent_usd'] or 0:.3f} floors {r['floor_version']} "
              f"cands {n[0]} proven {n[1] or 0} improved {n[2] or 0} pending {n[3] or 0}")
    print("phase4 LLM spend:", round(conn.execute("SELECT COALESCE(SUM(amount),0) FROM budget_ledger WHERE phase='phase4_generation' AND kind='llm'").fetchone()[0], 3), "USD")
    return 0



# ----------------------------------------------------------------------------- literature objects (PLAN 4.1 inputs, 4.2)
LIT_ARM = "literature"
_MODULE = __import__("re").compile(r"^\s*module\s+([A-Za-z_][\w$]*)", __import__("re").M)


def guess_top(files, d_top):
    """The object's top module: D's name when the object declares it, else the only / first module it declares."""
    names = []
    for f in files:
        names += _MODULE.findall(__import__("pathlib").Path(f).read_text(errors="replace"))
    if d_top in names or not names:
        return d_top
    return names[0]


def literature_objects(cfg, conn):
    """[(design, object)] for the synthesizable RTL-OPT pairs (expert reference) and RTLRewriter pairs (engineers' rewrite,
    long and short benchmarks) plus RTLRewriter's LLM samples; objects are compared with their own D."""
    out = []
    for d in K.load_all():
        if d["suite"] not in ("rtlopt", "rtlrewriter"):
            continue
        r = conn.execute("SELECT e4_synthesizable, phi_main_ns_nangate45 FROM designs WHERE design_id=?", (d["design_id"],)).fetchone()
        if not r or not r[0] or r[1] is None:
            continue
        if d.get("reference"):
            out.append((d, {"role": "reference", "files": list(d["reference"]["files"]), "top": d["reference"].get("top"), "note": d["reference"].get("note") or ""}))
        for s in d.get("samples") or []:
            if s.get("role") == "llm":
                out.append((d, {"role": "llm", "files": list(s["files"]), "top": s.get("top"), "note": s.get("note") or s["files"][0]}))
    return out


def object_run_id(d):
    return f"lit_{d['design_id']}"


def eq_payload_for(d, cand_id, files, top, note):
    return {"design_id": d["design_id"], "cand_id": cand_id, "d_rtl": [str(p) for p in K.abs_paths(d, d["files"])], "c_rtl": files, "top": d["top"],
            "c_top": top if top != d["top"] else None, "clk": (d.get("clk_ports") or [None])[0], "rst": d.get("rst_port"), "rst_sense": d.get("rst_sense"),
            "sverilog": d.get("sverilog", False), "incdirs": [str(p) for p in K.abs_paths(d, d["incdirs"])], "note": note}


def eq_record_for(cfg, payload):
    """The equivalence record of an object by the content-addressed directory of its payload (as the search driver does)."""
    import json
    from pathlib import Path
    from src.equiv.run_equiv import equiv_hash
    extra = {"stages": "full", "clk": payload.get("clk"), "rst": payload.get("rst"), "rst_sense": payload.get("rst_sense"),
             "sverilog": payload.get("sverilog", False), "sim_seed": payload.get("sim_seed"), "c_top": payload.get("c_top")}
    root = Path(C.results_dir(cfg)) / "raw" / payload["design_id"] / "EQ"
    try:
        h = equiv_hash(payload["d_rtl"], payload["c_rtl"], payload["top"], cfg, extra)
    except OSError:
        return None, None
    best = None
    for eq in sorted(root.glob(f"{h}*/equiv.json"), key=lambda p: p.stat().st_mtime):
        try:
            best = (json.loads(eq.read_text()), str(eq.parent))
        except json.JSONDecodeError:
            continue
    return best if best else (None, None)


def object_dir(cfg, run_id):
    from pathlib import Path
    p = Path(C.ROOT) / "results" / "candidates" / run_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def cmd_objects(cfg, conn, do_submit, priority=2):
    """Register the literature objects as candidates of one `literature` run per design (exp phase4; idempotent), classify
    them with M6 (rules v2, the object's own top), and submit the missing equivalence jobs (V1 -> V2 -> V3, class-aware cap)."""
    import json
    import tempfile
    from pathlib import Path
    from src.classify import rules as M6
    from src.jobqueue.core import Queue
    from src.search import candidates as CA
    caps = cfg.get("equiv", {}).get("seq_cap_min_by_class") or {}
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={}) if do_submit else None
    n_new = n_existing = n_jobs = n_records = 0
    by_role = {}
    for d, o in literature_objects(cfg, conn):
        run_id = object_run_id(d)
        if conn.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone() is None:
            db.insert(conn, "runs", {"run_id": run_id, "exp": "phase4", "arm": LIT_ARM, "skeleton": None, "design_id": d["design_id"], "seed": 0, "llm_model": None,
                                     "prompt_version": None, "screening_enabled": 0, "e_s": None, "budget_dc_hours": None, "budget_llm_calls": 0, "status": "done",
                                     "started_at": db.now(), "finished_at": db.now(), "floor_version": cfg["noise"].get("floor_version")})
        files = [str(p) for p in K.abs_paths(d, o["files"])]
        rtl = "\n".join(Path(f).read_text(errors="replace") for f in files)
        cid = CA.cand_id_of(rtl, run_id)
        top = o.get("top") or guess_top(files, d["top"])
        by_role[o["role"]] = by_role.get(o["role"], 0) + 1
        payload = eq_payload_for(d, cid, files, top, f"phase4 object {o['role']} of {d['design_id']}")
        (object_dir(cfg, run_id) / f"{cid}.json").write_text(json.dumps({"cand_id": cid, "design_id": d["design_id"], "role": o["role"], "files": files, "top": top, "note": o["note"], "eq_payload": payload}, indent=1))
        row = conn.execute("SELECT cand_id, verdict, eq_job_id FROM candidates WHERE cand_id=?", (cid,)).fetchone()
        if row is None:
            wd = Path(tempfile.mkdtemp(prefix=f"bs_m6obj_{cid}_"))
            try:
                feat = M6.features(payload["d_rtl"], files, d["top"], cfg, sverilog=d.get("sverilog", False), incdirs=payload["incdirs"], workdir=wd, c_top=top)
                res = M6.classify(feat, cfg)
                feat_json = json.dumps(feat)
            except Exception as e:   # the object cannot be read by Yosys: no class, the default SEQ cap
                res, feat_json = {"class_rule": None, "rules": [f"m6 failed: {type(e).__name__}: {e}"[:200]], "confidence": None}, None
            finally:
                __import__("shutil").rmtree(wd, ignore_errors=True)
            cls = res["class_rule"]
            cap = int(caps.get(cls, cfg["timeouts"]["seq_min"])) if cls else int(caps.get("d", cfg["timeouts"]["seq_min"]))
            db.insert(conn, "candidates", {"cand_id": cid, "run_id": run_id, "design_id": d["design_id"], "gen": 0, "parent_id": None, "arm": LIT_ARM, "content_hash": CA.cand_id_of(rtl),
                                           "class_requested": None, "class_rule": cls, "class_final": cls, "confidence": res.get("confidence"), "subtags_json": json.dumps(res.get("rules")),
                                           "rules_version": 2, "features_json": feat_json, "llm_model": None, "rtl_path": files[0], "rtl_files_json": json.dumps(files) if len(files) > 1 else None,
                                           "top": top if top != d["top"] else None, "label": "object", "note": f"{o['role']}: {o['note']}"[:200], "seq_cap_min": cap, "prescreened": 0})
            n_new += 1
            row = conn.execute("SELECT cand_id, verdict, eq_job_id FROM candidates WHERE cand_id=?", (cid,)).fetchone()
        else:
            n_existing += 1
        if row["verdict"]:
            continue
        rec, rec_dir = eq_record_for(cfg, payload)
        if rec is not None:
            ingest_verdict(conn, cid, rec)
            n_records += 1
            continue
        if row["eq_job_id"] and conn.execute("SELECT 1 FROM jobs WHERE job_id=? AND state IN ('queued','running')", (row["eq_job_id"],)).fetchone():
            continue
        if do_submit:
            cap = conn.execute("SELECT seq_cap_min FROM candidates WHERE cand_id=?", (cid,)).fetchone()[0] or int(cfg["timeouts"]["seq_min"])
            jid = q.submit("vcf", payload, design_id=d["design_id"], cand_id=cid, config="EQ", priority=priority, timeout_sec=int(cap) * 60 + 900)
            conn.execute("UPDATE candidates SET eq_job_id=? WHERE cand_id=?", (jid, cid))
            conn.commit()
        n_jobs += 1
    conn.commit()
    print(f"objects: {n_new} new, {n_existing} existing ({by_role}); {n_records} verdicts ingested from earlier records; {n_jobs} equivalence jobs {'submitted' if do_submit else 'to submit'}")
    return 0


EQ_COLS = ("v1_status", "v2_status", "v2_cycles", "latency_offset_json", "v3_status", "v3_seconds", "v4_status", "counterexample_path", "verdict", "proven_by")


def ingest_verdict(conn, cand_id, rec):
    import json
    conn.execute("UPDATE candidates SET v1_status=?, v2_status=?, v2_cycles=?, latency_offset_json=?, v3_status=?, v3_seconds=?, v4_status=?, counterexample_path=?, verdict=?, proven_by=? WHERE cand_id=?",
                 tuple(rec.get(k) for k in EQ_COLS) + (cand_id,))
    offsets = json.loads(rec.get("latency_offset_json") or "{}")
    if rec.get("verdict") in ("proven", "proven_sim_only") and any(int(v) > 0 for v in offsets.values()):
        conn.execute("UPDATE candidates SET class_final='c2' WHERE cand_id=?", (cand_id,))
    conn.commit()


def cmd_verdicts(cfg, conn):
    """Ingest the equivalence verdicts of the literature objects whose jobs have finished (the search driver does this
    for its own candidates)."""
    import json
    from pathlib import Path
    n = pending = 0
    for c in conn.execute("SELECT c.cand_id, c.run_id, c.eq_job_id FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase4' AND r.arm=? AND c.verdict IS NULL", (LIT_ARM,)).fetchall():
        info = json.loads((object_dir(cfg, c["run_id"]) / f"{c['cand_id']}.json").read_text())
        rec, _ = eq_record_for(cfg, info["eq_payload"])
        if rec is None:
            js = conn.execute("SELECT state FROM jobs WHERE job_id=?", (c["eq_job_id"],)).fetchone() if c["eq_job_id"] else None
            if js and js[0] in ("done", "failed"):
                conn.execute("UPDATE candidates SET verdict='error', v1_status='error', note=COALESCE(note,'') || ' [no equivalence record]' WHERE cand_id=?", (c["cand_id"],))
                conn.commit()
                n += 1
            else:
                pending += 1
            continue
        ingest_verdict(conn, c["cand_id"], rec)
        n += 1
    print(f"verdicts ingested: {n}; pending: {pending}; objects by verdict: " + str([tuple(r) for r in conn.execute("SELECT verdict, count(*) FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase4' AND r.arm=? GROUP BY 1", (LIT_ARM,))]))
    return 0


# ----------------------------------------------------------------------------- ladder on every proven Phase 4 object (PLAN 4.2)
def phase4_objects(conn, proven_only=True):
    """Candidate rows of the Phase 4 runs (B0 searches and literature runs): proven objects only by default."""
    cond = "AND c.verdict IN ('proven','proven_sim_only')" if proven_only else ""
    return [dict(r) for r in conn.execute(f"SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, c.rtl_files_json, c.top, c.e4_job_id, c.label, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                                          f"WHERE r.exp='phase4' AND r.status != 'superseded' AND c.rtl_path IS NOT NULL AND c.label IS NOT NULL AND c.label != 'aborted' {cond} ORDER BY c.run_id, c.cand_id")]


def object_saif(cfg, conn, row):
    """The object's SAIF from its equivalence record (saif_c): the search driver's state file for B0 candidates, the object
    file for literature objects."""
    import json
    from pathlib import Path
    rec_dir = None
    if row["arm"] == LIT_ARM:
        info_p = object_dir(cfg, row["run_id"]) / f"{row['cand_id']}.json"
        if info_p.exists():
            _, rec_dir = eq_record_for(cfg, json.loads(info_p.read_text())["eq_payload"])
    else:
        st = Path(C.ROOT) / "results" / "candidates" / row["run_id"] / "state.json"
        if st.exists():
            rec_dir = (json.loads(st.read_text()).get("cands") or {}).get(row["cand_id"], {}).get("eq_record")
    if rec_dir and (Path(rec_dir) / "equiv.json").exists():
        s = json.loads((Path(rec_dir) / "equiv.json").read_text()).get("saif_c")
        return s if s and Path(s).exists() else None
    return None


def ladder_jobs(cfg, conn, configs, priority, retry_failed=False, skipped=None):
    """Missing records only; a pair whose latest record is a deterministic failure (src/eval/failures.py: the tool rejects the
    RTL) is skipped unless retry_failed, counted per configuration in `skipped` when a dict is given."""
    import json
    from src.eval.failures import deterministic_failure
    cat = {d["design_id"]: d for d in K.load_all()}
    jobs = []
    for c in phase4_objects(conn):
        d = cat[c["design_id"]]
        phi = float(conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (c["design_id"],)).fetchone()[0])
        files = json.loads(c["rtl_files_json"]) if c["rtl_files_json"] else [c["rtl_path"]]
        saif = object_saif(cfg, conn, c)
        for config in configs:
            if conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config=? AND status='ok' AND abs(clock_ns-?)<1e-6 LIMIT 1", (c["cand_id"], config, phi)).fetchone():
                continue
            if not retry_failed and deterministic_failure(conn, c["cand_id"], config, phi):
                if skipped is not None:
                    skipped[config] = skipped.get(config, 0) + 1
                continue
            j = J.dc_job(cfg, d, config, phi, priority)
            if cfg["configs"][config].get("tool") == "yosys_opensta":
                j["kind"] = "yosys"
            j["payload"].update(rtl=files, incdirs=[str(p) for p in K.abs_paths(d, d["incdirs"])], is_baseline=0, cand_id=c["cand_id"])   # candidates may `include D's files
            if c["top"]:
                j["payload"]["top"] = c["top"]
            if saif and j["kind"] == "dc":
                j["payload"].update(saif=saif, saif_instance="bs_lockstep/u_c")
            j["cand_id"] = c["cand_id"]
            jobs.append(j)
    return jobs


def cmd_ladder(cfg, conn, do_submit, priority, hidden, configs=None, retry_failed=False):
    """Every visible rung and supplementary Yosys configuration on every proven Phase 4 object (missing records only;
    deterministic failures skipped unless --retry-failed); with --hidden also the hidden configurations through
    scripts/hidden_worker.py --submit-candidates --exp phase4 (rule 3)."""
    from src.jobqueue.core import Queue
    visible = [c for c in cfg["exp1"]["configs"] if not cfg["configs"][c].get("hidden")]
    configs = configs or visible + ["Y"] + list(cfg["exp1"].get("supplementary") or [])
    skipped = {}
    jobs = ladder_jobs(cfg, conn, configs, priority, retry_failed=retry_failed, skipped=skipped)
    by = {}
    for j in jobs:
        by[j["config"]] = by.get(j["config"], 0) + 1
    print(f"{len(jobs)} ladder jobs on {len(phase4_objects(conn))} proven Phase 4 objects: {dict(sorted(by.items()))}; deterministic failures skipped: {dict(sorted(skipped.items()))}")
    if do_submit:
        q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
        for j in jobs:
            jid = q.submit(j["kind"], j["payload"], design_id=j["design_id"], cand_id=j["cand_id"], config=j["config"], priority=j["priority"], timeout_sec=j["timeout_sec"])
            if j["config"] == "E4":   # the hidden worker and the diagnosis find E4-evaluated objects by this column
                conn.execute("UPDATE candidates SET e4_job_id=COALESCE(e4_job_id, ?) WHERE cand_id=?", (jid, j["cand_id"]))
        conn.commit()
        print(f"submitted {len(jobs)} jobs")
    if hidden:
        import subprocess
        cmd = [sys.executable, os.path.join(ROOT, "scripts", "hidden_worker.py"), "--submit-candidates", "--exp", "phase4", "--priority", str(priority)]   # same priority as the visible rungs: the Phase 4 objects precede the Phase 3 backlog
        if not do_submit:
            cmd.append("--dry-run")
        if retry_failed:
            cmd.append("--retry-failed")
        print(subprocess.run(cmd, capture_output=True, text=True).stdout.strip())
    return 0



# ----------------------------------------------------------------------------- diagnosis, map, predictor, snapshot (PLAN 4.3-4.8)
def cmd_diagnose(cfg, conn, dry_run, force=False):
    from src.analysis import objects as O
    out = O.diagnose_objects(cfg, conn, "phase4", dry_run=dry_run, force=force)
    print(("dry run: " if dry_run else "") + f"diagnosed {out['diagnosed']} (labels {out['labels']}); existing {out['existing']}, replaced {out.get('replaced', 0)}, not proven {out['skipped_not_proven']}, no E4 record {out['skipped_no_e4']}")
    return 0


def cmd_collect(cfg, conn):
    """reports/data/phase4_exp1.json: object counts, the map (class x configuration), retention curves, non-monotone cases,
    the literature table, the misclassification rates, the predictor (with class / class-blind, leave-one-design-out),
    the map shape, and the sigma comparison of the Exp1 designs' floors with the calibration designs'."""
    import json
    from pathlib import Path
    from src.analysis import map as M
    from src.analysis import objects as O
    from src.analysis import predictor as P
    from src.noise import stats as S
    objs = O.build_object_rows(cfg, conn, "phase4")
    counts = {"objects": len(objs), "by_role": {}, "by_verdict": {}, "by_class": {}, "by_label": {}, "with_e4": sum(1 for o in objs if "E4" in o["gains"])}
    for o in objs:
        for k, v in (("by_role", o["role"]), ("by_verdict", o["verdict"] or "pending"), ("by_class", o["cls"] or "?"), ("by_label", o["label"] or "-")):
            counts[k][v] = counts[k].get(v, 0) + 1
    diagnosed = [o for o in objs if o.get("label") and o["label"] not in ("nonequiv", "duplicate")]   # a duplicate repeats an earlier object's netlist: not a map object
    b0 = [o for o in diagnosed if o["role"] == "b0"]
    lit = [o for o in diagnosed if o["role"] in ("reference", "llm")]
    map_all = M.build_map(diagnosed)
    map_b0 = M.build_map(b0)
    curves = M.retention_curves(diagnosed)
    nm = M.non_monotone(diagnosed)
    lit_table = M.literature_table([o for o in objs if o["role"] == "reference"])
    mis = M.misclassification_rates(diagnosed)
    pred_rows = O.predictor_rows(cfg, conn, diagnosed)
    pred = P.evaluate(pred_rows) if len(pred_rows) >= 16 else {"note": f"only {len(pred_rows)} diagnosed objects"}
    for k in ("with_class", "class_blind"):
        if isinstance(pred.get(k), dict):
            pred[k].pop("scores", None)
    shape, rates = M.shape(map_b0 if len(b0) >= 30 else map_all)
    floors = {}
    for did in list(cfg["exp1"]["designs"]) + [d for d in calibration_designs(cfg, conn) if d not in cfg["exp1"]["designs"]]:
        fl = S.latest_floor(conn, did, "E4", cfg["noise"].get("floor_version")) or S.latest_floor(conn, did, "E4")
        floors[did] = {m: {"t_d": (fl.get(k) or {}).get("t_d"), "sigma_robust": (fl.get(k) or {}).get("sigma_robust"), "floor_class": (fl.get(k) or {}).get("floor_class")} for m, k in (("area", "area"), ("wns", "wns"), ("power", "power_saif"))}
    # the out-of-scope contrast layer (DECISIONS 2026-09-14, C1 scope): the Phase 3 calibration candidates (RTLLM dev designs)
    # under the same map; their labels are the run-time M3 verdicts (floors of the runs), their classes rules v2
    p3 = O.build_object_rows(cfg, conn, "phase3")
    p3_diag = [o for o in p3 if o.get("label") in ("retained", "tradeoff", "absorbed", "absorbed_identical", "noise", "harmful", "fragile")]   # duplicates excluded (same netlist as an earlier candidate)
    mat = {"area": float(cfg["noise"]["materiality"]["area"]), "wns": float(cfg["noise"]["materiality"]["wns"]), "power": float(cfg["noise"]["materiality"]["power_saif"])}
    d_by_design = {}
    for o in p3_diag:
        if o["cls"] == "d":
            e = d_by_design.setdefault(o["design_id"], {})
            e[o["label"]] = e.get(o["label"], 0) + 1
    contrast = {"objects": len(p3), "diagnosed": len(p3_diag), "designs": sorted({o["design_id"] for o in p3}), "map": M.build_map(p3_diag), "map_materiality": M.build_map(p3_diag, t_override=mat),
                "materiality": mat, "retention_curves": M.retention_curves(p3_diag), "non_monotone": M.non_monotone(p3_diag), "misclassification": M.misclassification_rates(p3_diag),
                "shape": M.shape(M.build_map(p3_diag)), "d_by_design": d_by_design,
                "d_harmful_blocks_synthesis": sum(1 for o in p3_diag if o["cls"] == "d" and o["label"] == "harmful" and o.get("blocks_synthesis")),
                "harmful_blocks_synthesis_by_class": {cls: sum(1 for o in p3_diag if o["cls"] == cls and o["label"] == "harmful" and o.get("blocks_synthesis")) for cls in M.CLASSES},
                "harmful_by_class": {cls: sum(1 for o in p3_diag if o["cls"] == cls and o["label"] == "harmful") for cls in M.CLASSES}}
    map_mat = M.build_map(diagnosed, t_override=mat)
    out = {"generated_at": db.now(), "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(), "floor_version": cfg["noise"].get("floor_version"), "designs": cfg["exp1"]["designs"], "contrast_phase3": contrast,
           "counts": counts, "map": map_all, "map_b0": map_b0, "map_materiality": map_mat, "materiality": mat, "retention_curves": curves, "non_monotone": nm, "literature": lit_table, "misclassification": mis,
           "predictor": pred, "n_predictor_rows": len(pred_rows), "shape": {"shape": shape, "e4_retention_by_class": rates, "basis": "B0 objects" if len(b0) >= 30 else "all diagnosed objects"},
           "floors_e4": floors, "objects": [{k: o[k] for k in ("cand_id", "design_id", "run_id", "cls", "role", "verdict", "label", "rung", "attribution", "gains")} for o in objs]}
    p = Path(C.ROOT) / "reports" / "data" / "phase4_exp1.json"
    p.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(f"objects {counts['objects']} (roles {counts['by_role']}, verdicts {counts['by_verdict']}, labels {counts['by_label']}); E4-diagnosed {len(diagnosed)}; "
          f"shape {shape} {rates}; non-monotone {nm['fraction']}; predictor AUROC {(pred.get('with_class') or {}).get('auroc') if isinstance(pred.get('with_class'), dict) else pred.get('note')}; wrote {p}")
    return 0


def cmd_snapshot(cfg, conn, name=None):
    """results/snapshots/phase4-<date>/: the four tables of the Phase 4 acceptance (evaluations, candidates, diagnoses, map)
    as CSV / JSON, restricted to the Phase 4 objects and their designs; plus runs and noise_floor for reproducibility."""
    import csv
    import datetime
    import json
    import shutil
    from pathlib import Path
    name = name or f"phase4-{datetime.datetime.now():%Y%m%d-%H%M}"
    out = Path(C.results_dir(cfg)) / "snapshots" / name
    out.mkdir(parents=True, exist_ok=True)
    cands = [dict(r) for r in conn.execute("SELECT c.* FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase4' AND r.status != 'superseded'")]
    ids = [c["cand_id"] for c in cands]
    designs = sorted({c["design_id"] for c in cands})

    def dump(rows, fname):
        if not rows:
            (out / fname).write_text("")
            return 0
        with open(out / fname, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        return len(rows)
    n = {"candidates": dump(cands, "candidates.csv")}
    evals = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        evals += [dict(r) for r in conn.execute(f"SELECT * FROM evaluations WHERE cand_id IN ({','.join('?' * len(chunk))})", chunk)]
    for did in designs:
        evals += [dict(r) for r in conn.execute("SELECT * FROM evaluations WHERE design_id=? AND is_baseline=1 AND status='ok'", (did,))]
    n["evaluations"] = dump(evals, "evaluations.csv")
    diags = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        diags += [dict(r) for r in conn.execute(f"SELECT * FROM diagnoses WHERE cand_id IN ({','.join('?' * len(chunk))})", chunk)]
    n["diagnoses"] = dump(diags, "diagnoses.csv")
    n["runs"] = dump([dict(r) for r in conn.execute("SELECT * FROM runs WHERE exp='phase4' AND status != 'superseded'")], "runs.csv")
    n["noise_floor"] = dump([dict(r) for r in conn.execute(f"SELECT * FROM noise_floor WHERE design_id IN ({','.join('?' * len(designs))})", designs)], "noise_floor.csv") if designs else 0
    src = Path(C.ROOT) / "reports" / "data" / "phase4_exp1.json"
    if src.exists():
        shutil.copy(src, out / "map.json")
    (out / "MANIFEST.json").write_text(json.dumps({"snapshot": name, "created_at": db.now(), "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(), "rows": n, "designs": designs}, indent=1) + "\n")
    print(f"snapshot {out}: {n}")
    return 0



# ----------------------------------------------------------------------------- benchmark hygiene (DECISIONS 2026-09-14 item 3)
FAILURE_CATEGORIES = (   # substring of the tool error -> category: candidate-RTL faults the synthesizer rejects (the object stays unevaluated there, rule 8)
    ("VER-294", "DC syntax error (VER-294)"),
    ("VER-262", "DC: net defined twice (VER-262)"),
    ("VER-134", "DC: blocking and nonblocking assignments to one variable (VER-134)"),
    ("ELAB-366", "DC: net driven by more than one source (ELAB-366)"),
    ("LINK-3", "DC link: port width mismatch (LINK-3)"),
    ("behavioural constructs in the Yosys netlist", "Yosys: behavioural construct left in the netlist (no library cell for it)"),
    ("Can't open include file", "missing include directory (framework defect fixed 2026-09-14)"),
)


def failure_category(meta):
    """(failed_status, category) of a failed evaluation record from its meta.json (`other (<status>)` when unknown)."""
    err = str((meta or {}).get("error") or "")
    st = (meta or {}).get("failed_status") or (meta or {}).get("status") or "?"
    for needle, cat in FAILURE_CATEGORIES:
        if needle in err:
            return st, cat
    return st, f"other ({st})"


def object_role(c):
    if c.get("arm") != LIT_ARM:
        return "B0 candidate"
    return "RTL-OPT reference" if c["design_id"].startswith("rtlopt") else ("RTLRewriter LLM sample" if (c.get("note") or "").startswith("llm") else "RTLRewriter reference")


def eval_failed_objects(cfg, conn, rows):
    """Candidates (rows with cand_id, design_id, arm, note) with a failed evaluation under some configuration and no ok
    record under it (a failed record followed by an ok one is a recovered evaluation, not a failure) -> rows with the
    configurations concerned, the failure category (FAILURE_CATEGORIES) and the first error line."""
    import json
    from pathlib import Path
    out = []
    for c in rows:
        fails = [dict(r) for r in conn.execute("SELECT config, raw_dir FROM evaluations WHERE cand_id=? AND status!='ok' ORDER BY config, eval_id DESC", (c["cand_id"],))]
        if not fails:
            continue
        oks = {r[0] for r in conn.execute("SELECT DISTINCT config FROM evaluations WHERE cand_id=? AND status='ok'", (c["cand_id"],))}
        by_cfg = {}
        for f in fails:
            if f["config"] in oks or f["config"] in by_cfg:
                continue
            mp = Path(f["raw_dir"] or "") / "meta.json"
            meta = json.loads(mp.read_text()) if mp.exists() else {}
            st, cat = failure_category(meta)
            by_cfg[f["config"]] = (st, cat, str(meta.get("error") or "")[:160])
        if not by_cfg:
            continue
        cats = sorted({v[1] for v in by_cfg.values()})
        out.append({"cand_id": c["cand_id"], "design_id": c["design_id"], "role": object_role(c), "configs": sorted(by_cfg), "category": "; ".join(cats),
                    "failed_status": sorted({v[0] for v in by_cfg.values()}), "error": next(iter(by_cfg.values()))[2]})
    return out


def cmd_hygiene(cfg, conn):
    """The literature objects that are not equivalent to their D under the protocol: suite / role, verdict (V1 port
    mismatch, V2 mismatch, SEQ falsified, tool error), the counterexample cycle and signals where available, and the
    probable cause from the record (port mismatch; a clockless pair with a mismatch is a genuine functional difference;
    a mismatch in the first cycles of a pair whose registers lack a reset points at the all-zero initial-state assumption;
    X or Z values in the mismatch point at X semantics; otherwise a genuine functional difference). Written to
    reports/data/phase4_hygiene.json; the report renders the list before the re-evaluation table."""
    import json
    from pathlib import Path
    rows = []
    for c in conn.execute("SELECT c.cand_id, c.run_id, c.design_id, c.verdict, c.v1_status, c.v2_status, c.v3_status, c.note, c.features_json, c.class_final FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          "WHERE r.exp='phase4' AND r.arm=? AND c.verdict IS NOT NULL AND c.verdict NOT IN ('proven','proven_sim_only') ORDER BY c.design_id, c.cand_id", (LIT_ARM,)):
        info_p = object_dir(cfg, c["run_id"]) / f"{c['cand_id']}.json"
        info = json.loads(info_p.read_text()) if info_p.exists() else {}
        rec, rec_dir = eq_record_for(cfg, info["eq_payload"]) if info.get("eq_payload") else (None, None)
        rec = rec or {}
        v2 = rec.get("v2") or {}
        feat = json.loads(c["features_json"]) if c["features_json"] else {}
        hist_c, hist_d = feat.get("hist_c") or {}, feat.get("hist_d") or {}
        noreset_c = sum(v for k, v in hist_c.items() if k in ("$dff", "$dffe"))
        noreset_d = sum(v for k, v in hist_d.items() if k in ("$dff", "$dffe"))
        clockless = not (info.get("eq_payload") or {}).get("clk")
        role = "RTL-OPT reference" if c["design_id"].startswith("rtlopt") else ("RTLRewriter LLM sample" if (c["note"] or "").startswith("llm") else "RTLRewriter reference")
        first = v2.get("first_mismatch")
        mism = v2.get("mismatches") or {}
        xz = any(any(ch in str(m.get(k, "")).lower() for ch in "xz") for m in mism.values() if isinstance(m, dict) for k in ("c", "d"))
        if c["verdict"] == "rejected":
            detail = str(rec.get("v1_detail") or c["note"] or "")
            if "does not elaborate" in detail or "yosys exit" in detail:
                kind, cause = "V1 elaboration failure", "the object does not elaborate in the V1 port check (Yosys parse failure; a tool boundary of the protocol, not a functional difference): " + detail[:100]
            else:
                kind, cause = "V1 port mismatch", "port mismatch: " + detail[:120]
        elif c["verdict"] == "error":
            kind, cause = "tool error", str(rec.get("error") or "no equivalence record")[:120]
        elif c["verdict"] == "sim_fail":
            kind = f"V2 mismatch at cycle {first}" + (f" ({', '.join(sorted(mism))})" if mism else "")
            if clockless:
                cause = "genuine functional difference (combinational pair, no state)"
            elif xz:
                cause = "X semantics (X / Z in the mismatching values)"
            elif first is not None and int(first) <= 4 and (noreset_c or noreset_d):
                cause = f"all-zero initial-state assumption likely (mismatch in the first cycles; registers without reset: D {noreset_d}, object {noreset_c})"
            else:
                cause = "genuine functional difference (mismatch after the start-up cycles)" + (f"; registers without reset D {noreset_d} / object {noreset_c}" if (noreset_c or noreset_d) else "")
        elif c["verdict"] == "falsified":
            kind = "SEQ falsified" + (" (counterexample saved)" if rec.get("counterexample_path") else "")
            cause = "genuine functional difference (bounded proof found a counterexample)" + (f"; registers without reset D {noreset_d} / object {noreset_c}: the all-zero start state is part of the protocol" if (noreset_c or noreset_d) else "")
        elif c["verdict"] == "inconclusive":
            kind, cause = "SEQ inconclusive (class cap reached)", "undecided: the lock-step simulation passed and the bounded proof reached its cap; not proven, so not counted, reported apart (no-discard policy, C2.5)"
        else:
            kind, cause = c["verdict"], "-"
        rows.append({"cand_id": c["cand_id"], "design_id": c["design_id"], "role": role, "verdict": c["verdict"], "kind": kind, "first_mismatch_cycle": first,
                     "mismatching_signals": sorted(mism) if isinstance(mism, dict) else [], "clockless": clockless, "registers_without_reset": {"d": noreset_d, "object": noreset_c},
                     "probable_cause": cause, "class_rule": c["class_final"], "record": rec_dir})
    by = {}
    for r in rows:
        by[r["role"]] = by.get(r["role"], 0) + 1
    out = {"generated_at": db.now(), "n": len(rows), "by_role": by, "by_verdict": {v: sum(1 for r in rows if r["verdict"] == v) for v in sorted({r["verdict"] for r in rows})}, "rows": rows}
    # synthesis evaluations that failed (2026-09-15): proven objects the synthesizer rejects under some configuration, and B0
    # candidates whose fitness evaluation failed (no verdict, never objects)
    allrows = [dict(r) for r in conn.execute("SELECT c.cand_id, c.run_id, c.design_id, c.verdict, c.label, c.note, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                                             "WHERE r.exp='phase4' AND r.status != 'superseded' AND c.rtl_path IS NOT NULL ORDER BY c.run_id, c.cand_id")]
    ef = eval_failed_objects(cfg, conn, allrows)
    proven = {r["cand_id"] for r in allrows if r.get("verdict") in ("proven", "proven_sim_only")}

    def agg(rs):
        by_cat, by_design = {}, {}
        for r in rs:
            by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
            by_design[r["design_id"]] = by_design.get(r["design_id"], 0) + 1
        return {"n": len(rs), "by_category": dict(sorted(by_cat.items())), "by_design": dict(sorted(by_design.items())), "rows": rs}
    out["eval_failed_objects"] = agg([r for r in ef if r["cand_id"] in proven])
    out["fitness_failed_candidates"] = agg([r for r in ef if r["cand_id"] not in proven and r["role"] == "B0 candidate" and "Y" in r["configs"]])
    p = Path(C.ROOT) / "reports" / "data" / "phase4_hygiene.json"
    p.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(f"{len(rows)} non-equivalent literature objects ({by}; {out['by_verdict']}); {out['eval_failed_objects']['n']} proven objects with a failed synthesis evaluation "
          f"({out['eval_failed_objects']['by_category']}); {out['fitness_failed_candidates']['n']} B0 candidates with a failed fitness evaluation ({out['fitness_failed_candidates']['by_category']}); wrote {p}")
    return 0



def cmd_diag_sample(cfg, conn):
    """PLAN 4.6 tooling: a deterministic stratified sample of the E4 diagnoses of the Phase 4 objects per label
    (`exp1.manual_check_per_class` rows, seed `exp1.manual_check_seed`, round-robin over designs) with the evidence the
    manual check reads (gains vs t_D, fingerprint, resources, log diff, the E4 record directories of D and C, the object RTL),
    and the single-flag reproduction of every absorbed object (spec 04 B.5: D with one flag alone vs C@E1). Written to
    reports/data/phase4_diagnoser_sample.json; the human verdicts go to reports/data/phase4_diagnoser_check.md (by hand)."""
    import json
    from pathlib import Path
    from src.analysis import objects as O
    from src.analysis import validation as V
    n = int(cfg["exp1"].get("manual_check_per_class", 40))
    seed = int(cfg["exp1"].get("manual_check_seed", 1))
    objs = {o["cand_id"]: o for o in O.build_object_rows(cfg, conn, "phase4")}
    rows = [dict(r) for r in conn.execute("SELECT d.cand_id, d.label, d.rung, d.capability, d.attribution, d.fp_jaccard, d.evidence_json, c.design_id, c.class_final, c.rtl_path, r.arm "
                                          "FROM diagnoses d JOIN candidates c ON c.cand_id=d.cand_id JOIN runs r ON r.run_id=c.run_id "
                                          "WHERE r.exp='phase4' AND r.status != 'superseded' AND d.label NOT IN ('nonequiv','duplicate') ORDER BY d.cand_id")]
    phi = {}

    def phi_of(did):
        if did not in phi:
            phi[did] = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (did,)).fetchone()[0]
        return phi[did]
    by_label = {}
    for r in rows:
        by_label.setdefault(r["label"], []).append(r)
    sample = []
    for label, rs in sorted(by_label.items()):
        for r in V.stratified_sample(rs, n, seed):
            o = objs.get(r["cand_id"]) or {}
            did = r["design_id"]
            base = O.baseline_row(conn, did, "E4", phi_of(did))
            ev = O.object_row_eval(conn, r["cand_id"], "E4", phi_of(did))
            fl = O.thresholds(conn, did, "E4", cfg["noise"].get("floor_version"))[1]
            dup = conn.execute("SELECT duplicate_of FROM diagnoses WHERE cand_id=?", (r["cand_id"],)).fetchone()[0]
            dup_ev = O.object_row_eval(conn, dup, "E4", phi_of(did)) if dup else None
            sample.append({"cand_id": r["cand_id"], "design_id": did, "role": o.get("role"), "class": r["class_final"], "label": label, "rung": r["rung"], "attribution": r["attribution"],
                           "fp_jaccard": r["fp_jaccard"], "evidence": json.loads(r["evidence_json"] or "{}"), "gains": o.get("gains"), "t_d": o.get("t_d"), "phi": phi_of(did),
                           "sigma_area_e4": float((fl.get("area") or {}).get("sigma_robust") or 0.0),
                           "d_raw_dir_e4": base["raw_dir"] if base else None, "c_raw_dir_e4": ev["raw_dir"] if ev else None, "duplicate_of": dup,
                           "duplicate_raw_dir_e4": dup_ev["raw_dir"] if dup_ev else None, "c_rtl": r["rtl_path"], "human": None, "human_note": None})
    repro_rows = []
    for r in rows:
        if r["label"] in ("absorbed", "absorbed_identical"):
            rep = V.single_flag_reproduction(cfg, conn, r["cand_id"], r["design_id"], phi_of(r["design_id"]))
            if rep is not None:
                repro_rows.append({"cand_id": r["cand_id"], "design_id": r["design_id"], "label": r["label"], "rung": r["rung"], "repro": rep})
    out = {"generated_at": db.now(), "per_label_total": {k: len(v) for k, v in sorted(by_label.items())}, "sample_per_label": n, "seed": seed,
           "sample": sample, "reproduction": {**V.reproduction_summary(repro_rows), "rows": repro_rows}}
    p = Path(C.ROOT) / "reports" / "data" / "phase4_diagnoser_sample.json"
    p.write_text(json.dumps(out, indent=1, default=str) + "\n")
    rs = out["reproduction"]
    print(f"diagnoses by label {out['per_label_total']}; sample {len(sample)} rows ({n} per label, seed {seed}); single-flag reproduction of {rs['n']} absorbed objects: "
          f"{rs['reproduced_by_a_single_flag']} by at least one flag ({ {k: (v['converged'], v['evaluated']) for k, v in rs['by_flag'].items()} }); wrote {p}")
    return 0


def cmd_diag_verify(cfg, conn):
    """PLAN 4.6: independent re-derivation of every sampled diagnosis from the raw DC reports (src/analysis/verify.py:
    area.rpt, qor.rpt, power_saif.rpt, timing.rpt, netlist.v; B.2 re-implemented) -> agreement with the stored label and
    gains per label, the disagreements listed for the manual reading. reports/data/phase4_diagnoser_verify.json."""
    import json
    from pathlib import Path
    from src.analysis import verify as VF
    data = Path(C.ROOT) / "reports" / "data"
    sample = json.loads((data / "phase4_diagnoser_sample.json").read_text())
    jac = float(cfg["diag"]["fp_jaccard"])
    rows, by_label = [], {}
    for r in sample["sample"]:
        d_rec = VF.record_from_reports(r.get("d_raw_dir_e4"))
        c_rec = VF.record_from_reports(r.get("c_raw_dir_e4"))
        dup_rec = VF.record_from_reports(r.get("duplicate_raw_dir_e4")) if r.get("duplicate_raw_dir_e4") else None
        e = by_label.setdefault(r["label"], {"n": 0, "unreadable": 0, "label_agree": 0, "gains_agree": 0, "disagreements": []})
        e["n"] += 1
        if d_rec is None or c_rec is None:
            e["unreadable"] += 1
            rows.append({"cand_id": r["cand_id"], "design_id": r["design_id"], "label": r["label"], "independent": None, "note": "reports unreadable"})
            continue
        ind = VF.independent_diagnosis(d_rec, c_rec, r.get("phi"), (r.get("t_d") or {}).get("E4") or {}, r.get("sigma_area_e4"), jac, duplicate_rec=dup_rec)
        stored = (r.get("evidence") or {}).get("gains") or {}
        gains_ok = all(abs(float(stored.get(m, 0.0)) - float(ind["gains"].get(m, 0.0))) <= 1e-4 for m in ("area", "wns", "power") if m in stored and m in ind["gains"])
        agree = ind["label"] == r["label"]
        e["label_agree"] += int(agree)
        e["gains_agree"] += int(gains_ok)
        row = {"cand_id": r["cand_id"], "design_id": r["design_id"], "label": r["label"], "independent": ind["label"], "label_agree": agree, "gains_agree": gains_ok,
               "stored_gains": stored, "independent_gains": ind["gains"], "jaccard_netlist": ind["jaccard"], "fp_jaccard_stored": r.get("fp_jaccard"), "up": ind["up"], "down": ind["down"],
               "endpoints_coincide": ind["endpoints_coincide"], "area_within_sigma": ind["area_within_sigma"], "d_raw_dir_e4": r.get("d_raw_dir_e4"), "c_raw_dir_e4": r.get("c_raw_dir_e4")}
        if not agree or not gains_ok:
            e["disagreements"].append(row["cand_id"])
        rows.append(row)
    n = sum(e["n"] for e in by_label.values())
    agree = sum(e["label_agree"] for e in by_label.values())
    out = {"generated_at": db.now(), "n": n, "label_agree": agree, "agreement": (agree / n) if n else None, "by_label": by_label, "rows": rows}
    (data / "phase4_diagnoser_verify.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(f"independent re-derivation of {n} sampled diagnoses: {agree} labels agree ({'-' if not n else f'{100 * agree / n:.0f} %'}); per label " +
          "; ".join(f"{k}: {v['label_agree']}/{v['n']} (gains {v['gains_agree']}, unreadable {v['unreadable']}, disagreements {len(v['disagreements'])})" for k, v in sorted(by_label.items())))
    return 0


def cmd_motivating(cfg, conn):
    """PLAN 4.9: the two objects of the motivating figure chosen by the data (src/analysis/validation.py: the largest E1 gain
    the ladder recovers, the largest retained E4 gain) with their gains along E1..E4 and the Yosys configurations ->
    reports/data/phase4_motivating.json and .md (included by reports/phase4.md)."""
    import json
    from pathlib import Path
    from src.analysis import objects as O
    from src.analysis import validation as V
    objs = O.build_object_rows(cfg, conn, "phase4", configs=V.FIGURE_CONFIGS)
    picks = V.pick_motivating([o for o in objs if o.get("label")])
    data = Path(C.ROOT) / "reports" / "data"
    (data / "phase4_motivating.json").write_text(json.dumps({"generated_at": db.now(), "configs": list(V.FIGURE_CONFIGS), "picks": picks}, indent=1, default=str) + "\n")
    md = V.motivating_md(picks, V.FIGURE_CONFIGS)
    (data / "phase4_motivating.md").write_text(md)
    print(md)
    return 0


def cmd_topup(cfg, conn, do_submit):
    """PLAN 4.1 target of `exp1.candidates_per_design` proven candidates per design: designs below the target whose B0 runs
    have all finished get one more run with the next seed (K x N calls each), up to `exp1.b0.max_runs_per_design` runs."""
    b0 = cfg["exp1"]["b0"]
    target = int(cfg["exp1"]["candidates_per_design"])
    max_runs = int(b0.get("max_runs_per_design", 1))
    todo = []
    for did in cfg["exp1"]["designs"]:
        runs = [dict(r) for r in conn.execute("SELECT run_id, seed, status FROM runs WHERE exp='phase4' AND arm='B0' AND design_id=? AND status != 'superseded' ORDER BY seed", (did,))]
        proven = conn.execute("SELECT COUNT(*) FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase4' AND r.arm='B0' AND r.status != 'superseded' AND c.design_id=? AND c.verdict IN ('proven','proven_sim_only')", (did,)).fetchone()[0]
        running = [r for r in runs if r["status"] not in ("done", "failed")]
        state = f"{did:36s} runs {len(runs)} (running {len(running)}) proven {proven} / target {target}"
        if proven >= target:
            print(state + " -> target reached")
        elif running:
            print(state + " -> a run is still going")
        elif len(runs) >= max_runs:
            print(state + f" -> max_runs_per_design {max_runs} reached (reported as is)")
        else:
            # a large shortfall (below half the target) gets every remaining run at once so that the rounds do not serialise
            per_run = max(1, int(b0["K"]) * int(b0["N"]))
            need = max(1, -(-(target - proven) // max(1, proven // max(1, len(runs)) if proven else per_run)))   # runs needed at the observed proven rate
            n_new = min(max_runs - len(runs), need if proven < target / 2 else 1)
            next_seed = max(r["seed"] for r in runs) + 1 if runs else int(b0["seed"])
            print(state + f" -> {n_new} top-up run(s) with seed(s) {list(range(next_seed, next_seed + n_new))}")
            for seed in range(next_seed, next_seed + n_new):
                todo.append((did, seed))
    if not do_submit:   # a dry run only reports (a run row without a queue job would look like a stalled run)
        print(f"{len(todo)} top-up run(s) would be created; pass --submit to create and submit them")
        return 0
    for did, seed in todo:
        create_runs(cfg, conn, [did], "phase4", b0["K"], b0["N"], seed, True, note=f"exp1 B0 top-up seed {seed}")
    return 0



# ----------------------------------------------------------------------------- recovery of failed fitness evaluations (2026-09-14: include directories)
def cmd_refit(cfg, conn, do_submit, do_apply):
    """B0 candidates whose fitness evaluation failed for a tool reason (the include directories of the design were not
    passed to the candidate's Yosys job, 2026-09-14): --submit re-submits the Y job with the design's include directories
    (the failed job id is kept in the note); --apply applies the driver's scalar verdict once the evaluation exists,
    through the run's own driver (label improved / no_gain, archive flags, state file)."""
    import json
    from src.jobqueue.core import Queue
    from src.search.driver import SearchRun
    cat = {d["design_id"]: d for d in K.load_all()}
    rows = [dict(r) for r in conn.execute("SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, c.e4_job_id, c.note FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                                          "WHERE r.exp='phase4' AND r.arm='B0' AND c.label IS NULL AND c.note LIKE '%evaluation failed%' AND c.verdict IN ('proven','proven_sim_only') ORDER BY c.run_id, c.cand_id")]
    print(f"{len(rows)} proven B0 candidates with a failed fitness evaluation")
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={}) if do_submit else None
    n_sub = n_app = 0
    by_run = {}
    for c in rows:
        d = cat[c["design_id"]]
        phi = float(conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (c["design_id"],)).fetchone()[0])
        fit_cfg = (cfg["search"]["arms"].get("B0") or {}).get("fitness", "Y")
        have = conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config=? AND status='ok' AND abs(clock_ns-?)<1e-6 LIMIT 1", (c["cand_id"], fit_cfg, phi)).fetchone()
        js = conn.execute("SELECT state FROM jobs WHERE job_id=?", (c["e4_job_id"],)).fetchone() if c["e4_job_id"] else None
        if have is None and do_submit and (js is None or js[0] in ("failed", "done")):
            j = J.dc_job(cfg, d, fit_cfg, phi, int(cfg["search"].get("job_priority", 4)))
            if cfg["configs"][fit_cfg].get("tool") == "yosys_opensta":
                j["kind"] = "yosys"
            j["payload"].update(rtl=[c["rtl_path"]], incdirs=[str(p) for p in K.abs_paths(d, d["incdirs"])], is_baseline=0, cand_id=c["cand_id"])
            jid = q.submit(j["kind"], j["payload"], design_id=c["design_id"], cand_id=c["cand_id"], config=fit_cfg, priority=j["priority"], timeout_sec=j["timeout_sec"])
            conn.execute("UPDATE candidates SET e4_job_id=?, note=COALESCE(note,'') || ? WHERE cand_id=?", (jid, f" [refit {jid} replaces {c['e4_job_id']}]", c["cand_id"]))
            conn.commit()
            n_sub += 1
        elif have is not None and do_apply:
            by_run.setdefault(c["run_id"], []).append(c["cand_id"])
    for run_id, cids in by_run.items():
        run = SearchRun.resume(cfg, conn, run_id)
        for cid in cids:
            row = run.fit_row(cid)
            entry = run.state["cands"].get(cid)
            if row is None or entry is None:
                continue
            entry.pop("e4_failed", None)
            run.scalar_verdict(cid, entry, row)
            conn.execute("UPDATE candidates SET note=COALESCE(note,'') || ' [refit applied]' WHERE cand_id=?", (cid,))
            n_app += 1
        run.save_state()
        conn.commit()
    print(f"re-submitted {n_sub}, applied {n_app}; still pending: {len(rows) - n_app}")
    return 0


def collect_duplicates(conn, exp="phase4"):
    """G5 decisions item 4 (d): the duplicate answers of the Phase 4 runs (identical RTL text within a run: label `duplicate`,
    `duplicate_of` in the diagnosis evidence) by design, by generation and by design x generation, the generation gap to
    the original answer, and the identical rewrites found by different runs of the same design (same content hash)."""
    from collections import Counter
    rows = [dict(r) for r in conn.execute("SELECT c.cand_id, c.run_id, c.design_id, c.gen, c.label, c.content_hash, r.arm, d.evidence_json, d.duplicate_of FROM candidates c "
                                          "JOIN runs r ON r.run_id = c.run_id LEFT JOIN diagnoses d ON d.cand_id = c.cand_id WHERE r.exp = ? AND r.status != 'superseded'", (exp,))]
    gen_of = {r["cand_id"]: r["gen"] for r in rows}
    total_by_design, total_by_gen, total_by_dg = Counter(), Counter(), Counter()
    for r in rows:
        total_by_design[r["design_id"]] += 1
        total_by_gen[r["gen"] or 0] += 1
        total_by_dg[(r["design_id"], r["gen"] or 0)] += 1
    dups = [r for r in rows if r["label"] == "duplicate"]
    by_design, by_gen, by_dg, by_arm, gap, per_run = Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    for r in dups:
        by_design[r["design_id"]] += 1
        by_gen[r["gen"] or 0] += 1
        by_dg[(r["design_id"], r["gen"] or 0)] += 1
        by_arm[r["arm"]] += 1
        per_run[r["run_id"]] += 1
        of = r.get("duplicate_of")
        if not of:
            try:
                of = (json.loads(r["evidence_json"] or "{}") or {}).get("duplicate_of")
            except ValueError:
                of = None
        if of in gen_of and r["gen"] is not None and gen_of[of] is not None:
            gap[int(r["gen"]) - int(gen_of[of])] += 1
        else:
            gap["unknown"] += 1
    groups = {}
    for r in rows:
        if r["label"] == "duplicate" or not r["content_hash"] or r["arm"] == LIT_ARM:
            continue
        groups.setdefault((r["design_id"], r["content_hash"]), set()).add(r["run_id"])
    cross = {k: v for k, v in groups.items() if len(v) > 1}
    cross_by_design = Counter(k[0] for k in cross)
    return {"exp": exp, "n_candidates": len(rows), "n_duplicates": len(dups), "by_arm": dict(by_arm),
            "by_design": {d: {"candidates": total_by_design[d], "duplicates": by_design.get(d, 0), "share": round(by_design.get(d, 0) / total_by_design[d], 4)} for d in sorted(total_by_design)},
            "by_gen": {str(g): {"candidates": total_by_gen[g], "duplicates": by_gen.get(g, 0), "share": round(by_gen.get(g, 0) / total_by_gen[g], 4)} for g in sorted(total_by_gen)},
            "by_design_gen": {f"{d}|{g}": {"candidates": total_by_dg[(d, g)], "duplicates": by_dg.get((d, g), 0)} for (d, g) in sorted(total_by_dg)},
            "gap_to_original": {str(k): v for k, v in sorted(gap.items(), key=lambda kv: (isinstance(kv[0], str), kv[0]))},
            "runs_with_duplicates": len(per_run), "max_per_run": max(per_run.values()) if per_run else 0,
            "cross_run_identical": {"groups": len(cross), "runs_involved": sum(len(v) for v in cross.values()), "by_design": dict(cross_by_design)}}


def cmd_duplicates(cfg, conn):
    out = collect_duplicates(conn, "phase4")
    p = Path(C.ROOT) / "reports" / "data" / "phase4_duplicates.json"
    p.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"duplicates {out['n_duplicates']} of {out['n_candidates']} candidates; by arm {out['by_arm']}; by generation " +
          ", ".join(f"g{g}: {v['duplicates']}/{v['candidates']}" for g, v in out["by_gen"].items()) + f"; cross-run identical rewrites {out['cross_run_identical']['groups']} groups")
    for d, v in out["by_design"].items():
        if v["duplicates"]:
            print(f"  {d:34s} {v['duplicates']:4d} of {v['candidates']:4d} ({100 * v['share']:.0f} %)")
    print(f"written {p}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["baselines", "generate", "smoke", "status", "objects", "verdicts", "ladder", "diagnose", "collect", "snapshot", "hygiene", "topup", "refit", "diag-sample", "diag-verify", "motivating", "duplicates"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--name", default=None)
    ap.add_argument("--hidden", action="store_true")
    ap.add_argument("--configs", nargs="*", default=None)
    ap.add_argument("--design", nargs="*", default=None)
    ap.add_argument("--K", type=int, default=None)
    ap.add_argument("--N", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--priority", type=int, default=1)
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--objects", action="store_true", help="baselines: also the designs of every proven Phase 4 object (literature designs), E1-E3 included where missing")
    ap.add_argument("--force", action="store_true", help="diagnose: re-derive the diagnosis of every proven object under the current rules (replaces the analysis rows)")
    ap.add_argument("--retry-failed", action="store_true", help="ladder: re-submit pairs whose latest record is a deterministic failure (tool rejects the RTL)")
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    b0 = cfg["exp1"]["b0"]
    if a.what == "baselines":
        return cmd_baselines(cfg, conn, a.submit, a.priority, objects=a.objects)
    if a.what == "status":
        return cmd_status(cfg, conn)
    if a.what == "objects":
        return cmd_objects(cfg, conn, a.submit, a.priority)
    if a.what == "verdicts":
        return cmd_verdicts(cfg, conn)
    if a.what == "ladder":
        return cmd_ladder(cfg, conn, a.submit, a.priority, a.hidden, a.configs, retry_failed=a.retry_failed)
    if a.what == "diagnose":
        return cmd_diagnose(cfg, conn, a.dry_run, force=a.force)
    if a.what == "collect":
        return cmd_collect(cfg, conn)
    if a.what == "snapshot":
        return cmd_snapshot(cfg, conn, a.name)
    if a.what == "diag-sample":
        return cmd_diag_sample(cfg, conn)
    if a.what == "diag-verify":
        return cmd_diag_verify(cfg, conn)
    if a.what == "motivating":
        return cmd_motivating(cfg, conn)
    if a.what == "hygiene":
        return cmd_hygiene(cfg, conn)
    if a.what == "duplicates":
        return cmd_duplicates(cfg, conn)
    if a.what == "topup":
        return cmd_topup(cfg, conn, a.submit)
    if a.what == "refit":
        return cmd_refit(cfg, conn, a.submit, a.apply)
    if a.what == "smoke":
        designs = a.design or cfg["exp1"]["designs"][:1]
        create_runs(cfg, conn, designs, "smoke", a.K or 1, a.N or 2, a.seed or 1, a.submit, note="exp1 B0 smoke")
        return 0
    designs = a.design or cfg["exp1"]["designs"]
    create_runs(cfg, conn, designs, "phase4", a.K or b0["K"], a.N or b0["N"], a.seed or b0["seed"], a.submit, note="exp1 B0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
