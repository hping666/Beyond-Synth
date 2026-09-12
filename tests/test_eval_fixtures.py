"""Offline tests of the evaluation-service parsers against the reference artifacts in tests/fixtures/
(docs/spec/01-eval-service.md §7). Bidirectional: real reports must reproduce the recorded metrics; garbage must
not produce numbers."""
import json
from pathlib import Path

import pytest

from src.eval import parse as P
from src.eval.yosys import _sta_metrics, _stat_metrics

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "rtllm_accu"
REQUIRED = ["E1", "E1d", "E2", "E3", "E4", "E2g", "H1", "H2a", "H2b", "H3", "H5", "Y", "Ycoevo", "H4"]  # E2r = E3 (alias)
CONFIGS = sorted(d.name for d in FIX.iterdir() if (d / "meta.json").exists()) if FIX.exists() else []


def meta_of(config):
    return json.loads((FIX / config / "meta.json").read_text())


def read(config, rel):
    p = FIX / config / rel
    return p.read_text(errors="replace") if p.exists() else ""


def test_fixture_set_is_complete_and_ok():
    missing = [c for c in REQUIRED if c not in CONFIGS]
    assert not missing, f"missing fixtures: {missing} (run scripts/make_fixtures.py)"
    for c in CONFIGS:
        m = meta_of(c)
        assert m["status"] == "ok", c
        assert m["checks"] and all(m["checks"].values()), (c, m["checks"])
        assert m["git_sha"] and m["cfg_hash"] and m["tool_version"], c


@pytest.mark.parametrize("config", [c for c in CONFIGS if meta_of(c)["tool"] == "dc"])
def test_dc_parsers_reproduce_recorded_metrics(config):
    m = meta_of(config)
    rep = f"outputs/reports/"
    qor = P.parse_qor(read(config, rep + "qor.rpt"))
    scale = 1000.0 if m["lib"] == "asap7" else 1.0
    assert qor["area"] == m["metrics"]["area"]
    assert int(qor["cells"]) == m["metrics"]["cells"]
    assert qor["tns"] / scale == pytest.approx(m["metrics"]["tns_ns"])
    wns_attr = P.kv_file(read(config, rep + "metrics.txt")).get("wns")
    assert float(wns_attr) / scale == pytest.approx(m["metrics"]["wns_ns"])
    refs = P.parse_reference(read(config, rep + "refs.rpt"))
    assert refs["hist"] == m["hist"] and refs["n_cells"] == m["metrics"]["cells"]
    paths = P.parse_timing(read(config, rep + "timing.rpt"))
    assert paths and paths[0]["endpoint"] == m["crit_path"]["endpoint"] and paths[0]["points"]
    if "-gate_clock" in m["config_compile"]:
        cg = P.parse_clock_gating(read(config, rep + "clock_gating.rpt"))
        assert cg["icg_count"] == m["metrics"]["icg_count"] >= 1
        assert cg["gated_regs"] + cg["ungated_regs"] == cg["total_regs"]
    pw = P.parse_power(read(config, rep + "power_default.rpt"))
    assert pw["total_mw"] == pytest.approx(m["metrics"]["power_default_mw"])
    res = P.parse_resources(read(config, rep + "resources.rpt"))
    assert res["datapath_blocks"] == m["resources"]["datapath_blocks"]
    assert "create_clock" in read(config, rep + "applied_constraints.sdc")


def test_e4_log_summary_sees_retiming_and_clock_gating():
    m = meta_of("E4")
    log = read("E4", "outputs/dc_shell.log")
    if not log:
        pytest.skip("E4 dc_shell.log not in the fixtures")
    s = P.log_summary(log)
    assert s["counts"]["clock_gating"] >= 1 and s["counts"]["retime"] >= 1 and s["counts"]["error"] == 0
    assert s["counts"] == m["log_summary"]["counts"]


