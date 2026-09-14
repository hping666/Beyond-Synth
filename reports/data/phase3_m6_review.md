# M6 manual validation sample (DECISIONS 2026-09-14 a)

Classes (spec 04 §A.1): (a) logic-level simplification, registers untouched; (b) restructuring of combinational / control logic with the register set unchanged; (c1) retiming: registers moved / split / merged / duplicated at equal latency; (c2) latency change; (d) micro-architectural change: the operator set or the dataflow topology changes. For every sampled candidate the human class goes into reports/data/phase3_m6_human.json.

## 1. cec41e65ae2f127 — rtllm_multi_pipe_8bit — gpt-5.6-luna — requested c1 -> rule d — label tradeoff

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5052)"]

```diff
--- D
+++ C
@@ -2,91 +2,86 @@
     parameter size = 8
 )(
-          clk,      
-          rst_n,       
-          mul_a,       
-          mul_b, 
-          mul_en_in,
- 
-          mul_en_out,      
-          mul_out    
+    clk,
+    rst_n,
+    mul_a,
+    mul_b,
+    mul_en_in,
+    mul_en_out,
+    mul_out
 );
- 
-   input clk;           
-   input rst_n; 
-   input mul_en_in;      
-   input [size-1:0] mul_a;       
-   input [size-1:0] mul_b;       
- 
-   output reg mul_en_out;  
-   output reg [size*2-1:0] mul_out;    
- 
-            
+
+   input clk;
+   input rst_n;
+   input mul_en_in;
+   input [size-1:0] mul_a;
+   input [size-1:0] mul_b;
+
+   output reg mul_en_out;
+   output reg [size*2-1:0] mul_out;
+
    reg [2:0] mul_en_out_reg;
- always@(posedge clk or negedge rst_n)
-       if(!rst_n)begin
-            mul_en_out_reg <= 'd0;             
-            mul_en_out     <= 'd0;                           
-       end
-       else begin
-            mul_en_out_reg <= {mul_en_out_reg[1:0],mul_en_in};            
-            mul_en_out     <= mul_en_out_reg[2];                  
-       end
- 
- 
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
-  always @(posedge clk or negedge rst_n)
-         if(!rst_n) begin
-              mul_a_reg <= 'd0;
-              mul_a_reg <= 'd0;
-         end
-         else begin
-              mul_a_reg <= mul_en_in ? mul_a :'d0;
-              mul_b_reg <= mul_en_in ? mul_b :'d0;
-         end
- 
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
-       else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
-       end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
- 
- 
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out <= 'd0;
-       else if(mul_en_out_reg[2])
-          mul_out <= mul_out_reg;
-       else
-          mul_out <= 'd0;
- 
-          
+   reg [7:0] mul_a_reg;
+   reg [7:0] mul_b_reg;
+   reg [15:0] product_sum;
+   reg [15:0] mul_out_reg;
+
+   wire [15:0] temp [7:0];
+
+   assign temp[0] = mul_b_reg[0] ? {8'b0, mul_a_reg} : 16'b0;
+   assign temp[1] = mul_b_reg[1] ? {7'b0, mul_a_reg, 1'b0} : 16'b0;
+   assign temp[2] = mul_b_reg[2] ? {6'b0, mul_a_reg, 2'b0} : 16'b0;
+   assign temp[3] = mul_b_reg[3] ? {5'b0, mul_a_reg, 3'b0} : 16'b0;
+   assign temp[4] = mul_b_reg[4] ? {4'b0, mul_a_reg, 4'b0} : 16'b0;
+   assign temp[5] = mul_b_reg[5] ? {3'b0, mul_a_reg, 5'b0} : 16'b0;
+   assign temp[6] = mul_b_reg[6] ? {2'b0, mul_a_reg, 6'b0} : 16'b0;
+   assign temp[7] = mul_b_reg[7] ? {1'b0, mul_a_reg, 7'b0} : 16'b0;
+
+   always @(posedge clk or negedge rst_n) begin
+      if (!rst_n) begin
+         mul_en_out_reg <= 3'b0;
+         mul_en_out <= 1'b0;
+      end
+      else begin
+         mul_en_out_reg <= {mul_en_out_reg[1:0], mul_en_in};
+         mul_en_out <= mul_en_out_reg[2];
+      end
+   end
+
+   always @(posedge clk or negedge rst_n) begin
+      if (!rst_n) begin
+         mul_a_reg <= 8'b0;
+         mul_b_reg <= 8'b0;
+      end
+      else begin
+         mul_a_reg <= mul_en_in ? mul_a : 8'b0;
+         mul_b_reg <= mul_en_in ? mul_b : 8'b0;
+      end
+   end
+
+   always @(posedge clk or negedge rst_n) begin
+      if (!rst_n)
+         product_sum <= 16'b0;
+      else
+         product_sum <= (temp[0] + temp[1]) +
+                        (temp[2] + temp[3]) +
+                        (temp[4] + temp[5]) +
+                        (temp[6] + temp[7]);
+   end
+
+   always @(posedge clk or negedge rst_n) begin
+      if (!rst_n)
+         mul_out_reg <= 16'b0;
+      else
+         mul_out_reg <= product_sum;
+   end
+
+   always @(posedge clk or negedge rst_n) begin
+      if (!rst_n)
+         mul_out <= {size*2{1'b0}};
+      else if (mul_en_out_reg[2])
+         mul_out <= mul_out_reg;
+      else
+         mul_out <= {size*2{1'b0}};
+   end
+
 endmodule
```

## 2. c8ce03d085d2b2b — rtllm_multi_pipe_8bit — gpt-5.4-mini — requested free -> rule d — label retained

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5174)"]

```diff
--- D
+++ C
@@ -21,6 +21,34 @@
    output reg [size*2-1:0] mul_out;    
  
-            
    reg [2:0] mul_en_out_reg;
+   reg [size-1:0] mul_a_reg;
+   reg [size-1:0] mul_b_reg;
+   reg [size*2-1:0] mul_prod_reg;
+   reg [size*2-1:0] mul_out_reg;
+
+   wire [3:0] a_lo;
+   wire [3:0] a_hi;
+   wire [3:0] b_lo;
+   wire [3:0] b_hi;
+   wire [7:0] pp00;
+   wire [7:0] pp01;
+   wire [7:0] pp10;
+   wire [7:0] pp11;
+   wire [8:0] pp_mid;
+   wire [15:0] prod_next;
+
+   assign a_lo = mul_a_reg[3:0];
+   assign a_hi = mul_a_reg[7:4];
+   assign b_lo = mul_b_reg[3:0];
+   assign b_hi = mul_b_reg[7:4];
+
+   assign pp00 = a_lo * b_lo;
+   assign pp01 = a_lo * b_hi;
+   assign pp10 = a_hi * b_lo;
+   assign pp11 = a_hi * b_hi;
+
+   assign pp_mid = {1'b0, pp01} + {1'b0, pp10};
+   assign prod_next = {8'b0, pp00} + {3'b0, pp_mid, 4'b0} + {pp11, 8'b0};
+
  always@(posedge clk or negedge rst_n)
        if(!rst_n)begin
@@ -34,10 +62,8 @@
  
  
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
   always @(posedge clk or negedge rst_n)
          if(!rst_n) begin
               mul_a_reg <= 'd0;
-              mul_a_reg <= 'd0;
+              mul_b_reg <= 'd0;
          end
          else begin
@@ -45,39 +71,16 @@
               mul_b_reg <= mul_en_in ? mul_b :'d0;
          end
- 
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
-       else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
-       end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
+
+   always @(posedge clk or negedge rst_n) 
+       if(!rst_n)
+          mul_prod_reg <= 'd0;
+       else
+          mul_prod_reg <= prod_next;
+
+   always @(posedge clk or negedge rst_n) 
        if(!rst_n)
           mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
- 
+       else
+          mul_out_reg <= mul_prod_reg;
  
  always @(posedge clk or negedge rst_n) 
```

## 3. c7c5dc0bae9acca — rtllm_LIFObuffer — gpt-5.4-mini — requested b -> rule d — label nonequiv

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5391)"]

```diff
--- D
+++ C
@@ -12,38 +12,84 @@
     reg [3:0] stack_mem[0:3];
     reg [2:0] SP;
-    integer i;
 
     always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
-                SP = 3'd4;
-                EMPTY = SP[2];
-                dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
-                end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
+        if (EN) begin
+            if (Rst) begin
+                SP <= 3'd4;
+                EMPTY <= 1'b1;
+                dataOut <= 4'h0;
+                stack_mem[0] <= 4'h0;
+                stack_mem[1] <= 4'h0;
+                stack_mem[2] <= 4'h0;
+                stack_mem[3] <= 4'h0;
             end else begin
-                // Do nothing if neither condition is met
+                case (SP)
+                    3'd4: begin
+                        FULL <= 1'b0;
+                        EMPTY <= 1'b1;
+                        dataOut <= 4'hx;
+                        if (RW == 1'b0) begin
+                            SP <= 3'd3;
+                            EMPTY <= 1'b0;
+                            stack_mem[3] <= dataIn;
+                        end
+                    end
+                    3'd3: begin
+                        FULL <= 1'b0;
+                        EMPTY <= 1'b0;
+                        dataOut <= 4'hx;
+                        if (RW == 1'b0) begin
+                            SP <= 3'd2;
+                            stack_mem[2] <= dataIn;
+                        end else if (RW == 1'b1) begin
+                            SP <= 3'd4;
+                            EMPTY <= 1'b1;
+                            dataOut <= stack_mem[3];
+                            stack_mem[3] <= 4'h0;
+                        end
+                    end
+                    3'd2: begin
+                        FULL <= 1'b0;
+                        EMPTY <= 1'b0;
+                        dataOut <= 4'hx;
+                        if (RW == 1'b0) begin
+                            SP <= 3'd1;
+                            stack_mem[1] <= dataIn;
+                        end else if (RW == 1'b1) begin
+                            SP <= 3'd3;
+                            dataOut <= stack_mem[2];
+                            stack_mem[2] <= 4'h0;
+                        end
+                    end
+                    3'd1: begin
+                        FULL <= 1'b0;
+                        EMPTY <= 1'b0;
+                        dataOut <= 4'hx;
+                        if (RW == 1'b0) begin
+                            SP <= 3'd0;
+                            stack_mem[0] <= dataIn;
+                        end else if (RW == 1'b1) begin
+                            SP <= 3'd2;
+                            dataOut <= stack_mem[1];
+                            stack_mem[1] <= 4'h0;
+                        end
+                    end
+                    3'd0: begin
+                        FULL <= 1'b1;
+                        EMPTY <= 1'b0;
+                        dataOut <= 4'hx;
+                        if (RW == 1'b1) begin
+                            SP <= 3'd1;
+                            FULL <= 1'b0;
+                            dataOut <= stack_mem[0];
+                            stack_mem[0] <= 4'h0;
+                        end
+                    end
+                    default: begin
+                        FULL <= 1'b0;
+                        EMPTY <= 1'b1;
+                        dataOut <= 4'hx;
+                    end
+                endcase
             end
         end
```

## 4. ca80c2c0c8d77fc — rtllm_traffic_light — gpt-5.4 — requested d -> rule d — label nonequiv

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.599)"]

```diff
--- D
+++ C
@@ -12,90 +12,76 @@
     );
 	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
-				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
+	parameter 	idle = 2'b00,
+				s1_red = 2'b01,
+				s2_yellow = 2'b10,
+				s3_green = 2'b11;
 
+	reg [1:0] phase;
+	reg [5:0] cnt;
 
-always @(posedge clk or negedge rst_n) 
-    begin
-        if(!rst_n)
-        begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
-        end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
+	wire cnt_eq_1;
+	wire cnt_eq_8;
+	wire cnt_gt_10;
+
+	assign cnt_eq_1 = (~|cnt[5:1]) & cnt[0];
+	assign cnt_eq_8 = (~|cnt[5:4]) & cnt[3] & (~|cnt[2:0]);
+	assign cnt_gt_10 = cnt[5] | cnt[4] | (cnt[3] & (cnt[2] | cnt[0]));
+	assign clock = {2'b00, cnt};
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			phase <= idle;
+			cnt <= 6'd10;
+		end
+		else begin
+			case (phase)
+				idle: begin
+					if (cnt_eq_8) begin
+						phase <= s1_red;
+						cnt <= 6'd10;
+					end
+					else begin
+						cnt <= cnt - 6'd1;
+					end
+				end
+				s3_green: begin
+					if (pass_request && cnt_gt_10) begin
+						cnt <= 6'd10;
+					end
+					else if (cnt_eq_1) begin
+						phase <= s2_yellow;
+						cnt <= 6'd5;
+					end
+					else begin
+						cnt <= cnt - 6'd1;
+					end
+				end
+				s2_yellow: begin
+					if (cnt_eq_1) begin
+						phase <= s1_red;
+						cnt <= 6'd10;
+					end
+					else begin
+						cnt <= cnt - 6'd1;
+					end
+				end
+				default: begin
+					if (cnt_eq_1) begin
+						phase <= s3_green;
+						cnt <= 6'd60;
+					end
+					else begin
+						cnt <= cnt - 6'd1;
+					end
+				end
+			endcase
+		end
 	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+	always @(*) begin
+		red = (~phase[1]) & phase[0];
+		yellow = phase[1] & (~phase[0]);
+		green = phase[1] & phase[0];
+	end
 
 endmodule
```

## 5. cceb649a2c0c4ed — rtllm_traffic_light — gpt-5.6-terra — requested b -> rule d — label nonequiv

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.6088)"]

```diff
--- D
+++ C
@@ -3,99 +3,78 @@
 module traffic_light
     (
-		input rst_n, 
-      input clk, 
-      input pass_request,
-		  output wire[7:0]clock,
-      output reg red,
-		  output reg yellow,
-		  output reg green
+        input rst_n, 
+        input clk, 
+        input pass_request,
+        output wire[7:0]clock,
+        output reg red,
+        output reg yellow,
+        output reg green
     );
-	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
-				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+    parameter idle      = 2'd0,
+              s1_red    = 2'd1,
+              s2_yellow = 2'd2,
+              s3_green  = 2'd3;
 
-always @(posedge clk or negedge rst_n) 
+    reg [5:0] cnt;
+    reg [1:0] out_state;
+
+    wire is_idle;
+    wire is_red;
+    wire is_yellow;
+    wire is_green;
+    wire cnt_is_one;
+    wire cnt_is_eight;
+    wire cnt_gt_ten;
+    wire phase_done;
+    wire [5:0] phase_reload;
+
+    assign is_idle   = ~out_state[1] & ~out_state[0];
+    assign is_red    = ~out_state[1] &  out_state[0];
+    assign is_yellow =  out_state[1] & ~out_state[0];
+    assign is_green  =  out_state[1] &  out_state[0];
+
+    assign cnt_is_one   = ~cnt[5] & ~cnt[4] & ~cnt[3] & ~cnt[2] & ~cnt[1] & cnt[0];
+    assign cnt_is_eight = ~cnt[5] & ~cnt[4] & ~cnt[3] &  cnt[2] & ~cnt[1] & ~cnt[0];
+    assign cnt_gt_ten   = cnt[5] | cnt[4] | (cnt[3] & (cnt[2] | (cnt[1] & cnt[0])));
+    assign phase_done   = ~is_idle & cnt_is_one;
+
+    assign phase_reload = {is_red, is_red, ~is_green, is_green, is_yellow, is_green};
+
+    always @(posedge clk or negedge rst_n)
     begin
-        if(!rst_n)
+        if (!rst_n)
+            out_state <= idle;
+        else if (is_idle)
         begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
+            if (cnt_is_eight)
+                out_state <= s1_red;
         end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
-	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
+        else if (cnt_is_one)
+            out_state <= {out_state[0], out_state[1] ^ out_state[0]};
+    end
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+    always @(posedge clk or negedge rst_n)
+    begin
+        if (!rst_n)
+            cnt <= 6'd10;
+        else if (pass_request && is_green && cnt_gt_ten)
+            cnt <= 6'd10;
+        else if (is_idle && cnt_is_eight)
+            cnt <= 6'd10;
+        else if (phase_done)
+            cnt <= phase_reload;
+        else
+            cnt <= cnt - 6'd1;
+    end
+
+    always @*
+    begin
+        red = is_red;
+        yellow = is_yellow;
+        green = is_green;
+    end
+
+    assign clock = {2'b00, cnt};
 
 endmodule
```

## 6. c42c484df1483b2 — rtllm_multi_pipe_8bit — gpt-5.4-mini — requested c1 -> rule d — label retained

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.501)"]

```diff
--- D
+++ C
@@ -20,73 +20,57 @@
    output reg mul_en_out;  
    output reg [size*2-1:0] mul_out;    
- 
-            
-   reg [2:0] mul_en_out_reg;
- always@(posedge clk or negedge rst_n)
-       if(!rst_n)begin
-            mul_en_out_reg <= 'd0;             
-            mul_en_out     <= 'd0;                           
+
+   reg [2:0] mul_en_pipe;
+   reg [size-1:0] mul_a_reg;
+   reg [size-1:0] mul_b_reg;
+   reg [size*2-1:0] prod_s1;
+   reg [size*2-1:0] prod_s2;
+   wire [size*2-1:0] prod_comb;
+
+   assign prod_comb = mul_a_reg * mul_b_reg;
+
+   always @(posedge clk or negedge rst_n)
+       if(!rst_n) begin
+            mul_en_pipe <= 3'd0;
+            mul_en_out  <= 1'b0;
        end
        else begin
-            mul_en_out_reg <= {mul_en_out_reg[1:0],mul_en_in};            
-            mul_en_out     <= mul_en_out_reg[2];                  
+            mul_en_pipe <= {mul_en_pipe[1:0], mul_en_in};
+            mul_en_out  <= mul_en_pipe[2];
        end
- 
- 
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
-  always @(posedge clk or negedge rst_n)
-         if(!rst_n) begin
-              mul_a_reg <= 'd0;
-              mul_a_reg <= 'd0;
-         end
-         else begin
-              mul_a_reg <= mul_en_in ? mul_a :'d0;
-              mul_b_reg <= mul_en_in ? mul_b :'d0;
-         end
- 
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
+
+   always @(posedge clk or negedge rst_n)
        if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
+            mul_a_reg <= 'd0;
+            mul_b_reg <= 'd0;
+       end
        else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
+            mul_a_reg <= mul_en_in ? mul_a : 'd0;
+            mul_b_reg <= mul_en_in ? mul_b : 'd0;
        end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
+
+   always @(posedge clk or negedge rst_n)
        if(!rst_n)
-          mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
- 
- 
- always @(posedge clk or negedge rst_n) 
+            prod_s1 <= 'd0;
+       else if(mul_en_pipe[0])
+            prod_s1 <= prod_comb;
+       else
+            prod_s1 <= 'd0;
+
+   always @(posedge clk or negedge rst_n)
        if(!rst_n)
-          mul_out <= 'd0;
-       else if(mul_en_out_reg[2])
-          mul_out <= mul_out_reg;
+            prod_s2 <= 'd0;
+       else if(mul_en_pipe[1])
+            prod_s2 <= prod_s1;
        else
-          mul_out <= 'd0;
- 
-          
+            prod_s2 <= 'd0;
+
+   always @(posedge clk or negedge rst_n)
+       if(!rst_n)
+            mul_out <= 'd0;
+       else if(mul_en_pipe[2])
+            mul_out <= prod_s2;
+       else
+            mul_out <= 'd0;
+
 endmodule
```

## 7. cb1f43266f06ad1 — rtllm_multi_pipe_8bit — gpt-5.4-mini — requested c1 -> rule d — label tradeoff

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5719)"]

```diff
--- D
+++ C
@@ -20,73 +20,60 @@
    output reg mul_en_out;  
    output reg [size*2-1:0] mul_out;    
- 
-            
-   reg [2:0] mul_en_out_reg;
- always@(posedge clk or negedge rst_n)
-       if(!rst_n)begin
-            mul_en_out_reg <= 'd0;             
-            mul_en_out     <= 'd0;                           
-       end
-       else begin
-            mul_en_out_reg <= {mul_en_out_reg[1:0],mul_en_in};            
-            mul_en_out     <= mul_en_out_reg[2];                  
-       end
- 
- 
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
-  always @(posedge clk or negedge rst_n)
-         if(!rst_n) begin
-              mul_a_reg <= 'd0;
-              mul_a_reg <= 'd0;
+
+   localparam W = size*2;
+   localparam HALF = size/2;
+
+   reg [2:0] valid_pipe;
+   reg [W-1:0] operand_pipe;
+
+   wire [size-1:0] mul_a_reg;
+   wire [size-1:0] mul_b_reg;
+   assign mul_a_reg = operand_pipe[W-1:size];
+   assign mul_b_reg = operand_pipe[size-1:0];
+
+   wire [W-1:0] temp [0:size-1];
+   genvar i;
+   generate
+      for (i = 0; i < size; i = i + 1) begin : gen_temp
+         assign temp[i] = mul_b_reg[i] ? ({ {(size-i){1'b0}}, mul_a_reg, {i{1'b0}} }) : {W{1'b0}};
+      end
+   endgenerate
+
+   reg [W-1:0] sum [0:HALF-1];
+   reg [W-1:0] mul_out_reg;
+   integer j;
+
+   always @(posedge clk or negedge rst_n) begin
+      if (!rst_n) begin
+         valid_pipe   <= 3'b000;
+         mul_en_out   <= 1'b0;
+         operand_pipe <= {W{1'b0}};
+         for (j = 0; j < HALF; j = j + 1)
+            sum[j] <= {W{1'b0}};
+         mul_out_reg  <= {W{1'b0}};
+         mul_out      <= {W{1'b0}};
+      end else begin
+         valid_pipe   <= {valid_pipe[1:0], mul_en_in};
+         mul_en_out   <= valid_pipe[2];
+
+         if (mul_en_in)
+            operand_pipe <= {mul_a, mul_b};
+
+         if (valid_pipe[0]) begin
+            sum[0] <= temp[0] + temp[1];
+            sum[1] <= temp[2] + temp[3];
+            sum[2] <= temp[4] + temp[5];
+            sum[3] <= temp[6] + temp[7];
          end
-         else begin
-              mul_a_reg <= mul_en_in ? mul_a :'d0;
-              mul_b_reg <= mul_en_in ? mul_b :'d0;
-         end
- 
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
-       else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
-       end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
- 
- 
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out <= 'd0;
-       else if(mul_en_out_reg[2])
-          mul_out <= mul_out_reg;
-       else
-          mul_out <= 'd0;
- 
-          
+
+         if (valid_pipe[1])
+            mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
+
+         if (valid_pipe[2])
+            mul_out <= mul_out_reg;
+         else
+            mul_out <= {W{1'b0}};
+      end
+   end
+
 endmodule
```

## 8. c14561fddb8ff50 — rtllm_LIFObuffer — gpt-5.4-mini — requested d -> rule d — label nonequiv

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5763)"]

