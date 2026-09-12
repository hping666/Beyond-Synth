"""Staged design catalogue: data/designs/<suite>/<name>/design.json (+ rtl/, tb/, reference/, samples/ copies).

design.json (the metadata is versioned in git; the copies are rebuilt from the pinned sources by
scripts/stage_designs.py and are gitignored because the upstream licenses differ):
  design_id  = <suite>_<name>        top        module name synthesized / simulated
  files      RTL paths relative to the design directory (order as read by the tools)
  clk_ports  every clock input (0 = combinational, >1 = tag multi_clock)     rst_port / rst_sense (low | high | null)
  sverilog   read as SystemVerilog   incdirs    `include search directories (relative)
  tb         {files, top, data} or null         reference  {files, top, note} or null (expert version of a pair)
  samples    [{files, top, role}] rewrite samples of a pair set (calibration only)
  source     {suite_key, url, commit, commit_verified, license, paths, note}
  sha256     per staged file          loc       lines over `files`        tags / notes   free lists
  inventory  filled by src/designs/inventory.py (Yosys ports, flags, hash) after staging
"""
import hashlib
import json
from pathlib import Path

from src import config as C
from src.designs import verilog as V

DESIGNS_DIR = Path(C.ROOT) / "data" / "designs"
REQUIRED = ("design_id", "suite", "name", "top", "files", "clk_ports", "rst_port", "rst_sense", "sverilog", "incdirs",
            "tb", "reference", "source", "sha256", "loc", "tags", "notes")


class CatalogError(ValueError):
    pass


def design_id_for(suite, name):
    return f"{suite}_{name}"


def design_dir(suite, name):
    return DESIGNS_DIR / suite / name


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def abs_paths(d, rels):
    base = Path(d["_dir"])
    return [base / r for r in (rels or [])]


def hashed_files(d):
    """Every staged file that carries a hash: RTL, testbench, reference, samples."""
    rels = list(d["files"]) + list(d.get("includes") or [])
    if d.get("tb"):
        rels += list(d["tb"].get("files") or []) + list(d["tb"].get("data") or [])
    if d.get("reference"):
        rels += list(d["reference"].get("files") or [])
    for s in d.get("samples") or []:
        rels += list(s.get("files") or [])
    return rels


def validate(d, check_files=True):
    missing = [k for k in REQUIRED if k not in d]
    if missing:
        raise CatalogError(f"{d.get('design_id')}: missing keys {missing}")
    if d["design_id"] != design_id_for(d["suite"], d["name"]):
        raise CatalogError(f"{d['design_id']}: design_id must be <suite>_<name> ({d['suite']}_{d['name']})")
    if not d["files"]:
        raise CatalogError(f"{d['design_id']}: no RTL files")
    if not isinstance(d["clk_ports"], list):
        raise CatalogError(f"{d['design_id']}: clk_ports must be a list")
    if d["rst_sense"] not in (None, "low", "high"):
        raise CatalogError(f"{d['design_id']}: rst_sense must be low / high / null")
    if check_files:
        base = Path(d["_dir"])
        for rel in hashed_files(d):
            p = base / rel
            if not p.is_file():
                raise CatalogError(f"{d['design_id']}: staged file missing: {rel}")
            if d["sha256"].get(rel) != sha256_of(p):
                raise CatalogError(f"{d['design_id']}: sha256 mismatch for {rel} (re-stage from the pinned source)")
        declared = set()
        for p in abs_paths(d, d["files"]):
            declared.update(V.module_names(p.read_text(errors="replace")))
        if d["top"] not in declared:
            raise CatalogError(f"{d['design_id']}: top module {d['top']} is not declared in {d['files']}")
    return True


def write_design(d):
    """Validate and write design.json into the design directory (d['_dir'] or the canonical directory)."""
    d = dict(d)
    ddir = Path(d.get("_dir") or design_dir(d["suite"], d["name"]))
    ddir.mkdir(parents=True, exist_ok=True)
    d["_dir"] = str(ddir)
    validate(d)
    out = {k: v for k, v in d.items() if not k.startswith("_")}
    (ddir / "design.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return d


def load_design(path):
    """path: a design directory, its design.json, or a design_id (looked up under data/designs)."""
    p = Path(path)
    if not p.exists() and "_" in str(path):
        suite, name = str(path).split("_", 1)
        p = design_dir(suite, name)
    if p.is_dir():
        p = p / "design.json"
    d = json.loads(p.read_text())
    d["_dir"] = str(p.parent)
    return d


def load_all(suite=None, root=None):
    root = Path(root) if root else DESIGNS_DIR
    out = []
    for p in sorted(root.glob("*/*/design.json")):
        d = load_design(p)
        if suite is None or d["suite"] == suite:
            out.append(d)
    return out
