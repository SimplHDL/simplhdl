# Jinja2 & Chisel Generators

SimplHDL runs registered generator plugins prior to executing the selected flow, allowing templated files and hardware
construction languages to emit standard Verilog, SystemVerilog, VHDL, or constraint files into the build directory.

## Jinja2 Generator (`simplhdl_jinja2`)

Any file in the project ending with `.j2` (`Jinja2File`) is processed by `Jinja2Generator`:

1. The file is rendered using Jinja2 (`StrictUndefined`) into `_build/<flow>/jinja2/<filename_without_.j2>`.
2. The `os` module is exposed in the template context, allowing environment variable lookups such as
   `{{ os.environ['MY_PARAM'] }}`.
3. The `File` object's path in the project model is updated in-place to point to the rendered output file in
   `_build/<flow>/jinja2/`.

## Chisel Generator (`simplhdl_chisel`)

When a project includes a `.sbt` (`ChiselBuildFile`) file:

1. `ChiselGenerator` creates an isolated project workspace under `_build/<flow>/chisel/projects/<name>/` and symlinks
   the Chisel source tree.
2. It runs `sbt --sbt-dir _build/<flow>/chisel/sbt run` to emit Verilog (`.v`) files.
3. All generated `*.v` files are inserted into the fileset immediately after the `.sbt` file so downstream simulation
   and implementation flows compile them in order.
