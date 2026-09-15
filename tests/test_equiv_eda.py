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


def test_latency_mapping_proves_a_registered_output_and_falsifies_a_wrong_offset(cfg, tmp_path):
    """DECISIONS 2026-09-14 G2.1 (b), implemented 2026-09-15: the SEQ pilot's class-(c2) candidate of counter_12 registers the
    output once more (out lags by one cycle; proven_sim_only in the pilot). With the latency mapping V2's offset {out: 1}
    becomes a SEQ output latency and SEQ proves it; the same candidate asserted at the wrong offset (2) is falsified, and
    the plain by-name mapping (offset ignored) is falsified as well — the proof comes from the mapping, not from slack."""
    import copy
    from src.equiv.seq import run_seq
    c2cfg = copy.deepcopy(cfg)
    c2cfg["equiv"]["seq_latency_mapping"] = True
    d = ROOT / "data" / "designs" / "rtllm" / "counter_12" / "rtl" / "counter_12.v"
    c = ROOT / "data" / "pilot" / "llm_pilot_luna1__rtllm_counter_12" / "c2_0_c2378489f63201a.v"
    rec = check_equivalence(tmp_path / "job", [d], [c], "counter_12", c2cfg)
    assert rec["v1_status"] == "ok" and rec["v2_status"] == "offset" and rec["latency_offset_json"] == '{"out": 1}', rec.get("v2")
    assert rec["latency_mapped"] is True and rec["v3"]["latency"] == {"out": 1}
    assert rec["v3_status"] == "proven" and rec["verdict"] == "proven" and rec["proven_by"] == "seq", rec.get("v3")
    assert "seq_assert spec.out impl.out -clock spec.clk -latency1 0 -latency2 1" in (tmp_path / "job" / "v3_seq" / "seq.tcl").read_text()
    wrong = run_seq(tmp_path / "wrong", [d], [c], "counter_12", "clk", "rst_n", "low", c2cfg, latency={"out": 2})
    assert wrong["v3_status"] == "falsified" and wrong["latency"] == {"out": 2}, wrong
    plain = run_seq(tmp_path / "plain", [d], [c], "counter_12", "clk", "rst_n", "low", c2cfg)
    assert plain["v3_status"] == "falsified" and plain["latency_mapped"] is False, plain
