`timescale 1ns/1ns
module edge_detect(
	input clk,
	input rst_n,
	input a,
	
	output reg rise,
	output reg down
);
	reg a0;
	reg rise_next;
	reg down_next;

	always @(*) begin
		if (a & ~a0) begin
			rise_next = 1'b1;
			down_next = 1'b0;
		end
		else if (~a & a0) begin
			rise_next = 1'b0;
			down_next = 1'b1;
		end
		else begin
			rise_next = 1'b0;
			down_next = 1'b0;
		end
	end

	always @(posedge clk or negedge rst_n) begin
		if (~rst_n) begin
			rise <= 1'b0;
			down <= 1'b0;
			a0 <= 1'b0;
		end
		else begin
			rise <= rise_next;
			down <= down_next;
			a0 <= a;
		end
	end
endmodule
