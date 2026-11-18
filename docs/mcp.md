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

=== "Claude Code"

    ```bash
    claude mcp add simplhdl -- simpl-mcp
    ```

## Provided MCP Tools

| Tool               | Description                                                                                                                                                                   |
| :----------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_project_info` | Returns project metadata (`name`, `part`, `toplevels`, `defines`, `parameters`, `generics`, `plusargs`, `hooks`, `libraries`, and `targets`).                                 |
| `list_files`       | Lists project files in `compile` or `hierarchy` order with filters (`usedin`, `file_type`, `library`, `fileset`, and `run_generators_for_flow`).                              |
| `get_fileset_tree` | Validates the project DAG and returns the fileset dependency hierarchy and file memberships.                                                                                  |
| `list_targets`     | Lists all targets defined in the project specification and identifies the default target.                                                                                     |
| `list_flows`       | Introspects all registered flows, categories, steps, and CLI options.                                                                                                         |
| `list_plugins`     | Lists all registered parsers (ordered by priority), generators, flows, and file extensions.                                                                                   |
| `get_skill`        | Returns the active project specification skill (`project-spec`), respecting parser priority (`SIMPLHDL_PARSER` / `SIMPLHDL_CONFIG` / third-party parsers / `#%SimplAPI=1.0`). |
| `run_flow`         | Runs any flow in an isolated async subprocess (blocks `--gui` by default unless `allow_gui=True`).                                                                            |
| `run_target`       | Runs `simpl run` for a named or default target.                                                                                                                               |
| `run_lint`         | Runs `simpl lint` (Verible, VSG, Flake8) with optional `files` and `fix` arguments.                                                                                           |
| `read_flow_log`    | Reads the tail of `<outputdir>/<flow>/simplhdl.log` and tool-specific logs.                                                                                                   |

## Provided MCP Resources & Server Instructions

- **Server `instructions`**: Automatically sent during the MCP `initialize` handshake, informing the agent which parser
  plugin is active and how to use SimplHDL tools effectively.
- **`simplhdl://skills/project-spec`**: On-demand MCP resource returning the format specification guide for the
  highest-priority registered parser (`#%SimplAPI=1.0` by default, or a third-party parser's `format_guide`).

## Extending `simpl-mcp` from Third-Party Plugins

Third-party SimplHDL plugins can extend `simpl-mcp` in two ways:

1. Define `@classmethod def register_mcp_tools(cls, mcp)` on any `ParserBase`, `GeneratorBase`, or `FlowBase` plugin
   class.
2. Register a callable `def register(mcp): ...` under `[project.entry-points."simplhdl.mcp"]`.
