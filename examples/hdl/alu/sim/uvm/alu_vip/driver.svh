class driver extends uvm_driver #(alu_vip::sequence_item);

    `uvm_component_utils(alu_vip::driver)
    protected virtual alu_if vif;

    function new (string name, uvm_component parent);
        super.new(name, parent);
    endfunction : new

    function void build_phase(uvm_phase phase);
        alu_vip::agent agent;
        super.build_phase(phase);
        if ($cast(agent, get_parent()) && agent != null) begin
           vif = agent.vif;
        end
        else begin
            if(!uvm_config_db#(virtual alu_if)::get(this, "", "vif", vif))
                `uvm_fatal("NOVIF",{"virtual interface must be set for: ",get_full_name(),".vif"});
        end
    endfunction: build_phase


    virtual task run_phase(uvm_phase phase);
        super.run_phase(phase);
        @(this.vif.active_ck);
        wait(this.vif.reset === 1'b1);
        @(this.vif.active_ck);
        wait(this.vif.reset !== 1'b1);
        forever begin
            alu_vip::sequence_item tr;
            seq_item_port.get_next_item(tr);
            this.drive(tr);
            seq_item_port.item_done();
        end
    endtask : run_phase


    virtual task drive (alu_vip::sequence_item trans);
        if (trans.transmit_delay > 0) begin
            repeat(trans.transmit_delay) @(this.vif.active_ck);
        end
        this.vif.active_ck.valid  <= 1;
        this.vif.active_ck.a      <= trans.a;
        this.vif.active_ck.b      <= trans.b;
        this.vif.active_ck.cmd    <= trans.cmd;
        wait(this.vif.active_ck.ready);
        this.vif.active_ck.valid  <= 0;
        //      @(this.vif.active_ck);
    endtask : drive

endclass : driver
