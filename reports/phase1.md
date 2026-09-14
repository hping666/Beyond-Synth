# Phase 1 report — design sets and constraints

Generated 2026-09-14 04:19 by scripts/report_phase.py (git f8927024f8ee, cfg 35f19caaffcd). Data: reports/data/phase1_inventory.json, phase1_trial.json, phase1_knee.json; catalogue data/designs/<suite>/.

## 1. Sources (PLAN 1.1)

| suite | source | commit | license | staged | note |
|---|---|---|---|---|---|
| rtllm | https://github.com/hkust-zhiyao/RTLLM | `41b26896e3` | MIT | 50 | - |
| drrtl | https://github.com/hkust-zhiyao/DR_RTL | `62b95a5722` | unspecified (no LICENSE file in the repository) | 20 | - |
| rtlopt | https://github.com/hkust-zhiyao/RTL-OPT | `25e4bbe052` | MIT | 40 | the paper's anonymous repository (anonymous.4open.science/r/RTL-OPT-20C5) reports repository_expired (HTTP 410, 2026-09-12); this is the authors' public release with 40 pairs |
| cktevo | https://github.com/cure-lab/cktevo | `2f1abe75cc` | unspecified at repository level (the OpenCores cores carry their own LGPL/GPL headers) | 83 | - |
| rtlrewriter | https://github.com/yaoxufeng/RTLRewriter-Bench | `96639fe67b` | unspecified (no LICENSE file in the repository) | 72 | - |

RTL-OPT's anonymous repository named in the paper has expired (HTTP 410); the authors' public release is used (40 pairs, the proposal counted 36). Dr.RTL's 20 designs are public, so PLAN 1.1's substitution rule was not needed.

## 2. Inventory (PLAN 1.2)

| suite | designs | loc (min / median / max) | Yosys ok | with testbench | combinational | multi-clock | SystemVerilog | DC markers |
|---|---|---|---|---|---|---|---|---|
| cktevo | 83 | 122 / 423 / 3161 | 77 | 0 | 4 | 11 | 0 | 67 |
| rtlrewriter | 72 | 8 / 41 / 1418 | 67 | 2 | 42 | 0 | 0 | 13 |

