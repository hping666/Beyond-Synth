# Phase 5 report (Stage A — the large tier)

Generated 2026-09-16T01:57 by scripts/report_phase.py phase5 --stage A (git 9c4d20ef6b1a, cfg 66d90ba3fa0a). Data: reports/data/phase5_visible_A.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 0 / 18 / 18 | 139 | 0.62 | 0.0 | 0.0 |
| large | gpt-5.6-terra | B0 | 0 / 18 / 18 | 181 | 8.15 | 0.0 | 27.7 |
| large | gpt-5.6-terra | B1_E4 | 0 / 18 / 18 | 179 | 8.54 | 1.2 | 23.9 |
| large | gpt-5.6-terra | B2 | 0 / 18 / 18 | 169 | 7.31 | 0.0 | 10.2 |
| large | gpt-5.6-terra | DrRTL_reimpl | 0 / 18 / 18 | 150 | 6.01 | 0.0 | 11.0 |
| large | gpt-5.6-terra | M | 0 / 18 / 18 | 104 | 4.66 | 0.0 | 9.4 |

Unfinished groups: 6 of 6 — the numbers below are interim for those groups (runs still open, verdicts and fitness evaluations pending).

## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)

### large tier

| model (role) | arm | runs | candidates | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (contrast) | M | 0/18 | 139 | 0 | 0 (0.000) | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 0.62 | 0.0 | 0.0 |
| gpt-5.6-terra (main) | B0 | 0/18 | 181 | 0 | 2 (0.011) | 31 | 0 | 2 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 8.15 | 0.0 | 27.7 |
| gpt-5.6-terra (main) | B1_E4 | 0/18 | 182 | 0 | 20 (0.112) | 24 | 0 | 15 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | 0.00 | 8.54 | 1.2 | 23.9 |
| gpt-5.6-terra (main) | B2 | 0/18 | 170 | 0 | 0 (0.000) | 16 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 7.31 | 0.0 | 10.2 |
| gpt-5.6-terra (main) | DrRTL_reimpl | 0/18 | 134 | 2 | 0 (0.000) | 13 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 6.01 | 0.0 | 11.0 |
| gpt-5.6-terra (main) | M | 0/18 | 104 | 0 | 0 (0.000) | 11 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 4.66 | 0.0 | 9.4 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | M | 37 | 0 | 20 | 0 | 0 | 76 | 0 | 6 | - | nonequiv: 57 | 139 (no block-level answers) | 44 (0) | 6312 / 7437 |
| gpt-5.6-terra | B0 | 36 | 1 | 5 | 31 | 1 | 105 | 0 | 0 | - | improved: 2, nonequiv: 74 | 181 (no block-level answers) | 36 (2) | 3414 / 7890 |
| gpt-5.6-terra | B1_E4 | 22 | 0 | 3 | 24 | 0 | 103 | 10 | 0 | absorbed_identical: 5, harmful: 15 | improved: 15, no_gain: 5, nonequiv: 49 | 172 (no block-level answers) | 24 (0) | 3141 / 8488 |
| gpt-5.6-terra | B2 | 45 | 0 | 2 | 16 | 0 | 107 | 0 | 0 | - | nonequiv: 63 | 170 (no block-level answers) | 39 (0) | 5004 / 8552 |
| gpt-5.6-terra | DrRTL_reimpl | 26 | 0 | 2 | 13 | 0 | 93 | 0 | 0 | - | nonequiv: 41 | 134 (no block-level answers) | 27 (0) | 6462 / 8799 |
| gpt-5.6-terra | M | 26 | 0 | 3 | 11 | 0 | 64 | 0 | 0 | - | nonequiv: 40 | 104 (no block-level answers) | 24 (0) | 5318 / 8516 |

## 2. Best retained area gain per design (max over seeds; uniform rule A; '-' = no retained candidate; 0 = runs without one)

### large tier

| design | B0 (terra) | B1_E4 (terra) | B2 (terra) | DrRTL_reimpl (terra) | M (luna) | M (terra) |
|---|---|---|---|---|---|---|
| cktevo_hsm__hsm | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_nn_engine__spikeNeuron8_H7 | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_risc__btb | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_LSTM | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_aes | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_tv80 | 0 | 0 | 0 | 0 | 0 | 0 |

