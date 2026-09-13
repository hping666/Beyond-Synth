module serial2parallel(
	input clk,
	input rst_n,
	input din_serial,
	input din_valid,
	output reg [7:0]dout_parallel,
	output reg dout_valid
);

	reg din_tmp7;
	reg din_tmp6;
	reg din_tmp5;
	reg din_tmp4;
	reg din_tmp3;
	reg din_tmp2;
	reg din_tmp1;
	reg din_tmp0;
	reg[3:0]cnt;
	
	always@(posedge clk or negedge rst_n)begin
		if(!rst_n)
			cnt <= 0;
		else if(din_valid)
			cnt <= (cnt == 4'd8)?0:cnt+1'b1;
		else	
			cnt <= 0;
	end

	always@(posedge clk or negedge rst_n)begin
		if(!rst_n)begin
			din_tmp7 <= 1'b0;
			din_tmp6 <= 1'b0;
			din_tmp5 <= 1'b0;
			din_tmp4 <= 1'b0;
			din_tmp3 <= 1'b0;
			din_tmp2 <= 1'b0;
			din_tmp1 <= 1'b0;
			din_tmp0 <= 1'b0;
		end
		else if(din_valid && cnt <= 4'd7)begin
			din_tmp7 <= din_tmp6;
			din_tmp6 <= din_tmp5;
			din_tmp5 <= din_tmp4;
			din_tmp4 <= din_tmp3;
			din_tmp3 <= din_tmp2;
			din_tmp2 <= din_tmp1;
			din_tmp1 <= din_tmp0;
			din_tmp0 <= din_serial;
		end
	end
	
	always@(posedge clk or negedge rst_n)begin
		if(!rst_n)begin
			dout_valid <= 1'b0;
			dout_parallel <= 8'b0;
		end
		else if(cnt == 4'd8)begin
			dout_valid <= 1'b1;
			dout_parallel <= {din_tmp7,din_tmp6,din_tmp5,din_tmp4,din_tmp3,din_tmp2,din_tmp1,din_tmp0};
		end
		else begin
			dout_valid <= 1'b0;
		end
	end
	
endmodule
