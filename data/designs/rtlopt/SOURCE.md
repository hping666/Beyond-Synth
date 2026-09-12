# rtlopt — source record (Phase 1.1)

- Source: https://github.com/hkust-zhiyao/RTL-OPT
- Pinned commit: `25e4bbe052f02fde7f34eb8c3e37a7656e7dce20` (local checkout at `data/sources/RTL-OPT`: verified)
- License: MIT
- Note: the paper's anonymous repository (anonymous.4open.science/r/RTL-OPT-20C5) reports repository_expired (HTTP 410, 2026-09-12); this is the authors' public release with 40 pairs
- Staged designs: 40; skipped: 0

Staged copies (`rtl/`, `tb/`, `reference/`, `samples/`) are rebuilt by `scripts/stage_designs.py` and are not versioned; `design.json` carries top, ports, provenance and sha256 of every copy.

## Designs

| design_id | top | loc | clocks | tb | reference | source paths |
|---|---|---|---|---|---|---|
| rtlopt_add_sub | add_sub | 14 | - | - | y | benchmark/add_sub/add_sub.v, benchmark/add_sub_ref/add_sub_ref.v |
| rtlopt_adder | adder | 20 | clk | - | y | benchmark/adder/adder.v, benchmark/adder_ref/adder_ref.v |
| rtlopt_adder_carry | adder_carry | 48 | - | - | y | benchmark/adder_carry/adder_carry.v, benchmark/adder_carry_ref/adder_carry_ref.v |
| rtlopt_adder_select | adder_select | 14 | - | - | y | benchmark/adder_select/adder_select.v, benchmark/adder_select_ref/adder_select_ref.v |
| rtlopt_addr_calcu | addr_calcu | 23 | - | - | y | benchmark/addr_calcu/addr_calcu.v, benchmark/addr_calcu_ref/addr_calcu_ref.v |
| rtlopt_alu_64bit | alu_64bit | 19 | - | - | y | benchmark/alu_64bit/alu_64bit.v, benchmark/alu_64bit_ref/alu_64bit_ref.v |
| rtlopt_alu_8bit | alu_8bit | 23 | - | - | y | benchmark/alu_8bit/alu_8bit.v, benchmark/alu_8bit_ref/alu_8bit_ref.v |
| rtlopt_calculation | calculation | 22 | - | - | y | benchmark/calculation/calculation.v, benchmark/calculation_ref/calculation_ref.v |
| rtlopt_comparator | comparator | 28 | - | - | y | benchmark/comparator/comparator.v, benchmark/comparator_ref/comparator_ref.v |
| rtlopt_comparator_16bit | comparator_16bit | 14 | - | - | y | benchmark/comparator_16bit/comparator_16bit.v, benchmark/comparator_16bit_ref/comparator_16bit_ref.v |
| rtlopt_comparator_2bit | comparator_2bit | 8 | - | - | y | benchmark/comparator_2bit/comparator_2bit.v, benchmark/comparator_2bit_ref/comparator_2bit_ref.v |
| rtlopt_comparator_4bit | comparator_4bit | 14 | - | - | y | benchmark/comparator_4bit/comparator_4bit.v, benchmark/comparator_4bit_ref/comparator_4bit_ref.v |
| rtlopt_comparator_8bit | comparator_8bit | 23 | - | - | y | benchmark/comparator_8bit/comparator_8bit.v, benchmark/comparator_8bit_ref/comparator_8bit_ref.v |
| rtlopt_decoder_6bit | decoder_6bit | 12 | - | - | y | benchmark/decoder_6bit/decoder_6bit.v, benchmark/decoder_6bit_ref/decoder_6bit_ref.v |
| rtlopt_decoder_8bit | decoder_8bit | 12 | - | - | y | benchmark/decoder_8bit/decoder_8bit.v, benchmark/decoder_8bit_ref/decoder_8bit_ref.v |
| rtlopt_divider_16bit | divider_16bit | 37 | - | - | y | benchmark/divider_16bit/divider_16bit.v, benchmark/divider_16bit_ref/divider_16bit_ref.v |
| rtlopt_divider_32bit | divider_32bit | 37 | - | - | y | benchmark/divider_32bit/divider_32bit.v, benchmark/divider_32bit_ref/divider_32bit_ref.v |
| rtlopt_divider_4bit | divider_4bit | 36 | - | - | y | benchmark/divider_4bit/divider_4bit.v, benchmark/divider_4bit_ref/divider_4bit_ref.v |
| rtlopt_divider_8bit | divider_8bit | 36 | - | - | y | benchmark/divider_8bit/divider_8bit.v, benchmark/divider_8bit_ref/divider_8bit_ref.v |
| rtlopt_fsm | fsm | 60 | clk | - | y | benchmark/fsm/fsm.v, benchmark/fsm_ref/fsm_ref.v |
| rtlopt_fsm_encode | fsm_encode | 85 | clk | - | y | benchmark/fsm_encode/fsm_encode.v, benchmark/fsm_encode_ref/fsm_encode_ref.v |
| rtlopt_gray | gray | 82 | clk | - | y | benchmark/gray/gray.v, benchmark/gray_ref/gray_ref.v |
| rtlopt_mac | mac | 25 | clk | - | y | benchmark/mac/mac.v, benchmark/mac_ref/mac_ref.v |
| rtlopt_mul | mul | 12 | clk | - | y | benchmark/mul/mul.v, benchmark/mul_ref/mul_ref.v |
| rtlopt_mul_const | mul_const | 17 | - | - | y | benchmark/mul_const/mul_const.v, benchmark/mul_const_ref/mul_const_ref.v |
| rtlopt_mul_subexpression | mul_subexpression | 37 | - | - | y | benchmark/mul_subexpression/mul_subexpression.v, benchmark/mul_subexpression_ref/mul_subexpression_ref.v |
| rtlopt_mult_if | mult_if | 39 | - | - | y | benchmark/mult_if/mult_if.v, benchmark/mult_if_ref/mult_if_ref.v |
| rtlopt_mux_4to1_16bit | mux_4to1_16bit | 22 | - | - | y | benchmark/mux_4to1_16bit/mux_4to1_16bit.v, benchmark/mux_4to1_16bit_ref/mux_4to1_16bit_ref.v |
| rtlopt_mux_4to1_64bit | mux_4to1_64bit | 22 | - | - | y | benchmark/mux_4to1_64bit/mux_4to1_64bit.v, benchmark/mux_4to1_64bit_ref/mux_4to1_64bit_ref.v |
| rtlopt_mux_dead | mux_dead | 54 | - | - | y | benchmark/mux_dead/mux_dead.v, benchmark/mux_dead_ref/mux_dead_ref.v |
| rtlopt_mux_encode | mux_encode | 21 | - | - | y | benchmark/mux_encode/mux_encode.sv, benchmark/mux_encode_ref/mux_encode_ref.sv |
| rtlopt_mux_large | mux_large | 23 | - | - | y | benchmark/mux_large/mux_large.v, benchmark/mux_large_ref/mux_large_ref.v |
| rtlopt_register | register | 64 | clk | - | y | benchmark/register/register.v, benchmark/register_ref/register_ref.v |
| rtlopt_saturating_add | saturating_add | 17 | clk | - | y | benchmark/saturating_add/saturating_add.v, benchmark/saturating_add_ref/saturating_add_ref.v |
| rtlopt_selector | selector | 17 | clk | - | y | benchmark/selector/selector.v, benchmark/selector_ref/selector_ref.v |
| rtlopt_sub_16bit | sub_16bit | 12 | - | - | y | benchmark/sub_16bit/sub_16bit.v, benchmark/sub_16bit_ref/sub_16bit_ref.v |
| rtlopt_sub_32bit | sub_32bit | 24 | - | - | y | benchmark/sub_32bit/sub_32bit.v, benchmark/sub_32bit_ref/sub_32bit_ref.v |
| rtlopt_sub_4bit | sub_4bit | 25 | - | - | y | benchmark/sub_4bit/sub_4bit.v, benchmark/sub_4bit_ref/sub_4bit_ref.v |
| rtlopt_sub_8bit | sub_8bit | 25 | - | - | y | benchmark/sub_8bit/sub_8bit.v, benchmark/sub_8bit_ref/sub_8bit_ref.v |
| rtlopt_ticket_machine | ticket_machine | 135 | clk | - | y | benchmark/ticket_machine/ticket_machine.v, benchmark/ticket_machine_ref/ticket_machine_ref.v |
