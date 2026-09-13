module right_shifter(clk, q,d);

    input  clk;
    input  d;
    output [7:0] q;
    reg    [7:0] q;
    reg    [7:0] stage = 8'b0;
    reg    [7:0] q = 8'b0;

    always @(posedge clk)
        begin
            q <= stage;
            stage <= (stage >> 1);
            stage[7] <= d;
        end

endmodule
