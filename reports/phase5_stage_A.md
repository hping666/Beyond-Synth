# Phase 5 report (Stage A — the large tier) — interim

**Interim** (368 evaluations pending on the reported tiers: large 368; rows marked † are incomplete and `pending` stands where a value would otherwise read 0 — DECISION 2026-09-18 D1 / D3).

Generated 2026-09-21T03:46 by scripts/report_phase.py phase5 --stage A (git d38e61a0c8b1, cfg f857d446d282). Data: reports/data/phase5_visible_A.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 15 / 18 / 18 | 900 | 2.98 | 51.2 | 179.9 |
| large | gpt-5.6-terra | B0 | 15 / 18 / 18 | 900 | 30.72 | 27.7 | 490.4 |
| large | gpt-5.6-terra | B1_E4 | 15 / 18 / 18 | 900 | 34.70 | 60.6 | 470.6 |
| large | gpt-5.6-terra | B2 | 15 / 18 / 18 | 900 | 34.25 | 60.6 | 482.2 |
| large | gpt-5.6-terra | DrRTL_reimpl | 15 / 18 / 18 | 900 | 35.32 | 53.6 | 180.9 |
| large | gpt-5.6-terra | M | 15 / 18 / 18 | 900 | 31.32 | 62.2 | 450.7 |

Incomplete rows: 6 of 6 — runs still open or evaluations pending (proofs, offline simulations, E4 records); their result cells read `pending` or carry †.

## 0a. Design notes and disclosures (DECISION 2026-09-18 (b) items 5c–5e, D1; DECISION 2026-09-19 (k) item 3, (l) item 4, (n) item 1; REQUEST 2026-09-20 (e) item 1)

