#!/usr/bin/env python3
"""INQUIRY 2026-09-20 — facts for paper §3 / §4 (read-only): A3 prescreen state of the M runs and the prescreened candidates,
A5 requested -> produced class agreement, B1 rule_a_any survivors whose stored E4 label is not retained / trade-off, B2 the Fig. 3
matrices regenerated from the diagnoser's per-level verdicts (rule A at E1 / E2 / E3 / E4 with the frozen phase4 floors, the
materiality band at E1d / E2g; full verdict order identical -> retained -> absorbed -> noise -> harmful -> trade-off), B3 the static
rule on that basis, C1 the class_final version (pre- versus post-review). Writes reports/inquiry_2026-09-20.md and
reports/data/inquiry_2026-09-20.json; nothing else is written."""
import collections
import datetime
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.analysis import objects as OBJ  # noqa: E402
from src.analysis import map as MAP  # noqa: E402
from src.analysis import phase5 as P5  # noqa: E402
from src.diagnose import m3  # noqa: E402
from src.search.driver import record_from_row  # noqa: E402

_spec = importlib.util.spec_from_file_location("sec3", os.path.join(ROOT, "scripts", "report_paper_sec3.py"))
S3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S3)
LEVELS = ("E1", "E1d", "E2", "E2g", "E3", "E4")
SURV = ("retained", "tradeoff")
CLASSES = ("a", "b", "c1", "c2", "d")


def pct(n, d):
    return f"{100 * n / d:.1f} %" if d else "—"


def a3(cfg, conn, tiers):
    first = {}
    for j in conn.execute("SELECT payload_json, started_at FROM jobs WHERE kind='search' AND started_at IS NOT NULL"):
        try:
            rid = json.loads(j["payload_json"]).get("run_id")
        except (ValueError, TypeError):
            continue
        if rid and (rid not in first or j["started_at"] < first[rid]):
            first[rid] = j["started_at"]
    runs = [dict(r) for r in conn.execute("SELECT run_id, design_id, llm_model, prescreen_on, status, started_at, COALESCE(excluded_from_tables,0) ex, superseded_reason FROM runs WHERE exp='phase5' AND arm='M'")]
    out = {"by_tier_model": {}, "launch_windows": {}}
    for t in ("large", "medium", "small"):
        for model in ("gpt-5.6-luna", "gpt-5.6-terra"):
            rt = [r for r in runs if tiers.get(r["design_id"]) == t and r["llm_model"] == model and r["status"] != "superseded" and not r["ex"]]
            out["by_tier_model"][f"{t}|{model}"] = {"runs": len(rt), "prescreen_on": sum(1 for r in rt if r["prescreen_on"]), "prescreen_off": sum(1 for r in rt if not r["prescreen_on"]),
                                                    "launched": sum(1 for r in rt if r["run_id"] in first), "not_launched": sum(1 for r in rt if r["run_id"] not in first)}
        rt = [r for r in runs if tiers.get(r["design_id"]) == t]
        on = sorted(first[r["run_id"]] for r in rt if r["prescreen_on"] and r["run_id"] in first)
        off = sorted(first[r["run_id"]] for r in rt if not r["prescreen_on"] and r["run_id"] in first and r["status"] != "superseded" and not r["ex"])
        out["launch_windows"][t] = {"prescreen_on_launched": [on[0], on[-1]] if on else None, "prescreen_off_launched": [off[0], off[-1]] if off else None}
    out["superseded_or_excluded_M_runs"] = [{"run_id": r["run_id"], "design": r["design_id"], "model": r["llm_model"], "status": r["status"], "prescreen_on": r["prescreen_on"], "excluded": r["ex"], "reason": r["superseded_reason"], "launched": first.get(r["run_id"])}
                                            for r in runs if r["status"] == "superseded" or r["ex"]]
    pre = collections.defaultdict(collections.Counter)
    for r in conn.execute("""SELECT r.design_id, r.llm_model, CASE WHEN c.verdict IS NOT NULL AND c.verdict!='proven' THEN 'sim failed: '||c.verdict WHEN c.v2_status IS NOT NULL THEN 'sim passed' ELSE 'sim pending' END sim,
                             EXISTS(SELECT 1 FROM evaluations e WHERE e.cand_id=c.cand_id AND e.config='E4' AND e.status='ok') e4ok,
                             EXISTS(SELECT 1 FROM evaluations e WHERE e.cand_id=c.cand_id AND e.config='E4' AND e.status!='ok') e4fail, COUNT(*) n
                             FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase5' AND COALESCE(c.prescreened,0)=1 GROUP BY 1,2,3,4,5"""):
        key = f"{tiers.get(r['design_id'])}|{r['llm_model']}"
        state = r["sim"] + ("" if r["sim"] != "sim passed" else (", E4 ok" if r["e4ok"] else ", E4 failed (not retried: the retry scope is proven candidates)" if r["e4fail"] else ", E4 pending"))
        pre[key][state] += r["n"]
    out["prescreened_candidates"] = {k: dict(v) for k, v in pre.items()}
    out["prescreened_total"] = sum(sum(v.values()) for v in pre.values())
    out["prescreened_proofs"] = dict(collections.Counter(str(r[0]) for r in conn.execute("SELECT c.v3_status FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase5' AND COALESCE(c.prescreened,0)=1")))
    return out


