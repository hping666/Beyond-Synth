"""Bidirectional tests of the SAIF step (src/noise/saif.py): SAIFs are built from the latest equivalence record of
D (round trip, u_d) and of each proven perturbation (u_c) with a fake converter; records without a VCD are reported;
scratch pruning removes VCS builds always and VCDs only when their SAIF exists and the retention flag is on."""
import copy
import json
from pathlib import Path

from src import config as C
from src.db import core as db
from src.noise import saif as S


def make_record(root, design_id, cand_id, with_vcd=True):
    d = root / "raw" / design_id / "EQ" / cand_id
    sim = d / "v2_sim"
    (sim / "csrc").mkdir(parents=True)
    (sim / "csrc" / "x.o").write_bytes(b"0" * 100)
    (sim / "simv").write_bytes(b"1" * 50)
    vcd = sim / "sim.vcd"
    if with_vcd:
        vcd.write_bytes(b"$date\n" + b"x" * 1000)
    (d / "equiv.json").write_text(json.dumps({"cand_id": cand_id, "verdict": "proven", "vcd_path": str(vcd)}))
    return d


def test_build_prune_and_missing(tmp_path, monkeypatch):
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    monkeypatch.setattr(S.G, "PERT_DIR", tmp_path / "perts")
    pert_root = tmp_path / "perts" / "s_top"
    pert_root.mkdir(parents=True)
    (pert_root / "manifest.json").write_text(json.dumps({"design_id": "s_top", "roundtrip": {"pert_id": "p0", "path": "x"}, "perturbations": []}))
    for pid, st in (("p1", "proven"), ("p2", "proven_rename"), ("p3", "falsified"), ("p4", "proven")):
        db.insert(conn, "perturbations", {"pert_id": pid, "design_id": "s_top", "ptype": "P1_rename", "path": "x", "seq_status": st})
    r0 = make_record(tmp_path / "results", "s_top", "p0")
    r1 = make_record(tmp_path / "results", "s_top", "p1")
    r2 = make_record(tmp_path / "results", "s_top", "p2")
    make_record(tmp_path / "results", "s_top", "p4", with_vcd=False)
    calls = []

    def fake_convert(vcd, saif, instance, cfg_):
        calls.append((str(vcd), instance))
        Path(saif).write_text("SAIF")
        return {"status": "ok", "saif": str(saif), "instance": instance}

    proven = S.proven_ids(conn, "s_top")
    assert proven == {"p1", "p2", "p4"}
    res = S.build_for_design({"design_id": "s_top"}, proven, cfg, convert=fake_convert)
    assert res["design"]["instance"] == S.D_INSTANCE and res["design"]["saif"].endswith("D.saif")
    assert set(res["perturbations"]) == {"p1", "p2", "p4"} and res["missing"] == ["p4"]  # falsified p3 gets no SAIF, p4 has no VCD
    assert res["perturbations"]["p1"]["instance"] == S.C_INSTANCE and len(calls) == 3
    assert S.load_saif("s_top")["design"]["source_record"] == str(r0)
    assert S.build_for_design({"design_id": "s_top"}, proven, cfg, convert=fake_convert)["perturbations"]["p1"]["status"] == "exists" and len(calls) == 3  # idempotent
    # pruning: nothing without the flags; the VCS build only with prune_eq_build_after_saif and only where a SAIF exists;
    # the VCD only with prune_eq_vcd_after_saif, power ingested from that SAIF, and the record not kept (DECISIONS 2026-09-14)
    cfg["retention"].update(prune_eq_build_after_saif=False, prune_eq_vcd_after_saif=False)
    assert S.prune_eq_scratch(cfg, "s_top", conn) == 0 and (r1 / "v2_sim" / "csrc").exists() and (r1 / "v2_sim" / "sim.vcd").exists()
    cfg["retention"].update(prune_eq_build_after_saif=True, prune_eq_vcd_after_saif=False)
    freed = S.prune_eq_scratch(cfg, "s_top", conn)
    assert freed == 150 * 3 and not (r1 / "v2_sim" / "csrc").exists() and not (r1 / "v2_sim" / "simv").exists()
    assert (r1 / "v2_sim" / "sim.vcd").exists() and (r0 / "v2_sim" / "sim.vcd").exists() and (r2 / "v2_sim" / "sim.vcd").exists()
    r4 = tmp_path / "results" / "raw" / "s_top" / "EQ" / "p4"
    assert (r4 / "v2_sim" / "csrc").exists()  # no SAIF from p4 (no VCD) -> its build is kept
    cfg["retention"].update(prune_eq_vcd_after_saif=True, vcd_keep_verdicts=["sim_fail", "falsified"], vcd_keep_sample_frac=0.0)
    assert S.prune_eq_scratch(cfg, "s_top", conn) == 0  # SAIFs exist but no power was ingested yet -> every VCD stays
    n = [0]

    def ev(pert, is_base):
        n[0] += 1
        db.insert(conn, "evaluations", {"design_id": "s_top", "pert_id": pert, "is_baseline": is_base, "config": "E4", "lib": "n", "clock_ns": 1.0,
                                        "area_um2": 1.0, "cells": 1, "wns_ns": 0.0, "tns_ns": 0.0, "power_saif_mw": 0.5, "status": "ok", "raw_dir": f"/y/{n[0]}", "hist_json": "{}"})
    ev(None, 1)      # D's power from the round-trip SAIF
    ev("p1", 0)      # p1's power
    (r2 / "equiv.json").write_text(json.dumps({"cand_id": "p2", "verdict": "falsified", "vcd_path": str(r2 / "v2_sim" / "sim.vcd")}))
    ev("p2", 0)
    freed = S.prune_eq_scratch(cfg, "s_top", conn)
    assert freed == 1006 * 2 and not (r0 / "v2_sim" / "sim.vcd").exists() and not (r1 / "v2_sim" / "sim.vcd").exists()
    assert (r2 / "v2_sim" / "sim.vcd").exists()  # falsified: kept for diagnosis
    assert (r1 / "equiv.json").exists() and S.prune_eq_scratch(cfg, "s_top", conn) == 0  # records stay; idempotent
    cfg["retention"].update(vcd_keep_sample_frac=1.0)
    from src.equiv import saif as ES
    assert ES.keep_vcd(cfg, r1, "proven") is True and ES.keep_vcd({"retention": {"vcd_keep_sample_frac": 0.0}}, r1, "proven") is False


