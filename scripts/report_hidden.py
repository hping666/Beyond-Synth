#!/usr/bin/env python3
"""The only reader of the hidden results database (docs/spec/06-hidden-layer.md, CLAUDE.md rule 3).

    .venv/bin/python scripts/report_hidden.py [--check] [--stage-d]

Refuses to open the hidden database until STATUS.md carries the Phase 5 completion marker (`PHASE5_COMPLETE: yes`, written
by the human at the end of Phase 5). --check only reports whether the marker is present. The certification report (stage D
of the staged Phase 5 reports, user decision 2026-09-16): for every hidden configuration the speculation rate of the visible
layer's retained candidates (rule A at E4, uniform for every arm) and of the arms' own accepted candidates, combined across
configurations, per arm, per generation and per class; the reverse error on the audit sample; the retained gain under each
configuration next to the visible one; coverage of the hidden records; sigma_D under the hidden configurations. Writes
reports/phase5_hidden.md and reports/data/phase5_hidden.json and appends the hidden section to reports/phase5.md.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
from collections import defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.diagnose import m3  # noqa: E402
from src.noise import stats as S  # noqa: E402
from src.search.driver import record_from_row  # noqa: E402

MARKER = re.compile(r"^PHASE5_COMPLETE:\s*yes\s*$", re.M)
HIDDEN_SECTION = "## Hidden layer (stage D"


def phase5_complete(status_path=None):
    p = Path(status_path or (Path(C.ROOT) / "STATUS.md"))
    return bool(p.exists() and MARKER.search(p.read_text()))


def hidden_db_path(cfg):
    return os.path.join(C.results_dir(cfg), "hidden", "hidden.sqlite")


def config_clock(cfg, config, design_row):
    """The period of a hidden configuration for a design: its own clock_ns or the design's knee on the configuration's library."""
    cdef = cfg["configs"][config]
    if cdef.get("clock_ns") is not None:
        return float(cdef["clock_ns"])
    lib = cdef.get("lib") or "nangate45"
    v = design_row.get(f"phi_main_ns_{lib}") if design_row else None
    return float(v) if v is not None else None


def hidden_gain(cfg, hid, vis_design, config, cand_id, design_id, clock_ns, floor_cache, e4_area_gain=None):
    """Rule-A diagnosis of a candidate under a hidden configuration from the hidden records (D's baseline and the candidate's,
    same config and period) with the hidden floor (H4: the visible E4 floor, spec 06 §3). -> dict(label, gains, band) or None."""
    if clock_ns is None:
        return None
    base = hid.execute("SELECT * FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' "
                       "AND abs(clock_ns-?)<1e-6 ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (design_id, config, clock_ns)).fetchone()
    cand = hid.execute("SELECT * FROM evaluations WHERE design_id=? AND config=? AND cand_id=? AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY eval_id DESC LIMIT 1",
                       (design_id, config, cand_id, clock_ns)).fetchone()
    if base is None or cand is None:
        return None
    key = (design_id, config)
    if key not in floor_cache:
        floor_cache[key] = S.latest_floor(hid, design_id, config, cfg["noise"].get("floor_version")) or S.latest_floor(hid, design_id, config)
    floor = floor_cache[key]
    thresholds = {"area": (floor.get("area") or {}).get("t_d"), "wns": (floor.get("wns") or {}).get("t_d"), "power": (floor.get("power_saif") or {}).get("t_d")}
    sigma = {"area": (floor.get("area") or {}).get("sigma_robust") or 0.0, "wns": (floor.get("wns") or {}).get("sigma_robust") or 0.0, "power": (floor.get("power_saif") or {}).get("sigma_robust") or 0.0}
    floor_class = next((r.get("floor_class") for r in floor.values() if r.get("floor_class")), None)
    b, c = record_from_row(base), record_from_row(cand)
    if cfg["configs"][config].get("tool") == "pt_primepower" and e4_area_gain is not None:
        # H4 reads the E4 netlist: its area is E4's; the signoff adds timing and power. The area gain is E4's own.
        c["metrics"]["area"] = c["metrics"]["area_um2"] = (b["metrics"].get("area") or 0.0) * (1.0 - float(e4_area_gain)) if b["metrics"].get("area") else None
    out = m3.diagnose(b, c, sigma, clock_ns, v3_status="proven", k_sigma=float(cfg["noise"]["k_sigma"]), thresholds=thresholds, floor_class=floor_class)
    ev = out.get("evidence") or {}
    return {"label": out.get("label"), "gains": ev.get("gains") or {}, "band": ev.get("band") or {}, "floor_source": next((r.get("floor_source") for r in floor.values() if r.get("floor_source")), None)}


def build(cfg, vis, hid, exp="phase5", tier_of=None):
    """-> the stage-D data: per candidate of the visible layer (uniform retained set and the arms' own accepted set) the
    label under every hidden configuration; speculation rates; reverse error on the audit sample; coverage; hidden floors."""
    from src.analysis import phase5 as P5
    hidden_cfgs = [n for n, c in cfg["configs"].items() if isinstance(c, dict) and c.get("hidden")]
    tier_of = tier_of or P5.tier_of_design(cfg)
    designs = P5._Designs(cfg, vis)
    drows = {r["design_id"]: dict(r) for r in vis.execute("SELECT * FROM designs")}
    floor_cache = {}
    rows = vis.execute("SELECT c.*, r.llm_model AS run_model, r.arm AS run_arm, r.exp FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                       "WHERE r.exp=? AND r.status != 'superseded' AND c.verdict='proven' ORDER BY c.created_at, c.cand_id", (exp,)).fetchall()
    per_cand = []
    for c in rows:
        c = dict(c)
        ud = P5.uniform_diagnosis(designs, vis, c)
        vis_label = ud[0] if ud else None
        vis_gain = float((ud[1] or {}).get("area") or 0.0) if ud else 0.0
        entry = {"cand_id": c["cand_id"], "design_id": c["design_id"], "tier": tier_of.get(c["design_id"]), "model": c["run_model"], "arm": c["run_arm"], "gen": c.get("gen"),
                 "class": c.get("class_final"), "accepted": int(bool(c.get("accepted"))), "visible_label": vis_label, "visible_area_gain": round(vis_gain, 5), "hidden": {}}
        for h in hidden_cfgs:
            clk = config_clock(cfg, h, drows.get(c["design_id"]))
            entry["hidden"][h] = hidden_gain(cfg, hid, drows.get(c["design_id"]), h, c["cand_id"], c["design_id"], clk, floor_cache, e4_area_gain=vis_gain if vis_label else None) if clk is not None else None
        per_cand.append(entry)
    # ---- speculation: retained visibly (uniform) -> not retained under H; also on the arms' own accepted set
    def rates(entries, key_fn):
        out = defaultdict(lambda: {"n": 0, "with_records": 0, "vetoed_any": 0, **{h: {"n": 0, "vetoed": 0} for h in hidden_cfgs}})
        for e in entries:
            k = key_fn(e)
            g = out[k]
            g["n"] += 1
            have = [h for h in hidden_cfgs if e["hidden"].get(h)]
            if have:
                g["with_records"] += 1
            any_veto = False
            for h in have:
                lab = e["hidden"][h]["label"]
                g[h]["n"] += 1
                if lab != "retained":
                    g[h]["vetoed"] += 1
                    any_veto = True
            g["vetoed_any"] += int(any_veto)
        res = {}
        for k, g in out.items():
            res[k] = {"n": g["n"], "with_records": g["with_records"], "combined_rate": round(g["vetoed_any"] / g["with_records"], 4) if g["with_records"] else None,
                      **{h: {"n": g[h]["n"], "vetoed": g[h]["vetoed"], "rate": round(g[h]["vetoed"] / g[h]["n"], 4) if g[h]["n"] else None} for h in hidden_cfgs}}
        return res
    retained = [e for e in per_cand if e["visible_label"] == "retained"]
    accepted = [e for e in per_cand if e["accepted"]]
    spec = {"uniform_retained": {"by_arm": rates(retained, lambda e: f"{e['tier']}|{e['model']}|{e['arm']}"), "by_gen": rates(retained, lambda e: str(e["gen"])),
                                 "by_class": rates(retained, lambda e: str(e["class"])), "all": rates(retained, lambda e: "all")},
            "arms_accepted": {"by_arm": rates(accepted, lambda e: f"{e['tier']}|{e['model']}|{e['arm']}"), "all": rates(accepted, lambda e: "all")}}
    # ---- reverse error: proven candidates not retained visibly that carry hidden records (the audit sample) and are retained under H
    rejected = [e for e in per_cand if e["visible_label"] in ("noise", "absorbed", "absorbed_identical", "harmful", "tradeoff", "fragile") and any(e["hidden"].values())]
    reverse = {}
    for h in hidden_cfgs:
        n = sum(1 for e in rejected if e["hidden"].get(h))
        acc = sum(1 for e in rejected if e["hidden"].get(h) and e["hidden"][h]["label"] == "retained")
        reverse[h] = {"n": n, "acceptable_hidden": acc, "rate": round(acc / n, 4) if n else None}
    # ---- gains under H next to the visible gain (retained set): mean visible gain and mean gain under each H, and best gain per run (curves)
    gains = defaultdict(lambda: {"visible": [], **{h: [] for h in hidden_cfgs}})
    for e in retained:
        k = f"{e['tier']}|{e['model']}|{e['arm']}"
        gains[k]["visible"].append(e["visible_area_gain"])
        for h in hidden_cfgs:
            if e["hidden"].get(h) and e["hidden"][h]["gains"].get("area") is not None:
                gains[k][h].append(float(e["hidden"][h]["gains"]["area"]))
    gain_table = {k: {m: {"n": len(v), "mean": round(statistics.mean(v), 5) if v else None, "median": round(statistics.median(v), 5) if v else None} for m, v in g.items()} for k, g in gains.items()}
    # ---- coverage of the hidden records for the retained and accepted sets
    cov = {}
    for h in hidden_cfgs:
        exp_r = [e for e in retained if config_clock(cfg, h, drows.get(e["design_id"])) is not None]
        exp_a = [e for e in accepted if config_clock(cfg, h, drows.get(e["design_id"])) is not None]
        cov[h] = {"retained_expected": len(exp_r), "retained_with_record": sum(1 for e in exp_r if e["hidden"].get(h)),
                  "accepted_expected": len(exp_a), "accepted_with_record": sum(1 for e in exp_a if e["hidden"].get(h))}
    # ---- sigma_D under the hidden configurations (from the hidden noise_floor table: counts and medians only)
    floors = {}
    for h in hidden_cfgs:
        sig = [r[0] for r in hid.execute("SELECT sigma_robust FROM noise_floor WHERE config=? AND metric='area' AND sigma_robust IS NOT NULL", (h,))]
        td = [r[0] for r in hid.execute("SELECT t_d FROM noise_floor WHERE config=? AND metric='area' AND t_d IS NOT NULL", (h,))]
        floors[h] = {"designs_with_floor": len({r[0] for r in hid.execute("SELECT design_id FROM noise_floor WHERE config=? AND metric='area'", (h,))}),
                     "sigma_area_median": round(statistics.median(sig), 5) if sig else None, "t_d_area_median": round(statistics.median(td), 5) if td else None}
    return {"generated_at": datetime.datetime.now().isoformat(timespec="minutes"), "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(), "exp": exp, "hidden_configs": hidden_cfgs,
            "candidates_proven": len(per_cand), "retained_uniform": len(retained), "accepted_arms": len(accepted), "speculation": spec, "reverse_error": reverse,
            "gains": gain_table, "coverage": cov, "floors": floors, "per_candidate": per_cand}


def _pct(x):
    return "-" if x is None else f"{100.0 * x:.1f} %"


def render(data):
    H = data["hidden_configs"]
    L = [f"{HIDDEN_SECTION}; scripts/report_hidden.py)", "",
         f"Generated {data['generated_at']} (git {data['git_sha']}, cfg {data['cfg_hash']}) after the Phase 5 completion marker; data reports/data/phase5_hidden.json. "
         f"Proven candidates of the visible layer: {data['candidates_proven']}; retained under the uniform rule A at E4: {data['retained_uniform']}; accepted by the arms' own criteria: {data['accepted_arms']}. "
         "Speculation rate(H) = share of visibly retained candidates whose gain under H is not retained (no dimension beyond the configuration's rule-A band, or a dimension worse); combined = vetoed by any configuration (spec 06 §3). σ_D(H4) := σ_D(E4) (the E4 floor); H4 keeps E4's area and adds signoff timing and power.", "",
         "### D.1 Speculation rate per configuration and combined — retained set (uniform rule A), per tier / model / arm", "",
         "| tier | model | arm | retained | with hidden records | " + " | ".join(H) + " | combined |", "|---|---|---|---|---|" + "---|" * (len(H) + 1)]
    for k, g in sorted(data["speculation"]["uniform_retained"]["by_arm"].items()):
        t, m, a = k.split("|")
        L.append(f"| {t} | {m} | {a} | {g['n']} | {g['with_records']} | " + " | ".join(f"{_pct(g[h]['rate'])} ({g[h]['vetoed']}/{g[h]['n']})" for h in H) + f" | {_pct(g['combined_rate'])} |")
    g = data["speculation"]["uniform_retained"]["all"].get("all")
    if g:
        L.append(f"| all | | | {g['n']} | {g['with_records']} | " + " | ".join(f"{_pct(g[h]['rate'])} ({g[h]['vetoed']}/{g[h]['n']})" for h in H) + f" | {_pct(g['combined_rate'])} |")
    L += ["", "### D.2 Speculation rate by generation and by produced class (retained set)", "", "| generation | n | " + " | ".join(H) + " | combined |", "|---|---|" + "---|" * (len(H) + 1)]
    for k, g in sorted(data["speculation"]["uniform_retained"]["by_gen"].items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 99):
        L.append(f"| {k} | {g['n']} | " + " | ".join(_pct(g[h]["rate"]) for h in H) + f" | {_pct(g['combined_rate'])} |")
    L += ["", "| class | n | " + " | ".join(H) + " | combined |", "|---|---|" + "---|" * (len(H) + 1)]
    for k, g in sorted(data["speculation"]["uniform_retained"]["by_class"].items()):
        L.append(f"| {k} | {g['n']} | " + " | ".join(_pct(g[h]["rate"]) for h in H) + f" | {_pct(g['combined_rate'])} |")
    L += ["", "### D.3 The arms' own accepted sets", "", "| tier | model | arm | accepted | with records | " + " | ".join(H) + " | combined |", "|---|---|---|---|---|" + "---|" * (len(H) + 1)]
    for k, g in sorted(data["speculation"]["arms_accepted"]["by_arm"].items()):
        t, m, a = k.split("|")
        L.append(f"| {t} | {m} | {a} | {g['n']} | {g['with_records']} | " + " | ".join(_pct(g[h]["rate"]) for h in H) + f" | {_pct(g['combined_rate'])} |")
    L += ["", "### D.4 Reverse error (proven candidates not retained visibly, audit sample with hidden records: retained under H)", "", "| configuration | n | acceptable hidden | rate |", "|---|---|---|---|"]
    for h in H:
        r = data["reverse_error"][h]
        L.append(f"| {h} | {r['n']} | {r['acceptable_hidden']} | {_pct(r['rate'])} |")
    L += ["", "### D.5 Retained area gain: visible (E4) next to the hidden configurations (retained set; mean / median over candidates with a record)", "", "| tier | model | arm | visible | " + " | ".join(H) + " |", "|---|---|---|---|" + "---|" * len(H)]
    for k, g in sorted(data["gains"].items()):
        t, m, a = k.split("|")
        cell = lambda v: "-" if v["mean"] is None else f"{100 * v['mean']:.2f} / {100 * v['median']:.2f} % (n={v['n']})"
        L.append(f"| {t} | {m} | {a} | {cell(g['visible'])} | " + " | ".join(cell(g[h]) for h in H) + " |")
    L += ["", "### D.6 Coverage of the hidden records (PLAN 5 acceptance: every accepted candidate certified) and σ_D under the hidden configurations", "",
          "| configuration | retained: with record / expected | accepted: with record / expected | designs with a floor | median σ_D(area) | median t_d(area) |", "|---|---|---|---|---|---|"]
    for h in H:
        c, f = data["coverage"][h], data["floors"][h]
        L.append(f"| {h} | {c['retained_with_record']} / {c['retained_expected']} | {c['accepted_with_record']} / {c['accepted_expected']} | {f['designs_with_floor']} | {_pct(f['sigma_area_median'])} | {_pct(f['t_d_area_median'])} |")
    L.append("")
    return "\n".join(L) + "\n"


def write_reports(text, data, out_dir=None):
    out = Path(out_dir or (Path(C.ROOT) / "reports"))
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "phase5_hidden.md").write_text(text)
    slim = {k: v for k, v in data.items() if k != "per_candidate"}
    slim["per_candidate_n"] = len(data["per_candidate"])
    (out / "data" / "phase5_hidden.json").write_text(json.dumps(slim, indent=1, sort_keys=True, default=str) + "\n")
    full = out / "phase5.md"
    if full.exists():
        body = full.read_text()
        i = body.find(HIDDEN_SECTION)
        body = (body[:i] if i >= 0 else body.rstrip() + "\n\n") + text
        full.write_text(body)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only report whether the completion marker is present")
    ap.add_argument("--status-file", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--visible-db", default=None, help="tests: a visible database file instead of the project's")
    ap.add_argument("--hidden-db", default=None, help="tests: a hidden database file instead of the project's")
    a = ap.parse_args(argv)
    ok = phase5_complete(a.status_file)
    print(f"Phase 5 completion marker in STATUS.md: {'present' if ok else 'absent'}")
    if a.check:
        return 0
    if not ok:
        print("refusing to read the hidden database before Phase 5 is complete (spec 06)", file=sys.stderr)
        return 3
    cfg = C.load()
    vis = db.connect(path=a.visible_db) if a.visible_db else db.connect(cfg=cfg)
    hid = db.connect(path=a.hidden_db) if a.hidden_db else db.connect(path=hidden_db_path(cfg))
    data = build(cfg, vis, hid)
    text = render(data)
    out = write_reports(text, data, a.out)
    print(text[:2000])
    print(f"... written {out / 'phase5_hidden.md'} (and the hidden section of {out / 'phase5.md'} when present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
