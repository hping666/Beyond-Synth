#!/usr/bin/env python3
"""Generate a phase report from the collected data (CLAUDE.md working rhythm).

    .venv/bin/python scripts/report_phase.py phase1      # -> reports/phase1.md

phase1 reads reports/data/phase1_inventory.json, phase1_trial.json, phase1_knee.json, the designs table and the
staged catalogue, and writes the one-page report required by docs/PLAN.md Phase 1 (per suite: synthesizable count,
testbench count, knee-period distribution; RTLRewriter role table; spot-check curves; anomalies; next steps).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import collections  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import statistics  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.noise import stats as S  # noqa: E402

DATA = Path(ROOT) / "reports" / "data"


def load(name):
    p = DATA / name
    return json.loads(p.read_text()) if p.exists() else None


def fmt(x, nd=1):
    if x is None:
        return "-"
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def phase1(cfg):
    inv, trial, knee = load("phase1_inventory.json"), load("phase1_trial.json"), load("phase1_knee.json")
    conn = db.connect(cfg=cfg)
    designs = K.load_all()
    by_id = {d["design_id"]: d for d in designs}
    rows = {r["design_id"]: dict(r) for r in conn.execute("SELECT * FROM designs")}
    L = [f"# Phase 1 report — design sets and constraints", "",
         f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by scripts/report_phase.py (git {C.git_sha()}, cfg {C.cfg_hash()}). "
         "Data: reports/data/phase1_inventory.json, phase1_trial.json, phase1_knee.json; catalogue data/designs/<suite>/.", ""]
    # ---- sources
    L += ["## 1. Sources (PLAN 1.1)", "", "| suite | source | commit | license | staged | note |", "|---|---|---|---|---|---|"]
    for suite, s in cfg["design_sets"]["sources"].items():
        n = sum(1 for d in designs if d["suite"] == suite)
        L.append(f"| {suite} | {s['url']} | `{s['commit'][:10]}` | {s['license']} | {n} | {s.get('note') or '-'} |")
    L += ["", "RTL-OPT's anonymous repository named in the paper has expired (HTTP 410); the authors' public release is used (40 pairs, "
          "the proposal counted 36). Dr.RTL's 20 designs are public, so PLAN 1.1's substitution rule was not needed.", ""]
    # ---- inventory
    L += ["## 2. Inventory (PLAN 1.2)", ""]
    if inv:
        L += ["| suite | designs | loc (min / median / max) | Yosys ok | with testbench | combinational | multi-clock | SystemVerilog | DC markers |",
              "|---|---|---|---|---|---|---|---|---|"]
        for suite in sorted(inv["per_suite"]):
            ds = [d for d in inv["designs"] if d["suite"] == suite]
            locs = sorted(d["loc"] for d in ds)
            s = inv["per_suite"][suite]
            L.append(f"| {suite} | {s['designs']} | {locs[0]} / {locs[len(locs) // 2]} / {locs[-1]} | {s['yosys_ok']} | {s['tb']} | {s['no_clock']} | "
                     f"{s['multi_clock']} | {s['sverilog']} | {s['flagged']} |")
        L += ["", "DC markers = files with initial blocks, delay controls, system tasks, `include, `ifdef or `timescale (eda-knowledge/06-boundaries.md); "
              "they are informational, the E4 trial decides synthesizability. Clock ports are identified by use (Yosys flip-flop clock pins after "
              "flattening, src/designs/yosys_probe.py), not by name.", ""]
        multi = [d for d in inv["designs"] if "multi_clock" in d["tags"]]
        L += ["Multi-clock designs (inventoried and trial-synthesized with one clock per port, excluded from the knee sweeps and the search sets, DECISIONS 2026-09-12):", ""]
        L += [f"- {d['design_id']}: {' '.join(d['clk_ports'])}" for d in multi] + [""]
        failed = [d for d in inv["designs"] if not d["yosys_ok"]]
        L += ["Designs Yosys cannot parse (affects only the Y / O rungs and V1; DC is the arbiter):", ""]
        L += [f"- {d['design_id']}: {(d['yosys_error'] or '').splitlines()[0][:140]}" for d in failed] + [""]
    # ---- E4 trial
    L += ["## 3. E4 trial synthesis (PLAN 1.2)", ""]
    if trial:
        L += [f"Configuration {trial['config']} at {trial['clock_ns']} ns (loosest Nangate45 knee period), through the queue daemon.", "",
              "| suite | designs | synthesizable | failed | pending | DC hours |", "|---|---|---|---|---|---|"]
        for suite, s in sorted(trial["per_suite"].items()):
            L.append(f"| {suite} | {s['designs']} | {s['ok']} | {s['failed']} | {s['pending']} | {s['dc_seconds'] / 3600:.2f} |")
        n_rtllm = trial["per_suite"].get("rtllm", {}).get("ok")
        L += ["", f"RTLLM v2.0 synthesizable count N under this machine's DC E4: **{n_rtllm}** of 50.", ""]
        fails = [d for d in trial["designs"] if d["e4_synthesizable"] == 0]
        if fails:
            L += ["Failures and reasons:", ""] + [f"- {d['design_id']}: {d['e4_fail_reason']}" for d in fails] + [""]
        secs = sorted(float(d["dc_seconds"]) for d in trial["designs"] if d.get("dc_seconds"))
        if secs:
            L += [f"E4 seconds per design at the loosest period: min {secs[0]:.0f}, median {secs[len(secs) // 2]:.0f}, max {secs[-1]:.0f} (n = {len(secs)}).", ""]
    else:
        L += ["(not collected yet: scripts/phase1_collect.py trial)", ""]
    # ---- CktEvo pool
    pool = K.DESIGNS_DIR / "cktevo" / "POOL.json"
    if pool.exists():
        pj = json.loads(pool.read_text())
        total = sum(len(v) for v in pj["repos"].values())
        kept = {repo: [m for m in v if not m["excluded"]] for repo, v in pj["repos"].items()}
        L += ["## 4. CktEvo module pool", "",
              f"{total} modules scanned in {len(pj['repos'])} repositories; pool rule own_loc ≥ {pj['params']['loc_min']}, closure ≤ {pj['params']['closure_loc_max']} lines, "
              f"no testbench-like module, no duplicated module name (DECISIONS 2026-09-12). Pool: {sum(len(v) for v in kept.values())} modules "
              f"({', '.join(f'{r} {len(v)}' for r, v in sorted(kept.items()))}). The ~30-module set and the 8-module Sky130 subset (PLAN 1.5) are chosen after the knee sweep.", ""]
    # ---- RTLRewriter roles
    rw = [d for d in designs if d["suite"] == "rtlrewriter"]
    if rw:
        roles = collections.Counter()
        for d in rw:
            roles["original"] += 1
            roles["expert"] += int(bool(d["reference"]))
            for s in d.get("samples") or []:
                roles[s["role"]] += 1
        L += ["## 5. RTLRewriter-Bench (calibration only)", "",
              f"{len([d for d in rw if 'short' in d['tags']])} short cases and {len([d for d in rw if 'long' in d['tags']])} long module pairs staged; "
              f"file roles by the rule in src/designs/rtlrewriter.py: {dict(sorted(roles.items()))} "
              "(original = start point, expert = engineers' rewrite, tool = RTLRewriter output, llm = GPT-4 / Claude 3 / RTLCoder / VeriGen samples). "
              "Role table for the hand check (start = the staged original, reference = expert version, samples = the rest):", "",
              "| design | start file | reference | samples (role) |", "|---|---|---|---|"]
        for d in rw:
            ref = d["reference"]["files"][0].split("/")[-1] if d["reference"] else "-"
            samples = ", ".join(f"{s['files'][0].split('/')[-1]} ({s['role']})" for s in d.get("samples") or []) or "-"
            L.append(f"| {d['name']} | {d['files'][0].split('/')[-1]} | {ref} | {samples} |")
        L.append("")
    # ---- knee
    L += ["## 6. Knee-point constraints (PLAN 1.3)", ""]
    if knee:
        L += ["| library | designs swept | complete sweeps | with Φ_main | fallback (no period met) | Φ_main histogram (ns: designs) |", "|---|---|---|---|---|---|"]
        for lib, s in sorted(knee["per_lib"].items()):
            hist = ", ".join(f"{k}: {v}" for k, v in sorted(s["phi_hist"].items(), key=lambda kv: -float(kv[0])))
            L.append(f"| {lib} | {s['designs']} | {s['complete']} | {s['with_phi']} | {s['fallback']} | {hist} |")
        L += ["", f"Rule (spec 01 §3): candidates = periods with WNS ≥ −{knee['params']['slack_tol']}·T; tightest T with area ≤ (1 + {knee['params']['area_tol']}) × area(T_loosest); "
              "empty candidate set → smallest violation, `fallback`.", ""]
        # spot checks: five designs of different suites, area-period curves
        picks = []
        for suite in ("rtllm", "drrtl", "rtlopt", "cktevo", "rtlrewriter"):
            for rec in knee["designs"]:
                if rec["suite"] == suite and rec["table"].get("nangate45", {}).get("complete"):
                    picks.append(rec)
                    break
        if picks:
            L += ["Spot-check curves (Nangate45, area in µm² / WNS in ns per period; Φ marked with *):", ""]
            periods = [float(p) for p in knee["params"]["periods_ns"]["nangate45"]]
            L += ["| design | " + " | ".join(f"{p:g} ns" for p in periods) + " |", "|---|" + "---|" * len(periods)]
            for rec in picks:
                t = rec["table"]["nangate45"]
                cells = []
                for p in periods:
                    pt = next((x for x in t["points"] if abs(x["T"] - p) < 1e-6), None)
                    cells.append("-" if pt is None else f"{pt['area']:.0f} / {pt['wns']:.2f}" + ("*" if t["phi"] == p else ""))
                L.append(f"| {rec['design_id']} | " + " | ".join(cells) + " |")
            L.append("")
        hand = DATA / "phase1_handcheck.md"
        if hand.exists():
            L += [hand.read_text().strip(), ""]
    else:
        L += ["(not collected yet: scripts/phase1_collect.py knee)", ""]
    # ---- designs table completeness
    L += ["## 7. designs table (acceptance check)", ""]
    n = len(rows)
    complete = sum(1 for r in rows.values() if r["e4_synthesizable"] is not None and r["loc"] and r["suite"] and r["path"])
    with_phi = sum(1 for r in rows.values() if r["phi_main_ns_nangate45"] is not None)
    split = collections.Counter(r["split"] for r in rows.values())
    L += [f"{n} rows; {complete} with suite / path / loc / tb_available / e4_synthesizable filled; {with_phi} with Φ_main(nangate45); split: {dict(split)}.", ""]
    L += ["## 8. Anomalies and next steps", "",
          "- Anomalies are listed in sections 2 and 3 (Yosys parse failures, DC failures with reasons, multi-clock designs).",
          "- Next: knee sweeps for every synthesizable single-clock design (PLAN 1.3), dev / held split (1.4), CktEvo set and Sky130 subset (1.5), then Phase 2.", ""]
    out = Path(ROOT) / "reports" / "phase1.md"
    out.write_text("\n".join(L))
    print(f"wrote {out}")
    return 0


def _quantiles(xs):
    xs = sorted(xs)
    if not xs:
        return None
    q = lambda f: xs[min(len(xs) - 1, int(round(f * (len(xs) - 1))))]
    return {"n": len(xs), "min": xs[0], "q25": q(0.25), "median": q(0.5), "q75": q(0.75), "q95": q(0.95), "max": xs[-1], "mean": sum(xs) / len(xs)}


def phase2(cfg):
    """Noise floor (G1), perturbation generator and SEQ gate statistics (part of G2), E4 runtime and DC-hour estimates (G3)."""
    conn = db.connect(cfg=cfg)
    perts = load("phase2_perturbations.json")
    floor = load("phase2_noise_floor.json")
    rows = {r["design_id"]: dict(r) for r in conn.execute("SELECT * FROM designs")}
    L = [f"# Phase 2 report — noise floor, SEQ pilot, E4 runtime (Exp0)", "",
         f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by scripts/report_phase.py (git {C.git_sha()}, cfg {C.cfg_hash()}). "
         "Hidden-configuration floors (H1 / H2a / H2b / H5, H3) live in the hidden database and appear only in the hidden report after Phase 5.", ""]
    # ---- generator
    L += ["## 1. Perturbation generator (PLAN 2.1)", ""]
    manifests = []
    for mp in sorted((Path(ROOT) / "data" / "perturbations").glob("*/manifest.json")):
        try:
            manifests.append(json.loads(mp.read_text()))
        except json.JSONDecodeError:
            continue
    if manifests:
        per_type, not_app = collections.Counter(), collections.Counter()
        errors = []
        for m in manifests:
            if m.get("error"):
                errors.append(m["design_id"])
            for e in m.get("perturbations") or []:
                per_type[e["ptype"]] += 1
            for pt in (m.get("not_applicable") or {}):
                not_app[pt] += 1
        L += [f"{len(manifests)} designs with a generator manifest (sets + RTLRewriter); perturbations per type {dict(sorted(per_type.items()))}; "
              f"designs where a type is not applicable {dict(sorted(not_app.items()))}; designs Pyverilog cannot parse: {len(errors)} ({', '.join(errors)}).", ""]
    gate = collections.Counter((r["ptype"], r["seq_status"]) for r in conn.execute("SELECT ptype, seq_status FROM perturbations"))
    if gate:
        statuses = sorted({s for _, s in gate})
        L += ["SEQ gate (V1 -> V2 -> V3; only `proven` enters the floor):", "", "| type | " + " | ".join(statuses) + " | non-equivalence rate |",
              "|---|" + "---|" * (len(statuses) + 1)]
        for ptype in sorted({p for p, _ in gate}):
            counts = {s: gate.get((ptype, s), 0) for s in statuses}
            total = sum(counts.values())
            bad = counts.get("falsified", 0) + counts.get("sim_fail", 0) + counts.get("rejected", 0)
            L.append(f"| {ptype} | " + " | ".join(str(counts[s]) for s in statuses) + f" | {bad / total:.1%} of {total} |")
        L.append("")
    # ---- noise floor
    L += ["## 2. Noise floor sigma_D (PLAN 2.3, visible configurations)", ""]
    if floor and floor.get("summary"):
        L += ["| config | metric | designs | median sigma | q75 | max |", "|---|---|---|---|---|---|"]
        warn = float(cfg["noise"]["sigma_median_warn_pct"]) / 100
        for config, ms in sorted(floor["summary"].items()):
            for m, s in sorted(ms.items()):
                flag = " **(above the G1 warning level)**" if m == "area" and s["median"] > warn else ""
                L.append(f"| {config} | {m} | {s['n']} | {s['median']:.4f}{flag} | {s['q75']:.4f} | {s['max']:.4f} |")
        L += ["", f"Minimum reportable gain under the spec's original rule = {cfg['noise']['k_sigma']} x sigma_D (config noise.k_sigma); per-design values in the noise_floor table and reports/data/phase2_noise_floor.json.", ""]
        if floor.get("summary_t_d"):
            L += [f"**Rule A** (DECISIONS 2026-09-14): t_D = max({cfg['noise']['k_sigma']} x sigma_robust, the design's own max |delta| incl. P0, pooled q{int(100 * float(cfg['noise'].get('pooled_quantile', 0.9)))}); designs without a measured floor carry the pooled minimum (floor_source = pooled).", "",
                  "| config | metric | designs | pooled minimum | median t_D | q75 | max |", "|---|---|---|---|---|---|---|"]
            for config, ms in sorted(floor["summary_t_d"].items()):
                for m, s in sorted(ms.items()):
                    pm = (floor.get("pooled_min") or {}).get(config, {}).get(m)
                    L.append(f"| {config} | {m} | {s['n']} | {pm:.4f} | {s['median']:.4f} | {s['q75']:.4f} | {s['max']:.4f} |" if pm is not None else
                             f"| {config} | {m} | {s['n']} | - | {s['median']:.4f} | {s['q75']:.4f} | {s['max']:.4f} |")
            L.append("")
        if floor.get("floor_classes"):
            L += ["Floor classes per configuration (quiet / spread / offset; pooled = no measured floor, the pooled minimum applies; none = not a set design):", "",
                  "| config | " + " | ".join(("quiet", "spread", "offset", "pooled", "none")) + " |", "|---|---|---|---|---|---|"]
            for config, cl in sorted(floor["floor_classes"].items()):
                L.append(f"| {config} | " + " | ".join(str(cl.get(k, 0)) for k in ("quiet", "spread", "offset", "pooled", "none")) + " |")
            L.append("")
    else:
        L += ["(not collected yet: scripts/phase2_noise.py collect)", ""]
    # ---- G1 analysis: how the floors are distributed, which perturbation types change the netlist, monotonicity of D
    k = float(cfg["noise"]["k_sigma"])
    configs = (floor or {}).get("configs") or [c for c in cfg["noise"]["configs"] if not cfg["configs"][c].get("hidden")]
    set_designs = [{"design_id": r["design_id"], "phi": float(r["phi_main_ns_nangate45"])} for r in conn.execute(
        "SELECT design_id, phi_main_ns_nangate45 FROM designs WHERE split IN ('dev', 'held') AND phi_main_ns_nangate45 IS NOT NULL ORDER BY design_id")]
    proven = S.proven_by_design(conn)
    fa = S.floor_analysis(conn, set_designs, configs, proven, k, pooled_q=float(cfg["noise"].get("pooled_quantile", 0.9)), weighting=cfg["noise"].get("pooled_weighting", "design"))
    if fa:
        L += ["### 2a. Floor distribution on the set designs (dev + held)", "",
              "| config | metric | designs with floor | sigma_robust = 0 | sigma_std = 0 | max abs delta > 1 % | > 5 % | pooled q90 (design-weighted, rule A) | pooled q90 (record-weighted, rejected) | pooled q95 | pooled q99 | pooled max | rule-A t_D median / q95 / max | designs above the minimum |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for (config, m), a in sorted(fa.items()):
            tp = a["t_proposed"] or {}
            L.append(f"| {config} | {m} | {a['designs']} | {a['zero_robust']} | {a['zero_std']} | {a['max_abs_gt']['1pct']} | {a['max_abs_gt']['5pct']} | "
                     f"{a['pooled']['q90']:.4f} | {a['pooled']['q90_record_weighted']:.4f} | {a['pooled']['q95']:.4f} | {a['pooled']['q99']:.4f} | {a['pooled']['max']:.4f} | "
                     f"{tp.get('median', 0):.4f} / {tp.get('q95', 0):.4f} / {tp.get('max', 0):.4f} | {tp.get('above_pooled_min', 0)} |")
        L += ["", f"Rule A (adopted 2026-09-14): t_D = max({k:.0f} x sigma_robust, max |delta| over D's own proven perturbations including the re-print, the design-weighted pooled q90 of |delta| of the configuration); "
              "every design weighs equally in the pooled quantile so that the minimum floor does not depend on how many perturbations a design received (the record-weighted q90 is shown as the rejected sensitivity variant: it rose from 0.29 % to 1.43 % area when the spread / offset designs got twice their perturbations). The spec's 2 x sigma_robust stays in the table above for the sensitivity report.", ""]
    rates = S.ptype_change_rates(conn, set_designs, configs, proven)
    if rates:
        pts = sorted({pt for _, pt in rates})
        L += ["### 2b. Perturbation types that change the netlist (area or cell count of D differs)", "",
              "| config | " + " | ".join(pts) + " |", "|---|" + "---|" * len(pts)]
        for config in configs:
            cells = []
            for pt in pts:
                e = rates.get((config, pt))
                cells.append(f"{e['changed']} / {e['n']} ({100 * e['changed'] / e['n']:.0f} %)" if e and e["n"] else "-")
            L.append(f"| {config} | " + " | ".join(cells) + " |")
        L.append("")
    mono = S.monotonicity(conn, set_designs, configs)
    if mono["n"]:
        L += [f"### 2c. Monotonicity of D across the rungs ({mono['n']} set designs with every rung at Φ_main)", "",
              "| step | designs whose area grows | designs whose WNS drops |", "|---|---|---|"]
        for (a, b), e in mono["steps"].items():
            L.append(f"| {a} -> {b} | {e['area_up']} | {e['wns_down']} |")
        L += ["", "WNS is compared at Φ_main (the E4 knee): once a rung meets timing, area recovery legitimately trades slack, so a WNS drop between two rungs that both meet timing is not a regression.", ""]
    # ---- E4 runtime
    L += ["## 3. E4 runtime (PLAN 2.5)", ""]
    secs = {}
    for r in conn.execute("SELECT e.design_id, e.dc_seconds, d.suite, d.split FROM evaluations e JOIN designs d ON d.design_id = e.design_id "
                          "WHERE e.config='E4' AND e.is_baseline=1 AND e.pert_id IS NULL AND e.cand_id IS NULL AND e.status='ok' "
                          "AND abs(e.clock_ns - d.phi_main_ns_nangate45) < 1e-6 AND d.split IN ('dev', 'held')"):
        secs[r["design_id"]] = (float(r["dc_seconds"]), r["suite"])
    if secs:
        q = _quantiles([s for s, _ in secs.values()])
        L += [f"E4 seconds at Phi_main (Nangate45) over {q['n']} set designs: min {q['min']:.0f}, q25 {q['q25']:.0f}, median {q['median']:.0f}, q75 {q['q75']:.0f}, q95 {q['q95']:.0f}, max {q['max']:.0f}, mean {q['mean']:.0f}.", ""]
        sc = cfg["scale"]
        per_design = sum(s for s, _ in secs.values()) / len(secs)
        full_e4_runs = sc["starting_points"] * len(sc["arms"]) * sc["seeds"] * sc["N"] * sc["K"]
        L += [f"Scale (config `scale`): {sc['starting_points']} starting points x {len(sc['arms'])} arms x {sc['seeds']} seeds x N={sc['N']} x K={sc['K']} = {full_e4_runs} candidate evaluations.",
              f"- full-E4 scale: {full_e4_runs * per_design / 3600:.0f} DC hours at the mean t_E4 ({per_design:.0f} s); at 12 concurrent runs ≈ {full_e4_runs * per_design / 3600 / 12:.0f} h wall, at 50 seats ≈ {full_e4_runs * per_design / 3600 / 50:.0f} h.",
              f"- per-design budget rule k_e4_equiv = {sc['budget']['k_e4_equiv']} x t_E4(D): median budget {sc['budget']['k_e4_equiv'] * q['median'] / 3600:.1f} DC hours per run.", ""]
        # cascade scale: screening rung ES (E1 or E2 at Φ_main, times from the noise baselines) on every candidate, a fraction p promoted to E4
        t_es = {}
        for es in ("E1", "E2"):
            for r in conn.execute("SELECT e.design_id, e.dc_seconds FROM evaluations e JOIN designs d ON d.design_id = e.design_id "
                                  "WHERE e.config=? AND e.is_baseline=1 AND e.pert_id IS NULL AND e.cand_id IS NULL AND e.status='ok' "
                                  "AND abs(e.clock_ns - d.phi_main_ns_nangate45) < 1e-6 AND d.split IN ('dev', 'held') ORDER BY e.eval_id", (es,)):
                t_es.setdefault(es, {})[r["design_id"]] = float(r["dc_seconds"])
        cheap = float(cfg["screen"]["e4_cheap_sec"])
        big = {d: s for d, (s, _) in secs.items() if s >= cheap}
        L += [f"Screening economics (config `screen`): E4 is 'cheap' below {cheap:.0f} s; {len(big)} of {len(secs)} set designs are above that "
              f"(their mean t_E4 = {(sum(big.values()) / len(big)) if big else 0:.0f} s). Mean screening-rung seconds at Φ_main over the designs with both: "
              + ", ".join(f"{es} {sum(v for d, v in t_es[es].items() if d in secs) / max(1, sum(1 for d in t_es[es] if d in secs)):.0f} s" for es in sorted(t_es))
              + "; over the non-cheap designs alone: " + ", ".join(f"{es} {sum(v for d, v in t_es[es].items() if d in big) / max(1, sum(1 for d in t_es[es] if d in big)):.0f} s" for es in sorted(t_es))
              + f" against t_E4 {(sum(big.values()) / len(big)) if big else 0:.0f} s (a DC screening rung at Φ_main is not cheaper than E4 where E4 is expensive).", "",
              "| cascade (ES on every candidate, p promoted to E4) | all designs, DC hours | wall at 50 seats | hybrid: cheap designs straight to E4, only non-cheap designs screened |", "|---|---|---|---|"]
        for es in sorted(t_es):
            common = [d for d in secs if d in t_es[es]]
            if not common:
                continue
            for p in (0.1, 0.25, 0.5):
                per = sum(t_es[es][d] + p * secs[d][0] for d in common) / len(common)
                per_hybrid = sum((t_es[es][d] + p * secs[d][0]) if d in big else secs[d][0] for d in common) / len(common)
                hours = full_e4_runs * per / 3600
                hours_hybrid = full_e4_runs * per_hybrid / 3600
                full = full_e4_runs * per_design / 3600
                L.append(f"| ES = {es}, p = {p:.2f} | {hours:.0f} ({100 * hours / full:.0f} % of full-E4) | {hours / 50:.0f} h | {hours_hybrid:.0f} ({100 * hours_hybrid / full:.0f} %) |")
        L.append("")
        by_suite = {}
        for s, suite in secs.values():
            by_suite.setdefault(suite, []).append(s)
        L += ["| suite | designs | median t_E4 (s) | max t_E4 (s) |", "|---|---|---|---|"]
        for suite, xs in sorted(by_suite.items()):
            qq = _quantiles(xs)
            L.append(f"| {suite} | {qq['n']} | {qq['median']:.0f} | {qq['max']:.0f} |")
        L.append("")
    else:
        L += ["(no E4 baseline at Phi_main yet: run scripts/phase2_noise.py submit)", ""]
    L += ["## 4. SEQ pilot (PLAN 2.4) and t_H3 / t_E4", ""]
    pilot = load("phase2_pilot.json")
    if pilot:
        L += [f"Candidates: hand-made variants (CLAUDE.md exception 2), RTL-OPT pairs with a changed flip-flop count, and the LLM batch; every candidate ran V1 -> V2 -> V3 with random seeds {pilot['seeds']}.", "",
              "| requested class | n | verdicts (seed 1) | median V3 seconds |", "|---|---|---|---|"]
        for cls, s in sorted(pilot["per_class"].items()):
            secs = sorted(s["v3_seconds"])
            L.append(f"| {cls} | {s['n']} | {s['verdicts']} | {secs[len(secs) // 2] if secs else '-'} |")
        agree = [c for c in pilot["candidates"] if isinstance(c.get("class_rule"), dict) and c["class_rule"].get("class_rule")]
        if agree:
            same = sum(1 for c in agree if c["class_rule"]["class_rule"] == c["class"])
            L += ["", f"M6 rule class vs requested class: {same} of {len(agree)} agree (LLM answers often deliver another class than instructed; the rule class is what the protocol uses)."]
        g3 = pilot.get("guardrail3") or []
        L += ["", f"Guardrail-3 facts for the {len(g3)} SEQ-inconclusive candidates (clocked arithmetic / offsets constant across seeds / start-done signals):", ""]
        L += [f"- {x['design_id']} {x['file']}: arithmetic={x['clocked_arithmetic']}, offsets_constant={x['offsets_constant']}, start-like={x['start_like_ports']}, done-like={x['done_like_ports']}" for x in g3[:40]] + [""]
    else:
        L += ["(pilot not collected yet: scripts/phase2_pilot.py collect --classify)", ""]
    lat = load("phase2_pilot_latency.json")
    if lat:
        L += ["### 4b. SEQ latency mapping of the class-(c2) pilot candidates (DECISIONS 2026-09-14 G2.1 (b), implemented 2026-09-15)", "",
              "Each candidate whose lock-step simulation found constant per-output offsets (verdict `proven_sim_only` under the by-name mapping) was re-run with the outputs asserted at those offsets "
              "(`map_by_name -input`, `seq_assert spec.o impl.o -clock spec.clk -latency1 0 -latency2 k`; config `equiv.seq_latency_mapping`). "
              f"Seeds {lat['seeds']}; verdict counts of the first seed: " + ", ".join(f"{k} {v}" for k, v in sorted(lat["summary"].items())) + ".", "",
              "| design | candidate | offsets | by-name verdict | mapped verdicts (seeds) | V3 s |", "|---|---|---|---|---|---|"]
        for r in lat["candidates"]:
            L.append(f"| {r['design_id']} | {r['file']} | {json.dumps(r['offsets'], sort_keys=True)} | {r['by_name_verdict']} | {', '.join(str(v) for v in r['mapped_verdicts'])} | {', '.join(str(round(float(x), 1)) for x in r['v3_seconds'] if x is not None)} |")
        L.append("")
    g3s = load("phase2_g3.json")
    if g3s and g3s.get("n_designs_with_ratio"):
        tr = g3s["t_ratio"]
        L += [f"t_H3 / t_E4 (baseline runs of the same design at Φ_main, {g3s['n_designs_with_ratio']} designs; hidden worker, counts and seconds only): "
              f"median {tr['median']:.2f}, quartiles {tr['q25']:.2f}–{tr['q75']:.2f}, range {tr['min']:.2f}–{tr['max']:.2f}; "
              f"total {g3s['e4_seconds_total'] / 3600:.1f} DC hours under E4 vs {g3s['h3_seconds_total'] / 3600:.1f} under H3.", ""]
        if g3s.get("pairs"):
            conf = ", ".join(f"{k}: {v}" for k, v in sorted(g3s["confusion"].items()))
            L += [f"E4-vs-H3 agreement of the four-way floor conclusion (retained / trade-off / harmful / noise at {g3s['k_sigma']:.0f} σ_D of each configuration) "
                  f"per perturbation with records under both: {g3s['agree']} of {g3s['pairs']} ({100 * g3s['agreement_rate']:.1f} %). Confusion counts: {conf}.", ""]
            ch = g3s.get("area_change") or {}
            if ch:
                both = ch.get("both changed", 0)
                L += [f"Whether the perturbation changed the netlist at all (|delta area| > 0.1 %): both unchanged {ch.get('both unchanged', 0)}, both changed {both} "
                      f"(same direction in {g3s.get('both_changed_same_direction', 0)}), changed under E4 only {ch.get('E4 only', 0)}, under H3 only {ch.get('H3 only', 0)}.", ""]
    else:
        L += ["t_H3 / t_E4 and the E4-vs-H3 agreement rate come from the hidden worker as counts and seconds only (scripts/hidden_worker.py --g3-summary after the H3 noise runs).", ""]
    L += ["## 5. Next steps", "", "- G1: decide on the truncation if the median area floor exceeds the warning level.", "- G2: SEQ fractions per class from the pilot.", "- G3: screening recommendation from the E4 seconds and the cascade estimate.", ""]
    concl = Path(ROOT) / "reports" / "phase2_conclusions.md"
    if concl.exists():
        L += [concl.read_text().rstrip("\n"), ""]
    out = Path(ROOT) / "reports" / "phase2.md"
    out.write_text("\n".join(L))
    print(f"wrote {out}")
    return 0


def phase3(cfg):
    """LLM calibration (PLAN 3.4 / 3.5): per-model table, confusion matrices, retention with the materiality row, best gains,
    efficiency, time-to-verdict, the decision rule, and the diagnoser's label distribution."""
    data = load("phase3_calibration.json")
    L = [f"# Phase 3 report — LLM calibration (residual-guided evolution, minimal skeleton)", "",
         f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by scripts/report_phase.py (git {C.git_sha()}, cfg {C.cfg_hash()}). Data: reports/data/phase3_calibration.json (scripts/phase3_calibrate.py collect).", ""]
    if not data:
        L += ["(not collected yet: scripts/phase3_calibrate.py collect)", ""]
    else:
        cal = cfg["llm"]["calibration"]
        L += ["## 1. Setup", "", f"Models {cfg['llm']['candidates']}; designs (dev split only, DECISIONS 2026-09-14) × {cal['seeds']} seeds; K = {cal['K']} generations × N = {cal['N']} candidates per run; "
              f"arm M without synthesis-rung screening and without a map prior; pipeline V1 → V2 (zero initial state) → V3 SEQ (class-aware caps) → E4 → diagnosis (rule-A floors). Budget caliber: equal LLM calls.", "",
              "## 2. Per-model results", "",
              "| model | runs | candidates | unusable answers | V1 ok | V3 proven | proven_sim_only (apart) | inconclusive | retained (rule A) | retained (materiality row) | LLM calls / retained | USD / retained | DC h / retained | USD | DC h | VCF h |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for mo, v in sorted(data["models"].items()):
            ret = v["retained"]
            cpr = v["llm_calls_per_retained"]
            L.append(f"| {mo} | {v['runs']} | {v['cands']} | {v['unusable']} | {v['v1_ok']} | {v['v3_proven']} | {v['proven_sim_only']} | {v['inconclusive']} | {ret} | {v['retained_material']} | "
                     f"{'-' if cpr is None else f'{cpr:.1f}'} | {(v['usd'] / ret) if ret else float('nan'):.3f} | {(v['dc_h'] / ret) if ret else float('nan'):.2f} | {v['usd']:.2f} | {v['dc_h']:.2f} | {v['vcf_h']:.2f} |")
        L.append("")
        L += ["## 3. Classes: produced distribution and requested → produced confusion", ""]
        for mo, v in sorted(data["models"].items()):
            conf = ", ".join(f"{k}: {n}" for k, n in sorted(v["confusion"].items()))
            L += [f"- **{mo}**: produced classes {dict(sorted(v['classes'].items()))}; confusion {conf}; labels {dict(sorted(v['labels'].items()))}; "
                  f"inconclusive rate by class {{{', '.join(f'{c}: {100 * r:.0f} %' for c, r in sorted(v['inconclusive_rate_by_class'].items()))}}}"]
        L += ["", "## 4. Best retained area gain per design (offset designs flagged)", "", "| model | " + " | ".join(sorted({d for v in data["models"].values() for d in v["best_gain"]})) + " |"]
        designs = sorted({d for v in data["models"].values() for d in v["best_gain"]})
        L.append("|---|" + "---|" * len(designs))
        for mo, v in sorted(data["models"].items()):
            cells = []
            for d in designs:
                b = v["best_gain"].get(d)
                cells.append("-" if not b else f"{100 * b['area']:.2f} %" + (" (offset design)" if b.get("offset_design") else ""))
            L.append(f"| {mo} | " + " | ".join(cells) + " |")
        L += ["", "## 5. Time to verdict (seconds from the LLM answer to the equivalence verdict) and the response to absorbed feedback", ""]
        for mo, v in sorted(data["models"].items()):
            ttv = "; ".join(f"{c}: n={t['n']} median {t['median']:.0f} q95 {t['q95']:.0f} max {t['max']:.0f}" for c, t in sorted(v["time_to_verdict"].items()))
            L.append(f"- **{mo}**: {ttv or 'no verdicts'}")
        fr = data.get("feedback_response") or {}
        if fr:
            L += ["", "Feedback response (DECISIONS 2026-09-14 b): absorbed_identical rate among candidates whose lineage feedback carried an absorbed verdict versus candidates whose feedback did not, per generation:", "",
                  "| model | generation | with absorbed feedback: absorbed_identical / n | without: absorbed_identical / n |", "|---|---|---|---|"]
            for mo, gens in sorted(fr.items()):
                for g, kinds in sorted(gens.items(), key=lambda kv: int(kv[0])):
                    w, wo = kinds.get("with_absorbed_feedback"), kinds.get("without")
                    L.append(f"| {mo} | {g} | {f'{w[chr(97)+chr(98)+chr(115)+chr(111)+chr(114)+chr(98)+chr(101)+chr(100)+chr(95)+chr(105)+chr(100)+chr(101)+chr(110)+chr(116)+chr(105)+chr(99)+chr(97)+chr(108)]} / {w[chr(110)]} ({100 * w[chr(114)+chr(97)+chr(116)+chr(101)]:.0f} %)' if w else '-'} | {f'{wo[chr(97)+chr(98)+chr(115)+chr(111)+chr(114)+chr(98)+chr(101)+chr(100)+chr(95)+chr(105)+chr(100)+chr(101)+chr(110)+chr(116)+chr(105)+chr(99)+chr(97)+chr(108)]} / {wo[chr(110)]} ({100 * wo[chr(114)+chr(97)+chr(116)+chr(101)]:.0f} %)' if wo else '-'} |")
        vp = data.get("vcf_projection") or {}
        if vp:
            L += ["", "## 5c. Phase 5 VC Formal projection (DECISIONS 2026-09-14 e)", "",
                  f"Model {vp['model']}: {vp['phase3_calls']} Phase 3 calls consumed {3600 * 0 + sum(c['hours'] for k in vp['by_type_and_class'].values() for c in k.values()):.1f} SEQ hours ({vp['seq_seconds_per_call']:.0f} s per LLM call; arithmetic pipelines {vp['seq_seconds_per_call_by_type']['arith_pipeline']:.0f} s, other designs {vp['seq_seconds_per_call_by_type']['other']:.0f} s per call). "
                  f"Phase 5 at the planned scale ({vp['phase5_runs']} runs, {vp['phase5_calls']} calls; starting pool {vp['starting_pool']} held designs of which {100 * vp['share_arith_pipeline_in_pool']:.0f} % arithmetic pipelines by name): "
                  f"**{vp['projected_vcf_hours']:.0f} VC Formal hours** by design-type mix ({vp['projected_vcf_hours_flat_mix']:.0f} h with the calibration's own mix); threshold {vp['threshold_hours']} h.", ""]
            for k, d in vp["by_type_and_class"].items():
                L.append(f"- {k}: " + "; ".join(f"class {cls}: n={c['n']}, median {c['median_s']:.0f} s, q95 {c['q95_s']:.0f} s, {c['hours']:.1f} h" for cls, c in sorted(d.items())))
            L.append("")
            L += [f"Method: every Phase 3 SEQ verdict of the main model is binned by produced class (rules v2) and design type (arithmetic pipelines by name — `pipe`, `mult`, `div` — versus the rest); "
                  f"the per-call SEQ seconds of each design type (the type's total verdict seconds over its LLM calls) are combined with the design-type share of the Phase 5 starting pool "
                  f"({vp['starting_pool']} held designs, {100 * vp['share_arith_pipeline_in_pool']:.0f} % arithmetic pipelines) and multiplied by the planned {vp['phase5_calls']} calls; the flat-mix figure applies the calibration's own mix instead. "
                  f"Decision (2026-09-14 item 2): accepted as is — {vp['projected_vcf_hours']:.0f} h at 50 seats is ≈ {vp['projected_vcf_hours'] / 50:.0f} h of wall-clock; the class caps and the pipeline share of the starting pool are not changed; "
                  f"Phase 5 proofs run in bulk mode at 50 seats; the SEQ latency mapping (G2.1(b)) stays on the critical path before Phase 5 and the DPV phase mapping follows it; within a generation the (c1) / (d) proofs on arithmetic designs are submitted first (config `search.long_proof_first`).", ""]
            if vp["projected_vcf_hours"] > float(vp["threshold_hours"]) and vp.get("projected_vcf_hours_with_cap") is not None:
                L += [f"**Addendum (DECISIONS 2026-09-14 e, the projection exceeds {vp['threshold_hours']} h — proposal for the user, nothing changed):** "
                      f"(1) lower the SEQ class caps of arithmetic pipelined designs to {vp['proposal_cap_hours']:.0f} h for (c1) and (d) (config `equiv.seq_cap_min_by_class` would need a per-design-type entry; "
                      f"today's caps are 4 h): {vp['arith_c1d_over_cap']} of the {vp['arith_c1d_verdicts']} Phase 3 (c1) / (d) verdicts on the arithmetic pipeline ran longer than {vp['proposal_cap_hours']:.0f} h and would become "
                      f"`inconclusive` (never discarded, C2.5); the projection drops to **{vp['projected_vcf_hours_with_cap']:.0f} h** at the planned scale, so the cap alone does not reach the threshold — "
                      f"the verdict distribution of the pipeline is bimodal (30–40 s or hours) and the hours sit in the proofs that finish under the cap as well. "
                      f"(2) Prioritise the SEQ latency mapping (G2.1(b)) and a DPV phase mapping for fixed-latency arithmetic pipelines before Phase 5: the pipeline's (c1) / (d) rewrites are "
                      f"fixed-latency datapaths where DPV's transaction equivalence needs no state-space search; this is the engineering item that removes the hours, the cap only bounds them. "
                      f"(3) Alternatively reduce the arithmetic-pipeline share of the Phase 5 starting pool ({100 * vp['share_arith_pipeline_in_pool']:.0f} % by name) — a design-set decision for the user. "
                      f"The no-discard timeout policy is unchanged either way.", ""]
        ls = data.get("label_sensitivity") or {}
        if ls:
            pm = ls.get("_pooled_min") or {}
            L += ["", "## 5a. Verdict sensitivity: stored (run-time) floors vs rule A design-weighted (adopted) vs record-weighted (rejected) vs materiality", "",
                  "Every E4-evaluated candidate re-diagnosed offline (no tool runs; archived in reports/data/phase3_label_sensitivity.json). "
                  f"Pooled E4 minima: design-weighted area {100 * (pm.get('design_weighted') or {}).get('area', 0):.2f} % / power {100 * (pm.get('design_weighted') or {}).get('power_saif', 0):.2f} %; "
                  f"record-weighted area {100 * (pm.get('record_weighted') or {}).get('area', 0):.2f} % / power {100 * (pm.get('record_weighted') or {}).get('power_saif', 0):.2f} % (DECISIONS 2026-09-14: the record-weighted minimum follows the number of perturbations per design and was rejected).", "",
                  "| model | E4-evaluated | stored: retained / tradeoff / absorbed_identical / noise / harmful | design-weighted: same | record-weighted: same | materiality: same |", "|---|---|---|---|---|---|"]
            keys = ("retained", "tradeoff", "absorbed_identical", "noise", "harmful")
            for mo, v in sorted((k, v) for k, v in ls.items() if not k.startswith("_")):
                cells = [" / ".join(str(v[which].get(k, 0)) for k in keys) for which in ("stored", "design_weighted", "record_weighted", "materiality")]
                L.append(f"| {mo} | {v['n']} | " + " | ".join(cells) + " |")
            fl = ls.get("_floors") or {}
            L += ["", "Rule-A t_D per calibration design under the adopted design-weighted minimum (area / WNS as a fraction of the period / power): " + "; ".join(
                f"{d}: {100 * (f['design_weighted_t_d'].get('area') or 0):.2f} % / {100 * (f['design_weighted_t_d'].get('wns') or 0):.2f} % / {100 * (f['design_weighted_t_d'].get('power') or 0):.2f} % ({f['class']})" for d, f in sorted(fl.items())), ""]
        ya = data.get("y_auroc") or {}
        if ya.get("auroc_area") is not None:
            L += ["", "## 5b. Y (Yosys + OpenSTA) as a screen for E4 retention", "",
                  f"AUROC of the Y area gain for E4 retention over {ya['n_retained']} retained vs {ya['n_other']} other diagnosed candidates: {ya['auroc_area']:.3f}; "
                  f"best-of-three-components gain: {ya['auroc_best_component']:.3f}; threshold `screen.auroc_min` = {cfg['screen']['auroc_min']} "
                  f"({'Y qualifies as the M_noscreen screen' if ya['auroc_area'] >= float(cfg['screen']['auroc_min']) else 'Y does not qualify: the M_noscreen arm is dropped and its budget goes to starting points (DECISIONS 2026-09-14 G3.1)'}).", ""]
        dec = data["decision"]
        L += ["", "## 6. Decision rule (config llm.calibration.decision)", "",
              f"Primary metric {dec['primary_metric']}: scores {dict((k, round(v, 3)) for k, v in dec['scores'].items())}; best area gain per model {dict((k, round(100 * v, 2)) for k, v in dec['best_gain_by_model'].items())} %; "
              f"eligible (best gain ≥ {cfg['llm']['calibration']['decision']['floor_best_gain_ratio']} × strongest, a retained (c1) or (d)): {dec['eligible']}; **recommended: {dec['recommended']}** — {dec['note']}", ""]
    m6 = load("phase3_m6_agreement.json")
    if m6:
        classes = ("a", "b", "c1", "c2", "d")
        L += ["", "## 6a. M6 manual validation and the rules-v2 classifier (DECISIONS 2026-09-14 a)", "",
              f"{m6['n']} candidates sampled over the rules-v1 produced classes (seed {m6['sample']['seed']}, quotas {m6['sample']['quotas']}) were read as diffs against D and "
              f"classified by hand under the protocol of reports/data/phase3_m6_human.json (state-element criterion: (a) same registers and stored values, (b) register structure / "
              f"stored state changed without registers crossing logic, (c1) registers cross logic at equal latency, (c2) output timing changed, (d) another algorithm / organisation / schedule). "
              f"Human classes: {m6['human_class_counts']}.", "",
              "| rules | agreement | (a) precision / recall | (b) | (c1) | (c2) | (d) |", "|---|---|---|---|---|---|---|"]
        for ver in ("v1", "v2"):
            r = m6["rules"][ver]
            cells = []
            for c in classes:
                pr, rc = r["per_rule_class"][c], r["per_human_class"][c]
                cells.append(f"{'-' if pr['precision'] is None else f'{100 * pr['precision']:.0f} %'} ({pr['correct']}/{pr['n']}) / {'-' if rc['recall'] is None else f'{100 * rc['recall']:.0f} %'} ({rc['found']}/{rc['n']})")
            L.append(f"| {ver} | {r['agree']} / {r['n']} ({100 * r['agreement']:.0f} %) | " + " | ".join(cells) + " |")
        for ver in ("v1", "v2"):
            L += ["", f"Confusion {ver} (human -> rule): " + ", ".join(f"{k}: {n}" for k, n in m6["rules"][ver]["confusion"].items())]
        wrong = [l for l in m6["labels"] if l["rule_v2"] != l["human"]]

        def category(l):
            h, r = l["human"], l["rule_v2"]
            if h == "c2" and r == "c1":
                return "output-timing change of a nonequiv candidate (human c2 -> rule c1)"
            if h == "d" and r in ("a", "b", "c1"):
                return "buffer / schedule re-organisation without operator or depth evidence (human d -> rule a / b / c1)"
            if h == "b" and r in ("a", "c1"):
                return "unobservable-state or redundant-register removal (human b -> rule a / c1)"
            if h == "a" and r == "c1":
                return "nonequiv artifact (human a -> rule c1)"
            return "other"
        cats = {}
        for l in wrong:
            cats[category(l)] = cats.get(category(l), 0) + 1
        L += ["", "Disagreement categories of rules v2 (DECISIONS 2026-09-14 item 1):", ""] + [f"- {k}: {n}" for k, n in sorted(cats.items(), key=lambda kv: -kv[1])]
        if data and data.get("models"):
            L += ["", "Phase 3 class distribution per model after the rules-v2 re-labelling (supersedes the distribution reported at G4; the run-time bandit credits and SEQ caps are unchanged):", "",
                  "| model | a | b | c1 | c2 | d | unclassified |", "|---|---|---|---|---|---|---|"]
            for mo, v in sorted(data["models"].items()):
                cl = v.get("classes") or {}
                L.append(f"| {mo} | " + " | ".join(str(cl.get(c, 0)) for c in ("a", "b", "c1", "c2", "d")) + f" | {sum(n for c, n in cl.items() if c not in ('a', 'b', 'c1', 'c2', 'd'))} |")
        L += ["", "The LLM review of spec 04 A.2 step 2 (DECISIONS 2026-09-14 item 1; `src/classify/review.py`, prompt `src/search/prompts/m6_review.md`, model `llm.selected`) runs on the candidates with low "
              "v2 confidence or in the four categories above (`phase3_calibrate.py m6-review`); its class replaces the rule class for (a) / (b) / (c1) / (c2) and is stored as `class_llm` / `class_final`, "
              "while (d) stays defined by tool evidence: the recall loss of (d) (7 of the 21 human-labelled (d) candidates of the sample end up as (a) / (b) / (c1)) is a stated limitation and the map's (d) row is read precision-first.",
              "", f"Rules v2 (`src/classify/rules.py`, config `classify`): (d) requires an operator family gained (multiply / divide, add / subtract, variable shift; "
              f"present in C's word-level RTLIL histogram, absent in D's) or a longest-combinational-path ratio ≥ {m6['classify_config']['d_depth_ratio']} (Yosys `ltp -noff`); "
              f"the text diff ratio only flags a rewrite for review. Flip-flop bits are counted after `opt` (the 32-bit loop variable of LIFObuffer's reset loop no longer counts as a "
              f"register), (c1) needs the flip-flop bits **and** the number of register cells to change, blocking assignments count as clocked targets.",
              "", f"Remaining disagreements of v2 ({len(wrong)}): " + "; ".join(f"#{l['i']} human {l['human']} / rule {l['rule_v2']}" for l in wrong) + ".",
              "", "Known limits of the static rules (recorded, not fixed): output-timing changes of nonequiv candidates cannot be seen without a lock-step offset (human c2 -> rule c1); "
              "buffer re-organisations that keep the register count (shift-register stacks, pointer-addressed writes without a shift cell), the FSM-to-phase-counter schedule change and "
              "the radix-4 partial-product recoding carry no operator or depth evidence (human d -> rule b / c1 / a); removals of unobservable state updates (reset / pop clears of an unread memory "
              "entry) and redundant-register removals are refactors the register features cannot separate from recodes (human b -> rule a / c1). These cases are the domain of the LLM review "
              "of spec 04 A.2 step 2, which is not part of the Phase 3 protocol. Every Phase 3 candidate was re-labelled with rules v2 (candidates.class_rule_v1 keeps the v1 class); "
              "the produced-class tables of §3 use the v2 classes, the run-time bandit credits and SEQ caps are untouched.", ""]
    concl = Path(ROOT) / "reports" / "phase3_conclusions.md"
    if concl.exists():
        L += ["", concl.read_text().rstrip("\n"), ""]
    out = Path(ROOT) / "reports" / "phase3.md"
    out.write_text("\n".join(L))
    print(f"wrote {out}")
    return 0


def phase4(cfg):
    """Exp1 (PLAN 4.1–4.9, acceptance of Phase 4): map heatmap (class × configuration), retention curves, σ_D comparison,
    predictor metrics with the class-blind control, literature re-evaluation table, misclassification rates, the map shape;
    diagnoser agreement and the motivating figure are appended by hand-checked data (reports/data/phase4_*)."""
    data = load("phase4_exp1.json")
    L = ["# Phase 4 report — Exp1: ladder and map (C1)", "",
         f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by scripts/report_phase.py (git {C.git_sha()}, cfg {C.cfg_hash()}). Data: reports/data/phase4_exp1.json (scripts/phase4_exp1.py collect).", ""]
    if not data:
        L += ["(not collected yet: scripts/phase4_exp1.py collect)", ""]
    else:
        c = data["counts"]
        L += ["## 1. Objects", "",
              f"Designs (config `exp1.designs`, C1 scope: human-written RTL): {', '.join(data['designs'])}; floor version `{data['floor_version']}`. "
              f"{c['objects']} objects: roles {c['by_role']}; equivalence verdicts {c['by_verdict']}; M6 classes (rules v2) {c['by_class']}; E4-evaluated {c['with_e4']}; M3 labels at E4 {c['by_label']}.", ""]
        L += ["## 2. Map v1: E4 retention rate (area, rule-A threshold of the design under each configuration) by class × configuration", "",
              "| class | " + " | ".join(f"{cfg_} rate (n)" for cfg_ in ("E1", "E1d", "E2", "E3", "E2g", "E4")) + " | E4 median gain | E4 labels | absorption rung (E4) |",
              "|---|" + "---|" * 9]
        mp = data["map"]
        for cls in ("a", "b", "c1", "c2", "d"):
            cells = mp.get(cls) or {}
            row = [cls]
            for cfg_ in ("E1", "E1d", "E2", "E3", "E2g", "E4"):
                ce = cells.get(cfg_) or {}
                row.append(f"{'-' if ce.get('retention_rate') is None else f'{100 * ce['retention_rate']:.0f} %'} ({ce.get('n_evaluated', 0)})")
            e4 = cells.get("E4") or {}
            row += [f"{'-' if e4.get('magnitude_median') is None else f'{100 * e4['magnitude_median']:.1f} %'}", str(e4.get("labels") or {}), str(e4.get("absorption_rung") or {})]
            L.append("| " + " | ".join(row) + " |")
        sh = data["shape"]
        L += ["", f"Map shape ({sh['basis']}): **{sh['shape']}** — E4 retention by class {dict((k, round(v, 2)) for k, v in sh['e4_retention_by_class'].items())} "
              "(concentrated: the rates differ by ≥ 0.3 between classes with ≥ 10 evaluated objects; near-zero: every class < 10 %; diffuse otherwise).", ""]

        def map_table(mp_, title, with_labels=True):
            L.append(title)
            L.append("")
            L.append("| class | " + " | ".join(f"{cfg_} rate (n)" for cfg_ in ("E1", "E1d", "E2", "E3", "E2g", "E4")) + (" | E4 median gain | E4 labels |" if with_labels else " |"))
            L.append("|---|" + "---|" * (8 if with_labels else 6))
            for cls_ in ("a", "b", "c1", "c2", "d"):
                cells_ = mp_.get(cls_) or {}
                row_ = [cls_]
                for cfg_ in ("E1", "E1d", "E2", "E3", "E2g", "E4"):
                    ce_ = cells_.get(cfg_) or {}
                    row_.append(f"{'-' if ce_.get('retention_rate') is None else f'{100 * ce_['retention_rate']:.0f} %'} ({ce_.get('n_evaluated', 0)})")
                if with_labels:
                    e4_ = cells_.get("E4") or {}
                    row_ += [f"{'-' if e4_.get('magnitude_median') is None else f'{100 * e4_['magnitude_median']:.1f} %'}", str(e4_.get("labels") or {})]
                L.append("| " + " | ".join(row_) + " |")
            L.append("")
        map_table(data.get("map_b0") or {}, "The same map on the B0 objects alone (the C1 scope: luna rewrites of the ten human-written designs; the literature objects excluded):")
        map_table(data.get("map_materiality") or {}, "All objects under the materiality thresholds (area 1 %, power 2 %, WNS 1 % of the period) instead of the rule-A floors — the sensitivity row; "
                  "E1d and E2g have no measured floor, so they appear here only:", with_labels=False)
        nm = data["non_monotone"]
        L += ["## 3. Retention curves and non-monotone cases", "",
              "| class | " + " | ".join(f"{cfg_}" for cfg_, _, _ in (data["retention_curves"].get("a") or [])) + " |", "|---|" + "---|" * len(data["retention_curves"].get("a") or [])]
        for cls, pts in data["retention_curves"].items():
            L.append(f"| {cls} | " + " | ".join("-" if r is None else f"{100 * r:.0f} % ({n})" for _, r, n in pts) + " |")
        L += ["", f"Non-monotone objects (inside the band at a lower rung, above it at a higher one): {len(nm['cases'])} of {nm['n_evaluated_on_all']} evaluated under E1–E4 "
              f"({'-' if nm['fraction'] is None else f'{100 * nm['fraction']:.1f} %'}): {', '.join(f'{cid} {pat}' for cid, pat in nm['cases'][:20])}", ""]
        hy = load("phase4_hygiene.json")
        if hy:
            L += ["## 4a. Benchmark hygiene: literature objects that are not equivalent to their original under the protocol (DECISIONS 2026-09-14 item 3)", "",
                  f"{hy['n']} objects ({hy['by_role']}; by verdict {hy['by_verdict']}) are excluded from the re-evaluation counts and reported here with the probable cause. "
                  "Protocol: V1 ports -> V2 lock-step simulation from the all-zero initial state (`+vcs+initreg+0`, G2.2) -> VC Formal SEQ with the same start state; the RTL-OPT authors verified their pairs with combinational equivalence, "
                  "which ignores the start state and the cycle-level timing.", "",
                  "| object | role | verdict | first mismatch (cycle, signals) | registers without reset (D / object) | probable cause |", "|---|---|---|---|---|---|"]
            for r in hy["rows"]:
                sig = ", ".join(r["mismatching_signals"][:4]) + (" …" if len(r["mismatching_signals"]) > 4 else "")
                L.append(f"| {r['design_id']} | {r['role']} | {r['kind']} | {'-' if r['first_mismatch_cycle'] is None else r['first_mismatch_cycle']}{(' (' + sig + ')') if sig else ''} | "
                         f"{r['registers_without_reset']['d']} / {r['registers_without_reset']['object']} | {r['probable_cause']} |")
            L.append("")
            ef = hy.get("eval_failed_objects") or {}
            if ef.get("n"):
                L += [f"**Objects whose synthesis evaluation failed**: {ef['n']} proven objects are rejected by the synthesizer under some configuration although VCS / VC Formal accepted them "
                      "(a fault of the object's RTL, recorded as `evaluation failed` under rule 8 and never repaired by the operator). They stay in the object counts and are absent from the map cells of the configurations concerned.", "",
                      "| design | role | objects | configurations | category |", "|---|---|---|---|---|"]
                groups = {}
                for r in ef["rows"]:
                    g = groups.setdefault((r["design_id"], r["role"], r["category"]), {"n": 0, "configs": set()})
                    g["n"] += 1
                    g["configs"] |= set(r["configs"])
                for (d, role, cat), g in sorted(groups.items()):
                    L.append(f"| {d} | {role} | {g['n']} | {', '.join(sorted(g['configs']))} | {cat} |")
                L.append("")
            ff = hy.get("fitness_failed_candidates") or {}
            if ff.get("n"):
                L += [f"B0 candidates whose Yosys fitness evaluation failed (no verdict, never objects): {ff['n']}, " + "; ".join(f"{k}: {v}" for k, v in sorted(ff["by_category"].items()))
                      + " (by design: " + ", ".join(f"{k} {v}" for k, v in sorted(ff["by_design"].items())) + ").", ""]
        dup = load("phase4_duplicates.json")
        if dup:
            cr = dup["cross_run_identical"]
            L += ["## 4c. Duplicate answers by design and by generation (G5 decisions item 4 (d))", "",
                  f"{dup['n_duplicates']} of the {dup['n_candidates']} Phase 4 answers repeat the RTL text of an earlier answer of the same run (label `duplicate`, no evaluation; by arm {dup['by_arm']}); "
                  f"{dup['runs_with_duplicates']} runs have at least one, at most {dup['max_per_run']} in a run. Generation gap to the repeated answer: " +
                  ", ".join(f"{k}: {v}" for k, v in dup["gap_to_original"].items()) + ". Identical rewrites produced by different runs of the same design (same content hash, not counted as duplicates within a run): "
                  f"{cr['groups']} groups over {cr['runs_involved']} run memberships" + (" (" + ", ".join(f"{d} {n}" for d, n in sorted(cr["by_design"].items())) + ")" if cr["by_design"] else "") + ".", "",
                  "| design | answers | duplicates | share |", "|---|---|---|---|"]
            for d, v in dup["by_design"].items():
                if v["duplicates"]:
                    L.append(f"| {d} | {v['candidates']} | {v['duplicates']} | {100 * v['share']:.0f} % |")
            L += ["", "| generation | answers | duplicates | share |", "|---|---|---|---|"]
            for g, v in dup["by_gen"].items():
                L.append(f"| {g} | {v['candidates']} | {v['duplicates']} | {100 * v['share']:.0f} % |")
            L.append("")
        rs = load("phase4_rtlopt_setting.json")
        if rs:
            cb = rs.get("counts_by_setting") or {"E2_1ns": rs["counts"]}
            ar = rs.get("authors_released_reports") or {}
            st = rs.get("settings") or {}
            def cnt(c):
                return f"{c.get('better', 0)} better / {c.get('same', 0)} same / {c.get('worse', 0)} worse" + (f" / {c['missing']} not evaluated" if c.get("missing") else "")
            L += ["## 4d. RTL-OPT pairs under the settings of the authors' published work and released artifacts (G5 item 4 (a); decisions 2026-09-15 items 4 and 5)", "",
                  f"Objects: the {rs['pairs']} proven RTL-OPT pairs (the six pairs that are not equivalent under this project's protocol, §4a, are outside every count; the mux_dead reference does not link under DC). "
                  "Criterion in every column: the reference version's total cell area against the suboptimal start's (better = smaller). Three settings side by side:", "",
                  "| setting | where it comes from | count over the proven pairs |", "|---|---|---|",
                  f"| authors' released reports | {ar.get('setting', '-')} | {ar.get('better_by_area', '-')} better / {ar.get('same', '-')} same / {ar.get('worse', '-')} worse of {ar.get('n', '-')} (their reports, their DC) |"]
            for name, label in (("E1_authors", "the released scripts' settings reproduced on DC W-2024.09 with this project's SDC (I/O delays 20 % of the period added to their input-to-output max-delay; standard synthetic library)"),
                                ("E2_1ns", "the paper's Table 1 setting as described (compile_ultra, 1 ns, no retime, no gate clock; DesignWare Foundation; this project's SDC) reproduced on W-2024.09")):
                if name in cb:
                    L.append(f"| `{name}` | {label}; compile string `{st.get(name, {}).get('compile', '-')}` | {cnt(cb[name])} |")
            L += ["", f"The paper's Table 1 reports {rs['authors_count']} for the compile_ultra / 1 ns setting; the released artifacts document the plain-compile / 0.1 ns setting. The rows above state what each artifact and each reproduction shows; "
                  "the remaining differences between the released scripts and this project's flow are the DC version, the I/O constraint form and the library compilation. At the knee period the same pairs under E2 and E4 are listed for reference.", "",
                  "| pair | phi_main (ns) | authors' released: D / ref / rel. | E1_authors: D / ref / rel. | E2_1ns: D / ref / rel. | rel. area E2 (knee) | rel. area E4 (knee) |", "|---|---|---|---|---|---|---|"]
            f = lambda v: "-" if v is None else f"{100 * v:+.1f} %"
            g = lambda v: "-" if v is None else f"{v:.1f}"
            for r in rs["rows"]:
                o = r.get("other_rungs") or {}
                t = r.get("authors_released") or {}
                se = r.get("settings") or {"E2_1ns": {"d_area": r.get("d_area"), "ref_area": r.get("ref_area"), "rel": r.get("rel_area")}}
                cells = [f"{g(x.get('d_area'))} / {g(x.get('ref_area'))} / {f(x.get('rel'))}" for x in (t, se.get("E1_authors") or {}, se.get("E2_1ns") or {})]
                L.append(f"| {r['design_id']} | {r['phi_main_ns']:.2f} | " + " | ".join(cells) + f" | {f((o.get('E2') or {}).get('rel'))} | {f((o.get('E4') or {}).get('rel'))} |")
            L.append("")
        if (Path(ROOT) / "reports" / "data" / "phase4_divider_counterexamples.md").exists():
            L += ["The four RTL-OPT divider references of §4a were inspected by hand (G5 item 4 (c)): the pairs differ only on division by zero with the dividend's MSB set (non-restoring vs restoring algorithm) and agree for every non-zero divisor; "
                  "analysis, traces and the confirming directed simulation in reports/data/phase4_divider_counterexamples.md.", ""]
        L += ["## 4. Literature settings re-evaluated (PLAN 4.7)", "",
              "| suite | pairs | proven | " + " | ".join(f"{cfg_} better / retained (evaluated)" for cfg_ in ("E1", "E1d", "E2", "E3", "E2g", "E4")) + " |", "|---|---|---|" + "---|" * 6]
        for suite, e in sorted(data["literature"].items()):
            L.append(f"| {suite} | {e['pairs']} | {e['proven']} | " + " | ".join(f"{e['better'].get(cfg_, 0)} / {e['retained'].get(cfg_, 0)} ({e['evaluated'].get(cfg_, 0)})" for cfg_ in ("E1", "E1d", "E2", "E3", "E2g", "E4")) + " |")
        L += ["", "better = the optimized version's area is below D's under that rung; retained = above D's rule-A threshold there. The papers' own counts are compared in the paper text (RTL-OPT: pairs judged better by the authors' flow; RTLRewriter: pass@k of the engineers' rewrite).", ""]
        mis = data["misclassification"]
        L += ["## 5. Static-rule misclassification rates (PLAN 4.8)", "",
              f"Rule R forbids classes {mis['forbidden_classes']} (syntactic / coding rewrites) and allows {mis['allowed_classes']}. "
              f"P(retained | forbidden by R) = {'-' if mis['p_retained_given_forbidden'] is None else f'{100 * mis['p_retained_given_forbidden']:.0f} %'} (n = {mis['n_forbidden']}); "
              f"P(absorbed | allowed by R) = {'-' if mis['p_absorbed_given_allowed'] is None else f'{100 * mis['p_absorbed_given_allowed']:.0f} %'} (n = {mis['n_allowed']}).", ""]
        ds = load("phase4_diagnoser_sample.json")
        if ds:
            rp = ds.get("reproduction") or {}
            L += ["## 5b. Diagnoser validation data (PLAN 4.6, spec 04 B.5)", "",
                  f"Diagnoses by label: {ds.get('per_label_total')}; manual sample of {ds.get('sample_per_label')} per label (seed {ds.get('seed')}, round-robin over designs; reports/data/phase4_diagnoser_sample.json, verdicts in phase4_diagnoser_check.md). "
                  f"Single-flag reproduction of the {rp.get('n', 0)} absorbed objects (D compiled with one flag alone vs the object's plain-compile netlist C@E1, convergence = histogram Jaccard >= {cfg['diag']['fp_jaccard']}, area within the E1 band, endpoints coincide): "
                  f"{rp.get('reproduced_by_a_single_flag', 0)} reproduced by at least one flag ({'-' if rp.get('rate_any_flag') is None else f'{100 * rp['rate_any_flag']:.0f} %'}).", "",
                  "| flag (configuration) | absorbed objects evaluated | converged with C@E1 | rate |", "|---|---|---|---|"]
            for flag, e in (rp.get("by_flag") or {}).items():
                L.append(f"| {flag} ({e.get('config')}) | {e['evaluated']} | {e['converged']} | {'-' if e.get('rate') is None else f'{100 * e['rate']:.0f} %'} |")
            L.append("")
        pr = data["predictor"]
        L += ["## 6. Retention predictor (PLAN 4.5; leave-one-design-out)", ""]
        if isinstance(pr.get("with_class"), dict):
            for k, lab in (("with_class", "with the class features"), ("class_blind", "class-blind control")):
                r = pr[k]
                L.append(f"- {lab}: n = {r['n']} ({r['n_pos']} retained), AUROC {'-' if r['auroc'] is None else f'{r['auroc']:.3f}'}, precision at recall ≥ 85 % "
                         f"{'-' if r['precision_at_85'] is None else f'{100 * r['precision_at_85']:.0f} %'} (τ = {'-' if r['tau_85'] is None else f'{r['tau_85']:.3f}'}, miss rate "
                         f"{'-' if r['miss_rate_at_85'] is None else f'{100 * r['miss_rate_at_85']:.0f} %'}); skipped designs {r['skipped_designs']}; "
                         f"coefficients (standardised) {dict((kk, round(v, 2)) for kk, v in (r.get('feature_importance') or {}).items())}")
        else:
            L.append(f"- {pr.get('note')}")
        L += ["", "## 7. σ_D comparison (E4 floors of the Exp1 designs vs the calibration designs)", "", "| design | area t_D | area σ | power t_D | WNS t_D | floor class |", "|---|---|---|---|---|---|"]
        for did, f in data["floors_e4"].items():
            a, p, w = f["area"], f["power"], f["wns"]
            L.append(f"| {did} | {'-' if a['t_d'] is None else f'{100 * a['t_d']:.2f} %'} | {'-' if a['sigma_robust'] is None else f'{100 * a['sigma_robust']:.2f} %'} | "
                     f"{'-' if p['t_d'] is None else f'{100 * p['t_d']:.2f} %'} | {'-' if w['t_d'] is None else f'{100 * w['t_d']:.2f} %'} | {a['floor_class'] or '-'} |")
        L.append("")
    ct = (data or {}).get("contrast_phase3")
    if ct:
        L += ["## 8. Out-of-scope contrast layer: the Phase 3 calibration candidates (RTLLM dev designs, C1 scope decision)", "",
              f"{ct['diagnosed']} E4-diagnosed candidates of {len(ct['designs'])} RTLLM designs (run-time M3 verdicts under the Phase 3 floors; classes rules v2); map shape **{ct['shape'][0]}** "
              f"({dict((k, round(v, 2)) for k, v in ct['shape'][1].items())}); rule-R misclassification: P(retained | forbidden) = "
              f"{'-' if ct['misclassification']['p_retained_given_forbidden'] is None else f'{100 * ct['misclassification']['p_retained_given_forbidden']:.0f} %'} (n = {ct['misclassification']['n_forbidden']}), "
              f"P(absorbed | allowed) = {'-' if ct['misclassification']['p_absorbed_given_allowed'] is None else f'{100 * ct['misclassification']['p_absorbed_given_allowed']:.0f} %'} (n = {ct['misclassification']['n_allowed']}); "
              f"non-monotone {len(ct['non_monotone']['cases'])} of {ct['non_monotone']['n_evaluated_on_all']} evaluated under E1–E4.", "",
              "| class | " + " | ".join(f"{cfg_} rate (n)" for cfg_ in ("E1", "E1d", "E2", "E3", "E2g", "E4")) + " | E4 median gain | E4 labels |", "|---|" + "---|" * 8]
        for cls in ("a", "b", "c1", "c2", "d"):
            cells = ct["map"].get(cls) or {}
            row = [cls]
            for cfg_ in ("E1", "E1d", "E2", "E3", "E2g", "E4"):
                ce = cells.get(cfg_) or {}
                row.append(f"{'-' if ce.get('retention_rate') is None else f'{100 * ce['retention_rate']:.0f} %'} ({ce.get('n_evaluated', 0)})")
            e4 = cells.get("E4") or {}
            row += [f"{'-' if e4.get('magnitude_median') is None else f'{100 * e4['magnitude_median']:.1f} %'}", str(e4.get("labels") or {})]
            L.append("| " + " | ".join(row) + " |")
        L.append("")
        mat = ct.get("materiality") or {}
        mm = ct.get("map_materiality") or {}
        if mm:
            L += [f"The same table under the materiality thresholds (area {100 * mat.get('area', 0):.0f} %, power {100 * mat.get('power', 0):.0f} %, WNS {100 * mat.get('wns', 0):.0f} % of the period) instead of the rule-A floors:", "",
                  "| class | " + " | ".join(f"{cfg_} rate (n)" for cfg_ in ("E1", "E1d", "E2", "E3", "E2g", "E4")) + " |", "|---|" + "---|" * 6]
            for cls in ("a", "b", "c1", "c2", "d"):
                cells = mm.get(cls) or {}
                L.append(f"| {cls} | " + " | ".join(f"{'-' if (cells.get(cfg_) or {}).get('retention_rate') is None else f'{100 * cells[cfg_]['retention_rate']:.0f} %'} ({(cells.get(cfg_) or {}).get('n_evaluated', 0)})" for cfg_ in ("E1", "E1d", "E2", "E3", "E2g", "E4")) + " |")
            L.append("")
        L += ["Diagnosis labels at E4 per class (run-time M3 verdicts; `harmful` split by the `blocks_synthesis` sub-label = DesignWare components of D absent from the candidate):", "",
              "| class | retained | trade-off | absorbed_identical | absorbed | noise | harmful (of which blocks_synthesis) | fragile |", "|---|---|---|---|---|---|---|---|"]
        for cls in ("a", "b", "c1", "c2", "d"):
            lab = ((ct["map"].get(cls) or {}).get("E4") or {}).get("labels") or {}
            hb = (ct.get("harmful_blocks_synthesis_by_class") or {}).get(cls, 0)
            L.append(f"| {cls} | {lab.get('retained', 0)} | {lab.get('tradeoff', 0)} | {lab.get('absorbed_identical', 0)} | {lab.get('absorbed', 0)} | {lab.get('noise', 0)} | {lab.get('harmful', 0)} ({hb}) | {lab.get('fragile', 0)} |")
        dbd = ct.get("d_by_design") or {}
        d_tot = sum(sum(v.values()) for v in dbd.values())
        d_ident = sum(v.get("absorbed_identical", 0) for v in dbd.values())
        top_ident = max(dbd.items(), key=lambda kv: kv[1].get("absorbed_identical", 0))[0] if dbd else "-"
        L += ["", f"Inspection of the (d) row: of the {d_tot} class-(d) candidates on RTLLM, {d_ident} are `absorbed_identical` ({dict((k, v.get('absorbed_identical', 0)) for k, v in sorted(dbd.items()))}; "
              f"on {top_ident} these are hand-written carry-lookahead / prefix / behavioural adders whose E4 netlist is identical to D's — DC's own adder synthesis reproduces them), "
              f"{sum(v.get('harmful', 0) for v in dbd.values())} are `harmful` of which {ct.get('d_harmful_blocks_synthesis', 0)} carry `blocks_synthesis` (a DesignWare component of D displaced by hand-written arithmetic: the first measured instances, "
              f"{'see the map' if ct.get('d_harmful_blocks_synthesis', 0) else 'none so far'}); the low (d) retention on RTLLM is absorption of textbook-adder rewrites, not displacement of DesignWare.", ""]
    for extra in ("phase4_diagnoser_check.md", "phase4_motivating.md"):
        p = DATA / extra
        if p.exists():
            L += ["", p.read_text().rstrip("\n"), ""]
    concl = Path(ROOT) / "reports" / "phase4_conclusions.md"
    if concl.exists():
        L += ["", concl.read_text().rstrip("\n"), ""]
    out = Path(ROOT) / "reports" / "phase4.md"
    out.write_text("\n".join(L))
    print(f"wrote {out}")
    return 0


# ----------------------------------------------------------------------------- Phase 5 (visible part; stages A / B / C, user decision 2026-09-16)
def _pct(x, digits=2):
    return "-" if x is None else f"{100.0 * x:.{digits}f} %"


def _num(x, digits=2):
    return "-" if x is None else f"{x:.{digits}f}"


ZERO_CELLS = ("0", "-", "0.00", "0.000", "0.00 %", "0.0", "0 / 0", "0.00 % / 0.00 %")


def _cell(txt, incomplete):
    """DECISION 2026-09-18 D1: a result cell of a row whose evaluation is incomplete never reads 0 — it reads `pending`; a
    non-zero interim value carries the dagger."""
    if not incomplete:
        return txt
    return "pending" if txt in ZERO_CELLS else f"{txt} †"


def phase5_notes_section(cfg, tiers, tier_of):
    """§0a of every Phase 5 report: the design notes and disclosures of DECISION 2026-09-18 (b) items 5c–5e and D1 (wording from
    config exp5.design_notes / exp5.disclosures, printed verbatim)."""
    notes = (cfg.get("exp5") or {}).get("design_notes") or {}
    disc = (cfg.get("exp5") or {}).get("disclosures") or []
    L = ["## 0a. Design notes and disclosures (DECISION 2026-09-18 (b) items 5c–5e, D1)", ""]
    shown = [(d, n) for d, n in sorted(notes.items()) if tier_of.get(d) in tiers]
    if shown:
        L += ["| design | tier | note |", "|---|---|---|"] + [f"| {d} | {tier_of.get(d)} | {n} |" for d, n in shown] + [""]
    for s in disc:
        L.append(f"- {s}")
    if not shown and not disc:
        L.append("(none)")
    L.append("")
    return L


def phase5_markdown(cfg, data, stage="all", final=False):
    """The visible-layer report from the collector's data (src/analysis/phase5.collect). Stage A: the large tier; B: large + medium;
    C / all: every tier. Nothing here reads the hidden database; the hidden part is scripts/report_hidden.py after Phase 5 completes."""
    from src.analysis import phase5 as P5
    tiers = P5.stage_tiers(stage)
    groups = data["groups"]
    planned = data.get("planned") or {}
    title = {"A": "Stage A — the large tier", "B": "Stage B — large and medium tiers", "C": "Stage C — every tier (full visible part)", "all": "visible part"}[stage]
    pend_total = sum((data.get("pending_total") or {}).values())
    status_line = ("**Final for its tiers** (every planned run done, no pending evaluation, no open visible job — the completeness rule of DECISION 2026-09-18 D2 / D3)." if final else
                   f"**Interim** ({pend_total} evaluations pending on the reported tiers: " + ", ".join(f"{t} {n}" for t, n in sorted((data.get("pending_total") or {}).items())) +
                   "; rows marked † are incomplete and `pending` stands where a value would otherwise read 0 — DECISION 2026-09-18 D1 / D3).")
    L = [f"# Phase 5 report ({title}) — {'final' if final else 'interim'}", "", status_line, "",
         f"Generated {data['generated_at']} by scripts/report_phase.py phase5 --stage {stage} (git {data['git_sha']}, cfg {data['cfg_hash']}). Data: reports/data/phase5_visible_{stage}.json (src/analysis/phase5.collect). "
         f"Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. "
         f"Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = {data['equiv_version']}, floor_version = {data['floor_version']}); an interim report changes nothing.", ""]
    # progress
    L += ["## 0. Progress", "", "| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |", "|---|---|---|---|---|---|---|---|"]
    order = {"large": 0, "medium": 1, "small": 2}
    keys = sorted(groups, key=lambda k: (order.get(k.split("|")[0], 3), k.split("|")[1], k.split("|")[2]))
    for k in keys:
        g = groups[k]
        L.append(f"| {g['tier']} | {g['model']} | {g['arm']} | {g['done']} / {g['runs']} / {g['planned'] if g['planned'] is not None else '-'} | {g['calls']} | {g['usd']:.2f} | {g['dc_h']:.1f} | {g['vcf_h']:.1f} |")
    unfinished = [k for k in keys if groups[k].get("incomplete")]
    if unfinished:
        L += ["", f"Incomplete rows: {len(unfinished)} of {len(keys)} — runs still open or evaluations pending (proofs, offline simulations, E4 records); their result cells read `pending` or carry †."]
    L.append("")
    tier_of = P5.tier_of_design(cfg)
    L += phase5_notes_section(cfg, tiers, tier_of)
    limits = {d: n.split(" — ")[0].split(" (")[0] for d, n in ((cfg.get("exp5") or {}).get("design_notes") or {}).items() if str(n).startswith(("harness limit", "verification limit"))}
    # arm comparison per tier
    L += ["## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)", ""]
    for tier in tiers:
        tk = [k for k in keys if k.startswith(tier + "|")]
        if not tk:
            L += [f"### {tier} tier: no runs yet", ""]
            continue
        L += [f"### {tier} tier", "", "| model (role) | arm | runs | candidates | pending | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for k in tk:
            g = groups[k]
            inc = bool(g.get("incomplete"))
            pend = (f"{g['pending']} (" + ", ".join(f"{a} {n}" for a, n in sorted((g.get("pending_by") or {}).items())) + ")") if g["pending"] else "0"
            pv = "pending" if (inc and not g["proven"]) else f"{g['proven']} ({_num(g['proven_per_call'], 3)})" + (" †" if inc else "")
            L.append(f"| {g['model']} ({g['role']}) | {g['arm']} | {g['done']}/{g['runs']}{' †' if inc else ''} | {g['cands']} | {pend} | {g['unusable']} | {pv} | {g['inconclusive']} | {g['latency_mapped']} | {g['accepted']} | {_cell(str(g['retained']), inc)} | {_cell(_num(g['retained_per_run'], 2), inc)} | {_cell(str(g['runs_with_retained']), inc)} | {_cell(_pct(g['best_gain_mean']) + ' / ' + _pct(g['best_gain_median']), inc)} | {_cell(_num(g['retained_per_100_calls'], 2), inc)} | {_cell(_num(g['retained_per_usd'], 2), inc)} | {_cell(_num(g['retained_per_dc_hour'], 2), inc)} | {g['usd']:.2f} | {g['dc_h']:.1f} | {g['vcf_h']:.1f} |")
        L.append("")
        L += ["Verdict mix and labels:", "", "| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for k in tk:
            g = groups[k]
            uni = ", ".join(f"{a}: {n}" for a, n in sorted(g["uniform"].items()))
            sto = ", ".join(f"{a}: {n}" for a, n in sorted(g["stored"].items()))
            bl = f"{g['block_flags']} / {g['block_answers']} = {_pct(g['block_flag_rate'], 0)}" if g["block_answers"] else "no block-level answers"
            L.append(f"| {g['model']} | {g['arm']} | {g['sim_fail']} | {g['falsified']} | {g['rejected']} | {g['inconclusive']} | {g['error']} | {g['pending']} | {g['duplicate']} | {g['prescreened']} | {uni or '-'} | {sto or '-'} | {g['scope_flags']} ({bl}) | {g['repairs']} ({g['repairs_proven']}) | {_num(g['ttv']['median'], 0)} / {_num(g['ttv']['q95'], 0)} |")
        L.append("")
    # best gain per design
    L += ["## 2. Best retained area gain per design (max over seeds; uniform rule A; '-' = no retained candidate; 0 = runs without one)", ""]
    for tier in tiers:
        dkeys = [k for k in data["designs"] if k.startswith(tier + "|")]
        if not dkeys:
            continue
        designs = sorted({k.split("|")[3] for k in dkeys})
        cols = sorted({(k.split("|")[1], k.split("|")[2]) for k in dkeys}, key=lambda x: (x[1], x[0]))
        L += [f"### {tier} tier", "", "| design | " + " | ".join(f"{a} ({m.split('-')[-1]})" for m, a in cols) + " |", "|---|" + "---|" * len(cols)]
        for d in designs:
            cells = []
            for m, a in cols:
                v = data["designs"].get(f"{tier}|{m}|{a}|{d}")
                if not v:
                    cells.append("-")
                else:
                    txt = _pct(v["best_retained_area_gain"]) if v["best_retained_area_gain"] else "0"
                    txt = _cell(txt, bool(v.get("pending")))
                    cells.append(limits[d] if (d in limits and txt in ("0", "pending")) else txt)   # DECISION 2026-09-18 (b) 5c / 5d: a design under a harness or verification limit never reads 0
            L.append(f"| {d} | " + " | ".join(cells) + " |")
        L.append("")
    # retained candidates: class, sub-tags, gains per metric (D2)
    L += ["## 2a. Retained and tradeoff candidates under the uniform rule A: class, sub-tags, gains per metric (DECISION 2026-09-18 D2)", ""]
    for tier in tiers:
        rl = [x for x in (data.get("retained_list") or []) if x["tier"] == tier]
        if not rl:
            continue
        L += [f"### {tier} tier ({sum(1 for x in rl if x['label'] == 'retained')} retained, {sum(1 for x in rl if x['label'] == 'tradeoff')} tradeoff)", "",
              "| model | arm | design | candidate | uniform label | arm's label | class | sub-tags | area | WNS (clock periods) | power | tradeoff composition |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for x in sorted(rl, key=lambda x: (x["arm"], x["model"], x["design_id"], -(x["gains"].get("area") or 0))):
            gA, gW, gP = x["gains"].get("area"), x["gains"].get("wns"), x["gains"].get("power")
            L.append(f"| {x['model']} | {x['arm']} | {x['design_id']} | {x['cand_id']} | {x['label']} | {x.get('stored_label') or '-'} | {x.get('class_final') or '-'} | {'; '.join(str(s) for s in x['subtags']) or '-'} | {_pct(gA)} | {_num(gW, 4) if gW is not None else '-'} | {_pct(gP)} | {x.get('sublabel') or '-'} |")
        L.append("")
        L += ["Per row: retained gains per metric (median / max over the retained candidates; WNS in clock periods) and the tradeoff composition:", "",
              "| model | arm | retained | area: median / max | WNS: median / max | power: median / max | tradeoffs | composition (up = better, down = worse) |", "|---|---|---|---|---|---|---|---|"]
        rows = sorted({(x["model"], x["arm"]) for x in rl}, key=lambda k: (k[1], k[0]))
        for m, a in rows:
            ret = [x for x in rl if x["model"] == m and x["arm"] == a and x["label"] == "retained"]
            tr = [x for x in rl if x["model"] == m and x["arm"] == a and x["label"] == "tradeoff"]
            def mm(metric, fmt):
                vals = [x["gains"].get(metric) for x in ret if x["gains"].get(metric) is not None]
                return f"{fmt(statistics.median(vals))} / {fmt(max(vals))}" if vals else "-"
            comp = collections.Counter(x.get("sublabel") or "?" for x in tr)
            L.append(f"| {m} | {a} | {len(ret)} | {mm('area', _pct)} | {mm('wns', lambda v: _num(v, 4))} | {mm('power', _pct)} | {len(tr)} | {'; '.join(f'{k}: {n}' for k, n in sorted(comp.items())) or '-'} |")
        L.append("")
    # model contrast
    L += ["## 3. Model contrast (the same arm under two models on the same tier)", ""]
    any_contrast = False
    for tier in tiers:
        arms = sorted({k.split("|")[2] for k in keys if k.startswith(tier + "|")})
        for arm in arms:
            ks = [k for k in keys if k.startswith(tier + "|") and k.endswith("|" + arm)]
            if len(ks) < 2:
                continue
            any_contrast = True
            L += [f"- **{tier} / {arm}**: " + "; ".join(f"{groups[k]['model']} ({groups[k]['role']}): proven {_num(groups[k]['proven_per_call'], 3)} / call, retained {_num(groups[k]['retained_per_run'], 2)} / run, best gain mean {_pct(groups[k]['best_gain_mean'])}, unusable {groups[k]['unusable']}, USD {groups[k]['usd']:.2f}" for k in ks)]
    if not any_contrast:
        L.append("(no arm has two models on the reported tiers yet)")
    L.append("")
    # curves
    L += ["## 4. Retained-gain curves (mean over the group's runs of the best retained area gain so far)", ""]
    for tier in tiers:
        ck = [k for k in data["curves"] if k.startswith(tier + "|")]
        if not ck:
            continue
        pts = [5, 10, 20, 30, 40, 50, 60]
        L += [f"### {tier} tier — by LLM calls (equal-call caliber)", "", "| model | arm | " + " | ".join(f"{x} calls" for x in pts) + " |", "|---|---|" + "---|" * len(pts)]
        for k in sorted(ck, key=lambda k: (k.split("|")[2], k.split("|")[1])):
            byc = {p["calls"]: p for p in data["curves"][k].get("by_calls", [])}
            inc = bool((groups.get(k) or {}).get("incomplete"))
            L.append(f"| {k.split('|')[1]} | {k.split('|')[2]}{' †' if inc else ''} | " + " | ".join(_cell(_pct((byc.get(x) or {}).get("mean_best_gain")), inc) for x in pts) + " |")
        L += ["", f"### {tier} tier — by visible DC hours per run", ""]
        for k in sorted(ck, key=lambda k: (k.split("|")[2], k.split("|")[1])):
            bd = data["curves"][k].get("by_dc_hours", [])
            if not bd:
                continue
            sample = bd[:: max(1, len(bd) // 6)][:7]
            L.append(f"- {k.split('|')[1]} / {k.split('|')[2]}: " + ", ".join(f"{p['dc_hours']:.2f} h → {_pct(p['mean_best_gain'])}" for p in sample))
        L.append("")
    # correctness
    L += ["## 5. Correctness (the LLM's equivalence-preserving rate)", "", "| tier | model | design | runs | candidates | proven | proven rate |", "|---|---|---|---|---|---|---|"]
    for k in sorted(data["correctness"], key=lambda k: (order.get(k.split("|")[0], 3), k.split("|")[2], k.split("|")[1])):
        if k.split("|")[0] not in tiers:
            continue
        v = data["correctness"][k]
        d = k.split("|")[2]
        L.append(f"| {k.split('|')[0]} | {k.split('|')[1]} | {d}{' (' + limits[d] + ')' if d in limits else ''} | {v['runs']} | {v['cands']} | {v['proven']} | {_pct(v['proven_rate'], 1)} |")
    inc = data.get("inconclusive") or {}
    L += ["", "### 5a. Inconclusive proofs per class and per design (DECISION 2026-09-18 D2)", ""]
    any_inc = False
    for tier in tiers:
        bc = {k.split("|")[1]: n for k, n in (inc.get("by_class") or {}).items() if k.split("|")[0] == tier}
        bd = {k.split("|")[1]: n for k, n in (inc.get("by_design") or {}).items() if k.split("|")[0] == tier}
        if bc or bd:
            any_inc = True
            L.append(f"- {tier} tier — by class: " + (", ".join(f"{c}: {n}" for c, n in sorted(bc.items())) or "none") + "; by design: " + (", ".join(f"{d}: {n}" for d, n in sorted(bd.items(), key=lambda kv: -kv[1])) or "none"))
    if not any_inc:
        L.append("(no inconclusive proof on the reported tiers)")
    L.append("")
    noted = (cfg.get("exp5") or {}).get("design_notes") or {}
    low = [k for k, v in data["correctness"].items() if k.split("|")[0] in tiers and v["cands"] >= 30 and (v["proven_rate"] or 0) < 0.05 and k.split("|")[2] not in noted]   # a design with a note (5c / 5d) is described by the note, not by this rule
    noted_low = sorted({k.split("|")[2] for k, v in data["correctness"].items() if k.split("|")[0] in tiers and v["cands"] >= 30 and (v["proven_rate"] or 0) < 0.05 and k.split("|")[2] in noted})
    L += ["", "LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): " + (", ".join(f"{k.split('|')[2]} under {k.split('|')[1]}" for k in low) if low else "none on the reported tiers") + ("; designs below the rate whose note applies instead (§0a): " + ", ".join(f"{d} — {noted[d]}" for d in noted_low) if noted_low else "") + ".", ""]
    # classes
    L += ["## 6. Classes produced (rules v2) and requested → produced", ""]
    for k in keys:
        g = groups[k]
        if g["classes"]:
            conf = ", ".join(f"{a}: {n}" for a, n in sorted(g["confusion"].items()))
            L.append(f"- {g['tier']} / {g['model']} / {g['arm']}: produced {dict(sorted(g['classes'].items()))}" + (f"; requested → produced {conf}" if conf else ""))
    L.append("")
    # runs / anomalies
    bad = [r for r in data["runs"] if r["status"] not in ("done", "running", "created")]
    L += ["## 7. Runs and anomalies", "", f"Runs on the reported tiers: {len(data['runs'])} ({sum(1 for r in data['runs'] if r['status'] == 'done')} done, {sum(1 for r in data['runs'] if r['status'] == 'running')} running, {sum(1 for r in data['runs'] if r['status'] == 'created')} not started). "
          + (f"Abnormal statuses: " + ", ".join(f"{r['run_id']} {r['status']}" for r in bad[:20]) + "." if bad else "No run in an abnormal status."), ""]
    L += phase5_ops_section(data.get("ops") or {})
    cond = data.get("conditions") or {}
    L += ["## 7b. Verification conditions per arm-model row (DECISION 2026-09-18 item 5c: median host load and VC Formal wait during the row's runs)", "",
          "| tier | model | arm | proofs | VC Formal queue wait: median / q95 (min) | median 1-min load over the row's run-minutes | run-minutes with a load sample (coverage) |", "|---|---|---|---|---|---|---|"]
    for k in keys:
        cnd = cond.get(k) or {}
        g = groups[k]
        cov = cnd.get("load_coverage")
        L.append(f"| {g['tier']} | {g['model']} | {g['arm']} | {cnd.get('proofs', 0)} | {_num(cnd.get('vcf_wait_median_min'), 1)} / {_num(cnd.get('vcf_wait_q95_min'), 1)} | {_num(cnd.get('load_median'), 1)} | {cnd.get('load_samples', 0)} ({_pct(cov, 0) if cov is not None else '-'}) |")
    L += ["", "The load log (scripts/load_logger.py, one sample per minute) starts 2026-09-18 05:49; rows whose runs predate it show a partial coverage — the VC Formal wait comes from the queue's own timestamps and covers every proof.", ""]
    if stage in ("C", "all"):
        L += ["## 8. Success criteria (PROPOSAL §7.2), visible-layer view", "",
              "- C2 (M vs B2 and vs B1@E4 at equal calls; the hidden-configuration form of the criterion is **sealed** until the Phase 5 completion marker — scripts/report_hidden.py): see §1 (retained per run, best gain per run) and §2 (per-design best gains) per tier; the geometric-mean form and the 2σ_D test per design are computed in the final report once every tier is complete.",
              "- Dr.RTL re-implementation: arm DrRTL_reimpl against M and B2 in §1 / §2 (the original reference row, PLAN 5.4, is the user's manual run).",
              "- C1 (map): the produced-class distribution per arm in §6; the absorbed / retained map by class over the accepted candidates of every arm follows in Phase 6.2.",
              "- Screening: not part of Phase 5 (dropped at G3).", ""]
    return "\n".join(L) + "\n"


def phase5_ops_section(ops):
    """§7a of the Phase 5 report: the operational changes of 2026-09-16 (user follow-up items 1 and 5) — provisional-versus-final
    agreement, the exposure window of positive provisional feedback and the fate of its candidates, cross-run verdict reuse, the
    hourly proven-to-inconclusive ratio since the hidden-job throttle."""
    if not ops:
        return []
    ev = ops.get("events") or {}
    L = ["## 7a. Operational changes during the run (DECISIONS 2026-09-16; verdict definitions, floors, budgets and the stack unchanged)", "",
         f"Hidden DC registrations capped at 8 from {ev.get('hidden_throttle_at')}; split equivalence pipeline, provisional diagnosis and proof ordering from {ev.get('scheduling_change_at')}; "
         f"positive provisional verdicts withheld from the model from {ev.get('provisional_fix_at') or '(not yet)'}.", ""]
    ag = ops.get("agreement") or {}
    if "error" in ag:
        L.append(f"- Provisional-versus-final agreement: not computed ({ag['error']}).")
    else:
        rate = f"{100.0 * ag['agree_rate']:.1f} %" if ag.get("agree_rate") is not None else "n/a"
        dis = "; ".join(f"{d['provisional']}→{d['final']}" for d in (ag.get("disagree") or [])[:8])
        L.append(f"- Provisional-versus-final diagnosis agreement: {ag.get('agree', 0)} of {ag.get('proven_final', 0)} proven candidates with a final diagnosis agree ({rate}); "
                 f"{ag.get('n_provisional', 0)} candidates received a provisional label ({', '.join(f'{k} {v}' for k, v in sorted((ag.get('by_label') or {}).items()))}), "
                 f"{ag.get('not_proven', 0)} of them were not proven, {ag.get('pending', 0)} still wait for the proof or the diagnosis, {ag.get('withheld', 0)} labels withheld from the model" + (f". Disagreements: {dis}" if dis else "") + ".")
    ex = ops.get("exposure") or {}
    if "error" in ex:
        L.append(f"- Positive provisional feedback exposure: not computed ({ex['error']}).")
    else:
        fate = ex.get("fate") or {}
        L.append(f"- Positive provisional feedback exposure (window {ex.get('window', ['?', '?'])[0]} to {ex.get('window', ['?', '?'])[1]}): {ex.get('calls', 0)} LLM calls carried {ex.get('blocks', 0)} positive pending blocks "
                 f"({len(ex.get('runs') or {})} runs); {ex.get('n_candidates', 0)} candidates behind them — proofs since: " + (", ".join(f"{k} {v}" for k, v in sorted(fate.items())) or "none") +
                 (f"; {ex['unmatched_blocks']} blocks could not be matched to a candidate" if ex.get("unmatched_blocks") else "") + ".")
    ru = ops.get("reuse") or {}
    if "error" in ru:
        L.append(f"- Cross-run verdict reuse: not computed ({ru['error']}).")
    else:
        L.append(f"- Cross-run verdict reuse since {ru.get('since')}: {ru.get('reused', 0)} proofs copied from a decided record of the same pair ({ru.get('by_verdict') or {}}), "
                 f"over {ru.get('split_proofs', 0)} split-pipeline proofs of {ru.get('records_scanned', 0)} equivalence records; sim records missing: {ru.get('sim_record_missing', 0)}.")
    hr = ops.get("hourly") or {}
    if "error" in hr:
        L.append(f"- Hourly proven-to-inconclusive ratio: not computed ({hr['error']}).")
    elif hr.get("hours"):
        L += ["", f"Equivalence jobs finished per hour on the VC Formal pool since the throttle ({hr.get('since')}), by the candidate's verdict:", "",
              "| hour | finished | proven | inconclusive | proven : inconclusive | falsified | rejected | sim_fail |", "|---|---|---|---|---|---|---|---|"]
        for h in hr["hours"]:
            L.append(f"| {h['hour']} | {h['finished']} | {h['proven']} | {h['inconclusive']} | {h['ratio'] if h['ratio'] is not None else '-'} | {h['falsified']} | {h['rejected']} | {h['sim_fail']} |")
    L.append("")
    return L


def phase5(cfg, stage="all", out_dir=None, conn=None, final=False):
    """Collect the visible-layer data of the stage's tiers and write reports/phase5_stage_<stage>.md (stage C / all also
    reports/phase5.md, the visible part of the Phase 5 report)."""
    from src.analysis import phase5 as P5
    from src.db import core as db
    conn = conn or db.connect(cfg=cfg)
    data = P5.collect(cfg, conn, tiers=P5.stage_tiers(stage))
    data["final"] = bool(final)
    out = Path(out_dir or (Path(C.ROOT) / "reports"))
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / f"phase5_visible_{stage}.json").write_text(json.dumps(data, indent=1, sort_keys=True, default=str) + "\n")
    text = phase5_markdown(cfg, data, stage, final=bool(final))
    (out / f"phase5_stage_{stage}.md").write_text(text)
    if stage in ("C", "all"):
        (out / "phase5.md").write_text(text)
    print(text[:1500])
    print(f"... written {out / f'phase5_stage_{stage}.md'}" + (f" and {out / 'phase5.md'}" if stage in ("C", "all") else ""))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["phase1", "phase2", "phase3", "phase4", "phase5"])
    ap.add_argument("--stage", default="all", choices=["A", "B", "C", "all"], help="phase5: A = large tier, B = large + medium, C / all = every tier (the full visible part)")
    ap.add_argument("--final", action="store_true", help="phase5: render as the stage's final report (the stages loop passes it when the completeness rule holds)")
    a = ap.parse_args(argv)
    cfg = C.load()
    if a.phase == "phase5":
        return phase5(cfg, stage=a.stage, final=a.final)
    return {"phase1": phase1, "phase2": phase2, "phase3": phase3, "phase4": phase4}[a.phase](cfg)


if __name__ == "__main__":
    sys.exit(main())
