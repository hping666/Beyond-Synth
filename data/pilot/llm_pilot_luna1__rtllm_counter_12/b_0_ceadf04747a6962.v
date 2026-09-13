`timescale 1ns/1ps
module counter_12 
(
  input rst_n,
  input clk,
  input valid_count,

  output reg [3:0] out
);

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
      out <= 4'b0000;
    else if (valid_count)
      out <= (out == 4'd11) ? 4'b0000 : out + 1'b1;
  end

endmodule
