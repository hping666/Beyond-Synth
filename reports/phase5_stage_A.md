# Phase 5 report (Stage A — the large tier)

Generated 2026-09-16T04:57 by scripts/report_phase.py phase5 --stage A (git 1d905dbd749d, cfg 47f7ba4d337d). Data: reports/data/phase5_visible_A.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 0 / 18 / 18 | 206 | 0.90 | 0.0 | 0.1 |
| large | gpt-5.6-terra | B0 | 0 / 18 / 18 | 317 | 12.15 | 0.0 | 41.5 |
| large | gpt-5.6-terra | B1_E4 | 0 / 18 / 18 | 346 | 14.23 | 3.8 | 39.1 |
| large | gpt-5.6-terra | B2 | 0 / 18 / 18 | 330 | 12.80 | 1.1 | 21.4 |
| large | gpt-5.6-terra | DrRTL_reimpl | 0 / 18 / 18 | 349 | 11.49 | 2.2 | 19.1 |
| large | gpt-5.6-terra | M | 0 / 18 / 18 | 140 | 6.37 | 0.0 | 10.2 |

Unfinished groups: 6 of 6 — the numbers below are interim for those groups (runs still open, verdicts and fitness evaluations pending).

## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)

### large tier

| model (role) | arm | runs | candidates | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (contrast) | M | 0/18 | 206 | 0 | 0 (0.000) | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 0.90 | 0.0 | 0.1 |
| gpt-5.6-terra (main) | B0 | 0/18 | 322 | 0 | 17 (0.054) | 44 | 0 | 9 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 12.15 | 0.0 | 41.5 |
| gpt-5.6-terra (main) | B1_E4 | 0/18 | 346 | 0 | 39 (0.113) | 40 | 0 | 27 | 3 | 0.17 | 2 | 0.14 % / 0.00 % | 0.87 | 0.21 | 0.80 | 14.23 | 3.8 | 39.1 |
| gpt-5.6-terra (main) | B2 | 0/18 | 330 | 0 | 8 (0.024) | 42 | 0 | 4 | 3 | 0.17 | 1 | 0.03 % / 0.00 % | 0.91 | 0.23 | 2.74 | 12.80 | 1.1 | 21.4 |
| gpt-5.6-terra (main) | DrRTL_reimpl | 0/18 | 300 | 3 | 17 (0.049) | 34 | 0 | 7 | 2 | 0.11 | 1 | 0.01 % / 0.00 % | 0.57 | 0.17 | 0.90 | 11.49 | 2.2 | 19.1 |
| gpt-5.6-terra (main) | M | 0/18 | 140 | 0 | 0 (0.000) | 20 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 6.37 | 0.0 | 10.2 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | M | 67 | 1 | 27 | 0 | 0 | 91 | 0 | 20 | - | nonequiv: 95 | 206 (no block-level answers) | 60 (0) | 7181 / 14976 |
| gpt-5.6-terra | B0 | 55 | 1 | 16 | 44 | 1 | 180 | 8 | 0 | - | improved: 12, no_gain: 5, nonequiv: 117 | 304 (no block-level answers) | 45 (2) | 6455 / 13717 |
| gpt-5.6-terra | B1_E4 | 49 | 3 | 15 | 40 | 0 | 183 | 17 | 0 | absorbed_identical: 7, harmful: 24, noise: 2, retained: 3, tradeoff: 3 | improved: 29, no_gain: 10, nonequiv: 107 | 313 (no block-level answers) | 41 (1) | 6907 / 12808 |
| gpt-5.6-terra | B2 | 70 | 3 | 15 | 42 | 0 | 191 | 1 | 0 | harmful: 3, noise: 2, retained: 3 | improved: 5, no_gain: 3, nonequiv: 130 | 315 (no block-level answers) | 64 (0) | 8163 / 14738 |
| gpt-5.6-terra | DrRTL_reimpl | 38 | 2 | 14 | 34 | 0 | 162 | 33 | 0 | harmful: 7, noise: 7, retained: 2 | improved: 9, no_gain: 7, nonequiv: 88 | 255 (no block-level answers) | 39 (0) | 8323 / 15072 |
| gpt-5.6-terra | M | 39 | 0 | 5 | 20 | 0 | 76 | 0 | 0 | - | nonequiv: 64 | 135 (no block-level answers) | 29 (0) | 6421 / 14752 |

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

