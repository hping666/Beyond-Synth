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
    cfg["retention"].update(vcd_to_scratch=True, vcd_keep_verdicts=["sim_fail"], vcd_compress_kept=True, vcd_keep_sample_frac=0.0)

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
