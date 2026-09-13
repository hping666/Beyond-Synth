# Phase 2 report — noise floor, SEQ pilot, E4 runtime (Exp0)

Generated 2026-09-13 10:07 by scripts/report_phase.py (git 71cf22ff2b84, cfg 443559992d75). Hidden-configuration floors (H1 / H2a / H2b / H5, H3) live in the hidden database and appear only in the hidden report after Phase 5.

## 1. Perturbation generator (PLAN 2.1)

4 designs of the sets; perturbations per type {'P1_rename': 14, 'P2_reorder': 10, 'P3_expr': 1, 'P4_ctrl': 4}; types not applicable {'P3_expr': 3, 'P4_ctrl': 3}; designs Pyverilog cannot parse: 0 ().

SEQ gate (V1 -> V2 -> V3; only `proven` enters the floor):

| type | error | falsified | inconclusive | pending | proven | proven_rename | rejected | sim_fail | non-equivalence rate |
|---|---|---|---|---|---|---|---|---|---|
| P1_rename | 1 | 16 | 0 | 21 | 392 | 91 | 45 | 5 | 11.6% of 571 |
| P2_reorder | 0 | 7 | 3 | 8 | 328 | 0 | 43 | 5 | 14.0% of 394 |
| P3_expr | 0 | 8 | 6 | 10 | 163 | 0 | 44 | 4 | 23.8% of 235 |
| P4_ctrl | 0 | 6 | 2 | 6 | 145 | 0 | 61 | 8 | 32.9% of 228 |

## 2. Noise floor sigma_D (PLAN 2.3, visible configurations)

| config | metric | designs | median sigma | q75 | max |
|---|---|---|---|---|---|
| E1 | area | 137 | 0.0000 | 0.0000 | 0.0153 |
| E1 | power_saif | 137 | 0.0000 | 0.0000 | 0.0913 |
| E1 | tns | 137 | 0.0000 | 0.0000 | 46.2520 |
| E1 | wns | 137 | 0.0000 | 0.0000 | 0.0434 |
| E2 | area | 137 | 0.0000 | 0.0000 | 0.0488 |
| E2 | power_saif | 137 | 0.0000 | 0.0000 | 0.1211 |
| E2 | tns | 137 | 0.0000 | 0.0000 | 0.0533 |
| E2 | wns | 137 | 0.0000 | 0.0000 | 0.0134 |
| E3 | area | 138 | 0.0000 | 0.0000 | 0.0488 |
| E3 | power_saif | 138 | 0.0000 | 0.0000 | 0.1892 |
| E3 | tns | 138 | 0.0000 | 0.0000 | 0.0533 |
| E3 | wns | 138 | 0.0000 | 0.0000 | 0.0134 |
| E4 | area | 138 | 0.0000 | 0.0000 | 0.0488 |
| E4 | power_saif | 138 | 0.0000 | 0.0000 | 0.3241 |
| E4 | tns | 138 | 0.0000 | 0.0000 | 0.0533 |
| E4 | wns | 138 | 0.0000 | 0.0000 | 0.0134 |

Minimum reportable gain = 2.0 x sigma_D (config noise.k_sigma); per-design values in the noise_floor table and reports/data/phase2_noise_floor.json.

### 2a. Floor distribution on the set designs (dev + held)

| config | metric | designs with floor | sigma_robust = 0 | sigma_std = 0 | max abs delta > 1 % | > 5 % | pooled q95 of abs delta | pooled q99 | pooled max | proposed t_D median / q95 / max | designs above pooled min |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | area | 95 | 81 | 60 | 18 | 2 | 0.0152 | 0.0594 | 0.0669 | 0.0152 / 0.0264 / 0.0669 | 10 |
| E1 | power_saif | 95 | 69 | 47 | 28 | 11 | 0.0441 | 0.1302 | 0.3943 | 0.0441 / 0.0901 / 0.3943 | 12 |
| E1 | tns | 95 | 87 | 85 | 9 | 7 | 1.6394 | 38.4399 | 153.9485 | 1.6394 / 3.9967 / 153.9485 | 6 |
| E1 | wns | 95 | 85 | 63 | 17 | 5 | 0.0323 | 0.0623 | 0.1033 | 0.0323 / 0.0584 / 0.1033 | 10 |
| E2 | area | 95 | 88 | 65 | 17 | 6 | 0.0171 | 0.0805 | 0.1625 | 0.0171 / 0.0525 / 0.1625 | 12 |
| E2 | power_saif | 95 | 85 | 51 | 26 | 10 | 0.0638 | 0.1661 | 0.3648 | 0.0638 / 0.1219 / 0.3648 | 10 |
| E2 | tns | 95 | 95 | 90 | 5 | 5 | 0.0000 | 0.0867 | 8.2259 | 0.0000 / 0.0180 / 8.2259 | 5 |
| E2 | wns | 95 | 88 | 63 | 17 | 9 | 0.0148 | 0.1364 | 0.1460 | 0.0148 / 0.0752 / 0.1460 | 14 |
| E3 | area | 95 | 88 | 64 | 25 | 13 | 0.0513 | 0.1523 | 0.2605 | 0.0513 / 0.1386 / 0.2605 | 12 |
| E3 | power_saif | 95 | 85 | 51 | 27 | 15 | 0.0751 | 0.2157 | 0.5771 | 0.0751 / 0.1947 / 0.5771 | 12 |
| E3 | tns | 95 | 95 | 93 | 1 | 1 | 0.0000 | 0.0000 | 2.1978 | 0.0000 / 0.0000 / 2.1978 | 2 |
| E3 | wns | 95 | 88 | 63 | 19 | 7 | 0.0130 | 0.1364 | 0.1460 | 0.0130 / 0.0522 / 0.1460 | 15 |
| E4 | area | 95 | 90 | 68 | 18 | 9 | 0.0497 | 0.1865 | 0.1866 | 0.0497 / 0.1016 / 0.1866 | 9 |
| E4 | power_saif | 95 | 86 | 53 | 25 | 16 | 0.1156 | 0.3219 | 0.6425 | 0.1156 / 0.2257 / 0.6482 | 10 |
| E4 | tns | 95 | 95 | 93 | 2 | 1 | 0.0000 | 0.0000 | 0.3120 | 0.0000 / 0.0000 / 0.3120 | 2 |
| E4 | wns | 95 | 91 | 67 | 13 | 6 | 0.0167 | 0.0821 | 0.1460 | 0.0167 / 0.0522 / 0.1460 | 11 |

