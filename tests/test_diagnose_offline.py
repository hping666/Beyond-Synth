"""Bidirectional tests of the diagnoser M3 (spec 04 §B) on synthetic E4 records: every label of the decision order,
the rung attribution from lower rungs, the harmful/blocks_synthesis sub-label, the feedback block and the credit."""
import copy

from src.diagnose import m3

BASE = {"metrics": {"area": 100.0, "wns_ns": 0.5, "tns_ns": 0.0, "power_saif_mw": 1.0, "registers": 10, "icg_count": 1},
        "hist": {"DFF_X1": 10, "NAND2_X1": 20, "XOR2_X1": 5}, "resources": {"dw_modules": ["DW02_mult"], "datapath_blocks": 1, "shared_resources": 0},
        "path_endpoints": [["a", "q_reg[3]", 0.5], ["b", "q_reg[2]", 0.6]], "log_summary": {"counts": {"retime": 1, "ungroup": 2}}}
SIGMA = {"area": 0.01, "wns": 0.01, "power": 0.02}
T = 2.0


def cand(**changes):
    c = copy.deepcopy(BASE)
    for k, v in changes.items():
        if k in c["metrics"]:
            c["metrics"][k] = v
        else:
            c[k] = v
    return c


def test_labels_follow_the_decision_order():
    assert m3.diagnose(BASE, cand(), SIGMA, T, v3_status="inconclusive")["label"] == "nonequiv"
    assert m3.diagnose(BASE, cand(), SIGMA, T)["label"] == "absorbed_identical"  # identical fingerprint (DECISIONS 2026-09-14 C2.4)
    r = m3.diagnose(BASE, cand(area=90.0, hist={"DFF_X1": 10, "NAND2_X1": 12, "XOR2_X1": 5}), SIGMA, T)
    assert r["label"] == "retained" and r["evidence"]["gains"]["area"] == 0.1 and r["rung"] == "E4"
    r = m3.diagnose(BASE, cand(area=101.5, hist={"DFF_X1": 10, "NAND2_X1": 21, "XOR2_X1": 5, "AOI21_X1": 3}), SIGMA, T)
    assert r["label"] == "noise"  # within 2 sigma but the fingerprint moved
    r = m3.diagnose(BASE, cand(area=120.0, resources={"dw_modules": [], "datapath_blocks": 0, "shared_resources": 0}), SIGMA, T)
    assert r["label"] == "harmful" and r["sublabel"] == "blocks_synthesis" and r["evidence"]["missing_resources"] == ["DW02_mult"]
    r = m3.diagnose(BASE, cand(area=120.0, hist={"DFF_X1": 12, "NAND2_X1": 30}), SIGMA, T)
    assert r["label"] == "harmful" and r["sublabel"] is None
    r = m3.diagnose(BASE, cand(area=85.0, wns_ns=0.3, hist={"DFF_X1": 9, "NAND2_X1": 12}), SIGMA, T)
    assert r["label"] == "tradeoff" and "up=area" in r["sublabel"] and "down=wns" in r["sublabel"]


def test_rung_attribution_from_lower_rungs():
    c = cand(area=100.4, hist={"DFF_X1": 10, "NAND2_X1": 20, "XOR2_X1": 5, "INV_X1": 1})  # converged at E4 (within sigma, Jaccard >= 0.95) but not identical
    lower = {"E1": (BASE, cand(area=110.0, hist={"DFF_X1": 10, "NAND2_X1": 40}), 0.01), "E2": (BASE, cand(), 0.01)}
    r = m3.diagnose(BASE, c, SIGMA, T, lower_rungs=lower, prior={"capability_of_rung": {"E2": "resource_sharing"}})
    assert r["label"] == "absorbed" and r["rung"] == "E2" and r["capability"] == "resource_sharing" and r["attribution"] == "measured"
    r = m3.diagnose(BASE, c, SIGMA, T, prior={"capability": "unknown_from_map"})
    assert r["rung"] == "after_Es" and r["attribution"] == "prior" and r["capability"] == "unknown_from_map"


