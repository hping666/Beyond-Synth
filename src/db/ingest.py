"""The only writer of results.sqlite.evaluations (docs/spec/07-results-db.md, spec 01 §6).

ingest_evaluation() accepts a meta.json record produced by src/eval/service.py and refuses anything that has not
passed the bidirectional checks: the raw directory must exist, its meta.json must carry status ok (or eval_failed
for a run that failed twice and is recorded as such), and every checklist item must be true for ok records.
"""
import json
from pathlib import Path

from src.db import core as db


class IngestError(ValueError):
    pass


def ingest_evaluation(conn, meta):
    raw_dir = Path(meta["raw_dir"])
    mpath = raw_dir / "meta.json"
    if not mpath.exists():
        raise IngestError(f"{raw_dir}: meta.json missing")
    on_disk = json.loads(mpath.read_text())
    status = on_disk.get("status")
    if status not in ("ok", "eval_failed"):
        raise IngestError(f"{raw_dir}: status {status!r} may not be ingested (only ok / eval_failed)")
    if status != meta.get("status"):
        raise IngestError(f"{raw_dir}: status on disk {status!r} differs from the record {meta.get('status')!r}")
    checks = on_disk.get("checks") or {}
    if status == "ok" and (not checks or not all(checks.values())):
        raise IngestError(f"{raw_dir}: checklist not all true: {checks}")
    m = on_disk.get("metrics") or {}
    row = {
        "design_id": meta["design_id"], "cand_id": meta.get("cand_id"), "pert_id": meta.get("pert_id"),
        "is_baseline": int(meta.get("is_baseline") or 0), "config": meta["config"], "lib": on_disk.get("lib"),
        "clock_ns": on_disk.get("clock_ns"),
        "area_um2": m.get("area"), "cells": m.get("cells"), "wns_ns": m.get("wns_ns"), "tns_ns": m.get("tns_ns"),
        "crit_delay_ns": m.get("crit_delay_ns"), "power_saif_mw": m.get("power_saif_mw"),
        "power_default_mw": m.get("power_default_mw"), "saif_coverage": m.get("saif_coverage"),
        "power_confidence": on_disk.get("power_confidence"),
        "hist_json": json.dumps(on_disk.get("hist") or {}, sort_keys=True),
        "log_summary_json": json.dumps({"log": on_disk.get("log_summary"), "icg_count": m.get("icg_count"),
                                        "registers": m.get("registers"), "datapath_blocks": (on_disk.get("resources") or {}).get("datapath_blocks"),
                                        "shared_resources": (on_disk.get("resources") or {}).get("shared_resources")}, sort_keys=True),
        "resources_json": json.dumps(on_disk.get("resources") or {}, sort_keys=True),
        "crit_path_json": json.dumps({"critical": on_disk.get("crit_path"), "endpoints": on_disk.get("path_endpoints")}, sort_keys=True),
        "dc_seconds": on_disk.get("dc_seconds"), "tool_version": on_disk.get("tool_version"),
        "status": status, "raw_dir": str(raw_dir),
    }
    return db.insert(conn, "evaluations", row)
