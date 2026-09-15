"""Bidirectional tests of the retention policy (src/eval/service.py: prune_scratch): scratch of ok records is
removed, everything else stays; failed records are untouched; the policy switch turns it off."""
import copy
import json
from pathlib import Path

from src import config as C
from src.eval.service import prune_scratch

CFG = C.load()


def make_job(root, status):
    job = root / "d1" / "E4" / "abc123"
    for d in ("outputs/dc_work/csrc", "outputs/mw_design", "outputs/reports", "inputs"):
        (job / d).mkdir(parents=True)
    (job / "outputs/dc_work/command.log").write_text("x")
    (job / "outputs/dc_work/csrc/a.o").write_bytes(b"\0" * 10)
    (job / "outputs/mw_design/lib").write_text("x")
    (job / "outputs/reports/qor.rpt").write_text("Design Area: 1")
    (job / "outputs/reports/netlist.v").write_text("module d1; endmodule")
    (job / "outputs/dc_shell.log").write_text("log")
    (job / "meta.json").write_text(json.dumps({"status": status}))
    return job


def test_ok_record_loses_scratch_and_keeps_results(tmp_path):
    job = make_job(tmp_path, "ok")
    removed = prune_scratch(job, CFG)
    assert sorted(Path(p).name for p in removed) == ["dc_work", "mw_design"]
    assert not (job / "outputs/dc_work").exists() and not (job / "outputs/mw_design").exists()
    for kept in ("outputs/reports/qor.rpt", "outputs/reports/netlist.v", "outputs/dc_shell.log", "meta.json", "inputs"):
        assert (job / kept).exists(), kept
    assert prune_scratch(job, CFG) == []  # idempotent


def test_failed_record_is_never_pruned(tmp_path):
    for status in ("failed", "eval_failed", "compile_failed"):
        job = make_job(tmp_path / status, status)
        assert prune_scratch(job, CFG) == []
        assert (job / "outputs/dc_work/command.log").exists()


def test_policy_switch_and_missing_meta(tmp_path):
    off = copy.deepcopy(CFG)
    off["retention"]["prune_dc_work_after_ingest"] = False
    job = make_job(tmp_path, "ok")
    assert prune_scratch(job, off) == [] and (job / "outputs/dc_work").exists()
    (job / "meta.json").unlink()
    assert prune_scratch(job, CFG) == [] and (job / "outputs/dc_work").exists()


def _eq_record(root, name, verdict, vcd_bytes=b"$date x $end\n" * 200, with_cex=True):
    """An equivalence record with a lock-step VCD and a VCS build, as src/equiv/stack.py leaves it."""
    d = root / "rtllm_d" / "EQ" / name
    sim = d / "v2_sim"
    (sim / "csrc").mkdir(parents=True)
    (sim / "simv.daidir").mkdir()
    (sim / "csrc" / "a.o").write_bytes(b"\0" * 100)
    (sim / "simv.daidir" / "b").write_bytes(b"\0" * 100)
    (sim / "simv").write_bytes(b"\0" * 50)
    (sim / "sim.vcd").write_bytes(vcd_bytes)
    (sim / "sim.log").write_text("log")
    if with_cex:
        (d / "v3_seq").mkdir()
        (d / "v3_seq" / "cex.txt").write_text("counterexample")
    (d / "equiv.json").write_text(json.dumps({"verdict": verdict, "vcd_path": str(sim / "sim.vcd"), "counterexample_path": str(d / "v3_seq" / "cex.txt") if with_cex else None}))
    return d


