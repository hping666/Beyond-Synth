module right_shifter(clk, q,d);

    input clk;
    input d;
    output [7:0] q;
    reg [7:0] q;

    always @(posedge clk)
        q <= {d, q[7:1]};

endmodule
