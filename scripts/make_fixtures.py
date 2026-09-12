#!/usr/bin/env python3
"""Copy the reference artifacts of the Phase 0.5 smoke design into tests/fixtures/<design_id>/<config>/
(docs/PLAN.md Phase 0 acceptance). For every configuration the latest ok raw directory is used; text reports,
meta.json and the inputs are copied, binaries (.ddc) are not. Re-generate after a tool-version change and
record it in docs/DECISIONS.md (spec 01 §7).

    .venv/bin/python scripts/make_fixtures.py [--design-id rtllm_accu] [--configs E1 ...]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = ROOT

import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
from pathlib import Path  # noqa: E402

from src import config as C  # noqa: E402

DEFAULT_CONFIGS = ["E1", "E2", "E3", "E4", "E2r", "E2t", "E2g", "H1", "H2a", "H2b", "H3", "H5", "Y", "H4"]
SKIP_SUFFIXES = (".ddc",)
MAX_BYTES = 400_000


def latest_ok(raw_root):
    best = None
    for meta in raw_root.glob("*/meta.json"):
        try:
            m = json.loads(meta.read_text())
        except json.JSONDecodeError:
            continue
        if m.get("status") != "ok":
            continue
        if best is None or m.get("finished_at", "") > best[0].get("finished_at", ""):
            best = (m, meta.parent)
    return best


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--design-id", default="rtllm_accu")
    ap.add_argument("--configs", nargs="+", default=DEFAULT_CONFIGS)
    a = ap.parse_args(argv)
    cfg = C.load()
    raw = Path(C.results_dir(cfg)) / "raw" / a.design_id
    fix = Path(ROOT) / "tests" / "fixtures" / a.design_id
    index = {}
    for name in a.configs:
        found = latest_ok(raw / name)
        if not found:
            print(f"{name}: no ok record under {raw / name}")
            continue
        meta, src = found
        dst = fix / name
        if dst.exists():
            shutil.rmtree(dst)  # fixtures are versioned in git, not results (append-only does not apply here)
        copied = 0
        for f in src.rglob("*"):
            if not f.is_file() or f.suffix in SKIP_SUFFIXES or f.stat().st_size > MAX_BYTES:
                continue
            if "dc_work" in f.parts or "mw_design" in f.parts:
                continue
            if f.name in ("dc_shell.log", "pt_shell.log") and name != "E4":
                continue  # full tool logs only for E4 (the log-summary test); the others would add ~100 KB each
            rel = f.relative_to(src)
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dst / rel)
            copied += 1
        index[name] = {"raw_dir": str(src), "finished_at": meta.get("finished_at"), "git_sha": meta.get("git_sha"),
                       "tool_version": meta.get("tool_version"), "files": copied,
                       "metrics": {k: v for k, v in (meta.get("metrics") or {}).items() if v is not None}}
        print(f"{name}: {copied} files from {src}")
    (fix / "INDEX.json").write_text(json.dumps({"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                                                "design_id": a.design_id, "configs": index}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
