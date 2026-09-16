# Phase 5 report (Stage A — the large tier)

Generated 2026-09-16T07:58 by scripts/report_phase.py phase5 --stage A (git 29aa0e2b95cd, cfg b326eaa98549). Data: reports/data/phase5_visible_A.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 0 / 18 / 18 | 234 | 1.04 | 0.2 | 0.4 |
| large | gpt-5.6-terra | B0 | 0 / 18 / 18 | 459 | 16.37 | 0.0 | 61.1 |
| large | gpt-5.6-terra | B1_E4 | 1 / 18 / 18 | 505 | 21.07 | 6.0 | 56.4 |
| large | gpt-5.6-terra | B2 | 0 / 18 / 18 | 464 | 17.00 | 3.2 | 34.4 |
| large | gpt-5.6-terra | DrRTL_reimpl | 0 / 18 / 18 | 480 | 17.34 | 6.3 | 30.4 |
| large | gpt-5.6-terra | M | 0 / 18 / 18 | 166 | 7.54 | 0.0 | 10.2 |

Unfinished groups: 6 of 6 — the numbers below are interim for those groups (runs still open, verdicts and fitness evaluations pending).

## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)

### large tier

| model (role) | arm | runs | candidates | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (contrast) | M | 0/18 | 234 | 0 | 1 (0.004) | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | 0.00 | 1.04 | 0.2 | 0.4 |
| gpt-5.6-terra (main) | B0 | 0/18 | 459 | 0 | 37 (0.081) | 62 | 0 | 12 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 16.37 | 0.0 | 61.1 |
| gpt-5.6-terra (main) | B1_E4 | 1/18 | 510 | 0 | 61 (0.121) | 71 | 0 | 36 | 9 | 0.50 | 2 | 0.14 % / 0.00 % | 1.78 | 0.43 | 1.50 | 21.07 | 6.0 | 56.4 |
| gpt-5.6-terra (main) | B2 | 0/18 | 464 | 0 | 23 (0.050) | 66 | 0 | 9 | 4 | 0.22 | 1 | 0.03 % / 0.00 % | 0.86 | 0.23 | 1.26 | 17.00 | 3.2 | 34.4 |
| gpt-5.6-terra (main) | DrRTL_reimpl | 0/18 | 408 | 3 | 52 (0.108) | 57 | 0 | 23 | 3 | 0.17 | 1 | 0.01 % / 0.00 % | 0.62 | 0.17 | 0.48 | 17.34 | 6.3 | 30.4 |
| gpt-5.6-terra (main) | M | 0/18 | 166 | 0 | 0 (0.000) | 31 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 7.54 | 0.0 | 10.2 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | M | 96 | 2 | 38 | 0 | 0 | 60 | 1 | 36 | harmful: 1 | harmful: 1, nonequiv: 136 | 233 (no block-level answers) | 63 (0) | 11424 / 21686 |
| gpt-5.6-terra | B0 | 79 | 1 | 37 | 62 | 1 | 231 | 11 | 0 | - | improved: 26, no_gain: 11, nonequiv: 180 | 375 (no block-level answers) | 59 (2) | 9418 / 18704 |
| gpt-5.6-terra | B1_E4 | 63 | 5 | 36 | 71 | 1 | 246 | 27 | 0 | absorbed_identical: 12, harmful: 29, noise: 4, retained: 9, tradeoff: 4 | improved: 40, no_gain: 18, nonequiv: 176 | 383 (no block-level answers) | 51 (2) | 9673 / 19554 |
| gpt-5.6-terra | B2 | 104 | 8 | 36 | 66 | 0 | 224 | 3 | 0 | absorbed_identical: 3, harmful: 7, noise: 6, retained: 4, tradeoff: 3 | improved: 12, no_gain: 11, nonequiv: 214 | 387 (no block-level answers) | 81 (0) | 10388 / 20194 |
| gpt-5.6-terra | DrRTL_reimpl | 54 | 5 | 34 | 57 | 1 | 172 | 33 | 0 | absorbed: 1, harmful: 24, noise: 15, retained: 3 | improved: 27, no_gain: 16, nonequiv: 151 | 308 (no block-level answers) | 49 (0) | 11085 / 19377 |
| gpt-5.6-terra | M | 57 | 0 | 7 | 31 | 0 | 71 | 0 | 0 | - | nonequiv: 95 | 135 (no block-level answers) | 30 (0) | 11840 / 21856 |

## 2. Best retained area gain per design (max over seeds; uniform rule A; '-' = no retained candidate; 0 = runs without one)

### large tier

| design | B0 (terra) | B1_E4 (terra) | B2 (terra) | DrRTL_reimpl (terra) | M (luna) | M (terra) |
|---|---|---|---|---|---|---|
| cktevo_hsm__hsm | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_nn_engine__spikeNeuron8_H7 | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_risc__btb | 0 | 1.76 % | 0.60 % | 0.25 % | 0 | 0 |
| drrtl_LSTM | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_aes | 0 | 0.72 % | 0 | 0 | 0 | 0 |
| drrtl_tv80 | 0 | 0 | 0 | 0 | 0 | 0 |

## 3. Model contrast (the same arm under two models on the same tier)

- **large / M**: gpt-5.6-luna (contrast): proven 0.004 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 1.04; gpt-5.6-terra (main): proven 0.000 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 7.54

## 4. Retained-gain curves (mean over the group's runs of the best retained area gain so far)

