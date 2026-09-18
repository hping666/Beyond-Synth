"""V3: VC Formal SEQ through the read-only flow/vcf.py (docs/spec/03-equivalence.md §1, eda-knowledge #20/#22/#23).

Statuses returned by the flow are mapped to the project vocabulary: equivalent -> proven, not_equivalent ->
falsified, inconclusive / timeout -> inconclusive (never treated as proven, CLAUDE.md rule 8), everything else
-> error. The VC Formal work directory is kept as the counterexample path for falsified candidates.
"""
import re
import sys
import time
from pathlib import Path

from src.equiv.seq_tcl import seq_equiv as seq_equiv_project

STATUS_MAP = {"equivalent": "proven", "not_equivalent": "falsified", "inconclusive": "inconclusive",
              "timeout": "inconclusive", "no_properties": "error", "error": "error"}


def _vcf(cfg):
    fd = cfg["project"]["flow_dir"]
    if fd not in sys.path:
        sys.path.insert(0, fd)
    import vcf  # noqa: E402  (flow/vcf.py)
    return vcf


_XZ_LITERAL = re.compile(r"(\b\d*\s*'\s*[sS]?[bBoOhHdD])([0-9a-fA-F_xXzZ?]*[xXzZ?][0-9a-fA-F_xXzZ?]*)")


def rewrite_xz_literals(text):
    """DECISION 2026-09-18 (e) item 1 (harness_version 2): every x / z / ? digit of a Verilog literal becomes 0 — z on compared outputs,
    from registers or from combinational assignments, is treated as 0, identically on both sides; x the same. -> (new text, count)."""
    n = 0
    def sub(m):
        nonlocal n
        n += 1
        return m.group(1) + re.sub(r"[xXzZ?]", "0", m.group(2))
    return _XZ_LITERAL.sub(sub, text), n


def xz_free_copies(files, out_dir):
    """Copies of `files` under `out_dir` with their x / z literals rewritten (same base names); -> (paths, rewrites per file)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths, counts = [], {}
    for f in files:
        src = Path(f)
        txt, n = rewrite_xz_literals(src.read_text(errors="replace"))
        dst = out_dir / src.name
        if dst.exists() and dst.read_text(errors="replace") != txt:
            dst = out_dir / f"{src.stem}_{len(paths)}{src.suffix}"
        dst.write_text(txt)
        paths.append(str(dst))
        counts[src.name] = n
    return paths, counts


def run_seq(job_dir, d_files, c_files, top, clk, rst, rst_sense, cfg, *, impl_top=None, sverilog=False, timeout_sec=None, max_time=None, incdirs=None, latency=None):
    """`latency` ({output: cycles}, the constant per-output offsets found by V2) switches the run to the latency mapping of
    DECISIONS 2026-09-14 G2.1 (b): outputs asserted at their offsets instead of mapped by name (project script only)."""
    vcf = _vcf(cfg)
    wd = Path(job_dir) / "v3_seq"
    seq_min = int(cfg["timeouts"]["seq_min"])
    t0 = time.time()
    if max_time is None:
        # the solver's own limit stays well inside the process budget so that SEQ returns `inconclusive` by itself
        # instead of being killed by the process (or queue) timeout without a record (divider_32bit, 2026-09-13)
        minutes = max(1, int(float(timeout_sec) * 0.8 // 60)) if timeout_sec else seq_min
        max_time = f"{minutes}M"
    zero_init = bool((cfg.get("equiv") or {}).get("init_state_zero_no_reset", False))
    hv = int((cfg.get("equiv") or {}).get("harness_version", 1) or 1)   # DECISION 2026-09-18 (d) C1: 2 = every sequential zeroed before the reset run
    use_project = zero_init or bool(latency) or hv >= 2
    xz = None
    if hv >= 2:   # DECISION 2026-09-18 (e) item 1: the sources compiled for V3 have their x / z literals rewritten to 0, identically on both sides
        d_files, cd = xz_free_copies(d_files, wd / "spec_src")
        c_files, cc = xz_free_copies(c_files, wd / "impl_src")
        xz = {"spec": cd, "impl": cc}
    runner = seq_equiv_project if use_project else vcf.seq_equiv   # DECISIONS 2026-09-14 G2.2: the project-owned script adds the zero-init line
    kw = {"zero_init": zero_init, "incdirs": incdirs, "latency": latency, "harness_version": hv, "structural_x": bool((cfg.get("equiv") or {}).get("harness_v2_structural_x", False))} if use_project else {}   # the flow's own runner has no include / latency option
    r = runner([str(f) for f in d_files], [str(f) for f in c_files], top, impl_top=impl_top or top, clk=clk, rst=rst,
               rst_sense=rst_sense or "high", workdir=str(wd), max_time=max_time,
               timeout=float(timeout_sec or seq_min * 60 + 300), sverilog=sverilog,
               workers=int(cfg["tools"]["vcformal"].get("seq_workers", 1)), **kw)
    status = STATUS_MAP.get(r.get("status"), "error")
    out = {"v3_status": status, "v3_seconds": r.get("runtime_s", round(time.time() - t0, 1)), "flow_status": r.get("status"), "zero_init": zero_init, "harness_version": hv, "xz_rewrites": xz,
           "error": r.get("error"), "proven": r.get("proven"), "falsified": r.get("failed"), "inconclusive": r.get("inconclusive"),
           "total": r.get("total"), "regs_mapped": r.get("regs_mapped"), "regs_unmapped": r.get("regs_unmapped"),
           "properties": r.get("properties"), "workdir": str(wd), "latency_mapped": bool(latency), "latency": dict(latency) if latency else None}
    if status == "falsified":
        out["counterexample_path"] = str(wd)
        out["cex_depths"] = cex_depths((wd / "vcf.log").read_text(errors="replace")) if (wd / "vcf.log").exists() else {}
    return out


_CEX = re.compile(r"> ID: \[\d+\] falsified \(depth=(\d+)\)\s*\n\s*- name\s*:\s*(\S+)")


def cex_depths(log_text):
    """{property name: counterexample depth (cycles after reset)} from `report_fv -verbose` (the repair prompt of G5 item 1
    names the failing outputs and the shortest counterexample)."""
    return {m.group(2): int(m.group(1)) for m in _CEX.finditer(log_text)}
