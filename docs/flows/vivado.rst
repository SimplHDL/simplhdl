Vivado
======

The Vivado flow enabled SimplHDL to use Vivado to implement FPGA designs.
The Vivado flow is based on the standard Vivado Project mode, but can be
extended with Tcl hook to accomodate any Tcl flow with in Vivado,

The Vivado flow support the following design files.

.. list-table:: Supported file types
    :header-rows: 1

    * - File type
      - Extension
      - Description
    * - Verilog
      - .v
      - Verilog source file
    * - SystemVerilog
      - .sv
      - System Verilog Source file
    * - VerilogIncludeFiles
      - .vh
      - Verilog Include file
    * - SystemVerilogIncludeFiles
      - .vh
      - System Verilog Include file
    * - XilinxConstraintFiles
      - .xdc
      - Timing and placement constraints
    * - XilinxTclConstraintFiles
      - .tcl
      - Timing and placement constraints
    * - XilinxIPSpecification
      - .xci
      - Xilinx IP
    * - XilinxIPContainer
      - .xcix
      - Xilinx IP archive
    * - XilinxBDFile
      - .bd
      - Xilinx block design
    * - XilinxTclBDFile
      - .bd.tcl
      - Xilinx Tcl block design
    * - XilinxStepFiles
      - .step.tcl
      - Xilinx Tcl hook
