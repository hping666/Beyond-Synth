# spec 04 — Rewrite classifier M6 and diagnoser M3 `src/classify/`, `src/diagnose/`

## A. Classifier M6

Input: RTL of D and C. Output: main class, sub-tags, confidence, rule basis.

### A.1 Main classes

| Class | Definition | Rule criterion (AST/dataflow diff with Pyverilog; register counts from the DFF count of Yosys `proc; opt; stat`) |
|---|---|---|
| (a) combinational rewrite | only combinational expressions / muxes / constants change | flip-flop bits (Yosys `proc; flatten; opt`), register-name set and the assignment targets of clocked always blocks (blocking and nonblocking) unchanged; no (d) evidence |
| (b) latency-preserving coding/structural refactor | always-block merge/split, state encoding, resource sharing, bit width, precomputation, strength reduction; register count or names may change but latency does not | V2 identical every cycle; register names / targets change, or the flip-flop bits change inside the same register cells (widths) |
| (c1) latency-preserving sequential restructuring | retiming-style register movement/duplication | V2 identical every cycle; flip-flop bits **and** the number of register cells change (register positions move in the dataflow graph) |
| (c2) latency / interface-timing change | pipeline stages added/removed, multi-cycling | V2 finds a constant offset k > 0 |
| (d) algorithm / architecture replacement | different algorithm, datapath organization, buffer structure, schedule | **rules version 2 (DECISIONS 2026-09-14):** an operator family (`classify.operator_families`: multiply / divide, add / subtract, variable shift; memory cells excluded because Yosys turns small arrays into register lists by indexing style) present in C's word-level RTLIL histogram and absent in D's, or the longest combinational path (`ltp -noff`, cells) changed by `classify.d_depth_ratio` or more; the text diff size alone never yields (d) (a wide rewrite without such evidence keeps its structural class and is flagged for review); or LLM review decides |

Sub-tags (multi-select): bit-width reduction, precomputation/LUT, operator strength reduction, control simplification, resource sharing, state encoding, clock gating, pipelining, algorithm replacement, buffer/memory organization, and the "knowledge the synthesizer lacks" sub-classes: value range, mutual exclusivity, algebraic identity, cross-cycle invariant.

### A.2 Procedure

1. Rule labeling (explainable; the triggered rules are recorded).
2. When rule confidence is below threshold or rules conflict, LLM review (cheap model, Batch): given D, C, the diff summary and the class definitions, return JSON (class, sub-tags, one-sentence basis). Record `class_rule, class_llm, class_final, confidence`. Implemented 2026-09-14 (`src/classify/review.py`, prompt `src/search/prompts/m6_review.md`, queue kind `llm`; DECISIONS 2026-09-14 item 1): the review set is every rules-v2 candidate with confidence below `classify.review_below`, or flagged as a wide rewrite without operator / depth evidence, or a nonequiv candidate classed (b) / (c1) (the timing-change category), or a (c1) whose flip-flop bits moved by at most two (the redundant-register category); the model is `llm.selected` on the Flex tier (the Batch API is not wired into the client), the answer is stored in `candidates.review_json`; `class_final` takes the review's (a) / (b) / (c1) / (c2), while (d) stays defined by the tool evidence of the rules (an LLM (d) is recorded in `class_llm` only).
3. Calibration: manual verification of samples in Phases 3/4; report rule-vs-human and LLM-vs-human agreement; revise rules on misclassifications (record revisions in DECISIONS). Done once before Phase 4 on 60 Phase 3 candidates (reports/data/phase3_m6_human.json, protocol included; reports/data/phase3_m6_agreement.json): rules v1 agreed on 23 of 60 with a (d) precision of 29 %, rules v2 on 40 of 60 with a (d) precision of 14 / 14 and a recall of 14 / 21 (DECISIONS 2026-09-14). The known limits of the static rules (output-timing changes of nonequiv candidates, buffer / schedule re-organisations without operator or depth evidence, unobservable-state and redundant-register removals) are the cases step 2 is for.

## B. Diagnoser M3

Input: C's E4 record, D's E4 baseline record, σ_D, available lower-rung records (E_s, plus sampled E2/E3/single-flag runs), the M6 class. Output: five-way label, rung/capability attribution, evidence, feedback block.

### B.1 Evidence

