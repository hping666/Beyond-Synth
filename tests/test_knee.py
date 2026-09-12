"""Bidirectional tests for the knee-point rule (src/eval/knee.py)."""
import pytest

from src import config as C
from src.eval.knee import choose_knee

CFG = C.load()["knee"]


def curve(rows):
    return [{"T": t, "area": a, "wns": w, "tns": s} for t, a, w, s in rows]


def test_picks_tightest_period_before_area_rises():
    pts = curve([(4.0, 100, 2.5, 0), (2.8, 100, 1.3, 0), (2.0, 101, 0.5, 0), (1.4, 104, 0.01, 0),
                 (1.0, 130, -0.05, -1.2), (0.7, 160, -0.3, -9), (0.5, 170, -0.5, -20)])
    T, fb = choose_knee(pts, CFG["slack_tol"], CFG["area_tol"])
    assert T == 1.4 and fb is False  # 1.0 ns still meets timing within tol? WNS -0.05 < -0.01*1.0 -> not a candidate


def test_slack_tolerance_admits_slightly_negative_wns():
    pts = curve([(4.0, 100, 2.5, 0), (2.0, 102, -0.015, -0.1), (1.0, 150, -0.4, -5)])
    T, fb = choose_knee(pts, slack_tol=0.01, area_tol=0.10)
    assert T == 2.0 and fb is False  # -0.015 >= -0.01*2.0


def test_area_bound_rejects_sharp_rise():
    pts = curve([(4.0, 100, 2.0, 0), (2.0, 100, 0.8, 0), (1.0, 125, 0.02, 0)])
    T, fb = choose_knee(pts, slack_tol=0.01, area_tol=0.10)
    assert T == 2.0 and fb is False  # 1.0 ns meets timing but area 125 > 110


def test_fallback_when_nothing_meets_timing():
    pts = curve([(4.0, 100, -0.5, -3.0), (2.0, 120, -1.0, -8.0), (1.0, 150, -1.6, -20.0)])
    T, fb = choose_knee(pts, slack_tol=0.01, area_tol=0.10)
    assert T == 4.0 and fb is True


def test_missing_values_ignored_and_empty_rejected():
    pts = curve([(4.0, 100, 2.0, 0)]) + [{"T": 2.0, "area": None, "wns": None, "tns": None}]
    assert choose_knee(pts, 0.01, 0.1) == (4.0, False)
    with pytest.raises(ValueError):
        choose_knee([{"T": 2.0, "area": None, "wns": None, "tns": None}], 0.01, 0.1)


def test_config_periods_are_geometric_and_descending():
    for lib, periods in CFG["periods_ns"].items():
        assert periods == sorted(periods, reverse=True), lib
        assert len(periods) == 7