def test_nonproven_retention_rule_both_directions(tmp_path):
    """DECISIONS 2026-09-14 (user): a falsified record loses its VCD (the counterexample stays), a sim_fail record's VCD is
    gzip-compressed losslessly, every non-proven record loses its VCS build; proven records and the logs are untouched;
    the switches turn each part off."""
    import gzip
    from src.noise import saif as NS
    cfg = copy.deepcopy(CFG)
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    cfg["retention"].update(vcd_keep_verdicts=["sim_fail"], vcd_compress_kept=True, prune_eq_build_nonproven=True)
    raw = tmp_path / "results" / "raw"
    fals = _eq_record(raw, "r_fals", "falsified")
    simf = _eq_record(raw, "r_simf", "sim_fail", vcd_bytes=b"$var wire 1 ! x $end\n" * 500)
    prov = _eq_record(raw, "r_prov", "proven")
    rej = _eq_record(raw, "r_rej", "rejected", with_cex=False)
    running = _eq_record(raw, "r_run", None)
    out = NS.prune_nonproven_scratch(cfg, "rtllm_d")
    assert out["vcd_deleted"] == 1 and out["vcd_compressed"] == 1 and out["builds"] == 6 and out["freed"] > 0   # builds: csrc + daidir of fals, simf, rej
    assert not (fals / "v2_sim" / "sim.vcd").exists() and (fals / "v3_seq" / "cex.txt").exists() and (fals / "v2_sim" / "sim.log").exists()
    rec = json.loads((fals / "equiv.json").read_text())
    assert rec["vcd_deleted"] is True and rec["vcd_path"] is None and "falsified" in rec["vcd_deleted_reason"] and rec["retention_log"]
    gz = simf / "v2_sim" / "sim.vcd.gz"
    assert gz.exists() and not (simf / "v2_sim" / "sim.vcd").exists() and gzip.open(gz, "rb").read() == b"$var wire 1 ! x $end\n" * 500
    rec = json.loads((simf / "equiv.json").read_text())
    assert rec["vcd_compressed"] is True and rec["vcd_path"] == str(gz)
    for d in (fals, simf, rej):
        assert not (d / "v2_sim" / "csrc").exists() and not (d / "v2_sim" / "simv.daidir").exists() and not (d / "v2_sim" / "simv").exists()
    assert (prov / "v2_sim" / "sim.vcd").exists() and (prov / "v2_sim" / "csrc").exists() and (prov / "v2_sim" / "simv").exists()   # proven: the other rule decides
    assert (running / "v2_sim" / "sim.vcd").exists() and (running / "v2_sim" / "csrc").exists()                                  # no verdict yet: untouched
    assert (rej / "v2_sim" / "sim.vcd").exists()                                                                                   # rejected VCDs are not part of the decision
    # switches off: nothing happens
    cfg["retention"].update(vcd_keep_verdicts=["sim_fail", "falsified"], vcd_compress_kept=False, prune_eq_build_nonproven=False)
    fals2 = _eq_record(raw, "r_fals2", "falsified")
    out2 = NS.prune_nonproven_scratch(cfg, "rtllm_d")
    assert out2 == {"freed": 0, "vcd_deleted": 0, "vcd_compressed": 0, "builds": 0} and (fals2 / "v2_sim" / "sim.vcd").exists()


def test_finalize_vcd_compresses_kept_and_drops_falsified(tmp_path):
    """At record time: with the new switches a kept sim_fail VCD is gzipped and a falsified VCD deleted after the SAIFs."""
    from src.equiv import saif as ES
    cfg = copy.deepcopy(CFG)
    cfg["retention"].update(vcd_to_scratch=True, vcd_keep_verdicts=["sim_fail"], vcd_compress_kept=True, vcd_keep_sample_frac=0.0, sim_fail_vcd_sample={"frac": 1.0, "seed": 1})

    def fake_convert(vcd, saif, instance, cfg_):
        Path(saif).write_text("saif")
        return {"status": "ok", "saif": str(saif)}
    for verdict, kept in (("sim_fail", True), ("falsified", False)):
        job = tmp_path / verdict
        job.mkdir()
        vcd = job / "sim.vcd"
        vcd.write_bytes(b"$enddefinitions $end\n" * 300)
        rec = ES.finalize_vcd(job, {"verdict": verdict, "vcd_path": str(vcd)}, cfg, convert=fake_convert)
        if kept:
            assert rec["vcd_deleted"] is False and rec["vcd_compressed"] is True and rec["vcd_path"].endswith(".vcd.gz") and Path(rec["vcd_path"]).exists() and not vcd.exists()
        else:
            assert rec["vcd_deleted"] is True and rec["vcd_path"] is None and not vcd.exists()


