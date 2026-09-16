#!/usr/bin/env python3
"""Phase 5 main experiment (PLAN 5.1-5.2; decisions 2026-09-15 item 6, pre-authorised conditional launch).
    .venv/bin/python scripts/phase5_main.py plan          # the run matrix: luna on every arm and tier, the second model on M / B2, the large tier per the probe rule
    .venv/bin/python scripts/phase5_main.py prelaunch     # projections (LLM USD, disk, DC and VC Formal hours) against the caps -> reports/data/phase5_prelaunch.md; go / no-go
    .venv/bin/python scripts/phase5_main.py launch        # only when prelaunch says go and the probe is finished: seat targets to bulk, runs created and submitted
    .venv/bin/python scripts/phase5_main.py status        # progress by arm, tier and model
The probe rule (G5 item 1): a model with at least `exp5.correctness_probe.min_proven` proven candidates on a probe design
carries the large tier for arms M and B2 (sol never the main model). Stop conditions (item 6): a projection outside its cap,
or the probe yielding zero proven candidates for both models on all three designs.
"""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
from pathlib import Path  # noqa: E402
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402

EXP = "phase5"
PROBE_EXP = "phase5_probe"


# ----------------------------------------------------------------------------- the probe rule and the run matrix
def probe_verdicts(cfg, conn):
    """{model: {design: proven}}, {model: qualifies}, finished flag, zero flag (no proven candidate for both models on all designs)."""
    pc = cfg["exp5"]["correctness_probe"]
    rows = [dict(r) for r in conn.execute("SELECT run_id, llm_model, design_id, status FROM runs WHERE exp=? AND status != 'superseded'", (PROBE_EXP,))]
    proven = {m: {d: 0 for d in pc["designs"]} for m in pc["models"]}
    for r in rows:
        n = conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND verdict='proven'", (r["run_id"],)).fetchone()[0]
        proven.setdefault(r["llm_model"], {}).setdefault(r["design_id"], 0)
        proven[r["llm_model"]][r["design_id"]] += int(n)
    qualifies = {m: any(v >= int(pc["min_proven"]) for v in proven[m].values()) for m in proven}
    finished = bool(rows) and all(r["status"] in ("done", "failed") for r in rows)
    zero = all(v == 0 for m in pc["models"] for v in proven.get(m, {}).values())
    return proven, qualifies, finished, zero, len(rows)


def large_tier_model(cfg, qualifies):
    """The second model of arms M / B2 on the large tier: the configured second model when it qualifies, else the other
    probe model when that one qualifies (sol never the main model), else the configured second model with a note."""
    second = cfg["llm"]["second_model"]["model"]
    if qualifies.get(second):
        return second, f"{second} carries the large tier (>= min_proven on a probe design)"
    for m in cfg["exp5"]["correctness_probe"]["models"]:
        if m != second and qualifies.get(m):
            return m, f"{m} carries the large tier for arms M / B2 ({second} did not qualify; sol never the main model)"
    return second, f"no probe model reached min_proven: the large tier stays with {second} (a zero proven rate there is a result about the LLM, G5 item 1)"


def tier_assignment(cfg, tier):
    """The models of a tier (config `exp5.model_assignment`, decision 2026-09-15 evening item 3): {"all_arms": model, "second":
    {model: [arms]}, "contrast": {model: [arms]}}; a tier without an entry falls back to the pre-amendment rule (the main model
    on every arm, the second model on its arms)."""
    ma = (cfg["exp5"].get("model_assignment") or {}).get(tier)
    if ma:
        return {"all_arms": ma["all_arms"], "second": dict(ma.get("second") or {}), "contrast": dict(ma.get("contrast") or {})}
    second = cfg["llm"]["second_model"]
    return {"all_arms": cfg["llm"]["selected"], "second": {second["model"]: list(second.get("arms") or [])}, "contrast": {}}


