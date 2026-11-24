# MCP Server (`simpl-mcp`)

SimplHDL includes an optional **Model Context Protocol (MCP)** server (`simpl-mcp`) that gives AI coding agents (such as
OpenCode, VS Code GitHub Copilot, and Claude Code) structured tools and skills to inspect projects and run flows.

## Installation

Install SimplHDL with the `mcp` extra (requires Python 3.10+):

```bash
pip install "simplhdl[mcp]"
```

Verify the binary is available:

```bash
simpl-mcp --version
```

## Configuring Your AI Harness

=== "OpenCode (`opencode.jsonc`)"

    Add `simpl-mcp` globally or per-project via the CLI:

    ```bash
    opencode mcp add simplhdl --global -- simpl-mcp
    ```

    Or in `opencode.jsonc`:

    ```jsonc
    {
      "$schema": "https://opencode.ai/config.json",
      "mcp": {
        "servers": {
          "simplhdl": {
            "type": "local",
            "command": ["simpl-mcp"]
          }
        }
      }
    }
    ```

=== "VS Code (`.vscode/mcp.json`)"

    ```json
    {
      "servers": {
        "simplhdl": {
          "type": "stdio",
          "command": "simpl-mcp"
        }
      }
    }
    ```

=== "Cursor (`.cursor/mcp.json`)"

    Add this configuration to `.cursor/mcp.json` in your project, or to `~/.cursor/mcp.json` for all projects:

    ```json
    {
      "mcpServers": {
        "simplhdl": {
          "type": "stdio",
          "command": "simpl-mcp"
        }
      }
    }
    ```

    Ensure `simpl-mcp` is available on Cursor's `PATH`, or use the absolute path to the executable in the Python
    environment where you installed `simplhdl[mcp]` and any parser plugins. See the
    [Cursor MCP documentation](https://cursor.com/docs/context/mcp) for configuration and troubleshooting.

=== "Claude Code"

    ```bash
    claude mcp add simplhdl -- simpl-mcp
    ```

## Provided MCP Tools

| Tool               | Description                                                                                                                                   |
| :----------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_project_info` | Returns project metadata (`name`, `part`, `toplevels`, `defines`, `parameters`, `generics`, `plusargs`, `hooks`, `libraries`, and `targets`). |
| `list_files`       | Lists files in compile or hierarchy order, with filters and optional `flow` and `generate` arguments.                                         |
| `get_fileset_tree` | Validates the project DAG and returns fileset memberships, optionally for a flow or after generation.                                         |
| `list_targets`     | Lists all targets defined in the project specification and identifies the default target.                                                     |
| `list_flows`       | Introspects all registered flows, categories, steps, and CLI options.                                                                         |
| `list_plugins`     | Lists all registered parsers (ordered by priority), generators, flows, and file extensions.                                                   |
| `get_skill`        | Returns the project specification guide for the highest-priority registered parser.                                                           |
| `run_flow`         | Runs any flow in an isolated async subprocess (blocks `--gui` by default unless `allow_gui=True`).                                            |
| `run_target`       | Runs `simpl run` for a named or default target.                                                                                               |
| `run_lint`         | Runs `simpl lint` (Verible, VSG, Flake8) with optional `files` and `fix` arguments.                                                           |
| `read_flow_log`    | Reads the tail of `<outputdir>/<flow>/simplhdl.log` and tool-specific logs.                                                                   |

For `list_files` and `get_fileset_tree`, set `flow` to inspect that flow's modeled inputs. Before generation, the view
also includes declared generator inputs. Set `generate=true` with a flow to run generators first; this may write files
and invoke external tools. Generated files include `generated` and `parent_file` in `list_files`. The older
`run_generators_for_flow` argument to `list_files` remains supported and, without `flow`, retains its unfiltered view.

`selection_declared` is false when a flow or generator has not declared its selection contract. In that case the view is
a fallback, not an exact list of tool inputs. Even for declared plugins, vendor tools or scripts can introduce
additional files outside the SimplHDL project model.

## Provided MCP Resources & Server Instructions

- **Server `instructions`**: Sent during the MCP `initialize` handshake, naming the highest-priority registered parser
  and describing how to use SimplHDL tools.
- **`simplhdl://skills/project-spec`**: On-demand MCP resource returning the format specification guide for the
  highest-priority registered parser (`#%SimplAPI=1.0` by default). A plugin can supply `format_guide` or use its
  installed package description. See [parser guides](plugins.md#parser-guides-for-mcp-clients).

The guide is selected by priority, **not by matching the specification of a particular project**. SimplHDL's runtime
parser selection also checks `is_valid_format()`, so it may select a different parser. Restart `simpl-mcp` after
changing its environment or installed plugins.

## Extending `simpl-mcp` from Third-Party Plugins

Third-party SimplHDL plugins can extend `simpl-mcp` in two ways:

1. Define `@classmethod def register_mcp_tools(cls, mcp)` on any `ParserBase`, `GeneratorBase`, or `FlowBase` plugin
   class.
2. Register a callable `def register(mcp): ...` under `[project.entry-points."simplhdl.mcp"]`.

See [MCP extensions](plugins.md#mcp-extensions) for an example.
