#!/usr/bin/env python3
"""Phase 2.4 SEQ pilot (docs/PLAN.md, spec 03 §1 guardrail 3): class-(b)/(c1)/(c2) candidates from the hand-made
variants under data/pilot/<design_id>/ (CLAUDE.md exception 2), the RTL-OPT pairs whose flip-flop count changes,
and (later) a temporary LLM batch, all pushed through V1 -> V2 -> V3 twice with different random seeds.

    .venv/bin/python scripts/phase2_pilot.py gate    [--design ...] [--submit] [--priority N]
    .venv/bin/python scripts/phase2_pilot.py collect [--design ...]

collect writes reports/data/phase2_pilot.json: per class the proven / falsified / inconclusive / rejected / sim_fail
fractions and V3 seconds, and per SEQ-inconclusive candidate the three guardrail-3 facts: clocked arithmetic
module, V2 offsets constant across the random runs, recognisable start/valid and done/valid signals.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import datetime  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.designs import verilog as V  # noqa: E402

PILOT_DIR = Path(ROOT) / "data" / "pilot"
SEEDS = (1, 2)
START_RE = re.compile(r"(^|_)(start|valid_in|valid_i|in_valid|req|go|en|enable|load)(_|$)", re.I)
DONE_RE = re.compile(r"(^|_)(done|valid_out|valid_o|out_valid|ready|ack|busy|finish)(_|$)", re.I)


def cand_id_of(path):
    return "h" + hashlib.sha256(Path(path).read_bytes()).hexdigest()[:14]


def pilot_entries(designs=None):
    """[(design dict, variant dict with abs path and cand_id)] from every data/pilot manifest, plus the RTL-OPT
    reference versions of pairs whose flip-flop count differs from the start point (class c candidates)."""
    out = []
    for m in sorted(PILOT_DIR.glob("*/manifest.json")):
        man = json.loads(m.read_text())
        if designs and man["design_id"] not in designs:
            continue
        d = K.load_design(man["design_id"])
        for v in man["variants"]:
            path = m.parent / v["file"]
            out.append((d, dict(v, path=str(path), cand_id=cand_id_of(path), source="hand_made", top=man.get("top") or d["top"])))
    pairs_file = PILOT_DIR / "rtlopt_pairs.json"
    if pairs_file.exists():
        for rec in json.loads(pairs_file.read_text())["pairs"]:
            if designs and rec["design_id"] not in designs:
                continue
            d = K.load_design(rec["design_id"])
            path = Path(d["_dir"]) / d["reference"]["files"][0]
            out.append((d, {"file": d["reference"]["files"][0], "class": "c_pair", "note": f"RTL-OPT expert version, flip-flop bits {rec['ff_start']} -> {rec['ff_ref']}",
                            "path": str(path), "cand_id": cand_id_of(path), "source": "rtlopt_pair", "top": d["reference"]["top"]}))
    return out


def rtlopt_pairs(cfg):
    """Probe every RTL-OPT reference with Yosys and list the pairs whose flip-flop count differs from the start point
    (the class-(c) candidates PLAN 2.4 takes from RTL-OPT); written to data/pilot/rtlopt_pairs.json."""
    from src.designs import yosys_probe as YP
    pairs, all_pairs = [], []
    for d in K.load_all("rtlopt"):
        inv = d.get("inventory") or {}
        ref = d.get("reference")
        if not ref or not inv.get("yosys_ok"):
            continue
        try:
            r = YP.probe(K.abs_paths(d, ref["files"]), ref["top"], cfg, sverilog=d["sverilog"], workdir=PILOT_DIR / ".probe" / d["name"])
        except Exception as e:
            all_pairs.append({"design_id": d["design_id"], "error": str(e)[:120]})
            continue
        rec = {"design_id": d["design_id"], "ff_start": inv.get("n_ff_bits"), "ff_ref": r["n_ff_bits"], "cells_start": inv.get("n_cells"), "cells_ref": r["n_cells"]}
        all_pairs.append(rec)
        if rec["ff_start"] != rec["ff_ref"]:
            pairs.append(rec)
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    (PILOT_DIR / "rtlopt_pairs.json").write_text(json.dumps({"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "pairs": pairs, "all": all_pairs}, indent=1) + "\n")
    return pairs


def gate_jobs(cfg, entries, priority=0):
    jobs = []
    for d, v in entries:
        for seed in SEEDS:
            payload = {"design_id": d["design_id"], "cand_id": f"{v['cand_id']}_s{seed}", "d_rtl": [str(p) for p in K.abs_paths(d, d["files"])],
                       "c_rtl": [v["path"]], "top": d["top"], "clk": (d["clk_ports"] or [None])[0], "rst": d.get("rst_port"),
                       "rst_sense": d.get("rst_sense"), "sverilog": bool(d["sverilog"]), "incdirs": [str(p) for p in K.abs_paths(d, d["incdirs"])],
                       "sim_seed": seed, "note": f"pilot {v['class']} {v['file']} seed {seed}"}
            if v.get("top") and v["top"] != d["top"]:
                payload["note"] += f" (candidate top {v['top']}: renamed by the harness)"
            jobs.append({"kind": "vcf", "design_id": d["design_id"], "cand_id": payload["cand_id"], "config": "PILOT", "priority": priority, "payload": payload})
    return jobs


def records(cfg, design_id):
    raw = Path(C.results_dir(cfg)) / "raw" / design_id / "EQ"
    by = {}
    for eq in raw.glob("*/equiv.json"):
        try:
            rec = json.loads(eq.read_text())
        except json.JSONDecodeError:
            continue
        cid = rec.get("cand_id") or ""
        by.setdefault(cid, []).append((eq.stat().st_mtime, rec))
    return {cid: sorted(v)[-1][1] for cid, v in by.items()}


def is_clocked_arithmetic(text, n_ff):
    s = V.strip_comments(text)
    return bool(n_ff) and bool(re.search(r"[^=!<>]\*[^=/]|(?<![+])\+(?![+=])|(?<![-])-(?![-=>])", s)) and bool(re.search(r"\balways\s*@\s*\(\s*(posedge|negedge)", s))


def collect(cfg, entries):
    per_class = {}
    guardrail = []
    for d, v in entries:
        recs = records(cfg, d["design_id"])
        runs = [recs.get(f"{v['cand_id']}_s{seed}") for seed in SEEDS]
        verdicts = [r.get("verdict") if r else "pending" for r in runs]
        offsets = [json.loads(r["latency_offset_json"]) if r and r.get("latency_offset_json") else None for r in runs]
        v3s = [r.get("v3_seconds") for r in runs if r and r.get("v3_seconds") is not None]
        entry = {"design_id": d["design_id"], "file": v["file"], "class": v["class"], "source": v["source"], "verdicts": verdicts,
                 "offsets": offsets, "offsets_constant": (None if any(o is None for o in offsets) else offsets[0] == offsets[1]), "v3_seconds": v3s}
        cls = per_class.setdefault(v["class"], {"n": 0, "verdicts": {}, "v3_seconds": []})
        cls["n"] += 1
        cls["verdicts"][verdicts[0]] = cls["verdicts"].get(verdicts[0], 0) + 1
        cls["v3_seconds"] += v3s
        if "inconclusive" in verdicts:
            text = Path(v["path"]).read_text(errors="replace")
            ports = (d.get("inventory") or {}).get("ports") or {}
            entry["guardrail3"] = {"clocked_arithmetic": is_clocked_arithmetic(text, (d.get("inventory") or {}).get("n_ff_bits")),
                                   "offsets_constant": entry["offsets_constant"],
                                   "start_like_ports": [p for p in ports if START_RE.search(p)], "done_like_ports": [p for p in ports if DONE_RE.search(p)]}
            guardrail.append(entry["guardrail3"] | {"design_id": d["design_id"], "file": v["file"]})
        yield entry, per_class, guardrail


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["pairs", "gate", "collect"])
    ap.add_argument("--design", nargs="*", default=None)
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--priority", type=int, default=0)
    a = ap.parse_args(argv)
    cfg = C.load()
    if a.what == "pairs":
        pairs = rtlopt_pairs(cfg)
        print(f"{len(pairs)} RTL-OPT pairs with a different flip-flop count: {[p['design_id'] for p in pairs]}")
        return 0
    entries = pilot_entries(a.design)
    if a.what == "gate":
        jobs = gate_jobs(cfg, entries, a.priority)
        print(f"{len(jobs)} pilot gate jobs ({len(entries)} candidates x {len(SEEDS)} seeds)")
        if a.submit:
            from src.jobqueue.core import Queue
            conn = db.connect(cfg=cfg)
            q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
            for j in jobs:
                q.submit(j["kind"], j["payload"], design_id=j["design_id"], cand_id=j["cand_id"], config=j["config"], priority=j["priority"])
            print(f"submitted {len(jobs)} vcf jobs")
        return 0
    rows, per_class, guardrail = [], {}, []
    for entry, per_class, guardrail in collect(cfg, entries):
        rows.append(entry)
        print(f"{entry['design_id']:28s} {entry['class']:8s} {entry['file']:45s} verdicts={entry['verdicts']} offsets_constant={entry['offsets_constant']} v3s={entry['v3_seconds']}")
    for cls, s in sorted(per_class.items()):
        secs = sorted(s["v3_seconds"])
        med = secs[len(secs) // 2] if secs else None
        print(f"  class {cls:8s} n={s['n']} verdicts={s['verdicts']} median V3 s={med}")
    out = Path(ROOT) / "reports" / "data" / "phase2_pilot.json"
    out.write_text(json.dumps({"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "seeds": SEEDS, "per_class": per_class,
                               "guardrail3": guardrail, "candidates": rows}, indent=1, sort_keys=True, default=str) + "\n")
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
