# spec 05 — Residual-guided evolution `src/search/` (C2)

C2 is named **residual-guided evolution** (DECISIONS 2026-09-14). Its four mechanisms: (a) fitness = retained gain with the rule-A floor of spec 02, zero inside the floor; (b) feedback = the synthesizer's verdict (absorbed with capability attribution, absorbed_identical, duplicate, noise, harmful with locus including `blocks_synthesis`, retained, fragile) instead of a scalar; (c) operator selection = a class bandit initialised from the map prior, credited only for retained or trade-off improvements and credited by the produced class from M6, not the requested class; (d) acceptance = on spread / offset designs a candidate's gain must exceed the envelope of 2–3 surface perturbations of the candidate itself at E4. Synthesis-rung screening is not part of the main method (G3.1); the word "screening" is reserved for it. The pipeline order is conventional: V1 → testbench → V2 (SAIF) → V3 SEQ → E4 → diagnosis.

## 1. Main skeleton: parallel-candidate hill climbing + small archive

State: archive A (three-objective Pareto front, at most `search.archive_size`=5, holding proven candidates already evaluated at E4); class bandit (five arms: (a), (b), (c1), (d), free; initialised from the map prior); budget B = `scale.budget.llm_calls_per_run` LLM calls (DC and VC Formal hours are recorded, not budgeted); the prescreen prior; audit records; the convergence classes of the run (fingerprints of every E4-evaluated candidate).

Per generation:
1. Parent selection: sample from A by crowding distance; after `search.stall_gens` generations without retained improvement -> switch parent / restart (another element of A, or D).
2. Generation: the bandit draws N classes (UCB-softmax, config), one prompt per class, the LLM generates N candidates in parallel; each candidate carries the feedback blocks of its parent lineage (the most recent `search.feedback_depth`).
3. M6 classification (produced class).
4. Prescreen (`config: prescreen`): a candidate whose produced class has a map-prior absorption probability ≥ `prescreen.p_min` is not evaluated with probability 1 − `prescreen.audit_frac` and receives immediate feedback with the prior (label `prescreened`, audited candidates continue).
5. Equivalence stack V1 → testbench → V2 → V3 (V4 for clockless modules); class-aware SEQ caps (spec 03); non-proven candidates are recorded and discarded from the population, `inconclusive` ones are reported.
6. E4 evaluation; M3 diagnosis (spec 04 §B.2, including `absorbed_identical`, `duplicate`, `fragile`); feedback blocks written; bandit credit by the produced class.
7. Acceptance check on spread / offset designs: `search.acceptance_envelope.n_perturbations` surface perturbations of the candidate are generated and run at E4; the candidate's gain must exceed their envelope, otherwise `fragile`.
8. Archive update (Pareto front); budget deduction (LLM calls); stop when the calls are exhausted or K generations are reached.
9. Accepted candidates (those that ever entered the archive) are submitted to the hidden-layer queue (handled by `hidden_worker`; the search process never reads the results).

Generations are **asynchronous** (§7): the next generation is built from the verdicts available at the time; late verdicts update the archive, the bandit credit and the lineage feedback when they arrive.

## 2. Prompt structure (cache-friendly)

Stable prefix (fixed per design): system prompt -> task definition and output format (return RTL plus a one-sentence transformation note, JSON-wrapped) -> D's RTL -> D's E4 summary (area/WNS/TNS/power, critical path mapped to RTL lines, resource-report summary, compile-log summary: what DC already did) -> noise floor (minimum reportable gain) -> map prior table (Phase 4 output; B1 uses the static complement text instead).
Variable suffix: parent RTL (if not D) -> feedback blocks of the parent lineage -> the class instruction for this call.
Static complement text (B1 only): an explicit list of "the synthesizer does this, do not do it" rewrites and "do this" directions; fixed content, no candidate-level evidence.
Template files: `src/search/prompts/*.md`, versioned; changes are recorded in DECISIONS.

## 3. Prescreen, and synthesis-rung screening as an experiment only

**Prescreen (classifier-based, part of the main method; DECISIONS 2026-09-14 C2.3)**: after M6, the produced class's map-prior absorption probability decides whether the candidate is evaluated at all (§1 step 4); the audited fraction measures the prescreen's miss rate, which is reported per design.

**Synthesis-rung screening (not in the main method; DECISIONS 2026-09-14 G3.1)**: E4 is cheap for 90 % of the designs and no DC rung is cheaper where E4 is expensive (Phase 2 §3). The only candidate screening rung is Y (`screen.candidates_es = [Y]`). Its AUROC for E4 retention is measured in Phases 3 / 4 from the E4-evaluated candidates; if AUROC < `screen.auroc_min` the M_noscreen arm is dropped and its budget reallocated to starting points (`screen.noscreen_arm`). If Y qualifies, the earlier rung-control rules (τ from the E4 quota, audit miss-rate correction, per-design predictor) apply to the M_noscreen comparison only.

## 4. Budget accounting

The primary caliber is **equal LLM calls** (`scale.budget.primary`, `scale.budget.llm_calls_per_run` = K × N; DECISIONS 2026-09-14 C2.7). DC hours (E4, sampled single-flag runs, the acceptance-envelope runs), VC Formal hours and LLM dollars are recorded per generation in the `runs` table and reported; the DC-hour equivalent `scale.budget.k_e4_equiv` × t_E4(D) is a reporting quantity only. Efficiency metric = LLM calls per retained candidate. LLM dollars stay bounded by the phase cap.

