"""Evaluation service (docs/spec/01-eval-service.md): one call = one configuration on one RTL, producing a
content-addressed job directory under results/raw/<design_id>/<config>/<hash>/ with inputs/, outputs/ and
meta.json, and (for status ok) one row in results.sqlite.evaluations via src/db/ingest.py.

Configuration names (E1..E4, E2r/E2t/E2g, H1, H2a, H2b, H3, H5, Y, O0..O2) are resolved from config:
configs; the clock comes from the design's knee-point constraint (phi_main_ns_<lib>) unless the configuration
fixes it (H1) or the caller overrides it (Phase 0 smoke, knee sweeps).
Directories are append-only: a rerun of identical inputs returns the cached ok record unless force_rerun=True,
in which case a new directory <hash>-r<N> is created (docs/PLAN.md §1).
"""
import datetime
import hashlib
import json
from pathlib import Path

from src import config as C
from src.db import ingest
from src.eval.dc import run_dc
from src.eval.sdc import clock_ports

CLOCK_KEYS = {"phi_main": "phi_main_ns_nangate45", "phi_main_asap7": "phi_main_ns_asap7",
              "phi_main_sky130hd": "phi_main_ns_sky130hd"}


def canonical_config(cfg, name):
    """Follow `alias_of` links (E2r -> E3): one DC run serves both roles; records are stored under the target name."""
    seen = []
    while "alias_of" in cfg["configs"][name]:
        seen.append(name)
        name = cfg["configs"][name]["alias_of"]
        if name in seen:
            raise ValueError(f"alias cycle: {seen}")
    return name


def resolve_config(cfg, name, design=None, clock_ns=None):
    """-> dict(tool, compile/script, lib, clock_ns, mode, ...) for configuration `name` (aliases resolved)."""
    name = canonical_config(cfg, name)
    c = cfg["configs"][name]
    lib = c.get("lib")
    if clock_ns is None:
        if "clock_ns" in c:
            clock_ns = float(c["clock_ns"])
        else:
            if c.get("clock") == "sweep":
                raise ValueError(f"configuration {name} is a knee-sweep configuration: pass clock_ns explicitly")
            key = CLOCK_KEYS.get(c.get("clock"))
            if not key or not design or design.get(key) is None:
                raise ValueError(f"configuration {name} needs the design's {key or c.get('clock')} clock; none given")
            clock_ns = float(design[key])
    out = {"config": name, "tool": c["tool"], "lib": lib, "clock_ns": float(clock_ns)}
    if c["tool"] == "dc":
        out["compile"] = c["compile"]
        out["mode"] = "topo" if "-spg" in c["compile"] else "wireload"
        out["synlib"] = c.get("synlib", "dw")
        out["dont_use"] = list((cfg["libs"].get(lib) or {}).get("dont_use") or [])  # library-level excluded cells (part of the hash)
    elif c["tool"] in ("yosys_opensta",):
        out["script"] = c["script"]
        for key in ("read_sv", "io_delay_frac", "sta_max_delay"):
            if key in c:
                out[key] = c[key]
    elif c["tool"] == "pt_primepower":
        out["input"] = c.get("input")
    return out


class HiddenConfigError(ValueError):
    """A hidden configuration was asked to record into the visible database, or vice versa (CLAUDE.md rule 3)."""


def db_is_hidden(conn):
    """True when the connection's main database file lives under a hidden/ directory (the hidden results DB)."""
    row = conn.execute("PRAGMA database_list").fetchone()
    path = ((row[2] if row else "") or "").replace("\\", "/")
    return "/hidden/" in path


def source_evaluation(conn, design_id, cand_id, pert_id, input_spec, clock_ns=None):
    """The latest ok evaluation whose netlist a signoff configuration reads (e.g. input 'E4_netlist' -> config E4); with
    `clock_ns` the latest record at that period (D's E4 baselines exist at several knee-sweep periods, so the signoff run at
    Phi_main must not pick up a tighter-period sweep record; 2026-09-15)."""
    config = str(input_spec).split("_")[0]
    q = ("SELECT raw_dir, eval_id, clock_ns FROM evaluations WHERE design_id=? AND config=? AND status='ok' "
         "AND COALESCE(cand_id,'')=COALESCE(?,'') AND COALESCE(pert_id,'')=COALESCE(?,'')")
    args = [design_id, config, cand_id, pert_id]
    if clock_ns is not None:
        q += " AND abs(clock_ns-?)<1e-6"
        args.append(float(clock_ns))
    row = conn.execute(q + " ORDER BY eval_id DESC LIMIT 1", args).fetchone()
    return dict(row) if row else None


