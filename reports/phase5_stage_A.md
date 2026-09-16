# Phase 5 report (Stage A — the large tier)

Generated 2026-09-16T11:00 by scripts/report_phase.py phase5 --stage A (git 34c0dfe9bb75, cfg b326eaa98549). Data: reports/data/phase5_visible_A.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 0 / 18 / 18 | 240 | 1.06 | 0.5 | 0.4 |
| large | gpt-5.6-terra | B0 | 2 / 18 / 18 | 476 | 16.97 | 0.0 | 72.2 |
| large | gpt-5.6-terra | B1_E4 | 2 / 18 / 18 | 540 | 22.71 | 8.9 | 60.2 |
| large | gpt-5.6-terra | B2 | 2 / 18 / 18 | 480 | 17.72 | 7.0 | 59.4 |
| large | gpt-5.6-terra | DrRTL_reimpl | 4 / 18 / 18 | 480 | 17.39 | 11.1 | 67.8 |
| large | gpt-5.6-terra | M | 1 / 18 / 18 | 180 | 8.20 | 0.0 | 23.1 |

Unfinished groups: 6 of 6 — the numbers below are interim for those groups (runs still open, verdicts and fitness evaluations pending).

## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)

### large tier

| model (role) | arm | runs | candidates | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (contrast) | M | 0/18 | 240 | 0 | 2 (0.008) | 1 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | 0.00 | 1.06 | 0.5 | 0.4 |
| gpt-5.6-terra (main) | B0 | 2/18 | 476 | 0 | 53 (0.111) | 84 | 0 | 15 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 16.97 | 0.0 | 72.2 |
| gpt-5.6-terra (main) | B1_E4 | 2/18 | 540 | 0 | 88 (0.163) | 97 | 0 | 48 | 13 | 0.72 | 2 | 0.15 % / 0.00 % | 2.41 | 0.57 | 1.46 | 22.71 | 8.9 | 60.2 |
| gpt-5.6-terra (main) | B2 | 2/18 | 480 | 0 | 59 (0.123) | 98 | 0 | 14 | 14 | 0.78 | 1 | 0.10 % / 0.00 % | 2.92 | 0.79 | 2.00 | 17.72 | 7.0 | 59.4 |
| gpt-5.6-terra (main) | DrRTL_reimpl | 4/18 | 408 | 3 | 92 (0.192) | 75 | 0 | 40 | 7 | 0.39 | 1 | 0.01 % / 0.00 % | 1.46 | 0.40 | 0.63 | 17.39 | 11.1 | 67.8 |
| gpt-5.6-terra (main) | M | 1/18 | 180 | 0 | 0 (0.000) | 43 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 8.20 | 0.0 | 23.1 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | M | 122 | 2 | 48 | 1 | 0 | 23 | 3 | 39 | absorbed_identical: 1, harmful: 1 | absorbed_identical: 1, harmful: 1, nonequiv: 173 | 237 (no block-level answers) | 64 (1) | 13159 / 27149 |
| gpt-5.6-terra | B0 | 106 | 4 | 70 | 84 | 1 | 147 | 11 | 0 | - | improved: 38, no_gain: 15, nonequiv: 265 | 375 (no block-level answers) | 60 (3) | 12402 / 25860 |
| gpt-5.6-terra | B1_E4 | 99 | 10 | 68 | 97 | 1 | 150 | 27 | 0 | absorbed_identical: 14, harmful: 38, noise: 5, retained: 13, tradeoff: 12 | improved: 61, no_gain: 21, nonequiv: 275 | 383 (no block-level answers) | 54 (5) | 12507 / 27105 |
| gpt-5.6-terra | B2 | 135 | 12 | 69 | 98 | 0 | 104 | 3 | 0 | absorbed_identical: 16, harmful: 11, noise: 9, retained: 14, tradeoff: 5 | improved: 25, no_gain: 30, nonequiv: 314 | 387 (no block-level answers) | 81 (8) | 13553 / 24796 |
| gpt-5.6-terra | DrRTL_reimpl | 68 | 5 | 58 | 75 | 1 | 76 | 33 | 0 | absorbed: 2, absorbed_identical: 1, harmful: 44, noise: 23, retained: 7 | improved: 49, no_gain: 28, nonequiv: 207 | 308 (no block-level answers) | 49 (2) | 13499 / 23433 |
| gpt-5.6-terra | M | 79 | 0 | 8 | 43 | 0 | 50 | 0 | 0 | - | nonequiv: 130 | 135 (no block-level answers) | 31 (0) | 16960 / 28178 |

## 2. Best retained area gain per design (max over seeds; uniform rule A; '-' = no retained candidate; 0 = runs without one)

### large tier

| design | B0 (terra) | B1_E4 (terra) | B2 (terra) | DrRTL_reimpl (terra) | M (luna) | M (terra) |
|---|---|---|---|---|---|---|
| cktevo_hsm__hsm | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_nn_engine__spikeNeuron8_H7 | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_risc__btb | 0 | 1.93 % | 1.76 % | 0.25 % | 0 | 0 |
| drrtl_LSTM | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_aes | 0 | 0.76 % | 0 | 0 | 0 | 0 |
| drrtl_tv80 | 0 | 0 | 0 | 0 | 0 | 0 |

## 3. Model contrast (the same arm under two models on the same tier)

- **large / M**: gpt-5.6-luna (contrast): proven 0.008 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 1.06; gpt-5.6-terra (main): proven 0.000 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 8.20

