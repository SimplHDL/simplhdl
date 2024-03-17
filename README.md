## Introduction

SimplHDL is a plugin-based command-line application for simplifying FPGA and
ASIC development regardless of EDA tools and flows.

The goal is to embrase structured and reusable designs by creating a generic
project model that can be used in any hdl development flow regardless of
project structure and EDA tool requirements.

The plugin based architecture allows for SimplHDL to be migrated into any
existing project, replacing ad-hoc simulation and implmentation scripts while
providing a intuitive command-line interface for HDL design and verification
engineers.

I wide vararity of languges, standards and tools are supported.

### HDL languages

* Verilog / System Verilog
* VHDL
* Chisel
* SystemRDL
* IPXact
* Vivado IP containters (.xci, .xcix)
* Quartus IP containers (.ip)

### Methodologies

* UVM
* OSVMM
* UVVM
* Cocotb
* pyuvm

### EDA Tools

* Vivado
* Quartus
* Modelsim
* Questasim
* Xsim
* Vcs
* Riviera Pro
* Xcelium (coming)
* Verilator (coming)
* Icarus (coming)
* GHDL (coming)

## Getting Started

SimplHDL currently works on Linux and Windows WSL. It is written in Python and can
be installed with *pip*. To run SimplHDL Python 3.8 or later is required. The
tools for the flows you wish to run also need to be installed and set up
correctly in the shell environment. SimplHDL can be installed on your system's
Python installation, but it is highly recommended to install and run SimplHDL
in a Python virtual environment or a Conda environment.

## Example

To quickly try out SimplHDL follow these steps. In this example, we will use
Vivado and QuestaSim. The prerequisites are that SimplHDL install installed and
Vivado and QuestaSim are correctly set up in your shell environment.

1. Clone Git repository from GitHub

```console
git clone https://github.com/SimplHDL/simplhdl.git
```

2. install SimplHDL from source

```console
pip install ./simplhdl
```

3. Run simulation

```console
cd simplhdl/examples/hdl/alu/sim
simpl questasim
```

4. Run simulation interactively in Gui.

```console
cd simplhdl/examples/hdl/alu/sim
simpl questasim --gui
```

5. Run implementation

```console
cd ../syn
simpl vivado
```

6. Run implementation interactively in Gui.

```console
simpl vivado --gui
```

In this example, the project specification is written in Yaml. This format is
only meant as a demonstration. To integrate SimplHDL into your project, you have
to write a parser plugin for your specific project specification format.
See the documentation and plugin examples for more information.

## Links

* Homepage:
* Source: <https://github.com/SimplHDL/simplhdl>
* Tracker: <https://github.com/SimplHDL/simplhdl/issues>
