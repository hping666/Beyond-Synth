"""Parsers for DC / PrimeTime report files and logs (docs/spec/01-eval-service.md §2.4, §6).

Everything here is pure text processing so that it can be unit-tested on saved reports (tests/fixtures/).
Numbers are parsed from `report_qor` (6 significant digits, see the template) and `metrics.txt`; the cell
histogram from `report_reference`; DesignWare components, implementations and datapath blocks from
`report_resources`; ICG counts from `report_clock_gating`; critical paths from `report_timing`.
"""
import re

_NUM = r"(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"

LICENSE_SIGNATURES = (  # exact FlexLM / DCSH strings (eda-knowledge/05-traps.md #4, #5): never a bare "license"
    "Design Compiler is not enabled",
    "Cannot connect to license server",
    "Failure in Synopsys Common Licensing",
    "License server machine is down",
    "Unable to check out",
    "cannot checkout",
    "No such feature exists",
    "Licensed number of users already reached",
)


def license_failure(log):
    low = (log or "").lower()
    for sig in LICENSE_SIGNATURES:
        if sig.lower() in low:
            return sig
    return None


def sdc_errors(log):
    """Error lines DC printed while sourcing the SDC (it continues after them: traps #2/#3)."""
    if "###SDC_BEGIN###" not in (log or ""):
        return []
    seg = log.split("###SDC_BEGIN###", 1)[1].split("###SDC_END###", 1)[0]
    return [l.strip() for l in seg.splitlines() if l.lstrip().startswith("Error:")]


