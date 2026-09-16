"""Tiered retention of raw artifacts (G5 decisions item 5 (ii), DECISIONS 2026-09-15).

Full raw artifacts are kept only for accepted candidates (ever in an archive) and for a deterministic audit sample; for
every other candidate evaluation the record (meta.json / equiv.json), the small reports (qor, area, timing, power, the
other .rpt / .txt / .sdc reports), the logs and the scripts stay, and the regenerable artifacts go once the run has
applied the verdict: netlists, ddc, SAIFs and the RTL copy of a DC / Yosys record; VCDs, lock-step traces, port JSONs,
VC Formal databases and learnt data, VCS builds and SAIFs of an equivalence record; the M6 classifier workdir of a
candidate (its features are archived in candidates.features_json). Records, rows and counterexample summaries are never
deleted (CLAUDE.md rule 5: only regenerable artifacts). Every slimmed record carries a `slimmed` marker."""
import hashlib
import json
import shutil
from pathlib import Path

from src.db import core as db

DC_CATEGORIES = {   # category -> (relative glob patterns under the record directory)
    "netlist": ("outputs/reports/*.v", "outputs/reports/*.vg", "outputs/*.v"),
    "ddc": ("outputs/reports/*.ddc",),
    "saif": ("**/*.saif",),
    "inputs_rtl": ("inputs/rtl",),
}
EQ_CATEGORIES = {
    "vcd": ("v2_sim/*.vcd", "v2_sim/*.vcd.gz"),
    "trace": ("v2_sim/trace.txt",),
    "ports": ("v1_ports_c", "v1_ports_d"),
    "seq_rtdb": ("v3_seq/vcst_rtdb", "v3_seq/seq_top_learn_dir"),
    "seq_learnt": ("v3_seq/learnt_data*",),
    "vcs_build": ("v2_sim/csrc", "v2_sim/simv", "v2_sim/simv.daidir"),
    "saif": ("*.saif",),
}


def policy(cfg):
    return (cfg.get("retention") or {})


def free_gb(path=None):
    """Free space of the filesystem holding `path` (default: the results directory's filesystem root `/`) in GB (1e9)."""
    return shutil.disk_usage(str(path or "/")).free / 1e9


def disk_ok(cfg, path=None):
    """Decision 2026-09-15 item 1: the search driver submits no new job while the free space on `/` is below
    `retention.min_free_gb` (15 GB). -> (ok, free_gb, threshold_gb)."""
    thr = float(policy(cfg).get("min_free_gb") or 0.0)
    free = free_gb(path)
    return free >= thr, free, thr


def enabled(cfg):
    return bool(policy(cfg).get("tiered", False))


def is_audit_sample(cand_id, frac):
    """Deterministic audit sample by candidate id (the same rule the hidden layer's rejected-candidate sample uses)."""
    if not cand_id or frac <= 0:
        return False
    h = int(hashlib.sha256(str(cand_id).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return h < float(frac)


def sim_fail_vcd_sampled(cfg, key):
    """Amendment of 2026-09-15 (user) to the VCD decision of 2026-09-14: of the `sim_fail` records only a seeded random
    sample (`retention.sim_fail_vcd_sample`: frac, seed; keyed by the record directory name) keeps its VCD, at record time
    and in the tiered prune; the mismatch cycle and signal values in the record are the evidence."""
    sp = policy(cfg).get("sim_fail_vcd_sample") or {}
    frac = float(sp.get("frac", 1.0) if sp.get("frac") is not None else 1.0)
    if frac >= 1.0:
        return True
    if frac <= 0.0:
        return False
    h = int(hashlib.sha256(f"{sp.get('seed', 0)}|{key}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return h < frac


def keep_full(cfg, cand_id, accepted):
    """True when the candidate's artifacts must stay complete: accepted (ever archived) or in the audit sample."""
    if accepted:
        return True
    return is_audit_sample(cand_id, float(policy(cfg).get("tiered_audit_frac") or 0.0))


def _size(p):
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def _remove(p):
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p)
    else:
        p.unlink()


def _slim(rec_dir, categories, table, record_file, dry_run=False):
    """Delete the artifacts of the configured categories under rec_dir; -> {category: bytes}. Marks the record file."""
    rec_dir = Path(rec_dir)
    freed, removed = {}, []
    for cat in categories:
        for pat in table.get(cat, ()):
            for p in sorted(rec_dir.glob(pat)):
                if not p.exists() or p.name in (record_file,):
                    continue
                b = _size(p)
                freed[cat] = freed.get(cat, 0) + b
                removed.append(str(p.relative_to(rec_dir)))
                if not dry_run:
                    _remove(p)
    if removed and not dry_run:
        f = rec_dir / record_file
        if f.exists():
            try:
                rec = json.loads(f.read_text())
                rec["slimmed"] = {"at": db.now(), "categories": sorted(freed), "bytes": sum(freed.values()), "removed": removed[:40]}
                f.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str))
            except (ValueError, OSError):
                pass
    return freed


def slim_dc_record(rec_dir, cfg, dry_run=False):
    """A DC / Yosys evaluation record of a non-kept candidate: keep meta.json, the reports, the logs and the SDCs."""
    if not enabled(cfg) or not (Path(rec_dir) / "meta.json").exists():
        return {}
    return _slim(rec_dir, policy(cfg).get("tiered_dc_delete") or [], DC_CATEGORIES, "meta.json", dry_run)


def slim_eq_record(rec_dir, cfg, dry_run=False):
    """An equivalence record of a non-kept candidate: keep equiv.json, the logs, seq.tcl, the harness and the candidate copy;
    a sim_fail record of the seeded VCD sample keeps its VCD as well."""
    f = Path(rec_dir) / "equiv.json"
    if not enabled(cfg) or not f.exists():
        return {}
    cats = list(policy(cfg).get("tiered_eq_delete") or [])
    try:
        verdict = json.loads(f.read_text()).get("verdict")
    except (ValueError, OSError):
        verdict = None
    if verdict == "sim_fail" and sim_fail_vcd_sampled(cfg, Path(rec_dir).name):
        cats = [c for c in cats if c != "vcd"]
    return _slim(rec_dir, cats, EQ_CATEGORIES, "equiv.json", dry_run)


def slim_m6_workdir(path, cfg, dry_run=False):
    """The classifier's Yosys workdir of a candidate (features archived in the database)."""
    p = Path(path)
    if str(policy(cfg).get("m6_workdir_after_classification") or "keep") != "delete" or not p.is_dir():
        return 0
    b = _size(p)
    if not dry_run:
        shutil.rmtree(p)
    return b


def slim_candidate(cfg, cand_id, accepted, *, eq_dir=None, fit_dirs=(), m6_dir=None, dry_run=False):
    """Apply the tiered policy to one candidate's artifacts. -> {"kept_full": bool, "freed": {category: bytes}, "m6": bytes}."""
    out = {"kept_full": False, "freed": {}, "m6": 0}
    if not enabled(cfg):
        return out
    if keep_full(cfg, cand_id, accepted):
        out["kept_full"] = True
        return out
    if eq_dir:
        for k, v in slim_eq_record(eq_dir, cfg, dry_run).items():
            out["freed"]["eq_" + k] = out["freed"].get("eq_" + k, 0) + v
    for d in fit_dirs or ():
        if d:
            for k, v in slim_dc_record(d, cfg, dry_run).items():
                out["freed"]["dc_" + k] = out["freed"].get("dc_" + k, 0) + v
    if m6_dir:
        out["m6"] = slim_m6_workdir(m6_dir, cfg, dry_run)
    return out
