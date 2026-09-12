# rtllm — source record (Phase 1.1)

- Source: https://github.com/hkust-zhiyao/RTLLM
- Pinned commit: `41b26896e33b536940116a975626455eed3de65e` (local checkout at `/home/hping/RTLLM`: verified)
- License: MIT
- Note: -
- Staged designs: 50; skipped: 0

Staged copies (`rtl/`, `tb/`, `reference/`, `samples/`) are rebuilt by `scripts/stage_designs.py` and are not versioned; `design.json` carries top, ports, provenance and sha256 of every copy.

## Designs

| design_id | top | loc | clocks | tb | reference | source paths |
|---|---|---|---|---|---|---|
| rtllm_accu | accu | 77 | clk | y | - | Arithmetic/Accumulator/accu/verified_accu.v |
| rtllm_adder_16bit | adder_16bit | 123 | - | y | - | Arithmetic/Adder/adder_16bit/verified_adder_16bit.v |
| rtllm_adder_32bit | adder_32bit | 181 | - | y | - | Arithmetic/Adder/adder_32bit/verified_adder_32bit.v |
| rtllm_adder_8bit | adder_8bit | 23 | - | y | - | Arithmetic/Adder/adder_8bit/verified_adder_8bit.v |
| rtllm_adder_bcd | adder_bcd | 22 | - | y | - | Arithmetic/Adder/adder_bcd/verified_adder_bcd.v |
| rtllm_adder_pipe_64bit | adder_pipe_64bit | 195 | clk | y | - | Arithmetic/Adder/adder_pipe_64bit/verified_adder_64bit.v |
| rtllm_comparator_3bit | comparator_3bit | 13 | - | y | - | Arithmetic/Comparator/comparator_3bit/verified_comparator_3bit.v |
| rtllm_comparator_4bit | comparator_4bit | 21 | - | y | - | Arithmetic/Comparator/comparator_4bit/verified_comparator_4bit.v |
| rtllm_div_16bit | div_16bit | 38 | - | y | - | Arithmetic/Divider/div_16bit/verified_div_16bit.v |
| rtllm_radix2_div | radix2_div | 83 | clk | y | - | Arithmetic/Divider/radix2_div/verified_radix2_div.v |
| rtllm_multi_16bit | multi_16bit | 57 | clk | y | - | Arithmetic/Multiplier/multi_16bit/verified_multi_16bit.v |
| rtllm_multi_8bit | multi_8bit | 23 | - | y | - | Arithmetic/Multiplier/multi_8bit/verified_multi_8bit.v |
| rtllm_multi_booth_8bit | multi_booth_8bit | 42 | clk | y | - | Arithmetic/Multiplier/multi_booth_8bit/verified_booth4_mul.v |
| rtllm_multi_pipe_4bit | multi_pipe_4bit | 53 | clk | y | - | Arithmetic/Multiplier/multi_pipe_4bit/verified_multi_pipe_4bit.v |
| rtllm_multi_pipe_8bit | multi_pipe_8bit | 92 | clk | y | - | Arithmetic/Multiplier/multi_pipe_8bit/verified_multi_pipe_8bit.v |
| rtllm_fixed_point_adder | fixed_point_adder | 52 | - | y | - | Arithmetic/Other/fixed_point_adder/verified_fixed_point_adder.v |
| rtllm_fixed_point_substractor | fixed_point_subtractor | 51 | - | y | - | Arithmetic/Other/fixed_point_substractor/verified_fixed_point_substractor.v |
| rtllm_float_multi | float_multi | 165 | clk | y | - | Arithmetic/Other/float_multi/verified_float_multi.v |
| rtllm_sub_64bit | sub_64bit | 18 | - | y | - | Arithmetic/Substractor/sub_64bit/verified_sub_64bit.v |
| rtllm_JC_counter | JC_counter | 14 | clk | y | - | Control/Counter/JC_counter/verified_JC_counter.v |
| rtllm_counter_12 | counter_12 | 33 | clk | y | - | Control/Counter/counter_12/verified_counter_12.v |
| rtllm_ring_counter | ring_counter | 23 | clk | y | - | Control/Counter/ring_counter/verified_ring_counter.v |
| rtllm_up_down_counter | up_down_counter | 31 | clk | y | - | Control/Counter/up_down_counter/verified_up_down_counter.v |
| rtllm_fsm | fsm | 77 | CLK | y | - | Control/Finite State Machine/fsm/verified_fsm.v |
| rtllm_sequence_detector | sequence_detector | 48 | clk | y | - | Control/Finite State Machine/sequence_detector/verified_sequence_detector.v |
| rtllm_asyn_fifo | asyn_fifo | 147 | - | y | - | Memory/FIFO/asyn_fifo/verified_asyn_fifo.v |
| rtllm_LIFObuffer | LIFObuffer | 51 | - | y | - | Memory/LIFO/LIFObuffer/verified_LIFObuffer.v |
| rtllm_LFSR | LFSR | 15 | clk | y | - | Memory/Shifter/LFSR/verified_LFSR.v |
| rtllm_barrel_shifter | barrel_shifter | 45 | - | y | - | Memory/Shifter/barrel_shifter/verified_barrel_shifter.v |
| rtllm_right_shifter | right_shifter | 15 | clk | y | - | Memory/Shifter/right_shifter/verified_right_shifter.v |
| rtllm_freq_div | freq_div | 45 | - | y | - | Miscellaneous/Frequency divider/freq_div/verified_freq_div.v |
| rtllm_freq_divbyeven | freq_divbyeven | 27 | clk | y | - | Miscellaneous/Frequency divider/freq_divbyeven/verified_freq_divbyeven.v |
| rtllm_freq_divbyfrac | freq_divbyfrac | 58 | clk | y | - | Miscellaneous/Frequency divider/freq_divbyfrac/verified_freq_divbyfrac.v |
| rtllm_freq_divbyodd | freq_divbyodd | 49 | clk | y | - | Miscellaneous/Frequency divider/freq_divbyodd/verified_freq_divbyodd.v |
| rtllm_calendar | calendar | 37 | CLK | y | - | Miscellaneous/Others/calendar/verified_calendar.v |
| rtllm_edge_detect | edge_detect | 37 | clk | y | - | Miscellaneous/Others/edge_detect/verified_edge_detect.v |
| rtllm_parallel2serial | parallel2serial | 39 | clk | y | - | Miscellaneous/Others/parallel2serial/verified_parallel2serial.v |
| rtllm_pulse_detect | pulse_detect | 76 | clk | y | - | Miscellaneous/Others/pulse_detect/verified_pulse_detect.v |
| rtllm_serial2parallel | serial2parallel | 45 | clk | y | - | Miscellaneous/Others/serial2parallel/verified_serial2parallel.v |
| rtllm_synchronizer | synchronizer | 44 | - | y | - | Miscellaneous/Others/synchronizer/verified_synchronizer.v |
| rtllm_traffic_light | traffic_light | 101 | clk | y | - | Miscellaneous/Others/traffic_light/verified_traffic_light.v |
| rtllm_width_8to16 | width_8to16 | 44 | clk | y | - | Miscellaneous/Others/width_8to16/verified_width_8to16.v |
| rtllm_RAM | RAM | 36 | clk | y | - | Miscellaneous/RISC-V/RAM/verified_RAM.v |
| rtllm_ROM | ROM | 22 | - | y | - | Miscellaneous/RISC-V/ROM/verified_ROM.v |
| rtllm_alu | alu | 111 | - | y | - | Miscellaneous/RISC-V/alu/verified_alu.v |
| rtllm_clkgenerator | clkgenerator | 16 | - | y | - | Miscellaneous/RISC-V/clkgenerator/verified_clkgenerator.v |
| rtllm_instr_reg | instr_reg | 35 | clk | y | - | Miscellaneous/RISC-V/instr_reg/verified_instr_reg.v |
| rtllm_pe | pe | 27 | clk | y | - | Miscellaneous/RISC-V/pe/verified_pe.v |
| rtllm_signal_generator | signal_generator | 35 | clk | y | - | Miscellaneous/Signal generation/signal_generator/verified_signal_generator.v |
| rtllm_square_wave | square_wave | 24 | clk | y | - | Miscellaneous/Signal generation/square_wave/verified_square_wave.v |