def a5(cfg, conn, tiers):
    rows = [dict(r) for r in conn.execute("SELECT c.class_requested req, c.class_final fin, r.arm, r.llm_model, r.design_id FROM candidates c JOIN runs r ON r.run_id=c.run_id "
                                          "WHERE r.exp='phase5' AND r.status!='superseded' AND COALESCE(r.excluded_from_tables,0)=0 AND c.class_final IS NOT NULL")]
    out = {}
    for scope, rs in (("all started tiers", rows), ("large (Stage A)", [r for r in rows if tiers.get(r["design_id"]) == "large"]),
                      ("medium", [r for r in rows if tiers.get(r["design_id"]) == "medium"]), ("small", [r for r in rows if tiers.get(r["design_id"]) == "small"])):
        tab = {}
        for key in sorted({(r["llm_model"], r["arm"]) for r in rs}):
            rr = [r for r in rs if (r["llm_model"], r["arm"]) == key and r["req"] in ("a", "b", "c1", "d")]
            tab[f"{key[0]}|{key[1]}"] = {"n_with_class_intent": len(rr), "agree": sum(1 for r in rr if r["fin"] == r["req"]),
                                         "per_intent": {i: [sum(1 for r in rr if r["req"] == i and r["fin"] == i), sum(1 for r in rr if r["req"] == i)] for i in ("a", "b", "c1", "d")},
                                         "free_intent_rows": sum(1 for r in rs if (r["llm_model"], r["arm"]) == key and r["req"] == "free")}
        out[scope] = tab
    return out


