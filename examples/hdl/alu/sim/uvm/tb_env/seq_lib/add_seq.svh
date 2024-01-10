import alu_vip::ADD;

class add_seq extends tb_env::base_seq;

    `uvm_object_utils(tb_env::add_seq)

    function new(string name="add_seq");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info(
            get_type_name(),
            $sformatf("%s body() starting ", get_sequence_path()),
            UVM_MEDIUM
        )
        repeat(10) begin
            `uvm_do_with(req, {req.cmd == ADD;})
        end
    endtask

endclass : add_seq
