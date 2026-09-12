/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : W-2024.09-SP5-3
// Date      : Sat Sep 12 13:29:15 2026
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
  wire   end_cnt, N11, N29, N30, N31, N32, N33, N34, N35, N36, net40, n16, n18,
         n19, n20, n21, n22, n23, n24, n25, n26, n27, n28, n29, n30, n31, n32,
         n33, n34, n35, n36, n37, n38, n39, n40, n41, n42, n43, n44, n45, n46,
         n47, n48, n49, n50, n51, n52, n53, n54, n55, n56, n57, n58, n59, n60,
         n61, n62, n63, n64, n65, n66, n67, n68, n69, n70, n71, n72, n73, n74,
         n75, n76, n77, n78, n79, n80, n81, n82, n83, n84, n85, n86, n87, n88,
         n89, n90, n91, n92, n93, n94, n95, n96, n97, n98, n99, n100, n101,
         n102, n103, n104, n105, n106, n107, n108, n109, n110, n111, n112,
         n113, n114, n115, n116, n118, n119, n120, n121, n122, n123, n124,
         n125, n126, n127, n128, n129, n130, n131, n132;
  wire   [1:0] count;

  SNPS_CLOCK_GATE_HIGH_verified_accu clk_gate_count_reg ( .CLK(clk), .EN(n16), 
        .ENCLK(net40), .TE(1'b0) );
  DFFR_X1 R_2 ( .D(end_cnt), .CK(clk), .RN(rst_n), .Q(valid_out) );
  DFFR_X1 \count_reg[0]  ( .D(n132), .CK(net40), .RN(rst_n), .Q(count[0]), 
        .QN(n119) );
  DFFR_X1 \count_reg[1]  ( .D(N11), .CK(net40), .RN(rst_n), .Q(count[1]), .QN(
        n120) );
  DFFR_X1 \data_out_reg[0]  ( .D(N29), .CK(net40), .RN(rst_n), .Q(data_out[0]), 
        .QN(n130) );
  DFFR_X1 \data_out_reg[1]  ( .D(N30), .CK(net40), .RN(rst_n), .Q(data_out[1]), 
        .QN(n125) );
  DFFR_X1 \data_out_reg[2]  ( .D(N31), .CK(net40), .RN(rst_n), .Q(data_out[2]), 
        .QN(n129) );
  DFFR_X1 \data_out_reg[3]  ( .D(N32), .CK(net40), .RN(rst_n), .Q(data_out[3]), 
        .QN(n127) );
  DFFR_X1 \data_out_reg[4]  ( .D(N33), .CK(net40), .RN(rst_n), .Q(data_out[4]), 
        .QN(n126) );
  DFFR_X1 \data_out_reg[8]  ( .D(n118), .CK(net40), .RN(rst_n), .Q(data_out[8]), .QN(n121) );
  DFFS_X1 R_3 ( .D(n123), .CK(clk), .SN(rst_n), .Q(n131) );
  DFFR_X2 \data_out_reg[6]  ( .D(N35), .CK(net40), .RN(rst_n), .Q(data_out[6]), 
        .QN(n128) );
  DFFR_X1 \data_out_reg[5]  ( .D(N34), .CK(net40), .RN(rst_n), .Q(data_out[5]), 
        .QN(n18) );
  DFFR_X2 \data_out_reg[7]  ( .D(N36), .CK(net40), .RN(rst_n), .Q(data_out[7]), 
        .QN(n122) );
  DFFRS_X1 \data_out_reg[9]  ( .D(n124), .CK(net40), .RN(rst_n), .SN(1'b1), 
        .Q(data_out[9]) );
  OR2_X2 U33 ( .A1(valid_in), .A2(n131), .ZN(n16) );
  NAND2_X2 U34 ( .A1(n132), .A2(n120), .ZN(n106) );
  OR2_X2 U35 ( .A1(n75), .A2(n106), .ZN(n76) );
  BUF_X1 U36 ( .A(n79), .Z(n92) );
  AND2_X1 U38 ( .A1(n16), .A2(n119), .ZN(n132) );
  INV_X1 U39 ( .A(data_in[2]), .ZN(n97) );
  AND2_X1 U40 ( .A1(n129), .A2(n97), .ZN(n91) );
  INV_X1 U41 ( .A(data_in[3]), .ZN(n87) );
  AND2_X2 U42 ( .A1(n127), .A2(n87), .ZN(n80) );
  NOR2_X1 U43 ( .A1(n91), .A2(n80), .ZN(n21) );
  INV_X1 U44 ( .A(data_in[1]), .ZN(n107) );
  AND2_X1 U45 ( .A1(n125), .A2(n107), .ZN(n100) );
  INV_X1 U46 ( .A(n130), .ZN(n19) );
  NAND2_X1 U47 ( .A1(n19), .A2(data_in[0]), .ZN(n103) );
  OR2_X1 U48 ( .A1(n125), .A2(n107), .ZN(n101) );
  OAI21_X1 U49 ( .B1(n100), .B2(n103), .A(n101), .ZN(n78) );
  NAND2_X1 U50 ( .A1(data_out[2]), .A2(data_in[2]), .ZN(n79) );
  OR2_X1 U51 ( .A1(n87), .A2(n127), .ZN(n82) );
  OAI21_X1 U52 ( .B1(n80), .B2(n79), .A(n82), .ZN(n20) );
  AOI21_X1 U53 ( .B1(n21), .B2(n78), .A(n20), .ZN(n40) );
  INV_X1 U54 ( .A(n40), .ZN(n68) );
  NOR2_X1 U55 ( .A1(data_out[4]), .A2(data_in[4]), .ZN(n42) );
  INV_X1 U56 ( .A(data_in[5]), .ZN(n75) );
  AND2_X1 U57 ( .A1(n18), .A2(n75), .ZN(n69) );
  OR2_X1 U58 ( .A1(n42), .A2(n69), .ZN(n54) );
  INV_X1 U59 ( .A(data_in[6]), .ZN(n63) );
  AND2_X1 U60 ( .A1(n128), .A2(n63), .ZN(n31) );
  NOR2_X1 U61 ( .A1(n54), .A2(n31), .ZN(n23) );
  INV_X1 U62 ( .A(data_in[4]), .ZN(n48) );
  OR2_X1 U63 ( .A1(n126), .A2(n48), .ZN(n43) );
  NAND2_X1 U64 ( .A1(data_out[5]), .A2(data_in[5]), .ZN(n71) );
  OAI21_X1 U65 ( .B1(n69), .B2(n43), .A(n71), .ZN(n36) );
  INV_X1 U66 ( .A(n36), .ZN(n55) );
  NAND2_X1 U67 ( .A1(data_out[6]), .A2(data_in[6]), .ZN(n58) );
  OAI21_X1 U68 ( .B1(n55), .B2(n31), .A(n58), .ZN(n22) );
  AOI21_X1 U69 ( .B1(n68), .B2(n23), .A(n22), .ZN(n26) );
  INV_X1 U70 ( .A(data_in[7]), .ZN(n28) );
  AND2_X1 U71 ( .A1(n122), .A2(n28), .ZN(n34) );
  INV_X1 U72 ( .A(n34), .ZN(n24) );
  NAND2_X1 U73 ( .A1(data_out[7]), .A2(data_in[7]), .ZN(n33) );
  AND2_X1 U74 ( .A1(n24), .A2(n33), .ZN(n25) );
  XNOR2_X1 U75 ( .A(n26), .B(n25), .ZN(n27) );
  AND2_X2 U76 ( .A1(n106), .A2(n16), .ZN(n113) );
  NAND2_X1 U77 ( .A1(n27), .A2(n113), .ZN(n30) );
  OR2_X1 U78 ( .A1(n28), .A2(n106), .ZN(n29) );
  NAND2_X1 U79 ( .A1(n30), .A2(n29), .ZN(N36) );
  AND3_X1 U80 ( .A1(n16), .A2(count[1]), .A3(count[0]), .ZN(end_cnt) );
  INV_X1 U81 ( .A(end_cnt), .ZN(n123) );
  NOR2_X1 U82 ( .A1(n42), .A2(n69), .ZN(n32) );
  NOR2_X1 U83 ( .A1(n31), .A2(n34), .ZN(n37) );
  NAND2_X1 U84 ( .A1(n32), .A2(n37), .ZN(n39) );
  OAI21_X1 U85 ( .B1(n34), .B2(n58), .A(n33), .ZN(n35) );
  AOI21_X1 U86 ( .B1(n37), .B2(n36), .A(n35), .ZN(n38) );
  OAI21_X1 U87 ( .B1(n39), .B2(n40), .A(n38), .ZN(n51) );
  XNOR2_X1 U88 ( .A(n51), .B(n121), .ZN(n41) );
  AND2_X1 U89 ( .A1(n113), .A2(n41), .ZN(n118) );
  BUF_X1 U90 ( .A(n68), .Z(n46) );
  INV_X1 U91 ( .A(n42), .ZN(n67) );
  INV_X1 U92 ( .A(n43), .ZN(n66) );
  INV_X1 U93 ( .A(n66), .ZN(n44) );
  NAND2_X1 U94 ( .A1(n67), .A2(n44), .ZN(n45) );
  XNOR2_X1 U95 ( .A(n46), .B(n45), .ZN(n47) );
  NAND2_X1 U96 ( .A1(n47), .A2(n113), .ZN(n50) );
  OR2_X1 U97 ( .A1(n48), .A2(n106), .ZN(n49) );
  NAND2_X1 U98 ( .A1(n50), .A2(n49), .ZN(N33) );
  NAND2_X1 U99 ( .A1(n51), .A2(data_out[8]), .ZN(n52) );
  XNOR2_X1 U100 ( .A(n52), .B(data_out[9]), .ZN(n53) );
  AND2_X1 U101 ( .A1(n53), .A2(n113), .ZN(n124) );
  INV_X1 U102 ( .A(n54), .ZN(n57) );
  INV_X1 U103 ( .A(n55), .ZN(n56) );
  AOI21_X1 U104 ( .B1(n68), .B2(n57), .A(n56), .ZN(n61) );
  NAND2_X1 U105 ( .A1(n128), .A2(n63), .ZN(n59) );
  AND2_X1 U106 ( .A1(n59), .A2(n58), .ZN(n60) );
  XNOR2_X1 U107 ( .A(n61), .B(n60), .ZN(n62) );
  NAND2_X1 U108 ( .A1(n62), .A2(n113), .ZN(n65) );
  OR2_X1 U109 ( .A1(n63), .A2(n106), .ZN(n64) );
  NAND2_X1 U110 ( .A1(n65), .A2(n64), .ZN(N35) );
  AOI21_X1 U111 ( .B1(n68), .B2(n67), .A(n66), .ZN(n73) );
  INV_X1 U112 ( .A(n69), .ZN(n70) );
  AND2_X1 U113 ( .A1(n71), .A2(n70), .ZN(n72) );
  XNOR2_X1 U114 ( .A(n73), .B(n72), .ZN(n74) );
  NAND2_X1 U115 ( .A1(n74), .A2(n113), .ZN(n77) );
  NAND2_X1 U116 ( .A1(n77), .A2(n76), .ZN(N34) );
  INV_X1 U117 ( .A(n78), .ZN(n95) );
  OAI21_X1 U118 ( .B1(n95), .B2(n91), .A(n92), .ZN(n85) );
  BUF_X1 U119 ( .A(n80), .Z(n81) );
  INV_X1 U120 ( .A(n81), .ZN(n83) );
  NAND2_X1 U121 ( .A1(n83), .A2(n82), .ZN(n84) );
  XNOR2_X1 U122 ( .A(n85), .B(n84), .ZN(n86) );
  NAND2_X1 U123 ( .A1(n113), .A2(n86), .ZN(n89) );
  OR2_X1 U124 ( .A1(n87), .A2(n106), .ZN(n88) );
  NAND2_X1 U125 ( .A1(n89), .A2(n88), .ZN(N32) );
  AND2_X1 U126 ( .A1(n16), .A2(count[0]), .ZN(n90) );
  MUX2_X1 U127 ( .A(n90), .B(n132), .S(count[1]), .Z(N11) );
  INV_X1 U128 ( .A(n91), .ZN(n93) );
  NAND2_X1 U129 ( .A1(n93), .A2(n92), .ZN(n94) );
  XOR2_X1 U130 ( .A(n95), .B(n94), .Z(n96) );
  NAND2_X1 U131 ( .A1(n113), .A2(n96), .ZN(n99) );
  OR2_X1 U132 ( .A1(n97), .A2(n106), .ZN(n98) );
  NAND2_X1 U133 ( .A1(n99), .A2(n98), .ZN(N31) );
  INV_X1 U134 ( .A(n100), .ZN(n102) );
  NAND2_X1 U135 ( .A1(n102), .A2(n101), .ZN(n104) );
  BUF_X1 U136 ( .A(n103), .Z(n110) );
  XOR2_X1 U137 ( .A(n104), .B(n110), .Z(n105) );
  NAND2_X1 U138 ( .A1(n113), .A2(n105), .ZN(n109) );
  OR2_X1 U139 ( .A1(n107), .A2(n106), .ZN(n108) );
  NAND2_X1 U140 ( .A1(n109), .A2(n108), .ZN(N30) );
  OR2_X1 U141 ( .A1(data_out[0]), .A2(data_in[0]), .ZN(n111) );
  AND2_X1 U142 ( .A1(n111), .A2(n110), .ZN(n112) );
  NAND2_X1 U143 ( .A1(n113), .A2(n112), .ZN(n116) );
  INV_X1 U144 ( .A(data_in[0]), .ZN(n114) );
  OR2_X1 U145 ( .A1(n114), .A2(n106), .ZN(n115) );
  NAND2_X1 U146 ( .A1(n116), .A2(n115), .ZN(N29) );
endmodule

