"""Transparent reading of text files that may have been gzip-compressed in place (DECISION 2026-09-18 (b) item 2: DC logs of
ingested E4 records are stored as <name>.gz with their sha256 and original size in meta.json). `open_text(path)` opens `path`,
or `path + ".gz"` when only that exists, as text; `exists_text(path)` says whether either form is there."""
import gzip
import io
import os


def _gz(path):
    p = str(path)
    return p if p.endswith(".gz") else p + ".gz"


def exists_text(path):
    return os.path.exists(str(path)) or os.path.exists(_gz(path))


def open_text(path, errors="replace"):
    p = str(path)
    if os.path.exists(p) and not p.endswith(".gz"):
        return open(p, "r", errors=errors)
    g = _gz(path)
    if os.path.exists(g):
        return io.TextIOWrapper(gzip.open(g, "rb"), errors=errors)
    return open(p, "r", errors=errors)   # raises the usual FileNotFoundError


def read_text(path, errors="replace"):
    with open_text(path, errors=errors) as f:
        return f.read()
