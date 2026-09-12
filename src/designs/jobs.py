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
