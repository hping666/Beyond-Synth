/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : W-2024.09-SP5-3
// Date      : Sat Sep 12 07:57:34 2026
/////////////////////////////////////////////////////////////


module SNPS_CLOCK_GATE_HIGH_verified_accu ( CLK, EN, ENCLK, TE );
  input CLK, EN, TE;
  output ENCLK;


  ICGx1_ASAP7_75t_R latch ( .CLK(CLK), .ENA(EN), .SE(TE), .GCLK(ENCLK) );
endmodule


module verified_accu ( clk, rst_n, data_in, valid_in, valid_out, data_out );
  input [7:0] data_in;
  output [9:0] data_out;
  input clk, rst_n, valid_in;
  output valid_out;
  wire   end_cnt, N10, N11, N19, N21, N23, N25, N29, N30, N31, N32, N33, N34,
         N35, N36, N37, N38, net40, n5, n6, n7, n8, n9, n10, n11, n12, n13,
         n14, n15, n16, n17, n18, n19, n20, \add_x_4/n22 , \add_x_4/n21 ,
         \add_x_4/n20 , \add_x_4/n18 , \add_x_4/n17 , \add_x_4/n16 ,
         \add_x_4/n15 , \add_x_4/n14 , \add_x_4/n13 , \add_x_4/n12 ,
         \add_x_4/n11 , \add_x_4/n9 , \add_x_4/n7 , \add_x_4/n5 , \add_x_4/n3 ,
         n21, n22, n23, n24, n25, n26, n27, n28, n29, n30, n31, n32, n33;

  SNPS_CLOCK_GATE_HIGH_verified_accu clk_gate_count_reg ( .CLK(clk), .EN(n19), 
        .ENCLK(net40), .TE(n20) );
  DFFASRHQNx1_ASAP7_75t_R valid_out_reg ( .D(end_cnt), .CLK(clk), .SETN(n6), 
        .RESETN(rst_n), .QN(n18) );
  DFFASRHQNx1_ASAP7_75t_R \count_reg[0]  ( .D(N10), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n17) );
  DFFASRHQNx1_ASAP7_75t_R \count_reg[1]  ( .D(N11), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n16) );
  DFFASRHQNx1_ASAP7_75t_R \data_out_reg[0]  ( .D(N29), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n15) );
  DFFASRHQNx1_ASAP7_75t_R \data_out_reg[1]  ( .D(N30), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n14) );
  DFFASRHQNx1_ASAP7_75t_R \data_out_reg[2]  ( .D(N31), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n13) );
  DFFASRHQNx1_ASAP7_75t_R \data_out_reg[3]  ( .D(N32), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n12) );
  DFFASRHQNx1_ASAP7_75t_R \data_out_reg[4]  ( .D(N33), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n11) );
  DFFASRHQNx1_ASAP7_75t_R \data_out_reg[5]  ( .D(N34), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n10) );
  DFFASRHQNx1_ASAP7_75t_R \data_out_reg[6]  ( .D(N35), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n9) );
  DFFASRHQNx1_ASAP7_75t_R \data_out_reg[7]  ( .D(N36), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n8) );
  DFFASRHQNx1_ASAP7_75t_R \data_out_reg[8]  ( .D(N37), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n7) );
  DFFASRHQNx1_ASAP7_75t_R \data_out_reg[9]  ( .D(N38), .CLK(net40), .SETN(n6), 
        .RESETN(rst_n), .QN(n5) );
  FAx1_ASAP7_75t_R \add_x_4/U21  ( .A(n14), .B(\add_x_4/n9 ), .CI(
        \add_x_4/n18 ), .CON(\add_x_4/n17 ), .SN(N19) );
  FAx1_ASAP7_75t_R \add_x_4/U20  ( .A(data_out[2]), .B(data_in[2]), .CI(
        \add_x_4/n17 ), .CON(\add_x_4/n16 ), .SN(\add_x_4/n22 ) );
  FAx1_ASAP7_75t_R \add_x_4/U16  ( .A(n12), .B(\add_x_4/n7 ), .CI(
        \add_x_4/n16 ), .CON(\add_x_4/n15 ), .SN(N21) );
  FAx1_ASAP7_75t_R \add_x_4/U15  ( .A(data_out[4]), .B(data_in[4]), .CI(
        \add_x_4/n15 ), .CON(\add_x_4/n14 ), .SN(\add_x_4/n21 ) );
  FAx1_ASAP7_75t_R \add_x_4/U11  ( .A(n10), .B(\add_x_4/n5 ), .CI(
        \add_x_4/n14 ), .CON(\add_x_4/n13 ), .SN(N23) );
  FAx1_ASAP7_75t_R \add_x_4/U10  ( .A(data_out[6]), .B(data_in[6]), .CI(
        \add_x_4/n13 ), .CON(\add_x_4/n12 ), .SN(\add_x_4/n20 ) );
  FAx1_ASAP7_75t_R \add_x_4/U6  ( .A(n8), .B(\add_x_4/n3 ), .CI(\add_x_4/n12 ), 
        .CON(\add_x_4/n11 ), .SN(N25) );
  NAND2xp33_ASAP7_75t_R U34 ( .A(n16), .B(N10), .Y(n33) );
  OAI22xp33_ASAP7_75t_R U35 ( .A1(\add_x_4/n22 ), .A2(n29), .B1(n33), .B2(n25), 
        .Y(N31) );
  INVxp67_ASAP7_75t_R U36 ( .A(n23), .Y(n19) );
  TIEHIx1_ASAP7_75t_R U37 ( .H(n6) );
  TIELOx1_ASAP7_75t_R U38 ( .L(n20) );
  INVxp33_ASAP7_75t_R U39 ( .A(n18), .Y(valid_out) );
  INVxp33_ASAP7_75t_R U40 ( .A(n14), .Y(data_out[1]) );
  INVxp33_ASAP7_75t_R U41 ( .A(n12), .Y(data_out[3]) );
  INVxp33_ASAP7_75t_R U42 ( .A(n10), .Y(data_out[5]) );
  INVxp33_ASAP7_75t_R U43 ( .A(n8), .Y(data_out[7]) );
  NOR2xp33_ASAP7_75t_R U44 ( .A(n18), .B(valid_in), .Y(n23) );
  NOR3xp33_ASAP7_75t_R U45 ( .A(n16), .B(n23), .C(n17), .Y(end_cnt) );
  INVxp33_ASAP7_75t_R U46 ( .A(n16), .Y(n21) );
  INVxp33_ASAP7_75t_R U47 ( .A(n17), .Y(n22) );
  AOI221xp5_ASAP7_75t_R U48 ( .A1(n16), .A2(n17), .B1(n21), .B2(n22), .C(n23), 
        .Y(N11) );
  NOR2xp33_ASAP7_75t_R U49 ( .A(n23), .B(n22), .Y(N10) );
  NAND2xp33_ASAP7_75t_R U50 ( .A(n19), .B(n33), .Y(n29) );
  INVxp33_ASAP7_75t_R U51 ( .A(n33), .Y(n32) );
  A2O1A1Ixp33_ASAP7_75t_R U52 ( .A1(n15), .A2(n19), .B(n32), .C(data_in[0]), 
        .Y(n24) );
  OAI31xp33_ASAP7_75t_R U53 ( .A1(n15), .A2(data_in[0]), .A3(n29), .B(n24), 
        .Y(N29) );
  INVxp33_ASAP7_75t_R U54 ( .A(data_in[2]), .Y(n25) );
  INVxp33_ASAP7_75t_R U55 ( .A(data_in[4]), .Y(n26) );
  OAI22xp33_ASAP7_75t_R U56 ( .A1(\add_x_4/n21 ), .A2(n29), .B1(n33), .B2(n26), 
        .Y(N33) );
  INVxp33_ASAP7_75t_R U57 ( .A(data_in[6]), .Y(n27) );
  OAI22xp33_ASAP7_75t_R U58 ( .A1(\add_x_4/n20 ), .A2(n29), .B1(n33), .B2(n27), 
        .Y(N35) );
  INVxp33_ASAP7_75t_R U59 ( .A(n7), .Y(data_out[8]) );
  INVxp33_ASAP7_75t_R U60 ( .A(\add_x_4/n11 ), .Y(n28) );
  AOI221xp5_ASAP7_75t_R U61 ( .A1(n7), .A2(n28), .B1(data_out[8]), .B2(
        \add_x_4/n11 ), .C(n29), .Y(N37) );
  INVxp33_ASAP7_75t_R U62 ( .A(n5), .Y(data_out[9]) );
  NAND2xp33_ASAP7_75t_R U63 ( .A(data_out[8]), .B(\add_x_4/n11 ), .Y(n30) );
  INVxp33_ASAP7_75t_R U64 ( .A(n30), .Y(n31) );
  AOI221xp5_ASAP7_75t_R U65 ( .A1(n31), .A2(data_out[9]), .B1(n30), .B2(n5), 
        .C(n29), .Y(N38) );
  INVxp33_ASAP7_75t_R U66 ( .A(n15), .Y(data_out[0]) );
  NAND2xp33_ASAP7_75t_R U67 ( .A(data_in[0]), .B(data_out[0]), .Y(
        \add_x_4/n18 ) );
  INVxp33_ASAP7_75t_R U68 ( .A(data_in[1]), .Y(\add_x_4/n9 ) );
  INVxp33_ASAP7_75t_R U69 ( .A(n13), .Y(data_out[2]) );
  INVxp33_ASAP7_75t_R U70 ( .A(data_in[3]), .Y(\add_x_4/n7 ) );
  INVxp33_ASAP7_75t_R U71 ( .A(n11), .Y(data_out[4]) );
  INVxp33_ASAP7_75t_R U72 ( .A(data_in[5]), .Y(\add_x_4/n5 ) );
  INVxp33_ASAP7_75t_R U73 ( .A(n9), .Y(data_out[6]) );
  INVxp33_ASAP7_75t_R U74 ( .A(data_in[7]), .Y(\add_x_4/n3 ) );
  AO32x1_ASAP7_75t_R U75 ( .A1(N19), .A2(n33), .A3(n19), .B1(n32), .B2(
        data_in[1]), .Y(N30) );
  AO32x1_ASAP7_75t_R U76 ( .A1(N21), .A2(n33), .A3(n19), .B1(n32), .B2(
        data_in[3]), .Y(N32) );
  AO32x1_ASAP7_75t_R U77 ( .A1(N23), .A2(n33), .A3(n19), .B1(n32), .B2(
        data_in[5]), .Y(N34) );
  AO32x1_ASAP7_75t_R U78 ( .A1(N25), .A2(n33), .A3(n19), .B1(n32), .B2(
        data_in[7]), .Y(N36) );
endmodule

