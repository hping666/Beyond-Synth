/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : W-2024.09-SP5-3
// Date      : Sat Sep 12 07:43:27 2026
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
  wire   end_cnt, N10, N11, N30, N37, N38, net40, n16, n18, n19, n20, n21, n22,
         n23, n24, n25, n26, n27, n28, n29, n30, n31, n32, n33, n34, n35, n36,
         n37, n38, n39, n40, n41, n42, n43, n44, n45, n46, n47, n48, n49, n50,
         n51, n52, n53, n54, n55, n56, n57, n58;
  wire   [1:0] count;

  SNPS_CLOCK_GATE_HIGH_verified_accu clk_gate_count_reg ( .CLK(clk), .EN(n16), 
        .ENCLK(net40), .TE(1'b0) );
  DFFR_X1 valid_out_reg ( .D(end_cnt), .CK(clk), .RN(rst_n), .Q(valid_out), 
        .QN(n49) );
  DFFR_X1 \count_reg[0]  ( .D(N10), .CK(net40), .RN(rst_n), .Q(count[0]), .QN(
        n51) );
  DFFR_X1 \count_reg[1]  ( .D(N11), .CK(net40), .RN(rst_n), .Q(count[1]), .QN(
        n47) );
  DFFR_X1 \data_out_reg[1]  ( .D(N30), .CK(net40), .RN(rst_n), .Q(data_out[1]), 
        .QN(n48) );
  DFFR_X1 \data_out_reg[8]  ( .D(N37), .CK(net40), .RN(rst_n), .Q(data_out[8]), 
        .QN(n50) );
  DFFR_X1 \data_out_reg[9]  ( .D(N38), .CK(net40), .RN(rst_n), .Q(data_out[9]), 
        .QN(n52) );
  DFFS_X1 \data_out_reg[2]  ( .D(n53), .CK(net40), .SN(rst_n), .QN(data_out[2]) );
  DFFS_X1 \data_out_reg[0]  ( .D(n46), .CK(net40), .SN(rst_n), .QN(data_out[0]) );
  DFFS_X1 \data_out_reg[3]  ( .D(n54), .CK(net40), .SN(rst_n), .QN(data_out[3]) );
  DFFS_X1 \data_out_reg[4]  ( .D(n55), .CK(net40), .SN(rst_n), .QN(data_out[4]) );
  DFFS_X1 \data_out_reg[5]  ( .D(n56), .CK(net40), .SN(rst_n), .QN(data_out[5]) );
  DFFS_X1 \data_out_reg[6]  ( .D(n57), .CK(net40), .SN(rst_n), .QN(data_out[6]) );
  DFFS_X1 \data_out_reg[7]  ( .D(n58), .CK(net40), .SN(rst_n), .QN(data_out[7]) );
  NOR2_X1 U33 ( .A1(n49), .A2(valid_in), .ZN(n45) );
  NOR2_X1 U34 ( .A1(n45), .A2(count[0]), .ZN(N10) );
  NAND2_X1 U35 ( .A1(N10), .A2(n47), .ZN(n22) );
  INV_X1 U36 ( .A(n22), .ZN(n38) );
  NOR2_X1 U37 ( .A1(n45), .A2(n38), .ZN(n37) );
  INV_X1 U38 ( .A(n37), .ZN(n42) );
  XNOR2_X1 U39 ( .A(data_in[0]), .B(data_out[0]), .ZN(n19) );
  INV_X1 U40 ( .A(data_in[0]), .ZN(n18) );
  OAI22_X1 U41 ( .A1(n42), .A2(n19), .B1(n22), .B2(n18), .ZN(n20) );
  INV_X1 U42 ( .A(n20), .ZN(n46) );
  INV_X1 U43 ( .A(n45), .ZN(n16) );
  NAND2_X1 U44 ( .A1(data_in[0]), .A2(data_out[0]), .ZN(n25) );
  XNOR2_X1 U45 ( .A(n48), .B(n25), .ZN(n21) );
  XOR2_X1 U46 ( .A(data_in[1]), .B(n21), .Z(n23) );
  INV_X1 U47 ( .A(data_in[1]), .ZN(n24) );
  OAI22_X1 U48 ( .A1(n42), .A2(n23), .B1(n24), .B2(n22), .ZN(N30) );
  AOI222_X1 U49 ( .A1(n25), .A2(n24), .B1(n25), .B2(n48), .C1(n24), .C2(n48), 
        .ZN(n27) );
  AOI22_X1 U50 ( .A1(n38), .A2(data_in[2]), .B1(n37), .B2(n26), .ZN(n53) );
  FA_X1 U51 ( .A(data_in[2]), .B(data_out[2]), .CI(n27), .CO(n29), .S(n26) );
  AOI22_X1 U52 ( .A1(n38), .A2(data_in[3]), .B1(n37), .B2(n28), .ZN(n54) );
  FA_X1 U53 ( .A(data_in[3]), .B(data_out[3]), .CI(n29), .CO(n31), .S(n28) );
  AOI22_X1 U54 ( .A1(n38), .A2(data_in[4]), .B1(n37), .B2(n30), .ZN(n55) );
  FA_X1 U55 ( .A(data_in[4]), .B(data_out[4]), .CI(n31), .CO(n33), .S(n30) );
  AOI22_X1 U56 ( .A1(n38), .A2(data_in[5]), .B1(n37), .B2(n32), .ZN(n56) );
  FA_X1 U57 ( .A(data_in[5]), .B(data_out[5]), .CI(n33), .CO(n35), .S(n32) );
  AOI22_X1 U58 ( .A1(n38), .A2(data_in[6]), .B1(n37), .B2(n34), .ZN(n57) );
  FA_X1 U59 ( .A(data_in[6]), .B(data_out[6]), .CI(n35), .CO(n39), .S(n34) );
  AOI22_X1 U60 ( .A1(n38), .A2(data_in[7]), .B1(n37), .B2(n36), .ZN(n58) );
  FA_X1 U61 ( .A(data_in[7]), .B(data_out[7]), .CI(n39), .CO(n40), .S(n36) );
  INV_X1 U62 ( .A(n40), .ZN(n41) );
  AOI221_X1 U63 ( .B1(n40), .B2(data_out[8]), .C1(n41), .C2(n50), .A(n42), 
        .ZN(N37) );
  NOR2_X1 U64 ( .A1(n41), .A2(n50), .ZN(n44) );
  INV_X1 U65 ( .A(n44), .ZN(n43) );
  AOI221_X1 U66 ( .B1(n44), .B2(data_out[9]), .C1(n43), .C2(n52), .A(n42), 
        .ZN(N38) );
  AOI221_X1 U67 ( .B1(count[1]), .B2(count[0]), .C1(n47), .C2(n51), .A(n45), 
        .ZN(N11) );
  NOR3_X1 U69 ( .A1(n45), .A2(n47), .A3(n51), .ZN(end_cnt) );
endmodule

