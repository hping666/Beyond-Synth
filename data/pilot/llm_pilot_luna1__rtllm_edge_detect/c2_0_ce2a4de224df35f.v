`timescale 1ns/1ns
module edge_detect(
	input clk,
	input rst_n,
	input a,
	
	output reg rise,
	output reg down
);
	reg a0;
	reg rise_stage;
	reg down_stage;

	always @(posedge clk or negedge rst_n) begin
		if (~rst_n) begin
			rise_stage <= 1'b0;
			down_stage <= 1'b0;
		end
		else begin
			if (a & ~a0) begin
				rise_stage <= 1'b1;
				down_stage <= 1'b0;
			end
			else if (~a & a0) begin
				rise_stage <= 1'b0;
				down_stage <= 1'b1;
			end
			else begin
				rise_stage <= 1'b0;
				down_stage <= 1'b0;
			end
		end
	end

	always @(posedge clk or negedge rst_n) begin
		if (~rst_n) begin
			rise <= 1'b0;
			down <= 1'b0;
		end
		else begin
			rise <= rise_stage;
			down <= down_stage;
		end
	end

	always @(posedge clk or negedge rst_n) begin
		if (~rst_n)
			a0 <= 1'b0;
		else
			a0 <= a;
	end
endmodule
