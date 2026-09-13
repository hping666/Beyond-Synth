module comparator_4bit(
    input [3:0] A,
    input [3:0] B,
    output A_greater,
    output A_equal,
    output A_less
);

    wire [4:0] difference;

    assign difference = {1'b0, A} - {1'b0, B};
    assign A_greater = (~difference[4]) && (difference[3:0] != 4'b0000);
    assign A_equal = (A == B);
    assign A_less = difference[4];

endmodule
