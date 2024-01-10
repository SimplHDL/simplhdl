interface alu_if();

    import uvm_pkg::*;
    `include "uvm_macros.svh"

    logic        clk;
    logic        reset;
    logic [15:0] a;
    logic [15:0] b;
    logic [16:0] result;
    logic [16:0] result_ref;
    logic [16:0] result_refadd;
    logic [3:0]  cmd;
    logic        valid;
    logic        ready;

    clocking active_ck @(posedge clk);
       output valid, a, b, cmd;
       input  ready, result;
    endclocking: active_ck

    clocking passive_ck @(posedge clk);
       input valid, a, b, cmd, ready, result;
    endclocking: passive_ck

    modport active(clocking active_ck);
    modport passive(clocking passive_ck);

/*
    always @(posedge clk) begin

        // result must not be X or Z during valid and ready both asserted
        assertResultUnknown:assert property (
            disable iff(reset)
                ((ready & valid) |-> !$isunknown(result)))
        else
            `uvm_error("ERR_ADDR_XZ", "Address went to X or Z");


        //Reset must be asserted for at least 3 clocks each time it is asserted
        assertResetFor3Clocks: assert property (
            ($rose(reset) |=> reset[*2]))
        else
            `uvm_error("ERR_SHORT_RESET_DURING_TEST",
                       "Reset was asserted for less than 3 clock cycles");

        assign result_refadd = a+b;

        assert_AdditionCheck:assert property (
            disable iff(reset)
                ((ready & valid & (cmd==0)) |-> (result == a + b)))
        else
            `uvm_error("ERR_ADD_RESULT",
                       "Addition Result is wrong");

        assert_SubtractionCheck:assert property (
            disable iff(reset)
                ((ready & valid & (cmd==1)) |-> (result == a - b)))
        else
            `uvm_error("ERR_SUB_RESULT",
                       "Subraction Result is wrong");

        assert_MartineCheck:assert property (disable iff(reset)
            ((valid ) |-> (result == a + b)))
        else
            `uvm_error("ERR_SUB_RESULT",
                       "Subraction Result is wrong");

        assert_Mart2:assert property (
            disable iff(reset)
                ((valid) |=> (ready)))
        else
            `uvm_error("INTENTIONAL ERROR", " ");

    end
*/
endinterface : alu_if
