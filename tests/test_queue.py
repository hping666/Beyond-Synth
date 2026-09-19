"""Bidirectional tests for the job queue (scripts/queue/core.py): good jobs finish as done, bad jobs end as
failed after one retry, exit 75 backs the pool off without counting an attempt, pool caps hold, timeouts kill
the whole process group, and a restarted daemon recovers jobs it did not spawn."""
import copy
import json
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
    """config queue.dc_seats_target (DECISIONS 2026-09-14; formerly dc_concurrency) limits how many DC jobs run at once; the seat cap stays."""
    cfg = make_cfg()
    cfg["queue"]["dc_seats_max"] = 50
    cfg["queue"].pop("dc_concurrency", None)
    cfg["queue"]["dc_seats_target"] = 1
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    assert q.caps["dc"] == 50 and q.limits["dc"] == 1 and q.limits["local"] == q.caps["local"]
    j1 = q.submit("shell", {"cmd": "sleep 0.4"}, pool="dc")
    j2 = q.submit("shell", {"cmd": "sleep 0.4"}, pool="dc")
    q.tick()
    assert sorted(q.get(j)["state"] for j in (j1, j2)) == ["queued", "running"] and q.stats()["dc"]["limit"] == 1
    assert wait_state(q, j1, {"done"}, timeout=15) == "done" and wait_state(q, j2, {"done"}, timeout=15) == "done"  # either may start first
    del cfg["queue"]["dc_seats_target"]
    q2 = Queue(cfg, conn, str(tmp_path / "logs2"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    assert q2.limits["dc"] == 50 and q2.stats()["dc"]["limit"] == 50
    cfg["queue"]["dc_concurrency"] = 2  # the old key still works
    assert Queue(cfg, conn, str(tmp_path / "logs3"), env={"PATH": os.environ["PATH"]}, log=lambda m: None).limits["dc"] == 2


def test_hidden_kind_maps_to_the_dc_pool_and_the_hidden_worker():
    from src.jobqueue.core import POOL_OF_KIND, RUNNER_OF_KIND
    assert POOL_OF_KIND["dc_hidden"] == "dc" and RUNNER_OF_KIND["dc_hidden"] == "scripts.hidden_worker"


def test_unspawnable_job_fails_alone_and_the_pool_keeps_dispatching(q, monkeypatch):
    """A daemon running older code met a job kind it did not know (dc_hidden, 2026-09-13) and stopped dispatching everything."""
    from src.jobqueue import core as QC
    bad = q.submit("shell", {"cmd": "echo never"}, pool="local")
    q.conn.execute("UPDATE jobs SET kind='mystery' WHERE job_id=?", (bad,))
    good = q.submit("shell", {"cmd": "echo fine"}, pool="local")
    q.tick()
    assert q.get(bad)["state"] == "failed" and "cannot spawn" in q.get(bad)["error"]
    assert wait_state(q, good, {"done"}) == "done"


def test_per_design_fairness_in_a_pool(tmp_path):
    """config queue.per_design_max (DECISIONS 2026-09-14): a design cannot hold more than N running jobs of a pool while
    other designs wait; without other designs' jobs the seats stay unused rather than exceeding N; no cap changes."""
    cfg = make_cfg()
    cfg["queue"]["local_max"] = 4
    cfg["queue"]["per_design_max"] = {"local": 1}
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    a1 = q.submit("shell", {"cmd": "sleep 0.6"}, design_id="A", priority=5)
    a2 = q.submit("shell", {"cmd": "sleep 0.6"}, design_id="A", priority=5)
    b1 = q.submit("shell", {"cmd": "sleep 0.6"}, design_id="B", priority=0)
    q.tick()
    states = {j: q.get(j)["state"] for j in (a1, a2, b1)}
    running_a = [j for j in (a1, a2) if states[j] == "running"]
    assert len(running_a) == 1 and states[b1] == "running"   # one of A's jobs waits although its priority is higher; B's job runs
    waiting_a = a2 if running_a == [a1] else a1
    assert wait_state(q, running_a[0], {"done"}, timeout=15) == "done"
    q.tick()
    assert q.get(waiting_a)["state"] == "running"   # A's seat frees: its second job starts
    assert wait_state(q, waiting_a, {"done"}, timeout=15) == "done" and wait_state(q, b1, {"done"}, timeout=15) == "done"


def test_pool_hours_from_the_jobs_table(tmp_path):
    """2026-09-15: seat-hours per pool come from the jobs table (finished jobs by their timestamps, running jobs up to now);
    jobs never started, malformed timestamps and other pools do not count (both directions)."""
    import datetime
    from src.db import core as db
    from src.jobqueue.core import pool_hours
    conn = db.connect(path=str(tmp_path / "q.sqlite"))
    base = {"kind": "dc", "priority": 0, "payload_json": "{}", "attempts": 0, "submitted_at": "2026-09-15T10:00:00"}
    db.insert(conn, "jobs", {**base, "job_id": "a", "pool": "dc", "state": "done", "started_at": "2026-09-15T10:00:00", "finished_at": "2026-09-15T11:30:00"})
    db.insert(conn, "jobs", {**base, "job_id": "b", "pool": "dc", "state": "failed", "started_at": "2026-09-15T10:00:00", "finished_at": "2026-09-15T10:30:00"})
    db.insert(conn, "jobs", {**base, "job_id": "c", "pool": "pt", "state": "running", "started_at": "2026-09-15T12:00:00", "finished_at": None})
    db.insert(conn, "jobs", {**base, "job_id": "d", "pool": "vcf", "state": "queued", "started_at": None, "finished_at": None})
    db.insert(conn, "jobs", {**base, "job_id": "e", "pool": "vcf", "state": "done", "started_at": "garbage", "finished_at": "2026-09-15T13:00:00"})
    h = pool_hours(conn, now=datetime.datetime(2026, 9, 15, 12, 15, 0))
    assert abs(h["dc"] - 2.0) < 1e-9 and abs(h["pt"] - 0.25) < 1e-9 and "vcf" not in h


def test_search_runs_have_their_own_pool(tmp_path):
    """2026-09-15: search runs (kind search) are dispatched from the `search` pool (config queue.search_max) and do not count
    against the local pool whose yosys / sim / llm jobs they wait for (both directions: a running search job leaves the local
    pool free; a running yosys job leaves the search pool free)."""
    from src.jobqueue.core import POOL_OF_KIND, Queue
    from src import config as C
    from src.db import core as db
    cfg = C.load()
    assert POOL_OF_KIND["search"] == "search" and POOL_OF_KIND["yosys"] == "local"
    conn = db.connect(path=str(tmp_path / "q.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={}, log=lambda m: None)
    assert q.caps["search"] == int(cfg["queue"]["search_max"]) and "search" in q.limits and q.caps["local"] == int(cfg["queue"]["local_max"])
    js = q.submit("search", {"run_id": "r1"}, config="search")
    jy = q.submit("yosys", {"module": "x"}, config="Y")
    assert conn.execute("SELECT pool FROM jobs WHERE job_id=?", (js,)).fetchone()[0] == "search"
    assert conn.execute("SELECT pool FROM jobs WHERE job_id=?", (jy,)).fetchone()[0] == "local"
    conn.execute("UPDATE jobs SET state='running' WHERE job_id IN (?, ?)", (js, jy)); conn.commit()
    assert q.running_in_pool("search") == 1 and q.running_in_pool("local") == 1
    assert q.stats()["search"]["running"] == 1 and q.stats()["local"]["running"] == 1


def test_search_backpressure_from_the_vcf_queue(tmp_path):
    """User decision 2026-09-16: a search run is not started while the vcf pool is saturated and more than max_waiting proofs wait; it
    starts when the queue drains or when the vcf seats are not all busy (fairness-idled seats do not count) — both directions."""
    cfg = make_cfg()
    cfg["queue"]["search_max"] = 4
    cfg["queue"]["vcf_seats_max"] = 2
    cfg["queue"].pop("vcf_seats_target", None)
    cfg["queue"]["backpressure"] = {"search": {"pool": "vcf", "max_waiting": 1}}
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    base = {"kind": "vcf", "priority": 0, "payload_json": "{}", "attempts": 0, "submitted_at": "2026-09-16T01:00:00", "pool": "vcf"}
    for i, st in enumerate(("running", "running", "queued", "queued")):        # vcf saturated (2 of 2) with 2 waiting > 1
        db.insert(conn, "jobs", {**base, "job_id": f"v{i}", "state": st})
    sj = q.submit("shell", {"cmd": "sleep 0.3"}, pool="search", priority=5)
    q._dispatch()
    assert q.get(sj)["state"] == "queued" and q.backpressure_holds("search")
    conn.execute("UPDATE jobs SET state='done' WHERE job_id='v3'"); conn.commit()   # the queue drains to 1 waiting: not more than max_waiting
    assert not q.backpressure_holds("search")
    q._dispatch()
    assert q.get(sj)["state"] == "running"
    assert wait_state(q, sj, {"done"}, timeout=15) == "done"
    db.insert(conn, "jobs", {**base, "job_id": "v5", "state": "queued"})
    db.insert(conn, "jobs", {**base, "job_id": "v6", "state": "queued"})
    conn.execute("UPDATE jobs SET state='done' WHERE job_id='v1'"); conn.commit()   # one vcf seat free (fairness could be the reason): not saturated -> no backpressure
    assert not q.backpressure_holds("search")
    # a resumption (a run that already made calls) is dispatched although the backpressure holds; a fresh run is not
    db.insert(conn, "jobs", {**base, "job_id": "v7", "state": "queued"})
    db.insert(conn, "jobs", {**base, "job_id": "v8", "state": "queued"})
    conn.execute("UPDATE jobs SET state='running' WHERE job_id='v1'"); conn.commit()
    assert q.backpressure_holds("search")
    db.insert(conn, "runs", {"run_id": "r_old", "exp": "phase5", "arm": "M", "design_id": "d", "seed": 1, "llm_model": "m", "status": "failed", "llm_calls": 12})
    db.insert(conn, "runs", {"run_id": "r_new", "exp": "phase5", "arm": "M", "design_id": "d", "seed": 2, "llm_model": "m", "status": "created", "llm_calls": 0})
    old_job = q.submit("shell", {"cmd": "sleep 0.3", "run_id": "r_old"}, pool="search", priority=1)
    new_job = q.submit("shell", {"cmd": "sleep 0.3", "run_id": "r_new"}, pool="search", priority=9)
    conn.execute("UPDATE jobs SET kind='search' WHERE job_id IN (?, ?)", (old_job, new_job)); conn.commit()
    monkey_spawned = []
    q._spawn = lambda job: monkey_spawned.append(job["job_id"]) or conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (job["job_id"],))
    q._dispatch()
    assert monkey_spawned == [old_job] and q.get(new_job)["state"] == "queued"
    cfg["queue"].pop("backpressure")
    assert not Queue(cfg, conn, str(tmp_path / "logs2"), env={}, log=lambda m: None).backpressure_holds("search")


def test_per_design_fairness_scans_past_a_large_backlog(tmp_path):
    """2026-09-16: with a per-design cap the dispatcher must look past one design's backlog (480 queued proofs of one design sat in
    front of every other design's job and 28 seats idled) — a job of another design starts although hundreds of the capped
    design's jobs precede it in the queue (both directions: the capped design still gets no second seat)."""
    cfg = make_cfg()
    cfg["queue"]["local_max"] = 4
    cfg["queue"]["per_design_max"] = {"local": 1}
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    base = {"kind": "shell", "priority": 5, "payload_json": json.dumps({"cmd": "sleep 0.5"}), "attempts": 0, "pool": "local"}
    db.insert(conn, "jobs", {**base, "job_id": "a_run", "design_id": "A", "state": "running", "submitted_at": "2026-09-16T00:00:00"})   # A holds its one seat
    for i in range(300):
        db.insert(conn, "jobs", {**base, "job_id": f"a{i:04d}", "design_id": "A", "state": "queued", "submitted_at": f"2026-09-16T00:{i // 60:02d}:{i % 60:02d}"})
    b1 = q.submit("shell", {"cmd": "sleep 0.5"}, design_id="B", priority=0)                                                          # behind 300 A jobs, lower priority
    q._dispatch()
    assert q.get(b1)["state"] == "running"
    assert conn.execute("SELECT COUNT(*) FROM jobs WHERE design_id='A' AND state='running'").fetchone()[0] == 1
    assert wait_state(q, b1, {"done"}, timeout=15) == "done"


def test_file_size_limit_kills_a_runaway_writer(tmp_path):
    """2026-09-16: config queue.max_file_gb caps the largest file a job of that kind may write (ulimit -f): a job writing past the
    limit fails and the file stays at the limit; a kind without a limit writes freely (both directions)."""
    cfg = make_cfg()
    cfg["queue"]["max_file_gb"] = {"shell": 0.001}                                   # 1 MB
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    big = tmp_path / "big.bin"
    j = q.submit("shell", {"cmd": f"head -c 5000000 /dev/zero > {big}"})
    q.tick()
    assert wait_state(q, j, {"done", "failed"}, timeout=20) == "failed" and big.stat().st_size <= 1048576 + 65536   # ulimit rounds to the write block
    cfg["queue"].pop("max_file_gb")
    q2 = Queue(cfg, conn, str(tmp_path / "logs2"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    free = tmp_path / "free.bin"
    j2 = q2.submit("shell", {"cmd": f"head -c 3000000 /dev/zero > {free}"})
    q2.tick()
    assert wait_state(q2, j2, {"done", "failed"}, timeout=20) == "done" and free.stat().st_size == 3000000


def test_dispatch_alternates_designs_within_a_priority_level(tmp_path):
    """2026-09-16: with a per-design cap the free seats are shared round-robin across designs (within a priority level), so a
    design with newer jobs is not starved behind another design's older backlog; a higher priority still goes first."""
    from src.jobqueue.core import round_robin_by_design
    mk = lambda jid, d, pri, t: {"job_id": jid, "design_id": d, "priority": pri, "submitted_at": t}
    rows = [mk("a1", "A", 4, "01"), mk("a2", "A", 4, "02"), mk("a3", "A", 4, "03"), mk("b1", "B", 4, "04"), mk("b2", "B", 4, "05"), mk("c1", "C", 4, "06"), mk("hi", "A", 9, "07")]
    rows.sort(key=lambda r: (-r["priority"], r["submitted_at"]))
    assert [r["job_id"] for r in round_robin_by_design(rows)] == ["hi", "a1", "b1", "c1", "a2", "b2", "a3"]
    assert [r["job_id"] for r in round_robin_by_design(rows, {"A": 5, "B": 2, "C": 0})] == ["hi", "c1", "b1", "a1", "b2", "a2", "a3"]   # the design with the fewest seats goes first
    cfg = make_cfg()
    cfg["queue"]["local_max"] = 4
    cfg["queue"]["per_design_max"] = {"local": 3}
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    base = {"kind": "shell", "priority": 4, "payload_json": json.dumps({"cmd": "sleep 0.5"}), "attempts": 0, "pool": "local", "state": "queued"}
    for i in range(6):
        db.insert(conn, "jobs", {**base, "job_id": f"a{i}", "design_id": "A", "submitted_at": f"2026-09-16T00:00:{i:02d}"})
    for i in range(3):
        db.insert(conn, "jobs", {**base, "job_id": f"b{i}", "design_id": "B", "submitted_at": f"2026-09-16T00:01:{i:02d}"})
    spawned = []
    q._spawn = lambda job: spawned.append(job["job_id"]) or conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (job["job_id"],))
    q._dispatch()
    assert sorted(spawned) == ["a0", "a1", "b0", "b1"]                                   # 4 seats: two per design, not three of A and one of B


def test_fresh_search_runs_are_admitted_at_a_limited_rate(tmp_path):
    """2026-09-16: `queue.search_admit_per_min` caps the fresh search runs started per minute (a resumption is exempt); without the key
    there is no limit (both directions)."""
    cfg = make_cfg()
    cfg["queue"]["search_max"] = 8
    cfg["queue"]["search_admit_per_min"] = 2
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={}, log=lambda m: None)
    for i in range(5):
        db.insert(conn, "runs", {"run_id": f"r{i}", "exp": "phase5", "arm": "M", "design_id": "d", "seed": i, "llm_model": "m", "status": "created", "llm_calls": 0})
    db.insert(conn, "runs", {"run_id": "r_res", "exp": "phase5", "arm": "M", "design_id": "d", "seed": 9, "llm_model": "m", "status": "failed", "llm_calls": 30})
    jobs = [q.submit("shell", {"cmd": "sleep 0.2", "run_id": f"r{i}"}, pool="search", priority=1) for i in range(5)]
    res = q.submit("shell", {"cmd": "sleep 0.2", "run_id": "r_res"}, pool="search", priority=0)
    conn.execute("UPDATE jobs SET kind='search' WHERE pool='search'"); conn.commit()
    spawned = []
    q._spawn = lambda job: spawned.append(job["job_id"]) or conn.execute("UPDATE jobs SET state='running', started_at=? WHERE job_id=?", (db.now(), job["job_id"]))
    q._dispatch()
    assert len([j for j in spawned if j in jobs]) == 2 and res in spawned                # two fresh runs this minute, the resumption on top
    q._dispatch()
    assert len([j for j in spawned if j in jobs]) == 2                                   # nothing more within the minute
    cfg["queue"].pop("search_admit_per_min")
    q2 = Queue(cfg, conn, str(tmp_path / "logs2"), env={}, log=lambda m: None)
    q2._spawn = q._spawn
    q2._dispatch()
    assert len([j for j in spawned if j in jobs]) == 5                                   # no limit: the rest start


def test_per_kind_ceiling_inside_a_pool(tmp_path):
    """2026-09-16: `queue.per_kind_max` caps one kind inside a pool (hidden-layer DC jobs) while other kinds of the pool fill the
    remaining seats; without the key every kind competes freely (both directions)."""
    cfg = make_cfg()
    cfg["queue"]["local_max"] = 4
    cfg["queue"]["per_kind_max"] = {"shell": 1}
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={}, log=lambda m: None)
    shells = [q.submit("shell", {"cmd": "sleep 0.2"}, priority=5) for _ in range(3)]
    others = [q.submit("shell", {"cmd": "sleep 0.2"}, priority=0) for _ in range(2)]
    conn.execute("UPDATE jobs SET kind='yosys' WHERE job_id IN (?, ?)", tuple(others)); conn.commit()
    spawned = []
    q._spawn = lambda job: spawned.append(job["job_id"]) or conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (job["job_id"],))
    q._dispatch()
    assert len([j for j in spawned if j in shells]) == 1 and len([j for j in spawned if j in others]) == 2   # one shell (its ceiling), both yosys jobs
    cfg["queue"].pop("per_kind_max")
    q2 = Queue(cfg, conn, str(tmp_path / "logs2"), env={}, log=lambda m: None)
    q2._spawn = q._spawn
    q2._dispatch()
    assert len([j for j in spawned if j in shells]) == 2                                                     # no ceiling: the fourth seat goes to a shell job


def test_reprioritize_changes_a_waiting_job_only(q):
    """DECISIONS 2026-09-16 (scheduling change, item 2): a queued proof takes the tier of its provisional diagnosis; a job that
    already runs (or finished) keeps its priority."""
    a = q.submit("shell", {"cmd": "true"}, priority=4)
    assert q.reprioritize(a, 8) and q.get(a)["priority"] == 8
    q.conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (a,)); q.conn.commit()
    assert not q.reprioritize(a, 1) and q.get(a)["priority"] == 8


