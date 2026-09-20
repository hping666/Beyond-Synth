#!/usr/bin/env python3
"""REQUEST 2026-09-20 (d) — four remaining items for paper Section III (read-only, visible layer only). Writes
reports/paper_sec3_addendum.md and reports/data/paper_sec3_addendum.json. Every number carries its source; the mechanism lines
are the operator's reading of the candidate diff (comment-stripped, module by module) and are marked as such.
Run under nice: nice -n 19 .venv/bin/python3 scripts/report_paper_sec3_addendum.py
"""
import collections
import datetime
import difflib
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src import config as C  # noqa: E402
from src.db import core as db  # noqa: E402
from src.analysis import phase5 as P5  # noqa: E402
from src.designs import catalog as K  # noqa: E402

SOURCES = []


def src(name, text):
    SOURCES.append({"item": name, "source": text})
    return text


def pct(x, nd=1):
    return "-" if x is None else f"{100.0 * x:.{nd}f} %"


def modules_of(path):
    txt = open(path, errors="replace").read()
    txt = re.sub(r"//.*", "", txt)
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    return {m.group(1): [l.strip() for l in m.group(2).splitlines() if l.strip()] for m in re.finditer(r"module\s+(\w+)(.*?)endmodule", txt, flags=re.S)}


def module_diff(design_files, cand_path):
    D = {}
    for f in design_files:
        D.update(modules_of(f))
    Cm = modules_of(cand_path)
    out = {}
    for mod, body in Cm.items():
        if mod not in D:
            out[mod] = {"status": "new module", "lines": len(body)}
            continue
        diff = [l for l in difflib.unified_diff(D[mod], body, lineterm="", n=0) if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
        out[mod] = {"status": "changed" if diff else "unchanged", "changed_lines": len(diff), "d_lines": len(D[mod]), "c_lines": len(body)}
    for mod in D:
        if mod not in Cm:
            out[mod] = {"status": "removed"}
    return out


def e4_record(conn, cand_id):
    return conn.execute("SELECT eval_id, area_um2, cells, wns_ns, power_saif_mw, power_default_mw, saif_coverage, log_summary_json, raw_dir FROM evaluations WHERE cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1", (cand_id,)).fetchone()


def baseline(conn, design_id, phi):
    return conn.execute("SELECT eval_id, area_um2, cells, wns_ns, power_saif_mw, power_default_mw, saif_coverage, log_summary_json, raw_dir FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (design_id, phi)).fetchone()


def ls(row):
    try:
        return json.loads(row["log_summary_json"] or "{}") if row else {}
    except (ValueError, TypeError):
        return {}


# ----------------------------------------------------------------------------- item 1
def item1(conn):
    d = "cktevo_mem_ctrl__mc_rf"
    phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (d,)).fetchone()[0]
    b = baseline(conn, d, phi)
    src("1 mc_rf records", f"SELECT e.pert_id, p.ptype, p.seq_status, e.clock_ns, e.area_um2, e.cells, e.power_saif_mw FROM evaluations e JOIN perturbations p ON p.pert_id=e.pert_id WHERE e.design_id='{d}' AND e.config='E4' AND e.status='ok' AND abs(e.clock_ns-{phi})<1e-6; baseline eval {b['eval_id']} (is_baseline=1, same clock, SAIF power present)")
    recs = []
    for r in conn.execute("SELECT e.pert_id, p.ptype, p.seq_status, e.clock_ns, e.area_um2, e.cells, e.power_saif_mw FROM evaluations e JOIN perturbations p ON p.pert_id=e.pert_id WHERE e.design_id=? AND e.config='E4' AND e.status='ok' AND abs(e.clock_ns-?)<1e-6 ORDER BY e.area_um2 DESC, e.pert_id", (d, phi)):
        recs.append({"pert_id": r["pert_id"], "ptype": r["ptype"], "seq_status": r["seq_status"], "clock_ns": r["clock_ns"], "area_um2": r["area_um2"], "cells": r["cells"], "power_saif_mw": r["power_saif_mw"],
                     "area_rel": (r["area_um2"] - b["area_um2"]) / b["area_um2"], "power_rel": ((r["power_saif_mw"] - b["power_saif_mw"]) / b["power_saif_mw"]) if (r["power_saif_mw"] is not None and b["power_saif_mw"]) else None})
    top_area = max(r["area_rel"] for r in recs)
    at_top = [r for r in recs if abs(r["area_rel"] - top_area) < 1e-9]
    p0 = [r for r in recs if r["ptype"] == "P0_roundtrip"]
    fl = {r["metric"]: dict(r) for r in conn.execute("SELECT metric, floor_class, t_d, max_abs, n FROM noise_floor WHERE floor_version='phase4' AND config='E4' AND design_id=?", (d,))}
    return {"design": d, "phi": phi, "baseline": {"eval_id": b["eval_id"], "area_um2": b["area_um2"], "cells": b["cells"], "power_saif_mw": b["power_saif_mw"]},
            "n_records": len(recs), "largest_area_effect": top_area, "records_at_largest": at_top, "records_at_largest_by_ptype": dict(collections.Counter(r["ptype"] for r in at_top)),
            "p0_records": p0, "records": recs, "floor_row": fl,
            "statement": ("the +18.7 % area effect is not a P3_expr effect: at Φ_main every proven perturbation of mc_rf that changes the netlist lands on the same E4 result (2 816.408 µm², 1 039 cells) — the re-print P0 among them — so the design is an offset design (floor class offset, t_D = its own max |δ|); the frozen-table attribution to P3_expr in the Section III data is a tie-break among identical values. "
                          "The paper should name the re-print P0 (with every other proven perturbation alike): +18.7 % area, +64.2 % SAIF power; the P2 reorders split between the same +18.7 % and a second plateau at +17.4 % area / +19 % power.")}


# ----------------------------------------------------------------------------- item 2
def item2(conn):
    out = {}
    src("2 best objects", "candidates (class_rule / class_llm / class_final, subtags_json = rules-v2 evidence tags, rtl_path); E4 records of D at Φ_main and of the candidate (log_summary_json.registers = DC's flip-flop count, cells, area); the diff is data/designs/<suite>/<design>/rtl/*.v against the candidate file, comments stripped, module by module")
    for des, cid, reading in (("rtlopt_ticket_machine", "c634baa4b8fa859",
                               "D encodes the six-state Moore FSM one-hot (localparam RDY … BILL30 = 6'b000001 … 6'b100000; reg [5:0] State, NextState) with case-based output and next-state blocks; the candidate keeps the same two state registers but 3 bits wide (reg [2:0] State, NextState; RDY = 3'b000 …), computes the four outputs as boolean functions of the three state bits and collapses the next-state case into the same transitions on the binary codes. A state re-encoding (one-hot → binary) that changes the flip-flop count (6 → 3 bits) inside the same register cells."),
                              ("rtlopt_fsm_encode", "c92a0b6177cf6f6",
                               "D drives an 8-bit one-hot sequencer (localparam IDLE … STORE2 = 8'b00000001 … 8'b10000000; reg [7:0] current_state, next_state) through a next-state case and a datapath case over the same states; the candidate replaces the one-hot state with a 3-bit phase counter (reg [2:0] phase; phase <= phase + 1 once started, 000 = idle) and dispatches the same LOAD1 / LOAD2 / ADD / SUB / SHIFT / STORE1 / STORE2 datapath actions on the counter value (reg1, reg2, out_reg, done unchanged). A state re-encoding (one-hot → binary counter): flip-flop bits 33 → 28 at the RTL (rules v2), 33 → 27 in DC's E4 netlist, the register cells unchanged.")):
        c = dict(conn.execute("SELECT class_rule, class_llm, class_final, subtags_json, rtl_path, label FROM candidates WHERE cand_id=?", (cid,)).fetchone())
        phi = conn.execute("SELECT phi_main_ns_nangate45 FROM designs WHERE design_id=?", (des,)).fetchone()[0]
        b, e = baseline(conn, des, phi), e4_record(conn, cid)
        suite, name = des.split("_", 1)
        dfiles = sorted(glob.glob(os.path.join(ROOT, "data", "designs", suite, name, "rtl", "*.v")))
        out[des] = {"cand_id": cid, "class": {"rule": c["class_rule"], "llm": c["class_llm"], "final": c["class_final"]}, "label": c["label"], "evidence_tags": json.loads(c["subtags_json"] or "[]"),
                    "E4": {"D": {"registers": ls(b).get("registers"), "cells": b["cells"], "area_um2": b["area_um2"]}, "C": {"registers": ls(e).get("registers"), "cells": e["cells"], "area_um2": e["area_um2"]}, "area_gain": (b["area_um2"] - e["area_um2"]) / b["area_um2"]},
                    "module_diff": module_diff(dfiles, c["rtl_path"]), "reading": reading}
    out["class_rule_note"] = ("Rules v2 (src/classify/rules.py; docs/spec/04 §A; reports/phase3.md §6a) file a latency-preserving refactor as (b) when the register cells are unchanged — a width change inside the same cells carries the evidence tag 'flip-flop bits N -> M in the same register cells (widths)' — and as (c1) only when the number of register cells changes ('… and register cells N -> M'). "
                              "Both objects change the flip-flop bit count (6 → 3; 33 → 28) but keep every register cell, so the map classes them (b). The paper's sentence should read: a one-hot-to-binary re-encoding that halves the state bits inside the same state register (class (b) under rules v2; it changes the flip-flop count, not the register-cell count); it must not call them class (c1).")
    return out


# ----------------------------------------------------------------------------- item 3
def item3(cfg, conn):
    designs = P5._Designs(cfg, conn)
    src("3 power gains", "Phase 5 proven candidates of the design (duplicates excluded) with rule-A label retained (src.analysis.phase5.uniform_diagnosis; gains from src/diagnose/m3.relative_gains on the basis m3.power_basis picks: SAIF only when both D and C carry SAIF power, else DC's default switching activity); ICG count and DC register count from log_summary_json of the E4 records; E4 report directories keep power_default.rpt (no SAIF toggle summary is stored), so the total toggle rate under the V2 stimulus is not available for either side")
    held = [d for ds in cfg["exp5"]["starting_points"].values() for d in ds]
    no_saif = []
    for d in held:
        b = baseline(conn, d, designs.get(d)["phi"])
        if b is None or b["power_saif_mw"] is None:
            no_saif.append(d)
    out = {"designs_without_saif_baseline": no_saif, "designs": {}}
    readings = {
        "cktevo_risc__btb": "the top module btb is untouched; the rewrite is inside btb_array: the indexed array write (data[windex] <= in) becomes an explicit 8-way case per generate branch (a VALID_ARRAY branch with reset, a NONVALID_ARRAY branch without), i.e. a write-decoder re-expression with the same storage — no clock gating added (76 ICGs on both sides), cells 4 400 → 4 502 (+2.3 %), area within the band. The power figure is on the default-activity basis (D has no SAIF power at E4): DC's default toggle assumptions on the re-expressed write path, not a stimulus-based saving.",
        "cktevo_ethmac__eth_cop": "the two in-progress flags and the two full 32-bit slave address registers (s1_wb_adr_o, s2_wb_adr_o) become a 2-bit transaction_owner plus 11- and 17-bit address-low registers with valid bits, the addresses rebuilt combinationally from the ETH_BASE / MEMORY_BASE constants; the arbitration case over five bits becomes grant / finish wires. Flip-flop bits 174 → 140 (register cells 13 → 14), the same 3 ICGs; SAIF basis on both sides: 0.0649 → 0.0352 mW under the V2 stimulus (−45.7 %) with the wide address registers no longer toggling.",
        "cktevo_usb__usbf_sie_rx": "the RX state machine of usbf_sie_rx is rewritten (427 changed lines: the state constants and registers re-organised, usbf_crc16 unchanged); flip-flop bits 109 → 108 (register cells 23 → 22), 7 ICGs on both sides; the 1.4 % power gain is on the default-activity basis (D has no SAIF power at E4) and below the materiality threshold.",
    }
    for d, k in (("cktevo_risc__btb", 3), ("cktevo_ethmac__eth_cop", 1), ("cktevo_usb__usbf_sie_rx", 1)):
        phi = designs.get(d)["phi"]
        b = baseline(conn, d, phi)
        rows = []
        for c in conn.execute("SELECT c.*, r.arm FROM candidates c JOIN runs r ON r.run_id=c.run_id WHERE r.exp='phase5' AND r.status!='superseded' AND c.design_id=? AND c.verdict='proven' AND COALESCE(c.label,'')!='duplicate'", (d,)):
            c = dict(c)
            ud = P5.uniform_diagnosis(designs, conn, c)
            if ud and ud[0] == "retained" and ud[1].get("power") is not None:
                rows.append((float(ud[1]["power"]), ud[1], c))
        rows.sort(key=lambda x: -x[0])
        suite, name = d.split("_", 1)
        dfiles = sorted(glob.glob(os.path.join(ROOT, "data", "designs", suite, name, "rtl", "*.v")))
        top = []
        for pg, gains, c in rows[:k]:
            e = e4_record(conn, c["cand_id"])
            top.append({"cand_id": c["cand_id"], "arm": c["arm"], "class_final": c["class_final"], "evidence_tags": json.loads(c["subtags_json"] or "[]"),
                        "gains": {m: round(float(v), 4) for m, v in gains.items()}, "power_basis": ("saif" if (b["power_saif_mw"] is not None and e["power_saif_mw"] is not None) else "default"),
                        "D": {"power_saif_mw": b["power_saif_mw"], "power_default_mw": b["power_default_mw"], "icg": ls(b).get("icg_count"), "registers": ls(b).get("registers"), "cells": b["cells"]},
                        "C": {"power_saif_mw": e["power_saif_mw"], "power_default_mw": e["power_default_mw"], "icg": ls(e).get("icg_count"), "registers": ls(e).get("registers"), "cells": e["cells"]},
                        "toggle_rate_v2": "not stored (E4 records keep power_default.rpt only; the SAIF of the lock-step simulation is slimmed after E4)", "module_diff": module_diff(dfiles, c["rtl_path"])})
        out["designs"][d] = {"n_retained_with_power": len(rows), "top": top, "reading": readings.get(d)}
    out["basis_note"] = ("m3.power_basis compares SAIF with SAIF and default with default, never mixed (2026-09-15). D's E4 baseline at Φ_main carries no SAIF power on 13 of the 30 Phase 5 designs — the same 13 designs that have no measured floor: their design SAIF was never built because the SAIF pipeline (scripts/phase2_saif.py) runs on the perturbation records, which these designs do not have — so every power gain on those designs (btb's ≈ 80 % included) is a default-activity figure, while the candidates on them mostly carry SAIF power (btb 800 of 890 E4 records) that has no D counterpart. "
                         "Candidate fix (Phase 6 item 6.10, not run): build D's SAIF from the V2 lock-step stimulus of any proven candidate and re-run D's E4 once per design; then the SAIF basis applies retroactively to every candidate record that has one.")
    return out


# ----------------------------------------------------------------------------- item 4
def item4(cfg, conn):
    src("4 pooled-floor designs", "perturbations (ptype, seq_status per design), data/perturbations/<design>/manifest.json (generator error), evaluations (E4 records of perturbations), noise_floor (floor_source, floor_version phase4)")
    held = [d for ds in cfg["exp5"]["starting_points"].values() for d in ds]
    tier_of = P5.tier_of_design(cfg)
    rows = {}
    for d in held:
        fr = conn.execute("SELECT floor_source FROM noise_floor WHERE floor_version='phase4' AND config='E4' AND metric='area' AND design_id=?", (d,)).fetchone()
        if fr and fr["floor_source"] == "measured":
            continue
        pt = {r[0]: r[1] for r in conn.execute("SELECT ptype, COUNT(*) FROM perturbations WHERE design_id=? GROUP BY ptype", (d,))}
        st = {r[0]: r[1] for r in conn.execute("SELECT seq_status, COUNT(*) FROM perturbations WHERE design_id=? GROUP BY seq_status", (d,))}
        p0 = [r[0] for r in conn.execute("SELECT seq_status FROM perturbations WHERE design_id=? AND ptype='P0_roundtrip'", (d,))]
        ev = conn.execute("SELECT COUNT(*) FROM evaluations e JOIN perturbations p ON p.pert_id=e.pert_id WHERE e.design_id=? AND e.status='ok'", (d,)).fetchone()[0]
        mp = os.path.join(ROOT, "data", "perturbations", d, "manifest.json")
        err = None
        if os.path.exists(mp):
            try:
                err = json.load(open(mp)).get("error")
            except (OSError, ValueError):
                err = "manifest unreadable"
        if not pt:
            reason = f"no perturbation generated: the Pyverilog front end fails on the design ({err}); the text-level renamer (P1_text) is part of the same generator run and was not run either"
        elif st.get("proven", 0) + st.get("proven_rename", 0) == 0:
            reason = "perturbations generated (text-level renamer run: P1_text present) but none SEQ-proven — the re-print P0 is " + (p0[0] if p0 else "absent") + f"; statuses {st}" + ("; router: falsified under harness_version 1 (the formal step's z-reset defect corrected by harness_version 2 — a candidate for re-proof)" if d == "drrtl_router" else "") + ("; LSTM: the catalog reset-port defect fixed 2026-09-18 (harness_version 2)" if d == "drrtl_LSTM" else "")
        else:
            reason = f"perturbations generated and {st.get('proven', 0) + st.get('proven_rename', 0)} proven (text-level renames), but the re-print P0 is {p0[0] if p0 else 'absent'}: the floor pipeline requires the proven re-print, so no noise run was made ({ev} evaluation records)"
        rows[d] = {"tier": tier_of.get(d), "perturbations_by_type": pt, "seq_status": st, "P0_status": p0, "P1_text_run": bool(pt.get("P1_text")), "evaluation_records": ev, "generator_error": err, "reason": reason}
    return {"designs": rows, "n": len(rows),
            "phase6_candidate": "PLAN 6.9 — measure floors for these 13 designs under harness_version 2 (8 text-level renames + 8 reorders each; the text-level renamer needs no Pyverilog parse; the re-print P0 re-proven under v2 where its failure was the harness), report Phase 5 retention under the measured floors as a sensitivity row; the Phase 5 floors stay frozen (floor_version phase4)."}


def render(data):
    i1, i2, i3, i4 = data["item1"], data["item2"], data["item3"], data["item4"]
    L = [f"# Section III — four remaining items ({data['date']}; visible layer only)", "",
         f"Generated {data['generated_at']} by scripts/report_paper_sec3_addendum.py (git {data['git_sha']}); data reports/data/paper_sec3_addendum.json; sources in §S. Mechanism lines are the operator's reading of the comment-stripped, module-by-module diff and are marked as such.", ""]
    if data.get("default_power_basis") is not None:   # REQUEST 2026-09-20 (e) item 1
        dp = data["default_power_basis"]
        L += ["## 0a. Power basis (REQUEST 2026-09-20 (e) item 1)", "", f"Designs whose D has no SAIF power at E4 ({len(dp)}): " + ", ".join(dp) + f". For each of them: *{P5.DEFAULT_POWER_NOTE}*.", ""]
    # 1
    b = i1["baseline"]
    L += ["## 1. mc_rf — the largest single effect", "",
          f"Baseline D at Φ_main = {i1['phi']} ns (eval {b['eval_id']}): area {b['area_um2']:.3f} µm², {b['cells']} cells, SAIF power {b['power_saif_mw']:.4f} mW. {i1['n_records']} proven-perturbation E4 records at Φ_main; the largest area effect is +{100 * i1['largest_area_effect']:.2f} %, shared by {len(i1['records_at_largest'])} records ({i1['records_at_largest_by_ptype']}). Floor row: class {i1['floor_row'].get('area', {}).get('floor_class')}, t_D area {pct(i1['floor_row'].get('area', {}).get('t_d'), 2)} (its own max |δ|, n {i1['floor_row'].get('area', {}).get('n')}).", "",
          "| pert_id | type | SEQ | clock ns | area µm² | cells | SAIF power mW | area δ | power δ |", "|---|---|---|---|---|---|---|---|---|"]
    for r in i1["records_at_largest"][:6] + [r for r in i1["p0_records"] if r not in i1["records_at_largest"]]:
        L.append(f"| {r['pert_id']} | {r['ptype']} | {r['seq_status']} | {r['clock_ns']} | {r['area_um2']:.3f} | {r['cells']} | {r['power_saif_mw']:.5f} | {pct(r['area_rel'], 2)} | {pct(r['power_rel'], 1)} |")
    L += ["", f"The largest P0 record: " + "; ".join(f"{r['pert_id']} ({r['seq_status']}, {r['clock_ns']} ns): area {r['area_um2']:.3f} ({pct(r['area_rel'], 2)}), power {r['power_saif_mw']:.5f} mW ({pct(r['power_rel'], 1)})" for r in i1["p0_records"]) + ".",
          f"Statement for the paper: {i1['statement']}", "",
          "All records (area-descending): " + "; ".join(f"{r['ptype']} {pct(r['area_rel'], 2)} / {pct(r['power_rel'], 1)}" for r in i1["records"]) + ".", ""]
    # 2
    L += ["## 2. ticket_machine and fsm_encode best objects", ""]
    for des in ("rtlopt_ticket_machine", "rtlopt_fsm_encode"):
        v = i2[des]
        L += [f"**{des} — {v['cand_id']}** (class rule / LLM / final: {v['class']['rule']} / {v['class']['llm']} / {v['class']['final']}; E4 label {v['label']})", "",
              f"- rules-v2 evidence tags: {v['evidence_tags']}",
              f"- flip-flop count (DC E4 registers) D → C: {v['E4']['D']['registers']} → {v['E4']['C']['registers']}; cells {v['E4']['D']['cells']} → {v['E4']['C']['cells']}; area {v['E4']['D']['area_um2']:.3f} → {v['E4']['C']['area_um2']:.3f} µm² ({pct(v['E4']['area_gain'], 1)} gain)",
              f"- module diff (comment-stripped): {v['module_diff']}",
              f"- reading of the diff (operator): {v['reading']}", ""]
    L += [f"Class: {i2['class_rule_note']}", ""]
    # 3
    L += ["## 3. Largest retained power gains on btb, eth_cop and usbf_sie_rx", "",
          f"Power basis: {i3['basis_note']}", "",
          f"Designs whose E4 baseline at Φ_main has no SAIF power (power basis default for every candidate): {i3['designs_without_saif_baseline']}.", ""]
    for d, v in i3["designs"].items():
        L += [f"**{d}** — {v['n_retained_with_power']} retained candidates with a power gain; the largest:", "",
              "| candidate | arm | class | gains area / WNS / power | basis | D: SAIF / default mW, ICG, regs, cells | C: SAIF / default mW, ICG, regs, cells | evidence tags | modules changed |", "|---|---|---|---|---|---|---|---|---|"]
        for t in v["top"]:
            g = t["gains"]; D, Cc = t["D"], t["C"]
            L.append(f"| {t['cand_id']} | {t['arm']} | {t['class_final']} | {pct(g.get('area'), 2)} / {pct(g.get('wns'), 2)} / {pct(g.get('power'), 1)} | {t['power_basis']} | {D['power_saif_mw']} / {D['power_default_mw']:.4f}, {D['icg']}, {D['registers']}, {D['cells']} | {Cc['power_saif_mw']} / {Cc['power_default_mw']:.4f}, {Cc['icg']}, {Cc['registers']}, {Cc['cells']} | {t['evidence_tags']} | " + ", ".join(f"{m} {x['status']}" + (f" ({x.get('changed_lines')} lines)" if x.get('changed_lines') else "") for m, x in t["module_diff"].items()) + " |")
        L += ["", f"Toggle rate under the V2 stimulus: {v['top'][0]['toggle_rate_v2'] if v['top'] else '-'}.", f"Mechanism (operator's reading of the diff): {v['reading']}", ""]
    # 4
    L += ["## 4. The 13 designs on the pooled floor", "", "| design | tier | perturbations by type | SEQ status | P0 | P1_text run | evaluation records | reason no floor was measured |", "|---|---|---|---|---|---|---|---|"]
    for d, v in i4["designs"].items():
        L.append(f"| {d} | {v['tier']} | {v['perturbations_by_type'] or 'none'} | {v['seq_status'] or '-'} | {v['P0_status'] or '-'} | {'yes' if v['P1_text_run'] else 'no'} | {v['evaluation_records']} | {v['reason']} |")
    L += ["", f"Phase 6 candidate: {i4['phase6_candidate']}", "", "## S. Sources", ""] + [f"- {s['item']}: `{s['source']}`" for s in data["sources"]] + [""]
    return "\n".join(L)


def main():
    cfg = C.load()
    conn = db.connect(cfg=cfg)
    data = {"date": datetime.date.today().isoformat(), "generated_at": datetime.datetime.now().isoformat(timespec="minutes"), "git_sha": C.git_sha()}
    data["default_power_basis"] = P5.default_power_basis_designs(cfg, conn)   # REQUEST 2026-09-20 (e) item 1
    data["item1"] = item1(conn)
    data["item2"] = item2(conn)
    data["item3"] = item3(cfg, conn)
    data["item4"] = item4(cfg, conn)
    data["sources"] = SOURCES
    js = os.path.join(ROOT, "reports", "data", "paper_sec3_addendum.json")
    md = os.path.join(ROOT, "reports", "paper_sec3_addendum.md")
    with open(js, "w") as f:
        json.dump(data, f, indent=1, default=str)
    with open(md, "w") as f:
        f.write(render(data))
    print(f"written {md} and {js}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