## 3. Model contrast (the same arm under two models on the same tier)

- **large / M**: gpt-5.6-luna (contrast): proven 0.000 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 0.62; gpt-5.6-terra (main): proven 0.000 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 4.66

## 4. Retained-gain curves (mean over the group's runs of the best retained area gain so far)

### large tier — by LLM calls (equal-call caliber)

| model | arm | 5 calls | 10 calls | 20 calls | 30 calls | 40 calls | 50 calls | 60 calls |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | B1_E4 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | B2 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | DrRTL_reimpl | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-luna | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |

### large tier — by visible DC hours per run

- gpt-5.6-terra / B1_E4: 0.25 h → 0.00 %, 0.50 h → 0.00 %, 0.75 h → 0.00 %, 1.00 h → 0.00 %, 1.25 h → 0.00 %

## 5. Correctness (the LLM's equivalence-preserving rate)

| tier | model | design | runs | candidates | proven | proven rate |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | cktevo_hsm__hsm | 3 | 134 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_hsm__hsm | 15 | 579 | 0 | 0.0 % |
| large | gpt-5.6-luna | cktevo_nn_engine__spikeNeuron8_H7 | 3 | 5 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_nn_engine__spikeNeuron8_H7 | 15 | 112 | 22 | 19.6 % |
| large | gpt-5.6-luna | cktevo_risc__btb | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | cktevo_risc__btb | 15 | 20 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_LSTM | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_LSTM | 15 | 20 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_aes | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_aes | 15 | 20 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_tv80 | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_tv80 | 15 | 20 | 0 | 0.0 % |

LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): cktevo_hsm__hsm under gpt-5.6-terra, cktevo_hsm__hsm under gpt-5.6-luna.

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 7, 'b': 97, 'c1': 26, 'd': 9}; requested → produced a->a: 3, a->b: 7, a->c1: 2, b->b: 14, c1->b: 16, c1->c1: 18, d->a: 4, d->b: 48, d->c1: 6, d->d: 9, free->b: 12
- large / gpt-5.6-terra / B0: produced {'a': 13, 'b': 148, 'c1': 15, 'd': 5}; requested → produced a->a: 2, a->b: 26, a->c1: 3, b->a: 5, b->b: 12, c1->a: 1, c1->b: 29, c1->c1: 10, c1->d: 1, d->a: 1, d->b: 49, d->c1: 2, d->d: 2, free->a: 4, free->b: 32, free->d: 2
- large / gpt-5.6-terra / B1_E4: produced {'a': 44, 'b': 111, 'c1': 9, 'd': 8}; requested → produced a->a: 3, a->b: 29, a->c1: 2, a->d: 2, b->a: 19, b->b: 6, b->d: 1, c1->a: 5, c1->b: 26, c1->c1: 1, d->a: 8, d->b: 24, d->c1: 5, d->d: 1, free->a: 9, free->b: 26, free->c1: 1, free->d: 4
- large / gpt-5.6-terra / B2: produced {'a': 12, 'b': 148, 'c1': 8, 'd': 2}; requested → produced a->a: 5, a->b: 27, a->c1: 2, b->a: 1, b->b: 19, c1->a: 4, c1->b: 36, c1->c1: 1, c1->d: 1, d->b: 41, d->c1: 4, d->d: 1, free->a: 2, free->b: 25, free->c1: 1
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 21, 'b': 109, 'c1': 3, 'free': 1}; requested → produced free->a: 21, free->b: 109, free->c1: 3, free->free: 1
- large / gpt-5.6-terra / M: produced {'b': 95, 'c1': 9}; requested → produced a->b: 11, b->b: 5, c1->b: 18, c1->c1: 6, d->b: 55, d->c1: 2, free->b: 6, free->c1: 1

## 7. Runs and anomalies

Runs on the reported tiers: 108 (0 done, 40 running, 68 not started). No run in an abnormal status.