## 4. Retained-gain curves (mean over the group's runs of the best retained area gain so far)

### large tier — by LLM calls (equal-call caliber)

| model | arm | 5 calls | 10 calls | 20 calls | 30 calls | 40 calls | 50 calls | 60 calls |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | B1_E4 | 0.04 % | 0.14 % | 0.14 % | 0.14 % | 0.15 % | 0.15 % | 0.15 % |
| gpt-5.6-terra | B2 | 0.03 % | 0.03 % | 0.03 % | 0.09 % | 0.10 % | 0.10 % | 0.10 % |
| gpt-5.6-terra | DrRTL_reimpl | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % |
| gpt-5.6-luna | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |

### large tier — by visible DC hours per run

- gpt-5.6-terra / B1_E4: 0.25 h → 0.00 %, 0.50 h → 0.10 %, 0.75 h → 0.14 %, 1.00 h → 0.14 %, 1.25 h → 0.14 %, 1.50 h → 0.14 %, 1.75 h → 0.14 %
- gpt-5.6-terra / B2: 0.25 h → 0.03 %, 0.50 h → 0.03 %, 0.75 h → 0.03 %, 1.00 h → 0.03 %, 1.25 h → 0.08 %, 1.50 h → 0.09 %, 1.75 h → 0.10 %
- gpt-5.6-terra / DrRTL_reimpl: 0.25 h → 0.00 %, 1.00 h → 0.01 %, 1.75 h → 0.01 %, 2.50 h → 0.01 %, 3.25 h → 0.01 %, 4.00 h → 0.01 %, 4.75 h → 0.01 %
- gpt-5.6-luna / M: 0.25 h → 0.00 %

## 5. Correctness (the LLM's equivalence-preserving rate)

| tier | model | design | runs | candidates | proven | proven rate |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | cktevo_hsm__hsm | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_hsm__hsm | 15 | 875 | 0 | 0.0 % |
| large | gpt-5.6-luna | cktevo_nn_engine__spikeNeuron8_H7 | 3 | 60 | 5 | 8.3 % |
| large | gpt-5.6-terra | cktevo_nn_engine__spikeNeuron8_H7 | 15 | 286 | 104 | 36.4 % |
| large | gpt-5.6-luna | cktevo_risc__btb | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | cktevo_risc__btb | 15 | 230 | 112 | 48.7 % |
| large | gpt-5.6-luna | drrtl_LSTM | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_LSTM | 15 | 233 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_aes | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_aes | 15 | 230 | 76 | 33.0 % |
| large | gpt-5.6-luna | drrtl_tv80 | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_tv80 | 15 | 230 | 0 | 0.0 % |

LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): cktevo_hsm__hsm under gpt-5.6-terra, cktevo_hsm__hsm under gpt-5.6-luna, drrtl_LSTM under gpt-5.6-terra, drrtl_tv80 under gpt-5.6-terra.

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 47, 'b': 138, 'c1': 40, 'd': 12}; requested → produced a->a: 6, a->b: 11, a->c1: 3, b->a: 6, b->b: 16, c1->a: 8, c1->b: 20, c1->c1: 19, d->a: 21, d->b: 70, d->c1: 14, d->d: 12, free->a: 6, free->b: 21, free->c1: 4
- large / gpt-5.6-terra / B0: produced {'a': 85, 'b': 307, 'c1': 35, 'd': 38}; requested → produced a->a: 17, a->b: 62, a->c1: 3, a->d: 2, b->a: 18, b->b: 36, b->d: 3, c1->a: 13, c1->b: 46, c1->c1: 19, c1->d: 6, d->a: 14, d->b: 86, d->c1: 5, d->d: 12, free->a: 23, free->b: 77, free->c1: 8, free->d: 15
- large / gpt-5.6-terra / B1_E4: produced {'a': 162, 'b': 275, 'c1': 23, 'd': 53}; requested → produced a->a: 21, a->b: 71, a->c1: 3, a->d: 7, b->a: 53, b->b: 33, b->c1: 1, b->d: 19, c1->a: 26, c1->b: 54, c1->c1: 2, c1->d: 4, d->a: 29, d->b: 55, d->c1: 8, d->d: 6, free->a: 33, free->b: 62, free->c1: 9, free->d: 17
- large / gpt-5.6-terra / B2: produced {'a': 115, 'b': 293, 'c1': 29, 'd': 40}; requested → produced a->a: 27, a->b: 54, a->c1: 4, a->d: 1, b->a: 25, b->b: 43, b->d: 5, c1->a: 28, c1->b: 51, c1->c1: 6, c1->d: 3, d->a: 22, d->b: 86, d->c1: 10, d->d: 14, free->a: 13, free->b: 59, free->c1: 9, free->d: 17
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 165, 'b': 205, 'c1': 3, 'free': 2}; requested → produced free->a: 165, free->b: 205, free->c1: 3, free->free: 2
- large / gpt-5.6-terra / M: produced {'b': 167, 'c1': 12, 'd': 1}; requested → produced a->b: 16, a->c1: 1, b->b: 14, c1->b: 38, c1->c1: 7, d->b: 87, d->c1: 3, d->d: 1, free->b: 12, free->c1: 1

## 7. Runs and anomalies

Runs on the reported tiers: 108 (11 done, 28 running, 68 not started). Abnormal statuses: r20260915_214859_keNeuron8_H7_B0_-terra_s1 failed.

