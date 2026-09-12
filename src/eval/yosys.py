"""Yosys + ABC + OpenSTA runner for the reference caliber Y and the open-source ladder O0–O2
(docs/spec/01-eval-service.md §5). The synthesis script comes from config (configs.<name>.script with {top},
{lib} and {abc_heavy_script} placeholders; Liberty from libs.<lib>.liberty); the runner adds read_verilog and
write_verilog, then OpenSTA reads the netlist with the same OpenSTA-native SDC as every other tool.
Deterministic: no randomized ABC commands.
"""
import os
import re
import subprocess
import time
from pathlib import Path

from src import config as C
from src.eval.dc import stage_inputs
from src.eval.sdc import opensta_sdc


def _stat_metrics(log):
    """Area, cell count and cell-type histogram from the last `stat -liberty` block in the Yosys log."""
    area = None
    for m in re.finditer(r"Chip area for (?:top )?module '\\?([^']+)':\s*([\d.]+(?:[eE][-+]?\d+)?)", log):
        area = float(m.group(2))
    cells, hist = None, {}
    # Yosys >= 0.4x prints "   85  155.344 cells" followed by "    3    3.192   AND2_X1" rows;
    # older versions print "Number of cells: 85" followed by "  AND2_X1  3" rows. Take the last table (the top).
    new = list(re.finditer(r"^\s+(\d+)\s+(?:[\d.eE+-]+|-)\s+cells\s*\n((?:\s+\d+\s+(?:[\d.eE+-]+|-)\s+\S+\s*\n)*)", log, re.M))
    old = list(re.finditer(r"Number of cells:\s+(\d+)\n((?:\s+\S+\s+\d+\n)*)", log))
    if new:
        b = new[-1]
        cells = int(b.group(1))
        for line in b.group(2).splitlines():
            m = re.match(r"\s+(\d+)\s+(?:[\d.eE+-]+|-)\s+(\S+)\s*$", line)
            if m:
                hist[m.group(2).lstrip("\\")] = hist.get(m.group(2).lstrip("\\"), 0) + int(m.group(1))
    elif old:
        b = old[-1]
        cells = int(b.group(1))
        for line in b.group(2).splitlines():
            m = re.match(r"\s+(\S+)\s+(\d+)\s*$", line)
            if m:
                hist[m.group(1).lstrip("\\")] = hist.get(m.group(1).lstrip("\\"), 0) + int(m.group(2))
    return area, cells, hist


def _sta_metrics(log, clock_name="clk"):
    """wns/tns from report_wns / report_tns; the critical path from the report_checks block of the clock group
    (report_checks lists the asynchronous recovery group first, which is not the datapath)."""
    out = {}
    # OpenSTA prints "wns max 0.00" / "tns max 0.00": worst NEGATIVE slack, clipped at 0. DC reports the worst slack
    # itself (positive when timing is met), so wns_ns below is taken from the report_checks paths for the same meaning.
    m = re.search(r"^\s*wns(?:\s+max)?\s+(-?[\d.]+(?:[eE][-+]?\d+)?)", log, re.M)
    if m:
        out["wns_report"] = float(m.group(1))
    m = re.search(r"^\s*tns(?:\s+max)?\s+(-?[\d.]+(?:[eE][-+]?\d+)?)", log, re.M)
    if m:
        out["tns_ns"] = float(m.group(1))
    blocks = []
    for blk in re.split(r"(?=^Startpoint:)", log, flags=re.M)[1:]:
        b = {"startpoint": re.search(r"Startpoint:\s*(\S+)", blk).group(1)}
        for key, pat in (("endpoint", r"Endpoint:\s*(\S+)"), ("group", r"Path Group:\s*(\S+)")):
            mm = re.search(pat, blk)
            if mm:
                b[key] = mm.group(1)
        mm = re.search(r"(-?[\d.]+)\s+data arrival time", blk)
        if mm:
            b["arrival"] = float(mm.group(1))
        mm = re.search(r"(-?[\d.]+)\s+slack \((MET|VIOLATED)\)", blk)
        if mm:
            b["slack"] = float(mm.group(1))
        blocks.append(b)
    crit = [b for b in blocks if b.get("group") == clock_name] or blocks
    if crit:
        b = min(crit, key=lambda x: x.get("slack", float("inf")))
        out.update({"crit_delay_ns": b.get("arrival"), "startpoint": b.get("startpoint"), "endpoint": b.get("endpoint"),
                    "crit_slack_ns": b.get("slack"), "crit_group": b.get("group")})
        slacks = [x["slack"] for x in blocks if "slack" in x]
        if slacks:
            out["wns_ns"] = min(slacks)
    if "wns_ns" not in out and "wns_report" in out:
        out["wns_ns"] = out["wns_report"]
    return out


