"""Three-objective Pareto archive of residual-guided evolution (docs/spec/05-search.md §1): members are proven, E4-evaluated
candidates with a retained gain (gains relative to D: area, wns, power; larger is better). At most `search.archive_size`
members are kept by crowding distance; parents are drawn with probability proportional to crowding distance."""
import json
import math

OBJECTIVES = ("area", "wns", "power")


def dominates(a, b, eps=1e-12):
    """a dominates b: no objective worse, at least one better (missing objectives count as 0)."""
    ga, gb = a.get("gains") or {}, b.get("gains") or {}
    better = False
    for m in OBJECTIVES:
        x, y = float(ga.get(m) or 0.0), float(gb.get(m) or 0.0)
        if x < y - eps:
            return False
        if x > y + eps:
            better = True
    return better


def pareto_front(items):
    front = []
    for it in items:
        if any(dominates(o, it) for o in items if o is not it):
            continue
        if any(o["cand_id"] == it["cand_id"] for o in front):
            continue
        front.append(it)
    return front


def crowding_distance(front):
    """{cand_id: distance}; boundary members get infinity (kept first)."""
    n = len(front)
    dist = {it["cand_id"]: 0.0 for it in front}
    if n <= 2:
        return {k: math.inf for k in dist}
    for m in OBJECTIVES:
        order = sorted(front, key=lambda it: float((it.get("gains") or {}).get(m) or 0.0))
        lo, hi = float((order[0].get("gains") or {}).get(m) or 0.0), float((order[-1].get("gains") or {}).get(m) or 0.0)
        dist[order[0]["cand_id"]] = dist[order[-1]["cand_id"]] = math.inf
        span = hi - lo
        if span <= 0:
            continue
        for i in range(1, n - 1):
            prev_v = float((order[i - 1].get("gains") or {}).get(m) or 0.0)
            next_v = float((order[i + 1].get("gains") or {}).get(m) or 0.0)
            if not math.isinf(dist[order[i]["cand_id"]]):
                dist[order[i]["cand_id"]] += (next_v - prev_v) / span
    return dist


class Archive:
    def __init__(self, size):
        self.size = int(size)
        self.members = []   # dicts: cand_id, gains, gen, label

    def add(self, item):
        """Insert a retained candidate; keep the Pareto front truncated by crowding distance. -> True when it stays."""
        pool = [m for m in self.members if m["cand_id"] != item["cand_id"]] + [dict(item)]
        front = pareto_front(pool)
        if len(front) > self.size:
            dist = crowding_distance(front)
            front = sorted(front, key=lambda it: -dist[it["cand_id"]])[:self.size]
        self.members = front
        return any(m["cand_id"] == item["cand_id"] for m in self.members)

    def select_parent(self, rng):
        """A member drawn with probability proportional to its crowding distance (boundary members most often); None when empty."""
        if not self.members:
            return None
        dist = crowding_distance(self.members)
        weights = [1.0 if math.isinf(dist[m["cand_id"]]) else 0.25 + dist[m["cand_id"]] for m in self.members]
        return rng.choices(self.members, weights=weights, k=1)[0]

    def to_json(self):
        return json.dumps({"size": self.size, "members": self.members}, sort_keys=True)

    @classmethod
    def from_json(cls, text):
        d = json.loads(text) if text else {"size": 5, "members": []}
        a = cls(d.get("size", 5))
        a.members = list(d.get("members") or [])
        return a
