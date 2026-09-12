"""VCD -> SAIF for the power path (docs/spec/01-eval-service.md §4) with Synopsys vcd2saif (ships with DC)."""
import subprocess
from pathlib import Path


def vcd_to_saif(vcd, saif, instance, cfg, timeout=600):
    """instance: hierarchical path of the DUT inside the VCD, e.g. bs_lockstep/u_d; the SAIF keeps that hierarchy
    and DC / PrimePower read it with read_saif -instance <same path>."""
    tool = cfg["tools"]["vcs"]["vcd2saif"]
    p = subprocess.run([tool, "-input", str(vcd), "-output", str(saif), "-instance", instance],
                       capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    ok = p.returncode == 0 and Path(saif).exists() and Path(saif).stat().st_size > 0
    return {"status": "ok" if ok else "failed", "instance": instance, "saif": str(saif) if ok else None,
            "log": (p.stdout + p.stderr)[-800:]}
