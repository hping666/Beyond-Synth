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
EX_RESTART = 76      # a search run leaving for a code roll (driver: SIGUSR1 -> state saved -> exit 76): requeued as a resumption, no attempt consumed (2026-09-16)
ROLL_SIGNAL_RC = 128 + signal.SIGUSR1   # the same request delivered to a run whose driver predates the handler (the shell wrapper reports 128 + 10)
TIMEOUT_RC = 124
POOL_OF_KIND = {"shell": "local", "sim": "local", "yosys": "local", "llm": "local", "orfs": "local", "search": "search",   # search runs in their own pool (2026-09-15): they wait for local yosys jobs and must not fill the local pool
                "dc": "dc", "pt": "pt", "vcf": "vcf", "dc_hidden": "dc", "dc_retry": "dc"}   # dc_retry: the 4-slot retry lane of search-run E4 timeouts (DECISION 2026-09-18 (b) item 4)
RUNNER_OF_KIND = {"dc": "src.eval.run_dc", "pt": "src.eval.run_pt", "yosys": "src.eval.run_yosys",
                  "orfs": "src.eval.run_orfs", "vcf": "src.equiv.run_equiv", "sim": "src.equiv.run_equiv",
                  "llm": "src.search.run_llm", "search": "src.search.run_search",   # Phase 3: one residual-guided evolution run per job
                  "dc_hidden": "scripts.hidden_worker",  # hidden configurations: recorded only by the hidden worker (rule 3)
                  "dc_retry": "src.eval.run_dc"}
KILL_GRACE_SEC = 3.0


def _ts(iso):
    return datetime.datetime.fromisoformat(iso).timestamp()


def held_job(job):
    """DECISION 2026-09-18 item 2: a search job whose payload carries `hold` (the reason) waits until the flag is removed."""
    try:
        return bool(json.loads(job["payload_json"] or "{}").get("hold"))
    except (ValueError, TypeError):
        return False


def round_robin_by_row(rows, run_rows, tier_of, tier_order=("large", "medium", "small")):
    """DECISION 2026-09-18 item 5b and (b) item 6: queued search jobs re-ordered so that, within a priority level and a tier, every
    admission goes to the arm-model row with the fewest runs running or already placed ahead (ties: the queue order) — rows
    behind the others catch up first (the released M rows), then the rows alternate; tiers keep their order (large, medium,
    small, then unknown). Jobs of runs the runs table does not know keep their place at the end of their level."""
    from collections import OrderedDict
    out = []
    by_pri = OrderedDict()
    for r in rows:
        by_pri.setdefault(r["priority"], []).append(r)
    for pri, jobs in by_pri.items():
        by_tier = OrderedDict()
        unknown = []
        for j in jobs:
            try:
                rid = json.loads(j["payload_json"] or "{}").get("run_id")
            except (ValueError, TypeError):
                rid = None
            k = run_rows["rows"].get(rid)
            if not k:
                unknown.append(j)
                continue
            arm, model, design = k
            by_tier.setdefault(tier_of.get(design, "?"), OrderedDict()).setdefault((arm, model), []).append(j)
        for tier in sorted(by_tier, key=lambda t: tier_order.index(t) if t in tier_order else len(tier_order)):
            rws = by_tier[tier]
            order = list(rws)
            counts = {k: int(run_rows["running"].get(k, 0)) for k in order}
            while any(rws.values()):
                k = min((k for k in order if rws[k]), key=lambda k: (counts[k], order.index(k)))
                out.append(rws[k].pop(0))
                counts[k] += 1
        out.extend(unknown)
    return out


