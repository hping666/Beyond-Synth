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