| design | tier | note |
|---|---|---|
| cktevo_hsm__hsm | large | mixed (sim_fail 65 %, inconclusive 30 %); power on this design is on the default-activity basis for all arms during the search (REQUEST 2026-09-20 (e) 1: D's E4 baseline carries no SAIF power; m3.power_basis compares default with default) |
| cktevo_nn_engine__spikeNeuron8_H7 | large | evaluation failed (DC rejected): 1 proven candidate (LINK-3; M 1) — rejected by DC at elaboration, terminal, counted as resolved (DECISION 2026-09-19 (n) 1) |
| cktevo_risc__btb | large | power on this design is on the default-activity basis for all arms during the search (REQUEST 2026-09-20 (e) 1: D's E4 baseline carries no SAIF power; m3.power_basis compares default with default) |
| drrtl_LSTM | large | harness defect (catalog reset port), fixed 2026-09-18, runs superseded and repeated; power on this design is on the default-activity basis for all arms during the search (REQUEST 2026-09-20 (e) 1: D's E4 baseline carries no SAIF power; m3.power_basis compares default with default) |
| drrtl_aes | large | proof-latency-bound search (median proof latency 31 min above the 1 800 s generation window): on this design the archive was empty at 90 of 189 generation builds (B0-terra 8/35, B1_E4-terra 9/33, B2-terra 8/31, DrRTL_reimpl-terra 16/32, M-luna 27/29, M-terra 22/29); parents were D at those builds and the search reduced to E4-guided one-shot rewriting there; at the other builds the archive held proven candidates (wording qualified to the data, DECISION 2026-09-19 (l) 4); power on this design is on the default-activity basis for all arms during the search (REQUEST 2026-09-20 (e) 1: D's E4 baseline carries no SAIF power; m3.power_basis compares default with default) |
| drrtl_tv80 | large | verification limit (wall-clock cap under CPU contention); proof-latency-bound search (median proof latency 51 min above the 1 800 s generation window): on this design the archive stayed empty during generation for all arms; parents were D; the search reduces to E4-guided one-shot rewriting; power on this design is on the default-activity basis for all arms during the search (REQUEST 2026-09-20 (e) 1: D's E4 baseline carries no SAIF power; m3.power_basis compares default with default) |

- B0 is absent on thresholds_128x4096 (Yosys maps the 128×4096 memory to 1.4 M cells; 20-minute timeout), and this design's E4 runtime and log size are anomalous: median 8.5 min per E4 record against 3.8 min for the other medium-tier designs, and ≈ 69 MB per dc_shell log (compressed to ≈ 1.6 MB after ingestion, DECISION 2026-09-18 (b) item 2).
- The sentence "B0's gains are all absorbed by the synthesizer" is withdrawn until visible E4 records exist for B0's proven candidates (offline pool, DECISION 2026-09-18 D1); B0 rows whose E4 records are pending read `pending`, never 0.
- Hidden-configuration results are sealed until the Phase 5 completion marker; every hidden-form criterion reads `sealed` in this report.
- V3 initial-state handling corrected 2026-09-18 (harness_version 2); affected records re-proven. Don't-care (x) and high-impedance (z) values in the reference are fixed to 0 for V3; candidates must match 0 (value positions only, located with the Pyverilog AST, on the four designs whose RTL assigns x or z: router, spikeNeuron8_H7, tv80, spikeLayer8_H7; every other design's V3 sources are byte-identical to the originals). Verdicts of harness_version 1 stay on record, flagged superseded_by where re-proven; the main tables of LSTM, simple_spi and router use harness_version 2 verdicts only.

## 0b. Complete designs (DECISION 2026-09-18 (d) F2: every planned row × seed done, no verdict / E4 / offline simulation pending, B0 offline E4 in; DECISION 2026-09-19 (l) 3: a design complete except for B0's offline E4 is listed as B0 pending, its B0 column reads pending, and it counts in the tally and the reachability line. Per-row figures: the mean over seeds of each run's best retained area gain is the primary statistic (the tally rule of F2), with the max over seeds alongside; §2 shows the max over seeds only — the same record set, uniform rule A and floor; DECISION 2026-09-19 (n) 4)

Complete designs on the reported tiers: 2 — cktevo_hsm__hsm, drrtl_tv80; B0 pending: 1 — cktevo_risc__btb.

### cktevo_hsm__hsm (large tier; complete; main model gpt-5.6-terra; rule-A area floor t_d = 0.28 %; M: tie — no arm separates from the others on this design)

| model | arm | runs | candidates | proven | retained | tradeoff | best retained area gain per run: mean / max |
|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 3 | 180 | 0 | 0 | 0 | 0.00 % / 0.00 % |
| gpt-5.6-terra | B1_E4 | 3 | 180 | 0 | 0 | 0 | 0.00 % / 0.00 % |
| gpt-5.6-terra | B2 | 3 | 180 | 0 | 0 | 0 | 0.00 % / 0.00 % |
| gpt-5.6-terra | DrRTL_reimpl | 3 | 155 | 0 | 0 | 0 | 0.00 % / 0.00 % |
| gpt-5.6-luna | M | 3 | 180 | 0 | 0 | 0 | 0.00 % / 0.00 % |
| gpt-5.6-terra | M | 3 | 180 | 0 | 0 | 0 | 0.00 % / 0.00 % |

### drrtl_tv80 (large tier; complete; main model gpt-5.6-terra; rule-A area floor t_d = 0.28 %; M: tie — no arm separates from the others on this design)

| model | arm | runs | candidates | proven | retained | tradeoff | best retained area gain per run: mean / max |
|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 3 | 145 | 0 | 0 | 0 | 0.00 % / 0.00 % |
| gpt-5.6-terra | B1_E4 | 3 | 155 | 0 | 0 | 0 | 0.00 % / 0.00 % |
| gpt-5.6-terra | B2 | 3 | 167 | 0 | 0 | 0 | 0.00 % / 0.00 % |
| gpt-5.6-terra | DrRTL_reimpl | 3 | 39 | 0 | 0 | 0 | 0.00 % / 0.00 % |
| gpt-5.6-luna | M | 3 | 164 | 0 | 0 | 0 | 0.00 % / 0.00 % |
| gpt-5.6-terra | M | 3 | 164 | 0 | 0 | 0 | 0.00 % / 0.00 % |

### cktevo_risc__btb (large tier; B0 pending — complete except for B0 offline E4; main model gpt-5.6-terra; rule-A area floor t_d = 0.28 %; M: tie — no arm separates from the others on this design)

| model | arm | runs | candidates | proven | retained | tradeoff | best retained area gain per run: mean / max |
|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 3 | 177 | pending | pending | pending | pending (B0 offline E4) |
| gpt-5.6-terra | B1_E4 | 3 | 180 | 133 | 81 | 45 | 2.12 % / 2.36 % |
| gpt-5.6-terra | B2 | 3 | 180 | 135 | 81 | 37 | 1.97 % / 2.16 % |
| gpt-5.6-terra | DrRTL_reimpl | 3 | 136 | 119 | 43 | 5 | 0.36 % / 0.82 % |
| gpt-5.6-luna | M | 3 | 159 | 83 | 40 | 22 | 1.16 % / 1.76 % |
| gpt-5.6-terra | M | 3 | 157 | 102 | 67 | 30 | 1.91 % / 2.17 % |

**Tally (DECISION 2026-09-19 (m) 4, (n) 2): M wins — exceeds both B1_E4 and B2 by more than the design's floor — on 0 of 3 complete designs (visible layer; ties 3, partial 0, M loses 0; 1 of them B0 pending).**
Ties — no arm separates from the others on this design: cktevo_hsm__hsm, drrtl_tv80, cktevo_risc__btb.
Reachability of the pre-registered criterion (18 of 30 designs under the hidden configurations — sealed; the visible layer is the proxy): wins so far 0, already lost by M 7, undecided 0, designs not yet complete 8; M still needs 18 of the 8 remaining or undecided designs — no longer reachable in the visible layer.

- Mechanism note (C2): On aes M's archive was empty in 22/29 (terra) and 27/29 (luna) generations versus 8–9/33 for B1_E4 and B2, because M admits retained candidates only.

Designs with every planned run done — what still blocks "complete" (DECISION 2026-09-19 (l) 2; proofs drained = no proof job queued or running for the design):

| design | tier | runs done / planned | proofs open | blocks complete |
|---|---|---|---|---|
| cktevo_nn_engine__spikeNeuron8_H7 | large | 18 / 18 | 0 | E4 retries 1 (failed or timed-out E4; pool group e4_timeout); offline proofs 155 (D3, not blocking) |
| cktevo_risc__btb | large | 18 / 18 | 0 | B0 offline E4 11 (offline pool) — B0 pending |
| drrtl_aes | large | 18 / 18 | 0 | B0 offline E4 107 (offline pool); E4 retries 64 (failed or timed-out E4; pool group e4_timeout); offline proofs 20 (D3, not blocking) |

Incomplete designs (runs still open; per-row completion counts only, no arm comparison):

| design | tier | rows: done / planned (pending evaluations) |
|---|---|---|
| drrtl_LSTM | large | B0-terra 0/3, B1_E4-terra 0/3, B2-terra 0/3, DrRTL_reimpl-terra 0/3, M-luna 0/3, M-terra 0/3 |

## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)

### large tier

| model (role) | arm | runs | candidates | pending | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (contrast) | M | 15/18 † | 894 | 123 (e4 39, proof 84) | 6 | 121 (0.134) † | 130 | 0 | 29 | 44 † | 2.44 † | 4 † | 0.24 % / 0.00 % † | 4.89 † | 14.79 † | 0.86 † | 2.98 | 51.2 | 179.9 |
| gpt-5.6-terra (main) | B0 | 15/18 † | 900 | 118 (e4 118) | 0 | 289 (0.321) † | 344 | 0 | 79 | 43 † | 2.39 † | 6 † | 0.28 % / 0.00 % † | 4.78 † | 1.40 † | 1.55 † | 30.72 | 27.7 | 490.4 |
| gpt-5.6-terra (main) | B1_E4 | 15/18 † | 900 | 0 | 0 | 327 (0.363) † | 282 | 0 | 152 | 121 † | 6.72 † | 6 † | 0.49 % / 0.00 % † | 13.44 † | 3.49 † | 2.00 † | 34.70 | 60.6 | 470.6 |
| gpt-5.6-terra (main) | B2 | 15/18 † | 900 | 1 (e4 1) | 0 | 318 (0.353) † | 311 | 0 | 110 | 96 † | 5.33 † | 5 † | 0.41 % / 0.00 % † | 10.67 † | 2.80 † | 1.58 † | 34.25 | 60.6 | 482.2 |
| gpt-5.6-terra (main) | DrRTL_reimpl | 15/18 † | 757 | 0 | 3 | 341 (0.379) † | 130 | 0 | 168 | 44 † | 2.44 † | 3 † | 0.09 % / 0.00 % † | 4.89 † | 1.25 † | 0.82 † | 35.32 | 53.6 | 180.9 |
| gpt-5.6-terra (main) | M | 15/18 † | 899 | 126 (e4 25, proof 101) | 1 | 144 (0.160) † | 265 | 0 | 49 | 78 † | 4.33 † | 5 † | 0.62 % / 0.00 % † | 8.67 † | 2.49 † | 1.25 † | 31.32 | 62.2 | 450.7 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | formal-accepted, synthesis-rejected (DC error id; DECISION 2026-09-19 (o) 2) | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | M | 276 | 68 | 102 | 130 | 0 | 123 | 74 | 189 | 1 (cktevo_nn_engine__spikeNeuron8_H7 LINK-3) | absorbed_identical: 19, harmful: 20, noise: 16, retained: 44, tradeoff: 22 | absorbed_identical: 19, harmful: 19, noise: 16, nonequiv: 510, retained: 44, tradeoff: 22 | 235 (no block-level answers) | 183 (26) | 5332 / 28732 |
| gpt-5.6-terra | B0 | 178 | 29 | 18 | 344 | 2 | 118 | 40 | 0 | 0 | absorbed: 8, absorbed_identical: 8, harmful: 33, noise: 29, retained: 43, tradeoff: 50 | improved: 247, no_gain: 42, nonequiv: 571 | 316 (no block-level answers) | 86 (18) | 8243 / 39100 |
| gpt-5.6-terra | B1_E4 | 198 | 34 | 14 | 282 | 1 | 0 | 44 | 0 | 0 | absorbed: 1, absorbed_identical: 42, harmful: 78, noise: 39, retained: 121, tradeoff: 46 | improved: 256, no_gain: 62, nonequiv: 529 | 323 (no block-level answers) | 93 (30) | 10771 / 33905 |
| gpt-5.6-terra | B2 | 218 | 25 | 13 | 311 | 0 | 1 | 15 | 0 | 0 | absorbed_identical: 50, harmful: 84, noise: 48, retained: 96, tradeoff: 39 | improved: 208, no_gain: 98, nonequiv: 567 | 327 (no block-level answers) | 129 (44) | 8682 / 30652 |
| gpt-5.6-terra | DrRTL_reimpl | 92 | 7 | 9 | 130 | 1 | 0 | 177 | 0 | 0 | absorbed: 38, absorbed_identical: 42, harmful: 106, noise: 100, retained: 44, tradeoff: 11 | improved: 224, no_gain: 98, nonequiv: 239 | 255 (no block-level answers) | 39 (8) | 10491 / 31130 |
| gpt-5.6-terra | M | 246 | 35 | 22 | 265 | 0 | 126 | 61 | 165 | 0 | absorbed_identical: 8, harmful: 14, noise: 11, retained: 78, tradeoff: 33 | absorbed_identical: 8, harmful: 13, noise: 11, nonequiv: 529, retained: 78, tradeoff: 31 | 135 (no block-level answers) | 124 (28) | 5964 / 39366 |

Note (DECISION 2026-09-19 (k) 3 / (l) 4): on drrtl_tv80 the archive stayed empty during generation for all arms (proof-latency-bound search, §0a): parents were D and the search reduced to E4-guided one-shot rewriting; on drrtl_aes at 90 of 189 generation builds (B0-terra 8/35, B1_E4-terra 9/33, B2-terra 8/31, DrRTL_reimpl-terra 16/32, M-luna 27/29, M-terra 22/29) the archive was empty at that share of generation builds only — parents were D at those builds, proven candidates were in the archive at the others (wording qualified to the data).

## 2. Best retained area gain per design (max over seeds; uniform rule A; '-' = no retained candidate; 0 = runs without one)

### large tier

| design | B0 (terra) | B1_E4 (terra) | B2 (terra) | DrRTL_reimpl (terra) | M (luna) | M (terra) |
|---|---|---|---|---|---|---|
| cktevo_hsm__hsm | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_nn_engine__spikeNeuron8_H7 | 0 | 0 | 0 | 0 | pending | pending |
| cktevo_risc__btb | 1.71 % † | 2.36 % | 2.16 % | 0.82 % | 1.76 % | 2.17 % |
| drrtl_LSTM | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_aes | 0.72 % † | 0.88 % | 0.76 % † | 0.61 % | 0.88 % † | 4.67 % † |
| drrtl_tv80 | verification limit | verification limit | verification limit | verification limit | verification limit | verification limit |

Note (DECISION 2026-09-19 (k) 3 / (l) 4): on drrtl_tv80 the archive stayed empty during generation for all arms (proof-latency-bound search, §0a): parents were D and the search reduced to E4-guided one-shot rewriting; on drrtl_aes at 90 of 189 generation builds (B0-terra 8/35, B1_E4-terra 9/33, B2-terra 8/31, DrRTL_reimpl-terra 16/32, M-luna 27/29, M-terra 22/29) the archive was empty at that share of generation builds only — parents were D at those builds, proven candidates were in the archive at the others (wording qualified to the data).

## 2a. Retained and tradeoff candidates under the uniform rule A: class, sub-tags, gains per metric (DECISION 2026-09-18 D2)

### large tier (426 retained, 201 tradeoff)

| model | arm | design | candidate | uniform label | arm's label | class | sub-tags | area | WNS (clock periods) | power | tradeoff composition |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | cktevo_risc__btb | c39e459e533643a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.747) without operator or topology evidence -> review | 1.71 % | 0.0004 | 6.26 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c072b7bf83ef587 | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.60 % | 0.0014 | 6.61 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c33be040762eccd | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.751) without operator or topology evidence -> review | 1.31 % | 0.0025 | 78.84 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c4750c6fb7f3bd0 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.29 % | -0.0007 | 78.92 % | up=area,power down=wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c9f651d684af2a2 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.24 % | -0.0003 | 78.79 % | up=area,power down=wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c40463b1649015e | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7358) without operator or topology evidence -> review | 1.19 % | 0.0007 | 81.03 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c835a93feb1362d | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.17 % | 0.0005 | 78.92 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cf92beca0eb5761 | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.13 % | 0.0001 | 78.96 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c838acb81ff383f | tradeoff | improved | c1 | flip-flop bits 2008 -> 2016 and register cells 104 -> 112 with identical latency (no offset); text differs widely (ratio 0.7358) without operator or topology evidence -> review | 1.06 % | -0.0006 | 76.74 % | up=area,power down=wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c5258434b192e5d | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6539) without operator or topology evidence -> review | 0.83 % | 0.0003 | 80.85 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cbaeb7e9c96d0db | retained | improved | c1 | flip-flop bits 2008 -> 2016 and register cells 104 -> 112 with identical latency (no offset); text differs widely (ratio 0.7492) without operator or topology evidence -> review | 0.81 % | 0.0015 | 78.86 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cb70f6f33c5e8a5 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | 0.74 % | -0.0008 | 80.21 % | up=area,power down=wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c155c3a77a91c31 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.59 % | -0.0006 | 3.71 % | up=area,power down=wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | caa82c2e1d56835 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.53 % | 0.0008 | 3.61 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ca6643d769f5370 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.32 % | 0.0012 | 80.49 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ce1e6d2cc95323a | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6966) without operator or topology evidence -> review | 0.30 % | -0.0004 | 4.58 % | up=area,power down=wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cbfa2b4ffaa3e0e | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0003 | 81.56 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ca1f94a0bc33d4c | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.20 % | 0.0022 | 1.12 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c7c3b1afeca11c3 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.20 % | 0.0022 | 1.12 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c49a7a32438412b | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.20 % | 0.0022 | 1.12 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c8f399469dbf1a6 | retained | improved | d | operator family gained: shift (present in C, absent in D) | 0.19 % | 0.0020 | 1.12 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cefccd6957debca | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.13 % | 0.0002 | 3.84 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ccb0f2ea5031238 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.12 % | -0.0006 | 45.58 % | up=power down=wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cb5878c714e506c | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | -0.02 % | 0.0013 | 1.43 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c204190602656ac | retained | improved | c1 | flip-flop bits 2008 -> 2840 and register cells 104 -> 208 with identical latency (no offset) | -0.02 % | 0.0013 | 1.34 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c1ea81fd1056cb6 | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | -0.02 % | 0.0013 | 1.43 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c515037a1a1d285 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.02 % | 0.0010 | 0.01 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cdeec551e52fb36 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.02 % | 0.0010 | 0.01 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cd770e4a45b7c79 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.02 % | 0.0010 | 0.01 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ca9609319386672 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.07 % | 0.0001 | 82.76 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c7d0245fa7e5632 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.07 % | 0.0001 | 82.76 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c4e5a61f91aabeb | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.07 % | -0.0007 | 81.48 % | up=power down=wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c882176ab3f3027 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.08 % | 0.0031 | 80.60 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cd8fe0e6e9ffed6 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.09 % | 0.0005 | 79.77 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c17980edd3ced06 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.09 % | 0.0005 | 79.77 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c0b96600b72f4e3 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.10 % | 0.0002 | 80.33 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c128072263d95d4 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.10 % | 0.0002 | 78.48 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c9d22a03ee5ab35 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.10 % | 0.0002 | 78.48 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ce98cbf795c68c8 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.10 % | 0.0002 | 78.48 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cdc635bff7f81e6 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.12 % | 0.0008 | 80.23 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c7b838eb115d69a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.13 % | -0.0001 | 81.34 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cde91e697e3508a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.16 % | 0.0002 | 80.16 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ce2f9f6d2d96322 | retained | improved | d | operator family gained: add, mul, shift (present in C, absent in D) | -0.23 % | 0.0009 | 0.27 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ccd6e8b216d10ea | retained | improved | d | operator family gained: add, mul, shift (present in C, absent in D) | -0.23 % | 0.0009 | 0.27 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c9099e95837d962 | retained | improved | d | operator family gained: add, mul, shift (present in C, absent in D) | -0.23 % | 0.0009 | 0.27 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cc8ebaec54419aa | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.23 % | 0.0006 | 81.34 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c6705185ff70f4b | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.23 % | 0.0006 | 81.34 % | - |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ccf1071e8e892a9 | tradeoff | improved | d | operator family gained: shift (present in C, absent in D) | -0.44 % | 0.0003 | 82.29 % | up=wns,power down=area |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c2b3664e3673029 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -2.23 % | -0.0007 | 45.43 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cd6e7339e6e8b0b | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -2.23 % | -0.0007 | 45.43 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cdae4dc648ee6de | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -2.23 % | -0.0007 | 45.43 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cb97b776b8369e8 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -2.23 % | -0.0007 | 45.43 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c1dcd9adbc4df3f | tradeoff | improved | c1 | flip-flop bits 2008 -> 2080 and register cells 104 -> 176 with identical latency (no offset) | -4.08 % | -0.0003 | 80.79 % | up=power down=area |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c8e84ef49ad7ddc | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7594) without operator or topology evidence -> review | -4.34 % | 0.0008 | 5.76 % | up=wns,power down=area |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cbc6138d0f16ccd | tradeoff | improved | c1 | flip-flop bits 2008 -> 2080 and register cells 104 -> 176 with identical latency (no offset) | -5.34 % | -0.0001 | 80.45 % | up=power down=area |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ca17bc02e85de0c | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -5.39 % | -0.0057 | 79.31 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cd4a98edb0cc639 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -5.41 % | -0.0007 | 79.45 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c90549cf30929c7 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -5.41 % | -0.0007 | 79.45 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c306639748b53c4 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -5.67 % | -0.0008 | 80.53 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c5abc9a3a48bac3 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -5.67 % | -0.0008 | 80.53 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c20415fc07d2cbd | tradeoff | improved | d | operator family gained: shift (present in C, absent in D) | -5.68 % | -0.0007 | 79.04 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cff133ec462d8d8 | tradeoff | improved | c1 | flip-flop bits 2008 -> 2080 and register cells 104 -> 176 with identical latency (no offset) | -5.76 % | -0.0006 | 79.56 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ce5d830fa8f4000 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -5.79 % | -0.0007 | 46.36 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | caf59b41464caff | tradeoff | improved | d | operator family gained: shift (present in C, absent in D) | -5.84 % | -0.0007 | 80.28 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c2c6f7e9ac9ab4d | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -6.02 % | -0.0008 | 80.53 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c43b04508f41084 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -6.02 % | -0.0008 | 80.53 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cf2a69988b33434 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -7.51 % | -0.0006 | 78.88 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c6fef16eabc85c5 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -7.51 % | -0.0006 | 78.88 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cbc23e9043c6565 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -7.51 % | -0.0006 | 78.88 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c7fbf8a7b8c96cc | tradeoff | improved | c1 | flip-flop bits 2008 -> 2080 and register cells 104 -> 176 with identical latency (no offset) | -7.55 % | -0.0008 | 78.99 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c7b28fa48f8b738 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -7.66 % | -0.0008 | 79.01 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c52a93dbdd10e50 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -7.66 % | -0.0008 | 79.01 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c34acd31f661138 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -7.66 % | -0.0008 | 79.01 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ce649bce1b403dc | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -7.66 % | -0.0008 | 79.01 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c640fe52e0b9776 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -7.66 % | -0.0008 | 79.01 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ca9538fee4bbf66 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -7.66 % | -0.0008 | 79.01 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c2caa68b58f40e9 | tradeoff | improved | d | operator family gained: shift (present in C, absent in D) | -7.73 % | -0.0007 | 78.86 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cba37b660124133 | tradeoff | improved | d | operator family gained: shift (present in C, absent in D) | -7.91 % | -0.0082 | 78.64 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cfe4556137e2eb4 | tradeoff | improved | c1 | flip-flop bits 2008 -> 2080 and register cells 104 -> 176 with identical latency (no offset) | -7.92 % | -0.0082 | 78.63 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cbde09a977c001d | tradeoff | improved | d | operator family gained: shift (present in C, absent in D) | -7.92 % | -0.0082 | 78.63 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ca32fc8fe328082 | tradeoff | improved | c1 | flip-flop bits 2008 -> 2112 and register cells 104 -> 208 with identical latency (no offset) | -8.47 % | -0.0005 | 78.79 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c87f5fe6efc8ac5 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -12.47 % | 0.0004 | -1.83 % | up=wns down=area |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c3bab77b0a5c5f7 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -12.47 % | 0.0004 | -1.83 % | up=wns down=area |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cf580d6fe78524e | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -12.47 % | 0.0004 | -1.83 % | up=wns down=area |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c9a7c3a3d153926 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -12.47 % | 0.0004 | -1.83 % | up=wns down=area |
| gpt-5.6-terra | B0 | cktevo_risc__btb | cf8afecc5574c05 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -12.47 % | 0.0004 | -1.83 % | up=wns down=area |
| gpt-5.6-terra | B0 | cktevo_risc__btb | caaab83522f2894 | tradeoff | improved | d | operator family gained: shift (present in C, absent in D) | -13.10 % | 0.0012 | -2.23 % | up=wns down=area,power |
| gpt-5.6-terra | B0 | cktevo_risc__btb | c752be62f46f9b4 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -13.37 % | 0.0003 | -0.59 % | up=wns down=area |
| gpt-5.6-terra | B0 | cktevo_risc__btb | ce28497bdc4bce9 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -18.50 % | -0.0007 | 78.59 % | up=power down=area,wns |
| gpt-5.6-terra | B0 | drrtl_aes | c384e4a923bb2ad | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B0 | drrtl_aes | caf1d6ee4318abe | retained | improved | b | flip-flop bits 83339 -> 83338 in the same register cells (widths), latency unchanged | 0.41 % | -0.0000 | 0.22 % | - |
| gpt-5.6-terra | B0 | drrtl_aes | ca919f15e200091 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.36 % | 0.0000 | 0.02 % | - |
| gpt-5.6-terra | B0 | drrtl_aes | cb909ca198f7728 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.33 % | -0.0000 | 0.36 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c676419e982ce22 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6177) without operator or topology evidence -> review | 2.36 % | -0.0001 | 46.28 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cd2b39feb006fbc | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7731) without operator or topology evidence -> review | 2.17 % | -0.0006 | 47.96 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c2d174ff0dc59b0 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7516) without operator or topology evidence -> review | 2.10 % | 0.0005 | 48.08 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cb05913bea28f06 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7516) without operator or topology evidence -> review | 2.10 % | 0.0005 | 48.08 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ca6d27ced45265e | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7612) without operator or topology evidence -> review | 2.04 % | 0.0008 | 47.81 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c9c027aa25fd194 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.781) without operator or topology evidence -> review | 2.01 % | -0.0006 | 47.98 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ce6a546207b82b8 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.741) without operator or topology evidence -> review | 2.00 % | 0.0006 | 47.70 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c62672bfa343d57 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.99 % | -0.0005 | 78.56 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c937ef3fb980927 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7385) without operator or topology evidence -> review | 1.96 % | 0.0004 | 47.84 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ce72825d2e9a4f8 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5324) without operator or topology evidence -> review | 1.93 % | 0.0005 | 6.36 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c33edb0de49f0aa | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5324) without operator or topology evidence -> review | 1.93 % | 0.0005 | 6.36 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cc68f0d98afb8a7 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7768) without operator or topology evidence -> review | 1.91 % | 0.0032 | 47.80 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c71367a9a8ef8b0 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6733) without operator or topology evidence -> review | 1.91 % | 0.0014 | 7.35 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c7b6717c1fca226 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7749) without operator or topology evidence -> review | 1.89 % | 0.0015 | 79.88 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c21ed24fecb7279 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7022) without operator or topology evidence -> review | 1.87 % | 0.0016 | 3.84 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c08b55004b8fdba | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6875) without operator or topology evidence -> review | 1.86 % | 0.0021 | 9.46 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cf8e93e36be6b87 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5887) without operator or topology evidence -> review | 1.83 % | -0.0008 | 6.39 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c7abb99cc9195de | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7664) without operator or topology evidence -> review | 1.83 % | 0.0003 | 6.73 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c919fda67febf26 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.81 % | -0.0004 | 79.82 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c8078397b94ee84 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7449) without operator or topology evidence -> review | 1.80 % | -0.0008 | 47.88 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c64d78cf3b8498d | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7197) without operator or topology evidence -> review | 1.80 % | -0.0003 | 9.54 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c1c025144099ec0 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.763) without operator or topology evidence -> review | 1.79 % | 0.0004 | 79.89 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cf6eb02a83dd4eb | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.78 % | 0.0026 | 79.93 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c26368cd0582cda | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7072) without operator or topology evidence -> review | 1.77 % | -0.0002 | 3.88 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cf54bc5f5fd4598 | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.76 % | -0.0001 | 79.77 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cd890deaabff300 | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.76 % | 0.0006 | 79.88 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cd077f0b6c76d2f | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6906) without operator or topology evidence -> review | 1.76 % | -0.0001 | 6.79 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c54b6b9901251d1 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7512) without operator or topology evidence -> review | 1.75 % | -0.0003 | 6.88 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | caa16b99d9204b0 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7498) without operator or topology evidence -> review | 1.75 % | -0.0003 | 6.88 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c8b4d7e30560dc4 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7498) without operator or topology evidence -> review | 1.75 % | -0.0003 | 6.88 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c2dd0f448e46f29 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7507) without operator or topology evidence -> review | 1.75 % | -0.0001 | 6.88 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c1e915cfd483cc3 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7495) without operator or topology evidence -> review | 1.74 % | 0.0004 | 6.93 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | caab6ca76c7ad72 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7418) without operator or topology evidence -> review | 1.73 % | 0.0039 | 6.93 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c5aa85b2428832b | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.71 % | 0.0000 | 79.90 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c611b5023a77299 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7366) without operator or topology evidence -> review | 1.71 % | 0.0002 | 79.24 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c0b61c4bd5b0c33 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7519) without operator or topology evidence -> review | 1.71 % | 0.0004 | 79.09 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cdc54e6f3f2db39 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7446) without operator or topology evidence -> review | 1.67 % | 0.0003 | 47.70 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c19e7e0d9f55292 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7359) without operator or topology evidence -> review | 1.63 % | 0.0001 | 6.44 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cff539629e503aa | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6925) without operator or topology evidence -> review | 1.62 % | -0.0005 | 5.49 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c6ab21c62648d29 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7116) without operator or topology evidence -> review | 1.60 % | -0.0002 | 6.59 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c62f533e3c34064 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7405) without operator or topology evidence -> review | 1.60 % | -0.0002 | 6.59 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | caf2f0ee37dab32 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5201) without operator or topology evidence -> review | 1.60 % | -0.0003 | 6.40 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ce3f169bbd780ff | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7611) without operator or topology evidence -> review | 1.59 % | 0.0000 | 6.54 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c487817aa7d0a69 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6155) without operator or topology evidence -> review | 1.58 % | -0.0006 | 6.27 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ccd06d1f169bdcf | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.52 % | 0.0016 | 79.64 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c80550ffd67783a | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.749) without operator or topology evidence -> review | 1.52 % | -0.0005 | 6.00 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c11a1ef85535f89 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7401) without operator or topology evidence -> review | 1.49 % | 0.0006 | 9.13 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cc1799570aa0336 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5248) without operator or topology evidence -> review | 1.49 % | 0.0001 | 5.85 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c8d55eaf986a359 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7514) without operator or topology evidence -> review | 1.48 % | 0.0014 | 6.86 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c64a907bb7e79a0 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7199) without operator or topology evidence -> review | 1.47 % | -0.0004 | 9.55 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c1d1fd9d154b236 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6141) without operator or topology evidence -> review | 1.45 % | 0.0012 | 9.12 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c2d373519aeb422 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.66) without operator or topology evidence -> review | 1.44 % | -0.0006 | 6.67 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cf48d0c584f4488 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7489) without operator or topology evidence -> review | 1.43 % | 0.0001 | 6.53 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c86798a7abf8691 | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.41 % | 0.0013 | 79.67 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c59ca9ec3aa5e27 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6886) without operator or topology evidence -> review | 1.41 % | 0.0012 | 9.21 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ce3de0b51553586 | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.37 % | 0.0008 | 79.73 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c8bd12e4cc7fa32 | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.34 % | -0.0001 | 79.60 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c15bb8780bc7db3 | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.34 % | -0.0000 | 79.64 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c1d414f2795d94f | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.32 % | 0.0009 | 79.72 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c13cc452bbbf57b | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.32 % | 0.0009 | 79.72 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c3f56a9110c9629 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7336) without operator or topology evidence -> review | 1.30 % | 0.0004 | 5.99 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c46205e17697dcd | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7354) without operator or topology evidence -> review | 1.29 % | 0.0015 | 78.95 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c9300dd4f999443 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6264) without operator or topology evidence -> review | 1.28 % | -0.0007 | 3.50 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c1a99cf0aa4c640 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6819) without operator or topology evidence -> review | 1.26 % | -0.0001 | 3.97 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ce9793608b8bc8a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7352) without operator or topology evidence -> review | 1.26 % | 0.0004 | 79.67 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c5000b2316208e6 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.633) without operator or topology evidence -> review | 1.23 % | 0.0012 | 5.40 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cbab59e1ccb62a0 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7236) without operator or topology evidence -> review | 1.22 % | -0.0007 | 2.89 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c5b9fd3691f6af9 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7665) without operator or topology evidence -> review | 1.19 % | 0.0011 | 5.57 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ce648c252873bce | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.18 % | 0.0003 | 79.76 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cbe0149fa5ac181 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6738) without operator or topology evidence -> review | 1.16 % | 0.0003 | 3.74 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | caddd920d225dde | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.13 % | 0.0005 | 79.57 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c24f5b4438a9640 | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.13 % | 0.0023 | 79.68 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c2c4eb5442db61f | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6058) without operator or topology evidence -> review | 1.08 % | -0.0002 | 46.92 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c73161faac6ee53 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.06 % | -0.0005 | 78.90 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cd4d86b2208aca1 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6664) without operator or topology evidence -> review | 1.05 % | 0.0010 | 6.60 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c24cfa6054b2eac | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7471) without operator or topology evidence -> review | 1.03 % | 0.0022 | 78.70 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cf575485232eb30 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | 0.96 % | -0.0005 | 79.39 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c98ffb2451c0152 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | 0.92 % | -0.0007 | 80.01 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cd8b4f5c2fea389 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5582) without operator or topology evidence -> review | 0.89 % | 0.0008 | 1.73 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cdb4dfa1f2d5394 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.88 % | 0.0014 | 5.01 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cfebc15dc240a7b | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5692) without operator or topology evidence -> review | 0.87 % | -0.0008 | 1.67 % | up=area down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c692f7d54072250 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.82 % | 0.0005 | 5.11 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cba296ee669b93e | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5738) without operator or topology evidence -> review | 0.82 % | 0.0010 | 5.07 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c389aef5fe11f35 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.77 % | 0.0015 | 5.11 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cffb547a43d3231 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5609) without operator or topology evidence -> review | 0.76 % | -0.0004 | 1.69 % | up=area down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c46e21d5a227b40 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.69 % | 0.0004 | 5.17 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c6d0c8fb09505e4 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.65 % | 0.0016 | 5.10 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | caf7b27ea11087e | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.65 % | 0.0016 | 5.10 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c4245dc2f7bcf65 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.63 % | -0.0005 | 5.03 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cded181d13c3f57 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ceecc54babd42cd | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cb7922a19281eb6 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c3ffa4665a2f437 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c8c41373d77695a | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c9f56318182bfd1 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | 0.0001 | 3.70 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cd482a82e4f3d7f | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c5a86b61c2c146c | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | 0.0003 | 3.47 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c264d042878a111 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | 0.0003 | 3.47 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cbc349b9d125dc0 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | -0.0006 | 3.50 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c625fd63fcfe232 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.59 % | -0.0006 | 3.71 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c603f2996e26572 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.59 % | 0.0006 | 5.07 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c67c04f00b0231a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.57 % | -0.0002 | 3.59 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c5f28df63b6c26f | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.57 % | -0.0002 | 3.59 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c5f9f60ae851e3a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.534) without operator or topology evidence -> review | 0.55 % | 0.0000 | 3.62 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ce94643bafc19a1 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.589) without operator or topology evidence -> review | 0.55 % | -0.0007 | 4.80 % | up=area,power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c2667298fd7fe40 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5349) without operator or topology evidence -> review | 0.47 % | -0.0002 | 4.75 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c3e8293f104ceb7 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.38 % | -0.0001 | 5.01 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cc7cdf4d36a4322 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5555) without operator or topology evidence -> review | 0.31 % | 0.0000 | 0.11 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c9635f2ecfb49db | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.11 % | -0.0002 | 45.56 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cc68e78e68c117a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.06 % | 0.0007 | 1.37 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c4760857f62ea9d | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.00 % | -0.0001 | 45.45 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c7cc5ee65582eb9 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.03 % | -0.0004 | 4.88 % | up=power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c36be734d289659 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.09 % | -0.0000 | 3.58 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c0e4df2d9f376a4 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.17 % | -0.0008 | 4.99 % | up=power down=wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c40bfe274a11d59 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.20 % | 0.0010 | -0.18 % | - |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c76a0e78c53b01e | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.60 % | -0.0018 | 3.16 % | up=power down=area,wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cae2c92bd904e0d | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6284) without operator or topology evidence -> review | -4.51 % | -0.0006 | 5.44 % | up=power down=area,wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c15268686098f40 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5374) without operator or topology evidence -> review | -4.54 % | -0.0008 | 5.61 % | up=power down=area,wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c4f7fb2f346b120 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6368) without operator or topology evidence -> review | -4.65 % | -0.0008 | 6.11 % | up=power down=area,wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c3c94d3c5b52de7 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.738) without operator or topology evidence -> review | -4.67 % | 0.0004 | 4.21 % | up=wns,power down=area |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cce0cdbf66bc232 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7108) without operator or topology evidence -> review | -4.71 % | -0.0006 | 5.09 % | up=power down=area,wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | ce618d587839653 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5238) without operator or topology evidence -> review | -4.88 % | -0.0002 | 4.13 % | up=power down=area |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c14c33f85b7f411 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -5.73 % | 0.0007 | 3.34 % | up=wns,power down=area |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cfce5eec3d197b3 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.698) without operator or topology evidence -> review | -5.96 % | -0.0004 | 3.25 % | up=power down=area,wns |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | cd30f925acb1a0e | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5272) without operator or topology evidence -> review | -14.60 % | 0.0005 | 0.90 % | up=wns down=area |
| gpt-5.6-terra | B1_E4 | cktevo_risc__btb | c90bcb748d6ce53 | tradeoff | improved | d | operator family gained: add, shift (present in C, absent in D) | -16.98 % | -0.0007 | 74.13 % | up=power down=area,wns |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c49eea58b3cde5a | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.88 % | -0.0000 | 0.87 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cbcfcb1fc36a32f | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.82 % | -0.0000 | 0.72 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cc659d34d4322e8 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.76 % | -0.0000 | 0.96 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c78613637f63f0f | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.76 % | -0.0000 | 0.96 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c17cead3b28efc0 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.76 % | -0.0000 | 0.96 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c145b491a68fac1 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.76 % | -0.0000 | 0.96 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cb51abd143144c8 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cd7681bbc33cf12 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cf34a4f10a33869 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cac8b005ad75a69 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c4b24428362c098 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c0f41249321247b | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c1e67492838da26 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | ca4858f6656d44c | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cf2eccc24043d20 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c5443afc322352a | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c03db3702acbcbb | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c8ff0c531dfa07f | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c489bb2c26c3009 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c5b73f62777c3c1 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c71459554911b68 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c3e98dc26bfb62d | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c56b536bc056579 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cb96227004466a4 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c40f5088c2d61f9 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c0e91d815e17499 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | -0.0000 | 0.17 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cae5db1e25aabd4 | retained | - | d | operator family gained: add (present in C, absent in D) | 0.72 % | -0.0000 | 0.17 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cfcb1c3412bd513 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | -0.0000 | 0.17 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c94758df13b931c | retained | improved | c1 | flip-flop bits 83339 -> 83396 and register cells 10243 -> 10259 with identical latency (no offset) | 0.68 % | -0.0000 | 0.86 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cf9312d81b163cf | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.64 % | -0.0000 | 0.95 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | ca81ac2fc185ccb | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.63 % | -0.0000 | 0.94 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c850e46aa2fa957 | retained | improved | c1 | flip-flop bits 83339 -> 83396 and register cells 10243 -> 10259 with identical latency (no offset) | 0.44 % | -0.0000 | 0.16 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c9cea85cd43e3b4 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.42 % | -0.0001 | 0.21 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | ca2a519357f9dfb | retained | improved | c1 | flip-flop bits 83339 -> 83332 and register cells 10243 -> 10252 with identical latency (no offset) | 0.41 % | -0.0000 | 0.85 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c37bbd1d3e9aa86 | retained | improved | c1 | flip-flop bits 83339 -> 83396 and register cells 10243 -> 10268 with identical latency (no offset) | 0.37 % | -0.0001 | 0.73 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cfb6b6ebe4a81d4 | retained | improved | c1 | flip-flop bits 83339 -> 83396 and register cells 10243 -> 10268 with identical latency (no offset) | 0.37 % | -0.0001 | 0.73 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c2b6967710c1bc7 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.35 % | -0.0000 | 0.52 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | ca01d65412ed3e3 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.33 % | -0.0000 | 0.36 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c33e4d89358b491 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.32 % | 0.0000 | 0.10 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | c8031fc628003cd | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.32 % | 0.0000 | 0.10 % | - |
| gpt-5.6-terra | B1_E4 | drrtl_aes | cf45f5faa8917ab | tradeoff | improved | d | operator family gained: add (present in C, absent in D) | -7.84 % | 0.0001 | 12.09 % | up=power down=area |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c14e4f845fb439b | tradeoff | improved | c1 | flip-flop bits 2008 -> 2010 and register cells 104 -> 26 with identical latency (no offset); text differs widely (ratio 0.7578) without operator or topology evidence -> review | 2.26 % | -0.0004 | 80.42 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cf6e09f546b5d26 | retained | improved | c1 | flip-flop bits 2008 -> 2010 and register cells 104 -> 18 with identical latency (no offset); text differs widely (ratio 0.7425) without operator or topology evidence -> review | 2.16 % | 0.0003 | 80.49 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cadb34ddaf203a4 | retained | improved | c1 | flip-flop bits 2008 -> 2010 and register cells 104 -> 26 with identical latency (no offset); text differs widely (ratio 0.7477) without operator or topology evidence -> review | 2.15 % | 0.0005 | 80.46 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cc95d7a726e52dc | retained | improved | c1 | flip-flop bits 2008 -> 2010 and register cells 104 -> 26 with identical latency (no offset); text differs widely (ratio 0.7505) without operator or topology evidence -> review | 2.15 % | 0.0005 | 80.46 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c63d7532441cfa9 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6509) without operator or topology evidence -> review | 2.04 % | 0.0021 | 47.34 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c3868631dbdcaad | retained | improved | d | operator family gained: add, shift (present in C, absent in D) | 1.97 % | 0.0016 | 47.67 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c11022d97027382 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7456) without operator or topology evidence -> review | 1.94 % | -0.0003 | 78.50 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c880e491abac603 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7499) without operator or topology evidence -> review | 1.88 % | -0.0004 | 79.15 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c988841854e6b46 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6433) without operator or topology evidence -> review | 1.83 % | 0.0006 | 5.82 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c8113231ec4c12d | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7032) without operator or topology evidence -> review | 1.83 % | 0.0006 | 5.88 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c58d326f926a7c0 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7051) without operator or topology evidence -> review | 1.83 % | 0.0006 | 5.88 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cf70a9eb234db0a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6394) without operator or topology evidence -> review | 1.77 % | 0.0006 | 9.52 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cd9f417f53e1dbb | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.742) without operator or topology evidence -> review | 1.77 % | 0.0006 | 9.52 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cc52e4a1158d947 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6861) without operator or topology evidence -> review | 1.77 % | 0.0006 | 9.52 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cea918e80f92175 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5419) without operator or topology evidence -> review | 1.76 % | 0.0010 | 6.76 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c8d60947fd067fe | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6673) without operator or topology evidence -> review | 1.75 % | -0.0003 | 6.88 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cb1ab70e627ebb1 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7245) without operator or topology evidence -> review | 1.75 % | 0.0009 | 9.46 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c2624e3b424e8f8 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7398) without operator or topology evidence -> review | 1.75 % | 0.0012 | 79.91 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cbb0985ebb2cad7 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.721) without operator or topology evidence -> review | 1.75 % | 0.0004 | 5.85 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c2c587b9e29c845 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7072) without operator or topology evidence -> review | 1.73 % | 0.0020 | 6.31 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cf6d09f88284333 | tradeoff | improved | c1 | flip-flop bits 2008 -> 2018 and register cells 104 -> 34 with identical latency (no offset); text differs widely (ratio 0.7486) without operator or topology evidence -> review | 1.72 % | -0.0006 | 81.37 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ced698fb2f098d9 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6671) without operator or topology evidence -> review | 1.71 % | 0.0008 | 5.85 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c36d5b3371fdeee | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6861) without operator or topology evidence -> review | 1.70 % | 0.0006 | 9.57 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cb4c6b1cb5ed5f3 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7288) without operator or topology evidence -> review | 1.69 % | 0.0003 | 9.21 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c39eba041fab1f6 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.693) without operator or topology evidence -> review | 1.66 % | -0.0005 | 6.38 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cb73a56f0da00b5 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6306) without operator or topology evidence -> review | 1.66 % | -0.0005 | 6.38 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cc28f50b39c2b8c | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6624) without operator or topology evidence -> review | 1.66 % | 0.0004 | 3.42 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c615b06e00d7dfe | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6753) without operator or topology evidence -> review | 1.65 % | -0.0006 | 5.92 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c8f548f58c64840 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6906) without operator or topology evidence -> review | 1.63 % | -0.0007 | 6.38 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c1210513270dd5e | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6453) without operator or topology evidence -> review | 1.63 % | 0.0015 | 5.91 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c84ef3a996377cd | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6827) without operator or topology evidence -> review | 1.62 % | -0.0002 | 46.43 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cd5fac40ed79767 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7456) without operator or topology evidence -> review | 1.62 % | 0.0004 | 78.48 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c10c667fd6b1008 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7103) without operator or topology evidence -> review | 1.62 % | 0.0000 | 6.46 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c65880a40ca6c5c | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7196) without operator or topology evidence -> review | 1.62 % | 0.0000 | 6.46 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c69d9e7ff63a8b0 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6672) without operator or topology evidence -> review | 1.60 % | 0.0025 | 3.74 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c79bd6d84cc8678 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.634) without operator or topology evidence -> review | 1.60 % | 0.0007 | 6.98 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c07f3f42565c7c3 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7283) without operator or topology evidence -> review | 1.60 % | 0.0007 | 6.98 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c04bdee0f34ebc1 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7357) without operator or topology evidence -> review | 1.60 % | 0.0007 | 6.98 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c1a0a82ff85a33d | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7357) without operator or topology evidence -> review | 1.60 % | 0.0007 | 6.98 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c37e34a1af03eed | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.634) without operator or topology evidence -> review | 1.60 % | 0.0007 | 6.98 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cd84f879732b7ce | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.634) without operator or topology evidence -> review | 1.60 % | 0.0007 | 6.98 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c4f630702fd7bf8 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6446) without operator or topology evidence -> review | 1.58 % | -0.0006 | 6.27 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cc28a2f1105a210 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6649) without operator or topology evidence -> review | 1.58 % | -0.0007 | 6.57 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c5fdc9d0fdfba66 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7062) without operator or topology evidence -> review | 1.58 % | 0.0009 | 79.19 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cc43c5711f74c48 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.763) without operator or topology evidence -> review | 1.56 % | 0.0001 | 9.52 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c6126c016201b48 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6545) without operator or topology evidence -> review | 1.55 % | -0.0005 | 9.15 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ce6e115706fa5f3 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6947) without operator or topology evidence -> review | 1.55 % | 0.0001 | 5.97 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c0a38bb7fb65b73 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7221) without operator or topology evidence -> review | 1.55 % | 0.0007 | 79.11 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cd3cd148b10b84a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5684) without operator or topology evidence -> review | 1.53 % | 0.0021 | 5.95 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cad6fdd9323a351 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6791) without operator or topology evidence -> review | 1.53 % | -0.0002 | 9.16 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cb3237f2435bbbc | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7361) without operator or topology evidence -> review | 1.52 % | -0.0005 | 6.27 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c9ab3aa3be08425 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7027) without operator or topology evidence -> review | 1.50 % | 0.0006 | 79.27 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cb4316823c0df2f | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7593) without operator or topology evidence -> review | 1.50 % | 0.0006 | 79.27 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c8fb136ef81cbab | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7531) without operator or topology evidence -> review | 1.49 % | 0.0007 | 9.48 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c1059ecb592325a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7454) without operator or topology evidence -> review | 1.48 % | 0.0014 | 79.20 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c6376caa7504a01 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6937) without operator or topology evidence -> review | 1.44 % | 0.0002 | 9.53 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c3072454b7dc3ee | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6865) without operator or topology evidence -> review | 1.44 % | -0.0002 | 6.15 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cf7fd7af8a87a13 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7006) without operator or topology evidence -> review | 1.40 % | -0.0004 | 78.92 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c0e2d9d2ea22156 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7241) without operator or topology evidence -> review | 1.38 % | 0.0012 | 5.88 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cec7835c2ab1d5d | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.73) without operator or topology evidence -> review | 1.36 % | 0.0008 | 6.49 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c99f83b100461aa | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7077) without operator or topology evidence -> review | 1.36 % | -0.0006 | 79.03 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c40269f6608e301 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7084) without operator or topology evidence -> review | 1.36 % | 0.0029 | 78.67 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ce5e97751838749 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7556) without operator or topology evidence -> review | 1.32 % | -0.0004 | 5.56 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ccaa848a89e794a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6945) without operator or topology evidence -> review | 1.31 % | 0.0003 | 5.97 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cb45e0160f2efd3 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.643) without operator or topology evidence -> review | 1.13 % | 0.0043 | 5.86 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c4344ace6efa89b | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7418) without operator or topology evidence -> review | 1.13 % | 0.0043 | 5.86 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c081201b4ace4ae | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.667) without operator or topology evidence -> review | 1.11 % | -0.0003 | 6.23 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ce47ba336dda3dd | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7663) without operator or topology evidence -> review | 0.99 % | -0.0002 | 79.03 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c8675fe50e01dc4 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7095) without operator or topology evidence -> review | 0.98 % | -0.0001 | 6.63 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cc36168dc16afae | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7043) without operator or topology evidence -> review | 0.97 % | 0.0000 | 80.08 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ced9ff0c72fcf74 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.90 % | 0.0017 | 4.92 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cb0683fbfc335f0 | retained | improved | c1 | flip-flop bits 2008 -> 2010 and register cells 104 -> 26 with identical latency (no offset); text differs widely (ratio 0.7143) without operator or topology evidence -> review | 0.87 % | -0.0001 | 79.94 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cd8bd444022469b | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.83 % | 0.0002 | 4.98 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cf09b9b19083d3c | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.83 % | 0.0002 | 4.98 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c1cbc4a74ccc104 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.83 % | 0.0002 | 4.98 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c071081650e99c8 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.82 % | -0.0003 | 5.07 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c5b929356ee0429 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.81 % | -0.0007 | 5.04 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ca45189b24724f1 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.78 % | -0.0001 | 4.91 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c45f7b67d7e01b1 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6831) without operator or topology evidence -> review | 0.78 % | -0.0003 | 5.67 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cb50f75558b30a1 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.76 % | -0.0008 | 4.94 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cbe31dfef96f399 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7107) without operator or topology evidence -> review | 0.75 % | -0.0005 | 6.65 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c583e412bb84e94 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7188) without operator or topology evidence -> review | 0.74 % | -0.0005 | 78.75 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cf58f279d711a1b | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.71 % | 0.0008 | 5.07 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cca644ff965789a | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cd96757c7df098a | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c6a58116540d46f | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c0b5f7c05307312 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | 0.0003 | 3.47 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c0c2151fb716924 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | 0.0003 | 3.47 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cdb8b790c520491 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | 0.0003 | 3.47 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c2fce8f799a49c0 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.59 % | -0.0006 | 3.71 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cbef3936926b3c3 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.58 % | -0.0001 | 3.48 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c5fa30a24664a7d | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.53 % | 0.0008 | 3.61 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ccf9d65ee218837 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.52 % | 0.0006 | 3.46 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c91b324b68bf32d | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.43 % | 0.0003 | 4.76 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c060147d2f18b1f | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.38 % | -0.0007 | 2.16 % | up=area down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c80789c9d5ecb88 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.30 % | -0.0007 | 2.26 % | up=area,power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c25f11e368a677e | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.24 % | -0.0006 | 2.40 % | up=power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c4f11d39cb9e428 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.23 % | 0.0020 | 0.08 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c9627ccc87fecc0 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.23 % | 0.0011 | 0.07 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c134e63d67fd0d8 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.23 % | 0.0020 | 0.08 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cf8e98d8233215f | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.17 % | 0.0004 | 0.13 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cd3a359bd346ca1 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.14 % | 0.0005 | 0.22 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cba6bc4eeed2fb9 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5086) without operator or topology evidence -> review | 0.14 % | -0.0006 | 2.26 % | up=power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cb683b120f73319 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5921) without operator or topology evidence -> review | 0.12 % | 0.0008 | 0.15 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ce1fe2401bc9866 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.11 % | -0.0002 | 45.56 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c4d8c0a248494e0 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7328) without operator or topology evidence -> review | 0.09 % | 0.0001 | 7.82 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ca8e8db332f01f1 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.01 % | 0.0004 | -0.08 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c8ceae05443a43f | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.02 % | -0.0002 | 3.15 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c62d8795bc20a5b | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5513) without operator or topology evidence -> review | -0.02 % | -0.0004 | 4.74 % | up=power down=wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c835275775e1242 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.09 % | 0.0014 | 0.09 % | - |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c802c5867e7267a | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.33 % | 0.0007 | -0.06 % | up=wns down=area |
| gpt-5.6-terra | B2 | cktevo_risc__btb | caae76a717cdec5 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.37 % | 0.0000 | 81.34 % | up=power down=area |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c9487a369ab8e11 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.42 % | -0.0008 | 4.80 % | up=power down=area,wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ca66b4c94310aec | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7479) without operator or topology evidence -> review | -1.52 % | -0.0147 | 5.67 % | up=power down=area,wns |
| gpt-5.6-terra | B2 | cktevo_risc__btb | ce895ad10f8900f | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7173) without operator or topology evidence -> review | -4.44 % | 0.0003 | 5.53 % | up=wns,power down=area |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c91445c5f61c319 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6473) without operator or topology evidence -> review | -4.69 % | -0.0001 | 5.52 % | up=power down=area |
| gpt-5.6-terra | B2 | cktevo_risc__btb | cf2111deba8dfdb | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6698) without operator or topology evidence -> review | -4.79 % | -0.0003 | 5.07 % | up=power down=area |
| gpt-5.6-terra | B2 | cktevo_risc__btb | c0e064783f8782d | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -5.19 % | 0.0005 | 2.89 % | up=wns,power down=area |
| gpt-5.6-terra | B2 | drrtl_aes | c447cd4f31ae511 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.76 % | 0.0000 | 0.97 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c0bf7867626e445 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.76 % | 0.0000 | 0.97 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | cb2c9769da192c5 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c1239f5e1779601 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c2ff5ec00a997b1 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | ce4a2bcd59dadba | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.61 % | 0.0000 | 0.19 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c73aa8f938965ca | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.49 % | 0.0001 | 0.13 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | cb39c0cd7647fe7 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.49 % | 0.0001 | 0.13 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c785ab69a6bfa0e | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.33 % | -0.0000 | 0.36 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c5cb4c90fb11b2e | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.33 % | -0.0000 | 0.36 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c1b589d21b15072 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.33 % | -0.0000 | 0.36 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c57ce93663d2a23 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.30 % | 0.0000 | 0.19 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c15495205f34708 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.30 % | 0.0000 | 0.19 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c65236e79070a88 | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.30 % | 0.0000 | 0.19 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | c673edf2f8f06cf | retained | improved | d | operator family gained: add (present in C, absent in D) | 0.30 % | 0.0000 | 0.19 % | - |
| gpt-5.6-terra | B2 | drrtl_aes | cc364e9fc5cd15e | tradeoff | improved | c1 | flip-flop bits 83339 -> 83340 and register cells 10243 -> 10253 with identical latency (no offset) | -6.79 % | -0.0001 | 7.77 % | up=power down=area |
| gpt-5.6-terra | B2 | drrtl_aes | cbf7b3c4fd71abf | tradeoff | - | c1 | flip-flop bits 83339 -> 83659 and register cells 10243 -> 10263 with identical latency (no offset) | -9.31 % | -0.0039 | 10.74 % | up=power down=area,wns |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c0adc7143ee0034 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.88 % | -0.0003 | 2.67 % | up=area,power down=wns |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c9b7fe807a638fc | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.82 % | 0.0002 | 3.59 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c7d7f485730e753 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.82 % | 0.0002 | 3.59 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c6623bf13c9da37 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.81 % | 0.0007 | 5.25 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c55dcf3e2c97516 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.79 % | -0.0007 | 3.51 % | up=area,power down=wns |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cfbe27014eb5a5a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.76 % | 0.0002 | 5.10 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c60b6c3585374bd | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.76 % | 0.0002 | 5.10 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c5cff7de20271b5 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.76 % | 0.0002 | 5.10 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cc55c5f0d8ff1a6 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.74 % | 0.0012 | 2.45 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cbf246f5a0ac53f | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.66 % | 0.0011 | 5.04 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c3d76b653342a7c | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.58 % | -0.0001 | 5.16 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c282a7d3229df64 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.51 % | 0.0008 | 5.08 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | ca6419f01aa92ec | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.48 % | -0.0004 | 5.01 % | up=area,power down=wns |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c522d7decf8d6f3 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.39 % | -0.0000 | 4.70 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cdc50e7c896c34b | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cd6922e78f65b65 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c4589eed86ed1a3 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c96ca95313926b7 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cd99b179691e48e | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | ca06f55bfe41108 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c4ab8c107b2fcad | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cb25b11a2b7967b | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c9670c86c269393 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c649f7b47d0413e | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cc1c91d2122abd7 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c37f5404a578222 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cf49d62fac686bc | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c9a451e3840f2f7 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c83789908ec0d99 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cbf0a1315ce483c | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c714ab1d9ffece8 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c803305ae9749f8 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cafd7eaa609e7bb | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c53cd3b19e37ae5 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c88012d6156146c | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c00c18bf1c01ff2 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c22aaadf914e89c | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.25 % | 0.0006 | 0.43 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cd2e7d3fe1d9ba1 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.24 % | 0.0005 | 0.42 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | ccddae4ade3bd0a | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.24 % | 0.0005 | 0.42 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c719cd760fc38d5 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.05 % | 0.0012 | 0.21 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c47c2f1312bb0b2 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.05 % | 0.0010 | 0.29 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c47f921dfd379b4 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.16 % | 0.0004 | -0.56 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c3097fe389488e0 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.17 % | 0.0017 | -0.30 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c9c4dcee783489e | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.17 % | 0.0009 | -0.17 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cc68120f500fc58 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.21 % | 0.0007 | -0.15 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c959b5622016317 | retained | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.23 % | 0.0027 | 0.38 % | - |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | cffdcd51ad98ab0 | tradeoff | improved | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.31 % | 0.0007 | -0.76 % | up=wns down=area |
| gpt-5.6-terra | DrRTL_reimpl | cktevo_risc__btb | c931334011201c5 | tradeoff | improved | c1 | flip-flop bits 2008 -> 2904 and register cells 104 -> 72 with identical latency (no offset) | -40.48 % | 0.0003 | -38.20 % | up=wns down=area,power |
| gpt-5.6-terra | DrRTL_reimpl | drrtl_aes | cc3b9acbcb716d7 | retained | improved | c1 | flip-flop bits 83339 -> 83363 and register cells 10243 -> 10246 with identical latency (no offset) | 0.61 % | 0.0000 | 3.30 % | - |
| gpt-5.6-terra | DrRTL_reimpl | drrtl_aes | cbe396f25262abe | tradeoff | improved | c1 | flip-flop bits 83339 -> 83357 and register cells 10243 -> 10250 with identical latency (no offset) | -0.47 % | 0.0000 | 2.24 % | up=power down=area |
| gpt-5.6-terra | DrRTL_reimpl | drrtl_aes | c42749a06c831b9 | tradeoff | improved | c1 | flip-flop bits 83339 -> 83403 and register cells 10243 -> 10245 with identical latency (no offset) | -1.09 % | 0.0000 | 3.15 % | up=power down=area |
| gpt-5.6-terra | DrRTL_reimpl | drrtl_aes | ca4edfe33fd0f73 | tradeoff | improved | c1 | flip-flop bits 83339 -> 83403 and register cells 10243 -> 10245 with identical latency (no offset) | -1.09 % | 0.0000 | 3.15 % | up=power down=area |
| gpt-5.6-terra | DrRTL_reimpl | drrtl_aes | c0e2343c2dc75ac | tradeoff | improved | c1 | flip-flop bits 83339 -> 83403 and register cells 10243 -> 10251 with identical latency (no offset) | -1.59 % | 0.0000 | 2.81 % | up=power down=area |
| gpt-5.6-terra | DrRTL_reimpl | drrtl_aes | c228c924ba492f4 | tradeoff | improved | c1 | flip-flop bits 83339 -> 83403 and register cells 10243 -> 10251 with identical latency (no offset) | -1.62 % | 0.0000 | 2.81 % | up=power down=area |
| gpt-5.6-terra | DrRTL_reimpl | drrtl_aes | c36f293fc1d271a | tradeoff | - | c1 | flip-flop bits 83339 -> 83659 and register cells 10243 -> 10253 with identical latency (no offset) | -10.55 % | 0.0000 | 10.09 % | up=power down=area |
| gpt-5.6-luna | M | cktevo_risc__btb | c65d37820e23dee | tradeoff | tradeoff | d | operator family gained: add (present in C, absent in D) | 1.84 % | -0.0007 | 6.89 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c5f8c64795c1fc6 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7135) without operator or topology evidence -> review | 1.79 % | -0.0004 | 6.29 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | cd560782aba87ff | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6663) without operator or topology evidence -> review | 1.76 % | 0.0012 | 47.76 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cc1c0de60302644 | retained | retained | d | operator family gained: add (present in C, absent in D) | 1.73 % | 0.0017 | 6.38 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c344d2cd38aa1b5 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7092) without operator or topology evidence -> review | 1.62 % | 0.0000 | 6.26 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cfad65644594e61 | retained | retained | d | operator family gained: add (present in C, absent in D) | 1.58 % | 0.0005 | 6.28 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c625e34fd2f57f7 | retained | retained | d | operator family gained: add (present in C, absent in D) | 1.57 % | 0.0000 | 5.93 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cc5098a42bfdc92 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6733) without operator or topology evidence -> review | 1.55 % | 0.0027 | 6.57 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cfcc15f56f04114 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7583) without operator or topology evidence -> review | 1.52 % | -0.0007 | 9.23 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c869c36b876eed5 | retained | retained | d | operator family gained: add (present in C, absent in D) | 1.43 % | -0.0001 | 5.97 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c7d7de2b4dab36d | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7246) without operator or topology evidence -> review | 1.43 % | 0.0010 | 6.04 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c5ed9b9388279b4 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6646) without operator or topology evidence -> review | 1.36 % | 0.0005 | 5.98 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c15657ca9f106ac | retained | retained | d | operator family gained: add (present in C, absent in D) | 1.33 % | 0.0013 | 6.88 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c894c05e2452562 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7072) without operator or topology evidence -> review | 1.31 % | -0.0004 | 5.89 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c412ce2f2b8b385 | retained | retained | d | operator family gained: add (present in C, absent in D) | 1.27 % | 0.0010 | 6.59 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c6943592c26003d | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7188) without operator or topology evidence -> review | 1.18 % | -0.0006 | 9.50 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c3b1a16195fa429 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6988) without operator or topology evidence -> review | 1.14 % | -0.0004 | 3.23 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c3e0e6c1f3caf55 | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | 0.88 % | 0.0010 | 5.00 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c5dfb24fce43e0e | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.86 % | -0.0001 | 4.89 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c78d12d4b57d5a7 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.85 % | -0.0003 | 5.10 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | ca4e28cc0f0b8c9 | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | 0.85 % | 0.0002 | 4.98 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cb3144f56c85b9f | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.83 % | -0.0003 | 5.02 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c8a3b1d90d9839f | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.82 % | 0.0012 | 5.01 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c408e353e54dbb2 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.81 % | 0.0005 | 4.93 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c4b1aae3c6389ee | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | 0.80 % | 0.0018 | 2.52 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c539be8ca9a26c9 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.77 % | -0.0006 | 4.97 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | cd9431025092a16 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.542) without operator or topology evidence -> review | 0.76 % | 0.0007 | 5.00 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c40c9892974f517 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.74 % | 0.0006 | 4.91 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c9b6e28a5ac7aac | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | 0.68 % | 0.0009 | 4.84 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c82fed8e94624f7 | retained | retained | d | longest combinational path 14 -> 42 cells (ratio 3.0 >= 3.0) | 0.66 % | -0.0001 | 4.98 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c5a31927d88104d | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5273) without operator or topology evidence -> review | 0.64 % | -0.0006 | 4.20 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c92c88b9a2aa7d2 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.64 % | 0.0006 | 3.58 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cb4a9030f27b425 | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | 0.64 % | 0.0006 | 5.00 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cd7d774b4b4fa6b | tradeoff | tradeoff | d | operator family gained: add, shift (present in C, absent in D) | 0.63 % | -0.0008 | 4.89 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c377dbf6203f845 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | cb128efc835098b | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | 0.62 % | 0.0006 | 4.76 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c35f4cf7e089ad1 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6658) without operator or topology evidence -> review | 0.62 % | -0.0007 | 4.32 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c6babf3b11e86f6 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | 0.0001 | 4.79 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c90186ef1263fec | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | 0.0003 | 3.47 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c89406033f439e7 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | -0.0005 | 4.95 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c414e07413a093a | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5161) without operator or topology evidence -> review | 0.58 % | -0.0003 | 4.85 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c349fc17f87f06d | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.58 % | 0.0006 | 5.04 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cdff9ed4f6536da | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.58 % | 0.0006 | 4.87 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c70e5fc412a1102 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.56 % | -0.0006 | 5.00 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c3693c6e44db723 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.52 % | -0.0007 | 4.87 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | cb39aa0ba43381f | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5066) without operator or topology evidence -> review | 0.51 % | 0.0002 | 5.01 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c6c12ab4b0ecff0 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6883) without operator or topology evidence -> review | 0.51 % | 0.0012 | 2.03 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c510ebdbfd4769e | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5173) without operator or topology evidence -> review | 0.34 % | 0.0007 | 0.12 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cf01a6dc193c22e | tradeoff | tradeoff | d | operator family gained: add, shift (present in C, absent in D) | 0.32 % | -0.0005 | 3.15 % | up=area,power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c0e5048389ed098 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5232) without operator or topology evidence -> review | 0.20 % | 0.0003 | 2.29 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c4067aacb79b2f2 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.14 % | 0.0005 | 0.22 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cdbc21bb7651490 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.01 % | 0.0004 | -0.18 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c82932fe11bc910 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.02 % | -0.0005 | 4.76 % | up=power down=wns |
| gpt-5.6-luna | M | cktevo_risc__btb | cb1c7a1650123de | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | -0.04 % | 0.0004 | 0.06 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c170bd16f78e6b9 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.06 % | 0.0013 | 0.09 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c6aaad519b8b8f3 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.08 % | 0.0009 | -0.10 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | cde3350f87f9b02 | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | -0.10 % | 0.0003 | 0.04 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c8a73fff48a5988 | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | -0.23 % | 0.0010 | 0.91 % | - |
| gpt-5.6-luna | M | cktevo_risc__btb | c762ae2577b7651 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7239) without operator or topology evidence -> review | -0.35 % | 0.0004 | -0.28 % | up=wns down=area |
| gpt-5.6-luna | M | cktevo_risc__btb | c69c8717b1206c2 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.38 % | 0.0020 | -0.19 % | up=wns down=area |
| gpt-5.6-luna | M | cktevo_risc__btb | c2be69cec1afe29 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.38 % | -0.0008 | 4.71 % | up=power down=area,wns |
| gpt-5.6-luna | M | cktevo_risc__btb | c7d9c9af5f876fe | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.45 % | -0.0008 | 3.29 % | up=power down=area,wns |
| gpt-5.6-luna | M | drrtl_aes | c9473593813452e | retained | retained | d | operator family gained: add (present in C, absent in D) | 0.88 % | 0.0000 | 0.93 % | - |
| gpt-5.6-luna | M | drrtl_aes | c68825008fac508 | retained | retained | d | operator family gained: add (present in C, absent in D) | 0.86 % | 0.0000 | 0.91 % | - |
| gpt-5.6-luna | M | drrtl_aes | cc6ed9a23a9f219 | retained | retained | d | operator family gained: add (present in C, absent in D) | 0.67 % | 0.0001 | 0.96 % | - |
| gpt-5.6-luna | M | drrtl_aes | cb9639f019009ed | retained | retained | d | operator family gained: add (present in C, absent in D) | 0.60 % | -0.0001 | 0.94 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cb0d66d8ab42a3a | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6893) without operator or topology evidence -> review | 2.17 % | -0.0001 | 47.47 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cb2f1ad787f355f | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6084) without operator or topology evidence -> review | 2.17 % | 0.0005 | 46.98 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cfa1899af74ad71 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7368) without operator or topology evidence -> review | 1.94 % | -0.0008 | 47.78 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c067d37e9072f2f | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7402) without operator or topology evidence -> review | 1.91 % | -0.0005 | 6.33 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | cb6e128d0630345 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5442) without operator or topology evidence -> review | 1.89 % | 0.0016 | 3.76 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c84f139038262a4 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6109) without operator or topology evidence -> review | 1.88 % | -0.0003 | 3.62 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cb6a729b70fe799 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7039) without operator or topology evidence -> review | 1.86 % | -0.0004 | 3.70 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | ca1ca629b9da0e0 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6755) without operator or topology evidence -> review | 1.86 % | -0.0005 | 5.87 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c440e025c233cf4 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7393) without operator or topology evidence -> review | 1.84 % | 0.0005 | 6.91 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cd5dddede7067c9 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5669) without operator or topology evidence -> review | 1.83 % | 0.0006 | 3.58 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c6a85c3e0a5bc97 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7277) without operator or topology evidence -> review | 1.81 % | -0.0008 | 8.12 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | cdf4749dcc28e5c | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.759) without operator or topology evidence -> review | 1.81 % | -0.0008 | 79.01 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | cdfe81131c0ca59 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.556) without operator or topology evidence -> review | 1.81 % | -0.0001 | 3.76 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c5c16a79f973086 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6266) without operator or topology evidence -> review | 1.80 % | -0.0002 | 6.88 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c819913117597d4 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6249) without operator or topology evidence -> review | 1.79 % | -0.0001 | 9.47 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cd0d0e9db70a9f4 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.749) without operator or topology evidence -> review | 1.78 % | -0.0001 | 6.28 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c02ee2f24068802 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7303) without operator or topology evidence -> review | 1.76 % | -0.0003 | 6.88 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c5279e058974af9 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7156) without operator or topology evidence -> review | 1.76 % | -0.0004 | 6.85 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | cdb6eb7a0cc147e | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.62) without operator or topology evidence -> review | 1.76 % | -0.0001 | 6.79 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c2f623df96aacc7 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6977) without operator or topology evidence -> review | 1.73 % | 0.0007 | 3.85 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c8ac30b92358b09 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6042) without operator or topology evidence -> review | 1.72 % | 0.0029 | 3.71 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c5e0e246dc0d096 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.641) without operator or topology evidence -> review | 1.71 % | 0.0014 | 6.33 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c37cf1f52827402 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7088) without operator or topology evidence -> review | 1.69 % | -0.0003 | 78.89 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | ccd0890d399d912 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6963) without operator or topology evidence -> review | 1.69 % | 0.0031 | 5.89 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c87989db34bfae6 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7446) without operator or topology evidence -> review | 1.68 % | -0.0001 | 6.88 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c61f5f635f80a15 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6489) without operator or topology evidence -> review | 1.68 % | -0.0000 | 6.26 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c78f9e21842ed3d | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.569) without operator or topology evidence -> review | 1.66 % | 0.0023 | 9.43 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cf77a678e9ae8b7 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7293) without operator or topology evidence -> review | 1.65 % | 0.0011 | 6.49 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c756f0018cb102c | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7809) without operator or topology evidence -> review | 1.64 % | 0.0001 | 78.99 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c95a13452560121 | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | 1.64 % | 0.0013 | 78.94 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c612c271b584c9a | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6839) without operator or topology evidence -> review | 1.62 % | 0.0003 | 78.98 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c3bb18ee897c19b | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6904) without operator or topology evidence -> review | 1.62 % | -0.0003 | 6.47 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c57c5189b348c22 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5722) without operator or topology evidence -> review | 1.62 % | 0.0009 | 6.40 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c39696e62eed818 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.761) without operator or topology evidence -> review | 1.61 % | 0.0049 | 79.05 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cb0248d8e669ee5 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6982) without operator or topology evidence -> review | 1.60 % | -0.0002 | 6.59 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c378193306ef619 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7121) without operator or topology evidence -> review | 1.58 % | 0.0010 | 78.97 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cfacc0c30b14024 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7072) without operator or topology evidence -> review | 1.57 % | -0.0008 | 6.33 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c2ac76a8725ac48 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7329) without operator or topology evidence -> review | 1.55 % | 0.0026 | 6.75 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cf23b56ab6749cd | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7152) without operator or topology evidence -> review | 1.54 % | -0.0000 | 6.26 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c56ca822e8a8dad | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7148) without operator or topology evidence -> review | 1.54 % | 0.0006 | 6.61 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cb3ea838eca5a11 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7336) without operator or topology evidence -> review | 1.54 % | -0.0002 | 5.37 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cc3ba66e08b070b | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7294) without operator or topology evidence -> review | 1.54 % | -0.0004 | 78.85 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c97a691496a2d8d | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7244) without operator or topology evidence -> review | 1.53 % | 0.0010 | 6.71 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c442d917c36a141 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6946) without operator or topology evidence -> review | 1.51 % | -0.0005 | 9.40 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c8e6e27bab1a19b | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7092) without operator or topology evidence -> review | 1.50 % | -0.0002 | 6.61 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c8dee9064b7cbd0 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7321) without operator or topology evidence -> review | 1.48 % | 0.0045 | 6.65 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | ce95d0d90a07569 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6223) without operator or topology evidence -> review | 1.47 % | 0.0003 | 5.48 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | caca6b65b23a4ae | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7418) without operator or topology evidence -> review | 1.45 % | 0.0010 | 6.57 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c0b9c308716c0ca | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.742) without operator or topology evidence -> review | 1.41 % | 0.0001 | 6.65 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c42f24776b06ed0 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7454) without operator or topology evidence -> review | 1.41 % | 0.0004 | 47.37 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cfb6641f434e9a3 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7223) without operator or topology evidence -> review | 1.40 % | 0.0015 | 6.57 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c80e1fb0c248175 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7218) without operator or topology evidence -> review | 1.40 % | -0.0003 | 4.99 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c0f908ce6ca52de | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7535) without operator or topology evidence -> review | 1.40 % | 0.0011 | 6.58 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c88060ad22223ae | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7457) without operator or topology evidence -> review | 1.35 % | -0.0005 | 6.48 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c6686a36d48ee70 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.716) without operator or topology evidence -> review | 1.34 % | 0.0004 | 78.96 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c8e27d8da333a13 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7526) without operator or topology evidence -> review | 1.34 % | -0.0001 | 78.40 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c7754413afe859b | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6124) without operator or topology evidence -> review | 1.32 % | 0.0004 | 6.73 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c2850299f31be7d | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7418) without operator or topology evidence -> review | 1.28 % | 0.0007 | 9.27 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cfbd2494a1f9b69 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7228) without operator or topology evidence -> review | 1.28 % | -0.0000 | 6.83 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c0496df1340690c | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6904) without operator or topology evidence -> review | 1.22 % | 0.0002 | 6.48 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cb26848e205d708 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7221) without operator or topology evidence -> review | 1.22 % | 0.0025 | 5.85 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c02c37df0b75ae4 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5906) without operator or topology evidence -> review | 1.15 % | 0.0016 | 6.36 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cf427ebca748e43 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7045) without operator or topology evidence -> review | 0.99 % | -0.0004 | 6.84 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | ca5370eea28113d | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7574) without operator or topology evidence -> review | 0.98 % | -0.0003 | 80.83 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cd43691ab940a12 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6922) without operator or topology evidence -> review | 0.87 % | -0.0008 | 80.55 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | cc8dc6be0fdbdbd | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.78 % | 0.0009 | 5.03 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c5d05affe869bcf | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.77 % | -0.0003 | 3.54 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c4f3189de50c49f | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6215) without operator or topology evidence -> review | 0.75 % | -0.0006 | 3.55 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c4262c75bc52904 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.73 % | 0.0003 | 4.98 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cc07ac23294a34b | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.72 % | 0.0002 | 47.66 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c1942962882ed60 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.69 % | 0.0001 | 5.21 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c3829f9c2003cf0 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.65 % | 0.0011 | 5.01 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | ccb1439c2da4c3d | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.64 % | -0.0002 | 5.23 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cbc2a27e1122099 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c11838f64b79481 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c320a30402d67b2 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.62 % | -0.0004 | 3.47 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c7f134a5b86e53c | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.61 % | 0.0004 | 5.00 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cab628c2b5a701d | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | 0.0003 | 3.47 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c5ede3fe3bff42d | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | 0.0003 | 3.47 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cb2eb85d36ec3e2 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.60 % | 0.0003 | 3.47 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c74f77b8ffd2395 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.53 % | 0.0008 | 3.61 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c69ed97cad8322d | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7307) without operator or topology evidence -> review | 0.51 % | 0.0000 | 6.53 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c82dd0d2343538b | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.44 % | 0.0009 | 2.36 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c7a6dd5d78908f7 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.36 % | -0.0008 | 5.01 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | c1f4a98ba063397 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.694) without operator or topology evidence -> review | 0.34 % | -0.0006 | 6.50 % | up=area,power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | cfe2a6d95d84700 | retained | retained | d | operator family gained: add, shift (present in C, absent in D) | 0.11 % | 0.0009 | 0.25 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c001525b5433058 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | 0.03 % | 0.0010 | 46.24 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | c0376a7e5efe57e | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.01 % | -0.0006 | 2.40 % | up=power down=wns |
| gpt-5.6-terra | M | cktevo_risc__btb | cd6345de8623197 | retained | retained | b | register names or clocked targets changed, flip-flop count and latency unchanged | -0.20 % | 0.0010 | -0.18 % | - |
| gpt-5.6-terra | M | cktevo_risc__btb | cdb1d8da2b89c22 | tradeoff | tradeoff | c1 | flip-flop bits 2008 -> 2080 and register cells 104 -> 32 with identical latency (no offset); text differs widely (ratio 0.6046) without operator or topology evidence -> review | -2.33 % | 0.0006 | 4.79 % | up=wns,power down=area |
| gpt-5.6-terra | M | cktevo_risc__btb | c4c214bdd7135da | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5799) without operator or topology evidence -> review | -4.08 % | 0.0001 | 5.92 % | up=power down=area |
| gpt-5.6-terra | M | cktevo_risc__btb | c80391b5b18457c | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.5509) without operator or topology evidence -> review | -4.20 % | -0.0008 | 6.08 % | up=power down=area,wns |
| gpt-5.6-terra | M | cktevo_risc__btb | cf59d92a9845134 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6007) without operator or topology evidence -> review | -4.53 % | 0.0012 | 6.78 % | up=wns,power down=area |
| gpt-5.6-terra | M | cktevo_risc__btb | c0575ae6d90223c | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.7173) without operator or topology evidence -> review | -4.95 % | 0.0005 | 45.57 % | up=wns,power down=area |
| gpt-5.6-terra | M | cktevo_risc__btb | ce27ce6b1df4761 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.643) without operator or topology evidence -> review | -12.78 % | 0.0008 | 1.78 % | up=wns down=area |
| gpt-5.6-terra | M | cktevo_risc__btb | ce4587f9e56f237 | tradeoff | tradeoff | b | register names or clocked targets changed, flip-flop count and latency unchanged; text differs widely (ratio 0.6216) without operator or topology evidence -> review | -12.98 % | -0.0006 | 2.33 % | up=power down=area,wns |
| gpt-5.6-terra | M | cktevo_risc__btb | cd2bb1f0f12080b | tradeoff | tradeoff | c1 | flip-flop bits 2008 -> 2904 and register cells 104 -> 72 with identical latency (no offset) | -40.76 % | 0.0010 | -38.96 % | up=wns down=area,power |
| gpt-5.6-terra | M | drrtl_aes | c3d70125c32f56f | retained | retained | d | operator family gained: add (present in C, absent in D) | 4.67 % | 0.0001 | 5.81 % | - |
| gpt-5.6-terra | M | drrtl_aes | c3b2f7d559df078 | retained | retained | d | operator family gained: add (present in C, absent in D) | 4.65 % | 0.0003 | 5.79 % | - |
| gpt-5.6-terra | M | drrtl_aes | ccaf578155640bc | retained | retained | d | operator family gained: add (present in C, absent in D) | 4.62 % | 0.0001 | 5.75 % | - |
| gpt-5.6-terra | M | drrtl_aes | c38d5601fca0aef | retained | retained | d | operator family gained: add (present in C, absent in D) | 4.58 % | 0.0005 | 5.67 % | - |
| gpt-5.6-terra | M | drrtl_aes | cf8550a658d94cc | retained | retained | d | operator family gained: add (present in C, absent in D) | 4.30 % | 0.0007 | 5.44 % | - |
| gpt-5.6-terra | M | drrtl_aes | cfb1796372d40bc | retained | retained | d | operator family gained: add (present in C, absent in D) | 0.76 % | -0.0000 | 0.96 % | - |
| gpt-5.6-terra | M | drrtl_aes | c8e26cda64f3c00 | retained | retained | d | operator family gained: add (present in C, absent in D) | 0.72 % | 0.0000 | 0.86 % | - |
| gpt-5.6-terra | M | drrtl_aes | c1a2a1cd2ee5279 | retained | retained | d | operator family gained: add (present in C, absent in D) | 0.64 % | -0.0000 | 0.95 % | - |
| gpt-5.6-terra | M | drrtl_aes | c025c847e79250e | retained | retained | d | operator family gained: add (present in C, absent in D) | 0.60 % | -0.0001 | 0.94 % | - |
| gpt-5.6-terra | M | drrtl_aes | cd4599d079d5d43 | retained | retained | d | operator family gained: add (present in C, absent in D) | 0.51 % | 0.0001 | 0.96 % | - |
| gpt-5.6-terra | M | drrtl_aes | cb94867eec6190e | retained | retained | d | operator family gained: add (present in C, absent in D) | 0.48 % | 0.0000 | 0.99 % | - |
| gpt-5.6-terra | M | drrtl_aes | c806fe3afde8e49 | tradeoff | - | c1 | flip-flop bits 83339 -> 83659 and register cells 10243 -> 10253 with identical latency (no offset) | -7.97 % | -0.0174 | 10.19 % | up=power down=area,wns |
| gpt-5.6-terra | M | drrtl_aes | ce4c5ef9e85a3f9 | tradeoff | tradeoff | d | operator family gained: add (present in C, absent in D) | -9.13 % | 0.0002 | 10.76 % | up=power down=area |
| gpt-5.6-terra | M | drrtl_aes | c7b95dbd66eb24b | tradeoff | - | c1 | flip-flop bits 83339 -> 83659 and register cells 10243 -> 10253 with identical latency (no offset) | -10.55 % | 0.0000 | 10.09 % | up=power down=area |

