# Phase 5 report (Stage A — the large tier)

Generated 2026-09-17T10:23 by scripts/report_phase.py phase5 --stage A (git c045fb119fdc, cfg 8aa246ed60b7). Data: reports/data/phase5_visible_A.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 10 / 18 / 18 | 791 | 2.50 | 22.4 | 102.6 |
| large | gpt-5.6-terra | B0 | 15 / 18 / 18 | 987 | 32.02 | 0.0 | 412.3 |
| large | gpt-5.6-terra | B1_E4 | 12 / 18 / 18 | 936 | 33.95 | 42.1 | 257.6 |
| large | gpt-5.6-terra | B2 | 12 / 18 / 18 | 895 | 32.61 | 39.7 | 311.6 |
| large | gpt-5.6-terra | DrRTL_reimpl | 13 / 18 / 18 | 844 | 29.65 | 33.3 | 156.0 |
| large | gpt-5.6-terra | M | 8 / 18 / 18 | 785 | 25.98 | 25.1 | 195.0 |

Unfinished groups: 6 of 6 — the numbers below are interim for those groups (runs still open, verdicts and fitness evaluations pending).

## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)

### large tier

| model (role) | arm | runs | candidates | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (contrast) | M | 10/18 | 787 | 4 | 74 (0.094) | 81 | 0 | 23 | 32 | 1.78 | 3 | 0.19 % / 0.00 % | 4.05 | 12.80 | 1.43 | 2.50 | 22.4 | 102.6 |
| gpt-5.6-terra (main) | B0 | 15/18 | 987 | 0 | 241 (0.244) | 299 | 0 | 63 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 32.02 | 0.0 | 412.3 |
| gpt-5.6-terra (main) | B1_E4 | 12/18 | 936 | 0 | 262 (0.280) | 203 | 0 | 128 | 90 | 5.00 | 5 | 0.34 % / 0.00 % | 9.62 | 2.65 | 2.14 | 33.95 | 42.1 | 257.6 |
| gpt-5.6-terra (main) | B2 | 12/18 | 898 | 0 | 235 (0.263) | 243 | 0 | 82 | 52 | 2.89 | 3 | 0.25 % / 0.00 % | 5.81 | 1.59 | 1.31 | 32.61 | 39.7 | 311.6 |
| gpt-5.6-terra (main) | DrRTL_reimpl | 13/18 | 726 | 3 | 245 (0.290) | 112 | 0 | 130 | 10 | 0.56 | 2 | 0.05 % / 0.00 % | 1.19 | 0.34 | 0.30 | 29.65 | 33.3 | 156.0 |
| gpt-5.6-terra (main) | M | 8/18 | 785 | 0 | 98 (0.125) | 171 | 0 | 36 | 62 | 3.44 | 4 | 0.52 % / 0.00 % | 7.90 | 2.39 | 2.47 | 25.98 | 25.1 | 195.0 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | M | 199 | 45 | 90 | 81 | 0 | 25 | 45 | 228 | absorbed_identical: 7, harmful: 11, noise: 11, retained: 32, tradeoff: 13 | absorbed_identical: 7, harmful: 11, noise: 11, nonequiv: 415, retained: 32, tradeoff: 13 | 235 (no block-level answers) | 161 (17) | 5165 / 28632 |
| gpt-5.6-terra | B0 | 173 | 29 | 195 | 299 | 2 | 20 | 28 | 0 | - | improved: 205, no_gain: 36, nonequiv: 700 | 375 (no block-level answers) | 154 (14) | 5509 / 35916 |
| gpt-5.6-terra | B1_E4 | 179 | 23 | 194 | 203 | 1 | 36 | 38 | 0 | absorbed: 1, absorbed_identical: 38, harmful: 69, noise: 26, retained: 90, tradeoff: 29 | improved: 197, no_gain: 56, nonequiv: 600 | 383 (no block-level answers) | 149 (20) | 9619 / 30232 |
| gpt-5.6-terra | B2 | 194 | 23 | 167 | 243 | 0 | 27 | 9 | 0 | absorbed_identical: 48, harmful: 75, noise: 26, retained: 52, tradeoff: 23 | improved: 139, no_gain: 85, nonequiv: 627 | 387 (no block-level answers) | 171 (31) | 8267 / 27401 |
| gpt-5.6-terra | DrRTL_reimpl | 91 | 6 | 144 | 112 | 1 | 22 | 105 | 0 | absorbed: 23, absorbed_identical: 6, harmful: 103, noise: 78, retained: 10, tradeoff: 6 | improved: 160, no_gain: 66, nonequiv: 354 | 308 (no block-level answers) | 92 (5) | 10826 / 27607 |
| gpt-5.6-terra | M | 184 | 27 | 34 | 171 | 0 | 29 | 33 | 209 | absorbed_identical: 4, harmful: 3, noise: 5, retained: 62, tradeoff: 22 | absorbed_identical: 4, harmful: 3, noise: 5, nonequiv: 416, retained: 62, tradeoff: 22 | 135 (no block-level answers) | 112 (21) | 5197 / 28748 |

