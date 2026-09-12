/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : W-2024.09-SP5-3
// Date      : Sat Sep 12 07:45:25 2026
/////////////////////////////////////////////////////////////


module SNPS_CLOCK_GATE_HIGH_verified_accu ( CLK, EN, ENCLK, TE );
  input CLK, EN, TE;
  output ENCLK;


  sky130_fd_sc_hd__sdlclkp_1 latch ( .CLK(CLK), .GATE(EN), .SCE(TE), .GCLK(
        ENCLK) );
endmodule


module verified_accu ( clk, rst_n, data_in, valid_in, valid_out, data_out );
  input [7:0] data_in;
  output [9:0] data_out;
  input clk, rst_n, valid_in;
  output valid_out;
  wire   end_cnt, N10, N11, N29, N30, N31, N32, N33, N34, N35, N36, N37, N38,
         net40, n7, n8, n9, n10, n11, n12, n13, n14, n15, n16, n17, n18, n19,
         n20, n21, n22, n23, n24, n25, n26, n27, n28, n29, n30, n31, n32, n33,
         n34, n35, n36, n37, n38;
  wire   [1:0] count;

  SNPS_CLOCK_GATE_HIGH_verified_accu clk_gate_count_reg ( .CLK(clk), .EN(n7), 
        .ENCLK(net40), .TE(n8) );
  sky130_fd_sc_hd__dfrtp_1 valid_out_reg ( .D(end_cnt), .CLK(clk), .RESET_B(
        rst_n), .Q(valid_out) );
  sky130_fd_sc_hd__dfrtp_1 \count_reg[0]  ( .D(N10), .CLK(net40), .RESET_B(
        rst_n), .Q(count[0]) );
  sky130_fd_sc_hd__dfrtp_1 \count_reg[1]  ( .D(N11), .CLK(net40), .RESET_B(
        rst_n), .Q(count[1]) );
  sky130_fd_sc_hd__dfrtp_1 \data_out_reg[0]  ( .D(N29), .CLK(net40), .RESET_B(
        rst_n), .Q(data_out[0]) );
  sky130_fd_sc_hd__dfrtp_1 \data_out_reg[1]  ( .D(N30), .CLK(net40), .RESET_B(
        rst_n), .Q(data_out[1]) );
  sky130_fd_sc_hd__dfrtp_1 \data_out_reg[2]  ( .D(N31), .CLK(net40), .RESET_B(
        rst_n), .Q(data_out[2]) );
  sky130_fd_sc_hd__dfrtp_1 \data_out_reg[3]  ( .D(N32), .CLK(net40), .RESET_B(
        rst_n), .Q(data_out[3]) );
  sky130_fd_sc_hd__dfrtp_1 \data_out_reg[4]  ( .D(N33), .CLK(net40), .RESET_B(
        rst_n), .Q(data_out[4]) );
  sky130_fd_sc_hd__dfrtp_1 \data_out_reg[5]  ( .D(N34), .CLK(net40), .RESET_B(
        rst_n), .Q(data_out[5]) );
  sky130_fd_sc_hd__dfrtp_1 \data_out_reg[6]  ( .D(N35), .CLK(net40), .RESET_B(
        rst_n), .Q(data_out[6]) );
  sky130_fd_sc_hd__dfrtp_1 \data_out_reg[7]  ( .D(N36), .CLK(net40), .RESET_B(
        rst_n), .Q(data_out[7]) );
  sky130_fd_sc_hd__dfrtp_1 \data_out_reg[8]  ( .D(N37), .CLK(net40), .RESET_B(
        rst_n), .Q(data_out[8]) );
  sky130_fd_sc_hd__dfrtp_1 \data_out_reg[9]  ( .D(N38), .CLK(net40), .RESET_B(
        rst_n), .Q(data_out[9]) );
  sky130_fd_sc_hd__clkinv_1 U24 ( .A(n15), .Y(n30) );
  sky130_fd_sc_hd__and2_0 U25 ( .A(n33), .B(data_out[8]), .X(n36) );
  sky130_fd_sc_hd__clkinv_1 U26 ( .A(count[1]), .Y(n38) );
  sky130_fd_sc_hd__clkinv_1 U27 ( .A(n34), .Y(n11) );
  sky130_fd_sc_hd__clkinv_1 U28 ( .A(n9), .Y(n7) );
  sky130_fd_sc_hd__clkinv_1 U29 ( .A(data_out[1]), .Y(n17) );
  sky130_fd_sc_hd__clkinv_1 U30 ( .A(data_in[1]), .Y(n16) );
  sky130_fd_sc_hd__conb_1 U31 ( .LO(n8) );
  sky130_fd_sc_hd__nor2b_1 U32 ( .B_N(valid_out), .A(valid_in), .Y(n9) );
  sky130_fd_sc_hd__nor2_1 U33 ( .A(n9), .B(count[0]), .Y(N10) );
  sky130_fd_sc_hd__nand2_1 U34 ( .A(count[0]), .B(n7), .Y(n37) );
  sky130_fd_sc_hd__o2bb2ai_1 U35 ( .B1(count[1]), .B2(n37), .A1_N(count[1]), 
        .A2_N(N10), .Y(N11) );
  sky130_fd_sc_hd__nand2_1 U36 ( .A(N10), .B(n38), .Y(n15) );
  sky130_fd_sc_hd__nor2_1 U37 ( .A(n9), .B(n30), .Y(n34) );
  sky130_fd_sc_hd__xnor2_1 U38 ( .A(data_out[0]), .B(data_in[0]), .Y(n10) );
  sky130_fd_sc_hd__o2bb2ai_1 U39 ( .B1(n11), .B2(n10), .A1_N(data_in[0]), 
        .A2_N(n30), .Y(N29) );
  sky130_fd_sc_hd__nand2_1 U40 ( .A(data_in[0]), .B(data_out[0]), .Y(n18) );
  sky130_fd_sc_hd__o22ai_1 U41 ( .A1(data_out[1]), .A2(data_in[1]), .B1(n17), 
        .B2(n16), .Y(n13) );
  sky130_fd_sc_hd__a21oi_1 U42 ( .A1(n18), .A2(n13), .B1(n11), .Y(n12) );
  sky130_fd_sc_hd__o21ai_1 U43 ( .A1(n18), .A2(n13), .B1(n12), .Y(n14) );
  sky130_fd_sc_hd__o21ai_1 U44 ( .A1(n16), .A2(n15), .B1(n14), .Y(N30) );
  sky130_fd_sc_hd__a222oi_1 U45 ( .A1(n18), .A2(n17), .B1(n18), .B2(n16), .C1(
        n17), .C2(n16), .Y(n20) );
  sky130_fd_sc_hd__a22o_1 U46 ( .A1(n30), .A2(data_in[2]), .B1(n34), .B2(n19), 
        .X(N31) );
  sky130_fd_sc_hd__fa_1 U47 ( .A(data_in[2]), .B(data_out[2]), .CIN(n20), 
        .COUT(n22), .SUM(n19) );
  sky130_fd_sc_hd__a22o_1 U48 ( .A1(n30), .A2(data_in[3]), .B1(n34), .B2(n21), 
        .X(N32) );
  sky130_fd_sc_hd__fa_1 U49 ( .A(data_in[3]), .B(data_out[3]), .CIN(n22), 
        .COUT(n24), .SUM(n21) );
  sky130_fd_sc_hd__a22o_1 U50 ( .A1(n30), .A2(data_in[4]), .B1(n34), .B2(n23), 
        .X(N33) );
  sky130_fd_sc_hd__fa_1 U51 ( .A(data_in[4]), .B(data_out[4]), .CIN(n24), 
        .COUT(n26), .SUM(n23) );
  sky130_fd_sc_hd__a22o_1 U52 ( .A1(n30), .A2(data_in[5]), .B1(n34), .B2(n25), 
        .X(N34) );
  sky130_fd_sc_hd__fa_1 U53 ( .A(data_in[5]), .B(data_out[5]), .CIN(n26), 
        .COUT(n28), .SUM(n25) );
  sky130_fd_sc_hd__a22o_1 U54 ( .A1(n30), .A2(data_in[6]), .B1(n34), .B2(n27), 
        .X(N35) );
  sky130_fd_sc_hd__fa_1 U55 ( .A(data_in[6]), .B(data_out[6]), .CIN(n28), 
        .COUT(n31), .SUM(n27) );
  sky130_fd_sc_hd__a22o_1 U56 ( .A1(n30), .A2(data_in[7]), .B1(n34), .B2(n29), 
        .X(N36) );
  sky130_fd_sc_hd__fa_1 U57 ( .A(data_in[7]), .B(data_out[7]), .CIN(n31), 
        .COUT(n33), .SUM(n29) );
  sky130_fd_sc_hd__o21ai_1 U58 ( .A1(n33), .A2(data_out[8]), .B1(n34), .Y(n32)
         );
  sky130_fd_sc_hd__a21oi_1 U59 ( .A1(n33), .A2(data_out[8]), .B1(n32), .Y(N37)
         );
  sky130_fd_sc_hd__o21ai_1 U60 ( .A1(n36), .A2(data_out[9]), .B1(n34), .Y(n35)
         );
  sky130_fd_sc_hd__a21oi_1 U61 ( .A1(n36), .A2(data_out[9]), .B1(n35), .Y(N38)
         );
  sky130_fd_sc_hd__nor2_1 U62 ( .A(n38), .B(n37), .Y(end_cnt) );
endmodule

