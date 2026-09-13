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
reg [1:0] next_pulse_level;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        pulse_level1 <= s0;
        pulse_level2 <= s0;
    end
    else begin
        pulse_level1 <= next_pulse_level;
        pulse_level2 <= next_pulse_level;
    end
end

always @(*) begin
    case (pulse_level1)
        s0: begin
            if (data_in == 0)
                next_pulse_level = s1;
            else
                next_pulse_level = s0;
        end

        s1: begin
            if (data_in == 1)
                next_pulse_level = s2;
            else
                next_pulse_level = s1;
        end

        s2: begin
            if (data_in == 0)
                next_pulse_level = s3;
            else
                next_pulse_level = s0;
        end

        s3: begin
            if (data_in == 1)
                next_pulse_level = s2;
            else
                next_pulse_level = s1;
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
