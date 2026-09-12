#!/usr/bin/env python3
"""Phase 0.5 smoke: run configurations on one small design through the evaluation service (in-process, no queue)
and print a summary table.   .venv/bin/python scripts/phase0_smoke.py --configs E1 E4 [--parallel 2]

Defaults: RTLLM accu (verified_accu.v, top verified_accu, clk port clk), clocks per library from --clock-ns
(nangate45), --clock-asap7-ns, --clock-sky130-ns; H1 fixes its own 0.1 ns. Results land under results/raw/
and results.sqlite like any other evaluation (CLAUDE.md rule 7: small before large).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT  # before any other import: scripts/ must never shadow standard-library modules

import argparse  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.eval.service import evaluate  # noqa: E402

DEFAULT_RTL = "/home/hping/RTLLM/Arithmetic/Accumulator/accu/verified_accu.v"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="+", default=["E1"])
    ap.add_argument("--design-id", default="rtllm_accu")
    ap.add_argument("--rtl", nargs="+", default=[DEFAULT_RTL])
    ap.add_argument("--top", default="verified_accu")
    ap.add_argument("--clk-port", default="clk")
    ap.add_argument("--clock-ns", type=float, default=2.0)
    ap.add_argument("--clock-asap7-ns", type=float, default=0.5)
    ap.add_argument("--clock-sky130-ns", type=float, default=5.0)
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--force-rerun", action="store_true")
    ap.add_argument("--no-ingest", action="store_true")
    ap.add_argument("--saif", default=None)
    a = ap.parse_args(argv)
    cfg = C.load()
    design = {"phi_main_ns_nangate45": a.clock_ns, "phi_main_ns_asap7": a.clock_asap7_ns, "phi_main_ns_sky130hd": a.clock_sky130_ns}

    def one(name):
        t0 = time.time()
        conn = db.connect(cfg=cfg)  # SQLite connections are per thread
        try:
            m = evaluate(cfg, conn, a.design_id, a.rtl, a.top, name, design=design, clk_port=a.clk_port,
                         is_baseline=1, saif=a.saif, force_rerun=a.force_rerun, do_ingest=not a.no_ingest)
        except Exception as e:  # keep the table complete; the traceback is in the exception text
            return name, {"status": "exception", "error": repr(e)[:300], "wall_seconds": round(time.time() - t0, 1)}
        return name, m

    with ThreadPoolExecutor(max_workers=max(1, a.parallel)) as ex:
        results = dict(ex.map(one, a.configs))

    print(f"{'config':6s} {'status':22s} {'area':>10s} {'cells':>6s} {'wns':>9s} {'tns':>9s} {'icg':>4s} {'dc_s':>6s} {'wall':>6s}  error / raw_dir")
    for name in a.configs:
        m = results[name]
        met = m.get("metrics") or {}
        fmt = lambda v, w: (f"{v:{w}.4f}" if isinstance(v, float) else f"{str(v) if v is not None else '-':>{w}s}")
        print(f"{name:6s} {m.get('status', '?'):22s} {fmt(met.get('area'), 10)} {fmt(met.get('cells'), 6)} "
              f"{fmt(met.get('wns_ns'), 9)} {fmt(met.get('tns_ns'), 9)} {fmt(met.get('icg_count'), 4)} "
              f"{fmt(m.get('dc_seconds'), 6)} {fmt(m.get('wall_seconds'), 6)}  "
              f"{(m.get('error') or '')[:70] if m.get('status') != 'ok' else ('cached ' if m.get('cached') else '') + str(m.get('raw_dir', ''))}")
    bad = [n for n, m in results.items() if m.get("status") != "ok"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
