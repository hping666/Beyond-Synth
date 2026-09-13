module fixed_point_adder #(
	//Parameterized values
	parameter Q = 15,
	parameter N = 32
	)
	(
    input [N-1:0] a,
    input [N-1:0] b,
    output [N-1:0] c
    );

reg [N-2:0] magnitude;
reg sign;

assign c = {sign, magnitude};

always @(a,b) begin
	// both negative or both positive
	if(a[N-1] == b[N-1]) begin
		magnitude = a[N-2:0] + b[N-2:0];
		sign = a[N-1];
	end
	// one of them is negative...
	else if(a[N-1] == 0 && b[N-1] == 1) begin
		if(a[N-2:0] > b[N-2:0]) begin
			magnitude = a[N-2:0] - b[N-2:0];
			sign = 0;
		end
		else begin
			magnitude = b[N-2:0] - a[N-2:0];
			if(magnitude == 0)
				sign = 0;
			else
				sign = 1;
		end
	end
	else begin
		if(a[N-2:0] > b[N-2:0]) begin
			magnitude = a[N-2:0] - b[N-2:0];
			if(magnitude == 0)
				sign = 0;
			else
				sign = 1;
		end
		else begin
			magnitude = b[N-2:0] - a[N-2:0];
			sign = 0;
		end
	end
end
endmodule