def b_items(cfg, conn):
    fv = cfg["noise"]["floor_version"]
    mat = {"area": cfg["noise"]["materiality"]["area"], "power": cfg["noise"]["materiality"]["power_saif"], "wns": cfg["noise"]["materiality"]["wns"]}
    p4, objs = S3.phase4_objects(conn, fv)
    odd = []
    for o in objs:
        if S3.survival(o, "E4", "rule_a_any", mat) and o["label"] not in SURV:
            phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (o["design_id"],)).fetchone()[0]
            b, e = OBJ.baseline_row(conn, o["design_id"], "E4", phi), OBJ.object_row_eval(conn, o["cand_id"], "E4", phi)
            g, t = o["gains"]["E4"], o["t_d"]["E4"]
            odd.append({"cand_id": o["cand_id"], "design": o["design_id"], "class": o["cls"], "role": o["role"], "label": o["label"],
                        "delta_E4": {m: (round(float(g[m]), 5) if g.get(m) is not None else None) for m in ("area", "wns", "power")}, "t_d_E4": {m: (round(float(t[m]), 5) if t.get(m) is not None else None) for m in ("area", "wns", "power")},
                        "D": {"area": b["area_um2"], "cells": b["cells"], "wns_ns": b["wns_ns"], "power_saif_mw": b["power_saif_mw"]}, "C": {"area": e["area_um2"], "cells": e["cells"], "wns_ns": e["wns_ns"], "power_saif_mw": e["power_saif_mw"]},
                        "identical_fingerprint": m3.identical_fingerprint(record_from_row(b), record_from_row(e)), "power_basis": m3.power_basis(record_from_row(b), record_from_row(e))})
    k_sigma, fpj = float(cfg["noise"]["k_sigma"]), float(cfg["diag"]["fp_jaccard"])
    verd = {}
    for o in objs:
        did, cid = o["design_id"], o["cand_id"]
        phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (did,)).fetchone()[0]
        verd[cid] = {}
        for lv in LEVELS:
            b, e = OBJ.baseline_row(conn, did, lv, phi), OBJ.object_row_eval(conn, cid, lv, phi)
            if b is None or e is None:
                verd[cid][lv] = None
                continue
            if lv in ("E1d", "E2g"):
                thr, fl = dict(mat), {}
            else:
                thr, fl = OBJ.thresholds(conn, did, lv, fv)
                thr = {m: v for m, v in thr.items() if v is not None} or None
            sigma = {m: float((fl.get(k) or {}).get("sigma_robust") or 0.0) for m, k in (("area", "area"), ("wns", "wns"), ("power", "power_saif"))}
            fc = next((r.get("floor_class") for r in fl.values() if r.get("floor_class")), None)
            verd[cid][lv] = m3.diagnose(record_from_row(b), record_from_row(e), sigma, float(phi), v3_status="proven", k_sigma=k_sigma, fp_jaccard=fpj, thresholds=thr, floor_class=fc)["label"]
    mism = [(o["cand_id"], o["label"], verd[o["cand_id"]]["E4"]) for o in objs if verd[o["cand_id"]]["E4"] != o["label"]]

    def matrix(rows):
        out = {}
        for cls in CLASSES:
            rc = [o for o in rows if o["cls"] == cls]
            out[cls] = {}
            for lv in LEVELS:
                known = [o for o in rc if verd[o["cand_id"]][lv] is not None]
                out[cls][lv] = [sum(1 for o in known if verd[o["cand_id"]][lv] in SURV), len(known)]
        ab = [o for o in rows if o["cls"] in ("a", "b")]
        out["_totals"] = {"a_plus_b_E4": [sum(1 for o in ab if verd[o["cand_id"]]["E4"] in SURV), len(ab)], "all_E4": [sum(1 for o in rows if verd[o["cand_id"]]["E4"] in SURV), len(rows)],
                          "labels_E4_by_class": {cls: dict(collections.Counter(verd[o["cand_id"]]["E4"] for o in rows if o["cls"] == cls)) for cls in CLASSES}}
        return out
    b0 = [o for o in objs if o["role"] == "b0"]
    forb = [o for o in objs if o["cls"] in ("a", "b")]
    allow = [o for o in objs if o["cls"] in ("c1", "c2", "d")]
    absorbed_ids = [{"cand_id": o["cand_id"], "design": o["design_id"], "class": o["cls"], "label": verd[o["cand_id"]]["E4"]} for o in allow if verd[o["cand_id"]]["E4"] in MAP.ABSORBED_LABELS]
    rule = {r["cand_id"]: r["class_rule"] for r in conn.execute("SELECT cand_id, class_rule FROM candidates WHERE review_json IS NOT NULL")}
    pre_objs = [dict(o, cls=rule.get(o["cand_id"], o["cls"])) for o in objs]
    reviewed = [dict(r) for r in conn.execute("SELECT c.cand_id, c.design_id, c.class_rule, c.class_llm, c.class_final, c.confidence, c.verdict, c.label, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase4' AND c.review_json IS NOT NULL ORDER BY c.design_id")]
    lab = {o["cand_id"]: o for o in p4["objects"]}
    changed = [{"cand_id": r["cand_id"], "design": r["design_id"], "arm": r["arm"], "rule": r["class_rule"], "llm": r["class_llm"], "final": r["class_final"], "verdict": r["verdict"], "label_E4": (lab.get(r["cand_id"]) or {}).get("label"),
                "role": (lab.get(r["cand_id"]) or {}).get("role"), "among_255": r["cand_id"] in {o["cand_id"] for o in objs}} for r in reviewed if r["class_final"] != r["class_rule"]]
    mb0_pre = MAP.build_map([dict(o, cls=rule.get(o["cand_id"], o["cls"])) for o in b0], configs=("E4",))
    return {"n_objects": len(objs), "n_b0": len(b0), "b1": odd, "b2": {"e4_recomputed_equals_stored": len(objs) - len(mism), "mismatches": mism, "panel_b0": matrix(b0), "panel_all": matrix(objs)},
            "b3": {"p_survive_given_a_or_b": [sum(1 for o in forb if verd[o["cand_id"]]["E4"] in SURV), len(forb)], "absorbed_given_c1_c2_d": [len(absorbed_ids), len(allow)],
                   "absorbed_without_noise": [sum(1 for x in absorbed_ids if x["label"] != "noise"), len(allow)], "absorbed_ids": absorbed_ids, "absorbed_labels_definition": list(MAP.ABSORBED_LABELS)},
            "c1": {"json": {"generated_at": p4["generated_at"], "git_sha": p4["git_sha"]}, "class_final_differs_from_json": [o["cand_id"] for o in objs if o.get("cls_db") and o["cls_db"] != o["cls"]],
                   "post_review": {"class_counts": dict(collections.Counter(o["cls"] for o in objs)), "static_rule": MAP.misclassification_rates(objs)},
                   "pre_review": {"class_counts": dict(collections.Counter(o["cls"] for o in pre_objs)), "static_rule": MAP.misclassification_rates(pre_objs)},
                   "reviewed": len(reviewed), "changed": changed, "b0_objects_reviewed": [o["cand_id"] for o in b0 if o["cand_id"] in rule],
                   "map_prior_pre_review_b0_E4": {c: [v["E4"]["n_retained"], v["E4"]["n_evaluated"]] for c, v in mb0_pre.items()},
                   "map_prior_post_review_b0_E4": {c: [p4["map_b0"][c]["E4"]["n_retained"], p4["map_b0"][c]["E4"]["n_evaluated"]] for c in p4["map_b0"]},
                   "auroc": {"post_review_json": p4["predictor"]["with_class"].get("auroc"), "class_blind": p4["predictor"]["class_blind"].get("auroc")}}}


