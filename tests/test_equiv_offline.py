"""Offline tests of the equivalence stack pieces (Yosys is local and fast; no license): port extraction and
comparison, candidate renaming, harness generation, trace comparison with latency offsets."""
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