def test_code_roll_exit_requeues_a_search_run_without_an_attempt(tmp_path):
    """2026-09-16: a search run leaving for a code roll (exit 76 from the driver, or 128 + SIGUSR1 from a driver that predates
    the handler) is requeued as it is — no attempt consumed, no backoff; any other kind, or any other exit code, follows the
    retry rule (both directions)."""
    from src.jobqueue.core import EX_RESTART, ROLL_SIGNAL_RC
    cfg = make_cfg()
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    s = q.submit("shell", {"cmd": "true", "run_id": "r1"}, pool="search")
    conn.execute("UPDATE jobs SET kind='search', state='running', attempts=1 WHERE job_id=?", (s,)); conn.commit()
    q._finish(q.get(s), EX_RESTART)
    assert q.get(s)["state"] == "queued" and q.get(s)["attempts"] == 1 and q.get(s)["error"] == "restarted for a code roll"
    conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (s,)); conn.commit()
    q._finish(q.get(s), ROLL_SIGNAL_RC)
    assert q.get(s)["state"] == "queued" and q.get(s)["attempts"] == 1 and q._backoff("search")[1] == 0
    conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (s,)); conn.commit()
    q._finish(q.get(s), 1)                                                        # an ordinary failure of a job on its last attempt
    assert q.get(s)["state"] == "failed" and q.get(s)["attempts"] == 2
    o = q.submit("shell", {"cmd": "true"})
    conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (o,)); conn.commit()
    q._finish(q.get(o), EX_RESTART)                                               # not a search job: exit 76 is a failure like any other
    assert q.get(o)["state"] == "queued" and q.get(o)["attempts"] == 1


