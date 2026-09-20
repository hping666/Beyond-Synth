# Data for paper Section III — Measuring Retained Gain (2026-09-20; visible layer only; interim)

Generated 2026-09-20T04:40 by scripts/report_paper_sec3.py (git e0322cf7dff0, cfg de7d24d19295); floor_version **phase4**; duplicates collapsed as in spec 04 §B step 3; data reports/data/paper_sec3.json; every table's source in §S. Phase 5 is interim (runs at generation: {'medium': {'done': 297, 'created': 35, 'running': 44}, 'small': {'created': 120, 'done': 1, 'running': 5}, 'large': {'done': 90, 'created': 18}}).

## A. Table I — noise floor on the frozen phase4 floor table

Definitions (docs/spec/02-noise-floor.md (floor class) and reports/phase2.md §2 (rule A)): floor class — quiet (every |δ_area| ≤ noise.quiet_max_abs), offset (median |δ| above that and MAD ≈ 0: every perturbation shifted together), spread otherwise; stored next to the floor. A retained gain on an offset design is flagged (noise.quiet_max_abs = 0.001); rule A — t_D = max(2.0 × σ_robust, the design's own max |δ| incl. P0, pooled q90); designs without a measured floor carry the pooled minimum (floor_source = pooled).

| quantity | frozen phase4 table (this value) | n | Phase 2 value (99 designs) where it differs |
|---|---|---|---|
| designs with a measured floor / on the pooled minimum | 148 / 25 | 173 designs | Phase 2 snapshot (148 set designs): measured 148, pooled 25; G1 (99 designs): floors for 99 of 128 |
| floor classes quiet / spread / offset | 114 / 29 / 5 (pooled 25) | 148 measured | 72 / 21 / 6 of 99 (reports/phase2.md §6 G1) |
| perturbation records leaving E4 area and cell count unchanged | 86.2 % | 1827 records, 150 designs | 88 % (reports/phase2.md §6 G1, 99 designs) |
| netlists changed by renaming alone (P1_rename) at E1 / at E4 | 27.6 % / 5.3 % | 678 / 678 rename records | E1 29 %, E4 5 % (reports/phase2.md §6 G1) |
| designs with a perturbation moving E4 area by > 1 % / > 5 % | 24 / 12 (max 18.7 %) | 150 designs with records | 18 of 99 > 1 %, 9 > 5 %, max 18.7 % (reports/phase2.md §6 G1) |
| design-weighted pooled q90 / q95 / q99 of \|δ_area\| at E4 | 0.00 % / 1.45 % / 16.24 % (record-weighted 0.35 % / 4.61 % / 18.65 %) | 1827 records, 150 designs | frozen pooled minimum (design-weighted q90 of the phase4 snapshot) 0.279 % |
| pooled minima area / power / WNS (exact) | 0.0027938 = 0.28 % / 0.0222275 = 2.22 % / 0.0003018 = 0.030 % of the period | frozen table | Phase 2 snapshot identical ({'area': 0.0027938146505548643, 'power_saif': 0.022227533067402338, 'tns': 0.0, 'wns': 0.0003017775}); G1 text (99 designs): 0.29 % / 1.4 % / 0.07 % |
| largest single effect at E4 | cktevo_mem_ctrl__mc_rf (P3_expr): area 18.7 %, power 64.2 % | 1 record | mc_rf +18.7 % area and +64 % power from the re-print P0 (reports/phase2.md §6 G1) |

The rows above use every ok E4 record of the table's designs (any clock). On the floor table's own basis — SEQ-proven perturbations at Φ_main, the latest record per perturbation, the records the floor rows were computed from — the same quantities read:

| quantity (floor basis) | value | n |
|---|---|---|
| records leaving E4 area and cell count unchanged | 84.1 % | 1571 records, 150 designs |
| netlists changed by renaming alone at E1 / at E4 | 29.8 % / 6.2 % | 574 / 578 rename records |
| designs with a perturbation moving E4 area by > 1 % / > 5 % | 24 / 12 (max 18.7 %) | 150 designs |
| pooled q90 / q95 / q99 of \|δ_area\| at E4, design-weighted (record-weighted) | 0.000 % / 1.454 % / 16.245 % (0.492 % / 5.680 % / 18.648 %) | 1571 records, 150 designs |
| pooled q90 design-weighted, power / WNS | 1.456 % / 0.002 % | 1305 / 1571 records |
| **the frozen pooled minima's own basis: the set designs (split dev / held)** — design-weighted q90 / q95 / q99 of \|δ_area\| (record-weighted) | 0.279 % / 4.695 % / 16.250 % (1.372 % / 7.744 % / 18.660 %) | 128 set designs, 105 with records, 1247 records |
| pooled minima reproduced on that basis (area / power / WNS) | 0.279 % / 2.223 % / 0.030 % — the frozen values exactly | design-weighted zero mass 88.0 % of \|δ_area\| is 0 on the set basis, 90.1 % over all table designs (q90 = 0 there) |
| E4 tail (> 1 %) by type / by family | {'P2_reorder': 87, 'P4_ctrl': 19, 'P1_rename': 16, 'P3_expr': 17, 'P0_roundtrip': 2} / {'CktEvo': {'P2_reorder': 72, 'P4_ctrl': 12, 'P1_rename': 16, 'P3_expr': 16, 'P0_roundtrip': 2}, 'RTLLM': {'P2_reorder': 4}, 'RTL-OPT': {'P4_ctrl': 4, 'P2_reorder': 8}, 'RTLRewriter': {'P2_reorder': 3, 'P4_ctrl': 3, 'P3_expr': 1}} | |

E4 tail (records with |δ_area| > 1 %) by perturbation type over the whole frozen table: {'P2_reorder': 88, 'P4_ctrl': 19, 'P1_rename': 16, 'P3_expr': 17, 'P0_roundtrip': 2} of 142 tail records (all E4 records by type {'P2_reorder': 482, 'P1_rename': 678, 'P4_ctrl': 210, 'P0_roundtrip': 175, 'P3_expr': 254, 'P1_text': 28}); per design family: {'CktEvo': {'P2_reorder': 73, 'P4_ctrl': 12, 'P1_rename': 16, 'P3_expr': 16, 'P0_roundtrip': 2}, 'RTL-OPT': {'P4_ctrl': 4, 'P2_reorder': 8}, 'RTLLM': {'P2_reorder': 4}, 'RTLRewriter': {'P2_reorder': 3, 'P4_ctrl': 3, 'P3_expr': 1}} (records per family {'CktEvo': 386, 'Dr.RTL': 214, 'RTLLM': 445, 'RTL-OPT': 338, 'RTLRewriter': 444}).

## B. Fig. 3 — survival per class and level (Phase 4 objects)

255 diagnosed objects with an E4 record ({'harmful': 20, 'tradeoff': 54, 'absorbed_identical': 59, 'retained': 75, 'absorbed': 15, 'noise': 32}), 168 in the B0 layer; 255 with a record at every rung E1–E4. the map counts 255 diagnosed objects (verdict proven or proven_sim_only, label not duplicate, E4 record present); the strictly proven set has 254 — the object that differs is [('c50bcff7d1f3960', 'rtlrewriter_fsm_small_case__example3', 'llm', 'c2', 'harmful')] (proven by simulation only, class c2, harmful at E4); 255 of the 255 carry a record at every rung E1–E4.

**Panel 1 — B0 layer — survival = retained or trade-off at the level (some metric above the level's rule-A t_D)** (cells: survive / n)

| class | E1 | E1d | E2 | E2g | E3 | E4 |
|---|---|---|---|---|---|---|
| a | 2 / 33 (6 %) | - | 2 / 33 (6 %) | - | 2 / 33 (6 %) | 2 / 33 (6 %) |
| b | 51 / 84 (61 %) | - | 56 / 84 (67 %) | - | 50 / 84 (60 %) | 44 / 84 (52 %) |
| c1 | 19 / 19 (100 %) | - | 19 / 19 (100 %) | - | 19 / 19 (100 %) | 19 / 19 (100 %) |
| c2 | - | - | - | - | - | - |
| d | 27 / 32 (84 %) | - | 20 / 32 (62 %) | - | 15 / 32 (47 %) | 32 / 32 (100 %) |

**Panel 1 — B0 layer — the §2 map cell: area gain above t_D at the level** (cells: survive / n)

| class | E1 | E1d | E2 | E2g | E3 | E4 |
|---|---|---|---|---|---|---|
| a | 2 / 33 (6 %) | - | 2 / 33 (6 %) | - | 2 / 33 (6 %) | 2 / 33 (6 %) |
| b | 41 / 84 (49 %) | - | 41 / 84 (49 %) | - | 39 / 84 (46 %) | 41 / 84 (49 %) |
| c1 | 17 / 19 (89 %) | - | 19 / 19 (100 %) | - | 19 / 19 (100 %) | 19 / 19 (100 %) |
| c2 | - | - | - | - | - | - |
| d | 27 / 32 (84 %) | - | 19 / 32 (59 %) | - | 6 / 32 (19 %) | 30 / 32 (94 %) |

**Panel 1 — B0 layer — materiality: some metric above 1 % area / 2 % power / 1 % WNS** (cells: survive / n)

| class | E1 | E1d | E2 | E2g | E3 | E4 |
|---|---|---|---|---|---|---|
| a | 20 / 33 (61 %) | 3 / 33 (9 %) | 7 / 33 (21 %) | 2 / 33 (6 %) | 9 / 33 (27 %) | 10 / 33 (30 %) |
| b | 57 / 84 (68 %) | 52 / 84 (62 %) | 46 / 84 (55 %) | 39 / 84 (46 %) | 68 / 84 (81 %) | 48 / 84 (57 %) |
| c1 | 19 / 19 (100 %) | 19 / 19 (100 %) | 19 / 19 (100 %) | 19 / 19 (100 %) | 19 / 19 (100 %) | 19 / 19 (100 %) |
| c2 | - | - | - | - | - | - |
| d | 27 / 32 (84 %) | 14 / 32 (44 %) | 20 / 32 (62 %) | 25 / 32 (78 %) | 18 / 32 (56 %) | 28 / 32 (88 %) |

**Panel 1 — B0 layer — materiality, area only (> 1 %)** (cells: survive / n)

| class | E1 | E1d | E2 | E2g | E3 | E4 |
|---|---|---|---|---|---|---|
| a | 9 / 33 (27 %) | 2 / 33 (6 %) | 2 / 33 (6 %) | 2 / 33 (6 %) | 6 / 33 (18 %) | 6 / 33 (18 %) |
| b | 48 / 84 (57 %) | 47 / 84 (56 %) | 40 / 84 (48 %) | 36 / 84 (43 %) | 65 / 84 (77 %) | 39 / 84 (46 %) |
| c1 | 19 / 19 (100 %) | 17 / 19 (89 %) | 19 / 19 (100 %) | 19 / 19 (100 %) | 19 / 19 (100 %) | 19 / 19 (100 %) |
| c2 | - | - | - | - | - | - |
| d | 25 / 32 (78 %) | 14 / 32 (44 %) | 19 / 32 (59 %) | 25 / 32 (78 %) | 6 / 32 (19 %) | 26 / 32 (81 %) |

**Panel 2 — all diagnosed objects — survival = retained or trade-off at the level (some metric above the level's rule-A t_D)** (cells: survive / n)

| class | E1 | E1d | E2 | E2g | E3 | E4 |
|---|---|---|---|---|---|---|
| a | 31 / 75 (41 %) | - | 17 / 75 (23 %) | - | 17 / 75 (23 %) | 17 / 75 (23 %) |
| b | 66 / 109 (61 %) | - | 65 / 109 (60 %) | - | 59 / 109 (54 %) | 54 / 109 (50 %) |
| c1 | 23 / 24 (96 %) | - | 22 / 24 (92 %) | - | 22 / 24 (92 %) | 23 / 24 (96 %) |
| c2 | 0 / 2 (0 %) | - | 1 / 2 (50 %) | - | 1 / 2 (50 %) | 1 / 2 (50 %) |
| d | 37 / 45 (82 %) | - | 25 / 45 (56 %) | - | 20 / 45 (44 %) | 37 / 45 (82 %) |

**Panel 2 — all diagnosed objects — the §2 map cell: area gain above t_D at the level** (cells: survive / n)

| class | E1 | E1d | E2 | E2g | E3 | E4 |
|---|---|---|---|---|---|---|
| a | 25 / 75 (33 %) | - | 11 / 75 (15 %) | - | 11 / 75 (15 %) | 12 / 75 (16 %) |
| b | 54 / 109 (50 %) | - | 46 / 109 (42 %) | - | 44 / 109 (40 %) | 47 / 109 (43 %) |
| c1 | 21 / 24 (88 %) | - | 22 / 24 (92 %) | - | 21 / 24 (88 %) | 21 / 24 (88 %) |
| c2 | 0 / 2 (0 %) | - | 1 / 2 (50 %) | - | 1 / 2 (50 %) | 1 / 2 (50 %) |
| d | 34 / 45 (76 %) | - | 22 / 45 (49 %) | - | 9 / 45 (20 %) | 33 / 45 (73 %) |

**Panel 2 — all diagnosed objects — materiality: some metric above 1 % area / 2 % power / 1 % WNS** (cells: survive / n)

| class | E1 | E1d | E2 | E2g | E3 | E4 |
|---|---|---|---|---|---|---|
| a | 49 / 75 (65 %) | 30 / 75 (40 %) | 20 / 75 (27 %) | 15 / 75 (20 %) | 22 / 75 (29 %) | 23 / 75 (31 %) |
| b | 71 / 109 (65 %) | 64 / 109 (59 %) | 54 / 109 (50 %) | 46 / 109 (42 %) | 76 / 109 (70 %) | 56 / 109 (51 %) |
| c1 | 23 / 24 (96 %) | 23 / 24 (96 %) | 22 / 24 (92 %) | 23 / 24 (96 %) | 22 / 24 (92 %) | 23 / 24 (96 %) |
| c2 | 0 / 2 (0 %) | 1 / 2 (50 %) | 1 / 2 (50 %) | 1 / 2 (50 %) | 1 / 2 (50 %) | 1 / 2 (50 %) |
| d | 37 / 45 (82 %) | 24 / 45 (53 %) | 26 / 45 (58 %) | 30 / 45 (67 %) | 24 / 45 (53 %) | 34 / 45 (76 %) |

**Panel 2 — all diagnosed objects — materiality, area only (> 1 %)** (cells: survive / n)

| class | E1 | E1d | E2 | E2g | E3 | E4 |
|---|---|---|---|---|---|---|
| a | 32 / 75 (43 %) | 23 / 75 (31 %) | 11 / 75 (15 %) | 12 / 75 (16 %) | 15 / 75 (20 %) | 16 / 75 (21 %) |
| b | 60 / 109 (55 %) | 58 / 109 (53 %) | 44 / 109 (40 %) | 40 / 109 (37 %) | 69 / 109 (63 %) | 43 / 109 (39 %) |
| c1 | 23 / 24 (96 %) | 21 / 24 (88 %) | 22 / 24 (92 %) | 22 / 24 (92 %) | 21 / 24 (88 %) | 21 / 24 (88 %) |
| c2 | 0 / 2 (0 %) | 0 / 2 (0 %) | 1 / 2 (50 %) | 1 / 2 (50 %) | 1 / 2 (50 %) | 1 / 2 (50 %) |
| d | 32 / 45 (71 %) | 18 / 45 (40 %) | 24 / 45 (53 %) | 30 / 45 (67 %) | 11 / 45 (24 %) | 31 / 45 (69 %) |

Reconciliation with reports/phase4.md (reports/phase4.md §2 tables and §11 'Map shape'): the §2 map counts area gain above t_D only (mode 'area_only'): B0 layer at E4 {'a': '6 % (33)', 'b': '49 % (84)', 'c1': '100 % (19)', 'd': '94 % (32)'}, all objects {'a': '16 % (75) in §2; 15 % in §11', 'b': '43 % (109)', 'c1': '88 % (24)', 'd': '73 % (45)'}, materiality (area > 1 %) {'a': '21 % (75)', 'b': '39 % (109)', 'c1': '88 % (24)', 'd': '69 % (45)'} — reproduced above; the 'retained or trade-off' survival counts any metric above the band and is therefore higher where WNS or power carries the gain. §11's '15 %' for class (a) is 12 / 75 = 16.0 % in §2 and in the data (11 retained + 4 trade-off labels; 12 objects above t_area).
Objects whose stored class_final differs from the class in phase4_exp1.json: none.

## C. O1 — absorption attribution over the 74 absorbed objects

n = 74 ({'absorbed_identical': 59, 'absorbed': 15}). Exclusive categories: plain compile (converged with C@E1 under E1) 28 — of these 14 are also reproduced by a single flag alone ({'designware': 14, 'gate_clock': 4, 'retime': 4}); single capability without plain-compile convergence 0; only compile_ultra as a whole (no single option reproduces) 46. Single-flag counts in any order {'designware': 14, 'gate_clock': 4, 'retime': 4}. By class: {'a': {'plain': 15, 'ultra': 32}, 'b': {'plain': 12, 'ultra': 12}, 'c1': {}, 'c2': {}, 'd': {'ultra': 2, 'plain': 1}}. phase4.md: 28 plain compile, 14 single flag (designware 14, gate_clock 4, retime 4, some by several), 32 full-effort only (reports/phase4.md §9 / §11). Reconciliation: in the data every object reproduced by a single flag is also converged under a plain compile (the 14 are a subset of the 28), so the exclusive split is 28 plain compile / 0 single-flag-only / 46 compile_ultra only; phase4.md's 32 assumed the 14 outside the 28 (28 + 14 + 32 = 74) and is a double count.
Permanence: 45 of 255 objects (17.6 %) violate it — an object inside the band at a lower rung and above it at a higher one (area gain against the rung's t_D), over objects with a record at every rung E1–E4; patterns (E1 E2 E3 E4, R = above the band) {'-RRR': 14, 'R--R': 16, 'RR-R': 14, '-RR-': 1}.
Class (a): 47 objects collapse to D's E4 netlist (40) or converge (7); denominator 75 class-(a) objects with an E4 record, 75 with a record at every rung (47 of 75 = class-(a) objects with an E4 record; a denominator of 73 counts only those with a record at every rung E1–E4 (the map's non-monotone denominator)); the class-(a) objects without a record at some rung: [].

## D. O2 — object details

**rtlopt_ticket_machine** — best object c634baa4b8fa859 (class b, E4 label retained)

| level | area gain | WNS gain (periods) | power gain | band (area / WNS / power; source) | verdict |
|---|---|---|---|---|---|
| E1 | 58.87 % | 24.38 % | 73.84 % | 0.45 % / 0.52 % / 1.28 %; rule A | retained |
| E1d | 58.87 % | 24.38 % | 51.29 % | 1.00 % / 1.00 % / 2.00 %; materiality | retained |
| E2 | 58.45 % | 30.95 % | 33.95 % | 0.10 % / 0.02 % / 1.12 %; rule A | retained |
| E2g | 58.45 % | 30.95 % | 50.12 % | 1.00 % / 1.00 % / 2.00 %; materiality | retained |
| E3 | 58.45 % | 30.95 % | 33.95 % | 0.19 % / 0.03 % / 1.12 %; rule A | retained |
| E4 | 58.45 % | 30.95 % | 33.95 % | 0.28 % / 0.03 % / 2.22 %; rule A | retained |

**rtlopt_fsm_encode** — best object c92a0b6177cf6f6 (class b, E4 label retained)

| level | area gain | WNS gain (periods) | power gain | band (area / WNS / power; source) | verdict |
|---|---|---|---|---|---|
| E1 | 44.13 % | 22.03 % | 39.24 % | 0.86 % / 0.52 % / 8.96 %; rule A | retained |
| E1d | 44.13 % | 22.03 % | 43.96 % | 1.00 % / 1.00 % / 2.00 %; materiality | retained |
| E2 | 43.45 % | 47.86 % | 47.36 % | 0.16 % / 4.35 % / 1.32 %; rule A | retained |
| E2g | 46.42 % | 47.93 % | 53.96 % | 1.00 % / 1.00 % / 2.00 %; materiality | retained |
| E3 | 43.45 % | 47.86 % | 47.36 % | 0.19 % / 4.35 % / 1.32 %; rule A | retained |
| E4 | 46.42 % | 47.93 % | 58.92 % | 0.28 % / 0.03 % / 2.22 %; rule A | retained |

**drrtl_i2c** — best object c677509c91318c2 (class c1, E4 label retained)

| level | area gain | WNS gain (periods) | power gain | band (area / WNS / power; source) | verdict |
|---|---|---|---|---|---|
| E1 | 4.21 % | -2.59 % | 10.62 % | 1.85 % / 6.74 % / 1.28 %; rule A | retained |
| E1d | 5.11 % | -3.08 % | 10.63 % | 1.00 % / 1.00 % / 2.00 %; materiality | tradeoff |
| E2 | 4.55 % | -4.33 % | 9.76 % | 0.10 % / 0.02 % / 1.00 %; rule A | tradeoff |
| E2g | 7.42 % | 0.13 % | 9.57 % | 1.00 % / 1.00 % / 2.00 %; materiality | retained |
| E3 | 27.63 % | 5.07 % | 35.92 % | 0.19 % / 0.03 % / 1.12 %; rule A | retained |
| E4 | 7.83 % | 0.29 % | 10.51 % | 0.28 % / 0.03 % / 2.22 %; rule A | retained |

RTLLM class (d): 152 of 230 class-(d) candidates are absorbed_identical, all on rtllm_adder_16bit (hand-written adders identical to DC's inferred adder); by design {'rtllm_adder_16bit': {'absorbed_identical': 152, 'tradeoff': 29}, 'rtllm_multi_pipe_8bit': {'retained': 41, 'harmful': 1, 'tradeoff': 7}}. Source: reports/data/phase4_exp1.json contrast_phase3.d_by_design (run-time M3 verdicts of the Phase 3 calibration candidates; reports/phase4.md §8).

## E. O3 — static rule R and the predictor

phase4_exp1.json: P(retained | forbidden a/b) = 37.0 % (n 184), P(absorbed | allowed c1/c2/d) = 5.6 % (n 71).
Recomputed on the JSON classes: 37.0 % (n 184) / 5.6 % (n 71); on candidates.class_final as stored now: 37.0 % (n 184) / 5.6 % (n 71). phase4.md §11 quotes P(retained | forbidden) 37 % (n 183), P(absorbed | allowed) 6 % (n 72) — reports/phase4.md §11.
Predictor (leave-one-design-out): with the class features AUROC 0.710, class-blind 0.733 (n 255, 129 retained; precision at 85 % recall 54 % / 55 %). reports/data/phase4_exp1.json (the file the map is built from) holds AUROC 0.7103 with the class features and 0.7334 without; §6 of phase4.md quotes 0.710 / 0.733 from it; the 0.717 of §11 is not in the data file — the version consistent with the map is 0.733 / 0.710.

## F. O5 — RTL-OPT and RTLRewriter

Authors' released RTL-OPT reports: 40 of 40 pairs have the reference smaller than the start (0 same, 0 larger); over the proven 34 pairs: 34 of 34; the paper's claim: 35 of 36 better (RTL-OPT Table 1, compile_ultra 1 ns).
Baseline (start) areas, released over ours: against our E2_1ns D area min 0.86×, median 1.66×, max 3.47× (n 34; extremes [('rtlopt_calculation', 0.86), ('rtlopt_register', 1.09), ('rtlopt_decoder_8bit', 3.47), ('rtlopt_add_sub', 3.12)]); against our E1_authors D area (their settings on this DC) min 0.85×, median 1.05×, max 3.01× (n 34).
E1_authors column: {'better': 25, 'missing': 1, 'same': 1, 'worse': 7}; E2_1ns: {'better': 13, 'missing': 1, 'same': 4, 'worse': 16}; rtlopt_mux_dead's reference does not link under DC (LINK-3): the 'missing 1' of every setting; the released reports carry it (their DC T-2022.03 links it).
RTLRewriter: 54 pairs, 43 proven, better at E1 24 → better at E4 10, retained at E4 **10** (evaluated 42). memory_sharing: rtlrewriter_memory__memory_sharing (reference, proven, E4 label noise): E1 area 40.63 %, E4 area -0.15 %.

## G. Phase 5 additions (E4 verdicts, rule A; no rung attribution; duplicates collapsed)

Evaluated proven candidates 11312 (duplicates collapsed 2617; proven with E4 pending 175; DC-rejected terminal 44).

**large** — class × verdict

| class | n | retained | tradeoff | absorbed_identical | absorbed | noise | harmful | survival (ret.+trade-off) | retained only | material any (area / power / WNS) |
|---|---|---|---|---|---|---|---|---|---|---|
| a | 463 | 0 | 0 | 144 | 37 | 96 | 186 | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) (0 / 0 / 0) |
| b | 663 | 304 | 137 | 25 | 10 | 108 | 79 | 441 (66.5 %) | 304 (45.9 %) | 247 (37.3 %) (148 / 247 / 0) |
| c1 | 47 | 12 | 22 | 0 | 0 | 4 | 9 | 34 (72.3 %) | 12 (25.5 %) | 6 (12.8 %) (3 / 6 / 0) |
| d | 248 | 110 | 42 | 0 | 0 | 35 | 61 | 152 (61.3 %) | 110 (44.4 %) | 37 (14.9 %) (30 / 37 / 0) |

**medium** — class × verdict

| class | n | retained | tradeoff | absorbed_identical | absorbed | noise | harmful | survival (ret.+trade-off) | retained only | material any (area / power / WNS) |
|---|---|---|---|---|---|---|---|---|---|---|
| a | 2207 | 422 | 643 | 889 | 36 | 12 | 205 | 1065 (48.3 %) | 422 (19.1 %) | 393 (17.8 %) (346 / 384 / 18) |
| b | 3569 | 1269 | 1036 | 706 | 141 | 8 | 409 | 2305 (64.6 %) | 1269 (35.6 %) | 982 (27.5 %) (670 / 732 / 812) |
| c1 | 1604 | 593 | 567 | 14 | 5 | 185 | 240 | 1160 (72.3 %) | 593 (37.0 %) | 563 (35.1 %) (201 / 507 / 325) |
| c2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 (100.0 %) | 1 (100.0 %) | 1 (100.0 %) (0 / 1 / 0) |
| d | 2392 | 1059 | 1053 | 103 | 19 | 5 | 153 | 2112 (88.3 %) | 1059 (44.3 %) | 1024 (42.8 %) (536 / 1003 / 268) |

**small** — class × verdict

| class | n | retained | tradeoff | absorbed_identical | absorbed | noise | harmful | survival (ret.+trade-off) | retained only | material any (area / power / WNS) |
|---|---|---|---|---|---|---|---|---|---|---|
| a | 21 | 1 | 17 | 1 | 0 | 0 | 2 | 18 (85.7 %) | 1 (4.8 %) | 1 (4.8 %) (1 / 1 / 0) |
| b | 82 | 6 | 20 | 48 | 0 | 0 | 8 | 26 (31.7 %) | 6 (7.3 %) | 6 (7.3 %) (6 / 6 / 1) |
| d | 15 | 0 | 2 | 0 | 0 | 0 | 13 | 2 (13.3 %) | 0 (0.0 %) | 0 (0.0 %) (0 / 0 / 0) |

**pooled** — class × verdict

| class | n | retained | tradeoff | absorbed_identical | absorbed | noise | harmful | survival (ret.+trade-off) | retained only | material any (area / power / WNS) |
|---|---|---|---|---|---|---|---|---|---|---|
| a | 2691 | 423 | 660 | 1034 | 73 | 108 | 393 | 1083 (40.2 %) | 423 (15.7 %) | 394 (14.6 %) (347 / 385 / 18) |
| b | 4314 | 1579 | 1193 | 779 | 151 | 116 | 496 | 2772 (64.3 %) | 1579 (36.6 %) | 1235 (28.6 %) (824 / 985 / 813) |
| c1 | 1651 | 605 | 589 | 14 | 5 | 189 | 249 | 1194 (72.3 %) | 605 (36.6 %) | 569 (34.5 %) (204 / 513 / 325) |
| c2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 (100.0 %) | 1 (100.0 %) | 1 (100.0 %) (0 / 1 / 0) |
| d | 2655 | 1169 | 1097 | 103 | 19 | 40 | 227 | 2266 (85.3 %) | 1169 (44.0 %) | 1061 (40.0 %) (566 / 1040 / 268) |

| family | designs | proven (E4 in) | retained | retained rate | material |
|---|---|---|---|---|---|
| Dr.RTL | 6 | 2349 | 155 | 6.6 % | 78 |
| CktEvo | 8 | 4506 | 1495 | 33.2 % | 1111 |
| RTL-OPT | 8 | 4457 | 2127 | 47.7 % | 2071 |

Share of medium-tier retained candidates on RTL-OPT designs: 2120 of 3344 (63.4 %).

B0 (n proven 1987): Yosys label × rule-A E4 label {'improved|absorbed': 34, 'improved|absorbed_identical': 143, 'improved|dc_rejected': 20, 'improved|e4_pending': 105, 'improved|harmful': 183, 'improved|noise': 36, 'improved|retained': 645, 'improved|tradeoff': 449, 'no_gain|absorbed': 17, 'no_gain|absorbed_identical': 112, 'no_gain|dc_rejected': 2, 'no_gain|e4_pending': 41, 'no_gain|harmful': 57, 'no_gain|noise': 10, 'no_gain|retained': 39, 'no_gain|tradeoff': 84, 'none|retained': 3, 'none|tradeoff': 7}; per metric {'area: Y improved -> E4 not above t_D': 565, 'delay: Y improved -> E4 pending': 90, 'delay: Y improved -> E4 retained on that metric': 530, 'delay: Y improved -> E4 not above t_D': 313, 'area: Y improved -> E4 retained on that metric': 617, 'area: Y improved -> E4 pending': 75, 'no_y_record': 10}.

| design | per-metric outcomes (Y improved → E4) |
|---|---|
| drrtl_router | {'delay: Y improved -> E4 not above t_D': 89, 'area: Y improved -> E4 not above t_D': 13, 'delay: Y improved -> E4 retained on that metric': 3} |
| drrtl_UART | {'area: Y improved -> E4 not above t_D': 35, 'delay: Y improved -> E4 retained on that metric': 2, 'delay: Y improved -> E4 not above t_D': 2, 'area: Y improved -> E4 retained on that metric': 1} |
| drrtl_communication | {'area: Y improved -> E4 not above t_D': 46, 'delay: Y improved -> E4 not above t_D': 20, 'delay: Y improved -> E4 retained on that metric': 4, 'delay: Y improved -> E4 pending': 1} |
| cktevo_risc__cpu | no B0 candidate with a Y record |
| rtlopt_calculation | {'area: Y improved -> E4 retained on that metric': 134, 'delay: Y improved -> E4 retained on that metric': 25, 'delay: Y improved -> E4 not above t_D': 16, 'area: Y improved -> E4 pending': 2, 'area: Y improved -> E4 not above t_D': 3} |

Large tier, class (a): 0 of 463 retained; harmful 186 (40.2 %); labels {'absorbed_identical': 144, 'harmful': 186, 'noise': 96, 'absorbed': 37}. Large-tier WNS-material retained candidates per arm: {'B0': {'retained': 43, 'wns_material': 0}, 'B1_E4': {'retained': 121, 'wns_material': 0}, 'B2': {'retained': 96, 'wns_material': 0}, 'DrRTL_reimpl': {'retained': 44, 'wns_material': 0}, 'M': {'retained': 122, 'wns_material': 0}}.

## H. Caveat numbers

Designs on the pooled floor: 13 of 30 — retained / evaluated per design {'cktevo_risc__stall_control_unit': {'retained': 0, 'evaluated': 0}, 'cktevo_risc__cpu': {'retained': 0, 'evaluated': 89}, 'cktevo_usb__usbf_sie_rx': {'retained': 461, 'evaluated': 761}, 'drrtl_router': {'retained': 11, 'evaluated': 665}, 'cktevo_vga_enh__vga_wb_slave': {'retained': 298, 'evaluated': 687}, 'drrtl_arm_cpu2': {'retained': 0, 'evaluated': 0}, 'cktevo_nn_engine__thresholds_128x4096': {'retained': 1, 'evaluated': 522}, 'drrtl_simple_spi': {'retained': 0, 'evaluated': 87}, 'cktevo_hsm__hsm': {'retained': 0, 'evaluated': 0}, 'drrtl_aes': {'retained': 75, 'evaluated': 414}, 'drrtl_tv80': {'retained': 0, 'evaluated': 0}, 'cktevo_risc__btb': {'retained': 351, 'evaluated': 702}, 'drrtl_LSTM': {'retained': 0, 'evaluated': 0}}.
Offset designs: {'cktevo_mem_ctrl__mc_adr_sel': {'retained': 335, 'evaluated': 728}}.
ICG insertion: 88 of 2924 retained candidates with a material power gain carry more clock-gating cells than D (3.0 %); by design {'cktevo_risc__btb': 1, 'cktevo_mem_ctrl__mc_adr_sel': 40, 'rtlopt_register': 47}. request (b) item 5 is not in this session's record; computed here as retained candidates with a power gain above 2 % whose E4 netlist carries more clock-gating cells than D's E4 netlist.
Proof coverage: {'drrtl_SPI': {'with_verdict': 969, 'proven': 130, 'inconclusive': 778, 'evaluated': 130, 'retained': 58}, 'drrtl_simple_spi': {'with_verdict': 858, 'proven': 141, 'inconclusive': 536, 'evaluated': 87, 'retained': 0}, 'drrtl_tv80': {'with_verdict': 824, 'proven': 0, 'inconclusive': 669, 'evaluated': 0, 'retained': 0}, 'cktevo_hsm__hsm': {'with_verdict': 1054, 'proven': 0, 'inconclusive': 273, 'evaluated': 0, 'retained': 0}}.

## S. Sources

- A frozen floor table: `SELECT design_id, floor_source, floor_class, t_d, pooled_min FROM noise_floor WHERE floor_version='phase4' AND config='E4' AND metric='area' (one row per design; the table the Phase 5 experiments use)`
- A pooled minima: `SELECT metric, MAX(pooled_min) FROM noise_floor WHERE floor_version='phase4' AND config='E4' GROUP BY metric (the same value on every design row of the configuration and metric)`
- A perturbation records: `SELECT e.design_id, e.config, e.pert_id, p.ptype, e.area_um2, e.cells, e.wns_ns, e.power_saif_mw, e.clock_ns FROM evaluations e JOIN perturbations p ON p.pert_id=e.pert_id WHERE e.status='ok' AND e.config IN ('E1','E2','E3','E4') AND e.design_id IN (frozen-table designs); baseline = is_baseline=1, pert_id IS NULL, cand_id IS NULL, same config and clock`
- A floor-basis records: `src.noise.stats.proven_by_design + pick_records(conn, design, config, proven, phi_main, eps) for every frozen-table design: the baseline and the latest E4 record of each SEQ-proven perturbation at Φ_main (the records the floor rows were computed from); pooled quantiles by stats.pooled_quantile (design-weighted: every design's records weighted 1 / n_design; record-weighted for comparison)`
- A pooled-minimum basis: `scripts/phase2_noise.py cmd_collect: S.pooled_minimum over the set designs (designs.split IN ('dev','held')), SEQ-proven perturbations at Φ_main, quantile noise.pooled_quantile = 0.90, weighting noise.pooled_weighting = design; the frozen table then applies the minima to every design without a measured floor`
- B Fig. 3 matrices: `reports/data/phase4_exp1.json objects[] (proven, label not duplicate, E4 gains present; n = 255) with per-level thresholds from src.analysis.objects.thresholds(conn, design, level, 'phase4'); survival modes: rule_a_any (some metric above t, the label retained or trade-off), area_only (the §2 map cell: area gain above t_area), mat_area (area gain > 1 %), mat_any (some metric above materiality)`
- C absorption attribution: `reports/data/phase4_diagnoser_sample.json reproduction.rows (74 absorbed objects: D compiled with one flag alone — E1d designware, E2g gate_clock, E3 retime — or with a plain compile E1, against the object's plain-compile netlist C@E1; spec 04 §B.5) and phase4_exp1.json objects (label, rung, class); permanence = src.analysis.map.non_monotone over E1–E4 (reports/phase4.md §3)`
- D best objects: `reports/data/phase4_exp1.json objects (role b0, label retained or trade-off; the object with the largest E4 area gain of the design), gains per level; per-level rule-A verdict from the gains and the level's thresholds (retained: some metric above t and none below; trade-off: some above and some below; noise: all within; harmful: some below, none above); E1d / E2g carry no measured floor: verdict under the materiality thresholds there`
- E static rule and predictor: `src.analysis.map.misclassification_rates on the 255 objects — rule R forbids classes a / b and allows c1 / c2 / d; retained = label retained or trade-off; absorbed = absorbed, absorbed_identical, noise or duplicate — on (i) the class of phase4_exp1.json (the map's class_final at generation) and (ii) candidates.class_final as stored now; predictor AUROC from phase4_exp1.json predictor (leave-one-design-out logistic model, n = 255, 129 retained)`
- F RTL-OPT released reports: `data/sources/RTL-OPT/Results/RTL-OPT_DC/<pair>/report/area.rpt and <pair>_ref/report/area.rpt, 'Total cell area' (the authors' released DC runs: plain compile at 0.1 ns, their Nangate45 typical.db); reports/data/phase4_rtlopt_setting.json rows (authors_released, E1_authors, E2_1ns per proven pair); reports/data/phase4_exp1.json literature`
- G Phase 5 scan: `scripts/report_c1.scan_phase5 (every non-superseded Phase 5 candidate; rule A at E4 via src.analysis.phase5.uniform_diagnosis; duplicates collapsed: label duplicate never counted); evaluated = proven with an E4 record`
- G B0 Yosys vs E4: `candidates.label of the B0 arm (improved = any positive Y-caliber component); per metric: the candidate's Y record (evaluations config Y, same clock as the design's Y baseline) against the Y baseline — area gain (base − cand) / base, delay gain (cand WNS − base WNS) / clock — crossed with the rule-A E4 gains of the same candidate against the design's frozen t_D per metric`
- H caveats: `noise_floor (frozen phase4, E4 area row: floor_source / floor_class per design) joined with the Phase 5 scan; ICG insertion: log_summary_json.icg_count of the candidate's E4 record against the design's E4 baseline record; proof coverage: candidates with a verdict per design`
