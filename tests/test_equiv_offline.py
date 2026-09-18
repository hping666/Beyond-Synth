"""Offline tests of the equivalence stack pieces (Yosys is local and fast; no license): port extraction and
comparison, candidate renaming, harness generation, trace comparison with latency offsets."""
import json
import re
from pathlib import Path

import pytest

from src import config as C
from src.equiv import ports as PORTS
from src.equiv.harness import compare_traces, write_harness, HARNESS
from src.equiv.rename import module_names, rename_candidate, rename_modules

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "tests" / "assets"
ACCU = "/home/hping/RTLLM/Arithmetic/Accumulator/accu/verified_accu.v"
CFG = C.load()


def test_port_info_and_control_inference(tmp_path):
    p = PORTS.port_info([ACCU], "verified_accu", CFG, workdir=tmp_path)
    assert p["data_in"] == {"dir": "input", "width": 8} and p["data_out"] == {"dir": "output", "width": 10}
    assert PORTS.infer_control_ports(p) == ("clk", "rst_n", "low")


def test_port_compare_rejects_width_change_and_accepts_rename(tmp_path):
    d = PORTS.port_info([ACCU], "verified_accu", CFG, workdir=tmp_path / "d")
    w = PORTS.port_info([ASSETS / "accu_width.v"], "verified_accu", CFG, workdir=tmp_path / "w")
    r = PORTS.port_info([ASSETS / "accu_perturb_rename.v"], "verified_accu", CFG, workdir=tmp_path / "r")
    assert PORTS.compare_ports(d, w) == ["port data_out: width 10 -> 12"]
    assert PORTS.compare_ports(d, r) == []
    assert PORTS.compare_ports(d, {k: v for k, v in d.items() if k != "valid_in"}) == ["port valid_in missing in candidate"]


def test_port_info_raises_on_bad_rtl(tmp_path):
    bad = tmp_path / "bad.v"
    bad.write_text("module bad(input a, output b;\n assign b = ;\nendmodule\n")
    with pytest.raises(PORTS.PortError):
        PORTS.port_info([bad], "bad", CFG, workdir=tmp_path / "y")


def test_rename_modules_whole_word_only():
    text = "module acc(input a);\nendmodule\nmodule top;\n acc u0(.a(x));\n wire acc_x;\n accumulate y;\nendmodule\n"
    names = module_names(text)
    assert names == ["acc", "top"]
    out = rename_modules(text, names, "__cand")
    assert "module acc__cand(" in out and "acc__cand u0(" in out and "module top__cand;" in out
    assert "acc_x" in out and "accumulate" in out and "acc__cand_x" not in out


def test_rename_candidate_files(tmp_path):
    f = tmp_path / "c.v"
    f.write_text(Path(ACCU).read_text())
    renamed, names = rename_candidate([str(f)])
    assert names == ["verified_accu"] and "module verified_accu__cand(" in renamed[0][1]


def test_harness_generation(tmp_path):
    ports = PORTS.port_info([ACCU], "verified_accu", CFG, workdir=tmp_path)
    ins, outs = write_harness(tmp_path / "h.v", "verified_accu", "verified_accu__cand", ports, "clk", "rst_n", "low", CFG,
                              tmp_path / "trace.txt", tmp_path / "sim.vcd")
    h = (tmp_path / "h.v").read_text()
    assert ins == ["data_in", "valid_in"] and outs == ["valid_out", "data_out"]
    assert f"module {HARNESS};" in h and "verified_accu u_d (" in h and "verified_accu__cand u_c (" in h
    assert "rst = 1'b0;" in h and "rst = 1'b1;" in h  # active-low reset sequence
    assert "$random(seed)" in h and "$dumpvars(0, u_d);" in h and "$dumpvars(0, u_c);" in h
    assert re.search(r"\$fwrite\(fd, \"%0d %h %h %h %h\\n\", cyc, d_valid_out, c_valid_out, d_data_out, c_data_out\)", h)


def test_harness_wide_inputs_use_concatenated_random(tmp_path):
    ports = {"clk": {"dir": "input", "width": 1}, "a": {"dir": "input", "width": 70}, "y": {"dir": "output", "width": 3}}
    write_harness(tmp_path / "h.v", "m", "m__cand", ports, "clk", None, None, CFG, tmp_path / "t", tmp_path / "v")
    h = (tmp_path / "h.v").read_text()
    assert "a = {$random(seed), $random(seed), $random(seed)};" in h and "reg [69:0] a;" in h and "reg rst" not in h


