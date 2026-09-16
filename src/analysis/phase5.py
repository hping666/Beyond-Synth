"""Phase 5 visible-layer collector (PLAN 5, reports/phase5.md; staged reports A / B / C per tier, user decision 2026-09-16).

Reads the visible results database only (never the hidden one, rule 3). Every proven candidate with an E4 record is
re-labelled offline under the same rule-A diagnosis for every arm (`src/diagnose/m3.diagnose` with the design's frozen E4
floor): the uniform caliber of the comparison; arm M's stored labels (with the envelope runs) are reported alongside.
Stages: A = the large tier, B = large + medium, C = every tier (the full visible part); the hidden part comes from
scripts/report_hidden.py after the completion marker.
"""
import datetime
import json
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
    """Per-design baseline record, floor thresholds and class, cached."""
    def __init__(self, cfg, conn):
        self.cfg, self.conn, self.cache = cfg, conn, {}
        self.floor_version = cfg["noise"].get("floor_version")
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
        floor = S.latest_floor(self.conn, design_id, "E4", self.floor_version) or S.latest_floor(self.conn, design_id, "E4")
        d = {"phi": phi, "base": record_from_row(base) if base is not None else None,
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
    return label, (out.get("evidence") or {}).get("gains") or {}, {"envelope_required": bool(out.get("envelope_required")), "dc_seconds": ev["dc_seconds"], "eval_created": ev["created_at"]}


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
        if t not in tiers:
            continue
        r["tier"], r["role"] = t, role_of(cfg, t, r["llm_model"])
        runs.append(r)
    out = {"generated_at": datetime.datetime.now().isoformat(timespec="minutes"), "exp": exp, "tiers": tiers, "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(),
           "equiv_version": (cfg.get("equiv") or {}).get("version"), "floor_version": cfg["noise"].get("floor_version"),
           "planned": {}, "runs": [], "groups": {}, "designs": {}, "curves": {}, "correctness": {}, "classes": {}, "ttv": {}, "unfinished_note": None}
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
                                  "latency_mapped": 0})
    by_design = defaultdict(lambda: {"best": None, "runs": 0, "retained": 0})
    correctness = defaultdict(lambda: {"cands": 0, "proven": 0, "runs": 0})
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
            elif ver is None and lab not in ("duplicate", "prescreened", "absorbed_identical"):
                g["pending"] += 1
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
        }
    out["designs"] = {k: {"best_retained_area_gain": (None if v["best"] is None else round(v["best"], 5)), "runs": v["runs"], "retained": v["retained"]} for k, v in by_design.items()}
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
    return out


def stage_tiers(stage):
    return STAGES[stage]
