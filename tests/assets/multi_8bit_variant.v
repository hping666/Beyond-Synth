// Test asset (Phase 0.6 V4): RTLLM multi_8bit rewritten as a direct multiplication (class (a) combinational
// rewrite). Functionally equal to /home/hping/RTLLM/Arithmetic/Multiplier/multi_8bit/verified_multi_8bit.v.
module multi_8bit (
  input [7:0] A,
  input [7:0] B,
  output reg [15:0] product
);
  always @* begin
    product = A * B;
  end
endmodule
