// Test asset (Phase 0.6): RTLLM accu with a changed output width (data_out 12 bits instead of 10).
// Must be rejected at V1 (interface differs) before any simulation.
`timescale 1ns/1ns

module verified_accu(
    input               clk         ,
    input               rst_n       ,
    input       [7:0]   data_in     ,
    input               valid_in    ,
    output  reg         valid_out   ,
    output  reg [11:0]  data_out
);
   reg [1:0] count;
   wire ready_add = !valid_out | valid_in;
   wire end_cnt = ready_add && (count == 'd3);

   always @(posedge clk or negedge rst_n) begin
       if(!rst_n) count <= 0;
       else if(end_cnt) count <= 0;
       else if(ready_add) count <= count + 1;
   end

   always @(posedge clk or negedge rst_n) begin
      if(!rst_n) data_out <= 0;
      else if (ready_add && count == 0) data_out <= data_in;
      else if (ready_add) data_out <= data_out + data_in;
   end

   always @(posedge clk or negedge rst_n) begin
       if(!rst_n) valid_out <= 0;
       else if(end_cnt) valid_out <= 1;
       else valid_out <= 0;
   end
endmodule
