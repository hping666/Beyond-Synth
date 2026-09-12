"""Evaluation-service tests that run the real tools (marker `eda`, enabled with BS_EDA_TESTS=1 after sourcing
/hdd1/hping/eda/setup/env.sh). Bidirectional per spec 01 §7: a correct design reproduces the fixture; a syntax
error, a wrong top, a missing library and a broken SDC are each caught with the right status; two E4 runs of the
same input are bit-identical; the queue can run a DC job end to end."""
import copy
import json
import os
import time
from pathlib import Path

import pytest

from src import config as C
from src.db import core as db
from src.eval.dc import run_dc
from src.jobqueue.core import Queue
from src.jobqueue.daemon import build_env, read_pid
from src.jobqueue.core import _alive

pytestmark = pytest.mark.eda

ROOT = Path(__file__).resolve().parent.parent
ACCU = "/home/hping/RTLLM/Arithmetic/Accumulator/accu/verified_accu.v"
TOP = "verified_accu"
FIX = ROOT / "tests" / "fixtures" / "rtllm_accu"


@pytest.fixture(scope="module")
def cfg():
    return C.load()


def fixture_meta(config):
    return json.loads((FIX / config / "meta.json").read_text())


def test_e1_reproduces_fixture(cfg, tmp_path):
    rec = run_dc(tmp_path / "job", [ACCU], TOP, "nangate45", cfg["configs"]["E1"]["compile"], 2.0, "clk", cfg)
    assert rec["status"] == "ok", rec.get("error")
    f = fixture_meta("E1")
    for k in ("area", "cells", "wns_ns", "tns_ns"):
        assert rec["metrics"][k] == f["metrics"][k], k
    assert rec["hist"] == f["hist"]


def test_syntax_error_is_caught(cfg, tmp_path):
    bad = tmp_path / "bad.v"
    bad.write_text("module bad(input a, output b;\n  assign b = a &&& ;\nendmodule\n")
    rec = run_dc(tmp_path / "job", [bad], "bad", "nangate45", "compile", 2.0, "clk", cfg)
    assert rec["status"] == "analyze_failed", rec
    assert rec.get("dc_errors"), "the DC error text must be captured"


def test_wrong_top_is_caught(cfg, tmp_path):
    rec = run_dc(tmp_path / "job", [ACCU], "no_such_module", "nangate45", "compile", 2.0, "clk", cfg)
    assert rec["status"] == "elaborate_failed", rec


def test_missing_library_is_caught_before_dc_starts(cfg, tmp_path):
    cfg2 = copy.deepcopy(cfg)
    cfg2["libs"]["nangate45"]["db"] = "/nonexistent/lib.db"
    t0 = time.time()
    rec = run_dc(tmp_path / "job", [ACCU], TOP, "nangate45", "compile", 2.0, "clk", cfg2)
    assert rec["status"] == "library_missing" and time.time() - t0 < 2.0


def test_broken_sdc_is_caught_as_constraint_incomplete(cfg, tmp_path):
    sdc = tmp_path / "broken.sdc"
    sdc.write_text("current_design verified_accu\ncreate_clock -name clk -period 2 [get_ports clk]\n"
                   "this_command_does_not_exist_xyz\nset_output_delay 0.4 -clock clk [all_outputs]\n")
    rec = run_dc(tmp_path / "job", [ACCU], TOP, "nangate45", "compile", 2.0, "clk", cfg, sdc_override=sdc)
    assert rec["status"] in ("constraint_incomplete", "constraint_failed"), rec
    assert rec.get("sdc_errors"), "the SDC error must be reported"


def test_e4_is_deterministic(cfg, tmp_path):
    a = run_dc(tmp_path / "a", [ACCU], TOP, "nangate45", cfg["configs"]["E4"]["compile"], 2.0, "clk", cfg)
    b = run_dc(tmp_path / "b", [ACCU], TOP, "nangate45", cfg["configs"]["E4"]["compile"], 2.0, "clk", cfg)
    assert a["status"] == "ok" and b["status"] == "ok", (a.get("error"), b.get("error"))
    for k in ("area", "cells", "wns_ns", "tns_ns", "crit_delay_ns", "icg_count", "registers"):
        assert a["metrics"][k] == b["metrics"][k], k
    assert a["hist"] == b["hist"]
    assert a["crit_path"]["endpoint"] == b["crit_path"]["endpoint"]
    f = fixture_meta("E4")
    assert a["metrics"]["area"] == f["metrics"]["area"] and a["hist"] == f["hist"]


def test_queue_runs_a_dc_job_end_to_end(cfg):
    pid = read_pid(cfg)
    if pid and _alive(pid):
        pytest.skip("the queue daemon is running; this test drives the queue itself")
    conn = db.connect(cfg=cfg)
    q = Queue(cfg, conn, os.path.join(C.results_dir(cfg), "queue", "logs"), env=build_env(cfg), log=lambda m: None)
    jid = q.submit("dc", {"design_id": "rtllm_accu", "rtl": [ACCU], "top": TOP, "config": "E1", "clock_ns": 2.0,
                          "clk_port": "clk", "is_baseline": 1}, design_id="rtllm_accu", config="E1")
    deadline = time.time() + 180
    while time.time() < deadline:
        q.tick()
        st = q.get(jid)["state"]
        if st in ("done", "failed"):
            break
        time.sleep(1)
    job = q.get(jid)
    assert job["state"] == "done", (job["state"], job["error"], open(job["log_path"]).read()[-800:])
    out = open(job["log_path"]).read()
    assert '"status": "ok"' in out
