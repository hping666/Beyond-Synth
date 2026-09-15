"""Project-owned VC Formal SEQ run (DECISIONS 2026-09-14, G2.2): the same command sequence as flow/vcf.py::seq_equiv
(which must not be modified) plus the initial-state assumption `sim_set_state -uninitialized -apply 0` before the reset
state is saved, so that every register without a reset starts at zero in both designs. The flow module's own helpers
(_vcf_cmd, _env, _check_workdir, _kill_tree) and result regexes are reused unchanged so that verdict parsing stays identical."""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

FLOW_DIR = "/hdd1/hping/eda/flow"


def _vcf():
    if FLOW_DIR not in sys.path:
        sys.path.insert(0, FLOW_DIR)
    import vcf  # noqa: E402  (the flow module; never modified)
    return vcf


def latency_lines(latency, clk):
    """SEQ output assertions for a candidate whose outputs equal the original's delayed by a constant number of cycles
    (V2 offsets, class c2; DECISIONS 2026-09-14 G2.1 (b), implemented 2026-09-15). VC Formal SEQ's `seq_assert` takes the
    latency of each signal: `-latency1 a -latency2 b` compares the later signal with `$past` of the earlier one by |a-b|
    cycles after ##max(a,b) (user guide, "Creating Assert Mappings": `-latency1 {10 0 9} -latency2 {4 5 9}` yields
    `##10 (spec === $past(impl, 6))` ...). The candidate (impl) lags the original (spec) by k, impl(t) == spec(t-k):
    spec latency 0, impl latency k. Outputs with k = 0 keep the immediate assertion of map_by_name's output mapping."""
    out = []
    for name, k in sorted(latency.items()):
        k = int(k or 0)
        if k > 0:
            out.append(f"seq_assert spec.{name} impl.{name} -clock spec.{clk} -latency1 0 -latency2 {k}")
        else:
            out.append(f"seq_assert spec.{name} impl.{name}")
    return out


def seq_tcl(spec_files, impl_files, spec_top, impl_top, clk, rst, rst_sense, max_time, workers, fmt, zero_init, incdirs=(), latency=None):
    """The Tcl script text (identical to the flow's except for the optional zero-initialisation line, the include
    directories of designs with `include` files, passed to analyze as VCS options, and — with `latency` — the
    per-output latency mapping: inputs mapped by name only, every output asserted explicitly with its V2 offset)."""
    inc = (" -vcs {" + " ".join(f"+incdir+{d}" for d in incdirs) + "}") if incdirs else ""
    lines = ["set_fml_appmode SEQ", f"set_fml_var fml_max_time {max_time}", f"set_grid_usage -type rsh={workers}",
             f"analyze -format {fmt}{inc} -library spec {{{' '.join(spec_files)}}}",
             f"analyze -format {fmt}{inc} -library impl {{{' '.join(impl_files)}}}",
             f"elaborate_seq -spectop {spec_top} -impltop {impl_top}",
             "map_by_name -input" if latency else "map_by_name",   # latency mapping: the outputs are asserted below, not mapped by name
             f"create_clock spec.{clk} -period 100"]
    if rst:
        lines.append(f"create_reset spec.{rst} -sense {rst_sense}")
    if latency:
        lines += latency_lines(latency, clk)
    lines.append("sim_run -stable")
    if zero_init:
        lines.append("sim_set_state -uninitialized -apply 0")   # DECISIONS 2026-09-14 G2.2: registers without reset start at 0
    lines += ["sim_save_reset", "seq_config -map_uninit -map_x zero", "check_fv -block", "report_fv -verbose", "report_seq_mappings", "exit"]
    return "\n".join(lines) + "\n"