## 5. Implementation differences between arms

| Arm | Fitness source | Synthesis-rung screening | Feedback block | Bandit credit |
|---|---|---|---|---|
| B0 | three-component gain at Y caliber (no truncation) | none | scalar (Y numbers) | any positive gain |
| B1@E4 | three-component E4 gain (no truncation) | none | scalar + static complement text | any positive gain |
| B2 | three-component E4 gain (no truncation) | none | scalar (E4 numbers) | any positive gain |
| M | E4 retained gain (rule-A floor) | none (prescreen only) | synthesizer verdict + prior | retained / trade-off improvement, by produced class |
| M-noscreen (conditional) | same as M | Y rung, only if AUROC(Y) ≥ `screen.auroc_min` | same as M | same as M |
| Dr.RTL-reimpl | E4 scalar | none | Dr.RTL's top-k path feedback + in-run skill learning (implemented as in its paper) | — |

Dr.RTL-reimpl as implemented (2026-09-15, config `search.arms.DrRTL_reimpl`, `search.drrtl`): B2's fitness, archive and any-gain credit; the system prompt is the Dr. RTL optimizer / timing-analyzer role (`prompts/search_system_drrtl.md`); the cacheable prefix carries D's RTL, the E4 summary and the released Dr. RTL skill library (`data/sources/Dr_RTL/.claude/skill/rtl-opt/skill.md`, pattern–strategy entries with confidence tiers) in place of the map-prior table; each call carries the timing-analysis block — the K = 10 worst paths of the parent's (or D's) E4 report with slack, the critical path's cell chain, a diversity strategy rotated per call (path selection top_slack / random / module / endpoint_cluster × focus combinational / sequential / mixed) — and the run's learned skills, instead of a class instruction (the produced class is credited as for every arm); after every built round one skill-extraction call (group-relative: the round's attempts, notes, verdicts and PPA deltas → at most three pattern–strategy entries with a confidence tier) appends to the run's learned skills; it is charged to the equal-call budget before the next round's calls are counted, so the last round is never distilled. Dr. RTL's own timing score (0.5 WNS + 0.35 TNS + 0.15 area) is not used as fitness: at the knee period WNS is ≈ 0 for D and the normalisation is undefined; the arm is compared under the same three-component gain as every other arm.

Accepted candidates of B0/B1/B2 are also sent to E4 (B0) and the hidden layer so that all arms are compared under the same configurations.

## 6. Skeleton plugins (skeleton independence)

`src/search/skeletons/`: `hillclimb.py` (main), `coevo.py`, `revolution.py`. The latter two are adapted for RTL-to-RTL (correctness as a binary gate; COEVO's three-objective non-dominated sorting; REvolution's Fail population removed), with the same interface: `propose()`, `select()`, `update()`. M and B2 run once on each skeleton (30-start subset).

## 7. Run outputs and asynchronous generations

One row in `runs`; one row per candidate in `candidates`; one row per candidate in `screening` (M-noscreen only); one row per E4 candidate in `diagnoses`; all requests/responses under `results/llm/<run_id>/`; all candidate RTL under `results/candidates/<run_id>/`; per-generation `gen_summary.json` (archive, bandit probabilities, prescreen decisions, consumption, pending verdicts).

**Asynchronous generations (DECISIONS 2026-09-14 C2.6).** A generation is *issued* when its N candidates are submitted to the equivalence and E4 queues; it is *built* from the verdicts available when the next generation is due (the LLM calls of generation g+1 are made as soon as the bandit has the credits of the verdicts that arrived, never waiting for the class-aware SEQ caps). A verdict that arrives after its generation was built (late verdict) updates the archive (Pareto insertion), the bandit credit of its produced class and the lineage feedback of its descendants when it arrives; a late `retained` candidate becomes a parent from the next selection on. `gen_summary.json` records, per generation, the set of pending candidate ids and the timestamp at which it was built.

**Resumption semantics.** State is persisted after every build (`gen_summary.json`) and after every verdict (the `candidates` / `diagnoses` rows). On resume: (1) load the last built generation; (2) re-read every candidate row: verdicts that arrived while the process was down are applied in `finished_at` order exactly as late verdicts; (3) candidates still pending are re-attached to their queue jobs (never re-submitted unless the job is failed); (4) the LLM calls of an issued-but-unbuilt generation are not repeated: their saved responses are reloaded from `results/llm/<run_id>/`. A resumed run must reproduce the same archive and credits as an uninterrupted one given the same verdict arrival order (test in §8).

## 8. Tests

- Negative: a pure-renaming candidate must be diagnosed `absorbed_identical` (or `absorbed@E1` when its fingerprint differs); the RTL-OPT optimized version as a candidate must be `retained`.
- Rung attribution: a candidate that converges with D at E2 but not at E1 is `absorbed@E2`; one whose E1 result is better than D's E1 result but whose E4 result equals D's is `absorbed` (never `retained` from a lower rung).
- Asynchronous generations: with a simulated verdict stream, a late `retained` verdict enters the archive and credits the bandit; the resumed run matches the uninterrupted run.
- Budget: with simulated t_E4 and a fixed candidate stream, confirm stop on exhaustion and correct quota/τ computation.
- Bandit: probabilities drift toward the high-reward arm under synthetic rewards.
- Resumption: kill the process mid-run; resuming from `gen_summary.json` yields identical results.
- LLM client: requests saved, tokens counted, cost accumulated, raises and stops when the phase cap is reached.