Per row: retained gains per metric (median / max over the retained candidates; WNS in clock periods) and the tradeoff composition:

| model | arm | retained | area: median / max | WNS: median / max | power: median / max | tradeoffs | composition (up = better, down = worse) |
|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 43 | -0.02 % / 1.71 % | 0.0006 / 0.0031 | 78.48 % / 82.76 % | 50 | up=area,power down=wns: 6; up=power down=area: 2; up=power down=area,wns: 31; up=power down=wns: 2; up=wns down=area: 6; up=wns down=area,power: 1; up=wns,power down=area: 2 |
| gpt-5.6-terra | B1_E4 | 121 | 0.88 % / 2.36 % | 0.0000 / 0.0039 | 5.10 % / 79.93 % | 46 | up=area down=wns: 2; up=area,power down=wns: 30; up=power down=area: 2; up=power down=area,wns: 7; up=power down=wns: 2; up=wns down=area: 1; up=wns,power down=area: 2 |
| gpt-5.6-terra | B2 | 96 | 1.33 % / 2.16 % | 0.0004 / 0.0043 | 5.90 % / 80.49 % | 39 | up=area down=wns: 1; up=area,power down=wns: 25; up=power down=area: 4; up=power down=area,wns: 3; up=power down=wns: 3; up=wns down=area: 1; up=wns,power down=area: 2 |
| gpt-5.6-terra | DrRTL_reimpl | 44 | 0.25 % / 0.82 % | 0.0006 / 0.0027 | 0.43 % / 5.25 % | 11 | up=area,power down=wns: 3; up=power down=area: 6; up=wns down=area: 1; up=wns down=area,power: 1 |
| gpt-5.6-luna | M | 44 | 0.67 % / 1.76 % | 0.0005 / 0.0027 | 4.88 % / 47.76 % | 22 | up=area,power down=wns: 17; up=power down=area,wns: 2; up=power down=wns: 1; up=wns down=area: 2 |
| gpt-5.6-terra | M | 78 | 1.47 % / 4.67 % | 0.0003 / 0.0049 | 6.31 % / 80.83 % | 33 | up=area,power down=wns: 21; up=power down=area: 3; up=power down=area,wns: 3; up=power down=wns: 1; up=wns down=area: 1; up=wns down=area,power: 1; up=wns,power down=area: 3 |

