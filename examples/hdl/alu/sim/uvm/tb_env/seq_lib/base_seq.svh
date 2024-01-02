virtual class base_seq extends uvm_sequence #(alu_vip::sequence_item);

    function new(string name="base_seq");
        super.new(name);
    endfunction

    virtual task pre_body();
        if (starting_phase!=null) begin
            `uvm_info(
                get_type_name(),
                $sformatf(
                    "%s pre_body() raising %s objection",
                    get_sequence_path(),
                    starting_phase.get_name()
                ),
                UVM_MEDIUM
            );
            starting_phase.raise_objection(this);
        end
    endtask

    virtual task post_body();
        if (starting_phase!=null) begin
            `uvm_info(
                get_type_name(),
                $sformatf(
                    "%s post_body() dropping %s objection",
                    get_sequence_path(),
                    starting_phase.get_name()
                ),
                UVM_MEDIUM
            );
            starting_phase.drop_objection(this);
        end
    endtask

endclass : base_seq
