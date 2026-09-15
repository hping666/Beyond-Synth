# Phase 4 report — Exp1: ladder and map (C1)

Generated 2026-09-15 11:14 by scripts/report_phase.py (git 9b3178d4695c, cfg d845788457d4). Data: reports/data/phase4_exp1.json (scripts/phase4_exp1.py collect).

## 1. Objects

Designs (config `exp1.designs`, C1 scope: human-written RTL): cktevo_nn_engine__spikeLayer8_H7, cktevo_ethmac__eth_txethmac, cktevo_vga_enh__vga_wb_master, cktevo_mem_ctrl__mc_obct_top, cktevo_spi__spi, drrtl_datapath, drrtl_pcie, drrtl_i2c, rtlopt_ticket_machine, rtlopt_fsm_encode; floor version `phase4`. 1473 objects: roles {'reference': 94, 'llm': 22, 'b0': 1357}; equivalence verdicts {'proven': 409, 'sim_fail': 440, 'falsified': 342, 'rejected': 235, 'inconclusive': 43, 'proven_sim_only': 1, 'pending': 3}; M6 classes (rules v2) {'b': 407, 'a': 152, 'd': 475, 'c1': 399, '?': 9, 'c2': 1, 'free': 30}; E4-evaluated 380; M3 labels at E4 {'harmful': 22, 'tradeoff': 54, 'absorbed_identical': 59, 'retained': 75, '-': 55, 'absorbed': 4, 'duplicate': 128, 'noise': 41, 'nonequiv': 1035}.

## 2. Map v1: E4 retention rate (area, rule-A threshold of the design under each configuration) by class × configuration

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) | E4 median gain | E4 labels | absorption rung (E4) |
|---|---|---|---|---|---|---|---|---|---|
| a | 33 % (73) | - (0) | 14 % (73) | 14 % (73) | - (0) | 15 % (73) | 17.6 % | {'absorbed': 2, 'absorbed_identical': 40, 'harmful': 5, 'noise': 12, 'retained': 10, 'tradeoff': 4} | {'E1': 1, 'E4': 40, 'after_Es': 1} |
| b | 49 % (110) | - (0) | 42 % (110) | 40 % (110) | - (0) | 43 % (110) | 28.5 % | {'absorbed': 2, 'absorbed_identical': 16, 'harmful': 11, 'noise': 28, 'retained': 38, 'tradeoff': 15} | {'E2': 2, 'E4': 16} |
| c1 | 85 % (26) | - (0) | 92 % (26) | 88 % (26) | - (0) | 88 % (26) | 7.8 % | {'noise': 1, 'retained': 22, 'tradeoff': 3} | {} |
| c2 | 0 % (1) | - (0) | 0 % (1) | 0 % (1) | - (0) | 0 % (1) | - | {'harmful': 1} | {} |
| d | 76 % (45) | - (0) | 49 % (45) | 20 % (45) | - (0) | 73 % (45) | 4.8 % | {'absorbed_identical': 3, 'harmful': 5, 'retained': 5, 'tradeoff': 32} | {'E4': 3} |

Map shape (B0 objects): **concentrated** — E4 retention by class {'a': 0.06, 'b': 0.49, 'c1': 1.0, 'd': 0.94} (concentrated: the rates differ by ≥ 0.3 between classes with ≥ 10 evaluated objects; near-zero: every class < 10 %; diffuse otherwise).

The same map on the B0 objects alone (the C1 scope: luna rewrites of the ten human-written designs; the literature objects excluded):

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) | E4 median gain | E4 labels |
|---|---|---|---|---|---|---|---|---|
| a | 6 % (33) | - (0) | 6 % (33) | 6 % (33) | - (0) | 6 % (33) | 5.0 % | {'absorbed': 1, 'absorbed_identical': 19, 'noise': 11, 'retained': 1, 'tradeoff': 1} |
| b | 49 % (84) | - (0) | 49 % (84) | 46 % (84) | - (0) | 49 % (84) | 41.6 % | {'absorbed': 2, 'absorbed_identical': 5, 'harmful': 6, 'noise': 27, 'retained': 34, 'tradeoff': 10} |
| c1 | 89 % (19) | - (0) | 100 % (19) | 100 % (19) | - (0) | 100 % (19) | 7.8 % | {'retained': 17, 'tradeoff': 2} |
| c2 | - (0) | - (0) | - (0) | - (0) | - (0) | - (0) | - | {} |
| d | 84 % (32) | - (0) | 59 % (32) | 19 % (32) | - (0) | 94 % (32) | 4.4 % | {'retained': 3, 'tradeoff': 29} |

All objects under the materiality thresholds (area 1 %, power 2 %, WNS 1 % of the period) instead of the rule-A floors — the sensitivity row; E1d and E2g have no measured floor, so they appear here only:

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) |
|---|---|---|---|---|---|---|
| a | 42 % (73) | 30 % (73) | 14 % (73) | 19 % (73) | 15 % (73) | 21 % (73) |
| b | 55 % (110) | 53 % (110) | 40 % (110) | 63 % (110) | 36 % (110) | 39 % (110) |
| c1 | 92 % (26) | 85 % (26) | 92 % (26) | 88 % (26) | 92 % (26) | 88 % (26) |
| c2 | 0 % (1) | 0 % (1) | 0 % (1) | 0 % (1) | 0 % (1) | 0 % (1) |
| d | 71 % (45) | 40 % (45) | 53 % (45) | 24 % (45) | 67 % (45) | 69 % (45) |

## 3. Retention curves and non-monotone cases

