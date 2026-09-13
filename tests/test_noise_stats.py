"""Numeric tests of the noise-floor statistics (spec 02 §7): MAD / q95 on known distributions, the wns denominator,
degenerate inputs, and the noise_floor upsert."""
import statistics

from src.db import core as db
from src.noise import stats as S


def test_deviations_and_robust_sigma_on_known_data():
    d = S.deviations("area", 100.0, [100, 101, 99, 102, 98, 150])  # 150 is an outlier
    assert d == [0.0, 0.01, -0.01, 0.02, -0.02, 0.5]
    s = S.summarize(d)
    assert abs(s["sigma_robust"] - 1.4826 * 0.015) < 1e-9 and s["n"] == 6 and s["max_abs"] == 0.5
    assert s["sigma_std"] == statistics.pstdev(d) and s["sigma_robust"] < s["sigma_std"]  # robust to the outlier
    assert S.quantile([1, 2, 3, 4, 5], 0.5) == 3 and S.quantile([1, 2, 3, 4, 5], 0.95) == 4.8 and S.mad([1, 1, 1]) == 0
    assert abs(S.quantile(sorted(abs(x) for x in d), 0.95) - s["q95_abs"]) < 1e-12


def test_wns_uses_the_clock_period_and_degenerate_cases():
    assert S.deviations("wns", 0.0, [0.1, -0.1], clock_ns=2.0) == [0.05, -0.05]
    assert S.deviations("wns", 0.0, [0.1], clock_ns=None) == []  # no period, no deviation
    assert S.deviations("area", 0.0, [1.0]) == [] and S.deviations("area", 10.0, [None, 11.0]) == [0.1]
    assert S.summarize([0.1]) is None and S.summarize([]) is None


def test_floor_rows_and_upsert(tmp_path):
    base = {"area_um2": 100.0, "cells": 40, "wns_ns": 0.2, "tns_ns": 0.0, "power_saif_mw": None}
    perts = [{"area_um2": 101.0, "wns_ns": 0.25, "tns_ns": 0.0}, {"area_um2": 99.0, "wns_ns": 0.15, "tns_ns": 0.0}, {"area_um2": 100.5, "wns_ns": 0.2, "tns_ns": 0.0}]
    rows = S.floor_rows("d1", "E4", base, perts, clock_ns=2.0)
    by = {r["metric"]: r for r in rows}
    assert set(by) == {"area", "wns", "tns"}  # power_saif missing in the baseline -> no row
    assert by["area"]["n"] == 3 and abs(by["area"]["abs_unit_value"] - by["area"]["sigma_robust"] * 40) < 1e-12
    assert by["tns"]["sigma_robust"] == 0 and abs(by["wns"]["max_abs"] - 0.025) < 1e-12
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    assert S.upsert_floor(conn, rows) == 3 and S.upsert_floor(conn, rows) == 3
    assert conn.execute("SELECT COUNT(*) FROM noise_floor").fetchone()[0] == 3


def test_pick_records_prefers_saif_backed_records_then_latest(tmp_path):
    """Both directions: a SAIF-backed record wins over a newer SAIF-less one; without any SAIF the newest wins;
    falsified perturbations, other clocks and failed records are never picked."""
    from src.db import core as db
    conn = db.connect(path=str(tmp_path / "r.sqlite"))

    n = [0]

    def ev(pert, area, saif, clock=1.0, status="ok"):
        n[0] += 1
        row = {"design_id": "d", "pert_id": pert, "is_baseline": int(pert is None), "config": "E4", "lib": "nangate45", "clock_ns": clock,
               "area_um2": area, "cells": 10, "wns_ns": 0.0, "tns_ns": 0.0, "power_saif_mw": saif, "status": status, "raw_dir": f"/x/{n[0]}", "hist_json": "{}"}
        return db.insert(conn, "evaluations", row)
    ev(None, 100.0, 1.5)      # SAIF-backed baseline (older)
    ev(None, 101.0, None)     # newer, no SAIF -> must lose
    ev(None, 102.0, 1.5, clock=2.0)  # other clock -> ignored at 1.0
    ev(None, 103.0, 1.5, status="failed")
    ev("p1", 10.0, None)
    ev("p1", 11.0, 1.0)       # SAIF-backed -> wins although not the last for p1? it is the last here; add a newer SAIF-less one:
    ev("p1", 12.0, None)
    ev("p2", 20.0, None)
    ev("p2", 21.0, None)      # no SAIF anywhere for p2 -> newest wins
    ev("p3", 30.0, 1.0)       # falsified (not in proven) -> ignored
    base, latest = S.pick_records(conn, "d", "E4", {"p1", "p2"}, 1.0)
    assert base["area_um2"] == 100.0 and base["power_saif_mw"] == 1.5
    assert latest["p1"]["area_um2"] == 11.0 and latest["p2"]["area_um2"] == 21.0 and "p3" not in latest
    base2, _ = S.pick_records(conn, "d", "E4", set(), 2.0)
    assert base2["area_um2"] == 102.0
    assert S.pick_records(conn, "d", "E1", set(), 1.0) == (None, {})


