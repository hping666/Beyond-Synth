#!/usr/bin/env python3
"""Staged Phase 5 reports (user decision 2026-09-16): every --interval minutes check which tiers are complete — every planned run
of the tier (scripts/phase5_main.plan) has status done — and render the stage reports once each: A (large tier), B (large +
medium), C (every tier; also reports/phase5.md, the visible part). A stage is final only under the completeness rule of
DECISION 2026-09-18 D2 / D3 (every planned run done, no pending evaluation, no open visible job); until then every stage
whose newest tier has started is re-rendered as an interim report every --interim hours (pending columns, `pending` cells). Anomalies (failed search jobs, free space
below 25 GB, runs paused by the disk guard) are logged with the word ANOMALY. Detached like the other loops (setsid, pid file).
    .venv/bin/python scripts/phase5_stages.py start [--interval 15] [--interim 3]
    .venv/bin/python scripts/phase5_stages.py stop | status | once
Markers: reports/data/phase5_stage_<X>.done (a stage is rendered as final once; the operator commits the files)."""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
import argparse  # noqa: E402
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402

PID = os.path.join(ROOT, "results", "queue", "phase5_stages.pid")
LOG = os.path.join(ROOT, "results", "queue", "phase5_stages.log")
STAGES = (("A", ["large"]), ("B", ["large", "medium"]), ("C", ["large", "medium", "small"]))


def planned_runs(cfg, conn):
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import phase5_main as PM
    return PM.plan(cfg, conn)["runs"]


def tier_complete(cfg, conn, tier, exp="phase5", plan=None):
    """True when every planned run of the tier exists with status done (superseded rows do not count)."""
    plan = plan if plan is not None else planned_runs(cfg, conn)
    wanted = [(r["model"], r["arm"], r["design_id"], int(r["seed"])) for r in plan if r["tier"] == tier]
    if not wanted:
        return False
    done = {(r[0], r[1], r[2], int(r[3])) for r in conn.execute("SELECT llm_model, arm, design_id, seed FROM runs WHERE exp=? AND status='done'", (exp,))}
    return all(w in done for w in wanted)


def marker(stage):
    return os.path.join(ROOT, "reports", "data", f"phase5_stage_{stage}.done")


def render(cfg, stage, final=False):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "report_phase.py"), "phase5", "--stage", stage] + (["--final"] if final else []), capture_output=True, text=True, timeout=3600)
    return r.returncode, (r.stdout + r.stderr)[-600:]


def evaluation_complete(cfg, conn, tiers):
    """The completeness rule of DECISION 2026-09-18 D2 / D3: no pending evaluation (verdict, offline simulation, proof of a
    prescreened candidate, E4 record of a proven candidate) and no open visible job on the tiers' designs.
    -> (complete, summary) with the summary from src.analysis.phase5.pending_summary."""
    from src.analysis import phase5 as P5
    s = P5.pending_summary(cfg, conn, tiers)
    return bool(s["complete"]), s


def anomalies(cfg, conn):
    out = []
    failed = conn.execute("SELECT COUNT(*) FROM jobs WHERE kind='search' AND state='failed' AND submitted_at > '2026-09-15T21:39'").fetchone()[0]
    if failed:
        out.append(f"{failed} failed search jobs")
    free = shutil.disk_usage(C.results_dir(cfg)).free / 1e9
    if free < 25:
        out.append(f"free space {free:.1f} GB")
    paused = conn.execute("SELECT COUNT(*) FROM runs WHERE exp='phase5' AND status='paused_disk'").fetchone()[0]
    if paused:
        out.append(f"{paused} runs paused by the disk guard")
    return out


