# spec 05 — Ladder search `src/search/`

## 1. Main skeleton: parallel-candidate hill climbing + small archive

State: archive A (three-objective Pareto front, at most `search.archive_size`=5, holding proven candidates already evaluated at E4); class bandit (five arms: (a), (b), (c1), (d), free); budget B (DC hours); predictor P; screening rung E_s; audit records.

Per generation:
1. Parent selection: sample from A by crowding distance; after `search.stall_gens` generations without retained improvement -> switch parent / restart (another element of A, or D).
2. Generation: the bandit draws N classes (UCB-softmax, config), one prompt per class, the LLM generates N candidates in parallel; each candidate carries the feedback blocks of its parent lineage (the most recent `search.feedback_depth`).
3. Equivalence stack V1–V3 (V4 as needed); non-proven candidates are recorded and discarded.
4. M6 classification.
5. Screening (if enabled): evaluate at E_s; P gives p; p ≥ τ promotes; among the rest a random `search.audit_frac`=0.1 is promoted (marked audit); the remainder are recorded as `screened_out` with a reduced feedback block.
6. E4 evaluation of promoted candidates; M3 diagnosis; feedback blocks written; bandit credit.
7. Calibration: E4 results of audited candidates update the per-design P (online logistic regression or per-class Bayesian counts) and the miss-rate estimate; re-select E_s every `search.recal_gens` generations.
8. Archive update (Pareto front); budget deduction (this generation's DC seconds); stop when the budget is exhausted or K generations are reached.
9. Accepted candidates (those that ever entered the archive) are submitted to the hidden-layer queue (handled by `hidden_worker`; the search process never reads the results).

## 2. Prompt structure (cache-friendly)

Stable prefix (fixed per design): system prompt -> task definition and output format (return RTL plus a one-sentence transformation note, JSON-wrapped) -> D's RTL -> D's E4 summary (area/WNS/TNS/power, critical path mapped to RTL lines, resource-report summary, compile-log summary: what DC already did) -> noise floor (minimum reportable gain) -> map prior table (Phase 4 output; B1 uses the static complement text instead).
Variable suffix: parent RTL (if not D) -> feedback blocks of the parent lineage -> the class instruction for this call.
Static complement text (B1 only): an explicit list of "the synthesizer does this, do not do it" rewrites and "do this" directions; fixed content, no candidate-level evidence.
Template files: `src/search/prompts/*.md`, versioned; changes are recorded in DECISIONS.

## 3. Screening policy (automatic rung control)

**Rung selection (choose E_s)**: the first generation of every design is not screened; all candidates run E1, E2, E4 (Y optional). From this generation plus the noise-floor data, compute the AUROC of E1, E2 (, Y) for E4 retention; pick the cheapest rung with AUROC ≥ `screen.auroc_min` as E_s; if none qualifies -> screening off for this design; if the mean E4 runtime < `screen.e4_cheap_sec` -> screening off. Re-estimate from audit data every `search.recal_gens` generations; switching rungs is allowed.

**Threshold control (τ)**: this generation's E4 quota q = remaining budget / remaining generations / t_E4; τ is the p-quantile that promotes exactly q candidates; if the audit miss rate > `screen.miss_max`, lower τ one step (promote more); if < `screen.miss_min`, raise it.

**Predictor P**: initialized from the model trained in Phase 4 (features: class, three-component g_Es, E_s fingerprint convergence, register-count change, AST diff size, design features); updated online with this design's audit and promotion results (per class, Bayesian). A class-blind version is used for ablation.

## 4. Budget accounting

Per-design budget B = `scale.budget.k_e4_equiv` × t_E4(D) (t_E4 from Phase 2); deductions: E_s, E4, sampled single-flag runs; SEQ is not counted in DC hours but is tracked separately (VC Formal hours); LLM dollars are tracked separately and bounded by the phase cap. The `runs` table records cumulative consumption per generation. The auxiliary equal-LLM-calls group uses a fixed number of calls instead of B.

## 5. Implementation differences between arms

| Arm | Fitness source | Screening | Feedback block | Bandit credit |
|---|---|---|---|---|
| B0 | three-component gain at Y caliber (no truncation) | none | scalar (Y numbers) | any positive gain |
| B1@E4 | three-component E4 gain (no truncation) | none | scalar + static complement text | any positive gain |
| B2 | three-component E4 gain (no truncation) | none | scalar (E4 numbers) | any positive gain |
| M | E4 retained gain (2σ truncation) | automatic rung | five-way diagnosis + prior | only retained / trade-off improvement |
| M-noscreen | same as M | off | same as M | same as M |
| Dr.RTL-reimpl | E4 scalar | none | Dr.RTL's top-k path feedback + in-run skill learning (implemented as in its paper) | — |

Accepted candidates of B0/B1/B2 are also sent to E4 (B0) and the hidden layer so that all arms are compared under the same configurations.

## 6. Skeleton plugins (skeleton independence)

`src/search/skeletons/`: `hillclimb.py` (main), `coevo.py`, `revolution.py`. The latter two are adapted for RTL-to-RTL (correctness as a binary gate; COEVO's three-objective non-dominated sorting; REvolution's Fail population removed), with the same interface: `propose()`, `select()`, `update()`. M and B2 run once on each skeleton (30-start subset).

## 7. Run outputs

One row in `runs`; one row per candidate in `candidates`; one row per candidate in `screening` (if enabled); one row per E4 candidate in `diagnoses`; all requests/responses under `results/llm/<run_id>/`; all candidate RTL under `results/candidates/<run_id>/`; per-generation `gen_summary.json` (archive, bandit probabilities, τ, E_s, consumption).

## 8. Tests

- Negative: a pure-renaming candidate must be stopped at E_s (when screening is on) or diagnosed `absorbed@E1`; the RTL-OPT optimized version as a candidate must be promoted and `retained`.
- Budget: with simulated t_E4 and a fixed candidate stream, confirm stop on exhaustion and correct quota/τ computation.
- Bandit: probabilities drift toward the high-reward arm under synthetic rewards.
- Resumption: kill the process mid-run; resuming from `gen_summary.json` yields identical results.
- LLM client: requests saved, tokens counted, cost accumulated, raises and stops when the phase cap is reached.
