# Phase 5 report (Stage A — the large tier)

Generated 2026-09-16T14:01 by scripts/report_phase.py phase5 --stage A (git 783e525356f2, cfg 90f0c83611ef). Data: reports/data/phase5_visible_A.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 4 / 18 / 18 | 240 | 1.06 | 1.0 | 5.4 |
| large | gpt-5.6-terra | B0 | 3 / 18 / 18 | 476 | 16.97 | 0.0 | 85.9 |
| large | gpt-5.6-terra | B1_E4 | 5 / 18 / 18 | 540 | 22.71 | 12.8 | 93.1 |
| large | gpt-5.6-terra | B2 | 5 / 18 / 18 | 480 | 17.72 | 9.5 | 93.7 |
| large | gpt-5.6-terra | DrRTL_reimpl | 6 / 18 / 18 | 480 | 17.39 | 12.8 | 94.9 |
| large | gpt-5.6-terra | M | 2 / 18 / 18 | 180 | 8.20 | 0.0 | 37.5 |

Unfinished groups: 6 of 6 — the numbers below are interim for those groups (runs still open, verdicts and fitness evaluations pending).

## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)

### large tier

| model (role) | arm | runs | candidates | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (contrast) | M | 4/18 | 240 | 0 | 3 (0.013) | 3 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | 0.00 | 1.06 | 1.0 | 5.4 |
| gpt-5.6-terra (main) | B0 | 3/18 | 476 | 0 | 66 (0.139) | 108 | 0 | 18 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 16.97 | 0.0 | 85.9 |
| gpt-5.6-terra (main) | B1_E4 | 5/18 | 540 | 0 | 123 (0.228) | 119 | 0 | 74 | 22 | 1.22 | 2 | 0.17 % / 0.00 % | 4.07 | 0.97 | 1.72 | 22.71 | 12.8 | 93.1 |
| gpt-5.6-terra (main) | B2 | 5/18 | 480 | 0 | 85 (0.177) | 127 | 0 | 15 | 17 | 0.94 | 1 | 0.10 % / 0.00 % | 3.54 | 0.96 | 1.79 | 17.72 | 9.5 | 93.7 |
| gpt-5.6-terra (main) | DrRTL_reimpl | 6/18 | 408 | 3 | 113 (0.235) | 91 | 0 | 42 | 9 | 0.50 | 1 | 0.01 % / 0.00 % | 1.88 | 0.52 | 0.70 | 17.39 | 12.8 | 94.9 |
| gpt-5.6-terra (main) | M | 2/18 | 180 | 0 | 0 (0.000) | 49 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 8.20 | 0.0 | 37.5 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | M | 139 | 3 | 48 | 3 | 0 | 0 | 5 | 39 | absorbed_identical: 2, harmful: 1 | absorbed_identical: 2, harmful: 1, nonequiv: 193 | 235 (no block-level answers) | 64 (2) | 15046 / 28649 |
| gpt-5.6-terra | B0 | 134 | 11 | 72 | 108 | 2 | 72 | 11 | 0 | - | improved: 51, no_gain: 15, nonequiv: 327 | 375 (no block-level answers) | 60 (4) | 14423 / 26944 |
| gpt-5.6-terra | B1_E4 | 131 | 13 | 70 | 119 | 1 | 56 | 27 | 0 | absorbed: 1, absorbed_identical: 14, harmful: 58, noise: 5, retained: 22, tradeoff: 14 | improved: 93, no_gain: 21, nonequiv: 334 | 383 (no block-level answers) | 54 (7) | 14453 / 27123 |
| gpt-5.6-terra | B2 | 145 | 16 | 69 | 127 | 0 | 35 | 3 | 0 | absorbed_identical: 22, harmful: 18, noise: 10, retained: 17, tradeoff: 8 | improved: 32, no_gain: 43, nonequiv: 357 | 387 (no block-level answers) | 81 (10) | 15146 / 26632 |
| gpt-5.6-terra | DrRTL_reimpl | 90 | 5 | 61 | 91 | 1 | 14 | 33 | 0 | absorbed: 2, absorbed_identical: 1, harmful: 58, noise: 24, retained: 9, tradeoff: 1 | improved: 52, no_gain: 43, nonequiv: 248 | 308 (no block-level answers) | 49 (5) | 15157 / 25775 |
| gpt-5.6-terra | M | 110 | 0 | 10 | 49 | 0 | 11 | 0 | 0 | - | nonequiv: 169 | 135 (no block-level answers) | 31 (0) | 20611 / 28527 |

## 2. Best retained area gain per design (max over seeds; uniform rule A; '-' = no retained candidate; 0 = runs without one)

### large tier

| design | B0 (terra) | B1_E4 (terra) | B2 (terra) | DrRTL_reimpl (terra) | M (luna) | M (terra) |
|---|---|---|---|---|---|---|
| cktevo_hsm__hsm | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_nn_engine__spikeNeuron8_H7 | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_risc__btb | 0 | 2.36 % | 1.76 % | 0.25 % | 0 | 0 |
| drrtl_LSTM | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_aes | 0 | 0.76 % | 0 | 0 | 0 | 0 |
| drrtl_tv80 | 0 | 0 | 0 | 0 | 0 | 0 |

## 3. Model contrast (the same arm under two models on the same tier)

- **large / M**: gpt-5.6-luna (contrast): proven 0.013 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 1.06; gpt-5.6-terra (main): proven 0.000 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 8.20

