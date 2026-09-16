"""Prompt assembly for residual-guided evolution (docs/spec/05-search.md §2): a stable, cacheable prefix per design
(system text, D's RTL, D's E4 summary — what the synthesizer already did —, the noise floor, the prior table) and a
variable suffix (parent RTL when the parent is not D, the lineage's feedback blocks, the class instruction).
Template files are versioned; changes are recorded in DECISIONS."""
import json
import re
from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"


def load_templates(caliber="E4"):
    """System prompt (the Y-caliber variant `search_system_y.md` for arm B0 names Yosys + OpenSTA as the measuring tool and
    drops the reference to the synthesizer's report), class instructions and the template version."""
    name = "search_system_y.md" if caliber == "Y" else "search_system.md"
    system = (PROMPT_DIR / name).read_text()
    classes = json.loads((PROMPT_DIR / "search_classes.json").read_text())
    version = classes.pop("version", 1)
    return system, classes, version


def load_static_complement():
    """(text, version) of the static complement block of arm B1@E4 (`prompts/static_complement.md`; spec 05 §2): the
    front matter between the two `---` lines (version, purpose, sources) is stripped and only the body reaches the model.
    The body is written from the literature's own guidance, never from this project's map (G5 decisions, item 2 (i))."""
    raw = (PROMPT_DIR / "static_complement.md").read_text()
    body, version = raw, None
    if raw.startswith("---"):
        head, _, body = raw[3:].partition("\n---")
        for line in head.splitlines():
            if line.strip().startswith("version:"):
                version = line.split(":", 1)[1].strip()
    return body.strip() + "\n", version


CALIBER_TEXT = {"E4": "Synopsys DC full-effort (E4) result for the original design at a {clock} ns clock:",
                "Y": "Yosys + OpenSTA (Y) result for the original design at a {clock} ns clock (the caliber used by the RTL-rewriting literature; every positive difference counts):"}
_MSG_ID = re.compile(r"\(([A-Z]{2,6}-\d{1,5})\)")


def synth_log_line(log_summary):
    """The "what the synthesizer already did" line of the E4 summary (decision 2026-09-15 item 3 (ii)): the counts of the
    log categories plus the normalised DC message types (identifier and count, e.g. OPT-776 x4) — never the raw messages,
    never a file path — and the counts of integrated clock-gating cells, datapath blocks and registers. None when empty."""
    ls = log_summary if isinstance(log_summary, dict) else {}
    log = ls.get("log") if isinstance(ls.get("log"), dict) else {}
    counts = log.get("counts") if isinstance(log.get("counts"), dict) else (ls.get("counts") if isinstance(ls.get("counts"), dict) else {})
    parts = [f"{k} {v}" for k, v in sorted(counts.items()) if v]
    types = {}
    for msgs in (log.get("samples") or {}).values():
        for m in msgs or []:
            for mid in _MSG_ID.findall(str(m)):
                types[mid] = types.get(mid, 0) + 1
    extras = [f"{name} {int(ls[key])}" for key, name in (("icg_count", "integrated clock-gating cells"), ("datapath_blocks", "datapath blocks"), ("registers", "registers")) if ls.get(key) is not None]
    if not parts and not types and not extras:
        return None
    out = "- what the synthesizer already did: " + (", ".join(parts) if parts else "no log categories")
    if types:
        out += "; message types " + ", ".join(f"{k} x{v}" for k, v in sorted(types.items()))
    if extras:
        out += "; " + ", ".join(extras)
    return out


