class agent extends uvm_agent;

    uvm_sequencer#(alu_vip::sequence_item) m_sequencer;
    alu_vip::driver                        m_driver;
    alu_vip::monitor                       m_monitor;

    virtual alu_if                         vif;

    `uvm_component_utils_begin(alu_vip::agent)
        `uvm_field_object(m_sequencer, UVM_ALL_ON)
        `uvm_field_object(m_driver, UVM_ALL_ON)
        `uvm_field_object(m_monitor, UVM_ALL_ON)
    `uvm_component_utils_end

    function new (string name, uvm_component parent);
        super.new(name, parent);
    endfunction : new


    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        m_monitor = alu_vip::monitor::type_id::create("m_monitor", this);

        if(this.get_is_active() == UVM_ACTIVE) begin
            m_sequencer = uvm_sequencer#(alu_vip::sequence_item)::type_id::create("m_sequencer", this);
            m_driver = alu_vip::driver::type_id::create("m_driver", this);
        end
        if (!uvm_config_db#(virtual alu_if)::get(this, "", "vif", vif)) begin
            `uvm_fatal("ALU/AGT/NOVIF", "No virtual interface specified for this agent instance")
        end
    endfunction : build_phase


    function void connect_phase(uvm_phase phase);
        if(this.get_is_active() == UVM_ACTIVE) begin
            m_driver.seq_item_port.connect(m_sequencer.seq_item_export);
        end
    endfunction : connect_phase

endclass : agent
