"""V2 lock-step simulation (docs/spec/03-equivalence.md §1): one harness instantiates the original design D and
the candidate C (modules renamed with a suffix), drives both with the same reset sequence and the same
deterministic random stimulus, records every output of both designs each cycle to a trace file, and dumps a
VCD (both instances) for the power path. The Python side compares the traces: identical every cycle, or a
constant per-output offset k (C equals D delayed by k cycles), or a mismatch (first differing cycle recorded).

Simulator: VCS from the VC Formal tree (config tools.vcs.home). The harness is Verilog-2001 ($random with a
seed); designs are compiled in Verilog mode first and in SystemVerilog mode on a syntax error (the flow's
convention for LLM-written RTL).
"""
import os
import re
import subprocess
import time
from pathlib import Path

from src.equiv.rename import SUFFIX, rename_candidate

HARNESS = "bs_lockstep"


def _rand_expr(width):
    n = (width + 31) // 32
    parts = ", ".join("$random(seed)" for _ in range(n))
    return f"{{{parts}}}" if n > 1 else "$random(seed)"


def write_harness(path, top_d, top_c, ports, clk, rst, rst_sense, cfg, trace_path, vcd_path, seed=None):
    """seed: random-stimulus seed; the config default (sim.seed) unless the caller varies it (SEQ pilot: offsets must
    be constant across random runs, DECISIONS 2026-09-12 guardrail 3)."""
    s = cfg["sim"]
    half = float(s["clock_period_ns"]) / 2.0
    ins = [n for n, p in ports.items() if p["dir"] == "input" and n not in (clk, rst)]
    outs = [n for n, p in ports.items() if p["dir"] in ("output", "inout")]
    L = ["`timescale 1ns/1ps", f"module {HARNESS};",
         f"  parameter integer CYCLES = {int(s['random_cycles'])};",
         f"  parameter integer RESET_CYCLES = {int(s['reset_cycles'])};",
         f"  parameter integer SEED = {int(seed if seed is not None else s['seed'])};",
         "  reg clk = 1'b0;"]
    if rst:
        L.append("  reg rst;")
    for n in ins:
        w = ports[n]["width"]
        L.append(f"  reg [{w - 1}:0] {n};" if w > 1 else f"  reg {n};")
    for n in outs:
        w = ports[n]["width"]
        L.append(f"  wire [{w - 1}:0] d_{n}, c_{n};" if w > 1 else f"  wire d_{n}, c_{n};")

    def inst(top, prefix, name):
        conns = []
        if clk:
            conns.append(f".{clk}(clk)")
        if rst:
            conns.append(f".{rst}(rst)")
        conns += [f".{n}({n})" for n in ins]
        conns += [f".{n}({prefix}{n})" for n in outs]
        return f"  {top} {name} ({', '.join(conns)});"

    L.append(inst(top_d, "d_", "u_d"))
    L.append(inst(top_c, "c_", "u_c"))
    L += ["  integer seed = SEED;", "  integer cyc;", "  integer fd;",
          f"  always #{half:g} clk = ~clk;",
          "  task randomize_inputs; begin"]
    for n in ins:
        L.append(f"    {n} = {_rand_expr(ports[n]['width'])};")
    L += ["  end endtask",
          "  initial begin",
          f'    fd = $fopen("{trace_path}", "w");',
          f'    $dumpfile("{vcd_path}");', "    $dumpvars(0, u_d);", "    $dumpvars(0, u_c);"]
    for n in ins:
        L.append(f"    {n} = 0;")
    if rst:
        active = "1'b0" if rst_sense == "low" else "1'b1"
        inactive = "1'b1" if rst_sense == "low" else "1'b0"
        L += [f"    rst = {active};", "    repeat (RESET_CYCLES) @(negedge clk);", f"    rst = {inactive};"]
    else:
        L.append("    repeat (RESET_CYCLES) @(negedge clk);")
    fmt = " ".join("%h %h" for _ in outs)
    args = ", ".join(f"d_{n}, c_{n}" for n in outs)
    L += ["    for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin",
          "      @(negedge clk);",
          f'      $fwrite(fd, "%0d {fmt}\\n", cyc{", " + args if args else ""});',
          "      randomize_inputs;",
          "    end",
          "    @(negedge clk);",
          "    $fclose(fd);",
          '    $display("BS_SIM_DONE cycles=%0d", CYCLES);',
          "    $finish;",
          "  end", "endmodule", ""]
    Path(path).write_text("\n".join(L))
    return ins, outs


