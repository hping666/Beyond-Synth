"""Bidirectional tests of the map (spec 08 §1, PLAN 4.4 / 4.7 / 4.8) and the retention predictor (spec 08 §2, PLAN 4.5)
on synthetic object rows: retention against the rule-A threshold of each configuration, retention curves, non-monotone
detection, the literature table, the misclassification rates, the map shape; the predictor's leave-one-design-out
evaluation on separable data (AUROC 1) versus random labels (AUROC ≈ 0.5), the class-blind control, thresholds."""
import random

from src.analysis import map as M
from src.analysis import predictor as P

T = {c: {"area": 0.01, "wns": 0.01, "power": 0.02} for c in M.LADDER}


def obj(cid, design, cls, gains_area, label=None, rung=None, role="b0", proven=True):
    return {"cand_id": cid, "design_id": design, "cls": cls, "role": role, "label": label, "rung": rung, "attribution": "measured" if rung else None, "proven": proven,
            "gains": {c: {"area": g, "wns": 0.0, "power": 0.0} for c, g in gains_area.items()}, "t_d": T}


def test_cells_curves_and_non_monotone():
    objs = [obj("x1", "d1", "d", {"E1": 0.2, "E2": 0.15, "E3": 0.12, "E4": 0.10}, "retained"),
            obj("x2", "d1", "d", {"E1": 0.2, "E2": 0.005, "E3": 0.0, "E4": 0.0}, "absorbed", "E2"),
            obj("x3", "d2", "a", {"E1": 0.05, "E2": 0.0, "E3": 0.0, "E4": 0.0}, "absorbed_identical", "E4"),
            obj("x4", "d2", "a", {"E1": 0.0, "E2": 0.0, "E3": 0.0, "E4": 0.03}, "retained"),          # inside the band at E1-E3, out again at E4: non-monotone
            obj("x5", "d2", "b", {"E1": 0.02}, None)]                                                  # no E4 record: not evaluated there
    assert M.retained_under(objs[0], "E4") is True and M.retained_under(objs[1], "E4") is False and M.retained_under(objs[4], "E4") is None
    c = M.cell(objs, "d", "E4")
    assert c["n"] == 2 and c["n_evaluated"] == 2 and c["n_retained"] == 1 and c["retention_rate"] == 0.5 and c["magnitude_median"] == 0.10
    assert c["absorption_rung"] == {"E2": 1} and c["attribution"] == {"measured": 1} and c["labels"] == {"absorbed": 1, "retained": 1}
    assert M.cell(objs, "b", "E4")["n_evaluated"] == 0 and M.cell(objs, "b", "E4")["retention_rate"] is None
    curves = M.retention_curves(objs, ("E1", "E2", "E4"))
    assert curves["d"] == [("E1", 1.0, 2), ("E2", 0.5, 2), ("E4", 0.5, 2)] and curves["a"][0] == ("E1", 0.5, 2)
    nm = M.non_monotone(objs)
    assert nm["cases"] == [("x4", "---R")] and nm["n_evaluated_on_all"] == 4 and nm["fraction"] == 0.25
    mp = M.build_map(objs, ("E1", "E4"))
    assert set(mp) == set(M.CLASSES) and mp["d"]["E1"]["n_retained"] == 2
    assert M.shape(mp, min_n=1)[0] == "diffuse"             # d and a both retain 50 % at E4: no class structure
    conc = [obj(f"k{i}", "d1", "d", {"E4": 0.05}, "retained") for i in range(10)] + [obj(f"j{i}", "d1", "a", {"E4": 0.0}, "absorbed") for i in range(10)]
    assert M.shape(M.build_map(conc, ("E4",)), min_n=10) == ("concentrated", {"a": 0.0, "d": 1.0})
    low = [obj(f"z{i}", "d1", "b", {"E4": 0.0}, "absorbed") for i in range(12)]
    assert M.shape(M.build_map(low, ("E4",)), min_n=10)[0] == "near_zero"
    mixed = [obj(f"m{i}", "d1", "b", {"E4": 0.05 if i % 2 else 0.0}, "retained" if i % 2 else "absorbed") for i in range(12)]
    assert M.shape(M.build_map(mixed, ("E4",)), min_n=10)[0] == "diffuse"
    assert M.shape(M.build_map([], ("E4",)))[0] == "undetermined"