def _hash_inputs(rtl_files, res, clk_port, cfg, extra=None):
    h = hashlib.sha256()
    for f in sorted(str(Path(p).resolve()) for p in rtl_files):
        h.update(Path(f).name.encode() + b"\0" + Path(f).read_bytes() + b"\0")
    h.update(json.dumps(res, sort_keys=True).encode())
    h.update((clk_port or "").encode())
    h.update(C.cfg_hash().encode())
    h.update(json.dumps(cfg["tools"], sort_keys=True).encode())
    h.update(json.dumps(cfg["constraints"], sort_keys=True).encode())
    if extra:
        h.update(json.dumps(extra, sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]


def job_directory(raw_root, force_rerun=False):
    """The content-addressed directory, or a fresh -rN sibling when rerunning or after a failed attempt."""
    raw_root = Path(raw_root)
    meta = raw_root / "meta.json"
    if raw_root.exists():
        status = None
        if meta.exists():
            try:
                status = json.loads(meta.read_text()).get("status")
            except json.JSONDecodeError:
                status = None
        if status == "ok" and not force_rerun:
            return raw_root, True
        n = 2
        while (raw_root.parent / f"{raw_root.name}-r{n}").exists():
            n += 1
        return raw_root.parent / f"{raw_root.name}-r{n}", False
    return raw_root, False


def evaluate(cfg, conn, design_id, rtl_files, top, config_name, *, clock_ns=None, design=None, clk_port="clk",
             cand_id=None, pert_id=None, is_baseline=0, saif=None, saif_instance=None, sverilog=False,
             incdirs=None, force_rerun=False, do_ingest=True, timeout_sec=None, source_conn=None, extra_meta=None):
    """clk_port: one port name, a whitespace-separated list of names or a list (all clocks get the same period).
    Hidden configurations (config `hidden: true`) may only be recorded through a connection to the hidden database
    (opened by scripts/hidden_worker.py) and write their raw directories under the hidden results tree; visible
    configurations may not be recorded there (CLAUDE.md rule 3). `phase1_knee_only` configurations (K_asap7,
    K_sky130hd) accept original designs only. source_conn: where a signoff configuration looks up the
    netlist-producing evaluation (defaults to conn)."""
    config_name = canonical_config(cfg, config_name)
    cdef = cfg["configs"][config_name]
    hidden = bool(cdef.get("hidden"))
    if conn is not None and hidden != db_is_hidden(conn):
        raise HiddenConfigError(
            f"{config_name} is a {'hidden' if hidden else 'visible'} configuration but the database connection is "
            f"{'not ' if hidden else ''}the hidden one (CLAUDE.md rule 3)")
    if cdef.get("phase1_knee_only") and (cand_id or pert_id):
        raise ValueError(f"{config_name} is a Phase 1 knee-sweep configuration for original designs only (got cand_id={cand_id!r}, pert_id={pert_id!r})")
    clk_port = " ".join(clock_ports(clk_port)) or None
    res = resolve_config(cfg, config_name, design, clock_ns)
    extra = {"saif": str(saif) if saif else None, "sverilog": bool(sverilog), "cand_id": cand_id, "pert_id": pert_id}
    source = None
    if res["tool"] == "pt_primepower":
        source = source_evaluation(source_conn or conn, design_id, cand_id, pert_id, res["input"], clock_ns=res.get("clock_ns"))
        if source is None:
            raise ValueError(f"{config_name} needs an ok {res['input']} evaluation of {design_id}/{cand_id}/{pert_id} at {res.get('clock_ns')} ns first")
        extra["source_raw_dir"] = source["raw_dir"]
    h = _hash_inputs(rtl_files, res, clk_port, cfg, extra)
    root = Path(C.results_dir(cfg)) / ("hidden/raw" if hidden else "raw") / design_id / config_name / h
    job_dir, cached = job_directory(root, force_rerun)
    if cached:
        meta = json.loads((job_dir / "meta.json").read_text())
        meta["cached"] = True
        if do_ingest and conn is not None and meta["status"] == "ok" and not meta.get("eval_id"):
            meta["eval_id"] = _ingest_once(conn, meta)   # an earlier run that produced the record but never reached the DB
            (job_dir / "meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True, default=str))
        return meta
    job_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.datetime.now().isoformat(timespec="seconds")
    if res["tool"] == "dc":
        rec = run_dc(job_dir, rtl_files, top, res["lib"], res["compile"], res["clock_ns"], clk_port, cfg, mode=res["mode"],
                     saif=saif, saif_instance=saif_instance, sverilog=sverilog, incdirs=incdirs, timeout_sec=timeout_sec,
                     synlib=res.get("synlib", "dw"), dont_use=res.get("dont_use") or None)
    elif res["tool"] == "yosys_opensta":
        from src.eval.yosys import run_yosys
        rec = run_yosys(job_dir, rtl_files, top, res["lib"], res["script"], res["clock_ns"], clk_port, cfg,
                        sverilog=sverilog or bool(res.get("read_sv")), incdirs=incdirs, timeout_sec=timeout_sec,
                        io_delay_frac=res.get("io_delay_frac"), sta_max_delay=bool(res.get("sta_max_delay")))
    elif res["tool"] == "pt_primepower":
        from src.eval.pt import run_pt
        src_reports = Path(source["raw_dir"]) / "outputs" / "reports"
        rec = run_pt(job_dir, src_reports / "netlist.v", src_reports / "design.sdc", top, res["lib"], cfg,
                     saif=saif, saif_instance=saif_instance, timeout_sec=timeout_sec)
        rec["source_raw_dir"] = source["raw_dir"]
        rec["source_config"] = res["input"]
    else:
        raise NotImplementedError(f"tool {res['tool']} has no runner yet")
    meta = {
        "design_id": design_id, "cand_id": cand_id, "pert_id": pert_id, "is_baseline": int(is_baseline),
        "config": config_name, "top": top, "clk_port": clk_port, "rtl_files": [str(Path(p).resolve()) for p in rtl_files],
        "input_hash": h, "raw_dir": str(job_dir), "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(),
        "started_at": started, "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "cached": False,
    }
    meta.update(extra_meta or {})   # DECISION 2026-09-18 item 1: offline_eval / prescreened_offline flags of the offline pool's records
    meta.update(rec)
    (job_dir / "meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True, default=str))
    if do_ingest and conn is not None and meta["status"] == "ok":
        meta["eval_id"] = _ingest_once(conn, meta)
        (job_dir / "meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True, default=str))
        meta["pruned"] = prune_scratch(job_dir, cfg)
    return meta


SCRATCH_DIRS = ("dc_work", "mw_design")


def prune_scratch(job_dir, cfg):
    """Retention policy (config `retention`, DECISIONS 2026-09-12): after an ok record is ingested, DC's own scratch
    (`outputs/dc_work`: command.log, default.svf, *.pvl/*.syn/*.mr, alib) and the Milkyway design library are removed;
    reports, netlist, ddc, applied SDC, logs and meta.json are kept. Failed records are never pruned. Returns the
    list of directories removed."""
    import shutil
    r = cfg.get("retention") or {}
    if not r.get("prune_dc_work_after_ingest", False):
        return []
    meta_path = Path(job_dir) / "meta.json"
    if not meta_path.exists():
        return []
    try:
        status = json.loads(meta_path.read_text()).get("status")
    except json.JSONDecodeError:
        return []
    if status != "ok":
        return []
    removed = []
    for name in SCRATCH_DIRS:
        d = Path(job_dir) / "outputs" / name
        if d.is_dir():
            shutil.rmtree(d)
            removed.append(str(d))
    return removed


def _ingest_once(conn, meta):
    """Ingest, or return the eval_id of the row that already holds this raw_dir (UNIQUE(raw_dir))."""
    import sqlite3
    try:
        return ingest.ingest_evaluation(conn, meta)
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT eval_id FROM evaluations WHERE raw_dir=?", (meta["raw_dir"],)).fetchone()
        return row["eval_id"] if row else None
