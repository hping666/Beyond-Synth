module multi_16bit(
    input clk,
    input rst_n,
    input start,
    input [15:0] ain,
    input [15:0] bin,
    output [31:0] yout,
    output done
);

reg [31:0] operands_r;
reg [31:0] yout_r;
reg done_r;
reg [4:0] i;

always @(posedge clk or negedge rst_n)
    if (!rst_n) i <= 5'd0;
    else if (start && i < 5'd17) i <= i + 1'b1;
    else if (!start) i <= 5'd0;

always @(posedge clk or negedge rst_n)
    if (!rst_n) done_r <= 1'b0;
    else if (i == 5'd16) done_r <= 1'b1;
    else if (i == 5'd17) done_r <= 1'b0;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        operands_r <= 32'h00000000;
        yout_r <= 32'h00000000;
    end
    else if (start) begin
        if (i == 5'd0) begin
            operands_r <= {ain, bin};
        end
        else if (i > 5'd0 && i < 5'd17) begin
            if (operands_r[31-(i-1)])
                yout_r <= yout_r + ({16'h0000, operands_r[15:0]} << (i-1));
        end
    end
end

assign yout = yout_r;
assign done = done_r;

endmodule
