"""SQLite access for the results database (docs/spec/07-results-db.md).

connect() opens results/db/results.sqlite (or an explicit path), applies schema.sql idempotently and returns
an autocommit connection with WAL journaling so the queue daemon, job runners and analysis can share it.
stamp() supplies the created_at / git_sha / cfg_hash columns every table requires.
Writes of evaluation records go through ingest.py (Phase 0.5); this module only provides the plumbing.
"""
import datetime
import os
import sqlite3

from src import config as C

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def db_path(cfg=None):
    return os.path.join(C.results_dir(cfg), "db", "results.sqlite")


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def stamp():
    return {"created_at": now(), "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash()}


def init_schema(conn):
    with open(SCHEMA) as f:
        conn.executescript(f.read())


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
