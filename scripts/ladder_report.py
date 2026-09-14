#!/usr/bin/env python3
"""Summarise a ladder probe JSON (scripts/ladder_probe.py --json) as Markdown: one table per design with the
per-rung numbers, then the pairwise questions the ladder definition depends on.

    .venv/bin/python scripts/ladder_report.py probe.json
"""
import json
import sys
from collections import defaultdict


def fmt(v, d=3):
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:.{d}f}"
    return str(v)


def same(a, b, keys=("area", "cells", "wns_ns", "tns_ns")):
    ma, mb = a.get("metrics") or {}, b.get("metrics") or {}
    return all(ma.get(k) == mb.get(k) for k in keys) and (a.get("hist") == b.get("hist"))


def main(path):
    rows = json.load(open(path))
    by = defaultdict(dict)
    for r in rows:
        by[r["design"]][r["config"]] = r
    order = ["E1", "E2", "E2t", "XT", "E3", "E2g", "E4", "H5"]  # E2r removed (DECISIONS 2026-09-14)
    for design, cfgs in by.items():
        clk = next(iter(cfgs.values()))["clock_ns"]
        print(f"\n### {design} (clock {clk} ns)\n")
        print("| cfg | status | area | cells | regs | WNS | TNS | crit | DP blocks | DW impl | ICG | retime log | ungroup log | hier | dc_s |")
        print("|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|")
        for c in order:
            r = cfgs.get(c)
            if not r:
                continue
            m, res, lc = r.get("metrics") or {}, r.get("resources") or {}, r.get("log_counts") or {}
            impl = ",".join(sorted({f"{i['module']}:{i['impl']}" for i in (r.get("resources") or {}).get("implementations", [])})) if isinstance(res.get("implementations"), list) else ""
            print(f"| {c} | {r['status']} | {fmt(m.get('area'))} | {fmt(m.get('cells'))} | {fmt(m.get('registers'), 0)} | {fmt(m.get('wns_ns'))} | "
                  f"{fmt(m.get('tns_ns'))} | {fmt(m.get('crit_delay_ns'))} | {fmt(res.get('datapath_blocks'))} | {impl or ','.join(res.get('dw_modules') or [])} | "
                  f"{fmt(m.get('icg_count'))} | {fmt(lc.get('retime'))} | {fmt(lc.get('ungroup'))} | {fmt(m.get('hier_cells'), 0)} | {fmt(r.get('dc_seconds'), 1)} |")
        q = []
        def cmp(a, b, label):
            if a in cfgs and b in cfgs and cfgs[a]["status"] == "ok" and cfgs[b]["status"] == "ok":
                q.append(f"- {label}: {'identical' if same(cfgs[a], cfgs[b]) else 'DIFFERENT'} "
                         f"(area {fmt((cfgs[a]['metrics'] or {}).get('area'))} vs {fmt((cfgs[b]['metrics'] or {}).get('area'))}, "
                         f"WNS {fmt((cfgs[a]['metrics'] or {}).get('wns_ns'))} vs {fmt((cfgs[b]['metrics'] or {}).get('wns_ns'))})")
        cmp("E1", "E2", "E1 -> E2 (compile_ultra: datapath / DesignWare / boundary / ungroup / area strategy)")
        cmp("E2", "E2t", "E2 vs E2t (-timing_high_effort_script; man page says ignored)")
        cmp("E2", "XT", "E2 vs XT (compile_timing_high_effort variable + retime + gate_clock)")
        cmp("E4", "XT", "E4 vs XT (E4 with the variable instead of the ignored flag)")
        cmp("E2", "E3", "E2 -> E3 (-retime, adaptive retiming)")
        cmp("E3", "E4", "E3 -> E4 (-timing_high_effort_script -gate_clock)")
        cmp("E2", "E2g", "E2 vs E2g (-gate_clock alone)")
        cmp("E4", "E2g", "E4 vs E2g (does E4 add anything beyond gate_clock on top of E2?)")
        cmp("E2", "H5", "E2 vs H5 (-no_autoungroup -gate_clock)")
        print("\n" + "\n".join(q))


if __name__ == "__main__":
    main(sys.argv[1])
