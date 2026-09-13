module instr_reg (
    input clk,
    input rst,
    input [1:0] fetch,
    input [7:0] data,
    output [2:0] ins,
    output [4:0] ad1,
    output [7:0] ad2
);

    reg [7:0] ins_p1, ins_p2;
    reg [2:0] state;
    reg [2:0] ins_pipe;
    reg [4:0] ad1_pipe;
    reg [7:0] ad2_pipe;

    always @(posedge clk or negedge rst) begin
        if (!rst) begin
            ins_p1 <= 8'd0;
            ins_p2 <= 8'd0;
            ins_pipe <= 3'd0;
            ad1_pipe <= 5'd0;
            ad2_pipe <= 8'd0;
        end else begin
            ins_pipe <= ins_p1[7:5];
            ad1_pipe <= ins_p1[4:0];
            ad2_pipe <= ins_p2;
            if (fetch == 2'b01) begin
                ins_p1 <= data;
                ins_p2 <= ins_p2;
            end else if (fetch == 2'b10) begin
                ins_p1 <= ins_p1;
                ins_p2 <= data;
            end else begin
                ins_p1 <= ins_p1;
                ins_p2 <= ins_p2;
            end
        end
    end

    assign ins = ins_pipe;
    assign ad1 = ad1_pipe;
    assign ad2 = ad2_pipe;
endmodule
