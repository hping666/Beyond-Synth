#!/usr/bin/env python3
"""Phase 1.2 inventory: parse every staged design with Yosys (ports, clock / reset inference), count lines and
markers, write the values into design.json, upsert results.sqlite.designs and reports/data/phase1_inventory.json.

    .venv/bin/python scripts/inventory.py [--suite ...] [--no-db] [--jobs 8]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.designs import catalog as K  # noqa: E402
from src.designs import inventory as I  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", nargs="*", default=None)
    ap.add_argument("--no-db", action="store_true", help="do not touch results.sqlite")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    cfg = C.load()
    designs = [d for d in K.load_all() if not a.suite or d["suite"] in a.suite]
    work = Path(tempfile.mkdtemp(prefix="bs_inventory_"))
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        invs = list(ex.map(lambda d: I.inventory_design(d, cfg, workdir=work / d["design_id"]), designs))
    conn = None if a.no_db else db.connect(cfg=cfg)
    rows, per_suite = [], {}
    for d, inv in zip(designs, invs):
        d = I.apply_inventory(d, inv)
        row = I.designs_row(d)
        if conn is not None:
            I.upsert_design(conn, row)
        rec = {**row, "tags": d["tags"], "yosys_ok": inv["yosys_ok"], "yosys_error": inv.get("yosys_error"),
               "clk_ports": d["clk_ports"], "rst_port": d["rst_port"], "rst_sense": d["rst_sense"], "sverilog": d["sverilog"],
               "flags": {k for k, v in inv["flags"].items() if v}, "n_inputs": inv.get("n_inputs"), "n_outputs": inv.get("n_outputs"),
               "in_bits": inv.get("in_bits"), "out_bits": inv.get("out_bits"), "top": d["top"]}
        rec["flags"] = sorted(rec["flags"])
        rows.append(rec)
        s = per_suite.setdefault(d["suite"], {"designs": 0, "yosys_ok": 0, "no_clock": 0, "multi_clock": 0, "tb": 0, "sverilog": 0, "flagged": 0, "loc_total": 0})
        s["designs"] += 1
        s["yosys_ok"] += inv["yosys_ok"]
        s["no_clock"] += int("no_clock" in d["tags"])
        s["multi_clock"] += int("multi_clock" in d["tags"])
        s["tb"] += int(bool(d["tb"]))
        s["sverilog"] += int(d["sverilog"])
        s["flagged"] += int(bool(rec["flags"]))
        s["loc_total"] += d["loc"]
        print(f"{d['design_id']:48s} loc={d['loc']:5d} yosys={'ok ' if inv['yosys_ok'] else 'ERR'} clk={' '.join(d['clk_ports']) or '-':14s} "
              f"rst={str(d['rst_port']) + ('/' + d['rst_sense'] if d['rst_sense'] else ''):16s} tb={'y' if d['tb'] else '-'} "
              f"sv={'y' if d['sverilog'] else '-'} flags={','.join(rec['flags']) or '-'}"
              + (f"  [{(inv.get('yosys_error') or '')[:90]}]" if not inv["yosys_ok"] else ""))
    out = Path(ROOT) / "reports" / "data" / "phase1_inventory.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "git_sha": C.git_sha(),
                               "cfg_hash": C.cfg_hash(), "per_suite": per_suite, "designs": rows}, indent=1, sort_keys=True, default=str) + "\n")
    print("\nper suite:")
    for suite, s in sorted(per_suite.items()):
        print(f"  {suite:12s} " + "  ".join(f"{k}={v}" for k, v in s.items()))
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
