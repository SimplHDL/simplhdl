class test_add extends tb_env::base_test;

    `uvm_component_utils(tb_env::test_add)

    function new(string name = "test_add", uvm_component parent=null);
        super.new(name,parent);
    endfunction: new

    virtual function void build_phase(uvm_phase phase);
        uvm_config_db#(uvm_object_wrapper)::set(
            this,
            "m_env.m_alu_agent.m_sequencer.run_phase",
            "default_sequence",
            tb_env::add_seq::type_id::get()
        );
        // set_type_override_by_type(alu_driver::get_type(), new_driver::get_type());
        super.build_phase(phase);
    endfunction : build_phase

    virtual function void connect_phase(uvm_phase phase);
        uvm_root::get().print_topology();
        uvm_factory::get().print();
        uvm_config_db #(uvm_object_wrapper)::dump();
    endfunction

endclass : test_add
