"""Equivalence-stack tests with the real tools (marker `eda`; VCS + VC Formal SEQ; BS_EDA_TESTS=1).
Bidirectional per spec 03 §3: the renaming perturbation of accu is identical in simulation and proven by SEQ;
the injected-bug mutant mismatches in simulation and is falsified by SEQ; the width change never reaches the
simulator. The VCD of the lock-step run converts to a SAIF (power path, PLAN 0.7)."""
from pathlib import Path

import pytest

from src import config as C
from src.equiv.saif import vcd_to_saif
from src.equiv.stack import check_equivalence

pytestmark = pytest.mark.eda

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "tests" / "assets"
ACCU = "/home/hping/RTLLM/Arithmetic/Accumulator/accu/verified_accu.v"
TOP = "verified_accu"


@pytest.fixture(scope="module")
def cfg():
    c = C.load()
    c["sim"]["random_cycles"] = 2000  # enough for a 4-input accumulator; keeps the test fast
    return c


def test_rename_perturbation_identical_and_proven(cfg, tmp_path):
    rec = check_equivalence(tmp_path / "job", [ACCU], [ASSETS / "accu_perturb_rename.v"], TOP, cfg)
    assert rec["v1_status"] == "ok" and rec["clk"] == "clk" and rec["rst"] == "rst_n" and rec["rst_sense"] == "low"
    assert rec["v2_status"] == "identical" and rec["v2_cycles"] == 2000, rec.get("v2")
    assert rec["latency_offset_json"] == '{"data_out": 0, "valid_out": 0}'
    assert rec["v3_status"] == "proven" and rec["verdict"] == "proven", rec.get("v3")
    assert rec["v3"]["proven"] and rec["v3"]["falsified"] == 0
    # DECISIONS 2026-09-14: the VCD became scratch once both SAIFs exist (vcd_to_scratch); a proven record keeps no VCD
    assert rec["saif_d"] and Path(rec["saif_d"]).stat().st_size > 0 and rec["saif_c"] and Path(rec["saif_c"]).stat().st_size > 0
    assert rec["vcd_deleted"] is True and rec["vcd_path"] is None
    assert rec["v3"]["zero_init"] is True
    assert "(INSTANCE u_d" in Path(rec["saif_d"]).read_text() and "(INSTANCE u_c" in Path(rec["saif_c"]).read_text()


def test_mutant_mismatches_and_is_falsified(cfg, tmp_path):
    rec = check_equivalence(tmp_path / "job", [ACCU], [ASSETS / "accu_mutant.v"], TOP, cfg)
    assert rec["v1_status"] == "ok"
    assert rec["v2_status"] == "sim_fail" and rec["verdict"] == "sim_fail", rec.get("v2")
    assert rec["v2"]["first_mismatch"] is not None and "valid_out" in rec["v2"]["mismatches"]
    # SEQ alone must also catch it (the search never relies on simulation for the verdict)
    from src.equiv.seq import run_seq
    v3 = run_seq(tmp_path / "job", [ACCU], [ASSETS / "accu_mutant.v"], TOP, "clk", "rst_n", "low", cfg)
    assert v3["v3_status"] == "falsified" and v3["falsified"] >= 1 and v3["counterexample_path"]


def test_width_change_rejected_before_simulation(cfg, tmp_path):
    rec = check_equivalence(tmp_path / "job", [ACCU], [ASSETS / "accu_width.v"], TOP, cfg)
    assert rec["v1_status"] == "rejected" and rec["verdict"] == "rejected" and "width 10 -> 12" in rec["v1_detail"]
    assert rec["v2_status"] is None and not (tmp_path / "job" / "v2_sim").exists()