def error_lines(log):
    seen, out = set(), []
    for l in (log or "").splitlines():
        s = l.strip()
        if s.startswith("Error:") and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def kv_file(text):
    out = {}
    for line in (text or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------- report_qor
def parse_qor(text):
    """Timing per path group, cell counts and area from `report_qor -nosplit`."""
    groups, section, cur = {}, "global", {}
    out = {"groups": groups}
    for line in (text or "").splitlines():
        m = re.match(r"^\s*Timing Path Group '([^']+)'", line)
        if m:
            section = m.group(1)
            groups[section] = cur = {}
            continue
        if re.match(r"^\s*(Cell Count|Area|Design Rules|Hostname|Compile CPU Statistics|Design\s|Timing Path Group)", line):
            if not line.strip().startswith("Timing Path Group"):
                section = "global"
        m = re.match(r"^\s*([A-Za-z][A-Za-z0-9 ./()-]*?):\s+" + _NUM + r"\s*$", line)
        if m:
            key, val = m.group(1).strip(), float(m.group(2))
            (cur if section != "global" else out)[key] = val
    slacks = [g.get("Critical Path Slack") for g in groups.values() if g.get("Critical Path Slack") is not None]
    out["wns"] = min(slacks) if slacks else None
    out["tns"] = sum(g.get("Total Negative Slack", 0.0) for g in groups.values()) if groups else None
    worst = None
    for g in groups.values():
        if g.get("Critical Path Slack") is not None and (worst is None or g["Critical Path Slack"] < worst["Critical Path Slack"]):
            worst = g
    out["crit_delay"] = worst.get("Critical Path Length") if worst else None
    out["period"] = worst.get("Critical Path Clk Period") if worst else None
    out["area"] = out.get("Design Area", out.get("Cell Area"))
    out["cells"] = out.get("Leaf Cell Count")
    return out


# ----------------------------------------------------------------------------- report_area
def parse_area(text):
    keys = {"Number of ports": "ports", "Number of nets": "nets", "Number of cells": "cells",
            "Number of combinational cells": "comb_cells", "Number of sequential cells": "seq_cells",
            "Number of macros/black boxes": "macros", "Number of buf/inv": "buf_inv",
            "Combinational area": "comb_area", "Buf/Inv area": "buf_inv_area",
            "Noncombinational area": "noncomb_area", "Macro/Black Box area": "macro_area",
            "Net Interconnect area": "net_area", "Total cell area": "total", "Total area": "total_with_nets"}
    out = {}
    for line in (text or "").splitlines():
        for k, name in keys.items():
            m = re.match(r"^\s*" + re.escape(k) + r":\s+" + _NUM, line)
            if m:
                out[name] = float(m.group(1))
    return out


# ----------------------------------------------------------------------------- report_reference (histogram)
_REF_ROW = re.compile(r"^(\S+)\s+(\S+)\s+" + _NUM + r"\s+(\d+)\s+" + _NUM + r"\s*([a-z, ]*)\s*$")


def parse_reference(text):
    """Cell-type histogram {reference: count} over all hierarchy levels, hierarchical references excluded."""
    hist, unit_area = {}, {}
    for line in (text or "").splitlines():
        m = _REF_ROW.match(line)
        if not m:
            continue
        ref, lib, uarea, count, total, attrs = m.groups()
        if "h" in attrs.replace(",", " ").split():
            continue
        if ref in ("Total", "Reference"):
            continue
        hist[ref] = hist.get(ref, 0) + int(count)
        unit_area[ref] = float(uarea)
    return {"hist": hist, "unit_area": unit_area, "n_types": len(hist), "n_cells": sum(hist.values())}


# ----------------------------------------------------------------------------- report_resources
_RES_ROW = re.compile(r"^\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$")
_IMPL_ROW = re.compile(r"^\|\s*(\S+)\s*\|\s*(DW\w+)\s*\|\s*(\S+)\s*\|\s*([^|]*?)\s*\|\s*$")


def parse_resources(text):
    """DesignWare resources, implementation choices, sharing and datapath extraction from `report_resources`."""
    resources, impls = [], []
    section = None
    for line in (text or "").splitlines():
        s = line.strip()
        if s.startswith("Resource Report"):
            section = "res"
            continue
        if s.startswith("Implementation Report"):
            section = "impl"
            continue
        if s.startswith("Datapath Report") or s.startswith("Multiplexor Report") or s.startswith("Cell Report"):
            section = "other"
            continue
        if section == "res":
            m = _RES_ROW.match(line)
            if m and m.group(1) not in ("Resource",) and not m.group(1).startswith("-"):
                res, module, params, ops = m.groups()
                resources.append({"resource": res, "module": module, "params": params, "ops": ops.split()})
        elif section == "impl":
            m = _IMPL_ROW.match(line)
            if m:
                cell, module, impl, set_impl = m.groups()
                impls.append({"cell": cell, "module": module, "impl": impl})
    dp_blocks = len(re.findall(r"^\s*Datapath Report for", text or "", re.M))
    shared = [r for r in resources if len(r["ops"]) > 1]
    return {"resources": resources, "implementations": impls, "datapath_blocks": dp_blocks,
            "shared_resources": len(shared), "dw_modules": sorted({r["module"] for r in resources if r["module"].startswith("DW")})}


# ----------------------------------------------------------------------------- report_clock_gating
def parse_clock_gating(text):
    out = {}
    for key, name in (("Number of Clock gating elements", "icg_count"), ("Number of Gated registers", "gated_regs"),
                      ("Number of Ungated registers", "ungated_regs"), ("Total number of registers", "total_regs")):
        # DC prints a table ("| Number of Gated registers | 12 (92.31%) |"); older versions use "key: value"
        m = re.search(re.escape(key) + r"\s*[:|]\s*(\d+)", text or "")
        if m:
            out[name] = int(m.group(1))
    m = re.search(r"Number of tool-inserted clock gating elements\s*\|\s*(\d+)", text or "")
    if m:
        out["icg_tool_inserted"] = int(m.group(1))
    return out


# ----------------------------------------------------------------------------- report_power
def parse_power(text):
    """Total power in mW from `report_power` (DC prints unit suffixes per line)."""
    scale = {"": 1e3, "m": 1.0, "u": 1e-3, "n": 1e-6, "p": 1e-9}
    out = {}
    for key, name in (("Cell Internal Power", "internal"), ("Net Switching Power", "switching"),
                      ("Total Dynamic Power", "dynamic"), ("Cell Leakage Power", "leakage")):
        m = re.search(re.escape(key) + r"\s*=\s*" + _NUM + r"\s*([munp]?)W", text or "")
        if m:
            out[name] = float(m.group(1)) * scale[m.group(2)]
    if "dynamic" in out or "leakage" in out:
        out["total_mw"] = out.get("dynamic", 0.0) + out.get("leakage", 0.0)
    return out


# ----------------------------------------------------------------------------- report_timing
_POINT = re.compile(r"^\s+(\S+)\s+\(([^)]+)\)\s+(?:" + _NUM + r"\s+){0,3}" + _NUM + r"\s+" + _NUM + r"\s*[rf]?\s*$")


def parse_timing(text):
    """Paths from `report_timing -max_paths N -nworst 1 -input_pins ...`; the first one is the critical path."""
    paths, cur, in_points = [], None, False
    for line in (text or "").splitlines():
        m = re.match(r"^\s*Startpoint:\s*(\S+)", line)
        if m:
            cur = {"startpoint": m.group(1), "points": []}
            paths.append(cur)
            in_points = False
            continue
        if cur is None:
            continue
        m = re.match(r"^\s*Endpoint:\s*(\S+)", line)
        if m:
            cur["endpoint"] = m.group(1)
            continue
        m = re.match(r"^\s*Path Group:\s*(\S+)", line)
        if m:
            cur["group"] = m.group(1)
            continue
        if re.match(r"^\s*Point\s+", line):
            in_points = True
            continue
        m = re.match(r"^\s*data arrival time\s+" + _NUM, line)
        if m:
            cur["arrival"] = float(m.group(1))
            in_points = False
            continue
        m = re.match(r"^\s*data required time\s+" + _NUM, line)
        if m:
            cur["required"] = float(m.group(1))
            continue
        m = re.match(r"^\s*slack \((MET|VIOLATED)\)\s+" + _NUM, line)
        if m:
            cur["slack"] = float(m.group(2))
            cur["met"] = m.group(1) == "MET"
            continue
        if in_points:
            m = _POINT.match(line)
            if m:
                pin, cell = m.group(1), m.group(2)
                if cell not in ("in", "out", "inout") and "/" in pin:
                    cur["points"].append([pin, cell])
    return paths


# ----------------------------------------------------------------------------- compile-log summary
_LOG_PATTERNS = {
    "retime": re.compile(r"retim", re.I),
    "ungroup": re.compile(r"ungroup", re.I),
    "datapath": re.compile(r"datapath", re.I),
    "sharing": re.compile(r"\bshar(ed|ing)\b", re.I),
    "clock_gating": re.compile(r"clock[ -]?gat", re.I),
    "warning": re.compile(r"^Warning:"),
    "error": re.compile(r"^Error:"),
}


def log_summary(log, max_samples=8):
    counts = {k: 0 for k in _LOG_PATTERNS}
    samples = {k: [] for k in _LOG_PATTERNS}
    for line in (log or "").splitlines():
        s = line.strip()
        if not s.startswith(("Information:", "Warning:", "Error:")):
            continue
        for k, pat in _LOG_PATTERNS.items():
            if pat.search(s):
                counts[k] += 1
                if len(samples[k]) < max_samples and s not in samples[k]:
                    samples[k].append(s[:240])
    return {"counts": counts, "samples": samples}