def plan(cfg, conn):
    """-> {"runs": [{model, arm, design_id, tier, seed, role}], "assignment": {tier: ...}, "skipped_arms", "probe": {...}}.
    role: main (the tier's model on every arm), second (the model-independence check), contrast (the model-correctness
    contrast, reported apart from the main table)."""
    sp = cfg["exp5"]["starting_points"]
    defined = cfg["search"].get("arms") or {}
    arms = [a for a in cfg["scale"]["arms"] if a in defined or a == "M"]
    skipped_arms = [a for a in cfg["scale"]["arms"] if a not in arms]   # an arm without a driver definition is not launched
    seeds = int(cfg["scale"]["seeds"])
    proven, qualifies, finished, zero, n_probe = probe_verdicts(cfg, conn)
    runs, assignment = [], {}
    for tier, designs in sp.items():
        ma = tier_assignment(cfg, tier)
        assignment[tier] = ma
        for did in designs:
            for seed in range(1, seeds + 1):
                for arm in arms:
                    runs.append({"model": ma["all_arms"], "arm": arm, "design_id": did, "tier": tier, "seed": seed, "role": "main"})
                for role in ("second", "contrast"):
                    for model, marms in ma[role].items():
                        for arm in marms:
                            if arm in arms and model != ma["all_arms"]:
                                runs.append({"model": model, "arm": arm, "design_id": did, "tier": tier, "seed": seed, "role": role})
    return {"runs": runs, "assignment": assignment, "skipped_arms": skipped_arms,
            "large_second": (assignment.get("large", {}).get("all_arms"), "exp5.model_assignment (decision 2026-09-15 evening, item 3) supersedes the probe rule"),
            "probe": {"proven": proven, "qualifies": qualifies, "finished": finished, "zero": zero, "runs": n_probe}}


def matrix_tables(pl):
    """Markdown: runs per (model, arm) and per (tier, model, role) — the launch summary of decision 2026-09-15 evening, item 7."""
    from collections import Counter
    by_ma = Counter((r["model"], r["arm"]) for r in pl["runs"])
    by_tmr = Counter((r["tier"], r["model"], r["role"]) for r in pl["runs"])
    arms = sorted({a for _, a in by_ma})
    models = sorted({m for m, _ in by_ma})
    L = ["| model | " + " | ".join(arms) + " | total |", "|---|" + "---|" * (len(arms) + 1)]
    for m in models:
        L.append(f"| {m} | " + " | ".join(str(by_ma.get((m, a), 0)) for a in arms) + f" | {sum(v for (mm, _), v in by_ma.items() if mm == m)} |")
    L += ["", "| tier | model | role | runs |", "|---|---|---|---|"]
    for (t, m, role), n in sorted(by_tmr.items(), key=lambda kv: ({"large": 0, "medium": 1, "small": 2}.get(kv[0][0], 3), kv[0][1], kv[0][2])):
        L.append(f"| {t} | {m} | {role} | {n} |")
    return L


# ----------------------------------------------------------------------------- projections
def _tier_of_design(cfg, did):
    for tier, ds in (cfg["exp5"].get("projection_reference_tiers") or {}).items():
        if did in ds:
            return tier
    for tier, ds in (cfg["exp5"].get("starting_points") or {}).items():
        if did in ds:
            return tier
    return None


