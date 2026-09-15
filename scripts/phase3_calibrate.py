#!/usr/bin/env python3
"""Phase 3 — LLM calibration (docs/PLAN.md Phase 3; config llm.calibration): the four candidate models run residual-guided
evolution (minimal skeleton: no synthesis-rung screening, full E4, no map prior yet) on the calibration designs with
K generations x N candidates and two seeds; every run is one `search` queue job (rule 9). Collect reports per model
the pass rates, the class distribution and the requested -> produced confusion matrix, the retention fraction (headline
and materiality row, proven_sim_only apart), the best retained gain per design (offset designs flagged), LLM calls /
dollars / DC hours / VC Formal hours per retained candidate, time-to-verdict distributions and inconclusive rates per
class, and applies the decision rule of config llm.calibration.decision.

    .venv/bin/python scripts/phase3_calibrate.py designs                    # the calibration set (dev designs only, rule 4)
    .venv/bin/python scripts/phase3_calibrate.py smoke  --model gpt-5.6-luna --design rtllm_accu [--K 1 --N 2] --submit
    .venv/bin/python scripts/phase3_calibrate.py submit [--models ...] [--seeds 1 2] [--K 6 --N 5] --submit
    .venv/bin/python scripts/phase3_calibrate.py status
    .venv/bin/python scripts/phase3_calibrate.py collect
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
from src.noise import stats as S  # noqa: E402
from src.search.driver import SearchRun  # noqa: E402

CATEGORY_HINTS = {"arith": ("adder", "sub", "mult", "multi", "div", "accu", "comparator", "fixed", "float", "alu"), "memory": ("RAM", "fifo", "FIFO", "LIFO", "reg", "buffer"),
                  "control": ("fsm", "counter", "detect", "traffic", "light", "signal", "freq", "pulse", "sequence"), "misc": ()}


def calibration_designs(cfg, conn, n=None):
    """Deterministic calibration set from the dev split only (CLAUDE.md rule 4): designs with a measured E4 floor and an
    E4 baseline at Phi, one per category first (arithmetic / memory / control / misc), the largest by LOC first."""
    n = int(n or cfg["llm"]["calibration"]["designs"])
    rows = [dict(r) for r in conn.execute("SELECT d.design_id, d.loc FROM designs d WHERE d.split='dev' AND d.phi_main_ns_nangate45 IS NOT NULL AND EXISTS "
                                          "(SELECT 1 FROM noise_floor n WHERE n.design_id=d.design_id AND n.config='E4' AND n.metric='area' AND n.floor_source='measured') AND EXISTS "
                                          "(SELECT 1 FROM evaluations e WHERE e.design_id=d.design_id AND e.config='E4' AND e.is_baseline=1 AND e.status='ok' AND abs(e.clock_ns-d.phi_main_ns_nangate45)<1e-6) "
                                          "ORDER BY d.loc DESC, d.design_id")]

    def cat(did):
        name = did.split("_", 1)[1] if "_" in did else did
        for c, hints in CATEGORY_HINTS.items():
            if any(h.lower() in name.lower() for h in hints):
                return c
        return "misc"
    chosen, seen_cat = [], set()
    for r in rows:
        c = cat(r["design_id"])
        if c not in seen_cat:
            chosen.append(r["design_id"])
            seen_cat.add(c)
        if len(chosen) >= n:
            break
    for r in rows:
        if len(chosen) >= n:
            break
        if r["design_id"] not in chosen:
            chosen.append(r["design_id"])
    return chosen[:n]


def submit_runs(cfg, conn, designs, models, seeds, K, N, exp, do_submit, note=""):
    from src.jobqueue.core import Queue
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    runs = []
    for model in models:
        for did in designs:
            for seed in seeds:
                run = SearchRun.create(cfg, conn, exp=exp, arm="M", design_id=did, seed=seed, model=model, K=K, N=N, queue=q, note=note)
                runs.append(run.run_id)
                if do_submit:
                    q.submit("search", {"run_id": run.run_id}, design_id=did, config="search", priority=3, timeout_sec=12 * 3600)
    print(f"{len(runs)} runs ({len(models)} models x {len(designs)} designs x {len(seeds)} seeds, K={K}, N={N}, exp={exp})" + (" submitted" if do_submit else " created (not submitted)"))
    return runs


def auroc(scores_pos, scores_neg):
    """Area under the ROC curve of a score that should be higher for positives (ties count half); None when a class is empty."""
    if not scores_pos or not scores_neg:
        return None
    wins = 0.0
    for p in scores_pos:
        for n in scores_neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(scores_pos) * len(scores_neg))


def y_jobs(cfg, conn, do_submit):
    """Y (Yosys + OpenSTA) evaluations of every E4-evaluated Phase 3 candidate and of D at Phi_main, for AUROC(Y -> E4
    retention) (PLAN 3 acceptance; DECISIONS 2026-09-14 G3.1). Missing records only; `yosys` jobs on the local pool."""
    from src.designs import catalog as K
    from src.designs import jobs as J
    from src.jobqueue.core import Queue
    designs = {d["design_id"]: d for d in K.load_all()}
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    jobs = []
    seen_design = set()
    for c in conn.execute("SELECT c.cand_id, c.design_id, c.rtl_path FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase3' AND r.status != 'superseded' AND c.e4_job_id IS NOT NULL"):
        d = designs[c["design_id"]]
        phi = float(conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (c["design_id"],)).fetchone()[0])
        if c["design_id"] not in seen_design:
            seen_design.add(c["design_id"])
            if conn.execute("SELECT 1 FROM evaluations WHERE design_id=? AND config='Y' AND is_baseline=1 AND status='ok' AND abs(clock_ns-?)<1e-6 LIMIT 1", (c["design_id"], phi)).fetchone() is None:
                j = J.dc_job(cfg, d, "Y", phi, 3)
                j["kind"] = "yosys"
                jobs.append(j)
        if conn.execute("SELECT 1 FROM evaluations WHERE design_id=? AND cand_id=? AND config='Y' AND status='ok' LIMIT 1", (c["design_id"], c["cand_id"])).fetchone():
            continue
        j = J.dc_job(cfg, d, "Y", phi, 3)
        j["kind"] = "yosys"
        j["payload"].update(rtl=[c["rtl_path"]], incdirs=[], is_baseline=0, cand_id=c["cand_id"])
        j["cand_id"] = c["cand_id"]
        jobs.append(j)
    print(f"{len(jobs)} Y jobs (candidates of the Phase 3 runs and their baselines, missing records only)")
    if do_submit:
        for j in jobs:
            q.submit(j["kind"], j["payload"], design_id=j["design_id"], cand_id=j.get("cand_id"), config="Y", priority=j["priority"], timeout_sec=j["timeout_sec"])
        print(f"submitted {len(jobs)} yosys jobs")
    return jobs


def y_auroc(cfg, conn):
    """AUROC of the Y area gain (and of the best-of-three-components Y gain) for E4 retention over the diagnosed candidates."""
    pos, neg, pos3, neg3 = [], [], [], []
    for c in conn.execute("SELECT c.cand_id, c.design_id, c.label FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase3' AND r.status != 'superseded' AND c.label IN ('retained','absorbed','absorbed_identical','noise','harmful','tradeoff','fragile','duplicate')"):
        phi = float(conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (c["design_id"],)).fetchone()[0])
        base = conn.execute("SELECT area_um2, wns_ns, power_default_mw FROM evaluations WHERE design_id=? AND config='Y' AND is_baseline=1 AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY eval_id DESC LIMIT 1", (c["design_id"], phi)).fetchone()
        cand = conn.execute("SELECT area_um2, wns_ns, power_default_mw FROM evaluations WHERE design_id=? AND cand_id=? AND config='Y' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (c["design_id"], c["cand_id"])).fetchone()
        if base is None or cand is None or not base["area_um2"]:
            continue
        g_area = (float(base["area_um2"]) - float(cand["area_um2"])) / float(base["area_um2"])
        g_wns = ((float(cand["wns_ns"] or 0) - float(base["wns_ns"] or 0)) / phi) if phi else 0.0
        g_pow = ((float(base["power_default_mw"]) - float(cand["power_default_mw"])) / float(base["power_default_mw"])) if base["power_default_mw"] and cand["power_default_mw"] else 0.0
        (pos if c["label"] == "retained" else neg).append(g_area)
        (pos3 if c["label"] == "retained" else neg3).append(max(g_area, g_wns, g_pow))
    return {"n_retained": len(pos), "n_other": len(neg), "auroc_area": auroc(pos, neg), "auroc_best_component": auroc(pos3, neg3)}


def cmd_sample(cfg, conn, n=40, seed=1):
    """PLAN 3.5: a stratified sample of diagnosed candidates for the manual verification (reading both netlists and logs):
    up to n candidates spread over the labels, deterministic; the checklist lists the evidence and the raw directories."""
    import random
    rows = [dict(r) for r in conn.execute("SELECT c.cand_id, c.run_id, c.design_id, c.llm_model, c.class_requested, c.class_final, c.rtl_path, d.label, d.rung, d.evidence_json "
                                          "FROM candidates c JOIN diagnoses d ON d.cand_id=c.cand_id JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase3' AND r.status != 'superseded' ORDER BY c.cand_id")]
    by = {}
    for r in rows:
        by.setdefault(r["label"], []).append(r)
    rng = random.Random(seed)
    labels = sorted(by)
    quota = {lab: max(1, n // len(labels)) for lab in labels} if labels else {}
    sample = []
    for lab in labels:
        pool = by[lab][:]
        rng.shuffle(pool)
        sample += pool[:quota[lab]]
    rest = [r for lab in labels for r in by[lab] if r not in sample]
    rng.shuffle(rest)
    sample += rest[:max(0, n - len(sample))]
    out = Path(C.ROOT) / "reports" / "data" / "phase3_manual_sample.json"
    out.write_text(json.dumps({"seed": seed, "n": len(sample), "labels": {lab: len(v) for lab, v in by.items()}, "sample": sample}, indent=1, default=str) + "\n")
    md = [f"# Phase 3 manual verification sample ({len(sample)} of {len(rows)} diagnosed candidates, seed {seed})", "",
          "| # | design | model | requested -> produced | label (rung) | E4 raw dir | candidate RTL | agree? | note |", "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(sample, 1):
        raw = conn.execute("SELECT raw_dir FROM evaluations WHERE cand_id=? AND config='E4' ORDER BY eval_id DESC LIMIT 1", (r["cand_id"],)).fetchone()
        md.append(f"| {i} | {r['design_id']} | {r['llm_model']} | {r['class_requested']} -> {r['class_final']} | {r['label']} ({r['rung'] or '-'}) | {raw[0] if raw else '-'} | {r['rtl_path']} |  |  |")
    (Path(C.ROOT) / "reports" / "data" / "phase3_manual_sample.md").write_text("\n".join(md) + "\n")
    print(f"{len(sample)} sampled from {len(rows)} diagnosed candidates over labels {dict((lab, len(v)) for lab, v in by.items())}; wrote {out} and the .md checklist")
    return 0


def cmd_verify(cfg, conn):
    """PLAN 3.5 manual verification support: for every sampled candidate print the raw evidence the operator checks by hand
    (D's and C's E4 numbers re-read from the raw qor / area reports, the diff size of the RTL, the fingerprint equality,
    the duplicate's content match) next to the diagnoser's label, and write reports/data/phase3_manual_verify.json with the
    automatic consistency checks; the operator's verdicts go into the .md checklist."""
    import difflib
    sample = json.loads((Path(C.ROOT) / "reports" / "data" / "phase3_manual_sample.json").read_text())["sample"]
    designs = {d["design_id"]: d for d in __import__("src.designs.catalog", fromlist=["load_all"]).load_all()}
    out = []
    for r in sample:
        d = designs[r["design_id"]]
        d_text = "\n".join(Path(d["_dir"], f).read_text(errors="replace") for f in d["files"])
        c_text = Path(r["rtl_path"]).read_text(errors="replace") if r.get("rtl_path") and Path(r["rtl_path"]).exists() else ""
        ratio = difflib.SequenceMatcher(None, d_text, c_text).ratio() if c_text else None
        phi = float(conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (r["design_id"],)).fetchone()[0])
        base = conn.execute("SELECT area_um2, cells, wns_ns, power_saif_mw, hist_json, raw_dir FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (r["design_id"], phi)).fetchone()
        cand = conn.execute("SELECT area_um2, cells, wns_ns, power_saif_mw, hist_json, raw_dir FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (r["cand_id"],)).fetchone()

        def qor_area(raw_dir):
            p = Path(raw_dir or "/nonexistent") / "outputs" / "reports" / "area.rpt"
            if not p.exists():
                return None
            for line in p.read_text(errors="replace").splitlines():
                if line.startswith("Total cell area:"):
                    return float(line.split(":")[1])
            return None
        ev = json.loads(r.get("evidence_json") or "{}")
        item = {"cand_id": r["cand_id"], "design_id": r["design_id"], "model": r["llm_model"], "label": r["label"], "class": f"{r['class_requested']}->{r['class_final']}",
                "rtl_diff_ratio": round(ratio, 3) if ratio is not None else None,
                "d_area_db": base["area_um2"] if base else None, "c_area_db": cand["area_um2"] if cand else None,
                "d_area_rpt": qor_area(base["raw_dir"]) if base else None, "c_area_rpt": qor_area(cand["raw_dir"]) if cand else None,
                "d_cells": base["cells"] if base else None, "c_cells": cand["cells"] if cand else None,
                "gains_recorded": ev.get("gains"), "fp_jaccard": ev.get("fp_jaccard"), "checks": {}}
        if base and cand:
            item["checks"]["area_db_matches_report"] = (item["d_area_rpt"] is None or abs(item["d_area_rpt"] - base["area_um2"]) < 1e-3) and (item["c_area_rpt"] is None or abs(item["c_area_rpt"] - cand["area_um2"]) < 1e-3)
            g_area = (base["area_um2"] - cand["area_um2"]) / base["area_um2"]
            item["checks"]["gain_recomputed_matches"] = abs(g_area - float((ev.get("gains") or {}).get("area", g_area))) < 1e-4
            item["checks"]["identical_hist_iff_absorbed_identical"] = ((base["hist_json"] == cand["hist_json"] and abs(base["area_um2"] - cand["area_um2"]) < 1e-6) == (r["label"] == "absorbed_identical"))
        if r["label"] == "duplicate":
            # two kinds (spec 04 §B.2): an identical answer text (no evaluation, id suffixed _dup) or an identical E4 fingerprint of an earlier candidate
            dup = conn.execute("SELECT duplicate_of FROM diagnoses WHERE cand_id=?", (r["cand_id"],)).fetchone()
            other = conn.execute("SELECT rtl_path FROM candidates WHERE cand_id=?", (dup[0],)).fetchone() if dup and dup[0] else None
            if cand is not None and dup and dup[0]:
                o = conn.execute("SELECT area_um2, cells, hist_json FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (dup[0],)).fetchone()
                item["checks"]["duplicate_fingerprint_identical"] = bool(o and o["hist_json"] == cand["hist_json"] and abs(float(o["area_um2"]) - float(cand["area_um2"])) < 1e-6)
                item["duplicate_of"] = dup[0]
            else:
                item["checks"]["duplicate_text_identical"] = bool(other and Path(other[0]).exists() and Path(other[0]).read_text() == c_text) if other else None
        if r["label"] == "nonequiv":
            v = conn.execute("SELECT verdict, v2_status, v3_status FROM candidates WHERE cand_id=?", (r["cand_id"],)).fetchone()
            item["checks"]["stack_verdict"] = dict(v) if v else None
        out.append(item)
        print(f"{item['cand_id']} {item['design_id']:24s} {item['model']:13s} {item['label']:19s} {item['class']:8s} diff={item['rtl_diff_ratio']} "
              f"D area {item['d_area_db']} C area {item['c_area_db']} cells {item['d_cells']}->{item['c_cells']} gains={item['gains_recorded']} checks={item['checks']}")
    p = Path(C.ROOT) / "reports" / "data" / "phase3_manual_verify.json"
    p.write_text(json.dumps(out, indent=1, default=str) + "\n")
    ok = sum(1 for i in out if i["checks"] and all(v is True or isinstance(v, dict) for v in i["checks"].values()))
    print(f"{ok} of {len(out)} sampled candidates pass every automatic consistency check; wrote {p}")
    return 0


def label_sensitivity(cfg, conn):
    """Per model, the verdict distribution of every E4-evaluated candidate (a) as diagnosed at run time (stored), (b)
    re-diagnosed under the current rule-A floors (design-weighted pooled minimum, adopted 2026-09-14), (c) under rule A
    with the rejected record-weighted pooled minimum, (d) under the fixed materiality thresholds. No tool runs: the stored
    E4 records are re-read. Archived in reports/data/phase3_label_sensitivity.json for the paper's protocol section."""
    from src.diagnose import m3
    from src.search.driver import record_from_row
    mat = cfg["noise"]["materiality"]
    nz = cfg["noise"]
    k, q = float(nz["k_sigma"]), float(nz.get("pooled_quantile", 0.9))
    # the record-weighted pooled minimum over the set designs (the rejected variant), for the comparison column
    set_list = [{"design_id": r["design_id"], "phi": float(r["phi_main_ns_nangate45"])} for r in conn.execute(
        "SELECT design_id, phi_main_ns_nangate45 FROM designs WHERE split IN ('dev','held') AND phi_main_ns_nangate45 IS NOT NULL")]
    proven_all = S.proven_by_design(conn)
    pooled_record = S.pooled_minimum(conn, set_list, "E4", proven_all, q, 1e-6, "record")
    pooled_design = S.pooled_minimum(conn, set_list, "E4", proven_all, q, 1e-6, "design")
    out, floors, bases = {}, {}, {}
    variants = ("stored", "design_weighted", "record_weighted", "materiality")
    for c in conn.execute("SELECT c.cand_id, c.design_id, c.label, c.class_final, r.llm_model FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          "WHERE r.exp='phase3' AND r.status != 'superseded' AND c.e4_job_id IS NOT NULL AND c.label IS NOT NULL"):
        did = c["design_id"]
        if did not in floors:
            fl = S.latest_floor(conn, did, "E4")
            sig = {"area": (fl.get("area") or {}).get("sigma_robust") or 0.0, "wns": (fl.get("wns") or {}).get("sigma_robust") or 0.0, "power": (fl.get("power_saif") or {}).get("sigma_robust") or 0.0}
            mx = {"area": (fl.get("area") or {}).get("max_abs") or 0.0, "wns": (fl.get("wns") or {}).get("max_abs") or 0.0, "power": (fl.get("power_saif") or {}).get("max_abs") or 0.0}
            th_design = {m: S.rule_a_threshold(sig[m], mx[m], pooled_design.get({"power": "power_saif"}.get(m, m)), k) for m in sig}
            th_record = {m: S.rule_a_threshold(sig[m], mx[m], pooled_record.get({"power": "power_saif"}.get(m, m)), k) for m in sig}
            cls = next((r.get("floor_class") for r in fl.values() if r.get("floor_class")), None)
            floors[did] = (th_design, th_record, sig, cls)
            phi = float(conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (did,)).fetchone()[0])
            b = conn.execute("SELECT * FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (did, phi)).fetchone()
            bases[did] = (record_from_row(b) if b else None, phi)
        base, phi = bases[did]
        row = conn.execute("SELECT * FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (c["cand_id"],)).fetchone()
        m = out.setdefault(c["llm_model"], {v: {} for v in variants} | {"n": 0})
        if base is None or row is None:
            continue
        m["n"] += 1
        m["stored"][c["label"]] = m["stored"].get(c["label"], 0) + 1
        cand = record_from_row(row)
        th_d, th_r, sig, cls = floors[did]
        for name, th in (("design_weighted", th_d), ("record_weighted", th_r), ("materiality", {"area": mat["area"], "wns": mat["wns"], "power": mat["power_saif"]})):
            dg = m3.diagnose(base, cand, sig, phi, thresholds=th, floor_class=cls, k_sigma=k, fp_jaccard=float(cfg["diag"]["fp_jaccard"]))
            m[name][dg["label"]] = m[name].get(dg["label"], 0) + 1
    out["_floors"] = {did: {"design_weighted_t_d": f[0], "record_weighted_t_d": f[1], "class": f[3]} for did, f in floors.items()}
    out["_pooled_min"] = {"design_weighted": pooled_design, "record_weighted": pooled_record, "materiality": mat}
    (Path(C.ROOT) / "reports" / "data" / "phase3_label_sensitivity.json").write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    return out


def feedback_response(cfg, conn):
    """DECISIONS 2026-09-14 (pre-Phase-4 b): per model and generation, the absorbed_identical rate among candidates whose
    lineage feedback (the parent chain's stored feedback blocks, depth search.feedback_depth; a fresh start from D sees the
    most recent verdicts of the run) contained an absorbed verdict, versus candidates whose feedback did not."""
    depth = int(cfg["search"]["feedback_depth"])
    out = {}
    for run in conn.execute("SELECT run_id, llm_model FROM runs WHERE exp='phase3' AND status != 'superseded'"):
        state_path = Path(C.ROOT) / "results" / "candidates" / run["run_id"] / "state.json"
        if not state_path.exists():
            continue
        st = json.loads(state_path.read_text())
        cands, fb = st.get("cands") or {}, st.get("feedback") or {}
        by_gen = {}
        for c in cands.values():
            by_gen.setdefault(c.get("gen"), []).append(c)
        for c in cands.values():
            if c.get("label") in (None, "aborted") or c.get("gen") is None:
                continue
            # reconstruct the feedback the candidate's prompt carried: its lineage, else the most recent verdicts before its generation
            blocks, cid, seen_absorbed = [], c.get("parent_id"), False
            while cid and len(blocks) < depth:
                if cid in fb:
                    blocks.append(fb[cid])
                cid = (cands.get(cid) or {}).get("parent_id")
            if not blocks:
                earlier = [x for g, xs in by_gen.items() if g is not None and g < c["gen"] for x in xs if x["cand_id"] in fb]
                earlier.sort(key=lambda x: -x.get("gen", 0))
                blocks = [fb[x["cand_id"]] for x in earlier[:depth]]
            seen_absorbed = any((b.get("diagnosis") or "").startswith("absorbed") for b in blocks)
            key = (run["llm_model"], int(c["gen"]), "with_absorbed_feedback" if seen_absorbed else "without")
            e = out.setdefault(key, {"n": 0, "absorbed_identical": 0})
            e["n"] += 1
            e["absorbed_identical"] += int(c.get("label") == "absorbed_identical")
    table = {}
    for (model, gen, kind), e in out.items():
        table.setdefault(model, {}).setdefault(str(gen), {})[kind] = {"n": e["n"], "absorbed_identical": e["absorbed_identical"], "rate": e["absorbed_identical"] / e["n"] if e["n"] else None}
    return table


def vcf_projection(cfg, conn):
    """DECISIONS 2026-09-14 (pre-Phase-4 e): VC Formal hours of Phase 5 at the planned scale with luna, projected from the
    Phase 3 time-to-verdict distributions (SEQ seconds per produced class and per design type: arithmetic pipelines vs the
    rest), assuming the calibration's per-class mix of proven candidates per LLM call."""
    sc = cfg["scale"]
    runs_p5 = int(sc["starting_points"]) * len(sc["arms"]) * int(sc["seeds"])
    calls_p5 = runs_p5 * int(sc["budget"]["llm_calls_per_run"])
    calls_p3 = 0
    secs = {"arith_pipeline": {}, "other": {}}
    for c in conn.execute("SELECT c.design_id, c.class_final, c.v3_seconds, r.llm_model FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase3' AND r.status != 'superseded' AND r.llm_model=? AND c.v3_seconds IS NOT NULL", (cfg["llm"]["selected"],)):
        kind = "arith_pipeline" if "pipe" in c["design_id"] or "mult" in c["design_id"] else "other"
        secs[kind].setdefault(c["class_final"] or "?", []).append(float(c["v3_seconds"]))
    calls_p3 = conn.execute("SELECT COALESCE(SUM(llm_calls),0) FROM runs WHERE exp='phase3' AND status != 'superseded' AND llm_model=?", (cfg["llm"]["selected"],)).fetchone()[0]
    total_secs = sum(sum(v) for k in secs.values() for v in k.values())
    per_call = total_secs / calls_p3 if calls_p3 else 0.0
    # design-type shares in Phase 5: the starting-point pool (held designs minus the Exp1 set) by name heuristic
    pool = [r[0] for r in conn.execute("SELECT design_id FROM designs WHERE split='held' AND phi_main_ns_nangate45 IS NOT NULL")]
    excluded = set(cfg["design_sets"].get("phase5_excluded") or [])
    pool = [d for d in pool if d not in excluded]
    share_arith = sum(1 for d in pool if "pipe" in d or "mult" in d or "div" in d) / len(pool) if pool else 0.0
    # per-call SEQ seconds by design type in Phase 3 (luna): arithmetic pipelines vs other designs
    calls_by_type = {"arith_pipeline": 0, "other": 0}
    for r in conn.execute("SELECT design_id, llm_calls FROM runs WHERE exp='phase3' AND status != 'superseded' AND llm_model=?", (cfg["llm"]["selected"],)):
        calls_by_type["arith_pipeline" if "pipe" in r["design_id"] or "mult" in r["design_id"] else "other"] += int(r["llm_calls"] or 0)
    per_call_type = {k: (sum(sum(v) for v in secs[k].values()) / calls_by_type[k] if calls_by_type[k] else 0.0) for k in secs}
    hours_p5 = calls_p5 * (share_arith * per_call_type["arith_pipeline"] + (1 - share_arith) * per_call_type["other"]) / 3600.0
    hours_p5_flat = calls_p5 * per_call / 3600.0
    by_class = {k: {cls: {"n": len(v), "median_s": S.quantile(v, 0.5), "q95_s": S.quantile(v, 0.95), "hours": sum(v) / 3600.0} for cls, v in d.items()} for k, d in secs.items()}
    # the proposal of DECISIONS 2026-09-14 e when the projection exceeds the threshold: (c1) / (d) verdicts of arithmetic
    # pipelines capped at `cap_h` hours (the verdict becomes inconclusive at the cap, never discarded) -> projected hours
    cap_h = 2.0
    capped = {k: {cls: [min(x, cap_h * 3600.0) if (k == "arith_pipeline" and cls in ("c1", "d")) else x for x in v] for cls, v in d.items()} for k, d in secs.items()}
    per_call_capped = {k: (sum(sum(v) for v in capped[k].values()) / calls_by_type[k] if calls_by_type[k] else 0.0) for k in capped}
    hours_p5_capped = calls_p5 * (share_arith * per_call_capped["arith_pipeline"] + (1 - share_arith) * per_call_capped["other"]) / 3600.0
    n_over_cap = sum(1 for cls in ("c1", "d") for x in secs["arith_pipeline"].get(cls, []) if x > cap_h * 3600.0)
    n_arith_c1d = sum(len(secs["arith_pipeline"].get(cls, [])) for cls in ("c1", "d"))
    return {"model": cfg["llm"]["selected"], "phase5_runs": runs_p5, "phase5_calls": calls_p5, "phase3_calls": calls_p3, "seq_seconds_per_call": per_call,
            "seq_seconds_per_call_by_type": per_call_type, "starting_pool": len(pool), "share_arith_pipeline_in_pool": share_arith,
            "projected_vcf_hours": hours_p5, "projected_vcf_hours_flat_mix": hours_p5_flat, "by_type_and_class": by_class, "threshold_hours": 2000,
            "proposal_cap_hours": cap_h, "projected_vcf_hours_with_cap": hours_p5_capped, "arith_c1d_verdicts": n_arith_c1d, "arith_c1d_over_cap": n_over_cap}


def cmd_m6_sample(cfg, conn, n=60, seed=2):
    """DECISIONS 2026-09-14 (pre-Phase-4 a): a stratified sample of Phase 3 candidates over the produced classes for the
    manual M6 validation, with emphasis on the (d) versus (a)/(b) boundary and on (c1): quotas d 24, c1 16, a 10, b 10.
    Writes reports/data/phase3_m6_sample.json and a review file with the unified diff of every sampled candidate."""
    import difflib
    import random
    from src.designs import catalog as K
    quotas = {"d": 24, "c1": 16, "a": 10, "b": 10}
    rows = [dict(r) for r in conn.execute("SELECT c.cand_id, c.design_id, c.llm_model, c.class_requested, c.class_final, c.rtl_path, c.label, c.subtags_json "
                                          "FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase3' AND r.status != 'superseded' AND c.label NOT IN ('aborted','duplicate','prescreened') "
                                          "AND c.rtl_path IS NOT NULL ORDER BY c.cand_id")]
    rng = random.Random(seed)
    by = {}
    for r in rows:
        by.setdefault(r["class_final"], []).append(r)
    sample = []
    for cls, q in quotas.items():
        pool = by.get(cls, [])[:]
        rng.shuffle(pool)
        sample += pool[:q]
    designs = {d["design_id"]: d for d in K.load_all()}
    review = ["# M6 manual validation sample (DECISIONS 2026-09-14 a)", "",
              "Classes per spec 04 §A.1 ((a) combinational rewrite, (b) latency-preserving coding / structural refactor, (c1) latency-preserving sequential restructuring, "
              "(c2) latency / interface-timing change, (d) algorithm / architecture replacement); the operational protocol of the human labels is written in "
              "reports/data/phase3_m6_human.json, which also holds the human class and a one-line basis for every sampled candidate.", ""]
    for i, r in enumerate(sample, 1):
        d = designs[r["design_id"]]
        d_text = "\n".join(Path(d["_dir"], f).read_text(errors="replace") for f in d["files"])
        c_text = Path(r["rtl_path"]).read_text(errors="replace")
        diff = list(difflib.unified_diff(d_text.splitlines(), c_text.splitlines(), "D", "C", lineterm="", n=2))
        review += [f"## {i}. {r['cand_id']} — {r['design_id']} — {r['llm_model']} — requested {r['class_requested']} -> rule {r['class_final']} — label {r['label']}", "",
                   f"rule evidence: {r['subtags_json']}", "", "```diff"] + diff[:400] + (["... (diff truncated)"] if len(diff) > 400 else []) + ["```", ""]
    out = Path(C.ROOT) / "reports" / "data" / "phase3_m6_sample.json"
    out.write_text(json.dumps({"seed": seed, "quotas": quotas, "sample": sample}, indent=1, default=str) + "\n")
    (Path(C.ROOT) / "reports" / "data" / "phase3_m6_review.md").write_text("\n".join(review) + "\n")
    print(f"{len(sample)} sampled ({dict((c, sum(1 for s in sample if s['class_final'] == c)) for c in quotas)}); wrote {out} and phase3_m6_review.md")
    return 0


def cmd_status(cfg, conn):
    for r in conn.execute("SELECT run_id, design_id, llm_model, seed, status, gens_done, llm_calls, spent_usd, spent_dc_hours FROM runs WHERE exp IN ('phase3','smoke') AND status != 'superseded' ORDER BY started_at"):
        n = conn.execute("SELECT COUNT(*), SUM(label='retained'), SUM(label IS NULL) FROM candidates WHERE run_id=?", (r["run_id"],)).fetchone()
        print(f"{r['run_id']:44s} {r['design_id']:28s} {r['llm_model']:14s} s{r['seed']} {r['status']:8s} gens {r['gens_done']} calls {r['llm_calls']} "
              f"usd {r['spent_usd'] or 0:.3f} dc_h {r['spent_dc_hours'] or 0:.2f} cands {n[0]} retained {n[1] or 0} pending {n[2] or 0}")
    print("phase3 LLM spend:", round(conn.execute("SELECT COALESCE(SUM(amount),0) FROM budget_ledger WHERE phase='phase3_calibration' AND kind='llm'").fetchone()[0], 3), "USD")
    return 0


def cmd_collect(cfg, conn):
    mat = cfg["noise"]["materiality"]
    runs = [dict(r) for r in conn.execute("SELECT * FROM runs WHERE exp='phase3' AND status != 'superseded'")]
    per_model = {}
    for run in runs:
        m = per_model.setdefault(run["llm_model"], {"runs": 0, "designs": set(), "calls": 0, "usd": 0.0, "dc_h": 0.0, "vcf_h": 0.0, "cands": 0, "unusable": 0,
                                                    "v1_ok": 0, "v3_proven": 0, "proven_sim_only": 0, "inconclusive": 0, "labels": {}, "classes": {}, "confusion": {},
                                                    "retained_material": 0, "best_gain": {}, "ttv": {}, "inconclusive_by_class": {}, "n_by_class": {}, "offset_retained": 0, "absorbed_response": [0, 0]})
        m["runs"] += 1
        m["designs"].add(run["design_id"])
        m["calls"] += int(run["llm_calls"] or 0)
        m["usd"] += float(run["spent_usd"] or 0)
        m["dc_h"] += float(run["spent_dc_hours"] or 0)
        m["vcf_h"] += float(run["spent_vcf_hours"] or 0)
        m["unusable"] += len(list((Path(C.ROOT) / "results" / "candidates" / run["run_id"]).glob("unusable_*.json")))
        floor = S.latest_floor(conn, run["design_id"], "E4")
        offset = any(r.get("floor_class") == "offset" for r in floor.values())
        base = conn.execute("SELECT area_um2, wns_ns, power_saif_mw, power_default_mw FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND status='ok' ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (run["design_id"],)).fetchone()
        for c in conn.execute("SELECT c.*, d.label AS dlabel, d.evidence_json FROM candidates c LEFT JOIN diagnoses d ON d.cand_id=c.cand_id WHERE c.run_id=?", (run["run_id"],)):
            c = dict(c)
            m["cands"] += 1
            m["v1_ok"] += int(c.get("v1_status") == "ok")
            m["v3_proven"] += int(c.get("verdict") == "proven")
            m["proven_sim_only"] += int(c.get("verdict") == "proven_sim_only")
            m["inconclusive"] += int(c.get("v3_status") == "inconclusive")
            cls = c.get("class_final") or "?"
            m["classes"][cls] = m["classes"].get(cls, 0) + 1
            key = f"{c.get('class_requested')}->{cls}"
            m["confusion"][key] = m["confusion"].get(key, 0) + 1
            m["n_by_class"][cls] = m["n_by_class"].get(cls, 0) + 1
            if c.get("v3_status") == "inconclusive":
                m["inconclusive_by_class"][cls] = m["inconclusive_by_class"].get(cls, 0) + 1
            if c.get("time_to_verdict_s") is not None:
                m["ttv"].setdefault(cls, []).append(float(c["time_to_verdict_s"]))
            lab = c.get("label") or c.get("dlabel") or "pending"
            m["labels"][lab] = m["labels"].get(lab, 0) + 1
            ev = json.loads(c.get("evidence_json") or "{}") if c.get("evidence_json") else {}
            g = ev.get("gains") or {}
            if lab == "retained":
                if offset:
                    m["offset_retained"] += 1
                best = m["best_gain"].setdefault(run["design_id"], {"area": 0.0, "offset_design": offset})
                best["area"] = max(best["area"], float(g.get("area") or 0.0))
            # materiality sensitivity row: a fixed threshold instead of rule A
            if c.get("verdict") == "proven" and g:
                up = [k for k in g if float(g[k]) > float(mat.get({"power": "power_saif"}.get(k, k), 1.0))]
                down = [k for k in g if float(g[k]) < -float(mat.get({"power": "power_saif"}.get(k, k), 1.0))]
                m["retained_material"] += int(bool(up) and not down)
            # response to "absorbed" feedback: a child of an absorbed parent that is not absorbed itself
            if c.get("parent_id"):
                pl = conn.execute("SELECT label FROM candidates WHERE cand_id=?", (c["parent_id"],)).fetchone()
                if pl and pl[0] in ("absorbed", "absorbed_identical"):
                    m["absorbed_response"][1] += 1
                    m["absorbed_response"][0] += int(lab not in ("absorbed", "absorbed_identical", "duplicate"))
    out = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "models": {}}
    for model, m in per_model.items():
        retained = m["labels"].get("retained", 0)
        ttv = {cls: {"n": len(v), "median": statistics.median(v), "q95": S.quantile(v, 0.95), "max": max(v)} for cls, v in m["ttv"].items() if v}
        out["models"][model] = {**{k: v for k, v in m.items() if k not in ("designs", "ttv")}, "designs": sorted(m["designs"]), "retained": retained,
                                "retained_per_usd": (retained / m["usd"]) if m["usd"] else None, "retained_per_dc_hour": (retained / m["dc_h"]) if m["dc_h"] else None,
                                "llm_calls_per_retained": (m["calls"] / retained) if retained else None, "time_to_verdict": ttv,
                                "inconclusive_rate_by_class": {cls: m["inconclusive_by_class"].get(cls, 0) / n for cls, n in m["n_by_class"].items() if n}}
    dec = cfg["llm"]["calibration"]["decision"]
    scored = {mo: (v.get("retained_per_usd") or 0.0) for mo, v in out["models"].items()}
    best_gain_by_model = {mo: max((b["area"] for b in v["best_gain"].values()), default=0.0) for mo, v in out["models"].items()}
    strongest = max(best_gain_by_model.values(), default=0.0)
    eligible = [mo for mo, v in out["models"].items() if best_gain_by_model[mo] >= float(dec["floor_best_gain_ratio"]) * strongest
                and (not dec.get("require_c1_or_d_retained") or any(k.endswith("c1") or k.endswith("d") for k in v["confusion"] if v["labels"].get("retained")))]
    out["decision"] = {"primary_metric": dec["primary_metric"], "scores": scored, "best_gain_by_model": best_gain_by_model, "eligible": eligible,
                       "recommended": max(eligible, key=lambda mo: scored[mo]) if eligible else None,
                       "note": "recommendation by config llm.calibration.decision; the user confirms at G4 (config llm.selected stays TBD until then)"}
    out["y_auroc"] = y_auroc(cfg, conn)
    out["label_sensitivity"] = label_sensitivity(cfg, conn)
    out["feedback_response"] = feedback_response(cfg, conn)
    out["vcf_projection"] = vcf_projection(cfg, conn)
    p = Path(C.ROOT) / "reports" / "data" / "phase3_calibration.json"
    p.write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    for mo, v in sorted(out["models"].items()):
        print(f"{mo:14s} runs {v['runs']} cands {v['cands']} unusable {v['unusable']} v3 proven {v['v3_proven']} sim_only {v['proven_sim_only']} inconclusive {v['inconclusive']} "
              f"retained {v['retained']} (material {v['retained_material']}) usd {v['usd']:.2f} dc_h {v['dc_h']:.2f} calls/retained {v['llm_calls_per_retained']}")
    print("decision:", out["decision"]["recommended"], "eligible:", out["decision"]["eligible"])
    print(f"wrote {p}")
    return 0


def m6_classify_row(cfg, row, designs, scratch):
    """Rules-v2 features and class of one candidate row (design files from the catalog, the lock-step offsets from the
    row); the Yosys scratch directory is removed afterwards, the features are returned for archiving."""
    import shutil
    import tempfile
    from src.classify import rules as M6
    from src.designs import catalog as K
    d = designs[row["design_id"]]
    d_files = [str(p) for p in K.abs_paths(d, d["files"])]
    offsets = json.loads(row.get("latency_offset_json") or "{}") if row.get("latency_offset_json") else {}
    wd = Path(tempfile.mkdtemp(prefix=f"bs_m6v2_{row['cand_id']}_"))
    try:
        feat = M6.features(d_files, [row["rtl_path"]], d["top"], cfg, sverilog=d.get("sverilog", False),
                           incdirs=[str(p) for p in K.abs_paths(d, d["incdirs"])], workdir=wd, offsets=offsets)
    finally:
        shutil.rmtree(wd, ignore_errors=True)
    res = M6.classify(feat, cfg)
    feat = {k: v for k, v in feat.items() if k not in ("hist_d", "hist_c")} | {"hist_d": feat["hist_d"], "hist_c": feat["hist_c"]}
    return feat, res


def _agreement(pairs, classes=("a", "b", "c1", "c2", "d")):
    """pairs: (rule, human) -> {agreement, n, confusion 'human->rule', per_rule_class precision, per_human_class recall}."""
    conf, n_ok = {}, 0
    for rule, human in pairs:
        key = f"{human}->{rule}"
        conf[key] = conf.get(key, 0) + 1
        n_ok += int(rule == human)
    per_rule, per_human = {}, {}
    for c in classes:
        pred = [h for r, h in pairs if r == c]
        truth = [r for r, h in pairs if h == c]
        per_rule[c] = {"n": len(pred), "correct": sum(1 for h in pred if h == c), "precision": (sum(1 for h in pred if h == c) / len(pred)) if pred else None}
        per_human[c] = {"n": len(truth), "found": sum(1 for r in truth if r == c), "recall": (sum(1 for r in truth if r == c) / len(truth)) if truth else None}
    return {"n": len(pairs), "agree": n_ok, "agreement": (n_ok / len(pairs)) if pairs else None, "confusion": dict(sorted(conf.items())),
            "per_rule_class": per_rule, "per_human_class": per_human}


def cmd_m6_agreement(cfg, conn):
    """DECISIONS 2026-09-14 (pre-Phase-4 a): rule-vs-human agreement of the M6 classifier on the reviewed sample —
    rules v1 (the classes stored at run time, reports/data/phase3_m6_sample.json) and rules v2 (recomputed here with
    src/classify/rules.py) against reports/data/phase3_m6_human.json; writes reports/data/phase3_m6_agreement.json."""
    from src.designs import catalog as K
    human = json.loads((Path(C.ROOT) / "reports" / "data" / "phase3_m6_human.json").read_text())
    sample = {s["cand_id"]: s for s in json.loads((Path(C.ROOT) / "reports" / "data" / "phase3_m6_sample.json").read_text())["sample"]}
    designs = {d["design_id"]: d for d in K.load_all()}
    scratch = None   # Yosys runs in a temporary directory (rule 5: results/ is append-only)
    labels, v1, v2 = [], [], []
    for h in human["labels"]:
        s = sample[h["cand_id"]]
        row = dict(conn.execute("SELECT cand_id, run_id, design_id, rtl_path, latency_offset_json, class_final FROM candidates WHERE cand_id=?", (h["cand_id"],)).fetchone())
        feat, res = m6_classify_row(cfg, row, designs, scratch)
        labels.append({"i": h["i"], "cand_id": h["cand_id"], "design_id": h["design_id"], "model": h["model"], "human": h["human"], "rule_v1": s["class_final"],
                       "rule_v2": res["class_rule"], "v2_rules": res["rules"], "v2_confidence": res["confidence"], "note": h["note"],
                       "features": {k: feat[k] for k in ("ff_d", "ff_c", "ff_cells_d", "ff_cells_c", "depth_d", "depth_c", "ops_d", "ops_c", "diff_ratio", "max_offset")}})
        v1.append((s["class_final"], h["human"]))
        v2.append((res["class_rule"], h["human"]))
        print(f"{h['i']:2d} {h['cand_id']} {h['design_id'][6:]:18s} human {h['human']:2s} v1 {s['class_final']:2s} v2 {res['class_rule']:2s} {'ok' if res['class_rule'] == h['human'] else '--'}  {res['rules'][0][:70]}")
    out = {"generated_at": db.now(), "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(), "n": len(labels), "protocol": human["protocol"],
           "sample": {"seed": json.loads((Path(C.ROOT) / "reports" / "data" / "phase3_m6_sample.json").read_text())["seed"], "quotas": json.loads((Path(C.ROOT) / "reports" / "data" / "phase3_m6_sample.json").read_text())["quotas"]},
           "human_class_counts": {c: sum(1 for l in labels if l["human"] == c) for c in ("a", "b", "c1", "c2", "d")},
           "rules": {"v1": _agreement(v1), "v2": _agreement(v2)}, "classify_config": cfg["classify"], "labels": labels}
    p = Path(C.ROOT) / "reports" / "data" / "phase3_m6_agreement.json"
    p.write_text(json.dumps(out, indent=1) + "\n")
    print(f"v1 agreement {out['rules']['v1']['agree']}/{out['n']}, v2 agreement {out['rules']['v2']['agree']}/{out['n']}; (d) precision v1 {out['rules']['v1']['per_rule_class']['d']}, v2 {out['rules']['v2']['per_rule_class']['d']}")
    print(f"wrote {p}")
    return 0


def cmd_m6_relabel(cfg, conn, limit=None, force=False):
    """Re-label every Phase 3 candidate with rules v2 (DECISIONS 2026-09-14 a): the rules-v1 class is kept in
    candidates.class_rule_v1, class_rule / class_final / subtags_json / confidence are replaced, the features archived in
    features_json, rules_version = 2. Idempotent (rows already at version 2 are skipped unless --force, which recomputes every row, e.g. after the running drivers wrote their run-time classes or offsets) and resumable; verdict labels,
    credits and SEQ caps of the runs are untouched (they belong to the run). Runs locally (Yosys only)."""
    from src.designs import catalog as K
    designs = {d["design_id"]: d for d in K.load_all()}
    scratch = None
    rows = [dict(r) for r in conn.execute("SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, c.latency_offset_json, c.class_rule, c.class_final, c.rules_version "
                                          "FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase3' AND r.status != 'superseded' AND c.rtl_path IS NOT NULL "
                                          + ("" if force else "AND (c.rules_version IS NULL OR c.rules_version < 2) ") + "ORDER BY c.run_id, c.cand_id")]
    print(f"{len(rows)} candidates to re-label ({db.now()})")
    done = failed = 0
    changed = {}
    for i, row in enumerate(rows[: (limit or len(rows))], 1):
        if not Path(row["rtl_path"]).exists():
            failed += 1
            continue
        try:
            feat, res = m6_classify_row(cfg, row, designs, scratch)
        except Exception as e:
            failed += 1
            conn.execute("UPDATE candidates SET class_rule_v1=COALESCE(class_rule_v1, class_rule), rules_version=2, note=COALESCE(note,'') || ? WHERE cand_id=?",
                         (f" [m6 v2 failed: {type(e).__name__}: {e}"[:160] + "]", row["cand_id"]))
            conn.commit()
            continue
        old = row["class_final"]
        conn.execute("UPDATE candidates SET class_rule_v1=COALESCE(class_rule_v1, class_rule), class_rule=?, class_final=?, subtags_json=?, confidence=?, rules_version=2, features_json=? WHERE cand_id=?",
                     (res["class_rule"], res["class_rule"], json.dumps(res["rules"]), res["confidence"], json.dumps(feat), row["cand_id"]))
        conn.commit()
        done += 1
        changed[f"{old}->{res['class_rule']}"] = changed.get(f"{old}->{res['class_rule']}", 0) + 1
        if i % 50 == 0:
            print(f"  {i}/{len(rows)} done {done} failed {failed} ({db.now()})", flush=True)
    print(f"re-labelled {done}, failed {failed}; transitions v1->v2: {dict(sorted(changed.items()))} ({db.now()})")
    return 0



def cmd_m6_review(cfg, conn, do_submit, limit=None, exp="phase3"):
    """DECISIONS 2026-09-14 item 1: the LLM review of spec 04 §A.2 on the candidates whose rules-v2 class has low
    confidence or falls into the four disagreement categories (src/classify/review.py). Without --submit: the selection
    counts; with --submit: one `llm` queue job (src/search/run_llm.py, task m6_review; the daemon holds the API key)."""
    from src.classify import review as R
    from src.jobqueue.core import Queue
    rows = R.review_set(conn, cfg, exp, limit)
    why = {}
    for r in rows:
        for w in r["why"]:
            why[w] = why.get(w, 0) + 1
    by_cls = {}
    for r in rows:
        by_cls[r["class_rule"]] = by_cls.get(r["class_rule"], 0) + 1
    print(f"{len(rows)} candidates of exp {exp} to review ({why}; rule classes {by_cls}); model {cfg['llm']['selected']}, prompt src/search/prompts/m6_review.md")
    if do_submit and rows:
        q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
        jid = q.submit("llm", {"task": "m6_review", "exp": exp, "limit": limit}, design_id=None, config="m6_review", priority=3, timeout_sec=6 * 3600)
        print(f"submitted llm job {jid}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["designs", "smoke", "submit", "status", "collect", "yruns", "sample", "verify", "m6-sample", "m6-agreement", "m6-relabel", "m6-review"])
    ap.add_argument("--exp", default="phase3")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--design", nargs="*", default=None)
    ap.add_argument("--seeds", nargs="*", type=int, default=None)
    ap.add_argument("--K", type=int, default=None)
    ap.add_argument("--N", type=int, default=None)
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    cal = cfg["llm"]["calibration"]
    if a.what == "designs":
        print(calibration_designs(cfg, conn))
        return 0
    if a.what == "status":
        return cmd_status(cfg, conn)
    if a.what == "collect":
        return cmd_collect(cfg, conn)
    if a.what == "yruns":
        y_jobs(cfg, conn, a.submit)
        return 0
    if a.what == "sample":
        return cmd_sample(cfg, conn)
    if a.what == "verify":
        return cmd_verify(cfg, conn)
    if a.what == "m6-sample":
        return cmd_m6_sample(cfg, conn)
    if a.what == "m6-agreement":
        return cmd_m6_agreement(cfg, conn)
    if a.what == "m6-relabel":
        return cmd_m6_relabel(cfg, conn, a.limit, a.force)
    if a.what == "m6-review":
        return cmd_m6_review(cfg, conn, a.submit, a.limit, a.exp)
    if a.what == "smoke":
        designs = a.design or calibration_designs(cfg, conn)[:1]
        submit_runs(cfg, conn, designs, [a.model or cfg["llm"]["candidates"][0]], a.seeds or [1], a.K or 1, a.N or 2, "smoke", a.submit, note="smoke")
        return 0
    designs = a.design or calibration_designs(cfg, conn)
    submit_runs(cfg, conn, designs, a.models or cfg["llm"]["candidates"], a.seeds or list(range(1, int(cal["seeds"]) + 1)), a.K or int(cal["K"]), a.N or int(cal["N"]), "phase3", a.submit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
