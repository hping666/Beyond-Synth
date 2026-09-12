/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Expert(TM) in wire load mode
// Version   : W-2024.09-SP5-3
// Date      : Sat Sep 12 13:28:16 2026
/////////////////////////////////////////////////////////////


module verified_accu_DW01_add_0 ( A, B, CI, SUM, CO );
  input [9:0] A;
  input [9:0] B;
  output [9:0] SUM;
  input CI;
  output CO;
  wire   n4, n5;
  wire   [9:1] carry;

  FA_X1 U1_7 ( .A(A[7]), .B(B[7]), .CI(carry[7]), .CO(carry[8]), .S(SUM[7]) );
  FA_X1 U1_6 ( .A(A[6]), .B(B[6]), .CI(carry[6]), .CO(carry[7]), .S(SUM[6]) );
  FA_X1 U1_5 ( .A(A[5]), .B(B[5]), .CI(carry[5]), .CO(carry[6]), .S(SUM[5]) );
  FA_X1 U1_4 ( .A(A[4]), .B(B[4]), .CI(carry[4]), .CO(carry[5]), .S(SUM[4]) );
  FA_X1 U1_3 ( .A(A[3]), .B(B[3]), .CI(carry[3]), .CO(carry[4]), .S(SUM[3]) );
  FA_X1 U1_2 ( .A(A[2]), .B(B[2]), .CI(carry[2]), .CO(carry[3]), .S(SUM[2]) );
  FA_X1 U1_1 ( .A(A[1]), .B(B[1]), .CI(n5), .CO(carry[2]), .S(SUM[1]) );
  XOR2_X1 U1 ( .A(A[9]), .B(n4), .Z(SUM[9]) );
  XOR2_X1 U2 ( .A(A[8]), .B(carry[8]), .Z(SUM[8]) );
  XOR2_X1 U3 ( .A(B[0]), .B(A[0]), .Z(SUM[0]) );
  AND2_X1 U4 ( .A1(A[8]), .A2(carry[8]), .ZN(n4) );
  AND2_X1 U5 ( .A1(B[0]), .A2(A[0]), .ZN(n5) );
endmodule


