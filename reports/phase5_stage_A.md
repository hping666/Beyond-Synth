# Phase 5 report (Stage A — the large tier)

Generated 2026-09-17T13:25 by scripts/report_phase.py phase5 --stage A (git 1ae7cb000aba, cfg 8aa246ed60b7). Data: reports/data/phase5_visible_A.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 11 / 18 / 18 | 981 | 2.99 | 28.3 | 104.4 |
| large | gpt-5.6-terra | B0 | 16 / 18 / 18 | 1040 | 33.32 | 0.0 | 441.4 |
| large | gpt-5.6-terra | B1_E4 | 15 / 18 / 18 | 1026 | 36.65 | 52.4 | 363.2 |
| large | gpt-5.6-terra | B2 | 15 / 18 / 18 | 1014 | 35.73 | 49.8 | 390.4 |
| large | gpt-5.6-terra | DrRTL_reimpl | 14 / 18 / 18 | 1032 | 35.64 | 43.0 | 164.9 |
| large | gpt-5.6-terra | M | 12 / 18 / 18 | 943 | 30.11 | 31.8 | 263.6 |

Unfinished groups: 6 of 6 — the numbers below are interim for those groups (runs still open, verdicts and fitness evaluations pending).

## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)

### large tier

| model (role) | arm | runs | candidates | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (contrast) | M | 11/18 | 978 | 4 | 84 (0.086) | 84 | 0 | 25 | 34 | 1.89 | 4 | 0.23 % / 0.00 % | 3.47 | 11.38 | 1.20 | 2.99 | 28.3 | 104.4 |
| gpt-5.6-terra (main) | B0 | 16/18 | 1040 | 0 | 250 (0.240) | 313 | 0 | 67 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 33.32 | 0.0 | 441.4 |
| gpt-5.6-terra (main) | B1_E4 | 15/18 | 1026 | 0 | 294 (0.286) | 225 | 0 | 141 | 104 | 5.78 | 6 | 0.49 % / 0.00 % | 10.14 | 2.84 | 1.99 | 36.65 | 52.4 | 363.2 |
| gpt-5.6-terra (main) | B2 | 15/18 | 1014 | 0 | 266 (0.262) | 262 | 0 | 97 | 70 | 3.89 | 5 | 0.38 % / 0.00 % | 6.90 | 1.96 | 1.41 | 35.73 | 49.8 | 390.4 |
| gpt-5.6-terra (main) | DrRTL_reimpl | 14/18 | 881 | 3 | 298 (0.289) | 117 | 0 | 158 | 37 | 2.06 | 3 | 0.09 % / 0.00 % | 3.58 | 1.04 | 0.86 | 35.64 | 43.0 | 164.9 |
| gpt-5.6-terra (main) | M | 12/18 | 943 | 0 | 106 (0.112) | 178 | 0 | 41 | 67 | 3.72 | 5 | 0.61 % / 0.00 % | 7.11 | 2.23 | 2.11 | 30.11 | 31.8 | 263.6 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | M | 214 | 55 | 109 | 84 | 0 | 69 | 49 | 314 | absorbed_identical: 8, harmful: 13, noise: 11, retained: 34, tradeoff: 18 | absorbed_identical: 8, harmful: 13, noise: 11, nonequiv: 462, retained: 34, tradeoff: 18 | 235 (no block-level answers) | 198 (19) | 4310 / 27777 |
| gpt-5.6-terra | B0 | 176 | 29 | 195 | 313 | 2 | 40 | 35 | 0 | - | improved: 214, no_gain: 36, nonequiv: 717 | 375 (no block-level answers) | 156 (14) | 5474 / 35401 |
| gpt-5.6-terra | B1_E4 | 190 | 30 | 194 | 225 | 1 | 53 | 39 | 0 | absorbed: 1, absorbed_identical: 38, harmful: 71, noise: 28, retained: 104, tradeoff: 43 | improved: 229, no_gain: 56, nonequiv: 640 | 383 (no block-level answers) | 164 (25) | 8522 / 31468 |
| gpt-5.6-terra | B2 | 209 | 25 | 193 | 262 | 0 | 47 | 12 | 0 | absorbed_identical: 49, harmful: 76, noise: 29, retained: 70, tradeoff: 31 | improved: 169, no_gain: 86, nonequiv: 689 | 387 (no block-level answers) | 197 (36) | 6419 / 27337 |
| gpt-5.6-terra | DrRTL_reimpl | 92 | 7 | 164 | 117 | 1 | 34 | 168 | 0 | absorbed: 30, absorbed_identical: 18, harmful: 106, noise: 81, retained: 37, tradeoff: 7 | improved: 200, no_gain: 79, nonequiv: 381 | 308 (no block-level answers) | 102 (6) | 8592 / 26602 |
| gpt-5.6-terra | M | 193 | 31 | 50 | 178 | 0 | 71 | 37 | 277 | absorbed_identical: 4, harmful: 4, noise: 6, retained: 67, tradeoff: 23 | absorbed_identical: 4, harmful: 4, noise: 6, nonequiv: 452, retained: 67, tradeoff: 23 | 135 (no block-level answers) | 135 (22) | 4607 / 30010 |

