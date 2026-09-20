# Power basis and per-metric retention — Phase 5 Section III tables recomputed (2026-09-20; visible layer only; interim)

Generated 2026-09-20T05:26 by scripts/report_power_basis.py (git e3de7f0b1103, cfg 45803d414957); floor_version **phase4**, equiv_version phase5, harness_version 2; baseline basis **search**. REQUEST 2026-09-20 (e) items 1, 4, 5. Rule A on each candidate's E4 record (uniform_diagnosis); duplicates collapsed (spec 04 §B step 3); every retention figure carries its materiality count (area > 1 %, power > 2 %, WNS > 1 % of the period). No record, default or configuration was altered; results/hidden was not read. Phase 5 state at generation: runs {'medium': {'done': 297, 'created': 35, 'running': 44}, 'small': {'created': 120, 'done': 1, 'running': 5}, 'large': {'done': 90, 'created': 18}}; evaluated (proven with E4) 11341, pending E4 176, DC rejected 44, duplicates collapsed 2620.

## 0a. Power basis marks (item 1)

Designs whose D has no SAIF power at E4 (the evaluators' baseline, is_baseline = 1 at Φ_main): **13** — cktevo_hsm__MixColumns, cktevo_hsm__hsm, cktevo_nn_engine__thresholds_128x4096, cktevo_risc__btb, cktevo_risc__cpu, cktevo_risc__stall_control_unit, cktevo_usb__usbf_sie_rx, cktevo_vga_enh__vga_wb_slave, drrtl_LSTM, drrtl_aes, drrtl_arm_cpu2, drrtl_simple_spi, drrtl_tv80.

For each of them: *power on this design is on the default-activity basis for all arms during the search* (m3.power_basis compares default with default; the candidates' SAIF figures on these designs have no D counterpart).

The pooled-floor designs of the frozen table (PLAN 6.9, item 3 of the request): 13 — cktevo_hsm__hsm, cktevo_nn_engine__thresholds_128x4096, cktevo_risc__btb, cktevo_risc__cpu, cktevo_risc__stall_control_unit, cktevo_usb__usbf_sie_rx, cktevo_vga_enh__vga_wb_slave, drrtl_LSTM, drrtl_aes, drrtl_arm_cpu2, drrtl_router, drrtl_simple_spi, drrtl_tv80. The two lists differ by one design each: drrtl_router has a measured floor basis question only on power (D carries SAIF power); cktevo_hsm__MixColumns has a measured floor (its P1_text perturbations) but no D SAIF.

## 1. Versions

- **current** — rule A as reported (all metrics, the search's power basis)
- **a** — (a) power excluded on the default-basis designs; elsewhere power only when both records carry SAIF power
- **area** — (b) area only
- **wns** — (b) WNS only
- **power** — (b) power only (basis marked)

Under (a) a candidate whose only metric above its floor was power is labelled by area and WNS alone (noise, or absorbed when its E4 fingerprint converges with D's); a trade-off whose only metric below the floor was power becomes retained. Under (b) each metric is judged alone: retained = that metric above t_D, harmful = below −t_D, noise otherwise, absorbed when the fingerprint converges; absorbed_identical (D's netlist) keeps its label in every version. The power-only column marks the basis of each pair: saif (both records SAIF-backed), default (DC default activity on both), None (no power comparison possible).

## 2. Class × verdict per tier and pooled (paper_sec3.md §G (i); C1 §2.2)

### large tier (evaluated 1421)

| class | n | retained current (material) | retained a (material) | retained area (material) | retained wns (material) | retained power (material) | labels under (a) |
|---|---|---|---|---|---|---|---|
| a | 463 | 0 / 463 = 0.0 % (0) | 0 / 463 = 0.0 % (0) | 0 / 463 = 0.0 % (0) | 0 / 463 = 0.0 % (0) | 0 / 463 = 0.0 % (0) | absorbed_identical 144, absorbed 37, noise 96, harmful 186 |
| b | 663 | 304 / 663 = 45.9 % (247) | 287 / 663 = 43.3 % (148) | 318 / 663 = 48.0 % (194) | 219 / 663 = 33.0 % (0) | 368 / 663 = 55.5 % (368) | retained 287, tradeoff 110, absorbed_identical 25, absorbed 12, noise 123, harmful 106 |
| c1 | 47 | 12 / 47 = 25.5 % (6) | 12 / 47 = 25.5 % (3) | 14 / 47 = 29.8 % (6) | 7 / 47 = 14.9 % (0) | 26 / 47 = 55.3 % (26) | retained 12, tradeoff 6, noise 4, harmful 25 |
| d | 248 | 110 / 248 = 44.4 % (37) | 110 / 248 = 44.4 % (30) | 111 / 248 = 44.8 % (36) | 38 / 248 = 15.3 % (0) | 78 / 248 = 31.5 % (78) | retained 110, tradeoff 13, noise 35, harmful 90 |

### medium tier (evaluated 9802)

| class | n | retained current (material) | retained a (material) | retained area (material) | retained wns (material) | retained power (material) | labels under (a) |
|---|---|---|---|---|---|---|---|
| a | 2208 | 423 / 2208 = 19.2 % (394) | 430 / 2208 = 19.5 % (390) | 483 / 2208 = 21.9 % (417) | 860 / 2208 = 38.9 % (81) | 606 / 2208 = 27.4 % (606) | retained 430, tradeoff 607, absorbed_identical 889, absorbed 36, noise 14, harmful 232 |
| b | 3578 | 1270 / 3578 = 35.5 % (983) | 1308 / 3578 = 36.6 % (1008) | 1368 / 3578 = 38.2 % (952) | 2092 / 3578 = 58.5 % (1020) | 884 / 3578 = 24.7 % (884) | retained 1308, tradeoff 974, absorbed_identical 708, absorbed 141, noise 8, harmful 439 |
| c1 | 1610 | 593 / 1610 = 36.8 % (563) | 579 / 1610 = 36.0 % (540) | 360 / 1610 = 22.4 % (200) | 960 / 1610 = 59.6 % (412) | 518 / 1610 = 32.2 % (518) | retained 579, tradeoff 560, absorbed_identical 14, absorbed 5, noise 201, harmful 251 |
| c2 | 1 | 1 / 1 = 100.0 % (1) | 1 / 1 = 100.0 % (1) | 0 / 1 = 0.0 % (0) | 0 / 1 = 0.0 % (0) | 1 / 1 = 100.0 % (1) | retained 1 |
| d | 2405 | 1072 / 2405 = 44.6 % (1037) | 1087 / 2405 = 45.2 % (1049) | 1262 / 2405 = 52.5 % (800) | 1708 / 2405 = 71.0 % (615) | 1192 / 2405 = 49.6 % (1192) | retained 1087, tradeoff 1030, absorbed_identical 103, absorbed 19, noise 6, harmful 160 |

### small tier (evaluated 118)

| class | n | retained current (material) | retained a (material) | retained area (material) | retained wns (material) | retained power (material) | labels under (a) |
|---|---|---|---|---|---|---|---|
| a | 21 | 1 / 21 = 4.8 % (1) | 1 / 21 = 4.8 % (1) | 13 / 21 = 61.9 % (13) | 17 / 21 = 81.0 % (16) | 1 / 21 = 4.8 % (1) | retained 1, tradeoff 17, absorbed_identical 1, harmful 2 |
| b | 82 | 6 / 82 = 7.3 % (6) | 6 / 82 = 7.3 % (6) | 20 / 82 = 24.4 % (15) | 17 / 82 = 20.7 % (8) | 13 / 82 = 15.9 % (13) | retained 6, tradeoff 20, absorbed_identical 48, harmful 8 |
| d | 15 | 0 / 15 = 0.0 % (0) | 0 / 15 = 0.0 % (0) | 2 / 15 = 13.3 % (2) | 0 / 15 = 0.0 % (0) | 0 / 15 = 0.0 % (0) | tradeoff 2, harmful 13 |

### pooled over the started tiers (evaluated 11341)

| class | n | retained current (material) | retained a (material) | retained area (material) | retained wns (material) | retained power (material) | labels under (a) |
|---|---|---|---|---|---|---|---|
| a | 2692 | 424 / 2692 = 15.8 % (395) | 431 / 2692 = 16.0 % (391) | 496 / 2692 = 18.4 % (430) | 877 / 2692 = 32.6 % (97) | 607 / 2692 = 22.5 % (607) | retained 431, tradeoff 624, absorbed_identical 1034, absorbed 73, noise 110, harmful 420 |
| b | 4323 | 1580 / 4323 = 36.5 % (1236) | 1601 / 4323 = 37.0 % (1162) | 1706 / 4323 = 39.5 % (1161) | 2328 / 4323 = 53.9 % (1028) | 1265 / 4323 = 29.3 % (1265) | retained 1601, tradeoff 1104, absorbed_identical 781, absorbed 153, noise 131, harmful 553 |
| c1 | 1657 | 605 / 1657 = 36.5 % (569) | 591 / 1657 = 35.7 % (543) | 374 / 1657 = 22.6 % (206) | 967 / 1657 = 58.4 % (412) | 544 / 1657 = 32.8 % (544) | retained 591, tradeoff 566, absorbed_identical 14, absorbed 5, noise 205, harmful 276 |
| c2 | 1 | 1 / 1 = 100.0 % (1) | 1 / 1 = 100.0 % (1) | 0 / 1 = 0.0 % (0) | 0 / 1 = 0.0 % (0) | 1 / 1 = 100.0 % (1) | retained 1 |
| d | 2668 | 1182 / 2668 = 44.3 % (1074) | 1197 / 2668 = 44.9 % (1079) | 1375 / 2668 = 51.5 % (838) | 1746 / 2668 = 65.4 % (615) | 1270 / 2668 = 47.6 % (1270) | retained 1197, tradeoff 1045, absorbed_identical 103, absorbed 19, noise 41, harmful 263 |

## 3. The family table (paper_sec3.md §G (ii))

| family | designs | evaluated | retained current (material) | retained a (material) | retained area (material) | retained wns (material) | retained power (material) |
|---|---|---|---|---|---|---|---|
| Dr.RTL | 6 | 2364 | 156 = 6.6 % (79) | 157 = 6.6 % (76) | 249 = 10.5 % (152) | 419 = 17.7 % (96) | 141 = 6.0 % (141) |
| CktEvo | 8 | 4506 | 1495 = 33.2 % (1111) | 1489 = 33.0 % (1014) | 1143 = 25.4 % (748) | 2255 = 50.0 % (837) | 1262 = 28.0 % (1262) |
| RTL-OPT | 8 | 4471 | 2141 = 47.9 % (2085) | 2175 = 48.6 % (2086) | 2559 = 57.2 % (1735) | 3244 = 72.6 % (1219) | 2284 = 51.1 % (2284) |

## 4. Per-design retained counts (C1 §4 rows; every evaluated design, by arm)

| design | tier | basis | arm | evaluated | retained current | retained a | retained area | retained wns | retained power | power pairs by basis |
|---|---|---|---|---|---|---|---|---|---|---|
| cktevo_nn_engine__spikeNeuron8_H7 | large | saif | B0 | 4 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | saif 4 |
| cktevo_nn_engine__spikeNeuron8_H7 | large | saif | B1_E4 | 92 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | saif 92 |
| cktevo_nn_engine__spikeNeuron8_H7 | large | saif | B2 | 92 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | saif 92 |
| cktevo_nn_engine__spikeNeuron8_H7 | large | saif | DrRTL_reimpl | 99 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | saif 99 |
| cktevo_nn_engine__spikeNeuron8_H7 | large | saif | M | 18 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | saif 18 |
| cktevo_nn_engine__spikeNeuron8_H7 | large | | **all arms** | 305 | 0 | 0 | 0 | 0 | 0 | |
| cktevo_risc__btb | large | default | B0 | 130 | 39 (26) | 29 (6) | 16 (9) | 36 (0) | 69 (69) | default 130 |
| cktevo_risc__btb | large | default | B1_E4 | 133 | 81 (77) | 78 (58) | 108 (76) | 54 (0) | 119 (119) | default 133 |
| cktevo_risc__btb | large | default | B2 | 135 | 81 (73) | 78 (52) | 96 (67) | 57 (0) | 108 (108) | default 135 |
| cktevo_risc__btb | large | default | DrRTL_reimpl | 119 | 43 (11) | 43 (0) | 14 (0) | 38 (0) | 14 (14) | default 119 |
| cktevo_risc__btb | large | default | M | 185 | 107 (97) | 106 (60) | 134 (79) | 76 (0) | 144 (144) | default 185 |
| cktevo_risc__btb | large | | **all arms** | 702 | 351 | 334 | 368 | 261 | 454 | |
| drrtl_aes | large | default | B0 | 37 | 4 (0) | 4 (0) | 4 (0) | 0 (0) | 0 (0) | default 37 |
| drrtl_aes | large | default | B1_E4 | 102 | 40 (0) | 40 (0) | 40 (0) | 0 (0) | 1 (1) | default 102 |
| drrtl_aes | large | default | B2 | 90 | 15 (0) | 15 (0) | 15 (0) | 0 (0) | 2 (2) | default 90 |
| drrtl_aes | large | default | DrRTL_reimpl | 123 | 1 (1) | 1 (0) | 1 (0) | 0 (0) | 7 (7) | default 123 |
| drrtl_aes | large | default | M | 62 | 15 (5) | 15 (5) | 15 (5) | 3 (0) | 8 (8) | default 62 |
| drrtl_aes | large | | **all arms** | 414 | 75 | 75 | 75 | 3 | 18 | |
| cktevo_ethmac__eth_cop | medium | saif | B0 | 88 | 7 (7) | 9 (7) | 6 (6) | 71 (2) | 47 (47) | default 44, saif 44 |
| cktevo_ethmac__eth_cop | medium | saif | B1_E4 | 119 | 7 (7) | 7 (7) | 7 (7) | 101 (10) | 17 (17) | saif 119 |
| cktevo_ethmac__eth_cop | medium | saif | B2 | 267 | 3 (3) | 3 (3) | 5 (5) | 222 (22) | 48 (48) | default 2, saif 265 |
| cktevo_ethmac__eth_cop | medium | saif | DrRTL_reimpl | 86 | 15 (13) | 15 (13) | 14 (14) | 65 (1) | 50 (50) | saif 86 |
| cktevo_ethmac__eth_cop | medium | saif | M | 152 | 17 (15) | 17 (15) | 15 (15) | 134 (4) | 76 (76) | saif 152 |
| cktevo_ethmac__eth_cop | medium | | **all arms** | 712 | 49 | 51 | 47 | 593 | 238 | |
| cktevo_mem_ctrl__mc_adr_sel | medium | saif | B0 | 120 | 46 (45) | 29 (29) | 8 (8) | 26 (26) | 38 (38) | default 67, saif 53 |
| cktevo_mem_ctrl__mc_adr_sel | medium | saif | B1_E4 | 121 | 70 (70) | 70 (70) | 4 (4) | 36 (36) | 56 (56) | saif 121 |
| cktevo_mem_ctrl__mc_adr_sel | medium | saif | B2 | 277 | 76 (76) | 76 (76) | 24 (24) | 73 (73) | 55 (55) | saif 277 |
| cktevo_mem_ctrl__mc_adr_sel | medium | saif | DrRTL_reimpl | 127 | 119 (119) | 119 (119) | 71 (71) | 101 (101) | 72 (72) | saif 127 |
| cktevo_mem_ctrl__mc_adr_sel | medium | saif | M | 83 | 24 (23) | 24 (23) | 5 (5) | 15 (15) | 16 (16) | saif 83 |
| cktevo_mem_ctrl__mc_adr_sel | medium | | **all arms** | 728 | 335 | 318 | 112 | 251 | 237 | |
| cktevo_nn_engine__thresholds_128x4096 | medium | default | B1_E4 | 129 | 0 (0) | 0 (0) | 0 (0) | 9 (9) | 24 (24) | default 129 |
| cktevo_nn_engine__thresholds_128x4096 | medium | default | B2 | 227 | 1 (0) | 1 (0) | 0 (0) | 48 (31) | 45 (45) | default 227 |
| cktevo_nn_engine__thresholds_128x4096 | medium | default | DrRTL_reimpl | 130 | 0 (0) | 0 (0) | 0 (0) | 19 (19) | 1 (1) | default 130 |
| cktevo_nn_engine__thresholds_128x4096 | medium | default | M | 36 | 0 (0) | 0 (0) | 0 (0) | 3 (3) | 8 (8) | default 36 |
| cktevo_nn_engine__thresholds_128x4096 | medium | | **all arms** | 522 | 1 | 1 | 0 | 79 | 78 | |
| cktevo_risc__cpu | medium | default | B0 | 41 | 0 (0) | 1 (0) | 1 (0) | 0 (0) | 0 (0) | default 41 |
| cktevo_risc__cpu | medium | default | B1_E4 | 9 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | default 9 |
| cktevo_risc__cpu | medium | default | B2 | 16 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | default 16 |
| cktevo_risc__cpu | medium | default | DrRTL_reimpl | 11 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | default 11 |
| cktevo_risc__cpu | medium | default | M | 12 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | default 12 |
| cktevo_risc__cpu | medium | | **all arms** | 89 | 0 | 1 | 1 | 0 | 0 | |
| cktevo_usb__usbf_sie_rx | medium | default | B0 | 116 | 94 (17) | 94 (18) | 45 (7) | 109 (19) | 0 (0) | default 116 |
| cktevo_usb__usbf_sie_rx | medium | default | B1_E4 | 113 | 61 (34) | 61 (34) | 45 (6) | 99 (45) | 2 (2) | default 113 |
| cktevo_usb__usbf_sie_rx | medium | default | B2 | 261 | 138 (91) | 138 (94) | 77 (18) | 232 (145) | 0 (0) | default 261 |
| cktevo_usb__usbf_sie_rx | medium | default | DrRTL_reimpl | 89 | 65 (29) | 65 (29) | 39 (0) | 74 (34) | 0 (0) | default 89 |
| cktevo_usb__usbf_sie_rx | medium | default | M | 182 | 103 (69) | 103 (69) | 62 (17) | 171 (100) | 0 (0) | default 182 |
| cktevo_usb__usbf_sie_rx | medium | | **all arms** | 761 | 461 | 461 | 268 | 685 | 2 | |
| cktevo_vga_enh__vga_wb_slave | medium | default | B0 | 115 | 50 (47) | 51 (48) | 85 (83) | 52 (8) | 67 (67) | default 115 |
| cktevo_vga_enh__vga_wb_slave | medium | default | B1_E4 | 103 | 72 (23) | 72 (23) | 43 (30) | 74 (19) | 26 (26) | default 103 |
| cktevo_vga_enh__vga_wb_slave | medium | default | B2 | 226 | 95 (77) | 117 (99) | 128 (118) | 161 (83) | 90 (90) | default 226 |
| cktevo_vga_enh__vga_wb_slave | medium | default | DrRTL_reimpl | 111 | 35 (30) | 35 (28) | 30 (28) | 35 (0) | 30 (30) | default 111 |
| cktevo_vga_enh__vga_wb_slave | medium | default | M | 132 | 46 (32) | 48 (34) | 61 (51) | 64 (32) | 40 (40) | default 132 |
| cktevo_vga_enh__vga_wb_slave | medium | | **all arms** | 687 | 298 | 323 | 347 | 386 | 253 | |
| drrtl_SPI | medium | saif | B1_E4 | 20 | 2 (2) | 2 (2) | 3 (3) | 0 (0) | 7 (7) | saif 20 |
| drrtl_SPI | medium | saif | B2 | 19 | 11 (11) | 11 (11) | 12 (12) | 0 (0) | 11 (11) | saif 19 |
| drrtl_SPI | medium | saif | DrRTL_reimpl | 78 | 40 (40) | 40 (40) | 30 (30) | 0 (0) | 71 (71) | saif 78 |
| drrtl_SPI | medium | saif | M | 13 | 5 (5) | 5 (5) | 5 (5) | 0 (0) | 9 (9) | saif 13 |
| drrtl_SPI | medium | | **all arms** | 130 | 58 | 58 | 50 | 0 | 98 | |
| drrtl_UART | medium | saif | B0 | 160 | 0 (0) | 0 (0) | 13 (13) | 49 (27) | 0 (0) | default 122, saif 38 |
| drrtl_UART | medium | saif | B1_E4 | 152 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | saif 152 |
| drrtl_UART | medium | saif | B2 | 378 | 0 (0) | 0 (0) | 37 (37) | 18 (14) | 0 (0) | saif 378 |
| drrtl_UART | medium | saif | DrRTL_reimpl | 80 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | saif 80 |
| drrtl_UART | medium | saif | M | 71 | 0 (0) | 0 (0) | 5 (3) | 1 (0) | 0 (0) | saif 71 |
| drrtl_UART | medium | | **all arms** | 841 | 0 | 0 | 55 | 68 | 0 | |
| drrtl_communication | medium | saif | B0 | 66 | 4 (4) | 3 (0) | 3 (0) | 9 (0) | 4 (4) | default 23, saif 43 |
| drrtl_communication | medium | saif | B1_E4 | 46 | 2 (2) | 2 (2) | 2 (2) | 17 (2) | 2 (2) | saif 46 |
| drrtl_communication | medium | saif | B2 | 61 | 5 (5) | 5 (5) | 7 (6) | 16 (1) | 4 (4) | saif 61 |
| drrtl_communication | medium | saif | DrRTL_reimpl | 46 | 0 (0) | 0 (0) | 4 (0) | 22 (13) | 0 (0) | saif 46 |
| drrtl_communication | medium | | **all arms** | 219 | 11 | 10 | 16 | 64 | 10 | |
| drrtl_router | medium | saif | B0 | 122 | 2 (0) | 2 (0) | 0 (0) | 12 (0) | 0 (0) | default 25, saif 97 |
| drrtl_router | medium | saif | B1_E4 | 115 | 0 (0) | 0 (0) | 2 (0) | 50 (0) | 0 (0) | saif 115 |
| drrtl_router | medium | saif | B2 | 215 | 8 (3) | 8 (3) | 46 (34) | 137 (32) | 14 (14) | saif 215 |
| drrtl_router | medium | saif | DrRTL_reimpl | 74 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | saif 74 |
| drrtl_router | medium | saif | M | 147 | 2 (1) | 2 (1) | 5 (2) | 13 (3) | 0 (0) | saif 147 |
| drrtl_router | medium | | **all arms** | 673 | 12 | 12 | 53 | 212 | 14 | |
| drrtl_simple_spi | medium | default | B0 | 13 | 0 (0) | 0 (0) | 0 (0) | 13 (0) | 0 (0) | default 13 |
| drrtl_simple_spi | medium | default | B1_E4 | 2 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | default 2 |
| drrtl_simple_spi | medium | default | B2 | 17 | 0 (0) | 0 (0) | 0 (0) | 12 (1) | 1 (1) | default 17 |
| drrtl_simple_spi | medium | default | DrRTL_reimpl | 55 | 0 (0) | 2 (2) | 0 (0) | 47 (3) | 0 (0) | default 55 |
| drrtl_simple_spi | medium | | **all arms** | 87 | 0 | 2 | 0 | 72 | 1 | |
| rtlopt_alu_64bit | medium | saif | B0 | 144 | 5 (5) | 23 (22) | 41 (41) | 107 (1) | 18 (18) | default 72, saif 72 |
| rtlopt_alu_64bit | medium | saif | B1_E4 | 149 | 30 (30) | 30 (30) | 40 (40) | 101 (2) | 64 (64) | saif 149 |
| rtlopt_alu_64bit | medium | saif | B2 | 293 | 46 (46) | 46 (46) | 165 (164) | 225 (7) | 81 (81) | saif 293 |
| rtlopt_alu_64bit | medium | saif | DrRTL_reimpl | 93 | 0 (0) | 0 (0) | 5 (5) | 22 (0) | 0 (0) | saif 93 |
| rtlopt_alu_64bit | medium | saif | M | 64 | 3 (3) | 3 (3) | 17 (17) | 42 (1) | 23 (23) | saif 64 |
| rtlopt_alu_64bit | medium | | **all arms** | 743 | 84 | 102 | 268 | 497 | 186 | |
| rtlopt_calculation | medium | saif | B0 | 144 | 131 (131) | 131 (131) | 135 (135) | 39 (0) | 133 (133) | default 51, saif 93 |
| rtlopt_calculation | medium | saif | B1_E4 | 114 | 105 (105) | 105 (105) | 106 (106) | 57 (0) | 106 (106) | saif 114 |
| rtlopt_calculation | medium | saif | B2 | 231 | 225 (225) | 225 (225) | 228 (228) | 133 (5) | 226 (226) | saif 231 |
| rtlopt_calculation | medium | saif | DrRTL_reimpl | 93 | 89 (89) | 89 (89) | 89 (88) | 84 (0) | 89 (89) | saif 93 |
| rtlopt_calculation | medium | | **all arms** | 582 | 550 | 550 | 558 | 313 | 554 | |
| rtlopt_decoder_8bit | medium | saif | B0 | 131 | 129 (88) | 129 (88) | 129 (0) | 131 (42) | 71 (71) | default 59, saif 72 |
| rtlopt_decoder_8bit | medium | saif | B1_E4 | 156 | 140 (140) | 140 (140) | 140 (0) | 143 (85) | 140 (140) | saif 156 |
| rtlopt_decoder_8bit | medium | saif | B2 | 289 | 257 (257) | 257 (257) | 257 (0) | 266 (122) | 257 (257) | saif 289 |
| rtlopt_decoder_8bit | medium | saif | DrRTL_reimpl | 62 | 61 (61) | 61 (61) | 61 (0) | 61 (35) | 61 (61) | saif 62 |
| rtlopt_decoder_8bit | medium | saif | M | 49 | 18 (18) | 18 (18) | 18 (0) | 31 (10) | 18 (18) | saif 49 |
| rtlopt_decoder_8bit | medium | | **all arms** | 687 | 605 | 605 | 605 | 632 | 547 | |
| rtlopt_divider_8bit | medium | saif | B0 | 127 | 93 (93) | 93 (93) | 94 (93) | 104 (104) | 93 (93) | default 66, saif 61 |
| rtlopt_divider_8bit | medium | saif | B1_E4 | 130 | 67 (67) | 67 (67) | 68 (68) | 117 (117) | 78 (78) | saif 130 |
| rtlopt_divider_8bit | medium | saif | B2 | 267 | 212 (212) | 212 (212) | 217 (215) | 240 (239) | 216 (216) | saif 267 |
| rtlopt_divider_8bit | medium | saif | DrRTL_reimpl | 116 | 69 (69) | 69 (69) | 78 (78) | 99 (97) | 78 (78) | saif 116 |
| rtlopt_divider_8bit | medium | saif | M | 147 | 104 (104) | 104 (104) | 107 (106) | 119 (119) | 110 (110) | saif 147 |
| rtlopt_divider_8bit | medium | | **all arms** | 787 | 545 | 545 | 564 | 679 | 575 | |
| rtlopt_register | medium | saif | B0 | 136 | 47 (41) | 63 (25) | 74 (58) | 78 (1) | 71 (71) | default 91, saif 45 |
| rtlopt_register | medium | saif | B1_E4 | 148 | 56 (56) | 56 (56) | 100 (31) | 130 (9) | 59 (59) | saif 148 |
| rtlopt_register | medium | saif | B2 | 298 | 40 (31) | 40 (31) | 151 (78) | 216 (0) | 64 (64) | saif 298 |
| rtlopt_register | medium | saif | DrRTL_reimpl | 135 | 59 (59) | 59 (59) | 42 (0) | 118 (1) | 61 (61) | saif 135 |
| rtlopt_register | medium | saif | M | 77 | 18 (18) | 18 (18) | 32 (24) | 47 (0) | 35 (35) | saif 77 |
| rtlopt_register | medium | | **all arms** | 794 | 220 | 236 | 399 | 589 | 290 | |
| rtlopt_sub_32bit | medium | saif | B0 | 125 | 36 (36) | 36 (36) | 36 (36) | 101 (37) | 24 (24) | default 67, saif 58 |
| rtlopt_sub_32bit | medium | saif | B1_E4 | 135 | 18 (18) | 18 (18) | 18 (18) | 91 (41) | 18 (18) | saif 135 |
| rtlopt_sub_32bit | medium | saif | B2 | 280 | 36 (36) | 36 (36) | 36 (36) | 198 (94) | 36 (36) | saif 280 |
| rtlopt_sub_32bit | medium | saif | DrRTL_reimpl | 73 | 34 (34) | 34 (34) | 34 (34) | 52 (2) | 34 (34) | saif 73 |
| rtlopt_sub_32bit | medium | saif | M | 147 | 6 (6) | 6 (6) | 6 (6) | 58 (24) | 6 (6) | saif 147 |
| rtlopt_sub_32bit | medium | | **all arms** | 760 | 130 | 130 | 130 | 500 | 118 | |
| rtlopt_mux_large | small | saif | B2 | 38 | 1 (1) | 1 (1) | 24 (24) | 27 (24) | 2 (2) | saif 38 |
| rtlopt_mux_large | small | | **all arms** | 38 | 1 | 1 | 24 | 27 | 2 | |
| rtlopt_sub_8bit | small | saif | B1_E4 | 19 | 3 (3) | 3 (3) | 3 (3) | 3 (0) | 3 (3) | saif 19 |
| rtlopt_sub_8bit | small | saif | B2 | 61 | 3 (3) | 3 (3) | 8 (3) | 4 (0) | 9 (9) | saif 61 |
| rtlopt_sub_8bit | small | | **all arms** | 80 | 6 | 6 | 11 | 7 | 12 | |

## 5. Retained candidates on the default-basis designs that are power-only (item 1: become noise under (a))

Currently retained on the 13 default-basis designs: 1186; power-only among them: **17** (under (a): noise 15, absorbed 2); with a power gain above the materiality threshold: 17.

| design | B0 | B1_E4 | B2 | M | total |
|---|---|---|---|---|---|
| cktevo_risc__btb | 10 | 3 | 3 | 1 | 17 |
| **per arm** | 10 | 3 | 3 | 1 | 17 |

Default-basis pairs on SAIF-basis designs (the candidate's own record carries no SAIF power; power excluded for them under (a) as well): 689 pairs on 11 designs, currently retained 221, retained under (a) 239.

| design | default-basis pairs | retained (current) | retained (a) |
|---|---|---|---|
| cktevo_ethmac__eth_cop | 46 | 3 | 5 |
| cktevo_mem_ctrl__mc_adr_sel | 67 | 28 | 11 |
| drrtl_UART | 122 | 0 | 0 |
| drrtl_communication | 23 | 4 | 3 |
| drrtl_router | 25 | 2 | 2 |
| rtlopt_alu_64bit | 72 | 1 | 19 |
| rtlopt_calculation | 51 | 41 | 41 |
| rtlopt_decoder_8bit | 59 | 58 | 58 |
| rtlopt_divider_8bit | 66 | 40 | 40 |
| rtlopt_register | 91 | 32 | 48 |
| rtlopt_sub_32bit | 67 | 12 | 12 |

## 6. B0: Yosys-caliber label against rule A at E4 (paper_sec3.md §G (iii))

Proven B0 candidates 1987 (E4 pending / DC rejected rows stay as states).

| Y label \| E4 label | current | (a) |
|---|---|---|
| improved|absorbed | 34 | 34 |
| improved|absorbed_identical | 143 | 143 |
| improved|dc_rejected | 20 | 20 |
| improved|e4_pending | 105 | 105 |
| improved|harmful | 183 | 221 |
| improved|noise | 36 | 56 |
| improved|retained | 645 | 647 |
| improved|tradeoff | 449 | 389 |
| no_gain|absorbed | 17 | 17 |
| no_gain|absorbed_identical | 112 | 112 |
| no_gain|dc_rejected | 2 | 2 |
| no_gain|e4_pending | 41 | 41 |
| no_gain|harmful | 57 | 60 |
| no_gain|noise | 10 | 19 |
| no_gain|retained | 39 | 47 |
| no_gain|tradeoff | 84 | 64 |
| none|retained | 3 | 3 |
| none|tradeoff | 7 | 7 |

Per metric (version (b)): Y label -> rule-A label on that metric alone.

- **area**: improved -> absorbed 34, improved -> absorbed_identical 143, improved -> harmful 485, improved -> noise 184, improved -> retained 644, no_gain -> absorbed 17, no_gain -> absorbed_identical 112, no_gain -> harmful 104, no_gain -> noise 50, no_gain -> retained 36, none -> retained 10, pending 168
- **power**: improved -> absorbed (default) 29, improved -> absorbed (saif) 17, improved -> absorbed_identical (default) 40, improved -> absorbed_identical (saif) 103, improved -> harmful (default) 167, improved -> harmful (saif) 155, improved -> noise (default) 321, improved -> noise (saif) 65, improved -> retained (default) 279, improved -> retained (saif) 314, no_gain -> absorbed (default) 18, no_gain -> absorbed (saif) 1, no_gain -> absorbed_identical (default) 106, no_gain -> absorbed_identical (saif) 6, no_gain -> harmful (default) 74, no_gain -> harmful (saif) 5, no_gain -> noise (default) 68, no_gain -> noise (saif) 9, no_gain -> retained (default) 30, no_gain -> retained (saif) 2, none -> retained (default) 7, none -> retained (saif) 3, pending 168
- **wns**: improved -> absorbed 42, improved -> absorbed_identical 143, improved -> harmful 215, improved -> noise 254, improved -> retained 836, no_gain -> absorbed 18, no_gain -> absorbed_identical 112, no_gain -> harmful 55, no_gain -> noise 36, no_gain -> retained 98, none -> harmful 7, none -> retained 3, pending 168

## 8. Class definitions and the re-encoding sub-population (item 4)

- (b): class (b), latency-preserving coding / structural refactor: V2 identical every cycle (no lock-step offset), no (d) evidence (no operator family gained, combinational depth ratio below classify.d_depth_ratio), and either the register names / clocked targets change with the flip-flop bit count unchanged, or the flip-flop bits change while the number of register cells is unchanged (bit widths may change inside the same cells) — evidence tag "flip-flop bits N -> M in the same register cells (widths), latency unchanged"
- (c1): class (c1), latency-preserving sequential restructuring: V2 identical every cycle, no (d) evidence, and the flip-flop bits AND the number of register cells both change (ff_c != ff_d and reg_cells_c != reg_cells_d, registers cross logic, are duplicated, merged or removed) — evidence tag "flip-flop bits N -> M and register cells K -> L with identical latency (no offset)"
- counting: flip-flop bits and register cells counted by Yosys after `proc; flatten; opt` (memories included); precedence in classify(): offset > 0 -> c2; operator family gained or depth ratio -> d; bits and registers unchanged -> a; bits and cells changed -> c1; else b
- source: src/classify/rules.py classify() (RULES_VERSION 2, DECISIONS 2026-09-14 / 2026-09-15); docs/spec/04-classifier-diagnoser.md §A.1

| population | n | class (b) all | (b) with flip-flop count changed (re-encodings) | (b) flip-flop count unchanged | (c1) all |
|---|---|---|---|---|---|
| Phase 4 objects (proven, with E4) | 255 | 38 / 109 = 34.9 % | 32 / 38 = 84.2 % | 6 / 71 = 8.5 % | 20 / 24 = 83.3 % |
| Phase 5 evaluated, all started tiers | 11341 | 1580 / 4323 = 36.5 % | 11 / 116 = 9.5 % | 1569 / 4207 = 37.3 % | 605 / 1657 = 36.5 % |
| Phase 5 evaluated, large tier | 1421 | 304 / 663 = 45.9 % | 1 / 1 = 100.0 % | 303 / 662 = 45.8 % | 12 / 47 = 25.5 % |
| Phase 5 evaluated, medium tier | 9802 | 1270 / 3578 = 35.5 % | 10 / 115 = 8.7 % | 1260 / 3463 = 36.4 % | 593 / 1610 = 36.8 % |
| Phase 5 evaluated, small tier | 118 | 6 / 82 = 7.3 % | 0 / 0 = — | 6 / 82 = 7.3 % | 0 / 0 = — |

Retained = rule A at E4 (the frozen phase4 floors), current version. The two FSM objects of the addendum: rtlopt_ticket_machine (c634baa4b8fa859): class b, in the re-encoding sub-population: True; rtlopt_fsm_encode (c92a0b6177cf6f6): class b, in the re-encoding sub-population: True.

## 9. mc_rf: D's E4 result across the rungs (item 5)

Design cktevo_mem_ctrl__mc_rf at Φ_main = 0.7 ns.

| rung | D area µm² (cells) | proven-perturbation records | records at D's area | D unique | δ range of the records vs D | distinct areas (n) |
|---|---|---|---|---|---|---|
| E1 | 3114.3 (1732) | 28 | 0 | yes | 1.30 % … 6.88 % | 3328.5 (1, 6.88 %); 3323.7 (1, 6.72 %); 3322.6 (1, 6.69 %); 3318.6 (1, 6.56 %); 3306.6 (1, 6.18 %); 3262.0 (1, 4.74 %); 3234.6 (12, 3.86 %); 3230.3 (1, 3.72 %); 3227.1 (1, 3.62 %); 3225.5 (1, 3.57 %); 3225.2 (1, 3.56 %); 3222.6 (1, 3.48 %); 3218.6 (1, 3.35 %); 3212.5 (1, 3.15 %); 3201.3 (1, 2.79 %); 3197.3 (1, 2.66 %); 3154.8 (1, 1.30 %) |
| E2 | 2652.6 (1087) | 28 | 0 | yes | 3.19 % … 6.10 % | 2814.3 (1, 6.10 %); 2774.1 (2, 4.58 %); 2768.5 (1, 4.37 %); 2756.8 (13, 3.93 %); 2755.8 (4, 3.89 %); 2755.5 (3, 3.88 %); 2754.4 (1, 3.84 %); 2748.8 (1, 3.63 %); 2737.4 (1, 3.20 %); 2737.1 (1, 3.19 %) |
| E3 | 3580.6 (1287) | 28 | 0 | yes | 0.56 % … 14.57 % | 4102.3 (3, 14.57 %); 4038.7 (13, 12.79 %); 4037.1 (4, 12.75 %); 3880.7 (1, 8.38 %); 3869.0 (1, 8.05 %); 3826.9 (1, 6.88 %); 3764.7 (1, 5.14 %); 3764.4 (1, 5.13 %); 3656.2 (1, 2.11 %); 3622.1 (1, 1.16 %); 3600.8 (1, 0.56 %) |
| E4 | 2373.5 (937) | 28 | 0 | yes | 17.37 % … 18.66 % | 2816.4 (15, 18.66 %); 2816.1 (7, 18.65 %); 2815.6 (1, 18.63 %); 2812.7 (1, 18.50 %); 2806.6 (1, 18.24 %); 2785.8 (3, 17.37 %) |

E4: 29 records including D; within 1 µm² of 2 816.4 µm²: 23; on the 17.4 % plateau: 3; between: 2.

## S. Sources

- **Phase 5 scan**: scripts/report_c1.scan_phase5: every non-superseded Phase 5 candidate of the started tiers; evaluated = proven with an ok E4 record; duplicates (label duplicate) collapsed
- **class tables**: class_final × rule-A label per version; retained rate = retained / evaluated of the class; material = retained candidates with a gain above the materiality threshold on some metric of the version and none below
- **B0 Yosys vs E4**: candidates.label of the B0 arm (improved = a positive Y-caliber component, Yosys + OpenSTA, spec 05 §5) against the rule-A label of the same proven candidate's E4 record under each version; proven candidates without an E4 record are pending (e4_pending / dc_rejected as in paper_sec3.md §G)
- **item 4**: rules v2 as implemented (src/classify/rules.py classify(); docs/spec/04 §A.1): Phase 4 objects from reports/data/phase4_exp1.json objects[] (verdict proven / proven_sim_only, label = rule A at E4 under the frozen floors) joined with candidates.subtags_json; Phase 5 evaluated candidates from the scan with their normalised evidence tags (report_c1.norm_subtag)
- **item 5**: evaluations of cktevo_mem_ctrl__mc_rf at Φ_main (designs.phi_main_ns_nangate45): D = is_baseline 1, pert_id / cand_id NULL, status ok (SAIF-backed record preferred, latest among equals); perturbations = status ok records joined with perturbations.seq_status in (proven, proven_rename); one record per (perturbation, config) counted — distinct areas with their counts
