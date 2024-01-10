class base_test extends uvm_test;

    `uvm_component_utils(tb_env::base_test)

    tb_env::env       m_env;
    uvm_table_printer m_printer;
    bit test_pass = 1;

    function new(string name = "alu_base_test", uvm_component parent=null);
        super.new(name,parent);
    endfunction : new

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        // Enable transaction recording for everything
        uvm_config_db#(int)::set(this, "*", "recording_detail", UVM_FULL);
        m_env = tb_env::env::type_id::create("m_env", this);
        m_printer = new();
        m_printer.knobs.depth = 3;
    endfunction : build_phase

endclass: base_test
