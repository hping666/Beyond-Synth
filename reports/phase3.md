# Phase 3 report — LLM calibration (residual-guided evolution, minimal skeleton)

Generated 2026-09-14 13:38 by scripts/report_phase.py (git 8105ea0e031c, cfg 5c4f19739d23). Data: reports/data/phase3_calibration.json (scripts/phase3_calibrate.py collect).

## 1. Setup

Models ['gpt-5.6-luna', 'gpt-5.4-mini', 'gpt-5.6-terra', 'gpt-5.4']; designs (dev split only, DECISIONS 2026-09-14) × 2 seeds; K = 6 generations × N = 5 candidates per run; arm M without synthesis-rung screening and without a map prior; pipeline V1 → V2 (zero initial state) → V3 SEQ (class-aware caps) → E4 → diagnosis (rule-A floors). Budget caliber: equal LLM calls.

## 2. Per-model results

| model | runs | candidates | unusable answers | V1 ok | V3 proven | proven_sim_only (apart) | inconclusive | retained (rule A) | retained (materiality row) | LLM calls / retained | USD / retained | DC h / retained | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.4 | 10 | 295 | 0 | 240 | 207 | 0 | 0 | 69 | 112 | 4.3 | 0.230 | 0.08 | 15.84 | 5.32 | 2.00 |
| gpt-5.4-mini | 10 | 269 | 31 | 239 | 177 | 0 | 6 | 37 | 85 | 8.1 | 0.220 | 0.14 | 8.13 | 5.16 | 26.04 |
| gpt-5.6-luna | 10 | 300 | 0 | 267 | 223 | 0 | 4 | 57 | 120 | 5.3 | 0.009 | 0.12 | 0.52 | 6.65 | 12.42 |
| gpt-5.6-terra | 10 | 303 | 0 | 238 | 199 | 0 | 0 | 59 | 107 | 5.1 | 0.086 | 0.09 | 5.10 | 5.54 | 1.95 |

## 3. Classes: produced distribution and requested → produced confusion

- **gpt-5.4**: produced classes {'a': 88, 'b': 29, 'c1': 26, 'd': 152}; confusion a->a: 17, a->b: 2, a->c1: 3, a->d: 19, b->a: 31, b->b: 3, b->c1: 2, b->d: 27, c1->a: 12, c1->b: 5, c1->c1: 7, c1->d: 25, d->a: 16, d->b: 11, d->c1: 6, d->d: 27, free->a: 12, free->b: 8, free->c1: 8, free->d: 54; labels {'absorbed_identical': 39, 'duplicate': 36, 'harmful': 3, 'nonequiv': 33, 'pending': 55, 'retained': 69, 'tradeoff': 60}; inconclusive rate by class {a: 0 %, b: 0 %, c1: 0 %, d: 0 %}
- **gpt-5.4-mini**: produced classes {'a': 70, 'b': 27, 'c1': 53, 'd': 119}; confusion a->a: 15, a->b: 4, a->c1: 23, a->d: 7, b->a: 23, b->b: 2, b->c1: 2, b->d: 30, c1->a: 13, c1->b: 6, c1->c1: 6, c1->d: 24, d->a: 11, d->b: 4, d->c1: 10, d->d: 28, free->a: 8, free->b: 11, free->c1: 12, free->d: 30; labels {'absorbed_identical': 55, 'duplicate': 44, 'harmful': 4, 'nonequiv': 63, 'pending': 29, 'retained': 37, 'tradeoff': 37}; inconclusive rate by class {a: 1 %, b: 0 %, c1: 4 %, d: 3 %}
- **gpt-5.6-luna**: produced classes {'?': 4, 'a': 99, 'b': 34, 'c1': 100, 'd': 62, 'free': 1}; confusion a->a: 16, a->b: 2, a->c1: 12, b->?: 1, b->a: 32, b->b: 9, b->c1: 12, b->d: 14, c1->?: 2, c1->a: 7, c1->b: 9, c1->c1: 18, c1->d: 19, d->a: 26, d->b: 8, d->c1: 14, d->d: 13, free->?: 1, free->a: 18, free->b: 6, free->c1: 44, free->d: 16, free->free: 1; labels {'absorbed_identical': 35, 'duplicate': 77, 'harmful': 6, 'nonequiv': 48, 'pending': 25, 'retained': 57, 'tradeoff': 52}; inconclusive rate by class {?: 0 %, a: 2 %, b: 0 %, c1: 0 %, d: 3 %, free: 0 %}
- **gpt-5.6-terra**: produced classes {'?': 7, 'a': 100, 'b': 28, 'c1': 80, 'd': 88}; confusion a->a: 18, a->c1: 8, a->d: 11, b->a: 26, b->b: 1, b->c1: 10, b->d: 16, c1->?: 2, c1->a: 8, c1->b: 10, c1->c1: 21, c1->d: 11, d->a: 18, d->b: 16, d->c1: 18, d->d: 23, free->?: 5, free->a: 30, free->b: 1, free->c1: 23, free->d: 27; labels {'aborted': 2, 'absorbed_identical': 39, 'duplicate': 67, 'harmful': 1, 'nonequiv': 39, 'pending': 57, 'retained': 59, 'tradeoff': 39}; inconclusive rate by class {?: 0 %, a: 0 %, b: 0 %, c1: 0 %, d: 0 %}

