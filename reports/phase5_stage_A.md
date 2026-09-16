# Phase 5 report (Stage A — the large tier)

Generated 2026-09-16T16:09 by scripts/report_phase.py phase5 --stage A (git 883932a1ce8d, cfg 8aa246ed60b7). Data: reports/data/phase5_visible_A.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 5 / 18 / 18 | 360 | 1.31 | 2.9 | 11.5 |
| large | gpt-5.6-terra | B0 | 6 / 18 / 18 | 606 | 20.03 | 0.0 | 137.6 |
| large | gpt-5.6-terra | B1_E4 | 7 / 18 / 18 | 540 | 22.71 | 14.2 | 116.4 |
| large | gpt-5.6-terra | B2 | 7 / 18 / 18 | 496 | 18.81 | 12.1 | 153.5 |
| large | gpt-5.6-terra | DrRTL_reimpl | 8 / 18 / 18 | 480 | 17.39 | 14.8 | 123.2 |
| large | gpt-5.6-terra | M | 4 / 18 / 18 | 314 | 11.86 | 2.3 | 50.3 |

Unfinished groups: 6 of 6 — the numbers below are interim for those groups (runs still open, verdicts and fitness evaluations pending).

## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)

### large tier

| model (role) | arm | runs | candidates | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (contrast) | M | 5/18 | 359 | 1 | 12 (0.033) | 8 | 0 | 5 | 5 | 0.28 | 1 | 0.09 % / 0.00 % | 1.39 | 3.83 | 1.74 | 1.31 | 2.9 | 11.5 |
| gpt-5.6-terra (main) | B0 | 6/18 | 606 | 0 | 96 (0.158) | 150 | 0 | 26 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 20.03 | 0.0 | 137.6 |
| gpt-5.6-terra (main) | B1_E4 | 7/18 | 540 | 0 | 130 (0.241) | 133 | 0 | 76 | 25 | 1.39 | 2 | 0.17 % / 0.00 % | 4.63 | 1.10 | 1.76 | 22.71 | 14.2 | 116.4 |
| gpt-5.6-terra (main) | B2 | 7/18 | 496 | 0 | 99 (0.200) | 138 | 0 | 24 | 17 | 0.94 | 1 | 0.10 % / 0.00 % | 3.43 | 0.90 | 1.41 | 18.81 | 12.1 | 153.5 |
| gpt-5.6-terra (main) | DrRTL_reimpl | 8/18 | 408 | 3 | 122 (0.254) | 95 | 0 | 42 | 9 | 0.50 | 1 | 0.01 % / 0.00 % | 1.88 | 0.52 | 0.61 | 17.39 | 14.8 | 123.2 |
| gpt-5.6-terra (main) | M | 4/18 | 314 | 0 | 9 (0.029) | 57 | 0 | 5 | 5 | 0.28 | 1 | 0.10 % / 0.00 % | 1.59 | 0.42 | 2.17 | 11.86 | 2.3 | 50.3 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | M | 141 | 13 | 58 | 8 | 0 | 20 | 8 | 99 | absorbed_identical: 2, harmful: 4, retained: 5, tradeoff: 1 | absorbed_identical: 2, harmful: 4, nonequiv: 220, retained: 5, tradeoff: 1 | 235 (no block-level answers) | 82 (5) | 12917 / 28644 |
| gpt-5.6-terra | B0 | 144 | 16 | 130 | 150 | 2 | 55 | 13 | 0 | - | improved: 78, no_gain: 18, nonequiv: 444 | 375 (no block-level answers) | 94 (5) | 13225 / 32277 |
| gpt-5.6-terra | B1_E4 | 142 | 13 | 71 | 133 | 1 | 23 | 27 | 0 | absorbed: 1, absorbed_identical: 14, harmful: 59, noise: 8, retained: 25, tradeoff: 14 | improved: 100, no_gain: 21, nonequiv: 360 | 383 (no block-level answers) | 54 (7) | 15057 / 28812 |
| gpt-5.6-terra | B2 | 151 | 16 | 69 | 138 | 0 | 19 | 4 | 0 | absorbed_identical: 25, harmful: 27, noise: 12, retained: 17, tradeoff: 8 | improved: 42, no_gain: 47, nonequiv: 374 | 387 (no block-level answers) | 82 (11) | 15334 / 27345 |
| gpt-5.6-terra | DrRTL_reimpl | 91 | 5 | 61 | 95 | 1 | 0 | 33 | 0 | absorbed: 2, absorbed_identical: 1, harmful: 58, noise: 33, retained: 9, tradeoff: 1 | improved: 52, no_gain: 52, nonequiv: 253 | 308 (no block-level answers) | 49 (5) | 15262 / 27246 |
| gpt-5.6-terra | M | 126 | 9 | 21 | 57 | 0 | 30 | 3 | 59 | retained: 5, tradeoff: 4 | nonequiv: 213, retained: 5, tradeoff: 4 | 135 (no block-level answers) | 51 (1) | 17180 / 28279 |

