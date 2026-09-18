"""The equivalence stack (docs/spec/03-equivalence.md): V1 interface check -> V2 lock-step simulation ->
V3 VC Formal SEQ (-> V4 DPV, not yet implemented). check_equivalence() runs the levels in order inside a job
directory and returns the record fields of the `candidates` table plus a verdict:

    rejected        V1: ports differ or the candidate does not compile
    sim_fail        V2: outputs differ (mismatch) or the simulation failed
    proven_sim_only V2 found a constant latency offset (class c2) and the SEQ latency mapping is off (`equiv.seq_latency_mapping`)
    proven / falsified / inconclusive / error   V3 result (inconclusive is never promoted to proven)
"""
import json
import time
from pathlib import Path

from src.equiv import ports as PORTS
from src.equiv.harness import run_lockstep
from src.equiv.saif import finalize_vcd, retain_vcd
from src.equiv.seq import run_seq

MIN_STAGE_SEC = 20.0  # a stage is not started with less budget than this; the record says why
from src.equiv.verdict import decide, v4_acceptance


def check_equivalence(job_dir, d_files, c_files, top, cfg, *, clk=None, rst=None, rst_sense=None, d_ports=None,
                      sverilog=False, incdirs=None, run_v3=True, run_v4=True, timeout_sec=None, design_id=None, sim_seed=None,
                      c_top=None, sim_record=None):
    """c_top: the candidate's top module when it is not named like D's (RTL-OPT `<name>_ref`); ports must still match.
    run_v4: after an inconclusive SEQ, try DPV on combinational modules (no clock port) under the guardrails of
    DECISIONS 2026-09-12 (V3 falsified is final; a DPV proven needs all outputs, no assumes and a passed per-module
    vacuity check, cached by design_id). Clocked datapaths wait for the Phase 2 pilot.
    sim_record: the record of a V1 + V2-only run of the same pair (the `sim` job of the split pipeline, DECISIONS
    2026-09-16): its stages are copied (ports, control ports, lock-step result, SAIFs) and this job runs V3 (and V4)
    only; a simulation record that already carries a verdict (rejected / sim_fail / error) is copied as the verdict.
    The stages themselves are unchanged (the frozen `equiv.version` stack)."""
    job_dir = Path(job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)
    rec = {"top": top, "v1_status": None, "v1_detail": None, "v2_status": None, "v2_cycles": None, "latency_offset_json": None,
           "v3_status": None, "v3_seconds": None, "v4_status": "not_run", "counterexample_path": None, "vcd_path": None,
           "verdict": None, "proven_by": None, "seconds": None}
    t0 = time.time()

    def remaining():
        """Time left of the whole budget (None = unlimited); every stage is bounded by it so that the record
        (inconclusive / error) is written before the queue's own timeout kills the job."""
        return None if timeout_sec is None else max(0.0, float(timeout_sec) - (time.time() - t0))

    if sim_record is not None:   # split pipeline: V1 / V2 already done by the sim job
        v2, d_ports, clk, rst, rst_sense, c_top = from_sim_record(rec, sim_record)
        if rec["verdict"]:   # the simulation stage decided (rejected / sim_fail / error): copied, nothing to prove
            rec["seconds"] = round(time.time() - t0, 1)
            _dump(job_dir, rec)
            return rec
    else:
        # ---- V1: interface ----
        try:
            v1_to = min(300.0, remaining()) if timeout_sec is not None else 300.0
            d_ports = d_ports or PORTS.port_info(d_files, top, cfg, sverilog=sverilog, incdirs=incdirs, workdir=job_dir / "v1_ports_d", timeout=v1_to)
            c_ports = PORTS.port_info(c_files, c_top or top, cfg, sverilog=sverilog, incdirs=incdirs, workdir=job_dir / "v1_ports_c", timeout=v1_to)
        except PORTS.PortTimeout as e:  # no statement about the interface: an error, never a rejection
            rec.update(v1_status="error", v1_detail=str(e), verdict="error", seconds=round(time.time() - t0, 1))
            _dump(job_dir, rec)
            return rec
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
        if timeout_sec is not None and remaining() < MIN_STAGE_SEC:
            rec.update(v2_status="error", verdict="error", v2_detail="out of time before V2", seconds=round(time.time() - t0, 1))
            _dump(job_dir, rec)
            return rec
        v2 = run_lockstep(job_dir, d_files, c_files, top, d_ports, clk, rst, rst_sense, cfg, sverilog=sverilog, incdirs=incdirs, timeout_sec=remaining(), sim_seed=sim_seed, c_top=c_top)
        rec["sim_seed"] = sim_seed if sim_seed is not None else cfg["sim"]["seed"]
        rec["c_top"] = c_top or top
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
            retain_vcd(job_dir, rec, cfg)   # a sim_fail VCD is kept gzip-compressed (DECISIONS 2026-09-14); no SAIF for a non-equivalent candidate
            _dump(job_dir, rec)
            return rec
    # ---- V3: SEQ ----
    v4_accepted = False
    sv_used = v2.get("sverilog", sverilog)
    latency = latency_map(cfg, v2)   # G2.1 (b): the V2 offsets become SEQ output latencies when the mapping is enabled
    rec["latency_mapped"] = bool(latency)
    if v2["status"] == "offset" and not latency:
        rec["v3_status"] = "proven_sim_only"
    elif run_v3:
        if timeout_sec is not None and remaining() < MIN_STAGE_SEC:
            v3 = {"v3_status": "inconclusive", "v3_seconds": 0.0, "error": "out of time before V3 (V1 + V2 used the budget)", "counterexample_path": None}
        else:
            v3 = run_seq(job_dir, d_files, c_files, top, clk, rst, rst_sense, cfg, impl_top=c_top, sverilog=sv_used, timeout_sec=remaining(), incdirs=incdirs, latency=latency, design_id=design_id)
        rec["v3"] = v3
        rec["v3_status"] = v3["v3_status"]
        rec["v3_seconds"] = v3["v3_seconds"]
        rec["counterexample_path"] = v3.get("counterexample_path")
        # ---- V4: DPV, only after an inconclusive V3 (guardrail 1), combinational modules only (guardrail 3) ----
        if v3["v3_status"] == "inconclusive" and run_v4 and not clk and cfg["tools"]["vcformal"].get("dpv_app_ok"):
            from src.equiv.dpv import run_dpv, vacuity_check
            outs = [n for n, p in d_ports.items() if p["dir"] in ("output", "inout")]
            v4 = run_dpv(job_dir, d_files, c_files, top, outs, cfg, sverilog=sv_used, timeout_sec=remaining())
            rec["v4"] = v4
            rec["v4_status"] = v4["v4_status"]
            if v4["v4_status"] == "proven":
                vac = vacuity_check(job_dir, d_files, top, d_ports, cfg, design_id=design_id, sverilog=sv_used, timeout_sec=remaining())
                rec["v4_vacuity"] = vac
                v4_accepted, failed = v4_acceptance(v4, outs, vac)
                rec["v4_acceptance"] = {"accepted": v4_accepted, "failed_conditions": failed}
                if not v4_accepted:
                    rec["v4_status"] = "proven_unaccepted"   # guardrail 2: recorded, never counted as proven
            elif v4["v4_status"] == "falsified":
                rec["counterexample_path"] = v4["workdir"]
    else:
        rec["v3_status"] = "not_run"
    rec["verdict"], rec["proven_by"] = decide(rec["v1_status"], rec["v2_status"], rec["v3_status"], rec.get("v4_status"), v4_accepted, latency_mapped=bool(latency))
    rec["seconds"] = round(time.time() - t0, 1)
    finalize_vcd(job_dir, rec, cfg)   # SAIFs next to the record, VCD to scratch (DECISIONS 2026-09-14); a no-op for a V3-only job (its SAIFs are the sim record's)
    _dump(job_dir, rec)
    return rec


