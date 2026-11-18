# Flows Overview

SimplHDL flows generate tool-specific build scripts, Makefiles, or Tcl project files inside `<outputdir>/<flow>/`
(default `_build/<flow>/`) and execute the target EDA tool.

Every flow run writes a detailed execution log to `_build/<flow>/simplhdl.log`.

## Flow Categories

| Category                         | Flows                                                                                                                                                                                                                               |
| :------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Simulation**                   | [QuestaSim](questasim.md) (`questasim`), [ModelSim](modelsim.md) (`modelsim`), [Synopsys VCS](vcs.md) (`vcs`), [Riviera-PRO](rivierapro.md) (`rivierapro`), [Xilinx Xsim](xsim.md) (`xsim`), [Icarus Verilog](icarus.md) (`icarus`) |
| **Implementation**               | [Xilinx Vivado](vivado.md) (`vivado`, `vivado-export`), [Intel Quartus](quartus.md) (`quartus`, `quartus-dse`, `quartus-export`)                                                                                                    |
| **Lint & IP Protection**         | [Lint & Encrypt](lint-encrypt.md) (`lint`, `encrypt`)                                                                                                                                                                               |
| **Project Inspection & Targets** | `info`, `run`                                                                                                                                                                                                                       |

## Common Simulation Capabilities

All simulation flows inherit from `SimulationFlow` and provide:

- **Step control (`--step`)**: Stop after `generate`, `compile`, `elaborate`, or run full `simulate`.
- **Random seeds (`--seed`, `--random-seed`)**: Sets simulator seed and exports `RANDOM_SEED` and `COCOTB_RANDOM_SEED`.
- **Cocotb & pyuvm**: Automatically detects `CocotbPythonFile` (`.py`) files in the project, configures `PYTHONPATH` and
  GPI libraries, and launches Cocotb tests against the HDL top-level.
- **UVM**: Automatically enables UVM compilation/elaboration flags when any plusarg starting with `UVM_` (such as
  `UVM_TESTNAME`) is present in the project.
- **Memory files**: Copies `.hex` and `.mif` (`MemoryFile`) files into the simulation working directory.
