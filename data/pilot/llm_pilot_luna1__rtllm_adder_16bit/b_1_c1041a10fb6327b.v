module adder_16bit (
    input wire [15:0] a,
    input wire [15:0] b,
    input wire Cin,
    output wire [15:0] y,
    output wire Co
);
    assign {Co, y} = {1'b0, a} + {1'b0, b} + Cin;
endmodule

module add8 (
    input wire [7:0] a,
    input wire [7:0] b,
    input wire Cin,
    output wire [7:0] y,
    output wire Co
);
    assign {Co, y} = {1'b0, a} + {1'b0, b} + Cin;
endmodule

module add4 (
    input wire [3:0] a,
    input wire [3:0] b,
    input wire Cin,
    output wire [3:0] y,
    output wire Co
);
    assign {Co, y} = {1'b0, a} + {1'b0, b} + Cin;
endmodule

module add2 (
    input wire [1:0] a,
    input wire [1:0] b,
    input wire Cin,
    output wire [1:0] y,
    output wire Co
);
    assign {Co, y} = {1'b0, a} + {1'b0, b} + Cin;
endmodule

module add1 (
    input wire a,
    input wire b,
    input wire Cin,
    output wire y,
    output wire Co
);
    assign y = a ^ b ^ Cin;
    assign Co = (a & b) | (a & Cin) | (b & Cin);
endmodule
