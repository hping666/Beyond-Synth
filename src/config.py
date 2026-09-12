"""Configuration access. config/experiments.yaml is the single source of parameters (CLAUDE.md rule 11):
code reads it through load(); numbers are never hard-coded elsewhere. cfg_hash() and git_sha() stamp every
database record (docs/spec/07-results-db.md)."""
import functools
import hashlib
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config", "experiments.yaml")


def load(path=CONFIG_PATH):
    with open(path) as f:
        return yaml.safe_load(f)


@functools.lru_cache(maxsize=8)
def cfg_hash(path=CONFIG_PATH):
    """Short content hash of the configuration file actually in use."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


@functools.lru_cache(maxsize=1)
def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "nogit"


def results_dir(cfg=None):
    return (cfg or load())["project"]["results_dir"]


def is_tbd(value):
    return isinstance(value, str) and value.upper().startswith("TBD")
