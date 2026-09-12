# rtlrewriter — source record (Phase 1.1)

- Source: https://github.com/yaoxufeng/RTLRewriter-Bench
- Pinned commit: `96639fe67bc8f020c05978ef5028d75fcf6980f2` (local checkout at `data/sources/RTLRewriter-Bench`: verified)
- License: unspecified (no LICENSE file in the repository)
- Note: -
- Staged designs: 72; skipped: 0

Staged copies (`rtl/`, `tb/`, `reference/`, `samples/`) are rebuilt by `scripts/stage_designs.py` and are not versioned; `design.json` carries top, ports, provenance and sha256 of every copy.

## Designs

| design_id | top | loc | clocks | tb | reference | source paths |
|---|---|---|---|---|---|---|
| rtlrewriter_algorithm__gemm | gemm | 51 | clk | - | y | short_benchmark/algorithm/gemm/gemm.v, short_benchmark/algorithm/gemm/gemm_redundancy.v |
| rtlrewriter_algorithm__md | MolecularDynamics | 51 | clk | - | y | short_benchmark/algorithm/md/md.v, short_benchmark/algorithm/md/md_redundancy.v |
| rtlrewriter_algorithm__sort_merge | MergeSort | 66 | clk | - | y | short_benchmark/algorithm/sort_merge/sort_merge.v, short_benchmark/algorithm/sort_merge/sort_merge_redundancy.v |
| rtlrewriter_algorithm__spmv | spmv | 78 | clk | - | y | short_benchmark/algorithm/spmv/spmv.v, short_benchmark/algorithm/spmv/spmv_redundancy.v |
| rtlrewriter_basic__add1 | example | 14 | - | - | y | short_benchmark/basic/add1/basic.v, short_benchmark/basic/add1/basic_optimized.v |
| rtlrewriter_basic__add3 | example | 16 | clk | - | y | short_benchmark/basic/add3/add3.v, short_benchmark/basic/add3/add3_claude3.v, short_benchmark/basic/add3/add3_gpt4.v ... |
| rtlrewriter_basic__checksum | example | 8 | - | - | y | short_benchmark/basic/checksum/basic.v, short_benchmark/basic/checksum/basic_optimized.v |
| rtlrewriter_basic__communtativity_subpexpression2 | example | 14 | - | - | y | short_benchmark/basic/communtativity_subpexpression2/basic.v, short_benchmark/basic/communtativity_subpexpression2/basic_RTLCoder.v, short_benchmark/basic/communtativity_subpexpression2/basic_claude3.v ... |
| rtlrewriter_basic__commutativity_subexpression | arithmetic_operations | 14 | - | - | y | short_benchmark/basic/commutativity_subexpression/basic.v, short_benchmark/basic/commutativity_subexpression/basic_RTLCoder.v, short_benchmark/basic/commutativity_subexpression/basic_VeriGen.v ... |
| rtlrewriter_basic__distributed_ram | memory_blockram | 22 | clk | - | y | short_benchmark/basic/distributed_ram/basic1.v, short_benchmark/basic/distributed_ram/optimized.v |
| rtlrewriter_basic__flatten1 | multiplexer_structured | 24 | - | - | y | short_benchmark/basic/flatten1/basic.v, short_benchmark/basic/flatten1/optimized.v |
| rtlrewriter_basic__if_else | MUX6to1 | 19 | - | - | y | short_benchmark/basic/if_else/basic1.v, short_benchmark/basic/if_else/optimized1.v |
| rtlrewriter_basic__if_prority | example | 16 | - | - | y | short_benchmark/basic/if_prority/basic.v, short_benchmark/basic/if_prority/basic_optimized.v |
| rtlrewriter_basic__logic_elimnation | logic_reduce | 38 | clk | - | y | short_benchmark/basic/logic_elimnation/basic1.v, short_benchmark/basic/logic_elimnation/optimized1.v |
| rtlrewriter_basic__multi_constant_multiplication | example | 12 | - | - | y | short_benchmark/basic/multi_constant_multiplication/basic.v, short_benchmark/basic/multi_constant_multiplication/basic_gpt4.v, short_benchmark/basic/multi_constant_multiplication/basic_optimized.v ... |
| rtlrewriter_basic__multi_constant_multiplication2 | example | 12 | - | - | y | short_benchmark/basic/multi_constant_multiplication2/basic.v, short_benchmark/basic/multi_constant_multiplication2/basic_claude3.v, short_benchmark/basic/multi_constant_multiplication2/basic_gpt4.v ... |
| rtlrewriter_basic__register_balancing | add3 | 10 | clk | - | y | short_benchmark/basic/register_balancing/basic1.v, short_benchmark/basic/register_balancing/optimized1.v |
| rtlrewriter_basic__sub-expression-basic | multiplier | 13 | - | - | y | short_benchmark/basic/sub-expression-basic/basic1.v, short_benchmark/basic/sub-expression-basic/optimized1.v |
| rtlrewriter_datapath__adder_architecture | ripple_adder | 48 | - | - | y | short_benchmark/datapath/adder_architecture/adder_architecture.v, short_benchmark/datapath/adder_architecture/adder_architecture_improve.v |
| rtlrewriter_datapath__adder_bit_width | example | 18 | - | - | y | short_benchmark/datapath/adder_bit_width/adder_bit_width.v, short_benchmark/datapath/adder_bit_width/adder_bit_width_gpt4.v, short_benchmark/datapath/adder_bit_width/adder_bit_width_optimized.v ... |
| rtlrewriter_datapath__adder_resource | non_shared_adder | 54 | - | - | y | short_benchmark/datapath/adder_resource/adder_resource.v, short_benchmark/datapath/adder_resource/adder_resource_improve.v |
| rtlrewriter_datapath__adder_subexpression | example | 27 | - | - | y | short_benchmark/datapath/adder_subexpression/adder_subexpression.v, short_benchmark/datapath/adder_subexpression/adder_subexpression_claude3.v, short_benchmark/datapath/adder_subexpression/adder_subexpression_gpt4.v ... |
| rtlrewriter_datapath__algebraic_simplification | example_raw | 14 | - | - | y | short_benchmark/datapath/algebraic_simplification/algebraic_simplification.v, short_benchmark/datapath/algebraic_simplification/algebraic_simplification_raw.v |
| rtlrewriter_datapath__alu_bit_width | alu_raw | 37 | - | - | y | short_benchmark/datapath/alu_bit_width/alu_bit_width.v, short_benchmark/datapath/alu_bit_width/alu_bit_width_improve.v |
| rtlrewriter_datapath__alu_resource | DedicatedResources | 37 | - | - | y | short_benchmark/datapath/alu_resource/alu_resource.v, short_benchmark/datapath/alu_resource/alu_resource_improve.v |
| rtlrewriter_datapath__alu_subexpression | example | 59 | - | - | y | short_benchmark/datapath/alu_subexpression/alu_subexpression.v, short_benchmark/datapath/alu_subexpression/alu_subexpression_claude3.v, short_benchmark/datapath/alu_subexpression/alu_subexpression_gpt4.v ... |
| rtlrewriter_datapath__constant_folding | example_raw | 14 | - | - | y | short_benchmark/datapath/constant_folding/constant_folding.v, short_benchmark/datapath/constant_folding/constant_folding_raw.v |
| rtlrewriter_datapath__constant_propagation | example_raw | 10 | - | - | y | short_benchmark/datapath/constant_propagation/constant_propagation.v, short_benchmark/datapath/constant_propagation/constant_propagation_raw.v |
| rtlrewriter_datapath__dead_code_elimination | example_raw | 16 | - | - | y | short_benchmark/datapath/dead_code_elimination/dead_code_elimination.v, short_benchmark/datapath/dead_code_elimination/dead_code_elimination_raw.v |
| rtlrewriter_datapath__loop_fusion | example_raw | 18 | - | - | y | short_benchmark/datapath/loop_fusion/loop_fusion.v, short_benchmark/datapath/loop_fusion/loop_fusion_raw.v |
| rtlrewriter_datapath__loop_jamming | example_raw | 21 | - | - | y | short_benchmark/datapath/loop_jamming/loop_jamming.v, short_benchmark/datapath/loop_jamming/loop_jamming_raw.v |
| rtlrewriter_datapath__loop_tiling | example_raw | 16 | - | - | y | short_benchmark/datapath/loop_tiling/loop_tiling.v, short_benchmark/datapath/loop_tiling/loop_tiling_raw.v |
| rtlrewriter_datapath__loop_unrolling | example_raw | 14 | - | - | y | short_benchmark/datapath/loop_unrolling/loop_unrolling.v, short_benchmark/datapath/loop_unrolling/loop_unrolling_raw.v |
| rtlrewriter_datapath__multiplier_architecture | array_multiplier | 49 | - | - | y | short_benchmark/datapath/multiplier_architecture/multiplier_architecture.v, short_benchmark/datapath/multiplier_architecture/multiplier_architecture_improve.v |
| rtlrewriter_datapath__multiplier_bitwidth | inefficient_multiplier | 41 | - | - | y | short_benchmark/datapath/multiplier_bitwidth/multiplier_bitwidth.v, short_benchmark/datapath/multiplier_bitwidth/multiplier_bitwidth_claude3.v, short_benchmark/datapath/multiplier_bitwidth/multiplier_bitwidth_gpt4.v ... |
| rtlrewriter_datapath__multiplier_subexpression | basic_array_multiplier | 39 | - | - | y | short_benchmark/datapath/multiplier_subexpression/multiplier_subexpression.v, short_benchmark/datapath/multiplier_subexpression/multiplier_subexpression_improve.v |
| rtlrewriter_datapath__strength_reduction | example_raw | 17 | - | - | y | short_benchmark/datapath/strength_reduction/strength_reduction.v, short_benchmark/datapath/strength_reduction/strength_reduction_raw.v |
| rtlrewriter_datapath__subexpression_elimination | example_raw | 22 | - | - | y | short_benchmark/datapath/subexpression_elimination/subexpression_elimination.v, short_benchmark/datapath/subexpression_elimination/subexpression_elimination_raw.v |
| rtlrewriter_fsm_small_case__example1 | example | 87 | clk | y | y | short_benchmark/fsm_small_case/example1/example1_state.v, short_benchmark/fsm_small_case/example1/example1_state_gpt4.v, short_benchmark/fsm_small_case/example1/example1_state_optimized.v ... |
| rtlrewriter_fsm_small_case__example2 | fsm_raw | 66 | clk | - | y | short_benchmark/fsm_small_case/example2/example2_state.v, short_benchmark/fsm_small_case/example2/example2_state_optimized.v |
| rtlrewriter_fsm_small_case__example3 | example | 66 | clk | y | y | short_benchmark/fsm_small_case/example3/example3_state.v, short_benchmark/fsm_small_case/example3/example3_state_gpt4.v, short_benchmark/fsm_small_case/example3/example3_state_optimized.v ... |
| rtlrewriter_fsm_small_case__example4 | fsm | 54 | clk | - | y | short_benchmark/fsm_small_case/example4/example4_state.v, short_benchmark/fsm_small_case/example4/example4_state_optimized.v |
| rtlrewriter_fsm_small_case__example5 | fsm | 54 | clk | - | y | short_benchmark/fsm_small_case/example5/example5_state.v, short_benchmark/fsm_small_case/example5/example5_state_optimized.v |
| rtlrewriter_memory__memory_banking | memory_bank | 45 | clk | - | y | short_benchmark/memory/memory_banking/memory_banking_opt.v, short_benchmark/memory/memory_banking/memory_banking_raw.v |
| rtlrewriter_memory__memory_compression | memory_compression_opt | 44 | clk | - | y | short_benchmark/memory/memory_compression/memory_compression_opt.v, short_benchmark/memory/memory_compression/memory_compression_raw.v |
| rtlrewriter_memory__memory_folding | memory_folding_opt | 79 | clk | - | y | short_benchmark/memory/memory_folding/memory_folding_opt.v, short_benchmark/memory/memory_folding/memory_folding_raw.v |
| rtlrewriter_memory__memory_folding2 | memory_folding_opt | 108 | clk | - | y | short_benchmark/memory/memory_folding2/memory_folding_opt_1.v, short_benchmark/memory/memory_folding2/memory_folding_raw_1.v |
| rtlrewriter_memory__memory_sharing | shared_memory_raw | 52 | clk | - | y | short_benchmark/memory/memory_sharing/memory_sharing_opt.v, short_benchmark/memory/memory_sharing/memory_sharing_raw.v |
| rtlrewriter_mux__mux_dead_code | example | 106 | - | - | y | short_benchmark/mux/mux_dead_code/mux_dead_code.v, short_benchmark/mux/mux_dead_code/mux_dead_code_claude3.v, short_benchmark/mux/mux_dead_code/mux_dead_code_gpt4.v ... |
| rtlrewriter_mux__mux_type1 | mux_tree | 35 | - | - | y | short_benchmark/mux/mux_type1/mux_type1_gpt4.v, short_benchmark/mux/mux_type1/mux_type1_ours.v, short_benchmark/mux/mux_type1/mux_type1_redundancy.v ... |
| rtlrewriter_mux__mux_type2 | mux_tree | 31 | - | - | y | short_benchmark/mux/mux_type2/mux_type2_redundancy.v, short_benchmark/mux/mux_type2/mux_type2_redundancy_improve.v, short_benchmark/mux/mux_type2/mux_type2_redundancy_optimized.v |
| rtlrewriter_mux__mux_type3 | mux_tree | 19 | - | - | y | short_benchmark/mux/mux_type3/mux_type3_claude3.v, short_benchmark/mux/mux_type3/mux_type3_gp4.v, short_benchmark/mux/mux_type3/mux_type3_ours.v ... |
| rtlrewriter_mux__mux_type4 | mux_tree | 26 | - | - | y | short_benchmark/mux/mux_type4/mux_type4_claude3.v, short_benchmark/mux/mux_type4/mux_type4_gpt4.v, short_benchmark/mux/mux_type4/mux_type4_redundancy.v ... |
| rtlrewriter_mux__mux_type5 | mux_tree | 27 | - | - | y | short_benchmark/mux/mux_type5/mux_type5_gpt4.v, short_benchmark/mux/mux_type5/mux_type5_ours.v, short_benchmark/mux/mux_type5/mux_type5_redundancy.v ... |
| rtlrewriter_long_cnn__RFselector | RFselector_raw | 67 | - | - | y | long_benchmark/cnn/RFselector_raw.v, long_benchmark/cnn/RFselector.v |
| rtlrewriter_long_cnn__convLayerSingle | convLayerSingle | 790 | clk | - | y | long_benchmark/cnn/convLayerSingle_raw.v, long_benchmark/cnn/RFselector.v, long_benchmark/cnn/convUnit.v ... |
| rtlrewriter_long_cnn__convUnit | convUnit_raw | 600 | clk | - | y | long_benchmark/cnn/convUnit_raw.v, long_benchmark/cnn/processingElement.v, long_benchmark/cnn/processingElementRaw.v ... |
| rtlrewriter_long_cnn__floatAdd | floatAdd_raw | 103 | - | - | y | long_benchmark/cnn/floatAdd_raw.v, long_benchmark/cnn/floatAdd.v |
| rtlrewriter_long_cnn__floatMult | floatMult_raw | 68 | - | - | y | long_benchmark/cnn/floatMult_raw.v, long_benchmark/cnn/floatMult.v |
| rtlrewriter_long_cnn__processingElement | processingElement_raw | 546 | clk | - | y | long_benchmark/cnn/processingElementRaw.v, long_benchmark/cnn/floatAdd_raw.v, long_benchmark/cnn/floatMult_raw.v ... |
| rtlrewriter_long_cpu__ALU | ALU_raw | 92 | - | - | y | long_benchmark/cpu/ALURaw.v, long_benchmark/cpu/ALU.v |
| rtlrewriter_long_cpu__BranchAndJumpHazard | BranchAndJumpHazard_raw | 32 | - | - | y | long_benchmark/cpu/BranchAndJumpHazardRaw.v, long_benchmark/cpu/BranchAndJumpHazard.v |
| rtlrewriter_long_cpu__DataHazard | DataHazard_raw | 54 | - | - | y | long_benchmark/cpu/DataHazardRaw.v, long_benchmark/cpu/DataHazard.v |
| rtlrewriter_long_cpu__DataMem | DataMem_raw | 66 | clk | - | y | long_benchmark/cpu/DataMemRaw.v, long_benchmark/cpu/DataMem.v |
| rtlrewriter_long_cpu__ImmExtend | ImmExtend_raw | 12 | - | - | y | long_benchmark/cpu/ImmExtendRaw.v, long_benchmark/cpu/ImmExtend.v |
| rtlrewriter_long_cpu__InstMem | InstMem_raw | 209 | clk | - | y | long_benchmark/cpu/InstMemRaw.v, long_benchmark/cpu/InstMem.v |
| rtlrewriter_long_cpu__PC | PC_raw | 51 | clk | - | y | long_benchmark/cpu/PCRaw.v, long_benchmark/cpu/PC.v |
| rtlrewriter_long_cpu__PipelineCPU | PipelineCPU_raw | 1418 | - | - | y | long_benchmark/cpu/PipelineCPURaw.v, long_benchmark/cpu/ALURaw.v, long_benchmark/cpu/BranchAndJumpHazardRaw.v ... |
| rtlrewriter_long_cpu__RegFile | RegFile | 51 | clk | - | y | long_benchmark/cpu/RegFileRaw.v, long_benchmark/cpu/RegFile.v |
| rtlrewriter_long_fft__Butterfly | butterfly_raw | 115 | clk | - | y | long_benchmark/fft/ButterflyRaw.v, long_benchmark/fft/Butterfly.v |
| rtlrewriter_long_huffman__Decoder | decoder_raw | 1276 | clk | - | y | long_benchmark/huffman/DecoderRaw.v, long_benchmark/huffman/HuffmanDecoder.v, long_benchmark/huffman/HuffmanDecoderRaw.v ... |
| rtlrewriter_long_huffman__HuffmanDecoder | HuffmanDecoderRaw | 584 | clk | - | y | long_benchmark/huffman/HuffmanDecoderRaw.v, long_benchmark/huffman/HuffmanDecoder.v |
