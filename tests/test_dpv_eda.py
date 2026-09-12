"""V4 DPV with the real tool (marker `eda`, BS_EDA_TESTS=1). Bidirectional on the RTLLM 8-bit multiplier:
the direct-multiplication rewrite is proven, the dropped-partial-product bug is falsified (measured 2026-09-12,
~50 s each; the tool logs a FlexNet -5 for the BASE feature and then checks out VC-FORMAL-DPV-ELITE-SH).
Should every DPV feature ever be missing, the driver must report `unavailable` and never a proof."""
from pathlib import Path

import pytest

from src import config as C
from src.equiv import ports as PORTS
from src.equiv.dpv import run_dpv

pytestmark = pytest.mark.eda

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "tests" / "assets"
MULT = "/home/hping/RTLLM/Arithmetic/Multiplier/multi_8bit/verified_multi_8bit.v"
TOP = "multi_8bit"


@pytest.fixture(scope="module")
def cfg():
    return C.load()


def outputs(cfg, tmp_path):
    p = PORTS.port_info([MULT], TOP, cfg, sverilog=True, workdir=tmp_path / "ports")
    return [n for n, i in p.items() if i["dir"] == "output"]


def _check(rec, expected):
    assert rec["steps_done"] == ["compile_spec", "compile_impl", "compose", "solve"], rec  # frontend and compose work
    if rec["v4_status"] == "unavailable":
        assert rec["license_feature"].startswith("VC-FORMAL-DPV") and rec["lemmas"] == {}, rec
        assert rec["license_status"] == -5
        return "unavailable"
    assert rec["v4_status"] == expected, rec
    assert rec["lemmas"].get("eq_product") == expected
    return expected


def test_dpv_equivalent_rewrite(cfg, tmp_path):
    rec = run_dpv(tmp_path / "job", [MULT], [ASSETS / "multi_8bit_variant.v"], TOP, outputs(cfg, tmp_path), cfg, max_time_sec=300)
    outcome = _check(rec, "proven")
    print(f"\nDPV equivalent rewrite: {outcome} ({rec.get('error') or 'lemma proven'})")


def test_dpv_injected_bug(cfg, tmp_path):
    rec = run_dpv(tmp_path / "job", [MULT], [ASSETS / "multi_8bit_bug.v"], TOP, outputs(cfg, tmp_path), cfg, max_time_sec=300)
    outcome = _check(rec, "falsified")
    print(f"\nDPV injected bug: {outcome} ({rec.get('error') or 'lemma falsified'})")
    assert rec["v4_status"] != "proven"  # a bug must never come out as proven, whatever the license state
