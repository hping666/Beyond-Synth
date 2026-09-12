"""Quick Yosys equivalence check (no license): `equiv_make` + `equiv_simple` + `equiv_induct` on two RTL versions
with the same top name. Used by the perturbation generator's self-tests and as a cheap pre-check; the protocol's
verdicts (spec 03) come from VC Formal SEQ, never from here (not_proven != non-equivalent)."""
import subprocess
import tempfile
from pathlib import Path


def yosys_equiv(gold_files, gate_files, top, cfg, workdir=None, seq=5, timeout=600, sverilog=False, incdirs=None):
    """-> 'equivalent' | 'not_proven' | 'error' (with the log in <workdir>/yosys_equiv.log)."""
    wd = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="bs_yeq_"))
    wd.mkdir(parents=True, exist_ok=True)
    sv = "-sv " if sverilog else ""
    incs = " ".join(f"-I {Path(d).resolve()}" for d in (incdirs or []))
    gold = " ".join(str(Path(f).resolve()) for f in gold_files)
    gate = " ".join(str(Path(f).resolve()) for f in gate_files)
    script = (f"read_verilog {sv}{incs} {gold}; prep -top {top}; flatten; async2sync; design -stash gold; "
              f"read_verilog {sv}{incs} {gate}; prep -top {top}; flatten; async2sync; design -stash gate; "
              f"design -copy-from gold -as gold {top}; design -copy-from gate -as gate {top}; "
              f"equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple -seq {seq}; equiv_induct -seq {seq}; equiv_status -assert")
    try:
        p = subprocess.run([cfg["tools"]["yosys"]["bin"], "-q", "-p", script], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        (wd / "yosys_equiv.log").write_text("timeout")
        return "not_proven"
    (wd / "yosys_equiv.log").write_text(p.stdout + p.stderr)
    if p.returncode == 0:
        return "equivalent"
    out = p.stdout + p.stderr
    if "Unproven" in out or "unproven" in out or "equiv_status" in out:
        return "not_proven"
    return "error"
