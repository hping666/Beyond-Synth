"""Job generation for the Phase 1 EDA steps (docs/PLAN.md 1.2 / 1.3): the E4 trial synthesis at the loosest
knee period, and the knee-point sweeps (config knee.periods_ns / knee.configs) per library. Only selectors and
payloads are produced; rung commands, constraints and caps stay in config/experiments.yaml."""
from src.designs import catalog as K


def trial_period(cfg, lib):
    return max(float(p) for p in cfg["knee"]["periods_ns"][lib])


def timeout_for(cfg, loc):
    t = cfg["timeouts"]
    minutes = t["dc_small"] if (loc or 0) < 500 else t["dc_medium"] if (loc or 0) < 3000 else t["dc_large"]
    return int(minutes) * 60


def dc_job(cfg, d, config, clock_ns, priority=0):
    payload = {"design_id": d["design_id"], "config": config, "rtl": [str(p) for p in K.abs_paths(d, d["files"])], "top": d["top"],
               "clock_ns": float(clock_ns), "clk_port": " ".join(d["clk_ports"]) or None, "sverilog": bool(d["sverilog"]),
               "incdirs": [str(p) for p in K.abs_paths(d, d["incdirs"])], "is_baseline": 1}
    return {"kind": "dc", "design_id": d["design_id"], "config": config, "priority": int(priority),
            "timeout_sec": timeout_for(cfg, d.get("loc")), "payload": payload}


def trial_jobs(cfg, designs, lib="nangate45", priority=0):
    config = cfg["knee"]["configs"][lib]
    return [dc_job(cfg, d, config, trial_period(cfg, lib), priority) for d in designs]


def knee_jobs(cfg, designs, libs=None, priority=0, skip_tags=("multi_clock",)):
    out = []
    for lib in (libs or list(cfg["knee"]["periods_ns"])):
        config = cfg["knee"]["configs"][lib]
        for d in designs:
            if any(t in d["tags"] for t in skip_tags):
                continue
            for period in cfg["knee"]["periods_ns"][lib]:
                out.append(dc_job(cfg, d, config, period, priority))
    return out


def knee_ext_jobs(cfg, designs, need, priority=0):
    """DECISIONS 2026-09-14 (additional task 1): two tighter periods (config knee.periods_ext_ns) for the designs whose
    Phi_main sits at the tightest swept period of a library; need: {lib: [design_id]}."""
    out = []
    by_id = {d["design_id"]: d for d in designs}
    for lib, ids in need.items():
        config = cfg["knee"]["configs"][lib]
        for did in ids:
            d = by_id.get(did)
            if d is None or "multi_clock" in d["tags"]:
                continue
            for period in cfg["knee"].get("periods_ext_ns", {}).get(lib, []):
                out.append(dc_job(cfg, d, config, float(period), priority))
    return out


def designs_at_tightest_period(cfg, conn):
    """{lib: [design_id]} whose current Phi_main equals the tightest period of knee.periods_ns on that library."""
    col = {"nangate45": "phi_main_ns_nangate45", "asap7": "phi_main_ns_asap7", "sky130hd": "phi_main_ns_sky130hd"}
    need = {}
    for lib, periods in cfg["knee"]["periods_ns"].items():
        tight = min(float(p) for p in periods)
        need[lib] = [r[0] for r in conn.execute(f"SELECT design_id FROM designs WHERE abs({col[lib]} - ?) < 1e-9 ORDER BY design_id", (tight,))]
    return need
