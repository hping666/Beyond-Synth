`timescale 1ns/1ps
module counter_12 
(
  input rst_n,
  input clk,
  input valid_count,

  output reg [3:0] out
);

  reg [3:0] count;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      count <= 4'b0000;
      out <= 4'b0000;
    end else begin
      out <= count;

      if (valid_count) begin
        if (count == 4'd11) begin
          count <= 4'b0000;
        end else begin
          count <= count + 1;
        end
      end else begin
        count <= count;
      end
    end
  end

endmodule