def test_retain_vcd_early_return_rules(tmp_path):
    """A record that ends at V2 (sim_fail) keeps its VCD gzip-compressed, a falsified one loses it, an error record keeps it
    untouched, and the compression switch turns the compression off (both directions; defect of 2026-09-15)."""
    from src.equiv import saif as ES
    cfg = copy.deepcopy(CFG)
    cfg["retention"].update(vcd_keep_verdicts=["sim_fail"], vcd_compress_kept=True, sim_fail_vcd_sample={"frac": 1.0, "seed": 1})

    def rec_with_vcd(name, verdict):
        job = tmp_path / name
        job.mkdir()
        vcd = job / "sim.vcd"
        vcd.write_bytes(b"$enddefinitions $end\n" * 300)
        return job, vcd, {"verdict": verdict, "vcd_path": str(vcd)}
    job, vcd, rec = rec_with_vcd("sim_fail", "sim_fail")
    ES.retain_vcd(job, rec, cfg)
    assert rec["vcd_compressed"] is True and rec["vcd_deleted"] is False and rec["vcd_path"].endswith(".vcd.gz") and Path(rec["vcd_path"]).exists() and not vcd.exists()
    job, vcd, rec = rec_with_vcd("falsified", "falsified")
    ES.retain_vcd(job, rec, cfg)
    assert rec["vcd_deleted"] is True and rec["vcd_path"] is None and not vcd.exists()
    job, vcd, rec = rec_with_vcd("error", "error")
    ES.retain_vcd(job, rec, cfg)
    assert vcd.exists() and "vcd_compressed" not in rec and "vcd_deleted" not in rec
    cfg["retention"]["vcd_compress_kept"] = False
    job, vcd, rec = rec_with_vcd("sim_fail_off", "sim_fail")
    ES.retain_vcd(job, rec, cfg)
    assert vcd.exists() and rec["vcd_path"] == str(vcd) and "vcd_compressed" not in rec
    assert ES.retain_vcd(job, {"verdict": "sim_fail", "vcd_path": None}, cfg) == {"verdict": "sim_fail", "vcd_path": None}   # no VCD: nothing to do


# ----------------------------------------------------------------------------- tiered retention (G5 item 5 (ii), 2026-09-15)
def make_eq(root, cand_id="c1"):
    job = root / "d1" / "EQ" / "eq1"
    for d in ("v1_ports_c", "v1_ports_d", "v2_sim/csrc", "v2_sim/simv.daidir", "v3_seq/vcst_rtdb/x", "v3_seq/seq_top_learn_dir"):
        (job / d).mkdir(parents=True)
    files = {"equiv.json": json.dumps({"cand_id": cand_id, "verdict": "sim_fail"}), "saif_c.saif": "s" * 50, "saif_d.saif": "s" * 50,
             "v1_ports_c/ports.json": "p" * 100, "v1_ports_d/ports.json": "p" * 100, "v2_sim/sim.vcd.gz": "v" * 300, "v2_sim/trace.txt": "t" * 200,
             "v2_sim/harness.v": "h", "v2_sim/c1__cand.v": "module d1; endmodule", "v2_sim/vcs.log": "l", "v2_sim/sim.log": "l", "v2_sim/csrc/a.o": "o" * 40,
             "v2_sim/simv": "x" * 30, "v2_sim/simv.daidir/k": "k", "v3_seq/seq.tcl": "tcl", "v3_seq/vcf.log": "log", "v3_seq/vcst_command.log": "c",
             "v3_seq/learnt_data_to_server.gz": "g" * 120, "v3_seq/vcst_rtdb/x/y.db": "d" * 70, "v3_seq/seq_top_learn_dir/z": "z"}
    for rel, content in files.items():
        (job / rel).write_text(content)
    return job


def make_dc(root, cand_id="c1", status="ok"):
    job = root / "d1" / "E4" / "e4x"
    (job / "outputs/reports").mkdir(parents=True)
    (job / "inputs/rtl").mkdir(parents=True)
    files = {"meta.json": json.dumps({"status": status, "cand_id": cand_id}), "outputs/reports/netlist.v": "n" * 500, "outputs/reports/design.ddc": "d" * 900,
             "outputs/reports/qor.rpt": "q", "outputs/reports/area.rpt": "a", "outputs/reports/timing.rpt": "t", "outputs/reports/power_saif.rpt": "p",
             "outputs/reports/design.sdc": "sdc", "outputs/dc_shell.log": "log", "inputs/constraint.sdc": "sdc", "inputs/rtl/c1.v": "module d1; endmodule",
             "outputs/reports/c1.saif": "s" * 60}
    for rel, content in files.items():
        (job / rel).write_text(content)
    return job


def tiered_cfg(on=True, audit=0.0):
    cfg = copy.deepcopy(CFG)
    cfg["retention"].update(tiered=on, tiered_audit_frac=audit, tiered_dc_delete=["netlist", "ddc", "saif", "inputs_rtl"],
                            tiered_eq_delete=["vcd", "trace", "ports", "seq_rtdb", "seq_learnt", "vcs_build", "saif"], m6_workdir_after_classification="delete")
    return cfg


