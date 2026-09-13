`timescale 1ns/1ns
module edge_detect(
	input clk,
	input rst_n,
	input a,
	
	output reg rise,
	output reg down
);
	reg a0;

	always @(posedge clk or negedge rst_n) begin
		if (~rst_n) begin
			rise <= 1'b0;
			down <= 1'b0;
			a0 <= 1'b0;
		end
		else begin
			if (a & ~a0) begin
				rise <= 1'b1;
				down <= 1'b0;
			end
			else if (~a & a0) begin
				rise <= 1'b0;
				down <= 1'b1;
			end
			else begin
				rise <= 1'b0;
				down <= 1'b0;
			end
			a0 <= a;
		end
	end
endmodule
