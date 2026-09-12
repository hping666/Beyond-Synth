# drrtl — source record (Phase 1.1)

- Source: https://github.com/hkust-zhiyao/DR_RTL
- Pinned commit: `62b95a57223e8fb187d8b8ec1dcb3d193ef20c6b` (local checkout at `data/sources/Dr_RTL`: verified)
- License: unspecified (no LICENSE file in the repository)
- Note: -
- Staged designs: 20; skipped: 0

Staged copies (`rtl/`, `tb/`, `reference/`, `samples/`) are rebuilt by `scripts/stage_designs.py` and are not versioned; `design.json` carries top, ports, provenance and sha256 of every copy.

## Designs

| design_id | top | loc | clocks | tb | reference | source paths |
|---|---|---|---|---|---|---|
| drrtl_DSP | DSP | 165 | clk | y | - | rtl_dataset/DSP.v0.v |
| drrtl_FIFO | fifo | 383 | clk_in | - | - | rtl_dataset/FIFO.v0.v |
| drrtl_LSTM | lstm_cell | 135 | clk | y | - | rtl_dataset/LSTM.v0.v |
| drrtl_SPI | spi | 441 | clk | - | - | rtl_dataset/SPI.v0.v |
| drrtl_UART | uart_top_design | 447 | clk | - | - | rtl_dataset/UART.v0.v |
| drrtl_aes | key_expansion_128aes | 374 | clk | - | - | rtl_dataset/aes.v0.sv |
| drrtl_arm_cpu1 | arm9_compatiable_code | 1870 | clk | - | - | rtl_dataset/arm_cpu1.v0.v |
| drrtl_arm_cpu2 | risclite_mx | 1450 | clk | - | - | rtl_dataset/arm_cpu2.v0.v |
| drrtl_communication | sync_serial_communication_tx_rx | 225 | clk | - | - | rtl_dataset/communication.v0.v |
| drrtl_controller | control_unit | 546 | clk | - | - | rtl_dataset/controller.v0.v |
| drrtl_cpu_fsm | mini_cpu | 354 | clk | - | - | rtl_dataset/cpu_fsm.v0.v |
| drrtl_cpu_pipe | dcpu16_cpu | 927 | clk | - | - | rtl_dataset/cpu_pipe.v0.v |
| drrtl_datapath | datapath | 1065 | clk | - | - | rtl_dataset/datapath.v0.v |
| drrtl_i2c | i2c_master_top | 915 | wb_clk_i | - | - | rtl_dataset/i2c.v0.v |
| drrtl_pcie | top | 923 | clk | - | - | rtl_dataset/pcie.v0.v |
| drrtl_router | router_top | 594 | clk | - | - | rtl_dataset/router.v0.v |
| drrtl_simple_spi | simple_spi_top | 463 | clk_i | - | - | rtl_dataset/simple_spi.v0.v |
| drrtl_ticket_machine | ticket_machine | 134 | clk | - | - | rtl_dataset/ticket_machine.v0.v |
| drrtl_tv80 | tv80s | 4616 | clk | - | - | rtl_dataset/tv80.v0.v |
| drrtl_vending_machine | vending_machine | 128 | clk | - | - | rtl_dataset/vending_machine.v0.v |
