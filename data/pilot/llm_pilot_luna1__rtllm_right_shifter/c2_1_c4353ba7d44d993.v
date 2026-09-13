module right_shifter(clk, q,d);  

    input  clk;  
    input  d;  
    output [7:0] q;  
    reg    [7:0] q;  
    reg    [7:0] state;

    always @(posedge clk)
          begin
            state <= (state >> 1);
            state[7] <= d;
            q <= state;
          end  

endmodule
