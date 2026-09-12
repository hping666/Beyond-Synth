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
