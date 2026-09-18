# Phase 5 report (Stage B — large and medium tiers)

Generated 2026-09-18T04:24 by scripts/report_phase.py phase5 --stage B (git b4a15b569fc7, cfg 2530153494cf). Data: reports/data/phase5_visible_B.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 18 / 18 / 18 | 1080 | 3.25 | 33.3 | 179.9 |
| large | gpt-5.6-terra | B0 | 18 / 18 / 18 | 1080 | 34.21 | 0.0 | 490.4 |
| large | gpt-5.6-terra | B1_E4 | 18 / 18 / 18 | 1080 | 38.15 | 57.2 | 470.6 |
| large | gpt-5.6-terra | B2 | 18 / 18 / 18 | 1080 | 37.62 | 55.8 | 482.2 |
| large | gpt-5.6-terra | DrRTL_reimpl | 18 / 18 / 18 | 1080 | 38.17 | 46.5 | 180.9 |
| large | gpt-5.6-terra | M | 18 / 18 / 18 | 1080 | 34.40 | 38.9 | 450.7 |
| medium | gpt-5.6-luna | B0 | 15 / 51 / 51 | 1013 | 2.00 | 0.0 | 86.4 |
| medium | gpt-5.6-luna | B1_E4 | 14 / 54 / 54 | 1063 | 2.34 | 37.6 | 82.2 |
| medium | gpt-5.6-luna | B2 | 7 / 54 / 54 | 903 | 2.09 | 37.4 | 48.5 |
| medium | gpt-5.6-luna | DrRTL_reimpl | 0 / 54 / 54 | 31 | 0.06 | 4.0 | 0.3 |
| medium | gpt-5.6-luna | M | 0 / 54 / 54 | 0 | 0.00 | 0.0 | 0.0 |
| medium | gpt-5.6-terra | B2 | 2 / 54 / 54 | 563 | 15.26 | 25.1 | 14.8 |
| medium | gpt-5.6-terra | M | 0 / 54 / 54 | 0 | 0.00 | 0.0 | 0.0 |

Unfinished groups: 7 of 13 — the numbers below are interim for those groups (runs still open, verdicts and fitness evaluations pending).

## 1. Arm comparison per tier (uniform caliber: equal LLM calls; every proven candidate re-labelled offline under rule A with the design's frozen E4 floor)

### large tier