def run_yosys(job_dir, rtl_files, top, lib, script_tpl, clock_ns, clk_port, cfg, *, sverilog=False, incdirs=None, timeout_sec=None):
    job_dir = Path(job_dir)
    inputs, outputs = job_dir / "inputs", job_dir / "outputs"
    inputs.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)
    lib_cfg = cfg["libs"][lib]
    tools = cfg["tools"]
    rec = {"tool": "yosys_opensta", "tool_version": f"yosys {tools['yosys']['version']} / {tools['opensta']['version']}",
           "config_script": script_tpl, "lib": lib, "clock_ns": float(clock_ns), "status": "unknown", "error": None,
           "checks": {}, "metrics": {}, "dc_seconds": None, "wall_seconds": None}
    liberty = lib_cfg.get("liberty")
    if not liberty or not Path(liberty).exists():
        rec.update(status="library_missing", error=f"no Liberty file for {lib} (libs.{lib}.liberty)")
        return rec
    staged = stage_inputs(job_dir, rtl_files)
    sdc_path = inputs / "constraint.sdc"
    sdc_path.write_text(opensta_sdc(top, clk_port, clock_ns, cfg, lib))
    abc_heavy = str(Path(C.ROOT) / cfg["configs"].get("abc_heavy_script", ""))
    script = script_tpl.format(top=top, lib=liberty, abc_heavy_script=abc_heavy)
    netlist = outputs / "netlist.v"
    ys = [f"read_verilog {'-sv ' if sverilog else ''}{' '.join('-I ' + str(Path(d).resolve()) for d in (incdirs or []))} {' '.join(str(p) for p in staged)}",
          f"hierarchy -check -top {top}"]
    ys += [s.strip() for s in script.split(";") if s.strip()]
    ys += [f"write_verilog -noattr {netlist}"]
    (inputs / "synth.ys").write_text("\n".join(ys) + "\n")
    t0 = time.time()
    timeout_sec = float(timeout_sec or cfg["timeouts"]["dc_small"] * 60)
    try:
        p = subprocess.run([tools["yosys"]["bin"], "-q", "-l", str(outputs / "yosys.log"), "-s", str(inputs / "synth.ys")],
                           cwd=str(outputs), capture_output=True, text=True, timeout=timeout_sec, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        rec.update(status="timeout", error=f"yosys exceeded {timeout_sec:.0f} s", wall_seconds=round(time.time() - t0, 1))
        return rec
    ylog = (outputs / "yosys.log").read_text(errors="replace") if (outputs / "yosys.log").exists() else p.stdout + p.stderr
    if p.returncode != 0 or not netlist.exists():
        err = [l for l in (ylog + p.stderr).splitlines() if l.startswith("ERROR")]
        rec.update(status="yosys_failed", error=(err[0] if err else f"yosys exit {p.returncode}")[:300],
                   wall_seconds=round(time.time() - t0, 1))
        return rec
    area, cells, hist = _stat_metrics(ylog)
    sta_tcl = inputs / "sta.tcl"
    sta_tcl.write_text("\n".join([
        f"read_liberty {liberty}", f"read_verilog {netlist}", f"link_design {top}", f"read_sdc {sdc_path}",
        "report_checks -path_delay max -format full_clock_expanded", "report_wns", "report_tns", "exit"]) + "\n")
    try:
        s = subprocess.run([tools["opensta"]["bin"], "-exit", str(sta_tcl)], cwd=str(outputs), capture_output=True, text=True,
                           timeout=timeout_sec, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        rec.update(status="timeout", error=f"opensta exceeded {timeout_sec:.0f} s", wall_seconds=round(time.time() - t0, 1))
        return rec
    slog = s.stdout + s.stderr
    (outputs / "opensta.log").write_text(slog)
    rec["wall_seconds"] = round(time.time() - t0, 1)
    rec["dc_seconds"] = 0.0  # no DC seat involved
    sm = _sta_metrics(slog, cfg["constraints"]["clock_name"])
    m = {"area": area, "cells": cells, "wns_ns": sm.get("wns_ns"), "tns_ns": sm.get("tns_ns"),
         "crit_delay_ns": sm.get("crit_delay_ns"), "registers": sum(v for k, v in hist.items() if re.search(r"DFF|dff|SDFF|LATCH", k))}
    rec["metrics"] = m
    rec["hist"] = hist
    rec["crit_path"] = {"startpoint": sm.get("startpoint"), "endpoint": sm.get("endpoint")}
    rec["netlist"] = str(netlist)
    rec["sdc"] = str(sdc_path)
    sta_errors = [l for l in slog.splitlines() if l.startswith("Error")]
    checks = {"status_ok": s.returncode == 0, "area_positive": bool(area and area > 0), "cells_positive": bool(cells and cells > 0),
              "timing_parsed": m["wns_ns"] is not None and m["tns_ns"] is not None, "histogram_nonempty": bool(hist),
              "netlist_present": netlist.exists() and netlist.stat().st_size > 0, "no_sta_errors": not sta_errors}
    rec["checks"] = checks
    failed = [k for k, v in checks.items() if not v]
    rec["status"] = "ok" if not failed else "failed"
    if failed:
        rec["error"] = "checklist failed: " + ", ".join(failed) + (f"; {sta_errors[0]}" if sta_errors else "")
    return rec
