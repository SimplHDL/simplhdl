# Project Specification (`#%SimplAPI=1.0`)

SimplHDL uses **Parser plugins** to read project specifications and construct the in-memory `Project`, `Design`,
`Fileset`, and `File` dependency graphs.

Out of the box, SimplHDL includes `SimplHdlParser` (`simplhdl_parser`), which parses YAML specification files marked
with the `#%SimplAPI=1.0` header.

!!! note "Custom Project Formats" If your organization uses its own project specification format (such as `import_list`
files), you can install a [custom Parser plugin](plugins.md). Installed third-party parser plugins automatically take
precedence over `#%SimplAPI=1.0`.

## Required Header & Auto-Discovery

Every `#%SimplAPI=1.0` YAML file **must** begin with `#%SimplAPI=1.0` on the very first line:

```yaml
#%SimplAPI=1.0
```

- When `--projectspec` is omitted on the command line, `SimplHdlParser` scans `*.yml` in the current working directory
  and selects the first file whose first line is `#%SimplAPI=1.0`.
- All relative paths in `files` and `dependencies` are resolved relative to the directory containing the `.yml` file
  that declares them.

## Supported Keys

### Root-Only Keys

The following keys are applied only when defined in the **top-level (root) entry specification**:

| Key       | Type  | Description                                                                   |
| :-------- | :---- | :---------------------------------------------------------------------------- |
| `project` | `str` | Project name used for tool projects and archives (defaults to `"default"`).   |
| `part`    | `str` | Target FPGA device part number (e.g., `xc7z007sclg225-2`).                    |
| `top`     | `str` | Space-separated top-level module/entity names (e.g., `alu` or `tb_top glbl`). |

### Fileset & Hierarchy Keys

The following keys can be used in **any** `.yml` file in the dependency hierarchy:

| Key            | Type        | Description                                                                                                                                   |
| :------------- | :---------- | :-------------------------------------------------------------------------------------------------------------------------------------------- |
| `library`      | `str`       | HDL library name for all HDL files in this specification (defaults to `work`).                                                                |
| `dependencies` | `list[str]` | List of relative or absolute paths to child `.yml` specifications. Child filesets are compiled **before** the parent specification's `files`. |
| `files`        | `list[str]` | Ordered list of design, verification, constraint, IP, or template files. Compiled in the exact order listed.                                  |

### Project-Wide Maps

First definition wins if the same key is declared in multiple `.yml` files across the dependency tree:

| Key          | Type             | Description                                                                                                                                                                           |
| :----------- | :--------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `defines`    | `dict[str, str]` | Verilog/SystemVerilog (`+define+NAME="VALUE"`) and SystemRDL preprocessor macros.                                                                                                     |
| `parameters` | `dict[str, str]` | Top-level Verilog/SystemVerilog parameters.                                                                                                                                           |
| `generics`   | `dict[str, str]` | Top-level VHDL generics.                                                                                                                                                              |
| `plusargs`   | `dict[str, str]` | Runtime simulator plusargs (`+NAME="VALUE"`). Any plusarg starting with `UVM_` (such as `UVM_TESTNAME`) automatically enables UVM mode in simulation flows.                           |
| `targets`    | `dict[str, str]` | Named flow commands runnable via `simpl run -t <name>`. Each target runs from the directory of the `.yml` file that defined it. The first target becomes the default for `simpl run`. |

## Automatic File Classification

SimplHDL classifies files in `files:` by extension (matching longest suffix first):

| Category                      | Extensions                                                                                           | Default `usedin`                                        |
| :---------------------------- | :--------------------------------------------------------------------------------------------------- | :------------------------------------------------------ |
| **Verilog / SystemVerilog**   | `.sv`, `.v`, `.vh`, `.svh`, `.svp`, `.vp`, `.vhp`, `.svhp`                                           | `simulation`, `implementation`                          |
| **VHDL**                      | `.vhd`, `.vhdl`                                                                                      | `simulation`, `implementation`                          |
| **Constraints**               | `.xdc`, `.sdc`                                                                                       | `implementation`                                        |
| **Vivado IP / Design**        | `.xci`, `.xcix`, `.bd`, `.bd.tcl`, `.dcp`, `.edn`, `.edif`, `.steps.tcl`                             | `simulation`, `implementation` (IPs) / `implementation` |
| **Quartus IP / Design**       | `.ip`, `.ip.zip`, `.qsys`, `.qsys.zip`, `.ipx`, `.qip`, `.qsf`, `.source.tcl`, `.stp`, `quartus.ini` | `simulation`, `implementation` (IPs) / `implementation` |
| **Code Generators**           | `.rdl` (SystemRDL), `.j2` (Jinja2), `.sbt` (Chisel)                                                  | `simulation`, `implementation`                          |
| **Verification / C / Cocotb** | `.py` (Cocotb/pyuvm), `modelsim.ini`, `.c`, `.s`, `.cpp`, `.h`                                       | `simulation` (`.py`, `modelsim.ini`)                    |
| **Memory Initialization**     | `.hex`, `.mif`                                                                                       | `simulation`, `implementation`                          |

## Complete Example

=== "RTL (`alu.yml`)"

    ```yaml
    #%SimplAPI=1.0
    library: work

    dependencies:
      - hdl/add.yml

    files:
      - hdl/alu.sv
      - hdl/sub.sv
      - hdl/mul.sv
    ```

=== "Simulation (`sim/test_add.yml`)"

    ```yaml
    #%SimplAPI=1.0
    top: testbench

    dependencies:
      - ../alu.yml

    files:
      - testbench.sv

    plusargs:
      UVM_TESTNAME: tb_env::test_add

    targets:
      sim: questasim --wavedump
    ```

=== "Synthesis (`syn/build.yml`)"

    ```yaml
    #%SimplAPI=1.0
    project: alu
    part: xc7z007sclg225-2
    top: alu

    dependencies:
      - ../alu.yml

    files:
      - timing.xdc
      - placement.xdc

    targets:
      synth: vivado --step bitstream
    ```