| model (role) | arm | runs | candidates | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (contrast) | M | 18/18 | 1074 | 6 | 121 (0.112) | 130 | 0 | 29 | 44 | 2.44 | 4 | 0.24 % / 0.00 % | 4.07 | 13.52 | 1.32 | 3.25 | 33.3 | 179.9 |
| gpt-5.6-terra (main) | B0 | 18/18 | 1080 | 0 | 289 (0.268) | 344 | 0 | 79 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 34.21 | 0.0 | 490.4 |
| gpt-5.6-terra (main) | B1_E4 | 18/18 | 1080 | 0 | 327 (0.303) | 282 | 0 | 152 | 120 | 6.67 | 6 | 0.49 % / 0.00 % | 11.11 | 3.15 | 2.10 | 38.15 | 57.2 | 470.6 |
| gpt-5.6-terra (main) | B2 | 18/18 | 1080 | 0 | 318 (0.294) | 311 | 0 | 110 | 96 | 5.33 | 5 | 0.41 % / 0.00 % | 8.89 | 2.55 | 1.72 | 37.62 | 55.8 | 482.2 |
| gpt-5.6-terra (main) | DrRTL_reimpl | 18/18 | 920 | 3 | 341 (0.316) | 130 | 0 | 168 | 44 | 2.44 | 3 | 0.09 % / 0.00 % | 4.07 | 1.15 | 0.94 | 38.17 | 46.5 | 180.9 |
| gpt-5.6-terra (main) | M | 18/18 | 1079 | 1 | 144 (0.133) | 265 | 0 | 49 | 78 | 4.33 | 5 | 0.62 % / 0.00 % | 7.22 | 2.27 | 2.00 | 34.40 | 38.9 | 450.7 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | M | 229 | 68 | 116 | 130 | 0 | 0 | 78 | 332 | absorbed_identical: 19, harmful: 19, noise: 16, retained: 44, tradeoff: 22 | absorbed_identical: 19, harmful: 19, noise: 16, nonequiv: 543, retained: 44, tradeoff: 22 | 235 (no block-level answers) | 209 (26) | 4905 / 28714 |
| gpt-5.6-terra | B0 | 178 | 29 | 195 | 344 | 2 | 2 | 41 | 0 | - | improved: 247, no_gain: 42, nonequiv: 750 | 375 (no block-level answers) | 158 (18) | 6472 / 35488 |
| gpt-5.6-terra | B1_E4 | 198 | 34 | 194 | 282 | 1 | 0 | 44 | 0 | absorbed: 1, absorbed_identical: 40, harmful: 74, noise: 37, retained: 120, tradeoff: 46 | improved: 256, no_gain: 62, nonequiv: 709 | 383 (no block-level answers) | 168 (30) | 9049 / 32109 |
| gpt-5.6-terra | B2 | 218 | 25 | 193 | 311 | 0 | 0 | 15 | 0 | absorbed_identical: 50, harmful: 78, noise: 44, retained: 96, tradeoff: 38 | improved: 208, no_gain: 98, nonequiv: 747 | 387 (no block-level answers) | 204 (44) | 7302 / 29440 |
| gpt-5.6-terra | DrRTL_reimpl | 92 | 7 | 164 | 130 | 1 | 0 | 185 | 0 | absorbed: 37, absorbed_identical: 39, harmful: 106, noise: 86, retained: 44, tradeoff: 10 | improved: 224, no_gain: 98, nonequiv: 394 | 308 (no block-level answers) | 102 (8) | 8584 / 29215 |
| gpt-5.6-terra | M | 212 | 35 | 52 | 265 | 0 | 0 | 67 | 304 | absorbed_identical: 8, harmful: 13, noise: 11, retained: 78, tradeoff: 31 | absorbed_identical: 8, harmful: 13, noise: 11, nonequiv: 564, retained: 78, tradeoff: 31 | 135 (no block-level answers) | 145 (28) | 5408 / 37812 |

### medium tier

