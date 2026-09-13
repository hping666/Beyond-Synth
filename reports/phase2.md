# Phase 2 report — noise floor, SEQ pilot, E4 runtime (Exp0)

Generated 2026-09-12 18:04 by scripts/report_phase.py (git 2e4d4060fdd5, cfg 0eb167e58d08). Hidden-configuration floors (H1 / H2a / H2b / H5, H3) live in the hidden database and appear only in the hidden report after Phase 5.

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

(no E4 baseline at Phi_main yet: run scripts/phase2_noise.py submit)

## 4. SEQ pilot (PLAN 2.4) and t_H3 / t_E4

Candidates: hand-made variants (CLAUDE.md exception 2), RTL-OPT pairs with a changed flip-flop count, and the LLM batch; every candidate ran V1 -> V2 -> V3 with random seeds [1, 2].

| requested class | n | verdicts (seed 1) | median V3 seconds |
|---|---|---|---|
| b | 43 | {'pending': 40, 'proven': 3} | 29.31 |
| c1 | 43 | {'pending': 41, 'proven': 2} | 29.16 |
| c2 | 41 | {'pending': 39, 'proven_sim_only': 1, 'sim_fail': 1} | - |
| c_pair | 4 | {'falsified': 1, 'proven': 2, 'sim_fail': 1} | 30.26 |
| control_nonequiv | 1 | {'sim_fail': 1} | - |

M6 rule class vs requested class: 16 of 130 agree (LLM answers often deliver another class than instructed; the rule class is what the protocol uses).

Guardrail-3 facts for the 0 SEQ-inconclusive candidates (clocked arithmetic / offsets constant across seeds / start-done signals):


t_H3 / t_E4 and the E4-vs-H3 agreement rate come from the hidden worker as counts and seconds only (after the hidden noise runs).

## 5. Next steps

- G1: decide on the truncation if the median area floor exceeds the warning level.
- G2: SEQ fractions per class from the pilot.
- G3: screening recommendation from the E4 seconds and the cascade estimate.
