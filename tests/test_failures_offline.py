"""Bidirectional tests of src/eval/failures.py (2026-09-15): a pair whose latest record failed with a status the tool
cannot change on a re-run (DC analyze / elaborate / link, a non-structural Yosys netlist) is a deterministic failure;
a license failure, a timeout, a meta.json without a status, an unreadable record, a record at another clock or a later
ok record are not."""
import json

from src.db import core as db
from src.eval import failures as F


def test_deterministic_failure_both_directions(tmp_path):
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    n = [0]

    def ev(cid, config, status, failed_status="-", clock=1.0, meta=True):
        n[0] += 1
        raw = tmp_path / f"raw{n[0]}"
        raw.mkdir()
        if status != "ok" and meta:
            body = {"status": "eval_failed"} if failed_status == "-" else {"status": "eval_failed", "failed_status": failed_status}
            (raw / "meta.json").write_text(json.dumps(body))
        db.insert(conn, "evaluations", {"design_id": "d", "cand_id": cid, "config": config, "lib": "nangate45", "clock_ns": clock, "status": status, "raw_dir": str(raw), "created_at": "t"})
    ev("a", "E1", "eval_failed", "analyze_failed")
    assert F.deterministic_failure(conn, "a", "E1", 1.0) is True
    assert F.deterministic_failure(conn, "a", "E1", 2.0) is False          # another clock: no record there
    assert F.deterministic_failure(conn, "a", "E4", 1.0) is False          # no record
    assert F.deterministic_failure(conn, "a", "E1", 1.0, design_id="other") is False
    for st in ("elaborate_failed", "link_failed", "netlist_not_structural"):
        ev("b_" + st, "E1", "eval_failed", st)
        assert F.deterministic_failure(conn, "b_" + st, "E1", 1.0) is True
    for st in ("license_failed", "timeout", "dc_crashed"):
        ev("c_" + st, "E1", "eval_failed", st)
        assert F.deterministic_failure(conn, "c_" + st, "E1", 1.0) is False
    ev("e", "E1", "eval_failed")                                            # meta.json without failed_status
    assert F.deterministic_failure(conn, "e", "E1", 1.0) is False
    ev("f", "E1", "eval_failed", "analyze_failed", meta=False)             # no meta.json at all
    assert F.deterministic_failure(conn, "f", "E1", 1.0) is False
    ev("g", "E1", "eval_failed", "analyze_failed")
    ev("g", "E1", "ok")                                                     # a later ok record wins
    assert F.deterministic_failure(conn, "g", "E1", 1.0) is False
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "meta.json").write_text("{not json")
    assert F.failed_status_of(str(tmp_path / "bad")) is None and F.failed_status_of(None) is None
    assert F.failed_status_of(str(tmp_path / "raw1")) == "analyze_failed"
