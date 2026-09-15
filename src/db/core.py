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
    # Phase 3 (DECISIONS 2026-09-14, spec 07): requested class, prescreen, class-aware SEQ cap, time to verdict, job links, label
    ("candidates", "class_requested", "ALTER TABLE candidates ADD COLUMN class_requested TEXT"),
    ("candidates", "prescreened", "ALTER TABLE candidates ADD COLUMN prescreened INTEGER NOT NULL DEFAULT 0"),
    ("candidates", "seq_cap_min", "ALTER TABLE candidates ADD COLUMN seq_cap_min INTEGER"),
    ("candidates", "time_to_verdict_s", "ALTER TABLE candidates ADD COLUMN time_to_verdict_s REAL"),
    ("candidates", "eq_job_id", "ALTER TABLE candidates ADD COLUMN eq_job_id TEXT"),
    ("candidates", "e4_job_id", "ALTER TABLE candidates ADD COLUMN e4_job_id TEXT"),
    ("candidates", "verdict", "ALTER TABLE candidates ADD COLUMN verdict TEXT"),
    ("candidates", "label", "ALTER TABLE candidates ADD COLUMN label TEXT"),
    ("candidates", "note", "ALTER TABLE candidates ADD COLUMN note TEXT"),
    ("candidates", "call_id", "ALTER TABLE candidates ADD COLUMN call_id TEXT"),
    ("candidates", "content_hash", "ALTER TABLE candidates ADD COLUMN content_hash TEXT"),   # unsalted RTL hash (cand_id is per run since 2026-09-14)
    ("diagnoses", "offset_design", "ALTER TABLE diagnoses ADD COLUMN offset_design INTEGER"),
    ("diagnoses", "duplicate_of", "ALTER TABLE diagnoses ADD COLUMN duplicate_of TEXT"),
    ("diagnoses", "envelope_json", "ALTER TABLE diagnoses ADD COLUMN envelope_json TEXT"),
    ("diagnoses", "seq_audit", "ALTER TABLE diagnoses ADD COLUMN seq_audit INTEGER"),
    ("diagnoses", "seq_audit_result", "ALTER TABLE diagnoses ADD COLUMN seq_audit_result TEXT"),
    ("diagnoses", "credited_class", "ALTER TABLE diagnoses ADD COLUMN credited_class TEXT"),
    ("diagnoses", "run_id", "ALTER TABLE diagnoses ADD COLUMN run_id TEXT"),
    ("runs", "budget_llm_calls", "ALTER TABLE runs ADD COLUMN budget_llm_calls INTEGER"),
    ("gen_summary", "pending_json", "ALTER TABLE gen_summary ADD COLUMN pending_json TEXT"),
    ("gen_summary", "built_at", "ALTER TABLE gen_summary ADD COLUMN built_at TEXT"),
    ("gen_summary", "llm_calls_cum", "ALTER TABLE gen_summary ADD COLUMN llm_calls_cum INTEGER"),
    # floor versioning (DECISIONS 2026-09-14, G4.3): the floor table is frozen per phase and stamped on runs and diagnoses
    ("noise_floor", "floor_version", "ALTER TABLE noise_floor ADD COLUMN floor_version TEXT"),
    ("runs", "floor_version", "ALTER TABLE runs ADD COLUMN floor_version TEXT"),
    ("diagnoses", "floor_version", "ALTER TABLE diagnoses ADD COLUMN floor_version TEXT"),
    # M6 rules version 2 (DECISIONS 2026-09-14, pre-Phase-4 task a): the rules-v1 class is kept, the features archived
    ("candidates", "class_rule_v1", "ALTER TABLE candidates ADD COLUMN class_rule_v1 TEXT"),
    ("candidates", "rules_version", "ALTER TABLE candidates ADD COLUMN rules_version INTEGER"),
    ("candidates", "features_json", "ALTER TABLE candidates ADD COLUMN features_json TEXT"),
]

REBUILDS = [  # tables whose CHECK constraint was widened after they existed: (table, needle that the current DDL must contain)
    ("perturbations", ("P0_roundtrip", "P1_text")),
    ("diagnoses", ("absorbed_identical", "fragile", "prescreened")),
]


def _table_ddl(name):
    """The CREATE TABLE statement of one table from schema.sql."""
    with open(SCHEMA) as f:
        m = re.search(rf"CREATE TABLE IF NOT EXISTS {name} \(.*?\);", f.read(), re.S)
    return m.group(0)


def _rebuild_if_check_old(conn, table, needles):
    """SQLite cannot alter a CHECK constraint: a table created with an older constraint (its DDL lacks one of `needles`)
    is rebuilt once from schema.sql — common columns copied, the old table dropped (2026-09-13 perturbations, 2026-09-14
    diagnoses)."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if not row or all(n in row[0] for n in needles):
        return False
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if all(n in row[0] for n in needles):  # another connection rebuilt it while we waited for the lock
            conn.execute("COMMIT")
            return False
        old_cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        conn.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
        conn.execute(_table_ddl(table))
        new_cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        cols = [c for c in old_cols if c in new_cols]
        conn.execute(f"INSERT INTO {table} ({', '.join(cols)}) SELECT {', '.join(cols)} FROM {table}_old")
        conn.execute(f"DROP TABLE {table}_old")
        conn.execute("COMMIT")
        return True
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _rebuild_perturbations_if_old(conn):
    return _rebuild_if_check_old(conn, "perturbations", ("P0_roundtrip", "P1_text"))


def init_schema(conn):
    for table, needles in REBUILDS:
        _rebuild_if_check_old(conn, table, needles)
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
