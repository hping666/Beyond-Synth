# Phase 1 report — design sets and constraints

Generated 2026-09-12 14:51 by scripts/report_phase.py (git c748712f471b, cfg 386abc93a383). Data: reports/data/phase1_inventory.json, phase1_trial.json, phase1_knee.json; catalogue data/designs/<suite>/.

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
| cktevo | 83 | 122 / 417 / 3161 | 77 | 0 | 4 | 11 | 0 | 67 |
| drrtl | 20 | 128 / 463 / 4616 | 20 | 2 | 1 | 1 | 1 | 7 |
| rtllm | 50 | 13 / 44 / 195 | 47 | 50 | 15 | 1 | 1 | 17 |
| rtlopt | 40 | 8 / 23 / 135 | 39 | 0 | 29 | 0 | 1 | 1 |
| rtlrewriter | 72 | 8 / 41 / 1418 | 66 | 2 | 42 | 0 | 0 | 13 |

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
- drrtl_FIFO: clk_in clk_out
- rtllm_asyn_fifo: wclk rclk

Designs Yosys cannot parse (affects only the Y / O rungs and V1; DC is the arbiter):

- cktevo_risc__cache_sys: yosys exit 1: /home/hping/Beyond-Synth/data/designs/cktevo/risc__cache_sys/rtl/l2_cache_datapath.v:217: Warning: Identifier `\WRITE_EN_0_MUX
- cktevo_risc__l2_cache: yosys exit 1: /home/hping/Beyond-Synth/data/designs/cktevo/risc__l2_cache/rtl/l2_cache_datapath.v:217: Warning: Identifier `\WRITE_EN_0_MUX.
- cktevo_risc__l2_cache_datapath: yosys exit 1: /home/hping/Beyond-Synth/data/designs/cktevo/risc__l2_cache_datapath/rtl/l2_cache_datapath.v:217: Warning: Identifier `\WRITE_
- cktevo_risc__p_i_cache: yosys exit 1: /home/hping/Beyond-Synth/data/designs/cktevo/risc__p_i_cache/rtl/p_i_cache_metadata_check.v:166: Warning: Identifier `\WRITE_E
- cktevo_risc__p_i_cache_metadata_check: yosys exit 1: /home/hping/Beyond-Synth/data/designs/cktevo/risc__p_i_cache_metadata_check/rtl/p_i_cache_metadata_check.v:166: Warning: Ident
- cktevo_simple_cpu__simple_cpu: yosys exit -6: terminate called after throwing an instance of 'std::out_of_range'
- rtllm_RAM: yosys exit -6: terminate called after throwing an instance of 'std::out_of_range'
- rtllm_float_multi: yosys exit 1: /home/hping/Beyond-Synth/data/designs/rtllm/float_multi/rtl/float_multi.v:17: ERROR: Found non-synthesizable event list!
- rtllm_synchronizer: ERROR: Multiple edge sensitive events found for this signal!
- rtlopt_mux_encode: yosys exit 1: /home/hping/Beyond-Synth/data/designs/rtlopt/mux_encode/rtl/mux_encode.sv:3: ERROR: syntax error, unexpected '[', expecting ')
- rtlrewriter_algorithm__gemm: TimeoutExpired: Command '['/home/hping/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys', '-q', '-p', 'read_verilog -sv  /home/hping/Beyo
- rtlrewriter_basic__if_prority: yosys exit 1: /home/hping/Beyond-Synth/data/designs/rtlrewriter/basic__if_prority/rtl/basic.v:16: ERROR: syntax error, unexpected invalid to
- rtlrewriter_long_cnn__convLayerSingle: yosys exit 1: signs/rtlrewriter/long_cnn__convLayerSingle/rtl/processingElementRaw.v:36: Warning: Identifier `\intermediateResult2' is impli
- rtlrewriter_long_cnn__convUnit: yosys exit 1: /Beyond-Synth/data/designs/rtlrewriter/long_cnn__convUnit/rtl/processingElementRaw.v:36: Warning: Identifier `\intermediateRes
- rtlrewriter_long_cnn__processingElement: yosys exit 1: signs/rtlrewriter/long_cnn__processingElement/rtl/processingElementRaw.v:36: Warning: Identifier `\intermediateResult2' is imp
- rtlrewriter_long_huffman__Decoder: yosys exit 1: rRaw.v:101.17-101.342.

## 3. E4 trial synthesis (PLAN 1.2)

Configuration E4 at 4.0 ns (loosest Nangate45 knee period), through the queue daemon.

| suite | designs | synthesizable | failed | pending | DC hours |
|---|---|---|---|---|---|
| cktevo | 83 | 13 | 0 | 70 | 0.25 |
| drrtl | 20 | 4 | 0 | 16 | 0.14 |
| rtllm | 50 | 17 | 2 | 31 | 0.29 |
| rtlopt | 40 | 12 | 0 | 28 | 0.22 |
| rtlrewriter | 72 | 6 | 6 | 60 | 0.14 |

RTLLM v2.0 synthesizable count N under this machine's DC E4: **17** of 50.

Failures and reasons:

- rtllm_clkgenerator: eval_failed: Error: Value for list 'port_pin_list' must have 1 elements. (CMD-036)
- rtllm_float_multi: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtllm_float_multi/E4/a1d104a2d1ae68d6-r2/inputs/rtl/float_multi.v:17: The event depends on both edge and nonedge expressions, which synthesis does not support. (ELAB-91)
- rtlrewriter_datapath__constant_propagation: eval_failed: no leaf cells after compile
- rtlrewriter_datapath__loop_tiling: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_datapath__loop_tiling/E4/accbbdf396d8085d-r2/inputs/rtl/loop_tiling_raw.v:10: The construct 'post-increment assignment operator ++' is not supported in this language. (VER-720)
- rtlrewriter_datapath__multiplier_architecture: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_datapath__multiplier_architecture/E4/18f5ecf37eedb71a-r2/inputs/rtl/multiplier_architecture.v:14: The construct 'C-style unpacked dimension' is not supported in this language. (VER-720)
- rtlrewriter_long_cpu__PipelineCPU: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_long_cpu__PipelineCPU/E4/d8a2abbc5af04275-r2/inputs/rtl/PipelineCPURaw.v:155: bad hierarchical name (ID_EX_Reg). (VER-264)
- rtlrewriter_long_huffman__Decoder: eval_failed: Error:  /home/hping/Beyond-Synth/results/raw/rtlrewriter_long_huffman__Decoder/E4/fc4f176cef8b0879-r2/inputs/rtl/DecoderRaw.v:97: Assigment to 'result1' requires that it be a register. (VER-952)
- rtlrewriter_mux__mux_dead_code: eval_failed: Error: Width mismatch on port 'sum_result' of reference to 'adder' in 'example'. (LINK-3)

E4 seconds per design at the loosest period: min 54, median 62, max 202 (n = 52).

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

(not collected yet: scripts/phase1_collect.py knee)

## 7. designs table (acceptance check)

265 rows; 60 with suite / path / loc / tb_available / e4_synthesizable filled; 0 with Φ_main(nangate45); split: {None: 265}.

## 8. Anomalies and next steps

- Anomalies are listed in sections 2 and 3 (Yosys parse failures, DC failures with reasons, multi-clock designs).
- Next: knee sweeps for every synthesizable single-clock design (PLAN 1.3), dev / held split (1.4), CktEvo set and Sky130 subset (1.5), then Phase 2.
