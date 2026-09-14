# Phase 3 report — LLM calibration (residual-guided evolution, minimal skeleton)

Generated 2026-09-14 14:11 by scripts/report_phase.py (git 8a20578da17c, cfg 332d14a3c38a). Data: reports/data/phase3_calibration.json (scripts/phase3_calibrate.py collect).

## 1. Setup

Models ['gpt-5.6-luna', 'gpt-5.4-mini', 'gpt-5.6-terra', 'gpt-5.4']; designs (dev split only, DECISIONS 2026-09-14) × 2 seeds; K = 6 generations × N = 5 candidates per run; arm M without synthesis-rung screening and without a map prior; pipeline V1 → V2 (zero initial state) → V3 SEQ (class-aware caps) → E4 → diagnosis (rule-A floors). Budget caliber: equal LLM calls.

## 2. Per-model results

| model | runs | candidates | unusable answers | V1 ok | V3 proven | proven_sim_only (apart) | inconclusive | retained (rule A) | retained (materiality row) | LLM calls / retained | USD / retained | DC h / retained | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.4 | 10 | 300 | 0 | 241 | 208 | 0 | 0 | 69 | 112 | 4.3 | 0.234 | 0.08 | 16.16 | 5.32 | 2.00 |
| gpt-5.4-mini | 10 | 269 | 31 | 253 | 187 | 0 | 6 | 40 | 92 | 7.5 | 0.203 | 0.13 | 8.13 | 5.16 | 26.04 |
| gpt-5.6-luna | 10 | 300 | 0 | 274 | 227 | 0 | 4 | 59 | 123 | 5.1 | 0.009 | 0.11 | 0.52 | 6.65 | 12.42 |
| gpt-5.6-terra | 10 | 303 | 0 | 242 | 203 | 0 | 0 | 60 | 108 | 5.0 | 0.085 | 0.09 | 5.10 | 5.54 | 1.95 |

## 3. Classes: produced distribution and requested → produced confusion

- **gpt-5.4**: produced classes {'a': 89, 'b': 30, 'c1': 26, 'd': 155}; confusion a->a: 18, a->b: 3, a->c1: 3, a->d: 19, b->a: 31, b->b: 3, b->c1: 2, b->d: 27, c1->a: 12, c1->b: 5, c1->c1: 7, c1->d: 25, d->a: 16, d->b: 11, d->c1: 6, d->d: 29, free->a: 12, free->b: 8, free->c1: 8, free->d: 55; labels {'absorbed_identical': 39, 'duplicate': 36, 'harmful': 3, 'nonequiv': 33, 'pending': 59, 'retained': 69, 'tradeoff': 61}; inconclusive rate by class {a: 0 %, b: 0 %, c1: 0 %, d: 0 %}
- **gpt-5.4-mini**: produced classes {'a': 70, 'b': 27, 'c1': 53, 'd': 119}; confusion a->a: 15, a->b: 4, a->c1: 23, a->d: 7, b->a: 23, b->b: 2, b->c1: 2, b->d: 30, c1->a: 13, c1->b: 6, c1->c1: 6, c1->d: 24, d->a: 11, d->b: 4, d->c1: 10, d->d: 28, free->a: 8, free->b: 11, free->c1: 12, free->d: 30; labels {'absorbed_identical': 55, 'duplicate': 47, 'harmful': 5, 'nonequiv': 67, 'pending': 17, 'retained': 40, 'tradeoff': 38}; inconclusive rate by class {a: 1 %, b: 0 %, c1: 4 %, d: 3 %}
- **gpt-5.6-luna**: produced classes {'?': 4, 'a': 99, 'b': 34, 'c1': 100, 'd': 62, 'free': 1}; confusion a->a: 16, a->b: 2, a->c1: 12, b->?: 1, b->a: 32, b->b: 9, b->c1: 12, b->d: 14, c1->?: 2, c1->a: 7, c1->b: 9, c1->c1: 18, c1->d: 19, d->a: 26, d->b: 8, d->c1: 14, d->d: 13, free->?: 1, free->a: 18, free->b: 6, free->c1: 44, free->d: 16, free->free: 1; labels {'absorbed_identical': 36, 'duplicate': 78, 'harmful': 6, 'nonequiv': 51, 'pending': 18, 'retained': 59, 'tradeoff': 52}; inconclusive rate by class {?: 0 %, a: 2 %, b: 0 %, c1: 0 %, d: 3 %, free: 0 %}
- **gpt-5.6-terra**: produced classes {'?': 7, 'a': 100, 'b': 28, 'c1': 80, 'd': 88}; confusion a->a: 18, a->c1: 8, a->d: 11, b->a: 26, b->b: 1, b->c1: 10, b->d: 16, c1->?: 2, c1->a: 8, c1->b: 10, c1->c1: 21, c1->d: 11, d->a: 18, d->b: 16, d->c1: 18, d->d: 23, free->?: 5, free->a: 30, free->b: 1, free->c1: 23, free->d: 27; labels {'aborted': 2, 'absorbed_identical': 40, 'duplicate': 67, 'harmful': 1, 'nonequiv': 39, 'pending': 53, 'retained': 60, 'tradeoff': 41}; inconclusive rate by class {?: 0 %, a: 0 %, b: 0 %, c1: 0 %, d: 0 %}

## 4. Best retained area gain per design (offset designs flagged)