| model (role) | arm | runs | candidates | unusable | proven (rate / call) | inconclusive | latency-mapped (c2) | accepted (arm's own) | retained (rule A) | retained / run | runs with ≥ 1 retained | best area gain per run: mean / median | retained per 100 calls | retained per USD | retained per DC h | USD | DC h | VCF h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna (main) | B0 | 15/51 | 1013 | 0 | 497 (0.491) | 45 | 0 | 189 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 2.00 | 0.0 | 86.4 |
| gpt-5.6-luna (main) | B1_E4 | 14/54 | 1057 | 6 | 508 (0.478) | 51 | 0 | 220 | 191 | 3.54 | 10 | 2.59 % / 0.00 % | 17.97 | 81.73 | 5.08 | 2.34 | 37.6 | 82.2 |
| gpt-5.6-luna (main) | B2 | 7/54 | 901 | 9 | 451 (0.499) | 26 | 0 | 165 | 163 | 3.02 | 9 | 2.16 % / 0.00 % | 18.05 | 78.01 | 4.36 | 2.09 | 37.4 | 48.5 |
| gpt-5.6-luna (main) | DrRTL_reimpl | 0/54 | 27 | 0 | 19 (0.613) | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | 0.00 | 0.06 | 4.0 | 0.3 |
| gpt-5.6-luna (main) | M | 0/54 | 0 | 0 | 0 (-) | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | - | - | - | 0.00 | 0.0 | 0.0 |
| gpt-5.6-terra (second) | B2 | 2/54 | 587 | 6 | 241 (0.428) | 9 | 0 | 112 | 79 | 1.46 | 8 | 2.16 % / 0.00 % | 14.03 | 5.18 | 3.15 | 15.26 | 25.1 | 14.8 |
| gpt-5.6-terra (second) | M | 0/54 | 0 | 0 | 0 (-) | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | - | - | - | 0.00 | 0.0 | 0.0 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | B0 | 153 | 98 | 124 | 45 | 0 | 19 | 77 | 0 | - | improved: 409, no_gain: 82, nonequiv: 420 | 0 (0 / 102 = 0 %) | 220 (74) | 274 / 3522 |
| gpt-5.6-luna | B1_E4 | 172 | 114 | 152 | 51 | 0 | 21 | 39 | 0 | absorbed: 32, absorbed_identical: 63, harmful: 44, noise: 14, retained: 191, tradeoff: 164 | improved: 437, no_gain: 70, nonequiv: 489 | 6 (6 / 163 = 4 %) | 255 (83) | 455 / 3455 |
| gpt-5.6-luna | B2 | 127 | 77 | 146 | 26 | 0 | 56 | 18 | 0 | absorbed: 17, absorbed_identical: 47, harmful: 42, noise: 14, retained: 163, tradeoff: 167 | improved: 370, no_gain: 80, nonequiv: 376 | 3 (3 / 161 = 2 %) | 214 (79) | 412 / 3081 |
| gpt-5.6-luna | DrRTL_reimpl | 0 | 0 | 3 | 0 | 0 | 5 | 0 | 0 | absorbed: 5, absorbed_identical: 12, harmful: 2 | no_gain: 19, nonequiv: 3 | 0 (no block-level answers) | 2 (1) | 304 / 2102 |
| gpt-5.6-luna | M | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 0 (no block-level answers) | 0 (0) | - / - |
| gpt-5.6-terra | B2 | 92 | 41 | 109 | 9 | 0 | 86 | 9 | 0 | absorbed: 6, absorbed_identical: 11, harmful: 25, noise: 10, retained: 79, tradeoff: 110 | improved: 221, no_gain: 20, nonequiv: 251 | 4 (4 / 96 = 4 %) | 147 (38) | 282 / 2250 |
| gpt-5.6-terra | M | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 0 (no block-level answers) | 0 (0) | - / - |

## 2. Best retained area gain per design (max over seeds; uniform rule A; '-' = no retained candidate; 0 = runs without one)

### large tier

| design | B0 (terra) | B1_E4 (terra) | B2 (terra) | DrRTL_reimpl (terra) | M (luna) | M (terra) |
|---|---|---|---|---|---|---|
| cktevo_hsm__hsm | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_nn_engine__spikeNeuron8_H7 | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_risc__btb | 0 | 2.36 % | 2.16 % | 0.82 % | 1.76 % | 2.17 % |
| drrtl_LSTM | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_aes | 0 | 0.88 % | 0.76 % | 0.61 % | 0.88 % | 4.67 % |
| drrtl_tv80 | 0 | 0 | 0 | 0 | 0 | 0 |

### medium tier

| design | B0 (luna) | B1_E4 (luna) | B2 (luna) | B2 (terra) | DrRTL_reimpl (luna) | M (luna) | M (terra) |
|---|---|---|---|---|---|---|---|
| cktevo_ethmac__eth_cop | 0 | 5.76 % | 0 | 0 | 0 | 0 | 0 |
| cktevo_mem_ctrl__mc_adr_sel | 0 | 0.44 % | 1.25 % | 1.35 % | 0 | 0 | 0 |
| cktevo_nn_engine__thresholds_128x4096 | - | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_risc__cpu | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_usb__usbf_sie_rx | 0 | 1.28 % | 1.25 % | 1.32 % | 0 | 0 | 0 |
| cktevo_vga_enh__vga_wb_slave | 0 | 1.93 % | 2.04 % | 1.90 % | 0 | 0 | 0 |
| drrtl_SPI | 0 | 0 | 6.28 % | 6.28 % | 0 | 0 | 0 |
| drrtl_UART | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_arm_cpu2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_communication | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_router | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_simple_spi | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rtlopt_alu_64bit | 0 | 20.97 % | 0 | 0 | 0 | 0 | 0 |
| rtlopt_calculation | 0 | 38.86 % | 35.66 % | 37.76 % | 0 | 0 | 0 |
| rtlopt_decoder_8bit | 0 | 0.32 % | 0.32 % | 0.32 % | 0 | 0 | 0 |
| rtlopt_divider_8bit | 0 | 65.38 % | 65.18 % | 64.04 % | 0 | 0 | 0 |
| rtlopt_register | 0 | 0.87 % | 0.63 % | 0 | 0 | 0 | 0 |
| rtlopt_sub_32bit | 0 | 3.83 % | 3.83 % | 3.83 % | 0 | 0 | 0 |

## 3. Model contrast (the same arm under two models on the same tier)

- **large / M**: gpt-5.6-luna (contrast): proven 0.112 / call, retained 2.44 / run, best gain mean 0.24 %, unusable 6, USD 3.25; gpt-5.6-terra (main): proven 0.133 / call, retained 4.33 / run, best gain mean 0.62 %, unusable 1, USD 34.40
- **medium / B2**: gpt-5.6-luna (main): proven 0.499 / call, retained 3.02 / run, best gain mean 2.16 %, unusable 9, USD 2.09; gpt-5.6-terra (second): proven 0.428 / call, retained 1.46 / run, best gain mean 2.16 %, unusable 6, USD 15.26
- **medium / M**: gpt-5.6-luna (main): proven - / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 0.00; gpt-5.6-terra (second): proven - / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 0.00

## 4. Retained-gain curves (mean over the group's runs of the best retained area gain so far)

### large tier — by LLM calls (equal-call caliber)

| model | arm | 5 calls | 10 calls | 20 calls | 30 calls | 40 calls | 50 calls | 60 calls |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-terra | B0 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | B1_E4 | 0.13 % | 0.28 % | 0.44 % | 0.44 % | 0.46 % | 0.46 % | 0.49 % |
| gpt-5.6-terra | B2 | 0.10 % | 0.15 % | 0.26 % | 0.37 % | 0.38 % | 0.40 % | 0.41 % |
| gpt-5.6-terra | DrRTL_reimpl | 0.03 % | 0.03 % | 0.03 % | 0.06 % | 0.09 % | 0.09 % | 0.09 % |
| gpt-5.6-luna | M | 0.02 % | 0.05 % | 0.12 % | 0.16 % | 0.22 % | 0.23 % | 0.24 % |
| gpt-5.6-terra | M | 0.07 % | 0.22 % | 0.27 % | 0.33 % | 0.56 % | 0.56 % | 0.62 % |

### large tier — by visible DC hours per run

- gpt-5.6-terra / B1_E4: 0.25 h → 0.09 %, 1.50 h → 0.40 %, 2.75 h → 0.46 %, 4.00 h → 0.48 %, 5.25 h → 0.48 %, 6.50 h → 0.49 %, 7.75 h → 0.49 %
- gpt-5.6-terra / B2: 0.25 h → 0.10 %, 1.25 h → 0.25 %, 2.25 h → 0.34 %, 3.25 h → 0.39 %, 4.25 h → 0.40 %, 5.25 h → 0.40 %, 6.25 h → 0.41 %
- gpt-5.6-terra / DrRTL_reimpl: 0.25 h → 0.01 %, 1.75 h → 0.03 %, 3.25 h → 0.06 %, 4.75 h → 0.06 %, 6.25 h → 0.06 %, 7.75 h → 0.09 %
- gpt-5.6-luna / M: 0.25 h → 0.05 %, 0.50 h → 0.12 %, 0.75 h → 0.12 %, 1.00 h → 0.21 %, 1.25 h → 0.22 %, 1.50 h → 0.23 %, 1.75 h → 0.24 %
- gpt-5.6-terra / M: 0.25 h → 0.07 %, 0.75 h → 0.28 %, 1.25 h → 0.37 %, 1.75 h → 0.37 %, 2.25 h → 0.62 %, 2.75 h → 0.62 %, 3.25 h → 0.62 %

### medium tier — by LLM calls (equal-call caliber)

| model | arm | 5 calls | 10 calls | 20 calls | 30 calls | 40 calls | 50 calls | 60 calls |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | B0 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-luna | B1_E4 | 1.20 % | 1.89 % | 2.06 % | 2.11 % | 2.14 % | 2.20 % | 2.59 % |
| gpt-5.6-luna | B2 | 0.71 % | 0.71 % | 1.91 % | 2.13 % | 2.15 % | 2.16 % | 2.16 % |
| gpt-5.6-terra | B2 | 0.78 % | 0.95 % | 2.14 % | 2.15 % | 2.15 % | 2.16 % | 2.16 % |
| gpt-5.6-luna | DrRTL_reimpl | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-luna | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |

### medium tier — by visible DC hours per run

- gpt-5.6-luna / B1_E4: 0.25 h → 1.89 %, 1.25 h → 2.14 %, 2.25 h → 2.59 %, 3.25 h → 2.59 %, 4.25 h → 2.59 %, 5.25 h → 2.59 %, 6.25 h → 2.59 %
- gpt-5.6-luna / B2: 0.25 h → 0.83 %, 1.00 h → 2.04 %, 1.75 h → 2.15 %, 2.50 h → 2.15 %, 3.25 h → 2.16 %, 4.00 h → 2.16 %, 4.75 h → 2.16 %
- gpt-5.6-terra / B2: 0.25 h → 0.89 %, 0.75 h → 2.13 %, 1.25 h → 2.14 %, 1.75 h → 2.15 %, 2.25 h → 2.16 %, 2.75 h → 2.16 %, 3.25 h → 2.16 %
- gpt-5.6-luna / DrRTL_reimpl: 0.25 h → 0.00 %, 0.75 h → 0.00 %, 1.25 h → 0.00 %, 1.75 h → 0.00 %, 2.25 h → 0.00 %, 2.75 h → 0.00 %, 3.25 h → 0.00 %

## 5. Correctness (the LLM's equivalence-preserving rate)

| tier | model | design | runs | candidates | proven | proven rate |
|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | cktevo_hsm__hsm | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | cktevo_hsm__hsm | 15 | 875 | 0 | 0.0 % |
| large | gpt-5.6-luna | cktevo_nn_engine__spikeNeuron8_H7 | 3 | 180 | 21 | 11.7 % |
| large | gpt-5.6-terra | cktevo_nn_engine__spikeNeuron8_H7 | 15 | 870 | 293 | 33.7 % |
| large | gpt-5.6-luna | cktevo_risc__btb | 3 | 180 | 102 | 56.7 % |
| large | gpt-5.6-terra | cktevo_risc__btb | 15 | 871 | 650 | 74.6 % |
| large | gpt-5.6-luna | drrtl_LSTM | 3 | 180 | 0 | 0.0 % |
| large | gpt-5.6-terra | drrtl_LSTM | 15 | 883 | 0 | 0.0 % |
| large | gpt-5.6-luna | drrtl_aes | 3 | 180 | 59 | 32.8 % |
| large | gpt-5.6-terra | drrtl_aes | 15 | 870 | 518 | 59.5 % |
| large | gpt-5.6-luna | drrtl_tv80 | 3 | 174 | 0 | 0.0 % |
| large | gpt-5.6-terra | drrtl_tv80 | 15 | 870 | 0 | 0.0 % |
| medium | gpt-5.6-luna | cktevo_ethmac__eth_cop | 15 | 180 | 94 | 52.2 % |
| medium | gpt-5.6-terra | cktevo_ethmac__eth_cop | 6 | 48 | 37 | 77.1 % |
| medium | gpt-5.6-luna | cktevo_mem_ctrl__mc_adr_sel | 15 | 179 | 124 | 69.3 % |
| medium | gpt-5.6-terra | cktevo_mem_ctrl__mc_adr_sel | 6 | 50 | 39 | 78.0 % |
| medium | gpt-5.6-luna | cktevo_nn_engine__thresholds_128x4096 | 12 | 147 | 111 | 75.5 % |
| medium | gpt-5.6-terra | cktevo_nn_engine__thresholds_128x4096 | 6 | 40 | 17 | 42.5 % |
| medium | gpt-5.6-luna | cktevo_risc__cpu | 15 | 180 | 17 | 9.4 % |
| medium | gpt-5.6-terra | cktevo_risc__cpu | 6 | 22 | 0 | 0.0 % |
| medium | gpt-5.6-luna | cktevo_usb__usbf_sie_rx | 15 | 173 | 117 | 67.6 % |
| medium | gpt-5.6-terra | cktevo_usb__usbf_sie_rx | 6 | 50 | 40 | 80.0 % |
| medium | gpt-5.6-luna | cktevo_vga_enh__vga_wb_slave | 15 | 180 | 112 | 62.2 % |
| medium | gpt-5.6-terra | cktevo_vga_enh__vga_wb_slave | 6 | 38 | 29 | 76.3 % |
| medium | gpt-5.6-luna | drrtl_SPI | 15 | 136 | 6 | 4.4 % |
| medium | gpt-5.6-terra | drrtl_SPI | 6 | 15 | 2 | 13.3 % |
| medium | gpt-5.6-luna | drrtl_UART | 15 | 141 | 107 | 75.9 % |
| medium | gpt-5.6-terra | drrtl_UART | 6 | 21 | 4 | 19.1 % |
| medium | gpt-5.6-luna | drrtl_arm_cpu2 | 15 | 166 | 0 | 0.0 % |
| medium | gpt-5.6-terra | drrtl_arm_cpu2 | 6 | 54 | 0 | 0.0 % |
| medium | gpt-5.6-luna | drrtl_communication | 15 | 162 | 29 | 17.9 % |
| medium | gpt-5.6-terra | drrtl_communication | 6 | 59 | 0 | 0.0 % |
| medium | gpt-5.6-luna | drrtl_router | 15 | 180 | 0 | 0.0 % |
| medium | gpt-5.6-terra | drrtl_router | 6 | 16 | 0 | 0.0 % |
| medium | gpt-5.6-luna | drrtl_simple_spi | 15 | 180 | 0 | 0.0 % |
| medium | gpt-5.6-terra | drrtl_simple_spi | 6 | 60 | 0 | 0.0 % |
| medium | gpt-5.6-luna | rtlopt_alu_64bit | 15 | 180 | 144 | 80.0 % |
| medium | gpt-5.6-terra | rtlopt_alu_64bit | 6 | 29 | 19 | 65.5 % |
| medium | gpt-5.6-luna | rtlopt_calculation | 15 | 151 | 121 | 80.1 % |
| medium | gpt-5.6-terra | rtlopt_calculation | 6 | 15 | 10 | 66.7 % |
| medium | gpt-5.6-luna | rtlopt_decoder_8bit | 15 | 168 | 127 | 75.6 % |
| medium | gpt-5.6-terra | rtlopt_decoder_8bit | 6 | 25 | 16 | 64.0 % |
| medium | gpt-5.6-luna | rtlopt_divider_8bit | 15 | 169 | 121 | 71.6 % |
| medium | gpt-5.6-terra | rtlopt_divider_8bit | 6 | 20 | 13 | 65.0 % |
| medium | gpt-5.6-luna | rtlopt_register | 15 | 167 | 127 | 76.0 % |
| medium | gpt-5.6-terra | rtlopt_register | 6 | 14 | 8 | 57.1 % |
| medium | gpt-5.6-luna | rtlopt_sub_32bit | 15 | 159 | 118 | 74.2 % |
| medium | gpt-5.6-terra | rtlopt_sub_32bit | 6 | 11 | 7 | 63.6 % |

LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): cktevo_hsm__hsm under gpt-5.6-terra, cktevo_hsm__hsm under gpt-5.6-luna, drrtl_LSTM under gpt-5.6-terra, drrtl_LSTM under gpt-5.6-luna, drrtl_tv80 under gpt-5.6-terra, drrtl_tv80 under gpt-5.6-luna, drrtl_SPI under gpt-5.6-luna, drrtl_arm_cpu2 under gpt-5.6-luna, drrtl_arm_cpu2 under gpt-5.6-terra, drrtl_communication under gpt-5.6-terra, drrtl_router under gpt-5.6-luna, drrtl_simple_spi under gpt-5.6-luna, drrtl_simple_spi under gpt-5.6-terra.

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 381, 'b': 446, 'c1': 81, 'd': 82, 'free': 6}; requested → produced a->a: 21, a->b: 41, a->c1: 3, a->d: 11, b->a: 73, b->b: 27, b->c1: 1, b->d: 7, c1->a: 83, c1->b: 136, c1->c1: 38, c1->d: 16, d->a: 147, d->b: 176, d->c1: 28, d->d: 33, free->a: 57, free->b: 66, free->c1: 11, free->d: 15, free->free: 6
- large / gpt-5.6-terra / B0: produced {'a': 245, 'b': 577, 'c1': 60, 'd': 156, 'free': 1}; requested → produced a->a: 41, a->b: 95, a->c1: 4, a->d: 25, b->a: 47, b->b: 59, b->c1: 1, b->d: 21, c1->a: 46, c1->b: 89, c1->c1: 36, c1->d: 28, d->a: 54, d->b: 162, d->c1: 8, d->d: 36, free->a: 57, free->b: 172, free->c1: 11, free->d: 46, free->free: 1
- large / gpt-5.6-terra / B1_E4: produced {'a': 314, 'b': 505, 'c1': 72, 'd': 145}; requested → produced a->a: 32, a->b: 110, a->c1: 7, a->d: 27, b->a: 75, b->b: 55, b->c1: 5, b->d: 29, c1->a: 55, c1->b: 104, c1->c1: 9, c1->d: 12, d->a: 78, d->b: 111, d->c1: 18, d->d: 23, free->a: 74, free->b: 125, free->c1: 33, free->d: 54
- large / gpt-5.6-terra / B2: produced {'a': 373, 'b': 516, 'c1': 66, 'd': 110}; requested → produced a->a: 46, a->b: 96, a->c1: 5, a->d: 2, b->a: 75, b->b: 58, b->d: 13, c1->a: 83, c1->b: 105, c1->c1: 11, c1->d: 19, d->a: 74, d->b: 134, d->c1: 30, d->d: 24, free->a: 95, free->b: 123, free->c1: 20, free->d: 52
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 423, 'b': 288, 'c1': 20, 'd': 1, 'free': 3}; requested → produced free->a: 423, free->b: 288, free->c1: 20, free->d: 1, free->free: 3
- large / gpt-5.6-terra / M: produced {'a': 336, 'b': 495, 'c1': 102, 'd': 78, 'free': 1}; requested → produced a->a: 8, a->b: 49, a->c1: 1, a->d: 2, b->a: 59, b->b: 33, b->d: 12, c1->a: 92, c1->b: 156, c1->c1: 40, c1->d: 32, d->a: 136, d->b: 205, d->c1: 47, d->d: 18, free->a: 41, free->b: 52, free->c1: 14, free->d: 14, free->free: 1
- medium / gpt-5.6-luna / B0: produced {'a': 190, 'b': 273, 'c1': 206, 'd': 255, 'free': 12}; requested → produced a->a: 31, a->b: 51, a->c1: 46, a->d: 48, b->a: 50, b->b: 24, b->c1: 33, b->d: 48, c1->a: 27, c1->b: 49, c1->c1: 28, c1->d: 46, d->a: 37, d->b: 87, d->c1: 63, d->d: 49, free->a: 45, free->b: 62, free->c1: 36, free->d: 64, free->free: 12
- medium / gpt-5.6-luna / B1_E4: produced {'a': 146, 'b': 461, 'c1': 177, 'd': 225, 'free': 9}; requested → produced a->a: 23, a->b: 67, a->c1: 16, a->d: 20, b->a: 20, b->b: 39, b->c1: 21, b->d: 44, c1->a: 35, c1->b: 68, c1->c1: 20, c1->d: 29, d->a: 25, d->b: 128, d->c1: 63, d->d: 44, free->a: 43, free->b: 159, free->c1: 57, free->d: 88, free->free: 9
- medium / gpt-5.6-luna / B2: produced {'a': 169, 'b': 375, 'c1': 150, 'd': 184, 'free': 5}; requested → produced a->a: 24, a->b: 75, a->c1: 25, a->d: 31, b->a: 30, b->b: 30, b->c1: 25, b->d: 33, c1->a: 29, c1->b: 55, c1->c1: 27, c1->d: 26, d->a: 32, d->b: 109, d->c1: 37, d->d: 28, free->a: 54, free->b: 106, free->c1: 36, free->d: 66, free->free: 5
- medium / gpt-5.6-luna / DrRTL_reimpl: produced {'a': 17, 'b': 3, 'd': 7}; requested → produced free->a: 17, free->b: 3, free->d: 7
- medium / gpt-5.6-terra / B2: produced {'a': 105, 'b': 230, 'c1': 144, 'd': 91, 'free': 8}; requested → produced a->a: 32, a->b: 54, a->c1: 18, a->d: 13, b->a: 26, b->b: 31, b->c1: 11, b->d: 12, c1->a: 6, c1->b: 27, c1->c1: 25, c1->d: 12, d->a: 13, d->b: 60, d->c1: 52, d->d: 21, free->a: 28, free->b: 58, free->c1: 38, free->d: 33, free->free: 8