## 3. Model contrast (the same arm under two models on the same tier)

- **large / M**: gpt-5.6-luna (contrast): proven 0.134 / call, retained 2.44 / run, best gain mean 0.24 %, unusable 6, USD 2.98; gpt-5.6-terra (main): proven 0.160 / call, retained 4.33 / run, best gain mean 0.62 %, unusable 1, USD 31.32

## 4. Retained-gain curves (mean over the group's runs of the best retained area gain so far)

### large tier — by LLM calls (equal-call caliber)

| model | arm | 5 calls | 10 calls | 20 calls | 30 calls | 40 calls | 50 calls | 60 calls |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 † | pending | pending | 0.04 % † | 0.13 % † | 0.23 % † | 0.25 % † | 0.28 % † |
| gpt-5.6-terra | B1_E4 † | 0.13 % † | 0.28 % † | 0.44 % † | 0.44 % † | 0.46 % † | 0.46 % † | 0.49 % † |
| gpt-5.6-terra | B2 † | 0.10 % † | 0.15 % † | 0.26 % † | 0.37 % † | 0.38 % † | 0.40 % † | 0.41 % † |
| gpt-5.6-terra | DrRTL_reimpl † | 0.03 % † | 0.03 % † | 0.03 % † | 0.06 % † | 0.09 % † | 0.09 % † | 0.09 % † |
| gpt-5.6-luna | M † | 0.02 % † | 0.05 % † | 0.12 % † | 0.16 % † | 0.22 % † | 0.23 % † | 0.24 % † |
| gpt-5.6-terra | M † | 0.07 % † | 0.22 % † | 0.27 % † | 0.33 % † | 0.56 % † | 0.56 % † | 0.62 % † |

