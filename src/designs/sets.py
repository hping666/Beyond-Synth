"""Design-set assignment (docs/PLAN.md 1.4 / 1.5): the CktEvo set from the module pool, the dev / held split, and
the Sky130 subset. Pure functions here; scripts/phase1_sets.py applies them to the designs table, design.json tags
and config/experiments.yaml (rule 4: dev designs are the ones marked in the config)."""
import hashlib
import re


def repo_of(design):
    """cktevo design names are <repo>__<module>."""
    return design["name"].split("__", 1)[0]


def category_of(design):
    """RTLLM category = first path segment of the source path (Arithmetic / Memory / Control / Miscellaneous)."""
    paths = (design.get("source") or {}).get("paths") or []
    return paths[0].split("/")[0] if paths else "unknown"


def select_cktevo_set(designs, target_count, max_per_repo):
    """Round-robin over the repositories (alphabetical), each repository's eligible modules ordered by size
    (loc descending, then name), at most `max_per_repo` per repository, until `target_count` modules are chosen."""
    by_repo = {}
    for d in designs:
        by_repo.setdefault(repo_of(d), []).append(d)
    for lst in by_repo.values():
        lst.sort(key=lambda d: (-int(d.get("loc") or 0), d["name"]))
    chosen, taken = [], {r: 0 for r in by_repo}
    while len(chosen) < target_count:
        progressed = False
        for repo in sorted(by_repo):
            if len(chosen) >= target_count:
                break
            if taken[repo] < min(max_per_repo, len(by_repo[repo])):
                chosen.append(by_repo[repo][taken[repo]])
                taken[repo] += 1
                progressed = True
        if not progressed:
            break
    return chosen


def _rank(design_id, seed):
    return hashlib.sha256(f"{seed}:{design_id}".encode()).hexdigest()


def stratified_sample(designs, count, seed, key=category_of):
    """Deterministic stratified sample: per stratum (largest first) a share proportional to its size (largest
    remainders fill up), members ordered by a seeded hash of the design_id."""
    strata = {}
    for d in designs:
        strata.setdefault(key(d), []).append(d)
    if not designs or count <= 0:
        return []
    count = min(count, len(designs))
    shares = {s: len(m) * count / len(designs) for s, m in strata.items()}
    alloc = {s: int(v) for s, v in shares.items()}
    for s in sorted(shares, key=lambda s: (-(shares[s] - alloc[s]), s)):
        if sum(alloc.values()) >= count:
            break
        alloc[s] += 1
    out = []
    for s in sorted(strata):
        members = sorted(strata[s], key=lambda d: _rank(d["design_id"], seed))
        out.extend(members[:min(alloc[s], len(members))])
    return sorted(out, key=lambda d: d["design_id"])


def select_sky130_subset(designs, count):
    """One module per repository first (largest by loc), then second modules, until `count`."""
    return select_cktevo_set(designs, count, max_per_repo=max(1, count))


def set_yaml_list(text, suite, field, values):
    """Replace `field: <value>` inside the one-line flow mapping of `<suite>:` under design_sets.suites."""
    pat = re.compile(rf"^(\s*{re.escape(suite)}:\s*\{{.*?\b{re.escape(field)}:\s*)(\[[^\]]*\]|[^,}}]*)(.*)$", re.M)  # scalar or flow list
    m = pat.search(text)
    if not m:
        raise ValueError(f"field {field} of suite {suite} not found in the config text")
    rendered = "[" + ", ".join(values) + "]"
    return text[:m.start()] + m.group(1) + rendered + m.group(3) + text[m.end():]
