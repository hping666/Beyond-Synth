"""PrimeTime / PrimePower runner for the hidden signoff configuration H4 (docs/spec/01 §1, spec 06 §1).

Reads the netlist and the fully expanded constraints DC wrote for the source configuration (E4: netlist.v and
design.sdc), runs flow/sta.py sign_off() for signoff timing and flow/power.py analyze() for power (the same SAIF
as the DC power path when available, otherwise explicit toggle rates), through the read-only flow/ scripts.
PrimeTime numbers come from full-precision attributes (get_timing_paths), not from the rounded text report.
"""
import shutil
import sys
import time
from pathlib import Path


def _flow_modules(cfg):
    fd = cfg["project"]["flow_dir"]
    if fd not in sys.path:
        sys.path.insert(0, fd)
    import power  # noqa: E402  (flow/power.py)
    import sta  # noqa: E402  (flow/sta.py)
    return sta, power


def run_pt(job_dir, netlist, sdc, top, lib, cfg, *, saif=None, saif_instance=None, timeout_sec=None):
    job_dir = Path(job_dir)
    inputs, outputs = job_dir / "inputs", job_dir / "outputs"
    inputs.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)
    tools = cfg["tools"]
    rec = {"tool": "pt_primepower", "tool_version": f"pt {tools['pt']['version']} / primepower {tools['primepower']['version']}",
           "lib": lib, "status": "unknown", "error": None, "checks": {}, "metrics": {}, "dc_seconds": 0.0, "wall_seconds": None}
    netlist, sdc = Path(netlist), Path(sdc)
    if not netlist.exists() or not sdc.exists():
        rec.update(status="input_missing", error=f"netlist or sdc missing: {netlist} / {sdc}")
        return rec
    shutil.copyfile(netlist, inputs / "netlist.v")
    shutil.copyfile(sdc, inputs / "design.sdc")
    if saif:
        shutil.copyfile(saif, inputs / Path(saif).name)
    sta, power = _flow_modules(cfg)
    timeout = float(timeout_sec or cfg["timeouts"]["pt"] * 60)
    t0 = time.time()
    r_sta = sta.sign_off(str(outputs), top, lib=lib, netlist=str(inputs / "netlist.v"), sdc=str(inputs / "design.sdc"), timeout=timeout)
    r_pwr = power.analyze(str(outputs), top, lib=lib, netlist=str(inputs / "netlist.v"), sdc=str(inputs / "design.sdc"),
                          mode="averaged", saif=str(inputs / Path(saif).name) if saif else None,
                          strip_path=saif_instance, timeout=timeout)
    rec["wall_seconds"] = round(time.time() - t0, 1)
    rec["pt"] = {k: r_sta.get(k) for k in ("status", "error", "timing", "summary", "violations", "runtime_s", "pt_errors")}
    rec["primepower"] = {k: r_pwr.get(k) for k in ("status", "error", "activity", "total", "groups", "runtime_s", "accuracy", "pt_errors")}
    timing = r_sta.get("timing") or {}
    setup = (r_sta.get("summary") or {}).get("setup") or {}
    total = r_pwr.get("total") or {}
    time_scale = float(cfg["libs"][lib].get("time_scale", 1.0))
    wns = timing.get("wns")
    tns = setup.get("tns")
    m = {"wns_ns": wns / time_scale if wns is not None else None,
         "tns_ns": tns / time_scale if tns is not None else None,
         "hold_wns_ns": (timing.get("hold_wns") / time_scale) if timing.get("hold_wns") is not None else None,
         "cells": timing.get("cells"),
         "power_saif_mw": total.get("total_mw") if r_pwr.get("activity") in ("saif", "vcd") else None,
         "power_default_mw": total.get("total_mw") if str(r_pwr.get("activity", "")).startswith("explicit") else None,
         "power_dynamic_mw": total.get("dynamic_mw"), "power_leakage_mw": total.get("leakage_mw")}
    rec["metrics"] = m
    rec["crit_path"] = {"startpoint": timing.get("startpoint"), "endpoint": timing.get("endpoint")}
    checks = {"pt_ok": r_sta.get("status") == "ok", "primepower_ok": r_pwr.get("status") == "ok",
              "timing_parsed": m["wns_ns"] is not None,
              "power_parsed": (m["power_saif_mw"] is not None) or (m["power_default_mw"] is not None),
              "saif_used_when_given": (not saif) or r_pwr.get("activity") == "saif"}
    rec["checks"] = checks
    failed = [k for k, v in checks.items() if not v]
    rec["status"] = "ok" if not failed else "failed"
    if failed:
        rec["error"] = "checklist failed: " + ", ".join(failed) + "; " + str(r_sta.get("error") or r_pwr.get("error") or "")
    rec["reports_dir"] = str(outputs)
    return rec