| model | rtllm_LIFObuffer | rtllm_multi_pipe_8bit | rtllm_serial2parallel | rtllm_traffic_light |
|---|---|---|---|---|
| gpt-5.4 | 14.90 % | - | 19.28 % | 44.96 % |
| gpt-5.4-mini | 7.59 % | 17.03 % | 19.28 % | 26.74 % |
| gpt-5.6-luna | 15.17 % | 15.12 % | 19.28 % | 42.05 % |
| gpt-5.6-terra | 14.34 % | 0.62 % | 9.74 % | 44.96 % |

## 5. Time to verdict (seconds from the LLM answer to the equivalence verdict) and response to absorbed feedback

- **gpt-5.4**: a: n=71 median 245 q95 690 max 1043; b: n=26 median 262 q95 579 max 680; c1: n=24 median 228 q95 757 max 16627; d: n=120 median 389 q95 827 max 1158; children of absorbed parents that were not absorbed again: 0 of 0
- **gpt-5.4-mini**: a: n=69 median 284 q95 4490 max 12992; b: n=27 median 270 q95 7033 max 16913; c1: n=49 median 465 q95 18588 max 19552; d: n=109 median 1891 q95 17299 max 21402; children of absorbed parents that were not absorbed again: 0 of 0
- **gpt-5.6-luna**: a: n=98 median 206 q95 11480 max 17292; b: n=34 median 242 q95 3687 max 4588; c1: n=96 median 375 q95 11336 max 15842; d: n=49 median 390 q95 17300 max 17938; free: n=1 median 13209 q95 13209 max 13209; children of absorbed parents that were not absorbed again: 0 of 0
- **gpt-5.6-terra**: a: n=88 median 88 q95 10524 max 16533; b: n=26 median 88 q95 165 max 173; c1: n=70 median 97 q95 242 max 16565; d: n=58 median 113 q95 263 max 290; children of absorbed parents that were not absorbed again: 0 of 0

## 5a. Verdict sensitivity: stored (run-time) floors vs rule A design-weighted (adopted) vs record-weighted (rejected) vs materiality

Every E4-evaluated candidate re-diagnosed offline (no tool runs; archived in reports/data/phase3_label_sensitivity.json). Pooled E4 minima: design-weighted area 0.28 % / power 2.22 %; record-weighted area 1.43 % / power 5.92 % (DECISIONS 2026-09-14: the record-weighted minimum follows the number of perturbations per design and was rejected).

| model | E4-evaluated | stored: retained / tradeoff / absorbed_identical / noise / harmful | design-weighted: same | record-weighted: same | materiality: same |
|---|---|---|---|---|---|
| gpt-5.4 | 208 | 69 / 61 / 39 / 0 / 3 | 96 / 70 / 39 / 0 / 3 | 104 / 60 / 39 / 1 / 4 | 112 / 53 / 39 / 0 / 4 |
| gpt-5.4-mini | 185 | 40 / 38 / 55 / 0 / 5 | 85 / 40 / 55 / 0 / 5 | 90 / 33 / 55 / 0 / 7 | 89 / 31 / 55 / 0 / 10 |
| gpt-5.6-luna | 227 | 59 / 52 / 36 / 0 / 6 | 117 / 68 / 36 / 0 / 6 | 124 / 56 / 36 / 1 / 10 | 122 / 52 / 36 / 1 / 16 |
| gpt-5.6-terra | 202 | 60 / 41 / 40 / 0 / 1 | 105 / 56 / 40 / 0 / 1 | 107 / 51 / 40 / 1 / 3 | 106 / 48 / 40 / 2 / 6 |

Rule-A t_D per calibration design under the adopted design-weighted minimum (area / WNS as a fraction of the period / power): rtllm_LIFObuffer: 0.28 % / 0.04 % / 2.22 % (quiet); rtllm_adder_16bit: 0.28 % / 0.04 % / 2.22 % (quiet); rtllm_multi_pipe_8bit: 0.28 % / 0.04 % / 2.22 % (quiet); rtllm_serial2parallel: 0.28 % / 0.04 % / 2.22 % (quiet); rtllm_traffic_light: 0.28 % / 0.04 % / 2.22 % (quiet)


## 5b. Y (Yosys + OpenSTA) as a screen for E4 retention

AUROC of the Y area gain for E4 retention over 197 retained vs 528 other diagnosed candidates: 0.748; best-of-three-components gain: 0.579; threshold `screen.auroc_min` = 0.75 (Y does not qualify: the M_noscreen arm is dropped and its budget goes to starting points (DECISIONS 2026-09-14 G3.1)).


## 6. Decision rule (config llm.calibration.decision)

Primary metric retained_candidates_per_usd: scores {'gpt-5.4': 4.27, 'gpt-5.4-mini': 4.92, 'gpt-5.6-luna': 114.082, 'gpt-5.6-terra': 11.773}; best area gain per model {'gpt-5.4': 44.96, 'gpt-5.4-mini': 26.74, 'gpt-5.6-luna': 42.05, 'gpt-5.6-terra': 44.96} %; eligible (best gain ≥ 0.7 × strongest, a retained (c1) or (d)): ['gpt-5.6-luna', 'gpt-5.6-terra', 'gpt-5.4']; **recommended: gpt-5.6-luna** — recommendation by config llm.calibration.decision; the user confirms at G4 (config llm.selected stays TBD until then)
