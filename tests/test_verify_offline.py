"""Bidirectional tests of src/analysis/verify.py: the report parsers (area, slack, leaf cells, power in any unit, the
first three endpoints, the netlist histogram without the module names), and the independent B.2 re-derivation on
synthetic report sets: retained, absorbed_identical, duplicate, absorbed (converged but not identical), noise, harmful,
tradeoff; an unreadable record is None."""
import copy

from src.analysis import verify as V

QOR = "  Critical Path Length:      0.660732\n  Critical Path Slack:       {slack}\n  Leaf Cell Count:                {cells}\n"
AREA = "Number of cells:  429\nCombinational area:  302.7\nTotal cell area:                   {area}\n"
POWER = "Total Dynamic Power    = 106.26 uW  (100%)\nCell Leakage Power     =  17.75 uW\n                 Internal   Switching   Leakage   Total\nTotal           67.12 uW      39.14 uW     1.7e+04 nW     {total} {unit}\n"
TIMING = "  Startpoint: a_reg[0]\n  Endpoint: {e1}\n  slack (MET)   0.003817\n\n  Startpoint: a_reg[1]\n  Endpoint: {e2}\n  slack (VIOLATED)   -0.01\n"
NETLIST = "module top ( clk, y );\n  input clk;\n  wire n1;\n  sub u_sub ( .a(n1) );\n{cells}endmodule\n\nmodule sub ( a );\n  input a;\n  NAND2_X1 U1 ( .A1(a), .A2(a), .ZN(n2) );\nendmodule\n"


def write_record(root, area, slack, cells, power_uw, hist, endpoints=("y_reg[0]", "y_reg[1]"), power_default_uw=None, saif=True):
    rep = root / "outputs" / "reports"
    rep.mkdir(parents=True, exist_ok=True)
    (rep / "qor.rpt").write_text(QOR.format(slack=slack, cells=cells))
    (rep / "area.rpt").write_text(AREA.format(area=area))
    if saif:
        (rep / "power_saif.rpt").write_text(POWER.format(total=power_uw, unit="uW"))
    if power_default_uw is not None:
        (rep / "power_default.rpt").write_text(POWER.format(total=power_default_uw, unit="uW"))
    (rep / "timing.rpt").write_text(TIMING.format(e1=endpoints[0], e2=endpoints[1]))
    lines = "".join(f"  {typ} U{i}_{k} ( .A(n1), .ZN(n1) );\n" for typ, n in hist.items() for i, k in enumerate(range(n)))
    (rep / "netlist.v").write_text(NETLIST.format(cells=lines))
    return root


def test_parsers(tmp_path):
    r = write_record(tmp_path / "r", 937.118020, 0.003817, 421, 124.018456, {"NAND2_X1": 3, "DFF_X1": 2})
    rec = V.record_from_reports(r)
    assert rec["area"] == 937.11802 and rec["wns_ns"] == 0.003817 and rec["cells"] == 421 and abs(rec["power_saif_mw"] - 0.124018456) < 1e-9 and rec["power_default_mw"] is None
    assert rec["hist"] == {"NAND2_X1": 4, "DFF_X1": 2}                        # the NAND2 inside `sub` counts too; `sub` itself (a module) does not
    assert rec["endpoints"] == [("a_reg[0]", "y_reg[0]", 0.003817), ("a_reg[1]", "y_reg[1]", -0.01)]
    assert V.parse_power_mw("Total   1.5 mW\n") == 1.5 and V.parse_power_mw("Total   2 W\n") == 2000.0 and V.parse_power_mw("nothing") is None
    assert V.parse_slack("Critical Path Slack:  -0.25") == -0.25 and V.parse_area("no area here") is None
    assert V.record_from_reports(tmp_path / "missing") is None


