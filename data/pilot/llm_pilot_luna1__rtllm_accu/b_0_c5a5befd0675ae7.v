`timescale 1ns/1ns

module accu(
    input               clk         ,
    input               rst_n       ,
    input       [7:0]   data_in     ,
    input               valid_in     ,

    output  reg         valid_out     ,
    output  reg [9:0]   data_out
);

   reg [1:0] count;
   reg [9:0] data_out_reg;
   wire add_cnt;
   wire ready_add;
   wire end_cnt;

   assign ready_add = !valid_out | valid_in;
   assign add_cnt   = ready_add;
   assign end_cnt   = ready_add && (count == 2'd3);

   always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
         count        <= 0;
         data_out_reg <= 0;
         data_out     <= 0;
         valid_out    <= 0;
      end
      else begin
         if (end_cnt)
            count <= 0;
         else if (add_cnt)
            count <= count + 1;

         if (add_cnt && (count == 0)) begin
            data_out_reg <= data_in;
            data_out     <= data_in;
         end
         else if (add_cnt) begin
            data_out_reg <= data_out_reg + data_in;
            data_out     <= data_out + data_in;
         end

         valid_out <= end_cnt;
      end
   end

endmodule