def window_dispatch(rows, run_rows, tier_of, design_order, window, lane_designs=(), lane_search_max=0, running_by_design=None,
                    tier_order=("large", "medium", "small")):
    """DECISION 2026-09-18 (d) B2 / B3: queued search jobs ordered for dispatch. Within a priority level and a tier every admission goes
    to the arm-model row with the fewest runs running or already placed (ties: queue order; the least-run-row-first catch-up of item 6).
    The row takes its next run from the earliest design, in the tier's fixed `design_order` (designs not listed come after, by name),
    among the `window` earliest designs that still have queued runs in any row; a row with no seed left inside the window takes its
    earliest design beyond it (so no row idles). Designs in `lane_designs` (the long-pole lane) sit outside the window: a row alternates
    between its lane run and its window run while the lane's running + placed search runs stay below `lane_search_max` (0 = no lane);
    lane runs beyond that cap are left out of the tick's order (the cap is enforced here).
    Tiers keep their order; jobs of runs the runs table does not know keep their place at the end of their level."""
    from collections import OrderedDict
    running_by_design = running_by_design or {}
    out = []
    by_pri = OrderedDict()
    for r in rows:
        by_pri.setdefault(r["priority"], []).append(r)
    for pri, jobs in by_pri.items():
        by_tier = OrderedDict()
        unknown = []
        for j in jobs:
            try:
                rid = json.loads(j["payload_json"] or "{}").get("run_id")
            except (ValueError, TypeError):
                rid = None
            k = run_rows["rows"].get(rid)
            if not k:
                unknown.append(j)
                continue
            arm, model, design = k
            by_tier.setdefault(tier_of.get(design, "?"), OrderedDict()).setdefault((arm, model), []).append((design, j))
        for tier in sorted(by_tier, key=lambda t: tier_order.index(t) if t in tier_order else len(tier_order)):
            rws = by_tier[tier]
            order = list(design_order.get(tier) or [])
            def rank(d):
                return (order.index(d), "") if d in order else (len(order), d)
            lane = {k: [x for x in v if x[0] in lane_designs] for k, v in rws.items()}
            win = {k: sorted([x for x in v if x[0] not in lane_designs], key=lambda x: rank(x[0])) for k, v in rws.items()}
            for k in lane:
                lane[k].sort(key=lambda x: rank(x[0]))
            row_order = list(rws)
            counts = {k: int(run_rows["running"].get(k, 0)) for k in row_order}
            last = {k: None for k in row_order}
            lane_load = sum(int(running_by_design.get(d, 0)) for d in lane_designs)
            active = [k for k in row_order if lane[k] or win[k]]
            while active:
                k = min(active, key=lambda k: (counts[k], row_order.index(k)))
                pick = None
                lane_ok = bool(lane[k]) and lane_search_max > 0 and lane_load < lane_search_max
                if lane_ok and (last[k] != "lane" or not win[k]):
                    pick = lane[k].pop(0)
                    last[k] = "lane"
                    lane_load += 1
                elif win[k]:
                    remaining = sorted({d for v in win.values() for d, _ in v}, key=rank)
                    wset = set(remaining[:max(1, int(window or 1))])
                    idx = next((i for i, (d, _) in enumerate(win[k]) if d in wset), 0)   # the earliest design of the window this row still has a seed on, else its earliest beyond the window
                    pick = win[k].pop(idx)
                    last[k] = "window"
                elif lane[k]:   # only lane runs left for this row but the lane is at its search cap: the row waits
                    active.remove(k)
                    continue
                out.append(pick[1])
                counts[k] += 1
                if not lane[k] and not win[k]:
                    active.remove(k)
        out.extend(unknown)
    return out


def lane_of(lanes, design_id):
    """(lane name, spec) of a design under config queue.lanes[pool] = {name: {designs: [...], share: n}}, or (None, None)."""
    for name, spec in (lanes or {}).items():
        if design_id in (spec.get("designs") or []):
            return name, spec
    return None, None


