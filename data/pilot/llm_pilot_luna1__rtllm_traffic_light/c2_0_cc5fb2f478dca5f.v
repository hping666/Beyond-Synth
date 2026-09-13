`timescale 1ns/1ns

module traffic_light
    (
        input rst_n,
        input clk,
        input pass_request,
        output wire[7:0]clock,
        output reg red,
        output reg yellow,
        output reg green
    );

    parameter idle = 2'd0,
              s1_red = 2'd1,
              s2_yellow = 2'd2,
              s3_green = 2'd3;
    reg [7:0] cnt;
    reg [1:0] state;
    reg p_red, p_yellow, p_green;
    reg red_orig, yellow_orig, green_orig;
    reg [7:0] clock_pipe;

    always @(posedge clk or negedge rst_n)
    begin
        if(!rst_n)
        begin
            state <= idle;
            p_red <= 1'b0;
            p_green <= 1'b0;
            p_yellow <= 1'b0;
        end
        else case(state)
            idle:
                begin
                    p_red <= 1'b0;
                    p_green <= 1'b0;
                    p_yellow <= 1'b0;
                    state <= s1_red;
                end
            s1_red:
                begin
                    p_red <= 1'b1;
                    p_green <= 1'b0;
                    p_yellow <= 1'b0;
                    if (cnt == 3)
                        state <= s3_green;
                    else
                        state <= s1_red;
                end
            s2_yellow:
                begin
                    p_red <= 1'b0;
                    p_green <= 1'b0;
                    p_yellow <= 1'b1;
                    if (cnt == 3)
                        state <= s1_red;
                    else
                        state <= s2_yellow;
                end
            s3_green:
                begin
                    p_red <= 1'b0;
                    p_green <= 1'b1;
                    p_yellow <= 1'b0;
                    if (cnt == 3)
                        state <= s2_yellow;
                    else
                        state <= s3_green;
                end
        endcase
    end

    always @(posedge clk or negedge rst_n)
        if(!rst_n)
            cnt <= 7'd10;
        else if (pass_request && green_orig && (cnt > 10))
            cnt <= 7'd10;
        else if (!green_orig && p_green)
            cnt <= 7'd60;
        else if (!yellow_orig && p_yellow)
            cnt <= 7'd5;
        else if (!red_orig && p_red)
            cnt <= 7'd10;
        else
            cnt <= cnt - 1;

    always @(posedge clk or negedge rst_n)
        if(!rst_n)
        begin
            red_orig <= 1'd0;
            yellow_orig <= 1'd0;
            green_orig <= 1'd0;
        end
        else
        begin
            yellow_orig <= p_yellow;
            red_orig <= p_red;
            green_orig <= p_green;
        end

    always @(posedge clk or negedge rst_n)
        if(!rst_n)
        begin
            clock_pipe <= 8'd10;
            red <= 1'd0;
            yellow <= 1'd0;
            green <= 1'd0;
        end
        else
        begin
            clock_pipe <= cnt;
            red <= red_orig;
            yellow <= yellow_orig;
            green <= green_orig;
        end

    assign clock = clock_pipe;

endmodule