def test_a_resumption_behind_held_fresh_runs_is_still_dispatched(tmp_path):
    """2026-09-16: while backpressure holds fresh search runs, the dispatcher scans the whole queue — a resumption submitted after
    hundreds of fresh runs is started (it sat unreached behind the window of `free` rows for hours)."""
    cfg = make_cfg()
    cfg["queue"]["search_max"] = 4
    cfg["queue"]["backpressure"] = {"search": {"pool": "vcf", "max_waiting": 0}}
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    base = {"kind": "vcf", "priority": 0, "payload_json": "{}", "attempts": 0, "pool": "vcf", "design_id": "d"}
    for i in range(cfg["queue"]["vcf_seats_max"]):
        db.insert(conn, "jobs", {**base, "job_id": f"v{i}", "state": "running", "submitted_at": "2026-09-16T00:00:00"})
    db.insert(conn, "jobs", {**base, "job_id": "vq", "state": "queued", "submitted_at": "2026-09-16T00:00:01", "design_id": "e"})   # another design: dispatchable, so it counts (DECISION (d) B1)
    assert q.backpressure_holds("search")
    db.insert(conn, "runs", {"run_id": "r_old", "exp": "phase5", "arm": "M", "design_id": "d", "seed": 1, "llm_model": "m", "status": "failed", "llm_calls": 12})
    fresh = []
    for i in range(20):
        db.insert(conn, "runs", {"run_id": f"r_new{i}", "exp": "phase5", "arm": "M", "design_id": "d", "seed": 10 + i, "llm_model": "m", "status": "created", "llm_calls": 0})
        fresh.append(q.submit("shell", {"cmd": "true", "run_id": f"r_new{i}"}, pool="search", priority=5))
    old_job = q.submit("shell", {"cmd": "true", "run_id": "r_old"}, pool="search", priority=5)          # the last row of the queue
    conn.execute("UPDATE jobs SET kind='search' WHERE pool='search'"); conn.commit()
    spawned = []
    q._spawn = lambda job: spawned.append(job["job_id"]) or conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (job["job_id"],))
    q._dispatch()
    assert spawned == [old_job] and all(q.get(j)["state"] == "queued" for j in fresh)