- **Retained-gain vector** g (area, timing, power), relative, compared with the rule-A threshold t_D(E4) of each metric (spec 02 §4; DECISIONS 2026-09-14 G1.1). A fixed materiality threshold (area 1 %, power 2 %, WNS 1 % of the period) gives the sensitivity row of every headline number. Power is compared on one basis only (2026-09-15): SAIF-based power when both records carry it, otherwise DC default-activity power on both sides, never one against the other; the evidence records `power_basis`. A metric of a design without a measured floor component takes the pooled minimum of the configuration as its threshold (G1.2); no metric is ever judged against a zero band.
- **Fingerprint similarity**: weighted Jaccard of cell-type histograms (threshold config: `diag.fp_jaccard`, calibrated in Phase 4); whether the area delta lies within that rung's σ_D; whether critical-path endpoints coincide. All three satisfied -> "converged".
- **Log diff**: datapath-extracted blocks, retimed registers, ICG count, ungrouped modules, shared resources — one summary each for D and C, diffed item by item.
- **Resource diff**: DesignWare components and implementations (e.g. DW02_mult Booth) present in D but absent in C -> evidence of "blocks synthesis".
- **Path mapping**: which RTL lines the critical path of C falls on; whether newly added registers sit on the critical path.

### B.2 Decision order

1. V3 not proven -> `nonequiv`, stop (a `proven_sim_only` candidate is diagnosed but reported apart and never in the headline).
2. E4 fingerprint identical to D's (equal cell histogram, area and cell count) -> `absorbed_identical`; no simulation or proof is needed for the verdict, a random `diag.absorbed_identical_seq_audit_frac` = 10 % is still sent through SEQ (audit fields in spec 07).
3. E4 fingerprint identical to an earlier candidate's of the same run -> `duplicate` (the run keeps its convergence classes; `duplicate_of` records the first candidate).
4. Some component g > t_D and no component g < −t_D -> `retained`; on a spread / offset design the gain must also exceed the envelope of `search.acceptance_envelope.n_perturbations` surface perturbations of the candidate itself at E4 (C2.1(d)), otherwise the label is `fragile` (reported, not credited, kept out of the archive).
5. Fingerprint converged at E4 -> `absorbed`; rung attribution compares the candidate with D **under the same rung** and never assumes that a higher rung dominates a lower one (DECISIONS 2026-09-14 G1.4; area is not monotone from E1 to E4): if converged already at E_s -> absorbed by E_s; else if E2/E3/single-flag records exist, take the lowest rung "from which all higher rungs converge" and attribute the capability from the single-flag runs; else rung = "after E_s", capability = map prior (marked `prior`).
6. Fingerprint not converged and all three components within the band -> `noise`.
7. Some component g < −t_D and none > t_D -> `harmful`; if the resource diff shows datapath extraction / DesignWare in D but not in C -> sub-label `blocks_synthesis`; otherwise locate the loss with register counts, ICG counts and path mapping.
8. Some component > t_D and some < −t_D -> `tradeoff`, with the dimensions named.

Every label on an offset design carries the flag `offset_design = 1` in the tables and in the map.

### B.3 Feedback block (JSON, injected into the prompt)

```json
{"class": "(b)", "subtags": ["resource_sharing"],
 "diagnosis": "absorbed", "rung": "E2", "capability": "resource_sharing", "attribution": "measured|prior",
 "evidence": {"dA_pct": -0.4, "dWNS_ns": 0.0, "dP_pct": 0.2, "sigma2_pct": 1.6,
              "fp_jaccard": 0.98, "log_diff": "D@E2: shared 1 multiplier; C@E2: 1 multiplier",
              "missing_resources": [], "extra_regs": 0},
 "prior": {"absorb_prob": 0.9, "retained_examples": ["bitwidth_reduction (value-range)"]}}
```
Feedback states evidence only; suggestions come solely from the prior table (Phase 4 map). The block also carries `floor_class` and, for `absorbed_identical` / `duplicate`, the matching record. Prescreened candidates (spec 05 §3) receive the prior's block immediately; screened-out candidates of the synthesis-rung experiments receive a reduced block: `{"diagnosis":"screened_out","rung":"E_s","fp_converged":true,...}`.

### B.4 Operator credit

`retained` or `tradeoff` with a Pareto improvement over the parent -> the class bandit is credited 1; everything else 0. The credit goes to the **produced** class from M6, not to the requested class (DECISIONS 2026-09-14 C2.1(c)); the requested-class → produced-class confusion matrix is reported in Phase 3 and Phase 5.

### B.5 Validation (Phase 4)

- Manual verification of 30–50 per class (reading both netlists and logs); report agreement.
- Single-flag reproduction of "absorbed": apply only `-retime` / `-gate_clock` to D and check whether the fingerprint matches C; report the reproduction rate.
- Negative cases: a pure-renaming candidate must be `absorbed@E1`; the RTL-OPT optimized version relative to its suboptimal version must be `retained` (for most pairs); a hand-written slow multiplier must be `harmful/blocks_synthesis`.

### B.6 Limitations (stated in the paper)

Fingerprint convergence is a proxy for "equal quality"; structurally different netlists with equal PPA are recorded as `noise` rather than `absorbed`; the granularity of log fields depends on the DC version.
