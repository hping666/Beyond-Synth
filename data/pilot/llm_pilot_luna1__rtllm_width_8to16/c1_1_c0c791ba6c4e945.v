`timescale 1ns/1ns
module width_8to16(
	input  				   clk 		,
	input  				   rst_n		,
	input				      valid_in	,
	input	   [7:0]		   data_in	,
 
 	output	reg			valid_out,
	output   reg [15:0]	data_out
);
reg 	[7:0]		data_lock;
reg 				flag;

always @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		data_lock <= 8'd0;
		flag      <= 1'b0;
		valid_out <= 1'b0;
		data_out  <= 16'd0;
	end
	else begin
		if (valid_in && !flag)
			data_lock <= data_in;

		if (valid_in)
			flag <= ~flag;

		if (valid_in && flag) begin
			valid_out <= 1'b1;
			data_out  <= {data_lock, data_in};
		end
		else begin
			valid_out <= 1'b0;
		end
	end
end

endmodule