def test_recovery_adopts_a_live_process_despite_a_stale_done_marker(tmp_path):
    """2026-09-18: a code roll requeues a search run under the same attempt number, so the earlier exit's `.done` marker stays on
    disk; a daemon restart must adopt the live process instead of reading that marker and spawning a second driver (both
    directions: a dead process with a fresh marker is finished from the marker; a dead process with only a stale marker counts
    as vanished; a new spawn removes the old marker first)."""
    import subprocess as sp
    cfg = make_cfg()
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    s = q.submit("shell", {"cmd": "sleep 5", "run_id": "r1"}, pool="search")
    conn.execute("UPDATE jobs SET kind='search' WHERE job_id=?", (s,)); conn.commit()
    q._dispatch()
    job = q.get(s)
    assert job["state"] == "running" and job["host_pid"]
    done = job["done_path"]
    with open(done, "w") as f:
        f.write("76")                                                    # the marker of an earlier exit of this attempt
    os.utime(done, (time.time() - 3600, time.time() - 3600))
    q2 = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)   # "a new daemon"
    q2._recover()
    assert q2.get(s)["state"] == "running" and q2.get(s)["host_pid"] == job["host_pid"]   # adopted, not re-spawned
    assert conn.execute("SELECT COUNT(*) FROM jobs WHERE job_id=? AND state='queued'", (s,)).fetchone()[0] == 0
    q._kill(job["host_pid"]); q._reap()                                  # the process ends; its wrapper writes a fresh marker
    time.sleep(0.5)
    conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (s,)); conn.commit()
    with open(done, "w") as f:
        f.write("0")
    q3 = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    q3._recover()
    assert q3.get(s)["state"] == "done"                                  # dead process + fresh marker: finished from the marker
    conn.execute("UPDATE jobs SET state='running', host_pid=999999999 WHERE job_id=?", (s,)); conn.commit()
    os.utime(done, (time.time() - 7200, time.time() - 7200))
    conn.execute("UPDATE jobs SET started_at=? WHERE job_id=?", (db.now(), s)); conn.commit()
    q3._recover()
    assert q3.get(s)["state"] in ("queued", "failed") and "vanished" in (q3.get(s)["error"] or "")   # dead process + stale marker: vanished
    # a new spawn removes the stale marker of the same attempt before starting
    with open(done, "w") as f:
        f.write("76")
    conn.execute("UPDATE jobs SET state='queued', attempts=0 WHERE job_id=?", (s,)); conn.commit()
    q3._spawn(q3.get(s))
    assert not os.path.exists(done) or open(done).read().strip() != "76"
    q3._kill(q3.get(s)["host_pid"])


