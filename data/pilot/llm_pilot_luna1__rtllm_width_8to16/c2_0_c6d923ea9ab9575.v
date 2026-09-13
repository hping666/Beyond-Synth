`timescale 1ns/1ns
module width_8to16(
	input 				   clk 		,
	input 				   rst_n		,
	input				      valid_in	,
	input	   [7:0]		   data_in	,
 
 	output	reg			valid_out,
	output   reg [15:0]	data_out
);
reg 	[7:0]		data_lock;
reg 				flag;
reg 				valid_out_stage;
reg 	[15:0]		data_out_stage;

always @(posedge clk or negedge rst_n) begin
	if(!rst_n)
		data_lock <= 0;
	else if(valid_in && !flag)
		data_lock <= data_in;
end

always @(posedge clk or negedge rst_n) begin
	if(!rst_n)
		flag <= 0;
	else if(valid_in)
		flag <= ~flag;
end

always @(posedge clk or negedge rst_n) begin
	if(!rst_n)
		valid_out_stage <= 0;
	else if(valid_in && flag)
		valid_out_stage <= 1'b1;
	else
		valid_out_stage <= 1'b0;
end

always @(posedge clk or negedge rst_n) begin
	if(!rst_n)
		data_out_stage <= 0;
	else if(valid_in && flag)
		data_out_stage <= {data_lock, data_in};
end

always @(posedge clk or negedge rst_n) begin
	if(!rst_n) begin
		valid_out <= 0;
		data_out <= 0;
	end
	else begin
		valid_out <= valid_out_stage;
		data_out <= data_out_stage;
	end
end

endmodule
