# Phase 4 report — Exp1: ladder and map (C1)

Generated 2026-09-15 17:25 by scripts/report_phase.py (git 19fa49cafb78, cfg f8b2ecbba79c). Data: reports/data/phase4_exp1.json (scripts/phase4_exp1.py collect).

## 1. Objects

Designs (config `exp1.designs`, C1 scope: human-written RTL): cktevo_nn_engine__spikeLayer8_H7, cktevo_ethmac__eth_txethmac, cktevo_vga_enh__vga_wb_master, cktevo_mem_ctrl__mc_obct_top, cktevo_spi__spi, drrtl_datapath, drrtl_pcie, drrtl_i2c, rtlopt_ticket_machine, rtlopt_fsm_encode; floor version `phase4`. 1473 objects: roles {'reference': 94, 'llm': 22, 'b0': 1357}; equivalence verdicts {'proven': 409, 'sim_fail': 440, 'falsified': 342, 'rejected': 235, 'inconclusive': 43, 'proven_sim_only': 1, 'pending': 3}; M6 classes (rules v2) {'a': 155, 'b': 405, 'd': 475, 'c2': 5, '?': 9, 'c1': 394, 'free': 30}; E4-evaluated 380; M3 labels at E4 {'harmful': 20, 'tradeoff': 54, 'absorbed_identical': 59, 'retained': 75, '-': 55, 'absorbed': 15, 'duplicate': 128, 'noise': 32, 'nonequiv': 1035}.

## 2. Map v1: E4 retention rate (area, rule-A threshold of the design under each configuration) by class × configuration

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) | E4 median gain | E4 labels | absorption rung (E4) |
|---|---|---|---|---|---|---|---|---|---|
| a | 33 % (75) | - (0) | 15 % (75) | 15 % (75) | - (0) | 16 % (75) | 17.6 % | {'absorbed': 7, 'absorbed_identical': 40, 'harmful': 5, 'noise': 8, 'retained': 11, 'tradeoff': 4} | {'E1': 2, 'E2': 4, 'E4': 40, 'after_Es': 1} |
| b | 50 % (109) | - (0) | 42 % (109) | 40 % (109) | - (0) | 43 % (109) | 28.5 % | {'absorbed': 8, 'absorbed_identical': 16, 'harmful': 9, 'noise': 23, 'retained': 38, 'tradeoff': 15} | {'E1': 2, 'E2': 1, 'E4': 16, 'after_Es': 5} |
| c1 | 88 % (24) | - (0) | 92 % (24) | 88 % (24) | - (0) | 88 % (24) | 10.5 % | {'noise': 1, 'retained': 20, 'tradeoff': 3} | {} |
| c2 | 0 % (2) | - (0) | 50 % (2) | 50 % (2) | - (0) | 50 % (2) | 1.9 % | {'harmful': 1, 'retained': 1} | {} |
| d | 76 % (45) | - (0) | 49 % (45) | 20 % (45) | - (0) | 73 % (45) | 4.8 % | {'absorbed_identical': 3, 'harmful': 5, 'retained': 5, 'tradeoff': 32} | {'E4': 3} |

Map shape (B0 objects): **concentrated** — E4 retention by class {'a': 0.06, 'b': 0.49, 'c1': 1.0, 'd': 0.94} (concentrated: the rates differ by ≥ 0.3 between classes with ≥ 10 evaluated objects; near-zero: every class < 10 %; diffuse otherwise).

The same map on the B0 objects alone (the C1 scope: luna rewrites of the ten human-written designs; the literature objects excluded):

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) | E4 median gain | E4 labels |
|---|---|---|---|---|---|---|---|---|
| a | 6 % (33) | - (0) | 6 % (33) | 6 % (33) | - (0) | 6 % (33) | 5.0 % | {'absorbed': 5, 'absorbed_identical': 19, 'noise': 7, 'retained': 1, 'tradeoff': 1} |
| b | 49 % (84) | - (0) | 49 % (84) | 46 % (84) | - (0) | 49 % (84) | 41.6 % | {'absorbed': 7, 'absorbed_identical': 5, 'harmful': 6, 'noise': 22, 'retained': 34, 'tradeoff': 10} |
| c1 | 89 % (19) | - (0) | 100 % (19) | 100 % (19) | - (0) | 100 % (19) | 7.8 % | {'retained': 17, 'tradeoff': 2} |
| c2 | - (0) | - (0) | - (0) | - (0) | - (0) | - (0) | - | {} |
| d | 84 % (32) | - (0) | 59 % (32) | 19 % (32) | - (0) | 94 % (32) | 4.4 % | {'retained': 3, 'tradeoff': 29} |

All objects under the materiality thresholds (area 1 %, power 2 %, WNS 1 % of the period) instead of the rule-A floors — the sensitivity row; E1d and E2g have no measured floor, so they appear here only:

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) |
|---|---|---|---|---|---|---|
| a | 43 % (75) | 31 % (75) | 15 % (75) | 20 % (75) | 16 % (75) | 21 % (75) |
| b | 55 % (109) | 53 % (109) | 40 % (109) | 63 % (109) | 37 % (109) | 39 % (109) |
| c1 | 96 % (24) | 88 % (24) | 92 % (24) | 88 % (24) | 92 % (24) | 88 % (24) |
| c2 | 0 % (2) | 0 % (2) | 50 % (2) | 50 % (2) | 50 % (2) | 50 % (2) |
| d | 71 % (45) | 40 % (45) | 53 % (45) | 24 % (45) | 67 % (45) | 69 % (45) |

## 3. Retention curves and non-monotone cases

| class | E1 | E1d | E2 | E3 | E2g | E4 |
|---|---|---|---|---|---|---|
| a | 33 % (75) | - | 15 % (75) | 15 % (75) | - | 16 % (75) |
| b | 50 % (109) | - | 42 % (109) | 40 % (109) | - | 43 % (109) |
| c1 | 88 % (24) | - | 92 % (24) | 88 % (24) | - | 88 % (24) |
| c2 | 0 % (2) | - | 50 % (2) | 50 % (2) | - | 50 % (2) |
| d | 76 % (45) | - | 49 % (45) | 20 % (45) | - | 73 % (45) |

Non-monotone objects (inside the band at a lower rung, above it at a higher one): 45 of 255 evaluated under E1–E4 (17.6 %): cf89ddd75fb3c99 -RRR, c7fceae7b2cef3e -RRR, cd12c8499b8d1ab -RRR, c5dd5be5540ec6c R--R, c31d3356c1aa4ac R--R, c329f2002ffaa79 RR-R, c5abf0a43a48dd4 -RRR, c8eb4a4b69a2dfe RR-R, ca6a75d9995d074 R--R, cbd06175747b32e R--R, cc722b602ba80f4 -RRR, cfcff4cec55f7f1 -RRR, cde5444e8ee9dcf -RRR, c097257d3463bc2 R--R, c0c021141c94ff8 R--R, c25c096cd506b86 R--R, c56fa2529a980c5 RR-R, c5def31472daffa RR-R, c5fac3ac89179d4 RR-R, cb313beed61b03b RR-R

