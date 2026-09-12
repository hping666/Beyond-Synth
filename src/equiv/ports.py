"""Port extraction and comparison for V1 of the equivalence stack (docs/spec/03-equivalence.md §1).

Yosys reads the RTL (`read_verilog; hierarchy -top; proc; write_json`) and the JSON gives every port's name,
direction and width without evaluating anything else. Any difference in names, directions or widths between the
original design D and a candidate C rejects the candidate before simulation.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path


class PortError(RuntimeError):
    pass


def port_info(rtl_files, top, cfg, sverilog=False, incdirs=None, workdir=None, timeout=300):
    """-> {port: {"dir": "input"|"output"|"inout", "width": int}} of `top` (order preserved)."""
    wd = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="bs_ports_"))
    wd.mkdir(parents=True, exist_ok=True)
    out = wd / "ports.json"
    incs = " ".join(f"-I {Path(d).resolve()}" for d in (incdirs or []))
    files = " ".join(str(Path(f).resolve()) for f in rtl_files)
    script = f"read_verilog {'-sv ' if sverilog else ''}{incs} {files}; hierarchy -top {top}; proc; write_json {out}"
    p = subprocess.run([cfg["tools"]["yosys"]["bin"], "-q", "-p", script], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0 or not out.exists():
        err = [l for l in (p.stdout + p.stderr).splitlines() if l.startswith("ERROR")]
        raise PortError(err[0] if err else f"yosys exit {p.returncode}: {(p.stdout + p.stderr)[-500:]}")
    data = json.loads(out.read_text())
    mod = data["modules"].get(top)
    if mod is None:
        raise PortError(f"module {top} not found after hierarchy -top")
    return {name: {"dir": info["direction"], "width": len(info["bits"])} for name, info in mod["ports"].items()}


def compare_ports(d_ports, c_ports):
    """List of human-readable differences; empty when the interfaces are identical."""
    diffs = []
    for name, info in d_ports.items():
        if name not in c_ports:
            diffs.append(f"port {name} missing in candidate")
            continue
        for key in ("dir", "width"):
            if c_ports[name][key] != info[key]:
                diffs.append(f"port {name}: {key} {info[key]} -> {c_ports[name][key]}")
    for name in c_ports:
        if name not in d_ports:
            diffs.append(f"extra port {name} in candidate")
    return diffs


_CLOCK = re.compile(r"^(clk|clock|i_clk|clk_i|sclk|sys_clk|CLK|CLOCK)$")
_RESET = re.compile(r"^(rst_n|reset_n|rstn|resetn|nrst|nreset|arst_n|i_rst_n|rst_ni|RST_N|RESET_N)$")
_RESET_HIGH = re.compile(r"^(rst|reset|arst|i_rst|rst_i|RST|RESET|clear|clr)$")


def infer_control_ports(ports):
    """Guess (clock, reset, reset_sense) from port names; Phase 1 stores the verified values per design."""
    clk = rst = sense = None
    for name, info in ports.items():
        if info["dir"] != "input" or info["width"] != 1:
            continue
        if clk is None and _CLOCK.match(name):
            clk = name
        elif rst is None and _RESET.match(name):
            rst, sense = name, "low"
        elif rst is None and _RESET_HIGH.match(name):
            rst, sense = name, "high"
    return clk, rst, sense
