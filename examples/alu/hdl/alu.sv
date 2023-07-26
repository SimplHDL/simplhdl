module alu #(
    parameter int WIDTH = 8
)
(
    input              clk_i,
    input              rst_i,
    input  [WIDTH-1:0] a_i,
    input  [WIDTH-1:0] b_i,
    output [WIDTH-1:0] result_o
);

    adder i_adder();
    substraction i_substraction();
    alu_regblock i_alu_regblock();

endmodule: alu
