# Section III — four remaining items (2026-09-20; visible layer only)

Generated 2026-09-20T04:56 by scripts/report_paper_sec3_addendum.py (git 953c31178e38); data reports/data/paper_sec3_addendum.json; sources in §S. Mechanism lines are the operator's reading of the comment-stripped, module-by-module diff and are marked as such.

## 1. mc_rf — the largest single effect

Baseline D at Φ_main = 0.7 ns (eval 3770): area 2373.518 µm², 937 cells, SAIF power 0.1618 mW. 28 proven-perturbation E4 records at Φ_main; the largest area effect is +18.66 %, shared by 15 records ({'P4_ctrl': 3, 'P3_expr': 8, 'P2_reorder': 1, 'P1_rename': 2, 'P0_roundtrip': 1}). Floor row: class offset, t_D area 18.66 % (its own max |δ|, n 28).

| pert_id | type | SEQ | clock ns | area µm² | cells | SAIF power mW | area δ | power δ |
|---|---|---|---|---|---|---|---|---|
| p150d8065883457 | P4_ctrl | proven | 0.7 | 2816.408 | 1039 | 0.26861 | 18.66 % | 66.0 % |
| p3e4134c3fc3001 | P3_expr | proven | 0.7 | 2816.408 | 1039 | 0.26574 | 18.66 % | 64.2 % |
| p5be15c6505f4e5 | P3_expr | proven | 0.7 | 2816.408 | 1039 | 0.26861 | 18.66 % | 66.0 % |
| p658a6b2fa7acc3 | P2_reorder | proven | 0.7 | 2816.408 | 1038 | 0.26335 | 18.66 % | 62.8 % |
| p66e2167baae5eb | P1_rename | proven | 0.7 | 2816.408 | 1039 | 0.26861 | 18.66 % | 66.0 % |
| p6ffdd40a17779b | P3_expr | proven | 0.7 | 2816.408 | 1039 | 0.26861 | 18.66 % | 66.0 % |

The largest P0 record: pd184c3280bdc44 (proven, 0.7 ns): area 2816.408 (18.66 %), power 0.26574 mW (64.2 %).
Statement for the paper: the +18.7 % area effect is not a P3_expr effect: at Φ_main every proven perturbation of mc_rf that changes the netlist lands on the same E4 result (2 816.408 µm², 1 039 cells) — the re-print P0 among them — so the design is an offset design (floor class offset, t_D = its own max |δ|); the frozen-table attribution to P3_expr in the Section III data is a tie-break among identical values. The paper should name the re-print P0 (with every other proven perturbation alike): +18.7 % area, +64.2 % SAIF power; the P2 reorders split between the same +18.7 % and a second plateau at +17.4 % area / +19 % power.

All records (area-descending): P4_ctrl 18.66 % / 66.0 %; P3_expr 18.66 % / 64.2 %; P3_expr 18.66 % / 66.0 %; P2_reorder 18.66 % / 62.8 %; P1_rename 18.66 % / 66.0 %; P3_expr 18.66 % / 66.0 %; P4_ctrl 18.66 % / 66.0 %; P3_expr 18.66 % / 64.2 %; P3_expr 18.66 % / 64.2 %; P3_expr 18.66 % / 66.0 %; P3_expr 18.66 % / 64.2 %; P0_roundtrip 18.66 % / 64.2 %; P1_rename 18.66 % / 64.2 %; P3_expr 18.66 % / 66.0 %; P4_ctrl 18.66 % / 66.0 %; P1_rename 18.65 % / 21.7 %; P1_rename 18.65 % / 21.7 %; P1_rename 18.65 % / 22.4 %; P1_rename 18.65 % / 21.7 %; P1_rename 18.65 % / 22.4 %; P1_rename 18.65 % / 22.4 %; P2_reorder 18.65 % / 22.0 %; P2_reorder 18.63 % / 66.5 %; P2_reorder 18.50 % / 65.0 %; P2_reorder 18.24 % / 63.6 %; P2_reorder 17.37 % / 19.0 %; P2_reorder 17.37 % / 19.2 %; P2_reorder 17.37 % / 18.8 %.