def per_call_stats(cfg, conn):
    """Measured per-call quantities by (model, tier) from the finished runs of Phase 4 (luna, B0) and the probe (terra, sol):
    USD per call, VC Formal seconds per call, proven candidates per call, accepted per call, E4 seconds per proven candidate."""
    stats = {}
    q = ("SELECT r.run_id, r.llm_model, r.design_id, r.llm_calls, r.spent_usd, r.spent_vcf_hours FROM runs r WHERE r.exp IN ('phase4', ?) AND r.status IN ('done', 'running', 'failed') "
         "AND r.arm != 'literature' AND r.llm_calls > 0")
    for r in conn.execute(q, (PROBE_EXP,)):
        tier = _tier_of_design(cfg, r["design_id"])
        if tier is None:
            continue
        k = (r["llm_model"], tier)
        s = stats.setdefault(k, {"calls": 0, "usd": 0.0, "vcf_s": 0.0, "proven": 0, "accepted": 0, "e4_s": 0.0, "e4_n": 0, "runs": 0})
        s["runs"] += 1
        s["calls"] += int(r["llm_calls"] or 0)
        s["usd"] += float(r["spent_usd"] or 0.0)
        s["vcf_s"] += 3600.0 * float(r["spent_vcf_hours"] or 0.0)
        n = conn.execute("SELECT SUM(verdict='proven'), SUM(accepted) FROM candidates WHERE run_id=?", (r["run_id"],)).fetchone()
        s["proven"] += int(n[0] or 0)
        s["accepted"] += int(n[1] or 0)
        e4 = conn.execute("SELECT COALESCE(SUM(e.dc_seconds),0), COUNT(*) FROM evaluations e JOIN candidates c ON c.cand_id=e.cand_id WHERE c.run_id=? AND e.config='E4' AND e.status='ok'", (r["run_id"],)).fetchone()
        s["e4_s"] += float(e4[0] or 0.0)
        s["e4_n"] += int(e4[1] or 0)
    out = {}
    for (model, tier), s in stats.items():
        calls = max(s["calls"], 1)
        out[(model, tier)] = {"runs": s["runs"], "calls": s["calls"], "usd_per_call": s["usd"] / calls, "vcf_s_per_call": s["vcf_s"] / calls,
                              "proven_per_call": s["proven"] / calls, "accepted_per_call": s["accepted"] / calls,
                              "e4_s_per_proven": (s["e4_s"] / s["e4_n"]) if s["e4_n"] else None}
    return out


def _lookup(stats, cfg, model, tier, key, default=None):
    """The measured value, else the main model's value of the tier scaled by the price ratio for USD, else the default."""
    if (model, tier) in stats and stats[(model, tier)].get(key) is not None:
        return stats[(model, tier)][key], "measured"
    main = cfg["llm"]["selected"]
    if (main, tier) in stats and stats[(main, tier)].get(key) is not None:
        v = stats[(main, tier)][key]
        if key == "usd_per_call":
            pm, po = cfg["llm"]["prices_usd_per_1m"]["flex"].get(model), cfg["llm"]["prices_usd_per_1m"]["flex"].get(main)
            if pm and po:
                v = v * (float(pm["output"]) / float(po["output"]))
        return v, f"from {main} on the tier"
    return default, "default"


