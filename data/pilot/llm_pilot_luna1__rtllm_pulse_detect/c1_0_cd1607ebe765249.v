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

reg pulse_level1_bit1, pulse_level1_bit0;
reg [1:0] pulse_level2;
wire [1:0] pulse_level1;

assign pulse_level1 = {pulse_level1_bit1, pulse_level1_bit0};

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        pulse_level1_bit1 <= s0[1];
        pulse_level1_bit0 <= s0[0];
    end
    else begin
        pulse_level1_bit1 <= pulse_level2[1];
        pulse_level1_bit0 <= pulse_level2[0];
    end
end

always @(*) begin
    case (pulse_level1)
        s0: begin
            if (data_in == 0)
                pulse_level2 = s1;
            else
                pulse_level2 = s0;
        end

        s1: begin
            if (data_in == 1)
                pulse_level2 = s2;
            else
                pulse_level2 = s1;
        end

        s2: begin
            if (data_in == 0)
                pulse_level2 = s3;
            else
                pulse_level2 = s0;
        end

        s3: begin
            if (data_in == 1)
                pulse_level2 = s2;
            else
                pulse_level2 = s1;
        end
    endcase
end

always @(*) begin
    if (~rst_n)
        data_out = 0;
    else if (pulse_level1 == s2 && data_in == 0)
        data_out = 1;
    else
        data_out = 0;
end

endmodule
