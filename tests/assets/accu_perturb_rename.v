// Test asset (Phase 0.6): RTLLM accu with internal signals renamed only (a P1-type surface perturbation).
// Sequentially equivalent to /home/hping/RTLLM/Arithmetic/Accumulator/accu/verified_accu.v; ports unchanged.
`timescale 1ns/1ns

module verified_accu(
    input               clk         ,
    input               rst_n       ,
    input       [7:0]   data_in     ,
    input               valid_in    ,
    output  reg         valid_out   ,
    output  reg [9:0]   data_out
);

   reg [1:0] cnt_r;
   wire inc_en;
   wire can_add;
   wire last_cnt;
   reg [9:0]   acc_r;

   assign inc_en = can_add;
   assign last_cnt = can_add && (cnt_r == 'd3);

   always @(posedge clk or negedge rst_n) begin
       if(!rst_n) begin
          cnt_r <= 0;
       end
       else if(last_cnt) begin
          cnt_r <= 0;
       end
       else if(inc_en) begin
          cnt_r <= cnt_r + 1;
       end
   end

   always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin
        acc_r <= 0;
      end
      else if (inc_en && cnt_r == 0) begin
          acc_r <= data_in;
      end
      else if (inc_en) begin
          acc_r <= acc_r + data_in;
      end
   end

   always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin
        data_out <= 0;
      end
      else if (inc_en && cnt_r == 0) begin
          data_out <= data_in;
      end
      else if (inc_en) begin
          data_out <= data_out + data_in;
      end
   end

   assign can_add = !valid_out | valid_in;

   always @(posedge clk or negedge rst_n) begin
       if(!rst_n) begin
           valid_out <= 0;
       end
       else if(last_cnt) begin
           valid_out <= 1;
       end
       else begin
           valid_out <= 0;
       end
   end

endmodule
