module adder_bcd (
    input  [3:0] A,
    input  [3:0] B,
    input  Cin,
    output [3:0] Sum,
    output Cout
);
    wire [4:0] temp_sum;
    wire [4:0] adjusted_sum;

    assign temp_sum = A + B + Cin;
    assign Cout = (temp_sum > 5'd9);
    assign adjusted_sum = temp_sum + 5'd6;
    assign Sum = Cout ? adjusted_sum[3:0] : temp_sum[3:0];
endmodule
