#!/usr/bin/env python3
"""DC-log compression (DECISION 2026-09-18 (b) item 2): gzip the logs of E4 records that are ingested (an evaluations row with
status ok) and consistent (meta.json present with the same status; the same check scripts/db_check.py makes), when larger than
`--min-mb` (default 5). The sha256 and original size of every compressed log go into the record's meta.json (`log_gz`); nothing
is deleted before its .gz is written and verified. Readers use src/util_textio.open_text (transparent .gz).

    .venv/bin/python scripts/compress_logs.py --dry-run [--min-mb 5] [--limit N] [--design D]
    .venv/bin/python scripts/compress_logs.py --apply --limit 3        # the 3-log test
    .venv/bin/python scripts/compress_logs.py --apply                  # the batch"""
import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def candidates(conn, min_bytes, design=None, configs=("E4",)):
    q = "SELECT raw_dir, status FROM evaluations WHERE status='ok' AND config IN (%s)" % ",".join("?" * len(configs))
    args = list(configs)
    if design:
        q += " AND design_id=?"; args.append(design)
    for raw_dir, status in conn.execute(q, args):
        meta_path = Path(raw_dir) / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("status") != status:
            continue
        for log in sorted(Path(raw_dir).rglob("*.log")):
            if log.is_file() and log.stat().st_size >= min_bytes:
                yield raw_dir, meta_path, log


def compress_one(meta_path, log):
    if not log.exists():   # another instance (the offline pool's hourly run) compressed it meanwhile
        return None
    orig = log.stat().st_size
    digest = sha256(log)
    gz = Path(str(log) + ".gz")
    with open(log, "rb") as fin, gzip.open(gz, "wb", compresslevel=6) as fout:
        shutil.copyfileobj(fin, fout)
    with gzip.open(gz, "rb") as fin:   # verify before removing the original
        h = hashlib.sha256()
        for chunk in iter(lambda: fin.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != digest:
        gz.unlink()
        raise RuntimeError(f"{log}: gzip verification failed")
    meta = json.loads(meta_path.read_text())
    meta.setdefault("log_gz", {})[log.name] = {"sha256": digest, "bytes": orig, "gz_bytes": gz.stat().st_size}
    meta_path.write_text(json.dumps(meta, indent=1, sort_keys=True, default=str))
    log.unlink()
    return orig, gz.stat().st_size


def _lock():
    """One instance at a time (the offline pool runs this hourly; a manual run must not race it): a non-blocking flock on
    results/queue/compress_logs.lock, or None when another instance holds it."""
    import fcntl
    path = Path(__file__).resolve().parent.parent / "results" / "queue" / "compress_logs.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return None
    return fh


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-mb", type=float, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--design", default=None)
    a = ap.parse_args(argv)
    cfg = C.load()
    min_mb = a.min_mb if a.min_mb is not None else float((cfg.get("retention") or {}).get("gzip_logs_over_mb", 5))
    conn = db.connect(cfg=cfg)
    lock = _lock() if a.apply else True
    if lock is None:
        print(json.dumps({"logs": 0, "skipped": "another compress_logs instance holds the lock", "applied": False}))
        return 0
    n = 0; total = 0; saved = 0
    for raw_dir, meta_path, log in candidates(conn, int(min_mb * 1e6), a.design):
        if a.limit and n >= a.limit:
            break
        try:
            size = log.stat().st_size
        except OSError:   # compressed by another instance meanwhile
            continue
        n += 1; total += size
        if a.apply:
            res = compress_one(meta_path, log)
            if res is None:
                n -= 1; total -= size
                continue
            orig, gzb = res
            saved += orig - gzb
            print(f"compressed {log} {orig/1e6:.1f} MB -> {gzb/1e6:.1f} MB")
        else:
            print(f"would compress {log} ({size/1e6:.1f} MB)")
    print(json.dumps({"logs": n, "bytes": total, "saved_bytes": saved if a.apply else None, "min_mb": min_mb, "applied": bool(a.apply)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
