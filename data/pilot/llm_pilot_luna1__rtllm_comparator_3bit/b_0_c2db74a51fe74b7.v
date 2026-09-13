module comparator_3bit (
    input [2:0] A,
    input [2:0] B,
    output A_greater,
    output A_equal,
    output A_less
);

    wire [2:0] comparison;

    assign comparison = {(A > B), (A == B), (A < B)};
    assign A_greater = comparison[2];
    assign A_equal = comparison[1];
    assign A_less = comparison[0];

endmodule