def once(cfg, interim_hours=3.0, log=print):
    conn = db.connect(cfg=cfg)
    plan = planned_runs(cfg, conn)
    an = anomalies(cfg, conn)
    if an:
        log("ANOMALY: " + "; ".join(an))
    st = {r[0]: r[1] for r in conn.execute("SELECT status, COUNT(*) FROM runs WHERE exp='phase5' AND status != 'superseded' GROUP BY status")}
    log(f"runs {st}")
    current = None
    for stage, tiers in STAGES:
        if os.path.exists(marker(stage)):
            continue
        runs_done = all(tier_complete(cfg, conn, t, plan=plan) for t in tiers)
        evals_done, summary = evaluation_complete(cfg, conn, tiers) if runs_done else (False, None)
        if runs_done and evals_done:   # DECISION 2026-09-18 D2 / D3: final only when the runs are done and nothing is pending
            rc, out = render(cfg, stage, final=True)
            if rc == 0:
                with open(marker(stage), "w") as f:
                    json.dump({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "tiers": tiers, "pending": summary}, f)
                log(f"STAGE {stage} WRITTEN (final for its tiers): reports/phase5_stage_{stage}.md")
            else:
                log(f"stage {stage} render failed rc={rc}: {out}")
            continue
        if runs_done:
            log(f"stage {stage}: every run done, evaluations pending {summary['pending']}, open jobs {summary['open_jobs']} -> interim")
        current = current or stage
    # DECISION 2026-09-18 D3: every stage that is not final yet and whose newest tier has started is re-rendered as an interim
    # report (pending columns) every --interim hours — B while the medium tier runs, C once the small tier starts
    started = {r[0] for r in conn.execute("SELECT DISTINCT design_id FROM runs WHERE exp='phase5' AND status NOT IN ('created', 'superseded')")}
    tier_of = {d: t for t, ds in (cfg["exp5"].get("starting_points") or {}).items() for d in ds}
    for stage, tiers in STAGES:
        if os.path.exists(marker(stage)) or not any(tier_of.get(d) == tiers[-1] for d in started):
            continue
        path = os.path.join(ROOT, "reports", f"phase5_stage_{stage}.md")
        age_h = (time.time() - os.path.getmtime(path)) / 3600.0 if os.path.exists(path) else 1e9
        if age_h >= interim_hours:
            rc, out = render(cfg, stage)
            log(f"interim stage {stage} rendered rc={rc}" if rc == 0 else f"interim stage {stage} render failed rc={rc}: {out}")
    return 0


def loop(interval_min, interim_hours):
    with open(PID, "w") as f:
        f.write(str(os.getpid()))
    stop = {"flag": False}

    def on_signal(signum, frame):
        stop["flag"] = True
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    with open(LOG, "a") as logf:
        def log(msg):
            logf.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n")
            logf.flush()
        log(f"stages loop started pid {os.getpid()} interval {interval_min} min interim {interim_hours} h")
        while not stop["flag"]:
            try:
                once(C.load(), interim_hours, log)
            except Exception as e:
                log(f"check failed: {type(e).__name__}: {e}")
            for _ in range(int(interval_min * 60)):
                if stop["flag"]:
                    break
                time.sleep(1)
        log("stages loop stopped")
    try:
        os.remove(PID)
    except OSError:
        pass


def running():
    if not os.path.exists(PID):
        return None
    try:
        pid = int(open(PID).read().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["start", "stop", "status", "once", "_run"])
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--interim", type=float, default=3.0)
    a = ap.parse_args(argv)
    cfg = C.load()
    if a.what == "once":
        return once(cfg, a.interim)
    if a.what == "_run":
        loop(a.interval, a.interim)
        return 0
    if a.what == "status":
        pid = running()
        print(f"stages loop: {'running pid ' + str(pid) if pid else 'not running'} (log {LOG})")
        return 0
    if a.what == "stop":
        pid = running()
        if pid:
            os.kill(pid, signal.SIGTERM)
            print(f"stop signal sent to pid {pid}")
        else:
            print("not running")
        return 0
    if running():
        print(f"already running pid {running()}")
        return 0
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    subprocess.Popen(["setsid", sys.executable, os.path.abspath(__file__), "_run", "--interval", str(a.interval), "--interim", str(a.interim)],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(1)
    print(f"stages loop started ({'pid ' + str(running()) if running() else 'pid file not yet written'}); log {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