| class | E1 | E1d | E2 | E3 | E2g | E4 |
|---|---|---|---|---|---|---|
| a | 33 % (73) | - | 14 % (73) | 14 % (73) | - | 15 % (73) |
| b | 49 % (110) | - | 42 % (110) | 40 % (110) | - | 43 % (110) |
| c1 | 85 % (26) | - | 92 % (26) | 88 % (26) | - | 88 % (26) |
| c2 | 0 % (1) | - | 0 % (1) | 0 % (1) | - | 0 % (1) |
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

## 4. Literature settings re-evaluated (PLAN 4.7)

| suite | pairs | proven | E1 better / retained (evaluated) | E1d better / retained (evaluated) | E2 better / retained (evaluated) | E3 better / retained (evaluated) | E2g better / retained (evaluated) | E4 better / retained (evaluated) |
|---|---|---|---|---|---|---|---|---|
| rtlopt | 40 | 34 | 20 / 20 (33) | 17 / 0 (33) | 13 / 11 (33) | 13 / 11 (33) | 13 / 0 (33) | 13 / 11 (33) |
| rtlrewriter | 54 | 43 | 24 / 24 (42) | 21 / 0 (42) | 11 / 10 (42) | 10 / 9 (42) | 11 / 0 (42) | 10 / 10 (42) |

better = the optimized version's area is below D's under that rung; retained = above D's rule-A threshold there. The papers' own counts are compared in the paper text (RTL-OPT: pairs judged better by the authors' flow; RTLRewriter: pass@k of the engineers' rewrite).

## 5. Static-rule misclassification rates (PLAN 4.8)

Rule R forbids classes ['a', 'b'] (syntactic / coding rewrites) and allows ['c1', 'c2', 'd']. P(retained | forbidden by R) = 37 % (n = 183); P(absorbed | allowed by R) = 6 % (n = 72).

## 5b. Diagnoser validation data (PLAN 4.6, spec 04 B.5)

Diagnoses by label: {'absorbed': 4, 'absorbed_identical': 59, 'harmful': 22, 'noise': 41, 'retained': 75, 'tradeoff': 54}; manual sample of 40 per label (seed 1, round-robin over designs; reports/data/phase4_diagnoser_sample.json, verdicts in phase4_diagnoser_check.md). Single-flag reproduction of the 63 absorbed objects (D compiled with one flag alone vs the object's plain-compile netlist C@E1, convergence = histogram Jaccard >= 0.95, area within the E1 band, endpoints coincide): 14 reproduced by at least one flag (22 %).

| flag (configuration) | absorbed objects evaluated | converged with C@E1 | rate |
|---|---|---|---|
| designware (E1d) | 63 | 14 | 22 % |
| gate_clock (E2g) | 63 | 4 | 6 % |
| none (E1) | 63 | 26 | 41 % |
| retime (E3) | 63 | 4 | 6 % |

## 6. Retention predictor (PLAN 4.5; leave-one-design-out)

- with the class features: n = 255 (129 retained), AUROC 0.717, precision at recall ≥ 85 % 55 % (τ = 0.138, miss rate 15 %); skipped designs []; coefficients (standardised) {'g_e1': 0.47, 'g_e2': 3.62, 'fp_conv_e1': -1.66, 'dff_delta': 1.14, 'diff_ratio': 0.15, 'cls_a': -1.07, 'cls_b': -0.55, 'cls_c1': 1.96, 'cls_c2': -0.22, 'cls_d': 0.47}
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


## 10. Motivating figure (PLAN 4.9): the same rewrite along the ladder

Two Phase 4 objects chosen by the data: the largest plain-compile (E1) gain that the full-effort flow recovers on its own, and the largest gain that survives E4 (retained). Positive = better than D under that configuration (relative); t_D is the rule-A threshold of the design at E4.

| object | design | class | E4 label / rung | E1 area / wns / power | E1d area / wns / power | E2 area / wns / power | E3 area / wns / power | E2g area / wns / power | E4 area / wns / power | Y area / wns / power | O0 area / wns / power | O1 area / wns / power | O2 area / wns / power | t_D(E4) area |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| recovered: c5873c2b59da776 | rtlrewriter_memory__memory_sharing | c1 | noise / - | +40.6 % / -0.6 % / +34.6 % | +40.6 % / -0.6 % / +47.4 % | +0.0 % / +0.0 % / +0.0 % | +0.0 % / +0.0 % / -0.0 % | -0.1 % / +0.0 % / +3.0 % | -0.1 % / +0.0 % / -0.9 % | +0.0 % / +1.4 % / +0.0 % | +0.0 % / +1.4 % / +0.0 % | +0.0 % / +1.4 % / +0.0 % | +0.1 % / +0.0 % / +0.0 % | 0.28 % |
| retained: c634baa4b8fa859 | rtlopt_ticket_machine | b | retained / E4 | +58.9 % / +24.4 % / +73.8 % | +58.9 % / +24.4 % / +51.3 % | +58.4 % / +30.9 % / +34.0 % | +58.4 % / +30.9 % / +34.0 % | +58.4 % / +30.9 % / +50.1 % | +58.4 % / +30.9 % / +34.0 % | +42.8 % / +6.0 % / +41.7 % | +42.8 % / +6.0 % / +41.7 % | +42.8 % / +6.0 % / +41.7 % | +41.2 % / +2.0 % / +43.2 % | 0.28 % |

The recovered object shows the gain a plain compile reports vanishing under `compile_ultra -retime -gate_clock` (the synthesizer obtains it on its own); the retained object keeps its gain there — the complement the ladder search aims at (PROPOSAL §1).