def test_search_hold_flag_and_round_robin_across_rows(tmp_path):
    """DECISION 2026-09-18 items 2 and 5b: a queued search job whose payload carries `hold` is never dispatched until the flag is
    removed; with queue.round_robin_rows the queued runs of a tier are dispatched alternating across arm-model rows, the row with
    the fewest running runs first, tiers in order large, medium, small (both directions: without the option the queue order stays)."""
    from src.jobqueue.core import round_robin_by_row, held_job
    cfg = make_cfg()
    cfg["queue"]["search_max"] = 4
    cfg["queue"]["round_robin_rows"] = True
    cfg["exp5"] = dict(cfg.get("exp5") or {}, starting_points={"large": ["L"], "medium": ["M1", "M2"], "small": ["S"]})
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    jobs = []
    for i, (arm, model, design) in enumerate([("B0", "luna", "M1"), ("B0", "luna", "M2"), ("B2", "terra", "M1"), ("M", "luna", "M1"), ("B0", "luna", "S"), ("M", "terra", "M2")]):
        rid = f"r{i}"
        db.insert(conn, "runs", {"run_id": rid, "exp": "phase5", "arm": arm, "design_id": design, "seed": 1, "llm_model": model, "status": "created", "llm_calls": 0})
        payload = {"cmd": "true", "run_id": rid}
        if arm == "M":
            payload["hold"] = "C2"
        jobs.append(q.submit("shell", payload, design_id=design, pool="search", priority=3))
    conn.execute("UPDATE jobs SET kind='search' WHERE pool='search'"); conn.commit()
    for i, j in enumerate(jobs):   # a deterministic queue order (same-second submissions would otherwise tie-break on the random job id)
        conn.execute("UPDATE jobs SET submitted_at=? WHERE job_id=?", (f"2026-09-18T00:01:{i:02d}", j))
    conn.execute("UPDATE jobs SET submitted_at=? WHERE job_id=?", ("2026-09-18T00:00:00", jobs[4])); conn.commit()   # the small-tier job was submitted first
    rows = conn.execute("SELECT * FROM jobs WHERE pool='search' AND state='queued' ORDER BY priority DESC, submitted_at ASC, job_id ASC").fetchall()
    assert [held_job(r) for r in rows].count(True) == 2
    ordered = round_robin_by_row([r for r in rows if not held_job(r)], q.run_rows(), q.tier_of_design())
    assert [r["job_id"] for r in ordered] == [jobs[0], jobs[2], jobs[1], jobs[4]]   # medium: B0-luna, B2-terra, B0-luna again; then the small tier
    spawned = []
    q._spawn = lambda job: spawned.append(job["job_id"]) or conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (job["job_id"],))
    q._dispatch()
    assert spawned[:3] == [jobs[0], jobs[2], jobs[1]] and not {jobs[3], jobs[5]} & set(spawned)          # cap 4: three admissions per minute here (admit rate) ...
    conn.execute("UPDATE jobs SET payload_json=? WHERE job_id=?", (json.dumps({"cmd": "true", "run_id": "r3"}), jobs[3])); conn.commit()  # released
    assert not held_job(q.get(jobs[3]))
    cfg["queue"]["round_robin_rows"] = False
    q2 = Queue(cfg, conn, str(tmp_path / "logs2"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    rows2 = conn.execute("SELECT * FROM jobs WHERE pool='search' AND state='queued' ORDER BY priority DESC, submitted_at ASC, job_id ASC").fetchall()
    assert [r["job_id"] for r in rows2][0] == jobs[4]                                                     # without the option the plain queue order (submission time) stays


def test_per_kind_ceiling_applies_in_every_pool(tmp_path):
    """DECISION 2026-09-18 item 3a: `per_kind_max.dc_hidden: 0` holds hidden jobs in the pt pool as well as in the dc pool."""
    cfg = make_cfg()
    cfg["queue"]["per_kind_max"] = {"dc_hidden": 0}
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    h_pt = q.submit("shell", {"cmd": "true"}, pool="pt")
    h_dc = q.submit("shell", {"cmd": "true"}, pool="dc")
    other = q.submit("shell", {"cmd": "true"}, pool="pt")
    conn.execute("UPDATE jobs SET kind='dc_hidden' WHERE job_id IN (?, ?)", (h_pt, h_dc)); conn.commit()
    spawned = []
    q._spawn = lambda job: spawned.append(job["job_id"]) or conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (job["job_id"],))
    q._dispatch()
    assert spawned == [other]


def test_round_robin_rows_least_loaded_first_catches_up():
    """DECISION 2026-09-18 (b) item 6 ("the M rows are the priority once released") under item 5b's round-robin: a row with
    fewer runs running receives every admission until it has caught up with the others, then the rows alternate; tiers keep
    their order. Both directions: equal rows alternate from the first admission."""
    from src.jobqueue.core import round_robin_by_row
    def job(i, rid, pri=8600):
        return {"job_id": f"j{i}", "priority": pri, "payload_json": json.dumps({"run_id": rid})}
    rows_meta = {"r_b0_1": ("B0", "luna", "M1"), "r_b0_2": ("B0", "luna", "M2"), "r_b0_3": ("B0", "luna", "M1"),
                 "r_m_1": ("M", "luna", "M1"), "r_m_2": ("M", "luna", "M2"), "r_m_3": ("M", "luna", "M1"), "r_s": ("B0", "luna", "S")}
    rows = [job(0, "r_b0_1"), job(1, "r_b0_2"), job(2, "r_b0_3"), job(3, "r_m_1"), job(4, "r_m_2"), job(5, "r_m_3"), job(6, "r_s")]
    tier_of = {"M1": "medium", "M2": "medium", "S": "small"}
    run_rows = {"rows": rows_meta, "running": {("B0", "luna"): 2, ("M", "luna"): 0}}
    out = [r["job_id"] for r in round_robin_by_row(rows, run_rows, tier_of)]
    assert out == ["j3", "j4", "j0", "j5", "j1", "j2", "j6"]        # M catches up (0 -> 2), then B0 / M alternate, the small tier last
    run_rows = {"rows": rows_meta, "running": {("B0", "luna"): 1, ("M", "luna"): 1}}
    out = [r["job_id"] for r in round_robin_by_row(rows, run_rows, tier_of)]
    assert out == ["j0", "j3", "j1", "j4", "j2", "j5", "j6"]        # equal rows alternate from the start (queue order breaks the tie)


def test_window_dispatch_fixed_order_window_lane_and_catch_up():
    """DECISION 2026-09-18 (d) B2 / B3: rows take their next run from the earliest design of the fixed order inside the sliding window
    of the next 5 designs with runs left (a row with no seed in the window takes its earliest design beyond it); the long-pole lane
    is dispatched outside the window, alternating with window runs per row, while its search runs stay below the lane cap; rows
    alternate least-loaded first; tiers keep their order. Both directions: without a lane every pick is a window pick."""
    from src.jobqueue.core import window_dispatch
    def job(i, rid, pri=8600):
        return {"job_id": f"j{i}", "priority": pri, "payload_json": json.dumps({"run_id": rid})}
    order = {"medium": ["d1", "d2", "d3", "d4", "d5", "d6", "d7"]}
    tier_of = {d: "medium" for d in order["medium"]}; tier_of["spi"] = "medium"; tier_of["s1"] = "small"
    meta = {}
    rows = []
    i = 0
    for arm in ("B0", "M"):
        for d in ("d7", "d6", "d5", "d4", "d3", "d2", "d1"):            # queue order is the reverse of the design order: the order must come from the config, not the queue
            meta[f"r_{arm}_{d}"] = (arm, "luna", d); rows.append(job(i, f"r_{arm}_{d}")); i += 1
        meta[f"r_{arm}_spi"] = (arm, "luna", "spi"); rows.append(job(i, f"r_{arm}_spi")); i += 1
    meta["r_B0_s1"] = ("B0", "luna", "s1"); rows.append(job(i, "r_B0_s1"))
    run_rows = {"rows": meta, "running": {("B0", "luna"): 1, ("M", "luna"): 0}}
    out = window_dispatch(rows, run_rows, tier_of, order, 5, lane_designs=("spi",), lane_search_max=1, running_by_design={})
    picks = [(meta[json.loads(j["payload_json"])["run_id"]][0], meta[json.loads(j["payload_json"])["run_id"]][2]) for j in out]
    assert picks[0] == ("M", "spi")                                     # M is behind (0 vs 1 running): first, and its lane run comes first
    assert picks[1] == ("B0", "d1") and picks[2] == ("M", "d1")         # rows level at 1: queue order breaks the tie (B0), the earliest window design; the lane is at its cap of 1
    assert picks[3] == ("B0", "d2") and picks[4] == ("M", "d2")         # rows alternate, designs in the fixed order
    assert picks[-1] == ("B0", "s1") and ("B0", "spi") not in picks     # the small tier last; B0's lane run is held back by the lane cap (left out of this tick's order)
    # without a lane: every design goes through the window in order, rows alternating
    out2 = window_dispatch(rows, run_rows, tier_of, order, 5, lane_designs=(), lane_search_max=0)
    picks2 = [meta[json.loads(j["payload_json"])["run_id"]][2] for j in out2]
    assert picks2[:4] == ["d1", "d1", "d2", "d2"] and picks2.index("spi") > picks2.index("d7")   # spi is not in the order: after the listed designs
    # a row with no seed inside the window takes its earliest design beyond it: B0 has only d6 / d7 left while M still has d1..d5
    rows3 = [job(0, "r_B0_d7"), job(1, "r_B0_d6"), job(2, "r_M_d1"), job(3, "r_M_d2"), job(4, "r_M_d3"), job(5, "r_M_d4"), job(6, "r_M_d5"), job(7, "r_M_d6")]
    out3 = window_dispatch(rows3, {"rows": meta, "running": {}}, tier_of, order, 5)
    picks3 = [meta[json.loads(j["payload_json"])["run_id"]][:3:2] for j in out3]
    assert picks3[0] == ("B0", "d6") and picks3[1] == ("M", "d1")       # B0's earliest beyond the window (d6), not idle; M inside the window


def test_backpressure_counts_only_dispatchable_proofs_and_lane_shares(tmp_path):
    """DECISION 2026-09-18 (d) B1 / B3: proofs blocked by a per-design cap or waiting behind a lane's share do not count towards the
    backpressure; a lane's jobs start up to the lane's share regardless of the global per-design cap; the other designs stay within
    cap minus the seats the busy lanes can use (an idle lane releases its share). Both directions."""
    cfg = make_cfg()
    cfg["queue"]["vcf_seats_max"] = 10; cfg["queue"]["vcf_seats_target"] = 10
    cfg["queue"]["per_design_max"] = {"vcf": 2}
    cfg["queue"]["lanes"] = {"vcf": {"spi": {"designs": ["SPI"], "share": 4}}}
    cfg["queue"]["backpressure"] = {"search": {"pool": "vcf", "max_waiting": 3}}
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    def running(design, n):
        for k in range(n):
            db.insert(conn, "jobs", {"job_id": f"run_{design}_{k}", "kind": "vcf", "pool": "vcf", "design_id": design, "state": "running", "priority": 0, "payload_json": "{}", "submitted_at": "t", "started_at": "t"})
    seq = {"n": 0}
    def queued(design, n):
        for k in range(n):
            seq["n"] += 1
            db.insert(conn, "jobs", {"job_id": f"q_{design}_{seq['n']}", "kind": "vcf", "pool": "vcf", "design_id": design, "state": "queued", "priority": 0, "payload_json": "{}", "submitted_at": "t"})
    running("A", 2); queued("A", 6)                     # A at its cap of 2: its 6 waiting proofs are blocked, not dispatchable
    running("SPI", 4); queued("SPI", 10)                # SPI at its lane share of 4: blocked as well
    running("B", 1); queued("B", 1)                     # B below its cap: 1 dispatchable
    running("C", 1); running("D", 1); running("E", 1)   # 10 seats busy
    assert q.running_in_pool("vcf") == 10 and q.dispatchable_waiting("vcf") == 1 and not q.backpressure_holds("search")
    queued("B", 3)                                      # B: 4 waiting, room for 1 -> still 1 dispatchable
    assert q.dispatchable_waiting("vcf") == 1
    conn.execute("UPDATE jobs SET state='done' WHERE job_id='run_B_0'"); conn.commit()
    assert q.dispatchable_waiting("vcf") == 2           # B now has room for 2 (of its 4 waiting)
    running("F", 1)
    queued("G", 5)                                      # G: nothing running, cap 2 -> 2 dispatchable => 4 > 3: holds
    assert q.backpressure_holds("search")
    # lane admission: the others' limit is cap - min(share, running + queued) of the busy lane
    rows = conn.execute("SELECT * FROM jobs WHERE state='queued' AND pool='vcf'").fetchall()
    st = q.lane_state("vcf", cfg["queue"]["lanes"]["vcf"], rows)
    assert st["running"]["spi"] == 4 and st["queued"]["spi"] == 10 and st["others_running"] == 6
    assert not q.lane_admits(st, cfg["queue"]["lanes"]["vcf"], "SPI", 10)          # the lane is at its share
    assert not q.lane_admits(st, cfg["queue"]["lanes"]["vcf"], "G", 10)            # others: 6 running, limit 10 - 4 = 6 -> full
    conn.execute("UPDATE jobs SET state='done' WHERE job_id IN ('run_SPI_0','run_SPI_1')"); conn.commit()
    rows = conn.execute("SELECT * FROM jobs WHERE state='queued' AND pool='vcf'").fetchall()
    st = q.lane_state("vcf", cfg["queue"]["lanes"]["vcf"], rows)
    assert q.lane_admits(st, cfg["queue"]["lanes"]["vcf"], "SPI", 10) and not q.lane_admits(st, cfg["queue"]["lanes"]["vcf"], "G", 10)   # SPI may refill its share; others still capped at 6
    conn.execute("UPDATE jobs SET state='done' WHERE design_id='SPI'"); conn.commit()   # the lane goes idle: its share is released
    rows = conn.execute("SELECT * FROM jobs WHERE state='queued' AND pool='vcf'").fetchall()
    st = q.lane_state("vcf", cfg["queue"]["lanes"]["vcf"], rows)
    assert st["running"]["spi"] == 0 and st["queued"]["spi"] == 0 and q.lane_admits(st, cfg["queue"]["lanes"]["vcf"], "G", 10)


def test_window_design_cap_grows_when_few_designs_remain_and_lane_search_cap_is_per_design():
    """DECISION 2026-09-18 (e) item 3: inside the window the per-design VC Formal cap is max(16, floor(others' share / active window
    designs)); the long-pole lane's search cap applies per lane design. Both directions."""
    from src.jobqueue.core import Queue, window_dispatch
    lanes = {"spi": {"designs": ["SPI"], "share": 20}, "uart": {"designs": ["UART"], "share": 10}}
    st = {"running": {"spi": 20, "uart": 10}, "queued": {"spi": 5, "uart": 5}, "others_running": 10, "active_window": 2}
    assert Queue.window_design_cap(st, lanes, 50, 16) == 16                      # others' share 20 over 2 designs = 10 < 16 -> the floor 16 holds
    st["active_window"] = 1
    assert Queue.window_design_cap(st, lanes, 50, 16) == 20                      # one design left: it may take the whole share
    st["queued"]["uart"] = 0; st["running"]["uart"] = 0                            # an idle lane releases its share: 50 - 20 = 30 for the single window design
    assert Queue.window_design_cap(st, lanes, 50, 16) == 30
    def job(i, rid):
        return {"job_id": f"j{i}", "priority": 8600, "payload_json": json.dumps({"run_id": rid})}
    meta = {"r_spi": ("B0", "luna", "SPI"), "r_uart": ("B0", "luna", "UART"), "r_d1": ("B0", "luna", "d1")}
    rows = [job(0, "r_spi"), job(1, "r_uart"), job(2, "r_d1")]
    tier_of = {"SPI": "medium", "UART": "medium", "d1": "medium"}
    out = window_dispatch(rows, {"rows": meta, "running": {}}, tier_of, {"medium": ["d1"]}, 5, lane_designs=("SPI", "UART"), lane_search_max=1, running_by_design={"SPI": 1})
    picks = [meta[json.loads(j["payload_json"])["run_id"]][2] for j in out]
    assert picks == ["UART", "d1"]                                                 # SPI at its own cap (1 running) is held back; UART's lane run still goes; the window run alternates


def test_rebalance_shares_are_proportional_and_release_idle_lanes():
    """DECISION 2026-09-18 (d) B3 / (e) 3: lane shares proportional to the remaining seat-hours, the rest to the window designs, total
    at the cap; a lane without work gets 0; the window designs keep at least the minimum. Both directions."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("rebalance_lanes", str(Path(C.ROOT) / "scripts" / "rebalance_lanes.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    cfg = {"queue": {"lanes": {"vcf": {"spi": {"designs": ["SPI"], "share": 24}, "uart": {"designs": ["UART"], "share": 8}, "idle": {"designs": ["ROUTER"], "share": 8}}}}}
    hours = {"SPI": {"hours": 700.0}, "UART": {"hours": 300.0}, "A": {"hours": 500.0}, "B": {"hours": 500.0}}
    new, rest, lane_hours, others = mod.shares(cfg, hours, 50, min_seats=4)
    assert new == {"spi": 17, "uart": 8, "idle": 0} and rest == 25 and others == 1000.0                      # the integer split with the smallest spread of finish times (41.2 / 37.5 / 40.0 h); the idle lane releases its seats
    new2, rest2, _, _ = mod.shares(cfg, {"SPI": {"hours": 990.0}, "A": {"hours": 10.0}}, 50, min_seats=1)
    assert new2["spi"] == 49 and rest2 == 1                                                                 # the window designs keep the minimum seat
    new3, rest3, _, _ = mod.shares(cfg, {}, 50, min_seats=1)
    assert new3 == {"spi": 0, "uart": 0, "idle": 0} and rest3 == 50                                          # nothing left: every seat to the rest


def test_leftover_lane_takes_only_unfillable_seats(tmp_path):
    """DECISION 2026-09-18 (g) item 1: the small tier's leftover lane starts a proof only with seats the medium lanes and window designs
    cannot fill this tick (their dispatchable queue is shorter than the free seats); it never draws on a reserved share; the
    re-balance equalises the medium lanes only. Both directions."""
    from src.jobqueue.core import Queue
    cfg = make_cfg()
    cfg["queue"]["vcf_seats_max"] = 10; cfg["queue"]["vcf_seats_target"] = 10
    cfg["queue"]["per_design_max"] = {"vcf": 2}
    lanes = {"spi": {"designs": ["SPI"], "share": 4}, "small": {"designs": ["S1", "S2"], "share": 0, "leftover": True}}
    cfg["queue"]["lanes"] = {"vcf": lanes}
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    k = {"n": 0}
    def add(design, state, n):
        for _ in range(n):
            k["n"] += 1
            db.insert(conn, "jobs", {"job_id": f"j{k['n']}", "kind": "vcf", "pool": "vcf", "design_id": design, "state": state, "priority": 0, "payload_json": "{}", "submitted_at": "t", "started_at": "t" if state == "running" else None})
    add("SPI", "running", 2); add("SPI", "queued", 5)          # the lane can still fill 2 (share 4)
    add("A", "running", 1); add("A", "queued", 3)              # a window design: can fill 1 more (cap 2)
    add("S1", "queued", 4)                                     # the small tier waits
    rows = conn.execute("SELECT * FROM jobs WHERE state='queued' AND pool='vcf'").fetchall()
    st = q.lane_state("vcf", lanes, rows)
    assert st["free_after_medium"] == 10 - 3 - (2 + 1) == 4                                    # 7 free seats, the medium side can fill 3 -> 4 left for the small tier
    assert q.lane_admits(st, lanes, "S1", 10) and q.lane_admits(st, lanes, "SPI", 10) and q.lane_admits(st, lanes, "A", 10)
    for _ in range(4):
        q.lane_count(st, lanes, "S1")
    assert not q.lane_admits(st, lanes, "S1", 10)                                              # the leftover is used up
    add("B", "queued", 6); add("C", "queued", 6)                                               # the medium window now fills every free seat
    rows = conn.execute("SELECT * FROM jobs WHERE state='queued' AND pool='vcf'").fetchall()
    st = q.lane_state("vcf", lanes, rows)
    assert st["free_after_medium"] == 0 and not q.lane_admits(st, lanes, "S2", 10)
    # the re-balance leaves the leftover lane at 0 and equalises the medium lanes only
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("rebalance_lanes", str(Path(C.ROOT) / "scripts" / "rebalance_lanes.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    hours = {"SPI": {"hours": 600.0, "runs_left": 10}, "A": {"hours": 400.0, "runs_left": 10}, "S1": {"hours": 900.0, "runs_left": 20}, "S2": {"hours": 900.0, "runs_left": 20}}
    new, rest, lane_hours, others = mod.shares(cfg, hours, 10)
    assert new["small"] == 0 and others == 400.0 and new["spi"] == 6 and rest == 4                # 600 : 400 -> 6 : 4; the small tier's 1 800 h are outside the split


def test_generating_only_slot_accounting_with_guardrails(tmp_path, monkeypatch):
    """DECISION 2026-09-19 (j) item 1: only generating runs hold a search slot (waiting runs do not), at most generating_max generate at
    once; admission pauses while the medium tier's unverified-at-build fraction exceeds the threshold, and a fresh run of a lane whose
    estimated proof wait exceeds the limit is skipped while a window run with a short wait is admitted; count_waiting_runs restores
    the old accounting. Both directions."""
    from src.jobqueue import core as Q
    cfg = make_cfg()
    cfg["queue"]["search_max"] = 48; cfg["queue"]["generating_max"] = 2; cfg["queue"]["count_waiting_runs"] = False
    cfg["queue"]["round_robin_rows"] = False; cfg["queue"].pop("dispatch_window", None); cfg["queue"]["search_admit_per_min"] = None
    cfg["queue"]["backpressure"] = {}
    cfg["queue"]["lanes"] = {"vcf": {"spi": {"designs": ["SPI"], "share": 4}}}
    cfg["queue"]["admission_guard"] = {"unverified_at_build_max": 0.35, "proof_wait_max_min": 60, "window_min": 60, "tier": "medium"}
    cfg["exp5"] = dict(cfg.get("exp5") or {}, starting_points={"large": [], "medium": ["SPI", "W1"], "small": []})
    conn = db.connect(path=str(tmp_path / "results.sqlite"))
    q = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None)
    # two running runs: one generating (10 of 60 calls), one waiting (60 of 60)
    for rid, calls in (("r_gen", 10), ("r_wait", 60)):
        db.insert(conn, "runs", {"run_id": rid, "exp": "phase5", "arm": "M", "design_id": "W1", "seed": 1, "llm_model": "m", "status": "running", "llm_calls": calls, "budget_llm_calls": 60})
        db.insert(conn, "jobs", {"job_id": f"j_{rid}", "kind": "search", "pool": "search", "design_id": "W1", "state": "running", "priority": 3, "payload_json": json.dumps({"run_id": rid}), "submitted_at": "t", "started_at": "t"})
    assert Q.search_slot_state(conn, cfg) == {"generating": 1, "waiting": 1, "queued": 0}
    # queued fresh runs: one on SPI (a lane with a long proof queue), one on the window design
    for rid, design in (("r_spi", "SPI"), ("r_w", "W1")):
        db.insert(conn, "runs", {"run_id": rid, "exp": "phase5", "arm": "B2", "design_id": design, "seed": 2, "llm_model": "m", "status": "created", "llm_calls": 0, "budget_llm_calls": 60})
    jobs = {design: q.submit("shell", {"cmd": "true", "run_id": rid}, design_id=design, pool="search", priority=3) for rid, design in (("r_spi", "SPI"), ("r_w", "W1"))}
    conn.execute("UPDATE jobs SET kind='search' WHERE pool='search' AND state='queued'"); conn.commit()
    for k in range(10):   # SPI's lane: 10 queued proofs of 50 minutes on 4 seats -> a new proof waits ≈ 125 min
        db.insert(conn, "jobs", {"job_id": f"p{k}", "kind": "vcf", "pool": "vcf", "design_id": "SPI", "state": "queued", "priority": 4, "payload_json": "{}", "submitted_at": "t"})
    db.insert(conn, "jobs", {"job_id": "pd", "kind": "vcf", "pool": "vcf", "design_id": "SPI", "state": "done", "priority": 4, "payload_json": "{}", "submitted_at": "t", "started_at": "2026-09-19T01:00:00", "finished_at": "2026-09-19T01:50:00"})
    conn.execute("UPDATE jobs SET finished_at=? WHERE job_id='pd'", ((__import__('datetime').datetime.now() - __import__('datetime').timedelta(minutes=10)).isoformat(timespec="seconds"),)); conn.commit()
    conn.execute("UPDATE jobs SET started_at=? WHERE job_id='pd'", ((__import__('datetime').datetime.now() - __import__('datetime').timedelta(minutes=60)).isoformat(timespec="seconds"),)); conn.commit()
    w = Q.proof_wait_estimate(conn, cfg)
    assert w["spi"]["queued"] == 10 and w["spi"]["seats"] == 4 and w["spi"]["wait_min"] > 60 and w["window"]["wait_min"] == 0.0
    spawned = []
    q._spawn = lambda job: (spawned.append(job["job_id"]) if job["pool"] == "search" else None) or conn.execute("UPDATE jobs SET state='running' WHERE job_id=?", (job["job_id"],))
    q._dispatch()
    assert spawned == [jobs["W1"]]                          # one free generating slot (2 - 1): the window run goes; the SPI run is held by its lane's wait
    # the fraction guard: a generation built in the last hour with every previous candidate unverified -> admission paused
    spawned.clear()
    conn.execute("UPDATE jobs SET state='queued' WHERE job_id=?", (jobs["W1"],)); conn.commit()
    db.insert(conn, "candidates", {"cand_id": "c1", "run_id": "r_gen", "design_id": "W1", "gen": 1, "arm": "M", "llm_model": "m"})
    db.insert(conn, "candidates", {"cand_id": "c2", "run_id": "r_gen", "design_id": "W1", "gen": 1, "arm": "M", "llm_model": "m"})
    db.insert(conn, "gen_summary", {"run_id": "r_gen", "gen": 2, "pending_json": json.dumps(["c1", "c2"]), "built_at": db.now()})
    assert abs(Q.unverified_at_build(conn, cfg) - 1.0) < 1e-9 and Q.unverified_at_build(conn, cfg, by_row=True) == {"m|M": 1.0}
    assert Q.unverified_at_build(conn, cfg, by="lane") == {"window": 1.0} and Q.unverified_at_build(conn, cfg, by="design") == {"W1": 1.0}
    q._dispatch()
    assert spawned == [] and q._lane_paused.get("window") is True   # the window lane is paused on its own fraction (DECISION (k) 1); SPI's lane on its wait
    conn.execute("UPDATE gen_summary SET pending_json='[]'"); conn.commit()
    q._dispatch()
    assert spawned == [jobs["W1"]] and q._lane_paused.get("window") is False   # the window lane resumed; SPI still held by its wait (per lane, no tier-wide pause)
    idle = Q.idle_seat_minutes(conn, cfg, hours=1.0)
    assert idle["spi"]["seats"] == 4 and idle["spi"]["occupied_min"] == 50.0 and idle["spi"]["idle_min"] == 190.0   # one 50-minute proof in the hour on 4 seats
    # DECISION 2026-09-19 (m) 7: a raised proof-wait threshold for SPI's lane lets its fresh run through while the default still holds a lane above 60 min
    spawned.clear(); conn.execute("UPDATE jobs SET state='queued' WHERE job_id IN (?, ?)", (jobs["W1"], jobs["SPI"])); conn.commit()
    assert Q.queued_runs_by_lane(conn, cfg) == {"spi": 1, "window": 1}
    cfg3 = copy.deepcopy(cfg); cfg3["queue"]["generating_max"] = 4
    cfg3["queue"]["admission_guard"]["proof_wait_max_min_by_lane"] = {"spi": 1000}
    q3 = Queue(cfg3, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None); q3._spawn = q._spawn
    q3._dispatch()
    assert set(spawned) == {jobs["W1"], jobs["SPI"]} and not q3._lane_paused.get("spi") and Q.queued_runs_by_lane(conn, cfg) == {}
    spawned.clear(); conn.execute("UPDATE jobs SET state='queued' WHERE job_id IN (?, ?)", (jobs["W1"], jobs["SPI"])); conn.commit()
    cfg3["queue"]["admission_guard"]["proof_wait_max_min_by_lane"] = {"spi": 70}     # below SPI's ≈ 75 min wait (4 of its 10 proofs started on the first dispatch): held again
    q4 = Queue(cfg3, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None); q4._spawn = q._spawn
    q4._dispatch()
    assert spawned == [jobs["W1"]] and q4._lane_paused.get("spi") is True, (spawned, jobs, Q.proof_wait_estimate(conn, cfg3), q4._lane_paused)
    # the revert switch: every running run holds a slot again -> with search_max 2 nothing is free
    spawned.clear(); conn.execute("UPDATE jobs SET state='queued' WHERE job_id=?", (jobs["W1"],)); conn.commit()
    cfg["queue"]["count_waiting_runs"] = True; cfg["queue"]["search_max"] = 2
    q2 = Queue(cfg, conn, str(tmp_path / "logs"), env={"PATH": os.environ["PATH"]}, log=lambda m: None); q2._spawn = q._spawn
    q2._dispatch()
    assert spawned == []