Proposed threshold (G1 alternative): t_D = max(2 x sigma_robust, max |delta| over D's own proven perturbations, pooled q95 of |delta| over all perturbation records of the configuration); the pooled q95 is the minimum for designs whose perturbations never change the netlist. The spec's 2 x sigma_robust stays in the table for the sensitivity report.

### 2b. Perturbation types that change the netlist (area or cell count of D differs)

| config | P1_rename | P2_reorder | P3_expr | P4_ctrl |
|---|---|---|---|---|
| E1 | 97 / 329 (29 %) | 70 / 243 (29 %) | 26 / 141 (18 %) | 15 / 123 (12 %) |
| E2 | 19 / 329 (6 %) | 89 / 243 (37 %) | 18 / 141 (13 %) | 15 / 123 (12 %) |
| E3 | 18 / 329 (5 %) | 95 / 243 (39 %) | 16 / 141 (11 %) | 15 / 123 (12 %) |
| E4 | 18 / 329 (5 %) | 77 / 243 (32 %) | 14 / 141 (10 %) | 17 / 123 (14 %) |

### 2c. Monotonicity of D across the rungs (127 set designs with every rung at Φ_main)

| step | designs whose area grows | designs whose WNS drops |
|---|---|---|
| E1 -> E2 | 15 | 47 |
| E2 -> E3 | 34 | 17 |
| E3 -> E4 | 5 | 19 |
| E1 -> E4 | 10 | 44 |

WNS is compared at Φ_main (the E4 knee): once a rung meets timing, area recovery legitimately trades slack, so a WNS drop between two rungs that both meet timing is not a regression.

## 3. E4 runtime (PLAN 2.5)

E4 seconds at Phi_main (Nangate45) over 128 set designs: min 62, q25 76, median 79, q75 85, q95 185, max 693, mean 100.

Scale (config `scale`): 30 starting points x 6 arms x 3 seeds x N=5 x K=12 = 32400 candidate evaluations.
- full-E4 scale: 903 DC hours at the mean t_E4 (100 s); at 12 concurrent runs ≈ 75 h wall, at 50 seats ≈ 18 h.
- per-design budget rule k_e4_equiv = 60 x t_E4(D): median budget 1.3 DC hours per run.

Screening economics (config `screen`): E4 is 'cheap' below 120 s; 13 of 128 set designs are above that (their mean t_E4 = 278 s). Mean screening-rung seconds at Φ_main over the designs with both: E1 35 s, E2 104 s; over the non-cheap designs alone: E1 272 s, E2 309 s against t_E4 278 s (a DC screening rung at Φ_main is not cheaper than E4 where E4 is expensive).

| cascade (ES on every candidate, p promoted to E4) | all designs, DC hours | wall at 50 seats | hybrid: cheap designs straight to E4, only non-cheap designs screened |
|---|---|---|---|
| ES = E1, p = 0.10 | 406 (45 % of full-E4) | 8 h | 909 (101 %) |
| ES = E1, p = 0.25 | 540 (60 % of full-E4) | 11 h | 945 (105 %) |
| ES = E1, p = 0.50 | 764 (85 % of full-E4) | 15 h | 1005 (111 %) |
| ES = E2, p = 0.10 | 1025 (113 % of full-E4) | 20 h | 957 (106 %) |
| ES = E2, p = 0.25 | 1160 (128 % of full-E4) | 23 h | 995 (110 %) |
| ES = E2, p = 0.50 | 1386 (153 % of full-E4) | 28 h | 1058 (117 %) |

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

t_H3 / t_E4 and the E4-vs-H3 agreement rate come from the hidden worker as counts and seconds only (scripts/hidden_worker.py --g3-summary after the H3 noise runs).

## 5. Next steps

- G1: decide on the truncation if the median area floor exceeds the warning level.
- G2: SEQ fractions per class from the pilot.
- G3: screening recommendation from the E4 seconds and the cascade estimate.