## 2. ticket_machine and fsm_encode best objects

**rtlopt_ticket_machine — c634baa4b8fa859** (class rule / LLM / final: b / None / b; E4 label retained)

- rules-v2 evidence tags: ['flip-flop bits 6 -> 3 in the same register cells (widths), latency unchanged', 'text differs widely (ratio 0.688) without operator or topology evidence -> review']
- flip-flop count (DC E4 registers) D → C: 6.0 → 3.0; cells 35 → 14; area 58.254 → 24.206 µm² (58.4 % gain)
- module diff (comment-stripped): {'ticket_machine': {'status': 'changed', 'changed_lines': 110, 'd_lines': 111, 'c_lines': 25}}
- reading of the diff (operator): D encodes the six-state Moore FSM one-hot (localparam RDY … BILL30 = 6'b000001 … 6'b100000; reg [5:0] State, NextState) with case-based output and next-state blocks; the candidate keeps the same two state registers but 3 bits wide (reg [2:0] State, NextState; RDY = 3'b000 …), computes the four outputs as boolean functions of the three state bits and collapses the next-state case into the same transitions on the binary codes. A state re-encoding (one-hot → binary) that changes the flip-flop count (6 → 3 bits) inside the same register cells.

**rtlopt_fsm_encode — c92a0b6177cf6f6** (class rule / LLM / final: b / None / b; E4 label retained)

- rules-v2 evidence tags: ['flip-flop bits 33 -> 28 in the same register cells (widths), latency unchanged']
- flip-flop count (DC E4 registers) D → C: 33.0 → 27.0; cells 144 → 60; area 319.200 → 171.038 µm² (46.4 % gain)
- module diff (comment-stripped): {'fsm_encode': {'status': 'changed', 'changed_lines': 78, 'd_lines': 74, 'c_lines': 36}}
- reading of the diff (operator): D drives an 8-bit one-hot sequencer (localparam IDLE … STORE2 = 8'b00000001 … 8'b10000000; reg [7:0] current_state, next_state) through a next-state case and a datapath case over the same states; the candidate replaces the one-hot state with a 3-bit phase counter (reg [2:0] phase; phase <= phase + 1 once started, 000 = idle) and dispatches the same LOAD1 / LOAD2 / ADD / SUB / SHIFT / STORE1 / STORE2 datapath actions on the counter value (reg1, reg2, out_reg, done unchanged). A state re-encoding (one-hot → binary counter): flip-flop bits 33 → 28 at the RTL (rules v2), 33 → 27 in DC's E4 netlist, the register cells unchanged.

Class: Rules v2 (src/classify/rules.py; docs/spec/04 §A; reports/phase3.md §6a) file a latency-preserving refactor as (b) when the register cells are unchanged — a width change inside the same cells carries the evidence tag 'flip-flop bits N -> M in the same register cells (widths)' — and as (c1) only when the number of register cells changes ('… and register cells N -> M'). Both objects change the flip-flop bit count (6 → 3; 33 → 28) but keep every register cell, so the map classes them (b). The paper's sentence should read: a one-hot-to-binary re-encoding that halves the state bits inside the same state register (class (b) under rules v2; it changes the flip-flop count, not the register-cell count); it must not call them class (c1).

## 3. Largest retained power gains on btb, eth_cop and usbf_sie_rx

Power basis: m3.power_basis compares SAIF with SAIF and default with default, never mixed (2026-09-15). D's E4 baseline at Φ_main carries no SAIF power on 13 of the 30 Phase 5 designs — the same 13 designs that have no measured floor: their design SAIF was never built because the SAIF pipeline (scripts/phase2_saif.py) runs on the perturbation records, which these designs do not have — so every power gain on those designs (btb's ≈ 80 % included) is a default-activity figure, while the candidates on them mostly carry SAIF power (btb 800 of 890 E4 records) that has no D counterpart. Candidate fix (Phase 6 item 6.10, not run): build D's SAIF from the V2 lock-step stimulus of any proven candidate and re-run D's E4 once per design; then the SAIF basis applies retroactively to every candidate record that has one.

