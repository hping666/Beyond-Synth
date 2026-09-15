# Phase 2 report — noise floor, SEQ pilot, E4 runtime (Exp0)

Generated 2026-09-14 19:12 by scripts/report_phase.py (git 8841f31bc7a2, cfg d398386ae5cc). Hidden-configuration floors (H1 / H2a / H2b / H5, H3) live in the hidden database and appear only in the hidden report after Phase 5.

## 1. Perturbation generator (PLAN 2.1)

179 designs with a generator manifest (sets + RTLRewriter); perturbations per type {'P1_rename': 655, 'P1_text': 68, 'P2_reorder': 474, 'P3_expr': 290, 'P4_ctrl': 241}; designs where a type is not applicable {'P1_rename': 23, 'P2_reorder': 38, 'P3_expr': 93, 'P4_ctrl': 73}; designs Pyverilog cannot parse: 16 (cktevo_hsm__G16Inv2SharesDep, cktevo_hsm__G256Inv2Shares5Stages, cktevo_hsm__hsm, cktevo_nn_engine__thresholds_128x4096, cktevo_risc__btb, cktevo_risc__cpu, cktevo_risc__l2_cache_control, cktevo_risc__stall_control_unit, cktevo_sdc_ctrl__sdc_controller, drrtl_aes, drrtl_simple_spi, rtllm_adder_32bit, rtllm_multi_8bit, rtllm_parallel2serial, rtlrewriter_datapath__loop_tiling, rtlrewriter_datapath__multiplier_architecture).

SEQ gate (V1 -> V2 -> V3; only `proven` enters the floor):

| type | error | falsified | inconclusive | pending | proven | proven_rename | rejected | sim_fail | non-equivalence rate |
|---|---|---|---|---|---|---|---|---|---|
| P0_roundtrip | 1 | 2 | 2 | 0 | 145 | 0 | 11 | 1 | 8.6% of 162 |
| P1_rename | 4 | 16 | 4 | 17 | 460 | 123 | 45 | 5 | 9.8% of 674 |
| P1_text | 1 | 8 | 12 | 0 | 35 | 0 | 12 | 0 | 29.4% of 68 |
| P2_reorder | 0 | 7 | 4 | 8 | 413 | 0 | 43 | 5 | 11.5% of 480 |
| P3_expr | 0 | 8 | 7 | 10 | 227 | 0 | 44 | 4 | 18.7% of 300 |
| P4_ctrl | 1 | 6 | 2 | 5 | 182 | 0 | 61 | 10 | 28.8% of 267 |

## 2. Noise floor sigma_D (PLAN 2.3, visible configurations)

| config | metric | designs | median sigma | q75 | max |
|---|---|---|---|---|---|
| E1 | area | 147 | 0.0000 | 0.0000 | 0.0154 |
| E1 | power_saif | 144 | 0.0000 | 0.0000 | 0.0884 |
| E1 | tns | 147 | 0.0000 | 0.0000 | 52.5020 |
| E1 | wns | 147 | 0.0000 | 0.0000 | 0.0488 |
| E2 | area | 147 | 0.0000 | 0.0000 | 0.0463 |
| E2 | power_saif | 144 | 0.0000 | 0.0000 | 0.1369 |
| E2 | tns | 147 | 0.0000 | 0.0000 | 0.0174 |
| E2 | wns | 147 | 0.0000 | 0.0000 | 0.0941 |
| E3 | area | 148 | 0.0000 | 0.0000 | 0.0463 |
| E3 | power_saif | 145 | 0.0000 | 0.0000 | 0.1369 |
| E3 | tns | 148 | 0.0000 | 0.0000 | 0.0174 |
| E3 | wns | 148 | 0.0000 | 0.0000 | 0.0941 |
| E4 | area | 148 | 0.0000 | 0.0000 | 0.0463 |
| E4 | power_saif | 114 | 0.0000 | 0.0000 | 0.1369 |
| E4 | tns | 148 | 0.0000 | 0.0000 | 0.0174 |
| E4 | wns | 148 | 0.0000 | 0.0000 | 0.0941 |