def test_tiered_slimming_keeps_records_and_small_reports_and_removes_regenerable_artifacts(tmp_path):
    from src.eval import retention as R
    cfg = tiered_cfg()
    eq, dc = make_eq(tmp_path), make_dc(tmp_path)
    m6 = tmp_path / "m6_c1"
    (m6 / "d").mkdir(parents=True)
    (m6 / "d" / "stats.json").write_text("{}" * 100)
    res = R.slim_candidate(cfg, "c1", accepted=False, eq_dir=eq, fit_dirs=[dc], m6_dir=m6)
    assert res["kept_full"] is False and res["m6"] > 0 and not m6.exists()
    assert set(res["freed"]) == {"eq_vcd", "eq_trace", "eq_ports", "eq_seq_rtdb", "eq_seq_learnt", "eq_vcs_build", "eq_saif", "dc_netlist", "dc_ddc", "dc_saif", "dc_inputs_rtl"}
    for gone in ("v2_sim/sim.vcd.gz", "v2_sim/trace.txt", "v1_ports_c", "v1_ports_d", "v3_seq/vcst_rtdb", "v3_seq/seq_top_learn_dir", "v3_seq/learnt_data_to_server.gz", "v2_sim/csrc", "v2_sim/simv", "v2_sim/simv.daidir", "saif_c.saif", "saif_d.saif"):
        assert not (eq / gone).exists(), gone
    for kept in ("equiv.json", "v2_sim/harness.v", "v2_sim/c1__cand.v", "v2_sim/vcs.log", "v2_sim/sim.log", "v3_seq/seq.tcl", "v3_seq/vcf.log", "v3_seq/vcst_command.log"):
        assert (eq / kept).exists(), kept
    for gone in ("outputs/reports/netlist.v", "outputs/reports/design.ddc", "outputs/reports/c1.saif", "inputs/rtl"):
        assert not (dc / gone).exists(), gone
    for kept in ("meta.json", "outputs/reports/qor.rpt", "outputs/reports/area.rpt", "outputs/reports/timing.rpt", "outputs/reports/power_saif.rpt", "outputs/reports/design.sdc", "outputs/dc_shell.log", "inputs/constraint.sdc"):
        assert (dc / kept).exists(), kept
    assert json.loads((eq / "equiv.json").read_text())["slimmed"]["categories"] == sorted(["vcd", "trace", "ports", "seq_rtdb", "seq_learnt", "vcs_build", "saif"])
    assert json.loads((dc / "meta.json").read_text())["slimmed"]["bytes"] == 500 + 900 + 60 + len("module d1; endmodule")
    again = R.slim_candidate(cfg, "c1", accepted=False, eq_dir=eq, fit_dirs=[dc], m6_dir=m6)
    assert again["freed"] == {} and again["m6"] == 0                                     # idempotent


def test_tiered_slimming_spares_accepted_candidates_the_audit_sample_and_switched_off_runs(tmp_path):
    from src.eval import retention as R
    for name, cfg, accepted in (("accepted", tiered_cfg(), True), ("off", tiered_cfg(on=False), False), ("audit", tiered_cfg(audit=1.0), False)):
        eq, dc = make_eq(tmp_path / name), make_dc(tmp_path / name)
        res = R.slim_candidate(cfg, "c1", accepted=accepted, eq_dir=eq, fit_dirs=[dc], m6_dir=None)
        assert res["freed"] == {} and (eq / "v2_sim/sim.vcd.gz").exists() and (dc / "outputs/reports/netlist.v").exists(), name
        assert res["kept_full"] is (name != "off")
    # the audit sample is deterministic and close to its fraction
    hits = sum(R.is_audit_sample(f"c{i:06d}", 0.10) for i in range(5000))
    assert 400 < hits < 600 and R.is_audit_sample("c000001", 0.10) == R.is_audit_sample("c000001", 0.10) and not R.is_audit_sample("c000001", 0.0)
    # dry run reports without deleting
    eq = make_eq(tmp_path / "dry")
    res = R.slim_candidate(tiered_cfg(), "c1", accepted=False, eq_dir=eq, dry_run=True)
    assert res["freed"]["eq_vcd"] == 300 and (eq / "v2_sim/sim.vcd.gz").exists() and "slimmed" not in json.loads((eq / "equiv.json").read_text())