## 2. Best retained area gain per design (max over seeds; uniform rule A; '-' = no retained candidate; 0 = runs without one)

### large tier

| design | B0 (terra) | B1_E4 (terra) | B2 (terra) | DrRTL_reimpl (terra) | M (luna) | M (terra) |
|---|---|---|---|---|---|---|
| cktevo_hsm__hsm | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_nn_engine__spikeNeuron8_H7 | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_risc__btb | 0 | 2.36 % | 1.76 % | 0.25 % | 1.57 % | 1.89 % |
| drrtl_LSTM | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_aes | 0 | 0.76 % | 0 | 0 | 0 | 0 |
| drrtl_tv80 | 0 | 0 | 0 | 0 | 0 | 0 |

## 3. Model contrast (the same arm under two models on the same tier)

- **large / M**: gpt-5.6-luna (contrast): proven 0.033 / call, retained 0.28 / run, best gain mean 0.09 %, unusable 1, USD 1.31; gpt-5.6-terra (main): proven 0.029 / call, retained 0.28 / run, best gain mean 0.10 %, unusable 0, USD 11.86

## 4. Retained-gain curves (mean over the group's runs of the best retained area gain so far)

### large tier — by LLM calls (equal-call caliber)

| model | arm | 5 calls | 10 calls | 20 calls | 30 calls | 40 calls | 50 calls | 60 calls |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | B1_E4 | 0.04 % | 0.14 % | 0.14 % | 0.14 % | 0.15 % | 0.15 % | 0.17 % |
| gpt-5.6-terra | B2 | 0.03 % | 0.03 % | 0.03 % | 0.09 % | 0.10 % | 0.10 % | 0.10 % |
| gpt-5.6-terra | DrRTL_reimpl | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % | 0.01 % |
| gpt-5.6-luna | M | 0.02 % | 0.02 % | 0.09 % | 0.09 % | 0.09 % | 0.09 % | 0.09 % |
| gpt-5.6-terra | M | 0.04 % | 0.10 % | 0.10 % | 0.10 % | 0.10 % | 0.10 % | 0.10 % |

### large tier — by visible DC hours per run

- gpt-5.6-terra / B1_E4: 0.25 h → 0.00 %, 1.00 h → 0.14 %, 1.75 h → 0.14 %, 2.50 h → 0.15 %, 3.25 h → 0.15 %, 4.00 h → 0.17 %, 4.75 h → 0.17 %
- gpt-5.6-terra / B2: 0.25 h → 0.03 %, 0.75 h → 0.03 %, 1.25 h → 0.08 %, 1.75 h → 0.10 %, 2.25 h → 0.10 %, 2.75 h → 0.10 %, 3.25 h → 0.10 %
- gpt-5.6-terra / DrRTL_reimpl: 0.25 h → 0.00 %, 1.25 h → 0.01 %, 2.25 h → 0.01 %, 3.25 h → 0.01 %, 4.25 h → 0.01 %, 5.25 h → 0.01 %, 6.25 h → 0.01 %
- gpt-5.6-luna / M: 0.25 h → 0.02 %, 0.50 h → 0.09 %, 0.75 h → 0.09 %
- gpt-5.6-terra / M: 0.25 h → 0.04 %, 0.50 h → 0.10 %, 0.75 h → 0.10 %

## 5. Correctness (the LLM's equivalence-preserving rate)

| tier | model | design | runs | candidates | proven | proven rate |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | cktevo_hsm__hsm | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_hsm__hsm | 15 | 875 | 0 | 0.0 % |
| large | gpt-5.6-luna | cktevo_nn_engine__spikeNeuron8_H7 | 3 | 60 | 8 | 13.3 % |
| large | gpt-5.6-terra | cktevo_nn_engine__spikeNeuron8_H7 | 15 | 339 | 142 | 41.9 % |
| large | gpt-5.6-luna | cktevo_risc__btb | 3 | 22 | 11 | 50.0 % |
| large | gpt-5.6-terra | cktevo_risc__btb | 15 | 269 | 183 | 68.0 % |
| large | gpt-5.6-luna | drrtl_LSTM | 3 | 60 | 0 | 0.0 % |
| large | gpt-5.6-terra | drrtl_LSTM | 15 | 353 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_aes | 3 | 20 | 0 | 0.0 % |
| large | gpt-5.6-terra | drrtl_aes | 15 | 263 | 131 | 49.8 % |
| large | gpt-5.6-luna | drrtl_tv80 | 3 | 17 | 0 | 0.0 % |
| large | gpt-5.6-terra | drrtl_tv80 | 15 | 265 | 0 | 0.0 % |

LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): cktevo_hsm__hsm under gpt-5.6-terra, cktevo_hsm__hsm under gpt-5.6-luna, drrtl_LSTM under gpt-5.6-terra, drrtl_LSTM under gpt-5.6-luna, drrtl_tv80 under gpt-5.6-terra.

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 118, 'b': 175, 'c1': 44, 'd': 14}; requested → produced a->a: 7, a->b: 14, a->c1: 3, b->a: 23, b->b: 17, b->c1: 1, c1->a: 27, c1->b: 32, c1->c1: 21, c1->d: 1, d->a: 54, d->b: 89, d->c1: 15, d->d: 13, free->a: 7, free->b: 23, free->c1: 4
- large / gpt-5.6-terra / B0: produced {'a': 154, 'b': 350, 'c1': 40, 'd': 49}; requested → produced a->a: 24, a->b: 68, a->c1: 3, a->d: 2, b->a: 31, b->b: 42, b->d: 3, c1->a: 31, c1->b: 51, c1->c1: 22, c1->d: 7, d->a: 31, d->b: 104, d->c1: 6, d->d: 19, free->a: 37, free->b: 85, free->c1: 9, free->d: 18
- large / gpt-5.6-terra / B1_E4: produced {'a': 162, 'b': 275, 'c1': 23, 'd': 53}; requested → produced a->a: 21, a->b: 71, a->c1: 3, a->d: 7, b->a: 53, b->b: 33, b->c1: 1, b->d: 19, c1->a: 26, c1->b: 54, c1->c1: 2, c1->d: 4, d->a: 29, d->b: 55, d->c1: 8, d->d: 6, free->a: 33, free->b: 62, free->c1: 9, free->d: 17
- large / gpt-5.6-terra / B2: produced {'a': 130, 'b': 293, 'c1': 29, 'd': 40}; requested → produced a->a: 27, a->b: 54, a->c1: 4, a->d: 1, b->a: 26, b->b: 43, b->d: 5, c1->a: 32, c1->b: 51, c1->c1: 6, c1->d: 3, d->a: 28, d->b: 86, d->c1: 10, d->d: 14, free->a: 17, free->b: 59, free->c1: 9, free->d: 17
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 165, 'b': 205, 'c1': 3, 'free': 2}; requested → produced free->a: 165, free->b: 205, free->c1: 3, free->free: 2
- large / gpt-5.6-terra / M: produced {'a': 66, 'b': 214, 'c1': 24, 'd': 7}; requested → produced a->a: 1, a->b: 20, a->c1: 1, b->a: 6, b->b: 18, c1->a: 17, c1->b: 51, c1->c1: 13, d->a: 19, d->b: 112, d->c1: 7, d->d: 7, free->a: 23, free->b: 13, free->c1: 3

## 7. Runs and anomalies

Runs on the reported tiers: 108 (37 done, 18 running, 53 not started). No run in an abnormal status.

## 7a. Operational changes during the run (DECISIONS 2026-09-16; verdict definitions, floors, budgets and the stack unchanged)

Hidden DC registrations capped at 8 from 2026-09-16T14:30; split equivalence pipeline, provisional diagnosis and proof ordering from 2026-09-16T15:14; positive provisional verdicts withheld from the model from 2026-09-16T16:03.

- Provisional-versus-final diagnosis agreement: 5 of 5 proven candidates with a final diagnosis agree (100.0 %); 87 candidates received a provisional label (absorbed_identical 2, harmful 2, improved 40, no_gain 10, noise 5, retained 12, tradeoff 16), 13 of them were not proven, 69 still wait for the proof or the diagnosis, 8 labels withheld from the model.
- Positive provisional feedback exposure (window 2026-09-16T15:14 to 2026-09-16T16:03): 15 LLM calls carried 25 positive pending blocks (2 runs); 8 candidates behind them — proofs since: inconclusive 1, pending 7.
- Cross-run verdict reuse since 2026-09-16T15:14: 0 proofs copied from a decided record of the same pair ({}), over 37 split-pipeline proofs of 244 equivalence records; sim records missing: 0.

Equivalence jobs finished per hour on the VC Formal pool since the throttle (2026-09-16T14:30), by the candidate's verdict:

| hour | finished | proven | inconclusive | proven : inconclusive | falsified | rejected | sim_fail |
|---|---|---|---|---|---|---|---|
| 2026-09-16T14 | 94 | 25 | 18 | 1.39 | 6 | 37 | 8 |
| 2026-09-16T15 | 101 | 43 | 26 | 1.65 | 8 | 21 | 3 |
| 2026-09-16T16 | 28 | 7 | 9 | 0.78 | 9 | 0 | 2 |

