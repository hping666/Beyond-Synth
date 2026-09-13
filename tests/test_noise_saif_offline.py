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
    # the VCD only with prune_eq_vcd_after_saif (off by default until the user decides)
    cfg["retention"].update(prune_eq_build_after_saif=False, prune_eq_vcd_after_saif=False)
    assert S.prune_eq_scratch(cfg, "s_top") == 0 and (r1 / "v2_sim" / "csrc").exists() and (r1 / "v2_sim" / "sim.vcd").exists()
    cfg["retention"].update(prune_eq_build_after_saif=True, prune_eq_vcd_after_saif=False)
    freed = S.prune_eq_scratch(cfg, "s_top")
    assert freed == 150 * 3 and not (r1 / "v2_sim" / "csrc").exists() and not (r1 / "v2_sim" / "simv").exists()
    assert (r1 / "v2_sim" / "sim.vcd").exists() and (r0 / "v2_sim" / "sim.vcd").exists() and (r2 / "v2_sim" / "sim.vcd").exists()
    r4 = tmp_path / "results" / "raw" / "s_top" / "EQ" / "p4"
    assert (r4 / "v2_sim" / "csrc").exists()  # no SAIF from p4 (no VCD) -> its build is kept
    cfg["retention"].update(prune_eq_vcd_after_saif=True)
    assert S.prune_eq_scratch(cfg, "s_top") == 1006 * 3 and not (r1 / "v2_sim" / "sim.vcd").exists() and not (r0 / "v2_sim" / "sim.vcd").exists()
    assert (r1 / "equiv.json").exists() and S.prune_eq_scratch(cfg, "s_top") == 0  # records stay; idempotent
