// Test asset (Phase 0.6 V4): RTLLM multi_8bit with an injected bug (the most significant partial product is
// dropped: the loop stops at bit 6). Must be falsified by DPV and caught by simulation.
module multi_8bit (
  input [7:0] A,
  input [7:0] B,
  output reg [15:0] product
);
  reg [7:0] multiplicand;
  reg [3:0] shift_count;
  always @* begin
    product = 16'b0;
    multiplicand = A;
    shift_count = 0;
    for (int i = 0; i < 7; i = i + 1) begin   // BUG: was 8
      if (B[i] == 1) begin
        product = product + (multiplicand << shift_count);
      end
      shift_count = shift_count + 1;
    end
  end
endmodule
