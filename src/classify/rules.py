"""Rewrite classifier M6, rule part (docs/spec/04-classifier-diagnoser.md §A). Features come from tools, not from
reading the RTL by hand: flip-flop bits from the Yosys probe (src/designs/yosys_probe.py), register names and the
assignment targets of clocked always blocks from the comment-stripped text (src/designs/verilog.py), the
lock-step latency offsets from the equivalence record, and a token-level diff ratio. The LLM review (§A.2 step 2)
is a separate module; here every decision records the rules that fired and a confidence for the review threshold."""
import difflib
import re

from src.designs import verilog as V
from src.designs import yosys_probe as YP

CLASSES = ("a", "b", "c1", "c2", "d")
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z_0-9$]*|\d+'[bBoOdDhH][0-9a-fA-F_xXzZ]+|\d+|[^\sA-Za-z_0-9]")
_REG = re.compile(r"\breg\b[^;]*?\b([A-Za-z_][A-Za-z_0-9$]*(?:\s*,\s*[A-Za-z_][A-Za-z_0-9$]*)*)\s*(?:\[[^\]]*\]\s*)*;")
_SEQ_BLOCK = re.compile(r"always\s*@\s*\(\s*(?:posedge|negedge)\b.*?\)(.*?)(?=\balways\b|\bendmodule\b|\bassign\b|\binitial\b)", re.S)
_NB_TARGET = re.compile(r"\b([A-Za-z_][A-Za-z_0-9$]*)\s*(?:\[[^\]]*\]\s*)?<=")


def tokens(text):
    return _TOKEN.findall(V.strip_comments(text))


def diff_ratio(d_text, c_text):
    """1 - similarity of the token streams (0 = identical, 1 = nothing in common)."""
    a, b = tokens(d_text), tokens(c_text)
    if not a and not b:
        return 0.0
    return 1.0 - difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def register_names(text):
    s = V.strip_comments(text)
    names = set()
    for m in _REG.finditer(s):
        for n in m.group(1).split(","):
            names.add(n.strip())
    return names


def seq_targets(text):
    s = V.strip_comments(text)
    targets = set()
    for m in _SEQ_BLOCK.finditer(s):
        targets.update(_NB_TARGET.findall(m.group(1)))
    return targets


def features(d_files, c_files, top, cfg, *, sverilog=False, incdirs=None, workdir=None, offsets=None, c_top=None):
    d_text = "\n".join(open(f, errors="replace").read() for f in d_files)
    c_text = "\n".join(open(f, errors="replace").read() for f in c_files)
    fd = YP.probe(d_files, top, cfg, sverilog=sverilog, incdirs=incdirs, workdir=(workdir / "d") if workdir else None)
    fc = YP.probe(c_files, c_top or top, cfg, sverilog=sverilog, incdirs=incdirs, workdir=(workdir / "c") if workdir else None)
    return {"ff_d": fd["n_ff_bits"], "ff_c": fc["n_ff_bits"], "cells_d": fd["n_cells"], "cells_c": fc["n_cells"],
            "regs_d": sorted(register_names(d_text)), "regs_c": sorted(register_names(c_text)),
            "targets_d": sorted(seq_targets(d_text)), "targets_c": sorted(seq_targets(c_text)),
            "diff_ratio": round(diff_ratio(d_text, c_text), 4),
            "max_offset": max([int(v) for v in (offsets or {}).values()] or [0])}


def classify(feat, *, d_diff_min=0.5, review_below=0.7):
    """-> dict(class_rule, rules, confidence, needs_review). Order: (c2) by offsets; (a) when the sequential
    structure is untouched; (d) when the text differs widely; (c1) when the register count changes; else (b)."""
    rules = []
    same_regs = feat["regs_d"] == feat["regs_c"] and feat["targets_d"] == feat["targets_c"]
    same_ff = feat["ff_d"] == feat["ff_c"]
    if feat["max_offset"] > 0:
        rules.append(f"lock-step offset {feat['max_offset']} > 0")
        return {"class_rule": "c2", "rules": rules, "confidence": 0.95, "needs_review": False}
    if same_ff and same_regs:
        rules.append("flip-flop count, register names and clocked targets unchanged")
        conf = 0.85 if feat["diff_ratio"] < d_diff_min else 0.6
        if feat["diff_ratio"] >= d_diff_min:
            rules.append(f"but the text differs widely (ratio {feat['diff_ratio']}) -> review for (d)")
        return {"class_rule": "a", "rules": rules, "confidence": conf, "needs_review": conf < review_below}
    if feat["diff_ratio"] >= d_diff_min:
        rules.append(f"sequential structure changed and the text differs widely (ratio {feat['diff_ratio']})")
        return {"class_rule": "d", "rules": rules, "confidence": 0.6, "needs_review": True}
    if not same_ff:
        rules.append(f"flip-flop bits {feat['ff_d']} -> {feat['ff_c']} with identical latency (no offset)")
        return {"class_rule": "c1", "rules": rules, "confidence": 0.5, "needs_review": True}
    rules.append("register names or clocked targets changed, flip-flop count and latency unchanged")
    return {"class_rule": "b", "rules": rules, "confidence": 0.7, "needs_review": 0.7 < review_below}
