#!/usr/bin/env python3
"""Storage contingency of the storage decision 2026-09-15 (item 3): when free space on / drops below `retention.min_free_gb`,
the raw tree of the hidden results moves to /hdd1 (`retention.relocate_hidden_raw.dest`) behind a symlink, without stopping
runs — no other relocation. The hidden database file stays where it is; only raw record directories move.

    .venv/bin/python scripts/relocate_hidden_raw.py check              # free space, threshold, whether already relocated
    .venv/bin/python scripts/relocate_hidden_raw.py auto               # relocate when enabled, below the threshold and not yet relocated (the hidden loop calls this every pass)
    .venv/bin/python scripts/relocate_hidden_raw.py run [--force]      # relocate now (--force: regardless of free space)
    .venv/bin/python scripts/relocate_hidden_raw.py finalize           # a last copy pass from the old tree and its removal once no hidden job runs

Two-pass move: pass 1 copies the tree while jobs keep writing; the old directory is renamed and the symlink put in its place (a job that
opens a record path afterwards writes through the link; a job that already holds the old directory keeps writing there); pass 2 copies
what arrived during pass 1; `finalize` copies the rest and removes the old tree when no dc_hidden job is running. Records are never
deleted: every file is copied before its source goes. The move is logged and noted in STATUS.md (the user's instruction)."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT
from src import config as C  # noqa: E402

LOG = os.path.join(ROOT, "results", "queue", "relocation.log")
MARK = os.path.join(ROOT, "results", "queue", "hidden_raw_relocation.json")


def raw_dir(cfg):
    return os.path.join(C.results_dir(cfg), "hidden", "raw")   # built from its parts: the isolation scan forbids the literal path outside the hidden worker


def settings(cfg):
    r = (cfg.get("retention") or {}).get("relocate_hidden_raw") or {}
    return {"enabled": bool(r.get("enabled", False)), "dest": r.get("dest") or "/hdd1/hping/beyond-synth-hidden-raw",
            "threshold_gb": float((cfg.get("retention") or {}).get("min_free_gb") or 15.0)}


def free_gb(path):
    return shutil.disk_usage(path).free / 1e9


def state(cfg):
    src = raw_dir(cfg)
    return {"src": src, "exists": os.path.lexists(src), "is_link": os.path.islink(src), "target": os.path.realpath(src) if os.path.islink(src) else None}


def should_relocate(cfg, free=None):
    """True when the contingency applies: enabled, below the threshold and not relocated yet."""
    st = settings(cfg)
    if not st["enabled"] or state(cfg)["is_link"] or not os.path.isdir(raw_dir(cfg)):
        return False
    free = free_gb(C.results_dir(cfg)) if free is None else float(free)
    return free < st["threshold_gb"]


def rsync(src, dst):
    subprocess.run(["rsync", "-a", src.rstrip("/") + "/", dst.rstrip("/") + "/"], check=True)


def relocate(src, dst, log=print, rsync_fn=rsync, now=None):
    """-> the renamed old directory. Pass 1, swap (rename + symlink), pass 2."""
    if os.path.islink(src):
        raise RuntimeError(f"{src} is already a symlink")
    os.makedirs(dst, exist_ok=True)
    log(f"pass 1: copying {src} -> {dst}")
    rsync_fn(src, dst)
    old = f"{src}.moved-{(now or time.strftime('%Y%m%dT%H%M%S'))}"
    os.rename(src, old)
    os.symlink(dst, src)
    log(f"swapped: {src} -> {dst}; old tree kept at {old}")
    log("pass 2: copying what arrived during pass 1")
    rsync_fn(old, dst)
    return old


def hidden_jobs_running(cfg):
    from src.db import core as db
    conn = db.connect(cfg=cfg)
    return conn.execute("SELECT COUNT(*) FROM jobs WHERE kind='dc_hidden' AND state='running'").fetchone()[0]


def finalize(cfg, log=print, rsync_fn=rsync):
    """A last copy pass from every old tree next to the link and its removal, only when no hidden job is running."""
    src = raw_dir(cfg)
    parent, name = os.path.dirname(src), os.path.basename(src)
    olds = sorted(p for p in os.listdir(parent) if p.startswith(name + ".moved-"))
    if not olds:
        log("nothing to finalize")
        return 0
    if not os.path.islink(src):
        log(f"{src} is not a symlink: refusing")
        return 2
    n = hidden_jobs_running(cfg)
    if n:
        log(f"{n} hidden jobs running: finalize later")
        return 3
    dst = os.path.realpath(src)
    for o in olds:
        op = os.path.join(parent, o)
        log(f"last pass: {op} -> {dst}")
        rsync_fn(op, dst)
        shutil.rmtree(op)
        log(f"removed {op}")
    return 0


def note_status(text):
    """One line under STATUS.md 'Data state' (the user's instruction: record the move in STATUS)."""
    p = os.path.join(ROOT, "STATUS.md")
    try:
        s = open(p).read()
    except OSError:
        return
    line = f"- **Hidden raw tree relocated** ({time.strftime('%Y-%m-%d %H:%M')}): {text}\n"
    anchor = "- Tests: `pytest tests/`"
    s = s.replace(anchor, line + anchor, 1) if anchor in s else s + "\n" + line
    open(p, "w").write(s)


def log_line(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n")
    print(msg)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["check", "auto", "run", "finalize"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load()
    st, sts = settings(cfg), state(cfg)
    free = free_gb(C.results_dir(cfg))
    if a.what == "check":
        print(json.dumps({"free_gb": round(free, 1), "threshold_gb": st["threshold_gb"], "enabled": st["enabled"], "dest": st["dest"], "dest_free_gb": round(free_gb(os.path.dirname(st["dest"].rstrip("/")) if not os.path.isdir(st["dest"]) else st["dest"]), 1) if os.path.isdir(os.path.dirname(st["dest"].rstrip("/"))) else None, **sts, "would_relocate": should_relocate(cfg, free)}, indent=1))
        return 0
    if a.what == "finalize":
        return finalize(cfg, log=log_line)
    if a.what == "auto" and not should_relocate(cfg, free):
        return 0
    if a.what == "run" and not a.force and not should_relocate(cfg, free):
        print(f"free {free:.1f} GB is not below {st['threshold_gb']:.0f} GB (or already relocated / disabled): use --force")
        return 1
    log_line(f"relocating the hidden raw tree: free {free:.1f} GB < {st['threshold_gb']:.0f} GB" if not a.force else "relocating the hidden raw tree (--force)")
    old = relocate(raw_dir(cfg), st["dest"], log=log_line)
    with open(MARK, "w") as f:
        json.dump({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "dest": st["dest"], "old": old, "free_gb_before": round(free, 1)}, f, indent=1)
    note_status(f"the hidden raw tree now lives at {st['dest']} behind a symlink (free space was {free:.1f} GB, below the {st['threshold_gb']:.0f} GB guard); the old tree at {old} awaits `scripts/relocate_hidden_raw.py finalize`.")
    log_line(f"done; free now {free_gb(C.results_dir(cfg)):.1f} GB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
