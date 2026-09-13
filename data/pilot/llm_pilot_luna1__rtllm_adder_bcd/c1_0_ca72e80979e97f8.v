module adder_bcd (
    input  [3:0] A,
    input  [3:0] B,
    input  Cin,
    output [3:0] Sum,
    output Cout
);
    wire [4:0] binary_sum;
    wire [4:0] adjusted_sum;

    assign binary_sum = A + B + Cin;
    assign adjusted_sum = (binary_sum > 5'd9) ? (binary_sum + 5'd6) : binary_sum;
    assign Sum = adjusted_sum[3:0];
    assign Cout = (binary_sum > 5'd9);
endmodule
