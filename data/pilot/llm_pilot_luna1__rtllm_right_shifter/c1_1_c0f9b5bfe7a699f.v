module right_shifter(clk, q,d);

    input clk;
    input d;
    output [7:0] q;
    reg [7:0] state;

    assign q = state;

    always @(posedge clk)
      begin
        state <= {d, state[7:1]};
      end

endmodule
