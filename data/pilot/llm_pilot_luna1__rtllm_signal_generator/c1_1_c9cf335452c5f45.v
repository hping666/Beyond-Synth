module signal_generator(
  input clk,
  input rst_n,
  output reg [4:0] wave
);

  reg [1:0] state;
  reg [1:0] state_copy;
  reg [1:0] state_next;
  reg [4:0] wave_next;

  always @* begin
    state_next = state_copy;
    wave_next = wave;

    case (state_copy)
      2'b00:
        begin
          if (wave == 5'b11111)
            state_next = 2'b01;
          else
            wave_next = wave + 1;
        end

      2'b01:
        begin
          if (wave == 5'b00000)
            state_next = 2'b00;
          else
            wave_next = wave - 1;
        end
    endcase
  end

  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      state <= 2'b0;
      state_copy <= 2'b0;
      wave <= 5'b0;
    end
    else begin
      state <= state_next;
      state_copy <= state_next;
      wave <= wave_next;
    end
  end

endmodule