SIM_RECORD_KEYS = ("v1_status", "v1_detail", "v2_status", "v2_detail", "v2_cycles", "latency_offset_json", "clk", "rst", "rst_sense",
                   "ports", "sim_seed", "c_top", "saif_d", "saif_c")


def from_sim_record(rec, sim):
    """Copy the V1 / V2 stages of a `sim` job's record into `rec` (the V3-only job of the split pipeline). The VCD, kept or
    not, belongs to the simulation record; this record points at it through `sim_record`. -> (v2, d_ports, clk, rst,
    rst_sense, c_top) as the in-process stages would have left them."""
    for k in SIM_RECORD_KEYS:
        if k in sim:
            rec[k] = sim[k]
    rec["v2"] = dict(sim.get("v2") or {})
    rec["sim_record"] = sim.get("raw_dir")
    rec["vcd_path"] = None
    if sim.get("verdict") in ("rejected", "sim_fail", "error"):
        rec.update(verdict=sim.get("verdict"), v3_status="not_run", sim_verdict_copied=True)
    top = rec.get("top")
    c_top = sim.get("c_top") if sim.get("c_top") and sim.get("c_top") != top else None
    return rec["v2"], sim.get("ports"), sim.get("clk"), sim.get("rst"), sim.get("rst_sense"), c_top


def latency_map(cfg, v2):
    """{output: cycles} for SEQ when V2 found constant per-output offsets and `equiv.seq_latency_mapping` is on; every
    output is listed (offset 0 outputs keep an immediate assertion) so that no output is left uncompared; else None."""
    if v2.get("status") != "offset" or not (cfg.get("equiv") or {}).get("seq_latency_mapping", False):
        return None
    offsets = {k: int(v or 0) for k, v in (v2.get("offsets") or {}).items()}
    return offsets if any(k > 0 for k in offsets.values()) else None


def _dump(job_dir, rec):
    (Path(job_dir) / "equiv.json").write_text(json.dumps(rec, indent=1, sort_keys=True, default=str))
