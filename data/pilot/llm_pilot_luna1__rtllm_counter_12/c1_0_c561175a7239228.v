`timescale 1ns/1ps
module counter_12 
(
  input rst_n,
  input clk,
  input valid_count,

  output reg [3:0] out
);

  reg [3:0] out_next;

  always @* begin
    out_next = out;
    if (valid_count) begin
      if (out == 4'd11) begin
        out_next = 4'b0000;
      end
      else begin
        out_next = out + 1;
      end
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      out <= 4'b0000;
    end
    else begin
      out <= out_next;
    end
  end

endmodule