## 4. Retained-gain curves (mean over the group's runs of the best retained area gain so far)

### large tier — by LLM calls (equal-call caliber)

| model | arm | 5 calls | 10 calls | 20 calls | 30 calls | 40 calls | 50 calls | 60 calls |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | B1_E4 | 0.04 % | 0.14 % | 0.14 % | 0.14 % | 0.15 % | 0.15 % | 0.17 % |
| gpt-5.6-terra | B2 | 0.03 % | 0.03 % | 0.03 % | 0.09 % | 0.10 % | 0.10 % | 0.10 % |
| gpt-5.6-terra | DrRTL_reimpl | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % |
| gpt-5.6-luna | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |

### large tier — by visible DC hours per run

- gpt-5.6-terra / B1_E4: 0.25 h → 0.00 %, 1.00 h → 0.14 %, 1.75 h → 0.14 %, 2.50 h → 0.15 %, 3.25 h → 0.15 %, 4.00 h → 0.17 %, 4.75 h → 0.17 %
- gpt-5.6-terra / B2: 0.25 h → 0.03 %, 0.75 h → 0.03 %, 1.25 h → 0.08 %, 1.75 h → 0.10 %, 2.25 h → 0.10 %, 2.75 h → 0.10 %, 3.25 h → 0.10 %
- gpt-5.6-terra / DrRTL_reimpl: 0.25 h → 0.00 %, 1.00 h → 0.01 %, 1.75 h → 0.01 %, 2.50 h → 0.01 %, 3.25 h → 0.01 %, 4.00 h → 0.01 %, 4.75 h → 0.01 %
- gpt-5.6-luna / M: 0.25 h → 0.00 %, 0.50 h → 0.00 %

## 5. Correctness (the LLM's equivalence-preserving rate)

| tier | model | design | runs | candidates | proven | proven rate |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | cktevo_hsm__hsm | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_hsm__hsm | 15 | 875 | 0 | 0.0 % |
| large | gpt-5.6-luna | cktevo_nn_engine__spikeNeuron8_H7 | 3 | 60 | 8 | 13.3 % |
| large | gpt-5.6-terra | cktevo_nn_engine__spikeNeuron8_H7 | 15 | 286 | 134 | 46.9 % |
| large | gpt-5.6-luna | cktevo_risc__btb | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | cktevo_risc__btb | 15 | 230 | 161 | 70.0 % |
| large | gpt-5.6-luna | drrtl_LSTM | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_LSTM | 15 | 233 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_aes | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_aes | 15 | 230 | 92 | 40.0 % |
| large | gpt-5.6-luna | drrtl_tv80 | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_tv80 | 15 | 230 | 0 | 0.0 % |

LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): cktevo_hsm__hsm under gpt-5.6-terra, cktevo_hsm__hsm under gpt-5.6-luna, drrtl_LSTM under gpt-5.6-terra, drrtl_tv80 under gpt-5.6-terra.

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 47, 'b': 136, 'c1': 40, 'd': 12}; requested → produced a->a: 6, a->b: 11, a->c1: 3, b->a: 6, b->b: 16, c1->a: 8, c1->b: 18, c1->c1: 19, d->a: 21, d->b: 70, d->c1: 14, d->d: 12, free->a: 6, free->b: 21, free->c1: 4
- large / gpt-5.6-terra / B0: produced {'a': 85, 'b': 307, 'c1': 35, 'd': 38}; requested → produced a->a: 17, a->b: 62, a->c1: 3, a->d: 2, b->a: 18, b->b: 36, b->d: 3, c1->a: 13, c1->b: 46, c1->c1: 19, c1->d: 6, d->a: 14, d->b: 86, d->c1: 5, d->d: 12, free->a: 23, free->b: 77, free->c1: 8, free->d: 15
- large / gpt-5.6-terra / B1_E4: produced {'a': 162, 'b': 275, 'c1': 23, 'd': 53}; requested → produced a->a: 21, a->b: 71, a->c1: 3, a->d: 7, b->a: 53, b->b: 33, b->c1: 1, b->d: 19, c1->a: 26, c1->b: 54, c1->c1: 2, c1->d: 4, d->a: 29, d->b: 55, d->c1: 8, d->d: 6, free->a: 33, free->b: 62, free->c1: 9, free->d: 17
- large / gpt-5.6-terra / B2: produced {'a': 115, 'b': 293, 'c1': 29, 'd': 40}; requested → produced a->a: 27, a->b: 54, a->c1: 4, a->d: 1, b->a: 25, b->b: 43, b->d: 5, c1->a: 28, c1->b: 51, c1->c1: 6, c1->d: 3, d->a: 22, d->b: 86, d->c1: 10, d->d: 14, free->a: 13, free->b: 59, free->c1: 9, free->d: 17
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 165, 'b': 205, 'c1': 3, 'free': 2}; requested → produced free->a: 165, free->b: 205, free->c1: 3, free->free: 2
- large / gpt-5.6-terra / M: produced {'b': 167, 'c1': 12, 'd': 1}; requested → produced a->b: 16, a->c1: 1, b->b: 14, c1->b: 38, c1->c1: 7, d->b: 87, d->c1: 3, d->d: 1, free->b: 12, free->c1: 1

## 7. Runs and anomalies

Runs on the reported tiers: 108 (25 done, 14 running, 68 not started). Abnormal statuses: r20260915_214859_keNeuron8_H7_B0_-terra_s1 failed.

