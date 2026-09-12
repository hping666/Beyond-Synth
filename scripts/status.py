#!/usr/bin/env python3
"""Daily status: queue, seat pools, budget, failed jobs, secrets, disk.   .venv/bin/python scripts/status.py

Never prints secret values: the OpenAI key is reported only as configured / not configured.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.jobqueue.core import Queue, _alive  # noqa: E402
from src.jobqueue.daemon import SECRETS_FILE, read_pid  # noqa: E402


def openai_key_configured():
    """Source the secrets file in a throw-away shell and report only whether the variable is non-empty."""
    if not os.path.isfile(SECRETS_FILE):
        return False
    script = f'. "{SECRETS_FILE}" >/dev/null 2>&1; if [ -n "${{OPENAI_API_KEY:-}}" ]; then echo yes; else echo no; fi'
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    return out.stdout.strip() == "yes"


EDA_PROCS = ("common_shell_exec", "dc_shell", "pt_shell", "svi", "seeqSolve", "workerController", "vcs1fe", "simv",
             "Milkyway", "AServer", "AMonitor", "NullXServer", "yosys", "openroad")


def orphan_eda_processes():
    """EDA processes adopted by init (PPID 1): leftovers of killed or crashed jobs that keep license seats
    (eda-knowledge/05-traps.md #9, #24). DC's worker binary is common_shell_exec, not dc_shell."""
    out = subprocess.run(["ps", "-u", os.environ.get("USER", "hping"), "-o", "pid=,ppid=,etime=,comm="], capture_output=True, text=True)
    rows = []
    for line in out.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4 and parts[1] == "1" and any(parts[3].startswith(p) for p in EDA_PROCS):
            rows.append((int(parts[0]), parts[2], parts[3]))
    return rows


def main():
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    pid = read_pid(cfg)
    print(f"Beyond-Synth status   git={C.git_sha()} cfg={C.cfg_hash()}")
    print(f"daemon: {'running pid=%d' % pid if pid and _alive(pid) else 'NOT running (scripts/queue/daemon.py start)'}")
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env={})
    print("pools:")
    for pool, s in q.stats().items():
        print(f"  {pool:6s} cap={s['cap']:3d} limit={s.get('limit', s['cap']):3d} running={s['running']:3d} waiting={s['waiting']:4d} done={s['done']:5d} "
              f"failed={s['failed']:4d} backoff={s['backoff_remaining_sec']:.0f}s (level {s['backoff_level']})")
    print("budget (budget_ledger vs config):")
    caps = cfg["llm"]["budget_usd"]
    spent = {r["phase"]: r["usd"] for r in conn.execute(
        "SELECT phase, SUM(amount) AS usd FROM budget_ledger WHERE kind='llm' AND unit='usd' GROUP BY phase")}
    total = sum(spent.values())
    print(f"  LLM total: {total:.2f} / {caps['total']} USD")
    for phase, cap in caps.items():
        if phase in ("total", "reserve"):
            continue
        print(f"  LLM {phase:20s}: {spent.get(phase, 0.0):8.2f} / {cap} USD")
    for kind in ("dc", "pt", "vcf"):
        h = conn.execute("SELECT COALESCE(SUM(amount),0) FROM budget_ledger WHERE kind=? AND unit='hours'", (kind,)).fetchone()[0]
        print(f"  {kind.upper():3s} hours cumulative: {h:.2f}")
    failed = conn.execute("SELECT job_id, kind, design_id, config, error, finished_at FROM jobs WHERE state='failed' "
                          "ORDER BY finished_at DESC LIMIT 10").fetchall()
    print(f"failed jobs (last {len(failed)}):")
    for r in failed:
        print(f"  {r['job_id']} {r['kind']} {r['design_id'] or '-'} {r['config'] or '-'} {r['error']} @ {r['finished_at']}")
    print(f"OpenAI API key: {'configured' if openai_key_configured() else 'NOT configured'} ({SECRETS_FILE})")
    orphans = orphan_eda_processes()
    print(f"orphan EDA processes (PPID 1): {len(orphans)}" + ("" if not orphans else "  <- check seats, kill if hung (traps #9/#24)"))
    for pid_, etime, comm in orphans[:10]:
        print(f"  pid {pid_} up {etime} {comm}")
    for label, path in (("/ (project, results)", ROOT), ("/hdd1 (EDA tools, work)", "/hdd1")):
        try:
            u = shutil.disk_usage(path)
            print(f"disk {label}: {u.free / 2**30:.0f} GB free of {u.total / 2**30:.0f} GB ({100 * u.used / u.total:.0f}% used)")
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
