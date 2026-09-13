module signal_generator(
  input clk,
  input rst_n,
  output reg [4:0] wave
);

  reg state;

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      state <= 1'b0;
      wave <= 5'b0;
    end
    else if (state == 1'b0) begin
      if (wave == 5'b11111)
        state <= 1'b1;
      else
        wave <= wave + 1'b1;
    end
    else begin
      if (wave == 5'b00000)
        state <= 1'b0;
      else
        wave <= wave - 1'b1;
    end
  end

endmodule