### large tier — by visible DC hours per run

- gpt-5.6-terra / B0: 0.25 h → 0.00 %, 1.25 h → 0.04 %, 2.25 h → 0.12 %, 3.25 h → 0.18 %, 4.25 h → 0.25 %, 5.25 h → 0.28 %, 6.25 h → 0.28 %
- gpt-5.6-terra / B1_E4: 0.25 h → 0.09 %, 1.75 h → 0.40 %, 3.25 h → 0.46 %, 4.75 h → 0.48 %, 6.25 h → 0.48 %, 7.75 h → 0.48 %, 9.25 h → 0.49 %
- gpt-5.6-terra / B2: 0.25 h → 0.10 %, 1.50 h → 0.25 %, 2.75 h → 0.36 %, 4.00 h → 0.40 %, 5.25 h → 0.40 %, 6.50 h → 0.40 %, 7.75 h → 0.41 %
- gpt-5.6-terra / DrRTL_reimpl: 0.25 h → 0.01 %, 2.50 h → 0.06 %, 4.75 h → 0.06 %, 7.00 h → 0.06 %, 9.25 h → 0.09 %, 11.50 h → 0.09 %, 13.75 h → 0.09 %
- gpt-5.6-luna / M: 0.25 h → 0.05 %, 0.75 h → 0.12 %, 1.25 h → 0.22 %, 1.75 h → 0.24 %, 2.25 h → 0.24 %, 2.75 h → 0.24 %
- gpt-5.6-terra / M: 0.25 h → 0.07 %, 0.75 h → 0.28 %, 1.25 h → 0.33 %, 1.75 h → 0.33 %, 2.25 h → 0.62 %, 2.75 h → 0.62 %, 3.25 h → 0.62 %

