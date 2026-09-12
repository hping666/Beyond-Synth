###################################################################

# Created by write_sdc on Sat Sep 12 13:29:08 2026

###################################################################
set sdc_version 2.1

set_units -time ns -resistance MOhm -capacitance fF -voltage V -current mA
set_max_fanout 20 [current_design]
set_driving_cell -lib_cell BUF_X1 [get_ports rst_n]
set_driving_cell -lib_cell BUF_X1 [get_ports {data_in[7]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {data_in[6]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {data_in[5]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {data_in[4]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {data_in[3]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {data_in[2]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {data_in[1]}]
set_driving_cell -lib_cell BUF_X1 [get_ports {data_in[0]}]
set_driving_cell -lib_cell BUF_X1 [get_ports valid_in]
create_clock [get_ports clk]  -period 2  -waveform {0 1}
set_input_delay -clock clk  0.4  [get_ports rst_n]
set_input_delay -clock clk  0.4  [get_ports {data_in[7]}]
set_input_delay -clock clk  0.4  [get_ports {data_in[6]}]
set_input_delay -clock clk  0.4  [get_ports {data_in[5]}]
set_input_delay -clock clk  0.4  [get_ports {data_in[4]}]
set_input_delay -clock clk  0.4  [get_ports {data_in[3]}]
set_input_delay -clock clk  0.4  [get_ports {data_in[2]}]
set_input_delay -clock clk  0.4  [get_ports {data_in[1]}]
set_input_delay -clock clk  0.4  [get_ports {data_in[0]}]
set_input_delay -clock clk  0.4  [get_ports valid_in]
set_output_delay -clock clk  0.4  [get_ports valid_out]
set_output_delay -clock clk  0.4  [get_ports {data_out[9]}]
set_output_delay -clock clk  0.4  [get_ports {data_out[8]}]
set_output_delay -clock clk  0.4  [get_ports {data_out[7]}]
set_output_delay -clock clk  0.4  [get_ports {data_out[6]}]
set_output_delay -clock clk  0.4  [get_ports {data_out[5]}]
set_output_delay -clock clk  0.4  [get_ports {data_out[4]}]
set_output_delay -clock clk  0.4  [get_ports {data_out[3]}]
set_output_delay -clock clk  0.4  [get_ports {data_out[2]}]
set_output_delay -clock clk  0.4  [get_ports {data_out[1]}]
set_output_delay -clock clk  0.4  [get_ports {data_out[0]}]
