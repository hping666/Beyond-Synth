# Phase 2 report — noise floor, SEQ pilot, E4 runtime (Exp0)

Generated 2026-09-12 19:27 by scripts/report_phase.py (git 55d02adc2117, cfg 0eb167e58d08). Hidden-configuration floors (H1 / H2a / H2b / H5, H3) live in the hidden database and appear only in the hidden report after Phase 5.

## 1. Perturbation generator (PLAN 2.1)

4 designs of the sets; perturbations per type {'P1_rename': 14, 'P2_reorder': 10, 'P3_expr': 1, 'P4_ctrl': 4}; types not applicable {'P3_expr': 3, 'P4_ctrl': 3}; designs Pyverilog cannot parse: 0 ().

SEQ gate (V1 -> V2 -> V3; only `proven` enters the floor):

| type | falsified | pending | proven | proven_rename | rejected | sim_fail | non-equivalence rate |
|---|---|---|---|---|---|---|---|
| P1_rename | 1 | 495 | 60 | 8 | 6 | 1 | 1.4% of 571 |
| P2_reorder | 0 | 344 | 45 | 0 | 5 | 0 | 1.3% of 394 |
| P3_expr | 0 | 219 | 11 | 0 | 5 | 0 | 2.1% of 235 |
| P4_ctrl | 0 | 199 | 21 | 0 | 5 | 0 | 2.2% of 225 |

## 2. Noise floor sigma_D (PLAN 2.3, visible configurations)

(not collected yet: scripts/phase2_noise.py collect)

## 3. E4 runtime (PLAN 2.5)

E4 seconds at Phi_main (Nangate45) over 128 set designs: min 54, q25 69, median 72, q75 75, q95 186, max 637, mean 89.

Scale (config `scale`): 30 starting points x 6 arms x 3 seeds x N=5 x K=12 = 32400 candidate evaluations.
- full-E4 scale: 804 DC hours at the mean t_E4 (89 s); at 12 concurrent runs ≈ 67 h wall, at 50 seats ≈ 16 h.
- per-design budget rule k_e4_equiv = 60 x t_E4(D): median budget 1.2 DC hours per run.

| suite | designs | median t_E4 (s) | max t_E4 (s) |
|---|---|---|---|
| cktevo | 30 | 66 | 540 |
| drrtl | 18 | 77 | 314 |
| rtllm | 41 | 72 | 148 |
| rtlopt | 39 | 73 | 637 |

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

t_H3 / t_E4 and the E4-vs-H3 agreement rate come from the hidden worker as counts and seconds only (after the hidden noise runs).

## 5. Next steps

- G1: decide on the truncation if the median area floor exceeds the warning level.
- G2: SEQ fractions per class from the pilot.
- G3: screening recommendation from the E4 seconds and the cascade estimate.
