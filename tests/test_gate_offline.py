"""Bidirectional tests of the perturbation gate collector (src/noise/gate.py): verdicts from equiv.json records,
the alpha-renaming rule (accepted only when the round trip is SEQ-proven and the inverse rename reproduces it byte
for byte), and the perturbations table upsert."""
import copy
import json
from pathlib import Path

from src import config as C
from src.db import core as db
from src.noise import gate as GT

RT = "module top(input a, output y);\n  wire t;\n  assign t = a;\n  assign y = t;\nendmodule\n"


def setup(tmp_path, p1_text, rt_verdict="proven", p1_verdict="falsified"):
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    root = tmp_path / "perts"
    d = root / "s_top"
    d.mkdir(parents=True)
    (d / "roundtrip.v").write_text(RT)
    (d / "P1_rename_0.v").write_text(p1_text)
    manifest = {"design_id": "s_top", "roundtrip": {"pert_id": "p0", "path": str(d / "roundtrip.v")},
                "perturbations": [{"pert_id": "p1", "ptype": "P1_rename", "k": 0, "path": str(d / "P1_rename_0.v"), "details": {"renamed": {"top": {"t": "alpha_0"}}}}]}
    (d / "manifest.json").write_text(json.dumps(manifest))
    for cid, verdict in (("p0", rt_verdict), ("p1", p1_verdict)):
        eq = tmp_path / "results" / "raw" / "s_top" / "EQ" / cid
        eq.mkdir(parents=True)
        (eq / "equiv.json").write_text(json.dumps({"cand_id": cid, "verdict": verdict, "v1_status": "ok", "v2_status": "identical", "v3_status": verdict}))
    conn = db.connect(path=str(tmp_path / "r.sqlite"))
    design = {"design_id": "s_top", "suite": "s", "name": "top"}
    return cfg, conn, design, root, manifest


def test_alpha_rename_accepted_only_with_a_proven_round_trip(tmp_path):
    p1 = RT.replace("wire t;", "wire alpha_0;").replace("assign t = a;", "assign alpha_0 = a;").replace("assign y = t;", "assign y = alpha_0;")
    cfg, conn, design, root, manifest = setup(tmp_path, p1)
    assert GT.rename_is_alpha(manifest, manifest["perturbations"][0], root)
    (root / "s_top" / "P1_rename_0.v").write_text(p1.replace("assign y = alpha_0;", "assign y =\n    alpha_0;"))  # different line wrapping only
    assert GT.rename_is_alpha(manifest, manifest["perturbations"][0], root)
    (root / "s_top" / "P1_rename_0.v").write_text(p1)
    s = GT.collect(conn, cfg, [design], root)
    assert s["s_top"]["roundtrip"] == "proven" and s["s_top"]["counts"] == {"proven": 1, "proven_rename": 1}  # the proven entry is the round trip itself
    rows = {r[0]: (r[1], r[2]) for r in conn.execute("SELECT pert_id, ptype, seq_status FROM perturbations WHERE design_id='s_top'")}
    assert rows["p0"] == ("P0_roundtrip", "proven")  # P0 is in the table and therefore part of the noise runs
    assert conn.execute("SELECT seq_status FROM perturbations WHERE pert_id='p1'").fetchone()[0] == "proven_rename"


def test_no_acceptance_when_the_rename_is_not_pure_or_the_round_trip_failed(tmp_path):
    p1 = RT.replace("wire t;", "wire alpha_0;").replace("assign t = a;", "assign alpha_0 = ~a;").replace("assign y = t;", "assign y = alpha_0;")
    cfg, conn, design, root, manifest = setup(tmp_path, p1)
    assert not GT.rename_is_alpha(manifest, manifest["perturbations"][0], root)  # the text changed beyond names
    s = GT.collect(conn, cfg, [design], root)
    assert s["s_top"]["counts"]["falsified"] == 1
    assert conn.execute("SELECT seq_status FROM perturbations WHERE pert_id='p1'").fetchone()[0] == "falsified"
    pure = RT.replace("wire t;", "wire alpha_0;").replace("assign t = a;", "assign alpha_0 = a;").replace("assign y = t;", "assign y = alpha_0;")
    cfg, conn, design, root, manifest = setup(tmp_path / "b", pure, rt_verdict="inconclusive")
    s = GT.collect(conn, cfg, [design], root)
    assert s["s_top"]["counts"]["falsified"] == 1  # a pure rename of an unproven round trip stays falsified
    cfg, conn, design, root, manifest = setup(tmp_path / "c", pure, p1_verdict="proven")
    assert GT.collect(conn, cfg, [design], root)["s_top"]["counts"] == {"proven": 2}  # SEQ-proven renames are just proven