Minimum reportable gain under the spec's original rule = 2.0 x sigma_D (config noise.k_sigma); per-design values in the noise_floor table and reports/data/phase2_noise_floor.json.

**Rule A** (DECISIONS 2026-09-14): t_D = max(2.0 x sigma_robust, the design's own max |delta| incl. P0, pooled q90); designs without a measured floor carry the pooled minimum (floor_source = pooled).

| config | metric | designs | pooled minimum | median t_D | q75 | max |
|---|---|---|---|---|---|---|
| E1 | area | 147 | 0.0045 | 0.0045 | 0.0045 | 0.0700 |
| E1 | power_saif | 144 | 0.0128 | 0.0128 | 0.0128 | 0.7446 |
| E1 | tns | 147 | 0.0000 | 0.0000 | 0.0000 | 153.9485 |
| E1 | wns | 147 | 0.0052 | 0.0052 | 0.0052 | 0.1153 |
| E2 | area | 147 | 0.0010 | 0.0010 | 0.0010 | 0.1625 |
| E2 | power_saif | 144 | 0.0100 | 0.0100 | 0.0117 | 3.2826 |
| E2 | tns | 147 | 0.0000 | 0.0000 | 0.0000 | 8.2259 |
| E2 | wns | 147 | 0.0002 | 0.0002 | 0.0004 | 0.1882 |
| E3 | area | 148 | 0.0019 | 0.0019 | 0.0019 | 0.2716 |
| E3 | power_saif | 145 | 0.0112 | 0.0112 | 0.0112 | 0.5830 |
| E3 | tns | 148 | 0.0000 | 0.0000 | 0.0000 | 2.1978 |
| E3 | wns | 148 | 0.0003 | 0.0003 | 0.0003 | 0.1882 |
| E4 | area | 148 | 0.0028 | 0.0028 | 0.0028 | 0.1866 |
| E4 | power_saif | 114 | 0.0222 | 0.0222 | 0.0222 | 0.6653 |
| E4 | tns | 148 | 0.0000 | 0.0000 | 0.0000 | 0.3120 |
| E4 | wns | 148 | 0.0003 | 0.0003 | 0.0003 | 0.1882 |

Floor classes per configuration (quiet / spread / offset; pooled = no measured floor, the pooled minimum applies; none = not a set design):

| config | quiet | spread | offset | pooled | none |
|---|---|---|---|---|---|
| E1 | 105 | 38 | 4 | 25 | 7 |
| E2 | 111 | 34 | 2 | 25 | 7 |
| E3 | 111 | 35 | 2 | 25 | 6 |
| E4 | 114 | 29 | 5 | 25 | 6 |

### 2a. Floor distribution on the set designs (dev + held)

| config | metric | designs with floor | sigma_robust = 0 | sigma_std = 0 | max abs delta > 1 % | > 5 % | pooled q90 (design-weighted, rule A) | pooled q90 (record-weighted, rejected) | pooled q95 | pooled q99 | pooled max | rule-A t_D median / q95 / max | designs above the minimum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | area | 103 | 86 | 65 | 22 | 3 | 0.0045 | 0.0100 | 0.0271 | 0.0594 | 0.0700 | 0.0045 / 0.0340 / 0.0700 | 26 |
| E1 | power_saif | 100 | 76 | 49 | 34 | 16 | 0.0128 | 0.0363 | 0.0653 | 0.2169 | 0.7446 | 0.0128 / 0.1640 / 0.7446 | 29 |
| E1 | tns | 103 | 95 | 88 | 15 | 14 | 0.0000 | 0.5847 | 3.4804 | 38.4399 | 153.9485 | 0.0000 / 4.9819 / 153.9485 | 16 |
| E1 | wns | 103 | 93 | 68 | 21 | 8 | 0.0052 | 0.0166 | 0.0372 | 0.0699 | 0.1153 | 0.0052 / 0.0913 / 0.1153 | 25 |
| E2 | area | 103 | 97 | 72 | 19 | 8 | 0.0010 | 0.0061 | 0.0389 | 0.0805 | 0.1625 | 0.0010 / 0.0708 / 0.1625 | 29 |
| E2 | power_saif | 100 | 80 | 55 | 30 | 15 | 0.0100 | 0.0440 | 0.0719 | 0.1926 | 3.2826 | 0.0100 / 0.1536 / 3.2826 | 30 |
| E2 | tns | 103 | 103 | 97 | 6 | 6 | 0.0000 | 0.0000 | 0.0000 | 0.5314 | 8.2259 | 0.0000 / 0.0540 / 8.2259 | 6 |
| E2 | wns | 103 | 95 | 71 | 19 | 9 | 0.0002 | 0.0050 | 0.0322 | 0.1364 | 0.1460 | 0.0002 / 0.0738 / 0.1882 | 31 |
| E3 | area | 103 | 97 | 71 | 26 | 17 | 0.0019 | 0.0202 | 0.0576 | 0.1457 | 0.2716 | 0.0019 / 0.1447 / 0.2716 | 29 |
| E3 | power_saif | 100 | 81 | 55 | 30 | 21 | 0.0112 | 0.0390 | 0.0985 | 0.2421 | 0.5830 | 0.0112 / 0.2437 / 0.5830 | 29 |
| E3 | tns | 103 | 103 | 101 | 1 | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0004 | 2.1978 | 0.0000 / 0.0000 / 2.1978 | 2 |
| E3 | wns | 103 | 95 | 71 | 20 | 7 | 0.0003 | 0.0088 | 0.0231 | 0.1364 | 0.1460 | 0.0003 / 0.0522 / 0.1882 | 32 |
| E4 | area | 103 | 98 | 76 | 18 | 10 | 0.0028 | 0.0137 | 0.0774 | 0.1866 | 0.1866 | 0.0028 / 0.1038 / 0.1866 | 22 |
| E4 | power_saif | 84 | 65 | 45 | 25 | 17 | 0.0222 | 0.0592 | 0.1213 | 0.6425 | 0.6653 | 0.0222 / 0.2411 / 0.6653 | 19 |
| E4 | tns | 103 | 103 | 100 | 3 | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3120 | 0.0000 / 0.0000 / 0.3120 | 3 |
| E4 | wns | 103 | 96 | 76 | 13 | 6 | 0.0003 | 0.0035 | 0.0524 | 0.0821 | 0.1460 | 0.0003 / 0.0521 / 0.1882 | 25 |

Rule A (adopted 2026-09-14): t_D = max(2 x sigma_robust, max |delta| over D's own proven perturbations including the re-print, the design-weighted pooled q90 of |delta| of the configuration); every design weighs equally in the pooled quantile so that the minimum floor does not depend on how many perturbations a design received (the record-weighted q90 is shown as the rejected sensitivity variant: it rose from 0.29 % to 1.43 % area when the spread / offset designs got twice their perturbations). The spec's 2 x sigma_robust stays in the table above for the sensitivity report.

### 2b. Perturbation types that change the netlist (area or cell count of D differs)

| config | P0_roundtrip | P1_rename | P1_text | P2_reorder | P3_expr | P4_ctrl |
|---|---|---|---|---|---|---|
| E1 | 7 / 98 (7 %) | 162 / 428 (38 %) | 20 / 28 (71 %) | 124 / 328 (38 %) | 46 / 205 (22 %) | 22 / 160 (14 %) |
| E2 | 3 / 98 (3 %) | 42 / 428 (10 %) | 0 / 28 (0 %) | 163 / 328 (50 %) | 32 / 205 (16 %) | 23 / 160 (14 %) |
| E3 | 3 / 98 (3 %) | 40 / 428 (9 %) | 0 / 28 (0 %) | 169 / 328 (52 %) | 30 / 205 (15 %) | 23 / 160 (14 %) |
| E4 | 3 / 98 (3 %) | 36 / 428 (8 %) | 0 / 28 (0 %) | 146 / 328 (45 %) | 26 / 205 (13 %) | 25 / 160 (16 %) |

### 2c. Monotonicity of D across the rungs (127 set designs with every rung at Φ_main)

| step | designs whose area grows | designs whose WNS drops |
|---|---|---|
| E1 -> E2 | 15 | 46 |
| E2 -> E3 | 36 | 18 |
| E3 -> E4 | 5 | 20 |
| E1 -> E4 | 10 | 43 |

WNS is compared at Φ_main (the E4 knee): once a rung meets timing, area recovery legitimately trades slack, so a WNS drop between two rungs that both meet timing is not a regression.

## 3. E4 runtime (PLAN 2.5)

E4 seconds at Phi_main (Nangate45) over 128 set designs: min 62, q25 76, median 80, q75 94, q95 185, max 693, mean 102.

Scale (config `scale`): 36 starting points x 5 arms x 3 seeds x N=5 x K=12 = 32400 candidate evaluations.
- full-E4 scale: 920 DC hours at the mean t_E4 (102 s); at 12 concurrent runs ≈ 77 h wall, at 50 seats ≈ 18 h.
- per-design budget rule k_e4_equiv = 60 x t_E4(D): median budget 1.3 DC hours per run.

Screening economics (config `screen`): E4 is 'cheap' below 120 s; 13 of 128 set designs are above that (their mean t_E4 = 278 s). Mean screening-rung seconds at Φ_main over the designs with both: E1 36 s, E2 108 s; over the non-cheap designs alone: E1 272 s, E2 309 s against t_E4 278 s (a DC screening rung at Φ_main is not cheaper than E4 where E4 is expensive).

| cascade (ES on every candidate, p promoted to E4) | all designs, DC hours | wall at 50 seats | hybrid: cheap designs straight to E4, only non-cheap designs screened |
|---|---|---|---|
| ES = E1, p = 0.10 | 411 (45 % of full-E4) | 8 h | 926 (101 %) |
| ES = E1, p = 0.25 | 547 (59 % of full-E4) | 11 h | 962 (105 %) |
| ES = E1, p = 0.50 | 775 (84 % of full-E4) | 15 h | 1022 (111 %) |
| ES = E2, p = 0.10 | 1064 (116 % of full-E4) | 21 h | 973 (106 %) |
| ES = E2, p = 0.25 | 1202 (131 % of full-E4) | 24 h | 1011 (110 %) |
| ES = E2, p = 0.50 | 1432 (156 % of full-E4) | 29 h | 1075 (117 %) |

| suite | designs | median t_E4 (s) | max t_E4 (s) |
|---|---|---|---|
| cktevo | 30 | 80 | 693 |
| drrtl | 18 | 86 | 339 |
| rtllm | 41 | 78 | 180 |
| rtlopt | 39 | 77 | 682 |

## 4. SEQ pilot (PLAN 2.4) and t_H3 / t_E4

Candidates: hand-made variants (CLAUDE.md exception 2), RTL-OPT pairs with a changed flip-flop count, and the LLM batch; every candidate ran V1 -> V2 -> V3 with random seeds [1, 2].

| requested class | n | verdicts (seed 1) | median V3 seconds |
|---|---|---|---|
| b | 43 | {'inconclusive': 1, 'proven': 41, 'rejected': 1} | 28.17 |
| c1 | 43 | {'inconclusive': 1, 'proven': 38, 'rejected': 1, 'sim_fail': 3} | 28.89 |
| c2 | 41 | {'proven': 11, 'proven_sim_only': 29, 'sim_fail': 1} | 30.97 |
| c_pair | 4 | {'falsified': 1, 'proven': 2, 'sim_fail': 1} | 30.26 |
| control_nonequiv | 1 | {'sim_fail': 1} | - |

M6 rule class vs requested class: 44 of 130 agree (LLM answers often deliver another class than instructed; the rule class is what the protocol uses).

Guardrail-3 facts for the 2 SEQ-inconclusive candidates (clocked arithmetic / offsets constant across seeds / start-done signals):

- drrtl_DSP c1_a_register_moved_to_stage0.v: arithmetic=True, offsets_constant=True, start-like=[], done-like=[]
- rtllm_multi_pipe_8bit b_0_c5a7dd97e61a549.v: arithmetic=True, offsets_constant=True, start-like=['mul_en_in', 'mul_en_out'], done-like=[]

t_H3 / t_E4 (baseline runs of the same design at Φ_main, 178 designs; hidden worker, counts and seconds only): median 0.97, quartiles 0.93–1.02, range 0.43–1.84; total 5.0 DC hours under E4 vs 4.7 under H3.

E4-vs-H3 agreement of the four-way floor conclusion (retained / trade-off / harmful / noise at 2 σ_D of each configuration) per perturbation with records under both: 402 of 496 (81.0 %). Confusion counts: E4=harmful|H3=harmful: 5, E4=harmful|H3=noise: 5, E4=harmful|H3=retained: 3, E4=harmful|H3=trade-off: 7, E4=noise|H3=harmful: 11, E4=noise|H3=noise: 387, E4=noise|H3=retained: 13, E4=noise|H3=trade-off: 19, E4=retained|H3=harmful: 4, E4=retained|H3=noise: 6, E4=retained|H3=retained: 1, E4=retained|H3=trade-off: 3, E4=trade-off|H3=harmful: 11, E4=trade-off|H3=noise: 4, E4=trade-off|H3=retained: 8, E4=trade-off|H3=trade-off: 9.

Whether the perturbation changed the netlist at all (|delta area| > 0.1 %): both unchanged 439, both changed 33 (same direction in 21), changed under E4 only 8, under H3 only 16.

## 5. Next steps

- G1: decide on the truncation if the median area floor exceeds the warning level.
- G2: SEQ fractions per class from the pilot.
- G3: screening recommendation from the E4 seconds and the cascade estimate.

## 6. Conclusions for the STOP gates (operator's reading of the data above; the decisions are the user's)

### G1 — noise floor (PLAN 2.3)

Facts (§2, §2a–2c; every number includes the round-trip P0 runs):

- Floors exist for 99 of the 128 set designs (77 %; 144 designs with the RTLRewriter calibration suite). 29 set designs have none: 13 that Pyverilog cannot parse (no perturbations generated), 14 whose perturbations exist but none is SEQ-proven (the re-print is rejected by VCS or its round trip is not proven: LSTM, arm_cpu1/2, i2c, tv80, communication, usbf_core/csr/sie_rx, MixColumns, vga_wb_slave, alu, router, …), 2 with a single proven perturbation. Behind the floors: 8 designs with 2–3 perturbations, 28 with 4–7, 63 with 8 or more.
- **The median σ_robust is 0 in every configuration and metric.** Under E4, 88 % of the perturbation records leave area and cell count of D unchanged: the re-print P0 changes the E4 result on 3 of 98 designs, a P1 rename in 5 % of its records, a P2 reorder in 32 %, P3 expression rewrites in 10 %, P4 control rewrites in 14 % (under E1, plain `compile`, renames change 29 %: the basic rung is name- and order-sensitive). With more than half of the deviations exactly 0 the MAD collapses, so the spec's threshold 2 σ_robust would be 0 for 95 of the 99 designs (E4 area): any nonzero change would count as retained. The G1 question as posed (median above 5 %) is inverted; the actual problem is a point mass at zero with a heavy tail.
- **The tail is real.** Under E4, 18 of 99 designs have a perturbation that moves area by more than 1 %, 9 by more than 5 % (maximum 18.7 %); for SAIF power 25 and 16 designs (maximum 64 %). Per design (E4 area): 72 quiet (every deviation ≤ 0.1 %), 21 spread (a minority of the perturbations shift the result: eth_txethmac 11.5 %, eth_miim 10.1 %, barrel_shifter 13.6 % from one P2 reorder), 6 offset (every non-trivial perturbation shifted together). The re-print alone moves three designs, all from the CktEvo mem_ctrl repository (mc_rf +18.7 % area and +64 % power, mc_dp +7.7 %, mc_adr_sel −0.4 %); RTL-OPT comparator_4bit (+16 %) is an offset of another kind: a 14-line design where any renaming or reordering flips DC's structural choice. Pooled over all perturbation records of the set designs under E4: q90 |δ_area| = 0.29 %, q95 = 4.7 %, q99 = 18.7 %; power q90 = 1.4 %, q95 = 10.0 %; WNS q90 = 0.07 % of the period, q95 = 1.5 %.
- Monotonicity of D across the rungs (127 designs): area grows from E2 to E3 in 34 designs (retiming duplicates registers: eth_cop 177 → 302 flip-flops, +42 % area) and from E3 to E4 in 5; from E1 to E4 in 10. WNS at Φ_main falls from E1 to E2 in 47 designs (area recovery once timing is met). The rungs are capability sets, not a monotone chain.

Decisions requested:

1. **Threshold rule.** (A) t_D = max(2 σ_robust, the largest |δ| among D's own proven perturbations including the re-print, the pooled q90 of the configuration and metric): distribution-free per design, catches the offset designs, and gives the quiet designs a small but nonzero floor (under E4: 0.29 % area, 1.4 % power, 0.07 % of the period for WNS; §2a lists every configuration). (B) the same rule with the pooled q95 as the minimum (4.7 % area, 10 % power under E4): conservative to the point that most LLM area gains (2–5 %) would vanish. (C) the spec's 2 σ_robust plus the absolute cell-count unit: unusable, zero for 96 % of the designs. Under rule A, 21 of the 99 designs get a floor above the minimum (E4 area: median t_D = 0.29 %, q95 = 10 %, max = 18.7 %), the other 78 the minimum itself. Recommendation: (A), with σ_robust and the 1/2/3 σ sensitivity still reported, and the quiet / spread / offset class of every design stored with its floor so that a retained gain on an offset design is flagged in the map.
2. **Designs without a floor** (29 set designs). Either exclude them from the search sets (held shrinks from 108 to about 80) or keep them with the pooled minimum as floor and a flag; for the Exp1 map designs a measured floor should be required. Recommendation: keep with the pooled minimum and the flag.
3. **Sample size.** 36 of the 99 floors rest on at most 7 perturbations. Generating 8 per type (the plan's number for the map designs) for the Exp1 map designs and the spread / offset designs costs about 3 DC hours plus 4 VC Formal hours. Recommendation: for the map designs only, before Phase 4.
4. **Rung attribution (Phase 3).** Because area is not monotone from E1 to E4, "absorbed at rung r" must compare the candidate with D under the same rung and never assume that a higher rung dominates a lower one (a check for spec 04).

### G2 — SEQ pilot (PLAN 2.4): done

Facts (131 candidates × 2 random seeds; §4 and reports/data/phase2_pilot.json):

- Class (b), latency-preserving restructurings: 41 of 43 SEQ-proven (95 %), 1 rejected at V1, 1 inconclusive; median V3 time 28 s.
- Class (c1), retimings at equal latency: 38 of 43 proven (88 %), 3 sim_fail (the LLM changed the function), 1 rejected, 1 inconclusive (the Dr.RTL DSP multiplier retiming, SEQ timeout at 1 530 s for both seeds); median 29 s.
- Class (c2), one extra pipeline stage: 11 proven (the model did not actually add latency) + 29 `proven_sim_only` (constant one-cycle offsets on every output over 20 000 random cycles for both seeds, SEQ falsifies without a latency mapping) + 1 sim_fail; median 31 s. Per-output offsets were identical across the two seeds for all 124 candidates with a measurable offset.
- The two RTL-OPT pairs with a changed flip-flop count that failed are not protocol failures: mac_ref changes the function (V2 mismatch from cycle 3) and saturating_add_ref keeps two never-set registers whose free initial state SEQ exploits.

Decisions requested:

1. **Class (c2) certificate.** SEQ as run (name-based state matching, no latency mapping) cannot prove a candidate that adds a pipeline stage. Options: (a) keep `proven_sim_only` as a separate, weaker evidence class (lock-step equivalence under a constant per-output offset, two seeds) and report it apart from `proven` in every table — recommended for Phase 3–4, it costs nothing and keeps the protocol honest; (b) add a SEQ latency mapping (per-output offsets from V2 fed to the SEQ setup) as an engineering task before Phase 5, so that (c2) candidates can be promoted to `proven`; (c) exclude (c2) from retained-gain claims. Recommendation: (a) now, (b) attempted on the 29 pilot candidates before Phase 5, (c) only if (b) fails.
2. **Registers without reset.** SEQ treats their initial state as free, which falsifies correct rewrites (renamed registers — handled by the `proven_rename` rule — and dead-code registers as in saturating_add). Options: assume the all-zero initial state for every register without a reset (a documented protocol assumption, applied to D and candidate alike) or keep the free initial state and accept the false falsifications. Recommendation: the all-zero assumption, recorded in spec 03, because the same assumption is what the lock-step simulation makes.
3. **Guardrail 3 / V4.** Neither SEQ-inconclusive candidate meets all three conditions for automatic phase derivation; V4 stays disabled in Phase 3 (no decision needed unless the user wants it earlier).

### G3 — E4 runtime (PLAN 2.5)

Facts (§3; t_H3 and the agreement rate from the hidden worker, §4):

- E4 at Φ_main over 128 set designs: median 79 s, mean 100 s, q95 185 s, max 693 s; about 60 s of every run is DC start-up and library loading, so E4 is "cheap" (below 120 s) for 115 of the 128 designs.
- Full-E4 Phase 5 scale (32 400 candidate evaluations): 903 DC hours = 18 h at 50 seats, 37 h at 24 concurrent runs (the setting used today), 75 h at 12. The per-design budget rule (60 × t_E4) gives a median budget of 1.3 DC hours per run.
- DC screening rungs at Φ_main are not cheaper where it matters: E1 averages 35 s over all designs but 272 s on the 13 designs whose E4 exceeds 120 s (plain `compile` at a tight period is slow on large designs; three designs even time out under E1), and E2 (104 s) costs as much as E4. A cascade that screens every candidate with E1 and promotes 25 % costs 60 % of full-E4 but pays with screening misses; the hybrid that screens only the expensive designs saves nothing (101–111 % of full-E4).
- t_H3 / t_E4 over 178 designs (baseline runs at Φ_main, both measured under the same 24-way load): median 0.97, quartiles 0.93–1.02, range 0.43–1.84; the physical-aware full-effort configuration costs the same as E4 (§4).
- E4 vs H3 on the noise-floor set (496 perturbations with records under both): they agree on whether a perturbation changes the netlist at all in 472 cases (95 %; 439 both unchanged, 33 both changed, 21 of those in the same direction), disagree in 24 (8 change under E4 only, 16 under H3 only). The four-way floor conclusion at 2 σ_D of each configuration agrees in 81 %, but that figure is dominated by the zero floors (any nonzero deviation counts as beyond the floor when σ_robust = 0), so the change agreement is the meaningful number until the threshold rule of G1 is decided.

Decisions requested:

1. **Screening.** Recommendation: screening does not enter the main method as a DC-rung cascade. E4 itself is the cheap rung for 90 % of the designs, and the DC rungs below it are not cheaper on the designs where E4 is expensive. The only screen with a real cost advantage is Y (Yosys, seconds per candidate); its predictive value (AUROC ≥ 0.75, config `screen.auroc_min`) is measured in Phase 3/4, and the M vs M_noscreen arms stay to quantify it — with `screen.candidates_es` reduced to [Y].
2. **Main scoring configuration.** Cost is no argument either way (t_H3 ≈ t_E4), and on the noise-floor set the two configurations agree on 95 % of the perturbations. Recommendation: keep E4 as the scoring configuration (the ladder's top rung, on which the floors and the rung attribution are built) and keep H3 hidden as the physical-aware certification; revisit after Exp1 (Phase 4), where real candidates instead of perturbations are evaluated under both. Moving the scoring to H3 would thin the hidden layer to H1 / H2 / H5 without a cost or agreement reason.
