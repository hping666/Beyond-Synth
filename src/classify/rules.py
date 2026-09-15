"""Rewrite classifier M6, rule part (docs/spec/04-classifier-diagnoser.md §A), rules version 2 (DECISIONS 2026-09-14,
pre-Phase-4 task a). Features come from tools, not from reading the RTL by hand: the word-level RTLIL statistics of
D and C from Yosys after `proc; flatten; opt` (src/designs/yosys_probe.rtl_stats: cell histogram, flip-flop bits and
cells, longest combinational path), register names and the assignment targets of clocked always blocks from the
comment-stripped text (src/designs/verilog.py), the lock-step latency offsets from the equivalence record, and a
token-level diff ratio.

Decision order (`classify`): (c2) a lock-step offset; (d) only with operator-set or dataflow-topology evidence — an
operator family (multiply / divide, add / subtract, variable shift) present in C but absent in D, or the
longest combinational path changed by the configured factor; (a) when the registers and clocked targets are
unchanged; (c1) when the flip-flop bits and the number of register cells change with the same latency; else (b).
The text diff ratio no longer decides (d): a wide rewrite without such evidence keeps its structural class and is
flagged for review. Thresholds and the operator families live in config `classify` (rule 11). The LLM review
(§A.2 step 2) is a separate module; every decision records the rules that fired and a confidence."""
import difflib
import re

from src.designs import verilog as V
from src.designs import yosys_probe as YP

RULES_VERSION = 2
CLASSES = ("a", "b", "c1", "c2", "d")
DEFAULTS = {"d_diff_min": 0.5, "review_below": 0.7, "d_depth_ratio": 3.0,
            "operator_families": {"mul": ["$mul", "$div", "$mod", "$divfloor", "$modfloor", "$pow", "$macc"],
                                  "add": ["$add", "$sub", "$neg", "$alu"],
                                  "shift": ["$shl", "$shr", "$sshl", "$sshr", "$shift", "$shiftx"]}}   # no memory family: Yosys turns small arrays into registers by indexing style
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z_0-9$]*|\d+'[bBoOdDhH][0-9a-fA-F_xXzZ]+|\d+|[^\sA-Za-z_0-9]")
_REG = re.compile(r"\breg\b[^;]*?\b([A-Za-z_][A-Za-z_0-9$]*(?:\s*,\s*[A-Za-z_][A-Za-z_0-9$]*)*)\s*(?:\[[^\]]*\]\s*)*;")
_SEQ_BLOCK = re.compile(r"always\s*@\s*\(\s*(?:posedge|negedge)\b.*?\)(.*?)(?=\balways\b|\bendmodule\b|\bassign\b|\binitial\b)", re.S)
_FOR_HEAD = re.compile(r"\bfor\s*\([^)]*\)")
_TARGET = re.compile(r"\b([A-Za-z_][A-Za-z_0-9$]*)\s*(?:\[[^\]]*\]\s*)?(?:<=|=(?!=))")
_CMP_BEFORE = re.compile(r"(?:\bif\b|\bwhile\b|\?|&&|\|\||\(|!)\s*$")


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
    """Names assigned inside clocked always blocks, blocking (`=`) and nonblocking (`<=`) alike, without the control
    variables of `for` headers; a `<=` that follows `if (` / `&&` / `?` is a comparison, not an assignment."""
    s = V.strip_comments(text)
    targets = set()
    for m in _SEQ_BLOCK.finditer(s):
        body = _FOR_HEAD.sub("", m.group(1))
        for t in _TARGET.finditer(body):
            if _CMP_BEFORE.search(body[:t.start()]):
                continue
            targets.add(t.group(1))
    return targets


def families_present(cells, families):
    """Operator families (config `classify.operator_families`) with at least one cell in the RTLIL histogram."""
    return sorted(name for name, types in families.items() if any(cells.get(t, 0) > 0 for t in types))


def d_statistics(d_files, top, cfg, *, sverilog=False, incdirs=None, workdir=None):
    """D's word-level statistics, computed once per run and passed to `features` as `d_stats` (2026-09-15: the per-candidate
    copy of D's Yosys JSON was 9.5 GB of results/candidates)."""
    return YP.rtl_stats(d_files, top, cfg, sverilog=sverilog, incdirs=incdirs, workdir=workdir)


