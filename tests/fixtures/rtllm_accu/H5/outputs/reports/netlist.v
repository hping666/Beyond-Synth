/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : W-2024.09-SP5-3
// Date      : Sat Sep 12 13:30:05 2026
/////////////////////////////////////////////////////////////


module SNPS_CLOCK_GATE_HIGH_verified_accu ( CLK, EN, ENCLK, TE );
  input CLK, EN, TE;
  output ENCLK;


  CLKGATETST_X1 latch ( .CK(CLK), .E(EN), .SE(TE), .GCK(ENCLK) );
endmodule


module verified_accu ( clk, rst_n, data_in, valid_in, valid_out, data_out );
  input [7:0] data_in;
  output [9:0] data_out;
  input clk, rst_n, valid_in;
  output valid_out;
  wire   end_cnt, N10, N11, N30, N37, N38, net40, n16, \intadd_0/CI ,
         \intadd_0/SUM[5] , \intadd_0/SUM[4] , \intadd_0/SUM[3] ,
         \intadd_0/SUM[2] , \intadd_0/SUM[1] , \intadd_0/SUM[0] ,
         \intadd_0/n6 , \intadd_0/n5 , \intadd_0/n4 , \intadd_0/n3 ,
         \intadd_0/n2 , \intadd_0/n1 , n18, n19, n20, n21, n22, n23, n24, n25,
         n26, n27, n28, n29, n30, n31, n32, n33, n34, n35, n36, n37, n38, n39,
         n40, n41, n42, n43, n44, n45;
  wire   [1:0] count;

  SNPS_CLOCK_GATE_HIGH_verified_accu clk_gate_count_reg ( .CLK(clk), .EN(n16), 
        .ENCLK(net40), .TE(1'b0) );
  DFFR_X1 valid_out_reg ( .D(end_cnt), .CK(clk), .RN(rst_n), .Q(valid_out), 
        .QN(n36) );
  DFFR_X1 \count_reg[0]  ( .D(N10), .CK(net40), .RN(rst_n), .Q(count[0]), .QN(
        n38) );
  DFFR_X1 \count_reg[1]  ( .D(N11), .CK(net40), .RN(rst_n), .Q(count[1]), .QN(
        n34) );
  DFFR_X1 \data_out_reg[1]  ( .D(N30), .CK(net40), .RN(rst_n), .Q(data_out[1]), 
        .QN(n35) );
  DFFR_X1 \data_out_reg[8]  ( .D(N37), .CK(net40), .RN(rst_n), .Q(data_out[8]), 
        .QN(n37) );
  DFFR_X1 \data_out_reg[9]  ( .D(N38), .CK(net40), .RN(rst_n), .Q(data_out[9]), 
        .QN(n39) );
  FA_X1 \intadd_0/U7  ( .A(data_in[2]), .B(data_out[2]), .CI(\intadd_0/CI ), 
        .CO(\intadd_0/n6 ), .S(\intadd_0/SUM[0] ) );
  FA_X1 \intadd_0/U6  ( .A(data_in[3]), .B(data_out[3]), .CI(\intadd_0/n6 ), 
        .CO(\intadd_0/n5 ), .S(\intadd_0/SUM[1] ) );
  FA_X1 \intadd_0/U5  ( .A(data_in[4]), .B(data_out[4]), .CI(\intadd_0/n5 ), 
        .CO(\intadd_0/n4 ), .S(\intadd_0/SUM[2] ) );
  FA_X1 \intadd_0/U4  ( .A(data_in[5]), .B(data_out[5]), .CI(\intadd_0/n4 ), 
        .CO(\intadd_0/n3 ), .S(\intadd_0/SUM[3] ) );
  FA_X1 \intadd_0/U3  ( .A(data_in[6]), .B(data_out[6]), .CI(\intadd_0/n3 ), 
        .CO(\intadd_0/n2 ), .S(\intadd_0/SUM[4] ) );
  FA_X1 \intadd_0/U2  ( .A(data_in[7]), .B(data_out[7]), .CI(\intadd_0/n2 ), 
        .CO(\intadd_0/n1 ), .S(\intadd_0/SUM[5] ) );
  DFFS_X1 \data_out_reg[2]  ( .D(n40), .CK(net40), .SN(rst_n), .QN(data_out[2]) );
  DFFS_X1 \data_out_reg[0]  ( .D(n33), .CK(net40), .SN(rst_n), .QN(data_out[0]) );
  DFFS_X1 \data_out_reg[3]  ( .D(n41), .CK(net40), .SN(rst_n), .QN(data_out[3]) );
  DFFS_X1 \data_out_reg[4]  ( .D(n42), .CK(net40), .SN(rst_n), .QN(data_out[4]) );
  DFFS_X1 \data_out_reg[5]  ( .D(n43), .CK(net40), .SN(rst_n), .QN(data_out[5]) );
  DFFS_X1 \data_out_reg[6]  ( .D(n44), .CK(net40), .SN(rst_n), .QN(data_out[6]) );
  DFFS_X1 \data_out_reg[7]  ( .D(n45), .CK(net40), .SN(rst_n), .QN(data_out[7]) );
  NOR2_X1 U33 ( .A1(n36), .A2(valid_in), .ZN(n32) );
  NOR2_X1 U34 ( .A1(n32), .A2(count[0]), .ZN(N10) );
  NAND2_X1 U35 ( .A1(N10), .A2(n34), .ZN(n22) );
  INV_X1 U36 ( .A(n22), .ZN(n27) );
  NOR2_X1 U37 ( .A1(n32), .A2(n27), .ZN(n26) );
  INV_X1 U38 ( .A(n26), .ZN(n29) );
  XNOR2_X1 U39 ( .A(data_in[0]), .B(data_out[0]), .ZN(n19) );
  INV_X1 U40 ( .A(data_in[0]), .ZN(n18) );
  OAI22_X1 U41 ( .A1(n29), .A2(n19), .B1(n22), .B2(n18), .ZN(n20) );
  INV_X1 U42 ( .A(n20), .ZN(n33) );
  INV_X1 U43 ( .A(n32), .ZN(n16) );
  NAND2_X1 U44 ( .A1(data_in[0]), .A2(data_out[0]), .ZN(n25) );
  XNOR2_X1 U45 ( .A(n35), .B(n25), .ZN(n21) );
  XOR2_X1 U46 ( .A(data_in[1]), .B(n21), .Z(n23) );
  INV_X1 U47 ( .A(data_in[1]), .ZN(n24) );
  OAI22_X1 U48 ( .A1(n29), .A2(n23), .B1(n24), .B2(n22), .ZN(N30) );
  AOI222_X1 U49 ( .A1(n25), .A2(n24), .B1(n25), .B2(n35), .C1(n24), .C2(n35), 
        .ZN(\intadd_0/CI ) );
  AOI22_X1 U50 ( .A1(n27), .A2(data_in[2]), .B1(n26), .B2(\intadd_0/SUM[0] ), 
        .ZN(n40) );
  AOI22_X1 U51 ( .A1(n27), .A2(data_in[3]), .B1(n26), .B2(\intadd_0/SUM[1] ), 
        .ZN(n41) );
  AOI22_X1 U52 ( .A1(n27), .A2(data_in[4]), .B1(n26), .B2(\intadd_0/SUM[2] ), 
        .ZN(n42) );
  AOI22_X1 U53 ( .A1(n27), .A2(data_in[5]), .B1(n26), .B2(\intadd_0/SUM[3] ), 
        .ZN(n43) );
  AOI22_X1 U54 ( .A1(n27), .A2(data_in[6]), .B1(n26), .B2(\intadd_0/SUM[4] ), 
        .ZN(n44) );
  AOI22_X1 U55 ( .A1(n27), .A2(data_in[7]), .B1(n26), .B2(\intadd_0/SUM[5] ), 
        .ZN(n45) );
  INV_X1 U56 ( .A(\intadd_0/n1 ), .ZN(n28) );
  AOI221_X1 U57 ( .B1(\intadd_0/n1 ), .B2(data_out[8]), .C1(n28), .C2(n37), 
        .A(n29), .ZN(N37) );
  NOR2_X1 U58 ( .A1(n28), .A2(n37), .ZN(n31) );
  INV_X1 U59 ( .A(n31), .ZN(n30) );
  AOI221_X1 U60 ( .B1(n31), .B2(data_out[9]), .C1(n30), .C2(n39), .A(n29), 
        .ZN(N38) );
  AOI221_X1 U61 ( .B1(count[1]), .B2(count[0]), .C1(n34), .C2(n38), .A(n32), 
        .ZN(N11) );
  NOR3_X1 U63 ( .A1(n32), .A2(n34), .A3(n38), .ZN(end_cnt) );
endmodule