## 2. Best retained area gain per design (max over seeds; uniform rule A; '-' = no retained candidate; 0 = runs without one)

### large tier

| design | B0 (terra) | B1_E4 (terra) | B2 (terra) | DrRTL_reimpl (terra) | M (luna) | M (terra) |
|---|---|---|---|---|---|---|
| cktevo_hsm__hsm | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_nn_engine__spikeNeuron8_H7 | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_risc__btb | 0 | 2.36 % | 1.97 % | 0.25 % | 1.76 % | 2.17 % |
| drrtl_LSTM | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_aes | 0 | 0.88 % | 0.76 % | 0.61 % | 0.88 % | 4.67 % |
| drrtl_tv80 | 0 | 0 | 0 | 0 | 0 | 0 |

## 3. Model contrast (the same arm under two models on the same tier)

- **large / M**: gpt-5.6-luna (contrast): proven 0.094 / call, retained 1.78 / run, best gain mean 0.19 %, unusable 4, USD 2.50; gpt-5.6-terra (main): proven 0.125 / call, retained 3.44 / run, best gain mean 0.52 %, unusable 0, USD 25.98

## 4. Retained-gain curves (mean over the group's runs of the best retained area gain so far)

### large tier — by LLM calls (equal-call caliber)

| model | arm | 5 calls | 10 calls | 20 calls | 30 calls | 40 calls | 50 calls | 60 calls |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | B1_E4 | 0.13 % | 0.24 % | 0.30 % | 0.30 % | 0.32 % | 0.32 % | 0.34 % |
| gpt-5.6-terra | B2 | 0.04 % | 0.08 % | 0.11 % | 0.22 % | 0.23 % | 0.24 % | 0.25 % |
| gpt-5.6-terra | DrRTL_reimpl | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.05 % | 0.05 % | 0.05 % |
| gpt-5.6-luna | M | 0.02 % | 0.02 % | 0.09 % | 0.12 % | 0.18 % | 0.18 % | 0.19 % |
| gpt-5.6-terra | M | 0.04 % | 0.14 % | 0.18 % | 0.23 % | 0.46 % | 0.46 % | 0.52 % |

### large tier — by visible DC hours per run

- gpt-5.6-terra / B1_E4: 0.25 h → 0.09 %, 1.50 h → 0.26 %, 2.75 h → 0.31 %, 4.00 h → 0.33 %, 5.25 h → 0.34 %, 6.50 h → 0.34 %, 7.75 h → 0.34 %
- gpt-5.6-terra / B2: 0.25 h → 0.03 %, 1.25 h → 0.14 %, 2.25 h → 0.23 %, 3.25 h → 0.24 %, 4.25 h → 0.24 %, 5.25 h → 0.24 %, 6.25 h → 0.25 %
- gpt-5.6-terra / DrRTL_reimpl: 0.25 h → 0.00 %, 1.75 h → 0.01 %, 3.25 h → 0.01 %, 4.75 h → 0.01 %, 6.25 h → 0.01 %, 7.75 h → 0.05 %
- gpt-5.6-luna / M: 0.25 h → 0.02 %, 0.50 h → 0.09 %, 0.75 h → 0.12 %, 1.00 h → 0.17 %, 1.25 h → 0.18 %, 1.50 h → 0.19 %, 1.75 h → 0.19 %
- gpt-5.6-terra / M: 0.25 h → 0.07 %, 0.50 h → 0.17 %, 0.75 h → 0.18 %, 1.00 h → 0.18 %, 1.25 h → 0.50 %, 1.50 h → 0.50 %, 1.75 h → 0.50 %

## 5. Correctness (the LLM's equivalence-preserving rate)

| tier | model | design | runs | candidates | proven | proven rate |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | cktevo_hsm__hsm | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_hsm__hsm | 15 | 875 | 0 | 0.0 % |
| large | gpt-5.6-luna | cktevo_nn_engine__spikeNeuron8_H7 | 3 | 131 | 13 | 9.9 % |
| large | gpt-5.6-terra | cktevo_nn_engine__spikeNeuron8_H7 | 15 | 775 | 268 | 34.6 % |
| large | gpt-5.6-luna | cktevo_risc__btb | 3 | 120 | 68 | 56.7 % |
| large | gpt-5.6-terra | cktevo_risc__btb | 15 | 665 | 476 | 71.6 % |
| large | gpt-5.6-luna | drrtl_LSTM | 3 | 120 | 0 | 0.0 % |
| large | gpt-5.6-terra | drrtl_LSTM | 15 | 784 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_aes | 3 | 120 | 24 | 20.0 % |
| large | gpt-5.6-terra | drrtl_aes | 15 | 620 | 354 | 57.1 % |
| large | gpt-5.6-luna | drrtl_tv80 | 3 | 116 | 0 | 0.0 % |
| large | gpt-5.6-terra | drrtl_tv80 | 15 | 613 | 0 | 0.0 % |

LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): cktevo_hsm__hsm under gpt-5.6-terra, cktevo_hsm__hsm under gpt-5.6-luna, drrtl_LSTM under gpt-5.6-terra, drrtl_LSTM under gpt-5.6-luna, drrtl_tv80 under gpt-5.6-terra, drrtl_tv80 under gpt-5.6-luna.

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 261, 'b': 342, 'c1': 70, 'd': 66, 'free': 3}; requested → produced a->a: 15, a->b: 31, a->c1: 3, a->d: 11, b->a: 46, b->b: 28, b->c1: 1, b->d: 4, c1->a: 65, c1->b: 70, c1->c1: 32, c1->d: 12, d->a: 96, d->b: 157, d->c1: 24, d->d: 25, free->a: 39, free->b: 56, free->c1: 10, free->d: 14, free->free: 3
- large / gpt-5.6-terra / B0: produced {'a': 237, 'b': 542, 'c1': 59, 'd': 120, 'free': 1}; requested → produced a->a: 39, a->b: 91, a->c1: 4, a->d: 19, b->a: 44, b->b: 58, b->c1: 1, b->d: 9, c1->a: 46, c1->b: 81, c1->c1: 35, c1->d: 27, d->a: 54, d->b: 152, d->c1: 8, d->d: 33, free->a: 54, free->b: 160, free->c1: 11, free->d: 32, free->free: 1
- large / gpt-5.6-terra / B1_E4: produced {'a': 309, 'b': 413, 'c1': 62, 'd': 114}; requested → produced a->a: 27, a->b: 95, a->c1: 6, a->d: 26, b->a: 75, b->b: 49, b->c1: 4, b->d: 27, c1->a: 55, c1->b: 85, c1->c1: 8, c1->d: 9, d->a: 78, d->b: 86, d->c1: 15, d->d: 16, free->a: 74, free->b: 98, free->c1: 29, free->d: 36
- large / gpt-5.6-terra / B2: produced {'a': 323, 'b': 422, 'c1': 53, 'd': 91}; requested → produced a->a: 40, a->b: 82, a->c1: 4, a->d: 2, b->a: 71, b->b: 51, b->d: 13, c1->a: 74, c1->b: 81, c1->c1: 8, c1->d: 17, d->a: 61, d->b: 108, d->c1: 29, d->d: 20, free->a: 77, free->b: 100, free->c1: 12, free->d: 39
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 353, 'b': 246, 'c1': 19, 'd': 1, 'free': 2}; requested → produced free->a: 353, free->b: 246, free->c1: 19, free->d: 1, free->free: 2
- large / gpt-5.6-terra / M: produced {'a': 230, 'b': 385, 'c1': 77, 'd': 60}; requested → produced a->a: 7, a->b: 41, a->c1: 1, a->d: 1, b->a: 44, b->b: 22, b->d: 15, c1->a: 54, c1->b: 114, c1->c1: 33, c1->d: 19, d->a: 93, d->b: 165, d->c1: 33, d->d: 15, free->a: 32, free->b: 43, free->c1: 10, free->d: 10

## 7. Runs and anomalies

Runs on the reported tiers: 108 (70 done, 30 running, 8 not started). No run in an abnormal status.

## 7a. Operational changes during the run (DECISIONS 2026-09-16; verdict definitions, floors, budgets and the stack unchanged)

Hidden DC registrations capped at 8 from 2026-09-16T14:30; split equivalence pipeline, provisional diagnosis and proof ordering from 2026-09-16T15:14; positive provisional verdicts withheld from the model from 2026-09-16T16:03.

- Provisional-versus-final diagnosis agreement: 163 of 188 proven candidates with a final diagnosis agree (86.7 %); 1392 candidates received a provisional label (absorbed_identical 18, duplicate 18, harmful 72, improved 760, no_gain 173, noise 49, retained 139, tradeoff 163), 575 of them were not proven, 629 still wait for the proof or the diagnosis, 1002 labels withheld from the model. Disagreements: tradeoff→duplicate; tradeoff→duplicate; retained→duplicate; harmful→duplicate; retained→duplicate; retained→duplicate; retained→duplicate; noise→duplicate.
- Positive provisional feedback exposure (window 2026-09-16T15:14 to 2026-09-16T16:03): 15 LLM calls carried 25 positive pending blocks (2 runs); 8 candidates behind them — proofs since: inconclusive 8.
- Cross-run verdict reuse since 2026-09-16T15:14: 0 proofs copied from a decided record of the same pair ({}), over 1304 split-pipeline proofs of 3590 equivalence records; sim records missing: 0.

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
| 2026-09-17T10 | 21 | 13 | 6 | 2.17 | 2 | 0 | 0 |