module verified_accu ( clk, rst_n, data_in, valid_in, valid_out, data_out );
  input [7:0] data_in;
  output [9:0] data_out;
  input clk, rst_n, valid_in;
  output valid_out;
  wire   end_cnt, N18, N19, N20, N21, N22, N23, N24, N25, N26, N27, n13, n15,
         n16, n17, n18, n19, n20, n21, n22, n23, n24, n25, n26, n27, n28, n29,
         n30, n31, n32, n33, n34, n35, n36, n37, n38, n39, n40, n41, n42, n43;
  wire   [1:0] count;

  DFFR_X1 valid_out_reg ( .D(end_cnt), .CK(clk), .RN(rst_n), .Q(valid_out), 
        .QN(n15) );
  DFFR_X1 \count_reg[0]  ( .D(n31), .CK(clk), .RN(rst_n), .Q(count[0]) );
  DFFR_X1 \count_reg[1]  ( .D(n32), .CK(clk), .RN(rst_n), .Q(count[1]), .QN(
        n13) );
  DFFR_X1 \data_out_reg[0]  ( .D(n42), .CK(clk), .RN(rst_n), .Q(data_out[0])
         );
  DFFR_X1 \data_out_reg[1]  ( .D(n41), .CK(clk), .RN(rst_n), .Q(data_out[1])
         );
  DFFR_X1 \data_out_reg[2]  ( .D(n40), .CK(clk), .RN(rst_n), .Q(data_out[2])
         );
  DFFR_X1 \data_out_reg[3]  ( .D(n39), .CK(clk), .RN(rst_n), .Q(data_out[3])
         );
  DFFR_X1 \data_out_reg[4]  ( .D(n38), .CK(clk), .RN(rst_n), .Q(data_out[4])
         );
  DFFR_X1 \data_out_reg[5]  ( .D(n37), .CK(clk), .RN(rst_n), .Q(data_out[5])
         );
  DFFR_X1 \data_out_reg[6]  ( .D(n36), .CK(clk), .RN(rst_n), .Q(data_out[6])
         );
  DFFR_X1 \data_out_reg[7]  ( .D(n35), .CK(clk), .RN(rst_n), .Q(data_out[7])
         );
  DFFR_X1 \data_out_reg[8]  ( .D(n34), .CK(clk), .RN(rst_n), .Q(data_out[8])
         );
  DFFR_X1 \data_out_reg[9]  ( .D(n33), .CK(clk), .RN(rst_n), .Q(data_out[9])
         );
  NAND3_X1 U32 ( .A1(n43), .A2(n13), .A3(count[0]), .ZN(n30) );
  verified_accu_DW01_add_0 add_57 ( .A(data_out), .B({1'b0, 1'b0, data_in}), 
        .CI(1'b0), .SUM({N27, N26, N25, N24, N23, N22, N21, N20, N19, N18}) );
  NOR2_X1 U33 ( .A1(n29), .A2(n21), .ZN(n17) );
  NOR2_X1 U34 ( .A1(n21), .A2(n17), .ZN(n18) );
  INV_X1 U35 ( .A(n29), .ZN(n43) );
  INV_X1 U36 ( .A(n16), .ZN(n33) );
  AOI22_X1 U37 ( .A1(N27), .A2(n17), .B1(data_out[9]), .B2(n18), .ZN(n16) );
  INV_X1 U38 ( .A(n19), .ZN(n34) );
  AOI22_X1 U39 ( .A1(N26), .A2(n17), .B1(data_out[8]), .B2(n18), .ZN(n19) );
  INV_X1 U40 ( .A(n20), .ZN(n35) );
  AOI222_X1 U41 ( .A1(data_out[7]), .A2(n18), .B1(data_in[7]), .B2(n21), .C1(
        N25), .C2(n17), .ZN(n20) );
  INV_X1 U42 ( .A(n22), .ZN(n36) );
  AOI222_X1 U43 ( .A1(data_out[6]), .A2(n18), .B1(data_in[6]), .B2(n21), .C1(
        N24), .C2(n17), .ZN(n22) );
  INV_X1 U44 ( .A(n23), .ZN(n37) );
  AOI222_X1 U45 ( .A1(data_out[5]), .A2(n18), .B1(data_in[5]), .B2(n21), .C1(
        N23), .C2(n17), .ZN(n23) );
  INV_X1 U46 ( .A(n24), .ZN(n38) );
  AOI222_X1 U47 ( .A1(data_out[4]), .A2(n18), .B1(data_in[4]), .B2(n21), .C1(
        N22), .C2(n17), .ZN(n24) );
  NOR3_X2 U48 ( .A1(count[0]), .A2(count[1]), .A3(n29), .ZN(n21) );
  NOR2_X1 U49 ( .A1(n15), .A2(valid_in), .ZN(n29) );
  INV_X1 U50 ( .A(n25), .ZN(n39) );
  AOI222_X1 U51 ( .A1(data_out[3]), .A2(n18), .B1(data_in[3]), .B2(n21), .C1(
        N21), .C2(n17), .ZN(n25) );
  INV_X1 U52 ( .A(n26), .ZN(n40) );
  AOI222_X1 U53 ( .A1(data_out[2]), .A2(n18), .B1(data_in[2]), .B2(n21), .C1(
        N20), .C2(n17), .ZN(n26) );
  INV_X1 U54 ( .A(n27), .ZN(n41) );
  AOI222_X1 U55 ( .A1(data_out[1]), .A2(n18), .B1(data_in[1]), .B2(n21), .C1(
        N19), .C2(n17), .ZN(n27) );
  INV_X1 U56 ( .A(n28), .ZN(n42) );
  AOI222_X1 U57 ( .A1(data_out[0]), .A2(n18), .B1(data_in[0]), .B2(n21), .C1(
        N18), .C2(n17), .ZN(n28) );
  OAI221_X1 U58 ( .B1(count[0]), .B2(n13), .C1(n43), .C2(n13), .A(n30), .ZN(
        n32) );
  AND3_X1 U59 ( .A1(count[1]), .A2(n43), .A3(count[0]), .ZN(end_cnt) );
  XNOR2_X1 U60 ( .A(n29), .B(count[0]), .ZN(n31) );
endmodule