### large tier — by LLM calls (equal-call caliber)

| model | arm | 5 calls | 10 calls | 20 calls | 30 calls | 40 calls | 50 calls | 60 calls |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | B1_E4 | 0.04 % | 0.14 % | 0.14 % | 0.14 % | 0.14 % | 0.14 % | 0.14 % |
| gpt-5.6-terra | B2 | 0.03 % | 0.03 % | 0.03 % | 0.03 % | 0.03 % | 0.03 % | 0.03 % |
| gpt-5.6-terra | DrRTL_reimpl | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % |
| gpt-5.6-luna | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |

### large tier — by visible DC hours per run

- gpt-5.6-terra / B1_E4: 0.25 h → 0.00 %, 0.50 h → 0.10 %, 0.75 h → 0.14 %, 1.00 h → 0.14 %, 1.25 h → 0.14 %, 1.50 h → 0.14 %, 1.75 h → 0.14 %
- gpt-5.6-terra / B2: 0.25 h → 0.03 %, 0.50 h → 0.03 %, 0.75 h → 0.03 %, 1.00 h → 0.03 %, 1.25 h → 0.03 %, 1.50 h → 0.03 %, 1.75 h → 0.03 %
- gpt-5.6-terra / DrRTL_reimpl: 0.25 h → 0.00 %, 0.75 h → 0.01 %, 1.25 h → 0.01 %, 1.75 h → 0.01 %, 2.25 h → 0.01 %, 2.75 h → 0.01 %, 3.25 h → 0.01 %
- gpt-5.6-luna / M: 0.25 h → 0.00 %

## 5. Correctness (the LLM's equivalence-preserving rate)

| tier | model | design | runs | candidates | proven | proven rate |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | cktevo_hsm__hsm | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_hsm__hsm | 15 | 836 | 0 | 0.0 % |
| large | gpt-5.6-luna | cktevo_nn_engine__spikeNeuron8_H7 | 3 | 54 | 2 | 3.7 % |
| large | gpt-5.6-terra | cktevo_nn_engine__spikeNeuron8_H7 | 15 | 266 | 69 | 25.9 % |
| large | gpt-5.6-luna | cktevo_risc__btb | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | cktevo_risc__btb | 15 | 230 | 58 | 25.2 % |
| large | gpt-5.6-luna | drrtl_LSTM | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_LSTM | 15 | 233 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_aes | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_aes | 15 | 212 | 46 | 21.7 % |
| large | gpt-5.6-luna | drrtl_tv80 | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_tv80 | 15 | 230 | 0 | 0.0 % |

LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): cktevo_hsm__hsm under gpt-5.6-terra, cktevo_hsm__hsm under gpt-5.6-luna, cktevo_nn_engine__spikeNeuron8_H7 under gpt-5.6-luna, drrtl_LSTM under gpt-5.6-terra, drrtl_tv80 under gpt-5.6-terra.

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 41, 'b': 140, 'c1': 40, 'd': 12}; requested → produced a->a: 6, a->b: 11, a->c1: 3, b->a: 6, b->b: 16, c1->a: 7, c1->b: 22, c1->c1: 19, d->a: 17, d->b: 70, d->c1: 14, d->d: 12, free->a: 5, free->b: 21, free->c1: 4
- large / gpt-5.6-terra / B0: produced {'a': 84, 'b': 296, 'c1': 35, 'd': 33}; requested → produced a->a: 17, a->b: 60, a->c1: 3, a->d: 1, b->a: 18, b->b: 35, b->d: 2, c1->a: 13, c1->b: 44, c1->c1: 19, c1->d: 6, d->a: 14, d->b: 85, d->c1: 5, d->d: 10, free->a: 22, free->b: 72, free->c1: 8, free->d: 14
- large / gpt-5.6-terra / B1_E4: produced {'a': 155, 'b': 260, 'c1': 22, 'd': 46}; requested → produced a->a: 20, a->b: 68, a->c1: 3, a->d: 7, b->a: 49, b->b: 30, b->c1: 1, b->d: 15, c1->a: 26, c1->b: 50, c1->c1: 2, c1->d: 4, d->a: 29, d->b: 54, d->c1: 8, d->d: 6, free->a: 31, free->b: 58, free->c1: 8, free->d: 14
- large / gpt-5.6-terra / B2: produced {'a': 106, 'b': 293, 'c1': 26, 'd': 36}; requested → produced a->a: 26, a->b: 54, a->c1: 4, a->d: 1, b->a: 21, b->b: 43, b->d: 5, c1->a: 28, c1->b: 51, c1->c1: 6, c1->d: 2, d->a: 19, d->b: 86, d->c1: 8, d->d: 14, free->a: 12, free->b: 59, free->c1: 8, free->d: 14
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 165, 'b': 205, 'c1': 3, 'free': 2}; requested → produced free->a: 165, free->b: 205, free->c1: 3, free->free: 2
- large / gpt-5.6-terra / M: produced {'b': 153, 'c1': 12, 'd': 1}; requested → produced a->b: 15, a->c1: 1, b->b: 14, c1->b: 32, c1->c1: 7, d->b: 82, d->c1: 3, d->d: 1, free->b: 10, free->c1: 1

## 7. Runs and anomalies

Runs on the reported tiers: 108 (1 done, 38 running, 68 not started). Abnormal statuses: r20260915_214859_keNeuron8_H7_B0_-terra_s1 failed.