def compare_traces(trace_text, outs, max_offset):
    """-> dict(status, offsets, cycles, first_mismatch, mismatches) with status identical|offset|mismatch."""
    rows = []
    for line in trace_text.splitlines():
        parts = line.split()
        if len(parts) != 1 + 2 * len(outs):
            continue
        rows.append(parts[1:])
    n = len(rows)
    if n == 0:
        return {"status": "no_trace", "offsets": {}, "cycles": 0, "first_mismatch": None, "mismatches": {}}
    offsets, first_mismatch, mismatches = {}, None, {}
    for i, o in enumerate(outs):
        d = [r[2 * i] for r in rows]
        c = [r[2 * i + 1] for r in rows]
        found = None
        for k in range(0, int(max_offset) + 1):
            if all(c[t] == d[t - k] for t in range(k, n)):
                found = k
                break
        if found is None:
            bad = next(t for t in range(n) if c[t] != d[t])
            mismatches[o] = {"first_cycle": bad, "d": d[bad], "c": c[bad]}
            first_mismatch = bad if first_mismatch is None else min(first_mismatch, bad)
        else:
            offsets[o] = found
    if mismatches:
        status = "mismatch"
    elif any(k > 0 for k in offsets.values()):
        status = "offset"
    else:
        status = "identical"
    return {"status": status, "offsets": offsets, "cycles": n, "first_mismatch": first_mismatch, "mismatches": mismatches}


SHIM_BIN = str(Path(__file__).resolve().parent.parent.parent / "scripts" / "bin")   # dc stand-in for the VCS wrapper


def vcs_env(cfg):
    home = cfg["tools"]["vcs"]["home"]
    e = dict(os.environ)
    e.update({"VCS_HOME": home, "SYNOPSYS": str(Path(home).parent), "PATH": f"{home}/bin:{SHIM_BIN}:" + e.get("PATH", ""),
              "SNPSLMD_LICENSE_FILE": "1720@viterbi-lic01.vlab.usc.edu", "TERM": "dumb"})
    return e


def bash_as_sh(argv, cfg):
    """VCS's generated csrc/rmapats.sh is `#!/bin/sh` with bashisms; on this Ubuntu /bin/sh is dash, so the
    compile dies after the C stage (eda-knowledge/05-traps.md #20, VCS form). Like flow/vcf.py, run the command
    in a private mount namespace with bash bound over /bin/sh: nothing outside the process tree changes and no
    root is needed. Disable with config sim.vcs_bash_namespace: false."""
    if not cfg["sim"].get("vcs_bash_namespace", True):
        return list(argv)
    return ["unshare", "-rm", "sh", "-c", 'mount --bind /bin/bash /bin/sh && exec "$@"', "--"] + list(argv)


def _is_syntax_error(log):
    return bool(re.search(r"Error-\[SE\]|Syntax error|requires SystemVerilog", log))


