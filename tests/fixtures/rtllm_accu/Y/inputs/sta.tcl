read_liberty /home/hping/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_verilog /home/hping/Beyond-Synth/results/raw/rtllm_accu/Y/12f52ceb1e7fdf1a/outputs/netlist.v
link_design verified_accu
read_sdc /home/hping/Beyond-Synth/results/raw/rtllm_accu/Y/12f52ceb1e7fdf1a/inputs/constraint.sdc
report_checks -path_delay max -format full_clock_expanded
report_wns
report_tns
exit
