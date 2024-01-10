package alu_vip;

    import uvm_pkg::*;
    `include "uvm_macros.svh"

    parameter WIDTH = 16;

    typedef enum logic[3:0] {NOP, ADD, SUB, MUL} cmd_e;

    typedef class sequence_item;
    typedef class monitor;
    typedef class driver;
    typedef class agent;
    typedef class env;

    `include "sequence_item.svh"
    `include "monitor.svh"
    `include "driver.svh"
    `include "agent.svh"
    `include "env.svh"

endpackage: alu_vip
