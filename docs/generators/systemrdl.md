# SystemRDL & PeakRDL Generator

When a SimplHDL project includes `.rdl` (`SystemRdlFile`) files, `PeakRdlGenerator` automatically compiles them using
`systemrdl-compiler` (passing `project.defines`) and generates:

1. **SystemVerilog Register Blocks** (`peakrdl-regblock`) for all unique leaf `addrmap` nodes (inserted into the fileset
   immediately after the source `.rdl` file so they compile before dependent RTL).
2. **PyUVM Register Abstraction Layer (RAL) Models** (`peakrdl-pyuvm`) in
   `_build/<flow>/systemrdl/peakrdl-pyuvm/ralmodel.py` when running a simulation flow that contains at least one `.py`
   (`CocotbPythonFile`) file.
3. **HTML Documentation** (`peakrdl-html`) in `_build/<flow>/systemrdl/peakrdl-docs/`.
4. **Custom Hierarchy Templates** rendered from `SIMPLHDL_SYSTEMRDL_TEMPLATES` for each root `addrmap`.

## Configuration (`SIMPLHDL_CONFIG`)

Set the `SIMPLHDL_CONFIG` environment variable to point to a TOML configuration file:

```bash
export SIMPLHDL_CONFIG=/path/to/simplhdl.toml
```

### Example `simplhdl.toml`

```toml
[peakrdl.regblock]
enable = true
cpuif = "axi4-lite"
default_reset = "rst_n"
type_style = "lexical"
module_name = "%_regblock"
package_name = "%_regblock_pkg"
address_width = 32
retime_read_fanin = false
retime_read_response = false
retime_external = ["reg", "mem"]
generate_hwif_report = false
err_if_bad_addr = false
err_if_bad_rw = false

[peakrdl.pyuvm]
enable = true
type_style = "lexical"
export_as_package = true
use_uvm_factory = false

[peakrdl.html]
enable = true
skip_not_present = false
```

### `[peakrdl.regblock]` Options

| Option            | Default     | Allowed Values / Notes                                                                                                                                         |
| :---------------- | :---------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `enable`          | `true`      | Enable or disable SystemVerilog regblock generation.                                                                                                           |
| `cpuif`           | `"apb3"`    | `"passthrough"`, `"apb3"`, `"apb3-flat"`, `"apb4"`, `"apb4-flat"`, `"axi4-lite"`, `"axi4-lite-flat"`, `"avalon-mm"`, `"avalon-mm-flat"`, `"obi"`, `"obi-flat"` |
| `default_reset`   | `"rst"`     | `"rst"` (active-high sync), `"rst_n"` (active-low sync), `"arst"` (active-high async), `"arst_n"` (active-low async)                                           |
| `type_style`      | `"lexical"` | `"lexical"` (reuses hardware interface typedefs) or `"hier"`                                                                                                   |
| `module_name`     | `"%"`       | `%` is replaced by `node.type_name`.                                                                                                                           |
| `package_name`    | `"%_pkg"`   | `%` is replaced by `node.type_name`.                                                                                                                           |
| `retime_external` | `[]`        | Array of `"reg"`, `"regfile"`, `"mem"`, `"addrmap"`, or `["all"]`.                                                                                             |
| `address_width`   | `None`      | Override address bus width (integer).                                                                                                                          |

## Custom Hierarchy Templates (`SIMPLHDL_SYSTEMRDL_TEMPLATES`)

To generate custom address decoders, interconnect wrappers, or headers for top-level address maps, set
`SIMPLHDL_SYSTEMRDL_TEMPLATES` to a colon-separated list of template directories:

```bash
export SIMPLHDL_SYSTEMRDL_TEMPLATES=/path/to/templates
```

- Each directory is searched for a Jinja2 template whose filename starts with `hierachymap` and ends with `.j2` (for
  example, `hierachymap.sv.j2`).
- For each root `addrmap`, the template is rendered to
  `_build/<flow>/systemrdl/<template_dir_name>/<root_type_name>__<template_name_without_j2>`.
- If the output file ends with `.sv`, `.v`, or `.vhd`, it is automatically inserted into the project fileset right after
  the source `.rdl` file.

### Template Context Globals

- `node`: The root `AddrmapNode` (`root.top`).
- `nodes`: All `AddrmapNode` instances in the root map.
- `leafnodes`: Leaf `AddrmapNode` instances (address maps with no child address maps).
- `hierachynodes`: Non-leaf `AddrmapNode` instances.
- `max_access_width`: Maximum register `accesswidth` or memory `memwidth` in bits.
- `max_addr_width`: Maximum address width in bits (`max(bit_length(node.size - 1), config.address_width)`).
- Helper functions: `get_reg_access(reg)`, `get_field_access(field)`, `is_leaf(node)`, `mask(node)`, `hex`, `len`.
