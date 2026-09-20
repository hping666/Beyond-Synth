# docs/PLAN.md — Phased Implementation Plan

This file is the implementation version of `docs/PROPOSAL.md`: for every phase it states what to do, the inputs, the outputs, how completion is verified, and where to stop. Module details live in `docs/spec/`; all parameters live in `config/experiments.yaml`. Phases depend on each other, but tasks within a phase may run in parallel; while waiting at a STOP gate, engineering tasks unrelated to that gate may proceed. There are no dates, only order and acceptance criteria.

Reading order: this file §0–§1 -> the current phase section -> the `docs/spec/*.md` files it references.

## 0. General conventions

- All scripts read parameters from `config/experiments.yaml`; command lines only accept selectors (which experiment, which design, which seed).
- Every EDA job is a directory: `inputs/` (RTL, SDC, scripts), `outputs/` (reports, logs, netlists, SAIF), `meta.json` (configuration, cfg_hash, git_sha, tool versions, start/end time, status, check results). Directory name = `<design_id>/<config>/<content_hash>`.
- Jobs are submitted and executed through `scripts/queue/` (daemon + SQLite job table + logs), supporting `--dry-run`, resumption, one retry on failure, and automatic backoff when license seats are exhausted.
- Every decision rule ("did this synthesis succeed", "did these two netlists converge", "which class is this candidate") has positive and negative test cases in `tests/`.
- Phase report template: `reports/TEMPLATE.md` (goal / what was done / key-number table / anomalies and handling / impact on the proposal / next steps).

## 1. Results storage (shared by all phases)

```
results/
  db/results.sqlite            structured records (schema in docs/spec/07-results-db.md)
  hidden/hidden.sqlite         hidden-configuration results; readable only by scripts/report_hidden.py
  raw/<design_id>/<config>/<content_hash>/   raw artifacts of each evaluation (DC/PT/VCF/VCS reports, logs, netlists, SAIF)
  llm/<run_id>/<gen>/<cand_id>.json          every LLM request and response (with tokens and dollars)
  candidates/<run_id>/<cand_id>.v            candidate RTL (named by content hash)
  snapshots/<phase>-<date>/*.parquet         table exports at the end of each phase
reports/<phase>.md                            phase reports
data/
  designs/<suite>/<design_id>/  original design RTL, testbench, SDC, source, license
  perturbations/<design_id>/    surface-perturbation RTL
```

Rules: append-only, never overwrite; a directory under `raw/` must have `meta.json` with `status == ok` before its record may enter `results.sqlite`; the only writer of `hidden.sqlite` is the separate process `scripts/hidden_worker.py`, and the search process does not import its module; analysis scripts read only the database, never the directories.

---

## Phase 0 — Environment and skeleton

**Inputs**: all of `eda-knowledge/`; the `flow/` scripts; this file.
**Outputs**: a runnable project skeleton; the environment section of `STATUS.md` filled; reference artifacts of one design run end-to-end through every tool.

Tasks:

