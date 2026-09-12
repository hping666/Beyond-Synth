"""V3: VC Formal SEQ through the read-only flow/vcf.py (docs/spec/03-equivalence.md §1, eda-knowledge #20/#22/#23).

Statuses returned by the flow are mapped to the project vocabulary: equivalent -> proven, not_equivalent ->
falsified, inconclusive / timeout -> inconclusive (never treated as proven, CLAUDE.md rule 8), everything else
-> error. The VC Formal work directory is kept as the counterexample path for falsified candidates.
"""
import sys
import time
from pathlib import Path

STATUS_MAP = {"equivalent": "proven", "not_equivalent": "falsified", "inconclusive": "inconclusive",
              "timeout": "inconclusive", "no_properties": "error", "error": "error"}


def _vcf(cfg):
    fd = cfg["project"]["flow_dir"]
    if fd not in sys.path:
        sys.path.insert(0, fd)
    import vcf  # noqa: E402  (flow/vcf.py)
    return vcf


def run_seq(job_dir, d_files, c_files, top, clk, rst, rst_sense, cfg, *, impl_top=None, sverilog=False, timeout_sec=None, max_time=None):
    vcf = _vcf(cfg)
    wd = Path(job_dir) / "v3_seq"
    seq_min = int(cfg["timeouts"]["seq_min"])
    t0 = time.time()
    r = vcf.seq_equiv([str(f) for f in d_files], [str(f) for f in c_files], top, impl_top=impl_top or top, clk=clk, rst=rst,
                      rst_sense=rst_sense or "high", workdir=str(wd), max_time=max_time or f"{seq_min}M",
                      timeout=float(timeout_sec or seq_min * 60 + 300), sverilog=sverilog,
                      workers=int(cfg["tools"]["vcformal"].get("seq_workers", 1)))
    status = STATUS_MAP.get(r.get("status"), "error")
    out = {"v3_status": status, "v3_seconds": r.get("runtime_s", round(time.time() - t0, 1)), "flow_status": r.get("status"),
           "error": r.get("error"), "proven": r.get("proven"), "falsified": r.get("failed"), "inconclusive": r.get("inconclusive"),
           "total": r.get("total"), "regs_mapped": r.get("regs_mapped"), "regs_unmapped": r.get("regs_unmapped"),
           "properties": r.get("properties"), "workdir": str(wd)}
    if status == "falsified":
        out["counterexample_path"] = str(wd)
    return out
