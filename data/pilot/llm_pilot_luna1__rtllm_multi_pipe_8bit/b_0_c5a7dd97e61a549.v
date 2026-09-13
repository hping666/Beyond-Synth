module multi_pipe_8bit#(
    parameter size = 8
)(
          clk,
          rst_n,
          mul_a,
          mul_b,
          mul_en_in,

          mul_en_out,
          mul_out
);

   input clk;
   input rst_n;
   input mul_en_in;
   input [size-1:0] mul_a;
   input [size-1:0] mul_b;

   output reg mul_en_out;
   output reg [size*2-1:0] mul_out;

   reg [2:0] mul_en_out_reg;
   reg [7:0] mul_a_reg;
   reg [7:0] mul_b_reg;
   reg [15:0] sum_stage;
   reg [15:0] mul_out_reg;

   wire [15:0] temp0;
   wire [15:0] temp1;
   wire [15:0] temp2;
   wire [15:0] temp3;
   wire [15:0] temp4;
   wire [15:0] temp5;
   wire [15:0] temp6;
   wire [15:0] temp7;

   assign temp0 = mul_b_reg[0] ? {8'b0, mul_a_reg}       : 16'd0;
   assign temp1 = mul_b_reg[1] ? {7'b0, mul_a_reg, 1'b0} : 16'd0;
   assign temp2 = mul_b_reg[2] ? {6'b0, mul_a_reg, 2'b0} : 16'd0;
   assign temp3 = mul_b_reg[3] ? {5'b0, mul_a_reg, 3'b0} : 16'd0;
   assign temp4 = mul_b_reg[4] ? {4'b0, mul_a_reg, 4'b0} : 16'd0;
   assign temp5 = mul_b_reg[5] ? {3'b0, mul_a_reg, 5'b0} : 16'd0;
   assign temp6 = mul_b_reg[6] ? {2'b0, mul_a_reg, 6'b0} : 16'd0;
   assign temp7 = mul_b_reg[7] ? {1'b0, mul_a_reg, 7'b0} : 16'd0;

   always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
         mul_en_out_reg <= 3'd0;
         mul_en_out     <= 1'd0;
      end
      else begin
         mul_en_out_reg <= {mul_en_out_reg[1:0], mul_en_in};
         mul_en_out     <= mul_en_out_reg[2];
      end

   always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
         mul_a_reg <= 8'd0;
         mul_a_reg <= 8'd0;
      end
      else begin
         mul_a_reg <= mul_en_in ? mul_a : 8'd0;
         mul_b_reg <= mul_en_in ? mul_b : 8'd0;
      end

   always @(posedge clk or negedge rst_n)
      if (!rst_n)
         sum_stage <= 16'd0;
      else
         sum_stage <= (temp0 + temp1) + (temp2 + temp3) +
                      (temp4 + temp5) + (temp6 + temp7);

   always @(posedge clk or negedge rst_n)
      if (!rst_n)
         mul_out_reg <= 16'd0;
      else
         mul_out_reg <= sum_stage;

   always @(posedge clk or negedge rst_n)
      if (!rst_n)
         mul_out <= 'd0;
      else if (mul_en_out_reg[2])
         mul_out <= mul_out_reg;
      else
         mul_out <= 'd0;

endmodule