def projection(cfg, conn, pl, slim_kept_eq=False):
    """LLM USD, VC Formal hours, DC hours and disk growth of the planned runs, with the sources of every per-call figure.
    slim_kept_eq: the what-if disk variant of scripts/phase5_footprint.project (accepted candidates' equivalence records slimmed too)."""
    stats = per_call_stats(cfg, conn)
    calls_per_run = int(cfg["scale"]["budget"]["llm_calls_per_run"])
    t_e4 = {}
    for tier, designs in cfg["exp5"]["starting_points"].items():
        secs = [r[0] for did in designs for r in conn.execute("SELECT dc_seconds FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND status='ok' AND dc_seconds IS NOT NULL ORDER BY eval_id DESC LIMIT 1", (did,))]
        t_e4[tier] = (sum(secs) / len(secs)) if secs else 100.0
    hidden_all = [h for h, sc in (cfg["exp5"].get("hidden_scope") or {}).items() if sc == "all_e4"]
    hidden_acc = [h for h, sc in (cfg["exp5"].get("hidden_scope") or {}).items() if sc == "accepted_and_audit"]
    audit = float((cfg.get("retention") or {}).get("tiered_audit_frac") or 0.0)
    usd = vcf_h = dc_h = 0.0
    sources, by_model = {}, {}
    for r in pl["runs"]:
        m, tier = r["model"], r["tier"]
        c_usd, s1 = _lookup(stats, cfg, m, tier, "usd_per_call", 0.0)
        c_vcf, s2 = _lookup(stats, cfg, m, tier, "vcf_s_per_call", 60.0)
        p_prov, s3 = _lookup(stats, cfg, m, tier, "proven_per_call", 0.25)
        p_acc, s4 = _lookup(stats, cfg, m, tier, "accepted_per_call", 0.1)
        e4s, _ = _lookup(stats, cfg, m, tier, "e4_s_per_proven", None)
        e4s = e4s or t_e4.get(tier, 100.0)
        sources[(m, tier)] = {"usd_per_call": (round(c_usd, 4), s1), "vcf_s_per_call": (round(c_vcf, 1), s2), "proven_per_call": (round(p_prov, 3), s3), "accepted_per_call": (round(p_acc, 3), s4), "e4_s": round(e4s, 1)}
        run_usd = calls_per_run * c_usd
        run_vcf = calls_per_run * c_vcf
        fitness_runs = calls_per_run * p_prov * (1 if r["arm"] != "B0" else 0) + (calls_per_run * p_acc if r["arm"] == "B0" else 0)   # B0: Yosys fitness, E4 only for its accepted candidates
        hidden_runs = calls_per_run * p_prov * len(hidden_all) + calls_per_run * (p_acc + (p_prov - p_acc) * audit) * len([h for h in hidden_acc if h != "H4"])
        run_dc = (fitness_runs + hidden_runs) * e4s * 1.1   # + 10 % for the acceptance envelope and the sampled single-flag runs
        usd += run_usd
        vcf_h += run_vcf / 3600.0
        dc_h += run_dc / 3600.0
        bm = by_model.setdefault(m, {"runs": 0, "usd": 0.0})
        bm["runs"] += 1
        bm["usd"] += run_usd
    # disk: the tiered policy plus H1 / H3 / H5 on every E4-evaluated candidate, from the footprint projection of G5 item 5
    disk_gb = None
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import phase5_footprint as PF
        ns = argparse.Namespace(measured=str(Path(ROOT) / "reports/data/phase5_footprint_measured.json"), out=str(Path(ROOT) / "reports/data/phase5_footprint.md"), large_proven_rate=0.10)
        model_rates = {}
        for r in pl["runs"]:
            k = (r["model"], r["tier"])
            if k not in model_rates:
                pp, s_p = _lookup(stats, cfg, r["model"], r["tier"], "proven_per_call", None)
                pa, s_a = _lookup(stats, cfg, r["model"], r["tier"], "accepted_per_call", None)
                model_rates[k] = {"proven_per_call": pp, "accepted_per_call": pa, "source": s_p}
        totals = PF.project(ns, plan_runs=pl["runs"], model_rates=model_rates, slim_kept_eq=slim_kept_eq)   # the footprint follows the launch matrix and the measured rates (decision 2026-09-15 evening, item 3)
        if totals:
            n_all = len([h for h in ("H1", "H3", "H5") if (cfg["exp5"].get("hidden_scope") or {}).get(h) == "all_e4"])   # the all-E4 extra counts only the configurations registered for every E4-evaluated candidate
            disk_gb = (totals["tiered"] + totals["hidden_all_e4"] * n_all / 3.0) / 1e9
    except Exception as e:   # the footprint projection is optional; its absence is reported
        disk_gb = None
        sources["disk_error"] = f"{type(e).__name__}: {e}"[:200]
    return {"llm_usd": usd, "vcf_hours": vcf_h, "dc_hours": dc_h, "disk_gb": disk_gb, "by_model": by_model, "sources": sources, "t_e4_by_tier": t_e4, "runs": len(pl["runs"]), "calls": len(pl["runs"]) * calls_per_run}


def caps(cfg):
    lc = cfg["exp5"]["launch_caps"]
    return {"llm_usd": float(lc.get("llm_usd") or cfg["llm"]["budget_usd"]["phase5_main"]), "disk_margin_gb": float(lc["disk_margin_gb"]),
            "vcf_hours": float(lc["vcf_hours"]), "dc_hours": float(lc["dc_hours"])}


