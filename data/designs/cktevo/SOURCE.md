# cktevo — source record (Phase 1.1)

- Source: https://github.com/cure-lab/cktevo
- Pinned commit: `2f1abe75cc48437378bd8832517048ba64d53149` (local checkout at `data/sources/cktevo`: verified)
- License: unspecified at repository level (the OpenCores cores carry their own LGPL/GPL headers)
- Note: -
- Staged designs: 83; skipped: 0

Staged copies (`rtl/`, `tb/`, `reference/`, `samples/`) are rebuilt by `scripts/stage_designs.py` and are not versioned; `design.json` carries top, ports, provenance and sha256 of every copy.

## Designs

| design_id | top | loc | clocks | tb | reference | source paths |
|---|---|---|---|---|---|---|
| cktevo_ethmac__eth_cop | eth_cop | 398 | - | - | - | benchmark/ethmac/eth_cop.v |
| cktevo_ethmac__eth_fifo | eth_fifo | 186 | clk | - | - | benchmark/ethmac/eth_fifo.v |
| cktevo_ethmac__eth_maccontrol | eth_maccontrol | 1030 | - | - | - | benchmark/ethmac/eth_maccontrol.v, benchmark/ethmac/eth_receivecontrol.v, benchmark/ethmac/eth_transmitcontrol.v |
| cktevo_ethmac__eth_macstatus | eth_macstatus | 423 | - | - | - | benchmark/ethmac/eth_macstatus.v |
| cktevo_ethmac__eth_miim | eth_miim | 872 | - | - | - | benchmark/ethmac/eth_miim.v, benchmark/ethmac/eth_clockgen.v, benchmark/ethmac/eth_outputcontrol.v ... |
| cktevo_ethmac__eth_receivecontrol | eth_receivecontrol | 437 | - | - | - | benchmark/ethmac/eth_receivecontrol.v |
| cktevo_ethmac__eth_registers | eth_registers | 1292 | - | - | - | benchmark/ethmac/eth_registers.v, benchmark/ethmac/eth_register.v |
| cktevo_ethmac__eth_rxaddrcheck | eth_rxaddrcheck | 214 | - | - | - | benchmark/ethmac/eth_rxaddrcheck.v |
| cktevo_ethmac__eth_rxcounters | eth_rxcounters | 217 | - | - | - | benchmark/ethmac/eth_rxcounters.v |
| cktevo_ethmac__eth_rxethmac | eth_rxethmac | 1204 | - | - | - | benchmark/ethmac/eth_rxethmac.v, benchmark/ethmac/eth_crc.v, benchmark/ethmac/eth_rxaddrcheck.v ... |
| cktevo_ethmac__eth_rxstatem | eth_rxstatem | 193 | - | - | - | benchmark/ethmac/eth_rxstatem.v |
| cktevo_ethmac__eth_spram_256x32 | eth_spram_256x32 | 299 | clk | - | - | benchmark/ethmac/eth_spram_256x32.v |
| cktevo_ethmac__eth_transmitcontrol | eth_transmitcontrol | 324 | - | - | - | benchmark/ethmac/eth_transmitcontrol.v |
| cktevo_ethmac__eth_txcounters | eth_txcounters | 219 | - | - | - | benchmark/ethmac/eth_txcounters.v |
| cktevo_ethmac__eth_txethmac | eth_txethmac | 1273 | - | - | - | benchmark/ethmac/eth_txethmac.v, benchmark/ethmac/eth_crc.v, benchmark/ethmac/eth_random.v ... |
| cktevo_ethmac__eth_txstatem | eth_txstatem | 282 | - | - | - | benchmark/ethmac/eth_txstatem.v |
| cktevo_ethmac__eth_wishbone | eth_wishbone | 3161 | - | - | - | benchmark/ethmac/eth_wishbone.v, benchmark/ethmac/eth_fifo.v, benchmark/ethmac/eth_spram_256x32.v |
| cktevo_hsm__G16Inv2SharesDep | G16Inv2SharesDep | 273 | - | - | - | benchmark/hsm/G16Inv2SharesDep.v, benchmark/hsm/G4Mul2SharesDepMul.v, benchmark/hsm/G4ScaleN.v ... |
| cktevo_hsm__G256Inv2Shares5Stages | G256Inv2Shares5Stages | 688 | - | - | - | benchmark/hsm/G256Inv2Shares5Stages.v, benchmark/hsm/G16Inv2SharesDep.v, benchmark/hsm/G16Mul2SharesDepMul.v ... |
| cktevo_hsm__MixColumns | MixColumns | 132 | - | - | - | benchmark/hsm/MixColumns.v |
| cktevo_hsm__hsm | hsm | 2503 | - | - | - | benchmark/hsm/HSM.v, benchmark/hsm/AddRoundKey.v, benchmark/hsm/MixColumns.v ... |
| cktevo_mem_ctrl__mc_adr_sel | mc_adr_sel | 392 | clk | - | - | benchmark/mem_ctrl/mc_adr_sel.v, benchmark/mem_ctrl/mc_incn_r.v |
| cktevo_mem_ctrl__mc_cs_rf | mc_cs_rf | 276 | clk | - | - | benchmark/mem_ctrl/mc_cs_rf.v |
| cktevo_mem_ctrl__mc_dp | mc_dp | 374 | clk | - | - | benchmark/mem_ctrl/mc_dp.v, benchmark/mem_ctrl/mc_rd_fifo.v |
| cktevo_mem_ctrl__mc_mem_if | mc_mem_if | 362 | clk | - | - | benchmark/mem_ctrl/mc_mem_if.v |
| cktevo_mem_ctrl__mc_obct | mc_obct | 236 | clk | - | - | benchmark/mem_ctrl/mc_obct.v |
| cktevo_mem_ctrl__mc_obct_top | mc_obct_top | 662 | clk | - | - | benchmark/mem_ctrl/mc_obct_top.v, benchmark/mem_ctrl/mc_obct.v |
| cktevo_mem_ctrl__mc_refresh | mc_refresh | 210 | clk | - | - | benchmark/mem_ctrl/mc_refresh.v |
| cktevo_mem_ctrl__mc_rf | mc_rf | 1112 | clk | - | - | benchmark/mem_ctrl/mc_rf.v, benchmark/mem_ctrl/mc_cs_rf.v |
| cktevo_mem_ctrl__mc_timing | mc_timing | 1735 | clk | - | - | benchmark/mem_ctrl/mc_timing.v |
| cktevo_mem_ctrl__mc_wb_if | mc_wb_if | 252 | clk | - | - | benchmark/mem_ctrl/mc_wb_if.v |
| cktevo_nn_engine__FADD711 | FADD711 | 223 | CLK | - | - | benchmark/nn_engine/FADD711.v |
| cktevo_nn_engine__FMUL711 | FMUL711 | 182 | CLK | - | - | benchmark/nn_engine/FMUL711.v |
| cktevo_nn_engine__dualDendRC_H7 | dualDendRC_H7 | 1067 | CLK | - | - | benchmark/nn_engine/dualDendRC_H7.v, benchmark/nn_engine/FMUL711.v, benchmark/nn_engine/tauRom_H7.v |
| cktevo_nn_engine__rates_256x4096 | rates_256x4096 | 575 | CLK | - | - | benchmark/nn_engine/rates_256x4096.v, benchmark/nn_engine/UltraTDP64x4096_4.v, benchmark/nn_engine/ultraRAMx72_TDP.v |
| cktevo_nn_engine__spikeLayer8_H7 | spikeLayer8_H7 | 2705 | CLK | - | - | benchmark/nn_engine/spikeLayer8_H7.v, benchmark/nn_engine/spikeNeuron8_H7.v, benchmark/nn_engine/FADD711.v ... |
| cktevo_nn_engine__spikeNeuron8_H7 | spikeNeuron8_H7 | 1674 | CLK | - | - | benchmark/nn_engine/spikeNeuron8_H7.v, benchmark/nn_engine/FADD711.v, benchmark/nn_engine/dualDendRC_H7.v ... |
| cktevo_nn_engine__tauRom_H7 | tauRom_H7 | 651 | CLK | - | - | benchmark/nn_engine/tauRom_H7.v |
| cktevo_nn_engine__thresholds_128x4096 | thresholds_128x4096 | 340 | CLK | - | - | benchmark/nn_engine/thresholds_128x4096.v, benchmark/nn_engine/ultraRAMx72_TDP.v |
| cktevo_nn_engine__ultraRAMx72_TDP | ultraRAMx72_TDP | 169 | CLK | - | - | benchmark/nn_engine/ultraRAMx72_TDP.v |
| cktevo_nn_engine__weights_1024x4096 | weights_1024x4096 | 640 | CLK | - | - | benchmark/nn_engine/weights_1024x4096.v, benchmark/nn_engine/UltraTDP64x4096_16.v, benchmark/nn_engine/ultraRAMx72_TDP.v |
| cktevo_risc__btb | btb | 453 | clk | - | - | benchmark/risc/btb.v, benchmark/risc/btb_array.v |
| cktevo_risc__cache_datapath | cache_datapath | 175 | clk | - | - | benchmark/risc/cache_datapath.v, benchmark/risc/array.v, benchmark/risc/data_array.v |
| cktevo_risc__cache_sys | cache_sys | 2954 | clk | - | - | benchmark/risc/cache_sys.v, benchmark/risc/arbiter_control.v, benchmark/risc/arbiter_datapath.v ... |
| cktevo_risc__cacheline_adaptor | cacheline_adaptor | 175 | clk | - | - | benchmark/risc/cacheline_adaptor.v |
| cktevo_risc__control_rom | control_rom | 162 | - | - | - | benchmark/risc/control_rom.v |
| cktevo_risc__cpu | cpu | 2010 | clk | - | - | benchmark/risc/cpu.v, benchmark/risc/alu.v, benchmark/risc/bht.v ... |
| cktevo_risc__ewb | ewb | 177 | clk | - | - | benchmark/risc/ewb.v |
| cktevo_risc__forward_control_unit | forward_control_unit | 122 | - | - | - | benchmark/risc/forward_control_unit.v |
| cktevo_risc__l2_cache | l2_cache | 1335 | clk | - | - | benchmark/risc/l2_cache.v, benchmark/risc/ewb.v, benchmark/risc/l2_cache_control.v ... |
| cktevo_risc__l2_cache_control | l2_cache_control | 454 | clk | - | - | benchmark/risc/l2_cache_control.v, benchmark/risc/perf_counter.v |
| cktevo_risc__l2_cache_datapath | l2_cache_datapath | 454 | clk | - | - | benchmark/risc/l2_cache_datapath.v, benchmark/risc/l2_array.v, benchmark/risc/l2_data_array.v |
| cktevo_risc__p_i_cache | p_i_cache | 887 | clk | - | - | benchmark/risc/p_i_cache.v, benchmark/risc/p_i_cache_control.v, benchmark/risc/p_i_cache_metadata_check.v ... |
| cktevo_risc__p_i_cache_control | p_i_cache_control | 287 | clk | - | - | benchmark/risc/p_i_cache_control.v, benchmark/risc/perf_counter.v |
| cktevo_risc__p_i_cache_metadata_check | p_i_cache_metadata_check | 365 | clk | - | - | benchmark/risc/p_i_cache_metadata_check.v, benchmark/risc/l2_array.v, benchmark/risc/l2_data_array.v |
| cktevo_risc__stall_control_unit | stall_control_unit | 307 | - | - | - | benchmark/risc/stall_control_unit.v |
| cktevo_sdc_ctrl__sd_cmd_master | sd_cmd_master | 152 | clock | - | - | benchmark/sdc_ctrl/sd_cmd_master.v |
| cktevo_sdc_ctrl__sd_cmd_serial_host | sd_cmd_serial_host | 263 | clock | - | - | benchmark/sdc_ctrl/sd_cmd_serial_host.v |
| cktevo_sdc_ctrl__sd_data_master | sd_data_master | 150 | clock | - | - | benchmark/sdc_ctrl/sd_data_master.v |
| cktevo_sdc_ctrl__sd_data_serial_host | sd_data_serial_host | 311 | clock | - | - | benchmark/sdc_ctrl/sd_data_serial_host.v |
| cktevo_sdc_ctrl__sdc_controller | sdc_controller | 1545 | clock | - | - | benchmark/sdc_ctrl/axi_sdc_controller.v, benchmark/sdc_ctrl/sd_cmd_master.v, benchmark/sdc_ctrl/sd_cmd_serial_host.v ... |
| cktevo_simple_cpu__simple_cpu | simple_cpu | 946 | clk | - | - | benchmark/simple_cpu/Computer.v, benchmark/simple_cpu/ALU.v, benchmark/simple_cpu/ALUMUX.v ... |
| cktevo_spi__spi | spi | 483 | clk | - | - | benchmark/spi/spi_top.v, benchmark/spi/spi_clgen.v, benchmark/spi/spi_shift_in.v ... |
| cktevo_usb__usbf_biu | usbf_biu | 469 | - | - | - | benchmark/usb/usbf_biu.v, benchmark/usb/usbf_dffs.v |
| cktevo_usb__usbf_core | usbf_core | 1734 | clk_i | - | - | benchmark/usb/usbf_core.v, benchmark/usb/usbf_sie_rx.v, benchmark/usb/usbf_sie_tx.v ... |
| cktevo_usb__usbf_csr | usbf_csr | 1109 | - | - | - | benchmark/usb/usbf_csr.v, benchmark/usb/usbf_dffs.v |
| cktevo_usb__usbf_epu | usbf_epu | 305 | - | - | - | benchmark/usb/usbf_epu.v, benchmark/usb/usbf_sie_ep.v |
| cktevo_usb__usbf_fifo | usbf_fifo | 248 | clk_i | - | - | benchmark/usb/usbf_fifo.v |
| cktevo_usb__usbf_sie_ep | usbf_sie_ep | 179 | clk_i | - | - | benchmark/usb/usbf_sie_ep.v |
| cktevo_usb__usbf_sie_rx | usbf_sie_rx | 521 | clk_i | - | - | benchmark/usb/usbf_sie_rx.v, benchmark/usb/usbf_crc16.v |
| cktevo_usb__usbf_sie_tx | usbf_sie_tx | 387 | clk_i | - | - | benchmark/usb/usbf_sie_tx.v, benchmark/usb/usbf_crc16.v |
| cktevo_usb__usbf_sync | usbf_sync | 905 | - | - | - | benchmark/usb/usbf_sync.v, benchmark/usb/usbf_sync_utilities.v, benchmark/usb/usbf_dffs.v |
| cktevo_usb__usbf_ulpi_wrapper | usbf_ulpi_wrapper | 423 | - | - | - | benchmark/usb/usbf_ulpi_wrapper.v |
| cktevo_vga_enh__generic_dpram | generic_dpram | 515 | - | - | - | benchmark/vga_enh/generic_dpram.v |
| cktevo_vga_enh__generic_spram | generic_spram | 410 | clk | - | - | benchmark/vga_enh/generic_spram.v |
| cktevo_vga_enh__vga_colproc | vga_colproc | 510 | clk | - | - | benchmark/vga_enh/vga_colproc.v |
| cktevo_vga_enh__vga_curproc | vga_curproc | 724 | clk | - | - | benchmark/vga_enh/vga_curproc.v, benchmark/vga_enh/generic_spram.v |
| cktevo_vga_enh__vga_fifo | vga_fifo | 259 | clk | - | - | benchmark/vga_enh/vga_fifo.v |
| cktevo_vga_enh__vga_fifo_dc | vga_fifo_dc | 749 | - | - | - | benchmark/vga_enh/vga_fifo_dc.v, benchmark/vga_enh/generic_dpram.v |
| cktevo_vga_enh__vga_pgen | vga_pgen | 2545 | clk_i | - | - | benchmark/vga_enh/vga_pgen.v, benchmark/vga_enh/vga_clkgen.v, benchmark/vga_enh/vga_colproc.v ... |
| cktevo_vga_enh__vga_vtim | vga_vtim | 179 | clk | - | - | benchmark/vga_enh/vga_vtim.v |
| cktevo_vga_enh__vga_wb_master | vga_wb_master | 730 | clk_i | - | - | benchmark/vga_enh/vga_wb_master.v, benchmark/vga_enh/vga_fifo.v |
| cktevo_vga_enh__vga_wb_slave | vga_wb_slave | 605 | clk_i | - | - | benchmark/vga_enh/vga_wb_slave.v, benchmark/vga_enh/vga_cur_cregs.v |