def test_fingerprint_helpers_and_feedback():
    assert m3.weighted_jaccard({"a": 2, "b": 1}, {"a": 2, "b": 1}) == 1.0 and abs(m3.weighted_jaccard({"a": 2}, {"a": 1, "b": 1}) - 1 / 3) < 1e-9
    assert m3.weighted_jaccard({}, {}) == 1.0
    assert m3.endpoints_coincide(BASE, cand()) is True and m3.endpoints_coincide(BASE, cand(path_endpoints=[["x", "z_reg", 0.1]])) is False
    assert m3.endpoints_coincide(BASE, cand(path_endpoints=[])) is None
    g = m3.relative_gains(BASE, cand(area=90.0, wns_ns=0.7, power_saif_mw=0.8), T)
    assert {k: round(v, 9) for k, v in g.items()} == {"area": 0.1, "wns": 0.1, "power": 0.2}
    d = m3.diagnose(BASE, cand(area=90.0, hist={"DFF_X1": 10, "NAND2_X1": 12}), SIGMA, T)
    fb = m3.feedback_block(d, "(b)", ["resource_sharing"], prior={"absorb_prob": 0.3})
    assert fb["diagnosis"] == "retained" and fb["evidence"]["dA_pct"] == -10.0 and fb["evidence"]["sigma2_pct"] == 2.0 and fb["prior"] == {"absorb_prob": 0.3}
    assert m3.credit(d, False) == 1 and m3.credit({"label": "absorbed"}, True) == 0 and m3.credit({"label": "tradeoff"}, True) == 1 and m3.credit({"label": "tradeoff"}, False) == 0
    assert m3.screened_out_block("E1", True) == {"diagnosis": "screened_out", "rung": "E1", "fp_converged": True}
    assert "retained" in m3.to_json(d)


def test_new_labels_absorbed_identical_duplicate_fragile_and_rule_a_bands():
    """DECISIONS 2026-09-14 C2.4 / G1.1: identical E4 netlist -> absorbed_identical; identical to an earlier candidate ->
    duplicate; a retained gain on a spread / offset design that does not beat the candidate's own perturbation envelope ->
    fragile; the rule-A thresholds replace k*sigma as the band; an offset design is flagged."""
    r = m3.diagnose(BASE, cand(), SIGMA, T)
    assert r["label"] == "absorbed_identical" and r["attribution"] == "measured" and r["evidence"]["identical_fingerprint"] is True
    c1 = cand(area=90.0, hist={"DFF_X1": 10, "NAND2_X1": 12, "XOR2_X1": 5})
    r = m3.diagnose(BASE, c1, SIGMA, T, run_fingerprints={"cand_A": c1})
    assert r["label"] == "duplicate" and r["duplicate_of"] == "cand_A"
    r = m3.diagnose(BASE, c1, SIGMA, T, run_fingerprints={"cand_A": cand(area=95.0)})
    assert r["label"] == "retained"  # a different earlier candidate is no duplicate
    # rule-A thresholds: an area gain of 10 % is retained at t_D = 5 % but noise-or-absorbed at t_D = 12 %
    assert m3.diagnose(BASE, c1, SIGMA, T, thresholds={"area": 0.05, "wns": 0.01, "power": 0.02})["label"] == "retained"
    assert m3.diagnose(BASE, c1, SIGMA, T, thresholds={"area": 0.12, "wns": 0.01, "power": 0.02})["label"] == "noise"
    # spread / offset designs: the envelope decides between retained and fragile
    r = m3.diagnose(BASE, c1, SIGMA, T, floor_class="offset")
    assert r["label"] == "retained" and r.get("envelope_required") is True and r["offset_design"] is True
    r = m3.diagnose(BASE, c1, SIGMA, T, floor_class="spread", envelope=[{"area": 0.02}, {"area": 0.11}])
    assert r["label"] == "fragile" and r["evidence"]["envelope_max"]["area"] == 0.11 and m3.credit(r, True) == 0
    r = m3.diagnose(BASE, c1, SIGMA, T, floor_class="spread", envelope=[{"area": 0.02}, {"area": 0.03}])
    assert r["label"] == "retained" and r["offset_design"] is False and m3.credit(r, False) == 1
    assert m3.diagnose(BASE, c1, SIGMA, T, floor_class="quiet")["label"] == "retained"  # quiet designs need no envelope


