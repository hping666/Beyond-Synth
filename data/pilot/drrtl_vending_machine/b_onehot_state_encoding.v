// vending-machine
module vending_machine(
                    clk,
                    reset,
                    condition,
                    sel,
                    discountA,
                    discountB,
                    discountC,
                    discountD,
                    total_discount,
                    sell_signal
                    );

    // State encoding
    localparam  S0 = 11'b00000000001,
               S1 = 11'b00000000010,
               S2 = 11'b00000000100,
               S3 = 11'b00000001000,
               S4 = 11'b00000010000,
               S5 = 11'b00000100000,
               S6 = 11'b00001000000,
               S7 = 11'b00010000000,
               S8 = 11'b00100000000,
               S9 = 11'b01000000000,
               S10 = 11'b10000000000;

    parameter DATA_WIDTH = 64;
    parameter K = 16;

    input wire clk, reset, condition, sel;
    input wire [K*DATA_WIDTH-1:0] discountA, discountB, discountC, discountD;

    output reg sell_signal;
    output reg [K*DATA_WIDTH-1:0] total_discount;

    reg [10:0] next_state;
    reg [10:0] state;  // one-hot state representation for S0 to S10


    // Sequential logic for state transitions
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state <= S0;  // Reset to state S0
        end else begin
            state <= next_state;
        end
    end


   always @(*) begin
        if (sel) begin
            total_discount = discountA + discountB;
        end else begin
            total_discount = discountC + discountD;
        end
    end


    // Combinatorial logic for next state and output
    always @(*) begin
        case (state)
            S0: begin
                next_state = condition ? S2 : S1;
                sell_signal = 1'b1;
                //total_discount = discountA + discountB;
            end
            S1: begin
                next_state = condition ? S5 : S3;
                sell_signal = 1'b1;
                //total_discount = discountA + discountB;
            end
            S2: begin
                next_state = condition ? S4 : S5;
                sell_signal = 1'b0;
                //total_discount = discountC + discountD;
            end
            S3: begin
                next_state = condition ? S6 : S1;
                sell_signal = 1'b1;
                //total_discount = discountA + discountB;
            end
            S4: begin
                next_state = condition ? S2 : S5;
                sell_signal = 1'b0;
                //total_discount = discountC + discountD;
            end
            S5: begin
                next_state = condition ? S3 : S4;
                sell_signal = 1'b0;
                //total_discount = discountC + discountD;
            end
            S6: begin
                next_state = condition ? S6 : S5;
                sell_signal = 1'b0;
                //total_discount = discountC + discountD;
            end

            S7: begin
                next_state = condition ? S4 : S9;
                sell_signal = 1'b0;
                //total_discount = discountC + discountD;
            end
            S8: begin
                next_state = condition ? S6 : S10;
                sell_signal = 1'b1;
                //total_discount = discountA + discountB;
            end
            S9: begin
                next_state = condition ? S0 : S2;
                sell_signal = 1'b0;
                //total_discount = discountC + discountD;
            end
            S10: begin
                next_state = condition ? S5 : S0;
                sell_signal = 1'b1;
                //total_discount = discountA + discountB;
            end

            default: begin
                next_state = S0;
                sell_signal = 1'b0;
                //total_discount = discountC + discountD;
            end
        endcase
    end
endmodule

