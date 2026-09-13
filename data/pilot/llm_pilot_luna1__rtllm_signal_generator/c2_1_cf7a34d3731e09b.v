module signal_generator(
  input clk,
  input rst_n,
  output reg [4:0] wave
);

  reg [1:0] state;
  reg [4:0] wave_int;
  
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      state <= 2'b0;
      wave_int <= 5'b0;
      wave <= 5'b0;
    end
    else begin
      wave <= wave_int;
      case (state)
        2'b00:
          begin
            if (wave_int == 5'b11111)
              state <= 2'b01;
            else
              wave_int <= wave_int + 1;
          end
          
        2'b01:
          begin
            if (wave_int == 5'b00000)
              state <= 2'b00;
            else
              wave_int <= wave_int - 1;
          end
      endcase
    end
  end

endmodule
