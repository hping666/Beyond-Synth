"""Candidate handling for LLM rewrites (docs/spec/05-search.md §7): parse the JSON answer, check that the rewrite
keeps the design's module name, and store the RTL under results/candidates/<run_id>/<cand_id>.v with a sidecar
JSON (note, model, call id). Candidate ids are content hashes of the RTL text."""
import hashlib
import json
import re
from pathlib import Path

from src import config as C
from src.designs import verilog as V

CAND_DIR = Path(C.ROOT) / "results" / "candidates"


class BadAnswer(ValueError):
    pass


def parse_answer(text):
    """-> (rtl, note) from the model's answer; tolerates a ```json fence around the object."""
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.S)
    start, end = s.find("{"), s.rfind("}")
    if start < 0 or end < 0:
        raise BadAnswer("no JSON object in the answer")
    try:
        obj = json.loads(s[start:end + 1])
    except json.JSONDecodeError as e:
        raise BadAnswer(f"JSON parse error: {e}")
    rtl = obj.get("rtl")
    if not isinstance(rtl, str) or "module" not in rtl:
        raise BadAnswer("answer carries no 'rtl' module text")
    return rtl.replace("\r\n", "\n"), str(obj.get("note") or "")


def check_top(rtl, top):
    names = V.module_names(rtl)
    if top not in names:
        raise BadAnswer(f"the rewrite does not declare module {top} (found {names})")
    return names


def cand_id_of(rtl):
    return "c" + hashlib.sha256(rtl.encode()).hexdigest()[:14]


def store(run_id, design, rtl, meta, root=None):
    """-> (cand_id, path); meta is written next to the RTL as <cand_id>.json."""
    d = Path(root or CAND_DIR) / run_id
    d.mkdir(parents=True, exist_ok=True)
    cid = cand_id_of(rtl)
    path = d / f"{cid}.v"
    path.write_text(rtl if rtl.endswith("\n") else rtl + "\n")
    (d / f"{cid}.json").write_text(json.dumps({"cand_id": cid, "design_id": design["design_id"], "top": design["top"], **meta}, indent=1, sort_keys=True, default=str) + "\n")
    return cid, path


def prompt_prefix(design, system_text):
    """Stable, cacheable prefix: the system text and the design's RTL (spec 05 §2)."""
    rtl = "\n\n".join(Path(design["_dir"], f).read_text(errors="replace") for f in design["files"])
    return f"{system_text.strip()}\n\nThe design to rewrite (top module `{design['top']}`):\n```verilog\n{rtl}\n```\n"
