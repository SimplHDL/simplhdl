![SimplHDL — Hardware Design Made Easy](docs/_static/simplhdl_logo_1.svg)

Modern FPGA and ASIC teams shouldn't waste weeks maintaining fragile Tcl scripts, ad-hoc Makefiles, and vendor-locked
build flows.

**SimplHDL** unifies your entire hardware development lifecycle behind a single, intuitive command-line interface—and
with its built-in **MCP Server (`simpl-mcp`)**, it transforms your EDA environment into a true **Agentic Hardware
Workflow**.

## Why Teams Should Choose SimplHDL

- **One Workflow, Every EDA Tool**: Switch seamlessly between simulators and FPGA toolchains without rewriting build
  scripts. Define your design once; run it anywhere.
- **Built for Agentic AI Workflows**: Give AI coding agents (OpenCode, GitHub Copilot, Claude Code) native, structured
  access to your hardware project. Agents can autonomously explore design hierarchies, run simulations, lint RTL, and
  diagnose build logs—turning hours of debugging into seconds.
- **Drop-In Adoption for Existing Projects**: No need to reorganize your repository. SimplHDL's plugin architecture
  adapts to your existing project specification format so you can modernize your flow without disrupting your team.
- **Automated Register & IP Generation**: Go straight from SystemRDL, Chisel, Jinja2 templates, and vendor IP containers
  to simulation-ready RTL and UVM/pyuvm register models in a single command.

## Unify Your Entire Hardware Ecosystem

SimplHDL bridges industry-standard commercial EDA suites and modern open-source verification frameworks under one roof:

|                                  |                                                                                                                                                                                              |
| :------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AI & Agentic Workflows**       | **Model Context Protocol (`simpl-mcp`)** — Native integration with **OpenCode**, **VS Code Copilot**, **Claude Code**, and **Cursor** for autonomous RTL design, verification, and debugging |
| **Commercial & Open Simulators** | **Siemens QuestaSim**, **Siemens ModelSim**, **Synopsys VCS**, **Aldec Riviera-PRO**, **AMD Vivado Xsim**, and **Icarus Verilog**                                                            |
| **FPGA Implementation**          | **AMD / Xilinx Vivado** and **Intel / Altera Quartus Prime** (including Design Space Exploration and IP packaging)                                                                           |
| **Modern Verification**          | **UVM**, **Cocotb**, **pyuvm**, **OSVVM**, and **UVVM**                                                                                                                                      |
| **Design & Code Generation**     | **SystemVerilog**, **Verilog**, **VHDL**, **SystemRDL / PeakRDL** (RTL, PyUVM RAL & HTML docs), **Chisel**, **Jinja2**, and **Vendor IP Containers**                                         |
| **Code Quality & IP Protection** | Automated HDL/Python linting (**Verible**, **VSG**, **Flake8**) and multi-vendor **IEEE-1735 IP Encryption**                                                                                 |

## Getting Started

SimplHDL works on Linux and Windows WSL and requires Python 3.9 or later (Python 3.10+ for the optional `simpl-mcp`
server). Installing inside a Python virtual environment or Conda environment is recommended:

```console
pip install simplhdl
```

To also install the MCP server for agentic workflows:

```console
pip install "simplhdl[mcp]"
```

## Quick Example

Assuming SimplHDL is installed and Vivado and QuestaSim are set up in your shell environment:

1. Clone the repository from GitHub:

```console
git clone https://github.com/SimplHDL/simplhdl.git
```

2. Install SimplHDL from source:

```console
pip install ./simplhdl
```

3. Run simulation in batch mode:

```console
cd simplhdl/examples/hdl/alu/sim/uvm/testcases/test_add
simpl questasim
```

4. Run simulation interactively in the GUI:

```console
simpl questasim --gui
```

5. Run FPGA implementation:

```console
cd ../../../../syn
simpl vivado
```

6. Open the FPGA project interactively in the GUI:

```console
simpl vivado --gui
```

In this example, the project specification is written in YAML (`#%SimplAPI=1.0`). To integrate SimplHDL into an existing
project with a custom specification format, you can write a parser plugin for your format. See the documentation and
plugin examples for details.

## Links

- Documentation: <https://simplhdl.readthedocs.io/en/latest/>
- Source: <https://github.com/SimplHDL/simplhdl>
- Issue Tracker: <https://github.com/SimplHDL/simplhdl/issues>
