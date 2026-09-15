# Phase 3 report — LLM calibration (residual-guided evolution, minimal skeleton)

Generated 2026-09-14 18:07 by scripts/report_phase.py (git 2ca44a890751, cfg 0a5870d5adac). Data: reports/data/phase3_calibration.json (scripts/phase3_calibrate.py collect).

## 1. Setup

Models ['gpt-5.6-luna', 'gpt-5.4-mini', 'gpt-5.6-terra', 'gpt-5.4']; designs (dev split only, DECISIONS 2026-09-14) × 2 seeds; K = 6 generations × N = 5 candidates per run; arm M without synthesis-rung screening and without a map prior; pipeline V1 → V2 (zero initial state) → V3 SEQ (class-aware caps) → E4 → diagnosis (rule-A floors). Budget caliber: equal LLM calls.

## 2. Per-model results

| model | runs | candidates | unusable answers | V1 ok | V3 proven | proven_sim_only (apart) | inconclusive | retained (rule A) | retained (materiality row) | LLM calls / retained | USD / retained | DC h / retained | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.4 | 10 | 300 | 0 | 259 | 220 | 0 | 4 | 74 | 118 | 4.1 | 0.218 | 0.07 | 16.16 | 5.32 | 2.00 |
| gpt-5.4-mini | 10 | 269 | 31 | 268 | 196 | 0 | 11 | 46 | 101 | 6.5 | 0.177 | 0.13 | 8.13 | 6.13 | 85.35 |
| gpt-5.6-luna | 10 | 300 | 0 | 288 | 237 | 0 | 8 | 63 | 131 | 4.8 | 0.008 | 0.11 | 0.52 | 7.20 | 32.81 |
| gpt-5.6-terra | 10 | 303 | 0 | 273 | 225 | 0 | 9 | 71 | 122 | 4.2 | 0.072 | 0.08 | 5.10 | 5.54 | 1.95 |

## 3. Classes: produced distribution and requested → produced confusion

- **gpt-5.4**: produced classes {'a': 20, 'b': 96, 'c1': 89, 'd': 95}; confusion a->a: 11, a->b: 21, a->c1: 5, a->d: 6, b->a: 8, b->b: 23, b->c1: 15, b->d: 17, c1->a: 1, c1->b: 9, c1->c1: 19, c1->d: 20, d->b: 18, d->c1: 14, d->d: 30, free->b: 25, free->c1: 36, free->d: 22; labels {'absorbed_identical': 39, 'duplicate': 36, 'harmful': 9, 'nonequiv': 39, 'pending': 41, 'retained': 74, 'tradeoff': 62}; inconclusive rate by class {a: 0 %, b: 0 %, c1: 0 %, d: 4 %}
- **gpt-5.4-mini**: produced classes {'a': 25, 'b': 86, 'c1': 51, 'd': 107}; confusion a->a: 20, a->b: 7, a->c1: 6, a->d: 16, b->a: 4, b->b: 19, b->c1: 11, b->d: 23, c1->b: 20, c1->c1: 11, c1->d: 18, d->b: 13, d->c1: 11, d->d: 29, free->a: 1, free->b: 27, free->c1: 12, free->d: 21; labels {'absorbed_identical': 55, 'duplicate': 49, 'harmful': 6, 'nonequiv': 73, 'retained': 46, 'tradeoff': 40}; inconclusive rate by class {a: 0 %, b: 0 %, c1: 0 %, d: 10 %}
- **gpt-5.6-luna**: produced classes {'a': 50, 'b': 64, 'c1': 97, 'd': 88, 'free': 1}; confusion a->a: 10, a->b: 5, a->c1: 7, a->d: 8, b->a: 20, b->b: 15, b->c1: 16, b->d: 17, c1->a: 3, c1->b: 20, c1->c1: 15, c1->d: 17, d->a: 1, d->b: 8, d->c1: 22, d->d: 30, free->a: 16, free->b: 16, free->c1: 37, free->d: 16, free->free: 1; labels {'absorbed_identical': 36, 'duplicate': 82, 'harmful': 6, 'nonequiv': 55, 'pending': 4, 'retained': 63, 'tradeoff': 54}; inconclusive rate by class {a: 0 %, b: 0 %, c1: 0 %, d: 9 %, free: 0 %}
- **gpt-5.6-terra**: produced classes {'a': 42, 'b': 60, 'c1': 107, 'd': 94}; confusion a->a: 15, a->b: 6, a->c1: 15, a->d: 1, b->a: 11, b->b: 8, b->c1: 21, b->d: 13, c1->a: 1, c1->b: 11, c1->c1: 20, c1->d: 20, d->a: 3, d->b: 25, d->c1: 19, d->d: 28, free->a: 12, free->b: 10, free->c1: 32, free->d: 32; labels {'aborted': 2, 'absorbed_identical': 40, 'duplicate': 73, 'harmful': 6, 'nonequiv': 48, 'pending': 22, 'retained': 71, 'tradeoff': 41}; inconclusive rate by class {a: 0 %, b: 3 %, c1: 0 %, d: 7 %}

