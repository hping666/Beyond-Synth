"""Stage D of the Phase 5 reports (scripts/report_hidden.py; spec 06 §3): speculation rates per hidden configuration and combined,
the reverse error on the audit sample, gains under the hidden configurations next to the visible one, coverage — computed on
fake visible and hidden databases in a temporary directory (the project's hidden database is never opened by a test)."""
import copy
import importlib.util
import json
from pathlib import Path

from src import config as C
from src.db import core as db


def load():
    spec = importlib.util.spec_from_file_location("report_hidden", str(Path(C.ROOT) / "scripts" / "report_hidden.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stage_d_speculation_reverse_error_coverage_and_rendering(tmp_path):
    mod = load()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["exp5"]["starting_points"] = {"small": [], "medium": [], "large": ["l1"]}
    vis = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    hid = db.connect(path=str(tmp_path / "results" / "hidden" / "hidden.sqlite"))
    vis.execute("INSERT INTO designs (design_id, suite, name, path, loc, e4_synthesizable, split, phi_main_ns_nangate45, phi_main_ns_asap7, phi_main_ns_sky130hd, created_at, git_sha, cfg_hash) VALUES ('l1','x','l1','p',1,1,'held',1.0,0.5,NULL,'t','g','c')")
    fv = cfg["noise"].get("floor_version")
    for metric, t in (("area", 0.01), ("wns", 0.005), ("power_saif", 0.02)):
        db.insert(vis, "noise_floor", {"design_id": "l1", "config": "E4", "metric": metric, "sigma_robust": 0.002, "t_d": t, "floor_class": "quiet", "floor_source": "measured", "floor_version": fv})
        for h in ("H1", "H2a"):
            db.insert(hid, "noise_floor", {"design_id": "l1", "config": h, "metric": metric, "sigma_robust": 0.003, "t_d": t, "floor_class": "quiet", "floor_source": "measured", "floor_version": fv})
    base_hist = json.dumps({"NAND2_X1": 100, "DFF_X1": 20})
    def ev(conn, config, clock, cand_id, area, hist, base=False):
        db.insert(conn, "evaluations", {"design_id": "l1", "cand_id": cand_id, "is_baseline": int(base), "config": config, "lib": cfg["configs"][config].get("lib"), "clock_ns": clock,
                                        "area_um2": area, "cells": 100, "wns_ns": 0.05, "tns_ns": 0.0, "power_saif_mw": 1.0, "dc_seconds": 10.0, "status": "ok",
                                        "raw_dir": f"/{'h' if conn is hid else 'v'}/{config}/{cand_id or 'base'}", "hist_json": json.dumps(hist)})
    ev(vis, "E4", 1.0, None, 100.0, {"NAND2_X1": 100, "DFF_X1": 20}, base=True)
    ev(hid, "H1", 0.1, None, 120.0, {"NAND2_X1": 120, "DFF_X1": 20}, base=True)
    ev(hid, "H2a", 0.5, None, 50.0, {"NAND2_X1": 100, "DFF_X1": 20}, base=True)
    db.insert(vis, "runs", {"run_id": "r1", "exp": "phase5", "arm": "M", "design_id": "l1", "seed": 1, "llm_model": "gpt-5.6-terra", "status": "done", "started_at": "t"})
    def cand(cid, accepted, e4_area, e4_hist, h1=None, h2a=None, gen=1, cls="b"):
        db.insert(vis, "candidates", {"cand_id": cid, "run_id": "r1", "design_id": "l1", "gen": gen, "arm": "M", "llm_model": "gpt-5.6-terra", "verdict": "proven", "label": "retained" if accepted else "noise", "accepted": accepted, "class_final": cls})
        ev(vis, "E4", 1.0, cid, e4_area, e4_hist)
        if h1:
            ev(hid, "H1", 0.1, cid, h1[0], h1[1])
        if h2a:
            ev(hid, "H2a", 0.5, cid, h2a[0], h2a[1])
    cand("c_solid", 1, 92.0, {"NAND2_X1": 70, "DFF_X1": 20}, h1=(110.0, {"NAND2_X1": 90, "DFF_X1": 20}), h2a=(46.0, {"NAND2_X1": 70, "DFF_X1": 20}))     # retained everywhere
    cand("c_spec", 1, 92.0, {"NAND2_X1": 71, "DFF_X1": 20}, h1=(119.9, {"NAND2_X1": 120, "DFF_X1": 20, "INV_X1": 1}), h2a=(46.0, {"NAND2_X1": 71, "DFF_X1": 20}), gen=2, cls="c1")   # vetoed by H1 (converged, no gain)
    cand("c_none", 1, 92.0, {"NAND2_X1": 72, "DFF_X1": 20})                                                                                            # accepted but no hidden record yet
    cand("c_audit", 0, 99.9, {"NAND2_X1": 100, "DFF_X1": 20, "INV_X1": 1}, h1=(100.0, {"NAND2_X1": 80, "DFF_X1": 20}))                                    # rejected visibly, retained under H1: reverse error
    data = mod.build(cfg, vis, hid)
    assert data["candidates_proven"] == 4 and data["retained_uniform"] == 3 and data["accepted_arms"] == 3
    g = data["speculation"]["uniform_retained"]["by_arm"]["large|gpt-5.6-terra|M"]
    assert g["n"] == 3 and g["with_records"] == 2 and g["H1"] == {"n": 2, "vetoed": 1, "rate": 0.5} and g["H2a"] == {"n": 2, "vetoed": 0, "rate": 0.0} and g["combined_rate"] == 0.5
    assert data["speculation"]["uniform_retained"]["by_gen"]["2"]["H1"]["rate"] == 1.0 and data["speculation"]["uniform_retained"]["by_class"]["b"]["H1"]["rate"] == 0.0
    assert data["reverse_error"]["H1"] == {"n": 1, "acceptable_hidden": 1, "rate": 1.0} and data["reverse_error"]["H2a"]["n"] == 0
    assert data["coverage"]["H1"] == {"retained_expected": 3, "retained_with_record": 2, "accepted_expected": 3, "accepted_with_record": 2}
    assert data["coverage"]["H2b"]["retained_expected"] == 0                                                                   # no sky130 knee: nothing expected
    assert data["floors"]["H1"]["designs_with_floor"] == 1 and abs(data["floors"]["H1"]["sigma_area_median"] - 0.003) < 1e-9
    gains = data["gains"]["large|gpt-5.6-terra|M"]
    assert gains["visible"]["n"] == 3 and abs(gains["visible"]["mean"] - 0.08) < 1e-6 and gains["H2a"]["n"] == 2 and abs(gains["H2a"]["mean"] - 0.08) < 1e-6
    text = mod.render(data)
    assert "### D.1" in text and "| large | gpt-5.6-terra | M | 3 | 2 | 50.0 % (1/2)" in text and "### D.4" in text and "| H1 | 1 | 1 | 100.0 % |" in text
    out = tmp_path / "reports"
    out.mkdir()
    (out / "phase5.md").write_text("# Phase 5 report (visible part)\n\nbody\n")
    mod.write_reports(text, data, str(out))
    full = (out / "phase5.md").read_text()
    assert full.startswith("# Phase 5 report (visible part)") and mod.HIDDEN_SECTION in full and (out / "phase5_hidden.md").exists()
    mod.write_reports(text.replace("### D.1", "### D.1 (again)"), data, str(out))
    assert (out / "phase5.md").read_text().count(mod.HIDDEN_SECTION) == 1 and "(again)" in (out / "phase5.md").read_text()       # the hidden section is replaced, not duplicated
    saved = json.loads((out / "data" / "phase5_hidden.json").read_text())
    assert "per_candidate" not in saved and saved["per_candidate_n"] == 4
    # the command line: refused without the marker; with the marker it runs on the given databases only
    status = tmp_path / "STATUS.md"
    status.write_text("PHASE5_COMPLETE: no\n")
    assert mod.main(["--status-file", str(status), "--visible-db", str(tmp_path / "results" / "db" / "results.sqlite"), "--hidden-db", str(tmp_path / "results" / "hidden" / "hidden.sqlite"), "--out", str(out)]) == 3
    status.write_text("PHASE5_COMPLETE: yes\n")
    assert mod.main(["--status-file", str(status), "--visible-db", str(tmp_path / "results" / "db" / "results.sqlite"), "--hidden-db", str(tmp_path / "results" / "hidden" / "hidden.sqlite"), "--out", str(out)]) == 0