## 5. Correctness (the LLM's equivalence-preserving rate)

| tier | model | design | runs | candidates | proven | proven rate |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | cktevo_hsm__hsm | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_hsm__hsm | 15 | 875 | 0 | 0.0 % |
| large | gpt-5.6-luna | cktevo_nn_engine__spikeNeuron8_H7 | 3 | 180 | 21 | 11.7 % |
| large | gpt-5.6-terra | cktevo_nn_engine__spikeNeuron8_H7 | 15 | 870 | 293 | 33.7 % |
| large | gpt-5.6-luna | cktevo_risc__btb | 3 | 180 | 102 | 56.7 % |
| large | gpt-5.6-terra | cktevo_risc__btb | 15 | 871 | 650 | 74.6 % |
| large | gpt-5.6-luna | drrtl_LSTM | 3 | 0 | 0 | - |
| large | gpt-5.6-terra | drrtl_LSTM | 15 | 0 | 0 | - |
| large | gpt-5.6-luna | drrtl_aes | 3 | 180 | 59 | 32.8 % |
| large | gpt-5.6-terra | drrtl_aes | 15 | 870 | 518 | 59.5 % |
| large | gpt-5.6-luna | drrtl_tv80 (verification limit) | 3 | 174 | 0 | 0.0 % |
| large | gpt-5.6-terra | drrtl_tv80 (verification limit) | 15 | 870 | 0 | 0.0 % |

