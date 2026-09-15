#!/usr/bin/env python3
"""Phase 4 — Exp1 (docs/PLAN.md 4.1–4.3; DECISIONS 2026-09-14 C1 scope): the objects of the map and their runs.

    .venv/bin/python scripts/phase4_exp1.py baselines [--submit] [--priority 1]   # missing D baselines at Phi_main: Y, E1d, E2g, O0-O2, Ycoevo (Exp1 + calibration designs)
    .venv/bin/python scripts/phase4_exp1.py generate  [--design ...] [--submit]   # B0 runs (Y-caliber fitness, llm.selected) on config exp1.designs, one `search` job each
    .venv/bin/python scripts/phase4_exp1.py smoke --design <id> [--K 1 --N 2] [--submit]   # rule 7: one B0 run first
    .venv/bin/python scripts/phase4_exp1.py status
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


def baseline_jobs(cfg, conn, designs, priority=1):
    cat = {d["design_id"]: d for d in K.load_all()}
    jobs = []
    for did in designs:
        d = cat[did]
        phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (did,)).fetchone()[0]
        if phi is None:
            continue
        for config in baseline_configs(cfg):
            have = conn.execute("SELECT power_default_mw FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY eval_id DESC LIMIT 1", (did, config, float(phi))).fetchone()
            if have is not None and not (cfg["configs"][config].get("tool") == "yosys_opensta" and have[0] is None):
                continue   # a Yosys record without OpenSTA power predates report_power (2026-09-14) and is refreshed (append-only: a newer record)
            if conn.execute("SELECT 1 FROM jobs WHERE design_id=? AND config=? AND cand_id IS NULL AND state IN ('queued','running') LIMIT 1", (did, config)).fetchone():
                continue   # already in the queue
            j = J.dc_job(cfg, d, config, float(phi), priority)
            if cfg["configs"][config].get("tool") == "yosys_opensta":
                j["kind"] = "yosys"
            jobs.append(j)
    return jobs


def cmd_baselines(cfg, conn, do_submit, priority):
    from src.jobqueue.core import Queue
    designs = list(cfg["exp1"]["designs"]) + [d for d in calibration_designs(cfg, conn) if d not in cfg["exp1"]["designs"]]
    jobs = baseline_jobs(cfg, conn, designs, priority)
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


def ladder_jobs(cfg, conn, configs, priority):
    import json
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
            j = J.dc_job(cfg, d, config, phi, priority)
            if cfg["configs"][config].get("tool") == "yosys_opensta":
                j["kind"] = "yosys"
            j["payload"].update(rtl=files, incdirs=[], is_baseline=0, cand_id=c["cand_id"])
            if c["top"]:
                j["payload"]["top"] = c["top"]
            if saif and j["kind"] == "dc":
                j["payload"].update(saif=saif, saif_instance="bs_lockstep/u_c")
            j["cand_id"] = c["cand_id"]
            jobs.append(j)
    return jobs


def cmd_ladder(cfg, conn, do_submit, priority, hidden, configs=None):
    """Every visible rung and supplementary Yosys configuration on every proven Phase 4 object (missing records only); with
    --hidden also the hidden configurations through scripts/hidden_worker.py --submit-candidates --exp phase4 (rule 3)."""
    from src.jobqueue.core import Queue
    visible = [c for c in cfg["exp1"]["configs"] if not cfg["configs"][c].get("hidden")]
    configs = configs or visible + ["Y"] + list(cfg["exp1"].get("supplementary") or [])
    jobs = ladder_jobs(cfg, conn, configs, priority)
    by = {}
    for j in jobs:
        by[j["config"]] = by.get(j["config"], 0) + 1
    print(f"{len(jobs)} ladder jobs on {len(phase4_objects(conn))} proven Phase 4 objects: {dict(sorted(by.items()))}")
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
        cmd = [sys.executable, os.path.join(ROOT, "scripts", "hidden_worker.py"), "--submit-candidates", "--exp", "phase4", "--priority", str(max(0, priority - 1))]
        if not do_submit:
            cmd.append("--dry-run")
        print(subprocess.run(cmd, capture_output=True, text=True).stdout.strip())
    return 0



# ----------------------------------------------------------------------------- diagnosis, map, predictor, snapshot (PLAN 4.3-4.8)
def cmd_diagnose(cfg, conn, dry_run):
    from src.analysis import objects as O
    out = O.diagnose_objects(cfg, conn, "phase4", dry_run=dry_run)
    print(("dry run: " if dry_run else "") + f"diagnosed {out['diagnosed']} (labels {out['labels']}); existing {out['existing']}, not proven {out['skipped_not_proven']}, no E4 record {out['skipped_no_e4']}")
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
    diagnosed = [o for o in objs if o.get("label") and o["label"] != "nonequiv"]
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
    out = {"generated_at": db.now(), "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(), "floor_version": cfg["noise"].get("floor_version"), "designs": cfg["exp1"]["designs"],
           "counts": counts, "map": map_all, "map_b0": map_b0, "retention_curves": curves, "non_monotone": nm, "literature": lit_table, "misclassification": mis,
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["baselines", "generate", "smoke", "status", "objects", "verdicts", "ladder", "diagnose", "collect", "snapshot"])
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
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    b0 = cfg["exp1"]["b0"]
    if a.what == "baselines":
        return cmd_baselines(cfg, conn, a.submit, a.priority)
    if a.what == "status":
        return cmd_status(cfg, conn)
    if a.what == "objects":
        return cmd_objects(cfg, conn, a.submit, a.priority)
    if a.what == "verdicts":
        return cmd_verdicts(cfg, conn)
    if a.what == "ladder":
        return cmd_ladder(cfg, conn, a.submit, a.priority, a.hidden, a.configs)
    if a.what == "diagnose":
        return cmd_diagnose(cfg, conn, a.dry_run)
    if a.what == "collect":
        return cmd_collect(cfg, conn)
    if a.what == "snapshot":
        return cmd_snapshot(cfg, conn, a.name)
    if a.what == "smoke":
        designs = a.design or cfg["exp1"]["designs"][:1]
        create_runs(cfg, conn, designs, "smoke", a.K or 1, a.N or 2, a.seed or 1, a.submit, note="exp1 B0 smoke")
        return 0
    designs = a.design or cfg["exp1"]["designs"]
    create_runs(cfg, conn, designs, "phase4", a.K or b0["K"], a.N or b0["N"], a.seed or b0["seed"], a.submit, note="exp1 B0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
