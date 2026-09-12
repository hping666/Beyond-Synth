// Test asset (Phase 0.6): RTLLM accu with an injected bug (accumulates 3 inputs instead of 4:
// the terminal count compares with 2 instead of 3). Must be caught by V2 and falsified by SEQ.
`timescale 1ns/1ns

module verified_accu(
    input               clk         ,
    input               rst_n       ,
    input       [7:0]   data_in     ,
    input               valid_in    ,
    output  reg         valid_out   ,
    output  reg [9:0]   data_out
);

   reg [1:0] count;
   wire add_cnt;
   wire ready_add;
   wire end_cnt;
   reg [9:0]   data_out_reg;

   assign add_cnt = ready_add;
   assign end_cnt = ready_add && (count == 'd2);   // BUG: was 'd3

   always @(posedge clk or negedge rst_n) begin
       if(!rst_n) begin
          count <= 0;
       end
       else if(end_cnt) begin
          count <= 0;
       end
       else if(add_cnt) begin
          count <= count + 1;
       end
   end

   always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin
        data_out_reg <= 0;
      end
      else if (add_cnt && count == 0) begin
          data_out_reg <= data_in;
      end
      else if (add_cnt) begin
          data_out_reg <= data_out_reg + data_in;
      end
   end

   always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin
        data_out <= 0;
      end
      else if (add_cnt && count == 0) begin
          data_out <= data_in;
      end
      else if (add_cnt) begin
          data_out <= data_out + data_in;
      end
   end

   assign ready_add = !valid_out | valid_in;

   always @(posedge clk or negedge rst_n) begin
       if(!rst_n) begin
           valid_out <= 0;
       end
       else if(end_cnt) begin
           valid_out <= 1;
       end
       else begin
           valid_out <= 0;
       end
   end

endmodule