## 2. Best retained area gain per design (max over seeds; uniform rule A; '-' = no retained candidate; 0 = runs without one)

### large tier

| design | B0 (terra) | B1_E4 (terra) | B2 (terra) | DrRTL_reimpl (terra) | M (luna) | M (terra) |
|---|---|---|---|---|---|---|
| cktevo_hsm__hsm | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_nn_engine__spikeNeuron8_H7 | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_risc__btb | 0 | 2.36 % | 2.04 % | 0.82 % | 1.76 % | 2.17 % |
| drrtl_LSTM | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_aes | 0 | 0.88 % | 0.76 % | 0.61 % | 0.88 % | 4.67 % |
| drrtl_tv80 | 0 | 0 | 0 | 0 | 0 | 0 |

## 3. Model contrast (the same arm under two models on the same tier)

- **large / M**: gpt-5.6-luna (contrast): proven 0.086 / call, retained 1.89 / run, best gain mean 0.23 %, unusable 4, USD 2.99; gpt-5.6-terra (main): proven 0.112 / call, retained 3.72 / run, best gain mean 0.61 %, unusable 0, USD 30.11

## 4. Retained-gain curves (mean over the group's runs of the best retained area gain so far)

### large tier — by LLM calls (equal-call caliber)

| model | arm | 5 calls | 10 calls | 20 calls | 30 calls | 40 calls | 50 calls | 60 calls |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | B1_E4 | 0.13 % | 0.28 % | 0.44 % | 0.44 % | 0.46 % | 0.46 % | 0.49 % |
| gpt-5.6-terra | B2 | 0.10 % | 0.15 % | 0.24 % | 0.35 % | 0.36 % | 0.37 % | 0.38 % |
| gpt-5.6-terra | DrRTL_reimpl | 0.03 % | 0.03 % | 0.03 % | 0.06 % | 0.09 % | 0.09 % | 0.09 % |
| gpt-5.6-luna | M | 0.02 % | 0.05 % | 0.12 % | 0.16 % | 0.21 % | 0.21 % | 0.23 % |
| gpt-5.6-terra | M | 0.07 % | 0.22 % | 0.27 % | 0.33 % | 0.55 % | 0.55 % | 0.61 % |

### large tier — by visible DC hours per run

- gpt-5.6-terra / B1_E4: 0.25 h → 0.09 %, 1.50 h → 0.40 %, 2.75 h → 0.46 %, 4.00 h → 0.48 %, 5.25 h → 0.48 %, 6.50 h → 0.49 %, 7.75 h → 0.49 %
- gpt-5.6-terra / B2: 0.25 h → 0.10 %, 1.25 h → 0.27 %, 2.25 h → 0.36 %, 3.25 h → 0.37 %, 4.25 h → 0.37 %, 5.25 h → 0.37 %, 6.25 h → 0.38 %
- gpt-5.6-terra / DrRTL_reimpl: 0.25 h → 0.01 %, 1.75 h → 0.03 %, 3.25 h → 0.06 %, 4.75 h → 0.06 %, 6.25 h → 0.06 %, 7.75 h → 0.09 %
- gpt-5.6-luna / M: 0.25 h → 0.05 %, 0.50 h → 0.12 %, 0.75 h → 0.15 %, 1.00 h → 0.21 %, 1.25 h → 0.22 %, 1.50 h → 0.23 %, 1.75 h → 0.23 %
- gpt-5.6-terra / M: 0.25 h → 0.07 %, 0.50 h → 0.26 %, 0.75 h → 0.27 %, 1.00 h → 0.27 %, 1.25 h → 0.36 %, 1.50 h → 0.59 %, 1.75 h → 0.59 %

