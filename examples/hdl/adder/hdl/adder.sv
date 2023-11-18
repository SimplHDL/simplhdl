module adder #(
    parameter int WIDTH = 32
)(
    input  logic             clk_i,
    input  logic             rst_i,
    input  logic [WIDTH-1:0] a_i,
    input  logic [WIDTH-1:0] b_i,
    output logic [WIDTH-1:0] sum_o
);

    always_ff @( posedge clk_i ) begin
        if (rst_i) begin
            sum_o <= 0;
        end else begin
           sum_o <= a_i + b_i;
        end
    end

endmodule: adder
