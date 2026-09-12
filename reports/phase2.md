# Phase 2 report — noise floor, SEQ pilot, E4 runtime (Exp0)

Generated 2026-09-12 15:53 by scripts/report_phase.py (git 090be1299949, cfg 621834f01e87). Hidden-configuration floors (H1 / H2a / H2b / H5, H3) live in the hidden database and appear only in the hidden report after Phase 5.

## 1. Perturbation generator (PLAN 2.1)

179 designs of the sets; perturbations per type {'P1_rename': 556, 'P2_reorder': 389, 'P3_expr': 229, 'P4_ctrl': 224}; types not applicable {'P1_rename': 23, 'P2_reorder': 38, 'P3_expr': 93, 'P4_ctrl': 68}; designs Pyverilog cannot parse: 15 (cktevo_hsm__G16Inv2SharesDep, cktevo_hsm__G256Inv2Shares5Stages, cktevo_hsm__hsm, cktevo_nn_engine__thresholds_128x4096, cktevo_risc__btb, cktevo_risc__cpu, cktevo_risc__l2_cache_control, cktevo_risc__stall_control_unit, cktevo_sdc_ctrl__sdc_controller, drrtl_aes, drrtl_simple_spi, rtllm_adder_32bit, rtllm_multi_8bit, rtlrewriter_datapath__loop_tiling, rtlrewriter_datapath__multiplier_architecture).

SEQ gate (V1 -> V2 -> V3; only `proven` enters the floor):

| type | pending | proven | non-equivalence rate |
|---|---|---|---|
| P1_rename | 550 | 6 | 0.0% of 556 |
| P2_reorder | 382 | 5 | 0.0% of 387 |
| P3_expr | 228 | 1 | 0.0% of 229 |
| P4_ctrl | 221 | 2 | 0.0% of 223 |

## 2. Noise floor sigma_D (PLAN 2.3, visible configurations)

(not collected yet: scripts/phase2_noise.py collect)

## 3. E4 runtime (PLAN 2.5)

(no E4 baseline at Phi_main yet: run scripts/phase2_noise.py submit)

## 4. SEQ pilot (PLAN 2.4) and t_H3 / t_E4

(filled when the pilot and the hidden light runs are done; hidden timings are reported by the hidden worker as counts and seconds only)

## 5. Next steps

- G1: decide on the truncation if the median area floor exceeds the warning level.
- G2: SEQ fractions per class from the pilot.
- G3: screening recommendation from the E4 seconds and the cascade estimate.
