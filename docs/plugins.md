# Plugins

SimplHDL is built around three plugin types registered under the Python entry-point group `simplhdl.plugins`:

1. **Parsers (`ParserBase`)** — Parse project specification files into the SimplHDL `Project` / `Design` / `Fileset`
   model.
2. **Generators (`GeneratorBase`)** — Generate HDL, IP, or verification files prior to running a flow and insert them
   into the project DAG.
3. **Flows (`FlowBase`, `SimulationFlow`, `ImplementationFlow`)** — Generate tool scripts/Makefiles and run EDA tools.

## Entry-Point Registration

Register plugins in your package's `pyproject.toml`:

```toml
[project.entry-points."simplhdl.plugins"]
my_parser = "my_package.parser:MyParser"
my_generator = "my_package.generator:MyGenerator"
my_flow = "my_package.flow:MyFlow"
```

## Parser Plugins & Precedence (`ParserBase`)

```python
from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from simplhdl import Fileset, Project
from simplhdl.plugin import ParserBase
from simplhdl.project.files import FileFactory


class MyParser(ParserBase):
    priority: int = 50  # Default for 3rd-party parsers (SimplHdlParser is 10)
    _format_id: str = "#%MyFormat=1.0"
    format_guide: str = """# MyFormat Specification Guide
    ...
    """

    def is_valid_format(self, filename: Path | None) -> bool:
        ...

    def parse(self, filename: Path | None, project: Project, args: Namespace) -> Fileset:
        ...
```

### Parser Priority Order

When SimplHDL selects a parser via `ParserFactory.get_parser(filename)` (and when `simpl-mcp` determines the active
project format skill):

1. **`SIMPLHDL_PARSER` environment variable**: Comma- or colon-separated list of parser names with highest precedence
   (e.g., `export SIMPLHDL_PARSER=simplhdl_parser`).
2. **`SIMPLHDL_CONFIG` TOML file**:
   ```toml
   [parser]
   priority = ["my_parser", "simplhdl_parser"]
   ```
3. **Third-party parser plugins**: Default `priority = 50` on `ParserBase`, automatically taking precedence over
   `SimplHdlParser`.
4. **Built-in `simplhdl_parser` (`SimplHdlParser`)**: Fallback `priority = 10`.

## Generator Plugins (`GeneratorBase`)

Generators inspect files in `self.project.defaultDesign` and can insert generated files immediately after their source
specification using `fileset.insert_file_after(source_file, generated_file)` so `project.elaborate()` preserves compile
order:

```python
from __future__ import annotations

from simplhdl.plugin import FlowBase, GeneratorBase
from simplhdl.project.files import SystemVerilogFile


class MyGenerator(GeneratorBase):
    def run(self, flow: FlowBase) -> None:
        ...
```

## Flow Plugins (`FlowBase`)

Flows define CLI subparser arguments in `@classmethod def parse_args(cls, subparsers)` and implement
`run(self) -> None`:

- Subclass `SimulationFlow` for HDL simulators (provides Makefile/dependency generation, Cocotb integration, plusarg and
  seed handling).
- Subclass `ImplementationFlow` (or `FlowBase`) for synthesis/FPGA implementation or utility flows.
