#!/usr/bin/env python3
"""Ladder probe (G0 follow-up): run a list of designs through several DC configurations at a chosen clock and
print one row per (design, config) with the numbers that tell the rungs apart: area, cells, WNS, TNS, critical
path, registers, ICGs, datapath blocks, DesignWare implementations, retiming / ungrouping log counts, DC seconds.
Records go to results/raw only (no DB ingest: the clocks are probe values, not knee points).

    .venv/bin/python scripts/ladder_probe.py --designs div_16bit:3.0 multi_pipe_8bit:1.0 --configs E1 E2 E3 E4 --parallel 6
Design spec: <rtllm_dir_name>:<clock_ns>[:<top>]; the RTL is /home/hping/RTLLM/*/*/<name>/verified_*.v, the top
is read from the file, the clock port is inferred from the port list (combinational designs get a virtual clock).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import glob  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

from src import config as C  # noqa: E402
from src.equiv import ports as PORTS  # noqa: E402
from src.eval.service import evaluate  # noqa: E402


def find_design(name):
    files = glob.glob(f"/home/hping/RTLLM/*/*/{name}/verified_*.v") or glob.glob(f"/home/hping/RTLLM/*/*/{name}/*.v")
    files = [f for f in files if not f.endswith("testbench.v")]
    if not files:
        raise SystemExit(f"no RTL for {name}")
    rtl = files[0]
    m = re.search(r"^\s*module\s+(\w+)", open(rtl, errors="replace").read(), re.M)
    return rtl, m.group(1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", nargs="+", required=True)
    ap.add_argument("--configs", nargs="+", default=["E1", "E1d", "E2", "E3", "E4", "E2r", "E2g"])
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--ingest", action="store_true", help="also write ok records to results.sqlite (default: raw only)")
    ap.add_argument("--json", default=None, help="write all records to this JSON file")
    ap.add_argument("--extra-config", action="append", default=[], metavar="NAME=COMPILE",
                    help="temporary DC configuration (nangate45, phi_main) injected for this probe only, e.g. "
                         "X1='set_app_var compile_timing_high_effort true; compile_ultra -retime -gate_clock'")
    a = ap.parse_args(argv)
    cfg = C.load()
    for spec in a.extra_config:
        name, compile_cmd = spec.split("=", 1)
        entry = {"tool": "dc", "compile": compile_cmd, "lib": "nangate45", "clock": "phi_main", "probe_only": True}
        if "|synlib=" in compile_cmd:  # NAME=<compile>|synlib=standard
            entry["compile"], synlib = compile_cmd.split("|synlib=", 1)
            entry["synlib"] = synlib.strip()
        cfg["configs"][name] = entry
        if name not in a.configs:
            a.configs.append(name)
    jobs = []
    for spec in a.designs:
        parts = spec.split(":")
        name, clock = parts[0], float(parts[1])
        rtl, top = find_design(name)
        if len(parts) > 2:
            top = parts[2]
        sv = False
        try:
            ports = PORTS.port_info([rtl], top, cfg, sverilog=False)
        except PORTS.PortError:
            ports = PORTS.port_info([rtl], top, cfg, sverilog=True)
            sv = True
        clk, rst, sense = PORTS.infer_control_ports(ports)
        for conf in a.configs:
            jobs.append((name, rtl, top, clock, clk, sv, conf))

    def one(job):
        name, rtl, top, clock, clk, sv, conf = job
        from src.db import core as db
        conn = db.connect(cfg=cfg) if a.ingest else None
        t0 = time.time()
        try:
            m = evaluate(cfg, conn, f"rtllm_{name}", [rtl], top, conf, clock_ns=clock, clk_port=clk, is_baseline=1,
                         sverilog=sv, do_ingest=a.ingest)
        except Exception as e:
            m = {"status": "exception", "error": repr(e)[:200], "wall_seconds": round(time.time() - t0, 1)}
        return job, m

    with ThreadPoolExecutor(max_workers=max(1, a.parallel)) as ex:
        results = list(ex.map(one, jobs))

    hdr = f"{'design':17s} {'cfg':4s} {'status':12s} {'area':>9s} {'cells':>6s} {'wns':>8s} {'tns':>8s} {'crit':>7s} {'regs':>5s} {'icg':>4s} {'dp':>3s} {'dw_impl':>18s} {'retime':>6s} {'ungrp':>5s} {'dc_s':>6s}"
    print(hdr)
    out = []
    for (name, rtl, top, clock, clk, sv, conf), m in results:
        met = m.get("metrics") or {}
        res = m.get("resources") or {}
        ls = (m.get("log_summary") or {}).get("counts") or {}
        impl = ",".join(sorted({f"{i['module']}:{i['impl']}" for i in res.get("implementations", [])}))[:18]
        f = lambda v, w, d=3: (f"{v:{w}.{d}f}" if isinstance(v, float) else f"{str(v) if v is not None else '-':>{w}s}")
        print(f"{name:17s} {conf:4s} {m.get('status', '?')[:12]:12s} {f(met.get('area'), 9)} {f(met.get('cells'), 6)} "
              f"{f(met.get('wns_ns'), 8)} {f(met.get('tns_ns'), 8)} {f(met.get('crit_delay_ns'), 7)} {f(met.get('registers'), 5, 0)} "
              f"{f(met.get('icg_count'), 4)} {f(res.get('datapath_blocks'), 3)} {impl:>18s} {f(ls.get('retime'), 6)} {f(ls.get('ungroup'), 5)} "
              f"{f(m.get('dc_seconds'), 6, 1)}" + (f"  ! {str(m.get('error'))[:60]}" if m.get("status") != "ok" else ""))
        out.append({"design": name, "config": conf, "clock_ns": clock, "clk_port": clk, "sverilog": sv, "status": m.get("status"),
                    "error": m.get("error"), "metrics": met, "resources": {k: v for k, v in res.items() if k != "resources"},
                    "log_counts": ls, "log_samples": (m.get("log_summary") or {}).get("samples"), "hist": m.get("hist"),
                    "raw_dir": m.get("raw_dir"), "dc_seconds": m.get("dc_seconds")})
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1, sort_keys=True, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
