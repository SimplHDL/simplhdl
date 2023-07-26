module adder #(
    parameter int WIDTH = 8
)(
    input                    clk_i,
    input                    rst_i,
    input        [WIDTH-1:0] a_i,
    input        [WIDTH-1:0] b_i,
    output logic [WIDTH-1:0] sum_o,
    output logic             carry_o
);

    always_ff @( clk_i ) begin
        if (rst_i) begin
            {carry_o, sum_o} <= 0;
        end else begin
            {carry_o, sum_o} <= a_i + b_i;
        end
    end

endmodule: adder