def test_finalize_vcd_writes_saifs_and_deletes_the_vcd(tmp_path):
    """The stack's own SAIF step: both instances converted, the VCD deleted unless the verdict or the sample keeps it."""
    from src.equiv import saif as ES
    cfg = {"retention": {"vcd_to_scratch": True, "vcd_keep_verdicts": ["sim_fail", "falsified"], "vcd_keep_sample_frac": 0.0}}
    calls = []

    def fake(vcd, saif, instance, cfg_):
        calls.append(instance)
        Path(saif).write_text("SAIF")
        return {"status": "ok", "saif": str(saif), "instance": instance}
    job = tmp_path / "rec"
    (job / "v2_sim").mkdir(parents=True)
    vcd = job / "v2_sim" / "sim.vcd"
    vcd.write_bytes(b"x" * 10)
    rec = {"vcd_path": str(vcd), "verdict": "proven"}
    ES.finalize_vcd(job, rec, cfg, convert=fake)
    assert calls == [ES.D_INSTANCE, ES.C_INSTANCE] and rec["saif_d"].endswith("saif_d.saif") and rec["saif_c"].endswith("saif_c.saif")
    assert rec["vcd_path"] is None and rec["vcd_deleted"] is True and not vcd.exists()
    vcd.write_bytes(b"x" * 10)
    rec = {"vcd_path": str(vcd), "verdict": "falsified"}
    ES.finalize_vcd(job, rec, cfg, convert=fake)
    assert rec["vcd_deleted"] is False and vcd.exists() and rec["vcd_path"] == str(vcd)  # kept for diagnosis
    rec = {"vcd_path": str(vcd), "verdict": "proven"}
    ES.finalize_vcd(job, rec, {"retention": {"vcd_to_scratch": False}}, convert=fake)
    assert "saif_d" not in rec and vcd.exists()  # switched off: nothing happens

    def failing(vcd, saif, instance, cfg_):
        return {"status": "failed", "saif": None, "instance": instance}
    rec = {"vcd_path": str(vcd), "verdict": "proven"}
    ES.finalize_vcd(job, rec, cfg, convert=failing)
    assert rec["vcd_deleted"] is False and vcd.exists()  # a failed conversion never deletes the VCD