## 4. Best retained area gain per design (offset designs flagged)

| model | rtllm_LIFObuffer | rtllm_multi_pipe_8bit | rtllm_serial2parallel | rtllm_traffic_light |
|---|---|---|---|---|
| gpt-5.4 | 14.90 % | 9.78 % | 19.28 % | 44.96 % |
| gpt-5.4-mini | 7.59 % | 17.03 % | 19.28 % | 26.74 % |
| gpt-5.6-luna | 15.17 % | 15.12 % | 19.28 % | 42.05 % |
| gpt-5.6-terra | 14.34 % | 15.62 % | 9.74 % | 44.96 % |

## 5. Time to verdict (seconds from the LLM answer to the equivalence verdict) and the response to absorbed feedback

- **gpt-5.4**: a: n=19 median 268 q95 636 max 674; b: n=87 median 440 q95 18162 max 20181; c1: n=88 median 293 q95 853 max 16627; d: n=65 median 321 q95 19384 max 27181
- **gpt-5.4-mini**: a: n=25 median 450 q95 3905 max 4914; b: n=86 median 435 q95 8239 max 17249; c1: n=51 median 539 q95 10015 max 17332; d: n=107 median 2675 q95 23503 max 25584
- **gpt-5.6-luna**: a: n=50 median 241 q95 11324 max 17257; b: n=63 median 251 q95 4591 max 17292; c1: n=97 median 495 q95 13259 max 24886; d: n=81 median 243 q95 24453 max 27291; free: n=1 median 13209 q95 13209 max 13209
- **gpt-5.6-terra**: a: n=40 median 103 q95 19526 max 19621; b: n=60 median 101 q95 19248 max 21634; c1: n=101 median 109 q95 262 max 16060; d: n=72 median 99 q95 26333 max 26823

Feedback response (DECISIONS 2026-09-14 b): absorbed_identical rate among candidates whose lineage feedback carried an absorbed verdict versus candidates whose feedback did not, per generation:

