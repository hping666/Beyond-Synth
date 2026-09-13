`timescale 1ns/1ns

module pulse_detect(    
    input clk,
    input rst_n,
    input data_in,
    output reg data_out
);

parameter s0 = 2'b00; // initial
parameter s1 = 2'b01; // 0, 00
parameter s2 = 2'b10; // 01
parameter s3 = 2'b11; // 010

reg [1:0] pulse_level1, pulse_level2;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        pulse_level1 <= s0;
    else
        pulse_level1 <= pulse_level2;
end

always @(*) begin
    case (pulse_level1)
        s0: pulse_level2 = data_in ? s0 : s1;
        s1: pulse_level2 = data_in ? s2 : s1;
        s2: pulse_level2 = data_in ? s0 : s3;
        s3: pulse_level2 = data_in ? s2 : s1;
    endcase

    if (!rst_n)
        data_out = 1'b0;
    else if ((pulse_level1 == s2) && !data_in)
        data_out = 1'b1;
    else
        data_out = 1'b0;
end

endmodule
