/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : W-2024.09-SP5-3
// Date      : Sat Sep 12 07:43:33 2026
/////////////////////////////////////////////////////////////


module verified_accu ( clk, rst_n, data_in, valid_in, valid_out, data_out );
  input [7:0] data_in;
  output [9:0] data_out;
  input clk, rst_n, valid_in;
  output valid_out;
  wire   end_cnt, n27, n28, n29, n30, n31, n32, n33, n34, n35, n36, n37, n38,
         \intadd_0/CI , \intadd_0/SUM[5] , \intadd_0/SUM[4] ,
         \intadd_0/SUM[3] , \intadd_0/SUM[2] , \intadd_0/SUM[1] ,
         \intadd_0/SUM[0] , \intadd_0/n6 , \intadd_0/n5 , \intadd_0/n4 ,
         \intadd_0/n3 , \intadd_0/n2 , \intadd_0/n1 , n40, n41, n42, n43, n44,
         n45, n46, n47, n48, n49, n50, n51, n52, n53, n54, n55, n56, n57, n58,
         n59, n60, n61, n62, n63, n64, n65, n67, n68, n69, n70, n71, n72, n73,
         n74, n75, n76;
  wire   [1:0] count;

  DFFR_X1 valid_out_reg ( .D(end_cnt), .CK(clk), .RN(rst_n), .Q(valid_out) );
  DFFR_X1 \count_reg[0]  ( .D(n37), .CK(clk), .RN(rst_n), .Q(count[0]), .QN(
        n67) );
  DFFR_X1 \count_reg[1]  ( .D(n38), .CK(clk), .RN(rst_n), .Q(count[1]), .QN(
        n69) );
  DFFR_X1 \data_out_reg[1]  ( .D(n36), .CK(clk), .RN(rst_n), .Q(data_out[1])
         );
  DFFR_X1 \data_out_reg[0]  ( .D(n35), .CK(clk), .RN(rst_n), .Q(data_out[0])
         );
  DFFR_X1 \data_out_reg[2]  ( .D(n34), .CK(clk), .RN(rst_n), .Q(data_out[2]), 
        .QN(n71) );
  DFFR_X1 \data_out_reg[3]  ( .D(n33), .CK(clk), .RN(rst_n), .Q(data_out[3]), 
        .QN(n72) );
  DFFR_X1 \data_out_reg[4]  ( .D(n32), .CK(clk), .RN(rst_n), .Q(data_out[4]), 
        .QN(n73) );
  DFFR_X1 \data_out_reg[5]  ( .D(n31), .CK(clk), .RN(rst_n), .Q(data_out[5]), 
        .QN(n74) );
  DFFR_X1 \data_out_reg[6]  ( .D(n30), .CK(clk), .RN(rst_n), .Q(data_out[6]), 
        .QN(n75) );
  DFFR_X1 \data_out_reg[7]  ( .D(n29), .CK(clk), .RN(rst_n), .Q(data_out[7]), 
        .QN(n76) );
  DFFR_X1 \data_out_reg[8]  ( .D(n28), .CK(clk), .RN(rst_n), .Q(data_out[8]), 
        .QN(n68) );
  DFFR_X1 \data_out_reg[9]  ( .D(n27), .CK(clk), .RN(rst_n), .Q(data_out[9]), 
        .QN(n70) );
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
  NOR3_X2 U43 ( .A1(n49), .A2(count[1]), .A3(count[0]), .ZN(n57) );
  INV_X1 U44 ( .A(valid_in), .ZN(n40) );
  NAND2_X1 U45 ( .A1(n40), .A2(valid_out), .ZN(n59) );
  INV_X1 U46 ( .A(n59), .ZN(n49) );
  OAI21_X1 U47 ( .B1(data_in[0]), .B2(n57), .A(n59), .ZN(n43) );
  INV_X1 U48 ( .A(n57), .ZN(n41) );
  OAI21_X1 U49 ( .B1(data_out[0]), .B2(n49), .A(n41), .ZN(n42) );
  AOI22_X1 U50 ( .A1(data_out[0]), .A2(n43), .B1(data_in[0]), .B2(n42), .ZN(
        n44) );
  INV_X1 U51 ( .A(n44), .ZN(n35) );
  AND2_X1 U52 ( .A1(data_in[0]), .A2(data_out[0]), .ZN(n48) );
  OAI222_X1 U53 ( .A1(n48), .A2(data_in[1]), .B1(n48), .B2(data_out[1]), .C1(
        data_in[1]), .C2(data_out[1]), .ZN(n45) );
  INV_X1 U54 ( .A(n45), .ZN(\intadd_0/CI ) );
  NOR3_X1 U55 ( .A1(n69), .A2(n67), .A3(n49), .ZN(end_cnt) );
  NAND2_X1 U56 ( .A1(count[0]), .A2(n59), .ZN(n46) );
  AOI21_X1 U57 ( .B1(n69), .B2(n46), .A(end_cnt), .ZN(n38) );
  AOI22_X1 U58 ( .A1(n49), .A2(n67), .B1(count[0]), .B2(n59), .ZN(n37) );
  NOR2_X1 U59 ( .A1(n49), .A2(n57), .ZN(n63) );
  INV_X1 U60 ( .A(n63), .ZN(n60) );
  XNOR2_X1 U61 ( .A(data_in[1]), .B(data_out[1]), .ZN(n47) );
  XOR2_X1 U62 ( .A(n48), .B(n47), .Z(n51) );
  AOI22_X1 U63 ( .A1(n49), .A2(data_out[1]), .B1(n57), .B2(data_in[1]), .ZN(
        n50) );
  OAI21_X1 U64 ( .B1(n60), .B2(n51), .A(n50), .ZN(n36) );
  AOI22_X1 U65 ( .A1(n57), .A2(data_in[2]), .B1(n63), .B2(\intadd_0/SUM[0] ), 
        .ZN(n52) );
  OAI21_X1 U66 ( .B1(n59), .B2(n71), .A(n52), .ZN(n34) );
  AOI22_X1 U67 ( .A1(n57), .A2(data_in[3]), .B1(n63), .B2(\intadd_0/SUM[1] ), 
        .ZN(n53) );
  OAI21_X1 U68 ( .B1(n59), .B2(n72), .A(n53), .ZN(n33) );
  AOI22_X1 U69 ( .A1(n57), .A2(data_in[4]), .B1(n63), .B2(\intadd_0/SUM[2] ), 
        .ZN(n54) );
  OAI21_X1 U70 ( .B1(n59), .B2(n73), .A(n54), .ZN(n32) );
  AOI22_X1 U71 ( .A1(n57), .A2(data_in[5]), .B1(n63), .B2(\intadd_0/SUM[3] ), 
        .ZN(n55) );
  OAI21_X1 U72 ( .B1(n59), .B2(n74), .A(n55), .ZN(n31) );
  AOI22_X1 U73 ( .A1(n57), .A2(data_in[6]), .B1(n63), .B2(\intadd_0/SUM[4] ), 
        .ZN(n56) );
  OAI21_X1 U74 ( .B1(n59), .B2(n75), .A(n56), .ZN(n30) );
  AOI22_X1 U75 ( .A1(n57), .A2(data_in[7]), .B1(n63), .B2(\intadd_0/SUM[5] ), 
        .ZN(n58) );
  OAI21_X1 U76 ( .B1(n59), .B2(n76), .A(n58), .ZN(n29) );
  OAI21_X1 U77 ( .B1(\intadd_0/n1 ), .B2(n60), .A(n59), .ZN(n62) );
  INV_X1 U78 ( .A(n62), .ZN(n61) );
  NAND2_X1 U79 ( .A1(n63), .A2(\intadd_0/n1 ), .ZN(n64) );
  AOI22_X1 U80 ( .A1(data_out[8]), .A2(n61), .B1(n64), .B2(n68), .ZN(n28) );
  AOI21_X1 U82 ( .B1(n63), .B2(n68), .A(n62), .ZN(n65) );
  OAI33_X1 U83 ( .A1(1'b0), .A2(n65), .A3(n70), .B1(data_out[9]), .B2(n68), 
        .B3(n64), .ZN(n27) );
endmodule

