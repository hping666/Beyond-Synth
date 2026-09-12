"""Power path (docs/PLAN.md 0.7, spec 01 §4), marker `eda`: lock-step VCS simulation -> VCD -> vcd2saif -> DC
E4 with read_saif and PrimePower with the same SAIF on the E4 netlist; the two SAIF-driven numbers must be of the
same order of magnitude, and the default-toggle number must be recorded next to them."""
from pathlib import Path

import pytest

from src import config as C
from src.equiv.saif import vcd_to_saif
from src.equiv.stack import check_equivalence
from src.eval.dc import run_dc
from src.eval.pt import run_pt

pytestmark = pytest.mark.eda

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "tests" / "assets"
ACCU = "/home/hping/RTLLM/Arithmetic/Accumulator/accu/verified_accu.v"
TOP = "verified_accu"
INSTANCE = "bs_lockstep/u_d"


@pytest.fixture(scope="module")
def cfg():
    c = C.load()
    c["sim"]["random_cycles"] = 2000
    return c


def test_saif_power_dc_and_primepower_agree(cfg, tmp_path):
    job = tmp_path / "job"
    eq = check_equivalence(job, [ACCU], [ASSETS / "accu_perturb_rename.v"], TOP, cfg, run_v3=False)
    assert eq["v2_status"] == "identical" and eq["vcd_path"]
    saif = vcd_to_saif(eq["vcd_path"], job / "d.saif", INSTANCE, cfg)
    assert saif["status"] == "ok"

    dc = run_dc(job / "dc_e4", [ACCU], TOP, "nangate45", cfg["configs"]["E4"]["compile"], 2.0, "clk", cfg,
                saif=saif["saif"], saif_instance=INSTANCE)
    assert dc["status"] == "ok", dc.get("error")
    assert dc["saif_status"] == "ok", dc.get("saif_status")
    m = dc["metrics"]
    assert m["power_saif_mw"] and m["power_saif_mw"] > 0 and m["power_default_mw"] > 0
    assert (Path(dc["reports_dir"]) / "saif.rpt").exists()

    reports = Path(dc["reports_dir"])
    pt = run_pt(job / "pt", reports / "netlist.v", reports / "design.sdc", TOP, "nangate45", cfg,
                saif=saif["saif"], saif_instance=INSTANCE)
    assert pt["status"] == "ok", pt.get("error")
    assert pt["primepower"]["activity"] == "saif"
    assert pt["metrics"]["power_saif_mw"] and pt["metrics"]["power_saif_mw"] > 0
    ratio = pt["metrics"]["power_saif_mw"] / m["power_saif_mw"]
    assert 0.1 < ratio < 10, f"DC {m['power_saif_mw']} mW vs PrimePower {pt['metrics']['power_saif_mw']} mW"
    print(f"\nDC read_saif: {m['power_saif_mw']:.4f} mW | DC default toggles: {m['power_default_mw']:.4f} mW | "
          f"PrimePower SAIF: {pt['metrics']['power_saif_mw']:.4f} mW")
