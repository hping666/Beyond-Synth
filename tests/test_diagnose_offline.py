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
    assert m3.diagnose(BASE, cand(), SIGMA, T)["label"] == "absorbed"  # identical fingerprint
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
    c = cand()
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
