# Phase 5 report (Stage B — large and medium tiers)

Generated 2026-09-18T01:20 by scripts/report_phase.py phase5 --stage B (git 2e44fe8719a3, cfg 3c7f3d2a961d). Data: reports/data/phase5_visible_B.json (src/analysis/phase5.collect). Visible layer only: no hidden-configuration result is read before the Phase 5 completion marker (rule 3, spec 06 §2); the hidden part follows from scripts/report_hidden.py. Protocol frozen for Phase 5: prompts, correctness aids, caps and the equivalence stack (equiv_version = phase5, floor_version = phase4); an interim report changes nothing.

## 0. Progress

| tier | model | arm | runs done / existing / planned | calls | USD | DC h (visible) | VC Formal h |
|---|---|---|---|---|---|---|---|
| large | gpt-5.6-luna | M | 18 / 18 / 18 | 1080 | 3.25 | 33.3 | 179.9 |
| large | gpt-5.6-terra | B0 | 18 / 18 / 18 | 1080 | 34.21 | 0.0 | 490.4 |
| large | gpt-5.6-terra | B1_E4 | 18 / 18 / 18 | 1080 | 38.15 | 57.2 | 470.6 |
| large | gpt-5.6-terra | B2 | 18 / 18 / 18 | 1080 | 37.62 | 55.8 | 482.2 |
| large | gpt-5.6-terra | DrRTL_reimpl | 18 / 18 / 18 | 1080 | 38.17 | 46.5 | 180.9 |
| large | gpt-5.6-terra | M | 18 / 18 / 18 | 1080 | 34.40 | 38.9 | 450.7 |
| medium | gpt-5.6-luna | B0 | 11 / 51 / 51 | 927 | 1.85 | 0.0 | 52.8 |
| medium | gpt-5.6-luna | B1_E4 | 4 / 54 / 54 | 792 | 1.77 | 24.0 | 36.3 |
| medium | gpt-5.6-luna | B2 | 0 / 54 / 54 | 249 | 0.64 | 9.5 | 3.0 |
| medium | gpt-5.6-luna | DrRTL_reimpl | 0 / 54 / 54 | 0 | 0.00 | 0.0 | 0.0 |
| medium | gpt-5.6-luna | M | 0 / 54 / 54 | 0 | 0.00 | 0.0 | 0.0 |
| medium | gpt-5.6-terra | B2 | 0 / 54 / 54 | 17 | 0.40 | 0.8 | 0.1 |
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
| gpt-5.6-luna (main) | B0 | 11/51 | 927 | 0 | 447 (0.482) | 29 | 0 | 177 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | - | 1.85 | 0.0 | 52.8 |
| gpt-5.6-luna (main) | B1_E4 | 4/54 | 786 | 6 | 365 (0.461) | 26 | 0 | 177 | 130 | 2.41 | 9 | 2.12 % / 0.00 % | 16.41 | 73.28 | 5.42 | 1.77 | 24.0 | 36.3 |
| gpt-5.6-luna (main) | B2 | 0/54 | 257 | 3 | 117 (0.470) | 4 | 0 | 42 | 22 | 0.41 | 4 | 0.65 % / 0.00 % | 8.84 | 34.58 | 2.32 | 0.64 | 9.5 | 3.0 |
| gpt-5.6-luna (main) | DrRTL_reimpl | 0/54 | 0 | 0 | 0 (-) | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | - | - | - | 0.00 | 0.0 | 0.0 |
| gpt-5.6-luna (main) | M | 0/54 | 0 | 0 | 0 (-) | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | - | - | - | 0.00 | 0.0 | 0.0 |
| gpt-5.6-terra (second) | B2 | 0/54 | 17 | 0 | 1 (0.059) | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | 0.00 | 0.00 | 0.00 | 0.40 | 0.8 | 0.1 |
| gpt-5.6-terra (second) | M | 0/54 | 0 | 0 | 0 (-) | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.00 % / 0.00 % | - | - | - | 0.00 | 0.0 | 0.0 |

Verdict mix and labels:

