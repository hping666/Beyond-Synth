module instr_reg (
    input clk,
    input rst,
    input [1:0] fetch,
    input [7:0] data,
    output [2:0] ins,
    output [4:0] ad1,
    output [7:0] ad2
);

    reg [15:0] instr_regs;

    always @(posedge clk or negedge rst) begin
        if (!rst) begin
            instr_regs <= 16'd0;
        end else begin
            if (fetch == 2'b01) begin
                instr_regs[15:8] <= data;
            end else if (fetch == 2'b10) begin
                instr_regs[7:0] <= data;
            end
        end
    end

    assign ins = instr_regs[15:13];
    assign ad1 = instr_regs[12:8];
    assign ad2 = instr_regs[7:0];
endmodule