def render(d):
    L = [f"# INQUIRY 2026-09-20 — facts for paper §3 / §4 (generated {d['generated_at']}, git {d['git_sha']}; read-only; scripts/report_inquiry_0920.py)", ""]
    a3_ = d["a3"]
    L += ["## A3. Arm M runs by tier and model: prescreen on / off (runs.prescreen_on; launch = first search job of the run)", "", "| tier \\| model | runs | prescreen on | prescreen off | launched | not launched |", "|---|---|---|---|---|---|"]
    for k, v in a3_["by_tier_model"].items():
        L.append(f"| {k} | {v['runs']} | {v['prescreen_on']} | {v['prescreen_off']} | {v['launched']} | {v['not_launched']} |")
    L += ["", "Launch windows: " + "; ".join(f"{t}: prescreen-on {w['prescreen_on_launched']}, prescreen-off {w['prescreen_off_launched']}" for t, w in a3_["launch_windows"].items()), "",
          "Superseded or excluded M runs: " + "; ".join(f"{r['run_id']} ({r['design']}, {r['model']}, {r['status']}, prescreen_on {r['prescreen_on']}, excluded {r['excluded']}, {r['reason']}, launched {r['launched']})" for r in a3_["superseded_or_excluded_M_runs"]), "",
          f"Prescreened candidates ({a3_['prescreened_total']}): " + "; ".join(f"{k}: " + ", ".join(f"{s} {n}" for s, n in v.items()) for k, v in a3_["prescreened_candidates"].items()) + f". Proofs (candidates.v3_status): {a3_['prescreened_proofs']}.", ""]
    L += ["## A5. Requested -> produced class agreement (candidates.class_requested versus class_final; rows = llm_model | arm)", ""]
    for scope, tab in d["a5"].items():
        L += [f"### {scope}", "", "| row | n (class intent) | overall | a | b | c1 | d | free-intent rows |", "|---|---|---|---|---|---|---|---|"]
        for k, v in tab.items():
            pi = v["per_intent"]
            L.append(f"| {k} | {v['n_with_class_intent']} | {v['agree']} = {pct(v['agree'], v['n_with_class_intent'])} | " + " | ".join(f"{pi[i][0]} / {pi[i][1]} = {pct(pi[i][0], pi[i][1])}" for i in ("a", "b", "c1", "d")) + f" | {v['free_intent_rows']} |")
        L.append("")
    b = d["b"]
    L += [f"## B1. rule_a_any survivors at E4 whose stored label is not retained / trade-off ({len(b['b1'])} of {b['n_objects']})", ""]
    for x in b["b1"]:
        L.append(f"- {x['cand_id']} {x['design']} class {x['class']} role {x['role']} label **{x['label']}**: δ at E4 {x['delta_E4']} against t_D {x['t_d_E4']}; D {x['D']} vs C {x['C']}; identical fingerprint {x['identical_fingerprint']}, power basis {x['power_basis']}")
    L += ["", f"## B2. Fig. 3 matrices from the diagnoser's per-level verdicts (E4 recomputed = stored label for {b['b2']['e4_recomputed_equals_stored']} of {b['n_objects']} objects; mismatches {b['b2']['mismatches']})", ""]
    for name, key in (("Panel 1 — B0 layer", "panel_b0"), ("Panel 2 — all diagnosed objects", "panel_all")):
        m = b["b2"][key]
        L += [f"**{name}** — survival = retained or trade-off by the diagnoser's verdict; E1 / E2 / E3 / E4 rule A with the frozen phase4 floors, E1d / E2g the materiality band (cells: survive / n)", "",
              "| class | " + " | ".join(LEVELS) + " |", "|---|" + "---|" * len(LEVELS)]
        for cls in CLASSES:
            L.append(f"| {cls} | " + " | ".join((f"{s} / {n} ({100 * s / n:.0f} %)" if n else "-") for s, n in m[cls].values()) + " |")
        t = m["_totals"]
        L += ["", f"a + b at E4: {t['a_plus_b_E4'][0]} of {t['a_plus_b_E4'][1]}; all at E4: {t['all_E4'][0]} of {t['all_E4'][1]}; E4 labels by class: {t['labels_E4_by_class']}", ""]
    b3 = b["b3"]
    L += ["## B3. Static rule on the same basis", "", f"P(survive | a or b) = {b3['p_survive_given_a_or_b'][0]} / {b3['p_survive_given_a_or_b'][1]} = {pct(*b3['p_survive_given_a_or_b'])}; "
          f"P(absorbed | c1, c2, d) = {b3['absorbed_given_c1_c2_d'][0]} / {b3['absorbed_given_c1_c2_d'][1]} = {pct(*b3['absorbed_given_c1_c2_d'])} with absorbed = {b3['absorbed_labels_definition']} "
          f"({b3['absorbed_without_noise'][0]} / {b3['absorbed_without_noise'][1]} = {pct(*b3['absorbed_without_noise'])} without noise): " + "; ".join(f"{x['cand_id']} {x['design']} ({x['class']}, {x['label']})" for x in b3["absorbed_ids"]), ""]
    c = b["c1"]
    L += ["## C1. class_final version", "", f"reports/data/phase4_exp1.json generated {c['json']['generated_at']} (git {c['json']['git_sha']}); objects whose `cls` differs from candidates.class_final: {c['class_final_differs_from_json'] or 'none'} (the file is the post-review version).",
          f"Post-review: classes {c['post_review']['class_counts']}, static rule {c['post_review']['static_rule']}. Pre-review (the 23 reviewed objects at class_rule): classes {c['pre_review']['class_counts']}, static rule {c['pre_review']['static_rule']}.",
          f"B0 objects among the reviewed: {c['b0_objects_reviewed'] or 'none'}; map prior (B0, E4 area above t_D) pre-review {c['map_prior_pre_review_b0_E4']} = post-review {c['map_prior_post_review_b0_E4']}. AUROC in the post-review file: {c['auroc']}.", "",
          f"Changed objects ({len(c['changed'])} of {c['reviewed']} reviewed):", ""]
    for x in c["changed"]:
        L.append(f"- {x['cand_id']} {x['design']} ({x['arm']}, role {x['role']}): {x['rule']} -> {x['final']} (LLM {x['llm']}); verdict {x['verdict']}; E4 label {x['label_E4']}; among the 255 diagnosed: {x['among_255']}")
    return "\n".join(L) + "\n"


def main():
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    tiers = P5.tier_of_design(cfg)
    d = {"generated_at": datetime.datetime.now().isoformat(timespec="minutes"), "git_sha": C.git_sha()}
    d["a3"] = a3(cfg, conn, tiers)
    d["a5"] = a5(cfg, conn, tiers)
    d["b"] = b_items(cfg, conn)
    with open(os.path.join(ROOT, "reports", "data", "inquiry_2026-09-20.json"), "w") as f:
        json.dump(d, f, indent=1, default=str)
    with open(os.path.join(ROOT, "reports", "inquiry_2026-09-20.md"), "w") as f:
        f.write(render(d))
    print("written reports/inquiry_2026-09-20.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