def prelaunch(cfg, conn, write=True):
    pl = plan(cfg, conn)
    pr = projection(cfg, conn, pl)
    cp = caps(cfg)
    free = shutil.disk_usage(C.results_dir(cfg)).free / 1e9
    checks = {"llm_usd": (pr["llm_usd"], cp["llm_usd"], pr["llm_usd"] <= cp["llm_usd"]),
              "disk_gb": (pr["disk_gb"], free - cp["disk_margin_gb"], pr["disk_gb"] is not None and pr["disk_gb"] <= free - cp["disk_margin_gb"]),
              "vcf_hours": (pr["vcf_hours"], cp["vcf_hours"], pr["vcf_hours"] <= cp["vcf_hours"]),
              "dc_hours": (pr["dc_hours"], cp["dc_hours"], pr["dc_hours"] <= cp["dc_hours"])}
    probe = pl["probe"]
    go = all(v[2] for v in checks.values()) and probe["finished"] and not probe["zero"]
    reasons = [k for k, v in checks.items() if not v[2]]
    if not probe["finished"]:
        reasons.append("probe not finished")
    if probe["zero"]:
        reasons.append("probe: zero proven candidates for both models on all three designs")
    L = [f"# Phase 5 pre-launch report ({datetime.datetime.now().isoformat(timespec='minutes')}; decisions 2026-09-15 item 6 and evening items 3 / 7)", "",
         f"**{'GO' if go else 'NO-GO'}**" + ("" if go else f" — {', '.join(reasons)}"), "",
         "## Probe (G5 item 1)", "", "| model | " + " | ".join(cfg["exp5"]["correctness_probe"]["designs"]) + " | qualifies (>= %d proven on a design) |" % int(cfg["exp5"]["correctness_probe"]["min_proven"]),
         "|---|" + "---|" * (len(cfg["exp5"]["correctness_probe"]["designs"]) + 1)]
    for m, byd in probe["proven"].items():
        L.append(f"| {m} | " + " | ".join(str(byd.get(d, 0)) for d in cfg["exp5"]["correctness_probe"]["designs"]) + f" | {'yes' if probe['qualifies'].get(m) else 'no'} |")
    asg = pl.get("assignment") or {}
    asg_text = "; ".join(f"{t}: {a['all_arms']} on every arm" + "".join(f", {m} on {'/'.join(ar)} ({role})" for role in ("second", "contrast") for m, ar in a[role].items()) for t, a in asg.items())
    lim = cfg["exp5"]["correctness_probe"]["designs"]
    low = [d for d in lim if all((probe["proven"].get(m) or {}).get(d, 0) < int(cfg["exp5"]["correctness_probe"]["min_proven"]) for m in probe["proven"])] if probe["proven"] else []
    L += ["", f"Probe runs: {probe['runs']}, finished: {probe['finished']}. Model assignment by tier (decision 2026-09-15 evening, item 3; supersedes the probe rule for the large tier): {asg_text}."
          + (f" Probe designs below min_proven under every model: {', '.join(low)} — kept in the large tier; their near-zero proven rate is the LLM-correctness limit and is reported as such (item 4)." if low else ""), "",
          "## Run matrix", "", f"{pr['runs']} runs, {pr['calls']} LLM calls: " + ", ".join(f"{m} {v['runs']} runs" for m, v in pr["by_model"].items()) + "."
          + (f" Arms without a driver definition are not in this launch and follow once implemented: {', '.join(pl['skipped_arms'])}." if pl.get("skipped_arms") else ""), ""]
    L += matrix_tables(pl)
    L += ["", f"Seat targets at launch: vcf_seats_target = dc_seats_target = {cfg['exp5']['launch_caps'].get('bulk_seats_target')} (restored to the Phase 3-4 targets afterwards); search runs in their own pool of {cfg['queue'].get('search_max')}.", "",
          "## Projections against the caps", "", "| quantity | projected | cap | inside |", "|---|---|---|---|"]
    for k, (v, c, ok) in checks.items():
        L.append(f"| {k} | {'-' if v is None else f'{v:.1f}'} | {c:.1f} | {'yes' if ok else 'NO'} |")
    L += ["", f"Free space now {free:.1f} GB (cap = free minus {cp['disk_margin_gb']:.0f} GB); disk projection = the tiered policy plus H1 / H3 / H5 on every E4-evaluated candidate (reports/data/phase5_footprint.md). "
          "DC hours count the E4 fitness runs of the proven candidates (B0: its accepted candidates), the hidden configurations per `exp5.hidden_scope` and 10 % for envelope and single-flag runs; VC Formal hours are the measured seconds per LLM call of the same model and tier (or the main model's).", "",
          "## Per-call figures used (measured where a finished run of the model on the tier exists)", "", "| model | tier | USD / call | VCF s / call | proven / call | accepted / call | E4 s / proven |", "|---|---|---|---|---|---|---|"]
    for (m, tier), v in sorted((k, v) for k, v in pr["sources"].items() if isinstance(k, tuple)):
        L.append(f"| {m} | {tier} | {v['usd_per_call'][0]} ({v['usd_per_call'][1]}) | {v['vcf_s_per_call'][0]} ({v['vcf_s_per_call'][1]}) | {v['proven_per_call'][0]} ({v['proven_per_call'][1]}) | {v['accepted_per_call'][0]} | {v['e4_s']} |")
    L.append("")
    text = "\n".join(L)
    if write:
        (Path(ROOT) / "reports" / "data" / "phase5_prelaunch.md").write_text(text + "\n")
    return go, pl, pr, checks, text