Designs whose E4 baseline at Φ_main has no SAIF power (power basis default for every candidate): ['cktevo_risc__stall_control_unit', 'cktevo_hsm__MixColumns', 'cktevo_risc__cpu', 'cktevo_usb__usbf_sie_rx', 'cktevo_vga_enh__vga_wb_slave', 'drrtl_arm_cpu2', 'cktevo_nn_engine__thresholds_128x4096', 'drrtl_simple_spi', 'cktevo_hsm__hsm', 'drrtl_aes', 'drrtl_tv80', 'cktevo_risc__btb', 'drrtl_LSTM'].

**cktevo_risc__btb** — 351 retained candidates with a power gain; the largest:

| candidate | arm | class | gains area / WNS / power | basis | D: SAIF / default mW, ICG, regs, cells | C: SAIF / default mW, ICG, regs, cells | evidence tags | modules changed |
|---|---|---|---|---|---|---|---|---|
| ca9609319386672 | B0 | b | -0.07 % / 0.01 % / 82.8 % | default | None / 5.4759, 76, 2008.0, 4400 | 0.5894897459999999 / 0.9441, 76, 2008.0, 4502 | ['register names or clocked targets changed, flip-flop count and latency unchanged'] | btb_array changed (53 lines), btb unchanged |
| c7d0245fa7e5632 | B0 | b | -0.07 % / 0.01 % / 82.8 % | default | None / 5.4759, 76, 2008.0, 4400 | 0.5894897459999999 / 0.9441, 76, 2008.0, 4502 | ['register names or clocked targets changed, flip-flop count and latency unchanged'] | btb_array changed (69 lines), btb unchanged |
| cbfa2b4ffaa3e0e | B0 | b | 0.25 % / 0.03 % / 81.6 % | default | None / 5.4759, 76, 2008.0, 4400 | None / 1.0096, 76, 2008.0, 4394 | ['register names or clocked targets changed, flip-flop count and latency unchanged'] | btb_array changed (54 lines), btb unchanged |

