/////////////////////////////////////////////////////////////
// Created by: Synopsys Design Compiler(R) Graphical
// Version   : W-2024.09-SP5-3
// Date      : Sat Sep 12 13:30:03 2026
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
  wire   end_cnt, N9, N10, N11, N29, N30, N31, N32, N33, N34, N35, N36, N37,
         N38, net40, n17, n18, n19, n20, n21, n22, n23, n24, n25, n26, n27,
         n28, n29, n30, n31, n32, n33, n34, n35, n36, n37, n38, n39, n40, n41,
         n42, n43, n44, n45, n46, n47, n48, n49, n50, n51, n52, n53, n54, n55,
         n56;
  wire   [1:0] count;

  SNPS_CLOCK_GATE_HIGH_verified_accu clk_gate_count_reg ( .CLK(clk), .EN(N9), 
        .ENCLK(net40), .TE(1'b0) );
  DFFR_X1 valid_out_reg ( .D(end_cnt), .CK(clk), .RN(rst_n), .Q(valid_out), 
        .QN(n52) );
  DFFR_X1 \count_reg[0]  ( .D(N10), .CK(net40), .RN(rst_n), .Q(count[0]) );
  DFFR_X1 \count_reg[1]  ( .D(N11), .CK(net40), .RN(rst_n), .Q(count[1]), .QN(
        n56) );
  DFFR_X1 \data_out_reg[0]  ( .D(N29), .CK(net40), .RN(rst_n), .Q(data_out[0])
         );
  DFFR_X1 \data_out_reg[1]  ( .D(N30), .CK(net40), .RN(rst_n), .Q(data_out[1]), 
        .QN(n53) );
  DFFR_X1 \data_out_reg[2]  ( .D(N31), .CK(net40), .RN(rst_n), .Q(data_out[2])
         );
  DFFR_X1 \data_out_reg[3]  ( .D(N32), .CK(net40), .RN(rst_n), .Q(data_out[3])
         );
  DFFR_X1 \data_out_reg[4]  ( .D(N33), .CK(net40), .RN(rst_n), .Q(data_out[4])
         );
  DFFR_X1 \data_out_reg[5]  ( .D(N34), .CK(net40), .RN(rst_n), .Q(data_out[5])
         );
  DFFR_X1 \data_out_reg[6]  ( .D(N35), .CK(net40), .RN(rst_n), .Q(data_out[6])
         );
  DFFR_X1 \data_out_reg[7]  ( .D(N36), .CK(net40), .RN(rst_n), .Q(data_out[7])
         );
  DFFR_X1 \data_out_reg[8]  ( .D(N37), .CK(net40), .RN(rst_n), .Q(data_out[8]), 
        .QN(n54) );
  DFFR_X1 \data_out_reg[9]  ( .D(N38), .CK(net40), .RN(rst_n), .Q(data_out[9]), 
        .QN(n55) );
  NOR2_X1 U33 ( .A1(n52), .A2(valid_in), .ZN(n51) );
  NOR2_X1 U34 ( .A1(n51), .A2(count[0]), .ZN(N10) );
  NAND2_X1 U35 ( .A1(N10), .A2(n56), .ZN(n20) );
  INV_X1 U36 ( .A(n20), .ZN(n41) );
  NOR2_X1 U37 ( .A1(n51), .A2(n41), .ZN(n40) );
  INV_X1 U38 ( .A(n40), .ZN(n47) );
  XNOR2_X1 U39 ( .A(data_in[0]), .B(data_out[0]), .ZN(n18) );
  INV_X1 U40 ( .A(data_in[0]), .ZN(n17) );
  OAI22_X1 U41 ( .A1(n47), .A2(n18), .B1(n20), .B2(n17), .ZN(N29) );
  NAND2_X1 U42 ( .A1(data_in[0]), .A2(data_out[0]), .ZN(n23) );
  XNOR2_X1 U43 ( .A(n53), .B(n23), .ZN(n19) );
  XOR2_X1 U44 ( .A(data_in[1]), .B(n19), .Z(n21) );
  INV_X1 U45 ( .A(data_in[1]), .ZN(n22) );
  OAI22_X1 U46 ( .A1(n47), .A2(n21), .B1(n22), .B2(n20), .ZN(N30) );
  AOI222_X1 U47 ( .A1(n23), .A2(n22), .B1(n23), .B2(n53), .C1(n22), .C2(n53), 
        .ZN(n26) );
  AOI22_X1 U48 ( .A1(n41), .A2(data_in[2]), .B1(n40), .B2(n24), .ZN(n25) );
  INV_X1 U49 ( .A(n25), .ZN(N31) );
  FA_X1 U50 ( .A(data_in[2]), .B(data_out[2]), .CI(n26), .CO(n29), .S(n24) );
  AOI22_X1 U51 ( .A1(n41), .A2(data_in[3]), .B1(n40), .B2(n27), .ZN(n28) );
  INV_X1 U52 ( .A(n28), .ZN(N32) );
  FA_X1 U53 ( .A(data_in[3]), .B(data_out[3]), .CI(n29), .CO(n32), .S(n27) );
  AOI22_X1 U54 ( .A1(n41), .A2(data_in[4]), .B1(n40), .B2(n30), .ZN(n31) );
  INV_X1 U55 ( .A(n31), .ZN(N33) );
  FA_X1 U56 ( .A(data_in[4]), .B(data_out[4]), .CI(n32), .CO(n35), .S(n30) );
  AOI22_X1 U57 ( .A1(n41), .A2(data_in[5]), .B1(n40), .B2(n33), .ZN(n34) );
  INV_X1 U58 ( .A(n34), .ZN(N34) );
  FA_X1 U59 ( .A(data_in[5]), .B(data_out[5]), .CI(n35), .CO(n38), .S(n33) );
  AOI22_X1 U60 ( .A1(n41), .A2(data_in[6]), .B1(n40), .B2(n36), .ZN(n37) );
  INV_X1 U61 ( .A(n37), .ZN(N35) );
  FA_X1 U62 ( .A(data_in[6]), .B(data_out[6]), .CI(n38), .CO(n43), .S(n36) );
  AOI22_X1 U63 ( .A1(n41), .A2(data_in[7]), .B1(n40), .B2(n39), .ZN(n42) );
  INV_X1 U64 ( .A(n42), .ZN(N36) );
  FA_X1 U65 ( .A(data_in[7]), .B(data_out[7]), .CI(n43), .CO(n44), .S(n39) );
  BUF_X1 U66 ( .A(n44), .Z(n45) );
  INV_X1 U67 ( .A(n45), .ZN(n46) );
  AOI221_X1 U68 ( .B1(n45), .B2(data_out[8]), .C1(n46), .C2(n54), .A(n47), 
        .ZN(N37) );
  NOR2_X1 U69 ( .A1(n46), .A2(n54), .ZN(n49) );
  INV_X1 U70 ( .A(n49), .ZN(n48) );
  AOI221_X1 U71 ( .B1(n49), .B2(data_out[9]), .C1(n48), .C2(n55), .A(n47), 
        .ZN(N38) );
  INV_X1 U72 ( .A(count[0]), .ZN(n50) );
  AOI221_X1 U73 ( .B1(count[1]), .B2(count[0]), .C1(n56), .C2(n50), .A(n51), 
        .ZN(N11) );
  INV_X1 U74 ( .A(n51), .ZN(N9) );
  NOR3_X1 U75 ( .A1(n51), .A2(n56), .A3(n50), .ZN(end_cnt) );
endmodule