| model | generation | with absorbed feedback: absorbed_identical / n | without: absorbed_identical / n |
|---|---|---|---|
| gpt-5.4 | 1 | - | 8 / 49 (16 %) |
| gpt-5.4 | 2 | 7 / 10 (70 %) | 0 / 34 (0 %) |
| gpt-5.4 | 3 | 8 / 10 (80 %) | 0 / 34 (0 %) |
| gpt-5.4 | 4 | 4 / 10 (40 %) | 0 / 32 (0 %) |
| gpt-5.4 | 5 | 9 / 10 (90 %) | 0 / 30 (0 %) |
| gpt-5.4 | 6 | 3 / 10 (30 %) | 0 / 30 (0 %) |
| gpt-5.4-mini | 1 | - | 12 / 46 (26 %) |
| gpt-5.4-mini | 2 | 7 / 10 (70 %) | 0 / 35 (0 %) |
| gpt-5.4-mini | 3 | 8 / 10 (80 %) | 0 / 34 (0 %) |
| gpt-5.4-mini | 4 | 8 / 10 (80 %) | 0 / 36 (0 %) |
| gpt-5.4-mini | 5 | 10 / 10 (100 %) | 0 / 35 (0 %) |
| gpt-5.4-mini | 6 | 10 / 10 (100 %) | 0 / 33 (0 %) |
| gpt-5.6-luna | 1 | - | 7 / 50 (14 %) |
| gpt-5.6-luna | 2 | 6 / 10 (60 %) | 0 / 40 (0 %) |
| gpt-5.6-luna | 3 | 7 / 10 (70 %) | 0 / 40 (0 %) |
| gpt-5.6-luna | 4 | 4 / 10 (40 %) | 1 / 40 (2 %) |
| gpt-5.6-luna | 5 | 5 / 10 (50 %) | 0 / 40 (0 %) |
| gpt-5.6-luna | 6 | 6 / 10 (60 %) | 0 / 36 (0 %) |
| gpt-5.6-terra | 1 | - | 10 / 50 (20 %) |
| gpt-5.6-terra | 2 | 7 / 9 (78 %) | 1 / 40 (2 %) |
| gpt-5.6-terra | 3 | 7 / 10 (70 %) | 0 / 38 (0 %) |
| gpt-5.6-terra | 4 | 6 / 10 (60 %) | 0 / 35 (0 %) |
| gpt-5.6-terra | 5 | 5 / 10 (50 %) | 0 / 33 (0 %) |
| gpt-5.6-terra | 6 | 2 / 5 (40 %) | 2 / 38 (5 %) |

## 5c. Phase 5 VC Formal projection (DECISIONS 2026-09-14 e)