DC markers = files with initial blocks, delay controls, system tasks, `include, `ifdef or `timescale (eda-knowledge/06-boundaries.md); they are informational, the E4 trial decides synthesizability. Clock ports are identified by use (Yosys flip-flop clock pins after flattening, src/designs/yosys_probe.py), not by name.

Multi-clock designs (inventoried and trial-synthesized with one clock per port, excluded from the knee sweeps and the search sets, DECISIONS 2026-09-12):

- cktevo_ethmac__eth_maccontrol: MTxClk MRxClk
- cktevo_ethmac__eth_macstatus: MRxClk MTxClk
- cktevo_ethmac__eth_receivecontrol: MTxClk MRxClk
- cktevo_ethmac__eth_registers: Clk TxClk RxClk
- cktevo_ethmac__eth_wishbone: WB_CLK_I MTxClk MRxClk
- cktevo_mem_ctrl__mc_mem_if: clk mc_clk
- cktevo_mem_ctrl__mc_timing: clk mc_clk
- cktevo_usb__usbf_sync: phy_clk_i hclk_i
- cktevo_vga_enh__generic_dpram: rclk wclk
- cktevo_vga_enh__vga_fifo_dc: rclk wclk
- cktevo_vga_enh__vga_pgen: clk_i pclk_i

Designs Yosys cannot parse (affects only the Y / O rungs and V1; DC is the arbiter):

- cktevo_risc__cache_sys: yosys exit 1: /home/hping/Beyond-Synth/data/designs/cktevo/risc__cache_sys/rtl/l2_cache_datapath.v:217: Warning: Identifier `\WRITE_EN_0_MUX
- cktevo_risc__l2_cache: yosys exit 1: /home/hping/Beyond-Synth/data/designs/cktevo/risc__l2_cache/rtl/l2_cache_datapath.v:217: Warning: Identifier `\WRITE_EN_0_MUX.
- cktevo_risc__l2_cache_datapath: yosys exit 1: /home/hping/Beyond-Synth/data/designs/cktevo/risc__l2_cache_datapath/rtl/l2_cache_datapath.v:217: Warning: Identifier `\WRITE_
- cktevo_risc__p_i_cache: yosys exit 1: /home/hping/Beyond-Synth/data/designs/cktevo/risc__p_i_cache/rtl/p_i_cache_metadata_check.v:166: Warning: Identifier `\WRITE_E
- cktevo_risc__p_i_cache_metadata_check: yosys exit 1: /home/hping/Beyond-Synth/data/designs/cktevo/risc__p_i_cache_metadata_check/rtl/p_i_cache_metadata_check.v:166: Warning: Ident
- cktevo_simple_cpu__simple_cpu: yosys exit -6: terminate called after throwing an instance of 'std::out_of_range'
- rtlrewriter_basic__if_prority: yosys exit 1: /home/hping/Beyond-Synth/data/designs/rtlrewriter/basic__if_prority/rtl/basic.v:16: ERROR: syntax error, unexpected invalid to
- rtlrewriter_long_cnn__convLayerSingle: yosys exit 1: signs/rtlrewriter/long_cnn__convLayerSingle/rtl/processingElementRaw.v:36: Warning: Identifier `\intermediateResult2' is impli
- rtlrewriter_long_cnn__convUnit: yosys exit 1: /Beyond-Synth/data/designs/rtlrewriter/long_cnn__convUnit/rtl/processingElementRaw.v:36: Warning: Identifier `\intermediateRes
- rtlrewriter_long_cnn__processingElement: yosys exit 1: signs/rtlrewriter/long_cnn__processingElement/rtl/processingElementRaw.v:36: Warning: Identifier `\intermediateResult2' is imp
- rtlrewriter_long_huffman__Decoder: yosys exit 1: rRaw.v:101.17-101.342.

## 3. E4 trial synthesis (PLAN 1.2)

Configuration E4 at 4.0 ns (loosest Nangate45 knee period), through the queue daemon.

| suite | designs | synthesizable | failed | pending | DC hours |
|---|---|---|---|---|---|
| cktevo | 83 | 78 | 5 | 0 | 2.07 |
| drrtl | 20 | 19 | 1 | 0 | 0.53 |
| rtllm | 50 | 43 | 7 | 0 | 0.87 |
| rtlopt | 40 | 40 | 0 | 0 | 0.99 |
| rtlrewriter | 72 | 54 | 18 | 0 | 2.24 |

RTLLM v2.0 synthesizable count N under this machine's DC E4: **43** of 50.

Failures and reasons:

