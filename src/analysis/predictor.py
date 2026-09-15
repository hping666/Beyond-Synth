"""Retention predictor (docs/spec/08-analysis.md §2, PLAN 4.5): features of an object (M6 class one-hot, area gains at
E1 and E2, E1 fingerprint convergence, flip-flop-bit change, token diff ratio) -> E4 retention; logistic regression
(scikit-learn), leave-one-design-out cross-validation, AUROC, precision / recall, precision at the threshold that gives
recall >= 0.85, miss rate; and the class-blind control (the same model without the class features). Pure functions over
object rows; the caller builds the rows from the results database.

Object row: {"cand_id", "design_id", "cls", "g_e1", "g_e2", "fp_conv_e1" (0/1), "dff_delta" (ff_c - ff_d), "diff_ratio", "retained_e4" (0/1)}
"""
import math

import numpy as np

CLASSES = ("a", "b", "c1", "c2", "d")
NUMERIC = ("g_e1", "g_e2", "fp_conv_e1", "dff_delta", "diff_ratio")


def feature_names(class_blind=False):
    return list(NUMERIC) + ([] if class_blind else [f"cls_{c}" for c in CLASSES])


def featurize(rows, class_blind=False):
    X = []
    for r in rows:
        x = [float(r.get(k) or 0.0) for k in NUMERIC]
        if not class_blind:
            x += [1.0 if r.get("cls") == c else 0.0 for c in CLASSES]
        X.append(x)
    return np.array(X, dtype=float)


def auroc(scores, y):
    """Ties count half; None when a class is empty."""
    pos = [s for s, t in zip(scores, y) if t]
    neg = [s for s, t in zip(scores, y) if not t]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(pos) * len(neg))


def precision_recall_at(scores, y, tau):
    pred = [s >= tau for s in scores]
    tp = sum(1 for p, t in zip(pred, y) if p and t)
    fp = sum(1 for p, t in zip(pred, y) if p and not t)
    fn = sum(1 for p, t in zip(pred, y) if not p and t)
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    return prec, rec


def threshold_for_recall(scores, y, target=0.85):
    """The highest threshold whose recall is >= target (None when no positive exists); the miss rate 1 - recall there."""
    if not any(y):
        return None, None, None
    best = None
    for tau in sorted(set(scores), reverse=True):
        prec, rec = precision_recall_at(scores, y, tau)
        if rec is not None and rec >= target:
            best = (tau, prec, rec)
            break
    if best is None:
        tau = min(scores)
        prec, rec = precision_recall_at(scores, y, tau)
        best = (tau, prec, rec)
    return best[0], best[1], (1.0 - best[2]) if best[2] is not None else None


class _Model:
    """Standardised logistic regression (the features live on different scales: gains in [-0.1, 0.5], diff ratios in
    [0, 1], flip-flop deltas in the tens); coefficients are reported on the standardised features."""

    def __init__(self):
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler()
        self.lr = LogisticRegression(max_iter=5000, C=10.0)

    def fit(self, X, y):
        self.lr.fit(self.scaler.fit_transform(X), y)
        return self

    def predict_proba(self, X):
        return self.lr.predict_proba(self.scaler.transform(X))

    @property
    def coef_(self):
        return self.lr.coef_


def _fit(X, y):
    return _Model().fit(X, y)


def lodo(rows, class_blind=False, min_train=8):
    """Leave-one-design-out: for every design, fit on the other designs, score its objects. -> {scores by cand_id, auroc,
    tau_85, precision_at_85, miss_rate_at_85, n, n_pos, designs, feature_importance (coefficients of the model fitted on
    everything)}. Designs with fewer than `min_train` training rows or a single class in training are skipped."""
    rows = [r for r in rows if r.get("retained_e4") is not None and r.get("design_id")]
    designs = sorted({r["design_id"] for r in rows})
    scores, truth, skipped = {}, {}, []
    for d in designs:
        train = [r for r in rows if r["design_id"] != d]
        test = [r for r in rows if r["design_id"] == d]
        ytr = [int(r["retained_e4"]) for r in train]
        if len(train) < min_train or len(set(ytr)) < 2:
            skipped.append(d)
            continue
        m = _fit(featurize(train, class_blind), ytr)
        p = m.predict_proba(featurize(test, class_blind))[:, 1]
        for r, s in zip(test, p):
            scores[r["cand_id"]] = float(s)
            truth[r["cand_id"]] = int(r["retained_e4"])
    ids = sorted(scores)
    s = [scores[i] for i in ids]
    y = [truth[i] for i in ids]
    tau, prec, miss = threshold_for_recall(s, y, 0.85) if ids else (None, None, None)
    out = {"n": len(ids), "n_pos": int(sum(y)), "designs": designs, "skipped_designs": skipped, "class_blind": class_blind,
           "auroc": auroc(s, y) if ids else None, "tau_85": tau, "precision_at_85": prec, "miss_rate_at_85": miss, "scores": scores}
    yall = [int(r["retained_e4"]) for r in rows]
    if len(rows) >= min_train and len(set(yall)) == 2:
        m = _fit(featurize(rows, class_blind), yall)
        out["feature_importance"] = dict(zip(feature_names(class_blind), [float(c) for c in m.coef_[0]]))
    return out


def evaluate(rows):
    """Both models: with the class features and class-blind (spec 08 §2)."""
    return {"with_class": lodo(rows, class_blind=False), "class_blind": lodo(rows, class_blind=True)}
