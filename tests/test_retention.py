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
