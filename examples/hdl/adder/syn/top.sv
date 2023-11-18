module top #(
    parameter int WIDTH = 32
)(
    input  logic                  clk_i,
    input  logic                  rst_i,
    input  logic      [WIDTH-1:0] a_i,
    input  logic      [WIDTH-1:0] b_i,
    output logic [WIDTH-1:0] sum_o
);

    adder #(
        .WIDTH(WIDTH)
    ) i_adder (
        .clk_i(clk_i),
        .rst_i(rst_i),
        .a_i(a_i),
        .b_i(b_i),
        .sum_o(sum_o)
    );

endmodule: top