0.0 First-time bootstrap (see CLAUDE.md "First-time bootstrap"): `git init` and `.gitignore`; generate the SSH deploy key and print the public key, **stop and wait for the user to add it on GitHub**; add the remote and make the first push; configure `OPENAI_API_KEY` under the user's direction and verify it with one minimal call. Acceptance: `git remote -v` points to hping666/Beyond-Synth and `git push` succeeds; `scripts/status.py` reports the OpenAI key as configured (without showing it).
0.1 Read `eda-knowledge/` (README -> 02 -> 05 -> 06 -> 04 -> 01 -> 03 -> 07), run `selfcheck.py` and `e2e.py`, write the environment facts into `STATUS.md`. Record inputs, outputs and exit codes of every `flow/` script and decide how this project calls them (wrap them in `src/eval/flow_adapter.py`; never modify the originals).
0.2 Initialize the repository layout (see the CLAUDE.md directory listing), `.venv`, `requirements.txt` (pyverilog, pandas, pyarrow, pyyaml, scikit-learn, openai, pytest), `.gitignore` (exclude `results/raw`, large artifacts under `data/`, any Synopsys files; whether the results database and snapshots enter git or git LFS is recorded in DECISIONS).
0.3 `.claude/settings.json`: deny `rm -rf results`, deny reads of `results/hidden/` (except `report_hidden.py`), deny exfiltration commands; hooks guarding critical paths.
0.4 Job queue `scripts/queue/`: daemon, job table, seat pools (DC / PT / VCF, caps from config), backoff, logs, `status.py`.
0.5 Evaluation service `src/eval/` (spec `docs/spec/01-eval-service.md`): implement and parse E1–E4, single-flag variants, H1/H2a/H2b/H3/H5, Y, PT/PrimePower; run every configuration on **one** small design and save reference artifacts to `tests/fixtures/`.
0.6 Equivalence stack `src/equiv/` (`docs/spec/03-equivalence.md`): V1–V4 on the same design; **bidirectional tests**: a known-equivalent surface perturbation must be proven, a mutant with an injected bug must be falsified. Confirm that the VC Formal SEQ and DPV app licenses are usable (job paths recorded in STATUS).
0.7 Power path: VCS simulation -> VCD -> `vcd2saif` -> DC `read_saif`/`report_power` and PrimePower, each run once; the two numbers must be of the same order of magnitude.
0.8 License check: copy the clauses of the Synopsys academic license concerning published benchmark comparisons into `docs/DECISIONS.md` and state whether Yosys-vs-DC comparisons may be published (write "unclear" if unclear).

Acceptance (all machine-checkable):
- `pytest tests/` green, and every decision rule has a positive and a negative test.
- `tests/fixtures/` holds reference artifacts for that design under E1, E1d, E2, E3, E4, E2g (E2r = E3), H1, H2a (ASAP7), H2b (sky130hd), H3 (-spg), H5, Y, Ycoevo, PT and PrimePower, each with `meta.json.status == ok`.
- Two consecutive E4 runs on the same input give bit-identical area, WNS and cell histogram (determinism check).
- SEQ bidirectional tests pass; DPV runs on at least one arithmetic module.
- `scripts/status.py` shows the queue, the three seat pools, and the budget.

**STOP G0**: report `reports/phase0.md` with the content listed in the G0 row of CLAUDE.md.

---

## Phase 1 — Design sets and constraints

**Inputs**: Phase 0 skeleton; data sources named in the papers (arXiv: Dr.RTL 2604.14989; RTL-OPT 2601.01765; CktEvo 2603.08718; RTLLM v2.0; RTLRewriter 2409.11414).
**Outputs**: inventory under `data/designs/`; knee-point constraint for every design; dev/held split; the `designs` table in `results.sqlite`.

Tasks:

1.1 Locate the dataset URLs from the papers and their code repositories, download into `data/designs/<suite>/`, record source, commit and license. If a dataset is not public (e.g. the Dr.RTL 20 designs), note it in STATUS and substitute RTL-OPT + CktEvo modules.
1.2 Inventory: per design, lines of code, ports, testbench present, SDC present; trial-synthesize with E4 and record synthesizability and failure reasons; the RTLLM v2.0 synthesizable count N under this machine's DC is taken from here. From the CktEvo repositories extract about 30 medium-size modules (hundreds to thousands of lines, preferably with self-contained interfaces).
1.3 Knee-point constraint sweep (`docs/spec/01-eval-service.md` §3): sweep 7 clock periods under E4 with Nangate45 and pick Φ_main by the rule; sweep ASAP7 and sky130hd separately (for the hidden layer). Write `designs.knee_table_json`.
1.4 Write the dev / held split into `config/experiments.yaml`: dev contains only about 20 RTLLM designs; everything else is held-out.
1.5 Tag the 8 CktEvo modules for the Sky130 sub-experiment as `cktevo_sky130`.

Acceptance:
- Every row of `designs` has suite, path, loc, tb_available, e4_synthesizable, phi_main_ns (three libraries), split.
- `reports/phase1.md` gives, per suite, the synthesizable count, the testbench count, and the distribution of knee periods.
- Spot-check 5 designs and confirm by hand that the knee choice is sensible (area–period curves attached to the report).