## 5. Correctness (the LLM's equivalence-preserving rate)

| tier | model | design | runs | candidates | proven | proven rate |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | cktevo_hsm__hsm | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_hsm__hsm | 15 | 875 | 0 | 0.0 % |
| large | gpt-5.6-luna | cktevo_nn_engine__spikeNeuron8_H7 | 3 | 172 | 16 | 9.3 % |
| large | gpt-5.6-terra | cktevo_nn_engine__spikeNeuron8_H7 | 15 | 826 | 279 | 33.8 % |
| large | gpt-5.6-luna | cktevo_risc__btb | 3 | 148 | 76 | 51.3 % |
| large | gpt-5.6-terra | cktevo_risc__btb | 15 | 788 | 570 | 72.3 % |
| large | gpt-5.6-luna | drrtl_LSTM | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | drrtl_LSTM | 15 | 883 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_aes | 3 | 153 | 24 | 15.7 % |
| large | gpt-5.6-terra | drrtl_aes | 15 | 768 | 383 | 49.9 % |
| large | gpt-5.6-luna | drrtl_tv80 | 3 | 145 | 0 | 0.0 % |
| large | gpt-5.6-terra | drrtl_tv80 | 15 | 764 | 0 | 0.0 % |

LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): cktevo_hsm__hsm under gpt-5.6-terra, cktevo_hsm__hsm under gpt-5.6-luna, drrtl_LSTM under gpt-5.6-terra, drrtl_LSTM under gpt-5.6-luna, drrtl_tv80 under gpt-5.6-terra, drrtl_tv80 under gpt-5.6-luna.

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 362, 'b': 408, 'c1': 77, 'd': 77, 'free': 5}; requested → produced a->a: 20, a->b: 35, a->c1: 3, a->d: 11, b->a: 70, b->b: 31, b->c1: 1, b->d: 7, c1->a: 81, c1->b: 113, c1->c1: 36, c1->d: 13, d->a: 140, d->b: 168, d->c1: 27, d->d: 31, free->a: 51, free->b: 61, free->c1: 10, free->d: 15, free->free: 5
- large / gpt-5.6-terra / B0: produced {'a': 241, 'b': 563, 'c1': 60, 'd': 140, 'free': 1}; requested → produced a->a: 40, a->b: 95, a->c1: 4, a->d: 21, b->a: 46, b->b: 58, b->c1: 1, b->d: 19, c1->a: 46, c1->b: 82, c1->c1: 36, c1->d: 28, d->a: 54, d->b: 159, d->c1: 8, d->d: 34, free->a: 55, free->b: 169, free->c1: 11, free->d: 38, free->free: 1
- large / gpt-5.6-terra / B1_E4: produced {'a': 313, 'b': 470, 'c1': 68, 'd': 136}; requested → produced a->a: 31, a->b: 104, a->c1: 7, a->d: 27, b->a: 75, b->b: 52, b->c1: 4, b->d: 29, c1->a: 55, c1->b: 96, c1->c1: 8, c1->d: 11, d->a: 78, d->b: 103, d->c1: 18, d->d: 20, free->a: 74, free->b: 115, free->c1: 31, free->d: 49
- large / gpt-5.6-terra / B2: produced {'a': 364, 'b': 482, 'c1': 57, 'd': 99}; requested → produced a->a: 45, a->b: 92, a->c1: 4, a->d: 2, b->a: 75, b->b: 56, b->d: 13, c1->a: 82, c1->b: 97, c1->c1: 10, c1->d: 17, d->a: 71, d->b: 123, d->c1: 30, d->d: 23, free->a: 91, free->b: 114, free->c1: 13, free->d: 44
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 408, 'b': 281, 'c1': 20, 'd': 1, 'free': 3}; requested → produced free->a: 408, free->b: 281, free->c1: 20, free->d: 1, free->free: 3
- large / gpt-5.6-terra / M: produced {'a': 309, 'b': 439, 'c1': 88, 'd': 70}; requested → produced a->a: 8, a->b: 45, a->c1: 1, a->d: 1, b->a: 49, b->b: 27, b->d: 15, c1->a: 87, c1->b: 141, c1->c1: 35, c1->d: 26, d->a: 124, d->b: 182, d->c1: 41, d->d: 17, free->a: 41, free->b: 44, free->c1: 11, free->d: 11

