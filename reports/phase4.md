# Phase 4 report — Exp1: ladder and map (C1)

Generated 2026-09-15 05:58 by scripts/report_phase.py (git 275fa99e7466, cfg 0d40d129a8e7). Data: reports/data/phase4_exp1.json (scripts/phase4_exp1.py collect).

## 1. Objects

Designs (config `exp1.designs`, C1 scope: human-written RTL): cktevo_nn_engine__spikeLayer8_H7, cktevo_ethmac__eth_txethmac, cktevo_vga_enh__vga_wb_master, cktevo_mem_ctrl__mc_obct_top, cktevo_spi__spi, drrtl_datapath, drrtl_pcie, drrtl_i2c, rtlopt_ticket_machine, rtlopt_fsm_encode; floor version `phase3`. 116 objects: roles {'reference': 94, 'llm': 22}; equivalence verdicts {'proven': 78, 'sim_fail': 10, 'pending': 19, 'rejected': 7, 'proven_sim_only': 1, 'falsified': 1}; M6 classes (rules v2) {'b': 33, 'a': 49, 'd': 17, 'c1': 10, '?': 6, 'c2': 1}; E4-evaluated 0; M3 labels at E4 {'-': 116}.

## 2. Map v1: E4 retention rate (area, rule-A threshold of the design under each configuration) by class × configuration

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) | E4 median gain | E4 labels | absorption rung (E4) |
|---|---|---|---|---|---|---|---|---|---|
| a | - (0) | - (0) | - (0) | - (0) | - (0) | - (0) | - | {} | {} |
| b | - (0) | - (0) | - (0) | - (0) | - (0) | - (0) | - | {} | {} |
| c1 | - (0) | - (0) | - (0) | - (0) | - (0) | - (0) | - | {} | {} |
| c2 | - (0) | - (0) | - (0) | - (0) | - (0) | - (0) | - | {} | {} |
| d | - (0) | - (0) | - (0) | - (0) | - (0) | - (0) | - | {} | {} |

Map shape (all diagnosed objects): **undetermined** — E4 retention by class {} (concentrated: the rates differ by ≥ 0.3 between classes with ≥ 10 evaluated objects; near-zero: every class < 10 %; diffuse otherwise).

## 3. Retention curves and non-monotone cases

| class | E1 | E1d | E2 | E3 | E2g | E4 |
|---|---|---|---|---|---|---|
| a | - | - | - | - | - | - |
| b | - | - | - | - | - | - |
| c1 | - | - | - | - | - | - |
| c2 | - | - | - | - | - | - |
| d | - | - | - | - | - | - |

Non-monotone objects (inside the band at a lower rung, above it at a higher one): 0 of 0 evaluated under E1–E4 (-): 

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
| rtlopt | 40 | 31 | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) |
| rtlrewriter | 54 | 36 | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) |

better = the optimized version's area is below D's under that rung; retained = above D's rule-A threshold there. The papers' own counts are compared in the paper text (RTL-OPT: pairs judged better by the authors' flow; RTLRewriter: pass@k of the engineers' rewrite).

## 5. Static-rule misclassification rates (PLAN 4.8)

Rule R forbids classes ['a', 'b'] (syntactic / coding rewrites) and allows ['c1', 'c2', 'd']. P(retained | forbidden by R) = - (n = 0); P(absorbed | allowed by R) = - (n = 0).

## 6. Retention predictor (PLAN 4.5; leave-one-design-out)

- only 0 diagnosed objects

## 7. σ_D comparison (E4 floors of the Exp1 designs vs the calibration designs)

| design | area t_D | area σ | power t_D | WNS t_D | floor class |
|---|---|---|---|---|---|
| cktevo_nn_engine__spikeLayer8_H7 | 10.41 % | 0.26 % | 21.58 % | 0.06 % | spread |
| cktevo_ethmac__eth_txethmac | 11.63 % | 0.00 % | 13.13 % | 3.16 % | spread |
| cktevo_vga_enh__vga_wb_master | 4.43 % | 0.00 % | 5.84 % | 0.61 % | spread |
| cktevo_mem_ctrl__mc_obct_top | 0.28 % | 0.00 % | 2.22 % | 0.04 % | quiet |
| cktevo_spi__spi | 15.18 % | 0.00 % | 23.57 % | 2.04 % | spread |
| drrtl_datapath | 0.28 % | 0.00 % | 2.22 % | 0.71 % | spread |
| drrtl_pcie | 0.28 % | 0.00 % | 2.77 % | 0.04 % | spread |
| drrtl_i2c | 0.28 % | 0.00 % | 1.41 % | 0.04 % | quiet |
| rtlopt_ticket_machine | 0.28 % | 0.00 % | 2.22 % | 0.04 % | quiet |
| rtlopt_fsm_encode | 0.28 % | 0.00 % | 2.22 % | 0.04 % | quiet |
| rtllm_adder_16bit | 0.28 % | 0.00 % | 2.22 % | 0.04 % | quiet |
| rtllm_traffic_light | 0.28 % | 0.00 % | 2.22 % | 0.04 % | quiet |
| rtllm_LIFObuffer | 0.28 % | 0.00 % | 2.22 % | 0.04 % | quiet |
| rtllm_serial2parallel | 0.28 % | 0.00 % | 1.41 % | 0.04 % | quiet |
| rtllm_multi_pipe_8bit | 0.28 % | 0.00 % | 2.22 % | 0.04 % | quiet |

