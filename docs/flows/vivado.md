# AMD / Xilinx Vivado (`vivado`)

The `vivado` flow implements FPGA designs in AMD/Xilinx Vivado Project Mode and supports Tcl step hooks for custom build
customization.

## Usage

```bash
simpl vivado [options]
```

## CLI Options

| Option                                                                                   | Description                                          |
| :--------------------------------------------------------------------------------------- | :--------------------------------------------------- |
| `--step {lint,project,elaborate,synthesis,opt,power_opt,place,phys_opt,route,bitstream}` | Target implementation step (default: `bitstream`).   |
| `--gui`                                                                                  | Open the generated `.xpr` project in the Vivado GUI. |
| `--archive {project,project-exclude-results,project-include-settings}`                   | Create a Vivado project archive (`.xpr.zip`).        |

## Supported File Types

| File Class           | Extension       | Description                                                                     |
| :------------------- | :-------------- | :------------------------------------------------------------------------------ |
| `VerilogFile`        | `.v`            | Verilog source file                                                             |
| `SystemVerilogFile`  | `.sv`           | SystemVerilog source file                                                       |
| `VerilogIncludeFile` | `.vh`, `.svh`   | Verilog / SystemVerilog include file                                            |
| `VhdlFile`           | `.vhd`, `.vhdl` | VHDL source file                                                                |
| `VivadoXdcFile`      | `.xdc`          | Timing and placement constraints                                                |
| `TclFile`            | `.tcl`          | Tcl constraint or script file                                                   |
| `VivadoXciFile`      | `.xci`          | Xilinx IP specification                                                         |
| `VivadoXcixFile`     | `.xcix`         | Xilinx IP core container archive (unpacked by `VivadoGenerator` for simulation) |
| `VivadoBdFile`       | `.bd`           | Vivado Block Design                                                             |
| `VivadoBdTclFile`    | `.bd.tcl`       | Vivado Tcl Block Design                                                         |
| `VivadoDcpFile`      | `.dcp`          | Design Checkpoint file                                                          |
| `EdifFile`           | `.edn`, `.edif` | EDIF netlist                                                                    |
| `VivadoStepFile`     | `.steps.tcl`    | Vivado Tcl step hook script                                                     |
