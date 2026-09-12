"""Yosys-based interface probe for the Phase 1 inventory (src/designs/inventory.py).

`read_verilog; hierarchy -top; proc; flatten; write_json` gives, without any optimisation, the ports of the top
(as src/equiv/ports.py), the input ports that drive flip-flop clock pins (`$dff`-family CLK, memory RD_CLK / WR_CLK)
after flattening the hierarchy, the input ports used as asynchronous resets with their polarity (`$adff` ARST), and
cell / flip-flop counts. Clock ports are therefore identified by their use, not by their name (CktEvo uses
WB_CLK_I / MTxClk / MRxClk, RTLLM rclk / wclk / clk_a / clk_b): a design with two or more clock ports is tagged
multi_clock, one without any is combinational (tag no_clock)."""
import json
import subprocess
import tempfile
from pathlib import Path

from src.equiv.ports import PortError

DFF_TYPES = {"$dff", "$dffe", "$adff", "$adffe", "$sdff", "$sdffe", "$sdffce", "$dffsr", "$dffsre", "$aldff", "$aldffe"}
MEM_TYPES = {"$mem", "$mem_v2"}


def _param(cell, name, default=None):
    v = (cell.get("parameters") or {}).get(name, default)
    if isinstance(v, str):
        return int(v, 2) if v and set(v) <= {"0", "1"} else v
    return v


def probe(rtl_files, top, cfg, sverilog=False, incdirs=None, workdir=None, timeout=900):
    wd = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="bs_probe_"))
    wd.mkdir(parents=True, exist_ok=True)
    out = wd / "design.json"
    incs = " ".join(f"-I {Path(d).resolve()}" for d in (incdirs or []))
    files = " ".join(str(Path(f).resolve()) for f in rtl_files)
    script = f"read_verilog {'-sv ' if sverilog else ''}{incs} {files}; hierarchy -top {top}; proc; flatten; write_json {out}"
    p = subprocess.run([cfg["tools"]["yosys"]["bin"], "-q", "-p", script], capture_output=True, text=True, timeout=timeout)
    (wd / "yosys.log").write_text(p.stdout + p.stderr)
    if p.returncode != 0 or not out.exists():
        err = [line for line in (p.stdout + p.stderr).splitlines() if line.startswith("ERROR")]
        raise PortError(err[0] if err else f"yosys exit {p.returncode}: {(p.stdout + p.stderr)[-500:]}")
    data = json.loads(out.read_text())
    mod = data["modules"].get(top) or next(iter(data["modules"].values()))
    ports = {n: {"dir": pp["direction"], "width": len(pp["bits"])} for n, pp in mod["ports"].items()}
    clk_bits, arst, n_ff = set(), {}, 0
    for cell in mod["cells"].values():
        t, conns = cell["type"], cell.get("connections", {})
        if t in DFF_TYPES:
            n_ff += len(conns.get("Q", []))
            clk_bits.update(b for b in conns.get("CLK", []) if isinstance(b, int))
            if t in ("$adff", "$adffe", "$aldff", "$aldffe"):
                pol = _param(cell, "ARST_POLARITY", 1)
                for b in conns.get("ARST", []):
                    if isinstance(b, int):
                        arst[b] = int(pol)
        elif t in MEM_TYPES:
            for k in ("RD_CLK", "WR_CLK"):
                clk_bits.update(b for b in conns.get(k, []) if isinstance(b, int))

    def bits(name):
        return [b for b in mod["ports"][name]["bits"] if isinstance(b, int)]

    clock_ports = [n for n, pp in mod["ports"].items() if pp["direction"] == "input" and any(b in clk_bits for b in bits(n))]
    async_resets = {}
    for n, pp in mod["ports"].items():
        if pp["direction"] != "input":
            continue
        pols = {arst[b] for b in bits(n) if b in arst}
        if pols:
            async_resets[n] = "high" if pols == {1} else "low" if pols == {0} else "mixed"
    return {"ports": ports, "clock_ports": clock_ports, "async_resets": async_resets,
            "n_cells": len(mod["cells"]), "n_ff_bits": n_ff}
