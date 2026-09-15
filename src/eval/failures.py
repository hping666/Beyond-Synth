"""Deterministic evaluation failures (2026-09-15): a synthesis run that the tool rejects because of the RTL itself
(DC analyze / elaborate / link errors, a Yosys netlist with behavioural constructs) cannot succeed on a re-run, so the
ladders skip such (object, configuration) pairs instead of re-submitting them at every pass (rule 8: the record stays
`evaluation failed`; `--retry-failed` forces a re-run). License seats, timeouts and tool crashes are not deterministic
and are re-submitted. The check reads the latest evaluation row of the pair and the `failed_status` of its meta.json."""
import json
from pathlib import Path

DETERMINISTIC_FAILURES = ("analyze_failed", "elaborate_failed", "link_failed", "netlist_not_structural")


def failed_status_of(raw_dir):
    """failed_status (or status) recorded in <raw_dir>/meta.json; None when unreadable."""
    mp = Path(raw_dir or "") / "meta.json"
    if not raw_dir or not mp.exists():
        return None
    try:
        meta = json.loads(mp.read_text())
    except ValueError:
        return None
    return meta.get("failed_status") or meta.get("status")


def deterministic_failure(conn, cand_id, config, clock_ns, design_id=None):
    """True when the latest evaluation record of the object under `config` (at that clock) failed with a status in
    DETERMINISTIC_FAILURES. False for ok records, no record, or a failure of another kind."""
    q = "SELECT status, raw_dir FROM evaluations WHERE cand_id=? AND config=? AND abs(clock_ns-?)<1e-6"
    args = [cand_id, config, float(clock_ns)]
    if design_id is not None:
        q += " AND design_id=?"
        args.append(design_id)
    r = conn.execute(q + " ORDER BY eval_id DESC LIMIT 1", args).fetchone()
    if r is None or r["status"] == "ok":
        return False
    return failed_status_of(r["raw_dir"]) in DETERMINISTIC_FAILURES
