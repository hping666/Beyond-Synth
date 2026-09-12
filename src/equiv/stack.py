"""The equivalence stack (docs/spec/03-equivalence.md): V1 interface check -> V2 lock-step simulation ->
V3 VC Formal SEQ (-> V4 DPV, not yet implemented). check_equivalence() runs the levels in order inside a job
directory and returns the record fields of the `candidates` table plus a verdict:

    rejected        V1: ports differ or the candidate does not compile
    sim_fail        V2: outputs differ (mismatch) or the simulation failed
    proven_sim_only V2 found a constant latency offset (class c2); SEQ latency mapping is a Phase 2 item
    proven / falsified / inconclusive / error   V3 result (inconclusive is never promoted to proven)
"""
import json
import time
from pathlib import Path

from src.equiv import ports as PORTS
from src.equiv.harness import run_lockstep
from src.equiv.seq import run_seq


def check_equivalence(job_dir, d_files, c_files, top, cfg, *, clk=None, rst=None, rst_sense=None, d_ports=None,
                      sverilog=False, incdirs=None, run_v3=True, timeout_sec=None):
    job_dir = Path(job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)
    rec = {"top": top, "v1_status": None, "v1_detail": None, "v2_status": None, "v2_cycles": None, "latency_offset_json": None,
           "v3_status": None, "v3_seconds": None, "v4_status": "not_run", "counterexample_path": None, "vcd_path": None,
           "verdict": None, "seconds": None}
    t0 = time.time()
    # ---- V1: interface ----
    try:
        d_ports = d_ports or PORTS.port_info(d_files, top, cfg, sverilog=sverilog, incdirs=incdirs, workdir=job_dir / "v1_ports_d")
        c_ports = PORTS.port_info(c_files, top, cfg, sverilog=sverilog, incdirs=incdirs, workdir=job_dir / "v1_ports_c")
    except PORTS.PortError as e:
        rec.update(v1_status="rejected", v1_detail=f"candidate does not elaborate: {e}", verdict="rejected", seconds=round(time.time() - t0, 1))
        _dump(job_dir, rec)
        return rec
    diffs = PORTS.compare_ports(d_ports, c_ports)
    if diffs:
        rec.update(v1_status="rejected", v1_detail="; ".join(diffs)[:500], verdict="rejected", seconds=round(time.time() - t0, 1))
        _dump(job_dir, rec)
        return rec
    rec["v1_status"] = "ok"
    if clk is None and rst is None:
        clk, rst, rst_sense = PORTS.infer_control_ports(d_ports)
    rec.update(clk=clk, rst=rst, rst_sense=rst_sense, ports=d_ports)
    # ---- V2: lock-step simulation ----
    v2 = run_lockstep(job_dir, d_files, c_files, top, d_ports, clk, rst, rst_sense, cfg, sverilog=sverilog, incdirs=incdirs, timeout_sec=timeout_sec)
    rec["v2"] = {k: v for k, v in v2.items() if k not in ("inputs", "outputs")}
    rec["v2_cycles"] = v2.get("cycles")
    rec["vcd_path"] = v2.get("vcd")
    if v2["status"] == "compile_failed":
        rec.update(v1_status="rejected", v1_detail=v2.get("error"), v2_status="compile_failed", verdict="rejected")
    elif v2["status"] in ("identical", "offset"):
        rec["v2_status"] = v2["status"]
        rec["latency_offset_json"] = json.dumps(v2["offsets"], sort_keys=True)
    else:
        rec.update(v2_status="sim_fail", verdict="sim_fail")
        rec["v2_detail"] = v2.get("error") or json.dumps(v2.get("mismatches"), sort_keys=True)[:500]
    if rec["verdict"]:
        rec["seconds"] = round(time.time() - t0, 1)
        _dump(job_dir, rec)
        return rec
    # ---- V3: SEQ ----
    if v2["status"] == "offset":
        rec.update(v3_status="proven_sim_only", verdict="proven_sim_only")
    elif run_v3:
        v3 = run_seq(job_dir, d_files, c_files, top, clk, rst, rst_sense, cfg, sverilog=v2.get("sverilog", sverilog), timeout_sec=timeout_sec)
        rec["v3"] = v3
        rec["v3_status"] = v3["v3_status"]
        rec["v3_seconds"] = v3["v3_seconds"]
        rec["counterexample_path"] = v3.get("counterexample_path")
        rec["verdict"] = v3["v3_status"]
    else:
        rec.update(v3_status="not_run", verdict="not_run")
    rec["seconds"] = round(time.time() - t0, 1)
    _dump(job_dir, rec)
    return rec


def _dump(job_dir, rec):
    (Path(job_dir) / "equiv.json").write_text(json.dumps(rec, indent=1, sort_keys=True, default=str))