```diff
--- D
+++ C
@@ -10,40 +10,85 @@
 );
 
-    reg [3:0] stack_mem[0:3];
-    reg [2:0] SP;
-    integer i;
+    reg [3:0] s0;
+    reg [3:0] s1;
+    reg [3:0] s2;
+    reg [3:0] s3;
+    reg [2:0] count;
 
     always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
-                SP = 3'd4;
-                EMPTY = SP[2];
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
+                count = 3'd0;
+                s0 = 4'h0;
+                s1 = 4'h0;
+                s2 = 4'h0;
+                s3 = 4'h0;
+                EMPTY = 1'b1;
                 dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
+            end else begin
+                dataOut = 4'hx;
+
+                if ((RW == 1'b0) && (count != 3'd4)) begin
+                    case (count)
+                        3'd0: begin
+                            s0 = dataIn;
+                            count = 3'd1;
+                        end
+                        3'd1: begin
+                            s1 = s0;
+                            s0 = dataIn;
+                            count = 3'd2;
+                        end
+                        3'd2: begin
+                            s2 = s1;
+                            s1 = s0;
+                            s0 = dataIn;
+                            count = 3'd3;
+                        end
+                        3'd3: begin
+                            s3 = s2;
+                            s2 = s1;
+                            s1 = s0;
+                            s0 = dataIn;
+                            count = 3'd4;
+                        end
+                        default: begin
+                        end
+                    endcase
+                end else if ((RW == 1'b1) && (count != 3'd0)) begin
+                    case (count)
+                        3'd1: begin
+                            dataOut = s0;
+                            s0 = 4'h0;
+                            count = 3'd0;
+                        end
+                        3'd2: begin
+                            dataOut = s1;
+                            s0 = s1;
+                            s1 = 4'h0;
+                            count = 3'd1;
+                        end
+                        3'd3: begin
+                            dataOut = s2;
+                            s0 = s1;
+                            s1 = s2;
+                            s2 = 4'h0;
+                            count = 3'd2;
+                        end
+                        3'd4: begin
+                            dataOut = s3;
+                            s0 = s1;
+                            s1 = s2;
+                            s2 = s3;
+                            s3 = 4'h0;
+                            count = 3'd3;
+                        end
+                        default: begin
+                        end
+                    endcase
                 end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
+
+                FULL = (count == 3'd4);
+                EMPTY = (count == 3'd0);
             end
         end
```

## 9. c85fb633c516eb0 — rtllm_traffic_light — gpt-5.4 — requested b -> rule d — label retained

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5217)"]

```diff
--- D
+++ C
@@ -16,86 +16,77 @@
 				s2_yellow = 2'd2,
 				s3_green = 2'd3;
-	reg [7:0] cnt;
+
+	reg [5:0] cnt;
 	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+	wire cnt_is_1;
+	wire cnt_is_8;
+	wire cnt_gt_10;
+	wire [5:0] cnt_dec;
 
-always @(posedge clk or negedge rst_n) 
-    begin
-        if(!rst_n)
-        begin
+	assign cnt_is_1 = (~|cnt[5:1]) & cnt[0];
+	assign cnt_is_8 = cnt[3] & (~|{cnt[5:4], cnt[2:0]});
+	assign cnt_gt_10 = cnt[5] | cnt[4] | (cnt[3] & (cnt[2] | (cnt[1] & cnt[0])));
+	assign cnt_dec = cnt - 6'd1;
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n)
 			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
-        end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
+		else begin
+			case (state)
+				idle:
+					if (cnt_is_8)
+						state <= s1_red;
+				s1_red:
+					if (cnt_is_1)
+						state <= s3_green;
+				s2_yellow:
+					if (cnt_is_1)
+						state <= s1_red;
+				s3_green:
+					if (cnt_is_1)
+						state <= s2_yellow;
+			endcase
+		end
 	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n)
+			cnt <= 6'd10;
+		else begin
+			case (state)
+				idle:
+					if (cnt_is_8)
+						cnt <= 6'd10;
+					else
+						cnt <= cnt_dec;
+				s1_red:
+					if (cnt_is_1)
+						cnt <= 6'd60;
+					else
+						cnt <= cnt_dec;
+				s2_yellow:
+					if (cnt_is_1)
+						cnt <= 6'd10;
+					else
+						cnt <= cnt_dec;
+				s3_green:
+					if (pass_request && cnt_gt_10)
+						cnt <= 6'd10;
+					else if (cnt_is_1)
+						cnt <= 6'd5;
+					else
+						cnt <= cnt_dec;
+			endcase
+		end
+	end
+
+	assign clock = {2'b00, cnt};
+
+	always @* begin
+		red = (~state[1]) & state[0];
+		yellow = state[1] & (~state[0]);
+		green = state[1] & state[0];
+	end
 
 endmodule
```

## 10. cd0f6fcc131a590 — rtllm_LIFObuffer — gpt-5.6-luna — requested c1 -> rule d — label tradeoff

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.6496)"]

```diff
--- D
+++ C
@@ -12,38 +12,75 @@
     reg [3:0] stack_mem[0:3];
     reg [2:0] SP;
+    reg [2:0] SP_next;
+    reg EMPTY_next;
+    reg FULL_next;
+    reg [3:0] dataOut_next;
+    reg push_next;
+    reg pop_next;
     integer i;
 
-    always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
-                SP = 3'd4;
-                EMPTY = SP[2];
-                dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
+    always @* begin
+        SP_next = SP;
+        EMPTY_next = EMPTY;
+        FULL_next = FULL;
+        dataOut_next = dataOut;
+        push_next = 1'b0;
+        pop_next = 1'b0;
+
+        if (EN) begin
+            if (Rst) begin
+                SP_next = 3'd4;
+                EMPTY_next = 1'b1;
+                dataOut_next = 4'h0;
+            end else begin
+                dataOut_next = 4'hx;
+                FULL_next = (SP == 3'd0);
+                EMPTY_next = SP[2];
+
+                if (!RW && (SP != 3'd0)) begin
+                    push_next = 1'b1;
+                    case (SP)
+                        3'd1: SP_next = 3'd0;
+                        3'd2: SP_next = 3'd1;
+                        3'd3: SP_next = 3'd2;
+                        3'd4: SP_next = 3'd3;
+                        default: SP_next = SP;
+                    endcase
+                    FULL_next = (SP_next == 3'd0);
+                    EMPTY_next = SP_next[2];
+                end else if (RW && !SP[2]) begin
+                    pop_next = 1'b1;
+                    dataOut_next = stack_mem[SP[1:0]];
+                    case (SP)
+                        3'd0: SP_next = 3'd1;
+                        3'd1: SP_next = 3'd2;
+                        3'd2: SP_next = 3'd3;
+                        3'd3: SP_next = 3'd4;
+                        default: SP_next = SP;
+                    endcase
+                    FULL_next = (SP_next == 3'd0);
+                    EMPTY_next = SP_next[2];
                 end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
+            end
+        end
+    end
+
+    always @(posedge Clk) begin
+        if (EN) begin
+            if (Rst) begin
+                SP <= 3'd4;
+                EMPTY <= 1'b1;
+                dataOut <= 4'h0;
+                for (i = 0; i < 4; i = i + 1)
+                    stack_mem[i] <= 4'h0;
             end else begin
-                // Do nothing if neither condition is met
+                SP <= SP_next;
+                EMPTY <= EMPTY_next;
+                FULL <= FULL_next;
+                dataOut <= dataOut_next;
+                if (push_next)
+                    stack_mem[SP_next[1:0]] <= dataIn;
+                else if (pop_next)
+                    stack_mem[SP[1:0]] <= 4'h0;
             end
         end
```

## 11. c91f0a15d3f07ec — rtllm_LIFObuffer — gpt-5.6-terra — requested b -> rule d — label retained

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.6221)"]

```diff
--- D
+++ C
@@ -10,40 +10,82 @@
 );
 
-    reg [3:0] stack_mem[0:3];
+    reg [3:0] stack0;
+    reg [3:0] stack1;
+    reg [3:0] stack2;
+    reg [3:0] stack3;
     reg [2:0] SP;
-    integer i;
 
-    always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
+    wire do_push;
+    wire do_pop;
+
+    assign do_push = (SP != 3'd0) && (RW == 1'b0);
+    assign do_pop  = (SP[2] == 1'b0) && (RW == 1'b1);
+
+    always @(*) begin
+        EMPTY = SP[2];
+    end
+
+    always @(posedge Clk) begin
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
                 SP = 3'd4;
-                EMPTY = SP[2];
                 dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
+                stack0 = 4'h0;
+                stack1 = 4'h0;
+                stack2 = 4'h0;
+                stack3 = 4'h0;
+            end else if (Rst == 1'b0) begin
+                if (do_push) begin
+                    FULL = (SP == 3'd1);
+                    case (SP)
+                        3'd1: begin
+                            SP = 3'd0;
+                            stack0 = dataIn;
+                        end
+                        3'd2: begin
+                            SP = 3'd1;
+                            stack1 = dataIn;
+                        end
+                        3'd3: begin
+                            SP = 3'd2;
+                            stack2 = dataIn;
+                        end
+                        3'd4: begin
+                            SP = 3'd3;
+                            stack3 = dataIn;
+                        end
+                        3'd5: SP = 3'd4;
+                        3'd6: SP = 3'd5;
+                        default: SP = 3'd6;
+                    endcase
+                    dataOut = 4'hx;
+                end else if (do_pop) begin
+                    FULL = 1'b0;
+                    case (SP)
+                        3'd0: begin
+                            dataOut = stack0;
+                            stack0 = 4'h0;
+                            SP = 3'd1;
+                        end
+                        3'd1: begin
+                            dataOut = stack1;
+                            stack1 = 4'h0;
+                            SP = 3'd2;
+                        end
+                        3'd2: begin
+                            dataOut = stack2;
+                            stack2 = 4'h0;
+                            SP = 3'd3;
+                        end
+                        default: begin
+                            dataOut = stack3;
+                            stack3 = 4'h0;
+                            SP = 3'd4;
+                        end
+                    endcase
+                end else begin
+                    FULL = (SP == 3'd0);
+                    dataOut = 4'hx;
                 end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
             end
         end
```

## 12. cceaf078b063988 — rtllm_LIFObuffer — gpt-5.4 — requested free -> rule d — label retained

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5294)"]

```diff
--- D
+++ C
@@ -10,40 +10,82 @@
 );
 
-    reg [3:0] stack_mem[0:3];
-    reg [2:0] SP;
-    integer i;
+    reg [3:0] mem0;
+    reg [3:0] mem1;
+    reg [3:0] mem2;
+    reg [3:0] mem3;
+    reg [2:0] sp_state;
 
-    always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
-                SP = 3'd4;
-                EMPTY = SP[2];
-                dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
-                end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
+    always @(*) begin
+        EMPTY = sp_state[2];
+    end
+
+    always @(posedge Clk) begin
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
+                sp_state <= 3'b100;
+                dataOut <= 4'h0;
+                /* FULL intentionally holds its previous value to match original behavior */
+            end else if (Rst == 1'b0) begin
+                dataOut <= 4'hx;
+
+                case (sp_state)
+                    3'b100: begin
+                        FULL <= 1'b0;
+                        if (RW == 1'b0) begin
+                            sp_state <= 3'b011;
+                            mem3 <= dataIn;
+                        end
+                    end
+
+                    3'b011: begin
+                        FULL <= 1'b0;
+                        if (RW == 1'b0) begin
+                            sp_state <= 3'b010;
+                            mem2 <= dataIn;
+                        end else if (RW == 1'b1) begin
+                            sp_state <= 3'b100;
+                            dataOut <= mem3;
+                        end
+                    end
+
+                    3'b010: begin
+                        FULL <= 1'b0;
+                        if (RW == 1'b0) begin
+                            sp_state <= 3'b001;
+                            mem1 <= dataIn;
+                        end else if (RW == 1'b1) begin
+                            sp_state <= 3'b011;
+                            dataOut <= mem2;
+                        end
+                    end
+
+                    3'b001: begin
+                        if (RW == 1'b0) begin
+                            sp_state <= 3'b000;
+                            FULL <= 1'b1;
+                            mem0 <= dataIn;
+                        end else if (RW == 1'b1) begin
+                            sp_state <= 3'b010;
+                            FULL <= 1'b0;
+                            dataOut <= mem1;
+                        end else begin
+                            FULL <= 1'b0;
+                        end
+                    end
+
+                    3'b000: begin
+                        if (RW == 1'b1) begin
+                            sp_state <= 3'b001;
+                            FULL <= 1'b0;
+                            dataOut <= mem0;
+                        end else begin
+                            FULL <= 1'b1;
+                        end
+                    end
+
+                    default: begin
+                        FULL <= 1'b0;
+                    end
+                endcase
             end
         end
```

## 13. c1573ced15e1248 — rtllm_traffic_light — gpt-5.6-terra — requested b -> rule d — label nonequiv

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5583)"]

```diff
--- D
+++ C
@@ -3,99 +3,82 @@
 module traffic_light
     (
-		input rst_n, 
-      input clk, 
-      input pass_request,
-		  output wire[7:0]clock,
-      output reg red,
-		  output reg yellow,
-		  output reg green
+        input rst_n, 
+        input clk, 
+        input pass_request,
+        output wire[7:0]clock,
+        output reg red,
+        output reg yellow,
+        output reg green
     );
-	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
-				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+    parameter idle = 2'd0,
+              s1_red = 2'd1,
+              s2_yellow = 2'd2,
+              s3_green = 2'd3;
 
-always @(posedge clk or negedge rst_n) 
+    reg [7:0] cnt;
+    reg [1:0] out_state;
+    reg transition_1;
+    reg transition_2;
+
+    wire cnt_is_3;
+    wire cnt_gt_10;
+    wire reload_red;
+    wire [7:0] reload_count;
+
+    assign cnt_is_3 = (~|cnt[7:2]) & cnt[1] & cnt[0];
+    assign cnt_gt_10 = (|cnt[7:4]) | (cnt[3] & (cnt[2] | cnt[1]));
+
+    assign reload_red = out_state[0] & ~out_state[1];
+    assign reload_count = {2'b00,
+                           reload_red,
+                           reload_red,
+                           (~out_state[0] | reload_red),
+                           out_state[0],
+                           ~out_state[0],
+                           (out_state[1] & out_state[0])};
+
+    always @(posedge clk or negedge rst_n)
     begin
-        if(!rst_n)
+        if (!rst_n)
         begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
+            out_state    <= idle;
+            transition_1 <= 1'b0;
+            transition_2 <= 1'b0;
         end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
-	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
+        else
+        begin
+            transition_2 <= transition_1;
+            if (!transition_1 && !transition_2 &&
+                ((~|out_state) || cnt_is_3))
+                transition_1 <= 1'b1;
+            else
+                transition_1 <= 1'b0;
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+            if (transition_2)
+                out_state <= {out_state[0], ~out_state[1]};
+        end
+    end
+
+    always @(posedge clk or negedge rst_n)
+    begin
+        if (!rst_n)
+            cnt <= 8'd10;
+        else if (pass_request && (&out_state) && cnt_gt_10)
+            cnt <= 8'd10;
+        else if (transition_2)
+            cnt <= reload_count;
+        else
+            cnt <= cnt - 8'd1;
+    end
+
+    always @*
+    begin
+        red    = ~out_state[1] &  out_state[0];
+        yellow =  out_state[1] & ~out_state[0];
+        green  =  out_state[1] &  out_state[0];
+    end
+
+    assign clock = cnt;
 
 endmodule
```

## 14. c54be66c4dbf198 — rtllm_traffic_light — gpt-5.4 — requested free -> rule d — label retained

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5711)"]

```diff
--- D
+++ C
@@ -16,86 +16,88 @@
 				s2_yellow = 2'd2,
 				s3_green = 2'd3;
+
 	reg [7:0] cnt;
 	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+	wire cnt_is_1;
+	wire cnt_is_8;
+	wire cnt_gt_10;
 
-always @(posedge clk or negedge rst_n) 
-    begin
-        if(!rst_n)
-        begin
+	assign cnt_is_1  = (~cnt[7]) & (~cnt[6]) & (~cnt[5]) & (~cnt[4]) & (~cnt[3]) & (~cnt[2]) & (~cnt[1]) & cnt[0];
+	assign cnt_is_8  = (~cnt[7]) & (~cnt[6]) & (~cnt[5]) & (~cnt[4]) & cnt[3] & (~cnt[2]) & (~cnt[1]) & (~cnt[0]);
+	assign cnt_gt_10 = (|cnt[7:4]) | (cnt[3] & (cnt[2] | (cnt[1] & cnt[0])));
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
 			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
-        end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
+			cnt <= 8'd10;
+		end
+		else begin
+			case (state)
+				idle: begin
+					if (cnt_is_8) begin
+						state <= s1_red;
+						cnt <= 8'd10;
+					end
+					else begin
+						state <= idle;
+						cnt <= cnt - 8'd1;
+					end
+				end
+				s1_red: begin
+					if (cnt_is_1) begin
+						state <= s3_green;
+						cnt <= 8'd60;
+					end
+					else begin
+						state <= s1_red;
+						cnt <= cnt - 8'd1;
+					end
+				end
+				s2_yellow: begin
+					if (cnt_is_1) begin
+						state <= s1_red;
+						cnt <= 8'd10;
+					end
+					else begin
+						state <= s2_yellow;
+						cnt <= cnt - 8'd1;
+					end
+				end
+				s3_green: begin
+					if (pass_request && cnt_gt_10) begin
+						state <= s3_green;
+						cnt <= 8'd10;
+					end
+					else if (cnt_is_1) begin
+						state <= s2_yellow;
+						cnt <= 8'd5;
+					end
+					else begin
+						state <= s3_green;
+						cnt <= cnt - 8'd1;
+					end
+				end
+				default: begin
+					state <= idle;
+					cnt <= 8'd10;
+				end
+			endcase
+		end
+	end
+
+	assign clock = cnt;
+
+	always @* begin
+		red = 1'b0;
+		yellow = 1'b0;
+		green = 1'b0;
+		case (state)
+			s1_red:    red = 1'b1;
+			s2_yellow: yellow = 1'b1;
+			s3_green:  green = 1'b1;
+			default: begin end
 		endcase
 	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
-
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
 
 endmodule
```

## 15. c5d7ecfc9c3a103 — rtllm_traffic_light — gpt-5.6-terra — requested a -> rule d — label nonequiv

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5057)"]

```diff
--- D
+++ C
@@ -3,99 +3,86 @@
 module traffic_light
     (
-		input rst_n, 
-      input clk, 
-      input pass_request,
-		  output wire[7:0]clock,
-      output reg red,
-		  output reg yellow,
-		  output reg green
+        input rst_n, 
+        input clk, 
+        input pass_request,
+        output wire[7:0]clock,
+        output reg red,
+        output reg yellow,
+        output reg green
     );
-	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
-				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+    parameter idle      = 2'd0,
+              s1_red    = 2'd1,
+              s2_yellow = 2'd2,
+              s3_green  = 2'd3;
 
-always @(posedge clk or negedge rst_n) 
+    reg [5:0] cnt;
+    reg [1:0] state;
+    reg [1:0] out_phase;
+    reg       phase_delay;
+
+    wire terminal_count;
+    wire phase_mismatch;
+    wire cnt_gt_ten;
+
+    assign terminal_count = ~cnt[5] & ~cnt[4] & ~cnt[3] & ~cnt[2] & cnt[1] & cnt[0];
+    assign phase_mismatch = (out_phase[1] ^ state[1]) | (out_phase[0] ^ state[0]);
+    assign cnt_gt_ten = cnt[5] | cnt[4] | (cnt[3] & (cnt[2] | cnt[1] | cnt[0]));
+
+    always @(posedge clk or negedge rst_n)
     begin
-        if(!rst_n)
+        if (!rst_n)
         begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
+            state       <= idle;
+            phase_delay <= 1'b0;
         end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
-	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
+        else
+        begin
+            phase_delay <= (~state[1] & ~state[0]) | terminal_count;
+            if (~state[1] & ~state[0])
+                state <= s1_red;
+            else if (terminal_count)
+                state <= {state[0], ~(state[1] & state[0])};
+        end
+    end
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+    always @(posedge clk or negedge rst_n)
+    begin
+        if (!rst_n)
+            cnt <= 6'd10;
+        else if (pass_request && green && cnt_gt_ten)
+            cnt <= 6'd10;
+        else if (!phase_delay && phase_mismatch)
+        begin
+            if (state[1])
+            begin
+                if (state[0])
+                    cnt <= 6'd60;
+                else
+                    cnt <= 6'd5;
+            end
+            else
+                cnt <= 6'd10;
+        end
+        else
+            cnt <= cnt - 1'b1;
+    end
+
+    always @(posedge clk or negedge rst_n)
+    begin
+        if (!rst_n)
+            out_phase <= idle;
+        else if (!phase_delay)
+            out_phase <= state;
+    end
+
+    always @*
+    begin
+        red    = ~out_phase[1] &  out_phase[0];
+        yellow =  out_phase[1] & ~out_phase[0];
+        green  =  out_phase[1] &  out_phase[0];
+    end
+
+    assign clock = {2'b00, cnt};
 
 endmodule
```

## 16. c35993cdd6aa0f0 — rtllm_adder_16bit — gpt-5.4 — requested d -> rule d — label tradeoff

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.8139)"]

```diff
--- D
+++ C
@@ -6,118 +6,84 @@
     output wire Co
 );
- 
-    wire Co_temp;
- 
-    add8 add8_inst1 (
-        .a(a[15:8]),
-        .b(b[15:8]),
-        .Cin(Co_temp), 
-        .y(y[15:8]),
-        .Co(Co)
-    );
- 
-    add8 add8_inst2 (
-        .a(a[7:0]),
-        .b(b[7:0]),
-        .Cin(Cin),
-        .y(y[7:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
 
-module add8 (
-    input wire [7:0] a,
-    input wire [7:0] b,
-    input wire Cin,
-    output wire [7:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add4 add4_inst1 (
-        .a(a[7:4]),
-        .b(b[7:4]),
-        .Cin(Co_temp),
-        .y(y[7:4]),
-        .Co(Co)
-    );
- 
-    add4 add4_inst2 (
-        .a(a[3:0]),
-        .b(b[3:0]),
-        .Cin(Cin),
-        .y(y[3:0]),
-        .Co(Co_temp)
-    );
- 
-endmodule
+    function gp4_p;
+        input [3:0] aa;
+        input [3:0] bb;
+        begin
+            gp4_p = &(aa ^ bb);
+        end
+    endfunction
 
-module add4 (
-    input wire [3:0] a,
-    input wire [3:0] b,
-    input wire Cin,
-    output wire [3:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add2 add2_inst1 (
-        .a(a[3:2]),
-        .b(b[3:2]),
-        .Cin(Co_temp),
-        .y(y[3:2]),
-        .Co(Co)
-    );
- 
-    add2 add2_inst2 (
-        .a(a[1:0]),
-        .b(b[1:0]),
-        .Cin(Cin),
-        .y(y[1:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
+    function gp4_g;
+        input [3:0] aa;
+        input [3:0] bb;
+        reg [3:0] p;
+        reg [3:0] g;
+        begin
+            p = aa ^ bb;
+            g = aa & bb;
+            gp4_g = g[3] |
+                    (p[3] & g[2]) |
+                    (p[3] & p[2] & g[1]) |
+                    (p[3] & p[2] & p[1] & g[0]);
+        end
+    endfunction
 
-module add2 (
-    input wire [1:0] a,
-    input wire [1:0] b,
-    input wire Cin,
-    output wire [1:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
+    wire P0;
+    wire P1;
+    wire P2;
+    wire P3;
+    wire G0;
+    wire G1;
+    wire G2;
+    wire G3;
 
-    add1 add1_inst1 (
-        .a(a[1]),
-        .b(b[1]),
-        .Cin(Co_temp),
-        .y(y[1]),
-        .Co(Co)
-    );
- 
-    add1 add1_inst2 (
-        .a(a[0]),
-        .b(b[0]),
-        .Cin(Cin),
-        .y(y[0]),
-        .Co(Co_temp)
-    );
-         
-endmodule
+    wire P01;
+    wire G01;
+    wire P012;
+    wire G012;
+    wire P0123;
+    wire G0123;
 
-module add1 (
-    input wire a,
-    input wire b,
-    input wire Cin,
-    output wire y,
-    output wire Co
-);
-    assign y = ((~a) & (~b) & Cin | (~a) & b & (~Cin) | a & (~b) & (~Cin) | (a & b & Cin));
-    assign Co = ((~a & b & Cin) | (a & ~b & Cin) | (a & b & ~Cin) | (a & b & Cin));
+    wire C4;
+    wire C8;
+    wire C12;
+
+    wire [4:0] s0;
+    wire [4:0] s1;
+    wire [4:0] s2;
+    wire [4:0] s3;
+
+    assign P0 = gp4_p(a[3:0],   b[3:0]);
+    assign P1 = gp4_p(a[7:4],   b[7:4]);
+    assign P2 = gp4_p(a[11:8],  b[11:8]);
+    assign P3 = gp4_p(a[15:12], b[15:12]);
+
+    assign G0 = gp4_g(a[3:0],   b[3:0]);
+    assign G1 = gp4_g(a[7:4],   b[7:4]);
+    assign G2 = gp4_g(a[11:8],  b[11:8]);
+    assign G3 = gp4_g(a[15:12], b[15:12]);
+
+    assign P01   = P1 & P0;
+    assign G01   = G1 | (P1 & G0);
+    assign P012  = P2 & P01;
+    assign G012  = G2 | (P2 & G01);
+    assign P0123 = P3 & P012;
+    assign G0123 = G3 | (P3 & G012);
+
+    assign C4  = G0   | (P0   & Cin);
+    assign C8  = G01  | (P01  & Cin);
+    assign C12 = G012 | (P012 & Cin);
+    assign Co  = G0123 | (P0123 & Cin);
+
+    assign s0 = {1'b0, a[3:0]}   + {1'b0, b[3:0]}   + Cin;
+    assign s1 = {1'b0, a[7:4]}   + {1'b0, b[7:4]}   + C4;
+    assign s2 = {1'b0, a[11:8]}  + {1'b0, b[11:8]}  + C8;
+    assign s3 = {1'b0, a[15:12]} + {1'b0, b[15:12]} + C12;
+
+    assign y[3:0]    = s0[3:0];
+    assign y[7:4]    = s1[3:0];
+    assign y[11:8]   = s2[3:0];
+    assign y[15:12]  = s3[3:0];
 
 endmodule
```

