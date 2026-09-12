"""Design Compiler driver for the evaluation service (docs/spec/01-eval-service.md §2).

run_dc() runs one configuration (compile command, library, clock) on one RTL through the project template
src/eval/templates/dc_eval.tcl inside a job directory:
    <job>/inputs/rtl/*.v, constraint.sdc (OpenSTA-native), constraint_dc.sdc (Synopsys copy)
    <job>/outputs/reports/*.rpt, netlist.v, design.ddc, metrics.txt, status.txt; outputs/dc_shell.log
and returns a record with status, metrics, cell histogram, resources, critical path, log summary and the
bidirectional checklist. It never modifies /hdd1/hping/eda/flow/; it only sources flow/sdc_compat.tcl.
Status values follow flow/synth.py: ok, analyze_failed, elaborate_failed, link_failed, constraint_failed,
constraint_incomplete, compile_failed, empty_netlist, report_missing, license_failed, timeout, dc_crashed,
setup_failed, library_missing.
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from src import config as C
from src.eval import parse as P
from src.eval.sdc import dc_sdc, opensta_sdc

TEMPLATE = Path(__file__).resolve().parent / "templates" / "dc_eval.tcl"


def resolve_dbs(spec):
    spec = Path(str(spec))
    if spec.suffix == ".list":
        if not spec.exists():
            return []
        return [Path(l.strip()) for l in spec.read_text().splitlines() if l.strip()]
    return [spec]


def stage_inputs(job_dir, rtl_files):
    rtl_dir = Path(job_dir) / "inputs" / "rtl"
    rtl_dir.mkdir(parents=True, exist_ok=True)
    staged = []
    for f in rtl_files:
        src = Path(f).resolve()
        dst = rtl_dir / src.name
        if dst.exists() and dst.read_bytes() != src.read_bytes():
            dst = rtl_dir / f"{src.stem}_{len(staged)}{src.suffix}"
        shutil.copyfile(src, dst)
        staged.append(dst)
    return staged


def run_dc(job_dir, rtl_files, top, lib, compile_cmd, clock_ns, clk_port, cfg, *, mode=None, saif=None,
           saif_instance=None, sverilog=False, incdirs=None, dont_use=None, timeout_sec=None, max_cores=None,
           sdc_override=None):
    """sdc_override: a ready Synopsys SDC used instead of the generated one (negative tests only)."""
    job_dir = Path(job_dir)
    inputs, outputs = job_dir / "inputs", job_dir / "outputs"
    reports, dc_work = outputs / "reports", outputs / "dc_work"
    for d in (inputs, reports, dc_work):
        d.mkdir(parents=True, exist_ok=True)
    tools, lib_cfg = cfg["tools"], cfg["libs"][lib]
    mode = mode or ("topo" if "-spg" in compile_cmd else "wireload")
    time_scale = float(lib_cfg.get("time_scale", 1.0))
    rec = {"tool": "dc", "tool_version": tools["dc"]["version"], "config_compile": compile_cmd, "lib": lib,
           "clock_ns": float(clock_ns), "mode": mode, "status": "unknown", "error": None, "checks": {},
           "metrics": {}, "dc_seconds": None, "wall_seconds": None}

    dbs = resolve_dbs(lib_cfg["db"])
    missing = [str(p) for p in dbs if not p.exists()]
    if not dbs or missing:
        rec.update(status="library_missing", error=f"library .db missing: {missing or lib_cfg['db']}")
        return rec
    if mode == "topo" and not lib_cfg.get("physical_ref_for_spg"):
        rec.update(status="constraint_failed", error=f"library {lib} has no Milkyway physical library for topo/-spg")
        return rec

    staged = stage_inputs(job_dir, rtl_files)
    sdc_text = opensta_sdc(top, clk_port, clock_ns, cfg, lib)
    (inputs / "constraint.sdc").write_text(sdc_text)
    dc_sdc_path = inputs / "constraint_dc.sdc"
    dc_sdc_path.write_text(Path(sdc_override).read_text() if sdc_override else dc_sdc(sdc_text, time_scale))

    dc_home = tools["dc"]["home"]
    env = dict(os.environ)
    env.update({
        "SYNOPSYS": dc_home,
        "PATH": f"{dc_home}/bin:" + env.get("PATH", ""),
        "LD_LIBRARY_PATH": "/hdd1/hping/eda/lib:" + env.get("LD_LIBRARY_PATH", ""),
        "EVAL_VERILOG": " ".join(str(p) for p in staged),
        "EVAL_TOP": top,
        "EVAL_FORMAT": "sverilog" if sverilog else "verilog",
        "EVAL_INCDIRS": " ".join(str(Path(d).resolve()) for d in (incdirs or [])),
        "EVAL_LIB_DB": " ".join(str(p) for p in dbs),
        "EVAL_LIB_NAME": lib_cfg["name"],
        "EVAL_DONT_USE": " ".join(dont_use or []),
        "EVAL_SDC": str(dc_sdc_path),
        "EVAL_CLK_NAME": cfg["constraints"]["clock_name"],
        "EVAL_CLK_PERIOD": f"{float(clock_ns) * time_scale:g}",
        "EVAL_OUT": str(reports),
        "EVAL_COMPILE": compile_cmd,
        "EVAL_MAX_CORES": str(max_cores or tools["dc"]["max_cores"]),
        "EVAL_MAX_FANOUT": str(cfg["constraints"]["max_fanout"]),
        "EVAL_MODE": mode,
        "EVAL_MW_REF": str(lib_cfg.get("physical_ref_for_spg") or ""),
        "EVAL_MW_TF": str(lib_cfg.get("mw_tf") or ""),
        "EVAL_CG_STYLE": str(cfg["constraints"].get("clock_gating_style") or ""),
        "EVAL_SAIF": str(saif) if saif else "",
        "EVAL_SAIF_INSTANCE": saif_instance or "",
        "EVAL_FLOW_DIR": cfg["project"]["flow_dir"],
        "SNPS_MALLOC_STATS": "0",
    })
    timeout_sec = float(timeout_sec or cfg["timeouts"]["dc_medium"] * 60)
    argv = [f"{dc_home}/bin/dc_shell"] + (["-topographical_mode"] if mode == "topo" else []) + ["-f", str(TEMPLATE)]
    t0 = time.time()
    try:
        proc = subprocess.run(argv, cwd=str(dc_work), env=env, timeout=timeout_sec, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        log, timed_out, rc = proc.stdout, False, proc.returncode
    except subprocess.TimeoutExpired as e:
        log, timed_out, rc = (e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode(errors="replace")), True, -1
    rec["wall_seconds"] = round(time.time() - t0, 1)
    rec["dc_returncode"] = rc
    (outputs / "dc_shell.log").write_text(log or "")

    st = P.kv_file((reports / "status.txt").read_text()) if (reports / "status.txt").exists() else {}
    if timed_out:
        rec.update(status="timeout", error=f"dc_shell exceeded {timeout_sec:.0f} s")
    elif not st:
        rec.update(status="dc_crashed", error=(log or "")[-2000:] or "no output")
    else:
        rec["status"] = st.get("status", "unknown")
        rec["error"] = st.get("error") or None
        rec["compile_seconds"] = float(st.get("elapsed") or 0)   # the compile command alone (1 s resolution)
        rec["dc_seconds"] = rec["wall_seconds"]                     # seat occupancy: startup + license + compile + reports
        rec["check_design_errors"] = int(st.get("check_errors") or -1)
        rec["saif_status"] = st.get("saif", "none")
    if rec["status"] != "ok":
        sig = P.license_failure(log)
        if sig:
            rec.update(status="license_failed", error=sig)
    errs = P.sdc_errors(log)
    if errs:
        rec["sdc_errors"] = errs[:10]
        if rec["status"] == "ok":
            rec.update(status="constraint_incomplete", error=errs[0])
    if rec["status"] != "ok":
        el = P.error_lines(log)
        if el:
            rec["dc_errors"] = el[:10]
            if not rec["error"] or "returned 0" in str(rec["error"]):
                rec["error"] = el[0]
        return rec

    # ---- reports and metrics ----
    def read(name):
        p = reports / name
        return p.read_text(errors="replace") if p.exists() else ""

    qor = P.parse_qor(read("qor.rpt"))
    area = P.parse_area(read("area.rpt"))
    refs = P.parse_reference(read("refs.rpt"))
    res = P.parse_resources(read("resources.rpt"))
    paths = P.parse_timing(read("timing.rpt"))
    metrics_txt = P.kv_file(read("metrics.txt"))
    power_default = P.parse_power(read("power_default.rpt"))
    power_saif = P.parse_power(read("power_saif.rpt")) if rec.get("saif_status") == "ok" else {}
    cg = P.parse_clock_gating(read("clock_gating.rpt")) if "-gate_clock" in compile_cmd else {}
    wns_attr = P._num(metrics_txt.get("wns"))
    m = {
        "area": qor.get("area", area.get("total")),
        "cells": int(qor["cells"]) if qor.get("cells") is not None else area.get("cells"),
        "wns_ns": (wns_attr if wns_attr is not None else qor.get("wns")),
        "tns_ns": qor.get("tns"),
        "crit_delay_ns": qor.get("crit_delay"),
        "period_lib_units": qor.get("period"),
        "registers": P._num(metrics_txt.get("registers")),
        "hier_cells": P._num(metrics_txt.get("hier_cells")),
        "power_default_mw": power_default.get("total_mw"),
        "power_saif_mw": power_saif.get("total_mw"),
        "seq_cells": area.get("seq_cells"),
        "comb_cells": area.get("comb_cells"),
        "comb_area": area.get("comb_area"),
        "noncomb_area": area.get("noncomb_area"),
    }
    for k in ("wns_ns", "tns_ns", "crit_delay_ns"):
        if m[k] is not None and time_scale != 1.0:
            m[k] = m[k] / time_scale
    m["icg_count"] = cg.get("icg_count", 0 if "-gate_clock" in compile_cmd else None)
    m.update({f"cg_{k}": v for k, v in cg.items()})
    rec["metrics"] = m
    rec["hist"] = refs["hist"]
    rec["resources"] = res
    rec["crit_path"] = paths[0] if paths else None
    rec["path_endpoints"] = [[p.get("startpoint"), p.get("endpoint"), p.get("slack")] for p in paths]
    rec["log_summary"] = P.log_summary(log)
    rec["power_default"] = power_default
    rec["power_saif"] = power_saif

    # ---- bidirectional checklist (CLAUDE.md rule 2): every item must be true for status ok ----
    required = ["qor.rpt", "area.rpt", "timing.rpt", "refs.rpt", "resources.rpt", "power_default.rpt",
                "netlist.v", "design.ddc", "applied_constraints.sdc", "metrics.txt"]
    checks = {
        "status_ok": True,
        "reports_present": all((reports / f).exists() and (reports / f).stat().st_size > 0 for f in required),
        "area_positive": bool(m["area"] and m["area"] > 0),
        "cells_positive": bool(m["cells"] and m["cells"] > 0),
        "clock_present": "create_clock" in read("applied_constraints.sdc"),
        "timing_parsed": m["wns_ns"] is not None and m["tns_ns"] is not None,
        "histogram_nonempty": refs["n_cells"] > 0,
        "no_unhandled_errors": len(P.error_lines(log)) == 0,
        "no_sdc_errors": not errs,
    }
    rec["checks"] = checks
    failed = [k for k, v in checks.items() if not v]
    if failed:
        rec.update(status="report_missing" if "reports_present" in failed else "failed",
                   error="checklist failed: " + ", ".join(failed))
    rec["reports_dir"] = str(reports)
    rec["netlist"] = str(reports / "netlist.v") if (reports / "netlist.v").exists() else None
    rec["sdc"] = str(inputs / "constraint.sdc")
    rec["sdc_dc"] = str(dc_sdc_path)
    return rec
