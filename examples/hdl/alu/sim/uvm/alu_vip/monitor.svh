class monitor extends uvm_monitor;

    `uvm_component_utils(alu_vip::monitor)

    protected virtual alu_if                    vif;
    uvm_analysis_port #(alu_vip::sequence_item) ap;
    alu_vip::sequence_item                      tr_cov;

    covergroup alu_trans;
        option.per_instance = 1;
        ops : coverpoint tr_cov.cmd {
            bins add={0};
            bins sub={1};
            bins mul={2};
        }
        delays : coverpoint tr_cov.transmit_delay {
            bins pow2_delays[] = {1, 2, 4, 8};
            bins other_delays[] = default;
        }
    endgroup : alu_trans

    covergroup add_trans;
        option.per_instance = 1;
        operand_A : coverpoint tr_cov.a {
            bins zero={16'h0};
            bins all_ones={16'hffff};
            bins alternate_ones[]={16'h5555, 16'hAAAA};
            bins ranges[10]={[1:16'hfffe]};
        }
        operand_B : coverpoint tr_cov.b  {
            bins zero={16'h0};
            bins all_ones={16'hffff};
            bins alternate_ones[]={16'h5555, 16'hAAAA};
            bins ranges[10]={[1:16'hfffe]};
        }
        result : coverpoint tr_cov.result {
            bins zero={16'h0};
            bins all_ones={16'hffff};
            bins alternate_ones[]={16'h5555, 16'hAAAA};
            bins ranges[10]={[1:16'hfffe]};
        }
    endgroup : add_trans

    covergroup sub_trans;
        option.per_instance = 1;
        operand_A : coverpoint tr_cov.a {
            bins zero={16'h0};
            bins all_ones={16'hffff};
            bins alternate_ones[]={16'h5555, 16'hAAAA};
            bins ranges[10]={[1:16'hfffe]};
        }
        operand_B : coverpoint tr_cov.b  {
            bins zero={16'h0};
            bins all_ones={16'hffff};
            bins alternate_ones[]={16'h5555, 16'hAAAA};
            bins ranges[10]={[1:16'hfffe]};
        }
        result : coverpoint tr_cov.result {
            bins zero={16'h0};
            bins all_ones={16'hffff};
            bins alternate_ones[]={16'h5555, 16'hAAAA};
            bins ranges[10]={[1:16'hfffe]};
        }
    endgroup : sub_trans


    function new (string name, uvm_component parent);
        super.new(name, parent);
        alu_trans = new();
        add_trans = new();
        sub_trans = new();
        alu_trans.set_inst_name({get_full_name(), ".alu_trans"});
        add_trans.set_inst_name({get_full_name(), ".add_trans"});
        sub_trans.set_inst_name({get_full_name(), ".sub_trans"});
        ap = new("ap", this);
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


    virtual protected task run_phase(uvm_phase phase);
        super.run_phase(phase);
        forever begin
            alu_vip::sequence_item tr;
            int delay_count = 0;
            tr = alu_vip::sequence_item::type_id::create("tr", this);

            @(this.vif.passive_ck);
            while (this.vif.passive_ck.valid !== 1'b1) begin
                @(this.vif.passive_ck);
            end

            while (this.vif.passive_ck.ready !== 1'b1) begin
                delay_count = delay_count + 1;
                @(this.vif.passive_ck);
            end
            tr.a = this.vif.passive_ck.a;
            tr.b = this.vif.passive_ck.b;
            //tr.cmd = this.vif.passive_ck.cmd;
            $cast(tr.cmd, this.vif.passive_ck.cmd);
	        tr.transmit_delay = delay_count;
            tr.result = this.vif.passive_ck.result;
            tr_cover(tr);
            ap.write(tr);
        end
    endtask: run_phase


    virtual protected function void tr_cover(alu_vip::sequence_item tr);
        this.tr_cov = tr;
        alu_trans.sample();
        if(this.tr_cov.cmd == 0) begin
            add_trans.sample();
        end else  if(this.tr_cov.cmd == 1) begin
            sub_trans.sample();
        end
    endfunction : tr_cover

    virtual function void report_phase(uvm_phase phase);
        `uvm_info(get_full_name(),$sformatf("Covergroup 'alu_trans' coverage: %2f",
			      alu_trans.get_inst_coverage()),UVM_LOW)
    endfunction

endclass : monitor