def test_conclusion_four_way_both_directions():
    """Signs: lower area / power and higher slack are gains; thresholds at k*sigma; unjudgeable inputs give None."""
    sig = {"area": 0.01, "wns": 0.02, "power_saif": 0.05}
    k = 2.0
    assert S.conclusion({"area": -0.05}, sig, k) == "retained"          # area down 5 % > 2 %
    assert S.conclusion({"area": +0.05}, sig, k) == "harmful"
    assert S.conclusion({"area": -0.015}, sig, k) == "noise"            # within 2 sigma
    assert S.conclusion({"area": -0.02}, sig, k) == "noise"             # exactly at the threshold is not beyond it
    assert S.conclusion({"wns": +0.05}, sig, k) == "retained"           # more slack
    assert S.conclusion({"wns": -0.05}, sig, k) == "harmful"
    assert S.conclusion({"area": -0.05, "wns": -0.05}, sig, k) == "trade-off"
    assert S.conclusion({"area": -0.05, "power_saif": +0.02}, sig, k) == "retained"  # power within 2 sigma (0.10)
    assert S.conclusion({"tns": None, "area": None}, sig, k) is None
    assert S.conclusion({"cells": -0.5}, sig, k) is None               # no sigma for that metric
    assert S.conclusion({}, sig, k) is None


def test_g1_analysis_helpers_both_directions(tmp_path):
    """floor_analysis / ptype_change_rates / monotonicity on a two-design, two-rung database: a perturbation that
    leaves the netlist unchanged counts as unchanged, one that changes it counts; the pooled quantiles and the proposed
    threshold come out as expected; a design whose area grows from E1 to E4 is counted as non-monotone."""
    from src.db import core as db
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    for pid, did, pt in (("a1", "A", "P1_rename"), ("a2", "A", "P2_reorder"), ("a3", "A", "P2_reorder"), ("b1", "B", "P1_rename"), ("b2", "B", "P1_rename")):
        db.insert(conn, "perturbations", {"pert_id": pid, "design_id": did, "ptype": pt, "path": "x", "seq_status": "proven"})
    n = [0]

    def ev(did, config, pert, area, cells=10):
        n[0] += 1
        db.insert(conn, "evaluations", {"design_id": did, "pert_id": pert, "is_baseline": int(pert is None), "config": config, "lib": "n", "clock_ns": 1.0,
                                        "area_um2": area, "cells": cells, "wns_ns": 0.0, "tns_ns": 0.0, "power_saif_mw": 1.0, "status": "ok", "raw_dir": f"/x/{n[0]}", "hist_json": "{}"})
    # design A: E1 area 100, E4 area 110 (non-monotone); perturbations a1 unchanged, a2 +10 %, a3 unchanged under E4
    ev("A", "E1", None, 100.0)
    ev("A", "E4", None, 110.0)
    ev("A", "E4", "a1", 110.0)
    ev("A", "E4", "a2", 121.0, cells=12)
    ev("A", "E4", "a3", 110.0)
    # design B: monotone (100 -> 90); both perturbations unchanged
    ev("B", "E1", None, 100.0)
    ev("B", "E4", None, 90.0)
    ev("B", "E4", "b1", 90.0)
    ev("B", "E4", "b2", 90.0)
    designs = [{"design_id": "A", "phi": 1.0}, {"design_id": "B", "phi": 1.0}]
    proven = S.proven_by_design(conn)
    assert proven == {"A": {"a1", "a2", "a3"}, "B": {"b1", "b2"}}
    fa = S.floor_analysis(conn, designs, ["E4"], proven, k=2.0)
    a = fa[("E4", "area")]
    assert a["records"] == 5 and abs(a["frac_zero"] - 0.8) < 1e-9 and a["designs"] == 2
    assert a["zero_robust"] == 2 and a["zero_std"] == 1           # A: MAD of [0, .1, 0] is 0 but std > 0; B: all zero
    assert abs(a["pooled"]["max"] - 0.1) < 1e-9 and a["max_abs_gt"] == {"1pct": 1, "5pct": 1}
    assert abs(a["t_proposed"]["max"] - 0.1) < 1e-9 and a["t_proposed"]["above_pooled_min"] == 1  # A above the pooled q90, B at it
    rates = S.ptype_change_rates(conn, designs, ["E4"], proven)
    assert rates[("E4", "P1_rename")] == {"n": 3, "changed": 0} and rates[("E4", "P2_reorder")] == {"n": 2, "changed": 1}
    mono = S.monotonicity(conn, designs, ["E1", "E4"])
    assert mono["n"] == 2 and mono["steps"][("E1", "E4")] == {"area_up": 1, "wns_down": 0}
