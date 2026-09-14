#!/usr/bin/env python3
"""Phase 2.1 (docs/PLAN.md, spec 02 §1–§2): perturbations for the noise floor.

    .venv/bin/python scripts/phase2_perturb.py generate [--suite ...] [--design ...] [--all]
    .venv/bin/python scripts/phase2_perturb.py gate     [--suite ...] [--design ...] [--submit] [--priority N]
    .venv/bin/python scripts/phase2_perturb.py collect  [--suite ...] [--design ...]

generate: Pyverilog perturbations under data/perturbations/<design_id>/ for the designs of the sets (split dev /
held, and rtlrewriter with E4 ok); --all takes every E4-synthesizable single-clock design instead.
gate: submits one vcf job (V1 -> V2 -> V3 SEQ) per perturbation and round trip. collect: fills `perturbations`.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.noise import gate as GT  # noqa: E402
from src.noise import generate as G  # noqa: E402


def selected(conn, a):
    rows = {r["design_id"]: dict(r) for r in conn.execute("SELECT design_id, split, e4_synthesizable FROM designs")}
    out = []
    for d in K.load_all():
        if a.suite and d["suite"] not in a.suite:
            continue
        if a.design and d["design_id"] not in a.design:
            continue
        r = rows.get(d["design_id"]) or {}
        eligible = r.get("e4_synthesizable") == 1 and "multi_clock" not in d["tags"] and "yosys_failed" not in d["tags"]
        in_sets = r.get("split") in ("dev", "held") or (d["suite"] == "rtlrewriter" and eligible)
        if a.design or (a.all and eligible) or (not a.all and in_sets):
            out.append(d)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["generate", "gate", "collect"])
    ap.add_argument("--suite", nargs="*", default=None)
    ap.add_argument("--design", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--missing", action="store_true", help="gate: only perturbations without any equivalence record (crashed / never run)")
    ap.add_argument("--priority", type=int, default=0)
    ap.add_argument("--n-per-type", type=int, default=None, help="generate: perturbations per type (config noise.n_per_type by default; 8 for spread / offset and map designs)")
    ap.add_argument("--text-p1", action="store_true", help="generate: text-level P1 renamings appended to the manifest (designs whose re-print is unusable)")
    a = ap.parse_args(argv)
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    designs = selected(conn, a)
    if a.what == "generate":
        totals, na, errors = {}, {}, []
        for d in designs:
            m = G.generate_text_p1(d, cfg, n_per_type=a.n_per_type) if a.text_p1 else G.generate(d, cfg, n_per_type=a.n_per_type)
            if m["error"] and not (a.text_p1 and m.get("text_p1", {}).get("n")):
                errors.append((d["design_id"], m["error"]))
            for p in m["perturbations"]:
                totals[p["ptype"]] = totals.get(p["ptype"], 0) + 1
            for t in m["not_applicable"]:
                na[t] = na.get(t, 0) + 1
            print(f"{d['design_id']:45s} {len(m['perturbations']):2d} perturbations  n/a={sorted(m['not_applicable'])}  {m['error'] or ''}"[:160])
        print(f"\n{len(designs)} designs: perturbations per type {totals}; not applicable {na}; parse errors {len(errors)}")
        for did, e in errors:
            print(f"  parse error {did}: {e[:120]}")
        out = Path(ROOT) / "reports" / "data" / "phase2_perturbations.json"
        out.write_text(json.dumps({"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "designs": len(designs),
                                   "per_type": totals, "not_applicable": na, "parse_errors": errors}, indent=1, sort_keys=True) + "\n")
        return 0
    if a.what == "gate":
        from src.jobqueue.core import Queue
        jobs = []
        for d in designs:
            m = GT.manifest_of(d["design_id"])
            if m and (not m.get("error") or m.get("perturbations")):  # a text-P1 manifest may carry the AST generator's error and still have entries
                new_jobs = GT.gate_jobs(d, m, cfg, priority=a.priority)
                if a.missing:  # no record and no job still queued or running for that perturbation
                    have = GT.recorded_cand_ids(cfg, d["design_id"])
                    active = {r[0] for r in conn.execute("SELECT cand_id FROM jobs WHERE kind='vcf' AND design_id=? AND state IN ('queued','running','backoff')", (d["design_id"],))}
                    new_jobs = [j for j in new_jobs if j["cand_id"] not in have and j["cand_id"] not in active]
                jobs += new_jobs
        print(f"{len(jobs)} gate jobs for {len(designs)} designs" + (" (missing records only)" if a.missing else ""))
        if a.submit:
            q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
            for j in jobs:
                q.submit(j["kind"], j["payload"], design_id=j["design_id"], cand_id=j["cand_id"], config=j["config"], priority=j["priority"])
            print(f"submitted {len(jobs)} vcf jobs")
        return 0
    summary = GT.collect(conn, cfg, designs)
    agg = {}
    for did, s in summary.items():
        for k, v in (s.get("counts") or {}).items():
            agg[k] = agg.get(k, 0) + v
        print(f"{did:45s} roundtrip={s.get('roundtrip', '-'):12s} {s.get('counts')}")
    print("totals:", agg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
