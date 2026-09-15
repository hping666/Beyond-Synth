"""M6 LLM review (docs/spec/04-classifier-diagnoser.md §A.2 step 2; DECISIONS 2026-09-14 item 1): candidates whose
rules-v2 class has low confidence or falls into the four documented disagreement categories are shown to the LLM with
the class definitions (prompt `src/search/prompts/m6_review.md`), D's RTL (cacheable prefix per design) and the rewrite;
the answer JSON {class, subtags, basis, confidence} is stored as `candidates.class_llm` / `review_json`, and
`class_final` follows the review for (a) / (b) / (c1) / (c2). Class (d) stays defined by tool evidence (an LLM (d)
without operator or depth evidence is recorded but does not become the final class). Every call goes through the LLM
client (budget ledger of the phase, request / response saved under results/llm/<run_id>/); the review is resumable
(candidates with class_llm set are skipped) and runs as a queue job of kind `llm` (src/search/run_llm.py)."""
import json
import re
from pathlib import Path

from src import config as C
from src.db import core as db
from src.designs import catalog as K
from src.search import llm as L

PROMPT_DIR = Path(__file__).resolve().parent.parent / "search" / "prompts"
CLASSES = ("a", "b", "c1", "c2", "d")
FINAL_FROM_LLM = ("a", "b", "c1", "c2")          # (d) is tool-defined (DECISIONS 2026-09-14 item 1)
BUDGET_PHASE = {"phase3": "phase3_calibration", "phase4": "phase4_generation", "phase5": "phase5_main", "smoke": "phase3_calibration"}


def review_set(conn, cfg, exp="phase3", limit=None, shard=None, shards=None):
    """Candidates to review: rules v2, RTL on disk, no LLM class yet, and (confidence below `classify.review_below`) or
    (the rules flagged the wide rewrite for review) or (a nonequiv candidate classed (b) / (c1): the timing-change
    category) or (a (c1) whose flip-flop bits moved by at most two: the redundant-register category)."""
    p = cfg.get("classify") or {}
    below = float(p.get("review_below", 0.7))
    rows = [dict(r) for r in conn.execute("SELECT c.cand_id, c.run_id, c.design_id, c.rtl_path, c.rtl_files_json, c.top, c.class_rule, c.class_final, c.confidence, c.subtags_json, c.features_json, c.verdict "
                                          "FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp=? AND r.status != 'superseded' AND c.rules_version=2 AND c.class_rule IS NOT NULL "
                                          "AND c.class_llm IS NULL AND c.rtl_path IS NOT NULL AND c.label IS NOT NULL AND c.label NOT IN ('aborted','duplicate') ORDER BY c.run_id, c.cand_id", (exp,))]
    out = []
    for r in rows:
        why = []
        if r["confidence"] is not None and float(r["confidence"]) < below:
            why.append("low_confidence")
        if "review" in (r["subtags_json"] or ""):
            why.append("wide_rewrite_without_evidence")
        if r["verdict"] not in ("proven", "proven_sim_only") and r["class_rule"] in ("b", "c1"):
            why.append("nonequiv_timing_change")
        f = json.loads(r["features_json"]) if r["features_json"] else {}
        if r["class_rule"] == "c1" and f and abs(int(f.get("ff_c") or 0) - int(f.get("ff_d") or 0)) <= 2:
            why.append("redundant_register")
        if why:
            r["why"] = why
            out.append(r)
    if shards:   # k parallel jobs take interleaved slices of the same deterministic order
        out = [r for i, r in enumerate(out) if i % int(shards) == int(shard or 0)]
    return out[: (limit or len(out))]


def prompt_parts(design, row):
    d_rtl = "\n\n".join(Path(design["_dir"], f).read_text(errors="replace") for f in design["files"])
    files = json.loads(row["rtl_files_json"]) if row.get("rtl_files_json") else [row["rtl_path"]]
    c_rtl = "\n\n".join(Path(f).read_text(errors="replace") for f in files)
    system = (PROMPT_DIR / "m6_review.md").read_text()
    prefix = f"{system.strip()}\n\nOriginal design (top module `{design['top']}`):\n```verilog\n{d_rtl}\n```\n"
    rules = row.get("subtags_json") or "[]"
    equiv = row.get("verdict") or "not checked"
    suffix = (f"Rewrite (top module `{row.get('top') or design['top']}`):\n```verilog\n{c_rtl}\n```\n"
              f"Rule classifier: class {row['class_rule']} with evidence {rules}. Equivalence verdict: {equiv}"
              + (" (the rewrite is NOT equivalent: judge the transformation it attempts, including any timing change).\n" if equiv not in ("proven", "proven_sim_only") else ".\n")
              + "Answer with the JSON object only.")
    return prefix, suffix