## 17. c2516f88ad77a2e — rtllm_LIFObuffer — gpt-5.4 — requested a -> rule d — label tradeoff

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5286)"]

```diff
--- D
+++ C
@@ -14,36 +14,86 @@
     integer i;
 
-    always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
-                SP = 3'd4;
-                EMPTY = SP[2];
-                dataOut = 4'h0;
+    always @(posedge Clk) begin
+        if (EN) begin
+            if (Rst) begin
+                SP <= 3'd4;
+                EMPTY <= 1'b1;
+                dataOut <= 4'h0;
                 for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
-                end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
+                    stack_mem[i] <= 4'h0;
                 end
             end else begin
-                // Do nothing if neither condition is met
+                dataOut <= 4'hx;
+
+                if (!RW && (SP != 3'd0)) begin
+                    case (SP)
+                        3'd4: begin
+                            SP <= 3'd3;
+                            stack_mem[3] <= dataIn;
+                            FULL <= 1'b0;
+                            EMPTY <= 1'b0;
+                        end
+                        3'd3: begin
+                            SP <= 3'd2;
+                            stack_mem[2] <= dataIn;
+                            FULL <= 1'b0;
+                            EMPTY <= 1'b0;
+                        end
+                        3'd2: begin
+                            SP <= 3'd1;
+                            stack_mem[1] <= dataIn;
+                            FULL <= 1'b0;
+                            EMPTY <= 1'b0;
+                        end
+                        3'd1: begin
+                            SP <= 3'd0;
+                            stack_mem[0] <= dataIn;
+                            FULL <= 1'b1;
+                            EMPTY <= 1'b0;
+                        end
+                        default: begin
+                            FULL <= (SP == 3'd0);
+                            EMPTY <= SP[2];
+                        end
+                    endcase
+                end else if (RW && !SP[2]) begin
+                    case (SP)
+                        3'd0: begin
+                            dataOut <= stack_mem[0];
+                            stack_mem[0] <= 4'h0;
+                            SP <= 3'd1;
+                            FULL <= 1'b0;
+                            EMPTY <= 1'b0;
+                        end
+                        3'd1: begin
+                            dataOut <= stack_mem[1];
+                            stack_mem[1] <= 4'h0;
+                            SP <= 3'd2;
+                            FULL <= 1'b0;
+                            EMPTY <= 1'b0;
+                        end
+                        3'd2: begin
+                            dataOut <= stack_mem[2];
+                            stack_mem[2] <= 4'h0;
+                            SP <= 3'd3;
+                            FULL <= 1'b0;
+                            EMPTY <= 1'b0;
+                        end
+                        3'd3: begin
+                            dataOut <= stack_mem[3];
+                            stack_mem[3] <= 4'h0;
+                            SP <= 3'd4;
+                            FULL <= 1'b0;
+                            EMPTY <= 1'b1;
+                        end
+                        default: begin
+                            FULL <= (SP == 3'd0);
+                            EMPTY <= SP[2];
+                        end
+                    endcase
+                end else begin
+                    FULL <= (SP == 3'd0);
+                    EMPTY <= SP[2];
+                end
             end
         end
```

## 18. c22d7036b29abd8 — rtllm_serial2parallel — gpt-5.4-mini — requested free -> rule d — label retained

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5678)"]

```diff
--- D
+++ C
@@ -1,3 +1,2 @@
-
 module serial2parallel(
 	input clk,
@@ -9,37 +8,36 @@
 );
 
-	reg[7:0]din_tmp;
-	reg[3:0]cnt;
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			cnt <= 0;
-		else if(din_valid)
-			cnt <= (cnt == 4'd8)?0:cnt+1'b1;
-		else	
-			cnt <= 0;
+	reg [3:0] sh_lo;
+	reg [3:0] sh_hi;
+	reg [2:0] cnt;
+	reg full;
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			sh_lo <= 4'b0;
+			sh_hi <= 4'b0;
+			cnt <= 3'b0;
+			full <= 1'b0;
+			dout_parallel <= 8'b0;
+			dout_valid <= 1'b0;
+		end else begin
+			dout_valid <= full;
+
+			if (full) begin
+				dout_parallel <= {sh_hi, sh_lo};
+				full <= 1'b0;
+				cnt <= 3'b0;
+			end else if (din_valid) begin
+				sh_lo <= {sh_lo[2:0], din_serial};
+				sh_hi <= {sh_hi[2:0], sh_lo[3]};
+				if (&cnt)
+					full <= 1'b1;
+				else
+					cnt <= cnt + 3'b001;
+			end else begin
+				cnt <= 3'b0;
+			end
+		end
 	end
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			din_tmp <= 8'b0;
-		else if(din_valid && cnt <= 4'd7)
-			din_tmp <= {din_tmp[6:0],din_serial};
-	
-	end 
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)begin
-			dout_valid <= 1'b0;
-			dout_parallel <= 8'b0;
-		end
-		else if(cnt == 4'd8)begin
-			dout_valid <= 1'b1;
-			dout_parallel <= din_tmp;
-		end
-		else begin
-			dout_valid <= 1'b0;
-		end
-	end 
-	
+
 endmodule
```

## 19. c7ec4da150c7ad0 — rtllm_traffic_light — gpt-5.4-mini — requested b -> rule d — label retained

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5885)"]

```diff
--- D
+++ C
@@ -9,93 +9,90 @@
       output reg red,
 		  output reg yellow,
-		  output reg green
+      output reg green
     );
 	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
+	parameter 	idle = 2'd3,
+				s1_red = 2'd0,
 				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
+				s3_green = 2'd1;
+
+	reg [5:0] cnt;
 	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
+	reg [1:0] phase;
+	reg [1:0] next_state;
 
+	wire cnt_is3;
+	wire cnt_gt10;
+	wire phase_is_red;
+	wire phase_is_yellow;
+	wire phase_is_green;
+	wire load_green;
+	wire load_yellow;
+	wire load_red;
+	wire pass_hold;
 
-always @(posedge clk or negedge rst_n) 
-    begin
-        if(!rst_n)
-        begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
-        end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
+	assign cnt_is3 = (cnt == 6'd3);
+	assign cnt_gt10 = (cnt > 6'd10);
+	assign phase_is_red = (phase == s1_red);
+	assign phase_is_yellow = (phase == s2_yellow);
+	assign phase_is_green = (phase == s3_green);
+	assign load_green = phase_is_green & ~green;
+	assign load_yellow = phase_is_yellow & ~yellow;
+	assign load_red = phase_is_red & ~red;
+	assign pass_hold = pass_request & green & cnt_gt10;
+
+	always @* begin
+		next_state = state;
+		case (state)
+			idle: begin
+				next_state = s1_red;
 			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
+			s1_red: begin
+				if (cnt_is3)
+					next_state = s3_green;
 			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
+			s2_yellow: begin
+				if (cnt_is3)
+					next_state = s1_red;
 			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
+			s3_green: begin
+				if (cnt_is3)
+					next_state = s2_yellow;
+			end
+			default: begin
+				next_state = idle;
 			end
 		endcase
 	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+	always @(posedge clk or negedge rst_n) begin
+		if(!rst_n) begin
+			state <= idle;
+			phase <= idle;
+			red <= 1'b0;
+			yellow <= 1'b0;
+			green <= 1'b0;
+			cnt <= 6'd10;
+		end
+		else begin
+			state <= next_state;
+			phase <= state;
+			red <= phase_is_red;
+			yellow <= phase_is_yellow;
+			green <= phase_is_green;
+			if (pass_hold)
+				cnt <= 6'd10;
+			else if (load_green)
+				cnt <= 6'd60;
+			else if (load_yellow)
+				cnt <= 6'd5;
+			else if (load_red)
+				cnt <= 6'd10;
+			else
+				cnt <= cnt - 6'd1;
+		end
+	end
+
+	assign clock = {2'b00, cnt};
 
 endmodule
```

## 20. ceeba4ce1dfb8a6 — rtllm_LIFObuffer — gpt-5.6-terra — requested d -> rule d — label nonequiv

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5501)"]

```diff
--- D
+++ C
@@ -10,40 +10,57 @@
 );
 
-    reg [3:0] stack_mem[0:3];
-    reg [2:0] SP;
-    integer i;
+    reg [3:0] stack0;
+    reg [3:0] stack1;
+    reg [3:0] stack2;
+    reg [3:0] stack3;
+    reg [3:0] valid;
 
-    always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
-                SP = 3'd4;
-                EMPTY = SP[2];
-                dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
+    always @(*) begin
+        EMPTY = ~(|valid);
+    end
+
+    always @(posedge Clk) begin
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
+                valid <= 4'b0000;
+                dataOut <= 4'h0;
+            end else if (Rst == 1'b0) begin
+                FULL <= &valid;
+                dataOut <= 4'hx;
+
+                if ((&valid) == 1'b0 && RW == 1'b0) begin
+                    if (valid[3] == 1'b0) begin
+                        stack3 <= dataIn;
+                        valid[3] <= 1'b1;
+                        FULL <= &valid[2:0];
+                    end else if (valid[2] == 1'b0) begin
+                        stack2 <= dataIn;
+                        valid[2] <= 1'b1;
+                        FULL <= &{valid[3], valid[1:0]};
+                    end else if (valid[1] == 1'b0) begin
+                        stack1 <= dataIn;
+                        valid[1] <= 1'b1;
+                        FULL <= &{valid[3:2], valid[0]};
+                    end else begin
+                        stack0 <= dataIn;
+                        valid[0] <= 1'b1;
+                        FULL <= 1'b1;
+                    end
+                end else if ((|valid) == 1'b1 && RW == 1'b1) begin
+                    FULL <= 1'b0;
+                    if (valid[0] == 1'b1) begin
+                        dataOut <= stack0;
+                        valid[0] <= 1'b0;
+                    end else if (valid[1] == 1'b1) begin
+                        dataOut <= stack1;
+                        valid[1] <= 1'b0;
+                    end else if (valid[2] == 1'b1) begin
+                        dataOut <= stack2;
+                        valid[2] <= 1'b0;
+                    end else begin
+                        dataOut <= stack3;
+                        valid[3] <= 1'b0;
+                    end
                 end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
             end
         end
```

## 21. c1262ae4a28f90a — rtllm_LIFObuffer — gpt-5.6-luna — requested c1 -> rule d — label retained

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.7902)"]

```diff
--- D
+++ C
@@ -10,42 +10,93 @@
 );
 
-    reg [3:0] stack_mem[0:3];
+    reg [15:0] stack_mem;
     reg [2:0] SP;
-    integer i;
+    reg [15:0] stack_mem_next;
+    reg [2:0] SP_next;
+    reg EMPTY_next;
+    reg FULL_next;
+    reg [3:0] dataOut_next;
 
-    always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
-                SP = 3'd4;
-                EMPTY = SP[2];
-                dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
+    always @* begin
+        stack_mem_next = stack_mem;
+        SP_next = SP;
+        EMPTY_next = EMPTY;
+        FULL_next = FULL;
+        dataOut_next = dataOut;
+
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
+                SP_next = 3'd4;
+                EMPTY_next = 1'b1;
+                dataOut_next = 4'h0;
+                stack_mem_next = 16'h0000;
+            end else if (Rst == 1'b0) begin
+                dataOut_next = 4'hx;
+                FULL_next = SP ? 1'b0 : 1'b1;
+                EMPTY_next = SP[2];
+
+                if (RW == 1'b0) begin
+                    case (SP)
+                        3'd7: SP_next = 3'd6;
+                        3'd6: SP_next = 3'd5;
+                        3'd5: SP_next = 3'd4;
+                        3'd4: begin
+                            SP_next = 3'd3;
+                            stack_mem_next[15:12] = dataIn;
+                        end
+                        3'd3: begin
+                            SP_next = 3'd2;
+                            stack_mem_next[11:8] = dataIn;
+                        end
+                        3'd2: begin
+                            SP_next = 3'd1;
+                            stack_mem_next[7:4] = dataIn;
+                        end
+                        3'd1: begin
+                            SP_next = 3'd0;
+                            stack_mem_next[3:0] = dataIn;
+                        end
+                        default: begin
+                        end
+                    endcase
+                end else if (RW == 1'b1) begin
+                    case (SP)
+                        3'd0: begin
+                            dataOut_next = stack_mem[3:0];
+                            stack_mem_next[3:0] = 4'h0;
+                            SP_next = 3'd1;
+                        end
+                        3'd1: begin
+                            dataOut_next = stack_mem[7:4];
+                            stack_mem_next[7:4] = 4'h0;
+                            SP_next = 3'd2;
+                        end
+                        3'd2: begin
+                            dataOut_next = stack_mem[11:8];
+                            stack_mem_next[11:8] = 4'h0;
+                            SP_next = 3'd3;
+                        end
+                        3'd3: begin
+                            dataOut_next = stack_mem[15:12];
+                            stack_mem_next[15:12] = 4'h0;
+                            SP_next = 3'd4;
+                        end
+                        default: begin
+                        end
+                    endcase
                 end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
+
+                FULL_next = SP_next ? 1'b0 : 1'b1;
+                EMPTY_next = SP_next[2];
             end
         end
     end
+
+    always @(posedge Clk) begin
+        stack_mem <= stack_mem_next;
+        SP <= SP_next;
+        EMPTY <= EMPTY_next;
+        FULL <= FULL_next;
+        dataOut <= dataOut_next;
+    end
 endmodule
```

## 22. c870992080f1644 — rtllm_multi_pipe_8bit — gpt-5.6-luna — requested b -> rule d — label tradeoff

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.6675)"]

```diff
--- D
+++ C
@@ -2,91 +2,85 @@
     parameter size = 8
 )(
-          clk,      
-          rst_n,       
-          mul_a,       
-          mul_b, 
-          mul_en_in,
- 
-          mul_en_out,      
-          mul_out    
+    clk,
+    rst_n,
+    mul_a,
+    mul_b,
+    mul_en_in,
+    mul_en_out,
+    mul_out
 );
- 
-   input clk;           
-   input rst_n; 
-   input mul_en_in;      
-   input [size-1:0] mul_a;       
-   input [size-1:0] mul_b;       
- 
-   output reg mul_en_out;  
-   output reg [size*2-1:0] mul_out;    
- 
-            
+
+   input clk;
+   input rst_n;
+   input mul_en_in;
+   input [size-1:0] mul_a;
+   input [size-1:0] mul_b;
+
+   output reg mul_en_out;
+   output reg [size*2-1:0] mul_out;
+
    reg [2:0] mul_en_out_reg;
- always@(posedge clk or negedge rst_n)
-       if(!rst_n)begin
-            mul_en_out_reg <= 'd0;             
-            mul_en_out     <= 'd0;                           
-       end
-       else begin
-            mul_en_out_reg <= {mul_en_out_reg[1:0],mul_en_in};            
-            mul_en_out     <= mul_en_out_reg[2];                  
-       end
- 
- 
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
-  always @(posedge clk or negedge rst_n)
-         if(!rst_n) begin
-              mul_a_reg <= 'd0;
-              mul_a_reg <= 'd0;
-         end
-         else begin
-              mul_a_reg <= mul_en_in ? mul_a :'d0;
-              mul_b_reg <= mul_en_in ? mul_b :'d0;
-         end
- 
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
-       else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
-       end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
- 
- 
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out <= 'd0;
-       else if(mul_en_out_reg[2])
-          mul_out <= mul_out_reg;
-       else
-          mul_out <= 'd0;
- 
-          
+   reg [7:0] mul_a_reg;
+   reg [7:0] mul_b_reg;
+
+   reg [9:0]  sum0;
+   reg [11:0] sum1;
+   reg [13:0] sum2;
+   reg [15:0] sum3;
+   reg [15:0] mul_out_reg;
+
+   wire [7:0]  temp0;
+   wire [8:0]  temp1;
+   wire [9:0]  temp2;
+   wire [10:0] temp3;
+   wire [11:0] temp4;
+   wire [12:0] temp5;
+   wire [13:0] temp6;
+   wire [14:0] temp7;
+
+   assign temp0 = mul_b_reg[0] ? mul_a_reg : 8'b0;
+   assign temp1 = mul_b_reg[1] ? {mul_a_reg,1'b0} : 9'b0;
+   assign temp2 = mul_b_reg[2] ? {mul_a_reg,2'b0} : 10'b0;
+   assign temp3 = mul_b_reg[3] ? {mul_a_reg,3'b0} : 11'b0;
+   assign temp4 = mul_b_reg[4] ? {mul_a_reg,4'b0} : 12'b0;
+   assign temp5 = mul_b_reg[5] ? {mul_a_reg,5'b0} : 13'b0;
+   assign temp6 = mul_b_reg[6] ? {mul_a_reg,6'b0} : 14'b0;
+   assign temp7 = mul_b_reg[7] ? {mul_a_reg,7'b0} : 15'b0;
+
+   always @(posedge clk or negedge rst_n) begin
+      if (!rst_n) begin
+         mul_en_out_reg <= 3'b0;
+         mul_en_out     <= 1'b0;
+         mul_a_reg      <= 8'b0;
+         mul_b_reg      <= 8'b0;
+         sum0           <= 10'b0;
+         sum1           <= 12'b0;
+         sum2           <= 14'b0;
+         sum3           <= 16'b0;
+         mul_out_reg    <= 16'b0;
+         mul_out        <= 'd0;
+      end
+      else begin
+         mul_en_out_reg <= {mul_en_out_reg[1:0],mul_en_in};
+         mul_en_out     <= mul_en_out_reg[2];
+
+         mul_a_reg <= mul_en_in ? mul_a : 8'b0;
+         mul_b_reg <= mul_en_in ? mul_b : 8'b0;
+
+         sum0 <= {2'b0,temp0} + {1'b0,temp1};
+         sum1 <= {2'b0,temp2} + {1'b0,temp3};
+         sum2 <= {2'b0,temp4} + {1'b0,temp5};
+         sum3 <= {2'b0,temp6} + {1'b0,temp7};
+
+         mul_out_reg <=
+              ({6'b0,sum0} + {4'b0,sum1}) +
+              ({2'b0,sum2} + sum3);
+
+         if (mul_en_out_reg[2])
+            mul_out <= mul_out_reg;
+         else
+            mul_out <= 'd0;
+      end
+   end
+
 endmodule
```

## 23. cc26273a169123f — rtllm_multi_pipe_8bit — gpt-5.4-mini — requested d -> rule d — label nonequiv

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.5825)"]

```diff
--- D
+++ C
@@ -20,72 +20,59 @@
    output reg mul_en_out;  
    output reg [size*2-1:0] mul_out;    
+
+   localparam HALF = size/2;
+
+   reg [2:0] mul_en_pipe;
+   reg [size-1:0] mul_a_reg;
+   reg [size-1:0] mul_b_reg;
+   reg [size+HALF-1:0] mul_lo_reg;
+   reg [size+HALF-1:0] mul_hi_reg;
+
+   wire [size+HALF-1:0] mul_lo_w;
+   wire [size+HALF-1:0] mul_hi_w;
+   wire [size*2-1:0] mul_sum_w;
+
+   assign mul_lo_w = mul_a_reg * mul_b_reg[HALF-1:0];
+   assign mul_hi_w = mul_a_reg * mul_b_reg[size-1:HALF];
+   assign mul_sum_w = {mul_hi_reg, {HALF{1'b0}}} + {{HALF{1'b0}}, mul_lo_reg};
  
-            
-   reg [2:0] mul_en_out_reg;
  always@(posedge clk or negedge rst_n)
        if(!rst_n)begin
-            mul_en_out_reg <= 'd0;             
-            mul_en_out     <= 'd0;                           
+            mul_en_pipe <= 3'b0;             
+            mul_en_out  <= 1'b0;                           
        end
        else begin
-            mul_en_out_reg <= {mul_en_out_reg[1:0],mul_en_in};            
-            mul_en_out     <= mul_en_out_reg[2];                  
+            mul_en_pipe <= {mul_en_pipe[1:0],mul_en_in};            
+            mul_en_out  <= mul_en_pipe[2];                  
        end
  
  
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
   always @(posedge clk or negedge rst_n)
          if(!rst_n) begin
-              mul_a_reg <= 'd0;
-              mul_a_reg <= 'd0;
+              mul_a_reg <= {size{1'b0}};
+              mul_b_reg <= {size{1'b0}};
          end
-         else begin
-              mul_a_reg <= mul_en_in ? mul_a :'d0;
-              mul_b_reg <= mul_en_in ? mul_b :'d0;
+         else if (mul_en_in) begin
+              mul_a_reg <= mul_a;
+              mul_b_reg <= mul_b;
+         end
+
+  always @(posedge clk or negedge rst_n)
+         if(!rst_n) begin
+              mul_lo_reg <= {size+HALF{1'b0}};
+              mul_hi_reg <= {size+HALF{1'b0}};
+         end
+         else if (mul_en_pipe[0]) begin
+              mul_lo_reg <= mul_lo_w;
+              mul_hi_reg <= mul_hi_w;
          end
  
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
-       else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
-       end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
+  always @(posedge clk or negedge rst_n) 
        if(!rst_n)
-          mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
- 
- 
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out <= 'd0;
-       else if(mul_en_out_reg[2])
-          mul_out <= mul_out_reg;
+          mul_out <= {size*2{1'b0}};
+       else if(mul_en_pipe[2])
+          mul_out <= mul_sum_w;
        else
-          mul_out <= 'd0;
+          mul_out <= {size*2{1'b0}};
  
           
```

## 24. c456d249fdd8eb5 — rtllm_traffic_light — gpt-5.6-terra — requested d -> rule d — label harmful

rule evidence: ["sequential structure changed and the text differs widely (ratio 0.6454)"]

```diff
--- D
+++ C
@@ -3,99 +3,55 @@
 module traffic_light
     (
-		input rst_n, 
-      input clk, 
-      input pass_request,
-		  output wire[7:0]clock,
-      output reg red,
-		  output reg yellow,
-		  output reg green
+        input rst_n, 
+        input clk, 
+        input pass_request,
+        output wire[7:0]clock,
+        output reg red,
+        output reg yellow,
+        output reg green
     );
-	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
-				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+    reg [6:0] phase;
+    reg [6:0] count_value;
 
-always @(posedge clk or negedge rst_n) 
+    always @(posedge clk or negedge rst_n)
     begin
-        if(!rst_n)
+        if (!rst_n)
+            phase <= 7'd0;
+        else if (phase == 7'd77)
+            phase <= 7'd3;
+        else if (pass_request && (phase >= 7'd13) && (phase <= 7'd62))
+            phase <= 7'd63;
+        else
+            phase <= phase + 7'd1;
+    end
+
+    always @*
+    begin
+        red = 1'b0;
+        yellow = 1'b0;
+        green = 1'b0;
+        count_value = 7'd0;
+
+        if (phase <= 7'd2)
+            count_value = 7'd10 - phase;
+        else if (phase <= 7'd12)
         begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
+            red = 1'b1;
+            count_value = 7'd13 - phase;
         end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
-	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
+        else if (phase <= 7'd72)
+        begin
+            green = 1'b1;
+            count_value = 7'd73 - phase;
+        end
+        else
+        begin
+            yellow = 1'b1;
+            count_value = 7'd78 - phase;
+        end
+    end
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+    assign clock = {1'b0, count_value};
 
 endmodule
```

