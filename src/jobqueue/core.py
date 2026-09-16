"""Job-queue core for Beyond-Synth (CLAUDE.md rule 9: long jobs are decoupled from the session).

A job is a row in the `jobs` table of results/db/results.sqlite. The daemon (daemon.py) calls Queue.tick()
every few seconds; a tick reaps finished children, recovers jobs left behind by a previous daemon, and
dispatches waiting jobs into seat pools (dc / pt / vcf / local) whose caps come from config: queue.

Each job runs detached in its own session (`bash -c '<cmd>; rc=$?; echo $rc > <done>; exit $rc'`) with
stdout+stderr in results/queue/logs/<job_id>.a<attempt>.log and its exit code in the matching .done file,
so a restarted daemon can recover the outcome of jobs it did not spawn (results stay append-only: every
attempt gets fresh files, nothing is overwritten or deleted).

Exit-code protocol for job runners:
    0   done
    75  EX_TEMPFAIL: license seat unavailable -> the pool backs off (config: queue.backoff) and the job is
        requeued in state `backoff` without counting an attempt
    any other value, a timeout (124) or a vanished process -> failure; retried once (config: queue.retries),
        then `failed`
Job kinds map to a pool and a runner module (`python -m <module> --job <job_id>`); kind `shell` runs
payload["cmd"] directly and exists for smoke tests and one-off scripts.
"""
import datetime
import hashlib
import json
import os
import shlex
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.db import core as db  # noqa: E402

EX_TEMPFAIL = 75
TIMEOUT_RC = 124
POOL_OF_KIND = {"shell": "local", "sim": "local", "yosys": "local", "llm": "local", "orfs": "local", "search": "search",   # search runs in their own pool (2026-09-15): they wait for local yosys jobs and must not fill the local pool
                "dc": "dc", "pt": "pt", "vcf": "vcf", "dc_hidden": "dc"}
RUNNER_OF_KIND = {"dc": "src.eval.run_dc", "pt": "src.eval.run_pt", "yosys": "src.eval.run_yosys",
                  "orfs": "src.eval.run_orfs", "vcf": "src.equiv.run_equiv", "sim": "src.equiv.run_equiv",
                  "llm": "src.search.run_llm", "search": "src.search.run_search",   # Phase 3: one residual-guided evolution run per job
                  "dc_hidden": "scripts.hidden_worker"}  # hidden configurations: recorded only by the hidden worker (rule 3)
KILL_GRACE_SEC = 3.0


def _ts(iso):
    return datetime.datetime.fromisoformat(iso).timestamp()


def pool_hours(conn, now=None):
    """Seat-hours per pool from the jobs table: started_at -> finished_at of every finished job (its last attempt), started_at -> now
    for running ones. The budget ledger never carried tool hours (2026-09-15); the jobs table covers the hidden runs as well
    without reading their database (rule 3). Timestamps are local ISO strings (never compared as text)."""
    now = now or datetime.datetime.now()
    out = {}
    for r in conn.execute("SELECT pool, state, started_at, finished_at FROM jobs WHERE started_at IS NOT NULL"):
        try:
            t0 = datetime.datetime.fromisoformat(r["started_at"])
            t1 = datetime.datetime.fromisoformat(r["finished_at"]) if r["finished_at"] else (now if r["state"] == "running" else None)
        except (TypeError, ValueError):
            continue
        if t1 is None:
            continue
        out[r["pool"]] = out.get(r["pool"], 0.0) + max(0.0, (t1 - t0).total_seconds()) / 3600.0
    return out


def _alive(pid):
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def job_id_for(kind, payload, nonce):
    h = hashlib.sha1(json.dumps([kind, payload, nonce], sort_keys=True, default=str).encode()).hexdigest()
    return "j" + h[:12]


