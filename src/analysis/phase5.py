"""Phase 5 visible-layer collector (PLAN 5, reports/phase5.md; staged reports A / B / C per tier, user decision 2026-09-16).

Reads the visible results database only (never the hidden one, rule 3). Every proven candidate with an E4 record is
re-labelled offline under the same rule-A diagnosis for every arm (`src/diagnose/m3.diagnose` with the design's frozen E4
floor): the uniform caliber of the comparison; arm M's stored labels (with the envelope runs) are reported alongside.
Stages: A = the large tier, B = large + medium, C = every tier (the full visible part); the hidden part comes from
scripts/report_hidden.py after the completion marker.
"""
import datetime
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from src import config as C
from src.diagnose import m3
from src.noise import stats as S
from src.search.driver import record_from_row

STAGES = {"A": ["large"], "B": ["large", "medium"], "C": ["large", "medium", "small"], "all": ["large", "medium", "small"]}
UNIFORM_LABELS = ("retained", "tradeoff", "noise", "harmful", "absorbed", "absorbed_identical", "duplicate", "fragile")


def tier_of_design(cfg):
    return {d: t for t, ds in (cfg["exp5"].get("starting_points") or {}).items() for d in ds}


def role_of(cfg, tier, model):
    ma = (cfg["exp5"].get("model_assignment") or {}).get(tier) or {}
    if ma.get("all_arms") == model:
        return "main"
    for role in ("second", "contrast"):
        if model in (ma.get(role) or {}):
            return role
    return "main" if model == cfg["llm"]["selected"] else "second"


