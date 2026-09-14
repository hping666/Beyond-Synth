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
    fa = S.floor_analysis(conn, set_designs, configs, proven, k)
    if fa:
        L += ["### 2a. Floor distribution on the set designs (dev + held)", "",
              "| config | metric | designs with floor | sigma_robust = 0 | sigma_std = 0 | max abs delta > 1 % | > 5 % | pooled q90 of abs delta | pooled q95 | pooled q99 | pooled max | rule-A t_D median / q95 / max | designs above the q90 minimum |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for (config, m), a in sorted(fa.items()):
            tp = a["t_proposed"] or {}
            L.append(f"| {config} | {m} | {a['designs']} | {a['zero_robust']} | {a['zero_std']} | {a['max_abs_gt']['1pct']} | {a['max_abs_gt']['5pct']} | "
                     f"{a['pooled']['q90']:.4f} | {a['pooled']['q95']:.4f} | {a['pooled']['q99']:.4f} | {a['pooled']['max']:.4f} | "
                     f"{tp.get('median', 0):.4f} / {tp.get('q95', 0):.4f} / {tp.get('max', 0):.4f} | {tp.get('above_pooled_min', 0)} |")
        L += ["", f"Rule A (G1 alternative, see the conclusions): t_D = max({k:.0f} x sigma_robust, max |delta| over D's own proven perturbations including the re-print, pooled q90 of |delta| over all perturbation records of the configuration); "
              "the pooled quantile is the minimum for designs whose perturbations never change the netlist (rule B uses the pooled q95 instead). The spec's 2 x sigma_robust stays in the table above for the sensitivity report.", ""]
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
        L += ["", "## 5. Time to verdict (seconds from the LLM answer to the equivalence verdict) and response to absorbed feedback", ""]
        for mo, v in sorted(data["models"].items()):
            ttv = "; ".join(f"{c}: n={t['n']} median {t['median']:.0f} q95 {t['q95']:.0f} max {t['max']:.0f}" for c, t in sorted(v["time_to_verdict"].items()))
            resp = v["absorbed_response"]
            L.append(f"- **{mo}**: {ttv or 'no verdicts'}; children of absorbed parents that were not absorbed again: {resp[0]} of {resp[1]}")
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
    out = Path(ROOT) / "reports" / "phase3.md"
    out.write_text("\n".join(L))
    print(f"wrote {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["phase1", "phase2", "phase3"])
    a = ap.parse_args(argv)
    cfg = C.load()
    return {"phase1": phase1, "phase2": phase2, "phase3": phase3}[a.phase](cfg)


if __name__ == "__main__":
    sys.exit(main())