## 7. Runs and anomalies

Runs on the reported tiers: 108 (83 done, 25 running, 0 not started). No run in an abnormal status.

## 7a. Operational changes during the run (DECISIONS 2026-09-16; verdict definitions, floors, budgets and the stack unchanged)

Hidden DC registrations capped at 8 from 2026-09-16T14:30; split equivalence pipeline, provisional diagnosis and proof ordering from 2026-09-16T15:14; positive provisional verdicts withheld from the model from 2026-09-16T16:03.

- Provisional-versus-final diagnosis agreement: 182 of 208 proven candidates with a final diagnosis agree (87.5 %); 1972 candidates received a provisional label (absorbed_identical 26, duplicate 26, harmful 90, improved 1140, no_gain 253, noise 63, retained 164, tradeoff 210), 686 of them were not proven, 1078 still wait for the proof or the diagnosis, 1454 labels withheld from the model. Disagreements: tradeoff→duplicate; tradeoff→duplicate; retained→duplicate; harmful→duplicate; retained→duplicate; retained→duplicate; retained→duplicate; tradeoff→duplicate.
- Positive provisional feedback exposure (window 2026-09-16T15:14 to 2026-09-16T16:03): 15 LLM calls carried 25 positive pending blocks (2 runs); 8 candidates behind them — proofs since: inconclusive 8.
- Cross-run verdict reuse since 2026-09-16T15:14: 0 proofs copied from a decided record of the same pair ({}), over 1711 split-pipeline proofs of 4768 equivalence records; sim records missing: 0.

Equivalence jobs finished per hour on the VC Formal pool since the throttle (2026-09-16T14:30), by the candidate's verdict:

| hour | finished | proven | inconclusive | proven : inconclusive | falsified | rejected | sim_fail |
|---|---|---|---|---|---|---|---|
| 2026-09-16T14 | 94 | 25 | 18 | 1.39 | 6 | 37 | 8 |
| 2026-09-16T15 | 101 | 43 | 26 | 1.65 | 8 | 21 | 3 |
| 2026-09-16T16 | 88 | 35 | 35 | 1.0 | 15 | 0 | 3 |
| 2026-09-16T17 | 82 | 49 | 31 | 1.58 | 2 | 0 | 0 |
| 2026-09-16T18 | 81 | 39 | 36 | 1.08 | 4 | 0 | 2 |
| 2026-09-16T19 | 90 | 47 | 34 | 1.38 | 4 | 1 | 4 |
| 2026-09-16T20 | 79 | 33 | 35 | 0.94 | 3 | 1 | 7 |
| 2026-09-16T21 | 84 | 61 | 20 | 3.05 | 3 | 0 | 0 |
| 2026-09-16T22 | 95 | 58 | 30 | 1.93 | 7 | 0 | 0 |
| 2026-09-16T23 | 86 | 51 | 28 | 1.82 | 7 | 0 | 0 |
| 2026-09-17T00 | 85 | 43 | 41 | 1.05 | 1 | 0 | 0 |
| 2026-09-17T01 | 74 | 38 | 26 | 1.46 | 10 | 0 | 0 |
| 2026-09-17T02 | 54 | 21 | 31 | 0.68 | 2 | 0 | 0 |
| 2026-09-17T03 | 70 | 36 | 34 | 1.06 | 0 | 0 | 0 |
| 2026-09-17T04 | 51 | 27 | 19 | 1.42 | 5 | 0 | 0 |
| 2026-09-17T05 | 78 | 52 | 23 | 2.26 | 3 | 0 | 0 |
| 2026-09-17T06 | 66 | 35 | 28 | 1.25 | 3 | 0 | 0 |
| 2026-09-17T07 | 58 | 28 | 21 | 1.33 | 9 | 0 | 0 |
| 2026-09-17T08 | 62 | 27 | 33 | 0.82 | 2 | 0 | 0 |
| 2026-09-17T09 | 76 | 42 | 25 | 1.68 | 9 | 0 | 0 |
| 2026-09-17T10 | 64 | 40 | 22 | 1.82 | 2 | 0 | 0 |
| 2026-09-17T11 | 147 | 97 | 23 | 4.22 | 27 | 0 | 0 |
| 2026-09-17T12 | 169 | 137 | 23 | 5.96 | 9 | 0 | 0 |
| 2026-09-17T13 | 49 | 33 | 8 | 4.12 | 8 | 0 | 0 |

