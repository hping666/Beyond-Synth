"""Class bandit of residual-guided evolution (docs/spec/05-search.md §1, DECISIONS 2026-09-14 C2.1(c)): UCB-softmax over
the rewrite classes (`search.bandit.arms`), initialised from the map prior when one exists, credited only for retained or
trade-off improvements and always for the class the LLM actually produced (M6), never the requested one."""
import json
import math
import random


class ClassBandit:
    def __init__(self, arms, c_ucb=1.0, softmax_temp=0.5, prior=None):
        self.arms = list(arms)
        self.c = float(c_ucb)
        self.temp = float(softmax_temp)
        self.n = {a: 0 for a in self.arms}
        self.reward = {a: 0.0 for a in self.arms}
        # prior: {arm: retained probability from the map}; enters as pseudo-counts so that data can override it
        self.prior = {a: float((prior or {}).get(a, 0.0)) for a in self.arms}

    def value(self, arm):
        n = self.n[arm]
        mean = (self.reward[arm] + self.prior[arm]) / (n + 1)
        total = sum(self.n.values()) + len(self.arms)
        return mean + self.c * math.sqrt(math.log(total + 1) / (n + 1))

    def probs(self):
        vals = {a: self.value(a) / max(self.temp, 1e-9) for a in self.arms}
        mx = max(vals.values())
        w = {a: math.exp(v - mx) for a, v in vals.items()}
        z = sum(w.values())
        return {a: w[a] / z for a in self.arms}

    def draw(self, rng, k):
        p = self.probs()
        return rng.choices(self.arms, weights=[p[a] for a in self.arms], k=k)

    def credit(self, produced_class, reward):
        """Reward 0 / 1 booked on the produced class (unknown classes are ignored, e.g. a c2 rewrite outside the arms)."""
        if produced_class not in self.n:
            return False
        self.n[produced_class] += 1
        self.reward[produced_class] += float(reward)
        return True

    def to_json(self):
        return json.dumps({"arms": self.arms, "c": self.c, "temp": self.temp, "n": self.n, "reward": self.reward, "prior": self.prior}, sort_keys=True)

    @classmethod
    def from_json(cls, text):
        d = json.loads(text)
        b = cls(d["arms"], d["c"], d["temp"], d.get("prior"))
        b.n, b.reward = {a: int(v) for a, v in d["n"].items()}, {a: float(v) for a, v in d["reward"].items()}
        return b


def rng_for(run_id, gen, salt=""):
    return random.Random(f"{run_id}|{gen}|{salt}")