def test_independent_labels(tmp_path):
    t_d = {"area": 0.01, "wns": 0.01, "power": 0.02}
    d = V.record_from_reports(write_record(tmp_path / "d", 1000.0, 0.05, 100, 500.0, {"NAND2_X1": 60, "DFF_X1": 40}))
    same = V.record_from_reports(write_record(tmp_path / "same", 1000.0, 0.05, 100, 500.0, {"NAND2_X1": 60, "DFF_X1": 40}))
    assert V.independent_diagnosis(d, same, 2.0, t_d, 0.003)["label"] == "absorbed_identical"
    smaller = V.record_from_reports(write_record(tmp_path / "small", 900.0, 0.05, 90, 450.0, {"NAND2_X1": 50, "DFF_X1": 40}))
    r = V.independent_diagnosis(d, smaller, 2.0, t_d, 0.003)
    assert r["label"] == "retained" and r["up"] == ["area", "power"] and r["down"] == [] and abs(r["gains"]["area"] - 0.1) < 1e-9
    earlier = copy.deepcopy(smaller)
    assert V.independent_diagnosis(d, smaller, 2.0, t_d, 0.003, duplicate_rec=earlier)["label"] == "duplicate"        # identical to the earlier candidate
    assert V.independent_diagnosis(d, smaller, 2.0, t_d, 0.003, duplicate_rec=same)["label"] == "retained"           # not identical to it
    near = V.record_from_reports(write_record(tmp_path / "near", 1001.0, 0.05, 100, 500.0, {"NAND2_X1": 60, "DFF_X1": 40, "INV_X1": 1}))
    r = V.independent_diagnosis(d, near, 2.0, t_d, 0.003)
    assert r["label"] == "absorbed" and r["jaccard"] > 0.95 and r["area_within_sigma"] and r["endpoints_coincide"] is True
    r = V.independent_diagnosis(d, near, 2.0, t_d, 0.0005)                                                             # outside sigma: not converged
    assert r["label"] == "noise"
    other = V.record_from_reports(write_record(tmp_path / "other", 1002.0, 0.05, 100, 501.0, {"NOR2_X1": 60, "DFF_X1": 40}))
    assert V.independent_diagnosis(d, other, 2.0, t_d, 0.01)["label"] == "noise"                                        # inside the band, different netlist
    bigger = V.record_from_reports(write_record(tmp_path / "big", 1100.0, 0.05, 110, 560.0, {"NAND2_X1": 70, "DFF_X1": 40}))
    assert V.independent_diagnosis(d, bigger, 2.0, t_d, 0.003)["label"] == "harmful"
    mixed = V.record_from_reports(write_record(tmp_path / "mixed", 900.0, 0.05, 90, 560.0, {"NAND2_X1": 50, "DFF_X1": 40}))
    r = V.independent_diagnosis(d, mixed, 2.0, t_d, 0.003)
    assert r["label"] == "tradeoff" and r["up"] == ["area"] and r["down"] == ["power"]
    slow = V.record_from_reports(write_record(tmp_path / "slow", 1000.0, -0.05, 100, 500.0, {"NAND2_X1": 60, "DFF_X1": 40, "INV_X1": 2}))
    r = V.independent_diagnosis(d, slow, 2.0, t_d, 0.003)
    assert r["label"] == "absorbed" and r["down"] == ["wns"] and abs(r["gains"]["wns"] + 0.05) < 1e-9                  # (−0.05 − 0.05) / 2.0; spec B.2 puts convergence before harmful
    slow2 = V.record_from_reports(write_record(tmp_path / "slow2", 1000.0, -0.05, 100, 500.0, {"NOR2_X1": 60, "DFF_X1": 40}))
    r = V.independent_diagnosis(d, slow2, 2.0, t_d, 0.003)
    assert r["label"] == "harmful" and r["down"] == ["wns"]                                                            # not converged: the timing loss counts
    assert V.independent_diagnosis(d, smaller, 2.0, {}, 0.003)["label"] == "noise"                                     # no thresholds: no verdict on any metric


def test_power_basis_mirrors_the_rule(tmp_path):
    """A record without SAIF power is compared on the default-activity basis on both sides; a SAIF figure never meets a
    default one (the mixed pairs of 2026-09-15)."""
    t_d = {"area": 0.01, "wns": 0.01, "power": 0.02}
    d = V.record_from_reports(write_record(tmp_path / "d", 1000.0, 0.05, 100, 500.0, {"NAND2_X1": 60, "DFF_X1": 40}, power_default_uw=2000.0, saif=False))
    c = V.record_from_reports(write_record(tmp_path / "c", 1000.0, 0.05, 100, 50.0, {"NOR2_X1": 60, "DFF_X1": 40}, power_default_uw=1900.0))
    r = V.independent_diagnosis(d, c, 2.0, t_d, 0.003)
    assert r["power_basis"] == "default" and abs(r["gains"]["power"] - 0.05) < 1e-9 and r["label"] == "retained"       # 2000 vs 1900, not 2000 vs 50
    c2 = V.record_from_reports(write_record(tmp_path / "c2", 1000.0, 0.05, 100, 50.0, {"NOR2_X1": 60, "DFF_X1": 40}))
    r = V.independent_diagnosis(d, c2, 2.0, t_d, 0.003)
    assert r["power_basis"] is None and "power" not in r["gains"] and r["label"] == "noise"                            # no common basis: no power verdict