| model | arm | sim_fail | falsified | rejected | inconclusive | error | pending | duplicate | prescreened | uniform labels of proven candidates | arm's stored labels | scope flags (block-level rate) | repairs (proven) | time to verdict s: median / q95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | B0 | 150 | 95 | 122 | 29 | 0 | 8 | 76 | 0 | - | improved: 365, no_gain: 77, nonequiv: 396 | 0 (0 / 94 = 0 %) | 214 (71) | 271 / 3420 |
| gpt-5.6-luna | B1_E4 | 133 | 65 | 135 | 26 | 0 | 39 | 23 | 0 | absorbed: 32, absorbed_identical: 40, harmful: 34, noise: 14, retained: 130, tradeoff: 115 | improved: 307, no_gain: 58, nonequiv: 359 | 3 (3 / 121 = 2 %) | 202 (63) | 357 / 3333 |
| gpt-5.6-luna | B2 | 24 | 33 | 31 | 4 | 0 | 48 | 0 | 0 | absorbed: 12, absorbed_identical: 14, harmful: 21, noise: 9, retained: 22, tradeoff: 33 | improved: 72, no_gain: 39, nonequiv: 92 | 3 (3 / 52 = 6 %) | 59 (23) | 272 / 2375 |
| gpt-5.6-luna | DrRTL_reimpl | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 0 (no block-level answers) | 0 (0) | - / - |
| gpt-5.6-luna | M | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 0 (no block-level answers) | 0 (0) | - / - |
| gpt-5.6-terra | B2 | 0 | 8 | 0 | 0 | 0 | 8 | 0 | 0 | absorbed_identical: 1 | nonequiv: 8 | 0 (no block-level answers) | 7 (1) | 939 / 3490 |
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
| cktevo_ethmac__eth_cop | 0 | 4.69 % | 0 | 0 | 0 | 0 | 0 |
| cktevo_mem_ctrl__mc_adr_sel | 0 | 0.44 % | 1.25 % | 0 | 0 | 0 | 0 |
| cktevo_nn_engine__thresholds_128x4096 | - | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_risc__cpu | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cktevo_usb__usbf_sie_rx | 0 | 1.28 % | 0.95 % | 0 | 0 | 0 | 0 |
| cktevo_vga_enh__vga_wb_slave | 0 | 1.93 % | 1.29 % | 0 | 0 | 0 | 0 |
| drrtl_SPI | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_UART | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_arm_cpu2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_communication | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_router | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drrtl_simple_spi | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rtlopt_alu_64bit | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rtlopt_calculation | 0 | 35.66 % | 31.55 % | 0 | 0 | 0 | 0 |
| rtlopt_decoder_8bit | 0 | 0.32 % | 0 | 0 | 0 | 0 | 0 |
| rtlopt_divider_8bit | 0 | 65.38 % | 0 | 0 | 0 | 0 | 0 |
| rtlopt_register | 0 | 0.85 % | 0 | 0 | 0 | 0 | 0 |
| rtlopt_sub_32bit | 0 | 3.83 % | 0 | 0 | 0 | 0 | 0 |

## 3. Model contrast (the same arm under two models on the same tier)

- **large / M**: gpt-5.6-luna (contrast): proven 0.112 / call, retained 2.44 / run, best gain mean 0.24 %, unusable 6, USD 3.25; gpt-5.6-terra (main): proven 0.133 / call, retained 4.33 / run, best gain mean 0.62 %, unusable 1, USD 34.40
- **medium / B2**: gpt-5.6-luna (main): proven 0.470 / call, retained 0.41 / run, best gain mean 0.65 %, unusable 3, USD 0.64; gpt-5.6-terra (second): proven 0.059 / call, retained 0.00 / run, best gain mean 0.00 %, unusable 0, USD 0.40
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
| gpt-5.6-luna | B1_E4 | 1.20 % | 1.89 % | 2.06 % | 2.11 % | 2.12 % | 2.12 % | 2.12 % |
| gpt-5.6-luna | B2 | 0.63 % | 0.63 % | 0.65 % | 0.65 % | 0.65 % | 0.65 % | 0.65 % |
| gpt-5.6-terra | B2 | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-luna | DrRTL_reimpl | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-luna | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| gpt-5.6-terra | M | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % | 0.00 % |

### medium tier — by visible DC hours per run