---

## Phase 2 — Noise floor, SEQ pilot, E4 runtime (Exp0)

**Inputs**: Phase 1 design sets.
**Outputs**: σ_D per design and configuration; baseline records of D under every configuration; SEQ runtimes and inconclusive rates per class; E4 seconds distribution; recommendation on whether screening enters the main method.

Tasks:

2.1 Perturbation generator `src/noise/` (`docs/spec/02-noise-floor.md`): 4 perturbations per type (8 for the 10 map designs); each perturbation is first proven equivalent to D by SEQ; non-equivalent perturbations are discarded and counted (the generator's bug rate is itself reported).
2.2 Run D and all perturbations under E1, E2, E3, E4, H1, H2a, H2b, H5 (H3 only for D and 4 perturbations).
2.3 Compute σ_D (robust standard deviation and q95, per configuration and metric), write the `noise_floor` table; produce the floor distribution plots and the "minimum reportable gain" table for `reports/phase2.md`.
2.4 SEQ pilot: before Phase 3, build 50 class-(c) candidates — from the RTL-OPT pipelining pairs, hand-made retiming variants of Dr.RTL designs, and one temporary LLM batch (within $10 of the Phase 3 budget) — and measure proven / falsified / inconclusive fractions and runtimes, split by (b), (c1), (c2). For the V4 clocked-datapath decision (DECISIONS 2026-09-12, spec 03 §1 guardrail 3) also record per SEQ-inconclusive candidate: whether the module is a clocked arithmetic module; whether V2's per-output offsets are constant across all random runs; whether start/valid and done/valid signals are recognisable.
2.5 E4 runtime: from the runs in 2.2 collect E4 seconds per design; with the scale parameters in `config`, compute DC hours and wall-clock at 50 seats for the full-E4 and the cascade scales. Also collect t_H3 / t_E4 per design and the agreement rate of E4 and H3 conclusions on the noise-floor set (retained / absorbed / noise per perturbation) for the G3 question whether the main scoring configuration should move to the physical-aware full-effort configuration (DECISIONS 2026-09-12).

Acceptance:
- The `noise_floor` table covers all designs × configurations × metrics; the E1–E4 fingerprints of every D (cell histogram, log summary, resource report, critical path) are in the `evaluations` table.
- Bidirectional tests: an artificially enlarged "perturbation" (changed bit width) must be rejected by SEQ; a legal renaming perturbation must be proven and its area delta must fall within the band.
- The report contains: median and distribution of σ_D; number of non-monotone cases (monotonicity statistics of D itself from E1 to E4); the three SEQ fractions; E4 seconds quantiles; DC hours for both scales; t_H3 / t_E4 and the E4-vs-H3 agreement rate.

**STOP G1, G2, G3**: the three reports may be merged into `reports/phase2.md`, with separate conclusions.

---

## Phase 3 — LLM calibration

**Inputs**: floors (rule A, floor classes) and baselines from Phase 2; the skeleton of `docs/spec/05-search.md` (residual-guided evolution, minimal version: no synthesis-rung screening, full E4, prescreen with the static prior).
**Outputs**: choice of main model; first measured run of the diagnoser; first-generation data for "rung selection".

Tasks:

3.1 Implement the minimal main skeleton (parallel-candidate hill climbing + archive, no synthesis-rung screening, full E4, asynchronous generations with resumption), the prompt templates, and the LLM client (OpenAI API, Flex, cache-friendly prefix, `max_output_tokens` and `reasoning.effort` from config, every request saved to disk). Budget caliber = equal LLM calls (DECISIONS 2026-09-14).
3.2 Implement the rule part of the M6 classifier and the M3 diagnoser (`docs/spec/04-classifier-diagnoser.md`, including `absorbed_identical`, `duplicate`, `fragile` and the same-rung attribution test); LLM review uses the cheap model. First measured run of the diagnoser with the new labels.
3.3 For each of the four candidate models in config, run K=6 × N=5 on 5 designs × 2 seeds (300 candidates per model), all through the equivalence stack and E4.
3.4 Per model, report: V1/V3 pass rates, class distribution (whether (c1)/(d) appear) and the requested-class → produced-class confusion matrix, E4 retention fraction (headline and the materiality sensitivity row; `proven_sim_only` apart), best retained gain per design (offset designs flagged), response rate to "absorbed" diagnoses, LLM calls, dollars, DC hours and VC Formal hours per retained candidate, time-to-verdict distributions and inconclusive rates per class, wall-clock per generation.
3.5 Recommend a model by the decision rule in config; also sample 40 of the 300 × 4 diagnoses for manual verification (in `reports/phase3.md`).

Acceptance:
- LLM spend ≤ the Phase 3 cap in config; every request has a saved record with token counts.
- The four-model comparison table is complete; the diagnoser's manual agreement rate is reported.
- The predictive power of `Y for E4 retention` (AUROC) is computed once on these 1200 candidates (E1 / E2 only as a report column); if AUROC(Y) < `screen.auroc_min` the M_noscreen arm is dropped and its budget reallocated to starting points (DECISIONS 2026-09-14 G3.1).

**STOP G4**.

---

## Phase 4 — Exp1: ladder and map (C1)

**Inputs**: the main model; Phase 2 baselines; RTL-OPT 36 pairs, RTLRewriter 20 pairs and 12 LLM samples.
**Outputs**: map v1; retention predictor; diagnoser validation; re-evaluation of the literature settings table; static-rule misclassification rates.

Tasks:

4.1 Use B0 (main skeleton + Y-caliber fitness, gpt-5.6-luna) to generate 30 proven candidates on each of 10 held designs (CktEvo 5 + Dr.RTL 3 + RTL-OPT 2, config `exp1.designs`, selected by `scripts/phase4_sets.py`: measured floors required; DECISIONS 2026-09-14 C1 scope — RTLLM is out of the C1 claim's scope and serves only as the calibration dev set and as the out-of-scope contrast layer of the map, provided by the Phase 3 candidates), 300 in total; LLM cap from config. The 10 Exp1 designs never serve as Phase 5 starting points (`design_sets.phase5_excluded`).
4.2 For the 300 candidates + 72 RTL-OPT objects + 40 RTLRewriter objects + 12 samples: run E1–E4, the attribution rungs E1d / E2r / E2g, H1, H2a, H2b, H3, H5, PT (H4); supplementary: O0–O2 and Ycoevo.
4.3 Classify all objects with M6; diagnose all objects with M3 (including absorption rung and capability attribution, under the permanent-absorption definition).
4.4 Map v1: retention rate and gain distribution by rewrite class (with sub-tags) × rung × hidden configuration; retention curves; list of non-monotone cases.
4.5 Retention predictor: features (class, g_E1, g_E2, E1 fingerprint convergence, register-count change, AST diff size) -> E4 retention; leave-one-design-out cross-validation; report AUROC, precision/recall, miss rate; also the class-blind version.
4.6 Diagnoser validation: manually check 30–50 per class; for "absorbed", reproduce with single flags (apply only `-retime` or `-gate_clock` to D and check whether the fingerprint matches C). The M6 rule validation was moved before Phase 4 (DECISIONS 2026-09-14): a stratified sample of at least 60 Phase 3 candidates over produced classes, emphasis on the (d) versus (a)/(b) boundary and on (c1); a (d) label requires a change of the operator set or of the dataflow topology, not a large diff alone; rule-vs-human agreement reported, rules revised, Phase 3 candidates re-labelled. Done 2026-09-14 (DECISIONS; reports/phase3.md §8): 60 candidates read by hand (protocol in reports/data/phase3_m6_human.json); rules v1 agreed on 23 / 60 with a (d) precision of 29 %, rules v2 (`src/classify/rules.py`: (d) only with an operator family gained or a ≥ 3× change of the longest combinational path; flip-flop bits after `opt`; (c1) needs bits and register cells to change) on 40 / 60 with a (d) precision of 14 / 14 and a recall of 14 / 21; every Phase 3 candidate re-labelled (`class_rule_v1` keeps v1). The remaining static-rule limits (nonequiv timing changes, buffer / schedule re-organisations without operator or depth evidence, unobservable-state removals) are the cases for the LLM review of spec 04 A.2 step 2, to be decided for Phase 4 / 5.
4.7 Literature settings re-evaluation: for RTL-OPT 36 pairs and RTLRewriter 20 pairs, the number of pairs where the optimized version is better under each of E1–E4, side by side with the papers' numbers.
4.8 Static-rule misclassification rates: with the static rule "no syntactic/coding optimizations, only architectural rewrites", compute the fractions "forbidden by the rule but retained" and "allowed by the rule but absorbed".
4.9 Motivating figure: re-run a barrel-shifter-style (structural mux -> behavioral) or hand-written clock-gating candidate through E1–E4. Done 2026-09-15 with the two objects the data selected (`phase4_exp1.py motivating`, reports/data/phase4_motivating.md): the RTLRewriter memory_sharing rewrite (41 % smaller at E1, reproduced by compile_ultra at E2) and a luna state re-encoding of ticket_machine (58 % smaller and retained at E4). The diagnoser validation of 4.6 was done the same day (reports/data/phase4_diagnoser_check.md: 187 / 187 sampled diagnoses agree with an independent re-derivation from the raw DC reports; single-flag reproduction 14 of 74 absorbed objects).

Acceptance:
- `snapshots/phase4-*/` contains the four tables evaluations, candidates, diagnoses, map.
- `reports/phase4.md` contains: map heatmap; retention curves; σ_D comparison; predictor metrics (with the class-blind control); diagnoser agreement rate; literature re-evaluation table; misclassification rates; motivating figure.
- One paragraph of conclusion: which map shape (concentrated / near-zero / diffuse) and on what evidence.

**STOP G5**.

---

## Phase 5 — Exp2: residual-guided evolution comparison (C2) + hidden layer (C3)

Deferred to the start of Phase 5 (DECISIONS 2026-09-14): whether H1/H3/H5 run on all E4-evaluated candidates rather than accepted candidates plus a 10 % sample. Phase 5 reports the requested-class → produced-class confusion matrix.

**Inputs**: conclusions of G3–G5 (screening on/off, main model, predictor); scale parameters in `config`.
**Outputs**: retained-gain-vs-DC-hour curves; speculation rates; Dr.RTL re-implementation arm and original reference; Sky130 sub-experiment.

Tasks:

5.1 Full search skeleton (`docs/spec/05-search.md`): screening, online predictor updates, τ control, audits, feedback blocks, operator bandit, archive, restarts, budget accounting. Bidirectional tests: a candidate that must be absorbed (pure renaming) must be stopped at the screening rung; a known-retained candidate (the RTL-OPT optimized version) must be promoted and diagnosed as retained.
5.2 Arms: B0, B1@E4, B2, M, Dr.RTL-reimpl (B2 + Dr.RTL's prompts and skill learning, same model); M-noscreen was dropped at G4 (AUROC(Y) 0.748 < 0.75, DECISIONS 2026-09-14) and its budget went to starting points (36). Main model gpt-5.6-luna; the second model gpt-5.6-terra runs arms M and B2 on all starting points (model-independence check on the full head-to-head comparison, ≈ 200–250 USD); ablations on luna only. Number of starting points, seeds, candidates per design = config; the primary caliber is equal LLM calls (DC and VC Formal hours reported). Report B1@E4's produced-class distribution next to M's, since the static complement prompt is subject to the same weak instruction following (requested → produced agreement 19–21 % in Phase 3), and state this when interpreting M versus B1@E4. The starting-point pool excludes the 10 Exp1 designs (`design_sets.phase5_excluded`).
5.3 Hidden layer: `scripts/hidden_worker.py` as a separate process; for every run's accepted candidates run H1, H2a, H2b, H3, H5 and PT; also a random 10% of rejected candidates; write `hidden.sqlite`.
5.4 Dr.RTL original reference row: on 5 Dr.RTL designs, run once with Claude Code + Claude Opus (the user's subscription) following its published workflow, with equivalence checking replaced by VC Formal SEQ; a separate row, annotated as a different LLM. This row is triggered manually by the user and does not consume the OpenAI budget.
5.5 Sky130 sub-experiment: 8 CktEvo modules, visible layer sky130hd + `compile_ultra -retime -timing_high_effort_script` (CktEvo's setting), run M and B2, report side by side with CktEvo's 1.77% (noting repository-level vs module-level).
5.6 (superseded 2026-09-14: equal LLM calls is the primary caliber of every arm, C2.7; the DC-hour view is reported from the same runs.)

Acceptance:
- Every run has budget and actual DC hours, dollars and status in the `runs` table; every accepted candidate of every run has records in `hidden.sqlite` (100% coverage).
- `reports/phase5.md` (visible part by `report_phase.py`, hidden part by `report_hidden.py`) contains: retained-gain-vs-DC-hour curves per arm (E4); curves under hidden configurations; speculation rate per configuration and combined; retained candidates per DC hour; SEQ pass rate per class; operator-distribution drift; fraction of expert gain recovered on RTL-OPT starting points; Dr.RTL head-to-head; Sky130 sub-experiment.
- Success criteria (PROPOSAL §7.2) reported item by item.

---

## Phase 6 — Ablations, final map, physical layer, paper tables

Tasks:

6.1 Ablations (30-start subset, 3 seeds, same model): no screening; fixed screening rung and fixed τ; class-blind predictor; no diagnosis feedback (scalar only); no change to operator credit; no noise truncation; no online rung attribution; no map prior; fitness rung lowered to E2 / E1; no power dimension; (c1) excluded; skeleton replaced by COEVO and by REvolution (one row each, via `src/search/skeletons/`).
6.2 Final map: aggregate accepted candidates of all arms into the three-axis map; compare with the Phase 4 map.
6.3 Physical layer: place and route the final designs with ORFS (`docs/spec/06-hidden-layer.md` §4), report the shrinkage from E4 to post-layout signoff; report the retention fraction under the open-source reproduction layer O.
6.4 Paper tables and figures: `scripts/paper_tables.py` generates all tables (LaTeX) and figures (PDF) from snapshots, each annotated with the source snapshot and git sha.
6.5 Release package: scripts, SDCs, library configuration notes, candidate RTL, results database (including the hidden table), map data, predictor, diagnoser, open-source ladder and reproduction-layer scripts; Synopsys files excluded.
6.6 Ablation recorded 2026-09-19 (DECISION 2026-09-19 (k) item 4), proof-latency-bound designs (median proof latency above the 1 800 s generation window in Phase 5: SPI, simple_spi, cpu at least): a verdict-synchronous cadence — generate the next round only when at least 60 % of the previous generation has a verdict, capped at 4 h per round — against the Phase 5 cadence, to measure informed versus blind search on those designs (in Phase 5 the archive stayed empty during generation for every arm on them; parents were D; the search reduced to E4-guided one-shot rewriting).
6.7 Proof-order ablation recorded 2026-09-19 (DECISION 2026-09-19 (k) item 4): a map_by_name-first proof for classes a and b — targeted at the class-b inconclusive concentration under harness_version 2 (SPI 99 %, simple_spi 84 %) — against the Phase 5 proof order; measures the inconclusive share and the seat-hours per proof.
6.8 Lint before proof, recorded 2026-09-19 (DECISION 2026-09-19 (o) item 2): a Yosys `check -assert` lint at V1 that rejects multi-driven nets, duplicate definitions and out-of-range indices (the ELAB-366 / ELAB-298 / VER-262 / LINK-3 cases of Phase 5: eight candidates proven by VC Formal and rejected by DC at elaboration) before any proof is spent; the rejection becomes a V1 outcome ("synthesis-rejected") with the lint message as feedback.
6.9 Floors for the 13 Phase 5 designs on the pooled floor, recorded 2026-09-20 (REQUEST 2026-09-20 (d) item 4): measure their floors under harness_version 2 — 8 text-level renames (no Pyverilog parse needed) + 8 reorders each, the re-print P0 re-proven under v2 where its rejection was the harness (router, LSTM) — and report Phase 5 retention under the measured floors as a sensitivity row; the Phase 5 floors stay frozen (floor_version phase4). **Status 2026-09-20 05:55 (REQUEST (e) 3):** text-level renames (8 per design) and reorders (8 on ten designs; btb 6, vga_wb_slave 5, stall_control_unit 0) generated with the parser-free scanner (src/noise/textscan.py, rename_text.py, reorder_text.py); the offline pool's `floor6` group proves them under harness_version 2 and runs their E4 once `offline_pool.proofs_enabled` is on (after the small tier's search runs); `scripts/phase6_floors.py` writes floor_version phase6 without requiring P0; `report_power_basis.py --floor-version phase6` gives the sensitivity row.
6.10 SAIF-based E4 baselines for the same 13 designs, recorded 2026-09-20 (REQUEST 2026-09-20 (d) item 3): D's E4 baseline at Φ_main carries no SAIF power there (the design SAIF comes from the perturbation pipeline, which these designs never entered), so every power gain on them is on DC's default-activity basis; build D's SAIF from the V2 lock-step stimulus and re-run D's E4 once per design, after which the SAIF basis applies to every candidate record that carries one. **Status 2026-09-20 05:55 (REQUEST (e) 2):** done by the offline pool's `d_saif` group (D-vs-D lock-step simulation → D.saif → E4 of D with SAIF, `evaluations.offline_baseline = 1`, is_baseline 0); 12 of 13 records in (drrtl_aes running); the SAIF-basis recomputation follows (reports/paper_sec3_power_basis_saif.md).

Acceptance:
- Ablation table complete, each row with mean and standard deviation over 3 seeds.
- `reports/phase6.md`; tables and figures under `paper/` regenerate from snapshots with one command.

---

## Appendix A: Arm definitions

| Arm | Fitness | Synthesis-rung screening | Feedback | Credit | Notes |
|---|---|---|---|---|---|
| B0 | Y caliber | none | scalar | any positive gain | EvolVE-style; accepted candidates also run E4 and the hidden layer |
| B1@E4 | E4 | none | scalar + static complement prompt | any positive gain | strongest "intuitive" baseline |
| B2 | E4 | none | scalar | any positive gain | naive commercial-in-the-loop |
| M | E4 retained gain (rule-A floor, zero inside the floor) | none; classifier prescreen (`prescreen`) | synthesizer verdict (absorbed / absorbed_identical / duplicate / noise / harmful with locus / retained / fragile) + map prior | retained / trade-off improvement only, credited by the produced class | this paper: residual-guided evolution (DECISIONS 2026-09-14) |
| M-noscreen | same as M | Y rung with automatic τ, only if AUROC(Y) ≥ `screen.auroc_min` | same as M | same as M | isolates the contribution of a synthesis-rung screen; dropped (budget to starting points) when Y does not qualify |
| Dr.RTL-reimpl | E4 | none | Dr.RTL prompts + skill learning | — | re-implementation with the same model |

Budget caliber for every arm: equal LLM calls (`scale.budget.llm_calls_per_run`); DC and VC Formal hours are reported. Pipeline order for every arm: V1 → testbench → V2 (SAIF) → V3 SEQ → E4 → diagnosis.

## Appendix B: Metric definitions

Retained gain g = PPA(E4(D)) − PPA(E4(C)), three components; retained = some component > t_D(E4) and no component < −t_D(E4), with t_D the rule-A threshold of spec 02 §4 (every headline number is also reported under the fixed materiality threshold area 1 % / power 2 % / WNS 1 % of the period); on spread / offset designs the gain must in addition exceed the acceptance envelope (else `fragile`); trade-off = some component > t_D and some component < −t_D; speculation rate = fraction of visible-layer accepted candidates whose gain under some hidden configuration is ≤ 2σ_D(H) or negative; recovered expert-gain fraction = M's retained gain on an RTL-OPT suboptimal start / the retained gain of that pair's optimized version; retained candidates per DC hour = number of retained candidates / DC hours consumed by the run.