- cktevo_nn_engine__rates_256x4096: eval_failed: checklist failed: area_positive, cells_positive, timing_parsed, histogram_nonempty
- cktevo_nn_engine__tauRom_H7: eval_failed: checklist failed: area_positive, cells_positive, timing_parsed, histogram_nonempty
- cktevo_nn_engine__ultraRAMx72_TDP: eval_failed: dc_shell exceeded 1200 s
- cktevo_nn_engine__weights_1024x4096: eval_failed: checklist failed: area_positive, cells_positive, timing_parsed, histogram_nonempty
- cktevo_simple_cpu__simple_cpu: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/cktevo_simple_cpu__simple_cpu/E4/e30ca72b915aef03-r2/inputs/rtl/IDEXReg.v:46: Variable 'ctrSignalsOut' is the target of both blocking and nonblocking assignments in the same always block. (VER-134)
- drrtl_cpu_pipe: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/drrtl_cpu_pipe/E4/8a3949ea60e01ca3-r2/inputs/rtl/cpu_pipe.v:805: The symbol 'f_rpc_sel_wpc' is not defined. (VER-956)
- rtllm_ROM: eval_failed: checklist failed: area_positive, cells_positive, timing_parsed, histogram_nonempty
- rtllm_clkgenerator: eval_failed: checklist failed: timing_parsed
- rtllm_float_multi: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtllm_float_multi/E4/a1d104a2d1ae68d6-r2/inputs/rtl/float_multi.v:17: The event depends on both edge and nonedge expressions, which synthesis does not support. (ELAB-91)
- rtllm_freq_divbyodd: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtllm_freq_divbyodd/E4/d2daeabc1fb9a921-r2/inputs/rtl/freq_divbyodd.v:48: continuous assignment output clk_div must be a net. (VER-261)
- rtllm_ring_counter: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtllm_ring_counter/E4/0ecfddc342a78fc7-r2/inputs/rtl/ring_counter.v:19: continuous assignment output out must be a net. (VER-261)
- rtllm_sequence_detector: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtllm_sequence_detector/E4/d1aafdc8ed8fa1f8-r2/inputs/rtl/sequence_detector.v:30: Variable 'next_state' is the target of both blocking and nonblocking assignments in the same always block. (VER-134)
- rtllm_synchronizer: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtllm_synchronizer/E4/0252e2c620aba30c-r2/inputs/rtl/synchronizer.v:21: Cannot test variable 'brstn' because it was not in the event expression or with wrong polarity. (ELAB-300)
- rtlrewriter_algorithm__gemm: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_algorithm__gemm/E4/0e37861a2b48f012-r2/inputs/rtl/gemm_redundancy.v:32: Assigment to 'mult' requires that it be a register. (VER-952)
- rtlrewriter_algorithm__sort_merge: elaborate_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_algorithm__sort_merge/E4/bcf34805991c4d6d-r2/inputs/rtl/sort_merge_redundancy.v:44: Variable 'i' is the target of both blocking and nonblocking assignments in the same always block. (VER-134)
- rtlrewriter_basic__add3: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_basic__add3/E4/27d40d08dc0bccd2-r2/inputs/rtl/add3.v:8: The symbol 'reg_d' is not defined. (VER-956)
- rtlrewriter_datapath__adder_bit_width: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_datapath__adder_bit_width/E4/a464c5c2c2511472-r2/inputs/rtl/adder_bit_width.v:15: Assigment to 'sum' requires that it be a register. (VER-952)
- rtlrewriter_datapath__adder_resource: eval_failed: Error: Width mismatch on port 'sum' of reference to 'adder' in 'non_shared_adder'. (LINK-3)
- rtlrewriter_datapath__alu_resource: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_datapath__alu_resource/E4/7d3744cfeb67bd26-r2/inputs/rtl/alu_resource.v:24: Assigment to 'sum_result' requires that it be a register. (VER-952)
- rtlrewriter_datapath__constant_propagation: eval_failed: no leaf cells after compile
- rtlrewriter_datapath__loop_fusion: empty_netlist: no leaf cells after compile
- rtlrewriter_datapath__loop_jamming: eval_failed: checklist failed: area_positive, cells_positive, histogram_nonempty
- rtlrewriter_datapath__loop_unrolling: empty_netlist: no leaf cells after compile
- rtlrewriter_long_cnn__processingElement: elaborate_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_long_cnn__processingElement/E4/43f72d105d3dad12-r2/inputs/rtl/processingElementRaw.v:36: Type query about dimensions or access by indexing requires an array reference for signal intermediateResult2 as the first argument. (ELAB-400)
- rtlrewriter_long_cpu__ALU: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_long_cpu__ALU/E4/79dcdbab9a13838e-r2/inputs/rtl/ALURaw.v:53: Assigment to 'result1' requires that it be a register. (VER-952)
- rtlrewriter_long_cpu__InstMem: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_long_cpu__InstMem/E4/431a2660899b0bb4-r2/inputs/rtl/InstMemRaw.v:8: Syntax error at or near token ')'. (VER-294)
- rtlrewriter_long_cpu__PipelineCPU: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_long_cpu__PipelineCPU/E4/d8a2abbc5af04275-r2/inputs/rtl/PipelineCPURaw.v:155: bad hierarchical name (ID_EX_Reg). (VER-264)
- rtlrewriter_long_huffman__Decoder: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_long_huffman__Decoder/E4/1d5de18b248c192b-r2/inputs/rtl/DecoderRaw.v:97: Assigment to 'result1' requires that it be a register. (VER-952)
- rtlrewriter_memory__memory_banking: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_memory__memory_banking/E4/c7e3d8c16cd5e5a7-r2/inputs/rtl/memory_banking_raw.v:35: Net 'mem_bank[63][7]' or a directly connected net is driven by more than one source, and not all drivers are three-state. (ELAB-366)
- rtlrewriter_mux__mux_dead_code: eval_failed: Error: Width mismatch on port 'sum_result' of reference to 'adder' in 'example'. (LINK-3)
- rtlrewriter_mux__mux_type3: eval_failed: Error: Width mismatch on port 'in1' of reference to 'mux2to1' in 'mux_tree'. (LINK-3)