def test_literature_table_and_misclassification_rates():
    objs = [obj("r1", "rtlopt_p1", "b", {"E1": 0.05, "E4": 0.0}, "absorbed", "E2", role="reference"),
            obj("r2", "rtlopt_p2", "d", {"E1": 0.10, "E4": 0.08}, "retained", role="reference"),
            obj("r3", "rtlopt_p3", "a", {"E1": 0.004, "E4": -0.02}, "harmful", role="reference"),
            obj("r4", "rtlopt_p4", "a", {}, None, role="reference", proven=False),
            obj("s1", "rtlrewriter_q", "c1", {"E1": 0.3, "E4": 0.2}, "retained", role="llm"),           # not a pair: excluded
            obj("b1", "cktevo_x", "b", {"E4": 0.05}, "retained"), obj("b2", "cktevo_x", "b", {"E4": 0.0}, "absorbed"),
            obj("b3", "cktevo_x", "c1", {"E4": 0.0}, "absorbed_identical"), obj("b4", "cktevo_x", "d", {"E4": 0.05}, "tradeoff")]
    lt = M.literature_table(objs, ("E1", "E4"))
    assert set(lt) == {"rtlopt"} and lt["rtlopt"]["pairs"] == 4 and lt["rtlopt"]["proven"] == 3
    assert lt["rtlopt"]["better"] == {"E1": 3, "E4": 1} and lt["rtlopt"]["retained"] == {"E1": 2, "E4": 1} and lt["rtlopt"]["evaluated"] == {"E1": 3, "E4": 3}
    mr = M.misclassification_rates(objs)
    # forbidden (a, b) with a label: r1 absorbed, r3 harmful, b1 retained, b2 absorbed -> 1/4 retained; allowed (c1, c2, d): r2 retained, s1 retained, b3 absorbed_identical, b4 tradeoff -> 1/4 absorbed
    assert mr["n_forbidden"] == 4 and mr["p_retained_given_forbidden"] == 0.25 and mr["n_allowed"] == 4 and mr["p_absorbed_given_allowed"] == 0.25
    assert M.misclassification_rates([])["p_retained_given_forbidden"] is None


def rows(seed, separable):
    rng = random.Random(seed)
    out = []
    for i in range(120):
        design = f"d{i % 6}"
        cls = rng.choice(P.CLASSES)
        g1 = rng.uniform(-0.05, 0.3)
        g2 = g1 * rng.uniform(0.5, 1.0)
        if separable:
            y = int(g2 > 0.08)                       # E2 gain decides (a clean rule the model can learn)
        else:
            y = rng.randint(0, 1)
        out.append({"cand_id": f"c{i}", "design_id": design, "cls": cls, "g_e1": g1, "g_e2": g2, "fp_conv_e1": int(g1 < 0.01), "dff_delta": rng.randint(-4, 4), "diff_ratio": rng.random(), "retained_e4": y})
    return out


def test_predictor_lodo_separable_vs_random_and_class_blind():
    sep = P.evaluate(rows(1, True))
    assert sep["with_class"]["n"] == 120 and sep["with_class"]["auroc"] > 0.9 and sep["class_blind"]["auroc"] > 0.9
    assert sep["with_class"]["precision_at_85"] > 0.8 and sep["with_class"]["miss_rate_at_85"] is not None and sep["with_class"]["miss_rate_at_85"] <= 0.15 + 1e-9
    assert set(sep["with_class"]["feature_importance"]) == set(P.feature_names()) and abs(sep["with_class"]["feature_importance"]["g_e2"]) > 0
    assert set(sep["class_blind"]["feature_importance"]) == set(P.NUMERIC)
    rnd = P.evaluate(rows(2, False))
    assert 0.3 < rnd["with_class"]["auroc"] < 0.7                       # random labels: no information
    assert P.auroc([0.9, 0.8, 0.1, 0.2], [1, 1, 0, 0]) == 1.0 and P.auroc([0.5, 0.5], [1, 0]) == 0.5 and P.auroc([1.0], [1]) is None
    assert P.precision_recall_at([0.9, 0.2, 0.6], [1, 0, 0], 0.5) == (0.5, 1.0)
    tau, prec, miss = P.threshold_for_recall([0.9, 0.7, 0.2, 0.1], [1, 1, 0, 1], 0.85)
    assert tau == 0.1 and prec == 0.75 and miss == 0.0                   # recall >= 0.85 needs the lowest threshold
    assert P.threshold_for_recall([0.2, 0.3], [0, 0], 0.85) == (None, None, None)
    few = P.lodo(rows(3, True)[:5])
    assert few["n"] == 0 and few["auroc"] is None and len(few["skipped_designs"]) >= 1   # too few rows to train: nothing scored, nothing invented