def features(d_files, c_files, top, cfg, *, sverilog=False, incdirs=None, workdir=None, offsets=None, c_top=None, d_stats=None):
    d_text = "\n".join(open(f, errors="replace").read() for f in d_files)
    c_text = "\n".join(open(f, errors="replace").read() for f in c_files)
    fams = (cfg.get("classify") or {}).get("operator_families") or DEFAULTS["operator_families"]
    sd = d_stats or YP.rtl_stats(d_files, top, cfg, sverilog=sverilog, incdirs=incdirs, workdir=(workdir / "d") if workdir else None)
    sc = YP.rtl_stats(c_files, c_top or top, cfg, sverilog=sverilog, incdirs=incdirs, workdir=(workdir / "c") if workdir else None)
    return {"rules_version": RULES_VERSION,
            "ff_d": sd["n_ff_bits"], "ff_c": sc["n_ff_bits"], "ff_cells_d": sd["n_ff_cells"], "ff_cells_c": sc["n_ff_cells"],
            "cells_d": sd["n_cells"], "cells_c": sc["n_cells"], "depth_d": sd["depth"], "depth_c": sc["depth"],
            "ops_d": families_present(sd["cells"], fams), "ops_c": families_present(sc["cells"], fams),
            "hist_d": sd["cells"], "hist_c": sc["cells"],
            "regs_d": sorted(register_names(d_text)), "regs_c": sorted(register_names(c_text)),
            "targets_d": sorted(seq_targets(d_text)), "targets_c": sorted(seq_targets(c_text)),
            "diff_ratio": round(diff_ratio(d_text, c_text), 4),
            "max_offset": max([int(v) for v in (offsets or {}).values()] or [0])}


def depth_ratio(feat):
    a, b = int(feat.get("depth_d") or 0), int(feat.get("depth_c") or 0)
    if a == 0 and b == 0:
        return 1.0
    return max(a, b) / max(1, min(a, b))


def classify(feat, cfg=None, **overrides):
    """-> dict(class_rule, rules, confidence, needs_review, rules_version). Thresholds from config `classify`
    (d_diff_min, review_below, d_depth_ratio); keyword overrides exist for tests."""
    p = dict(DEFAULTS)
    p.update((cfg or {}).get("classify") or {})
    p.update(overrides)
    rules = []
    same_regs = feat["regs_d"] == feat["regs_c"] and feat["targets_d"] == feat["targets_c"]
    same_ff = feat["ff_d"] == feat["ff_c"]
    wide = feat["diff_ratio"] >= float(p["d_diff_min"])
    if feat["max_offset"] > 0:
        rules.append(f"lock-step offset {feat['max_offset']} > 0")
        return {"class_rule": "c2", "rules": rules, "confidence": 0.95, "needs_review": False, "rules_version": RULES_VERSION}
    gained = sorted(set(feat.get("ops_c") or []) - set(feat.get("ops_d") or []))
    ratio = depth_ratio(feat)
    if gained:
        rules.append(f"operator family gained: {', '.join(gained)} (present in C, absent in D)")
    if ratio >= float(p["d_depth_ratio"]):
        rules.append(f"longest combinational path {feat.get('depth_d')} -> {feat.get('depth_c')} cells (ratio {ratio:.1f} >= {p['d_depth_ratio']})")
    if gained or ratio >= float(p["d_depth_ratio"]):
        conf = 0.9 if (gained and ratio >= float(p["d_depth_ratio"])) else 0.8
        return {"class_rule": "d", "rules": rules, "confidence": conf, "needs_review": conf < float(p["review_below"]), "rules_version": RULES_VERSION}
    if same_ff and same_regs:
        rules.append("flip-flop bits, register names and clocked targets unchanged")
        conf = 0.85 if not wide else 0.6
        if wide:
            rules.append(f"text differs widely (ratio {feat['diff_ratio']}) without operator or topology evidence -> review")
        return {"class_rule": "a", "rules": rules, "confidence": conf, "needs_review": conf < float(p["review_below"]), "rules_version": RULES_VERSION}
    if not same_ff and feat.get("ff_cells_d") != feat.get("ff_cells_c"):
        rules.append(f"flip-flop bits {feat['ff_d']} -> {feat['ff_c']} and register cells {feat.get('ff_cells_d')} -> {feat.get('ff_cells_c')} with identical latency (no offset)")
        conf = 0.6 if wide else 0.7
        if wide:
            rules.append(f"text differs widely (ratio {feat['diff_ratio']}) without operator or topology evidence -> review")
        return {"class_rule": "c1", "rules": rules, "confidence": conf, "needs_review": conf < float(p["review_below"]), "rules_version": RULES_VERSION}
    if not same_ff:
        rules.append(f"flip-flop bits {feat['ff_d']} -> {feat['ff_c']} in the same register cells (widths), latency unchanged")
    else:
        rules.append("register names or clocked targets changed, flip-flop count and latency unchanged")
    conf = 0.6 if wide else 0.7
    if wide:
        rules.append(f"text differs widely (ratio {feat['diff_ratio']}) without operator or topology evidence -> review")
    return {"class_rule": "b", "rules": rules, "confidence": conf, "needs_review": conf < float(p["review_below"]), "rules_version": RULES_VERSION}
