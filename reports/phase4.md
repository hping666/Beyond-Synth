# Phase 4 report — Exp1: ladder and map (C1)

Generated 2026-09-14 17:54 by scripts/report_phase.py (git 22efa598eec3, cfg 5c738a28481d). Data: reports/data/phase4_exp1.json (scripts/phase4_exp1.py collect).

## 1. Objects

Designs (config `exp1.designs`, C1 scope: human-written RTL): cktevo_nn_engine__spikeLayer8_H7, cktevo_ethmac__eth_txethmac, cktevo_vga_enh__vga_wb_master, cktevo_mem_ctrl__mc_obct_top, cktevo_spi__spi, drrtl_datapath, drrtl_pcie, drrtl_i2c, rtlopt_ticket_machine, rtlopt_fsm_encode; floor version `phase3`. 116 objects: roles {'reference': 94, 'llm': 22}; equivalence verdicts {'pending': 116}; M6 classes (rules v2) {'b': 33, 'a': 49, 'd': 17, 'c1': 11, '?': 6}; E4-evaluated 0; M3 labels at E4 {'-': 116}.

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

## 4. Literature settings re-evaluated (PLAN 4.7)

| suite | pairs | proven | E1 better / retained (evaluated) | E1d better / retained (evaluated) | E2 better / retained (evaluated) | E3 better / retained (evaluated) | E2g better / retained (evaluated) | E4 better / retained (evaluated) |
|---|---|---|---|---|---|---|---|---|
| rtlopt | 40 | 0 | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) |
| rtlrewriter | 54 | 0 | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) |

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

655 E4-diagnosed candidates of 5 RTLLM designs (run-time M3 verdicts under the Phase 3 floors; classes rules v2); map shape **concentrated** ({'a': 0.65, 'b': 0.62, 'c1': 0.9, 'd': 0.18}); rule-R misclassification: P(retained | forbidden) = 86 % (n = 255), P(absorbed | allowed) = 38 % (n = 400); non-monotone 10 of 91 evaluated under E1–E4.

| class | E1 rate (n) | E1d rate (n) | E2 rate (n) | E3 rate (n) | E2g rate (n) | E4 rate (n) | E4 median gain | E4 labels |
|---|---|---|---|---|---|---|---|---|
| a | 79 % (19) | - (0) | 68 % (19) | 86 % (14) | - (0) | 65 % (88) | 2.9 % | {'absorbed_identical': 12, 'retained': 44, 'tradeoff': 32} |
| b | 67 % (42) | - (0) | 76 % (41) | 68 % (38) | - (0) | 62 % (167) | 6.9 % | {'absorbed_identical': 6, 'harmful': 18, 'retained': 70, 'tradeoff': 73} |
| c1 | 95 % (40) | - (0) | 92 % (39) | 83 % (42) | - (0) | 90 % (175) | 14.5 % | {'harmful': 9, 'retained': 106, 'tradeoff': 60} |
| c2 | - (0) | - (0) | - (0) | - (0) | - (0) | - (0) | - | {} |
| d | 80 % (55) | - (0) | 15 % (48) | 12 % (50) | - (0) | 18 % (225) | 12.2 % | {'absorbed_identical': 152, 'harmful': 2, 'retained': 38, 'tradeoff': 33} |