def e4_summary(base_row, floor, clock_ns, caliber="E4"):
    """Text block from D's baseline evaluation row under the fitness caliber (E4, or Y for arm B0) and its rule-A floor rows
    ({metric: row}). Caliber Y (arm B0, the literature caliber) carries only what Yosys + OpenSTA measured — numbers, cell mix,
    critical endpoints — and no DC-derived line (decision 2026-09-15 item 3 (i))."""
    if not base_row:
        return f"No {caliber} baseline record is available for this design.\n"
    b = dict(base_row)
    lines = [CALIBER_TEXT.get(caliber, CALIBER_TEXT["E4"]).format(clock=clock_ns),
             f"- area {b.get('area_um2')} um2, {b.get('cells')} cells; WNS {b.get('wns_ns')} ns, TNS {b.get('tns_ns')} ns; power {b.get('power_saif_mw') or b.get('power_default_mw')} mW"]
    try:
        hist = json.loads(b.get("hist_json") or "{}")
        top = sorted(hist.items(), key=lambda kv: -float(kv[1]))[:8]
        if top:
            lines.append("- cell mix: " + ", ".join(f"{k} x{int(v)}" for k, v in top))
    except (ValueError, TypeError):
        pass
    if caliber != "Y":
        try:
            res = json.loads(b.get("resources_json") or "{}")
            dw = res.get("dw_modules") or []
            if dw:
                lines.append("- DesignWare components inferred: " + ", ".join(sorted(set(dw))))
        except (ValueError, TypeError):
            pass
        try:
            line = synth_log_line(json.loads(b.get("log_summary_json") or "{}"))
            if line:
                lines.append(line)
        except (ValueError, TypeError):
            pass
    try:
        cp = json.loads(b.get("crit_path_json") or "{}")
        ends = cp.get("endpoints") or cp.get("path_endpoints") or []
        if ends:
            lines.append("- most critical endpoints: " + ", ".join(str(e[1] if isinstance(e, (list, tuple)) and len(e) > 1 else e) for e in ends[:3]))
    except (ValueError, TypeError):
        pass
    if floor:
        td = {m: r.get("t_d") for m, r in floor.items() if r.get("t_d") is not None}
        cls = next((r.get("floor_class") for r in floor.values() if r.get("floor_class")), None)
        parts = [f"{m} {100 * float(v):.2f} %" if m != "wns" else f"wns {100 * float(v):.2f} % of the period" for m, v in sorted(td.items())]
        lines.append("- noise floor (minimum reportable gain, rule A): " + ", ".join(parts) + (f"; floor class {cls}" if cls else ""))
    return "\n".join(lines) + "\n"


def prior_text(prior):
    if not prior:
        return "No map prior is available yet (calibration phase): every rewrite class is evaluated.\n"
    lines = ["Map prior (fraction of rewrites of each class absorbed by the synthesizer, from Experiment 1):"]
    for cls, p in sorted(prior.items()):
        lines.append(f"- class {cls}: absorbed {100 * float(p):.0f} %")
    return "\n".join(lines) + "\n"


def prefix(design, system_text, base_row, floor, clock_ns, prior=None, caliber="E4", static_text=None, prior_block=True):
    """The cacheable prefix; `static_text` (arm B1@E4) takes the place of the map-prior table (spec 05 §2); the scalar arms
    B0 / B2 carry neither (`prior_block=False`)."""
    rtl = "\n\n".join(Path(design["_dir"], f).read_text(errors="replace") for f in design["files"])
    tail = static_text if static_text else (prior_text(prior) if prior_block else "")
    return (f"{system_text.strip()}\n\nThe design to rewrite (top module `{design['top']}`):\n```verilog\n{rtl}\n```\n\n"
            + e4_summary(base_row, floor, clock_ns, caliber) + "\n" + tail)


def suffix(instruction, cls, parent_rtl=None, feedback_blocks=(), design_top=None, scope_text=None):
    parts = []
    if parent_rtl:
        parts.append(f"Start from this earlier rewrite of the design (it is equivalent to the original):\n```verilog\n{parent_rtl}\n```\n")
    if feedback_blocks:
        parts.append("The synthesizer's verdicts on the earlier rewrites of this lineage (most recent first):\n" +
                     "\n".join("```json\n" + json.dumps(b, sort_keys=True) + "\n```" for b in feedback_blocks) + "\n")
    if scope_text:
        parts.append(scope_text.strip() + "\n")
    parts.append(f"Instruction (class {cls}): {instruction}\nAnswer with the JSON object only.")
    return "\n".join(parts)


def repair_suffix(instruction, cls, failed_rtl, failure_text, scope_text=None):
    """The counterexample-guided repair call (G5 item 1, correctness aid (ii)): the failed rewrite, the verifier's evidence,
    the same class instruction and scope; one such call per candidate, counted under the equal-call budget."""
    parts = [f"Your earlier rewrite of the design (below) was rejected by the equivalence check: {failure_text.strip()}.",
             f"```verilog\n{failed_rtl.strip()}\n```",
             "Repair this rewrite so that it is sequentially equivalent to the original design at every port, cycle by cycle after reset, "
             "while keeping the transformation it intended. Fix the cause named above rather than reverting to the original text."]
    if scope_text:
        parts.append(scope_text.strip())
    parts.append(f"Instruction (class {cls}): {instruction}\nAnswer with the JSON object only.")
    return "\n\n".join(parts) + "\n"
