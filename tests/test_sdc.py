"""Tests for the shared SDC generator (src/eval/sdc.py)."""
from src import config as C
from src.eval.sdc import dc_sdc, opensta_sdc

CFG = C.load()


def test_opensta_sdc_has_every_constraint_family():
    s = opensta_sdc("top_x", "clk", 2.5, CFG, "nangate45")
    assert "current_design top_x" in s
    assert "create_clock -name clk -period 2.5 [get_ports clk]" in s
    assert "all_inputs -no_clocks" in s
    assert "set_input_delay 0.5 -clock clk" in s and "set_output_delay 0.5 -clock clk" in s  # 20% of 2.5
    assert "set_driving_cell -lib_cell BUF_X1" in s
    assert "set_max_fanout 20" in s
    assert "set_load" not in s


def test_virtual_clock_for_combinational_designs():
    s = opensta_sdc("comb", None, 1.0, CFG, "sky130hd")
    assert "create_clock -name clk -period 1" in s and "get_ports" not in s.split("create_clock")[1].splitlines()[0]
    assert "sky130_fd_sc_hd__buf_1" in s


def test_dc_rewrite_replaces_no_clocks_and_scales_time_units():
    s = opensta_sdc("top_x", "clk", 0.5, CFG, "asap7")
    d = dc_sdc(s, CFG["libs"]["asap7"]["time_scale"])
    assert "all_inputs -no_clocks" not in d and "snps_all_inputs_no_clocks" in d
    assert "-period 500 " in d and "set_input_delay 100 " in d and "set_output_delay 100 " in d
    assert "BUFx2_ASAP7_75t_R" in d  # cell names untouched
    unscaled = dc_sdc(s, 1.0)
    assert "-period 0.5 " in unscaled