def test_d_statistics_are_computed_once_per_run(monkeypatch, tmp_path):
    """The classifier reuses D's Yosys statistics (`d_stats`) instead of re-running Yosys on D for every candidate."""
    from src.classify import rules as M6
    calls = []

    def fake_stats(files, top, cfg, **kw):
        calls.append(tuple(files))
        return {"n_ff_bits": 4, "n_ff_cells": 1, "n_cells": 10, "depth": 3, "cells": {"$add": 1}}

    monkeypatch.setattr(M6.YP, "rtl_stats", fake_stats)
    d, c = tmp_path / "d.v", tmp_path / "c.v"
    d.write_text("module d(input clk, output reg [3:0] y); always @(posedge clk) y <= y + 1; endmodule\n")
    c.write_text("module d(input clk, output reg [3:0] y); always @(posedge clk) y <= y + 4'd1; endmodule\n")
    sd = M6.d_statistics([str(d)], "d", CFG)
    f1 = M6.features([str(d)], [str(c)], "d", CFG, d_stats=sd)
    f2 = M6.features([str(d)], [str(c)], "d", CFG, d_stats=sd)
    assert len(calls) == 3 and calls.count((str(d),)) == 1 and f1["ff_d"] == f2["ff_d"] == 4      # D once, C twice
    M6.features([str(d)], [str(c)], "d", CFG)
    assert calls.count((str(d),)) == 2                                                             # without the cache D is recomputed


def test_prune_script_tiered_mode_dry_run_then_apply(tmp_path):
    """scripts/prune_scratch.py --tiered: records of accepted candidates, literature objects and failed records are kept, the
    audit sample is kept, everything else is slimmed; the dry run deletes nothing; M6 workdirs of runs are removed."""
    import scripts.prune_scratch as PS
    from src.db import core as db
    cfg = tiered_cfg()
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    conn = db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))
    db.insert(conn, "runs", {"run_id": "r1", "exp": "phase4", "arm": "B0", "design_id": "d1", "seed": 1, "status": "done"})
    db.insert(conn, "runs", {"run_id": "lit", "exp": "phase4", "arm": "literature", "design_id": "d1", "seed": 1, "status": "done"})
    for cid, rid, acc in (("c_acc", "r1", 1), ("c_no", "r1", 0), ("c_lit", "lit", 0), ("c_fail", "r1", 0)):
        db.insert(conn, "candidates", {"cand_id": cid, "run_id": rid, "design_id": "d1", "accepted": acc, "in_archive": acc})
    raw = tmp_path / "results" / "raw"
    recs = {}
    for cid in ("c_acc", "c_no", "c_lit", "c_fail"):
        eq = make_eq(raw / cid, cid)
        dc = make_dc(raw / cid, cid, status="ok" if cid != "c_fail" else "eval_failed")
        recs[cid] = (eq, dc)
    # the make_* helpers put every record under <root>/d1/...: move them under raw/<design>/<config>/<hash> layout
    import shutil
    for cid, (eq, dc) in recs.items():
        for src, cfgname in ((eq, "EQ"), (dc, "E4")):
            dst = raw / "d1" / cfgname / f"{cid}_rec"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            recs[cid] = tuple(dst if s is src else s for s in recs[cid])
    cand_root = tmp_path / "results" / "candidates"
    (cand_root / "r1" / "m6_c_no" / "c").mkdir(parents=True)
    (cand_root / "r1" / "m6_c_no" / "c" / "stats.json").write_text("{}" * 50)
    logs = []
    dry = PS.tiered(cfg, conn, raw, cand_root, apply=False, log=logs.append)
    # slimmed: c_no's EQ and E4 records and c_fail's EQ record (a sim_fail verdict is a regular record; only its failed E4 record is kept)
    assert dry["slimmed"] == 3 and dry["kept_accepted"] == 2 and dry["kept_literature"] == 2 and dry["kept_failed"] == 1 and dry["m6_dirs"] == 1
    assert dry["total_bytes"] > 0 and (raw / "d1" / "EQ" / "c_no_rec" / "v2_sim" / "trace.txt").exists() and (cand_root / "r1" / "m6_c_no").exists()   # dry run: nothing deleted
    applied = PS.tiered(cfg, conn, raw, cand_root, apply=True, log=logs.append)
    assert applied["total_bytes"] == dry["total_bytes"] and applied["slimmed"] == 3
    assert not (raw / "d1" / "EQ" / "c_no_rec" / "v2_sim" / "trace.txt").exists() and (raw / "d1" / "EQ" / "c_no_rec" / "equiv.json").exists()
    assert not (raw / "d1" / "E4" / "c_no_rec" / "outputs" / "reports" / "netlist.v").exists() and (raw / "d1" / "E4" / "c_no_rec" / "outputs" / "reports" / "qor.rpt").exists()
    assert (raw / "d1" / "EQ" / "c_acc_rec" / "v2_sim" / "trace.txt").exists() and (raw / "d1" / "EQ" / "c_lit_rec" / "v2_sim" / "trace.txt").exists()
    assert (raw / "d1" / "E4" / "c_fail_rec" / "outputs" / "reports" / "netlist.v").exists() and not (cand_root / "r1" / "m6_c_no").exists()
    assert PS.tiered(cfg, conn, raw, cand_root, apply=True, log=logs.append)["total_bytes"] == 0                       # idempotent
    assert any("would free" in l for l in logs) and any(l.startswith("freed") for l in logs)



