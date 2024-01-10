class sequence_item extends uvm_sequence_item;

    rand logic [alu_vip::WIDTH-1:0] a;
    rand logic [alu_vip::WIDTH-1:0] b;
    rand alu_vip::cmd_e             cmd;
    rand int                        transmit_delay;
    logic [16:0]                    result;

    constraint transmit_delay_cst {
        transmit_delay inside {[0:10]};
    }

    function new (string name = "sequence_item");
        super.new(name);
    endfunction


    `uvm_object_utils_begin(alu_vip::sequence_item)
    `uvm_field_int(a, UVM_ALL_ON | UVM_NOPACK);
    `uvm_field_int(b, UVM_ALL_ON | UVM_NOPACK);
    `uvm_field_int(result, UVM_ALL_ON | UVM_NOPACK);
    `uvm_field_int(transmit_delay, UVM_ALL_ON | UVM_NOPACK);
    `uvm_field_enum(cmd_e, cmd, UVM_ALL_ON | UVM_NOPACK);
    `uvm_object_utils_end


endclass: sequence_item