### 5a. Inconclusive proofs per class and per design (DECISION 2026-09-18 D2)

- large tier — by class: a: 188, b: 1031, c1: 141, d: 102; by design: drrtl_tv80: 669, cktevo_nn_engine__spikeNeuron8_H7: 311, cktevo_hsm__hsm: 273, drrtl_aes: 125, cktevo_risc__btb: 84


LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): none on the reported tiers; designs below the rate whose note applies instead (§0a): cktevo_hsm__hsm — mixed (sim_fail 65 %, inconclusive 30 %), drrtl_tv80 — verification limit (wall-clock cap under CPU contention).

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 213, 'b': 444, 'c1': 81, 'd': 77, 'free': 5}; requested → produced a->a: 15, a->b: 41, a->c1: 3, a->d: 11, b->a: 30, b->b: 27, b->c1: 1, b->d: 6, c1->a: 35, c1->b: 136, c1->c1: 38, c1->d: 16, d->a: 94, d->b: 174, d->c1: 28, d->d: 31, free->a: 39, free->b: 66, free->c1: 11, free->d: 13, free->free: 5
- large / gpt-5.6-terra / B0: produced {'a': 96, 'b': 547, 'c1': 60, 'd': 156, 'free': 1}; requested → produced a->a: 26, a->b: 91, a->c1: 4, a->d: 25, b->a: 21, b->b: 59, b->c1: 1, b->d: 21, c1->a: 12, c1->b: 85, c1->c1: 36, c1->d: 28, d->a: 8, d->b: 150, d->c1: 8, d->d: 36, free->a: 29, free->b: 162, free->c1: 11, free->d: 46, free->free: 1
- large / gpt-5.6-terra / B1_E4: produced {'a': 154, 'b': 485, 'c1': 72, 'd': 145}; requested → produced a->a: 26, a->b: 110, a->c1: 7, a->d: 27, b->a: 50, b->b: 49, b->c1: 5, b->d: 29, c1->a: 16, c1->b: 102, c1->c1: 9, c1->d: 12, d->a: 29, d->b: 104, d->c1: 18, d->d: 23, free->a: 33, free->b: 120, free->c1: 33, free->d: 54
- large / gpt-5.6-terra / B2: produced {'a': 202, 'b': 507, 'c1': 66, 'd': 110}; requested → produced a->a: 30, a->b: 96, a->c1: 5, a->d: 2, b->a: 52, b->b: 57, b->d: 13, c1->a: 32, c1->b: 103, c1->c1: 11, c1->d: 19, d->a: 42, d->b: 129, d->c1: 30, d->d: 24, free->a: 46, free->b: 122, free->c1: 20, free->d: 52
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 269, 'b': 288, 'c1': 20, 'd': 1, 'free': 2}; requested → produced free->a: 269, free->b: 288, free->c1: 20, free->d: 1, free->free: 2
- large / gpt-5.6-terra / M: produced {'a': 181, 'b': 480, 'c1': 102, 'd': 74, 'free': 1}; requested → produced a->a: 7, a->b: 49, a->c1: 1, a->d: 2, b->a: 55, b->b: 29, b->d: 12, c1->a: 37, c1->b: 152, c1->c1: 40, c1->d: 32, d->a: 69, d->b: 198, d->c1: 47, d->d: 14, free->a: 13, free->b: 52, free->c1: 14, free->d: 14, free->free: 1

## 7. Runs and anomalies

Runs on the reported tiers: 108 (90 done, 0 running, 18 not started). No run in an abnormal status.

## 7a. Operational changes during the run (DECISIONS 2026-09-16; verdict definitions, floors, budgets and the stack unchanged)

Hidden DC registrations capped at 8 from 2026-09-16T14:30; split equivalence pipeline, provisional diagnosis and proof ordering from 2026-09-16T15:14; positive provisional verdicts withheld from the model from 2026-09-16T16:03.

- Provisional-versus-final diagnosis agreement: 2652 of 2896 proven candidates with a final diagnosis agree (91.6 %); 14971 candidates received a provisional label (absorbed 88, absorbed_identical 758, duplicate 967, harmful 505, improved 8082, no_gain 2697, noise 116, retained 766, tradeoff 992), 3905 of them were not proven, 8170 still wait for the proof or the diagnosis, 9780 labels withheld from the model. Disagreements: tradeoff→duplicate; tradeoff→duplicate; retained→duplicate; harmful→duplicate; retained→duplicate; retained→duplicate; retained→duplicate; tradeoff→duplicate.
- Positive provisional feedback exposure (window 2026-09-16T15:14 to 2026-09-16T16:03): 15 LLM calls carried 25 positive pending blocks (2 runs); 8 candidates behind them — proofs since: inconclusive 8.
- Cross-run verdict reuse since 2026-09-16T15:14: 0 proofs copied from a decided record of the same pair ({}), over 24062 split-pipeline proofs of 57828 equivalence records; sim records missing: 0.

Equivalence jobs finished per hour on the VC Formal pool since the throttle (2026-09-16T14:30), by the candidate's verdict:

