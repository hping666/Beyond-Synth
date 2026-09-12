"""Bidirectional tests of the small operational scripts: the hidden report refuses to run without the Phase 5
marker, db_check flags a missing raw directory and a status mismatch, snapshot copies every row."""
import importlib.util
import json
from pathlib import Path

from src import config as C
from src.db import core as db


def load(name):
    spec = importlib.util.spec_from_file_location(name, str(Path(C.ROOT) / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_hidden_report_needs_the_completion_marker(tmp_path):
    mod = load("report_hidden")
    status = tmp_path / "STATUS.md"
    status.write_text("# status\nPHASE5_COMPLETE: no\n")
    assert not mod.phase5_complete(status) and mod.main(["--status-file", str(status)]) == 3
    assert mod.main(["--check", "--status-file", str(status)]) == 0
    status.write_text("# status\nPHASE5_COMPLETE: yes\n")
    assert mod.phase5_complete(status) and mod.main(["--status-file", str(status)]) == 4  # marker present, report not implemented yet
    assert not mod.phase5_complete(tmp_path / "missing.md")


def test_db_check_flags_missing_raw_dirs_and_status_mismatch(tmp_path):
    mod = load("db_check")
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    good = tmp_path / "raw" / "d1" / "E4" / "h1"
    good.mkdir(parents=True)
    (good / "meta.json").write_text(json.dumps({"status": "ok"}))
    bad = tmp_path / "raw" / "d1" / "E4" / "h2"
    bad.mkdir(parents=True)
    (bad / "meta.json").write_text(json.dumps({"status": "failed"}))
    for raw in (good, bad, tmp_path / "raw" / "d1" / "E4" / "nowhere"):
        db.insert(conn, "evaluations", {"design_id": "d1", "config": "E4", "status": "ok", "raw_dir": str(raw), "is_baseline": 1})
    (tmp_path / "p.v").write_text("module d1; endmodule")
    db.insert(conn, "perturbations", {"pert_id": "p1", "design_id": "d1", "ptype": "P1_rename", "path": str(tmp_path / "p.v"), "seq_status": "proven"})
    db.insert(conn, "perturbations", {"pert_id": "p2", "design_id": "d1", "ptype": "P1_rename", "path": str(tmp_path / "gone.v"), "seq_status": "proven"})
    conn.execute("INSERT INTO designs (design_id, suite, name, path, loc, tb_available, e4_synthesizable, split, created_at, git_sha, cfg_hash) "
                 "VALUES ('d1','s','d1','x',1,0,1,'dev','t','g','c')")
    problems, warnings, counts = mod.check(conn, root=tmp_path)
    assert counts == {"evaluations": 3, "perturbations": 2, "designs": 1, "jobs_failed": 0, "jobs_active": 0}
    assert len(problems) == 3 and any("nowhere" in p for p in problems) and any("failed on disk" in p for p in problems) and any("gone.v" in p for p in problems)
    assert warnings == ["design d1 (dev): no Phi_main(nangate45) yet"]


def test_snapshot_copies_every_row(tmp_path):
    mod = load("snapshot")
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    for i in range(5):
        db.insert(conn, "evaluations", {"design_id": f"d{i}", "config": "E4", "status": "ok", "raw_dir": f"/x/{i}", "is_baseline": 1})
    dst = mod.snapshot(tmp_path / "r.sqlite", tmp_path / "snaps", tag="test")
    import sqlite3
    assert dst.name.startswith("results_") and dst.name.endswith("_test.sqlite")
    assert sqlite3.connect(str(dst)).execute("SELECT COUNT(*) FROM evaluations").fetchone()[0] == 5