def test_sim_fail_vcd_sample_amendment_both_directions(tmp_path):
    """2026-09-15 amendment: only a seeded 5 % sample of sim_fail records keeps its VCD — at record time (retain_vcd deletes the
    others instead of compressing them) and in the tiered prune (the sampled record keeps sim.vcd.gz, the others lose it);
    the sample is deterministic in the seed; frac 1.0 restores the 2026-09-14 behaviour."""
    from src.equiv import saif as ES
    from src.eval import retention as R
    cfg = copy.deepcopy(CFG)
    cfg["retention"].update(vcd_keep_verdicts=["sim_fail"], vcd_compress_kept=True, sim_fail_vcd_sample={"frac": 0.05, "seed": 1})
    names = [f"rec{i:05d}" for i in range(4000)]
    sampled = [n for n in names if R.sim_fail_vcd_sampled(cfg, n)]
    assert 140 < len(sampled) < 260                                                    # ≈ 5 %
    assert sampled == [n for n in names if R.sim_fail_vcd_sampled(cfg, n)]              # deterministic
    cfg2 = copy.deepcopy(cfg)
    cfg2["retention"]["sim_fail_vcd_sample"]["seed"] = 2
    assert [n for n in names if R.sim_fail_vcd_sampled(cfg2, n)] != sampled              # the seed moves the sample
    kept_name, dropped_name = sampled[0], next(n for n in names if n not in set(sampled))
    for name, kept in ((kept_name, True), (dropped_name, False)):
        job = tmp_path / "rec" / name
        job.mkdir(parents=True)
        vcd = job / "sim.vcd"
        vcd.write_bytes(b"$enddefinitions $end\n" * 300)
        rec = {"verdict": "sim_fail", "vcd_path": str(vcd)}
        ES.retain_vcd(job, rec, cfg)
        if kept:
            assert rec["vcd_compressed"] is True and rec["vcd_deleted"] is False and Path(rec["vcd_path"]).exists()
        else:
            assert rec["vcd_deleted"] is True and rec["vcd_path"] is None and rec["vcd_sampled"] is False and not vcd.exists() and not list(job.glob("*.gz"))
    # the tiered prune: the sampled sim_fail record keeps its VCD and loses the rest; the other loses the VCD too
    tcfg = tiered_cfg()
    tcfg["retention"]["sim_fail_vcd_sample"] = {"frac": 0.05, "seed": 1}
    for name, kept in ((kept_name, True), (dropped_name, False)):
        eq = make_eq(tmp_path / "tier" / name)
        eq2 = eq.parent / name
        eq.rename(eq2)
        freed = R.slim_eq_record(eq2, tcfg)
        assert (eq2 / "v2_sim" / "sim.vcd.gz").exists() is kept and not (eq2 / "v2_sim" / "trace.txt").exists()
        assert ("vcd" in freed) is (not kept)
    # a falsified record is unaffected by the sample (its VCD goes as before)
    eq = make_eq(tmp_path / "fals")
    (eq / "equiv.json").write_text(json.dumps({"cand_id": "c1", "verdict": "falsified"}))
    assert "vcd" in R.slim_eq_record(eq, tcfg)
    # frac 1.0: every sim_fail VCD kept (the 2026-09-14 rule)
    cfg["retention"]["sim_fail_vcd_sample"] = {"frac": 1.0, "seed": 1}
    assert all(R.sim_fail_vcd_sampled(cfg, n) for n in names[:50])