| hour | finished | proven | inconclusive | proven : inconclusive | falsified | rejected | sim_fail |
|---|---|---|---|---|---|---|---|
| 2026-09-16T14 | 94 | 25 | 18 | 1.39 | 6 | 37 | 8 |
| 2026-09-16T15 | 101 | 43 | 26 | 1.65 | 8 | 21 | 3 |
| 2026-09-16T16 | 88 | 35 | 35 | 1.0 | 15 | 0 | 3 |
| 2026-09-16T17 | 82 | 49 | 31 | 1.58 | 2 | 0 | 0 |
| 2026-09-16T18 | 81 | 39 | 36 | 1.08 | 4 | 0 | 2 |
| 2026-09-16T19 | 90 | 47 | 34 | 1.38 | 4 | 1 | 4 |
| 2026-09-16T20 | 79 | 33 | 35 | 0.94 | 3 | 1 | 7 |
| 2026-09-16T21 | 84 | 61 | 20 | 3.05 | 3 | 0 | 0 |
| 2026-09-16T22 | 95 | 58 | 30 | 1.93 | 7 | 0 | 0 |
| 2026-09-16T23 | 86 | 51 | 28 | 1.82 | 7 | 0 | 0 |
| 2026-09-17T00 | 85 | 43 | 41 | 1.05 | 1 | 0 | 0 |
| 2026-09-17T01 | 74 | 38 | 26 | 1.46 | 10 | 0 | 0 |
| 2026-09-17T02 | 54 | 21 | 31 | 0.68 | 2 | 0 | 0 |
| 2026-09-17T03 | 70 | 36 | 34 | 1.06 | 0 | 0 | 0 |
| 2026-09-17T04 | 51 | 27 | 19 | 1.42 | 5 | 0 | 0 |
| 2026-09-17T05 | 78 | 52 | 23 | 2.26 | 3 | 0 | 0 |
| 2026-09-17T06 | 66 | 35 | 28 | 1.25 | 3 | 0 | 0 |
| 2026-09-17T07 | 58 | 28 | 21 | 1.33 | 9 | 0 | 0 |
| 2026-09-17T08 | 62 | 27 | 33 | 0.82 | 2 | 0 | 0 |
| 2026-09-17T09 | 76 | 42 | 25 | 1.68 | 9 | 0 | 0 |
| 2026-09-17T10 | 64 | 40 | 22 | 1.82 | 2 | 0 | 0 |
| 2026-09-17T11 | 147 | 97 | 23 | 4.22 | 27 | 0 | 0 |
| 2026-09-17T12 | 169 | 137 | 23 | 5.96 | 9 | 0 | 0 |
| 2026-09-17T13 | 106 | 63 | 25 | 2.52 | 18 | 0 | 0 |
| 2026-09-17T14 | 97 | 66 | 22 | 3.0 | 9 | 0 | 0 |
| 2026-09-17T15 | 94 | 57 | 28 | 2.04 | 9 | 0 | 0 |
| 2026-09-17T16 | 74 | 42 | 31 | 1.35 | 1 | 0 | 0 |
| 2026-09-17T17 | 84 | 38 | 39 | 0.97 | 7 | 0 | 0 |
| 2026-09-17T18 | 37 | 3 | 34 | 0.09 | 0 | 0 | 0 |
| 2026-09-17T19 | 51 | 20 | 30 | 0.67 | 1 | 0 | 0 |
| 2026-09-17T20 | 66 | 29 | 37 | 0.78 | 0 | 0 | 0 |
| 2026-09-17T21 | 151 | 102 | 26 | 3.92 | 23 | 0 | 0 |
| 2026-09-17T22 | 289 | 216 | 20 | 10.8 | 51 | 1 | 1 |
| 2026-09-17T23 | 253 | 197 | 25 | 7.88 | 31 | 0 | 0 |
| 2026-09-18T00 | 257 | 196 | 16 | 12.25 | 45 | 0 | 0 |
| 2026-09-18T01 | 292 | 209 | 36 | 5.81 | 47 | 0 | 0 |
| 2026-09-18T02 | 292 | 239 | 20 | 11.95 | 33 | 0 | 0 |
| 2026-09-18T03 | 357 | 282 | 23 | 12.26 | 52 | 0 | 0 |
| 2026-09-18T04 | 354 | 294 | 35 | 8.4 | 25 | 0 | 0 |
| 2026-09-18T05 | 306 | 212 | 29 | 7.31 | 37 | 0 | 0 |
| 2026-09-18T06 | 606 | 469 | 20 | 23.45 | 83 | 0 | 0 |
| 2026-09-18T07 | 557 | 443 | 25 | 17.72 | 81 | 0 | 0 |
| 2026-09-18T08 | 279 | 176 | 20 | 8.8 | 61 | 0 | 0 |
| 2026-09-18T09 | 520 | 387 | 18 | 21.5 | 105 | 0 | 0 |
| 2026-09-18T10 | 496 | 363 | 24 | 15.12 | 109 | 0 | 0 |
| 2026-09-18T11 | 565 | 464 | 18 | 25.78 | 83 | 0 | 0 |
| 2026-09-18T12 | 542 | 509 | 21 | 24.24 | 12 | 0 | 0 |
| 2026-09-18T13 | 613 | 578 | 21 | 27.52 | 14 | 0 | 0 |
| 2026-09-18T14 | 705 | 662 | 16 | 41.38 | 23 | 0 | 0 |
| 2026-09-18T15 | 700 | 651 | 17 | 38.29 | 32 | 0 | 0 |
| 2026-09-18T16 | 425 | 394 | 20 | 19.7 | 11 | 0 | 0 |
| 2026-09-18T17 | 344 | 299 | 32 | 9.34 | 13 | 0 | 0 |
| 2026-09-18T18 | 274 | 225 | 43 | 5.23 | 6 | 0 | 0 |
| 2026-09-18T19 | 184 | 141 | 37 | 3.81 | 6 | 0 | 0 |
| 2026-09-18T20 | 207 | 170 | 31 | 5.48 | 6 | 0 | 0 |
| 2026-09-18T21 | 186 | 130 | 37 | 3.51 | 19 | 0 | 0 |
| 2026-09-18T22 | 191 | 144 | 28 | 5.14 | 19 | 0 | 0 |
| 2026-09-18T23 | 186 | 134 | 30 | 4.47 | 22 | 0 | 0 |
| 2026-09-19T00 | 157 | 119 | 33 | 3.61 | 5 | 0 | 0 |
| 2026-09-19T01 | 129 | 83 | 41 | 2.02 | 5 | 0 | 0 |
| 2026-09-19T02 | 99 | 60 | 37 | 1.62 | 2 | 0 | 0 |
| 2026-09-19T03 | 122 | 84 | 32 | 2.62 | 6 | 0 | 0 |
| 2026-09-19T04 | 140 | 97 | 35 | 2.77 | 8 | 0 | 0 |
| 2026-09-19T05 | 139 | 102 | 28 | 3.64 | 9 | 0 | 0 |
| 2026-09-19T06 | 161 | 110 | 35 | 3.14 | 16 | 0 | 0 |
| 2026-09-19T07 | 162 | 131 | 22 | 5.95 | 9 | 0 | 0 |
| 2026-09-19T08 | 149 | 110 | 34 | 3.24 | 5 | 0 | 0 |
| 2026-09-19T09 | 182 | 134 | 33 | 4.06 | 15 | 0 | 0 |
| 2026-09-19T10 | 135 | 89 | 33 | 2.7 | 13 | 0 | 0 |
| 2026-09-19T11 | 189 | 140 | 35 | 4.0 | 14 | 0 | 0 |
| 2026-09-19T12 | 143 | 101 | 38 | 2.66 | 4 | 0 | 0 |
| 2026-09-19T13 | 222 | 178 | 36 | 4.94 | 8 | 0 | 0 |
| 2026-09-19T14 | 382 | 314 | 41 | 7.66 | 27 | 0 | 0 |
| 2026-09-19T15 | 201 | 146 | 32 | 4.56 | 23 | 0 | 0 |
| 2026-09-19T16 | 172 | 129 | 32 | 4.03 | 11 | 0 | 0 |
| 2026-09-19T17 | 181 | 125 | 34 | 3.68 | 22 | 0 | 0 |
| 2026-09-19T18 | 192 | 125 | 28 | 4.46 | 39 | 0 | 0 |
| 2026-09-19T19 | 64 | 33 | 27 | 1.22 | 4 | 0 | 0 |
| 2026-09-19T20 | 70 | 34 | 34 | 1.0 | 2 | 0 | 0 |
| 2026-09-19T21 | 87 | 48 | 35 | 1.37 | 4 | 0 | 0 |
| 2026-09-19T22 | 190 | 143 | 31 | 4.61 | 16 | 0 | 0 |
| 2026-09-19T23 | 110 | 77 | 26 | 2.96 | 7 | 0 | 0 |
| 2026-09-20T00 | 129 | 81 | 31 | 2.61 | 17 | 0 | 0 |
| 2026-09-20T01 | 106 | 64 | 28 | 2.29 | 14 | 0 | 0 |
| 2026-09-20T02 | 103 | 62 | 28 | 2.21 | 13 | 0 | 0 |
| 2026-09-20T03 | 108 | 60 | 35 | 1.71 | 13 | 0 | 0 |
| 2026-09-20T04 | 82 | 42 | 31 | 1.35 | 9 | 0 | 0 |
| 2026-09-20T05 | 112 | 62 | 30 | 2.07 | 20 | 0 | 0 |
| 2026-09-20T06 | 241 | 185 | 36 | 5.14 | 20 | 0 | 0 |
| 2026-09-20T07 | 179 | 133 | 36 | 3.69 | 10 | 0 | 0 |
| 2026-09-20T08 | 80 | 44 | 26 | 1.69 | 10 | 0 | 0 |
| 2026-09-20T09 | 151 | 116 | 32 | 3.62 | 3 | 0 | 0 |
| 2026-09-20T10 | 226 | 187 | 33 | 5.67 | 6 | 0 | 0 |
| 2026-09-20T11 | 153 | 117 | 30 | 3.9 | 6 | 0 | 0 |
| 2026-09-20T12 | 93 | 59 | 28 | 2.11 | 6 | 0 | 0 |
| 2026-09-20T13 | 72 | 45 | 27 | 1.67 | 0 | 0 | 0 |
| 2026-09-20T14 | 96 | 64 | 32 | 2.0 | 0 | 0 | 0 |
| 2026-09-20T15 | 129 | 102 | 27 | 3.78 | 0 | 0 | 0 |
| 2026-09-20T16 | 152 | 124 | 26 | 4.77 | 2 | 0 | 0 |
| 2026-09-20T17 | 102 | 71 | 25 | 2.84 | 6 | 0 | 0 |
| 2026-09-20T18 | 77 | 36 | 35 | 1.03 | 6 | 0 | 0 |
| 2026-09-20T19 | 86 | 56 | 28 | 2.0 | 2 | 0 | 0 |
| 2026-09-20T20 | 90 | 61 | 23 | 2.65 | 6 | 0 | 0 |
| 2026-09-20T21 | 263 | 226 | 27 | 8.37 | 10 | 0 | 0 |
| 2026-09-20T22 | 684 | 662 | 22 | 30.09 | 0 | 0 | 0 |
| 2026-09-20T23 | 980 | 959 | 14 | 68.5 | 7 | 0 | 0 |
| 2026-09-21T00 | 1074 | 945 | 8 | 118.12 | 121 | 0 | 0 |
| 2026-09-21T01 | 1112 | 1026 | 4 | 256.5 | 82 | 0 | 0 |
| 2026-09-21T02 | 1021 | 945 | 0 | - | 76 | 0 | 0 |
| 2026-09-21T03 | 178 | 166 | 0 | - | 12 | 0 | 0 |

## 7b. Verification conditions per arm-model row (DECISION 2026-09-18 item 5c: median host load and VC Formal wait during the row's runs)

| tier | model | arm | proofs | VC Formal queue wait: median / q95 (min) | median 1-min load over the row's run-minutes | run-minutes with a load sample (coverage) |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 573 | 158.2 / 661.6 | 97.3 | 11697 (48 %) |
| large | gpt-5.6-terra | B0 | 825 | 106.3 / 507.1 | 97.3 | 11697 (51 %) |
| large | gpt-5.6-terra | B1_E4 | 802 | 139.9 / 510.4 | 97.3 | 11697 (51 %) |
| large | gpt-5.6-terra | B2 | 814 | 120.2 / 483.9 | 97.3 | 11697 (52 %) |
| large | gpt-5.6-terra | DrRTL_reimpl | 578 | 149.9 / 481.0 | 97.3 | 11697 (56 %) |
| large | gpt-5.6-terra | M | 619 | 139.9 / 635.0 | 97.3 | 11697 (49 %) |

The load log (scripts/load_logger.py, one sample per minute) starts 2026-09-18 05:49; rows whose runs predate it show a partial coverage — the VC Formal wait comes from the queue's own timestamps and covers every proof.

## 7c. Verification conditions by host load (DECISION 2026-09-18 (h) item 1): inconclusive share of finished proofs at a 1-minute load above / at or below 100, per design and class

Proofs started from 2026-09-18T05:49:54 (the load log's first sample) with a load sample within two minutes before the start: 0.

| design | class | proofs at load > threshold | inconclusive share | proofs at load ≤ threshold | inconclusive share |
|---|---|---|---|---|---|

Search slots at render time (DECISION 2026-09-19 (j) item 1c): generating 0 (max 24), waiting for verdicts 0, queued 18; waiting runs counted against the cap: no.

| arm-model row | unverified-at-build fraction (generations built in the last hour, medium tier) |
|---|---|
| (no generation built in the last hour) | - |

| lane | queued proofs | seats | mean proof minutes (6 h) | estimated wait of a new proof (min) | unverified-at-build (lane, last hour) | idle seat-minutes (last hour) |
|---|---|---|---|---|---|---|
| spi | 0 | 1 | 51 | 0 | - | 0.0 of 0 |
| uart | 0 | 48 | 18 | 0 | - | 2880.0 of 2880 |
| cpu | 0 | 1 | 51 | 0 | - | 0.0 of 0 |
| router | 0 | 1 | 5 | 0 | - | 0.0 of 0 |
| simple_spi | 0 | 1 | 108 | 0 | - | 0.0 of 0 |
| small | 0 | 1 | 1 | 0 | - | - |
| window | 0 | 2 | 68 | 0 | - | 120.0 of 120 |

| design | unverified-at-build (last hour) |
|---|---|
| (none) | - |