def test_rung_attribution_compares_under_the_same_rung():
    """DECISIONS 2026-09-14 G1.4: the candidate is compared with D under each rung; a higher rung never dominates a lower
    one. (i) equal to D at E2 but not at E1 -> absorbed@E2 even though E1 differs; (ii) better than D at E1 and worse at E3
    but identical at E4 -> absorbed_identical, never retained or harmful from a lower rung."""
    base_e1 = cand(area=130.0, hist={"DFF_X1": 10, "NAND2_X1": 40})   # D's own E1 result (a weaker rung: larger area)
    base_e2 = cand(area=110.0, hist={"DFF_X1": 10, "NAND2_X1": 25})
    c_e1 = cand(area=131.0, hist={"DFF_X1": 10, "NAND2_X1": 38, "AOI21_X1": 4})   # not converged with D@E1
    c_e2 = cand(area=110.0, hist={"DFF_X1": 10, "NAND2_X1": 25})                   # converged with D@E2
    c_e4 = cand(area=100.5, hist={"DFF_X1": 10, "NAND2_X1": 20, "XOR2_X1": 5, "INV_X1": 1})  # within the band at E4, fingerprint moved
    lower = {"E1": (base_e1, c_e1, 0.01), "E2": (base_e2, c_e2, 0.01)}
    r = m3.diagnose(BASE, c_e4, SIGMA, T, lower_rungs=lower, prior={"capability_of_rung": {"E2": "resource_sharing"}})
    assert r["label"] == "absorbed" and r["rung"] == "E2" and r["attribution"] == "measured" and r["capability"] == "resource_sharing"
    # the same E2 records compared against D's E4 record would not converge (area 110 vs 100): the rung must use its own baseline
    assert m3.converged(BASE, c_e2, 0.01, 0.95)[0] is False and m3.converged(base_e2, c_e2, 0.01, 0.95)[0] is True
    better_e1 = cand(area=80.0, hist={"DFF_X1": 10, "NAND2_X1": 10})   # far better than D at E1 ...
    worse_e3 = cand(area=150.0, hist={"DFF_X1": 12, "NAND2_X1": 50})   # ... and far worse at E3
    r = m3.diagnose(BASE, cand(), SIGMA, T, lower_rungs={"E1": (base_e1, better_e1, 0.01), "E3": (base_e2, worse_e3, 0.01)})
    assert r["label"] == "absorbed_identical"  # identical at E4: the lower rungs neither promote nor demote the verdict


def test_power_basis_is_never_mixed():
    """2026-09-15: a SAIF power figure is compared only with a SAIF figure; when one side lacks SAIF power both sides use
    the default-activity figure; without any common basis there is no power gain. The evidence records the basis."""
    def rec(**metrics):
        c = cand()
        c["metrics"].update(metrics)
        return c
    d_saif = rec(power_saif_mw=1.0, power_default_mw=4.0)
    c_saif = rec(power_saif_mw=0.8, power_default_mw=3.0)
    c_default = rec(power_saif_mw=None, power_default_mw=3.0)
    assert m3.power_basis(d_saif, c_saif) == "saif" and round(m3.relative_gains(d_saif, c_saif, T)["power"], 9) == 0.2
    assert m3.power_basis(d_saif, c_default) == "default" and round(m3.relative_gains(d_saif, c_default, T)["power"], 9) == 0.25      # 4.0 vs 3.0, not 1.0 vs 3.0
    d_default = rec(power_saif_mw=None, power_default_mw=4.0)
    assert m3.power_basis(d_default, c_saif) == "default" and round(m3.relative_gains(d_default, c_saif, T)["power"], 9) == 0.25       # not 4.0 vs 0.8 (+80 %)
    none = rec(power_saif_mw=None, power_default_mw=None)
    assert m3.power_basis(none, c_saif) is None and "power" not in m3.relative_gains(none, c_saif, T)
    c = rec(area=90.0, power_saif_mw=None, power_default_mw=3.0)
    c["hist"] = {"DFF_X1": 10, "NAND2_X1": 12}
    r = m3.diagnose(d_saif, c, SIGMA, T)
    assert r["evidence"]["power_basis"] == "default" and round(r["evidence"]["gains"]["power"], 5) == 0.25