def test_compare_traces_identical_offset_and_mismatch():
    outs = ["o"]
    ident = "\n".join(f"{i} {i % 7:x} {i % 7:x}" for i in range(20))
    assert compare_traces(ident, outs, 8)["status"] == "identical"
    d = [i % 7 for i in range(30)]
    shifted = "\n".join(f"{i} {d[i]:x} {d[i - 2] if i >= 2 else 0:x}" for i in range(30))
    r = compare_traces(shifted, outs, 8)
    assert r["status"] == "offset" and r["offsets"] == {"o": 2}
    bad = "\n".join(f"{i} {d[i]:x} {(d[i] if i != 11 else 5):x}" for i in range(30))
    r = compare_traces(bad, outs, 8)
    assert r["status"] == "mismatch" and r["first_mismatch"] == 11 and r["mismatches"]["o"]["first_cycle"] == 11
    assert compare_traces("", outs, 8)["status"] == "no_trace"
    two = "\n".join(f"{i} {d[i]:x} {d[i]:x} {d[i]:x} {d[i - 1] if i else 0:x}" for i in range(30))
    r = compare_traces(two, ["p", "q"], 8)
    assert r["status"] == "offset" and r["offsets"] == {"p": 0, "q": 1}


def test_yosys_timeout_is_an_error_not_a_rejection(tmp_path, monkeypatch):
    """A V1 probe that runs out of time says nothing about the interface (RFselector gate crash, 2026-09-12)."""
    import subprocess
    from src.equiv import stack as ST

    def slow_run(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="yosys", timeout=1)

    monkeypatch.setattr(PORTS.subprocess, "run", slow_run)
    with pytest.raises(PORTS.PortTimeout):
        PORTS.port_info([ACCU], "verified_accu", CFG, workdir=tmp_path / "t", timeout=1)
    rec = ST.check_equivalence(tmp_path / "job", [ACCU], [ACCU], "verified_accu", CFG, run_v3=False, run_v4=False)
    assert rec["verdict"] == "error" and rec["v1_status"] == "error" and "timeout" in rec["v1_detail"]
    monkeypatch.setattr(PORTS.subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        PORTS.port_info([ACCU], "verified_accu", CFG, workdir=tmp_path / "u")  # other failures still propagate


def test_harness_seed_defaults_to_config_and_can_be_overridden(tmp_path):
    ports = PORTS.port_info([ACCU], "verified_accu", CFG, workdir=tmp_path / "p")
    from src.equiv.harness import write_harness
    write_harness(tmp_path / "h1.v", "verified_accu", "verified_accu__cand", ports, "clk", "rst_n", "low", CFG, tmp_path / "t1", tmp_path / "v1")
    write_harness(tmp_path / "h2.v", "verified_accu", "verified_accu__cand", ports, "clk", "rst_n", "low", CFG, tmp_path / "t2", tmp_path / "v2", seed=7)
    assert f"parameter integer SEED = {int(CFG['sim']['seed'])};" in (tmp_path / "h1.v").read_text()
    assert "parameter integer SEED = 7;" in (tmp_path / "h2.v").read_text()


def test_candidate_top_with_a_different_name(tmp_path, monkeypatch):
    """RTL-OPT references are named <name>_ref: V1 reads the candidate's own top, V2 instantiates it, V3 gets impl_top."""
    from src.equiv import stack as ST
    alt = tmp_path / "accu_alt.v"
    alt.write_text(open(ACCU).read().replace("module verified_accu", "module accu_alt"))
    seen = {}

    def fake_lockstep(job_dir, d_files, c_files, top, ports, clk, rst, rst_sense, cfg, **kw):
        seen["c_top"] = kw.get("c_top")
        return {"status": "identical", "offsets": {}, "cycles": 1, "vcd": None}

    def fake_seq(job_dir, d_files, c_files, top, clk, rst, rst_sense, cfg, **kw):
        seen["impl_top"] = kw.get("impl_top")
        return {"v3_status": "proven", "v3_seconds": 1.0, "counterexample_path": None, "flow_status": "equivalent"}

    monkeypatch.setattr(ST, "run_lockstep", fake_lockstep)
    monkeypatch.setattr(ST, "run_seq", fake_seq)
    rec = ST.check_equivalence(tmp_path / "job", [ACCU], [alt], "verified_accu", CFG, run_v4=False, c_top="accu_alt")
    assert rec["v1_status"] == "ok" and rec["c_top"] == "accu_alt" and seen == {"c_top": "accu_alt", "impl_top": "accu_alt"}
    rec2 = ST.check_equivalence(tmp_path / "job2", [ACCU], [alt], "verified_accu", CFG, run_v4=False)  # without c_top: V1 cannot find the module
    assert rec2["v1_status"] == "rejected" and "does not elaborate" in rec2["v1_detail"]


def test_stages_share_one_deadline(tmp_path, monkeypatch):
    """V2 / V3 get the remaining budget, and a stage is not started when less than MIN_STAGE_SEC is left (the record
    then says inconclusive / error instead of the queue killing the job without a record)."""
    import time
    from src.equiv import stack as ST
    seen = {}

    def slow_lockstep(job_dir, d_files, c_files, top, ports, clk, rst, rst_sense, cfg, **kw):
        seen["v2_timeout"] = kw.get("timeout_sec")
        time.sleep(1.2)
        return {"status": "identical", "offsets": {}, "cycles": 1, "vcd": None}

    def fake_seq(job_dir, d_files, c_files, top, clk, rst, rst_sense, cfg, **kw):
        seen["v3_timeout"] = kw.get("timeout_sec")
        return {"v3_status": "proven", "v3_seconds": 1.0, "counterexample_path": None, "flow_status": "equivalent"}

    monkeypatch.setattr(ST, "run_lockstep", slow_lockstep)
    monkeypatch.setattr(ST, "run_seq", fake_seq)
    rec = ST.check_equivalence(tmp_path / "a", [ACCU], [ACCU], "verified_accu", CFG, run_v4=False, timeout_sec=600.0)
    assert rec["verdict"] == "proven" and 500 < seen["v2_timeout"] <= 600 and seen["v3_timeout"] < seen["v2_timeout"]
    monkeypatch.setattr(ST, "MIN_STAGE_SEC", 5.0)
    rec = ST.check_equivalence(tmp_path / "b", [ACCU], [ACCU], "verified_accu", CFG, run_v4=False, timeout_sec=6.0)
    assert rec["v2_status"] == "identical" and rec["v3_status"] == "inconclusive" and "out of time" in (rec.get("v3") or {}).get("error", "")
    rec = ST.check_equivalence(tmp_path / "c", [ACCU], [ACCU], "verified_accu", CFG, run_v4=False, timeout_sec=None)
    assert rec["verdict"] == "proven" and seen["v2_timeout"] is None  # unlimited stays unlimited


def test_seq_solver_limit_stays_inside_the_process_budget(tmp_path, monkeypatch):
    from src.equiv import seq as SQ
    seen = {}

    class FakeVcf:
        def seq_equiv(self, *a, **kw):
            seen.update(kw)
            return {"status": "inconclusive", "runtime_s": 1.0}

    monkeypatch.setattr(SQ, "_vcf", lambda cfg: FakeVcf())
    monkeypatch.setattr(SQ, "seq_equiv_project", FakeVcf().seq_equiv)  # the zero-init runner (DECISIONS 2026-09-14) takes the same limits
    SQ.run_seq(tmp_path, [ACCU], [ACCU], "verified_accu", "clk", "rst_n", "low", CFG, timeout_sec=1530.0)
    assert seen["max_time"] == "20M" and seen["timeout"] == 1530.0  # 80 % of the budget in whole minutes
    SQ.run_seq(tmp_path, [ACCU], [ACCU], "verified_accu", "clk", "rst_n", "low", CFG)
    assert seen["max_time"] == f"{int(CFG['timeouts']['seq_min'])}M"
    SQ.run_seq(tmp_path, [ACCU], [ACCU], "verified_accu", "clk", "rst_n", "low", CFG, timeout_sec=30.0)
    assert seen["max_time"] == "1M"  # never below one minute


def test_zero_init_arguments_follow_the_config():
    """DECISIONS 2026-09-14 G2.2: with equiv.init_state_zero_no_reset the lock-step simulation compiles with
    +vcs+initreg+random and runs with +vcs+initreg+0; without the flag nothing is added."""
    from src.equiv.harness import init_args
    assert init_args({"equiv": {"init_state_zero_no_reset": True}}) == (["+vcs+initreg+random"], ["+vcs+initreg+0"])
    assert init_args({"equiv": {"init_state_zero_no_reset": False}}) == ([], [])
    assert init_args({}) == ([], [])


def test_project_seq_script_adds_the_zero_init_line_only_when_asked():
    """The project-owned SEQ Tcl equals the flow's sequence plus `sim_set_state -uninitialized -apply 0` before the reset
    state is saved when zero_init is on; nothing else changes (DECISIONS 2026-09-14 G2.2)."""
    from src.equiv.seq_tcl import seq_tcl
    on = seq_tcl(["/d.v"], ["/c.v"], "top", "top", "clk", "rst_n", "low", "20M", 1, "verilog", True).splitlines()
    off = seq_tcl(["/d.v"], ["/c.v"], "top", "top", "clk", "rst_n", "low", "20M", 1, "verilog", False).splitlines()
    assert "sim_set_state -uninitialized -apply 0" in on and "sim_set_state -uninitialized -apply 0" not in off
    assert [l for l in on if not l.startswith("sim_set_state")] == off
    assert on.index("sim_run -stable") < on.index("sim_set_state -uninitialized -apply 0") < on.index("sim_save_reset") < on.index("seq_config -map_uninit -map_x zero")
    assert "create_reset spec.rst_n -sense low" in off and off[-1] == "exit"


def test_project_seq_script_passes_include_directories():
    from src.equiv.seq_tcl import seq_tcl
    lines = seq_tcl(["/d.v"], ["/c.v"], "top", "top", "clk", None, "high", "20M", 1, "verilog", True, ["/inc/a", "/inc/b"]).splitlines()
    assert lines[3] == "analyze -format verilog -vcs {+incdir+/inc/a +incdir+/inc/b} -library spec {/d.v}"
    assert lines[4].startswith("analyze -format verilog -vcs {+incdir+/inc/a +incdir+/inc/b} -library impl")
    assert "create_reset" not in "\n".join(lines)
    assert "-vcs" not in seq_tcl(["/d.v"], ["/c.v"], "top", "top", "clk", None, "high", "20M", 1, "verilog", True).splitlines()[3]


def test_sim_fail_record_compresses_its_vcd(tmp_path, monkeypatch):
    """The V2 early return applies the retention rules (defect of 2026-09-15: sim_fail records returned before the rules
    and left their VCDs uncompressed): a sim_fail record's VCD is gzipped and the saved record says so; with the switch
    off the VCD stays."""
    import copy
    import json
    from pathlib import Path
    from src.equiv import stack as ST

    def fake_lockstep(job_dir, d_files, c_files, top, ports, clk, rst, rst_sense, cfg, **kw):
        sim = Path(job_dir) / "v2_sim"
        sim.mkdir(parents=True, exist_ok=True)
        vcd = sim / "sim.vcd"
        vcd.write_bytes(b"$enddefinitions $end\n" * 200)
        return {"status": "mismatch", "cycles": 3, "vcd": str(vcd), "mismatches": {"q": {"cycle": 3, "d": "1", "c": "0"}}}

    monkeypatch.setattr(ST, "run_lockstep", fake_lockstep)
    cfg = copy.deepcopy(CFG)
    cfg["retention"]["sim_fail_vcd_sample"] = {"frac": 1.0, "seed": 1}   # 2026-09-15 amendment: the compression path is tested with every sim_fail VCD kept
    cfg["retention"].update(vcd_keep_verdicts=["sim_fail"], vcd_compress_kept=True)
    rec = ST.check_equivalence(tmp_path / "a", [ACCU], [ACCU], "verified_accu", cfg, run_v3=False, run_v4=False)
    assert rec["verdict"] == "sim_fail" and rec["vcd_compressed"] is True and rec["vcd_path"].endswith(".vcd.gz") and Path(rec["vcd_path"]).exists()
    assert not (tmp_path / "a" / "v2_sim" / "sim.vcd").exists()
    saved = json.loads((tmp_path / "a" / "equiv.json").read_text())
    assert saved["vcd_path"].endswith(".vcd.gz") and saved["vcd_compressed"] is True and saved["v2_status"] == "sim_fail"
    cfg["retention"]["vcd_compress_kept"] = False
    rec = ST.check_equivalence(tmp_path / "b", [ACCU], [ACCU], "verified_accu", cfg, run_v3=False, run_v4=False)
    assert rec["verdict"] == "sim_fail" and (tmp_path / "b" / "v2_sim" / "sim.vcd").exists() and rec.get("vcd_compressed") is None


def test_project_seq_script_latency_mapping_lines():
    """DECISIONS 2026-09-14 G2.1 (b) (implemented 2026-09-15): with per-output offsets the script maps only the inputs by name
    and asserts every output at its latency (impl lags spec by k: -latency1 0 -latency2 k; k = 0 outputs keep an immediate
    assertion), between the reset definition and sim_run; without offsets the script is the one of before, byte for byte."""
    from src.equiv import seq_tcl as SQT
    args = (["/d/d.v"], ["/c/c.v"], "top", "top", "clk", "rst_n", "low", "20M", 1, "verilog", True)
    plain = SQT.seq_tcl(*args)
    mapped = SQT.seq_tcl(*args, latency={"out": 1, "flag": 0, "data": 3})
    assert "map_by_name\n" in plain and "seq_assert" not in plain and "-input" not in plain
    lines = mapped.splitlines()
    assert "map_by_name -input" in lines and "map_by_name" not in lines
    assert "seq_assert spec.out impl.out -clock spec.clk -latency1 0 -latency2 1" in lines
    assert "seq_assert spec.data impl.data -clock spec.clk -latency1 0 -latency2 3" in lines
    assert "seq_assert spec.flag impl.flag" in lines                              # offset 0: immediate assertion, still compared
    i_rst, i_first, i_run = lines.index("create_reset spec.rst_n -sense low"), min(i for i, l in enumerate(lines) if l.startswith("seq_assert")), lines.index("sim_run -stable")
    assert i_rst < i_first < i_run and "sim_set_state -uninitialized -apply 0" in lines
    assert [l for l in plain.splitlines() if not l.startswith("map_by_name")] == [l for l in lines if not l.startswith(("map_by_name", "seq_assert"))]
    assert SQT.seq_tcl(*args, latency={}) == plain and SQT.seq_tcl(*args, latency=None) == plain


def test_latency_map_needs_an_offset_and_the_switch():
    from src.equiv.stack import latency_map
    on, off = {"equiv": {"seq_latency_mapping": True}}, {"equiv": {"seq_latency_mapping": False}}
    assert latency_map(on, {"status": "offset", "offsets": {"a": 1, "b": 0}}) == {"a": 1, "b": 0}
    assert latency_map(off, {"status": "offset", "offsets": {"a": 1, "b": 0}}) is None                # switch off: proven_sim_only as before
    assert latency_map(on, {"status": "identical", "offsets": {"a": 0}}) is None                       # nothing to map
    assert latency_map(on, {"status": "offset", "offsets": {"a": 0}}) is None                          # an "offset" status without a positive offset


@pytest.mark.parametrize("switch, v3_verdict, expected, proven_by, seq_called", [(True, "proven", "proven", "seq", True), (True, "falsified", "falsified", None, True), (True, "inconclusive", "inconclusive", None, True), (False, "proven", "proven_sim_only", None, False)])
def test_stack_offset_candidates_run_seq_with_the_latency_mapping(tmp_path, monkeypatch, switch, v3_verdict, expected, proven_by, seq_called):
    """Both directions: with the switch on, a V2 offset candidate goes to SEQ with the offsets as latencies and SEQ's own
    verdict decides (proven / falsified / inconclusive); with the switch off it stays proven_sim_only and SEQ never runs."""
    import copy
    from src.equiv import stack as ST
    cfg = copy.deepcopy(CFG)
    cfg["equiv"]["seq_latency_mapping"] = switch
    seen = {}

    def fake_lockstep(job_dir, d_files, c_files, top, ports, clk, rst, rst_sense, cfg, **kw):
        return {"status": "offset", "offsets": {"data_out": 1, "valid_out": 1}, "cycles": 10, "vcd": None}

    def fake_seq(job_dir, d_files, c_files, top, clk, rst, rst_sense, cfg, **kw):
        seen["latency"] = kw.get("latency")
        return {"v3_status": v3_verdict, "v3_seconds": 1.0, "counterexample_path": str(job_dir) if v3_verdict == "falsified" else None,
                "flow_status": "x", "latency_mapped": True, "latency": kw.get("latency")}

    monkeypatch.setattr(ST, "run_lockstep", fake_lockstep)
    monkeypatch.setattr(ST, "run_seq", fake_seq)
    rec = ST.check_equivalence(tmp_path / "job", [ACCU], [ASSETS / "accu_perturb_rename.v"], "verified_accu", cfg, run_v4=False)
    assert rec["v2_status"] == "offset" and rec["latency_offset_json"] == '{"data_out": 1, "valid_out": 1}'
    assert rec["verdict"] == expected and rec["proven_by"] == proven_by and rec["latency_mapped"] is seq_called
    assert (seen.get("latency") == {"data_out": 1, "valid_out": 1}) is seq_called
    assert rec["v3_status"] == (v3_verdict if seq_called else "proven_sim_only")


def test_equiv_extra_adds_the_latency_switch_only_when_enabled():
    """The record hash of every earlier record is unchanged while the switch is off; enabling it gives new record directories."""
    import copy
    from src.equiv.run_equiv import equiv_extra
    p = {"clk": "clk", "rst": "rst_n", "rst_sense": "low", "sverilog": False, "sim_seed": 1, "c_top": None}
    off = copy.deepcopy(CFG)
    off["equiv"]["seq_latency_mapping"] = False
    on = copy.deepcopy(CFG)
    on["equiv"]["seq_latency_mapping"] = True
    assert equiv_extra(off, p, True) == {"stages": "full", "clk": "clk", "rst": "rst_n", "rst_sense": "low", "sverilog": False, "sim_seed": 1, "c_top": None}
    assert equiv_extra(on, p, True) == {**equiv_extra(off, p, True), "latency_mapping": True}
    assert equiv_extra(on, p, False)["stages"] == "v1v2"


def test_seq_log_parser_reads_both_summary_formats():
    """The by-name run prints its assertion counts under "Sequential Equivalence Summary: SEQ"; a run with explicit output
    assertions (latency mapping) prints them under "Property Summary: SEQ" (VC Formal Y-2026, counter_12 on 2026-09-15).
    Both parse; a log with neither is an error, never a verdict."""
    from src.equiv import seq as SQ
    from src.equiv.seq_tcl import parse_seq_log
    vcf = SQ._vcf(CFG)
    by_name = ("[Info] '3' registers are mapped by name\n[Info] PROP_I_RESULT: SEQ  _map_output_out  e1  proven  property  00:00:08\n"
               "  Summary Results\n   Property Summary: SEQ\n   -----------------\n   > Constraint\n     - # found        : 4\n\n"
               "   Sequential Equivalence Summary: SEQ\n   -------------------------------\n   > Assertion\n     - # found        : 2\n     - # proven       : 1\n     - # falsified    : 1\n\n")
    r = parse_seq_log(by_name, vcf)
    assert r["status"] == "not_equivalent" and (r["total"], r["proven"], r["failed"], r["inconclusive"]) == (2, 1, 1, 0) and r["regs_mapped"] == 3
    mapped = ("[Info] PROP_I_RESULT: SEQ  _map_output_seq_assert_out  checking  property  00:00:08\n"
              "[Info] PROP_I_RESULT: SEQ  _map_output_seq_assert_out  e1  proven  property  00:00:08\n"
              "  Summary Results\n   Property Summary: SEQ\n   -----------------\n   > Assertion\n     - # found        : 1\n     - # proven       : 1\n\n   > Constraint\n     - # found        : 4\n\n")
    r = parse_seq_log(mapped, vcf)
    assert r["status"] == "equivalent" and (r["total"], r["proven"], r["failed"], r["inconclusive"]) == (1, 1, 0, 0)
    assert r["properties"] == {"_map_output_seq_assert_out": "proven"}
    falsified = mapped.replace("- # proven       : 1", "- # falsified    : 1")
    assert parse_seq_log(falsified, vcf)["status"] == "not_equivalent"
    r = parse_seq_log("[Error] SEQ_SOMETHING: bad script\n", vcf, rc=1)
    assert r["status"] == "error" and r["error"].startswith("[Error] SEQ_SOMETHING")
    assert parse_seq_log("", vcf, timed_out=True, timeout=10, max_time="1M")["status"] == "timeout"


def test_cex_depths_from_the_verbose_report():
    from src.equiv.seq import cex_depths
    log = ("   > Assertion\n     # Assertion: 2\n     > ID: [22] falsified (depth=1) \n      - name          : _map_output_MTxD\n      - type          : assert\n"
           "     > ID: [23] falsified (depth=3) \n      - name          : _map_output_TxDone\n     > ID: [24] proven \n      - name          : _map_output_X\n")
    assert cex_depths(log) == {"_map_output_MTxD": 1, "_map_output_TxDone": 3}
    assert cex_depths("") == {}


def test_equiv_version_is_stamped_on_the_record_but_not_hashed():
    """Decision 2026-09-15 evening (item 5): every equivalence record carries config equiv.version; the record hash does not
    include it, so records produced earlier under the same stack stay cached (both directions: no version -> no stamp)."""
    from src.equiv import run_equiv as RE
    cfg = {"equiv": {"version": "phase5", "seq_latency_mapping": True}}
    rec = RE.stamp_version({"verdict": "proven"}, cfg)
    assert rec["equiv_version"] == "phase5"
    assert "equiv_version" not in RE.stamp_version({"verdict": "proven"}, {"equiv": {}}) and "version" not in RE.equiv_extra(cfg, {})


def test_proof_continues_from_a_simulation_record(tmp_path, monkeypatch):
    """Split pipeline (DECISIONS 2026-09-16): with `sim_record`, check_equivalence skips V1 / V2 (never calls the lock-step
    simulation), copies the stages and SAIFs of the sim job's record and runs V3; a sim record that already decided
    (sim_fail) is copied without a proof. The runner hashes such a job under stages `v3`, and reuses a decided `full` record
    of the same pair instead of proving it again (both directions: an inconclusive full record is not reused)."""
    from src.equiv import stack as ST
    from src.equiv import run_equiv as RE
    calls = {"seq": 0}

    def no_lockstep(*a, **kw):
        raise AssertionError("V2 must not run again")

    def fake_seq(job_dir, d_files, c_files, top, clk, rst, rst_sense, cfg, **kw):
        calls["seq"] += 1
        calls["impl_top"], calls["sverilog"] = kw.get("impl_top"), kw.get("sverilog")
        return {"v3_status": "proven", "v3_seconds": 1.0, "counterexample_path": None, "flow_status": "equivalent"}

    monkeypatch.setattr(ST, "run_lockstep", no_lockstep)
    monkeypatch.setattr(ST, "run_seq", fake_seq)
    sim = {"top": "verified_accu", "verdict": "not_run", "v1_status": "ok", "v2_status": "identical", "v2_cycles": 200, "latency_offset_json": "{}", "clk": "clk", "rst": "rst_n",
           "rst_sense": "low", "ports": {"clk": {"dir": "input", "width": 1}, "q": {"dir": "output", "width": 8}}, "sim_seed": 11, "c_top": "verified_accu",
           "saif_c": str(tmp_path / "saif_c.saif"), "saif_d": str(tmp_path / "saif_d.saif"), "raw_dir": str(tmp_path / "simrec"), "vcd_path": str(tmp_path / "x.vcd"),
           "v2": {"status": "identical", "offsets": {}, "cycles": 200, "sverilog": False}}
    rec = ST.check_equivalence(tmp_path / "job", [ACCU], [ACCU], "verified_accu", CFG, run_v4=False, sim_record=sim)
    assert rec["verdict"] == "proven" and rec["proven_by"] == "seq" and calls["seq"] == 1 and calls["impl_top"] is None
    assert rec["v1_status"] == "ok" and rec["v2_status"] == "identical" and rec["v2_cycles"] == 200 and rec["saif_c"] == sim["saif_c"] and rec["sim_seed"] == 11
    assert rec["sim_record"] == sim["raw_dir"] and rec["vcd_path"] is None and (tmp_path / "job" / "equiv.json").exists()
    failed = dict(sim, verdict="sim_fail", v2_status="sim_fail", v2_detail="q differs")
    rec2 = ST.check_equivalence(tmp_path / "job2", [ACCU], [ACCU], "verified_accu", CFG, run_v4=False, sim_record=failed)
    assert rec2["verdict"] == "sim_fail" and rec2["sim_verdict_copied"] and rec2["v3_status"] == "not_run" and calls["seq"] == 1
    # the runner: stage set `v3` for such a payload, `v1v2` for the sim job, `full` for the one-job pipeline; a decided full record is reused
    payload = {"d_rtl": [str(ACCU)], "c_rtl": [str(ACCU)], "top": "verified_accu", "clk": "clk", "rst": "rst_n", "rst_sense": "low"}
    assert RE.equiv_extra(CFG, payload, True)["stages"] == "full" and RE.equiv_extra(CFG, payload, False)["stages"] == "v1v2"
    assert RE.equiv_extra(CFG, dict(payload, sim_record="/x"), True)["stages"] == "v3"
    h_full = RE.equiv_hash(payload["d_rtl"], payload["c_rtl"], payload["top"], CFG, RE.equiv_extra(CFG, payload, True))
    h_v3 = RE.equiv_hash(payload["d_rtl"], payload["c_rtl"], payload["top"], CFG, RE.equiv_extra(CFG, dict(payload, sim_record="/x"), True))
    assert h_full != h_v3
    root = tmp_path / "EQ"
    (root / h_full).mkdir(parents=True)
    (root / h_full / "equiv.json").write_text(json.dumps({"verdict": "inconclusive", "raw_dir": str(root / h_full)}))
    assert RE.full_record(CFG, dict(payload, sim_record="/x"), root) is None                     # inconclusive: proved again
    (root / h_full / "equiv.json").write_text(json.dumps({"verdict": "falsified", "raw_dir": str(root / h_full), "v3_status": "falsified"}))
    reused = RE.full_record(CFG, dict(payload, sim_record="/x"), root)
    assert reused and reused["verdict"] == "falsified"
    assert RE.load_record(tmp_path / "nowhere") is None


def test_harness_version_2_zeroes_every_sequential_and_stamps_records(tmp_path):
    """DECISION 2026-09-18 (d) C1: under harness_version 2 the SEQ script zeroes every sequential (memories and z-assigned registers
    included) before the reset run and keeps the G2.2 line; the proof record's hash includes the version (a v2 proof never reuses a v1
    record) while V1 / V2 records and v1 proofs keep their hashes; records carry harness_version. Both directions."""
    from src.equiv import seq_tcl as ST
    from src.equiv.run_equiv import equiv_extra
    v1 = ST.seq_tcl(["d.v"], ["c.v"], "top", "top", "clk", "rst", "low", "24M", 1, "verilog", True)
    v2 = ST.seq_tcl(["d.v"], ["c.v"], "top", "top", "clk", "rst", "low", "24M", 1, "verilog", True, harness_version=2)
    assert "sim_set_state -all -apply 0" not in v1 and "sim_set_state -uninitialized -apply 0" in v1
    lines = v2.splitlines()
    assert lines.index("sim_set_state -all -apply 0") < lines.index("sim_run -stable") < lines.index("sim_set_state -uninitialized -apply 0") < lines.index("sim_save_reset")
    assert "sim_config -report_uninit ON" in lines and "-enable_structural_x" not in v2
    assert "-enable_structural_x true" in ST.seq_tcl(["d.v"], ["c.v"], "top", "top", "clk", "rst", "low", "24M", 1, "verilog", True, harness_version=2, structural_x=True)
    cfg1 = {"equiv": {"harness_version": 1}, "sim": {}}
    cfg2 = {"equiv": {"harness_version": 2}, "sim": {}}
    payload = {"clk": "clk", "rst": "rst", "rst_sense": "low"}
    assert "harness_version" not in equiv_extra(cfg1, payload, True)
    assert equiv_extra(cfg2, payload, True)["harness_version"] == 2 and equiv_extra(cfg2, dict(payload, sim_record={"x": 1}), True)["harness_version"] == 2
    assert "harness_version" not in equiv_extra(cfg2, payload, False)                       # a V1 / V2-only record is the same under both versions


def test_harness_version_2_rewrites_xz_literals_identically(tmp_path):
    """DECISION 2026-09-18 (e) item 1: every x / z / ? digit of a Verilog literal in the V3 sources becomes 0 (both sides, same base
    names); values, sizes, bases and everything else are untouched. Both directions."""
    from src.equiv.seq import rewrite_xz_literals, xz_free_copies
    src = "always @(posedge clk) if (!rstn) dout <= 8'bz; else if (rd) dout <= 8'bzz; assign bus = en ? d : 4'bZZZZ; wire [3:0] k = 4'b1x0?; wire h = 8'hzF; wire ok = 8'hA5 + 3'd7 - 1'b1;\n"
    out, n = rewrite_xz_literals(src)
    assert n == 5 and "8'b0" in out and "8'b00" in out and "4'b0000" in out and "4'b1000" in out and "8'h0F" in out and "8'hA5 + 3'd7 - 1'b1" in out
    assert rewrite_xz_literals("assign y = a & 8'hff; // no x or z\n") == ("assign y = a & 8'hff; // no x or z\n", 0)
    f = tmp_path / "d.v"; f.write_text(src)
    paths, counts = xz_free_copies([str(f)], tmp_path / "spec_src")
    assert Path(paths[0]).name == "d.v" and counts == {"d.v": 5} and "'bz" not in Path(paths[0]).read_text() and f.read_text() == src   # the original file is untouched