## 4a. Benchmark hygiene: literature objects that are not equivalent to their original under the protocol (DECISIONS 2026-09-14 item 3)

25 objects ({'RTL-OPT reference': 6, 'RTLRewriter LLM sample': 8, 'RTLRewriter reference': 11}; by verdict {'falsified': 2, 'inconclusive': 3, 'rejected': 9, 'sim_fail': 11}) are excluded from the re-evaluation counts and reported here with the probable cause. Protocol: V1 ports -> V2 lock-step simulation from the all-zero initial state (`+vcs+initreg+0`, G2.2) -> VC Formal SEQ with the same start state; the RTL-OPT authors verified their pairs with combinational equivalence, which ignores the start state and the cycle-level timing.

| object | role | verdict | first mismatch (cycle, signals) | registers without reset (D / object) | probable cause |
|---|---|---|---|---|---|
| rtlopt_divider_16bit | RTL-OPT reference | V2 mismatch at cycle 260 (result) | 260 (result) | 0 / 0 | genuine functional difference (combinational pair, no state) |
| rtlopt_divider_32bit | RTL-OPT reference | SEQ falsified (counterexample saved) | - | 0 / 0 | genuine functional difference (bounded proof found a counterexample) |
| rtlopt_divider_4bit | RTL-OPT reference | V2 mismatch at cycle 24 (result) | 24 (result) | 0 / 0 | genuine functional difference (combinational pair, no state) |
| rtlopt_divider_8bit | RTL-OPT reference | V2 mismatch at cycle 32 (result) | 32 (result) | 0 / 0 | genuine functional difference (combinational pair, no state) |
| rtlopt_mac | RTL-OPT reference | V2 mismatch at cycle 3 (z) | 3 (z) | 4 / 1 | all-zero initial-state assumption likely (mismatch in the first cycles; registers without reset: D 4, object 1) |
| rtlopt_mux_encode | RTL-OPT reference | V1 elaboration failure | - | 0 / 0 | the object does not elaborate in the V1 port check (Yosys parse failure; a tool boundary of the protocol, not a functional difference): candidate does not elaborate: yosys exit 1: /home/hping/Beyond-Synth/data/designs/rtlopt/mux_encode/ |
| rtlrewriter_basic__communtativity_subpexpression2 | RTLRewriter LLM sample | V2 mismatch at cycle 0 (output2) | 0 (output2) | 0 / 0 | genuine functional difference (combinational pair, no state) |
| rtlrewriter_basic__commutativity_subexpression | RTLRewriter LLM sample | V2 mismatch at cycle 0 (result1, result5) | 0 (result1, result5) | 0 / 0 | genuine functional difference (combinational pair, no state) |
| rtlrewriter_basic__distributed_ram | RTLRewriter reference | SEQ inconclusive (class cap reached) | - | 1 / 1 | undecided: the lock-step simulation passed and the bounded proof reached its cap; not proven, so not counted, reported apart (no-discard policy, C2.5) |
| rtlrewriter_basic__if_prority | RTLRewriter reference | V1 elaboration failure | - | 0 / 0 | the object does not elaborate in the V1 port check (Yosys parse failure; a tool boundary of the protocol, not a functional difference): candidate does not elaborate: yosys exit 1: /home/hping/Beyond-Synth/data/designs/rtlrewriter/basic_ |
| rtlrewriter_basic__multi_constant_multiplication | RTLRewriter reference | SEQ inconclusive (class cap reached) | - | 0 / 0 | undecided: the lock-step simulation passed and the bounded proof reached its cap; not proven, so not counted, reported apart (no-discard policy, C2.5) |
| rtlrewriter_basic__multi_constant_multiplication2 | RTLRewriter LLM sample | V2 mismatch at cycle 0 (w, y, z) | 0 (w, y, z) | 0 / 0 | genuine functional difference (combinational pair, no state) |
| rtlrewriter_basic__multi_constant_multiplication2 | RTLRewriter reference | SEQ inconclusive (class cap reached) | - | 0 / 0 | undecided: the lock-step simulation passed and the bounded proof reached its cap; not proven, so not counted, reported apart (no-discard policy, C2.5) |
| rtlrewriter_basic__multi_constant_multiplication2 | RTLRewriter LLM sample | V2 mismatch at cycle 0 (y, z) | 0 (y, z) | 0 / 0 | genuine functional difference (combinational pair, no state) |
| rtlrewriter_datapath__alu_subexpression | RTLRewriter LLM sample | V1 port mismatch | - | 0 / 0 | port mismatch: port opcode: width 4 -> 3 |
| rtlrewriter_long_cnn__convLayerSingle | RTLRewriter reference | V1 elaboration failure | - | 0 / 0 | the object does not elaborate in the V1 port check (Yosys parse failure; a tool boundary of the protocol, not a functional difference): candidate does not elaborate: yosys exit 1: signs/rtlrewriter/long_cnn__convLayerSingle/rtl/processi |
| rtlrewriter_long_cnn__convUnit | RTLRewriter reference | V1 elaboration failure | - | 0 / 0 | the object does not elaborate in the V1 port check (Yosys parse failure; a tool boundary of the protocol, not a functional difference): candidate does not elaborate: yosys exit 1: /Beyond-Synth/data/designs/rtlrewriter/long_cnn__convUni |
| rtlrewriter_long_cpu__DataHazard | RTLRewriter reference | V2 mismatch at cycle 185 (ForwardA, ForwardB) | 185 (ForwardA, ForwardB) | 0 / 0 | genuine functional difference (combinational pair, no state) |
| rtlrewriter_long_cpu__DataMem | RTLRewriter reference | SEQ falsified (counterexample saved) | - | 0 / 0 | genuine functional difference (bounded proof found a counterexample) |
| rtlrewriter_long_cpu__PC | RTLRewriter reference | V2 mismatch at cycle 0 (PC_o) | 0 (PC_o) | 0 / 0 | genuine functional difference (mismatch after the start-up cycles) |
| rtlrewriter_long_huffman__HuffmanDecoder | RTLRewriter reference | V1 port mismatch | - | 0 / 0 | port mismatch: Error-[IPC-E] Illegal port connection |
| rtlrewriter_mux__mux_type1 | RTLRewriter LLM sample | V1 elaboration failure | - | 0 / 0 | the object does not elaborate in the V1 port check (Yosys parse failure; a tool boundary of the protocol, not a functional difference): candidate does not elaborate: ERROR: Module `mux_tree' not found! |
| rtlrewriter_mux__mux_type1 | RTLRewriter LLM sample | V1 port mismatch | - | 0 / 0 | port mismatch: port sel missing in candidate; extra port s1 in candidate; extra port s2 in candidate; extra port d in candidate |
| rtlrewriter_mux__mux_type1 | RTLRewriter reference | V1 elaboration failure | - | 0 / 0 | the object does not elaborate in the V1 port check (Yosys parse failure; a tool boundary of the protocol, not a functional difference): candidate does not elaborate: yosys exit 1: /home/hping/Beyond-Synth/data/designs/rtlrewriter/mux__m |
| rtlrewriter_mux__mux_type5 | RTLRewriter LLM sample | V2 mismatch at cycle 3 (y) | 3 (y) | 0 / 0 | genuine functional difference (combinational pair, no state) |

**Objects whose synthesis evaluation failed**: 31 proven objects are rejected by the synthesizer under some configuration although VCS / VC Formal accepted them (a fault of the object's RTL, recorded as `evaluation failed` under rule 8 and never repaired by the operator). They stay in the object counts and are absent from the map cells of the configurations concerned.

| design | role | objects | configurations | category |
|---|---|---|---|---|
| cktevo_ethmac__eth_txethmac | B0 candidate | 1 | E1, E1d, E2, E2g, E3, E4 | DC: blocking and nonblocking assignments to one variable (VER-134) |
| cktevo_ethmac__eth_txethmac | B0 candidate | 1 | E1, E1d, E2, E2g, E3, E4 | DC: net defined twice (VER-262) |
| cktevo_mem_ctrl__mc_obct_top | B0 candidate | 1 | Y | Yosys: behavioural construct left in the netlist (no library cell for it) |
| cktevo_spi__spi | B0 candidate | 1 | E1, E1d, E2, E2g, E3, E4 | DC syntax error (VER-294) |
| cktevo_vga_enh__vga_wb_master | B0 candidate | 1 | E1, E1d, E2, E2g, E3, E4 | DC: net driven by more than one source (ELAB-366) |
| drrtl_i2c | B0 candidate | 24 | E1, E1d, E2, E2g, E3, E4 | DC syntax error (VER-294) |
| rtlopt_mux_dead | RTL-OPT reference | 1 | E1, E1d, E2, E2g, E3, E4 | DC link: port width mismatch (LINK-3) |
| rtlrewriter_mux__mux_type2 | RTLRewriter reference | 1 | E1, E1d, E2, E2g, E3, E4 | DC link: port width mismatch (LINK-3) |

## 4c. Duplicate answers by design and by generation (G5 decisions item 4 (d))

128 of the 1474 Phase 4 answers repeat the RTL text of an earlier answer of the same run (label `duplicate`, no evaluation; by arm {'B0': 126, 'literature': 2}); 18 runs have at least one, at most 25 in a run. Generation gap to the repeated answer: 0: 2, 1: 1, unknown: 125. Identical rewrites produced by different runs of the same design (same content hash, not counted as duplicates within a run): 1 groups over 2 run memberships (cktevo_nn_engine__spikeLayer8_H7 1).

| design | answers | duplicates | share |
|---|---|---|---|
| cktevo_ethmac__eth_txethmac | 197 | 12 | 6 % |
| cktevo_mem_ctrl__mc_obct_top | 199 | 23 | 12 % |
| cktevo_spi__spi | 50 | 11 | 22 % |
| cktevo_vga_enh__vga_wb_master | 150 | 9 | 6 % |
| drrtl_i2c | 100 | 22 | 22 % |
| rtlopt_fsm_encode | 51 | 24 | 47 % |
| rtlopt_ticket_machine | 51 | 25 | 49 % |
| rtlrewriter_basic__communtativity_subpexpression2 | 4 | 1 | 25 % |
| rtlrewriter_basic__commutativity_subexpression | 4 | 1 | 25 % |

| generation | answers | duplicates | share |
|---|---|---|---|
| 0 | 116 | 2 | 2 % |
| 1 | 139 | 6 | 4 % |
| 10 | 138 | 17 | 12 % |
| 2 | 138 | 11 | 8 % |
| 3 | 131 | 14 | 11 % |
| 4 | 135 | 11 | 8 % |
| 5 | 137 | 11 | 8 % |
| 6 | 135 | 14 | 10 % |
| 7 | 136 | 15 | 11 % |
| 8 | 133 | 15 | 11 % |
| 9 | 136 | 12 | 9 % |

## 4d. RTL-OPT pairs under the settings of the authors' published work and released artifacts (G5 item 4 (a); decisions 2026-09-15 items 4 and 5)

Objects: the 34 proven RTL-OPT pairs (the six pairs that are not equivalent under this project's protocol, §4a, are outside every count; the mux_dead reference does not link under DC). Criterion in every column: the reference version's total cell area against the suboptimal start's (better = smaller). Three settings side by side:

| setting | where it comes from | count over the proven pairs |
|---|---|---|
| authors' released reports | data/sources/RTL-OPT/Results/RTL-OPT_DC: `compile` (not compile_ultra) at CLOCK_PERIOD 0.1 ns with set_max_delay from all inputs to all outputs, set_transform_for_retiming dont_retime, register merging / sequential area recovery / clock gating through hierarchy off, ungroup -all -flatten, DC T-2022.03-SP2, the authors' own Nangate45 typical.db (their released run_dc.tcl and command.log) | 34 better / 0 same / 0 worse of 34 (their reports, their DC) |
| `E1_authors` | the released scripts' settings reproduced on DC W-2024.09 with this project's SDC (I/O delays 20 % of the period added to their input-to-output max-delay; standard synthetic library); compile string `set_app_var compile_enable_register_merging false; set_app_var compile_sequential_area_recovery false; set_fix_multiple_port_nets -all -buffer_constants -feedthroughs [all_designs]; set_max_delay -from [all_inputs] -to [all_outputs] 0.1; set_transform_for_retiming [get_cells *] dont_retime; compile` | 25 better / 1 same / 7 worse / 1 not evaluated |
| `E2_1ns` | the paper's Table 1 setting as described (compile_ultra, 1 ns, no retime, no gate clock; DesignWare Foundation; this project's SDC) reproduced on W-2024.09; compile string `compile_ultra` | 13 better / 4 same / 16 worse / 1 not evaluated |

The paper's Table 1 reports 35 of 36 better (RTL-OPT Table 1, compile_ultra 1 ns) for the compile_ultra / 1 ns setting; the released artifacts document the plain-compile / 0.1 ns setting. The rows above state what each artifact and each reproduction shows; the remaining differences between the released scripts and this project's flow are the DC version, the I/O constraint form and the library compilation. At the knee period the same pairs under E2 and E4 are listed for reference.

| pair | phi_main (ns) | authors' released: D / ref / rel. | E1_authors: D / ref / rel. | E2_1ns: D / ref / rel. | rel. area E2 (knee) | rel. area E4 (knee) |
|---|---|---|---|---|---|---|
| rtlopt_add_sub | 2.80 | 444.2 / 357.0 / -19.6 % | 409.4 / 347.4 / -15.1 % | 142.3 / 195.0 / +37.0 % | +93.7 % | +93.7 % |
| rtlopt_adder | 4.00 | 688.4 / 639.7 / -7.1 % | 696.7 / 601.4 / -13.7 % | 532.3 / 469.5 / -11.8 % | +12.0 % | +12.0 % |
| rtlopt_adder_carry | 1.40 | 98.7 / 54.0 / -45.3 % | 92.0 / 56.7 / -38.4 % | 64.1 / 64.1 / +0.0 % | +0.0 % | +0.0 % |
| rtlopt_adder_select | 4.00 | 812.1 / 522.7 / -35.6 % | 796.4 / 562.3 / -29.4 % | 385.2 / 396.6 / +3.0 % | +6.4 % | +6.4 % |
| rtlopt_addr_calcu | 2.00 | 388.1 / 214.4 / -44.8 % | 388.4 / 214.7 / -44.7 % | 158.8 / 158.3 / -0.3 % | +4.3 % | +4.3 % |
| rtlopt_alu_64bit | 2.00 | 3028.4 / 1748.9 / -42.2 % | 2953.1 / 1752.1 / -40.7 % | 1848.2 / 1879.3 / +1.7 % | +4.0 % | +4.0 % |
| rtlopt_alu_8bit | 2.00 | 370.0 / 245.8 / -33.6 % | 376.1 / 222.4 / -40.9 % | 214.4 / 219.7 / +2.5 % | -28.2 % | -28.2 % |
| rtlopt_calculation | 4.00 | 997.5 / 761.8 / -23.6 % | 1017.7 / 787.1 / -22.7 % | 1161.9 / 895.9 / -22.9 % | -16.9 % | -17.6 % |
| rtlopt_comparator | 1.00 | 98.2 / 80.6 / -17.9 % | 77.1 / 81.1 / +5.2 % | 41.8 / 56.4 / +35.0 % | +35.0 % | +35.0 % |
| rtlopt_comparator_16bit | 1.00 | 244.5 / 169.2 / -30.8 % | 205.6 / 152.2 / -26.0 % | 88.3 / 123.7 / +40.1 % | +40.1 % | +40.1 % |
| rtlopt_comparator_2bit | 0.35 | 14.4 / 13.0 / -9.3 % | 13.3 / 10.4 / -22.0 % | 9.6 / 8.8 / -8.3 % | -8.3 % | -8.3 % |
| rtlopt_comparator_4bit | 0.50 | 25.8 / 23.1 / -10.3 % | 26.3 / 22.6 / -14.1 % | 21.3 / 18.4 / -13.8 % | -10.0 % | -10.0 % |
| rtlopt_comparator_8bit | 0.70 | 71.3 / 67.3 / -5.6 % | 63.8 / 58.8 / -7.9 % | 44.4 / 41.2 / -7.2 % | -7.2 % | -7.2 % |
| rtlopt_decoder_6bit | 0.35 | 208.0 / 106.7 / -48.7 % | 169.2 / 88.0 / -48.0 % | 71.6 / 76.6 / +7.1 % | +8.6 % | +8.6 % |
| rtlopt_decoder_8bit | 0.50 | 856.0 / 373.2 / -56.4 % | 712.1 / 310.4 / -56.4 % | 246.8 / 257.2 / +4.2 % | +12.8 % | +12.8 % |
| rtlopt_fsm | 1.00 | 192.9 / 129.8 / -32.7 % | 186.2 / 140.4 / -24.6 % | 128.7 / 92.0 / -28.5 % | -28.5 % | -28.5 % |
| rtlopt_fsm_encode | 1.40 | 488.9 / 426.7 / -12.7 % | 528.8 / 449.3 / -15.0 % | 396.9 / 300.6 / -24.3 % | -10.5 % | -13.5 % |
| rtlopt_gray | 0.50 | 109.1 / 94.7 / -13.2 % | 106.4 / 104.8 / -1.5 % | 68.6 / 69.2 / +0.8 % | +0.8 % | +0.8 % |
| rtlopt_mul | 2.00 | 453.0 / 426.4 / -5.9 % | 461.2 / 469.5 / +1.8 % | 333.0 / 345.5 / +3.8 % | +0.0 % | +0.0 % |
| rtlopt_mul_const | 1.00 | 122.9 / 114.6 / -6.7 % | 98.4 / 81.9 / -16.8 % | 42.0 / 42.0 / +0.0 % | +0.0 % | +0.0 % |
| rtlopt_mul_subexpression | 2.80 | 623.2 / 603.8 / -3.1 % | 605.9 / 701.2 / +15.7 % | 370.3 / 387.6 / +4.7 % | +0.0 % | +0.0 % |
| rtlopt_mult_if | 0.50 | 16.0 / 14.9 / -6.7 % | 14.4 / 18.6 / +29.6 % | 10.9 / 10.1 / -7.3 % | -7.3 % | -7.3 % |
| rtlopt_mux_4to1_16bit | 0.50 | 77.4 / 73.7 / -4.8 % | 64.4 / 64.4 / +0.0 % | 60.6 / 60.6 / +0.0 % | +0.0 % | +0.0 % |
| rtlopt_mux_4to1_64bit | 0.50 | 263.9 / 260.7 / -1.2 % | 261.7 / 258.6 / -1.2 % | 234.1 / 234.1 / +0.0 % | -0.4 % | -0.4 % |
| rtlopt_mux_dead | 0.35 | 38.3 / 31.9 / -16.7 % | 31.9 / - / - | 21.8 / - / - | - | - |
| rtlopt_mux_large | 0.70 | 273.4 / 176.6 / -35.4 % | 90.7 / 102.1 / +12.6 % | 96.8 / 97.6 / +0.8 % | +1.1 % | +1.1 % |
| rtlopt_register | 1.00 | 9780.0 / 9582.9 / -2.0 % | 10241.3 / 9726.6 / -5.0 % | 8986.8 / 9085.5 / +1.1 % | +1.1 % | +0.8 % |
| rtlopt_saturating_add | 1.00 | 176.6 / 141.0 / -20.2 % | 162.5 / 134.6 / -17.2 % | 68.9 / 67.6 / -1.9 % | -1.9 % | -1.9 % |
| rtlopt_selector | 0.35 | 56.4 / 49.7 / -11.8 % | 57.7 / 45.5 / -21.2 % | 38.8 / 37.5 / -3.4 % | -3.4 % | -3.4 % |
| rtlopt_sub_16bit | 2.80 | 263.1 / 223.2 / -15.2 % | 199.0 / 196.8 / -1.1 % | 128.7 / 117.3 / -8.9 % | -10.7 % | -10.7 % |
| rtlopt_sub_32bit | 1.40 | 502.2 / 452.2 / -10.0 % | 497.2 / 379.3 / -23.7 % | 267.3 / 268.9 / +0.6 % | +1.3 % | +1.3 % |
| rtlopt_sub_4bit | 0.70 | 36.7 / 29.8 / -18.8 % | 27.9 / 29.8 / +6.7 % | 17.8 / 18.4 / +3.0 % | +43.3 % | +43.3 % |
| rtlopt_sub_8bit | 1.40 | 122.6 / 112.0 / -8.7 % | 88.6 / 92.3 / +4.2 % | 45.8 / 70.8 / +54.6 % | +13.0 % | +13.0 % |
| rtlopt_ticket_machine | 0.50 | 74.5 / 51.3 / -31.1 % | 88.0 / 54.3 / -38.4 % | 58.5 / 32.5 / -44.5 % | -44.3 % | -44.3 % |

The four RTL-OPT divider references of §4a were inspected by hand (G5 item 4 (c)): the pairs differ only on division by zero with the dividend's MSB set (non-restoring vs restoring algorithm) and agree for every non-zero divisor; analysis, traces and the confirming directed simulation in reports/data/phase4_divider_counterexamples.md.

## 4. Literature settings re-evaluated (PLAN 4.7)

| suite | pairs | proven | E1 better / retained (evaluated) | E1d better / retained (evaluated) | E2 better / retained (evaluated) | E3 better / retained (evaluated) | E2g better / retained (evaluated) | E4 better / retained (evaluated) |
|---|---|---|---|---|---|---|---|---|
| rtlopt | 40 | 34 | 20 / 20 (33) | 17 / 0 (33) | 13 / 11 (33) | 13 / 11 (33) | 13 / 0 (33) | 13 / 11 (33) |
| rtlrewriter | 54 | 43 | 24 / 24 (42) | 21 / 0 (42) | 11 / 10 (42) | 10 / 9 (42) | 11 / 0 (42) | 10 / 10 (42) |

better = the optimized version's area is below D's under that rung; retained = above D's rule-A threshold there. The papers' own counts are compared in the paper text (RTL-OPT: pairs judged better by the authors' flow; RTLRewriter: pass@k of the engineers' rewrite).

## 5. Static-rule misclassification rates (PLAN 4.8)

Rule R forbids classes ['a', 'b'] (syntactic / coding rewrites) and allows ['c1', 'c2', 'd']. P(retained | forbidden by R) = 37 % (n = 184); P(absorbed | allowed by R) = 6 % (n = 71).

## 5b. Diagnoser validation data (PLAN 4.6, spec 04 B.5)

Diagnoses by label: {'absorbed': 15, 'absorbed_identical': 59, 'harmful': 20, 'noise': 32, 'retained': 75, 'tradeoff': 54}; manual sample of 40 per label (seed 1, round-robin over designs; reports/data/phase4_diagnoser_sample.json, verdicts in phase4_diagnoser_check.md). Single-flag reproduction of the 74 absorbed objects (D compiled with one flag alone vs the object's plain-compile netlist C@E1, convergence = histogram Jaccard >= 0.95, area within the E1 band, endpoints coincide): 14 reproduced by at least one flag (19 %).

| flag (configuration) | absorbed objects evaluated | converged with C@E1 | rate |
|---|---|---|---|
| designware (E1d) | 74 | 14 | 19 % |
| gate_clock (E2g) | 74 | 4 | 5 % |
| none (E1) | 74 | 28 | 38 % |
| retime (E3) | 74 | 4 | 5 % |

## 6. Retention predictor (PLAN 4.5; leave-one-design-out)

- with the class features: n = 255 (129 retained), AUROC 0.710, precision at recall ≥ 85 % 54 % (τ = 0.125, miss rate 15 %); skipped designs []; coefficients (standardised) {'g_e1': 0.47, 'g_e2': 3.74, 'fp_conv_e1': -1.65, 'dff_delta': 1.13, 'diff_ratio': 0.15, 'cls_a': -1.07, 'cls_b': -0.53, 'cls_c1': 1.89, 'cls_c2': 0.14, 'cls_d': 0.49}
- class-blind control: n = 255 (129 retained), AUROC 0.733, precision at recall ≥ 85 % 55 % (τ = 0.263, miss rate 15 %); skipped designs []; coefficients (standardised) {'g_e1': 0.65, 'g_e2': 5.03, 'fp_conv_e1': -1.66, 'dff_delta': 0.21, 'diff_ratio': -0.06}

## 7. σ_D comparison (E4 floors of the Exp1 designs vs the calibration designs)

| design | area t_D | area σ | power t_D | WNS t_D | floor class |
|---|---|---|---|---|---|
| cktevo_nn_engine__spikeLayer8_H7 | 10.41 % | 0.26 % | 21.58 % | 0.06 % | spread |
| cktevo_ethmac__eth_txethmac | 11.63 % | 0.00 % | 13.13 % | 3.16 % | spread |
| cktevo_vga_enh__vga_wb_master | 4.43 % | 0.00 % | 5.84 % | 0.61 % | spread |
| cktevo_mem_ctrl__mc_obct_top | 0.28 % | 0.00 % | 2.22 % | 0.03 % | quiet |
| cktevo_spi__spi | 15.18 % | 0.00 % | 23.57 % | 2.04 % | spread |
| drrtl_datapath | 0.28 % | 0.00 % | 2.22 % | 0.71 % | spread |
| drrtl_pcie | 0.28 % | 0.00 % | 2.77 % | 0.03 % | spread |
| drrtl_i2c | 0.28 % | 0.00 % | - | 0.03 % | quiet |
| rtlopt_ticket_machine | 0.28 % | 0.00 % | 2.22 % | 0.03 % | quiet |
| rtlopt_fsm_encode | 0.28 % | 0.00 % | 2.22 % | 0.03 % | quiet |
| rtllm_adder_16bit | 0.28 % | 0.00 % | 2.22 % | 0.03 % | quiet |
| rtllm_traffic_light | 0.28 % | 0.00 % | 2.22 % | 0.03 % | quiet |
| rtllm_LIFObuffer | 0.28 % | 0.00 % | 2.22 % | 0.03 % | quiet |
| rtllm_serial2parallel | 0.28 % | 0.00 % | - | 0.03 % | quiet |
| rtllm_multi_pipe_8bit | 0.28 % | 0.00 % | 2.22 % | 0.03 % | quiet |

## 8. Out-of-scope contrast layer: the Phase 3 calibration candidates (RTLLM dev designs, C1 scope decision)

666 E4-diagnosed candidates of 5 RTLLM designs (run-time M3 verdicts under the Phase 3 floors; classes rules v2); map shape **concentrated** ({'a': 0.59, 'b': 0.66, 'c1': 0.9, 'd': 0.19}); rule-R misclassification: P(retained | forbidden) = 86 % (n = 277), P(absorbed | allowed) = 39 % (n = 389); non-monotone 92 of 635 evaluated under E1–E4.

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) | E4 median gain | E4 labels |
|---|---|---|---|---|---|---|---|---|
| a | 67 % (90) | - (0) | 61 % (90) | 66 % (90) | - (0) | 59 % (93) | 2.9 % | {'absorbed_identical': 14, 'harmful': 3, 'retained': 42, 'tradeoff': 34} |
| b | 71 % (175) | - (0) | 74 % (175) | 58 % (175) | - (0) | 66 % (184) | 7.0 % | {'absorbed_identical': 4, 'harmful': 18, 'retained': 86, 'tradeoff': 76} |
| c1 | 90 % (156) | - (0) | 94 % (156) | 87 % (156) | - (0) | 90 % (156) | 19.3 % | {'harmful': 9, 'retained': 92, 'tradeoff': 55} |
| c2 | 100 % (3) | - (0) | 100 % (3) | 100 % (3) | - (0) | 100 % (3) | 13.0 % | {'retained': 2, 'tradeoff': 1} |
| d | 89 % (211) | - (0) | 13 % (211) | 13 % (211) | - (0) | 19 % (230) | 12.2 % | {'absorbed_identical': 152, 'harmful': 1, 'retained': 41, 'tradeoff': 36} |

The same table under the materiality thresholds (area 1 %, power 2 %, WNS 1 % of the period) instead of the rule-A floors:

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) |
|---|---|---|---|---|---|---|
| a | 64 % (90) | 67 % (90) | 52 % (90) | 53 % (90) | 50 % (90) | 51 % (93) |
| b | 73 % (175) | 73 % (175) | 67 % (175) | 53 % (175) | 61 % (175) | 58 % (184) |
| c1 | 90 % (156) | 92 % (156) | 93 % (156) | 86 % (156) | 96 % (156) | 90 % (156) |
| c2 | 100 % (3) | 100 % (3) | 100 % (3) | 100 % (3) | 100 % (3) | 100 % (3) |
| d | 89 % (211) | 89 % (211) | 13 % (211) | 12 % (211) | 13 % (211) | 19 % (230) |

Diagnosis labels at E4 per class (run-time M3 verdicts; `harmful` split by the `blocks_synthesis` sub-label = DesignWare components of D absent from the candidate):

| class | retained | trade-off | absorbed_identical | absorbed | noise | harmful (of which blocks_synthesis) | fragile |
|---|---|---|---|---|---|---|---|
| a | 42 | 34 | 14 | 0 | 0 | 3 (0) | 0 |
| b | 86 | 76 | 4 | 0 | 0 | 18 (0) | 0 |
| c1 | 92 | 55 | 0 | 0 | 0 | 9 (2) | 0 |
| c2 | 2 | 1 | 0 | 0 | 0 | 0 (0) | 0 |
| d | 41 | 36 | 152 | 0 | 0 | 1 (1) | 0 |

Inspection of the (d) row: of the 230 class-(d) candidates on RTLLM, 152 are `absorbed_identical` ({'rtllm_adder_16bit': 152, 'rtllm_multi_pipe_8bit': 0}; on rtllm_adder_16bit these are hand-written carry-lookahead / prefix / behavioural adders whose E4 netlist is identical to D's — DC's own adder synthesis reproduces them), 1 are `harmful` of which 1 carry `blocks_synthesis` (a DesignWare component of D displaced by hand-written arithmetic: the first measured instances, see the map); the low (d) retention on RTLLM is absorption of textbook-adder rewrites, not displacement of DesignWare.


## 9. Diagnoser validation (PLAN 4.6, spec 04 §B.5) — manual check of 2026-09-15

**Protocol.** (1) A stratified sample of the E4 diagnoses of the Phase 4 objects: 40 per label (all of a label when fewer), round-robin over designs, ranked by a seeded hash of the candidate id (`phase4_exp1.py diag-sample`, seed `exp1.manual_check_seed` = 1). (2) Every sampled diagnosis is re-derived from the raw DC reports without the analysis code (`phase4_exp1.py diag-verify`, `src/analysis/verify.py`): area from `area.rpt`, slack and leaf cells from `qor.rpt`, power from the `Total` line of the power reports on the same basis as the rule (SAIF with SAIF, else default with default), the critical endpoints from `timing.rpt`, the cell histogram from the instances of `netlist.v` (the database histogram comes from `refs.rpt`), and §B.2 re-implemented. Agreement = same label; the gains are compared to 1e-4. (3) The rows of every label are then read by hand (RTL of D and of the object, the E4 report figures, the LLM's own note for B0 candidates), with the deep reads listed below. (4) For `absorbed` / `absorbed_identical`, the single-flag reproduction of §B.5: D compiled with one flag alone (E1d designware, E2g gate_clock, E3 = E2r retime) against the object's plain-compile netlist (C@E1), convergence as in §B.1 with the E1 band of the design.

**Result of the independent re-derivation (final rules).** 187 sampled diagnoses (absorbed 15, absorbed_identical 40, harmful 20, noise 32, retained 40, tradeoff 40): 187 of 187 labels agree, 187 of 187 gain vectors agree (reports/data/phase4_diagnoser_verify.json).

**What the first round found (165 sampled rows of the provisional diagnoses, 161 agreed).** The four disagreements were not reading errors but two defects of the diagnoser's inputs, both fixed before the final diagnosis (DECISIONS 2026-09-15): a candidate with SAIF-based power had been compared with a D that only had default-activity power (power "gains" of +88 % and +93 % on drrtl_i2c and rtlrewriter fsm example3), and designs without a floor row (RTLRewriter) or without a power floor (a D without SAIF) had been judged against a zero band. A third weakness surfaced in the by-hand reading: the convergence test used sigma_robust, which is zero on quiet designs, so a converged but not identical netlist could never be `absorbed` there and fell to `noise`; the test now uses the rule-A band of the rung (t_D), which moved 9 objects from noise to absorbed and gave the absorption-rung column its content (absorbed at E1: 4, at E2: 5, after E_s: 6; absorbed_identical at E4: 59).

**By-hand reading (20 rows: the first three of every label plus the two objects of the motivating figure).** The label was judged against the RTL and the report figures; every one was found consistent with §B.2 and with what the rewrite does:

| object | design | class | label | what the reading showed |
|---|---|---|---|---|
| c634baa4b8fa859 | rtlopt_ticket_machine (B0) | b | retained (+58 % area, +31 % WNS, +34 % power at E4) | D is a six-state one-hot FSM (6 flip-flops); the rewrite re-encodes it in three bits with hand-derived next-state and output equations (3 flip-flops, 14 cells vs 35). DC W-2024.09 does not re-encode a one-hot FSM on its own under `compile_ultra -retime -gate_clock`; VC Formal proved the outputs equal from reset. A genuine retained (b) gain. |
| c180f326d351e0b | rtlopt_add_sub (RTL-OPT reference) | b | harmful (−94 % area, −108 % power) | the "expert-optimized" reference splits the 16-bit add/sub into two 8-bit halves with an explicit carry; under a plain compile the two are equal (84 vs 86 cells), under E4 DC turns the original `a ± b` into one shared DesignWare add/sub (34 cells, 93 µm²) while the split version stays at 105 cells (180 µm²). The literature optimisation is neutral at E1 and harmful at E4 — the paper's thesis in one object. |
| c5873c2b59da776 | rtlrewriter memory_sharing (engineers' rewrite) | c1 | absorbed at E2 (final rules; noise under the provisional ones) | at E1 the rewrite is 41 % smaller (779 vs 1296 cells, 144 vs 272 registers); at E2 D collapses to exactly the rewrite's netlist (604 cells, 1307.92 µm², 144 registers, equal to the last digit); at E4 they differ by one cell. compile_ultra's own register sharing reproduces the engineers' rewrite. |
| ce0b8fe45ba6e9a | cktevo_spi__spi (B0) | a | absorbed (after E_s) | control-state consolidation; Jaccard 0.995, area equal, power −0.6 % inside the 23.6 % band of this spread design. |
| c5962911101c22b | cktevo_vga_enh (B0) | b | absorbed at E2 | collapsed identical Wishbone cycle/strobe state; Jaccard 0.999, converged from E2 on. |
| c42ea6425e1792a | rtlrewriter commutativity (LLM sample) | a | absorbed at E1 | a re-association of subexpressions; a plain compile already gives D the same netlist (Jaccard 0.956, −1 % area inside the 2.4 % band). |
| c570a28078bee79, cc34736dc71ee1e, cf96d541739cb1d | eth_txethmac, mc_obct_top, spi (B0) | a | absorbed_identical | factored next-state expressions, shared chip-select vectors, explicit enables: the E4 netlists are D's own (equal histogram, area and cell count). |
| cef0cadecf1e2f3 | cktevo_vga_enh (B0) | b | harmful (−5.4 % area, −5.7 % power; 48 extra registers) | the rewrite adds intermediate registers; the losses exceed the 4.4 % / 5.8 % bands of this spread design. |
| c19b2002f2f2b2e | rtlopt_adder_select (RTL-OPT reference) | b | harmful (−6.4 % area, −27 % power) | a carry-select adder written by hand against D's `a + b`: DesignWare's adder is smaller under E4. |
| cc1ec9451bbe90e | eth_txethmac (B0) | b | noise | +0.04 % area inside the 11.6 % band, Jaccard 0.998 but 1 cell apart: no gain, no convergence claim. |
| c0e1f050c420219 | spi (B0) | a | noise (+3.3 % area, −4.7 % power) | inside the 15.2 % / 23.6 % bands of this spread design; the fingerprint moved (Jaccard 0.89, 6 registers fewer): correctly not credited. |
| c110e6ce5c489b5 | cktevo_vga_enh (B0) | b | noise (−2.4 % area) | LFSR FIFO pointers replaced by binary pointers, DW_cmp appears in D only; losses inside the bands. |
| ca7289feac87ff6 | mc_obct_top (B0) | b | retained (+0.7 % area, +0.6 % WNS) | propagated compile-time-disabled chip selects; small but above the quiet design's 0.28 % band. |
| cd56b41d32d7637 | drrtl_i2c (B0) | c1 | retained (+6.9 % area, +10 % power on the default basis) | five one-hot state bits re-encoded in three; 15 registers fewer; i2c has no SAIF baseline, so power is compared on the default-activity basis on both sides. |
| c107891270e0cfd | rtlopt_calculation (RTL-OPT reference) | a | retained (+17.6 % area, +23 % power) | the reference removes a subtractor (DW01_sub in D only): a real algebraic gain. |
| c0c021141c94ff8 | mc_obct_top (B0) | d | tradeoff (+4.1 % area, −2.6 % WNS, −48 % power) | four bank-state networks replaced by a shared one-hot mask: smaller but slower and far more switching (both SAIF). |
| ca433d95ad43ab9 | drrtl_i2c (B0) | b | tradeoff (−1.2 % area, +2.7 % power) | the two one-hot FSMs re-encoded as binary: larger, less power on the default basis. |
| cb5db2844363636 | rtlopt_adder (RTL-OPT reference) | a | tradeoff (−12 % area, +19 % WNS) | the hand-written adder is faster and larger than DesignWare's. |

**Single-flag reproduction (§B.5) of the 74 absorbed objects.** 14 are reproduced by one flag alone (designware 14, gate_clock 4, retime 4; some by several); 28 are already converged with D under a plain compile (the rewrite changes nothing the tool sees); the remaining 32 converge only under `compile_ultra` as a whole, not under a single flag. The negative cases of §B.5 hold in the data: renaming-style rewrites are absorbed at E1 (4 objects) and the hand-written slow multiplier of the RTLRewriter datapath set is `tradeoff` (area up, WNS and power down).

**Agreement.** 187 / 187 (100 %) between the stored labels and the independent re-derivation from the raw reports; 20 / 20 rows read by hand consistent with the labels. The residual limitation is the one stated in spec 04 §B.6: convergence is a proxy for equal quality, and the 32 absorbed objects without a single-flag reproduction are attributed to `compile_ultra` as a whole.


## 10. Motivating figure (PLAN 4.9): the same rewrite along the ladder

Two Phase 4 objects chosen by the data: the largest plain-compile (E1) gain that the full-effort flow recovers on its own, and the largest gain that survives E4 (retained). Positive = better than D under that configuration (relative); t_D is the rule-A threshold of the design at E4.

| object | design | class | E4 label / rung | E1 area / wns / power | E1d area / wns / power | E2 area / wns / power | E3 area / wns / power | E2g area / wns / power | E4 area / wns / power | Y area / wns / power | O0 area / wns / power | O1 area / wns / power | O2 area / wns / power | t_D(E4) area |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| recovered: c5873c2b59da776 | rtlrewriter_memory__memory_sharing | c1 | noise / - | +40.6 % / -0.6 % / +34.6 % | +40.6 % / -0.6 % / +47.4 % | +0.0 % / +0.0 % / +0.0 % | +0.0 % / +0.0 % / -0.0 % | -0.1 % / +0.0 % / +3.0 % | -0.1 % / +0.0 % / -0.9 % | +0.0 % / +1.4 % / +0.0 % | +0.0 % / +1.4 % / +0.0 % | +0.0 % / +1.4 % / +0.0 % | +0.1 % / +0.0 % / +0.0 % | 0.28 % |
| retained: c634baa4b8fa859 | rtlopt_ticket_machine | b | retained / E4 | +58.9 % / +24.4 % / +73.8 % | +58.9 % / +24.4 % / +51.3 % | +58.4 % / +30.9 % / +34.0 % | +58.4 % / +30.9 % / +34.0 % | +58.4 % / +30.9 % / +50.1 % | +58.4 % / +30.9 % / +34.0 % | +42.8 % / +6.0 % / +41.7 % | +42.8 % / +6.0 % / +41.7 % | +42.8 % / +6.0 % / +41.7 % | +41.2 % / +2.0 % / +43.2 % | 0.28 % |

The recovered object shows the gain a plain compile reports vanishing under `compile_ultra -retime -gate_clock` (the synthesizer obtains it on its own); the retained object keeps its gain there — the complement the ladder search aims at (PROPOSAL §1).


## 11. Conclusions (STOP G5, 2026-09-15)

**Map shape: concentrated.** On the B0 objects (luna rewrites of the ten human-written designs, C1 scope) the E4 retention rate by class is (a) 6 % of 33, (b) 49 % of 84, (c1) 100 % of 19, (d) 94 % of 32, and on all 255 diagnosed objects (B0 plus the literature pairs) 15 % / 43 % / 88 % / 73 %. The evidence for "concentrated": the rates differ by far more than the 0.3 criterion between classes with at least 10 objects, and the shape survives the sensitivity row (materiality thresholds instead of the rule-A floors: 21 % / 39 % / 88 % / 69 %) and the two floor-class populations (five spread designs with bands of 4–15 % and four quiet ones at 0.28 %). Two nuances belong in the paper. First, the rate is an area criterion; by the five-way label the (d) objects are mostly `tradeoff` (29 of 32 on B0: area down, WNS or power up — the shared one-hot masks and re-organised datapaths of mc_obct_top), so the class that "retains" most is the class that pays for it elsewhere, while (c1) (register re-encoding, 22 retained of 26 overall) and the state-encoding half of (b) retain cleanly. Second, (a) is absorbed almost entirely: of 73 (a) objects 40 synthesise to D's own E4 netlist and 7 more converge with it, i.e. combinational rewriting is what the synthesizer does itself.

**Absorption is compile_ultra as a whole, rarely one flag.** Of the 74 absorbed objects, 28 are already indistinguishable from D under a plain compile, 14 are reproduced by a single flag (14 by the DesignWare mapping, 4 by clock gating, 4 by retiming, some by several) and 32 converge only under the full-effort flow. Retention is not monotone along the ladder: 45 of 255 objects (17.6 %) are inside the band at a lower rung and above it at a higher one (mostly `-RRR` and `R--R` patterns), which is why the ladder is measured at every rung rather than assumed to dominate from E4 downwards.

**The static rule R is wrong in both directions.** Forbidding "syntactic / coding" rewrites (classes (a) and (b)) would discard 37 % retained objects (n = 183), and allowing only architectural ones ((c1), (c2), (d)) would still let 6 % absorbed objects through (n = 72). The retained (b) objects are state re-encodings (one-hot to binary FSMs on ticket_machine, i2c, fsm_encode) that DC W-2024.09 does not perform under `compile_ultra -retime -gate_clock`.

**Predictor.** A leave-one-design-out logistic model on the cheap features (E1 and E2 gains, E1 convergence, flip-flop delta, diff ratio) reaches AUROC 0.717 with the class features and 0.733 without them (n = 255, 129 retained; precision 55 % at 85 % recall for both). The class adds nothing beyond the E1/E2 gains — the E2 gain alone carries the model — so the screening decision of G3 stands as it was: E2-level evidence predicts retention moderately, not enough to replace E4.

**Literature settings re-evaluated.** Of the 34 proven RTL-OPT pairs, 20 optimised versions are smaller than the original under a plain compile and every one of these retains at E1, but only 13 are smaller under E4 and 11 retain; the RTL-OPT `add_sub` reference is the emblematic case (equal to the original at E1, 94 % larger at E4 because DC turns the original `a ± b` into one shared DesignWare unit and cannot do so on the split version). Of the 43 proven RTLRewriter pairs, 24 are smaller at E1 and 10 at E4 (10 retained); the `memory_sharing` rewrite that is 41 % smaller at E1 is reproduced to the last cell by `compile_ultra` at E2. Six RTL-OPT references, eleven RTLRewriter references and eight of its LLM samples are not equivalent to their original under the protocol (V1 ports, lock-step simulation from the all-zero state, SEQ) and are reported apart (§4a): the four RTL-OPT dividers differ functionally, `mac` only under the initial-state assumption, and several RTLRewriter references do not elaborate or change the ports.

**Generation and hygiene (the B0 correctness finding).** 28 luna runs (K = 10 × N = 5, 1 400 calls, 4.01 USD) produced 1 357 candidates of which 320 (24 %) are proven equivalent — 429 lock-step mismatches, 340 SEQ counterexamples, 226 rejected at V1 (do not elaborate or change the interface), 40 inconclusive. The three largest designs (spikeLayer8_H7, drrtl_datapath, drrtl_pcie: 562 candidates over four seeds each) yielded no proven candidate at all, while the small FSM designs reached 78–84 % (fsm_encode 42 of 50, ticket_machine 39 of 50). A further 28 proven B0 candidates and two literature references are rejected by DC (25 `!|` reductions, VER-294; a double net declaration; blocking and nonblocking assignments to one variable; a multiply-driven net; two port-width mismatches at link) and stay `evaluation failed` (rule 8). The LLM's correctness on multi-module human-written RTL, not the synthesizer, is the first limit of the setting; Phase 5 keeps the ten designs but the projection of proofs per retained candidate must use these rates.

**Cost.** Search: 63.8 VC Formal hours and 5.7 DC hours at search time (Yosys fitness); ladder and diagnosis: 45.3 DC hours for 380 objects under E1–E4 plus the supplementary configurations; hidden registrations submitted for every E4-evaluated object (reported after Phase 5, rule 3).

**Validation of the instruments.** The M6 rules v2 (validated before Phase 4 on 60 candidates) and the M3 diagnoser (this phase: 187 of 187 sampled diagnoses agree with an independent re-derivation from the raw DC reports, 20 rows read by hand, §9) are fit for Phase 5. The validation itself found and fixed three input defects of the diagnoser (mixed SAIF / default power bases, a zero band for designs without a floor component, a convergence test that could never fire on quiet designs; DECISIONS 2026-09-15); Phase 3 was re-derived under the corrected rules and its conclusions stand (at most 15 substantive label changes of 906).

**Recommended paper form.** A map paper: "which rewrites survive the synthesizer" with the concentrated map as the central figure (class × rung retention with the sensitivity rows), the non-monotone ladder, the two-sided failure of the static rule, the literature re-evaluation table with the `add_sub` / `memory_sharing` pair as the motivating figure (§10), and the ladder search of Phase 5 as the method that aims at the complement ((c1), state re-encoding (b), and (d) only with a tradeoff-aware objective). The class-blind predictor result argues against a class-based prescreen and for the verdict feedback of the M arm.

**Open before Phase 5 (unchanged, DECISIONS 2026-09-14).** SEQ latency mapping (G2.1 (b)) — class (c2) has one object in this phase, so pipelining rewrites are not yet on the map; the DPV phase mapping for fixed-latency arithmetic pipelines; `vcf_seats_target` 50 in bulk mode; the B1@E4 static-complement prompt; whether the LLM review of spec 04 A.2 is applied to the Phase 4 / 5 objects.