@pytest.mark.parametrize("config", [c for c in ("Y", "Ycoevo") if c in CONFIGS])
def test_yosys_parsers_reproduce_recorded_metrics(config):
    m = meta_of(config)
    area, cells, hist = _stat_metrics(read(config, "outputs/yosys.log"))
    assert area == m["metrics"]["area"] and cells == m["metrics"]["cells"] and hist == m["hist"]
    sm = _sta_metrics(read(config, "outputs/opensta.log"), "clk")
    assert sm["wns_ns"] == pytest.approx(m["metrics"]["wns_ns"]) and sm["tns_ns"] == pytest.approx(m["metrics"]["tns_ns"])
    assert sm["crit_group"] == "clk"
    sdc = read(config, "inputs/constraint.sdc")
    if config == "Ycoevo":
        assert "set_input_delay 0 " in sdc and "set_max_delay" in sdc  # COEVO's OpenSTA setting
    else:
        assert "set_input_delay 0.4 " in sdc and "set_max_delay" not in sdc  # the project convention (20% of 2.0 ns)


def test_ladder_definition_matches_the_decision():
    """DECISIONS 2026-09-12: E1 standard library only, E2r alias of E3, E2t gone, no ignored high-effort flag in the ladder."""
    from src import config as C
    from src.eval.service import canonical_config
    cfg = C.load()
    cs = cfg["configs"]
    assert cs["E1"]["synlib"] == "standard" and cs["E1d"]["synlib"] == "dw" and cs["E1"]["compile"] == cs["E1d"]["compile"] == "compile"
    assert canonical_config(cfg, "E2r") == "E3" and "E2t" not in cs
    for name in ("E1", "E1d", "E2", "E3", "E4", "E2g", "H1", "H2a", "H2b", "H5"):
        assert "-timing_high_effort_script" not in cs[name]["compile"], name
    assert cs["E4"]["compile"] == "compile_ultra -retime -gate_clock" and cs["E4"].get("main_scoring")
    assert "-spg" in cs["H3"]["compile"] and "compile_timing_high_effort" in cs["H3"]["compile"]
    assert "E2t" not in cfg["exp1"]["configs"] and "E1d" in cfg["exp1"]["configs"] and "Ycoevo" in cfg["exp1"]["supplementary"]


def test_h4_signoff_agrees_with_e4_in_sign_and_magnitude():
    if "H4" not in CONFIGS or "E4" not in CONFIGS:
        pytest.skip("no H4/E4 fixtures")
    h4, e4 = meta_of("H4")["metrics"], meta_of("E4")["metrics"]
    assert h4["wns_ns"] is not None and (h4["wns_ns"] >= 0) == (e4["wns_ns"] >= 0)
    assert abs(h4["wns_ns"] - e4["wns_ns"]) < 0.5 * meta_of("E4")["clock_ns"]
    assert h4["power_default_mw"] and e4["power_default_mw"]
    assert 0.1 < h4["power_default_mw"] / e4["power_default_mw"] < 10  # same order of magnitude (PLAN 0.7)


def test_parsers_reject_garbage():
    q = P.parse_qor("nothing to see here\nDesign Area: nope\n")
    assert q["area"] is None and q["wns"] is None and q["tns"] is None and q["cells"] is None
    assert P.parse_reference("garbage")["n_cells"] == 0
    assert P.parse_clock_gating("") == {} and P.parse_power("") == {} and P.parse_timing("") == []
    assert P.parse_resources("")["datapath_blocks"] == 0
    assert P.license_failure("Licensed Products: DC Ultra") is None  # the banner must not trigger the signature
    assert P.license_failure("Error: Design Compiler is not enabled (DCSH-1)") == "Design Compiler is not enabled"
    assert P.sdc_errors("no markers") == [] and P.sdc_errors("###SDC_BEGIN###\nError: bad (CMD-010)\n###SDC_END###") == ["Error: bad (CMD-010)"]
    area, cells, hist = _stat_metrics("no stat block")
    assert area is None and cells is None and hist == {}
    assert _sta_metrics("no paths", "clk") == {}