Model gpt-5.6-luna: 300 Phase 3 calls consumed 56.2 SEQ hours (675 s per LLM call; arithmetic pipelines 3251 s, other designs 31 s per call). Phase 5 at the planned scale (540 runs, 32400 calls; starting pool 98 held designs of which 13 % arithmetic pipelines by name): **4121 VC Formal hours** by design-type mix (6073 h with the calibration's own mix); threshold 2000 h.

- arith_pipeline: class a: n=6, median 35 s, q95 48 s, 0.1 h; class b: n=4, median 36 s, q95 38 s, 0.0 h; class c1: n=14, median 104 s, q95 8259 s, 7.5 h; class d: n=25, median 7168 s, q95 10420 s, 46.6 h
- other: class a: n=38, median 37 s, q95 39 s, 0.4 h; class b: n=55, median 37 s, q95 40 s, 0.6 h; class c1: n=56, median 38 s, q95 41 s, 0.6 h; class d: n=51, median 36 s, q95 38 s, 0.5 h

Method: every Phase 3 SEQ verdict of the main model is binned by produced class (rules v2) and design type (arithmetic pipelines by name — `pipe`, `mult`, `div` — versus the rest); the per-call SEQ seconds of each design type (the type's total verdict seconds over its LLM calls) are combined with the design-type share of the Phase 5 starting pool (98 held designs, 13 % arithmetic pipelines) and multiplied by the planned 32400 calls; the flat-mix figure applies the calibration's own mix instead. Decision (2026-09-14 item 2): accepted as is — 4121 h at 50 seats is ≈ 82 h of wall-clock; the class caps and the pipeline share of the starting pool are not changed; Phase 5 proofs run in bulk mode at 50 seats; the SEQ latency mapping (G2.1(b)) stays on the critical path before Phase 5 and the DPV phase mapping follows it; within a generation the (c1) / (d) proofs on arithmetic designs are submitted first (config `search.long_proof_first`).

**Addendum (DECISIONS 2026-09-14 e, the projection exceeds 2000 h — proposal for the user, nothing changed):** (1) lower the SEQ class caps of arithmetic pipelined designs to 2 h for (c1) and (d) (config `equiv.seq_cap_min_by_class` would need a per-design-type entry; today's caps are 4 h): 12 of the 39 Phase 3 (c1) / (d) verdicts on the arithmetic pipeline ran longer than 2 h and would become `inconclusive` (never discarded, C2.5); the projection drops to **3707 h** at the planned scale, so the cap alone does not reach the threshold — the verdict distribution of the pipeline is bimodal (30–40 s or hours) and the hours sit in the proofs that finish under the cap as well. (2) Prioritise the SEQ latency mapping (G2.1(b)) and a DPV phase mapping for fixed-latency arithmetic pipelines before Phase 5: the pipeline's (c1) / (d) rewrites are fixed-latency datapaths where DPV's transaction equivalence needs no state-space search; this is the engineering item that removes the hours, the cap only bounds them. (3) Alternatively reduce the arithmetic-pipeline share of the Phase 5 starting pool (13 % by name) — a design-set decision for the user. The no-discard timeout policy is unchanged either way.


## 5a. Verdict sensitivity: stored (run-time) floors vs rule A design-weighted (adopted) vs record-weighted (rejected) vs materiality

Every E4-evaluated candidate re-diagnosed offline (no tool runs; archived in reports/data/phase3_label_sensitivity.json). Pooled E4 minima: design-weighted area 0.28 % / power 2.22 %; record-weighted area 1.43 % / power 5.92 % (DECISIONS 2026-09-14: the record-weighted minimum follows the number of perturbations per design and was rejected).

| model | E4-evaluated | stored: retained / tradeoff / absorbed_identical / noise / harmful | design-weighted: same | record-weighted: same | materiality: same |
|---|---|---|---|---|---|
| gpt-5.4 | 220 | 74 / 62 / 39 / 0 / 9 | 100 / 72 / 39 / 0 / 9 | 109 / 61 / 39 / 1 / 10 | 117 / 54 / 39 / 0 / 10 |
| gpt-5.4-mini | 196 | 46 / 40 / 55 / 0 / 6 | 93 / 42 / 55 / 0 / 6 | 99 / 34 / 55 / 0 / 8 | 98 / 31 / 55 / 0 / 12 |
| gpt-5.6-luna | 237 | 63 / 54 / 36 / 0 / 6 | 125 / 70 / 36 / 0 / 6 | 132 / 57 / 36 / 1 / 11 | 130 / 52 / 36 / 1 / 18 |
| gpt-5.6-terra | 224 | 71 / 41 / 40 / 0 / 6 | 121 / 56 / 40 / 0 / 7 | 123 / 51 / 40 / 2 / 8 | 120 / 48 / 40 / 4 / 12 |

Rule-A t_D per calibration design under the adopted design-weighted minimum (area / WNS as a fraction of the period / power): rtllm_LIFObuffer: 0.28 % / 0.04 % / 2.22 % (quiet); rtllm_adder_16bit: 0.28 % / 0.04 % / 2.22 % (quiet); rtllm_multi_pipe_8bit: 0.28 % / 0.04 % / 2.22 % (quiet); rtllm_serial2parallel: 0.28 % / 0.04 % / 2.22 % (quiet); rtllm_traffic_light: 0.28 % / 0.04 % / 2.22 % (quiet)


## 5b. Y (Yosys + OpenSTA) as a screen for E4 retention

AUROC of the Y area gain for E4 retention over 197 retained vs 528 other diagnosed candidates: 0.748; best-of-three-components gain: 0.579; threshold `screen.auroc_min` = 0.75 (Y does not qualify: the M_noscreen arm is dropped and its budget goes to starting points (DECISIONS 2026-09-14 G3.1)).


## 6. Decision rule (config llm.calibration.decision)

Primary metric retained_candidates_per_usd: scores {'gpt-5.4': 4.579, 'gpt-5.4-mini': 5.659, 'gpt-5.6-luna': 121.817, 'gpt-5.6-terra': 13.931}; best area gain per model {'gpt-5.4': 44.96, 'gpt-5.4-mini': 26.74, 'gpt-5.6-luna': 42.05, 'gpt-5.6-terra': 44.96} %; eligible (best gain ≥ 0.7 × strongest, a retained (c1) or (d)): ['gpt-5.6-luna', 'gpt-5.6-terra', 'gpt-5.4']; **recommended: gpt-5.6-luna** — recommendation by config llm.calibration.decision; the user confirms at G4 (config llm.selected stays TBD until then)


## 6a. M6 manual validation and the rules-v2 classifier (DECISIONS 2026-09-14 a)

60 candidates sampled over the rules-v1 produced classes (seed 2, quotas {'d': 24, 'c1': 16, 'a': 10, 'b': 10}) were read as diffs against D and classified by hand under the protocol of reports/data/phase3_m6_human.json (state-element criterion: (a) same registers and stored values, (b) register structure / stored state changed without registers crossing logic, (c1) registers cross logic at equal latency, (c2) output timing changed, (d) another algorithm / organisation / schedule). Human classes: {'a': 3, 'b': 23, 'c1': 9, 'c2': 4, 'd': 21}.

| rules | agreement | (a) precision / recall | (b) | (c1) | (c2) | (d) |
|---|---|---|---|---|---|---|
| v1 | 23 / 60 (38 %) | 10 % (1/10) / 33 % (1/3) | 90 % (9/10) / 39 % (9/23) | 38 % (6/16) / 67 % (6/9) | - (0/0) / 0 % (0/4) | 29 % (7/24) / 33 % (7/21) |
| v2 | 40 / 60 (67 %) | 29 % (2/7) / 67 % (2/3) | 88 % (15/17) / 65 % (15/23) | 41 % (9/22) / 100 % (9/9) | - (0/0) / 0 % (0/4) | 100 % (14/14) / 67 % (14/21) |

Confusion v1 (human -> rule): a->a: 1, a->c1: 1, a->d: 1, b->a: 1, b->b: 9, b->c1: 4, b->d: 9, c1->c1: 6, c1->d: 3, c2->d: 4, d->a: 8, d->b: 1, d->c1: 5, d->d: 7

Confusion v2 (human -> rule): a->a: 2, a->c1: 1, b->a: 4, b->b: 15, b->c1: 4, c1->c1: 9, c2->c1: 4, d->a: 1, d->b: 2, d->c1: 4, d->d: 14

Disagreement categories of rules v2 (DECISIONS 2026-09-14 item 1):

- unobservable-state or redundant-register removal (human b -> rule a / c1): 8
- buffer / schedule re-organisation without operator or depth evidence (human d -> rule a / b / c1): 7
- output-timing change of a nonequiv candidate (human c2 -> rule c1): 4
- nonequiv artifact (human a -> rule c1): 1

Phase 3 class distribution per model after the rules-v2 re-labelling (supersedes the distribution reported at G4; the run-time bandit credits and SEQ caps are unchanged):

| model | a | b | c1 | c2 | d | unclassified |
|---|---|---|---|---|---|---|
| gpt-5.4 | 20 | 96 | 89 | 0 | 95 | 0 |
| gpt-5.4-mini | 25 | 86 | 51 | 0 | 107 | 0 |
| gpt-5.6-luna | 50 | 64 | 97 | 0 | 88 | 1 |
| gpt-5.6-terra | 42 | 60 | 107 | 0 | 94 | 0 |

The LLM review of spec 04 A.2 step 2 (DECISIONS 2026-09-14 item 1; `src/classify/review.py`, prompt `src/search/prompts/m6_review.md`, model `llm.selected`) runs on the candidates with low v2 confidence or in the four categories above (`phase3_calibrate.py m6-review`); its class replaces the rule class for (a) / (b) / (c1) / (c2) and is stored as `class_llm` / `class_final`, while (d) stays defined by tool evidence: the recall loss of (d) (7 of the 21 human-labelled (d) candidates of the sample end up as (a) / (b) / (c1)) is a stated limitation and the map's (d) row is read precision-first.

Rules v2 (`src/classify/rules.py`, config `classify`): (d) requires an operator family gained (multiply / divide, add / subtract, variable shift; present in C's word-level RTLIL histogram, absent in D's) or a longest-combinational-path ratio ≥ 3.0 (Yosys `ltp -noff`); the text diff ratio only flags a rewrite for review. Flip-flop bits are counted after `opt` (the 32-bit loop variable of LIFObuffer's reset loop no longer counts as a register), (c1) needs the flip-flop bits **and** the number of register cells to change, blocking assignments count as clocked targets.

Remaining disagreements of v2 (20): #3 human b / rule a; #4 human c2 / rule c1; #5 human c2 / rule c1; #8 human d / rule b; #11 human b / rule c1; #12 human b / rule c1; #13 human c2 / rule c1; #15 human c2 / rule c1; #19 human b / rule c1; #20 human d / rule b; #24 human d / rule c1; #25 human b / rule a; #26 human b / rule a; #28 human b / rule a; #29 human b / rule c1; #31 human d / rule c1; #36 human d / rule c1; #40 human d / rule c1; #47 human a / rule c1; #49 human d / rule a.

Known limits of the static rules (recorded, not fixed): output-timing changes of nonequiv candidates cannot be seen without a lock-step offset (human c2 -> rule c1); buffer re-organisations that keep the register count (shift-register stacks, pointer-addressed writes without a shift cell), the FSM-to-phase-counter schedule change and the radix-4 partial-product recoding carry no operator or depth evidence (human d -> rule b / c1 / a); removals of unobservable state updates (reset / pop clears of an unread memory entry) and redundant-register removals are refactors the register features cannot separate from recodes (human b -> rule a / c1). These cases are the domain of the LLM review of spec 04 A.2 step 2, which is not part of the Phase 3 protocol. Every Phase 3 candidate was re-labelled with rules v2 (candidates.class_rule_v1 keeps the v1 class); the produced-class tables of §3 use the v2 classes, the run-time bandit credits and SEQ caps are untouched.


## 7. Conclusions for G4 (operator's reading; the decisions are the user's)

Status of the data: 32 of the 40 runs are complete; the 8 runs on multi_pipe_8bit have issued all 30 calls each and wait for 120 SEQ verdicts (classes (c1) / (d) of an 8-bit pipelined multiplier take 45–170 min each and often reach the class cap; the temporary 50-seat VC Formal pool drains them at ≈13 per hour, finishing around midnight). The background chain then re-runs the Y evaluations, the collect, the sample cross-check and this report; the numbers below carry every verdict available at 15:40 on 2026-09-14 and the model ranking cannot change by a factor that matters (the primary metric differs by an order of magnitude between the leader and the runners-up).

Facts (300 calls per model, K = 6 × N = 5 per run, 5 dev designs × 2 seeds, rule-A floors at run time, `proven_sim_only` apart — none occurred):

- **Usable answers**: luna, terra and gpt-5.4 answered every call within 20 000 output tokens; gpt-5.4-mini lost 31 of 300 answers to run-away reasoning (10 000+ reasoning tokens, no RTL). The first two launches were superseded by this very effect (`max_output_tokens` 3 000 → 10 000 → 20 000, DECISIONS 2026-09-14).
- **Pass rates**: V1 ok / V3 proven of the usable candidates — luna 274 / 227 of 300, terra 242 / 203 of 303, gpt-5.4 241 / 208 of 300, mini 253 / 187 of 269; SEQ inconclusive only on multi_pipe_8bit (luna 4, mini 6).
- **Retained (rule A, stored floors)**: gpt-5.4 69, terra 60, luna 59, mini 40; under the adopted design-weighted floors (§5a) 96 / 105 / 117 / 85, under the materiality thresholds 112 / 108 / 123 / 92. Every model produced retained (c1) or (d) rewrites.
- **Cost**: luna 0.52 USD for 300 calls (5.1 calls per retained candidate, 114 retained per USD), terra 5.10 USD (5.0 calls, 11.8 per USD), gpt-5.4 16.16 USD (4.3 calls, 4.3 per USD), mini 8.13 USD (7.5 calls, 4.9 per USD). DC hours per model 5.2–6.6; VC Formal hours 2.0 (terra), 2.0 (gpt-5.4), 12.4 (luna), 26.0 (mini) — the last two spent their SEQ time on multi_pipe_8bit (c1)/(d) candidates.
- **Best retained area gain per design**: traffic_light 45.0 % (gpt-5.4, terra; luna 42.1 %), serial2parallel 19.3 % (luna, gpt-5.4, mini), LIFObuffer 15.2 % (luna), multi_pipe_8bit 17.0 % (mini) / 15.1 % (luna) so far.
- **Classes**: the LLM rarely produces the class it was asked for (requested → produced agreement 19–21 %: `free` becomes (d) or (a), `b` is mostly delivered as (a), `c1` as (d)); the produced class from M6 is what the bandit is credited with (C2.1(c)).
- **Feedback response** (share of answers whose E4 netlist is identical to D's): gpt-5.4: generation 1 17 % absorbed_identical (8/47), generations 2–6 15 % (31/201); gpt-5.4-mini: generation 1 26 % absorbed_identical (12/46), generations 2–6 20 % (43/217); gpt-5.6-luna: generation 1 14 % absorbed_identical (7/50), generations 2–6 12 % (29/233); gpt-5.6-terra: generation 1 23 % absorbed_identical (10/44), generations 2–6 14 % (30/211).
- **Time to verdict** (LLM answer → SEQ verdict, seconds): medians 88–113 s for terra, 206–390 s for luna and gpt-5.4, 270–1 890 s for mini; the q95 tails (10 000–18 000 s) are the multi_pipe_8bit (c1)/(d) candidates waiting for seats and for the solver.
- **Y as a screen**: AUROC of the Y area gain for E4 retention = 0.748 over 197 retained vs 528 other diagnosed candidates (threshold 0.75; best-of-three components 0.58).
- **Diagnoser check** (PLAN 3.5): 40 sampled diagnoses (stratified over the labels) cross-checked against the raw DC area reports, the recomputed gains, the fingerprint equality behind `absorbed_identical`, the fingerprint / text identity behind `duplicate` and the stack verdicts behind `nonequiv`: 40 of 40 consistent (`phase3_calibrate.py verify`; reports/data/phase3_manual_verify.json). This is a consistency check of the labels against the evidence, not a human reading of every netlist.
- **Operations**: 3 runs crashed on a global candidate-id collision (identical rewrites from different runs) and 1 on a resume race; ids are now per run and the resume is idempotent (DECISIONS 2026-09-14); the crashed generations' rows are `aborted` (8 rows).

Decisions requested:

1. **Main model.** The decision rule (`llm.calibration.decision`: retained candidates per USD, best gain ≥ 70 % of the strongest, a retained (c1) or (d)) picks **gpt-5.6-luna** by an order of magnitude (114 per USD vs 11.8 terra, 4.9 mini, 4.3 gpt-5.4) with the same best gains (42 % vs 45 % on traffic_light, equal elsewhere) and the same retained count under the adopted floors. Recommendation: luna as the main model (`llm.selected`), terra as the second model for the 30-design re-run of the main arm (PROPOSAL §4.9), mini excluded (truncation, 7.5 calls per retained). Cost consequence for Phase 5 at equal LLM calls (32 400 calls): ≈ 60 USD with luna, ≈ 550 USD with terra, ≈ 1 750 USD with gpt-5.4.
2. **Y screen.** AUROC 0.748 is at the threshold; recommendation: keep the M_noscreen arm decision open until the final numbers (multi_pipe verdicts) and, if it stays below 0.75, drop the arm as decided (G3.1) — the difference is immaterial either way.
3. **Class instruction.** Because the produced class rarely matches the requested one, the bandit's arms are effectively "prompt styles" rather than classes; the map prior of Phase 4 should be indexed by the produced class (already the credit rule). No change requested, a note for the paper.
4. **Floors during a run.** A run reads its floors at start; floors were recomputed twice during the calibration. Proposal: freeze the floor table per phase (a `floor_version` stamped on every run and diagnosis) so that later recollections never change a run's verdicts silently; re-diagnosis stays an offline sensitivity analysis.