- **large / M**: gpt-5.6-luna (contrast): proven 0.000 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 0.90; gpt-5.6-terra (main): proven 0.000 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 6.37

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
- gpt-5.6-terra / B2: 0.25 h → 0.03 %, 0.50 h → 0.03 %, 0.75 h → 0.03 %, 1.00 h → 0.03 %
- gpt-5.6-terra / DrRTL_reimpl: 0.25 h → 0.00 %, 0.50 h → 0.01 %, 0.75 h → 0.01 %, 1.00 h → 0.01 %, 1.25 h → 0.01 %

## 5. Correctness (the LLM's equivalence-preserving rate)

| tier | model | design | runs | candidates | proven | proven rate |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | cktevo_hsm__hsm | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_hsm__hsm | 15 | 724 | 0 | 0.0 % |
| large | gpt-5.6-luna | cktevo_nn_engine__spikeNeuron8_H7 | 3 | 26 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_nn_engine__spikeNeuron8_H7 | 15 | 190 | 36 | 18.9 % |
| large | gpt-5.6-luna | cktevo_risc__btb | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | cktevo_risc__btb | 15 | 128 | 27 | 21.1 % |
| large | gpt-5.6-luna | drrtl_LSTM | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_LSTM | 15 | 160 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_aes | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_aes | 15 | 92 | 18 | 19.6 % |
| large | gpt-5.6-luna | drrtl_tv80 | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_tv80 | 15 | 144 | 0 | 0.0 % |

LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): cktevo_hsm__hsm under gpt-5.6-terra, cktevo_hsm__hsm under gpt-5.6-luna, drrtl_LSTM under gpt-5.6-terra, drrtl_tv80 under gpt-5.6-terra.

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 22, 'b': 138, 'c1': 36, 'd': 10}; requested → produced a->a: 6, a->b: 11, a->c1: 3, b->a: 2, b->b: 15, c1->a: 4, c1->b: 21, c1->c1: 19, d->a: 10, d->b: 70, d->c1: 12, d->d: 10, free->b: 21, free->c1: 2
- large / gpt-5.6-terra / B0: produced {'a': 52, 'b': 225, 'c1': 24, 'd': 13}; requested → produced a->a: 15, a->b: 49, a->c1: 3, b->a: 13, b->b: 26, b->d: 1, c1->a: 6, c1->b: 34, c1->c1: 16, c1->d: 4, d->a: 7, d->b: 66, d->c1: 3, d->d: 4, free->a: 11, free->b: 50, free->c1: 2, free->d: 4
- large / gpt-5.6-terra / B1_E4: produced {'a': 107, 'b': 191, 'c1': 16, 'd': 15}; requested → produced a->a: 15, a->b: 48, a->c1: 3, a->d: 2, b->a: 36, b->b: 20, b->d: 2, c1->a: 15, c1->b: 37, c1->c1: 2, c1->d: 1, d->a: 21, d->b: 42, d->c1: 7, d->d: 4, free->a: 20, free->b: 44, free->c1: 4, free->d: 6
- large / gpt-5.6-terra / B2: produced {'a': 65, 'b': 241, 'c1': 17, 'd': 6}; requested → produced a->a: 18, a->b: 47, a->c1: 4, b->a: 11, b->b: 39, c1->a: 21, c1->b: 46, c1->c1: 3, c1->d: 1, d->a: 8, d->b: 68, d->c1: 5, d->d: 4, free->a: 7, free->b: 41, free->c1: 5, free->d: 1
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 115, 'b': 148, 'c1': 3, 'free': 1}; requested → produced free->a: 115, free->b: 148, free->c1: 3, free->free: 1
- large / gpt-5.6-terra / M: produced {'b': 129, 'c1': 11}; requested → produced a->b: 15, b->b: 8, c1->b: 27, c1->c1: 7, d->b: 71, d->c1: 3, free->b: 8, free->c1: 1

## 7. Runs and anomalies

Runs on the reported tiers: 108 (0 done, 39 running, 68 not started). Abnormal statuses: r20260915_214859_keNeuron8_H7_B0_-terra_s1 failed.