def vcs_compile(workdir, sources, cfg, sverilog=False, incdirs=None, timeout=1800, top=None, extra=()):
    """Compile with VCS; retries in SystemVerilog mode on a syntax error. -> (ok, log, sverilog_used)."""
    wd = Path(workdir)
    wd.mkdir(parents=True, exist_ok=True)
    home = cfg["tools"]["vcs"]["home"]
    incs = [f"+incdir+{Path(d).resolve()}" for d in (incdirs or [])]
    modes = [sverilog, True] if not sverilog else [True]
    log_all = ""
    for sv in modes:
        argv = [f"{home}/bin/vcs", "-full64", "-timescale=1ns/1ps", "-o", "simv", "-l", "vcs.log"] + (["-sverilog"] if sv else [])
        argv += incs + list(extra) + ([f"-top", top] if top else []) + [str(Path(f).resolve()) for f in sources]
        p = subprocess.run(bash_as_sh(argv, cfg), cwd=str(wd), env=vcs_env(cfg), capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
        log = p.stdout + p.stderr
        log_all += f"\n### vcs {'-sverilog' if sv else '(verilog)'} exit {p.returncode}\n" + log
        if p.returncode == 0 and (wd / "simv").exists():
            return True, log_all, sv
        if not _is_syntax_error(log):
            break
    return False, log_all, sverilog


def vcs_run(workdir, cfg, timeout=1800, plusargs=()):
    wd = Path(workdir)
    p = subprocess.run(["./simv", "-l", "sim.log"] + list(plusargs), cwd=str(wd), env=vcs_env(cfg), capture_output=True,
                       text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def run_lockstep(job_dir, d_files, c_files, top, ports, clk, rst, rst_sense, cfg, *, sverilog=False, incdirs=None, timeout_sec=None, sim_seed=None, c_top=None):
    """-> dict(status, offsets, cycles, first_mismatch, vcd, trace, sverilog, compile_log_path)."""
    job_dir = Path(job_dir)
    wd = job_dir / "v2_sim"
    wd.mkdir(parents=True, exist_ok=True)
    renamed, names = rename_candidate([str(f) for f in c_files])
    c_sources = []
    for f, text in renamed:
        dst = wd / (Path(f).stem + SUFFIX + Path(f).suffix)
        dst.write_text(text)
        c_sources.append(dst)
    trace, vcd = wd / "trace.txt", wd / "sim.vcd"
    harness = wd / "harness.v"
    ins, outs = write_harness(harness, top, (c_top or top) + SUFFIX, ports, clk, rst, rst_sense, cfg, trace, vcd, seed=sim_seed)
    timeout = float(timeout_sec or cfg["timeouts"]["sim"] * 60)
    t0 = time.time()
    ok, clog, sv = vcs_compile(wd, [harness] + [str(f) for f in d_files] + [str(p) for p in c_sources], cfg,
                               sverilog=sverilog, incdirs=incdirs, timeout=timeout, top=HARNESS)
    (wd / "vcs_console.log").write_text(clog)
    rec = {"status": "unknown", "offsets": {}, "cycles": 0, "first_mismatch": None, "mismatches": {}, "vcd": None,
           "trace": str(trace), "sverilog": sv, "inputs": ins, "outputs": outs, "workdir": str(wd), "seconds": None}
    if not ok:
        errs = [l.strip() for l in clog.splitlines() if l.startswith("Error")]
        rec.update(status="compile_failed", error=(errs[0] if errs else "vcs compile failed")[:300], seconds=round(time.time() - t0, 1))
        return rec
    try:
        rc, slog = vcs_run(wd, cfg, timeout=timeout)
    except subprocess.TimeoutExpired:
        rec.update(status="timeout", error=f"simulation exceeded {timeout:.0f} s", seconds=round(time.time() - t0, 1))
        return rec
    rec["seconds"] = round(time.time() - t0, 1)
    if rc != 0 or "BS_SIM_DONE" not in slog or not trace.exists():
        errs = [l.strip() for l in slog.splitlines() if l.startswith("Error")]
        rec.update(status="run_failed", error=(errs[0] if errs else f"simv exit {rc}")[:300])
        return rec
    cmp = compare_traces(trace.read_text(), outs, cfg["sim"]["max_latency_offset"])
    rec.update(cmp)
    rec["vcd"] = str(vcd) if vcd.exists() and vcd.stat().st_size > 0 else None
    return rec


def run_testbench(workdir, tb_files, rtl_files, cfg, *, tb_top=None, sverilog=False, incdirs=None, timeout_sec=None):
    """Self-checking testbench: pass when the pass regex appears and no fail regex does (config: sim)."""
    wd = Path(workdir)
    wd.mkdir(parents=True, exist_ok=True)
    timeout = float(timeout_sec or cfg["timeouts"]["sim"] * 60)
    ok, clog, sv = vcs_compile(wd, list(tb_files) + list(rtl_files), cfg, sverilog=sverilog, incdirs=incdirs, timeout=timeout, top=tb_top)
    (wd / "vcs_console.log").write_text(clog)
    if not ok:
        return {"status": "compile_failed", "sverilog": sv, "log": clog[-1500:]}
    try:
        rc, slog = vcs_run(wd, cfg, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "sverilog": sv}
    passed = re.search(cfg["sim"]["tb_pass_regex"], slog) is not None
    failed = re.search(cfg["sim"]["tb_fail_regex"], slog) is not None
    return {"status": "pass" if passed and not failed else "fail", "sverilog": sv, "exit": rc, "log_tail": slog[-1500:]}
