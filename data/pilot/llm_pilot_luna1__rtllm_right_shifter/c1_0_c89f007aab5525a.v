module right_shifter(clk, q,d);

    input clk;
    input d;
    output [7:0] q;
    reg [7:0] q = 8'b0;

    always @(posedge clk)
        q <= {d, q[7:1]};

endmodule