## 8. Out-of-scope contrast layer: the Phase 3 calibration candidates (RTLLM dev designs, C1 scope decision)

662 E4-diagnosed candidates of 5 RTLLM designs (run-time M3 verdicts under the Phase 3 floors; classes rules v2); map shape **concentrated** ({'a': 0.64, 'b': 0.62, 'c1': 0.9, 'd': 0.18}); rule-R misclassification: P(retained | forbidden) = 85 % (n = 260), P(absorbed | allowed) = 38 % (n = 402); non-monotone 10 of 91 evaluated under E1–E4.

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) | E4 median gain | E4 labels |
|---|---|---|---|---|---|---|---|---|
| a | 79 % (19) | - (0) | 68 % (19) | 86 % (14) | - (0) | 64 % (91) | 2.9 % | {'absorbed_identical': 12, 'harmful': 2, 'retained': 45, 'tradeoff': 32} |
| b | 67 % (42) | - (0) | 76 % (41) | 68 % (38) | - (0) | 62 % (169) | 6.9 % | {'absorbed_identical': 6, 'harmful': 18, 'retained': 71, 'tradeoff': 74} |
| c1 | 95 % (40) | - (0) | 92 % (39) | 83 % (42) | - (0) | 90 % (175) | 14.5 % | {'harmful': 9, 'retained': 106, 'tradeoff': 60} |
| c2 | - (0) | - (0) | - (0) | - (0) | - (0) | - (0) | - | {} |
| d | 80 % (55) | - (0) | 15 % (48) | 12 % (50) | - (0) | 18 % (227) | 12.2 % | {'absorbed_identical': 152, 'harmful': 2, 'retained': 39, 'tradeoff': 34} |

The same table under the materiality thresholds (area 1 %, power 2 %, WNS 1 % of the period) instead of the rule-A floors:

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) |
|---|---|---|---|---|---|---|
| a | 74 % (19) | - (0) | 53 % (19) | 57 % (14) | - (0) | 53 % (91) |
| b | 71 % (42) | - (0) | 68 % (41) | 61 % (38) | - (0) | 56 % (169) |
| c1 | 95 % (40) | - (0) | 90 % (39) | 83 % (42) | - (0) | 89 % (175) |
| c2 | - (0) | - (0) | - (0) | - (0) | - (0) | - (0) |
| d | 80 % (55) | - (0) | 15 % (48) | 12 % (50) | - (0) | 18 % (227) |

Diagnosis labels at E4 per class (run-time M3 verdicts; `harmful` split by the `blocks_synthesis` sub-label = DesignWare components of D absent from the candidate):

| class | retained | trade-off | absorbed_identical | absorbed | noise | harmful (of which blocks_synthesis) | fragile |
|---|---|---|---|---|---|---|---|
| a | 45 | 32 | 12 | 0 | 0 | 2 (0) | 0 |
| b | 71 | 74 | 6 | 0 | 0 | 18 (0) | 0 |
| c1 | 106 | 60 | 0 | 0 | 0 | 9 (2) | 0 |
| c2 | 0 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| d | 39 | 34 | 152 | 0 | 0 | 2 (1) | 0 |

Inspection of the (d) row: of the 227 class-(d) candidates on RTLLM, 152 are `absorbed_identical` ({'rtllm_adder_16bit': 152, 'rtllm_multi_pipe_8bit': 0}; on rtllm_adder_16bit these are hand-written carry-lookahead / prefix / behavioural adders whose E4 netlist is identical to D's — DC's own adder synthesis reproduces them), 2 are `harmful` of which 1 carry `blocks_synthesis` (a DesignWare component of D displaced by hand-written arithmetic: the first measured instances, see the map); the low (d) retention on RTLLM is absorption of textbook-adder rewrites, not displacement of DesignWare.
