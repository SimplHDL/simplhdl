module alu #(
    parameter int WIDTH = 8
) (
    input  logic             clk_i,
    input  logic             rst_i,
    input  logic             valid_i,
    output logic             ready_o,
    input  logic [3:0]       cmd_i,
    input  logic [WIDTH-1:0] a_i,
    input  logic [WIDTH-1:0] b_i,
    output logic [WIDTH:0]   x_o
);

    typedef enum logic [3:0] {
        ADD = 1,
        SUB = 2,
        MUL = 3
    } cmd_e;

    typedef enum {
        IDLE,
        START,
        DONE
    } state_e;
    state_e current_state, next_state;

    logic ready;
    logic [WIDTH-1:0] add_result;
    logic [WIDTH-1:0] sub_result;
    logic [WIDTH-1:0] mul_result;

    always_ff @(posedge clk_i) begin
        if (rst_i == 1'b1) begin
            current_state <= IDLE;
        end else begin
            current_state <= next_state;
        end
    end

    always_comb begin
        case (current_state)
            IDLE: begin
                ready = 1'b0;
                if (valid_i == 1'b1) begin
                    next_state = START;
                end else begin
                    next_state = IDLE;
                end
            end

            START: begin
                if (valid_i == 1'b1) begin
                    ready = 1'b1;
                    next_state = DONE;
                end else begin
                    ready = 1'b0;
                    next_state = IDLE;
                end
            end

            DONE: begin
                ready = 1'b0;
                next_state = IDLE;
            end

            default: begin
                ready = 1'b0;
                next_state = IDLE;
            end
        endcase
    end

    always_ff @(posedge clk_i) begin
        ready_o <= ready;
        if (ready == 1'b1) begin
            case (cmd_e'(cmd_i))
                ADD:
                    x_o <= add_result;

                SUB:
                    x_o <= sub_result;

                MUL:
                    x_o <= mul_result;

                default:
                    x_o <= 0;
            endcase
        end
    end

    add #(
        .WIDTH(WIDTH)
    ) i_add (
        .a_i(a_i),
        .b_i(b_i),
        .x_o(add_result)
    );

    sub #(
        .WIDTH(WIDTH)
    ) i_sub (
        .a_i(a_i),
        .b_i(b_i),
        .x_o(sub_result)
    );

    mul #(
        .WIDTH(WIDTH)
    ) i_mul (
        .a_i(a_i),
        .b_i(b_i),
        .x_o(mul_result)
    );

endmodule: alu
