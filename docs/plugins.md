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

### Parser priority

`ParserFactory` tries parsers in descending priority order and selects the **first one that accepts the project
specification** via `is_valid_format()`. When no filename is supplied, parsers may discover specifications in the
current directory. Parsers with equal priority retain their registration order.

The `ParserBase.priority` default is `50`; the built-in `simplhdl_parser` has priority `10`. Projects can override these
values in the TOML file named by `SIMPLHDL_CONFIG`:

```toml
[parser]
priority = ["my_parser", "simplhdl_parser"]  # First is tried first
# Alternatively: priority = { my_parser = 100, simplhdl_parser = 10 }
```

`SIMPLHDL_PARSER` accepts a single parser name or a comma- or colon-separated list. It overrides the configured values
for the named parsers; it does not force a parser that rejects the specification to accept it. Numeric priorities from
other parsers can still affect the final ordering.

### Parser guides for MCP clients

These optional class attributes help `simpl-mcp` describe a parser; existing plugins do not need to define them:

| Attribute      | Purpose                                                                                  |
| -------------- | ---------------------------------------------------------------------------------------- |
| `priority`     | Controls parser selection order; inherited from `ParserBase` when omitted.               |
| `_format_id`   | Informational format identifier exposed by MCP; it does not replace `is_valid_format()`. |
| `format_guide` | Markdown guide served to MCP clients when this parser is selected for the guide.         |

`simpl-mcp` exposes the guide through `simplhdl://skills/project-spec` and `get_skill("project-spec")`. It currently
chooses the **highest-priority registered parser** for that guide without checking a particular project. A different
parser may actually handle a project if the higher-priority parser rejects it. Server instructions are generated at
startup; restart the server after changing its environment or installed plugins.

For a single source of documentation, a plugin can declare `readme = "README.md"` in its `pyproject.toml`. If it does
not provide a non-empty `format_guide`, `simpl-mcp` looks for the installed distribution's description, which normally
contains that README. Automatic discovery requires an unambiguous mapping from the parser's top-level Python package to
one installed distribution. If no guide is available, MCP returns a note and may include another parser's guide as a
fallback; that fallback does not describe the selected parser's format.

To explicitly provide the same README from a `src`-layout plugin, including an uninstalled source checkout:

```python
from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path


def load_readme() -> str | None:
    try:
        description = metadata("my-parser-distribution").get("Description")
    except PackageNotFoundError:
        description = None
    if description:
        return description

    readme = Path(__file__).resolve().parents[2] / "README.md"
    return readme.read_text(encoding="utf-8") if readme.is_file() else None


class MyParser(ParserBase):
    format_guide = load_readme()
    # Implement is_valid_format() and parse() as above.
```

Installed metadata is a snapshot: rebuild or reinstall the plugin after changing the README, including for editable
installs, then restart the MCP server.

## Generator Plugins (`GeneratorBase`)

Generators inspect files in `self.project.defaultDesign` and can use
`fileset.insert_file_after(source_file, generated_file)` to add generated files to the dependency graph:

```python
from __future__ import annotations

from simplhdl.plugin import FlowBase, GeneratorBase
from simplhdl.project.files import SystemVerilogFile


class MyGenerator(GeneratorBase):
    def run(self, flow: FlowBase) -> None:
        ...
```

Generators run in registration order. There is currently no generator-priority setting; the file ordering values below
apply to files, not generator execution.

## File attributes and ordering

`FileFactory.create(path, **attributes)` selects a file class by extension and accepts attributes such as `usedin`,
`encrypt`, and `order`. Constraint files also support `scope`. These attributes can be set on the resulting file object;
whether a flow uses a particular attribute depends on the flow. Files are cached by resolved path, so constructing the
same file again does not necessarily reapply new attributes.

`simplhdl.project.files.FileOrder` provides numeric values for `file.order`:

| Value              |  Numeric order |
| ------------------ | -------------: |
| `FileOrder.EARLY`  |           25.0 |
| `FileOrder.NORMAL` | 50.0 (default) |
| `FileOrder.LATE`   |           75.0 |

Custom numeric values are also supported. `Design.files()` starts with a topological ordering of the file graph, then
sorts by `file.order`; in compile order, lower values come first. Different order values can therefore override graph
order. `Fileset.files()` uses the graph ordering but does not apply the numeric sort. This `FileOrder` is distinct from
`simplhdl.project.fileset.FileOrder`, which selects `COMPILE` or `HIERARCHY` traversal.

```python
from pathlib import Path
from simplhdl.project.files import FileFactory, FileOrder

constraint = FileFactory.create(Path("timing.xdc"), order=FileOrder.EARLY, scope="top")
```

## Flow Plugins (`FlowBase`)

Flows define CLI subparser arguments in `@classmethod def parse_args(cls, subparsers)` and implement
`run(self) -> None`:

- Subclass `SimulationFlow` for HDL simulators (provides Makefile/dependency generation, Cocotb integration, plusarg and
  seed handling).
- Subclass `ImplementationFlow` (or `FlowBase`) for synthesis/FPGA implementation or utility flows.

## MCP extensions

To add custom MCP tools or resources, define an optional class or static method on a registered parser, generator, or
flow. The server calls it with its MCP server instance during startup:

```python
class MyParser(ParserBase):
    @classmethod
    def register_mcp_tools(cls, mcp):
        @mcp.tool()
        def explain_my_format() -> str:
            """Describe the project's specification format."""
            return "See the MyFormat guide."

    # Implement is_valid_format() and parse() as above.
```

Alternatively, register a callable accepting the MCP server under `[project.entry-points."simplhdl.mcp"]`. This hook is
separate from `simplhdl.plugins` and is loaded by `simpl-mcp`, not the regular CLI. See [MCP Server](mcp.md).
