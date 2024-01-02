module testbench;

    import uvm_pkg::*;
    import tb_env::test_add;

    alu_if vif();
    integer index ;

    alu #(
        .WIDTH(alu_vip::WIDTH))
    dut(
        .clk_i(vif.clk),
        .rst_i(vif.reset),
        .valid_i(vif.valid),
        .ready_o(vif.ready),
        .a_i(vif.a),
        .b_i(vif.b),
        .cmd_i(vif.cmd),
        .x_o(vif.result)
    );

    initial begin
        uvm_config_db#(virtual alu_if)::set(uvm_root::get(), "*", "vif", vif);
        run_test();
    end

    always @(posedge vif.clk) begin
        if (index < 100000000) begin
	        $display("%d",index);
            index <= index + 1;
        end
    end

    initial begin
        vif.reset <= 1'b1;
        vif.clk <= 1'b1;
        #51 vif.reset = 1'b0;
    end

    always
        #5 vif.clk = ~vif.clk;

/*
    // Dump some hierarchy
    initial begin
        $fsdbDumpfile("inter.fsdb");
        $fsdbDumpvars(1,tb_top.alu);
    end
*/


endmodule: testbench