Toggle rate under the V2 stimulus: not stored (E4 records keep power_default.rpt only; the SAIF of the lock-step simulation is slimmed after E4).
Mechanism (operator's reading of the diff): the top module btb is untouched; the rewrite is inside btb_array: the indexed array write (data[windex] <= in) becomes an explicit 8-way case per generate branch (a VALID_ARRAY branch with reset, a NONVALID_ARRAY branch without), i.e. a write-decoder re-expression with the same storage — no clock gating added (76 ICGs on both sides), cells 4 400 → 4 502 (+2.3 %), area within the band. The power figure is on the default-activity basis (D has no SAIF power at E4): DC's default toggle assumptions on the re-expressed write path, not a stimulus-based saving.

**cktevo_ethmac__eth_cop** — 49 retained candidates with a power gain; the largest:

| candidate | arm | class | gains area / WNS / power | basis | D: SAIF / default mW, ICG, regs, cells | C: SAIF / default mW, ICG, regs, cells | evidence tags | modules changed |
|---|---|---|---|---|---|---|---|---|
| ce09ee4414fa2db | B1_E4 | c1 | 0.47 % / 0.32 % / 45.7 % | saif | 0.064912796 / 0.1339, 3, 186.0, 563 | 0.035249439 / 0.0958, 3, 176.0, 640 | ['flip-flop bits 174 -> 140 and register cells 13 -> 14 with identical latency (no offset)'] | eth_cop changed (138 lines) |

Toggle rate under the V2 stimulus: not stored (E4 records keep power_default.rpt only; the SAIF of the lock-step simulation is slimmed after E4).
Mechanism (operator's reading of the diff): the two in-progress flags and the two full 32-bit slave address registers (s1_wb_adr_o, s2_wb_adr_o) become a 2-bit transaction_owner plus 11- and 17-bit address-low registers with valid bits, the addresses rebuilt combinationally from the ETH_BASE / MEMORY_BASE constants; the arbitration case over five bits becomes grant / finish wires. Flip-flop bits 174 → 140 (register cells 13 → 14), the same 3 ICGs; SAIF basis on both sides: 0.0649 → 0.0352 mW under the V2 stimulus (−45.7 %) with the wide address registers no longer toggling.

**cktevo_usb__usbf_sie_rx** — 461 retained candidates with a power gain; the largest:

| candidate | arm | class | gains area / WNS / power | basis | D: SAIF / default mW, ICG, regs, cells | C: SAIF / default mW, ICG, regs, cells | evidence tags | modules changed |
|---|---|---|---|---|---|---|---|---|
| c6157554c2aec6a | M | c1 | 0.95 % / 1.17 % / 1.4 % | default | None / 1.2252, 7, 109.0, 287 | 0.131398666 / 1.2077, 7, 108.0, 283 | ['flip-flop bits 109 -> 108 and register cells 23 -> 22 with identical latency (no offset)'] | usbf_sie_rx changed (427 lines), usbf_crc16 unchanged |

Toggle rate under the V2 stimulus: not stored (E4 records keep power_default.rpt only; the SAIF of the lock-step simulation is slimmed after E4).
Mechanism (operator's reading of the diff): the RX state machine of usbf_sie_rx is rewritten (427 changed lines: the state constants and registers re-organised, usbf_crc16 unchanged); flip-flop bits 109 → 108 (register cells 23 → 22), 7 ICGs on both sides; the 1.4 % power gain is on the default-activity basis (D has no SAIF power at E4) and below the materiality threshold.

## 4. The 13 designs on the pooled floor

| design | tier | perturbations by type | SEQ status | P0 | P1_text run | evaluation records | reason no floor was measured |
|---|---|---|---|---|---|---|---|
| cktevo_risc__stall_control_unit | small | none | - | - | no | 0 | no perturbation generated: the Pyverilog front end fails on the design (parse: ParseError: Syntax Error); the text-level renamer (P1_text) is part of the same generator run and was not run either |
| cktevo_risc__cpu | medium | none | - | - | no | 0 | no perturbation generated: the Pyverilog front end fails on the design (parse: ParseError:  line:115: before: "["); the text-level renamer (P1_text) is part of the same generator run and was not run either |
| cktevo_usb__usbf_sie_rx | medium | {'P0_roundtrip': 1, 'P1_rename': 4, 'P1_text': 4, 'P2_reorder': 4, 'P3_expr': 4, 'P4_ctrl': 4} | {'proven': 4, 'rejected': 17} | ['rejected'] | yes | 0 | perturbations generated and 4 proven (text-level renames), but the re-print P0 is rejected: the floor pipeline requires the proven re-print, so no noise run was made (0 evaluation records) |
| drrtl_router | medium | {'P0_roundtrip': 1, 'P1_rename': 4, 'P1_text': 4, 'P2_reorder': 4, 'P3_expr': 4, 'P4_ctrl': 4} | {'falsified': 20, 'sim_fail': 1} | ['falsified'] | yes | 0 | perturbations generated (text-level renamer run: P1_text present) but none SEQ-proven — the re-print P0 is falsified; statuses {'falsified': 20, 'sim_fail': 1}; router: falsified under harness_version 1 (the formal step's z-reset defect corrected by harness_version 2 — a candidate for re-proof) |
| cktevo_vga_enh__vga_wb_slave | medium | {'P0_roundtrip': 1, 'P1_rename': 4, 'P1_text': 4, 'P2_reorder': 4, 'P3_expr': 4, 'P4_ctrl': 3} | {'error': 1, 'proven': 3, 'rejected': 16} | ['rejected'] | yes | 0 | perturbations generated and 3 proven (text-level renames), but the re-print P0 is rejected: the floor pipeline requires the proven re-print, so no noise run was made (0 evaluation records) |
| drrtl_arm_cpu2 | medium | {'P0_roundtrip': 1, 'P1_rename': 4, 'P1_text': 4, 'P2_reorder': 4, 'P3_expr': 4, 'P4_ctrl': 3} | {'inconclusive': 4, 'rejected': 16} | ['rejected'] | yes | 0 | perturbations generated (text-level renamer run: P1_text present) but none SEQ-proven — the re-print P0 is rejected; statuses {'inconclusive': 4, 'rejected': 16} |
| cktevo_nn_engine__thresholds_128x4096 | medium | none | - | - | no | 0 | no perturbation generated: the Pyverilog front end fails on the design (parse: ParseError:  line:143: before: "("); the text-level renamer (P1_text) is part of the same generator run and was not run either |
| drrtl_simple_spi | medium | none | - | - | no | 0 | no perturbation generated: the Pyverilog front end fails on the design (parse: ParseError: None: at end of input); the text-level renamer (P1_text) is part of the same generator run and was not run either |
| cktevo_hsm__hsm | large | none | - | - | no | 0 | no perturbation generated: the Pyverilog front end fails on the design (parse: ParseError:  line:2408: before: "input"); the text-level renamer (P1_text) is part of the same generator run and was not run either |
| drrtl_aes | large | none | - | - | no | 0 | no perturbation generated: the Pyverilog front end fails on the design (parse: ParseError:  line:18: before: "]"); the text-level renamer (P1_text) is part of the same generator run and was not run either |
| drrtl_tv80 | large | {'P0_roundtrip': 1, 'P1_rename': 4, 'P1_text': 4, 'P2_reorder': 4, 'P3_expr': 4, 'P4_ctrl': 2} | {'inconclusive': 4, 'rejected': 15} | ['rejected'] | yes | 0 | perturbations generated (text-level renamer run: P1_text present) but none SEQ-proven — the re-print P0 is rejected; statuses {'inconclusive': 4, 'rejected': 15} |
| cktevo_risc__btb | large | none | - | - | no | 0 | no perturbation generated: the Pyverilog front end fails on the design (parse: ParseError: Syntax Error); the text-level renamer (P1_text) is part of the same generator run and was not run either |
| drrtl_LSTM | large | {'P0_roundtrip': 1, 'P1_rename': 8, 'P1_text': 4, 'P2_reorder': 8, 'P3_expr': 8} | {'pending': 12, 'rejected': 17} | ['rejected'] | yes | 0 | perturbations generated (text-level renamer run: P1_text present) but none SEQ-proven — the re-print P0 is rejected; statuses {'pending': 12, 'rejected': 17}; LSTM: the catalog reset-port defect fixed 2026-09-18 (harness_version 2) |

Phase 6 candidate: PLAN 6.9 — measure floors for these 13 designs under harness_version 2 (8 text-level renames + 8 reorders each; the text-level renamer needs no Pyverilog parse; the re-print P0 re-proven under v2 where its failure was the harness), report Phase 5 retention under the measured floors as a sensitivity row; the Phase 5 floors stay frozen (floor_version phase4).

## S. Sources

- 1 mc_rf records: `SELECT e.pert_id, p.ptype, p.seq_status, e.clock_ns, e.area_um2, e.cells, e.power_saif_mw FROM evaluations e JOIN perturbations p ON p.pert_id=e.pert_id WHERE e.design_id='cktevo_mem_ctrl__mc_rf' AND e.config='E4' AND e.status='ok' AND abs(e.clock_ns-0.7)<1e-6; baseline eval 3770 (is_baseline=1, same clock, SAIF power present)`
- 2 best objects: `candidates (class_rule / class_llm / class_final, subtags_json = rules-v2 evidence tags, rtl_path); E4 records of D at Φ_main and of the candidate (log_summary_json.registers = DC's flip-flop count, cells, area); the diff is data/designs/<suite>/<design>/rtl/*.v against the candidate file, comments stripped, module by module`
- 3 power gains: `Phase 5 proven candidates of the design (duplicates excluded) with rule-A label retained (src.analysis.phase5.uniform_diagnosis; gains from src/diagnose/m3.relative_gains on the basis m3.power_basis picks: SAIF only when both D and C carry SAIF power, else DC's default switching activity); ICG count and DC register count from log_summary_json of the E4 records; E4 report directories keep power_default.rpt (no SAIF toggle summary is stored), so the total toggle rate under the V2 stimulus is not available for either side`
- 4 pooled-floor designs: `perturbations (ptype, seq_status per design), data/perturbations/<design>/manifest.json (generator error), evaluations (E4 records of perturbations), noise_floor (floor_source, floor_version phase4)`
