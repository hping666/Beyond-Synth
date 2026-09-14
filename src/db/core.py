"""SQLite access for the results database (docs/spec/07-results-db.md).

connect() opens results/db/results.sqlite (or an explicit path), applies schema.sql idempotently and returns
an autocommit connection with WAL journaling so the queue daemon, job runners and analysis can share it.
stamp() supplies the created_at / git_sha / cfg_hash columns every table requires.
Writes of evaluation records go through ingest.py (Phase 0.5); this module only provides the plumbing.
"""
import datetime
import os
import re
import sqlite3

from src import config as C

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def db_path(cfg=None):
    return os.path.join(C.results_dir(cfg), "db", "results.sqlite")


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def stamp():
    return {"created_at": now(), "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash()}


MIGRATIONS = [  # (table, column, DDL) added after the table already existed; CREATE IF NOT EXISTS does not alter tables
    ("candidates", "proven_by", "ALTER TABLE candidates ADD COLUMN proven_by TEXT CHECK (proven_by IN ('seq', 'dpv') OR proven_by IS NULL)"),
    ("noise_floor", "t_d", "ALTER TABLE noise_floor ADD COLUMN t_d REAL"),                 # rule A threshold (DECISIONS 2026-09-14)
    ("noise_floor", "floor_class", "ALTER TABLE noise_floor ADD COLUMN floor_class TEXT"),   # quiet | spread | offset
    ("noise_floor", "floor_source", "ALTER TABLE noise_floor ADD COLUMN floor_source TEXT"), # measured | pooled
    ("noise_floor", "pooled_min", "ALTER TABLE noise_floor ADD COLUMN pooled_min REAL"),
]


def _table_ddl(name):
    """The CREATE TABLE statement of one table from schema.sql."""
    with open(SCHEMA) as f:
        m = re.search(rf"CREATE TABLE IF NOT EXISTS {name} \(.*?\);", f.read(), re.S)
    return m.group(0)


def _rebuild_perturbations_if_old(conn):
    """2026-09-13: the round trip (ptype P0_roundtrip) joined the perturbations table; SQLite cannot alter a CHECK
    constraint, so a table created with the old constraint is rebuilt once (rows copied, then the old table dropped)."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='perturbations'").fetchone()
    if not row or ("P0_roundtrip" in row[0] and "P1_text" in row[0]):
        return False
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='perturbations'").fetchone()
        if "P0_roundtrip" in row[0] and "P1_text" in row[0]:  # another connection rebuilt it while we waited for the lock
            conn.execute("COMMIT")
            return False
        conn.execute("ALTER TABLE perturbations RENAME TO perturbations_old")
        conn.execute(_table_ddl("perturbations"))
        conn.execute("INSERT INTO perturbations (pert_id, design_id, ptype, path, seq_status, created_at, git_sha, cfg_hash) "
                     "SELECT pert_id, design_id, ptype, path, seq_status, created_at, git_sha, cfg_hash FROM perturbations_old")
        conn.execute("DROP TABLE perturbations_old")
        conn.execute("COMMIT")
        return True
    except Exception:
        conn.execute("ROLLBACK")
        raise


def init_schema(conn):
    _rebuild_perturbations_if_old(conn)
    with open(SCHEMA) as f:
        conn.executescript(f.read())
    for table, column, ddl in MIGRATIONS:
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            conn.execute(ddl)


def connect(path=None, cfg=None):
    path = path or db_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)  # autocommit; each statement is atomic
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    return conn


def insert(conn, table, row):
    """Insert one row (dict) with the stamp columns added; returns the rowid."""
    row = dict(row)
    row.update(stamp())
    cols = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(row.values()))
    return cur.lastrowid