## 7. Runs and anomalies

Runs on the reported tiers: 483 (146 done, 34 running, 303 not started). No run in an abnormal status.

## 7a. Operational changes during the run (DECISIONS 2026-09-16; verdict definitions, floors, budgets and the stack unchanged)

Hidden DC registrations capped at 8 from 2026-09-16T14:30; split equivalence pipeline, provisional diagnosis and proof ordering from 2026-09-16T15:14; positive provisional verdicts withheld from the model from 2026-09-16T16:03.

- Provisional-versus-final diagnosis agreement: 274 of 333 proven candidates with a final diagnosis agree (82.3 %); 3666 candidates received a provisional label (absorbed_identical 31, duplicate 38, harmful 112, improved 2311, no_gain 637, noise 73, retained 198, tradeoff 266), 1305 of them were not proven, 2028 still wait for the proof or the diagnosis, 2715 labels withheld from the model. Disagreements: tradeoff→duplicate; tradeoff→duplicate; retained→duplicate; harmful→duplicate; retained→duplicate; retained→duplicate; retained→duplicate; tradeoff→duplicate.
- Positive provisional feedback exposure (window 2026-09-16T15:14 to 2026-09-16T16:03): 15 LLM calls carried 25 positive pending blocks (2 runs); 8 candidates behind them — proofs since: inconclusive 8.
- Cross-run verdict reuse since 2026-09-16T15:14: 0 proofs copied from a decided record of the same pair ({}), over 4326 split-pipeline proofs of 10946 equivalence records; sim records missing: 0.

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
| 2026-09-18T04 | 167 | 145 | 10 | 14.5 | 12 | 0 | 0 |

