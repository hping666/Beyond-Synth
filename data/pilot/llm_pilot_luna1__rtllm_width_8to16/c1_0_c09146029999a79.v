`timescale 1ns/1ns
module width_8to16(
	input 				   clk 		,
	input 				   rst_n		,
	input				      valid_in	,
	input	   [7:0]		   data_in	,
 
 	output	reg			valid_out,
	output   reg [15:0]	data_out
);
reg [8:0] state;

always @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		state     <= 9'd0;
		valid_out <= 1'd0;
		data_out  <= 16'd0;
	end else begin
		state <= {state[8] ^ valid_in,
		          (valid_in && !state[8]) ? data_in : state[7:0]};

		if (valid_in && state[8]) begin
			valid_out <= 1'd1;
			data_out  <= {state[7:0], data_in};
		end else begin
			valid_out <= 1'd0;
		end
	end
end

endmodule