## 25. c4a8f4d032925d3 — rtllm_LIFObuffer — gpt-5.4-mini — requested a -> rule c1 — label retained

rule evidence: ["flip-flop bits 57 -> 25 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -12,38 +12,35 @@
     reg [3:0] stack_mem[0:3];
     reg [2:0] SP;
-    integer i;
 
     always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
                 SP = 3'd4;
+                EMPTY = 1'b1;
+                dataOut = 4'h0;
+            end else begin
+                dataOut = 4'hx;
+                FULL = (SP == 3'd0);
                 EMPTY = SP[2];
-                dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
+
+                if (RW == 1'b0) begin
+                    case (SP)
+                        3'd4: begin SP = 3'd3; stack_mem[3] = dataIn; FULL = 1'b0; EMPTY = 1'b0; end
+                        3'd3: begin SP = 3'd2; stack_mem[2] = dataIn; FULL = 1'b0; EMPTY = 1'b0; end
+                        3'd2: begin SP = 3'd1; stack_mem[1] = dataIn; FULL = 1'b0; EMPTY = 1'b0; end
+                        3'd1: begin SP = 3'd0; stack_mem[0] = dataIn; FULL = 1'b1; EMPTY = 1'b0; end
+                        default: begin end
+                    endcase
+                end else if (RW == 1'b1) begin
+                    case (SP)
+                        3'd0: begin dataOut = stack_mem[0]; SP = 3'd1; FULL = 1'b0; EMPTY = 1'b0; end
+                        3'd1: begin dataOut = stack_mem[1]; SP = 3'd2; FULL = 1'b0; EMPTY = 1'b0; end
+                        3'd2: begin dataOut = stack_mem[2]; SP = 3'd3; FULL = 1'b0; EMPTY = 1'b0; end
+                        3'd3: begin dataOut = stack_mem[3]; SP = 3'd4; FULL = 1'b0; EMPTY = 1'b1; end
+                        default: begin end
+                    endcase
+                end else begin
+                    // Do nothing if RW is not 0 or 1
                 end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
             end
         end
```

## 26. c8a512245fd1412 — rtllm_LIFObuffer — gpt-5.4-mini — requested a -> rule c1 — label retained

rule evidence: ["flip-flop bits 57 -> 25 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -12,38 +12,26 @@
     reg [3:0] stack_mem[0:3];
     reg [2:0] SP;
-    integer i;
 
     always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
                 SP = 3'd4;
+                EMPTY = 1'b1;
+                dataOut = 4'h0;
+            end else begin
+                dataOut = 4'hx;
+
+                if (RW == 1'b0) begin
+                    if (SP != 3'd0) begin
+                        SP = SP - 1'b1;
+                        stack_mem[SP] = dataIn;
+                    end
+                end else if (SP[2] == 1'b0) begin
+                    dataOut = stack_mem[SP];
+                    SP = SP + 1'b1;
+                end
+
+                FULL = (SP == 3'd0);
                 EMPTY = SP[2];
-                dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
-                end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
             end
         end
```

## 27. ca4713bdeb8ad54 — rtllm_traffic_light — gpt-5.6-luna — requested free -> rule c1 — label retained

rule evidence: ["flip-flop bits 16 -> 10 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -3,99 +3,77 @@
 module traffic_light
     (
-		input rst_n, 
-      input clk, 
-      input pass_request,
-		  output wire[7:0]clock,
-      output reg red,
-		  output reg yellow,
-		  output reg green
+        input rst_n,
+        input clk,
+        input pass_request,
+        output wire[7:0] clock,
+        output reg red,
+        output reg yellow,
+        output reg green
     );
-	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
-				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+    parameter idle = 2'd0,
+              s1_red = 2'd1,
+              s2_yellow = 2'd2,
+              s3_green = 2'd3;
 
-always @(posedge clk or negedge rst_n) 
-    begin
-        if(!rst_n)
-        begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
+    reg [5:0] cnt;
+    reg [1:0] state_d1;
+    reg [1:0] state_d2;
+
+    always @(posedge clk or negedge rst_n) begin
+        if (!rst_n) begin
+            state_d1 <= idle;
+            state_d2 <= idle;
         end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
-	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
+        else begin
+            state_d2 <= state_d1;
+            if (state_d1 == idle) begin
+                if (cnt == 6'd9)
+                    state_d1 <= s1_red;
+                else
+                    state_d1 <= idle;
+            end
+            else if (cnt == 6'd2) begin
+                case (state_d1)
+                    s1_red:   state_d1 <= s3_green;
+                    s2_yellow: state_d1 <= s1_red;
+                    s3_green: state_d1 <= s2_yellow;
+                    default:  state_d1 <= idle;
+                endcase
+            end
+            else begin
+                state_d1 <= state_d1;
+            end
+        end
+    end
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+    always @(*) begin
+        red = 1'b0;
+        yellow = 1'b0;
+        green = 1'b0;
+        case (state_d2)
+            s1_red:    red = 1'b1;
+            s2_yellow: yellow = 1'b1;
+            s3_green:  green = 1'b1;
+            default:   begin end
+        endcase
+    end
+
+    always @(posedge clk or negedge rst_n) begin
+        if (!rst_n)
+            cnt <= 6'd10;
+        else if (pass_request && green && (cnt > 6'd10))
+            cnt <= 6'd10;
+        else if ((state_d1 == s3_green) && (state_d2 != s3_green))
+            cnt <= 6'd60;
+        else if ((state_d1 == s2_yellow) && (state_d2 != s2_yellow))
+            cnt <= 6'd5;
+        else if ((state_d1 == s1_red) && (state_d2 != s1_red))
+            cnt <= 6'd10;
+        else
+            cnt <= cnt - 1'b1;
+    end
+
+    assign clock = {2'b00, cnt};
 
 endmodule
```

## 28. c6028c0668636f1 — rtllm_LIFObuffer — gpt-5.4-mini — requested a -> rule c1 — label retained

rule evidence: ["flip-flop bits 57 -> 25 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -12,38 +12,34 @@
     reg [3:0] stack_mem[0:3];
     reg [2:0] SP;
-    integer i;
 
     always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
                 SP = 3'd4;
+                EMPTY = 1'b1;
+                dataOut = 4'h0;
+            end else begin
+                dataOut = 4'hx;
+
+                if (RW == 1'b0) begin
+                    case (SP)
+                        3'd4: begin SP = 3'd3; stack_mem[3] = dataIn; end
+                        3'd3: begin SP = 3'd2; stack_mem[2] = dataIn; end
+                        3'd2: begin SP = 3'd1; stack_mem[1] = dataIn; end
+                        3'd1: begin SP = 3'd0; stack_mem[0] = dataIn; end
+                        default: begin end
+                    endcase
+                end else if (RW == 1'b1) begin
+                    case (SP)
+                        3'd0: begin dataOut = stack_mem[0]; SP = 3'd1; end
+                        3'd1: begin dataOut = stack_mem[1]; SP = 3'd2; end
+                        3'd2: begin dataOut = stack_mem[2]; SP = 3'd3; end
+                        3'd3: begin dataOut = stack_mem[3]; SP = 3'd4; end
+                        default: begin end
+                    endcase
+                end
+
+                FULL = (SP == 3'd0);
                 EMPTY = SP[2];
-                dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
-                end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
             end
         end
```

## 29. cfc46f39b150eaf — rtllm_LIFObuffer — gpt-5.6-terra — requested d -> rule c1 — label tradeoff

rule evidence: ["flip-flop bits 57 -> 24 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -10,40 +10,80 @@
 );
 
-    reg [3:0] stack_mem[0:3];
+    reg [3:0] stack0;
+    reg [3:0] stack1;
+    reg [3:0] stack2;
+    reg [3:0] stack3;
     reg [2:0] SP;
-    integer i;
 
-    always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
+    always @(*) begin
+        EMPTY = SP[2];
+    end
+
+    always @(posedge Clk) begin
+        if (EN == 1'b0) begin
         end else begin
-            if (Rst == 1) begin
+            if (Rst == 1'b1) begin
                 SP = 3'd4;
-                EMPTY = SP[2];
                 dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
+                stack0 = 4'h0;
+                stack1 = 4'h0;
+                stack2 = 4'h0;
+                stack3 = 4'h0;
+            end else if (Rst == 1'b0) begin
+                FULL = (SP == 3'd0);
+                dataOut = 4'hx;
+
+                if ((SP != 3'd0) && (RW == 1'b0)) begin
+                    case (SP)
+                        3'd1: begin
+                            SP = 3'd0;
+                            FULL = 1'b1;
+                            stack0 = dataIn;
+                        end
+                        3'd2: begin
+                            SP = 3'd1;
+                            FULL = 1'b0;
+                            stack1 = dataIn;
+                        end
+                        3'd3: begin
+                            SP = 3'd2;
+                            FULL = 1'b0;
+                            stack2 = dataIn;
+                        end
+                        3'd4: begin
+                            SP = 3'd3;
+                            FULL = 1'b0;
+                            stack3 = dataIn;
+                        end
+                        default: begin
+                            SP = SP - 3'd1;
+                            FULL = 1'b0;
+                        end
+                    endcase
+                end else if ((SP[2] == 1'b0) && (RW == 1'b1)) begin
+                    case (SP)
+                        3'd0: begin
+                            dataOut = stack0;
+                            stack0 = 4'h0;
+                            SP = 3'd1;
+                        end
+                        3'd1: begin
+                            dataOut = stack1;
+                            stack1 = 4'h0;
+                            SP = 3'd2;
+                        end
+                        3'd2: begin
+                            dataOut = stack2;
+                            stack2 = 4'h0;
+                            SP = 3'd3;
+                        end
+                        default: begin
+                            dataOut = stack3;
+                            stack3 = 4'h0;
+                            SP = 3'd4;
+                        end
+                    endcase
+                    FULL = 1'b0;
                 end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
             end
         end
```

## 30. cfe1ddcc1168acb — rtllm_traffic_light — gpt-5.6-luna — requested b -> rule c1 — label nonequiv

rule evidence: ["flip-flop bits 16 -> 12 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -3,99 +3,77 @@
 module traffic_light
     (
-		input rst_n, 
-      input clk, 
-      input pass_request,
-		  output wire[7:0]clock,
-      output reg red,
-		  output reg yellow,
-		  output reg green
+        input rst_n,
+        input clk,
+        input pass_request,
+        output wire[7:0] clock,
+        output reg red,
+        output reg yellow,
+        output reg green
     );
-	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
-				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+    parameter s1_red    = 2'd0,
+              s3_green  = 2'd1,
+              s2_yellow = 2'd2,
+              idle       = 2'd3;
 
-always @(posedge clk or negedge rst_n) 
-    begin
-        if(!rst_n)
-        begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
+    reg [5:0] cnt;
+    reg [1:0] state;
+    reg [1:0] state_d1;
+    reg [1:0] state_d2;
+
+    wire state_d1_red    = (state_d1 == s1_red);
+    wire state_d1_yellow = (state_d1 == s2_yellow);
+    wire state_d1_green  = (state_d1 == s3_green);
+    wire state_d2_red    = (state_d2 == s1_red);
+    wire state_d2_yellow = (state_d2 == s2_yellow);
+    wire state_d2_green  = (state_d2 == s3_green);
+    wire count_is_three  = (cnt == 6'd3);
+    wire count_above_ten = (cnt > 6'd10);
+
+    always @(posedge clk or negedge rst_n) begin
+        if (!rst_n) begin
+            state    <= idle;
+            state_d1 <= idle;
+            state_d2 <= idle;
         end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
-	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
+        else begin
+            state_d2 <= state_d1;
+            state_d1 <= state;
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+            if (state == idle)
+                state <= s1_red;
+            else if (count_is_three) begin
+                if (state == s1_red)
+                    state <= s2_yellow;
+                else
+                    state <= state - 1'b1;
+            end
+            else
+                state <= state;
+        end
+    end
+
+    always @(*) begin
+        red    = state_d2_red;
+        yellow = state_d2_yellow;
+        green  = state_d2_green;
+    end
+
+    always @(posedge clk or negedge rst_n) begin
+        if (!rst_n)
+            cnt <= 6'd10;
+        else if (pass_request && state_d2_green && count_above_ten)
+            cnt <= 6'd10;
+        else if (!state_d2_green && state_d1_green)
+            cnt <= 6'd60;
+        else if (!state_d2_yellow && state_d1_yellow)
+            cnt <= 6'd5;
+        else if (!state_d2_red && state_d1_red)
+            cnt <= 6'd10;
+        else
+            cnt <= cnt - 1'b1;
+    end
+
+    assign clock = {2'b00, cnt};
 
 endmodule
```

## 31. c4294c201570633 — rtllm_LIFObuffer — gpt-5.6-terra — requested d -> rule c1 — label tradeoff

rule evidence: ["flip-flop bits 57 -> 24 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -10,40 +10,79 @@
 );
 
-    reg [3:0] stack_mem[0:3];
+    reg [3:0] top_data;
+    reg [3:0] level1_data;
+    reg [3:0] level2_data;
+    reg [3:0] level3_data;
     reg [2:0] SP;
-    integer i;
 
-    always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
+    always @(*) begin
+        EMPTY = SP[2];
+    end
+
+    always @(posedge Clk) begin
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
                 SP = 3'd4;
-                EMPTY = SP[2];
                 dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
+                top_data = 4'h0;
+                level1_data = 4'h0;
+                level2_data = 4'h0;
+                level3_data = 4'h0;
+            end else if (Rst == 1'b0) begin
+                FULL = (SP == 3'd0);
+                dataOut = 4'hx;
+
+                if ((SP != 3'd0) && (RW == 1'b0)) begin
+                    level3_data = level2_data;
+                    level2_data = level1_data;
+                    level1_data = top_data;
+                    top_data = dataIn;
+                    case (SP)
+                        3'd1: begin
+                            SP = 3'd0;
+                            FULL = 1'b1;
+                        end
+                        3'd2: begin
+                            SP = 3'd1;
+                            FULL = 1'b0;
+                        end
+                        3'd3: begin
+                            SP = 3'd2;
+                            FULL = 1'b0;
+                        end
+                        3'd4: begin
+                            SP = 3'd3;
+                            FULL = 1'b0;
+                        end
+                        default: begin
+                            SP = SP - 3'd1;
+                            FULL = (SP == 3'd0);
+                        end
+                    endcase
+                end else if ((SP[2] == 1'b0) && (RW == 1'b1)) begin
+                    dataOut = top_data;
+                    top_data = level1_data;
+                    level1_data = level2_data;
+                    level2_data = level3_data;
+                    level3_data = 4'h0;
+                    case (SP)
+                        3'd0: begin
+                            SP = 3'd1;
+                            FULL = 1'b0;
+                        end
+                        3'd1: begin
+                            SP = 3'd2;
+                            FULL = 1'b0;
+                        end
+                        3'd2: begin
+                            SP = 3'd3;
+                            FULL = 1'b0;
+                        end
+                        default: begin
+                            SP = 3'd4;
+                            FULL = 1'b0;
+                        end
+                    endcase
                 end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
             end
         end
```

## 32. cfa21f3d4abcbcb — rtllm_LIFObuffer — gpt-5.4 — requested a -> rule c1 — label retained

rule evidence: ["flip-flop bits 57 -> 25 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -12,38 +12,71 @@
     reg [3:0] stack_mem[0:3];
     reg [2:0] SP;
-    integer i;
 
     always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
+        if (EN) begin
+            if (Rst) begin
                 SP = 3'd4;
-                EMPTY = SP[2];
+                EMPTY = 1'b1;
                 dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
-                end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
+                stack_mem[0] = 4'h0;
+                stack_mem[1] = 4'h0;
+                stack_mem[2] = 4'h0;
+                stack_mem[3] = 4'h0;
+            end else begin
+                FULL = ~|SP;
                 EMPTY = SP[2];
                 dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
+
+                if (!RW) begin
+                    case (SP)
+                        3'd1: begin
+                            SP = 3'd0;
+                            FULL = 1'b1;
+                            stack_mem[0] = dataIn;
+                        end
+                        3'd2: begin
+                            SP = 3'd1;
+                            stack_mem[1] = dataIn;
+                        end
+                        3'd3: begin
+                            SP = 3'd2;
+                            stack_mem[2] = dataIn;
+                        end
+                        3'd4: begin
+                            SP = 3'd3;
+                            EMPTY = 1'b0;
+                            stack_mem[3] = dataIn;
+                        end
+                        default: begin
+                        end
+                    endcase
                 end else begin
-                    // Do nothing if neither condition is met
+                    case (SP)
+                        3'd0: begin
+                            dataOut = stack_mem[0];
+                            stack_mem[0] = 4'h0;
+                            SP = 3'd1;
+                            FULL = 1'b0;
+                        end
+                        3'd1: begin
+                            dataOut = stack_mem[1];
+                            stack_mem[1] = 4'h0;
+                            SP = 3'd2;
+                        end
+                        3'd2: begin
+                            dataOut = stack_mem[2];
+                            stack_mem[2] = 4'h0;
+                            SP = 3'd3;
+                        end
+                        3'd3: begin
+                            dataOut = stack_mem[3];
+                            stack_mem[3] = 4'h0;
+                            SP = 3'd4;
+                            EMPTY = 1'b1;
+                        end
+                        default: begin
+                        end
+                    endcase
                 end
-            end else begin
-                // Do nothing if neither condition is met
             end
         end
```

## 33. c70ab0689a6b700 — rtllm_traffic_light — gpt-5.4-mini — requested a -> rule c1 — label retained

rule evidence: ["flip-flop bits 16 -> 12 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -16,86 +16,84 @@
 				s2_yellow = 2'd2,
 				s3_green = 2'd3;
-	reg [7:0] cnt;
+
+	reg [5:0] cnt;
 	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
+	reg [1:0] state_d1;
+	reg [1:0] state_d2;
 
+	wire cnt_is3  = (cnt == 6'd3);
+	wire cnt_gt10 = (|cnt[5:4]) | (cnt[3:0] > 4'd10);
 
-always @(posedge clk or negedge rst_n) 
+	wire vis_red    = (state_d2 == s1_red);
+	wire vis_yellow = (state_d2 == s2_yellow);
+	wire vis_green  = (state_d2 == s3_green);
+
+	wire prev_red    = (state_d1 == s1_red);
+	wire prev_yellow = (state_d1 == s2_yellow);
+	wire prev_green  = (state_d1 == s3_green);
+
+	always @(posedge clk or negedge rst_n) 
     begin
         if(!rst_n)
         begin
 			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
+			state_d1 <= idle;
+			state_d2 <= idle;
+			cnt <= 6'd10;
         end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
+        else begin
+			state_d2 <= state_d1;
+			state_d1 <= state;
+			case(state)
+			idle:
 				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
+			s1_red:
+				begin
+					if (cnt_is3) 
+						state <= s3_green;
+					else
+						state <= s1_red;
+				end
+			s2_yellow:
+				begin
+					if (cnt_is3) 
+						state <= s1_red;
+					else
+						state <= s2_yellow;
+				end
+			s3_green:
+				begin
+					if (cnt_is3) 
+						state <= s2_yellow;
+					else
+						state <= s3_green;
+				end
+			endcase
+
+			if (pass_request && vis_green && cnt_gt10)
+				cnt <= 6'd10;
+			else if (!vis_green && prev_green)
+				cnt <= 6'd60;
+			else if (!vis_yellow && prev_yellow)
+				cnt <= 6'd5;
+			else if (!vis_red && prev_red)
+				cnt <= 6'd10;
+			else
+				cnt <= cnt - 6'd1;
+        end
+	end
+
+	always @* begin
+		red = 1'b0;
+		yellow = 1'b0;
+		green = 1'b0;
+		case (state_d2)
+			s1_red:     red = 1'b1;
+			s2_yellow:  yellow = 1'b1;
+			s3_green:   green = 1'b1;
 		endcase
 	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+	assign clock = {2'b00, cnt};
 
 endmodule
```

## 34. c813009d855d5a9 — rtllm_multi_pipe_8bit — gpt-5.4-mini — requested a -> rule c1 — label retained

rule evidence: ["flip-flop bits 116 -> 68 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -21,5 +21,4 @@
    output reg [size*2-1:0] mul_out;    
  
-            
    reg [2:0] mul_en_out_reg;
  always@(posedge clk or negedge rst_n)
@@ -34,6 +33,6 @@
  
  
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
+    reg [size-1:0] mul_a_reg;
+    reg [size-1:0] mul_b_reg;
   always @(posedge clk or negedge rst_n)
          if(!rst_n) begin
@@ -46,40 +45,22 @@
          end
  
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
+  wire [size*2-1:0] mul_prod;
+  assign mul_prod = mul_a_reg * mul_b_reg;
  
+     reg [size*2-1:0] prod_reg;
+ always @(posedge clk or negedge rst_n)
+       if(!rst_n)
+          prod_reg <= 'd0;
+       else
+          prod_reg <= mul_prod;
  
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
-       else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
-       end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
+     reg [size*2-1:0] mul_out_reg;
+ always @(posedge clk or negedge rst_n)
        if(!rst_n)
           mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
+       else
+          mul_out_reg <= prod_reg;
  
- 
- always @(posedge clk or negedge rst_n) 
+ always @(posedge clk or negedge rst_n)
        if(!rst_n)
           mul_out <= 'd0;
@@ -88,5 +69,4 @@
        else
           mul_out <= 'd0;
- 
           
 endmodule
```

## 35. ce6a2f3a815884a — rtllm_traffic_light — gpt-5.6-terra — requested c1 -> rule c1 — label retained

rule evidence: ["flip-flop bits 16 -> 14 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -3,99 +3,119 @@
 module traffic_light
     (
-		input rst_n, 
-      input clk, 
-      input pass_request,
-		  output wire[7:0]clock,
-      output reg red,
-		  output reg yellow,
-		  output reg green
+        input rst_n, 
+        input clk, 
+        input pass_request,
+        output wire[7:0]clock,
+        output reg red,
+        output reg yellow,
+        output reg green
     );
-	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
-				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+    parameter idle      = 2'd0,
+              s1_red    = 2'd1,
+              s2_yellow = 2'd2,
+              s3_green  = 2'd3;
 
-always @(posedge clk or negedge rst_n) 
+    reg [5:0] cnt;
+    reg [1:0] state;
+    reg [1:0] p_phase;
+    reg [1:0] out_phase;
+    reg cnt_is_3;
+    reg cnt_gt_10;
+
+    always @(posedge clk or negedge rst_n)
     begin
-        if(!rst_n)
+        if (!rst_n)
         begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
+            state   <= idle;
+            p_phase <= idle;
         end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
-	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
+        else
+        begin
+            p_phase <= state;
+            case (state)
+                idle:
+                    state <= s1_red;
+                s1_red:
+                    if (cnt_is_3)
+                        state <= s3_green;
+                    else
+                        state <= s1_red;
+                s2_yellow:
+                    if (cnt_is_3)
+                        state <= s1_red;
+                    else
+                        state <= s2_yellow;
+                s3_green:
+                    if (cnt_is_3)
+                        state <= s2_yellow;
+                    else
+                        state <= s3_green;
+            endcase
+        end
+    end
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+    always @(posedge clk or negedge rst_n)
+    begin
+        if (!rst_n)
+        begin
+            cnt       <= 6'd10;
+            cnt_is_3  <= 1'b0;
+            cnt_gt_10 <= 1'b0;
+        end
+        else if (pass_request && green && cnt_gt_10)
+        begin
+            cnt       <= 6'd10;
+            cnt_is_3  <= 1'b0;
+            cnt_gt_10 <= 1'b0;
+        end
+        else if (!green && (p_phase == s3_green))
+        begin
+            cnt       <= 6'd60;
+            cnt_is_3  <= 1'b0;
+            cnt_gt_10 <= 1'b1;
+        end
+        else if (!yellow && (p_phase == s2_yellow))
+        begin
+            cnt       <= 6'd5;
+            cnt_is_3  <= 1'b0;
+            cnt_gt_10 <= 1'b0;
+        end
+        else if (!red && (p_phase == s1_red))
+        begin
+            cnt       <= 6'd10;
+            cnt_is_3  <= 1'b0;
+            cnt_gt_10 <= 1'b0;
+        end
+        else
+        begin
+            cnt       <= cnt - 1'b1;
+            cnt_is_3  <= (cnt == 6'd4);
+            cnt_gt_10 <= (cnt > 6'd11) || (cnt == 6'd0);
+        end
+    end
+
+    always @(posedge clk or negedge rst_n)
+    begin
+        if (!rst_n)
+            out_phase <= idle;
+        else
+            out_phase <= p_phase;
+    end
+
+    always @*
+    begin
+        red    = 1'b0;
+        yellow = 1'b0;
+        green  = 1'b0;
+        case (out_phase)
+            s1_red:    red    = 1'b1;
+            s2_yellow: yellow = 1'b1;
+            s3_green:  green  = 1'b1;
+            default: begin end
+        endcase
+    end
+
+    assign clock = {2'b00, cnt};
 
 endmodule
```

## 36. c0b9e5eeb2a76ec — rtllm_LIFObuffer — gpt-5.6-terra — requested a -> rule c1 — label nonequiv

rule evidence: ["flip-flop bits 57 -> 24 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -10,40 +10,32 @@
 );
 
-    reg [3:0] stack_mem[0:3];
-    reg [2:0] SP;
-    integer i;
+    reg [15:0] stack_data;
+    reg [1:0] SPlo;
 
     always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
-                SP = 3'd4;
-                EMPTY = SP[2];
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
+                SPlo = 2'd0;
+                EMPTY = 1'b1;
                 dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
+            end else if (Rst == 1'b0) begin
+                dataOut = 4'hx;
+
+                if ((RW == 1'b0) && (EMPTY || (|SPlo))) begin
+                    stack_data = {dataIn, stack_data[15:4]};
+                    FULL = (~SPlo[1]) & SPlo[0];
+                    SPlo = {~SPlo[1], ~(SPlo[1] ^ SPlo[0])};
+                    if (EMPTY == 1'b1)
+                        EMPTY = 1'b0;
+                end else if ((RW == 1'b1) && (EMPTY == 1'b0)) begin
+                    dataOut = stack_data[15:12];
+                    stack_data = {stack_data[11:0], 4'b0000};
+                    FULL = 1'b0;
+                    if (&SPlo)
+                        EMPTY = 1'b1;
+                    SPlo = {SPlo[1] ^ SPlo[0], ~SPlo[0]};
+                end else begin
+                    FULL = (~EMPTY) & (~|SPlo);
                 end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
             end
         end
```

## 37. c4cc1bf0a3b1bdc — rtllm_traffic_light — gpt-5.6-luna — requested free -> rule c1 — label retained

rule evidence: ["flip-flop bits 16 -> 12 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -3,99 +3,83 @@
 module traffic_light
     (
-		input rst_n, 
-      input clk, 
-      input pass_request,
-		  output wire[7:0]clock,
-      output reg red,
-		  output reg yellow,
-		  output reg green
+        input rst_n,
+        input clk,
+        input pass_request,
+        output wire [7:0] clock,
+        output reg red,
+        output reg yellow,
+        output reg green
     );
-	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
-				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+    parameter s1_red    = 2'd0,
+              s3_green  = 2'd1,
+              s2_yellow = 2'd2,
+              idle      = 2'd3;
 
-always @(posedge clk or negedge rst_n) 
-    begin
-        if(!rst_n)
-        begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
+    reg [5:0] cnt;
+    reg [1:0] state;
+    reg [1:0] state_d1;
+    reg [1:0] state_d2;
+
+    wire p_red_i;
+    wire p_yellow_i;
+    wire p_green_i;
+    wire red_i;
+    wire yellow_i;
+    wire green_i;
+
+    assign p_red_i    = ~state_d1[1] & ~state_d1[0];
+    assign p_green_i  = ~state_d1[1] &  state_d1[0];
+    assign p_yellow_i =  state_d1[1] & ~state_d1[0];
+
+    assign red_i      = ~state_d2[1] & ~state_d2[0];
+    assign green_i    = ~state_d2[1] &  state_d2[0];
+    assign yellow_i   =  state_d2[1] & ~state_d2[0];
+
+    always @(posedge clk or negedge rst_n) begin
+        if (!rst_n) begin
+            state    <= idle;
+            state_d1 <= idle;
+            state_d2 <= idle;
         end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
-	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
+        else begin
+            state_d1 <= state;
+            state_d2 <= state_d1;
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+            if (state == idle)
+                state <= s1_red;
+            else if (cnt == 6'd3) begin
+                case (state)
+                    s1_red:    state <= s3_green;
+                    s3_green:  state <= s2_yellow;
+                    s2_yellow: state <= s1_red;
+                    default:   state <= idle;
+                endcase
+            end
+        end
+    end
+
+    always @(posedge clk or negedge rst_n) begin
+        if (!rst_n)
+            cnt <= 6'd10;
+        else if (pass_request && green_i && (cnt > 6'd10))
+            cnt <= 6'd10;
+        else if (!green_i && p_green_i)
+            cnt <= 6'd60;
+        else if (!yellow_i && p_yellow_i)
+            cnt <= 6'd5;
+        else if (!red_i && p_red_i)
+            cnt <= 6'd10;
+        else
+            cnt <= cnt - 1'b1;
+    end
+
+    assign clock = {2'b00, cnt};
+
+    always @* begin
+        red    = red_i;
+        yellow = yellow_i;
+        green  = green_i;
+    end
 
 endmodule
```

## 38. c1cc13efbd2c34d — rtllm_traffic_light — gpt-5.4 — requested free -> rule c1 — label tradeoff

rule evidence: ["flip-flop bits 16 -> 8 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -16,86 +16,65 @@
 				s2_yellow = 2'd2,
 				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+	reg [5:0] cnt;
+	reg [1:0] phase;
 
-always @(posedge clk or negedge rst_n) 
-    begin
-        if(!rst_n)
-        begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
-        end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
+	assign clock = {2'b00, cnt};
+
+	always @(posedge clk or negedge rst_n) begin
+		if(!rst_n) begin
+			phase <= idle;
+			cnt <= 6'd10;
+		end
+		else begin
+			case (phase)
+				idle: begin
+					if (cnt == 6'd8) begin
+						phase <= s1_red;
+						cnt <= 6'd10;
+					end
+					else begin
+						cnt <= cnt - 6'd1;
+					end
+				end
+				s1_red: begin
+					if (cnt == 6'd1) begin
+						phase <= s3_green;
+						cnt <= 6'd60;
+					end
+					else begin
+						cnt <= cnt - 6'd1;
+					end
+				end
+				s2_yellow: begin
+					if (cnt == 6'd1) begin
+						phase <= s1_red;
+						cnt <= 6'd10;
+					end
+					else begin
+						cnt <= cnt - 6'd1;
+					end
+				end
+				s3_green: begin
+					if (pass_request && (cnt > 6'd10)) begin
+						cnt <= 6'd10;
+					end
+					else if (cnt == 6'd1) begin
+						phase <= s2_yellow;
+						cnt <= 6'd5;
+					end
+					else begin
+						cnt <= cnt - 6'd1;
+					end
+				end
+			endcase
+		end
 	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+	always @(*) begin
+		red = phase[0] & ~phase[1];
+		yellow = ~phase[0] & phase[1];
+		green = phase[0] & phase[1];
+	end
 
 endmodule
```

## 39. cab845aa437aa16 — rtllm_multi_pipe_8bit — gpt-5.4-mini — requested c1 -> rule c1 — label nonequiv

rule evidence: ["flip-flop bits 116 -> 77 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -21,72 +21,69 @@
    output reg [size*2-1:0] mul_out;    
  
-            
    reg [2:0] mul_en_out_reg;
- always@(posedge clk or negedge rst_n)
-       if(!rst_n)begin
-            mul_en_out_reg <= 'd0;             
-            mul_en_out     <= 'd0;                           
-       end
-       else begin
-            mul_en_out_reg <= {mul_en_out_reg[1:0],mul_en_in};            
-            mul_en_out     <= mul_en_out_reg[2];                  
-       end
- 
- 
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
-  always @(posedge clk or negedge rst_n)
-         if(!rst_n) begin
-              mul_a_reg <= 'd0;
-              mul_a_reg <= 'd0;
-         end
-         else begin
-              mul_a_reg <= mul_en_in ? mul_a :'d0;
-              mul_b_reg <= mul_en_in ? mul_b :'d0;
-         end
- 
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
-       else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
-       end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
- 
- 
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out <= 'd0;
-       else if(mul_en_out_reg[2])
-          mul_out <= mul_out_reg;
-       else
-          mul_out <= 'd0;
- 
-          
+   always @(posedge clk or negedge rst_n)
+     if(!rst_n) begin
+       mul_en_out_reg <= 3'd0;
+       mul_en_out     <= 1'b0;
+     end else begin
+       mul_en_out_reg <= {mul_en_out_reg[1:0], mul_en_in};
+       mul_en_out     <= mul_en_out_reg[2];
+     end
+
+   reg [3:0] mul_a_lo_reg;
+   reg [3:0] mul_a_hi_reg;
+   reg [3:0] mul_b_lo_reg;
+   reg [3:0] mul_b_hi_reg;
+
+   always @(posedge clk or negedge rst_n)
+     if(!rst_n) begin
+       mul_a_lo_reg <= 4'd0;
+       mul_a_hi_reg <= 4'd0;
+       mul_b_lo_reg <= 4'd0;
+       mul_b_hi_reg <= 4'd0;
+     end else if(mul_en_in) begin
+       mul_a_lo_reg <= mul_a[3:0];
+       mul_a_hi_reg <= mul_a[7:4];
+       mul_b_lo_reg <= mul_b[3:0];
+       mul_b_hi_reg <= mul_b[7:4];
+     end else begin
+       mul_a_lo_reg <= 4'd0;
+       mul_a_hi_reg <= 4'd0;
+       mul_b_lo_reg <= 4'd0;
+       mul_b_hi_reg <= 4'd0;
+     end
+
+   reg [7:0] mul_p00_reg;
+   reg [8:0] mul_cross_reg;
+   reg [7:0] mul_p11_reg;
+
+   always @(posedge clk or negedge rst_n)
+     if(!rst_n) begin
+       mul_p00_reg   <= 8'd0;
+       mul_cross_reg <= 9'd0;
+       mul_p11_reg   <= 8'd0;
+     end else begin
+       mul_p00_reg   <= mul_a_lo_reg * mul_b_lo_reg;
+       mul_cross_reg <= (mul_a_lo_reg * mul_b_hi_reg) + (mul_a_hi_reg * mul_b_lo_reg);
+       mul_p11_reg   <= mul_a_hi_reg * mul_b_hi_reg;
+     end
+
+   wire [15:0] mul_stage3_sum;
+   assign mul_stage3_sum = {mul_p11_reg, 8'b0} + {3'b0, mul_cross_reg, 4'b0} + {8'b0, mul_p00_reg};
+
+   reg [15:0] mul_out_reg;
+   always @(posedge clk or negedge rst_n)
+     if(!rst_n)
+       mul_out_reg <= 16'd0;
+     else
+       mul_out_reg <= mul_stage3_sum;
+
+   always @(posedge clk or negedge rst_n)
+     if(!rst_n)
+       mul_out <= {size*2{1'b0}};
+     else if(mul_en_out_reg[2])
+       mul_out <= mul_out_reg;
+     else
+       mul_out <= {size*2{1'b0}};
+
 endmodule
```

## 40. c501fafcecf20f1 — rtllm_multi_pipe_8bit — gpt-5.6-luna — requested d -> rule c1 — label retained

rule evidence: ["flip-flop bits 116 -> 84 with identical latency (no offset)"]

```diff
--- D
+++ C
@@ -2,91 +2,100 @@
     parameter size = 8
 )(
-          clk,      
-          rst_n,       
-          mul_a,       
-          mul_b, 
-          mul_en_in,
- 
-          mul_en_out,      
-          mul_out    
+    clk,
+    rst_n,
+    mul_a,
+    mul_b,
+    mul_en_in,
+    mul_en_out,
+    mul_out
 );
- 
-   input clk;           
-   input rst_n; 
-   input mul_en_in;      
-   input [size-1:0] mul_a;       
-   input [size-1:0] mul_b;       
- 
-   output reg mul_en_out;  
-   output reg [size*2-1:0] mul_out;    
- 
-            
+
+   input clk;
+   input rst_n;
+   input mul_en_in;
+   input [size-1:0] mul_a;
+   input [size-1:0] mul_b;
+
+   output reg mul_en_out;
+   output reg [size*2-1:0] mul_out;
+
    reg [2:0] mul_en_out_reg;
- always@(posedge clk or negedge rst_n)
-       if(!rst_n)begin
-            mul_en_out_reg <= 'd0;             
-            mul_en_out     <= 'd0;                           
-       end
-       else begin
-            mul_en_out_reg <= {mul_en_out_reg[1:0],mul_en_in};            
-            mul_en_out     <= mul_en_out_reg[2];                  
-       end
- 
- 
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
-  always @(posedge clk or negedge rst_n)
-         if(!rst_n) begin
-              mul_a_reg <= 'd0;
-              mul_a_reg <= 'd0;
-         end
-         else begin
-              mul_a_reg <= mul_en_in ? mul_a :'d0;
-              mul_b_reg <= mul_en_in ? mul_b :'d0;
-         end
- 
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
-       else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
-       end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
- 
- 
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out <= 'd0;
-       else if(mul_en_out_reg[2])
-          mul_out <= mul_out_reg;
-       else
-          mul_out <= 'd0;
- 
-          
+   always @(posedge clk or negedge rst_n)
+     if (!rst_n) begin
+        mul_en_out_reg <= 3'd0;
+        mul_en_out     <= 1'b0;
+     end
+     else begin
+        mul_en_out_reg <= {mul_en_out_reg[1:0], mul_en_in};
+        mul_en_out     <= mul_en_out_reg[2];
+     end
+
+   reg [7:0] mul_a_reg;
+   reg [7:0] mul_b_reg;
+   always @(posedge clk or negedge rst_n)
+     if (!rst_n) begin
+        mul_a_reg <= 8'd0;
+        mul_b_reg <= 8'd0;
+     end
+     else begin
+        mul_a_reg <= mul_en_in ? mul_a : 8'd0;
+        mul_b_reg <= mul_en_in ? mul_b : 8'd0;
+     end
+
+   wire [15:0] radix4_pp0;
+   wire [15:0] radix4_pp1;
+   wire [15:0] radix4_pp2;
+   wire [15:0] radix4_pp3;
+
+   assign radix4_pp0 =
+          (mul_b_reg[1:0] == 2'b00) ? 16'd0 :
+          (mul_b_reg[1:0] == 2'b01) ? {8'b0, mul_a_reg} :
+          (mul_b_reg[1:0] == 2'b10) ? {7'b0, mul_a_reg, 1'b0} :
+                                      ({8'b0, mul_a_reg} + {7'b0, mul_a_reg, 1'b0});
+
+   assign radix4_pp1 =
+          (mul_b_reg[3:2] == 2'b00) ? 16'd0 :
+          (mul_b_reg[3:2] == 2'b01) ? {6'b0, mul_a_reg, 2'b0} :
+          (mul_b_reg[3:2] == 2'b10) ? {5'b0, mul_a_reg, 3'b0} :
+                                      ({6'b0, mul_a_reg, 2'b0} + {5'b0, mul_a_reg, 3'b0});
+
+   assign radix4_pp2 =
+          (mul_b_reg[5:4] == 2'b00) ? 16'd0 :
+          (mul_b_reg[5:4] == 2'b01) ? {4'b0, mul_a_reg, 4'b0} :
+          (mul_b_reg[5:4] == 2'b10) ? {3'b0, mul_a_reg, 5'b0} :
+                                      ({4'b0, mul_a_reg, 4'b0} + {3'b0, mul_a_reg, 5'b0});
+
+   assign radix4_pp3 =
+          (mul_b_reg[7:6] == 2'b00) ? 16'd0 :
+          (mul_b_reg[7:6] == 2'b01) ? {2'b0, mul_a_reg, 6'b0} :
+          (mul_b_reg[7:6] == 2'b10) ? {1'b0, mul_a_reg, 7'b0} :
+                                      ({2'b0, mul_a_reg, 6'b0} + {1'b0, mul_a_reg, 7'b0});
+
+   reg [15:0] radix4_low_reg;
+   reg [15:0] radix4_high_reg;
+   always @(posedge clk or negedge rst_n)
+     if (!rst_n) begin
+        radix4_low_reg  <= 16'd0;
+        radix4_high_reg <= 16'd0;
+     end
+     else begin
+        radix4_low_reg  <= radix4_pp0 + radix4_pp1;
+        radix4_high_reg <= radix4_pp2 + radix4_pp3;
+     end
+
+   reg [15:0] mul_out_reg;
+   always @(posedge clk or negedge rst_n)
+     if (!rst_n)
+        mul_out_reg <= 16'd0;
+     else
+        mul_out_reg <= radix4_low_reg + radix4_high_reg;
+
+   always @(posedge clk or negedge rst_n)
+     if (!rst_n)
+        mul_out <= 'd0;
+     else if (mul_en_out_reg[2])
+        mul_out <= mul_out_reg;
+     else
+        mul_out <= 'd0;
+
 endmodule
```

## 41. caf1dce11804fb5 — rtllm_adder_16bit — gpt-5.6-terra — requested free -> rule a — label tradeoff

rule evidence: ["flip-flop count, register names and clocked targets unchanged", "but the text differs widely (ratio 0.8583) -> review for (d)"]

```diff
--- D
+++ C
@@ -6,118 +6,40 @@
     output wire Co
 );
- 
-    wire Co_temp;
- 
-    add8 add8_inst1 (
-        .a(a[15:8]),
-        .b(b[15:8]),
-        .Cin(Co_temp), 
-        .y(y[15:8]),
-        .Co(Co)
-    );
- 
-    add8 add8_inst2 (
-        .a(a[7:0]),
-        .b(b[7:0]),
-        .Cin(Cin),
-        .y(y[7:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
 
-module add8 (
-    input wire [7:0] a,
-    input wire [7:0] b,
-    input wire Cin,
-    output wire [7:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add4 add4_inst1 (
-        .a(a[7:4]),
-        .b(b[7:4]),
-        .Cin(Co_temp),
-        .y(y[7:4]),
-        .Co(Co)
-    );
- 
-    add4 add4_inst2 (
-        .a(a[3:0]),
-        .b(b[3:0]),
-        .Cin(Cin),
-        .y(y[3:0]),
-        .Co(Co_temp)
-    );
- 
-endmodule
+    wire [15:0] p0;
+    wire [15:0] g0;
+    wire [15:0] p1, g1;
+    wire [15:0] p2, g2;
+    wire [15:0] p3, g3;
+    wire [15:0] p4, g4;
+    wire [16:0] c;
 
-module add4 (
-    input wire [3:0] a,
-    input wire [3:0] b,
-    input wire Cin,
-    output wire [3:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add2 add2_inst1 (
-        .a(a[3:2]),
-        .b(b[3:2]),
-        .Cin(Co_temp),
-        .y(y[3:2]),
-        .Co(Co)
-    );
- 
-    add2 add2_inst2 (
-        .a(a[1:0]),
-        .b(b[1:0]),
-        .Cin(Cin),
-        .y(y[1:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
+    assign p0 = a ^ b;
+    assign g0 = a & b;
 
-module add2 (
-    input wire [1:0] a,
-    input wire [1:0] b,
-    input wire Cin,
-    output wire [1:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
+    assign p1[0]    = p0[0];
+    assign g1[0]    = g0[0];
+    assign p1[15:1] = p0[15:1] & p0[14:0];
+    assign g1[15:1] = g0[15:1] | (p0[15:1] & g0[14:0]);
 
-    add1 add1_inst1 (
-        .a(a[1]),
-        .b(b[1]),
-        .Cin(Co_temp),
-        .y(y[1]),
-        .Co(Co)
-    );
- 
-    add1 add1_inst2 (
-        .a(a[0]),
-        .b(b[0]),
-        .Cin(Cin),
-        .y(y[0]),
-        .Co(Co_temp)
-    );
-         
-endmodule
+    assign p2[1:0]  = p1[1:0];
+    assign g2[1:0]  = g1[1:0];
+    assign p2[15:2] = p1[15:2] & p1[13:0];
+    assign g2[15:2] = g1[15:2] | (p1[15:2] & g1[13:0]);
 
-module add1 (
-    input wire a,
-    input wire b,
-    input wire Cin,
-    output wire y,
-    output wire Co
-);
-    assign y = ((~a) & (~b) & Cin | (~a) & b & (~Cin) | a & (~b) & (~Cin) | (a & b & Cin));
-    assign Co = ((~a & b & Cin) | (a & ~b & Cin) | (a & b & ~Cin) | (a & b & Cin));
+    assign p3[3:0]  = p2[3:0];
+    assign g3[3:0]  = g2[3:0];
+    assign p3[15:4] = p2[15:4] & p2[11:0];
+    assign g3[15:4] = g2[15:4] | (p2[15:4] & g2[11:0]);
+
+    assign p4[7:0]  = p3[7:0];
+    assign g4[7:0]  = g3[7:0];
+    assign p4[15:8] = p3[15:8] & p3[7:0];
+    assign g4[15:8] = g3[15:8] | (p3[15:8] & g3[7:0]);
+
+    assign c[0]    = Cin;
+    assign c[16:1] = g4 | (p4 & {16{Cin}});
+    assign y       = p0 ^ c[15:0];
+    assign Co      = c[16];
 
 endmodule
```

## 42. c888064c2a16509 — rtllm_adder_16bit — gpt-5.4-mini — requested free -> rule a — label absorbed_identical

rule evidence: ["flip-flop count, register names and clocked targets unchanged", "but the text differs widely (ratio 0.7936) -> review for (d)"]

```diff
--- D
+++ C
@@ -6,23 +6,68 @@
     output wire Co
 );
- 
-    wire Co_temp;
- 
-    add8 add8_inst1 (
-        .a(a[15:8]),
-        .b(b[15:8]),
-        .Cin(Co_temp), 
-        .y(y[15:8]),
-        .Co(Co)
-    );
- 
-    add8 add8_inst2 (
-        .a(a[7:0]),
-        .b(b[7:0]),
-        .Cin(Cin),
-        .y(y[7:0]),
-        .Co(Co_temp)
-    ); 
- 
+
+    wire [15:0] p;
+    wire [15:0] g;
+
+    wire P0, P1, P2, P3;
+    wire G0, G1, G2, G3;
+
+    wire c1, c2, c3, c4;
+    wire c5, c6, c7, c8;
+    wire c9, c10, c11, c12;
+    wire c13, c14, c15;
+
+    assign p = a ^ b;
+    assign g = a & b;
+
+    assign P0 = &p[3:0];
+    assign G0 = g[3] | (p[3] & g[2]) | (p[3] & p[2] & g[1]) | (p[3] & p[2] & p[1] & g[0]);
+    assign c4 = G0 | (P0 & Cin);
+
+    assign P1 = &p[7:4];
+    assign G1 = g[7] | (p[7] & g[6]) | (p[7] & p[6] & g[5]) | (p[7] & p[6] & p[5] & g[4]);
+    assign c8 = G1 | (P1 & c4);
+
+    assign P2 = &p[11:8];
+    assign G2 = g[11] | (p[11] & g[10]) | (p[11] & p[10] & g[9]) | (p[11] & p[10] & p[9] & g[8]);
+    assign c12 = G2 | (P2 & c8);
+
+    assign P3 = &p[15:12];
+    assign G3 = g[15] | (p[15] & g[14]) | (p[15] & p[14] & g[13]) | (p[15] & p[14] & p[13] & g[12]);
+    assign Co = G3 | (P3 & c12);
+
+    assign c1  = g[0]  | (p[0]  & Cin);
+    assign c2  = g[1]  | (p[1]  & g[0])  | (p[1]  & p[0]  & Cin);
+    assign c3  = g[2]  | (p[2]  & g[1])  | (p[2]  & p[1]  & g[0])  | (p[2]  & p[1]  & p[0]  & Cin);
+
+    assign c5  = g[4]  | (p[4]  & c4);
+    assign c6  = g[5]  | (p[5]  & g[4])  | (p[5]  & p[4]  & c4);
+    assign c7  = g[6]  | (p[6]  & g[5])  | (p[6]  & p[5]  & g[4])  | (p[6]  & p[5]  & p[4]  & c4);
+
+    assign c9  = g[8]  | (p[8]  & c8);
+    assign c10 = g[9]  | (p[9]  & g[8])  | (p[9]  & p[8]  & c8);
+    assign c11 = g[10] | (p[10] & g[9])  | (p[10] & p[9]  & g[8])  | (p[10] & p[9]  & p[8]  & c8);
+
+    assign c13 = g[12] | (p[12] & c12);
+    assign c14 = g[13] | (p[13] & g[12]) | (p[13] & p[12] & c12);
+    assign c15 = g[14] | (p[14] & g[13]) | (p[14] & p[13] & g[12]) | (p[14] & p[13] & p[12] & c12);
+
+    assign y[0]  = p[0]  ^ Cin;
+    assign y[1]  = p[1]  ^ c1;
+    assign y[2]  = p[2]  ^ c2;
+    assign y[3]  = p[3]  ^ c3;
+    assign y[4]  = p[4]  ^ c4;
+    assign y[5]  = p[5]  ^ c5;
+    assign y[6]  = p[6]  ^ c6;
+    assign y[7]  = p[7]  ^ c7;
+    assign y[8]  = p[8]  ^ c8;
+    assign y[9]  = p[9]  ^ c9;
+    assign y[10] = p[10] ^ c10;
+    assign y[11] = p[11] ^ c11;
+    assign y[12] = p[12] ^ c12;
+    assign y[13] = p[13] ^ c13;
+    assign y[14] = p[14] ^ c14;
+    assign y[15] = p[15] ^ c15;
+
 endmodule
 
@@ -34,23 +79,39 @@
     output wire Co
 );
- 
-    wire Co_temp;
- 
-    add4 add4_inst1 (
-        .a(a[7:4]),
-        .b(b[7:4]),
-        .Cin(Co_temp),
-        .y(y[7:4]),
-        .Co(Co)
-    );
- 
-    add4 add4_inst2 (
-        .a(a[3:0]),
-        .b(b[3:0]),
-        .Cin(Cin),
-        .y(y[3:0]),
-        .Co(Co_temp)
-    );
- 
+
+    wire [7:0] p;
+    wire [7:0] g;
+    wire P0, P1;
+    wire G0, G1;
+    wire c1, c2, c3, c4, c5, c6, c7;
+
+    assign p = a ^ b;
+    assign g = a & b;
+
+    assign P0 = &p[3:0];
+    assign G0 = g[3] | (p[3] & g[2]) | (p[3] & p[2] & g[1]) | (p[3] & p[2] & p[1] & g[0]);
+    assign c4 = G0 | (P0 & Cin);
+
+    assign P1 = &p[7:4];
+    assign G1 = g[7] | (p[7] & g[6]) | (p[7] & p[6] & g[5]) | (p[7] & p[6] & p[5] & g[4]);
+    assign Co = G1 | (P1 & c4);
+
+    assign c1 = g[0] | (p[0] & Cin);
+    assign c2 = g[1] | (p[1] & g[0]) | (p[1] & p[0] & Cin);
+    assign c3 = g[2] | (p[2] & g[1]) | (p[2] & p[1] & g[0]) | (p[2] & p[1] & p[0] & Cin);
+
+    assign c5 = g[4] | (p[4] & c4);
+    assign c6 = g[5] | (p[5] & g[4]) | (p[5] & p[4] & c4);
+    assign c7 = g[6] | (p[6] & g[5]) | (p[6] & p[5] & g[4]) | (p[6] & p[5] & p[4] & c4);
+
+    assign y[0] = p[0] ^ Cin;
+    assign y[1] = p[1] ^ c1;
+    assign y[2] = p[2] ^ c2;
+    assign y[3] = p[3] ^ c3;
+    assign y[4] = p[4] ^ c4;
+    assign y[5] = p[5] ^ c5;
+    assign y[6] = p[6] ^ c6;
+    assign y[7] = p[7] ^ c7;
+
 endmodule
 
@@ -62,23 +123,22 @@
     output wire Co
 );
- 
-    wire Co_temp;
- 
-    add2 add2_inst1 (
-        .a(a[3:2]),
-        .b(b[3:2]),
-        .Cin(Co_temp),
-        .y(y[3:2]),
-        .Co(Co)
-    );
- 
-    add2 add2_inst2 (
-        .a(a[1:0]),
-        .b(b[1:0]),
-        .Cin(Cin),
-        .y(y[1:0]),
-        .Co(Co_temp)
-    ); 
- 
+
+    wire [3:0] p;
+    wire [3:0] g;
+    wire c1, c2, c3;
+
+    assign p = a ^ b;
+    assign g = a & b;
+
+    assign c1 = g[0] | (p[0] & Cin);
+    assign c2 = g[1] | (p[1] & g[0]) | (p[1] & p[0] & Cin);
+    assign c3 = g[2] | (p[2] & g[1]) | (p[2] & p[1] & g[0]) | (p[2] & p[1] & p[0] & Cin);
+    assign Co = g[3] | (p[3] & g[2]) | (p[3] & p[2] & g[1]) | (p[3] & p[2] & p[1] & g[0]) | (p[3] & p[2] & p[1] & p[0] & Cin);
+
+    assign y[0] = p[0] ^ Cin;
+    assign y[1] = p[1] ^ c1;
+    assign y[2] = p[2] ^ c2;
+    assign y[3] = p[3] ^ c3;
+
 endmodule
 
@@ -90,23 +150,18 @@
     output wire Co
 );
- 
-    wire Co_temp;
 
-    add1 add1_inst1 (
-        .a(a[1]),
-        .b(b[1]),
-        .Cin(Co_temp),
-        .y(y[1]),
-        .Co(Co)
-    );
- 
-    add1 add1_inst2 (
-        .a(a[0]),
-        .b(b[0]),
-        .Cin(Cin),
-        .y(y[0]),
-        .Co(Co_temp)
-    );
-         
+    wire [1:0] p;
+    wire [1:0] g;
+    wire c1;
+
+    assign p = a ^ b;
+    assign g = a & b;
+
+    assign c1 = g[0] | (p[0] & Cin);
+    assign Co = g[1] | (p[1] & c1);
+
+    assign y[0] = p[0] ^ Cin;
+    assign y[1] = p[1] ^ c1;
+
 endmodule
 
@@ -118,6 +173,6 @@
     output wire Co
 );
-    assign y = ((~a) & (~b) & Cin | (~a) & b & (~Cin) | a & (~b) & (~Cin) | (a & b & Cin));
-    assign Co = ((~a & b & Cin) | (a & ~b & Cin) | (a & b & ~Cin) | (a & b & Cin));
+    assign y = a ^ b ^ Cin;
+    assign Co = (a & b) | (a & Cin) | (b & Cin);
 
 endmodule
```

## 43. c7573713980673c — rtllm_multi_pipe_8bit — gpt-5.4-mini — requested a -> rule a — label nonequiv

rule evidence: ["flip-flop count, register names and clocked targets unchanged"]

```diff
--- D
+++ C
@@ -21,7 +21,6 @@
    output reg [size*2-1:0] mul_out;    
  
-            
    reg [2:0] mul_en_out_reg;
- always@(posedge clk or negedge rst_n)
+   always@(posedge clk or negedge rst_n)
        if(!rst_n)begin
             mul_en_out_reg <= 'd0;             
@@ -47,16 +46,8 @@
  
   
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
+     reg [15:0] sum [3:0];
+     wire [15:0] partial_product;
+     assign partial_product = mul_a_reg * mul_b_reg;
+
  always @(posedge clk or negedge rst_n) 
        if(!rst_n) begin
@@ -67,8 +58,8 @@
        end 
        else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
+          sum[0] <= partial_product;
+          sum[1] <= 'd0;
+          sum[2] <= 'd0;
+          sum[3] <= 'd0;
        end
  
@@ -78,5 +69,5 @@
           mul_out_reg <= 'd0;
        else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
+          mul_out_reg <= sum[0];
  
  
```

## 44. cd4da8414dcee98 — rtllm_adder_16bit — gpt-5.4-mini — requested a -> rule a — label absorbed_identical

rule evidence: ["flip-flop count, register names and clocked targets unchanged", "but the text differs widely (ratio 0.8762) -> review for (d)"]

```diff
--- D
+++ C
@@ -6,118 +6,6 @@
     output wire Co
 );
- 
-    wire Co_temp;
- 
-    add8 add8_inst1 (
-        .a(a[15:8]),
-        .b(b[15:8]),
-        .Cin(Co_temp), 
-        .y(y[15:8]),
-        .Co(Co)
-    );
- 
-    add8 add8_inst2 (
-        .a(a[7:0]),
-        .b(b[7:0]),
-        .Cin(Cin),
-        .y(y[7:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
 
-module add8 (
-    input wire [7:0] a,
-    input wire [7:0] b,
-    input wire Cin,
-    output wire [7:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add4 add4_inst1 (
-        .a(a[7:4]),
-        .b(b[7:4]),
-        .Cin(Co_temp),
-        .y(y[7:4]),
-        .Co(Co)
-    );
- 
-    add4 add4_inst2 (
-        .a(a[3:0]),
-        .b(b[3:0]),
-        .Cin(Cin),
-        .y(y[3:0]),
-        .Co(Co_temp)
-    );
- 
-endmodule
-
-module add4 (
-    input wire [3:0] a,
-    input wire [3:0] b,
-    input wire Cin,
-    output wire [3:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add2 add2_inst1 (
-        .a(a[3:2]),
-        .b(b[3:2]),
-        .Cin(Co_temp),
-        .y(y[3:2]),
-        .Co(Co)
-    );
- 
-    add2 add2_inst2 (
-        .a(a[1:0]),
-        .b(b[1:0]),
-        .Cin(Cin),
-        .y(y[1:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
-
-module add2 (
-    input wire [1:0] a,
-    input wire [1:0] b,
-    input wire Cin,
-    output wire [1:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
-
-    add1 add1_inst1 (
-        .a(a[1]),
-        .b(b[1]),
-        .Cin(Co_temp),
-        .y(y[1]),
-        .Co(Co)
-    );
- 
-    add1 add1_inst2 (
-        .a(a[0]),
-        .b(b[0]),
-        .Cin(Cin),
-        .y(y[0]),
-        .Co(Co_temp)
-    );
-         
-endmodule
-
-module add1 (
-    input wire a,
-    input wire b,
-    input wire Cin,
-    output wire y,
-    output wire Co
-);
-    assign y = ((~a) & (~b) & Cin | (~a) & b & (~Cin) | a & (~b) & (~Cin) | (a & b & Cin));
-    assign Co = ((~a & b & Cin) | (a & ~b & Cin) | (a & b & ~Cin) | (a & b & Cin));
+    assign {Co, y} = {1'b0, a} + {1'b0, b} + Cin;
 
 endmodule
```

## 45. c8fc55d1e7afe09 — rtllm_adder_16bit — gpt-5.6-luna — requested free -> rule a — label absorbed_identical

rule evidence: ["flip-flop count, register names and clocked targets unchanged", "but the text differs widely (ratio 0.8565) -> review for (d)"]

```diff
--- D
+++ C
@@ -6,118 +6,56 @@
     output wire Co
 );
- 
-    wire Co_temp;
- 
-    add8 add8_inst1 (
-        .a(a[15:8]),
-        .b(b[15:8]),
-        .Cin(Co_temp), 
-        .y(y[15:8]),
-        .Co(Co)
-    );
- 
-    add8 add8_inst2 (
-        .a(a[7:0]),
-        .b(b[7:0]),
-        .Cin(Cin),
-        .y(y[7:0]),
-        .Co(Co_temp)
-    ); 
- 
+    wire [15:0] p;
+    wire [15:0] g;
+    wire [16:0] c;
+    wire P0, P1, P2, P3;
+    wire G0, G1, G2, G3;
+
+    assign p = a ^ b;
+    assign g = a & b;
+    assign c[0] = Cin;
+
+    assign P0 = p[3] & p[2] & p[1] & p[0];
+    assign G0 = g[3] |
+                (p[3] & g[2]) |
+                (p[3] & p[2] & g[1]) |
+                (p[3] & p[2] & p[1] & g[0]);
+    assign P1 = p[7] & p[6] & p[5] & p[4];
+    assign G1 = g[7] |
+                (p[7] & g[6]) |
+                (p[7] & p[6] & g[5]) |
+                (p[7] & p[6] & p[5] & g[4]);
+    assign P2 = p[11] & p[10] & p[9] & p[8];
+    assign G2 = g[11] |
+                (p[11] & g[10]) |
+                (p[11] & p[10] & g[9]) |
+                (p[11] & p[10] & p[9] & g[8]);
+    assign P3 = p[15] & p[14] & p[13] & p[12];
+    assign G3 = g[15] |
+                (p[15] & g[14]) |
+                (p[15] & p[14] & g[13]) |
+                (p[15] & p[14] & p[13] & g[12]);
+
+    assign c[1] = g[0] | (p[0] & c[0]);
+    assign c[2] = g[1] | (p[1] & g[0]) | (p[1] & p[0] & c[0]);
+    assign c[3] = g[2] | (p[2] & g[1]) | (p[2] & p[1] & g[0]) | (p[2] & p[1] & p[0] & c[0]);
+    assign c[4] = G0 | (P0 & c[0]);
+
+    assign c[5] = g[4] | (p[4] & c[4]);
+    assign c[6] = g[5] | (p[5] & g[4]) | (p[5] & p[4] & c[4]);
+    assign c[7] = g[6] | (p[6] & g[5]) | (p[6] & p[5] & g[4]) | (p[6] & p[5] & p[4] & c[4]);
+    assign c[8] = G1 | (P1 & c[4]);
+
+    assign c[9] = g[8] | (p[8] & c[8]);
+    assign c[10] = g[9] | (p[9] & g[8]) | (p[9] & p[8] & c[8]);
+    assign c[11] = g[10] | (p[10] & g[9]) | (p[10] & p[9] & g[8]) | (p[10] & p[9] & p[8] & c[8]);
+    assign c[12] = G2 | (P2 & c[8]);
+
+    assign c[13] = g[12] | (p[12] & c[12]);
+    assign c[14] = g[13] | (p[13] & g[12]) | (p[13] & p[12] & c[12]);
+    assign c[15] = g[14] | (p[14] & g[13]) | (p[14] & p[13] & g[12]) | (p[14] & p[13] & p[12] & c[12]);
+    assign c[16] = G3 | (P3 & c[12]);
+
+    assign y = p ^ c[15:0];
+    assign Co = c[16];
 endmodule
-
-module add8 (
-    input wire [7:0] a,
-    input wire [7:0] b,
-    input wire Cin,
-    output wire [7:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add4 add4_inst1 (
-        .a(a[7:4]),
-        .b(b[7:4]),
-        .Cin(Co_temp),
-        .y(y[7:4]),
-        .Co(Co)
-    );
- 
-    add4 add4_inst2 (
-        .a(a[3:0]),
-        .b(b[3:0]),
-        .Cin(Cin),
-        .y(y[3:0]),
-        .Co(Co_temp)
-    );
- 
-endmodule
-
-module add4 (
-    input wire [3:0] a,
-    input wire [3:0] b,
-    input wire Cin,
-    output wire [3:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add2 add2_inst1 (
-        .a(a[3:2]),
-        .b(b[3:2]),
-        .Cin(Co_temp),
-        .y(y[3:2]),
-        .Co(Co)
-    );
- 
-    add2 add2_inst2 (
-        .a(a[1:0]),
-        .b(b[1:0]),
-        .Cin(Cin),
-        .y(y[1:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
-
-module add2 (
-    input wire [1:0] a,
-    input wire [1:0] b,
-    input wire Cin,
-    output wire [1:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
-
-    add1 add1_inst1 (
-        .a(a[1]),
-        .b(b[1]),
-        .Cin(Co_temp),
-        .y(y[1]),
-        .Co(Co)
-    );
- 
-    add1 add1_inst2 (
-        .a(a[0]),
-        .b(b[0]),
-        .Cin(Cin),
-        .y(y[0]),
-        .Co(Co_temp)
-    );
-         
-endmodule
-
-module add1 (
-    input wire a,
-    input wire b,
-    input wire Cin,
-    output wire y,
-    output wire Co
-);
-    assign y = ((~a) & (~b) & Cin | (~a) & b & (~Cin) | a & (~b) & (~Cin) | (a & b & Cin));
-    assign Co = ((~a & b & Cin) | (a & ~b & Cin) | (a & b & ~Cin) | (a & b & Cin));
-
-endmodule
```

## 46. c851c1a2fb5d063 — rtllm_multi_pipe_8bit — gpt-5.6-terra — requested b -> rule a — label harmful

rule evidence: ["flip-flop count, register names and clocked targets unchanged", "but the text differs widely (ratio 0.5036) -> review for (d)"]

```diff
--- D
+++ C
@@ -2,91 +2,94 @@
     parameter size = 8
 )(
-          clk,      
-          rst_n,       
-          mul_a,       
-          mul_b, 
+          clk,
+          rst_n,
+          mul_a,
+          mul_b,
           mul_en_in,
- 
-          mul_en_out,      
-          mul_out    
+          mul_en_out,
+          mul_out
 );
- 
-   input clk;           
-   input rst_n; 
-   input mul_en_in;      
-   input [size-1:0] mul_a;       
-   input [size-1:0] mul_b;       
- 
-   output reg mul_en_out;  
-   output reg [size*2-1:0] mul_out;    
- 
-            
+
+   input clk;
+   input rst_n;
+   input mul_en_in;
+   input [size-1:0] mul_a;
+   input [size-1:0] mul_b;
+
+   output reg mul_en_out;
+   output reg [size*2-1:0] mul_out;
+
    reg [2:0] mul_en_out_reg;
- always@(posedge clk or negedge rst_n)
-       if(!rst_n)begin
-            mul_en_out_reg <= 'd0;             
-            mul_en_out     <= 'd0;                           
-       end
-       else begin
-            mul_en_out_reg <= {mul_en_out_reg[1:0],mul_en_in};            
-            mul_en_out     <= mul_en_out_reg[2];                  
-       end
- 
- 
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
-  always @(posedge clk or negedge rst_n)
-         if(!rst_n) begin
-              mul_a_reg <= 'd0;
-              mul_a_reg <= 'd0;
-         end
-         else begin
-              mul_a_reg <= mul_en_in ? mul_a :'d0;
-              mul_b_reg <= mul_en_in ? mul_b :'d0;
-         end
- 
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
-       else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
-       end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
- 
- 
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out <= 'd0;
-       else if(mul_en_out_reg[2])
-          mul_out <= mul_out_reg;
-       else
-          mul_out <= 'd0;
- 
-          
+   reg [7:0] mul_a_reg;
+   reg [7:0] mul_b_reg;
+   reg [15:0] sum [0:3];
+   reg [15:0] mul_out_reg;
+
+   wire [9:0] pair0;
+   wire [9:0] pair1;
+   wire [9:0] pair2;
+   wire [9:0] pair3;
+   wire [11:0] sum_lo;
+   wire [15:0] sum_hi;
+
+   assign pair0 = (mul_b_reg[0] ? {2'b00, mul_a_reg} : 10'b0) +
+                  (mul_b_reg[1] ? {1'b0, mul_a_reg, 1'b0} : 10'b0);
+   assign pair1 = (mul_b_reg[2] ? {2'b00, mul_a_reg} : 10'b0) +
+                  (mul_b_reg[3] ? {1'b0, mul_a_reg, 1'b0} : 10'b0);
+   assign pair2 = (mul_b_reg[4] ? {2'b00, mul_a_reg} : 10'b0) +
+                  (mul_b_reg[5] ? {1'b0, mul_a_reg, 1'b0} : 10'b0);
+   assign pair3 = (mul_b_reg[6] ? {2'b00, mul_a_reg} : 10'b0) +
+                  (mul_b_reg[7] ? {1'b0, mul_a_reg, 1'b0} : 10'b0);
+
+   assign sum_lo = {2'b00, sum[0][9:0]} + sum[1][11:0];
+   assign sum_hi = {2'b00, sum[2][13:0]} + sum[3];
+
+   always @(posedge clk or negedge rst_n)
+     if (!rst_n) begin
+       mul_en_out_reg <= 3'b000;
+       mul_en_out     <= 1'b0;
+     end
+     else begin
+       mul_en_out_reg <= {mul_en_out_reg[1:0], mul_en_in};
+       mul_en_out     <= mul_en_out_reg[2];
+     end
+
+   always @(posedge clk or negedge rst_n)
+     if (!rst_n) begin
+       mul_a_reg <= 8'b0;
+       mul_a_reg <= 8'b0;
+     end
+     else begin
+       mul_a_reg <= mul_en_in ? mul_a : 8'b0;
+       mul_b_reg <= mul_en_in ? mul_b : 8'b0;
+     end
+
+   always @(posedge clk or negedge rst_n)
+     if (!rst_n) begin
+       sum[0] <= 16'b0;
+       sum[1] <= 16'b0;
+       sum[2] <= 16'b0;
+       sum[3] <= 16'b0;
+     end
+     else begin
+       sum[0] <= {6'b0, pair0};
+       sum[1] <= {4'b0, pair1, 2'b0};
+       sum[2] <= {2'b0, pair2, 4'b0};
+       sum[3] <= {pair3, 6'b0};
+     end
+
+   always @(posedge clk or negedge rst_n)
+     if (!rst_n)
+       mul_out_reg <= 16'b0;
+     else
+       mul_out_reg <= {4'b0, sum_lo} + sum_hi;
+
+   always @(posedge clk or negedge rst_n)
+     if (!rst_n)
+       mul_out <= 0;
+     else if (mul_en_out_reg[2])
+       mul_out <= mul_out_reg;
+     else
+       mul_out <= 0;
+
 endmodule
```

## 47. c646470e93cedee — rtllm_LIFObuffer — gpt-5.6-luna — requested b -> rule a — label nonequiv

rule evidence: ["flip-flop count, register names and clocked targets unchanged"]

```diff
--- D
+++ C
@@ -15,35 +15,80 @@
 
     always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
-        end else begin
-            if (Rst == 1) begin
+        if (EN == 1'b1) begin
+            if (Rst == 1'b1) begin
                 SP = 3'd4;
-                EMPTY = SP[2];
+                EMPTY = 1'b1;
                 dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
-                end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
+                for (i = 0; i < 4; i = i + 1)
+                    stack_mem[i] = 4'h0;
+            end else if (Rst == 1'b0) begin
                 dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
-            end else begin
-                // Do nothing if neither condition is met
+                case (SP)
+                    3'd0: begin
+                        FULL = 1'b1;
+                        EMPTY = 1'b0;
+                    end
+                    3'd1: begin
+                        if (RW == 1'b0) begin
+                            SP = 3'd0;
+                            stack_mem[0] = dataIn;
+                            FULL = 1'b1;
+                            EMPTY = 1'b0;
+                        end else if (RW == 1'b1) begin
+                            dataOut = stack_mem[1];
+                            stack_mem[1] = 4'h0;
+                            SP = 3'd2;
+                            FULL = 1'b0;
+                            EMPTY = 1'b0;
+                        end else begin
+                            FULL = 1'b0;
+                            EMPTY = 1'b0;
+                        end
+                    end
+                    3'd2: begin
+                        if (RW == 1'b0) begin
+                            SP = 3'd1;
+                            stack_mem[1] = dataIn;
+                        end else if (RW == 1'b1) begin
+                            dataOut = stack_mem[2];
+                            stack_mem[2] = 4'h0;
+                            SP = 3'd3;
+                        end
+                        FULL = 1'b0;
+                        EMPTY = 1'b0;
+                    end
+                    3'd3: begin
+                        if (RW == 1'b0) begin
+                            SP = 3'd2;
+                            stack_mem[2] = dataIn;
+                            FULL = 1'b0;
+                            EMPTY = 1'b0;
+                        end else if (RW == 1'b1) begin
+                            dataOut = stack_mem[3];
+                            stack_mem[3] = 4'h0;
+                            SP = 3'd4;
+                            FULL = 1'b0;
+                            EMPTY = 1'b1;
+                        end else begin
+                            FULL = 1'b0;
+                            EMPTY = 1'b0;
+                        end
+                    end
+                    3'd4: begin
+                        if (RW == 1'b0) begin
+                            SP = 3'd3;
+                            stack_mem[3] = dataIn;
+                            FULL = 1'b0;
+                            EMPTY = 1'b0;
+                        end else begin
+                            FULL = 1'b0;
+                            EMPTY = 1'b1;
+                        end
+                    end
+                    default: begin
+                        FULL = (SP == 3'd0);
+                        EMPTY = SP[2];
+                    end
+                endcase
             end
         end
```

## 48. ca01ded8c8586b4 — rtllm_adder_16bit — gpt-5.4-mini — requested free -> rule a — label absorbed_identical

rule evidence: ["flip-flop count, register names and clocked targets unchanged", "but the text differs widely (ratio 0.8413) -> review for (d)"]

```diff
--- D
+++ C
@@ -6,118 +6,48 @@
     output wire Co
 );
- 
-    wire Co_temp;
- 
-    add8 add8_inst1 (
-        .a(a[15:8]),
-        .b(b[15:8]),
-        .Cin(Co_temp), 
-        .y(y[15:8]),
-        .Co(Co)
-    );
- 
-    add8 add8_inst2 (
-        .a(a[7:0]),
-        .b(b[7:0]),
-        .Cin(Cin),
-        .y(y[7:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
 
-module add8 (
-    input wire [7:0] a,
-    input wire [7:0] b,
-    input wire Cin,
-    output wire [7:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add4 add4_inst1 (
-        .a(a[7:4]),
-        .b(b[7:4]),
-        .Cin(Co_temp),
-        .y(y[7:4]),
-        .Co(Co)
-    );
- 
-    add4 add4_inst2 (
-        .a(a[3:0]),
-        .b(b[3:0]),
-        .Cin(Cin),
-        .y(y[3:0]),
-        .Co(Co_temp)
-    );
- 
-endmodule
+    wire [15:0] p;
+    wire [15:0] g;
+    wire [16:0] c;
 
-module add4 (
-    input wire [3:0] a,
-    input wire [3:0] b,
-    input wire Cin,
-    output wire [3:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add2 add2_inst1 (
-        .a(a[3:2]),
-        .b(b[3:2]),
-        .Cin(Co_temp),
-        .y(y[3:2]),
-        .Co(Co)
-    );
- 
-    add2 add2_inst2 (
-        .a(a[1:0]),
-        .b(b[1:0]),
-        .Cin(Cin),
-        .y(y[1:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
+    wire P0, P1, P2, P3;
+    wire G0, G1, G2, G3;
 
-module add2 (
-    input wire [1:0] a,
-    input wire [1:0] b,
-    input wire Cin,
-    output wire [1:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
+    assign p = a ^ b;
+    assign g = a & b;
+    assign c[0] = Cin;
 
-    add1 add1_inst1 (
-        .a(a[1]),
-        .b(b[1]),
-        .Cin(Co_temp),
-        .y(y[1]),
-        .Co(Co)
-    );
- 
-    add1 add1_inst2 (
-        .a(a[0]),
-        .b(b[0]),
-        .Cin(Cin),
-        .y(y[0]),
-        .Co(Co_temp)
-    );
-         
-endmodule
+    assign c[1]  = g[0]  | (p[0]  & c[0]);
+    assign c[2]  = g[1]  | (p[1]  & g[0])  | (p[1]  & p[0]  & c[0]);
+    assign c[3]  = g[2]  | (p[2]  & g[1])  | (p[2]  & p[1]  & g[0])  | (p[2]  & p[1]  & p[0]  & c[0]);
+    assign c[4]  = G0 | (P0 & c[0]);
 
-module add1 (
-    input wire a,
-    input wire b,
-    input wire Cin,
-    output wire y,
-    output wire Co
-);
-    assign y = ((~a) & (~b) & Cin | (~a) & b & (~Cin) | a & (~b) & (~Cin) | (a & b & Cin));
-    assign Co = ((~a & b & Cin) | (a & ~b & Cin) | (a & b & ~Cin) | (a & b & Cin));
+    assign c[5]  = g[4]  | (p[4]  & c[4]);
+    assign c[6]  = g[5]  | (p[5]  & g[4])  | (p[5]  & p[4]  & c[4]);
+    assign c[7]  = g[6]  | (p[6]  & g[5])  | (p[6]  & p[5]  & g[4])  | (p[6]  & p[5]  & p[4]  & c[4]);
+    assign c[8]  = G1 | (P1 & c[4]);
+
+    assign c[9]  = g[8]  | (p[8]  & c[8]);
+    assign c[10] = g[9]  | (p[9]  & g[8])  | (p[9]  & p[8]  & c[8]);
+    assign c[11] = g[10] | (p[10] & g[9])  | (p[10] & p[9]  & g[8])  | (p[10] & p[9]  & p[8]  & c[8]);
+    assign c[12] = G2 | (P2 & c[8]);
+
+    assign c[13] = g[12] | (p[12] & c[12]);
+    assign c[14] = g[13] | (p[13] & g[12]) | (p[13] & p[12] & c[12]);
+    assign c[15] = g[14] | (p[14] & g[13]) | (p[14] & p[13] & g[12]) | (p[14] & p[13] & p[12] & c[12]);
+    assign c[16] = G3 | (P3 & c[12]);
+
+    assign P0 = &p[3:0];
+    assign P1 = &p[7:4];
+    assign P2 = &p[11:8];
+    assign P3 = &p[15:12];
+
+    assign G0 = g[3]  | (p[3]  & g[2])  | (p[3]  & p[2]  & g[1])  | (p[3]  & p[2]  & p[1]  & g[0]);
+    assign G1 = g[7]  | (p[7]  & g[6])  | (p[7]  & p[6]  & g[5])  | (p[7]  & p[6]  & p[5]  & g[4]);
+    assign G2 = g[11] | (p[11] & g[10]) | (p[11] & p[10] & g[9]) | (p[11] & p[10] & p[9] & g[8]);
+    assign G3 = g[15] | (p[15] & g[14]) | (p[15] & p[14] & g[13]) | (p[15] & p[14] & p[13] & g[12]);
+
+    assign y = p ^ c[15:0];
+    assign Co = c[16];
 
 endmodule
```

## 49. ceaa3868ed144bd — rtllm_multi_pipe_8bit — gpt-5.6-luna — requested free -> rule a — label tradeoff

rule evidence: ["flip-flop count, register names and clocked targets unchanged"]

```diff
--- D
+++ C
@@ -2,91 +2,98 @@
     parameter size = 8
 )(
-          clk,      
-          rst_n,       
-          mul_a,       
-          mul_b, 
-          mul_en_in,
- 
-          mul_en_out,      
-          mul_out    
+    clk,
+    rst_n,
+    mul_a,
+    mul_b,
+    mul_en_in,
+    mul_en_out,
+    mul_out
 );
- 
-   input clk;           
-   input rst_n; 
-   input mul_en_in;      
-   input [size-1:0] mul_a;       
-   input [size-1:0] mul_b;       
- 
-   output reg mul_en_out;  
-   output reg [size*2-1:0] mul_out;    
- 
-            
+
+   input clk;
+   input rst_n;
+   input mul_en_in;
+   input [size-1:0] mul_a;
+   input [size-1:0] mul_b;
+
+   output reg mul_en_out;
+   output reg [size*2-1:0] mul_out;
+
    reg [2:0] mul_en_out_reg;
- always@(posedge clk or negedge rst_n)
-       if(!rst_n)begin
-            mul_en_out_reg <= 'd0;             
-            mul_en_out     <= 'd0;                           
-       end
-       else begin
-            mul_en_out_reg <= {mul_en_out_reg[1:0],mul_en_in};            
-            mul_en_out     <= mul_en_out_reg[2];                  
-       end
- 
- 
-    reg [7:0] mul_a_reg;
-    reg [7:0] mul_b_reg;
-  always @(posedge clk or negedge rst_n)
-         if(!rst_n) begin
-              mul_a_reg <= 'd0;
-              mul_a_reg <= 'd0;
-         end
-         else begin
-              mul_a_reg <= mul_en_in ? mul_a :'d0;
-              mul_b_reg <= mul_en_in ? mul_b :'d0;
-         end
- 
-  
-     wire [15:0] temp [size-1:0];
-  assign temp[0] = mul_b_reg[0]? {8'b0,mul_a_reg} : 'd0;
-  assign temp[1] = mul_b_reg[1]? {7'b0,mul_a_reg,1'b0} : 'd0;
-  assign temp[2] = mul_b_reg[2]? {6'b0,mul_a_reg,2'b0} : 'd0;
-  assign temp[3] = mul_b_reg[3]? {5'b0,mul_a_reg,3'b0} : 'd0;
-  assign temp[4] = mul_b_reg[4]? {4'b0,mul_a_reg,4'b0} : 'd0;
-  assign temp[5] = mul_b_reg[5]? {3'b0,mul_a_reg,5'b0} : 'd0;
-  assign temp[6] = mul_b_reg[6]? {2'b0,mul_a_reg,6'b0} : 'd0;
-  assign temp[7] = mul_b_reg[7]? {1'b0,mul_a_reg,7'b0} : 'd0; 
- 
- 
-     reg [15:0] sum [3:0];//[size/2-1:1]
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n) begin
-          sum[0]  <= 'd0;
-          sum[1]  <= 'd0;
-          sum[2]  <= 'd0;
-          sum[3]  <= 'd0;
-       end 
-       else begin
-          sum[0] <= temp[0] + temp[1];
-          sum[1] <= temp[2] + temp[3];
-          sum[2] <= temp[4] + temp[5];
-          sum[3] <= temp[6] + temp[7];
-       end
- 
-     reg [15:0] mul_out_reg;
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out_reg <= 'd0;
-       else 
-          mul_out_reg <= sum[0] + sum[1] + sum[2] + sum[3];
- 
- 
- always @(posedge clk or negedge rst_n) 
-       if(!rst_n)
-          mul_out <= 'd0;
-       else if(mul_en_out_reg[2])
-          mul_out <= mul_out_reg;
-       else
-          mul_out <= 'd0;
- 
-          
+   reg [7:0] mul_a_reg;
+   reg [7:0] mul_b_reg;
+   reg [15:0] sum [3:0];
+   reg [15:0] mul_out_reg;
+
+   wire [15:0] a_ext = {8'b0, mul_a_reg};
+   wire [15:0] p0;
+   wire [15:0] p1;
+   wire [15:0] p2;
+   wire [15:0] p3;
+
+   assign p0 = mul_b_reg[1:0] == 2'b00 ? 16'b0 :
+               mul_b_reg[1:0] == 2'b01 ? a_ext :
+               mul_b_reg[1:0] == 2'b10 ? (a_ext << 1) :
+                                         (a_ext + (a_ext << 1));
+   assign p1 = mul_b_reg[3:2] == 2'b00 ? 16'b0 :
+               mul_b_reg[3:2] == 2'b01 ? (a_ext << 2) :
+               mul_b_reg[3:2] == 2'b10 ? (a_ext << 3) :
+                                         ((a_ext << 2) + (a_ext << 3));
+   assign p2 = mul_b_reg[5:4] == 2'b00 ? 16'b0 :
+               mul_b_reg[5:4] == 2'b01 ? (a_ext << 4) :
+               mul_b_reg[5:4] == 2'b10 ? (a_ext << 5) :
+                                         ((a_ext << 4) + (a_ext << 5));
+   assign p3 = mul_b_reg[7:6] == 2'b00 ? 16'b0 :
+               mul_b_reg[7:6] == 2'b01 ? (a_ext << 6) :
+               mul_b_reg[7:6] == 2'b10 ? (a_ext << 7) :
+                                         ((a_ext << 6) + (a_ext << 7));
+
+   always @(posedge clk or negedge rst_n)
+      if (!rst_n) begin
+         mul_en_out_reg <= 3'b0;
+         mul_en_out <= 1'b0;
+      end
+      else begin
+         mul_en_out_reg <= {mul_en_out_reg[1:0], mul_en_in};
+         mul_en_out <= mul_en_out_reg[2];
+      end
+
+   always @(posedge clk or negedge rst_n)
+      if (!rst_n) begin
+         mul_a_reg <= 8'b0;
+         mul_a_reg <= 8'b0;
+      end
+      else begin
+         mul_a_reg <= mul_en_in ? mul_a : 8'b0;
+         mul_b_reg <= mul_en_in ? mul_b : 8'b0;
+      end
+
+   always @(posedge clk or negedge rst_n)
+      if (!rst_n) begin
+         sum[0] <= 16'b0;
+         sum[1] <= 16'b0;
+         sum[2] <= 16'b0;
+         sum[3] <= 16'b0;
+      end
+      else begin
+         sum[0] <= p0;
+         sum[1] <= p1;
+         sum[2] <= p2;
+         sum[3] <= p3;
+      end
+
+   always @(posedge clk or negedge rst_n)
+      if (!rst_n)
+         mul_out_reg <= 16'b0;
+      else
+         mul_out_reg <= (sum[0] + sum[1]) + (sum[2] + sum[3]);
+
+   always @(posedge clk or negedge rst_n)
+      if (!rst_n)
+         mul_out <= 'd0;
+      else if (mul_en_out_reg[2])
+         mul_out <= mul_out_reg;
+      else
+         mul_out <= 'd0;
+
 endmodule
```

## 50. c81240b24a7ba28 — rtllm_adder_16bit — gpt-5.4 — requested d -> rule a — label absorbed_identical

rule evidence: ["flip-flop count, register names and clocked targets unchanged", "but the text differs widely (ratio 0.9041) -> review for (d)"]

```diff
--- D
+++ C
@@ -6,118 +6,100 @@
     output wire Co
 );
- 
-    wire Co_temp;
- 
-    add8 add8_inst1 (
-        .a(a[15:8]),
-        .b(b[15:8]),
-        .Cin(Co_temp), 
-        .y(y[15:8]),
-        .Co(Co)
-    );
- 
-    add8 add8_inst2 (
-        .a(a[7:0]),
-        .b(b[7:0]),
-        .Cin(Cin),
-        .y(y[7:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
 
-module add8 (
-    input wire [7:0] a,
-    input wire [7:0] b,
-    input wire Cin,
-    output wire [7:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add4 add4_inst1 (
-        .a(a[7:4]),
-        .b(b[7:4]),
-        .Cin(Co_temp),
-        .y(y[7:4]),
-        .Co(Co)
-    );
- 
-    add4 add4_inst2 (
-        .a(a[3:0]),
-        .b(b[3:0]),
-        .Cin(Cin),
-        .y(y[3:0]),
-        .Co(Co_temp)
-    );
- 
-endmodule
+    wire [15:0] p;
+    wire [15:0] g;
 
-module add4 (
-    input wire [3:0] a,
-    input wire [3:0] b,
-    input wire Cin,
-    output wire [3:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
- 
-    add2 add2_inst1 (
-        .a(a[3:2]),
-        .b(b[3:2]),
-        .Cin(Co_temp),
-        .y(y[3:2]),
-        .Co(Co)
-    );
- 
-    add2 add2_inst2 (
-        .a(a[1:0]),
-        .b(b[1:0]),
-        .Cin(Cin),
-        .y(y[1:0]),
-        .Co(Co_temp)
-    ); 
- 
-endmodule
+    wire g10_0, p10_0, g210_0, p210_0, G0, P0;
+    wire g54_1, p54_1, g654_1, p654_1, G1, P1;
+    wire g98_2, p98_2, g1098_2, p1098_2, G2, P2;
+    wire g1312_3, p1312_3, g141312_3, p141312_3, G3, P3;
 
-module add2 (
-    input wire [1:0] a,
-    input wire [1:0] b,
-    input wire Cin,
-    output wire [1:0] y,
-    output wire Co
-);
- 
-    wire Co_temp;
+    wire BG01, BP01;
+    wire BG012, BP012;
+    wire BG0123, BP0123;
 
-    add1 add1_inst1 (
-        .a(a[1]),
-        .b(b[1]),
-        .Cin(Co_temp),
-        .y(y[1]),
-        .Co(Co)
-    );
- 
-    add1 add1_inst2 (
-        .a(a[0]),
-        .b(b[0]),
-        .Cin(Cin),
-        .y(y[0]),
-        .Co(Co_temp)
-    );
-         
-endmodule
+    wire C4, C8, C12;
+    wire c1, c2, c3;
+    wire c5, c6, c7;
+    wire c9, c10, c11;
+    wire c13, c14, c15;
 
-module add1 (
-    input wire a,
-    input wire b,
-    input wire Cin,
-    output wire y,
-    output wire Co
-);
-    assign y = ((~a) & (~b) & Cin | (~a) & b & (~Cin) | a & (~b) & (~Cin) | (a & b & Cin));
-    assign Co = ((~a & b & Cin) | (a & ~b & Cin) | (a & b & ~Cin) | (a & b & Cin));
+    assign p = a ^ b;
+    assign g = a & b;
+
+    assign g10_0  = g[1]  | (p[1]  & g[0]);
+    assign p10_0  = p[1]  & p[0];
+    assign g210_0 = g[2]  | (p[2]  & g10_0);
+    assign p210_0 = p[2]  & p10_0;
+    assign G0     = g[3]  | (p[3]  & g210_0);
+    assign P0     = p[3]  & p210_0;
+
+    assign g54_1  = g[5]  | (p[5]  & g[4]);
+    assign p54_1  = p[5]  & p[4];
+    assign g654_1 = g[6]  | (p[6]  & g54_1);
+    assign p654_1 = p[6]  & p54_1;
+    assign G1     = g[7]  | (p[7]  & g654_1);
+    assign P1     = p[7]  & p654_1;
+
+    assign g98_2   = g[9]  | (p[9]  & g[8]);
+    assign p98_2   = p[9]  & p[8];
+    assign g1098_2 = g[10] | (p[10] & g98_2);
+    assign p1098_2 = p[10] & p98_2;
+    assign G2      = g[11] | (p[11] & g1098_2);
+    assign P2      = p[11] & p1098_2;
+
+    assign g1312_3   = g[13] | (p[13] & g[12]);
+    assign p1312_3   = p[13] & p[12];
+    assign g141312_3 = g[14] | (p[14] & g1312_3);
+    assign p141312_3 = p[14] & p1312_3;
+    assign G3        = g[15] | (p[15] & g141312_3);
+    assign P3        = p[15] & p141312_3;
+
+    assign C4 = G0 | (P0 & Cin);
+
+    assign BG01 = G1 | (P1 & G0);
+    assign BP01 = P1 & P0;
+    assign C8   = BG01 | (BP01 & Cin);
+
+    assign BG012 = G2 | (P2 & BG01);
+    assign BP012 = P2 & BP01;
+    assign C12   = BG012 | (BP012 & Cin);
+
+    assign BG0123 = G3 | (P3 & BG012);
+    assign BP0123 = P3 & BP012;
+    assign Co     = BG0123 | (BP0123 & Cin);
+
+    assign c1 = g[0] | (p[0] & Cin);
+    assign c2 = g10_0 | (p10_0 & Cin);
+    assign c3 = g210_0 | (p210_0 & Cin);
+
+    assign c5 = g[4] | (p[4] & C4);
+    assign c6 = g54_1 | (p54_1 & C4);
+    assign c7 = g654_1 | (p654_1 & C4);
+
+    assign c9  = g[8]  | (p[8]  & C8);
+    assign c10 = g98_2 | (p98_2 & C8);
+    assign c11 = g1098_2 | (p1098_2 & C8);
+
+    assign c13 = g[12] | (p[12] & C12);
+    assign c14 = g1312_3 | (p1312_3 & C12);
+    assign c15 = g141312_3 | (p141312_3 & C12);
+
+    assign y[0]  = p[0]  ^ Cin;
+    assign y[1]  = p[1]  ^ c1;
+    assign y[2]  = p[2]  ^ c2;
+    assign y[3]  = p[3]  ^ c3;
+    assign y[4]  = p[4]  ^ C4;
+    assign y[5]  = p[5]  ^ c5;
+    assign y[6]  = p[6]  ^ c6;
+    assign y[7]  = p[7]  ^ c7;
+    assign y[8]  = p[8]  ^ C8;
+    assign y[9]  = p[9]  ^ c9;
+    assign y[10] = p[10] ^ c10;
+    assign y[11] = p[11] ^ c11;
+    assign y[12] = p[12] ^ C12;
+    assign y[13] = p[13] ^ c13;
+    assign y[14] = p[14] ^ c14;
+    assign y[15] = p[15] ^ c15;
 
 endmodule
```

## 51. c5a2824a0f46eea — rtllm_LIFObuffer — gpt-5.4-mini — requested d -> rule b — label nonequiv

rule evidence: ["register names or clocked targets changed, flip-flop count and latency unchanged"]

```diff
--- D
+++ C
@@ -11,39 +11,50 @@
 
     reg [3:0] stack_mem[0:3];
-    reg [2:0] SP;
+    reg [2:0] used;
     integer i;
 
     always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
+        if (EN == 1'b0) begin
+            // Hold state when disabled
+        end else if (Rst == 1'b1) begin
+            used = 3'd0;
+            EMPTY = 1'b1;
+            dataOut = 4'h0;
+            for (i = 0; i < 4; i = i + 1) begin
+                stack_mem[i] = 4'h0;
+            end
         end else begin
-            if (Rst == 1) begin
-                SP = 3'd4;
-                EMPTY = SP[2];
-                dataOut = 4'h0;
-                for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
-                end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
-                dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
-                    dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
-                end
+            dataOut = 4'hx;
+            FULL = (used == 3'd4);
+            EMPTY = (used == 3'd0);
+
+            if ((FULL == 1'b0) && (RW == 1'b0)) begin
+                case (used)
+                    3'd0: stack_mem[3] = dataIn;
+                    3'd1: stack_mem[2] = dataIn;
+                    3'd2: stack_mem[1] = dataIn;
+                    default: stack_mem[0] = dataIn;
+                endcase
+                used = used + 3'd1;
+                FULL = (used == 3'd4);
+                EMPTY = (used == 3'd0);
+            end else if ((EMPTY == 1'b0) && (RW == 1'b1)) begin
+                case (used)
+                    3'd1: dataOut = stack_mem[3];
+                    3'd2: dataOut = stack_mem[2];
+                    3'd3: dataOut = stack_mem[1];
+                    default: dataOut = stack_mem[0];
+                endcase
+                case (used)
+                    3'd1: stack_mem[3] = 4'h0;
+                    3'd2: stack_mem[2] = 4'h0;
+                    3'd3: stack_mem[1] = 4'h0;
+                    default: stack_mem[0] = 4'h0;
+                endcase
+                used = used - 3'd1;
+                FULL = (used == 3'd4);
+                EMPTY = (used == 3'd0);
             end else begin
-                // Do nothing if neither condition is met
+                // No stack movement
             end
         end
```

## 52. c52053fb93a511c — rtllm_serial2parallel — gpt-5.4-mini — requested free -> rule b — label nonequiv

rule evidence: ["register names or clocked targets changed, flip-flop count and latency unchanged"]

```diff
--- D
+++ C
@@ -1,3 +1,2 @@
-
 module serial2parallel(
 	input clk,
@@ -9,37 +8,41 @@
 );
 
-	reg[7:0]din_tmp;
-	reg[3:0]cnt;
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			cnt <= 0;
-		else if(din_valid)
-			cnt <= (cnt == 4'd8)?0:cnt+1'b1;
-		else	
-			cnt <= 0;
+	reg [7:0] mem;
+	reg [2:0] wptr;
+	reg full;
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			mem <= 8'b0;
+			wptr <= 3'd7;
+			full <= 1'b0;
+		end else if (!din_valid) begin
+			wptr <= 3'd7;
+			full <= 1'b0;
+		end else if (full) begin
+			wptr <= 3'd7;
+			full <= 1'b0;
+		end else begin
+			mem[wptr] <= din_serial;
+			if (wptr == 3'd0) begin
+				wptr <= 3'd7;
+				full <= 1'b1;
+			end else begin
+				wptr <= wptr - 3'd1;
+			end
+		end
 	end
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			din_tmp <= 8'b0;
-		else if(din_valid && cnt <= 4'd7)
-			din_tmp <= {din_tmp[6:0],din_serial};
-	
-	end 
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)begin
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			dout_parallel <= 8'b0;
 			dout_valid <= 1'b0;
-			dout_parallel <= 8'b0;
-		end
-		else if(cnt == 4'd8)begin
+		end else if (din_valid && full) begin
+			dout_parallel <= mem;
 			dout_valid <= 1'b1;
-			dout_parallel <= din_tmp;
-		end
-		else begin
+		end else begin
 			dout_valid <= 1'b0;
 		end
-	end 
-	
+	end
+
 endmodule
```

## 53. c11a57fa5034091 — rtllm_serial2parallel — gpt-5.6-terra — requested d -> rule b — label retained

rule evidence: ["register names or clocked targets changed, flip-flop count and latency unchanged"]

```diff
--- D
+++ C
@@ -1,3 +1,2 @@
-
 module serial2parallel(
 	input clk,
@@ -9,30 +8,46 @@
 );
 
-	reg[7:0]din_tmp;
-	reg[3:0]cnt;
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			cnt <= 0;
-		else if(din_valid)
-			cnt <= (cnt == 4'd8)?0:cnt+1'b1;
-		else	
-			cnt <= 0;
+	reg [7:0] din_tmp;
+	reg [2:0] slots_left;
+	reg frame_ready;
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			slots_left <= 3'b111;
+			frame_ready <= 1'b0;
+		end
+		else if (frame_ready) begin
+			slots_left <= 3'b111;
+			frame_ready <= 1'b0;
+		end
+		else if (!din_valid) begin
+			slots_left <= 3'b111;
+			frame_ready <= 1'b0;
+		end
+		else if (~|slots_left) begin
+			slots_left <= 3'b111;
+			frame_ready <= 1'b1;
+		end
+		else begin
+			slots_left[0] <= ~slots_left[0];
+			slots_left[1] <= slots_left[1] ^ ~slots_left[0];
+			slots_left[2] <= slots_left[2] ^ (~slots_left[1] & ~slots_left[0]);
+			frame_ready <= 1'b0;
+		end
 	end
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n)
 			din_tmp <= 8'b0;
-		else if(din_valid && cnt <= 4'd7)
-			din_tmp <= {din_tmp[6:0],din_serial};
-	
-	end 
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)begin
+		else if (din_valid && !frame_ready)
+			din_tmp <= {din_tmp[6:0], din_serial};
+	end
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
 			dout_valid <= 1'b0;
 			dout_parallel <= 8'b0;
 		end
-		else if(cnt == 4'd8)begin
+		else if (frame_ready) begin
 			dout_valid <= 1'b1;
 			dout_parallel <= din_tmp;
@@ -41,5 +56,5 @@
 			dout_valid <= 1'b0;
 		end
-	end 
-	
+	end
+
 endmodule
```

## 54. cd02403ad78299c — rtllm_LIFObuffer — gpt-5.6-terra — requested b -> rule b — label nonequiv

rule evidence: ["register names or clocked targets changed, flip-flop count and latency unchanged"]

```diff
--- D
+++ C
@@ -12,38 +12,56 @@
     reg [3:0] stack_mem[0:3];
     reg [2:0] SP;
+    reg [2:0] sp_next;
+    reg do_write;
+    reg do_read;
     integer i;
 
-    always @ (posedge Clk) begin
-        if (EN == 0) begin
-            // Do nothing if EN is 0
+    always @* begin
+        sp_next = SP;
+        do_write = 1'b0;
+        do_read = 1'b0;
+
+        if (RW == 1'b0) begin
+            case (SP)
+                3'd4: begin sp_next = 3'd3; do_write = 1'b1; end
+                3'd3: begin sp_next = 3'd2; do_write = 1'b1; end
+                3'd2: begin sp_next = 3'd1; do_write = 1'b1; end
+                3'd1: begin sp_next = 3'd0; do_write = 1'b1; end
+                default: begin end
+            endcase
+        end else if (RW == 1'b1) begin
+            case (SP)
+                3'd0: begin sp_next = 3'd1; do_read = 1'b1; end
+                3'd1: begin sp_next = 3'd2; do_read = 1'b1; end
+                3'd2: begin sp_next = 3'd3; do_read = 1'b1; end
+                3'd3: begin sp_next = 3'd4; do_read = 1'b1; end
+                default: begin end
+            endcase
+        end
+    end
+
+    always @(posedge Clk) begin
+        if (EN == 1'b0) begin
         end else begin
-            if (Rst == 1) begin
+            if (Rst == 1'b1) begin
                 SP = 3'd4;
-                EMPTY = SP[2];
+                EMPTY = 1'b1;
                 dataOut = 4'h0;
                 for (i = 0; i < 4; i = i + 1) begin
-                    stack_mem[i] = 0;
+                    stack_mem[i] = 4'h0;
                 end
-            end else if (Rst == 0) begin
-                FULL = SP ? 0 : 1;
-                EMPTY = SP[2];
+            end else if (Rst == 1'b0) begin
+                SP = sp_next;
+                FULL = (sp_next == 3'd0);
+                EMPTY = sp_next[2];
                 dataOut = 4'hx;
-                
-                if (FULL == 1'b0 && RW == 1'b0) begin
-                    SP = SP - 1'b1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                    stack_mem[SP] = dataIn;
-                end else if (EMPTY == 1'b0 && RW == 1'b1) begin
+
+                if (do_write == 1'b1) begin
+                    stack_mem[sp_next] = dataIn;
+                end else if (do_read == 1'b1) begin
                     dataOut = stack_mem[SP];
-                    stack_mem[SP] = 0;
-                    SP = SP + 1;
-                    FULL = SP ? 0 : 1;
-                    EMPTY = SP[2];
-                end else begin
-                    // Do nothing if neither condition is met
+                    stack_mem[SP] = 4'h0;
                 end
             end else begin
-                // Do nothing if neither condition is met
             end
         end
```

## 55. cce230deea8352e — rtllm_serial2parallel — gpt-5.6-luna — requested d -> rule b — label nonequiv

rule evidence: ["register names or clocked targets changed, flip-flop count and latency unchanged"]

```diff
--- D
+++ C
@@ -1,3 +1,2 @@
-
 module serial2parallel(
 	input clk,
@@ -9,37 +8,40 @@
 );
 
-	reg[7:0]din_tmp;
-	reg[3:0]cnt;
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			cnt <= 0;
-		else if(din_valid)
-			cnt <= (cnt == 4'd8)?0:cnt+1'b1;
-		else	
-			cnt <= 0;
-	end
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			din_tmp <= 8'b0;
-		else if(din_valid && cnt <= 4'd7)
-			din_tmp <= {din_tmp[6:0],din_serial};
-	
-	end 
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)begin
-			dout_valid <= 1'b0;
+	reg [7:0] din_tmp;
+	reg [2:0] bit_count;
+	reg frame_ready;
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			din_tmp       <= 8'b0;
+			bit_count     <= 3'b0;
+			frame_ready   <= 1'b0;
 			dout_parallel <= 8'b0;
-		end
-		else if(cnt == 4'd8)begin
-			dout_valid <= 1'b1;
-			dout_parallel <= din_tmp;
+			dout_valid    <= 1'b0;
 		end
 		else begin
 			dout_valid <= 1'b0;
+
+			if (!din_valid) begin
+				bit_count   <= 3'b0;
+				frame_ready <= 1'b0;
+			end
+			else if (frame_ready) begin
+				dout_parallel <= din_tmp;
+				dout_valid    <= 1'b1;
+				bit_count     <= 3'b0;
+				frame_ready   <= 1'b0;
+			end
+			else begin
+				din_tmp <= {din_tmp[6:0], din_serial};
+				if (bit_count == 3'd7) begin
+					frame_ready <= 1'b1;
+				end
+				else begin
+					bit_count <= bit_count + 3'd1;
+				end
+			end
 		end
-	end 
-	
+	end
+
 endmodule
```

## 56. c2115e983a350db — rtllm_traffic_light — gpt-5.6-luna — requested b -> rule b — label tradeoff

rule evidence: ["register names or clocked targets changed, flip-flop count and latency unchanged"]

```diff
--- D
+++ C
@@ -3,99 +3,115 @@
 module traffic_light
     (
-		input rst_n, 
-      input clk, 
-      input pass_request,
-		  output wire[7:0]clock,
-      output reg red,
-		  output reg yellow,
-		  output reg green
+        input rst_n,
+        input clk,
+        input pass_request,
+        output wire [7:0] clock,
+        output reg red,
+        output reg yellow,
+        output reg green
     );
-	
-	parameter 	idle = 2'd0,
-				s1_red = 2'd1,
-				s2_yellow = 2'd2,
-				s3_green = 2'd3;
-	reg [7:0] cnt;
-	reg [1:0] state;
-	reg p_red,p_yellow,p_green;	
 
+    parameter idle      = 2'b00,
+              s1_red    = 2'b01,
+              s2_yellow = 2'b11,
+              s3_green  = 2'b10;
 
-always @(posedge clk or negedge rst_n) 
-    begin
-        if(!rst_n)
-        begin
-			state <= idle;
-			p_red <= 1'b0;
-			p_green <= 1'b0;
-			p_yellow <= 1'b0;			
+    reg [7:0] cnt;
+    reg [1:0] state;
+    reg p_red, p_yellow, p_green;
+    reg [1:0] state_next;
+    reg p_red_next, p_yellow_next, p_green_next;
+
+    wire count_is_three;
+    wire count_gt_ten;
+
+    assign count_is_three = ~(|cnt[7:2]) & cnt[1] & cnt[0];
+    assign count_gt_ten = (|cnt[7:4]) |
+                          (cnt[3] & (cnt[2] | (cnt[1] & cnt[0])));
+
+    always @* begin
+        state_next = state;
+        p_red_next = p_red;
+        p_yellow_next = p_yellow;
+        p_green_next = p_green;
+
+        case (state)
+            idle: begin
+                state_next = s1_red;
+                p_red_next = 1'b0;
+                p_yellow_next = 1'b0;
+                p_green_next = 1'b0;
+            end
+            s1_red: begin
+                state_next = count_is_three ? s3_green : s1_red;
+                p_red_next = 1'b1;
+                p_yellow_next = 1'b0;
+                p_green_next = 1'b0;
+            end
+            s2_yellow: begin
+                state_next = count_is_three ? s1_red : s2_yellow;
+                p_red_next = 1'b0;
+                p_yellow_next = 1'b1;
+                p_green_next = 1'b0;
+            end
+            s3_green: begin
+                state_next = count_is_three ? s2_yellow : s3_green;
+                p_red_next = 1'b0;
+                p_yellow_next = 1'b0;
+                p_green_next = 1'b1;
+            end
+            default: begin
+                state_next = state;
+                p_red_next = p_red;
+                p_yellow_next = p_yellow;
+                p_green_next = p_green;
+            end
+        endcase
+    end
+
+    always @(posedge clk or negedge rst_n) begin
+        if (!rst_n) begin
+            state <= idle;
+            p_red <= 1'b0;
+            p_yellow <= 1'b0;
+            p_green <= 1'b0;
         end
-        else case(state)
-		idle:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				state <= s1_red;
-			end
-		s1_red:
-			begin
-				p_red <= 1'b1;
-				p_green <= 1'b0;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s3_green;
-				else
-					state <= s1_red;
-			end
-		s2_yellow:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b0;
-				p_yellow <= 1'b1;
-				if (cnt == 3) 
-					state <= s1_red;
-				else
-					state <= s2_yellow;
-			end
-		s3_green:
-			begin
-				p_red <= 1'b0;
-				p_green <= 1'b1;
-				p_yellow <= 1'b0;
-				if (cnt == 3) 
-					state <= s2_yellow;
-				else
-					state <= s3_green;
-			end
-		endcase
-	end
- 
-always @(posedge clk or negedge rst_n) 
-      if(!rst_n)
-			cnt <= 7'd10;
-		else if (pass_request&&green&&(cnt>10))
-			cnt <= 7'd10;
-		else if (!green&&p_green)
-			cnt <= 7'd60;
-		else if (!yellow&&p_yellow)
-			cnt <= 7'd5;
-		else if (!red&&p_red)
-			cnt <= 7'd10;	
-		else cnt <= cnt -1;
- assign clock = cnt;
+        else begin
+            state <= state_next;
+            p_red <= p_red_next;
+            p_yellow <= p_yellow_next;
+            p_green <= p_green_next;
+        end
+    end
 
-always @(posedge clk or negedge rst_n) 
-        if(!rst_n)
-			begin
-				yellow <= 1'd0;
-				red <= 1'd0;
-				green <= 1'd0;
-			end
-		else 
-			begin
-				yellow <= p_yellow;
-				red <= p_red;
-				green <= p_green;
-			end		
+    always @(posedge clk or negedge rst_n) begin
+        if (!rst_n)
+            cnt <= 8'd10;
+        else if (pass_request && green && count_gt_ten)
+            cnt <= 8'd10;
+        else if (!green && p_green)
+            cnt <= 8'd60;
+        else if (!yellow && p_yellow)
+            cnt <= 8'd5;
+        else if (!red && p_red)
+            cnt <= 8'd10;
+        else
+            cnt <= cnt - 8'd1;
+    end
+
+    assign clock = cnt;
+
+    always @(posedge clk or negedge rst_n) begin
+        if (!rst_n) begin
+            yellow <= 1'b0;
+            red <= 1'b0;
+            green <= 1'b0;
+        end
+        else begin
+            yellow <= p_yellow;
+            red <= p_red;
+            green <= p_green;
+        end
+    end
 
 endmodule
```

## 57. c19f200937bca8e — rtllm_serial2parallel — gpt-5.6-luna — requested c1 -> rule b — label tradeoff

rule evidence: ["register names or clocked targets changed, flip-flop count and latency unchanged"]

```diff
--- D
+++ C
@@ -1,3 +1,2 @@
-
 module serial2parallel(
 	input clk,
@@ -9,37 +8,45 @@
 );
 
-	reg[7:0]din_tmp;
-	reg[3:0]cnt;
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			cnt <= 0;
-		else if(din_valid)
-			cnt <= (cnt == 4'd8)?0:cnt+1'b1;
-		else	
-			cnt <= 0;
+	reg [3:0] phase;
+	reg [3:0] din_hi;
+	reg [3:0] din_lo;
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n)
+			phase <= 4'd0;
+		else if (din_valid) begin
+			if (phase == 4'd8)
+				phase <= 4'd0;
+			else
+				phase <= phase + 4'd1;
+		end
+		else
+			phase <= 4'd0;
 	end
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			din_tmp <= 8'b0;
-		else if(din_valid && cnt <= 4'd7)
-			din_tmp <= {din_tmp[6:0],din_serial};
-	
-	end 
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)begin
-			dout_valid <= 1'b0;
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			din_hi <= 4'b0;
+			din_lo <= 4'b0;
+		end
+		else if (din_valid && (phase != 4'd8)) begin
+			din_hi <= {din_hi[2:0], din_lo[3]};
+			din_lo <= {din_lo[2:0], din_serial};
+		end
+	end
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			dout_valid    <= 1'b0;
 			dout_parallel <= 8'b0;
 		end
-		else if(cnt == 4'd8)begin
-			dout_valid <= 1'b1;
-			dout_parallel <= din_tmp;
+		else if (phase == 4'd8) begin
+			dout_valid    <= 1'b1;
+			dout_parallel <= {din_hi, din_lo};
 		end
 		else begin
-			dout_valid <= 1'b0;
+			dout_valid    <= 1'b0;
 		end
-	end 
-	
+	end
+
 endmodule
```

## 58. ced6e3b9c573f33 — rtllm_serial2parallel — gpt-5.6-terra — requested d -> rule b — label retained

rule evidence: ["register names or clocked targets changed, flip-flop count and latency unchanged"]

```diff
--- D
+++ C
@@ -1,3 +1,2 @@
-
 module serial2parallel(
 	input clk,
@@ -9,37 +8,46 @@
 );
 
-	reg[7:0]din_tmp;
-	reg[3:0]cnt;
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			cnt <= 0;
-		else if(din_valid)
-			cnt <= (cnt == 4'd8)?0:cnt+1'b1;
-		else	
-			cnt <= 0;
-	end
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			din_tmp <= 8'b0;
-		else if(din_valid && cnt <= 4'd7)
-			din_tmp <= {din_tmp[6:0],din_serial};
-	
-	end 
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)begin
+	reg [7:0] din_tmp;
+	reg [2:0] remaining;
+	reg frame_done;
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			remaining <= 3'd7;
+			frame_done <= 1'b0;
+			din_tmp <= 8'b00000000;
+			dout_parallel <= 8'b00000000;
 			dout_valid <= 1'b0;
-			dout_parallel <= 8'b0;
-		end
-		else if(cnt == 4'd8)begin
-			dout_valid <= 1'b1;
-			dout_parallel <= din_tmp;
 		end
 		else begin
-			dout_valid <= 1'b0;
+			if (din_valid) begin
+				if (frame_done) begin
+					remaining <= 3'd7;
+					frame_done <= 1'b0;
+				end
+				else begin
+					remaining[0] <= ~remaining[0];
+					remaining[1] <= remaining[1] ^ ~remaining[0];
+					remaining[2] <= remaining[2] ^ (~remaining[1] & ~remaining[0]);
+					frame_done <= ~remaining[2] & ~remaining[1] & ~remaining[0];
+				end
+			end
+			else begin
+				remaining <= 3'd7;
+				frame_done <= 1'b0;
+			end
+
+			if (din_valid & ~frame_done)
+				din_tmp <= {din_tmp[6:0], din_serial};
+
+			if (frame_done) begin
+				dout_valid <= 1'b1;
+				dout_parallel <= din_tmp;
+			end
+			else begin
+				dout_valid <= 1'b0;
+			end
 		end
-	end 
-	
+	end
+
 endmodule
```

## 59. cca37889705b5c8 — rtllm_serial2parallel — gpt-5.6-luna — requested a -> rule b — label retained

rule evidence: ["register names or clocked targets changed, flip-flop count and latency unchanged"]

```diff
--- D
+++ C
@@ -1,3 +1,2 @@
-
 module serial2parallel(
 	input clk,
@@ -9,37 +8,32 @@
 );
 
-	reg[7:0]din_tmp;
-	reg[3:0]cnt;
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			cnt <= 0;
-		else if(din_valid)
-			cnt <= (cnt == 4'd8)?0:cnt+1'b1;
-		else	
-			cnt <= 0;
-	end
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
+	reg [7:0] din_tmp;
+	reg [2:0] cnt;
+	reg frame_done;
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			cnt <= 3'b000;
+			frame_done <= 1'b0;
 			din_tmp <= 8'b0;
-		else if(din_valid && cnt <= 4'd7)
-			din_tmp <= {din_tmp[6:0],din_serial};
-	
-	end 
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)begin
 			dout_valid <= 1'b0;
 			dout_parallel <= 8'b0;
 		end
-		else if(cnt == 4'd8)begin
-			dout_valid <= 1'b1;
-			dout_parallel <= din_tmp;
+		else begin
+			dout_valid <= frame_done;
+			frame_done <= din_valid && (&cnt);
+
+			if (din_valid && !frame_done)
+				cnt <= cnt + 3'b001;
+			else
+				cnt <= 3'b000;
+
+			if (din_valid && !frame_done)
+				din_tmp <= {din_tmp[6:0], din_serial};
+
+			if (frame_done)
+				dout_parallel <= din_tmp;
 		end
-		else begin
-			dout_valid <= 1'b0;
-		end
-	end 
-	
+	end
+
 endmodule
```

## 60. c7cbb69c3151e50 — rtllm_serial2parallel — gpt-5.4 — requested b -> rule b — label tradeoff

rule evidence: ["register names or clocked targets changed, flip-flop count and latency unchanged"]

```diff
--- D
+++ C
@@ -1,3 +1,2 @@
-
 module serial2parallel(
 	input clk,
@@ -9,37 +8,57 @@
 );
 
-	reg[7:0]din_tmp;
-	reg[3:0]cnt;
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			cnt <= 0;
-		else if(din_valid)
-			cnt <= (cnt == 4'd8)?0:cnt+1'b1;
-		else	
-			cnt <= 0;
+	reg [7:0] din_tmp;
+	reg [2:0] bit_cnt;
+	reg word_ready;
+
+	wire last_bit;
+	wire shift_en;
+	wire set_ready;
+	wire bit_cnt_nonzero;
+
+	assign last_bit = bit_cnt[2] & bit_cnt[1] & bit_cnt[0];
+	assign shift_en = din_valid & ~word_ready;
+	assign set_ready = shift_en & last_bit;
+	assign bit_cnt_nonzero = bit_cnt[2] | bit_cnt[1] | bit_cnt[0];
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
+			din_tmp <= 8'b0;
+			bit_cnt <= 3'b0;
+			word_ready <= 1'b0;
+		end else begin
+			if (shift_en)
+				din_tmp <= {din_tmp[6:0], din_serial};
+
+			if (word_ready)
+				word_ready <= 1'b0;
+			else if (set_ready)
+				word_ready <= 1'b1;
+
+			if (word_ready)
+				bit_cnt <= 3'b0;
+			else if (din_valid) begin
+				if (set_ready)
+					bit_cnt <= 3'b0;
+				else
+					bit_cnt <= bit_cnt + 1'b1;
+			end else if (bit_cnt_nonzero)
+				bit_cnt <= 3'b0;
+		end
 	end
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)
-			din_tmp <= 8'b0;
-		else if(din_valid && cnt <= 4'd7)
-			din_tmp <= {din_tmp[6:0],din_serial};
-	
-	end 
-	
-	always@(posedge clk or negedge rst_n)begin
-		if(!rst_n)begin
+
+	always @(posedge clk or negedge rst_n) begin
+		if (!rst_n) begin
 			dout_valid <= 1'b0;
 			dout_parallel <= 8'b0;
+		end else begin
+			if (word_ready) begin
+				dout_valid <= 1'b1;
+				dout_parallel <= din_tmp;
+			end else if (dout_valid) begin
+				dout_valid <= 1'b0;
+			end
 		end
-		else if(cnt == 4'd8)begin
-			dout_valid <= 1'b1;
-			dout_parallel <= din_tmp;
-		end
-		else begin
-			dout_valid <= 1'b0;
-		end
-	end 
-	
+	end
+
 endmodule
```

