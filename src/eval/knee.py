"""Knee-point constraint rule (docs/spec/01-eval-service.md §3; parameters config: knee).

choose_knee(points, slack_tol, area_tol) -> (period_ns, fallback):
  candidate set = periods with WNS >= -slack_tol * T; among them the tightest T with
  area(T) <= (1 + area_tol) * area(T_loosest); empty candidate set -> the T with the smallest timing violation
  (largest TNS, i.e. closest to zero) and fallback=True.
points: iterable of dicts {T, area, wns, tns}; entries with missing wns/area are ignored.
"""


def choose_knee(points, slack_tol, area_tol):
    pts = [p for p in points if p.get("T") is not None and p.get("area") is not None and p.get("wns") is not None]
    if not pts:
        raise ValueError("no usable sweep points")
    loosest = max(pts, key=lambda p: p["T"])
    cands = [p for p in pts if p["wns"] >= -float(slack_tol) * p["T"]]
    if not cands:
        best = max(pts, key=lambda p: (p.get("tns") if p.get("tns") is not None else float("-inf"), p["T"]))
        return best["T"], True
    bound = (1.0 + float(area_tol)) * loosest["area"]
    ok = [p for p in cands if p["area"] <= bound]
    pick = min(ok or cands, key=lambda p: p["T"])
    return pick["T"], False
