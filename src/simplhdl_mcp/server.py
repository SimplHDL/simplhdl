from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from simplhdl import __version__

from .context import (
    build_flow_cli_args,
    build_server_instructions,
    get_skill_data,
    load_project,
    read_log_file,
    register_external_mcp_extensions,
    run_simpl_cli,
    serialize_files,
    serialize_fileset_tree,
    serialize_flows,
    serialize_plugins,
    serialize_project_info,
    serialize_targets,
)


def _generated_inspection(operation: str, project: dict[str, Any], options: dict[str, Any]) -> Any:
    request = json.dumps({"operation": operation, "project": project, "options": options})
    result = subprocess.run(
        [sys.executable, "-m", "simplhdl_mcp.inspection_worker", request],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode:
        raise RuntimeError(f"Generated inspection failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def get_project_info(
    project_dir: str = ".",
    projectspec: str | None = None,
    outputdir: str = "_build",
) -> dict[str, Any]:
    """
    Return structured metadata for a SimplHDL project.

    Includes project name, FPGA part, top-levels, libraries, defines,
    parameters, generics, plusargs, hooks, and runnable targets.
    """
    project = load_project(project_dir=project_dir, projectspec=projectspec, outputdir=outputdir)
    return serialize_project_info(project)


def list_files(
    project_dir: str = ".",
    projectspec: str | None = None,
    order: str = "compile",
    usedin: str | None = None,
    file_type: str | None = None,
    library: str | None = None,
    fileset: str | None = None,
    run_generators_for_flow: str | None = None,
    outputdir: str = "_build",
    flow: str | None = None,
    generate: bool = False,
) -> list[dict[str, Any]]:
    """
    List files in the SimplHDL project in 'compile' or 'hierarchy' order.

    Optional filters:
    - usedin: 'simulation' or 'implementation'
    - file_type: class name such as 'SystemVerilogFile', 'VerilogFile', 'VhdlFile', 'SystemRdlFile', 'VivadoXdcFile'
    - library: HDL library name (e.g., 'work')
    - fileset: exact fileset name
    - run_generators_for_flow: flow name (e.g., 'questasim' or 'vivado') to run code/IP generators before listing files
    - flow: inspect files in the context of this flow, including generator inputs before generation
    - generate: run generators before listing files (requires flow; may run external tools and write files)
    """
    project_options = dict(
        project_dir=project_dir,
        projectspec=projectspec,
        outputdir=outputdir,
        run_generators_for_flow=run_generators_for_flow,
        flow=flow,
        generate=generate,
    )
    file_options = dict(order=order, usedin=usedin, file_type=file_type, library=library, fileset=fileset)
    if generate or run_generators_for_flow:
        return _generated_inspection("files", project_options, file_options)
    project = load_project(**project_options)
    return serialize_files(project, **file_options)


def get_fileset_tree(
    project_dir: str = ".",
    projectspec: str | None = None,
    order: str = "compile",
    outputdir: str = "_build",
    flow: str | None = None,
    generate: bool = False,
) -> dict[str, Any]:
    """
    Validate the project DAG and return the fileset hierarchy and files per fileset.
    """
    project_options = dict(
        project_dir=project_dir, projectspec=projectspec, outputdir=outputdir, flow=flow, generate=generate
    )
    if generate:
        return _generated_inspection("filesets", project_options, {"order": order})
    project = load_project(**project_options)
    return serialize_fileset_tree(project, order=order)


def list_targets(
    project_dir: str = ".",
    projectspec: str | None = None,
    outputdir: str = "_build",
) -> dict[str, Any]:
    """
    List all targets defined in the project specification and identify the default target.
    """
    project = load_project(project_dir=project_dir, projectspec=projectspec, outputdir=outputdir)
    return serialize_targets(project)


def list_flows() -> list[dict[str, Any]]:
    """
    List all registered SimplHDL flows, their categories (simulation, implementation, default),
    available steps, and CLI options.
    """
    return serialize_flows()


def list_plugins() -> dict[str, Any]:
    """
    List all registered SimplHDL plugins (built-in and third-party):
    parsers (ordered by priority), generators, flows, and registered file types/extensions.
    """
    return serialize_plugins()


def get_skill(name: str = "project-spec") -> dict[str, Any]:
    """
    Fetch a SimplHDL skill/guide (such as 'project-spec' for the active project specification format).
    """
    return get_skill_data(name=name)


def project_spec_skill_resource() -> str:
    """Return the active project specification skill markdown for `simplhdl://skills/project-spec`."""
    return str(get_skill_data("project-spec")["content"])


async def run_flow(
    flow: str,
    project_dir: str = ".",
    projectspec: str | None = None,
    outputdir: str = "_build",
    step: str | None = None,
    extra_args: list[str] | str | None = None,
    verbose: int = 0,
    timeout: int = 600,
    allow_gui: bool = False,
) -> dict[str, Any]:
    """
    Execute any SimplHDL flow (e.g., 'questasim', 'modelsim', 'vcs', 'rivierapro',
    'xsim', 'icarus', 'vivado', 'quartus', 'lint', 'encrypt', 'info', or third-party flows).
    """
    cli_args = build_flow_cli_args(
        flow=flow,
        projectspec=projectspec,
        outputdir=outputdir,
        step=step,
        extra_args=extra_args,
        verbose=verbose,
        allow_gui=allow_gui,
    )
    result = await run_simpl_cli(cli_args, cwd=project_dir, timeout=timeout)
    log_path = Path(project_dir).resolve() / outputdir / flow / "simplhdl.log"
    result["log_file"] = str(log_path) if log_path.is_file() else None
    return result


async def run_target(
    target: str | None = None,
    project_dir: str = ".",
    projectspec: str | None = None,
    outputdir: str = "_build",
    verbose: int = 0,
    timeout: int = 600,
) -> dict[str, Any]:
    """
    Run a named project target (`simpl run -t <target>`) or the default target if `target` is omitted.
    """
    extra = ["-t", target] if target else []
    cli_args = build_flow_cli_args(
        flow="run",
        projectspec=projectspec,
        outputdir=outputdir,
        extra_args=extra,
        verbose=verbose,
    )
    return await run_simpl_cli(cli_args, cwd=project_dir, timeout=timeout)


async def run_lint(
    project_dir: str = ".",
    projectspec: str | None = None,
    files: list[str] | None = None,
    fix: bool = False,
    outputdir: str = "_build",
    verbose: int = 0,
    timeout: int = 300,
) -> dict[str, Any]:
    """
    Run `simpl lint` (Verible, VSG, Flake8) on the project or a specific list of files.
    """
    extra: list[str] = []
    if fix:
        extra.append("--fix")
    if files:
        extra.extend(["-f", *files])

    return await run_flow(
        flow="lint",
        project_dir=project_dir,
        projectspec=projectspec,
        outputdir=outputdir,
        extra_args=extra,
        verbose=verbose,
        timeout=timeout,
    )


def read_flow_log(
    flow: str,
    project_dir: str = ".",
    outputdir: str = "_build",
    tail_lines: int = 200,
) -> dict[str, Any]:
    """
    Read the tail of `<outputdir>/<flow>/simplhdl.log` and any tool-specific `.log` files in that build directory.
    """
    return read_log_file(flow=flow, project_dir=project_dir, outputdir=outputdir, tail_lines=tail_lines)


def create_server() -> Any:
    """Create and configure the SimplHDL MCP server, including third-party extensions."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ModuleNotFoundError as exc:
        if exc.name not in {"mcp", "mcp.server", "mcp.server.mcpserver"}:
            raise
        raise ImportError('MCP SDK 2.x is required. Install it with: pip install "simplhdl[mcp]"') from exc

    instructions = build_server_instructions()
    mcp = MCPServer("simplhdl", instructions=instructions)

    mcp.tool()(get_project_info)
    mcp.tool()(list_files)
    mcp.tool()(get_fileset_tree)
    mcp.tool()(list_targets)
    mcp.tool()(list_flows)
    mcp.tool()(list_plugins)
    mcp.tool()(get_skill)
    mcp.tool()(run_flow)
    mcp.tool()(run_target)
    mcp.tool()(run_lint)
    mcp.tool()(read_flow_log)

    mcp.resource("simplhdl://skills/project-spec")(project_spec_skill_resource)

    register_external_mcp_extensions(mcp)
    return mcp


def parse_mcp_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="simpl-mcp",
        description="Model Context Protocol (MCP) server for SimplHDL",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"simpl-mcp (SimplHDL version {__version__})",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport protocol (default: stdio)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_mcp_args(argv)
    try:
        server = create_server()
    except ImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    server.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    sys.exit(main())
