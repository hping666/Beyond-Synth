module LIFObuffer (
    input [3:0] dataIn,
    input RW,
    input EN,
    input Rst,
    input Clk,
    output reg EMPTY,
    output reg FULL,
    output reg [3:0] dataOut
);

    reg [3:0] stack_mem[0:3];
    reg [2:0] SP;
    reg [2:0] SP_next;
    reg EMPTY_next;
    reg FULL_next;
    reg [3:0] dataOut_next;
    reg write_en;
    reg read_en;
    reg [2:0] mem_addr;
    integer i;

    always @* begin
        SP_next = SP;
        FULL_next = SP ? 1'b0 : 1'b1;
        EMPTY_next = SP[2];
        dataOut_next = dataOut;
        write_en = 1'b0;
        read_en = 1'b0;
        mem_addr = SP;

        if (EN == 1'b0) begin
        end else begin
            if (Rst == 1'b1) begin
                SP_next = 3'd4;
                EMPTY_next = SP_next[2];
                dataOut_next = 4'h0;
            end else if (Rst == 1'b0) begin
                dataOut_next = 4'hx;

                if ((SP ? 1'b0 : 1'b1) == 1'b0 && RW == 1'b0) begin
                    SP_next = SP - 1'b1;
                    FULL_next = SP_next ? 1'b0 : 1'b1;
                    EMPTY_next = SP_next[2];
                    write_en = 1'b1;
                    mem_addr = SP_next;
                end else if (SP[2] == 1'b0 && RW == 1'b1) begin
                    dataOut_next = stack_mem[SP];
                    SP_next = SP + 1'b1;
                    FULL_next = SP_next ? 1'b0 : 1'b1;
                    EMPTY_next = SP_next[2];
                    read_en = 1'b1;
                end
            end
        end
    end

    always @(posedge Clk) begin
        if (EN == 1'b0) begin
        end else begin
            if (Rst == 1'b1) begin
                for (i = 0; i < 4; i = i + 1) begin
                    stack_mem[i] <= 4'h0;
                end
            end else if (Rst == 1'b0) begin
                if (write_en == 1'b1) begin
                    stack_mem[mem_addr] <= dataIn;
                end else if (read_en == 1'b1) begin
                    stack_mem[SP] <= 4'h0;
                end
            end

            SP <= SP_next;
            EMPTY <= EMPTY_next;
            FULL <= FULL_next;
            dataOut <= dataOut_next;
        end
    end
endmodule
