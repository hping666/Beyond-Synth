"""Bidirectional tests for the job queue (scripts/queue/core.py): good jobs finish as done, bad jobs end as
failed after one retry, exit 75 backs the pool off without counting an attempt, pool caps hold, timeouts kill
the whole process group, and a restarted daemon recovers jobs it did not spawn."""
import copy
import os
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.jobqueue.core import Queue, EX_TEMPFAIL, TIMEOUT_RC  # noqa: E402


def make_cfg(local_max=2, retries=1, backoff=(0.3, 0.6, 2)):
    cfg = copy.deepcopy(C.load())
    cfg["queue"]["local_max"] = local_max
    cfg["queue"]["retries"] = retries
    cfg["queue"]["backoff"] = {"initial_sec": backoff[0], "max_sec": backoff[1], "factor": backoff[2]}
    return cfg


@pytest.fixture
def q(tmp_path):
    cfg = make_cfg()
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    return Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)


def wait_state(q, jid, states, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        q.tick()
        st = q.get(jid)["state"]
        if st in states:
            return st
        time.sleep(0.05)
    return q.get(jid)["state"]


def test_good_job_done(q):
    jid = q.submit("shell", {"cmd": "echo hello-from-job"})
    assert q.get(jid)["state"] == "queued"
    assert wait_state(q, jid, {"done"}) == "done"
    job = q.get(jid)
    assert job["exit_code"] == 0 and job["attempts"] == 0 and job["finished_at"]
    assert "hello-from-job" in open(job["log_path"]).read()
    assert open(job["done_path"]).read().strip() == "0"


def test_bad_job_retried_once_then_failed(q):
    jid = q.submit("shell", {"cmd": "exit 3"})
    assert wait_state(q, jid, {"failed"}) == "failed"
    job = q.get(jid)
    assert job["exit_code"] == 3 and job["attempts"] == 2 and "exit 3" in job["error"]
    # both attempts left their own log and done marker (append-only)
    assert os.path.exists(os.path.join(q.log_dir, f"{jid}.a0.log")) and os.path.exists(os.path.join(q.log_dir, f"{jid}.a1.done"))


def test_license_exit_75_backs_off_without_counting_attempt(q, tmp_path):
    marker = tmp_path / "second_run"
    cmd = f"if [ -f {marker} ]; then exit 0; else touch {marker}; exit {EX_TEMPFAIL}; fi"
    jid = q.submit("shell", {"cmd": cmd})
    assert wait_state(q, jid, {"backoff"}) == "backoff"
    assert q.get(jid)["attempts"] == 0
    s = q.stats()["local"]
    assert s["backoff_level"] == 1 and s["backoff_remaining_sec"] > 0
    q.tick()  # inside the backoff window: must not be dispatched
    assert q.get(jid)["state"] == "backoff"
    time.sleep(0.35)  # initial backoff is 0.3 s in the test config
    assert wait_state(q, jid, {"done"}) == "done"
    assert q.stats()["local"]["backoff_level"] == 0  # a success resets the pool backoff


def test_pool_cap_is_respected(q):
    ids = [q.submit("shell", {"cmd": "sleep 0.4"}) for _ in range(3)]
    q.tick()
    states = [q.get(j)["state"] for j in ids]
    assert states.count("running") == 2 and states.count("queued") == 1
    assert q.running_in_pool("local") == 2
    for j in ids:
        assert wait_state(q, j, {"done"}) == "done"


def test_priority_order(q):
    q.caps["local"] = 1
    low = q.submit("shell", {"cmd": "echo low"}, priority=0)
    high = q.submit("shell", {"cmd": "echo high"}, priority=10)
    q.tick()
    assert q.get(high)["state"] == "running" and q.get(low)["state"] == "queued"
    assert wait_state(q, low, {"done"}) == "done"


def test_timeout_kills_process_group(q, tmp_path):
    q.retries = 0
    tag = f"bs_timeout_probe_{os.getpid()}"
    jid = q.submit("shell", {"cmd": f"sleep 30 & echo {tag} > /dev/null; sleep 30"}, timeout_sec=0.5)
    assert wait_state(q, jid, {"failed"}, timeout=15) == "failed"
    job = q.get(jid)
    assert job["exit_code"] == TIMEOUT_RC and "timeout" in job["error"]
    time.sleep(0.2)
    alive = subprocess.run(["pgrep", "-f", f"^bash -c .*{tag}"], capture_output=True, text=True).stdout.strip()
    assert alive == "", f"wrapper still alive: {alive}"


def test_recover_after_daemon_restart(q, tmp_path):
    jid = q.submit("shell", {"cmd": "sleep 0.3; echo recovered"})
    q.tick()
    assert q.get(jid)["state"] == "running"
    # a new daemon on the same database: it did not spawn the job, so it must recover the outcome from the marker
    q2 = Queue(q.cfg, q.conn, q.log_dir, env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    assert q2.children == {}
    assert wait_state(q2, jid, {"done"}) == "done"


def test_vanished_process_is_retried_then_failed(q):
    jid = q.submit("shell", {"cmd": "true"})
    # forge a running row whose pid is dead and that has no done marker (daemon crashed mid-flight)
    q._set(jid, state="running", host_pid=2**22 - 1, started_at=db.now(), done_path=os.path.join(q.log_dir, "nonexistent.done"))
    q.tick()
    assert q.get(jid)["state"] in ("queued", "running")  # retried
    assert wait_state(q, jid, {"done"}) == "done"


def test_unknown_kind_or_pool_rejected(q):
    with pytest.raises(ValueError):
        q.submit("teleport", {"cmd": "x"})
    with pytest.raises(ValueError):
        q.submit("shell", {"cmd": "x"}, pool="gpu")
    with pytest.raises(ValueError):
        q.submit("shell", {})


def test_submit_cli_dry_run_inserts_nothing(tmp_path):
    spec = tmp_path / "jobs.yaml"
    spec.write_text("jobs:\n  - kind: shell\n    payload: {cmd: 'echo x'}\n")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/queue/submit.py"), str(spec), "--dry-run"],
                         capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0 and "DRY-RUN" in out.stdout, out.stderr
    bad = tmp_path / "bad.yaml"
    bad.write_text("jobs:\n  - kind: teleport\n    payload: {cmd: 'echo x'}\n")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/queue/submit.py"), str(bad), "--dry-run"],
                         capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 2


def test_status_script_runs():
    out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/status.py")], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    assert "pools:" in out.stdout and "OpenAI API key:" in out.stdout
    assert "sk-" not in out.stdout


def test_dispatch_limit_below_the_seat_cap(tmp_path):
    """config queue.dc_concurrency (DECISIONS 2026-09-12) limits how many DC jobs run at once; the seat cap stays."""
    cfg = make_cfg()
    cfg["queue"]["dc_seats_max"] = 50
    cfg["queue"]["dc_concurrency"] = 1
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    assert q.caps["dc"] == 50 and q.limits["dc"] == 1 and q.limits["local"] == q.caps["local"]
    j1 = q.submit("shell", {"cmd": "sleep 0.4"}, pool="dc")
    j2 = q.submit("shell", {"cmd": "sleep 0.4"}, pool="dc")
    q.tick()
    assert sorted(q.get(j)["state"] for j in (j1, j2)) == ["queued", "running"] and q.stats()["dc"]["limit"] == 1
    assert wait_state(q, j1, {"done"}, timeout=15) == "done" and wait_state(q, j2, {"done"}, timeout=15) == "done"  # either may start first
    del cfg["queue"]["dc_concurrency"]
    q2 = Queue(cfg, conn, str(tmp_path / "logs2"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    assert q2.limits["dc"] == 50 and q2.stats()["dc"]["limit"] == 50


def test_hidden_kind_maps_to_the_dc_pool_and_the_hidden_worker():
    from src.jobqueue.core import POOL_OF_KIND, RUNNER_OF_KIND
    assert POOL_OF_KIND["dc_hidden"] == "dc" and RUNNER_OF_KIND["dc_hidden"] == "scripts.hidden_worker"
