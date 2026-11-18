# SimplHDL

## Hardware Design Made Easy

Modern FPGA and ASIC teams shouldn't waste weeks maintaining fragile Tcl scripts, ad-hoc Makefiles, and vendor-locked
build flows.

**SimplHDL** unifies your entire hardware development lifecycle behind a single, intuitive command-line interface—and
with its built-in **MCP Server (`simpl-mcp`)**, it transforms your EDA environment into a true **Agentic Hardware
Workflow**.

---

## Why Teams Should Choose SimplHDL

- **One Workflow, Every EDA Tool** Switch seamlessly between simulators and FPGA toolchains without rewriting build
  scripts. Define your design once; run it anywhere.
- **Built for Agentic AI Workflows** Give AI coding agents (OpenCode, GitHub Copilot, Claude Code) native, structured
  access to your hardware project. Agents can autonomously explore design hierarchies, run simulations, lint RTL, and
  diagnose build logs—turning hours of debugging into seconds.
- **Drop-In Adoption for Existing Projects** No need to reorganize your repository. SimplHDL's plugin architecture
  adapts to your existing project specification format so you can modernize your flow without disrupting your team.
- **Automated Register & IP Generation** Go straight from SystemRDL, Chisel, Jinja2 templates, and vendor IP containers
  to simulation-ready RTL and UVM/pyuvm register models in a single command.

---

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

---

## Installation

SimplHDL requires **Python 3.9 or later** and works on Linux and Windows WSL. Installing inside a Python virtual
environment is recommended:

```bash
pip install simplhdl
```

To also install the [Model Context Protocol (MCP) server](mcp.md) (`simpl-mcp`, requires Python 3.10+):

```bash
pip install "simplhdl[mcp]"
```

## Quickstart

Assuming SimplHDL is installed and your target EDA tools (such as QuestaSim or Vivado) are available in `PATH`:

```bash
# Clone the repository to try the bundled examples
git clone https://github.com/SimplHDL/simplhdl.git

# 1. Inspect project structure and compile order
cd simplhdl/examples/hdl/alu/sim/uvm/testcases/test_add
simpl info

# 2. Run simulation in batch mode
simpl questasim

# 3. Open simulation interactively in the GUI
simpl questasim --gui

# 4. Run FPGA synthesis and implementation
cd ../../../../syn
simpl vivado
```

## Core CLI Commands

Global options apply before the flow subcommand:

```bash
simpl [-v] [-o OUTPUTDIR] [--projectspec FILE] <flow> [flow-options...]
```

- `--projectspec FILE`: Explicitly specify the project specification file (defaults to auto-discovery in the current
  directory).
- `-o`, `--outputdir DIR`: Build output directory (defaults to `_build`; each flow writes to `<outputdir>/<flow>/`).
- `-v`, `--verbose`: Increase logging verbosity (can be repeated: `-v`, `-vv`).

### Built-in Utility Flows

- **`simpl info`**: Inspect the elaborated project model (`--files`, `--filesets`, `--libraries`, `--hooks`) and
  generate topological DAG visualizations (`files.png`, `filesets.png`) in `_build/info/`.
- **`simpl run`**: List (`simpl run -l`) or execute (`simpl run -t <target>`) named project targets defined in the
  project specification.
