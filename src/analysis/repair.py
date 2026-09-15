"""Repair yield per failure type (G5 decisions item 1, correctness aid (ii)): for every candidate issued as the repair of a
failed one (`candidates.repair_of`), the original's failure type (its verdict: rejected / sim_fail / falsified), whether the
repair was proven, and whether it was accepted; plus the failures that got no repair (budget exhausted, unusable answer,
or a repair's own failure). Read from the results database only."""
from collections import defaultdict


def repair_yield(conn, exp=None, run_ids=None, arm=None):
    """-> {"by_failure": {failure: {attempted, proven, accepted, retained, scope_violation}}, "unrepaired": {failure: n},
    "runs": n, "calls_repair": n}. `retained` counts diagnoses labelled retained or tradeoff (M-arm labels) and `improved`
    (scalar arms) as the arm's own notion of an accepted improvement is `accepted`."""
    where, args = [], []
    if exp:
        where.append("r.exp = ?")
        args.append(exp)
    if arm:
        where.append("r.arm = ?")
        args.append(arm)
    if run_ids:
        where.append("r.run_id IN (%s)" % ",".join("?" for _ in run_ids))
        args += list(run_ids)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(f"SELECT c.cand_id, c.run_id, c.repair_of, c.verdict, c.label, c.accepted FROM candidates c JOIN runs r ON r.run_id = c.run_id {w}", args).fetchall()
    by_id = {r[0]: r for r in rows}
    by_failure = defaultdict(lambda: {"attempted": 0, "proven": 0, "accepted": 0, "retained": 0, "scope_violation": 0})
    repaired = set()
    for cid, run_id, repair_of, verdict, label, accepted in rows:
        if not repair_of:
            continue
        orig = by_id.get(repair_of)
        failure = orig[3] if orig else "unknown"
        repaired.add(repair_of)
        b = by_failure[failure]
        b["attempted"] += 1
        if label == "scope_violation":
            b["scope_violation"] += 1
        if verdict == "proven":
            b["proven"] += 1
        if accepted:
            b["accepted"] += 1
        if label in ("retained", "tradeoff", "improved"):
            b["retained"] += 1
    unrepaired = defaultdict(int)
    for cid, run_id, repair_of, verdict, label, accepted in rows:
        if verdict in ("rejected", "sim_fail", "falsified") and cid not in repaired:
            unrepaired[verdict] += 1
    return {"by_failure": dict(by_failure), "unrepaired": dict(unrepaired), "runs": len({r[1] for r in rows}),
            "calls_repair": sum(v["attempted"] for v in by_failure.values())}


def repair_table(y):
    """Markdown rows: failure type | repairs | proven | accepted | retained or improved | scope violations | yield."""
    L = ["| failure type of the original | repair calls | proven | accepted | retained / improved | scope violations | proven per repair call | not repaired (budget / unusable / already a repair) |",
         "|---|---|---|---|---|---|---|---|"]
    for f in ("rejected", "sim_fail", "falsified"):
        b = y["by_failure"].get(f) or {"attempted": 0, "proven": 0, "accepted": 0, "retained": 0, "scope_violation": 0}
        rate = f"{100.0 * b['proven'] / b['attempted']:.0f} %" if b["attempted"] else "-"
        L.append(f"| {f} | {b['attempted']} | {b['proven']} | {b['accepted']} | {b['retained']} | {b['scope_violation']} | {rate} | {y['unrepaired'].get(f, 0)} |")
    return L
