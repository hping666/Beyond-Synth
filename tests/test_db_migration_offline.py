"""The perturbations table created before 2026-09-13 (CHECK without P0_roundtrip) is rebuilt on connect: rows are
kept, P0_roundtrip is accepted afterwards, unknown types are still refused, and a second connect changes nothing."""
import sqlite3

from src.db import core as db

OLD = """CREATE TABLE perturbations (
  pert_id TEXT PRIMARY KEY,
  design_id TEXT NOT NULL, ptype TEXT NOT NULL CHECK (ptype IN ('P1_rename', 'P2_reorder', 'P3_expr', 'P4_ctrl')),
  path TEXT NOT NULL, seq_status TEXT,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);"""


def test_old_perturbations_table_is_rebuilt(tmp_path):
    path = str(tmp_path / "r.sqlite")
    raw = sqlite3.connect(path)
    raw.execute(OLD)
    raw.execute("INSERT INTO perturbations VALUES ('p1', 'd', 'P1_rename', 'x', 'proven', 't', 'g', 'c')")
    raw.commit()
    with __import__("pytest").raises(sqlite3.IntegrityError):
        raw.execute("INSERT INTO perturbations VALUES ('p0', 'd', 'P0_roundtrip', 'x', 'proven', 't', 'g', 'c')")
    raw.close()
    conn = db.connect(path=path)
    assert "P0_roundtrip" in conn.execute("SELECT sql FROM sqlite_master WHERE name='perturbations'").fetchone()[0]
    assert conn.execute("SELECT pert_id, ptype FROM perturbations").fetchall()[0][:] == ("p1", "P1_rename")
    db.insert(conn, "perturbations", {"pert_id": "p0", "design_id": "d", "ptype": "P0_roundtrip", "path": "x", "seq_status": "proven"})
    with __import__("pytest").raises(sqlite3.IntegrityError):
        db.insert(conn, "perturbations", {"pert_id": "p9", "design_id": "d", "ptype": "P9_none", "path": "x", "seq_status": "proven"})
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='perturbations_old'").fetchone() is None
    assert db._rebuild_perturbations_if_old(conn) is False  # idempotent
    assert conn.execute("SELECT COUNT(*) FROM perturbations").fetchone()[0] == 2


def test_scope_violation_label_and_repair_columns_are_migrated(tmp_path):
    """G5 item 1 (2026-09-15): an older database whose diagnoses CHECK lacks `scope_violation` is rebuilt on connect and accepts
    the label; the candidates table gains repair_of and scope_json; a second connect changes nothing."""
    path = str(tmp_path / "r.sqlite")
    conn = db.connect(path=path)
    old = conn.execute("SELECT sql FROM sqlite_master WHERE name='diagnoses'").fetchone()[0].replace(", 'scope_violation'", "")
    conn.execute("DROP TABLE diagnoses")
    conn.execute(old)
    conn.execute("ALTER TABLE candidates DROP COLUMN repair_of")
    conn.execute("ALTER TABLE candidates DROP COLUMN scope_json")
    conn.commit()
    with __import__("pytest").raises(sqlite3.IntegrityError):
        db.insert(conn, "diagnoses", {"cand_id": "c1", "label": "scope_violation", "credit": 0})
    conn.close()
    conn = db.connect(path=path)
    assert "scope_violation" in conn.execute("SELECT sql FROM sqlite_master WHERE name='diagnoses'").fetchone()[0]
    cols = {r[1] for r in conn.execute("PRAGMA table_info(candidates)")}
    assert {"repair_of", "scope_json"} <= cols
    db.insert(conn, "diagnoses", {"cand_id": "c1", "label": "scope_violation", "credit": 0})
    db.insert(conn, "candidates", {"cand_id": "c2", "design_id": "d", "repair_of": "c1", "scope_json": "{}"})
    assert conn.execute("SELECT repair_of FROM candidates WHERE cand_id='c2'").fetchone()[0] == "c1"
    with __import__("pytest").raises(sqlite3.IntegrityError):
        db.insert(conn, "diagnoses", {"cand_id": "c3", "label": "not_a_label", "credit": 0})


def test_runs_exp_check_is_widened_for_the_probe(tmp_path):
    """The runs table of an older database (exp CHECK without phase5_probe) is rebuilt on connect and accepts the probe experiment."""
    path = str(tmp_path / "r.sqlite")
    conn = db.connect(path=path)
    old = conn.execute("SELECT sql FROM sqlite_master WHERE name='runs'").fetchone()[0].replace(", 'phase5_probe'", "")
    conn.execute("DROP TABLE runs")
    conn.execute(old)
    db.insert(conn, "runs", {"run_id": "r1", "exp": "phase4", "arm": "B0", "design_id": "d", "seed": 1, "status": "done"})
    with __import__("pytest").raises(sqlite3.IntegrityError):
        db.insert(conn, "runs", {"run_id": "r2", "exp": "phase5_probe", "arm": "M", "design_id": "d", "seed": 1, "status": "created"})
    conn.close()
    conn = db.connect(path=path)
    db.insert(conn, "runs", {"run_id": "r2", "exp": "phase5_probe", "arm": "M", "design_id": "d", "seed": 1, "status": "created"})
    assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 2
    with __import__("pytest").raises(sqlite3.IntegrityError):
        db.insert(conn, "runs", {"run_id": "r3", "exp": "not_an_exp", "arm": "M", "design_id": "d", "seed": 1, "status": "created"})
