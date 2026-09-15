"""Yosys-based interface probe for the Phase 1 inventory (src/designs/inventory.py).

`read_verilog; hierarchy -top; proc; flatten; write_json` gives, without any optimisation, the ports of the top
(as src/equiv/ports.py), the input ports that drive flip-flop clock pins (`$dff`-family CLK, memory RD_CLK / WR_CLK)
after flattening the hierarchy, the input ports used as asynchronous resets with their polarity (`$adff` ARST), and
cell / flip-flop counts. Clock ports are therefore identified by their use, not by their name (CktEvo uses
WB_CLK_I / MTxClk / MRxClk, RTLLM rclk / wclk / clk_a / clk_b): a design with two or more clock ports is tagged
multi_clock, one without any is combinational (tag no_clock)."""
import json
import re
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


_STAT_ROW = re.compile(r"^\s+(\d+)\s+(\$\w+)\s*$", re.M)
_LTP = re.compile(r"Longest topological path in \S+ \(length=(\d+)\)")


def rtl_stats(rtl_files, top, cfg, sverilog=False, incdirs=None, workdir=None, timeout=900):
    """Word-level RTLIL statistics for the classifier M6 (spec 04 §A, rules version 2): `proc; flatten; opt` then
    `stat` (cell histogram by RTLIL type: $add, $mul, $mux, ...), `ltp -noff` (longest combinational path in cells, the
    dataflow-topology measure) and the flip-flop bits / cells after optimisation. Unlike `probe`, dead registers such
    as the loop variable of an unrolled `for` inside a clocked block are gone (LIFObuffer: 57 bits before opt, 25 after),
    so two rewrites of the same registers compare equal."""
    wd = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="bs_stats_"))
    wd.mkdir(parents=True, exist_ok=True)
    out = wd / "stats.json"
    incs = " ".join(f"-I {Path(d).resolve()}" for d in (incdirs or []))
    files = " ".join(str(Path(f).resolve()) for f in rtl_files)
    script = f"read_verilog {'-sv ' if sverilog else ''}{incs} {files}; hierarchy -top {top}; proc; flatten; opt; stat; ltp -noff; write_json {out}"
    p = subprocess.run([cfg["tools"]["yosys"]["bin"], "-p", script], capture_output=True, text=True, timeout=timeout)
    txt = p.stdout + p.stderr
    (wd / "yosys.log").write_text(txt)
    if p.returncode != 0 or not out.exists():
        err = [line for line in txt.splitlines() if line.startswith("ERROR")]
        raise PortError(err[0] if err else f"yosys exit {p.returncode}: {txt[-500:]}")
    stat_txt = txt[txt.rfind("Printing statistics"):]
    cells = {}
    for n, t in _STAT_ROW.findall(stat_txt):
        cells[t] = cells.get(t, 0) + int(n)
    m = _LTP.search(txt)
    data = json.loads(out.read_text())
    mod = data["modules"].get(top) or next(iter(data["modules"].values()))
    ff_bits = ff_cells = 0
    for cell in mod["cells"].values():
        if cell["type"] in DFF_TYPES:
            ff_cells += 1
            ff_bits += len(cell.get("connections", {}).get("Q", []))
        elif cell["type"] in MEM_TYPES:   # a memory that Yosys kept as $mem counts like the register list it would otherwise become
            size, width = int(_param(cell, "SIZE", 0) or 0), int(_param(cell, "WIDTH", 0) or 0)
            ff_cells += size
            ff_bits += size * width
    for mem in (mod.get("memories") or {}).values():   # memories not yet collected into a $mem cell (write_json lists them apart)
        size, width = int(mem.get("size", 0) or 0), int(mem.get("width", 0) or 0)
        ff_cells += size
        ff_bits += size * width
    return {"cells": cells, "n_cells": sum(cells.values()), "n_ff_bits": ff_bits, "n_ff_cells": ff_cells,
            "depth": int(m.group(1)) if m else 0}
