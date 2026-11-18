from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from shlex import split

import yaml

from simplhdl import (
    Fileset,
    Project,
)
from simplhdl.__main__ import parse_arguments
from simplhdl.plugin import ParserBase
from simplhdl.project.attributes import Library, Target
from simplhdl.project.files import FileFactory

SIMPLAPI_1_0_GUIDE = """# SimplHDL Project Specification (`#%SimplAPI=1.0`)

## Overview
SimplHDL's built-in YAML parser (`simplhdl_parser` / `SimplHdlParser`) reads `.yml` specification files whose **first line** is `#%SimplAPI=1.0`.

- **Auto-discovery**: When `--projectspec` is omitted, SimplHDL scans `*.yml` in the current working directory and selects the first `.yml` file starting with `#%SimplAPI=1.0`.
- **Relative paths**: All file paths (`files` and `dependencies`) are resolved relative to the directory containing the `.yml` file that declares them.

## Required Header
Every specification file **must** begin with the exact header on line 1:
```yaml
#%SimplAPI=1.0
```

## Supported YAML Keys

### Root-Only Keys (Applied Only in the Top-Level Entry Specification)
- `project` (`str`): Project name used for tool project files and archives (defaults to `"default"`).
- `part` (`str`): Target FPGA device part number (e.g., `xc7z007sclg225-2`).
- `top` (`str`): Space-separated top-level module/entity names for simulation or implementation (e.g., `alu` or `tb_top glbl`).

### Fileset & Hierarchy Keys (Valid in Any `.yml` Spec)
- `library` (`str`): HDL library name for files in this specification (defaults to `work`).
- `dependencies` (`list[str]`): Paths to child `#%SimplAPI=1.0` `.yml` files.
  - Child dependencies are compiled **before** the parent specification's `files`.
  - Duplicate references to the same resolved `.yml` file are automatically deduplicated.
- `files` (`list[str]`): Ordered list of source, include, constraint, IP, register, memory, or cocotb files.
  - Files within a specification are compiled in the exact order listed.
  - File types and `usedin` (`simulation`, `implementation`) are inferred automatically from file extensions via `FileFactory`:
    - **HDL**: `.sv`, `.v`, `.vh`, `.svh`, `.vhd`, `.vhdl` (encrypted: `.svp`, `.vp`, `.vhp`, `.svhp`)
    - **Constraints**: `.xdc` (Vivado), `.sdc` (Quartus/Synopsys)
    - **Vivado IP / Design**: `.xci`, `.xcix`, `.bd`, `.bd.tcl`, `.dcp`, `.edn`, `.edif`, `.steps.tcl`
    - **Quartus IP / Design**: `.ip`, `.ip.zip`, `.qsys`, `.qsys.zip`, `.qip`, `.qsf`, `.source.tcl`, `.stp`, `quartus.ini`
    - **Code Generation**: `.rdl` (SystemRDL / PeakRDL), `.j2` (Jinja2 template rendered with `os` in context and `.j2` suffix stripped), `.sbt` (Chisel)
    - **Simulation / Verification**: `.py` (Cocotb / pyuvm), `.c`, `.cpp`, `.h`, `modelsim.ini`
    - **Memory**: `.hex`, `.mif` (copied into simulation build directory)

### Project-Wide Configuration Maps (Valid in Any `.yml` Spec)
First definition wins if the same key is defined in multiple files:
- `defines` (`dict[str, str]`): Preprocessor macros for Verilog/SystemVerilog (`+define+NAME="VALUE"`) and SystemRDL.
- `parameters` (`dict[str, str]`): Top-level Verilog/SystemVerilog parameters.
- `generics` (`dict[str, str]`): Top-level VHDL generics.
- `plusargs` (`dict[str, str]`): Simulation runtime plusargs (`+NAME="VALUE"`).
  - **UVM note**: Defining any plusarg starting with `UVM_` (e.g., `UVM_TESTNAME`) automatically enables UVM compilation/simulation flags in supported simulators.
- `targets` (`dict[str, str]`): Named CLI flow invocations runnable with `simpl run -t <target>` (e.g., `sim: questasim --seed 1`).
  - Each target executes with its working directory set to the parent directory of the `.yml` file that defined it.
  - The first target defined becomes the default target for `simpl run`.

## Example Hierarchy

### 1. Reusable IP / RTL (`alu.yml`)
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

### 2. Simulation Spec (`sim/test_add.yml`)
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

### 3. FPGA Synthesis Spec (`syn/build.yml`)
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
"""


class SimplHdlParser(ParserBase):
    priority: int = 10
    _format_id: str = "#%SimplAPI=1.0"
    format_guide: str = SIMPLAPI_1_0_GUIDE

    def __init__(self):
        super().__init__()
        self._core_stack = list()
        self._core_visited = list()

    def is_valid_format(self, filename: Path | None) -> bool:
        if filename is None:
            filenames = Path(".").glob("*.yml")
        else:
            filenames = [filename]

        for filename in filenames:
            if filename.exists():
                with filename.open() as fp:
                    if fp.readline().strip() == self._format_id:
                        return True
        return False

    def parse(self, filename: Path | None, project: Project, args: Namespace) -> Fileset:
        if filename is None:
            files = Path(".").glob("*.yml")
        else:
            files = [filename]

        for file in files:
            if self.is_valid_format(file):
                return self.parse_core(file, project)

    def parse_core(self, filename: Path, project: Project) -> Fileset:  # noqa: C901
        self._core_stack.append(filename)
        spec = self.read_spec(filename)
        libname = spec.get("library")
        if not libname:
            library = project.defaultDesign.defaultLibrary
        else:
            library = Library(libname)

        fileset = Fileset(str(filename), Library=library)
        for corefile in spec.get("dependencies", list()):
            corefile = self.path(corefile)
            if corefile.absolute() in self._core_visited:
                continue
            subfileset = self.parse_core(corefile, project)
            fileset.add_fileset(subfileset)

        if "top" in spec:
            fileset.TopLevel = spec.get("top")

        for name, value in spec.get("targets", dict()).items():
            target = Target(
                name=name,
                args=parse_arguments(split(value)),
                cwd=self._core_stack[-1].parent,
            )
            project.add_target(target)
        for name, value in spec.get("defines", dict()).items():
            project.add_define(name, value)
        for name, value in spec.get("parameters", dict()).items():
            project.add_parameter(name, value)
        for name, value in spec.get("plusargs", dict()).items():
            project.add_plusarg(name, value)
        for name, value in spec.get("generics", dict()).items():
            project.add_generic(name, value)
        for filepath in spec.get("files", list()):
            resolvefilepath = filename.parent.joinpath(filepath).resolve()
            file = FileFactory.create(resolvefilepath)
            fileset.add_file(file)
        # Top level spec
        if len(self._core_stack) == 1:
            if "project" in spec:
                project.name = spec.get("project")
            if "part" in spec:
                project.part = spec.get("part")
            if "top" in spec:
                project.defaultDesign.toplevels = spec.get("top").split()

        self._core_stack.pop()
        return fileset

    def read_spec(self, filename: Path) -> dict:
        self._core_visited.append(filename.resolve())
        with filename.open() as fp:
            try:
                return yaml.safe_load(fp)
            except yaml.YAMLError as e:
                raise e

    def path(self, filename: str) -> Path:
        if Path(filename).is_absolute():
            path = Path(filename).resolve()
        else:
            path = self._core_stack[-1].parent.joinpath(filename).resolve()
        if not path.exists():
            raise FileNotFoundError(f"No such file: {str(path)}")
        return path