- gpt-5.6-luna / B1_E4: 0.25 h → 1.89 %, 1.25 h → 2.12 %, 2.25 h → 2.12 %, 3.25 h → 2.12 %, 4.25 h → 2.12 %, 5.25 h → 2.12 %, 6.25 h → 2.12 %
- gpt-5.6-luna / B2: 0.25 h → 0.63 %, 1.00 h → 0.65 %, 1.75 h → 0.65 %, 2.50 h → 0.65 %, 3.25 h → 0.65 %, 4.00 h → 0.65 %
- gpt-5.6-terra / B2: 0.25 h → 0.00 %

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
| medium | gpt-5.6-luna | cktevo_ethmac__eth_cop | 15 | 125 | 57 | 45.6 % |
| medium | gpt-5.6-terra | cktevo_ethmac__eth_cop | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | cktevo_mem_ctrl__mc_adr_sel | 15 | 149 | 102 | 68.5 % |
| medium | gpt-5.6-terra | cktevo_mem_ctrl__mc_adr_sel | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | cktevo_nn_engine__thresholds_128x4096 | 12 | 115 | 84 | 73.0 % |
| medium | gpt-5.6-terra | cktevo_nn_engine__thresholds_128x4096 | 6 | 17 | 1 | 5.9 % |
| medium | gpt-5.6-luna | cktevo_risc__cpu | 15 | 122 | 14 | 11.5 % |
| medium | gpt-5.6-terra | cktevo_risc__cpu | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | cktevo_usb__usbf_sie_rx | 15 | 130 | 88 | 67.7 % |
| medium | gpt-5.6-terra | cktevo_usb__usbf_sie_rx | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | cktevo_vga_enh__vga_wb_slave | 15 | 122 | 69 | 56.6 % |
| medium | gpt-5.6-terra | cktevo_vga_enh__vga_wb_slave | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | drrtl_SPI | 15 | 73 | 2 | 2.7 % |
| medium | gpt-5.6-terra | drrtl_SPI | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | drrtl_UART | 15 | 70 | 56 | 80.0 % |
| medium | gpt-5.6-terra | drrtl_UART | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | drrtl_arm_cpu2 | 15 | 127 | 0 | 0.0 % |
| medium | gpt-5.6-terra | drrtl_arm_cpu2 | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | drrtl_communication | 15 | 129 | 21 | 16.3 % |
| medium | gpt-5.6-terra | drrtl_communication | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | drrtl_router | 15 | 107 | 0 | 0.0 % |
| medium | gpt-5.6-terra | drrtl_router | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | drrtl_simple_spi | 15 | 129 | 0 | 0.0 % |
| medium | gpt-5.6-terra | drrtl_simple_spi | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | rtlopt_alu_64bit | 15 | 113 | 88 | 77.9 % |
| medium | gpt-5.6-terra | rtlopt_alu_64bit | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | rtlopt_calculation | 15 | 86 | 71 | 82.6 % |
| medium | gpt-5.6-terra | rtlopt_calculation | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | rtlopt_decoder_8bit | 15 | 113 | 87 | 77.0 % |
| medium | gpt-5.6-terra | rtlopt_decoder_8bit | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | rtlopt_divider_8bit | 15 | 95 | 68 | 71.6 % |
| medium | gpt-5.6-terra | rtlopt_divider_8bit | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | rtlopt_register | 15 | 78 | 51 | 65.4 % |
| medium | gpt-5.6-terra | rtlopt_register | 6 | 0 | 0 | - |
| medium | gpt-5.6-luna | rtlopt_sub_32bit | 15 | 87 | 71 | 81.6 % |
| medium | gpt-5.6-terra | rtlopt_sub_32bit | 6 | 0 | 0 | - |

LLM-correctness limit (proven rate below 5 % after ≥ 30 candidates): cktevo_hsm__hsm under gpt-5.6-terra, cktevo_hsm__hsm under gpt-5.6-luna, drrtl_LSTM under gpt-5.6-terra, drrtl_LSTM under gpt-5.6-luna, drrtl_tv80 under gpt-5.6-terra, drrtl_tv80 under gpt-5.6-luna, drrtl_SPI under gpt-5.6-luna, drrtl_arm_cpu2 under gpt-5.6-luna, drrtl_router under gpt-5.6-luna, drrtl_simple_spi under gpt-5.6-luna.

## 6. Classes produced (rules v2) and requested → produced

