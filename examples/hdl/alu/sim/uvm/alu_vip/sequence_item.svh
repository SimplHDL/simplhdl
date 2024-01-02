class sequence_item extends uvm_sequence_item;

   typedef enum logic[3:0] {ADD, SUB, MUL} cmd_e;

   rand logic [alu_vip::WIDTH-1:0] a;
   rand logic [alu_vip::WIDTH-1:0] b;
   rand cmd_e                  cmd;
   rand int                    transmit_delay;
   logic [16:0]                result;

   constraint transmit_delay_cst {
    transmit_delay inside {[0:10]};
   }

   `uvm_object_utils_begin(alu_vip::sequence_item)
     `uvm_field_int(a, UVM_ALL_ON | UVM_NOPACK);
     `uvm_field_int(b, UVM_ALL_ON | UVM_NOPACK);
     `uvm_field_int(transmit_delay, UVM_ALL_ON | UVM_NOPACK);
     `uvm_field_enum(cmd_e,cmd, UVM_ALL_ON | UVM_NOPACK);
   `uvm_object_utils_end

   function new (string name = "sequence_item");
      super.new(name);
   endfunction

   function string convert2string();
     return $sformatf("cmd=%s a=%0h b=%0h delay=%0h", cmd, a, b, transmit_delay);
   endfunction

endclass: sequence_item