# ----------------------------------------------------------------------------- launch and status
def set_bulk_targets(cfg, target):
    """queue.vcf_seats_target and dc_seats_target in config (the daemon reads them at start: restart afterwards)."""
    p = Path(ROOT) / "config" / "experiments.yaml"
    text = p.read_text()
    for key in ("vcf_seats_target", "dc_seats_target"):
        text, n = re.subn(rf"^(\s*{key}:\s*)\d+", rf"\g<1>{int(target)}", text, count=1, flags=re.M)
        if n == 0:
            raise SystemExit(f"config key queue.{key} not found")
    p.write_text(text)


def restart_daemon():
    d = os.path.join(ROOT, "scripts", "queue", "daemon.py")
    subprocess.run([sys.executable, d, "stop"], check=False)
    subprocess.run(["setsid", sys.executable, d, "start"], check=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def cmd_launch(cfg, conn, dry_run=False):
    from src.jobqueue.core import Queue
    from src.search.driver import SearchRun
    go, pl, pr, checks, text = prelaunch(cfg, conn, write=True)
    print(text)
    if not go:
        print("NO-GO: nothing launched (decision 2026-09-15 item 6: stop and report)")
        return 2
    if dry_run:
        print(f"dry run: {len(pl['runs'])} runs would be created")
        return 0
    have = {(r["llm_model"], r["arm"], r["design_id"], int(r["seed"])) for r in conn.execute("SELECT llm_model, arm, design_id, seed FROM runs WHERE exp=? AND status != 'superseded'", (EXP,))}
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    K, N = int(cfg["scale"]["K"]), int(cfg["scale"]["N"])
    created = 0
    order = {"large": 0, "medium": 1, "small": 2}   # the long proofs first (decision 2026-09-14 item 2: their tails overlap with the rest)
    for r in sorted(pl["runs"], key=lambda r: (order.get(r["tier"], 3), r["design_id"], r["seed"], r["arm"], r["model"])):
        if (r["model"], r["arm"], r["design_id"], r["seed"]) in have:
            continue
        run = SearchRun.create(cfg, conn, exp=EXP, arm=r["arm"], design_id=r["design_id"], seed=r["seed"], model=r["model"], K=K, N=N, queue=q, note=f"Phase 5 main: tier {r['tier']}")
        q.submit("search", {"run_id": run.run_id}, design_id=r["design_id"], config="search", priority=3, timeout_sec=48 * 3600)
        created += 1
    bulk = int(cfg["exp5"]["launch_caps"].get("bulk_seats_target") or 50)
    set_bulk_targets(cfg, bulk)
    restart_daemon()
    print(f"launched: {created} runs created and submitted (of {len(pl['runs'])} planned; {len(have)} existed); seat targets set to {bulk}, daemon restarted")
    return 0


def cmd_status(cfg, conn):
    rows = [dict(r) for r in conn.execute("SELECT r.run_id, r.llm_model, r.arm, r.design_id, r.status, r.gens_done, r.llm_calls, r.spent_usd, r.spent_vcf_hours, r.spent_dc_hours FROM runs r WHERE r.exp=? AND r.status != 'superseded' ORDER BY r.run_id", (EXP,))]
    if not rows:
        print("no Phase 5 runs")
        return 0
    from collections import Counter
    st = Counter(r["status"] for r in rows)
    usd = sum(float(r["spent_usd"] or 0) for r in rows)
    print(f"{len(rows)} runs: {dict(st)}; calls {sum(int(r['llm_calls'] or 0) for r in rows)}; USD {usd:.2f} of {cfg['llm']['budget_usd']['phase5_main']}; VCF h {sum(float(r['spent_vcf_hours'] or 0) for r in rows):.1f}; DC h {sum(float(r['spent_dc_hours'] or 0) for r in rows):.1f}")
    by = {}
    for r in rows:
        tier = _tier_of_design(cfg, r["design_id"]) or "?"
        k = (r["llm_model"], r["arm"], tier)
        n = conn.execute("SELECT COUNT(*), SUM(verdict='proven'), SUM(accepted), SUM((label='scope_violation' OR COALESCE(json_array_length(json_extract(scope_json,'$.violations')),0) > 0)), SUM(repair_of IS NOT NULL) FROM candidates WHERE run_id=?", (r["run_id"],)).fetchone()
        b = by.setdefault(k, {"runs": 0, "done": 0, "cands": 0, "proven": 0, "accepted": 0, "scope": 0, "repairs": 0})
        b["runs"] += 1
        b["done"] += int(r["status"] == "done")
        b["cands"] += int(n[0]); b["proven"] += int(n[1] or 0); b["accepted"] += int(n[2] or 0); b["scope"] += int(n[3] or 0); b["repairs"] += int(n[4] or 0)
    print("| model | arm | tier | runs | done | candidates | proven | accepted | scope flags (restored) | repairs |")
    for (m, arm, tier), b in sorted(by.items()):
        print(f"| {m} | {arm} | {tier} | {b['runs']} | {b['done']} | {b['cands']} | {b['proven']} | {b['accepted']} | {b['scope']} | {b['repairs']} |")
    free = shutil.disk_usage(C.results_dir(cfg)).free / 1e9
    paused = conn.execute("SELECT COUNT(*) FROM runs WHERE status='paused_disk'").fetchone()[0]
    print(f"free space {free:.1f} GB; disk guard threshold {(cfg.get('retention') or {}).get('min_free_gb')} GB; paused runs {paused}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["plan", "prelaunch", "launch", "status"])
    ap.add_argument("--dry-run", action="store_true", help="launch: report and count only")
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    if a.what == "plan":
        pl = plan(cfg, conn)
        from collections import Counter
        print(f"{len(pl['runs'])} runs; by model {dict(Counter(r['model'] for r in pl['runs']))}; by tier {dict(Counter(r['tier'] for r in pl['runs']))}; by arm {dict(Counter(r['arm'] for r in pl['runs']))}" + (f"; arms not launched (no driver definition): {pl['skipped_arms']}" if pl.get('skipped_arms') else ""))
        print(f"large tier second model: {pl['large_second'][0]} ({pl['large_second'][1]}); probe finished {pl['probe']['finished']}, proven {pl['probe']['proven']}")
        return 0
    if a.what == "prelaunch":
        go, pl, pr, checks, text = prelaunch(cfg, conn, write=True)
        print(text)
        return 0 if go else 2
    if a.what == "launch":
        return cmd_launch(cfg, conn, dry_run=a.dry_run)
    return cmd_status(cfg, conn)


if __name__ == "__main__":
    sys.exit(main())
