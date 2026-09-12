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
the design and one perturbation per type. --noise-floor: sigma_D of the hidden configurations into the hidden
database's noise_floor table (only counts are printed). Phase 5 adds the certification loop for archived candidates.
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
from src.eval.service import HiddenConfigError, evaluate  # noqa: E402
from src.noise import stats as S  # noqa: E402

EX_TEMPFAIL = 75


def hidden_db_path(cfg):
    return os.path.join(C.results_dir(cfg), "hidden", "hidden.sqlite")


def hidden_configs(cfg):
    return sorted(n for n, c in cfg["configs"].items() if isinstance(c, dict) and c.get("hidden"))


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
                        timeout_sec=job["timeout_sec"], source_conn=vis)
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
    return [dict(r) for r in vis.execute("SELECT pert_id, ptype, path FROM perturbations WHERE design_id=? AND seq_status='proven' ORDER BY ptype, pert_id", (design_id,))]


def noise_jobs(cfg, vis, suites=None, designs=None, priority=0):
    """[(job dict)] for the hidden noise configurations; the knee periods travel in payload.design."""
    full = [c for c in cfg["noise"]["configs"] if cfg["configs"][c].get("hidden")]
    light = [c for c in cfg["noise"].get("configs_light", []) if cfg["configs"][c].get("hidden")]
    jobs = []
    for d, r in _selected(vis, suites, designs):
        design = {k: r.get(k) for k in ("phi_main_ns_nangate45", "phi_main_ns_asap7", "phi_main_ns_sky130hd")}
        perts = _proven(vis, d["design_id"])
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
            base = J.dc_job(cfg, d, config, cdef.get("clock_ns") or design[f"phi_main_ns_{lib}"], priority)
            base["kind"] = "dc_hidden"
            base["payload"]["design"] = design
            jobs.append(base)
            for p in chosen:
                j = J.dc_job(cfg, d, config, cdef.get("clock_ns") or design[f"phi_main_ns_{lib}"], priority)
                j["kind"] = "dc_hidden"
                j["payload"].update(rtl=[str(Path(C.ROOT) / p["path"])], incdirs=[], is_baseline=0, pert_id=p["pert_id"], design=design)
                jobs.append(j)
    return jobs


def submit_noise(cfg, suites, designs, priority, dry_run):
    from src.jobqueue.core import Queue
    vis = db.connect(cfg=cfg)
    jobs = noise_jobs(cfg, vis, suites, designs, priority)
    by_cfg = {}
    for j in jobs:
        by_cfg[j["config"]] = by_cfg.get(j["config"], 0) + 1
    print(f"{len(jobs)} hidden noise jobs: {by_cfg}")
    if dry_run:
        return 0
    q = Queue(cfg, vis, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    for j in jobs:
        q.submit(j["kind"], j["payload"], design_id=j["design_id"], config=j["config"], priority=j["priority"], timeout_sec=j["timeout_sec"])
    print(f"submitted {len(jobs)} dc_hidden jobs")
    return 0


def noise_floor(cfg, suites=None, designs=None, vis=None, hid=None):
    """sigma_D of the hidden configurations into the hidden noise_floor table; -> {config: rows written}."""
    vis = vis or db.connect(cfg=cfg)
    hid = hid or db.connect(path=hidden_db_path(cfg))
    configs = [c for c in cfg["noise"]["configs"] + cfg["noise"].get("configs_light", []) if cfg["configs"][c].get("hidden")]
    written = {}
    for d, r in _selected(vis, suites, designs):
        proven = {p["pert_id"] for p in _proven(vis, d["design_id"])}
        for config in configs:
            base = hid.execute("SELECT * FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL "
                               "AND status='ok' ORDER BY eval_id DESC LIMIT 1", (d["design_id"], config)).fetchone()
            if base is None:
                continue
            latest = {}
            for x in hid.execute("SELECT * FROM evaluations WHERE design_id=? AND config=? AND pert_id IS NOT NULL AND status='ok' "
                                 "AND abs(clock_ns-?)<1e-6 ORDER BY eval_id", (d["design_id"], config, base["clock_ns"])):
                if x["pert_id"] in proven:
                    latest[x["pert_id"]] = dict(x)
            if len(latest) < 2:
                continue
            rows = S.floor_rows(d["design_id"], config, dict(base), list(latest.values()), base["clock_ns"])
            written[config] = written.get(config, 0) + S.upsert_floor(hid, rows)
    return written


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
    ap.add_argument("--migrate-phase0", action="store_true")
    ap.add_argument("--suite", nargs="*", default=None)
    ap.add_argument("--design", nargs="*", default=None)
    ap.add_argument("--priority", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    if a.job:
        return run_job(cfg, a.job)
    if a.submit_noise:
        return submit_noise(cfg, a.suite, a.design, a.priority, a.dry_run)
    if a.noise_floor:
        written = noise_floor(cfg, a.suite, a.design)
        print("hidden noise_floor rows written per configuration:", written)
        return 0
    if a.migrate_phase0:
        return migrate_phase0(cfg)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