def parse_answer(text):
    """The first JSON object in the answer -> {class, subtags, basis, confidence}; ValueError when unusable."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError("no JSON object in the answer")
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"bad JSON: {e}")
    cls = str(obj.get("class") or "").strip().strip("()").lower()
    if cls not in CLASSES:
        raise ValueError(f"class {obj.get('class')!r} not in {CLASSES}")
    conf = obj.get("confidence")
    try:
        conf = None if conf is None else max(0.0, min(1.0, float(conf)))
    except (TypeError, ValueError):
        conf = None
    tags = obj.get("subtags") or []
    return {"class": cls, "subtags": [str(t) for t in tags] if isinstance(tags, list) else [], "basis": str(obj.get("basis") or "")[:300], "confidence": conf}


def final_class(class_rule, class_llm):
    """(a) / (b) / (c1) / (c2) from the review replace the rule class; an LLM (d) does not (tool-defined (d))."""
    return class_llm if class_llm in FINAL_FROM_LLM else class_rule


def run_review(cfg, conn, exp="phase3", limit=None, transport=None, log=print, max_output_tokens=6000, shard=None, shards=None):
    """Review the selected candidates one by one (resumable; concurrent shard jobs re-check every candidate before the
    call, so a candidate reviewed meanwhile by another job is skipped). -> {reviewed, unusable, changed, by_transition}."""
    rows = review_set(conn, cfg, exp, limit, shard, shards)
    run_id = f"m6rev_{exp}_{db.now().replace('-', '').replace(':', '').replace('T', '_')}"
    client = L.LLMClient(cfg, conn, BUDGET_PHASE.get(exp, exp), run_id, transport=transport)
    designs = {d["design_id"]: d for d in K.load_all()}
    model = cfg["llm"]["selected"]
    out = {"run_id": run_id, "selected": len(rows), "reviewed": 0, "unusable": 0, "changed": 0, "by_transition": {}, "why": {}}
    for r in rows:
        for w in r["why"]:
            out["why"][w] = out["why"].get(w, 0) + 1
    log(f"{run_id}: {len(rows)} candidates to review with {model} ({out['why']})")
    for i, r in enumerate(rows, 1):
        if conn.execute("SELECT class_llm FROM candidates WHERE cand_id=?", (r["cand_id"],)).fetchone()[0] is not None:
            out["skipped_meanwhile"] = out.get("skipped_meanwhile", 0) + 1
            continue
        prefix, suffix = prompt_parts(designs[r["design_id"]], r)
        call = client.call(model, prefix, suffix, tag=f"m6_review:{r['cand_id']}", max_output_tokens=max_output_tokens)
        try:
            if call.get("status") == "incomplete":
                raise ValueError("truncated at max_output_tokens")
            ans = parse_answer(call["text"])
        except ValueError as e:
            out["unusable"] += 1
            conn.execute("UPDATE candidates SET review_json=? WHERE cand_id=?", (json.dumps({"run_id": run_id, "call_id": call["call_id"], "error": str(e), "why": r["why"]}), r["cand_id"]))
            conn.commit()
            continue
        cls_final = final_class(r["class_rule"], ans["class"])
        rec = {"run_id": run_id, "call_id": call["call_id"], "model": model, "why": r["why"], "class_rule": r["class_rule"], "class_llm": ans["class"], "class_final": cls_final,
               "subtags": ans["subtags"], "basis": ans["basis"], "confidence": ans["confidence"], "cost_usd": call["cost_usd"],
               "note": "llm (d) without tool evidence: final class stays the rule class" if ans["class"] == "d" and cls_final != "d" else None}
        conn.execute("UPDATE candidates SET class_llm=?, class_final=?, review_json=? WHERE cand_id=?", (ans["class"], cls_final, json.dumps(rec), r["cand_id"]))
        conn.commit()
        out["reviewed"] += 1
        key = f"{r['class_rule']}->{cls_final}"
        out["by_transition"][key] = out["by_transition"].get(key, 0) + 1
        if cls_final != r["class_rule"]:
            out["changed"] += 1
        if i % 25 == 0:
            log(f"  {i}/{len(rows)} reviewed, {out['unusable']} unusable, {out['changed']} changed ({db.now()})")
    log(f"done: {out}")
    return out
