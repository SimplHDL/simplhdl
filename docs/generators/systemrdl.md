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

- Every template whose filename ends with `.j2` is rendered for each root `addrmap`, in sorted filename order. Other
  files, including `.j2.disable`, are ignored. Directories with no matching templates are allowed.
- Each template is rendered to
  `_build/<flow>/systemrdl/<template_dir_name>/<root_type_name>_<template_name_without_j2>`.
  For example, `interconnect.sv.j2` produces `<root_type_name>_interconnect.sv`. Nested template paths are searched,
  but only the template's filename is used for the output; conflicting output paths cause an error.
- If the output file ends with `.sv`, `.v`, or `.vhd`, it is automatically inserted into the project fileset right after
  the source `.rdl` file.

### Template Context Globals

- `node`: The root `AddrmapNode` (`root.top`).
- `output_stem`: The generated filename without its final extension. For package templates, use
  `package {{ output_stem }};` and `endpackage : {{ output_stem }}` to match the package name to the output filename.
- `template_basename`: The template filename without `.j2` or its final output-file extension. For example,
  `nested/interconnect.sv.j2` gives `interconnect`. Use `{{ node.type_name }}_{{ template_basename }}_pkg` to form a
  package name; this does not change the generated filename.
- `nodes`: All `AddrmapNode` instances in the root map.
- `leafnodes`: Leaf `AddrmapNode` instances (address maps with no child address maps).
- `hierachynodes`: Non-leaf `AddrmapNode` instances.
- `max_access_width`: Maximum register `accesswidth` or memory `memwidth` in bits.
- `max_addr_width`: Maximum address width in bits (`max(bit_length(node.size - 1), config.address_width)`).
- Helper functions: `get_reg_access(reg)`, `get_field_access(field)`, `is_leaf(node)`, `mask(node)`, `hex`, `len`.