## 4. Best retained area gain per design (offset designs flagged)

| model | rtllm_LIFObuffer | rtllm_multi_pipe_8bit | rtllm_serial2parallel | rtllm_traffic_light |
|---|---|---|---|---|
| gpt-5.4 | 14.90 % | - | 19.28 % | 44.96 % |
| gpt-5.4-mini | 7.59 % | 17.03 % | 19.28 % | 26.74 % |
| gpt-5.6-luna | 15.17 % | 15.12 % | 19.28 % | 42.05 % |
| gpt-5.6-terra | 14.34 % | 0.62 % | 9.74 % | 44.96 % |

## 5. Time to verdict (seconds from the LLM answer to the equivalence verdict) and response to absorbed feedback

- **gpt-5.4**: a: n=71 median 245 q95 690 max 1043; b: n=26 median 262 q95 579 max 680; c1: n=23 median 197 q95 724 max 759; d: n=120 median 389 q95 827 max 1158; children of absorbed parents that were not absorbed again: 0 of 0
- **gpt-5.4-mini**: a: n=69 median 284 q95 4490 max 12992; b: n=26 median 253 q95 3303 max 8246; c1: n=46 median 454 q95 15676 max 19552; d: n=99 median 609 q95 13182 max 17642; children of absorbed parents that were not absorbed again: 0 of 0
- **gpt-5.6-luna**: a: n=96 median 203 q95 11310 max 15698; b: n=34 median 242 q95 3687 max 4588; c1: n=95 median 374 q95 10026 max 13110; d: n=45 median 316 q95 15556 max 17938; free: n=1 median 13209 q95 13209 max 13209; children of absorbed parents that were not absorbed again: 0 of 0
- **gpt-5.6-terra**: a: n=85 median 86 q95 285 max 16076; b: n=26 median 88 q95 165 max 173; c1: n=69 median 95 q95 214 max 16060; d: n=58 median 113 q95 263 max 290; children of absorbed parents that were not absorbed again: 0 of 0

## 5b. Y (Yosys + OpenSTA) as a screen for E4 retention

AUROC of the Y area gain for E4 retention over 197 retained vs 528 other diagnosed candidates: 0.748; best-of-three-components gain: 0.579; threshold `screen.auroc_min` = 0.75 (Y does not qualify: the M_noscreen arm is dropped and its budget goes to starting points (DECISIONS 2026-09-14 G3.1)).


## 6. Decision rule (config llm.calibration.decision)

Primary metric retained_candidates_per_usd: scores {'gpt-5.4': 4.356, 'gpt-5.4-mini': 4.551, 'gpt-5.6-luna': 110.215, 'gpt-5.6-terra': 11.577}; best area gain per model {'gpt-5.4': 44.96, 'gpt-5.4-mini': 26.74, 'gpt-5.6-luna': 42.05, 'gpt-5.6-terra': 44.96} %; eligible (best gain ≥ 0.7 × strongest, a retained (c1) or (d)): ['gpt-5.6-luna', 'gpt-5.6-terra', 'gpt-5.4']; **recommended: gpt-5.6-luna** — recommendation by config llm.calibration.decision; the user confirms at G4 (config llm.selected stays TBD until then)