def round_robin_by_design(rows, running_by_design=None):
    """Queued jobs re-ordered so that, within one priority level, designs alternate (each design's own jobs keep their order),
    the design holding the fewest running seats first: the per-design fairness cap bounds a design's seats, this gives every
    design a share of the seats that free up even when only a few free per tick."""
    from collections import OrderedDict
    running_by_design = running_by_design or {}
    out = []
    by_pri = OrderedDict()
    for r in rows:
        by_pri.setdefault(r["priority"], OrderedDict()).setdefault(r["design_id"] or "", []).append(r)
    for pri, designs in by_pri.items():
        order = sorted(designs, key=lambda d: (int(running_by_design.get(d, 0)), list(designs).index(d)))
        queues = [designs[d] for d in order]
        while any(queues):
            for q in queues:
                if q:
                    out.append(q.pop(0))
    return out


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
    """True when the process exists and is not a zombie (2026-09-18: the recovery adopts live processes first, so a zombie
    left by a daemon that spawned it must count as dead)."""
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        with open(f"/proc/{int(pid)}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
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
        table = {"dc": t["dc_medium"] * 60, "dc_hidden": t["dc_medium"] * 60, "dc_retry": 3600 + 180, "pt": t["pt"] * 60, "vcf": t["seq_min"] * 60,
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
    def reprioritize(self, job_id, priority):
        """A new priority for a job that has not started (queued / backoff): the proof queue is ordered by the provisional
        diagnosis (DECISIONS 2026-09-16, scheduling change item 2). -> True when the job was still waiting."""
        cur = self.conn.execute("UPDATE jobs SET priority=? WHERE job_id=? AND state IN ('queued','backoff')", (int(priority), job_id))
        return cur.rowcount > 0

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

    def run_rows(self):
        """run_id -> (arm, model, design_id, running count of that row) for the search jobs' round-robin across arm-model rows."""
        rows = {r["run_id"]: (r["arm"], r["llm_model"], r["design_id"]) for r in self.conn.execute("SELECT run_id, arm, llm_model, design_id FROM runs")}
        running = {}
        for r in self.conn.execute("SELECT payload_json FROM jobs WHERE kind='search' AND state='running'"):
            try:
                rid = json.loads(r[0] or "{}").get("run_id")
            except (ValueError, TypeError):
                continue
            k = rows.get(rid)
            if k:
                running[(k[0], k[1])] = running.get((k[0], k[1]), 0) + 1
        return {"rows": rows, "running": running}

    def tier_of_design(self):
        sp = (self.cfg.get("exp5") or {}).get("starting_points") or {}
        return {d: t for t, ds in sp.items() for d in (ds or [])}

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
        try:
            os.remove(done)   # a marker left by an earlier start of the same attempt (a code roll keeps the attempt number) must not be read as this start's exit
        except OSError:
            pass
        cmd = self._command_for(job, payload)
        # the command runs in a subshell so that an `exit N` inside it cannot skip writing the done marker
        if payload.get("offline_pool"):   # DECISION 2026-09-18 (b) item 3: offline-pool jobs run under nice 19 and the idle I/O class
            cmd = f"nice -n 19 ionice -c 3 {cmd}"
        wrapper = f"( {cmd} ); rc=$?; echo $rc > {shlex.quote(done)}; exit $rc"
        limit_gb = (self.cfg["queue"].get("max_file_gb") or {}).get(job["kind"])
        if limit_gb:   # 2026-09-16: a lock-step simulation dumped a 36 GB VCD in 18 minutes; a file-size limit kills such a job (SIGXFSZ) instead of filling the disk
            wrapper = f"ulimit -f {int(float(limit_gb) * 1048576)}; " + wrapper
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
        """Jobs marked running that this process did not spawn: a previous daemon left them behind. A job whose process is
        alive is adopted as it is — its done marker is consulted only once the process is gone (2026-09-18: a marker left by
        an earlier attempt of the same job, e.g. the exit 76 of a code roll, made three daemon restarts re-spawn running runs,
        so 22 runs had two or three drivers at once)."""
        for job in self.conn.execute("SELECT * FROM jobs WHERE state='running'").fetchall():
            jid = job["job_id"]
            if jid in self.children:
                continue
            if job["host_pid"] and _alive(job["host_pid"]):
                if job["timeout_sec"] and job["started_at"] and time.time() - _ts(job["started_at"]) > float(job["timeout_sec"]):
                    self._kill(job["host_pid"])
                    self._finish(job, TIMEOUT_RC, f"timeout after {job['timeout_sec']} s (adopted job)")
                continue
            done = job["done_path"]
            if done and os.path.exists(done) and (not job["started_at"] or os.path.getmtime(done) >= _ts(job["started_at"]) - 1.0):
                try:
                    rc = int(open(done).read().strip())
                except ValueError:
                    rc = -1
                self._finish(job, rc, None if rc == 0 else "recovered after daemon restart")
            else:
                self._finish(job, -1, "process vanished without a done marker (daemon restart)")

    def _finish(self, job, rc, error=None):
        jid, pool = job["job_id"], job["pool"]
        if job["kind"] == "search" and rc in (EX_RESTART, ROLL_SIGNAL_RC, -signal.SIGUSR1):   # a code roll (2026-09-16): the run resumes under the new code, no attempt consumed
            self._set(jid, state="queued", host_pid=None, exit_code=rc, error="restarted for a code roll", finished_at=None)
            self.log(f"{jid} requeued for a code roll (exit {rc})")
            return
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
        return self.dispatchable_waiting(other) > int(bp.get("max_waiting", 0))

    def dispatchable_waiting(self, pool):
        """DECISION 2026-09-18 (d) B1: the waiting jobs of `pool` that could start if a seat freed — a job of a design at its per-design
        cap (or of a lane at its share) is blocked by fairness, not by the pool, and does not count."""
        per_design = int((self.cfg["queue"].get("per_design_max") or {}).get(pool) or 0)
        lanes = (self.cfg["queue"].get("lanes") or {}).get(pool) or {}
        if not per_design and not lanes:
            return self.conn.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','backoff') AND pool=?", (pool,)).fetchone()[0]
        running = {r[0]: r[1] for r in self.conn.execute("SELECT design_id, COUNT(*) FROM jobs WHERE state='running' AND pool=? GROUP BY design_id", (pool,))}
        n = 0
        for r in self.conn.execute("SELECT design_id, COUNT(*) FROM jobs WHERE state IN ('queued','backoff') AND pool=? GROUP BY design_id", (pool,)):
            d, q = r[0], int(r[1])
            name, spec = lane_of(lanes, d)
            cap = int(spec.get("share") or 0) if spec and len(spec.get("designs") or []) == 1 else per_design
            room = max(0, cap - int(running.get(d, 0))) if cap else q
            n += min(q, room)
        return n

    def lane_state(self, pool, lanes, rows):
        """Running and queued counts per lane and for the rest (DECISION 2026-09-18 (d) B3)."""
        running = {r[0]: r[1] for r in self.conn.execute("SELECT design_id, COUNT(*) FROM jobs WHERE state='running' AND pool=? GROUP BY design_id", (pool,))}
        queued = {}
        for r in rows:
            queued[r["design_id"]] = queued.get(r["design_id"], 0) + 1
        st = {"running": {}, "queued": {}, "others_running": 0}
        for name, spec in lanes.items():
            ds = spec.get("designs") or []
            st["running"][name] = sum(int(running.get(d, 0)) for d in ds)
            st["queued"][name] = sum(int(queued.get(d, 0)) for d in ds)
        st["others_running"] = sum(running.values()) - sum(st["running"].values())
        return st

    @staticmethod
    def lane_admits(st, lanes, design_id, cap):
        """A lane job starts while its lane is below its share; another job starts while the rest stay within cap minus the seats the
        lanes can use now (min(share, running + queued) each): an idle lane releases its share, a busy one keeps it."""
        name, spec = lane_of(lanes, design_id)
        if spec:
            return st["running"].get(name, 0) < int(spec.get("share") or 0)
        reserved = sum(min(int(s.get("share") or 0), st["running"].get(n, 0) + st["queued"].get(n, 0)) for n, s in lanes.items())
        return st["others_running"] < int(cap) - reserved

    @staticmethod
    def lane_count(st, lanes, design_id):
        name, spec = lane_of(lanes, design_id)
        if spec:
            st["running"][name] = st["running"].get(name, 0) + 1
            st["queued"][name] = max(0, st["queued"].get(name, 0) - 1)
        else:
            st["others_running"] += 1

    def fresh_admissions_left(self, pool):
        """How many fresh search runs may still start this tick under `queue.search_admit_per_min` (None = no limit): the limit minus
        the search jobs started within the last minute."""
        if pool != "search":
            return 10 ** 9
        lim = self.cfg["queue"].get("search_admit_per_min")
        if not lim:
            return 10 ** 9
        since = (datetime.datetime.now() - datetime.timedelta(seconds=60)).isoformat(timespec="seconds")
        n = self.conn.execute("SELECT COUNT(*) FROM jobs WHERE kind='search' AND started_at >= ?", (since,)).fetchone()[0]
        return max(0, int(lim) - int(n))

    def is_resumption(self, job):
        """A search job of a run that already made LLM calls (an interrupted run resuming from its state)."""
        if job["kind"] != "search":
            return False
        try:
            rid = json.loads(job["payload_json"] or "{}").get("run_id")
        except (ValueError, TypeError):
            return False
        if not rid:
            return False
        r = self.conn.execute("SELECT llm_calls FROM runs WHERE run_id=?", (rid,)).fetchone()
        return bool(r and int(r[0] or 0) > 0)

    def _dispatch(self):
        now = time.time()
        for pool, cap in self.limits.items():
            until, _ = self._backoff(pool)
            if until > now:
                continue
            free = cap - self.running_in_pool(pool)
            if free <= 0:
                continue
            held = self.backpressure_holds(pool)   # fresh runs wait; a resumption (a run that already made calls) goes on — it has verdicts to process and records to slim (2026-09-16)
            admit_left = self.fresh_admissions_left(pool)   # and fresh runs are admitted a few per minute, so the concurrency ramps to what the proof seats sustain instead of bursting
            per_design = int((self.cfg["queue"].get("per_design_max") or {}).get(pool) or 0)
            per_kind = dict(self.cfg["queue"].get("per_kind_max") or {})   # 2026-09-16: a kind's own ceiling inside a pool (hidden-layer DC jobs while the visible layer needs the CPU); 2026-09-18: applied in every pool the kind's jobs sit in (H4 signoff jobs are kind dc_hidden in the pt pool)
            running_kind = {r[0]: r[1] for r in self.conn.execute("SELECT kind, COUNT(*) FROM jobs WHERE state='running' AND pool=? GROUP BY kind", (pool,))} if per_kind else {}
            rows = self.conn.execute(
                "SELECT * FROM jobs WHERE state IN ('queued','backoff') AND pool=? "
                "ORDER BY priority DESC, submitted_at ASC, job_id ASC LIMIT ?", (pool, -1 if (per_design or per_kind or held) else free)).fetchall()   # with a per-design cap, or while backpressure holds fresh runs (a resumption behind them must be reached, 2026-09-16), the whole queue is scanned: a window of free + 200 rows starved every other design behind one design's backlog (2026-09-16, 480 queued proofs of one design)
            if per_design:
                running_by_design = {r[0]: r[1] for r in self.conn.execute("SELECT design_id, COUNT(*) FROM jobs WHERE state='running' AND pool=? GROUP BY design_id", (pool,))}
                rows = round_robin_by_design(rows, running_by_design)   # 2026-09-16: within a priority level the designs take turns, the design holding the fewest seats first
            lanes = (self.cfg["queue"].get("lanes") or {}).get(pool) or {}   # DECISION 2026-09-18 (d) B3: long-pole lanes with reserved seat shares
            lane_state = self.lane_state(pool, lanes, rows) if lanes else None
            if pool == "search":
                rows = [r for r in rows if not held_job(r)]   # DECISION 2026-09-18 item 2: a run with `hold` in its payload is not submitted until released
                if self.cfg["queue"].get("dispatch_window"):   # DECISION 2026-09-18 (d) B2 / B3: fixed design order, sliding window, long-pole lane
                    lp = self.cfg["queue"].get("long_pole_lane") or {}
                    running_search = {r[0]: r[1] for r in self.conn.execute("SELECT design_id, COUNT(*) FROM jobs WHERE state='running' AND pool='search' GROUP BY design_id")}
                    rows = window_dispatch(rows, self.run_rows(), self.tier_of_design(), self.cfg["queue"].get("dispatch_design_order") or {}, int(self.cfg["queue"]["dispatch_window"]),
                                           lane_designs=tuple(lp.get("designs") or []), lane_search_max=int(lp.get("search_max") or 0), running_by_design=running_search)
                elif self.cfg["queue"].get("round_robin_rows"):
                    rows = round_robin_by_row(rows, self.run_rows(), self.tier_of_design())   # DECISION 2026-09-18 item 5b: within a tier the seven arm-model rows take turns
            spawned = 0
            for job in rows:
                if spawned >= free:
                    break
                lim_kind = per_kind.get(job["kind"])
                if lim_kind is not None and running_kind.get(job["kind"], 0) >= int(lim_kind):
                    continue   # this kind is at its ceiling; other kinds of the pool may still start
                fresh = not self.is_resumption(job)
                if held and fresh:
                    continue
                if fresh and job["kind"] == "search":
                    if admit_left <= 0:
                        continue
                    admit_left -= 1
                if per_design and job["design_id"]:
                    n = self.conn.execute("SELECT COUNT(*) FROM jobs WHERE state='running' AND pool=? AND design_id=?", (pool, job["design_id"])).fetchone()[0]
                    lname, lspec = lane_of(lanes, job["design_id"]) if lanes else (None, None)
                    single = bool(lspec) and len(lspec.get("designs") or []) == 1
                    if n >= per_design and not single:
                        continue  # fairness (config queue.per_design_max): another design's job goes first; this one waits
                if lane_state is not None and not self.lane_admits(lane_state, lanes, job["design_id"], cap):
                    continue  # DECISION 2026-09-18 (d) B3: the lane is at its share, or the others would eat into a lane's reserved seats
                try:
                    self._spawn(job)
                    spawned += 1
                    if lane_state is not None:
                        self.lane_count(lane_state, lanes, job["design_id"])
                    if per_kind:
                        running_kind[job["kind"]] = running_kind.get(job["kind"], 0) + 1
                except Exception as e:  # one unspawnable job (unknown kind in an old daemon, bad payload) must not block the pool
                    self._set(job["job_id"], state="failed", exit_code=None, error=f"cannot spawn: {type(e).__name__}: {e}"[:200],
                              finished_at=db.now())
                    self.log(f"{job['job_id']} FAILED before start ({type(e).__name__}: {e})")