def _q(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


class _Designs:
    """Per-design baseline record, floor thresholds and class, cached. basis: 'search' — the E4 baseline the running evaluators
    use (is_baseline = 1 at Φ_main, SAIF-backed record preferred); 'offline_saif' — REQUEST 2026-09-20 (e) item 2: the offline SAIF
    baseline of D (evaluations.offline_baseline = 1; is_baseline stays 0 so that no evaluator query can pick it up) when one exists,
    else the search baseline. Only the explicit recomputation reports pass 'offline_saif'; the stage reports keep the search basis."""
    def __init__(self, cfg, conn, basis="search", floor_version=None):
        """floor_version: a floor table to prefer per design (REQUEST 2026-09-20 (e) item 3: 'phase6' where measured), falling back to
        the frozen table of config noise.floor_version for the other designs; None = the frozen table only."""
        self.cfg, self.conn, self.cache, self.basis = cfg, conn, {}, basis
        self.floor_version = cfg["noise"].get("floor_version")
        self.prefer_floor_version = floor_version if floor_version and floor_version != self.floor_version else None
        self.k_sigma = float(cfg["noise"]["k_sigma"])

    def get(self, design_id):
        if design_id in self.cache:
            return self.cache[design_id]
        row = self.conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (design_id,)).fetchone()
        phi = float(row[0]) if row and row[0] is not None else None
        base = None
        if phi is not None:
            base = self.conn.execute("SELECT * FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' "
                                     "AND abs(clock_ns-?)<1e-6 ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (design_id, phi)).fetchone()
        basis = "search"
        if phi is not None and self.basis == "offline_saif":
            off = self.conn.execute("SELECT * FROM evaluations WHERE design_id=? AND config='E4' AND offline_baseline=1 AND is_baseline=0 AND pert_id IS NULL AND cand_id IS NULL "
                                    "AND status='ok' AND power_saif_mw IS NOT NULL AND abs(clock_ns-?)<1e-6 ORDER BY eval_id DESC LIMIT 1", (design_id, phi)).fetchone()
            if off is not None:
                base, basis = off, "offline_saif"
        floor, fv_used = {}, None
        if self.prefer_floor_version:
            floor = S.latest_floor(self.conn, design_id, "E4", self.prefer_floor_version)
            fv_used = self.prefer_floor_version if floor else None
        if not floor:
            floor = S.latest_floor(self.conn, design_id, "E4", self.floor_version) or S.latest_floor(self.conn, design_id, "E4")
            fv_used = self.floor_version if floor else None
        d = {"phi": phi, "base": record_from_row(base) if base is not None else None, "basis": basis, "base_eval_id": (base["eval_id"] if base is not None else None), "floor_version": fv_used,
             "thresholds": {"area": (floor.get("area") or {}).get("t_d"), "wns": (floor.get("wns") or {}).get("t_d"), "power": (floor.get("power_saif") or {}).get("t_d")},
             "sigma": {"area": (floor.get("area") or {}).get("sigma_robust") or 0.0, "wns": (floor.get("wns") or {}).get("sigma_robust") or 0.0, "power": (floor.get("power_saif") or {}).get("sigma_robust") or 0.0},
             "floor_class": next((r.get("floor_class") for r in floor.values() if r.get("floor_class")), None)}
        self.cache[design_id] = d
        return d


def uniform_diagnosis(designs, conn, cand):
    """The rule-A label of a proven candidate from its E4 record (offline, no tool runs) -> (label, gains, evidence) or None."""
    if cand["verdict"] != "proven":
        return None
    d = designs.get(cand["design_id"])
    if not d["base"] or d["phi"] is None:
        return None
    ev = conn.execute("SELECT * FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (cand["cand_id"],)).fetchone()
    if ev is None:
        return None
    out = m3.diagnose(d["base"], record_from_row(ev), d["sigma"], d["phi"], v3_status="proven", k_sigma=designs.k_sigma, thresholds=d["thresholds"], floor_class=d["floor_class"])
    label = out.get("label")
    if label == "retained" and out.get("envelope_required"):
        label = "retained"   # the envelope of the candidate's own perturbations is arm M's extra check; the uniform caliber stops at rule A
    return label, (out.get("evidence") or {}).get("gains") or {}, {"envelope_required": bool(out.get("envelope_required")), "dc_seconds": ev["dc_seconds"], "eval_created": ev["created_at"],
                                                                     "sublabel": out.get("sublabel")}


def has_e4(conn, cand_id):
    return conn.execute("SELECT 1 FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' LIMIT 1", (cand_id,)).fetchone() is not None


SIM_FAILED = ("compile_failed", "sim_fail", "mismatch", "error")


def pending_kind(c, e4_ok):
    """What a candidate still waits for (DECISION 2026-09-18 D1 / D2; 2026-09-19 (l) 2), or None when its evaluation is complete:
    'verdict' — no verdict yet (proof or simulation in flight); 'e4' — proven (or an offline-simulated prescreened
    candidate) without an E4 record; 'proof' — prescreened candidate whose offline simulation passed and whose proof has
    not been run (reported as pending until it is); 'sim' — prescreened candidate not yet simulated; 'failed_job' — a
    nonequiv label without a verdict, i.e. the evaluation job itself failed (the sim jobs of the 2026-09-18 10:41 operator
    edit): neither pending nor complete until re-run or recorded as an evaluation failure. `e4_ok` is a callable (the E4
    lookup is made only when it matters). Duplicates, identical-text candidates (never evaluated themselves), aborted rows
    and every failed verdict are complete."""
    lab, ver = c.get("label"), c.get("verdict")
    if lab in ("duplicate", "aborted", "absorbed_identical"):
        return None
    if ver == "proven":
        return None if (e4_ok() or c.get("e4_failure")) else "e4"   # DECISION 2026-09-19 (n) 1: a terminal DC rejection is resolved
    if ver in ("proven_sim_only", "sim_fail", "falsified", "rejected", "inconclusive", "error"):
        return None
    if lab == "prescreened":   # offline pool: sim -> E4; the proof stays pending (D2)
        if c.get("v1_status") in ("rejected", "error") or (c.get("v2_status") in SIM_FAILED):
            return None
        if c.get("v1_status") == "ok" and c.get("v2_status") and c.get("v2_status") not in SIM_FAILED:
            return "e4" if not e4_ok() else "proof"
        return "sim"
    if lab == "nonequiv":
        return "failed_job"
    return "verdict"


def pending_summary(cfg, conn, tiers, exp="phase5"):
    """Pending evaluations and open visible jobs of the runs on `tiers` (the completeness rule of DECISION 2026-09-18 D2 / D3: verdicts,
    offline simulations, E4 records including retries and B0's offline E4 hold a final report back; an offline-pool proof of a
    prescreened candidate is reported pending but does not): -> {"pending": {kind: n}, "pending_total": n, "blocking": {kind: n},
    "open_jobs": {kind: n}, "complete": bool}. Cheap enough for the stages loop."""
    tier_of = tier_of_design(cfg)
    designs = sorted(d for d, t in tier_of.items() if t in tiers)
    e4 = {r[0] for r in conn.execute("SELECT DISTINCT cand_id FROM evaluations WHERE config='E4' AND status='ok' AND cand_id IS NOT NULL")}
    pend = Counter()
    for c in conn.execute("SELECT c.cand_id, c.label, c.verdict, c.v1_status, c.v2_status, c.e4_failure FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          "WHERE r.exp=? AND r.status != 'superseded' AND COALESCE(r.excluded_from_tables, 0) = 0", (exp,)):
        c = dict(c)
        if tier_of.get(conn.execute("SELECT design_id FROM candidates WHERE cand_id=?", (c["cand_id"],)).fetchone()[0]) not in tiers:
            continue
        k = pending_kind(c, lambda: c["cand_id"] in e4)
        if k:
            pend[k] += 1
    open_jobs = Counter()
    if designs:
        marks = ",".join("?" * len(designs))
        for r in conn.execute(f"SELECT kind, COUNT(*) FROM jobs WHERE state IN ('queued', 'running') AND kind IN ('sim', 'vcf', 'dc', 'dc_retry', 'yosys', 'search') AND design_id IN ({marks}) GROUP BY kind", designs):
            open_jobs[r[0]] += r[1]
    blocking = {k: n for k, n in pend.items() if k != "proof"}   # DECISION 2026-09-18 (d) D3: a final report does not wait for any offline-pool proof
    return {"pending": dict(pend), "pending_total": sum(pend.values()), "blocking": blocking, "open_jobs": dict(open_jobs), "complete": not blocking and not open_jobs}


def complete_designs(cfg, conn, exp="phase5", plan=None):
    """DECISION 2026-09-18 (d) F2 and 2026-09-19 (l) items 2–3: the designs whose every planned arm-model row × seed is done (superseded
    and excluded rows aside) with no candidate pending a verdict, an offline simulation or an E4 record (B0's offline E4 included);
    an offline-pool proof of a prescreened candidate does not hold a design back (D3). "preliminary": every run done and the only
    blocker is B0's offline E4 (listed as B0 pending). "blockers" per design by kind: b0_e4 (B0's offline E4 in the pool), e4_retry
    (a non-B0 proven candidate whose E4 failed or timed out), e4_late (a non-B0 candidate proven after its run finished, without an
    E4 record), verdict, sim, failed_job, proof (offline proof, D3: does not block). -> {"complete": [...], "preliminary": [...],
    "rows": {design: {row: {"done", "planned", "pending"}}}, "blockers": {design: {kind: n}}, "runs_done": {design: bool}}."""
    tier_of = tier_of_design(cfg)
    if plan is None:
        import sys
        sys.path.insert(0, str(Path(C.ROOT) / "scripts"))
        import phase5_main as PM
        plan = PM.plan(cfg, conn)["runs"]
    planned = defaultdict(lambda: defaultdict(int))
    for pr in plan:
        planned[pr["design_id"]][f"{pr['model']}|{pr['arm']}"] += 1
    done = defaultdict(lambda: defaultdict(int))
    for r in conn.execute("SELECT design_id, llm_model, arm FROM runs WHERE exp=? AND status='done' AND COALESCE(excluded_from_tables, 0) = 0", (exp,)):
        done[r["design_id"]][f"{r['llm_model']}|{r['arm']}"] += 1
    e4 = {r[0] for r in conn.execute("SELECT DISTINCT cand_id FROM evaluations WHERE config='E4' AND status='ok' AND cand_id IS NOT NULL")}
    e4_failed = {r[0] for r in conn.execute("SELECT DISTINCT cand_id FROM evaluations WHERE config='E4' AND status != 'ok' AND cand_id IS NOT NULL")}
    e4_exhausted = {r[0] for r in conn.execute("SELECT cand_id FROM evaluations WHERE config='E4' AND status != 'ok' AND cand_id IS NOT NULL GROUP BY cand_id HAVING COUNT(*) >= 3")}   # (n) 1: the pool stops after three attempts
    pending = defaultdict(lambda: defaultdict(int))
    blockers = defaultdict(Counter)
    for c in conn.execute("SELECT c.cand_id, c.design_id, c.label, c.verdict, c.v1_status, c.v2_status, c.e4_failure, r.llm_model, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                          "WHERE r.exp=? AND r.status != 'superseded' AND COALESCE(r.excluded_from_tables, 0) = 0", (exp,)):
        c = dict(c)
        k = pending_kind(c, lambda: c["cand_id"] in e4)
        if not k:
            continue
        kind = k if k != "e4" else ("b0_e4" if c["arm"] == "B0" else ("e4_exhausted" if c["cand_id"] in e4_exhausted else "e4_retry" if c["cand_id"] in e4_failed else "e4_late"))
        blockers[c["design_id"]][kind] += 1
        if k != "proof":
            pending[c["design_id"]][f"{c['llm_model']}|{c['arm']}"] += 1
    out = {"complete": [], "preliminary": [], "rows": {}, "blockers": {}, "runs_done": {}}
    for d in sorted(planned):
        rows = {}
        ok = runs_ok = True
        for row, n in planned[d].items():
            rows[row] = {"done": done[d].get(row, 0), "planned": n, "pending": pending[d].get(row, 0)}
            if rows[row]["done"] < n:
                runs_ok = ok = False
            if rows[row]["pending"]:
                ok = False
        out["rows"][d] = rows
        out["blockers"][d] = dict(blockers.get(d) or {})
        out["runs_done"][d] = runs_ok
        if ok:
            out["complete"].append(d)
        elif runs_ok and {k for k in blockers[d] if k != "proof"} == {"b0_e4"}:
            out["preliminary"].append(d)
    return out


def design_arm_comparison(cfg, conn, designs_cache, design_id, exp="phase5"):
    """F2: the arm comparison of one design (uniform rule A): per arm-model row the runs, proven, retained, tradeoff, the best retained
    area gain per run (mean over seeds) and the best over the design; the design's rule-A area floor (t_d)."""
    d = designs_cache.get(design_id)
    rows = defaultdict(lambda: {"runs": 0, "cands": 0, "proven": 0, "retained": 0, "tradeoff": 0, "best_runs": []})
    for r in conn.execute("SELECT run_id, llm_model, arm FROM runs WHERE exp=? AND design_id=? AND status='done' AND COALESCE(excluded_from_tables, 0) = 0", (exp, design_id)):
        g = rows[f"{r['llm_model']}|{r['arm']}"]
        g["runs"] += 1
        best = 0.0
        for c in conn.execute("SELECT * FROM candidates WHERE run_id=?", (r["run_id"],)):
            c = dict(c)
            if c.get("label") in ("duplicate", "aborted"):
                continue
            g["cands"] += 1
            if c.get("verdict") == "proven":
                g["proven"] += 1
                ud = uniform_diagnosis(designs_cache, conn, c)
                if ud:
                    lab, gains, _ = ud
                    if lab == "retained":
                        g["retained"] += 1
                        best = max(best, float(gains.get("area") or 0.0))
                    elif lab == "tradeoff":
                        g["tradeoff"] += 1
        g["best_runs"].append(best)
    out = {}
    for k, g in rows.items():
        out[k] = {"runs": g["runs"], "cands": g["cands"], "proven": g["proven"], "retained": g["retained"], "tradeoff": g["tradeoff"],
                  "best_gain_mean": round(statistics.mean(g["best_runs"]), 5) if g["best_runs"] else None, "best_gain_max": round(max(g["best_runs"]), 5) if g["best_runs"] else None}
    return {"rows": out, "t_d_area": (d or {}).get("thresholds", {}).get("area") if d else None}


def m_outcome(comparison, model):
    """DECISION 2026-09-19 (m) item 4 and (n) item 2 (the F2 tally categories under `model`): 'win' — M's mean best retained area gain
    exceeds both B1_E4's and B2's by more than the design's rule-A area floor (t_d); 'loss' — worse than either by more than the floor;
    'partial' — separated from exactly one baseline by more than the floor and within the floor of the other; 'tie' — within the
    floor of both; None when a row is missing."""
    rows = comparison["rows"]
    m, b1, b2 = rows.get(f"{model}|M"), rows.get(f"{model}|B1_E4"), rows.get(f"{model}|B2")
    if not (m and b1 and b2) or m["best_gain_mean"] is None:
        return None
    t = float(comparison.get("t_d_area") or 0.0)
    d1, d2 = m["best_gain_mean"] - (b1["best_gain_mean"] or 0.0), m["best_gain_mean"] - (b2["best_gain_mean"] or 0.0)
    if d1 < -t or d2 < -t:
        return "loss"
    if d1 > t and d2 > t:
        return "win"
    if d1 > t or d2 > t:
        return "partial"
    return "tie"


def m_exceeds(comparison, model):
    """F2 tally rule (kept for the callers): True when M wins, False otherwise, None when a row is missing (see m_outcome)."""
    o = m_outcome(comparison, model)
    return None if o is None else o == "win"


def dc_rejected(conn, cfg, exp="phase5"):
    """DECISION 2026-09-19 (n) item 1: the candidates whose E4 failed terminally (candidates.e4_failure, e.g. "DC rejected (ELAB-366)"),
    per design -> {design_id: [(cand_id, arm, text)]} over the non-superseded runs."""
    out = {}
    for r in conn.execute("SELECT c.design_id, c.cand_id, r.arm, c.e4_failure FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp=? AND r.status != 'superseded' "
                          "AND c.e4_failure IS NOT NULL ORDER BY c.design_id, r.arm, c.cand_id", (exp,)):
        out.setdefault(r[0], []).append((r[1], r[2], r[3]))
    return out


def completion_view(cfg, conn, exp="phase5"):
    """F2 / F3 data (and DECISION 2026-09-19 (l) items 2–3): the complete designs and the B0-pending ones with their arm comparisons
    and the M tally (both counted), the reachability of the pre-registered criterion (18 of 30 under the hidden configurations —
    read here as the visible-layer proxy, the hidden form stays sealed), the per-row completion counts, the blockers and the open
    proofs of every design."""
    cd = complete_designs(cfg, conn, exp)
    tier_of = tier_of_design(cfg)
    designs = _Designs(cfg, conn)
    main_model = {t: (m.get("all_arms") or cfg["llm"]["selected"]) for t, m in ((cfg["exp5"].get("model_assignment") or {}).items())}
    comps, tally = {}, {"wins": [], "ties": [], "partials": [], "losses": [], "undecided": []}
    for d in cd["complete"] + cd["preliminary"]:
        comp = design_arm_comparison(cfg, conn, designs, d, exp)
        model = main_model.get(tier_of.get(d), cfg["llm"]["selected"])
        outcome = m_outcome(comp, model)   # DECISION 2026-09-19 (m) 4: win / tie / loss
        comp["model"], comp["m_outcome"], comp["m_exceeds"], comp["b0_pending"] = model, outcome, (None if outcome is None else outcome == "win"), d in cd["preliminary"]
        comps[d] = comp
        {"win": tally["wins"], "tie": tally["ties"], "partial": tally["partials"], "loss": tally["losses"], None: tally["undecided"]}[outcome].append(d)
    total = sum(len(v) for v in (cfg["exp5"].get("starting_points") or {}).values())
    need = int(cfg["exp5"].get("criterion_wins", 18))
    counted = len(cd["complete"]) + len(cd["preliminary"])
    remaining = total - counted
    reach = {"total_designs": total, "criterion_wins": need, "wins": len(tally["wins"]), "ties": len(tally["ties"]), "partial": len(tally["partials"]), "lost": len(tally["losses"]), "undecided": len(tally["undecided"]),
             "remaining_designs": remaining, "wins_still_needed": max(0, need - len(tally["wins"])), "reachable": (len(tally["wins"]) + remaining + len(tally["undecided"])) >= need,
             "preliminary": len(cd["preliminary"])}
    open_proofs = {r[0]: r[1] for r in conn.execute("SELECT design_id, COUNT(*) FROM jobs WHERE kind='vcf' AND state IN ('queued', 'running', 'held') GROUP BY design_id")}
    return {"complete": cd["complete"], "preliminary": cd["preliminary"], "rows": cd["rows"], "blockers": cd["blockers"], "runs_done": cd["runs_done"],
            "open_proofs": open_proofs, "comparisons": comps, "tally": tally, "reachability": reach}


def completion_alert(cfg, conn, state_path=None, write=True, view=None, exp="phase5"):
    """DECISION 2026-09-18 (d) F3 and 2026-09-19 (l) 3: compare the complete and the B0-pending design sets with the last recorded ones
    (reports/data/phase5_complete_designs.json); -> (new designs, alert line or None, view). A design is announced when it becomes
    B0 pending and again when it moves to the full table. With `write`, the state file is updated and the line appended to STATUS.md."""
    view = view or completion_view(cfg, conn, exp)
    state_path = Path(state_path or (Path(C.ROOT) / "reports" / "data" / "phase5_complete_designs.json"))
    try:
        prev = json.loads(state_path.read_text())
    except (OSError, ValueError):
        prev = {"designs": [], "history": []}
    prev_c, prev_p = set(prev.get("designs") or []), set(prev.get("preliminary") or [])
    new = [d for d in view["complete"] if d not in prev_c]
    new_p = [d for d in view.get("preliminary") or [] if d not in prev_p and d not in prev_c]
    now = datetime.datetime.now().isoformat(timespec="minutes")
    line = None
    if new or new_p:
        r = view["reachability"]
        wins = [d for d in new + new_p if d in view["tally"]["wins"]]
        ties = [d for d in new + new_p if d in view["tally"].get("ties", [])]
        partials = [d for d in new + new_p if d in view["tally"].get("partials", [])]
        n_all = len(view["complete"]) + len(view.get("preliminary") or [])
        line = (f"New complete designs since last render ({now}): " + (", ".join(new) or "none")
                + (f"; B0 pending (complete except for B0's offline E4, DECISION 2026-09-19 (l) 3): {', '.join(new_p)}" if new_p else "")
                + f" — M wins (exceeds both B1_E4 and B2 by more than the floor) on {len(wins)} of them, ties on {len(ties)}, partial on {len(partials)}; "
                f"tally {r['wins']} wins, {r.get('ties', 0)} ties, {r.get('partial', 0)} partial, {r['lost']} losses of {n_all} complete designs (visible layer" + (f"; {len(view['preliminary'])} of them B0 pending" if view.get("preliminary") else "") + f"), "
                f"{r['wins_still_needed']} wins still needed of {r['remaining_designs'] + r['undecided']} remaining / undecided"
                + ("" if r["reachable"] else " — the 18-of-30 criterion is no longer reachable in the visible layer") + ".")
    if write and (new or new_p):
        state = {"designs": list(view["complete"]), "preliminary": list(view.get("preliminary") or []), "at": now,
                 "history": (prev.get("history") or []) + [{"at": now, "new": new, "new_preliminary": new_p}]}
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=1))
        status = Path(C.ROOT) / "STATUS.md"
        if status.exists():
            status.write_text(status.read_text().rstrip("\n") + "\n\n- " + line + "\n")
    return new + new_p, line, view


def verification_conditions(cfg, conn, exp="phase5", tiers=None, threshold=100.0, window_s=120):
    """DECISION 2026-09-18 (h) item 1 — the standing table for the paper: per design and class, the inconclusive share of the
    finished proofs (proven or inconclusive) whose 1-minute host load at the proof's start was above `threshold` and at or below it
    (the load from scripts/load_logger.py's log, the sample nearest before the start within `window_s`; proofs started before the log
    began are left out). -> {"threshold": t, "rows": {design: {class: {"above": [proven, inconclusive], "below": [proven, inconclusive]}}}, "from": first sample, "n": counted}."""
    import bisect
    tier_of = tier_of_design(cfg)
    tiers = list(tiers or STAGES["all"])
    samples = load_samples(cfg)
    ts = [s[0] for s in samples]
    rows = defaultdict(lambda: defaultdict(lambda: {"above": [0, 0], "below": [0, 0]}))
    n = 0
    for r in conn.execute("SELECT c.design_id, c.class_final, c.verdict, j.started_at FROM candidates c JOIN jobs j ON j.cand_id=c.cand_id JOIN runs ru ON ru.run_id=c.run_id "
                          "WHERE ru.exp=? AND ru.status != 'superseded' AND j.kind='vcf' AND j.state='done' AND j.started_at IS NOT NULL AND c.verdict IN ('proven', 'inconclusive')", (exp,)):
        if tier_of.get(r["design_id"]) not in tiers or not samples:
            continue
        i = bisect.bisect_right(ts, r["started_at"]) - 1
        if i < 0:
            continue
        try:
            gap = (datetime.datetime.fromisoformat(r["started_at"]) - datetime.datetime.fromisoformat(ts[i])).total_seconds()
        except ValueError:
            continue
        if gap > window_s:
            continue
        side = "above" if samples[i][1] > threshold else "below"
        rows[r["design_id"]][r["class_final"] or "?"][side][0 if r["verdict"] == "proven" else 1] += 1
        n += 1
    return {"threshold": threshold, "from": ts[0] if ts else None, "n": n, "rows": {d: {k: v for k, v in cls.items()} for d, cls in rows.items()}}


def load_samples(cfg):
    """(timestamp, 1-minute load) samples of scripts/load_logger.py (results/queue/load.log), sorted; empty when absent."""
    p = Path(C.results_dir(cfg)) / "queue" / "load.log"
    out = []
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                out.append((parts[0], float(parts[1])))
            except ValueError:
                pass
    return sorted(out)


def row_conditions(conn, run_ids, spans, samples):
    """Verification conditions of one arm-model row (DECISION 2026-09-18 item 5c): the VC Formal queue wait of the row's
    proofs (submitted -> started, minutes; median / q95 / n) and the median 1-minute host load over the row's run spans
    (load.log samples inside [first candidate, finish]); `coverage` = the share of the spans' minutes with a sample."""
    waits = []
    if run_ids:
        marks = ",".join("?" * len(run_ids))
        for r in conn.execute(f"SELECT j.submitted_at, j.started_at FROM jobs j JOIN candidates c ON c.cand_id=j.cand_id WHERE c.run_id IN ({marks}) AND j.kind='vcf' AND j.started_at IS NOT NULL AND j.submitted_at IS NOT NULL", run_ids):
            try:
                waits.append((datetime.datetime.fromisoformat(r[1]) - datetime.datetime.fromisoformat(r[0])).total_seconds() / 60.0)
            except ValueError:
                pass
    loads, minutes = [], 0.0
    for a, b in spans:
        if not a:
            continue
        b = b or datetime.datetime.now().isoformat(timespec="seconds")
        loads += [v for ts, v in samples if a <= ts <= b]
        try:
            minutes += max(0.0, (datetime.datetime.fromisoformat(b) - datetime.datetime.fromisoformat(a)).total_seconds() / 60.0)
        except ValueError:
            pass
    return {"vcf_wait_median_min": round(statistics.median(waits), 1) if waits else None, "vcf_wait_q95_min": round(_q(waits, 0.95), 1) if waits else None, "proofs": len(waits),
            "load_median": round(statistics.median(loads), 1) if loads else None, "load_samples": len(loads),
            "load_coverage": round(min(1.0, len(loads) / max(minutes, 1.0)), 3) if (minutes or loads) else None}   # one sample per minute: a span under a minute with a sample is covered


def run_dc_hours(conn, run_id):
    """Visible DC seconds of a run's evaluations (fitness and envelope records of its candidates) -> hours."""
    s = conn.execute("SELECT COALESCE(SUM(e.dc_seconds),0) FROM evaluations e WHERE e.status='ok' AND e.cand_id IN (SELECT cand_id FROM candidates WHERE run_id=?)", (run_id,)).fetchone()[0]
    env = conn.execute("SELECT COALESCE(SUM(e.dc_seconds),0) FROM evaluations e JOIN candidates c ON e.cand_id LIKE c.cand_id || '_env%' WHERE c.run_id=? AND e.status='ok'", (run_id,)).fetchone()[0]
    return (float(s) + float(env)) / 3600.0


def collect(cfg, conn, exp="phase5", tiers=None, results_dir=None):
    """-> the visible-layer data of the runs of `exp` on the given tiers (default every tier)."""
    tiers = list(tiers or STAGES["all"])
    tier_of = tier_of_design(cfg)
    designs = _Designs(cfg, conn)
    root = Path(results_dir or C.results_dir(cfg)) / "candidates"
    calls_per_run = int(cfg["scale"]["budget"]["llm_calls_per_run"])
    runs = []
    for r in conn.execute("SELECT * FROM runs WHERE exp=? AND status != 'superseded' ORDER BY created_at", (exp,)):
        r = dict(r)
        t = tier_of.get(r["design_id"])
        if t not in tiers or int(r.get("excluded_from_tables") or 0):   # DECISION 2026-09-18 (b) item 1c: a run kept as a record but replaced (prescreen on) stays out of the tables
            continue
        r["tier"], r["role"] = t, role_of(cfg, t, r["llm_model"])
        runs.append(r)
    out = {"generated_at": datetime.datetime.now().isoformat(timespec="minutes"), "exp": exp, "tiers": tiers, "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(),
           "equiv_version": (cfg.get("equiv") or {}).get("version"), "floor_version": cfg["noise"].get("floor_version"),
           "planned": {}, "runs": [], "groups": {}, "designs": {}, "curves": {}, "correctness": {}, "classes": {}, "ttv": {}, "unfinished_note": None,
           "retained_list": [], "inconclusive": {}, "conditions": {}, "pending_total": {}}
    # ---- planned counts per tier (from the plan) for the progress lines
    try:
        import sys
        sys.path.insert(0, str(Path(C.ROOT) / "scripts"))
        import phase5_main as PM
        for pr in PM.plan(cfg, conn)["runs"]:
            k = f"{pr['tier']}|{pr['model']}|{pr['arm']}"
            out["planned"][k] = out["planned"].get(k, 0) + 1
    except Exception as e:   # the plan is only used for "done of planned"
        out["planned_error"] = f"{type(e).__name__}: {e}"[:120]
    groups = defaultdict(lambda: {"runs": 0, "done": 0, "calls": 0, "usd": 0.0, "dc_h": 0.0, "vcf_h": 0.0, "cands": 0, "unusable": 0, "duplicate": 0, "prescreened": 0,
                                  "proven": 0, "proven_sim_only": 0, "sim_fail": 0, "falsified": 0, "rejected": 0, "inconclusive": 0, "error": 0, "pending": 0,
                                  "accepted": 0, "scope_flags": 0, "block_answers": 0, "block_flags": 0, "repairs": 0, "repairs_proven": 0,
                                  "uniform": Counter(), "stored": Counter(), "retained_runs": 0, "best_gain_runs": [], "gains_retained": [], "ttv": [], "classes": Counter(), "confusion": Counter(),
                                  "latency_mapped": 0, "pending_by": Counter(), "run_ids": [], "spans": [], "synth_rejected": Counter()})
    by_design = defaultdict(lambda: {"best": None, "runs": 0, "retained": 0, "pending": 0})
    inconclusive = {"by_class": Counter(), "by_design": Counter()}
    correctness = defaultdict(lambda: {"cands": 0, "proven": 0, "runs": 0, "synth_rejected": 0})
    curves_calls = defaultdict(list)     # (tier|model|arm) -> per run: list of best-so-far retained area gain by call index
    curves_dc = defaultdict(list)        # (tier|model|arm) -> per run: [(cum dc hours, best so far)]
    for r in runs:
        key = f"{r['tier']}|{r['llm_model']}|{r['arm']}"
        g = groups[key]
        g["runs"] += 1
        g["done"] += int(r["status"] == "done")
        g["calls"] += int(r["llm_calls"] or 0)
        g["usd"] += float(r["spent_usd"] or 0.0)
        cands = [dict(c) for c in conn.execute("SELECT * FROM candidates WHERE run_id=? ORDER BY created_at, cand_id", (r["run_id"],))]
        usd_c = sum(float(c.get("cost_usd") or 0.0) for c in cands)
        if r["status"] != "done" and usd_c > float(r["spent_usd"] or 0.0):
            g["usd"] += usd_c - float(r["spent_usd"] or 0.0)   # a running run's spend lives in its candidate rows until the run closes
        dc_h = run_dc_hours(conn, r["run_id"])
        vcf_h = float(r["spent_vcf_hours"] or 0.0) or sum(float(c.get("v3_seconds") or 0.0) for c in cands) / 3600.0
        g["dc_h"] += dc_h
        g["vcf_h"] += vcf_h
        rdir = root / r["run_id"]
        unusable = len(list(rdir.glob("unusable_*.json"))) if rdir.exists() else 0
        g["unusable"] += unusable
        best_run, seq_calls, seq_dc, cum_dc = 0.0, [], [], 0.0
        for c in cands:
            g["cands"] += 1
            lab, ver = c.get("label"), c.get("verdict")
            cd = correctness[f"{r['tier']}|{r['llm_model']}|{r['design_id']}"]
            cd["cands"] += 1
            cd["proven"] += int(ver == "proven")
            if c.get("e4_failure"):   # DECISION 2026-09-19 (o) 2: formal-accepted, synthesis-rejected (terminal DC rejection, (n) 1), with the DC error id
                rid = re.sub(r"^.*\(([A-Z]+-\d+)\).*$", r"\1", str(c["e4_failure"]))
                g["synth_rejected"][f"{r['design_id']}|{rid}"] += 1
                cd["synth_rejected"] += 1
            if lab == "duplicate":   # the same RTL again: a spent call, no verdict, no class of its own
                g["duplicate"] += 1
                seq_calls.append(best_run)
                seq_dc.append((round(cum_dc, 3), best_run))
                continue
            if lab == "prescreened":
                g["prescreened"] += 1
            if ver == "proven":
                g["proven"] += 1
                try:
                    offs = json.loads(c.get("latency_offset_json") or "{}") or {}
                except (ValueError, TypeError):
                    offs = {}
                if isinstance(offs, dict) and any((v or 0) != 0 for v in offs.values()):
                    g["latency_mapped"] += 1   # proven through the SEQ latency mapping (class c2): a non-zero constant output offset
            elif ver == "proven_sim_only":
                g["proven_sim_only"] += 1
            elif ver in ("sim_fail", "falsified", "rejected", "inconclusive", "error"):
                g[ver] += 1
                if ver == "inconclusive":
                    inconclusive["by_class"][f"{r['tier']}|{c.get('class_final') or '?'}"] += 1
                    inconclusive["by_design"][f"{r['tier']}|{r['design_id']}"] += 1
            pk = pending_kind(c, lambda: has_e4(conn, c["cand_id"]))   # DECISION 2026-09-18 D1 / D2: what the candidate still waits for
            if pk:
                g["pending"] += 1
                g["pending_by"][pk] += 1
                by_design[f"{r['tier']}|{r['llm_model']}|{r['arm']}|{r['design_id']}"]["pending"] += 1
            g["accepted"] += int(bool(c.get("accepted")))
            if c.get("repair_of"):
                g["repairs"] += 1
                g["repairs_proven"] += int(ver == "proven")
            sj = c.get("scope_json")
            if sj:
                try:
                    sjd = json.loads(sj)
                except (ValueError, TypeError):
                    sjd = {}
                flagged = bool(sjd.get("violations"))
                g["scope_flags"] += int(flagged)
                if (sjd.get("region") or {}).get("kind") == "blocks":
                    g["block_answers"] += 1
                    g["block_flags"] += int(flagged)
            if c.get("class_final"):
                g["classes"][c["class_final"]] += 1
                if c.get("class_requested"):
                    g["confusion"][f"{c['class_requested']}->{c['class_final']}"] += 1
            if c.get("time_to_verdict_s") is not None:
                g["ttv"].append(float(c["time_to_verdict_s"]))
            if lab in ("retained", "tradeoff", "noise", "harmful", "absorbed", "absorbed_identical", "fragile", "improved", "no_gain", "nonequiv"):
                g["stored"][lab] += 1
            ud = uniform_diagnosis(designs, conn, c) if ver == "proven" else None
            gain_area = None
            if ud:
                ulabel, gains, extra = ud
                g["uniform"][ulabel] += 1
                if ulabel in ("retained", "tradeoff"):
                    try:
                        subtags = json.loads(c.get("subtags_json") or "[]")
                    except (ValueError, TypeError):
                        subtags = []
                    out["retained_list"].append({"tier": r["tier"], "model": r["llm_model"], "arm": r["arm"], "design_id": r["design_id"], "run_id": r["run_id"], "cand_id": c["cand_id"],
                                                 "label": ulabel, "class_final": c.get("class_final"), "subtags": subtags if isinstance(subtags, list) else [], "gains": {m: round(float(v), 5) for m, v in gains.items()},
                                                 "sublabel": extra.get("sublabel"), "stored_label": lab})
                    gain_area = float(gains.get("area") or 0.0)
                    if ulabel == "retained":
                        g["gains_retained"].append(gain_area)
                        by_design[f"{r['tier']}|{r['llm_model']}|{r['arm']}|{r['design_id']}"]["retained"] += 1
                        if gain_area > best_run:
                            best_run = gain_area
                if extra.get("dc_seconds"):
                    cum_dc += float(extra["dc_seconds"]) / 3600.0
            seq_calls.append(best_run)
            seq_dc.append((round(cum_dc, 3), best_run))
        g["best_gain_runs"].append(best_run)
        g["retained_runs"] += int(best_run > 0)
        g["run_ids"].append(r["run_id"])
        g["spans"].append((cands[0]["created_at"] if cands else r["started_at"], r["finished_at"] if r["status"] == "done" else None))
        bd = by_design[f"{r['tier']}|{r['llm_model']}|{r['arm']}|{r['design_id']}"]
        bd["runs"] += 1
        bd["best"] = best_run if bd["best"] is None else max(bd["best"], best_run)
        correctness[f"{r['tier']}|{r['llm_model']}|{r['design_id']}"]["runs"] += 1
        curves_calls[key].append(seq_calls)
        curves_dc[key].append(seq_dc)
        out["runs"].append({"run_id": r["run_id"], "tier": r["tier"], "role": r["role"], "model": r["llm_model"], "arm": r["arm"], "design_id": r["design_id"], "seed": r["seed"],
                            "status": r["status"], "calls": int(r["llm_calls"] or 0), "gens": int(r["gens_done"] or 0), "usd": round(float(r["spent_usd"] or 0.0) or usd_c, 4),
                            "dc_h": round(dc_h, 3), "vcf_h": round(vcf_h, 3), "cands": len(cands), "unusable": unusable, "best_retained_area_gain": round(best_run, 5)})
    # ---- aggregate the groups
    samples = load_samples(cfg)
    for key, g in groups.items():
        tier, model, arm = key.split("|")
        planned = out["planned"].get(key)
        n = g["runs"]
        ret = sum(v for k, v in g["uniform"].items() if k == "retained")
        gr = g["gains_retained"]
        out["groups"][key] = {
            "tier": tier, "model": model, "arm": arm, "role": role_of(cfg, tier, model), "planned": planned, "runs": n, "done": g["done"],
            "calls": g["calls"], "usd": round(g["usd"], 2), "dc_h": round(g["dc_h"], 2), "vcf_h": round(g["vcf_h"], 2),
            "cands": g["cands"], "unusable": g["unusable"], "duplicate": g["duplicate"], "prescreened": g["prescreened"], "pending": g["pending"],
            "proven": g["proven"], "proven_sim_only": g["proven_sim_only"], "latency_mapped": g["latency_mapped"], "sim_fail": g["sim_fail"], "falsified": g["falsified"], "rejected": g["rejected"],
            "inconclusive": g["inconclusive"], "error": g["error"], "accepted": g["accepted"],
            "proven_per_call": round(g["proven"] / g["calls"], 4) if g["calls"] else None,
            "uniform": dict(g["uniform"]), "stored": dict(g["stored"]),
            "retained": ret, "retained_per_run": round(ret / n, 3) if n else None, "runs_with_retained": g["retained_runs"],
            "retained_per_100_calls": round(100.0 * ret / g["calls"], 3) if g["calls"] else None,
            "retained_per_usd": round(ret / g["usd"], 3) if g["usd"] else None, "retained_per_dc_hour": round(ret / g["dc_h"], 3) if g["dc_h"] else None,
            "best_gain_mean": round(statistics.mean(g["best_gain_runs"]), 5) if g["best_gain_runs"] else None,
            "best_gain_median": round(statistics.median(g["best_gain_runs"]), 5) if g["best_gain_runs"] else None,
            "gain_retained_median": round(statistics.median(gr), 5) if gr else None, "gain_retained_max": round(max(gr), 5) if gr else None,
            "scope_flags": g["scope_flags"], "block_answers": g["block_answers"], "block_flags": g["block_flags"],
            "block_flag_rate": round(g["block_flags"] / g["block_answers"], 4) if g["block_answers"] else None,
            "repairs": g["repairs"], "repairs_proven": g["repairs_proven"],
            "classes": dict(g["classes"]), "confusion": dict(g["confusion"]),
            "ttv": {"n": len(g["ttv"]), "median": round(statistics.median(g["ttv"]), 1) if g["ttv"] else None, "q95": round(_q(g["ttv"], 0.95), 1) if g["ttv"] else None},
            "pending_by": dict(g["pending_by"]), "synth_rejected": dict(g["synth_rejected"]), "incomplete": bool(g["pending"] or g["done"] < n or (planned is not None and n < planned)),
        }
        out["conditions"][key] = row_conditions(conn, g["run_ids"], g["spans"], samples)
    out["designs"] = {k: {"best_retained_area_gain": (None if v["best"] is None else round(v["best"], 5)), "runs": v["runs"], "retained": v["retained"], "pending": v["pending"]} for k, v in by_design.items()}
    out["inconclusive"] = {"by_class": dict(inconclusive["by_class"]), "by_design": dict(inconclusive["by_design"])}
    for tier in tiers:
        out["pending_total"][tier] = sum(g["pending"] for k, g in out["groups"].items() if k.startswith(tier + "|"))
    out["correctness"] = {k: {**v, "proven_rate": round(v["proven"] / v["cands"], 4) if v["cands"] else None} for k, v in correctness.items()}
    # ---- curves: best-so-far retained area gain averaged over the runs of a group, by call index (equal-call caliber) and by DC hours
    grid_calls = list(range(5, calls_per_run + 1, 5))
    for key, seqs in curves_calls.items():
        pts = []
        for x in grid_calls:
            vals = [(s[x - 1] if len(s) >= x else (s[-1] if s else 0.0)) for s in seqs]
            pts.append({"calls": x, "mean_best_gain": round(statistics.mean(vals), 5) if vals else None, "runs_with_retained": sum(1 for v in vals if v > 0)})
        out["curves"].setdefault(key, {})["by_calls"] = pts
    for key, seqs in curves_dc.items():
        maxh = max((s[-1][0] for s in seqs if s), default=0.0)
        grid = [round(x * 0.25, 2) for x in range(1, int(maxh / 0.25) + 2)] if maxh > 0 else []
        pts = []
        for h in grid:
            vals = []
            for s in seqs:
                best = 0.0
                for cum, b in s:
                    if cum <= h:
                        best = b
                    else:
                        break
                vals.append(best)
            pts.append({"dc_hours": h, "mean_best_gain": round(statistics.mean(vals), 5) if vals else None})
        out["curves"].setdefault(key, {})["by_dc_hours"] = pts
    out["ops"] = operations(cfg, conn, exp, results_dir)   # user follow-up 2026-09-16 (items 1 and 5)
    out["verification_conditions"] = verification_conditions(cfg, conn, exp, tiers)   # DECISION 2026-09-18 (h) item 1
    return out


def stage_tiers(stage):
    return STAGES[stage]


# ----------------------------------------------------------------------------- operational changes of 2026-09-16 (DECISIONS; user follow-up items 1 and 5)
PROVISIONAL_RE = re.compile(r"\[provisional (\w+): equivalence pending")
POSITIVE_LABELS = ("retained", "tradeoff", "improved")
BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.S)


def _events(cfg):
    ev = (cfg.get("exp5") or {}).get("events") or {}
    return {k: (str(v) if v else None) for k, v in ev.items()}


def provisional_agreement(conn, exp="phase5"):
    """Provisional-versus-final diagnosis: every candidate that received a provisional label; agreement is counted on the
    candidates whose proof succeeded and whose final diagnosis exists (the same E4 record, the same rule)."""
    out = {"n_provisional": 0, "by_label": Counter(), "proven_final": 0, "agree": 0, "disagree": [], "not_proven": 0, "pending": 0, "withheld": 0}
    for r in conn.execute("SELECT cand.cand_id, cand.note, cand.verdict, (SELECT label FROM diagnoses d WHERE d.cand_id=cand.cand_id ORDER BY rowid DESC LIMIT 1) AS final "
                          "FROM candidates cand JOIN runs r ON r.run_id=cand.run_id WHERE r.exp=? AND cand.note LIKE '%[provisional %'", (exp,)):
        m = PROVISIONAL_RE.search(r["note"] or "")
        if not m:
            continue
        prov = m.group(1)
        out["n_provisional"] += 1
        out["by_label"][prov] += 1
        out["withheld"] += int("withheld]" in (r["note"] or ""))
        if r["verdict"] is None:
            out["pending"] += 1
        elif r["verdict"] not in ("proven", "proven_sim_only"):
            out["not_proven"] += 1
        elif r["final"]:
            out["proven_final"] += 1
            if r["final"] == prov:
                out["agree"] += 1
            elif len(out["disagree"]) < 50:
                out["disagree"].append({"cand_id": r["cand_id"], "provisional": prov, "final": r["final"]})
        else:
            out["pending"] += 1
    out["by_label"] = dict(out["by_label"])
    out["agree_rate"] = round(out["agree"] / out["proven_final"], 4) if out["proven_final"] else None
    return out


def provisional_exposure(cfg, conn, exp="phase5", results_dir=None, now=None):
    """User follow-up item 1: the calls whose prompt carried a positive provisional block ("equivalence": "pending" with a
    retained / tradeoff / improved diagnosis) between the change and the fix, the candidates behind them (the run's positively
    labelled provisional candidates whose proof had not arrived when the call was made) and what their proofs said since."""
    ev = _events(cfg)
    start, end = ev.get("scheduling_change_at"), ev.get("provisional_fix_at") or (now or datetime.datetime.now().isoformat(timespec="seconds"))
    out = {"window": [start, end], "calls": 0, "blocks": 0, "runs": Counter(), "cand_ids": set(), "unmatched_blocks": 0}
    if not start:
        return out
    root = Path(results_dir or C.results_dir(cfg))
    runs = [r[0] for r in conn.execute("SELECT run_id FROM runs WHERE exp=? AND status != 'superseded'", (exp,))]
    for rid in runs:
        d = root / "llm" / rid
        if not d.is_dir():
            continue
        cands = None
        for f in sorted(d.glob("c*.json")):
            try:
                rec = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            at = str(rec.get("at") or "")
            if not at or at < start or at > end:
                continue
            text = ((rec.get("request") or {}).get("input")) or ""
            if '"equivalence": "pending"' not in text:
                continue
            hits = []
            for blob in BLOCK_RE.findall(text):
                try:
                    b = json.loads(blob)
                except json.JSONDecodeError:
                    continue
                if isinstance(b, dict) and b.get("equivalence") == "pending" and b.get("diagnosis") in POSITIVE_LABELS:
                    hits.append(b.get("diagnosis"))
            if not hits:
                continue
            out["calls"] += 1
            out["blocks"] += len(hits)
            out["runs"][rid] += 1
            if cands is None:   # the run's positively labelled provisional candidates (state file) with the time of the label and of the verdict
                cands = []
                st = root / "candidates" / rid / "state.json"
                if st.exists():
                    try:
                        for cid, c in (json.loads(st.read_text()).get("cands") or {}).items():
                            prov = c.get("provisional") or {}
                            if prov.get("label") in POSITIVE_LABELS:
                                cands.append((cid, prov.get("label"), str(prov.get("at") or ""), c))
                    except (OSError, json.JSONDecodeError):
                        pass
            matched = False
            for cid, label, prov_at, c in cands:
                if label in hits and prov_at <= at:
                    verdict_at = conn.execute("SELECT finished_at FROM jobs WHERE job_id=? AND state IN ('done','failed')", (c.get("seq_job_id"),)).fetchone() if c.get("seq_job_id") else None
                    if verdict_at and verdict_at[0] and verdict_at[0] < at:
                        continue   # its proof had already arrived: the block in the prompt was the final one, not this candidate's provisional block
                    out["cand_ids"].add(cid)
                    matched = True
            out["unmatched_blocks"] += int(not matched)
    fate = Counter()
    for cid in out["cand_ids"]:
        r = conn.execute("SELECT verdict FROM candidates WHERE cand_id=?", (cid,)).fetchone()
        fate[(r[0] if r and r[0] else "pending")] += 1
    out["runs"] = dict(out["runs"])
    out["cand_ids"] = sorted(out["cand_ids"])
    out["n_candidates"] = len(out["cand_ids"])
    out["fate"] = dict(fate)
    return out


def verdict_reuse(cfg, conn, exp="phase5", results_dir=None, since=None):
    """Cross-run verdict reuse (split pipeline): proof records copied from a decided `full` record of the same pair (`reused_from`),
    counted over the EQ records written since the change."""
    ev = _events(cfg)
    since = since or ev.get("scheduling_change_at")
    root = Path(results_dir or C.results_dir(cfg)) / "raw"
    t0 = datetime.datetime.fromisoformat(since).timestamp() if since else 0.0
    out = {"since": since, "records_scanned": 0, "reused": 0, "split_proofs": 0, "sim_record_missing": 0, "by_verdict": Counter()}
    for eq in root.glob("*/EQ/*/equiv.json"):
        try:
            if eq.stat().st_mtime < t0:
                continue
            rec = json.loads(eq.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        out["records_scanned"] += 1
        if rec.get("sim_record") or rec.get("sim_record_missing"):
            out["split_proofs"] += 1
        out["sim_record_missing"] += int(bool(rec.get("sim_record_missing")))
        if rec.get("reused_from"):
            out["reused"] += 1
            out["by_verdict"][rec.get("verdict")] += 1
    out["by_verdict"] = dict(out["by_verdict"])
    return out


def hourly_proof_ratio(cfg, conn, since=None):
    """Per hour since the hidden-job throttle: equivalence jobs finished on the vcf pool by the candidate's verdict, and the
    proven-to-inconclusive ratio (the throttle's and the scheduling change's effect on the proofs)."""
    ev = _events(cfg)
    since = since or ev.get("hidden_throttle_at")
    rows = []
    if not since:
        return {"since": None, "hours": rows}
    by = defaultdict(Counter)
    for r in conn.execute("SELECT substr(j.finished_at, 1, 13) AS h, cand.verdict AS v, COUNT(*) AS n FROM jobs j JOIN candidates cand ON cand.cand_id=j.cand_id "
                          "WHERE j.pool='vcf' AND j.state='done' AND j.finished_at >= ? GROUP BY h, v ORDER BY h", (since,)):
        by[r["h"]][r["v"] or "pending"] += int(r["n"])
    for h in sorted(by):
        c = by[h]
        rows.append({"hour": h, "finished": sum(c.values()), "proven": c.get("proven", 0), "inconclusive": c.get("inconclusive", 0), "falsified": c.get("falsified", 0),
                     "rejected": c.get("rejected", 0), "sim_fail": c.get("sim_fail", 0), "ratio": round(c.get("proven", 0) / c["inconclusive"], 2) if c.get("inconclusive") else None})
    return {"since": since, "hours": rows}


def operations(cfg, conn, exp="phase5", results_dir=None):
    """The block of the report on the operational changes of 2026-09-16 (each part guarded: a failure is reported, never fatal)."""
    out = {"events": _events(cfg)}
    for name, fn in (("agreement", lambda: provisional_agreement(conn, exp)), ("exposure", lambda: provisional_exposure(cfg, conn, exp, results_dir)),
                     ("reuse", lambda: verdict_reuse(cfg, conn, exp, results_dir)), ("hourly", lambda: hourly_proof_ratio(cfg, conn))):
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = {"error": f"{type(e).__name__}: {e}"[:200]}
    return out


# ----------------------------------------------------------------------------- REQUEST 2026-09-20 (e): power basis of the search
DEFAULT_POWER_NOTE = "power on this design is on the default-activity basis for all arms during the search"


def default_power_basis_designs(cfg, conn):
    """The Phase 5 designs whose E4 baseline used by the running evaluators (is_baseline = 1 at Φ_main) carries no SAIF power: every
    power comparison of the search on them is made on DC's default switching activity (m3.power_basis never mixes the bases), whatever
    the candidate's record carries. Sorted design ids (REQUEST 2026-09-20 (e) item 1: marked in §0a of every report)."""
    held = [d for ds in ((cfg.get("exp5") or {}).get("starting_points") or {}).values() for d in ds]
    designs = _Designs(cfg, conn)
    out = []
    for d in held:
        base = designs.get(d)["base"]
        if base is not None and (base.get("metrics") or {}).get("power_saif_mw") is None:
            out.append(d)
    return sorted(out)


def pooled_floor_designs(cfg, conn, floor_version=None):
    """The Phase 5 designs without a measured floor in the frozen table (floor_source != measured or no E4 area row): PLAN 6.9."""
    fv = floor_version or cfg["noise"].get("floor_version")
    held = [d for ds in ((cfg.get("exp5") or {}).get("starting_points") or {}).values() for d in ds]
    out = []
    for d in held:
        row = conn.execute("SELECT floor_source FROM noise_floor WHERE floor_version=? AND config='E4' AND metric='area' AND design_id=?", (fv, d)).fetchone()
        if row is None or row["floor_source"] != "measured":
            out.append(d)
    return sorted(out)
