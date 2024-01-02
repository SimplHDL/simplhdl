module add #(
    parameter int WIDTH
) (
    input  logic [WIDTH-1:0] a_i,
    input  logic [WIDTH-1:0] b_i,
    output logic [WIDTH-1:0] x_o
);

    assign x_o = a_i + b_i;

endmodule: add
