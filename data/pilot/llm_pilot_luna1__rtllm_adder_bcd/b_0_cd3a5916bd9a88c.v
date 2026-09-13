module adder_bcd (
    input  [3:0] A,   // First BCD number (0-9)
    input  [3:0] B,   // Second BCD number (0-9)
    input  Cin,       // Input carry
    output [3:0] Sum, // BCD sum (0-9)
    output Cout       // Output carry
);
    wire [4:0] temp_sum;
    wire [3:0] corrected_sum;
    wire carry_out;
    wire needs_correction;

    assign temp_sum = A + B + Cin;
    assign needs_correction = (temp_sum > 9);
    assign carry_out = needs_correction;
    assign corrected_sum = needs_correction ? (temp_sum + 4'b0110) : temp_sum;
    assign Sum = corrected_sum[3:0];
    assign Cout = carry_out;
endmodule