class Queue:
    def __init__(self, cfg, conn, log_dir, env=None, python=None, log=print):
        self.cfg = cfg
        self.conn = conn
        self.log_dir = log_dir
        q = cfg["queue"]
        self.caps = {"dc": int(q["dc_seats_max"]), "pt": int(q["pt_seats_max"]),
                     "vcf": int(q["vcf_seats_max"]), "local": int(q["local_max"]),
                     "search": int(q["search_max"] if q.get("search_max") is not None else q["local_max"])}   # 0 = no search run dispatched (an outage stopgap)   # 2026-09-15: search runs poll for their queue jobs (yosys fitness of arm B0 in the local pool); sharing the local pool deadlocks once 16 such runs hold every seat
        # dispatch limits: an optional `<pool>_concurrency` below the seat cap (config queue.dc_concurrency, DECISIONS
        # 2026-09-12: 12 DC jobs at once on the 64-core host); the caps stay the hard ceiling
        # dispatch targets below the seat caps: `<pool>_seats_target` (DECISIONS 2026-09-14: 24 for Phases 3-4, 50 only for bulk
        # Phase 5-6 runs on the user's confirmation); the older `<pool>_concurrency` key is honoured for compatibility
        self.concurrency = {pool: (q.get(f"{pool}_seats_target") if q.get(f"{pool}_seats_target") is not None else q.get(f"{pool}_concurrency"))
                            for pool in self.caps}
        self.backoff_cfg = q["backoff"]
        self.retries = int(q["retries"])
        self.env = dict(env) if env is not None else dict(os.environ)
        self.python = python or sys.executable
        self.children = {}   # job_id -> Popen (only jobs spawned by this process)
        self._log = log
        os.makedirs(log_dir, exist_ok=True)

    @property
    def limits(self):
        """Effective dispatch limit per pool: min(seat cap, configured concurrency); follows later changes of caps."""
        return {p: (min(cap, int(self.concurrency[p])) if self.concurrency.get(p) else cap) for p, cap in self.caps.items()}

    def log(self, msg):
        self._log(f"{db.now()} {msg}", flush=True) if self._log is print else self._log(msg)

    # ------------------------------------------------------------------ submission
    def default_timeout(self, kind, payload=None):
        t = self.cfg["timeouts"]
        table = {"dc": t["dc_medium"] * 60, "dc_hidden": t["dc_medium"] * 60, "pt": t["pt"] * 60, "vcf": t["seq_min"] * 60,
                 "sim": t["sim"] * 60, "llm": t["llm_call_sec"], "yosys": t["sim"] * 60, "orfs": t["dc_large"] * 60}
        return float(table.get(kind, 3600))

    def submit(self, kind, payload, design_id=None, cand_id=None, config=None, priority=0, timeout_sec=None, pool=None):
        payload = dict(payload or {})
        pool = pool or payload.get("pool") or POOL_OF_KIND.get(kind)
        if pool not in self.caps:
            raise ValueError(f"unknown pool {pool!r} for kind {kind!r}; pools: {sorted(self.caps)}")
        if kind == "shell" and not (payload.get("cmd") or payload.get("argv")):
            raise ValueError("shell jobs need payload.cmd or payload.argv")
        if kind != "shell" and not (payload.get("module") or RUNNER_OF_KIND.get(kind)):
            raise ValueError(f"no runner module known for kind {kind!r}")
        submitted = db.now()
        jid = job_id_for(kind, payload, f"{submitted}:{time.time_ns()}")
        timeout = float(timeout_sec) if timeout_sec is not None else self.default_timeout(kind, payload)
        row = {"job_id": jid, "kind": kind, "pool": pool, "design_id": design_id, "cand_id": cand_id, "config": config,
               "priority": int(priority), "state": "queued", "attempts": 0, "payload_json": json.dumps(payload, sort_keys=True),
               "timeout_sec": timeout, "submitted_at": submitted}
        db.insert(self.conn, "jobs", row)
        return jid

    # ------------------------------------------------------------------ queries
    def get(self, job_id):
        return self.conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()

    def _set(self, job_id, **fields):
        cols = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE jobs SET {cols} WHERE job_id=?", (*fields.values(), job_id))

    def _backoff(self, pool):
        r = self.conn.execute("SELECT backoff_until, backoff_level FROM queue_state WHERE pool=?", (pool,)).fetchone()
        return (float(r["backoff_until"]), int(r["backoff_level"])) if r else (0.0, 0)

    def _set_backoff(self, pool, until, level):
        self.conn.execute("INSERT INTO queue_state (pool, backoff_until, backoff_level, updated_at) VALUES (?,?,?,?) "
                          "ON CONFLICT(pool) DO UPDATE SET backoff_until=excluded.backoff_until, "
                          "backoff_level=excluded.backoff_level, updated_at=excluded.updated_at",
                          (pool, float(until), int(level), db.now()))

    def running_in_pool(self, pool):
        return self.conn.execute("SELECT COUNT(*) FROM jobs WHERE state='running' AND pool=?", (pool,)).fetchone()[0]

    def stats(self):
        by = {}
        for r in self.conn.execute("SELECT pool, state, COUNT(*) AS n FROM jobs GROUP BY pool, state"):
            by.setdefault(r["pool"], {})[r["state"]] = r["n"]
        pools = {}
        for p, cap in self.caps.items():
            until, level = self._backoff(p)
            s = by.get(p, {})
            pools[p] = {"cap": cap, "limit": self.limits[p], "running": s.get("running", 0), "waiting": s.get("queued", 0) + s.get("backoff", 0),
                        "done": s.get("done", 0), "failed": s.get("failed", 0),
                        "backoff_remaining_sec": max(0.0, until - time.time()), "backoff_level": level}
        return pools

    # ------------------------------------------------------------------ the tick
    def tick(self):
        self._reap()
        self._recover()
        self._dispatch()

    def _command_for(self, job, payload):
        if job["kind"] == "shell":
            return payload.get("cmd") or shlex.join([str(a) for a in payload["argv"]])
        module = payload.get("module") or RUNNER_OF_KIND[job["kind"]]
        return shlex.join([self.python, "-m", module, "--job", job["job_id"]] + [str(a) for a in payload.get("args", [])])

    def _spawn(self, job):
        jid = job["job_id"]
        payload = json.loads(job["payload_json"])
        attempt = int(job["attempts"])
        log = os.path.join(self.log_dir, f"{jid}.a{attempt}.log")
        done = os.path.join(self.log_dir, f"{jid}.a{attempt}.done")
        cmd = self._command_for(job, payload)
        # the command runs in a subshell so that an `exit N` inside it cannot skip writing the done marker
        wrapper = f"( {cmd} ); rc=$?; echo $rc > {shlex.quote(done)}; exit $rc"
        env = dict(self.env, BEYOND_SYNTH_JOB_ID=jid, BEYOND_SYNTH_ROOT=ROOT,
                   PYTHONPATH=ROOT + (":" + self.env["PYTHONPATH"] if self.env.get("PYTHONPATH") else ""))
        with open(log, "ab") as lf:
            lf.write(f"# job {jid} attempt {attempt} kind={job['kind']} pool={job['pool']} started {db.now()}\n# {cmd}\n".encode())
            lf.flush()
            p = subprocess.Popen(["bash", "-c", wrapper], cwd=ROOT, env=env, stdout=lf, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
        self.children[jid] = p
        self._set(jid, state="running", host_pid=p.pid, log_path=log, done_path=done, started_at=db.now(),
                  finished_at=None, exit_code=None, error=None)
        self.log(f"{jid} start pool={job['pool']} kind={job['kind']} attempt={attempt} pid={p.pid}")

    def _kill(self, pid):
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(int(pid), sig)
            except ProcessLookupError:
                return
            except PermissionError:
                return
            deadline = time.time() + KILL_GRACE_SEC
            while time.time() < deadline and _alive(pid):
                time.sleep(0.05)
            if not _alive(pid):
                return

    def _reap(self):
        now = time.time()
        for jid, p in list(self.children.items()):
            job = self.get(jid)
            rc = p.poll()
            error = None
            if rc is None:
                if job["timeout_sec"] and job["started_at"] and now - _ts(job["started_at"]) > float(job["timeout_sec"]):
                    self._kill(p.pid)
                    try:
                        p.wait(timeout=KILL_GRACE_SEC)
                    except subprocess.TimeoutExpired:
                        pass
                    rc, error = TIMEOUT_RC, f"timeout after {job['timeout_sec']} s"
                else:
                    continue
            del self.children[jid]
            self._finish(job, rc, error)

    def _recover(self):
        """Jobs marked running that this process did not spawn: a previous daemon left them behind."""
        for job in self.conn.execute("SELECT * FROM jobs WHERE state='running'").fetchall():
            jid = job["job_id"]
            if jid in self.children:
                continue
            done = job["done_path"]
            if done and os.path.exists(done):
                try:
                    rc = int(open(done).read().strip())
                except ValueError:
                    rc = -1
                self._finish(job, rc, None if rc == 0 else "recovered after daemon restart")
            elif job["host_pid"] and _alive(job["host_pid"]):
                if job["timeout_sec"] and job["started_at"] and time.time() - _ts(job["started_at"]) > float(job["timeout_sec"]):
                    self._kill(job["host_pid"])
                    self._finish(job, TIMEOUT_RC, f"timeout after {job['timeout_sec']} s (adopted job)")
            else:
                self._finish(job, -1, "process vanished without a done marker (daemon restart)")

    def _finish(self, job, rc, error=None):
        jid, pool = job["job_id"], job["pool"]
        if rc == EX_TEMPFAIL:
            level = self._backoff(pool)[1] + 1
            b = self.backoff_cfg
            delay = min(float(b["initial_sec"]) * float(b["factor"]) ** (level - 1), float(b["max_sec"]))
            self._set_backoff(pool, time.time() + delay, level)
            self._set(jid, state="backoff", host_pid=None, exit_code=rc, error="license seat unavailable (exit 75)",
                      finished_at=db.now())
            self.log(f"{jid} backoff pool={pool} level={level} delay={delay:.0f}s")
            return
        if rc == 0:
            self._set_backoff(pool, 0, 0)
            self._set(jid, state="done", host_pid=None, exit_code=0, error=None, finished_at=db.now())
            self.log(f"{jid} done")
            return
        attempts = int(job["attempts"]) + 1
        error = error or f"exit {rc}"
        if attempts <= self.retries:
            self._set(jid, state="queued", attempts=attempts, host_pid=None, exit_code=rc, error=error, finished_at=None)
            self.log(f"{jid} failed ({error}); retry {attempts}/{self.retries}")
        else:
            self._set(jid, state="failed", attempts=attempts, host_pid=None, exit_code=rc, error=error, finished_at=db.now())
            self.log(f"{jid} FAILED ({error}) after {attempts} attempts")

    def backpressure_holds(self, pool):
        """config `queue.backpressure[pool] = {pool: <other>, max_waiting: N}` (user decision 2026-09-16): no new job of `pool` starts while
        the other pool is saturated (running at its limit) and more than N of its jobs wait — search runs are throttled by the depth of
        the VC Formal queue so that verdicts keep arriving within a generation's wait; seats that fairness leaves free do not count as
        saturation."""
        bp = ((self.cfg["queue"].get("backpressure") or {}).get(pool)) or {}
        other = bp.get("pool")
        if not other or other not in self.limits:
            return False
        if self.running_in_pool(other) < self.limits[other]:
            return False
        waiting = self.conn.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','backoff') AND pool=?", (other,)).fetchone()[0]
        return waiting > int(bp.get("max_waiting", 0))

    def _dispatch(self):
        now = time.time()
        for pool, cap in self.limits.items():
            until, _ = self._backoff(pool)
            if until > now:
                continue
            free = cap - self.running_in_pool(pool)
            if free <= 0:
                continue
            if self.backpressure_holds(pool):
                continue
            per_design = int((self.cfg["queue"].get("per_design_max") or {}).get(pool) or 0)
            rows = self.conn.execute(
                "SELECT * FROM jobs WHERE state IN ('queued','backoff') AND pool=? "
                "ORDER BY priority DESC, submitted_at ASC, job_id ASC LIMIT ?", (pool, -1 if per_design else free)).fetchall()   # with a per-design cap the whole queue is scanned: a window of free + 200 rows starved every other design behind one design's backlog (2026-09-16, 480 queued proofs of one design)
            spawned = 0
            for job in rows:
                if spawned >= free:
                    break
                if per_design and job["design_id"]:
                    n = self.conn.execute("SELECT COUNT(*) FROM jobs WHERE state='running' AND pool=? AND design_id=?", (pool, job["design_id"])).fetchone()[0]
                    if n >= per_design:
                        continue  # fairness (config queue.per_design_max): another design's job goes first; this one waits
                try:
                    self._spawn(job)
                    spawned += 1
                except Exception as e:  # one unspawnable job (unknown kind in an old daemon, bad payload) must not block the pool
                    self._set(job["job_id"], state="failed", exit_code=None, error=f"cannot spawn: {type(e).__name__}: {e}"[:200],
                              finished_at=db.now())
                    self.log(f"{job['job_id']} FAILED before start ({type(e).__name__}: {e})")