- large / gpt-5.6-luna / M: produced {'a': 381, 'b': 446, 'c1': 81, 'd': 82, 'free': 6}; requested → produced a->a: 21, a->b: 41, a->c1: 3, a->d: 11, b->a: 73, b->b: 27, b->c1: 1, b->d: 7, c1->a: 83, c1->b: 136, c1->c1: 38, c1->d: 16, d->a: 147, d->b: 176, d->c1: 28, d->d: 33, free->a: 57, free->b: 66, free->c1: 11, free->d: 15, free->free: 6
- large / gpt-5.6-terra / B0: produced {'a': 245, 'b': 577, 'c1': 60, 'd': 156, 'free': 1}; requested → produced a->a: 41, a->b: 95, a->c1: 4, a->d: 25, b->a: 47, b->b: 59, b->c1: 1, b->d: 21, c1->a: 46, c1->b: 89, c1->c1: 36, c1->d: 28, d->a: 54, d->b: 162, d->c1: 8, d->d: 36, free->a: 57, free->b: 172, free->c1: 11, free->d: 46, free->free: 1
- large / gpt-5.6-terra / B1_E4: produced {'a': 314, 'b': 505, 'c1': 72, 'd': 145}; requested → produced a->a: 32, a->b: 110, a->c1: 7, a->d: 27, b->a: 75, b->b: 55, b->c1: 5, b->d: 29, c1->a: 55, c1->b: 104, c1->c1: 9, c1->d: 12, d->a: 78, d->b: 111, d->c1: 18, d->d: 23, free->a: 74, free->b: 125, free->c1: 33, free->d: 54
- large / gpt-5.6-terra / B2: produced {'a': 373, 'b': 516, 'c1': 66, 'd': 110}; requested → produced a->a: 46, a->b: 96, a->c1: 5, a->d: 2, b->a: 75, b->b: 58, b->d: 13, c1->a: 83, c1->b: 105, c1->c1: 11, c1->d: 19, d->a: 74, d->b: 134, d->c1: 30, d->d: 24, free->a: 95, free->b: 123, free->c1: 20, free->d: 52
- large / gpt-5.6-terra / DrRTL_reimpl: produced {'a': 423, 'b': 288, 'c1': 20, 'd': 1, 'free': 3}; requested → produced free->a: 423, free->b: 288, free->c1: 20, free->d: 1, free->free: 3
- large / gpt-5.6-terra / M: produced {'a': 336, 'b': 495, 'c1': 102, 'd': 78, 'free': 1}; requested → produced a->a: 8, a->b: 49, a->c1: 1, a->d: 2, b->a: 59, b->b: 33, b->d: 12, c1->a: 92, c1->b: 156, c1->c1: 40, c1->d: 32, d->a: 136, d->b: 205, d->c1: 47, d->d: 18, free->a: 41, free->b: 52, free->c1: 14, free->d: 14, free->free: 1
- medium / gpt-5.6-luna / B0: produced {'a': 174, 'b': 244, 'c1': 197, 'd': 224, 'free': 12}; requested → produced a->a: 30, a->b: 49, a->c1: 44, a->d: 42, b->a: 46, b->b: 21, b->c1: 33, b->d: 47, c1->a: 26, c1->b: 47, c1->c1: 26, c1->d: 41, d->a: 34, d->b: 71, d->c1: 58, d->d: 45, free->a: 38, free->b: 56, free->c1: 36, free->d: 49, free->free: 12
- medium / gpt-5.6-luna / B1_E4: produced {'a': 109, 'b': 329, 'c1': 155, 'd': 161, 'free': 9}; requested → produced a->a: 19, a->b: 43, a->c1: 16, a->d: 11, b->a: 19, b->b: 28, b->c1: 17, b->d: 30, c1->a: 28, c1->b: 53, c1->c1: 19, c1->d: 25, d->a: 16, d->b: 89, d->c1: 54, d->d: 34, free->a: 27, free->b: 116, free->c1: 49, free->d: 61, free->free: 9
- medium / gpt-5.6-luna / B2: produced {'a': 81, 'b': 82, 'c1': 57, 'd': 35, 'free': 2}; requested → produced a->a: 11, a->b: 9, a->c1: 5, a->d: 3, b->a: 18, b->b: 12, b->c1: 11, b->d: 7, c1->a: 10, c1->b: 10, c1->c1: 13, c1->d: 5, d->a: 19, d->b: 27, d->c1: 14, d->d: 9, free->a: 23, free->b: 24, free->c1: 14, free->d: 11, free->free: 2
- medium / gpt-5.6-terra / B2: produced {'b': 15, 'c1': 2}; requested → produced a->b: 2, c1->b: 3, c1->c1: 2, d->b: 2, free->b: 8

## 7. Runs and anomalies

Runs on the reported tiers: 483 (123 done, 35 running, 325 not started). No run in an abnormal status.

## 7a. Operational changes during the run (DECISIONS 2026-09-16; verdict definitions, floors, budgets and the stack unchanged)

Hidden DC registrations capped at 8 from 2026-09-16T14:30; split equivalence pipeline, provisional diagnosis and proof ordering from 2026-09-16T15:14; positive provisional verdicts withheld from the model from 2026-09-16T16:03.

- Provisional-versus-final diagnosis agreement: 274 of 333 proven candidates with a final diagnosis agree (82.3 %); 2909 candidates received a provisional label (absorbed_identical 31, duplicate 38, harmful 112, improved 1756, no_gain 435, noise 73, retained 198, tradeoff 266), 1147 of them were not proven, 1429 still wait for the proof or the diagnosis, 2160 labels withheld from the model. Disagreements: tradeoff→duplicate; tradeoff→duplicate; retained→duplicate; harmful→duplicate; retained→duplicate; retained→duplicate; retained→duplicate; tradeoff→duplicate.
- Positive provisional feedback exposure (window 2026-09-16T15:14 to 2026-09-16T16:03): 15 LLM calls carried 25 positive pending blocks (2 runs); 8 candidates behind them — proofs since: inconclusive 8.
- Cross-run verdict reuse since 2026-09-16T15:14: 0 proofs copied from a decided record of the same pair ({}), over 3360 split-pipeline proofs of 8415 equivalence records; sim records missing: 0.

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
| 2026-09-18T01 | 142 | 82 | 17 | 4.82 | 15 | 0 | 0 |