def seq_equiv(spec_files, impl_files, spec_top, impl_top=None, clk="clk", rst=None, rst_sense="high", workdir=None,
              max_time="20M", timeout=3600, sverilog=False, workers=1, zero_init=True, incdirs=None, latency=None):
    """Same contract as flow/vcf.py::seq_equiv (-> dict with status equivalent / not_equivalent / inconclusive / timeout /
    error, counts, regs_mapped / regs_unmapped, properties, workdir, runtime_s), with the zero-init line when zero_init
    and the per-output latency mapping when `latency` ({output: cycles}) is given."""
    vcf = _vcf()
    impl_top = impl_top or spec_top
    spec_files = [str(Path(f).resolve()) for f in spec_files]
    impl_files = [str(Path(f).resolve()) for f in impl_files]
    for f in spec_files + impl_files:
        if not os.path.exists(f):
            raise FileNotFoundError(f)
    wd = Path(workdir or (Path(vcf.EDA_ROOT) / f"work/vcf_{spec_top}_{int(time.time())}"))
    wd.mkdir(parents=True, exist_ok=True)
    fmt = "sverilog" if sverilog else "verilog"
    tcl = wd / "seq.tcl"
    tcl.write_text(seq_tcl(spec_files, impl_files, spec_top, impl_top, clk, rst, rst_sense, max_time, workers, fmt, zero_init,
                           [str(Path(d).resolve()) for d in (incdirs or [])], latency=latency))
    vcf._check_workdir(wd)
    t0 = time.time()
    try:
        p = subprocess.run(vcf._vcf_cmd("SEQ", tcl), cwd=str(wd), env=vcf._env(), timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log, rc, to = p.stdout, p.returncode, False
    except subprocess.TimeoutExpired as e:
        log = e.stdout if isinstance(e.stdout, str) else ""
        rc, to = -1, True
        vcf._kill_tree(wd)
    (wd / "vcf_console.log").write_text(log or "")
    full = log + ((wd / "vcf.log").read_text(errors="replace") if (wd / "vcf.log").exists() else "")
    res = {"tool": "VC Formal SEQ", "spec_top": spec_top, "impl_top": impl_top, "status": "unknown", "error": None,
           "workdir": str(wd), "runtime_s": round(time.time() - t0, 2), "returncode": rc, "total": None, "proven": None,
           "failed": None, "inconclusive": None, "regs_mapped": None, "regs_unmapped": None, "zero_init": bool(zero_init),
           "latency": dict(latency) if latency else None}
    res.update(parse_seq_log(full, vcf, timed_out=to, timeout=timeout, max_time=max_time, rc=rc))
    return res


# With user-defined output assertions (`seq_assert`, latency mapping) VC Formal prints the assertion counts under
# "Property Summary: SEQ" instead of "Sequential Equivalence Summary: SEQ" (observed 2026-09-15 on counter_12); the flow's
# regexes only know the latter, so the project parser adds this block as a fallback.
_PROP_BLOCK = re.compile(r"Property Summary: SEQ\s*\n\s*-+\s*\n\s*> Assertion\s*\n((?:\s*- # \w+\s*:\s*\d+\s*\n)+)")


def parse_seq_log(full, vcf, *, timed_out=False, timeout=None, max_time=None, rc=None):
    """Status and counts from the console + vcf.log text: the flow's own regexes first (`Verification Result` line, the
    `Sequential Equivalence Summary` block), then the `Property Summary` block of runs with explicit output assertions.
    -> dict(status, total, proven, failed, inconclusive, regs_mapped, regs_unmapped, properties?, error, vcf_errors?)."""
    out = {"status": "unknown", "error": None}
    m = vcf._MAPPED.search(full)
    if m:
        out["regs_mapped"] = int(m.group(1))
    m = vcf._UNMAPPED.search(full)
    if m:
        out["regs_unmapped"] = int(m.group(1))
    props = {m.group(1): m.group(2) for m in vcf._SEQ_PROP.finditer(full)}
    if props:
        out["properties"] = props
    m = vcf._SUMMARY.search(full)
    counts = None
    if m:
        counts = tuple(int(x) for x in m.groups())
    else:
        mb = vcf._SEQ_BLOCK.search(full) or _PROP_BLOCK.search(full)
        if mb:
            f = {k: int(v) for k, v in vcf._SEQ_FIELD.findall(mb.group(1))}
            counts = (f.get("found", 0), f.get("proven", 0), f.get("falsified", 0), f.get("inconclusive", 0))
    if counts:
        tot, ok, bad, inc = counts
        out.update(total=tot, proven=ok, failed=bad, inconclusive=inc)
        out["status"] = "not_equivalent" if bad > 0 else "inconclusive" if inc > 0 else "equivalent" if (tot > 0 and ok == tot) else "no_properties"
    elif timed_out:
        out["status"], out["error"] = "timeout", f"exceeded {timeout}s (tool limit {max_time})"
    else:
        errs = [l.strip() for l in full.splitlines() if l.lstrip().startswith("[Error]")]
        out["status"], out["error"] = "error", (errs[0] if errs else f"vcf returned {rc}, no parsable result")
        if errs:
            out["vcf_errors"] = errs[:8]
    return out