E4 seconds per design at the loosest period: min 58, median 73, max 1986 (n = 234).

## 4. CktEvo module pool

191 modules scanned in 10 repositories; pool rule own_loc ≥ 100, closure ≤ 3000 lines, no testbench-like module, no duplicated module name (DECISIONS 2026-09-12). Pool: 83 modules (ethmac 17, hsm 4, mem_ctrl 10, nn_engine 10, risc 15, sdc_ctrl 5, simple_cpu 1, spi 1, usb 10, vga_enh 10). The ~30-module set and the 8-module Sky130 subset (PLAN 1.5) are chosen after the knee sweep.

## 5. RTLRewriter-Bench (calibration only)

54 short cases and 18 long module pairs staged; file roles by the rule in src/designs/rtlrewriter.py: {'expert': 79, 'llm': 29, 'original': 75, 'other': 1, 'tool': 15} (original = start point, expert = engineers' rewrite, tool = RTLRewriter output, llm = GPT-4 / Claude 3 / RTLCoder / VeriGen samples). Role table for the hand check (start = the staged original, reference = expert version, samples = the rest):

| design | start file | reference | samples (role) |
|---|---|---|---|
| algorithm__gemm | gemm_redundancy.v | gemm.v | - |
| algorithm__md | md_redundancy.v | md.v | - |
| algorithm__sort_merge | sort_merge_redundancy.v | sort_merge.v | - |
| algorithm__spmv | spmv_redundancy.v | spmv.v | - |
| basic__add1 | basic.v | basic_optimized.v | - |
| basic__add3 | add3.v | add3_optimized.v | add3_claude3.v (llm), add3_gpt4.v (llm), add3_ours.v (tool) |
| basic__checksum | basic.v | basic_optimized.v | - |
| basic__communtativity_subpexpression2 | basic.v | basic_optimized.v | basic_RTLCoder.v (llm), basic_claude3.v (llm), basic_gpt4.v (llm) |
| basic__commutativity_subexpression | basic.v | basic_optimized.v | basic_RTLCoder.v (llm), basic_VeriGen.v (llm), basic_gpt4.v (llm), basic_ours.v (tool), optimized1.v (expert) |
| basic__distributed_ram | basic1.v | optimized.v | - |
| basic__flatten1 | basic.v | optimized.v | - |
| basic__if_else | basic1.v | optimized1.v | - |
| basic__if_prority | basic.v | basic_optimized.v | - |
| basic__logic_elimnation | basic1.v | optimized1.v | - |
| basic__multi_constant_multiplication | basic.v | basic_optimized.v | basic_gpt4.v (llm), basic_ours.v (tool) |
| basic__multi_constant_multiplication2 | basic.v | basic_optimized.v | basic_claude3.v (llm), basic_gpt4.v (llm), basic_ours.v (tool) |
| basic__register_balancing | basic1.v | optimized1.v | - |
| basic__sub-expression-basic | basic1.v | optimized1.v | - |
| datapath__adder_architecture | adder_architecture.v | adder_architecture_improve.v | - |
| datapath__adder_bit_width | adder_bit_width.v | adder_bit_width_optimized.v | adder_bit_width_gpt4.v (llm), adder_bit_width_ours.v (tool) |
| datapath__adder_resource | adder_resource.v | adder_resource_improve.v | - |
| datapath__adder_subexpression | adder_subexpression.v | adder_subexpression_optimized.v | adder_subexpression_claude3.v (llm), adder_subexpression_gpt4.v (llm), adder_subexpression_ours.v (tool) |
| datapath__algebraic_simplification | algebraic_simplification_raw.v | algebraic_simplification.v | - |
| datapath__alu_bit_width | alu_bit_width.v | alu_bit_width_improve.v | - |
| datapath__alu_resource | alu_resource.v | alu_resource_improve.v | - |
| datapath__alu_subexpression | alu_subexpression.v | alu_subexpression_optimized.v | alu_subexpression_claude3.v (llm), alu_subexpression_gpt4.v (llm), alu_subexpression_ours.v (tool) |
| datapath__constant_folding | constant_folding_raw.v | constant_folding.v | - |
| datapath__constant_propagation | constant_propagation_raw.v | constant_propagation.v | - |
| datapath__dead_code_elimination | dead_code_elimination_raw.v | dead_code_elimination.v | - |
| datapath__loop_fusion | loop_fusion_raw.v | loop_fusion.v | - |
| datapath__loop_jamming | loop_jamming_raw.v | loop_jamming.v | - |
| datapath__loop_tiling | loop_tiling_raw.v | loop_tiling.v | - |
| datapath__loop_unrolling | loop_unrolling_raw.v | loop_unrolling.v | - |
| datapath__multiplier_architecture | multiplier_architecture.v | multiplier_architecture_improve.v | - |
| datapath__multiplier_bitwidth | multiplier_bitwidth.v | multiplier_bitwidth_optimized.v | multiplier_bitwidth_claude3.v (llm), multiplier_bitwidth_gpt4.v (llm) |
| datapath__multiplier_subexpression | multiplier_subexpression.v | multiplier_subexpression_improve.v | - |
| datapath__strength_reduction | strength_reduction_raw.v | strength_reduction.v | - |
| datapath__subexpression_elimination | subexpression_elimination_raw.v | subexpression_elimination.v | - |
| fsm_small_case__example1 | example1_state.v | example1_state_optimized.v | example1_state_gpt4.v (llm), example1_state_ours.v (tool) |
| fsm_small_case__example2 | example2_state.v | example2_state_optimized.v | - |
| fsm_small_case__example3 | example3_state.v | example3_state_optimized.v | example3_state_gpt4.v (llm), example3_state_ours.v (tool), example3_state_revision.v (other) |
| fsm_small_case__example4 | example4_state.v | example4_state_optimized.v | - |
| fsm_small_case__example5 | example5_state.v | example5_state_optimized.v | - |
| long_cnn__RFselector | RFselector_raw.v | RFselector.v | - |
| long_cnn__convLayerSingle | convLayerSingle_raw.v | convLayerSingle.v | - |
| long_cnn__convUnit | convUnit_raw.v | convUnit.v | - |
| long_cnn__floatAdd | floatAdd_raw.v | floatAdd.v | - |
| long_cnn__floatMult | floatMult_raw.v | floatMult.v | - |
| long_cnn__processingElement | processingElementRaw.v | processingElement.v | - |
| long_cpu__ALU | ALURaw.v | ALU.v | - |
| long_cpu__BranchAndJumpHazard | BranchAndJumpHazardRaw.v | BranchAndJumpHazard.v | - |
| long_cpu__DataHazard | DataHazardRaw.v | DataHazard.v | - |
| long_cpu__DataMem | DataMemRaw.v | DataMem.v | DataMem_raw_1.v (original) |
| long_cpu__ImmExtend | ImmExtendRaw.v | ImmExtend.v | ImmExtend_raw_1.v (original), ImmExtend_raw_2.v (original) |
| long_cpu__InstMem | InstMemRaw.v | InstMem.v | - |
| long_cpu__PC | PCRaw.v | PC.v | - |
| long_cpu__PipelineCPU | PipelineCPURaw.v | PipelineCPU.v | - |
| long_cpu__RegFile | RegFileRaw.v | RegFile.v | - |
| long_fft__Butterfly | ButterflyRaw.v | Butterfly.v | - |
| long_huffman__Decoder | DecoderRaw.v | Decoder.v | - |
| long_huffman__HuffmanDecoder | HuffmanDecoderRaw.v | HuffmanDecoder.v | - |
| memory__memory_banking | memory_banking_raw.v | memory_banking_opt.v | - |
| memory__memory_compression | memory_compression_raw.v | memory_compression_opt.v | - |
| memory__memory_folding | memory_folding_raw.v | memory_folding_opt.v | - |
| memory__memory_folding2 | memory_folding_raw_1.v | memory_folding_opt_1.v | - |
| memory__memory_sharing | memory_sharing_raw.v | memory_sharing_opt.v | - |
| mux__mux_dead_code | mux_dead_code.v | mux_dead_code_optimized.v | mux_dead_code_claude3.v (llm), mux_dead_code_gpt4.v (llm), mux_dead_code_ours.v (tool) |
| mux__mux_type1 | mux_type1_redundancy.v | mux_type1_redundancy_improve.v | mux_type1_gpt4.v (llm), mux_type1_redundancy_gpt4.v (llm), mux_type1_ours.v (tool), mux_type1_redundancy_ours.v (tool), mux_type1_redundancy_optimized.v (expert) |
| mux__mux_type2 | mux_type2_redundancy.v | mux_type2_redundancy_improve.v | mux_type2_redundancy_optimized.v (expert) |
| mux__mux_type3 | mux_type3_redundancy.v | mux_type3_redundancy_improve.v | mux_type3_claude3.v (llm), mux_type3_gp4.v (llm), mux_type3_ours.v (tool), mux_type3_redundancy_optimized.v (expert) |
| mux__mux_type4 | mux_type4_redundancy.v | mux_type4_redundancy_improve.v | mux_type4_claude3.v (llm), mux_type4_gpt4.v (llm), mux_type_ours.v (tool), mux_type4_redundancy_optimzied.v (expert) |
| mux__mux_type5 | mux_type5_redundancy.v | mux_type5_redundancy_improve.v | mux_type5_gpt4.v (llm), mux_type5_ours.v (tool), mux_type5_redundancy_improve_more.v (expert), mux_type5_redundancy_optimized.v (expert) |

## 6. Knee-point constraints (PLAN 1.3)

| library | designs swept | complete sweeps | with Φ_main | fallback (no period met) | Φ_main histogram (ns: designs) |
|---|---|---|---|---|---|
| asap7 | 252 | 128 | 128 | 4 | 1.0: 21, 0.7: 14, 0.5: 21, 0.35: 25, 0.25: 20, 0.18: 13, 0.13: 10, 0.09: 4 |
| nangate45 | 252 | 180 | 221 | 6 | 4.0: 62, 2.8: 19, 2.0: 15, 1.4: 13, 1.0: 28, 0.7: 21, 0.5: 28, 0.35: 14, 0.25: 21 |
| sky130hd | 252 | 129 | 129 | 3 | 10.0: 11, 7.0: 13, 5.0: 13, 3.5: 14, 2.5: 19, 1.8: 19, 1.3: 21, 0.9: 9, 0.65: 10 |

Rule (spec 01 §3): candidates = periods with WNS ≥ −0.01·T; tightest T with area ≤ (1 + 0.1) × area(T_loosest); empty candidate set → smallest violation, `fallback`.

Spot-check curves (Nangate45, area in µm² / WNS in ns per period; Φ marked with *):

| design | 4 ns | 2.8 ns | 2 ns | 1.4 ns | 1 ns | 0.7 ns | 0.5 ns |
|---|---|---|---|---|---|---|---|
| rtllm_JC_counter | 343 / 3.10 | 343 / 2.14 | 343 / 1.50 | 343 / 1.02 | 343 / 0.70 | 343 / 0.46 | 343 / 0.30 |
| drrtl_DSP | 3528 / 0.00 | 3700 / 0.00 | 3680 / 0.00 | 3818 / 0.00* | 3917 / -0.23 | 4421 / -0.31 | 4548 / -0.48 |
| rtlopt_add_sub | 93 / 0.77 | 93 / 0.05* | 132 / 0.00 | 134 / 0.03 | 142 / 0.00 | 155 / -0.07 | 176 / -0.16 |
| cktevo_ethmac__eth_cop | 1114 / 1.92 | 1114 / 0.96 | 1114 / 0.32 | 1115 / 0.03 | 1137 / 0.00 | 1186 / 0.00* | 1272 / -0.11 |
| rtlrewriter_algorithm__spmv | 1133 / 1.91 | 1133 / 0.71* | 2403 / 0.00 | 2468 / 0.01 | 2821 / 0.01 | 1385 / 0.00 | 2002 / -0.00 |

Hand check of the five spot-check curves (operator, 2026-09-13):

- rtllm_JC_counter: area 343 µm² at every period, timing met down to 0.5 ns (+0.30 ns) → Φ = 0.5 ns (the tightest swept period; a 4-bit Johnson counter meets everything). Sensible.
- drrtl_DSP: met at 4.0–1.4 ns with area rising 3528 → 3818 (+8 %); at 1.0 ns WNS −0.23 ns → Φ = 1.4 ns. Sensible.
- rtlopt_add_sub: met at every period, but the area jumps from 93 to 132 µm² (+42 %) between 2.8 and 2.0 ns → the +10 % bound stops at Φ = 2.8 ns, i.e. just before the area explosion — the knee the rule is meant to find. Sensible.
- cktevo_ethmac__eth_cop: met down to 0.7 ns with +6.5 % area; at 0.5 ns area +14 % and WNS −0.11 ns → Φ = 0.7 ns. Sensible.
- rtlrewriter_algorithm__spmv: met at 2.8 ns with unchanged area; at 2.0 ns DC more than doubles the area (2403 µm²), and the curve is non-monotone below (1385 µm² at 0.7 ns): the bound relative to the loosest area keeps Φ = 2.8 ns. Sensible; the non-monotone tail is a DC restructuring effect worth remembering when reading area deltas at tight periods.

Fallback designs among the sets (no swept period met on any library): drrtl_LSTM (deep combinational cell), rtllm_div_16bit, rtlopt_divider_8bit / 16bit / 32bit (combinational dividers, 9–13 ns critical paths): Φ = the loosest period with `knee_fallback = true`; their baselines carry negative WNS by construction. Missing hidden-library periods: rtllm_freq_divbyfrac on ASAP7 (negative-edge flip-flop absent from the library subset) and rtlopt_divider_32bit on ASAP7 / sky130hd (every point exceeded the 17-minute DC limit) → no H2a / H2b certification for those two designs.

## 7. designs table (acceptance check)

265 rows; 265 with suite / path / loc / tb_available / e4_synthesizable filled; 221 with Φ_main(nangate45); split: {'held': 108, None: 137, 'dev': 20}.

## 8. Anomalies and next steps

- Anomalies are listed in sections 2 and 3 (Yosys parse failures, DC failures with reasons, multi-clock designs).
- Next: knee sweeps for every synthesizable single-clock design (PLAN 1.3), dev / held split (1.4), CktEvo set and Sky130 subset (1.5), then Phase 2.
