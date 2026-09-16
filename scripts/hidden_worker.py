#!/usr/bin/env python3
"""The only writer of the hidden results database (docs/spec/06-hidden-layer.md, spec 07; CLAUDE.md rule 3).

    .venv/bin/python scripts/hidden_worker.py --job <job_id>            # queue runner for kind dc_hidden
    .venv/bin/python scripts/hidden_worker.py --submit-noise [--suite ...] [--design ...] [--priority N] [--dry-run]
    .venv/bin/python scripts/hidden_worker.py --noise-floor  [--suite ...] [--design ...]
    .venv/bin/python scripts/hidden_worker.py --migrate-phase0

--job: evaluates one design / perturbation / candidate under a hidden configuration; the record goes to the hidden
database and the hidden raw tree (src/eval/service.py refuses anything else). Prints status and paths, never
metrics. Exit codes as src/eval/run_dc.py (0 ok, 75 license seat, 1 failed; eval_failed recorded on the last attempt).
--submit-noise: Phase 2.2 hidden part: every original design of the sets (and rtlrewriter) plus its SEQ-proven
perturbations under the hidden `noise.configs` at the design's knee periods; `noise.configs_light` (H3) only for
the design and one perturbation per type; the signoff configurations (`noise.configs_signoff`, H4: PrimeTime on the E4
netlist) get the D baseline only, and --submit-candidates registers them for accepted candidates and the audit sample whose
E4 netlist is still on disk (pt pool). --noise-floor: sigma_D of the hidden configurations into the hidden database's
noise_floor table (only counts are printed). Phase 5 adds the certification loop for archived candidates.
--migrate-phase0 moved the Phase 0 smoke records of H1-H5 out of the visible database (done on 2026-09-12).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.db import ingest  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.designs import jobs as J  # noqa: E402
from src.eval.failures import deterministic_failure  # noqa: E402
from src.eval.service import HiddenConfigError, evaluate  # noqa: E402
from src.noise import stats as S  # noqa: E402

EX_TEMPFAIL = 75
RUNNER_TIMEOUT_FRACTION = 0.85  # the tool's own timeout fires before the queue kills the job, so the record says timeout / inconclusive


def runner_timeout(job):
    return float(job["timeout_sec"]) * RUNNER_TIMEOUT_FRACTION if job["timeout_sec"] else None



def hidden_db_path(cfg):
    return os.path.join(C.results_dir(cfg), "hidden", "hidden.sqlite")


def hidden_configs(cfg):
    return sorted(n for n, c in cfg["configs"].items() if isinstance(c, dict) and c.get("hidden"))


# ----------------------------------------------------------------------------- signoff configurations (H4; 2026-09-15)
def signoff_configs(cfg):
    """The hidden signoff configurations (config `noise.configs_signoff`, spec 06): PrimeTime / PrimePower on the E4 netlist of the
    same object; D baseline and candidates only, no perturbation runs (sigma_D(H4) := sigma_D(E4))."""
    return [c for c in (cfg["noise"].get("configs_signoff") or []) if cfg["configs"][c].get("hidden") and cfg["configs"][c].get("tool") == "pt_primepower"]


def signoff_source(vis, design_id, cand_id, pert_id, cdef, clock_ns):
    """The visible record whose netlist the signoff configuration reads (input E4_netlist -> the object's latest ok E4 record at the
    configuration's period), or None when its netlist and constraints are no longer on disk (the tiered retention keeps them only for
    accepted candidates and the audit sample)."""
    from src.eval.service import source_evaluation
    src = source_evaluation(vis, design_id, cand_id, pert_id, cdef.get("input"), clock_ns=clock_ns)
    if not src:
        return None
    reports = Path(src["raw_dir"]) / "outputs" / "reports"
    return src if (reports / "netlist.v").exists() and (reports / "design.sdc").exists() else None


def signoff_job(cfg, d, config, clock_ns, priority):
    """A PrimeTime job of the hidden worker: the dc_hidden runner (rule 3) dispatched in the `pt` pool with the PT timeout."""
    j = J.dc_job(cfg, d, config, float(clock_ns), priority)
    j.update(kind="dc_hidden", pool="pt", timeout_sec=int(cfg["timeouts"]["pt"]) * 60)
    return j


# ----------------------------------------------------------------------------- queue runner
def run_job(cfg, job_id, vis=None, hid=None):
    vis = vis or db.connect(cfg=cfg)
    hid = hid or db.connect(path=hidden_db_path(cfg))
    job = vis.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if job is None:
        print(f"job {job_id} not found", file=sys.stderr)
        return 1
    p = json.loads(job["payload_json"])
    config = p.get("config") or job["config"]
    try:
        meta = evaluate(cfg, hid, p["design_id"], p["rtl"], p["top"], config, clock_ns=p.get("clock_ns"), design=p.get("design"),
                        clk_port=p.get("clk_port", "clk"), cand_id=p.get("cand_id"), pert_id=p.get("pert_id"),
                        is_baseline=p.get("is_baseline", 0), saif=p.get("saif"), saif_instance=p.get("saif_instance"),
                        sverilog=p.get("sverilog", False), incdirs=p.get("incdirs"), force_rerun=p.get("force_rerun", False),
                        timeout_sec=runner_timeout(job), source_conn=vis)
    except HiddenConfigError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    print(json.dumps({k: meta.get(k) for k in ("design_id", "config", "status", "raw_dir", "dc_seconds", "cached")}))
    if meta["status"] == "ok":
        return 0
    if meta["status"] == "license_failed":
        return EX_TEMPFAIL
    if int(job["attempts"]) >= int(cfg["queue"]["retries"]):
        meta["failed_status"] = meta.get("status")
        meta["status"] = "eval_failed"
        with open(f"{meta['raw_dir']}/meta.json", "w") as f:
            json.dump(meta, f, indent=1, sort_keys=True, default=str)
        try:
            ingest.ingest_evaluation(hid, meta)
        except Exception as e:
            print(f"eval_failed record not ingested: {e}", file=sys.stderr)
    return 1


# ----------------------------------------------------------------------------- Phase 2.2 hidden part
def _selected(vis, suites=None, designs=None):
    rows = {r["design_id"]: dict(r) for r in vis.execute("SELECT * FROM designs")}
    out = []
    for d in K.load_all():
        if suites and d["suite"] not in suites:
            continue
        if designs and d["design_id"] not in designs:
            continue
        r = rows.get(d["design_id"]) or {}
        eligible = r.get("e4_synthesizable") == 1 and "multi_clock" not in d["tags"] and "yosys_failed" not in d["tags"]
        if r.get("split") in ("dev", "held") or (d["suite"] == "rtlrewriter" and eligible):
            out.append((d, r))
    return out


def _proven(vis, design_id):
    return [dict(r) for r in vis.execute("SELECT pert_id, ptype, path FROM perturbations WHERE design_id=? AND seq_status IN ('proven', 'proven_rename') ORDER BY ptype, pert_id", (design_id,))]


def noise_jobs(cfg, vis, suites=None, designs=None, priority=0, ptypes=None, missing=False, hid=None, configs=None):
    """[(job dict)] for the hidden noise configurations; the knee periods travel in payload.design. ptypes: only these
    perturbation types and no D baseline (adds perturbations to an existing batch). missing: skip D / perturbation runs
    that already have an ok record in the hidden database at the configuration's period. configs: only these configurations.
    The signoff configurations (`noise.configs_signoff`, H4) get the D baseline only, and only when D's E4 netlist at the knee
    period is on disk (2026-09-15)."""
    full = [c for c in cfg["noise"]["configs"] if cfg["configs"][c].get("hidden")]
    light = [c for c in cfg["noise"].get("configs_light", []) if cfg["configs"][c].get("hidden")]
    signoff = signoff_configs(cfg)
    if configs:
        full, light, signoff = [c for c in full if c in configs], [c for c in light if c in configs], [c for c in signoff if c in configs]
    hid = hid or (db.connect(path=hidden_db_path(cfg)) if missing else None)

    def have(design_id, config, clock_ns, pert_id):
        if not missing:
            return False
        if pert_id is None:
            q = "SELECT 1 FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' AND abs(clock_ns-?)<1e-6 LIMIT 1"
            return hid.execute(q, (design_id, config, float(clock_ns))).fetchone() is not None
        q = "SELECT 1 FROM evaluations WHERE design_id=? AND config=? AND pert_id=? AND status='ok' AND abs(clock_ns-?)<1e-6 LIMIT 1"
        return hid.execute(q, (design_id, config, pert_id, float(clock_ns))).fetchone() is not None
    jobs = []
    for d, r in _selected(vis, suites, designs):
        design = {k: r.get(k) for k in ("phi_main_ns_nangate45", "phi_main_ns_asap7", "phi_main_ns_sky130hd")}
        perts = _proven(vis, d["design_id"])
        if ptypes:
            perts = [p for p in perts if p["ptype"] in ptypes]
        from src.noise import saif as SF
        sf = SF.load_saif(d["design_id"]) or {}
        d_saif = sf.get("design") or {}
        first_per_type = {}
        for p in perts:
            first_per_type.setdefault(p["ptype"], p)
        for config in full + light:
            cdef = cfg["configs"][config]
            lib = cdef.get("lib")
            if "clock_ns" not in cdef and design.get(f"phi_main_ns_{lib}") is None:
                continue  # no knee period for this library yet
            if config in light and lib == "nangate45" and not cfg["libs"][lib].get("physical_ref_for_spg"):
                continue
            chosen = perts if config in full else list(first_per_type.values())
            clock_ns = cdef.get("clock_ns") or design[f"phi_main_ns_{lib}"]
            if not ptypes and not have(d["design_id"], config, clock_ns, None):
                base = J.dc_job(cfg, d, config, cdef.get("clock_ns") or design[f"phi_main_ns_{lib}"], priority)
                base["kind"] = "dc_hidden"
                base["payload"]["design"] = design
                if d_saif.get("saif"):
                    base["payload"].update(saif=d_saif["saif"], saif_instance=d_saif["instance"])
                jobs.append(base)
            for p in chosen:
                if have(d["design_id"], config, clock_ns, p["pert_id"]):
                    continue
                j = J.dc_job(cfg, d, config, cdef.get("clock_ns") or design[f"phi_main_ns_{lib}"], priority)
                j["kind"] = "dc_hidden"
                j["payload"].update(rtl=[str(Path(C.ROOT) / p["path"])], incdirs=[], is_baseline=0, pert_id=p["pert_id"], design=design)
                ps = (sf.get("perturbations") or {}).get(p["pert_id"]) or {}
                if ps.get("saif"):
                    j["payload"].update(saif=ps["saif"], saif_instance=ps["instance"])
                jobs.append(j)
        for config in signoff:
            if ptypes:
                continue   # signoff configurations have no perturbation runs
            cdef = cfg["configs"][config]
            lib = cdef.get("lib")
            clock_ns = cdef.get("clock_ns") or design.get(f"phi_main_ns_{lib}")
            if clock_ns is None or have(d["design_id"], config, clock_ns, None):
                continue
            if signoff_source(vis, d["design_id"], None, None, cdef, clock_ns) is None:
                continue   # D's E4 netlist at the knee period is not on disk: nothing to sign off
            base = signoff_job(cfg, d, config, clock_ns, priority)
            base["payload"]["design"] = design
            if d_saif.get("saif"):
                base["payload"].update(saif=d_saif["saif"], saif_instance=d_saif["instance"])
            jobs.append(base)
    return jobs


def submit_noise(cfg, suites, designs, priority, dry_run, ptypes=None, missing=False, configs=None):
    from src.jobqueue.core import Queue
    vis = db.connect(cfg=cfg)
    jobs = noise_jobs(cfg, vis, suites, designs, priority, ptypes, missing=missing, configs=configs)
    by_cfg = {}
    for j in jobs:
        by_cfg[j["config"]] = by_cfg.get(j["config"], 0) + 1
    print(f"{len(jobs)} hidden noise jobs: {by_cfg}")
    if dry_run:
        return 0
    q = Queue(cfg, vis, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    for j in jobs:
        q.submit(j["kind"], j["payload"], design_id=j["design_id"], config=j["config"], priority=j["priority"], timeout_sec=j["timeout_sec"], pool=j.get("pool"))
    print(f"submitted {len(jobs)} dc_hidden jobs")
    return 0


def noise_floor(cfg, suites=None, designs=None, vis=None, hid=None):
    """sigma_D of the hidden configurations into the hidden noise_floor table; -> {config: rows written}."""
    vis = vis or db.connect(cfg=cfg)
    hid = hid or db.connect(path=hidden_db_path(cfg))
    configs = [c for c in cfg["noise"]["configs"] + cfg["noise"].get("configs_light", []) if cfg["configs"][c].get("hidden")]
    nz = cfg["noise"]
    k, q, quiet = float(nz["k_sigma"]), float(nz.get("pooled_quantile", 0.90)), float(nz.get("quiet_max_abs", 0.001))
    written = {}
    sets = [(d, r) for d, r in _selected(vis) if r.get("split") in ("dev", "held")]
    proven_all = S.proven_by_design(vis)
    # rule A: pooled minimum per hidden configuration over the set designs' records at their own baseline period
    pooled = {}
    for config in configs:
        pool = {}
        for d, r in sets:
            base, _ = S.pick_records(hid, d["design_id"], config, proven_all.get(d["design_id"], set()))
            if base is None:
                continue
            _, latest = S.pick_records(hid, d["design_id"], config, proven_all.get(d["design_id"], set()), base["clock_ns"])
            for m, col in S.COLUMNS.items():
                pool.setdefault(m, []).extend((abs(x), d["design_id"]) for x in S.deviations(m, base.get(col), [x.get(col) for x in latest.values()], base["clock_ns"]))
        pooled[config] = {m: S.pooled_quantile(v, q, nz.get("pooled_weighting", "design")) for m, v in pool.items() if v}
    for d, r in _selected(vis, suites, designs):
        proven = {p["pert_id"] for p in _proven(vis, d["design_id"])}
        for config in configs:
            base, _ = S.pick_records(hid, d["design_id"], config, proven)
            if base is None:
                continue
            _, latest = S.pick_records(hid, d["design_id"], config, proven, base["clock_ns"])
            if len(latest) < 2:
                rows = S.pooled_rows(d["design_id"], config, pooled.get(config)) if (nz.get("pooled_floor_for_missing") and r.get("split") in ("dev", "held")) else []
            else:
                rows = S.floor_rows(d["design_id"], config, base, list(latest.values()), base["clock_ns"], pooled.get(config), k, quiet)
            written[config] = written.get(config, 0) + S.upsert_floor(hid, rows, nz.get("floor_version"))
    return written


CHANGE_EPS = 0.001  # |delta area| above which the perturbation changed the netlist (G3 change agreement)


def _delta(metric, base, rec, clock_ns):
    col = S.COLUMNS[metric]
    d = S.deviations(metric, base.get(col), [rec.get(col)], clock_ns)
    return d[0] if d else None


def g3_summary(cfg, suites=None, designs=None, vis=None, hid=None):
    """G3 (PLAN 2.5): t_H3 / t_E4 of the baseline runs and the agreement of the E4 and H3 floor conclusions
    (src/noise/stats.conclusion at noise.k_sigma) per perturbation, as counts and seconds only: no per-design
    hidden value leaves this function (CLAUDE.md rule 3). Needs the visible floor (phase2_noise.py collect) and
    the hidden floor (--noise-floor) to exist."""
    vis = vis or db.connect(cfg=cfg)
    hid = hid or db.connect(path=hidden_db_path(cfg))
    k = float(cfg["noise"]["k_sigma"])
    ratios, e4_secs, h3_secs = [], 0.0, 0.0
    pairs = agree = same_sign = 0
    confusion, change = {}, {}
    for d, r in _selected(vis, suites, designs):
        did = d["design_id"]
        phi = r.get("phi_main_ns_nangate45")
        if phi is None:
            continue
        proven = {p["pert_id"] for p in _proven(vis, did)}
        base_e4, perts_e4 = S.pick_records(vis, did, "E4", proven, phi)
        base_h3, perts_h3 = S.pick_records(hid, did, "H3", proven, phi)
        if base_e4 is None or base_h3 is None:
            continue
        if base_e4.get("dc_seconds") and base_h3.get("dc_seconds"):
            ratios.append(float(base_h3["dc_seconds"]) / float(base_e4["dc_seconds"]))
            e4_secs += float(base_e4["dc_seconds"])
            h3_secs += float(base_h3["dc_seconds"])
        sig_e4 = {m: x["sigma_robust"] for m, x in S.latest_floor(vis, did, "E4").items() if x.get("sigma_robust") is not None}
        sig_h3 = {m: x["sigma_robust"] for m, x in S.latest_floor(hid, did, "H3").items() if x.get("sigma_robust") is not None}
        for pid in sorted(set(perts_e4) & set(perts_h3)):
            d_e4 = {m: _delta(m, base_e4, perts_e4[pid], phi) for m in S.METRICS}
            d_h3 = {m: _delta(m, base_h3, perts_h3[pid], phi) for m in S.METRICS}
            c_e4 = S.conclusion(d_e4, sig_e4, k)
            c_h3 = S.conclusion(d_h3, sig_h3, k)
            if c_e4 is None or c_h3 is None:
                continue
            pairs += 1
            agree += int(c_e4 == c_h3)
            key = f"E4={c_e4}|H3={c_h3}"
            confusion[key] = confusion.get(key, 0) + 1
            if d_e4.get("area") is not None and d_h3.get("area") is not None:  # netlist changed by the perturbation (|delta area| > 0.1 %)?
                ce, ch = abs(d_e4["area"]) > CHANGE_EPS, abs(d_h3["area"]) > CHANGE_EPS
                ck = "both changed" if ce and ch else "both unchanged" if not ce and not ch else "E4 only" if ce else "H3 only"
                change[ck] = change.get(ck, 0) + 1
                if ce and ch:
                    same_sign += int((d_e4["area"] > 0) == (d_h3["area"] > 0))
    out = {"k_sigma": k, "n_designs_with_ratio": len(ratios),
           "t_ratio": {"min": min(ratios) if ratios else None, "q25": S.quantile(ratios, 0.25), "median": S.quantile(ratios, 0.5),
                       "q75": S.quantile(ratios, 0.75), "max": max(ratios) if ratios else None},
           "e4_seconds_total": e4_secs, "h3_seconds_total": h3_secs,
           "pairs": pairs, "agree": agree, "agreement_rate": (agree / pairs) if pairs else None, "confusion": confusion,
           "area_change": change, "both_changed_same_direction": same_sign}
    return out


def coverage(cfg, vis=None, hid=None):
    """Hidden-layer coverage check (DECISIONS 2026-09-14, additional task 3; counts and design ids only): for every set
    design with a measured visible E4 floor, per hidden configuration, whether D and every SEQ-proven perturbation (one per
    type under the light configurations) have an ok record in the hidden database. -> {config: {complete, incomplete: [ids], missing_D: [ids], n_missing_perturbations}}"""
    vis = vis or db.connect(cfg=cfg)
    hid = hid or db.connect(path=hidden_db_path(cfg))
    full = [c for c in cfg["noise"]["configs"] if cfg["configs"][c].get("hidden")]
    light = [c for c in cfg["noise"].get("configs_light", []) if cfg["configs"][c].get("hidden")]
    floored = {r[0] for r in vis.execute("SELECT DISTINCT design_id FROM noise_floor WHERE config='E4' AND metric='area' AND floor_source='measured'")}
    out = {}
    for d, r in _selected(vis):
        if d["design_id"] not in floored:
            continue
        perts = _proven(vis, d["design_id"])
        first_per_type = {}
        for p in perts:
            first_per_type.setdefault(p["ptype"], p)
        for config in full + light:
            lib = cfg["configs"][config].get("lib")
            if "clock_ns" not in cfg["configs"][config] and r.get(f"phi_main_ns_{lib}") is None:
                continue  # no knee on that library: not expected to exist
            e = out.setdefault(config, {"complete": 0, "incomplete": [], "missing_D": [], "n_missing_perturbations": 0, "expected": 0})
            e["expected"] += 1
            base, _ = S.pick_records(hid, d["design_id"], config, set())
            if base is None:
                e["missing_D"].append(d["design_id"])
                continue
            _, latest = S.pick_records(hid, d["design_id"], config, {p["pert_id"] for p in perts}, base["clock_ns"])
            wanted = perts if config in full else list(first_per_type.values())
            missing = [p["pert_id"] for p in wanted if p["pert_id"] not in latest]
            if missing:
                e["incomplete"].append(d["design_id"])
                e["n_missing_perturbations"] += len(missing)
            else:
                e["complete"] += 1
    return out



def candidate_coverage(cfg, exp="phase3", vis=None, hid=None, configs=None):
    """Hidden-layer registration check for candidates (DECISIONS 2026-09-14, pre-Phase-4 f; counts only): for the accepted
    candidates (archive members) and for every E4-evaluated candidate of the runs of `exp`, per hidden configuration,
    how many are expected (a knee period exists on the configuration's library), how many have an ok record in the hidden
    database, and how many are missing. Nothing but counts leaves the hidden database."""
    vis = vis or db.connect(cfg=cfg)
    hid = hid or db.connect(path=hidden_db_path(cfg))
    configs = configs or [c for c in cfg["noise"]["configs"] + cfg["noise"].get("configs_light", []) if cfg["configs"][c].get("hidden")] + signoff_configs(cfg)
    signoff = set(signoff_configs(cfg))
    from src.eval.retention import is_audit_sample
    audit_frac = float(((cfg.get("retention") or {}).get("tiered_audit_frac")) or 0.0)
    rows = [dict(r) for r in vis.execute("SELECT c.cand_id, c.design_id, c.accepted, c.in_archive FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                                         "WHERE r.exp=? AND r.status != 'superseded' AND c.e4_job_id IS NOT NULL AND c.label IS NOT NULL AND c.label != 'aborted'", (exp,))]
    phis = {}
    for r in rows:
        if r["design_id"] not in phis:
            d = vis.execute("SELECT phi_main_ns_nangate45, phi_main_ns_asap7, phi_main_ns_sky130hd FROM designs WHERE design_id=?", (r["design_id"],)).fetchone()
            phis[r["design_id"]] = {"nangate45": d[0], "asap7": d[1], "sky130hd": d[2]} if d else {}
    out = {"exp": exp, "candidates_e4": len(rows), "accepted": sum(1 for r in rows if r["accepted"]), "configs": {}}
    for config in configs:
        cdef = cfg["configs"][config]
        lib = cdef.get("lib")
        e = {"expected": 0, "ok": 0, "missing": 0, "accepted_expected": 0, "accepted_ok": 0, "accepted_missing": 0}
        for r in rows:
            clock_ns = cdef.get("clock_ns") or (phis.get(r["design_id"]) or {}).get(lib)
            if clock_ns is None:
                continue
            if config in signoff and not (r["accepted"] or r["in_archive"] or is_audit_sample(r["cand_id"], audit_frac)):
                continue   # signoff certifies accepted candidates and the audit sample only (spec 06)
            have = hid.execute("SELECT 1 FROM evaluations WHERE design_id=? AND cand_id=? AND config=? AND status='ok' AND abs(clock_ns-?)<1e-6 LIMIT 1", (r["design_id"], r["cand_id"], config, float(clock_ns))).fetchone() is not None
            e["expected"] += 1
            e["ok" if have else "missing"] += 1
            if r["accepted"]:
                e["accepted_expected"] += 1
                e["accepted_ok" if have else "accepted_missing"] += 1
        out["configs"][config] = e
    return out

def candidate_jobs(cfg, vis, exp="phase3", priority=0, hid=None, configs=None, retry_failed=False, skipped=None):
    """DECISIONS 2026-09-14 (pre-Phase-4 c): the hidden configurations on every E4-evaluated candidate of the runs of `exp`
    (all of H1 / H2a / H2b / H3 / H5, full — not the light set), missing hidden records only. The candidate's SAIF comes
    from its equivalence record (saif_c); records go to the hidden database only (rule 3)."""
    from src.designs import jobs as J
    hid = hid or db.connect(path=hidden_db_path(cfg))
    configs = configs or [c for c in cfg["noise"]["configs"] + cfg["noise"].get("configs_light", []) if cfg["configs"][c].get("hidden")] + signoff_configs(cfg)
    signoff = set(signoff_configs(cfg))   # H4: accepted candidates and the audit sample in every experiment, only with the E4 netlist on disk (2026-09-15)
    designs = {d["design_id"]: d for d in K.load_all()}
    jobs = []
    from src.eval.retention import is_audit_sample
    scope = (cfg.get("exp5") or {}).get("hidden_scope") or {}          # decision 2026-09-15 item 2 (Phase 5 runs): H1 / H3 / H5 on every E4-evaluated candidate, the rest on accepted + audit sample
    audit_frac = float(((cfg.get("retention") or {}).get("tiered_audit_frac")) or 0.0)
    for c in vis.execute("SELECT c.cand_id, c.design_id, c.rtl_path, c.run_id, c.top, c.rtl_files_json, c.accepted, c.in_archive FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                         "WHERE r.exp=? AND r.status != 'superseded' AND c.e4_job_id IS NOT NULL AND c.label IS NOT NULL AND c.label != 'aborted' ORDER BY c.cand_id", (exp,)):
        d = designs[c["design_id"]]
        kept = bool(c["accepted"] or c["in_archive"]) or is_audit_sample(c["cand_id"], audit_frac)
        r = vis.execute("SELECT phi_main_ns_nangate45, phi_main_ns_asap7, phi_main_ns_sky130hd FROM designs WHERE design_id=?", (c["design_id"],)).fetchone()
        design = {"phi_main_ns_nangate45": r[0], "phi_main_ns_asap7": r[1], "phi_main_ns_sky130hd": r[2]}
        saif = None
        st = Path(C.ROOT) / "results" / "candidates" / c["run_id"] / "state.json"
        if st.exists():
            rec_dir = (json.loads(st.read_text()).get("cands") or {}).get(c["cand_id"], {}).get("eq_record")
            if rec_dir and (Path(rec_dir) / "equiv.json").exists():
                s = json.loads((Path(rec_dir) / "equiv.json").read_text()).get("saif_c")
                saif = s if s and Path(s).exists() else None
        for config in configs:
            cdef = cfg["configs"][config]
            lib = cdef.get("lib")
            clock_ns = cdef.get("clock_ns") or design.get(f"phi_main_ns_{lib}")
            if clock_ns is None:
                continue
            if config in signoff:
                if not kept:
                    continue   # signoff (spec 06): accepted candidates and the audit sample only, in every experiment
            elif exp.startswith("phase5") and scope.get(config, "all_e4") == "accepted_and_audit" and not kept:
                continue   # Phase 5 scope: this configuration certifies accepted candidates and the audit sample only
            if config in cfg["noise"].get("configs_light", []) and lib == "nangate45" and not cfg["libs"][lib].get("physical_ref_for_spg"):
                continue
            if hid.execute("SELECT 1 FROM evaluations WHERE design_id=? AND cand_id=? AND config=? AND status='ok' AND abs(clock_ns-?)<1e-6 LIMIT 1", (c["design_id"], c["cand_id"], config, float(clock_ns))).fetchone():
                continue
            if config in signoff and signoff_source(vis, c["design_id"], c["cand_id"], None, cdef, float(clock_ns)) is None:
                if skipped is not None:
                    skipped[f"{config}_no_netlist"] = skipped.get(f"{config}_no_netlist", 0) + 1   # the E4 netlist is gone (retention): nothing to sign off
                continue
            if not retry_failed and deterministic_failure(hid, c["cand_id"], config, float(clock_ns), design_id=c["design_id"]):   # the tool rejects the RTL: no re-run (2026-09-15)
                if skipped is not None:
                    skipped[config] = skipped.get(config, 0) + 1
                continue
            j = signoff_job(cfg, d, config, float(clock_ns), priority) if config in signoff else J.dc_job(cfg, d, config, float(clock_ns), priority)
            j["kind"] = "dc_hidden"
            files = json.loads(c["rtl_files_json"]) if c["rtl_files_json"] else [c["rtl_path"]]   # Phase 4 objects: several files, own top (PLAN 4.2)
            j["payload"].update(rtl=files, incdirs=[str(p) for p in K.abs_paths(d, d["incdirs"])], is_baseline=0, cand_id=c["cand_id"], design=design)   # candidates may `include D's files
            if c["top"]:
                j["payload"]["top"] = c["top"]
            if saif:
                j["payload"].update(saif=saif, saif_instance="bs_lockstep/u_c")
            j["cand_id"] = c["cand_id"]
            jobs.append(j)
    return jobs


def submit_candidates(cfg, exp, priority, dry_run, retry_failed=False, configs=None):
    from src.jobqueue.core import Queue
    vis = db.connect(cfg=cfg)
    skipped = {}
    jobs = candidate_jobs(cfg, vis, exp, priority, retry_failed=retry_failed, skipped=skipped, configs=configs)
    by = {}
    for j in jobs:
        by[j["config"]] = by.get(j["config"], 0) + 1
    print(f"{len(jobs)} hidden candidate jobs ({exp}): {by}; deterministic failures skipped: {skipped}")
    if dry_run:
        return 0
    q = Queue(cfg, vis, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    for j in jobs:
        q.submit(j["kind"], j["payload"], design_id=j["design_id"], cand_id=j["cand_id"], config=j["config"], priority=j["priority"], timeout_sec=j["timeout_sec"], pool=j.get("pool"))
    print(f"submitted {len(jobs)} dc_hidden jobs")
    return 0


# ----------------------------------------------------------------------------- Phase 0 migration (done)
def _fix_meta(job_dir):
    m = Path(job_dir) / "meta.json"
    if m.exists():
        try:
            meta = json.loads(m.read_text())
        except json.JSONDecodeError:
            return
        meta["raw_dir"] = str(job_dir)
        m.write_text(json.dumps(meta, indent=1, sort_keys=True, default=str))


def migrate_phase0(cfg):
    names = hidden_configs(cfg)
    vis = db.connect(cfg=cfg)
    hid = db.connect(path=hidden_db_path(cfg))
    raw_root = Path(C.results_dir(cfg)) / "raw"
    hid_root = Path(C.results_dir(cfg)) / "hidden" / "raw"
    moved_rows = moved_dirs = 0
    marks = ",".join("?" for _ in names)
    for r in vis.execute(f"SELECT * FROM evaluations WHERE config IN ({marks}) ORDER BY eval_id", names).fetchall():
        r = dict(r)
        eval_id = r.pop("eval_id")
        old = Path(r["raw_dir"])
        try:
            rel = old.resolve().relative_to(raw_root.resolve())
        except ValueError:
            rel = None
        new = (hid_root / rel) if rel else old
        if rel and old.exists():
            new.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old), str(new))
            _fix_meta(new)
            moved_dirs += 1
        r["raw_dir"] = str(new)
        cols = list(r)
        hid.execute(f"INSERT OR IGNORE INTO evaluations ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})", tuple(r.values()))
        vis.execute("DELETE FROM evaluations WHERE eval_id=?", (eval_id,))
        moved_rows += 1
    for design_dir in sorted(p for p in raw_root.glob("*") if p.is_dir()):
        for name in names:
            src = design_dir / name
            if not src.is_dir():
                continue
            for job in sorted(src.iterdir()):
                new = hid_root / design_dir.name / name / job.name
                new.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(job), str(new))
                _fix_meta(new)
                moved_dirs += 1
            if not any(src.iterdir()):
                src.rmdir()
    print(f"hidden configurations {names}: {moved_rows} evaluation rows and {moved_dirs} raw directories moved into the hidden tree")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job")
    ap.add_argument("--submit-noise", action="store_true")
    ap.add_argument("--noise-floor", action="store_true")
    ap.add_argument("--g3-summary", action="store_true")
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--coverage-candidates", action="store_true", help="hidden registration counts of the candidates of --exp (accepted and all E4-evaluated; counts only)")
    ap.add_argument("--submit-candidates", action="store_true")
    ap.add_argument("--retry-failed", action="store_true", help="candidate jobs: re-submit pairs whose latest hidden record is a deterministic failure")
    ap.add_argument("--exp", default="phase3")
    ap.add_argument("--migrate-phase0", action="store_true")
    ap.add_argument("--suite", nargs="*", default=None)
    ap.add_argument("--design", nargs="*", default=None)
    ap.add_argument("--priority", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ptype", nargs="*", default=None)
    ap.add_argument("--missing", action="store_true", help="submit-noise: only D / perturbation runs without an ok hidden record at the configuration's period")
    ap.add_argument("--configs", nargs="*", default=None, help="submit-noise / submit-candidates: only these hidden configurations (e.g. H4)")
    a = ap.parse_args(argv)
    cfg = C.load()
    if a.job:
        return run_job(cfg, a.job)
    if a.submit_noise:
        return submit_noise(cfg, a.suite, a.design, a.priority, a.dry_run, a.ptype, a.missing, configs=a.configs)
    if a.noise_floor:
        written = noise_floor(cfg, a.suite, a.design)
        print("hidden noise_floor rows written per configuration:", written)
        return 0
    if a.submit_candidates:
        return submit_candidates(cfg, a.exp, a.priority, a.dry_run, retry_failed=a.retry_failed, configs=a.configs)
    if a.coverage_candidates:
        cov = candidate_coverage(cfg, a.exp)
        print(json.dumps(cov, indent=1))
        (Path(C.ROOT) / "reports" / "data" / f"{a.exp}_hidden_candidate_coverage.json").write_text(json.dumps(cov, indent=1) + "\n")
        return 0
    if a.coverage:
        cov = coverage(cfg)
        p = Path(C.ROOT) / "reports" / "data" / "phase2_hidden_coverage.json"
        p.write_text(json.dumps(cov, indent=1, sort_keys=True) + "\n")
        for config, e in sorted(cov.items()):
            print(f"{config}: expected {e['expected']}, complete {e['complete']}, incomplete {len(e['incomplete'])} (missing perturbation records {e['n_missing_perturbations']}), missing D {len(e['missing_D'])}")
            if e["incomplete"] or e["missing_D"]:
                print("   incomplete:", ", ".join(e["incomplete"][:20]), "" if len(e["incomplete"]) <= 20 else "...", "| missing D:", ", ".join(e["missing_D"][:20]))
        print(f"wrote {p} (counts and design ids only)")
        return 0
    if a.g3_summary:
        out = g3_summary(cfg, a.suite, a.design)
        p = Path(C.ROOT) / "reports" / "data" / "phase2_g3.json"
        p.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
        print(json.dumps(out, sort_keys=True))
        print(f"wrote {p} (aggregates only)")
        return 0
    if a.migrate_phase0:
        return migrate_phase0(cfg)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
