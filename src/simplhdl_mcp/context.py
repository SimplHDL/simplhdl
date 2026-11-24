from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
from importlib import metadata
import logging
import shlex
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any, Generator, cast

from simplhdl.plugin.flow import FlowBase, FlowFactory, inspection_files
from simplhdl.plugin.generator import GeneratorFactory
from simplhdl.plugin.implementationflow import ImplementationFlow
from simplhdl.plugin.loader import get_external_plugins, load_plugins
from simplhdl.plugin.parser import ParserFactory
from simplhdl.plugin.simulationflow import SimulationFlow
from simplhdl.project.files import File, FileFactory
from simplhdl.project.fileset import FileOrder, Fileset, FilesetOrder
from simplhdl.project.project import Project
from simplhdl.simplhdl import Simplhdl
from simplhdl.utils import chdir


def ensure_plugins_loaded() -> None:
    """Load SimplHDL built-in and entry-point plugins if not already loaded."""
    if not FlowFactory.get_flows():
        load_plugins()


def _iter_all_subclasses(cls: type) -> set[type]:
    """Recursively collect all subclasses of `cls`."""
    subclasses: set[type] = set()
    work = list(cls.__subclasses__())
    while work:
        sub = work.pop()
        if sub not in subclasses:
            subclasses.add(sub)
            work.extend(sub.__subclasses__())
    return subclasses


@contextmanager
def reset_project_state() -> Generator[None, None, None]:
    """Reset singleton and WeakRef caches before and after in-process operations."""
    root_logger = logging.getLogger()
    initial_handlers = list(root_logger.handlers)
    setattr(Project, "_instance", None)
    Fileset._cache.clear()
    for fs_sub in _iter_all_subclasses(Fileset):
        cache = getattr(fs_sub, "_cache", None)
        if cache is not None and hasattr(cache, "clear"):
            cache.clear()
    File._cache.clear()
    for file_sub in _iter_all_subclasses(File) | set(FileFactory._registered_types.values()):
        cache = getattr(file_sub, "_cache", None)
        if cache is not None and hasattr(cache, "clear"):
            cache.clear()
    File.set_path_relative_to(None)
    try:
        yield
    finally:
        for handler in list(root_logger.handlers):
            if handler not in initial_handlers:
                root_logger.removeHandler(handler)
                handler.close()


def _build_simpl_arg_parser() -> tuple[argparse.ArgumentParser, Any]:
    """
    Build the SimplHDL CLI ArgumentParser with all registered flow subparsers,
    without invoking `argcomplete.autocomplete`.
    """
    ensure_plugins_loaded()
    parser = argparse.ArgumentParser(prog="simpl", add_help=False)
    parser.add_argument("--projectspec", type=Path, help="Project specification file")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    parser.add_argument(
        "-o",
        "--outputdir",
        default=Path("_build"),
        type=Path,
        help="output directory for build files",
    )
    subparsers = parser.add_subparsers(title="Flows", dest="flow")
    flows_map = cast(dict[str, type[FlowBase]], FlowFactory.get_flows())
    for flow_class in flows_map.values():
        flow_class.parse_args(subparsers)
    return parser, subparsers


def build_default_flow_namespace(
    flow_name: str,
    projectspec: Path | None,
    outputdir: Path,
    verbose: int = 0,
) -> Namespace:
    """
    Create an `argparse.Namespace` populated with all default arguments registered
    by `flow_name`'s subparser so third-party parsers, generators, and flows can
    safely access any flow argument attribute.
    """
    parser, subparsers = _build_simpl_arg_parser()
    if flow_name in subparsers.choices:
        argv: list[str] = ["-o", str(outputdir)]
        if verbose > 0:
            argv.append("-" + "v" * min(verbose, 3))
        if projectspec is not None:
            argv.extend(["--projectspec", str(projectspec)])
        argv.append(flow_name)
        args = parser.parse_args(argv)
        args.projectspec = projectspec
        args.outputdir = outputdir
        return args

    return Namespace(
        projectspec=projectspec,
        outputdir=outputdir,
        flow=flow_name,
        verbose=verbose,
    )


def _resolve_order_files(order: str) -> FileOrder:
    order_norm = order.strip().upper()
    if order_norm == "COMPILE":
        return FileOrder.COMPILE
    if order_norm == "HIERARCHY":
        return FileOrder.HIERARCHY
    raise ValueError(f"Unsupported file order '{order}'. Must be 'compile' or 'hierarchy'.")


def _resolve_order_filesets(order: str) -> FilesetOrder:
    order_norm = order.strip().upper()
    if order_norm == "COMPILE":
        return FilesetOrder.COMPILE
    if order_norm == "HIERARCHY":
        return FilesetOrder.HIERARCHY
    raise ValueError(f"Unsupported fileset order '{order}'. Must be 'compile' or 'hierarchy'.")


def load_project(
    project_dir: str | Path = ".",
    projectspec: str | Path | None = None,
    outputdir: str | Path = "_build",
    run_generators_for_flow: str | None = None,
    flow: str | None = None,
    generate: bool = False,
) -> Project:
    """
    Parse, elaborate, and validate a SimplHDL project in-process.

    If `run_generators_for_flow` is given, also runs registered Generator plugins
    for that flow and re-elaborates the project.
    """
    ensure_plugins_loaded()
    project_dir_path = Path(project_dir).resolve()
    if not project_dir_path.is_dir():
        raise FileNotFoundError(f"Project directory does not exist: {project_dir_path}")

    spec_path: Path | None = None
    if projectspec is not None:
        raw_spec = Path(projectspec)
        spec_path = raw_spec.resolve() if raw_spec.is_absolute() else (project_dir_path / raw_spec).resolve()

    raw_output = Path(outputdir)
    output_path = raw_output.resolve() if raw_output.is_absolute() else (project_dir_path / raw_output).resolve()
    if run_generators_for_flow and flow and run_generators_for_flow != flow:
        raise ValueError("flow and run_generators_for_flow must name the same flow")
    if generate and not (flow or run_generators_for_flow):
        raise ValueError("flow is required when generate is true")
    flow_name = flow or run_generators_for_flow or "info"
    should_generate = generate or run_generators_for_flow is not None
    if flow_name not in FlowFactory.get_flows():
        raise ValueError(f"Unknown flow '{flow_name}'")

    with reset_project_state(), chdir(project_dir_path):
        args = build_default_flow_namespace(
            flow_name=flow_name,
            projectspec=spec_path,
            outputdir=output_path,
            verbose=0,
        )
        simpl = Simplhdl(args)
        # New inspection requests use the same isolated location as `simpl info`.
        # Keep the older run_generators_for_flow path for compatibility.
        builddir = (
            output_path.joinpath("info", flow_name)
            if flow and not run_generators_for_flow
            else output_path.joinpath(flow_name)
        )
        project = simpl.create_project(builddir)

        if flow or run_generators_for_flow:
            flow_instance = FlowFactory.get_flow(flow_name, args, project, builddir)
            generators = list(GeneratorFactory.get_generators(args, project, builddir))
            # The legacy option generated files without filtering the result.
            project._inspection_flow = flow_instance if flow else None
            project._inspection_generators = generators
            project._inspection_generated = should_generate
            if should_generate:
                simpl.run_generators(flow_instance, generators)

        return project


def serialize_project_info(project: Project) -> dict[str, Any]:
    """Serialize a Project instance into a JSON-compatible dictionary."""
    design = project.defaultDesign
    libraries = []
    toplevels: list[str] = []
    default_lib: str | None = None

    if design is not None:
        default_lib = design.defaultLibrary.name if design.defaultLibrary else None
        toplevels = list(design.toplevels)
        for lib in design.libraries:
            libraries.append(
                {
                    "name": lib.name,
                    "external": bool(lib.external),
                    "path": str(lib.path),
                }
            )

    targets: dict[str, dict[str, Any]] = {}
    default_target_name: str | None = None
    if project.targets:
        default_target_name = project.defaultTarget.name
        for name, target in project.targets.items():
            target_args = vars(target.args) if target._args is not None else {}
            serializable_args = {
                k: str(v) if isinstance(v, Path) else v for k, v in target_args.items() if not callable(v)
            }
            targets[name] = {
                "name": name,
                "default": name == default_target_name,
                "cwd": str(target.cwd),
                "flow": serializable_args.get("flow"),
                "args": serializable_args,
            }

    return {
        "name": project.name,
        "part": project.part,
        "build_dir": str(project.buildDir) if project.buildDir else None,
        "default_library": default_lib,
        "toplevels": toplevels,
        "defines": dict(project.defines),
        "parameters": dict(project.parameters),
        "generics": dict(project.generics),
        "plusargs": dict(project.plusargs),
        "hooks": {k: list(v) for k, v in project.hooks.items()},
        "libraries": libraries,
        "targets": targets,
    }


def serialize_files(
    project: Project,
    order: str = "compile",
    usedin: str | None = None,
    file_type: str | None = None,
    library: str | None = None,
    fileset: str | None = None,
) -> list[dict[str, Any]]:
    """Return filtered project files in compile or hierarchy order."""
    design = project.defaultDesign
    if design is None:
        return []

    file_order = _resolve_order_files(order)
    all_files = design.files(order=file_order)
    selected = set(
        inspection_files(
            project,
            flow=getattr(project, "_inspection_flow", None),
            generators=getattr(project, "_inspection_generators", []),
            include_generator_inputs=not getattr(project, "_inspection_generated", False),
        )
    )

    results: list[dict[str, Any]] = []
    for file in all_files:
        if file not in selected:
            continue
        file_cls_name = file.__class__.__name__
        file_lib = getattr(file, "library", None)
        file_lib_name = file_lib.name if file_lib is not None else None
        parent_name = file.parent.name if file.parent is not None else None
        file_usedin = [str(u.value if hasattr(u, "value") else u) for u in file.usedin]

        if usedin is not None and usedin.lower() not in [u.lower() for u in file_usedin]:
            continue
        if file_type is not None and file_cls_name.lower() != file_type.lower():
            continue
        if library is not None and (file_lib_name is None or file_lib_name.lower() != library.lower()):
            continue
        if fileset is not None and (parent_name is None or parent_name != fileset):
            continue

        entry: dict[str, Any] = {
            "path": str(file.path),
            "type": file_cls_name,
            "library": file_lib_name,
            "fileset": parent_name,
            "usedin": file_usedin,
            "encrypt": bool(file.encrypt),
            "order": float(file.order),
            "generated": file.generated,
            "parent_file": str(file.parent_file.path) if file.parent_file else None,
            "selection_declared": _inspection_selection_declared(project),
        }
        if hasattr(file, "scope") and getattr(file, "scope") is not None:
            entry["scope"] = getattr(file, "scope")
        if hasattr(file, "includeDir"):
            entry["include_dir"] = str(getattr(file, "includeDir"))
        results.append(entry)

    return results


def _inspection_selection_declared(project: Project) -> bool:
    flow = getattr(project, "_inspection_flow", None)
    return flow is None or (
        flow.supported_file_types is not None
        and all(generator.supported_file_types is not None for generator in project._inspection_generators)
    )


def serialize_fileset_tree(project: Project, order: str = "compile") -> dict[str, Any]:
    """Serialize the fileset DAG and file memberships."""
    design = project.defaultDesign
    if design is None:
        return {"roots": [], "filesets": [], "selection_declared": _inspection_selection_declared(project)}

    design.validate()
    fileset_order = _resolve_order_filesets(order)
    ordered_filesets = cast(list[Fileset], design.filesets(order=fileset_order))

    filesets_data: list[dict[str, Any]] = []
    for fs in ordered_filesets:
        fs_lib = fs.library.name if fs.library is not None else None
        fs_files = [
            str(f.path)
            for f in inspection_files(
                project,
                flow=getattr(project, "_inspection_flow", None),
                generators=getattr(project, "_inspection_generators", []),
                fileset=fs,
                include_generator_inputs=not getattr(project, "_inspection_generated", False),
            )
        ]
        parents = [p.name for p in (fs.parents or [])]
        children = [c.name for c in fs.children]
        filesets_data.append(
            {
                "name": fs.name,
                "library": fs_lib,
                "parents": parents,
                "children": children,
                "files": fs_files,
            }
        )

    return {
        "roots": [r.name for r in design.roots],
        "filesets": filesets_data,
        "selection_declared": _inspection_selection_declared(project),
    }


def serialize_targets(project: Project) -> dict[str, Any]:
    """Serialize all targets registered in the project."""
    info = serialize_project_info(project)
    return {
        "default_target": next((name for name, t in info["targets"].items() if t["default"]), None),
        "targets": info["targets"],
    }


def _flow_category_name(flow_class: type[FlowBase]) -> str:
    if isinstance(flow_class, type):
        if issubclass(flow_class, SimulationFlow):
            return "simulation"
        if issubclass(flow_class, ImplementationFlow):
            return "implementation"
    return "default"


def serialize_flows() -> list[dict[str, Any]]:
    """Introspect all registered SimplHDL flows and their CLI options."""
    _, subparsers = _build_simpl_arg_parser()
    flows_map = cast(dict[str, type[FlowBase]], FlowFactory.get_flows())

    help_by_name: dict[str, str] = {}
    for choice_action in getattr(subparsers, "_choices_actions", []):
        help_by_name[choice_action.dest] = choice_action.help or ""

    results: list[dict[str, Any]] = []
    for name, flow_class in sorted(flows_map.items()):
        subparser = subparsers.choices.get(name)
        options: list[dict[str, Any]] = []
        steps: list[str] | None = None

        if subparser is not None:
            for action in subparser._actions:
                if action.dest == "help":
                    continue
                choices = list(action.choices) if action.choices is not None else None
                if action.dest == "step" and choices:
                    steps = [str(c) for c in choices]
                default_val = action.default
                if isinstance(default_val, Path):
                    default_val = str(default_val)
                options.append(
                    {
                        "flags": list(action.option_strings),
                        "dest": action.dest,
                        "choices": choices,
                        "default": default_val,
                        "help": action.help,
                    }
                )

        results.append(
            {
                "name": name,
                "class": flow_class.__name__,
                "module": flow_class.__module__,
                "category": _flow_category_name(flow_class),
                "help": help_by_name.get(name, ""),
                "steps": steps,
                "options": options,
            }
        )

    return results


def _get_parser_format_guide(parser_cls: type) -> str | None:
    """Return an explicit parser guide or its unambiguous distribution description."""
    guide = getattr(parser_cls, "format_guide", None)
    if isinstance(guide, str) and guide.strip():
        return guide

    package = parser_cls.__module__.partition(".")[0]
    distributions = metadata.packages_distributions().get(package, [])
    # Namespace packages can belong to multiple distributions; do not guess.
    if len(distributions) != 1 or distributions[0].lower().replace("_", "-") == "simplhdl":
        return None
    try:
        description = metadata.metadata(distributions[0]).get("Description")
    except metadata.PackageNotFoundError:
        return None
    return description if description and description.strip() else None


def serialize_plugins() -> dict[str, Any]:
    """
    Introspect all registered SimplHDL plugins (parsers, generators, flows, and file types),
    including third-party plugins discovered via entry points.
    """
    ensure_plugins_loaded()

    parsers: list[dict[str, Any]] = []
    for name, parser_cls, eff_prio in ParserFactory.get_ordered_parsers(include_wip=False):
        parsers.append(
            {
                "name": name,
                "class": parser_cls.__name__,
                "module": parser_cls.__module__,
                "priority": eff_prio,
                "format_id": getattr(parser_cls, "_format_id", None),
                "has_format_guide": bool(_get_parser_format_guide(parser_cls)),
            }
        )

    generators: list[dict[str, Any]] = []
    for name, gen_cls, priority in GeneratorFactory.get_ordered_generators():
        generators.append(
            {
                "name": name,
                "class": gen_cls.__name__,
                "module": gen_cls.__module__,
                "priority": priority,
            }
        )

    extensions_by_cls: dict[type[File], list[str]] = {}
    for ext, file_cls in FileFactory._registered_extensions.items():
        extensions_by_cls.setdefault(file_cls, []).append(ext)

    file_types: list[dict[str, Any]] = []
    for type_key, file_cls in sorted(FileFactory._registered_types.items()):
        file_types.append(
            {
                "type": type_key,
                "class": file_cls.__name__,
                "module": file_cls.__module__,
                "extensions": sorted(extensions_by_cls.get(file_cls, [])),
            }
        )

    return {
        "parsers": parsers,
        "generators": generators,
        "flows": serialize_flows(),
        "file_types": file_types,
    }


def get_active_parser_info() -> dict[str, Any]:
    """
    Return metadata and format guide for the highest-priority registered parser
    (ignoring work-in-progress parsers with `priority <= 0`).
    """
    ensure_plugins_loaded()
    ordered = ParserFactory.get_ordered_parsers(include_wip=False)
    if not ordered:
        return {
            "name": "none",
            "class": None,
            "module": None,
            "priority": 0,
            "format_id": None,
            "format_guide": "No active SimplHDL parser registered.",
        }

    top_name, top_cls, top_prio = ordered[0]
    guide = _get_parser_format_guide(top_cls)

    if not guide:
        # Fallback: include SimplHdlParser's guide if a 3rd-party parser did not define format_guide
        fallback_guide = ""
        for _, cls, _ in ordered:
            candidate = _get_parser_format_guide(cls)
            if candidate:
                fallback_guide = candidate
                break
        format_id_note = (
            f" (header/format ID: `{getattr(top_cls, '_format_id')}`)" if getattr(top_cls, "_format_id", None) else ""
        )
        guide = (
            f"# Active Project Parser: `{top_name}` (`{top_cls.__module__}.{top_cls.__name__}`){format_id_note}\n\n"
            f"Note: Third-party parser `{top_name}` (priority {top_prio}) has precedence over `#%SimplAPI=1.0`, "
            f"but does not bundle a custom `format_guide`.\n\n"
            f"---\n\n{fallback_guide}".strip()
        )

    return {
        "name": top_name,
        "class": top_cls.__name__,
        "module": top_cls.__module__,
        "priority": top_prio,
        "format_id": getattr(top_cls, "_format_id", None),
        "format_guide": guide,
    }


def get_skill_data(name: str = "project-spec") -> dict[str, Any]:
    """
    Return a SimplHDL skill/guide by name.

    Currently supported skills:
    - `project-spec`: Documentation for the highest-priority active project specification format
      (defaults to `#%SimplAPI=1.0` unless overridden by a third-party parser or `SIMPLHDL_CONFIG` / `SIMPLHDL_PARSER`).
    """
    normalized = name.strip().lower()
    if normalized in {"project-spec", "simplapi", "parser"}:
        active = get_active_parser_info()
        return {
            "skill": "project-spec",
            "uri": "simplhdl://skills/project-spec",
            "active_parser": active["name"],
            "parser_class": active["class"],
            "priority": active["priority"],
            "format_id": active["format_id"],
            "content": active["format_guide"],
        }

    raise ValueError(f"Unknown skill '{name}'. Available skills: ['project-spec']")


def build_server_instructions() -> str:
    """Build concise MCP server instructions injected during client initialization."""
    active = get_active_parser_info()
    fmt = f" (format ID: `{active['format_id']}`)" if active["format_id"] else ""
    return (
        "SimplHDL MCP Server instructions:\n"
        f"- Active project specification parser: `{active['name']}` (`{active['class']}`, priority {active['priority']}){fmt}.\n"
        "- Before creating or editing project specification files, read resource `simplhdl://skills/project-spec` "
        "or call `get_skill('project-spec')`.\n"
        "- Before running a simulation or build flow, call `list_targets` or `get_project_info` to check for defined targets.\n"
        "- Prefer `step='compile'` or `step='elaborate'` via `run_flow` for fast verification before full simulation or synthesis.\n"
        "- On flow failure, inspect logs with `read_flow_log`."
    )


def register_external_mcp_extensions(mcp: Any) -> list[str]:
    """
    Allow third-party plugins to register additional MCP tools/resources on `mcp`:
    1. Any registered ParserBase, GeneratorBase, or FlowBase subclass defining a
       `register_mcp_tools(mcp)` classmethod/staticmethod.
    2. Any entry point registered under the `simplhdl.mcp` entry-point group.
    """
    ensure_plugins_loaded()
    logger = logging.getLogger(__name__)
    loaded_extensions: list[str] = []

    plugin_registries: list[dict[str, Any]] = [
        ParserFactory.registry,
        GeneratorFactory.registry,
        FlowFactory.get_flows(),
    ]
    seen_classes: set[Any] = set()
    for registry in plugin_registries:
        for name, plugin_cls in registry.items():
            if plugin_cls in seen_classes:
                continue
            seen_classes.add(plugin_cls)
            hook = getattr(plugin_cls, "register_mcp_tools", None)
            if callable(hook):
                try:
                    hook(mcp)
                    loaded_extensions.append(f"{plugin_cls.__module__}.{plugin_cls.__name__}")
                except Exception as exc:
                    logger.error(f"Failed to run register_mcp_tools on plugin '{name}': {exc}")

    for ep in get_external_plugins("simplhdl.mcp"):
        try:
            register_fn = ep.load()
            register_fn(mcp)
            loaded_extensions.append(ep.name)
        except Exception as exc:
            logger.error(f"Failed to load MCP extension '{ep.name}': {exc}")

    return loaded_extensions


def build_flow_cli_args(
    flow: str,
    projectspec: str | Path | None = None,
    outputdir: str | Path = "_build",
    step: str | None = None,
    extra_args: list[str] | str | None = None,
    verbose: int = 0,
    allow_gui: bool = False,
) -> list[str]:
    """Construct validated CLI arguments for running `python -m simplhdl`."""
    ensure_plugins_loaded()
    flows = FlowFactory.get_flows()
    if flow not in flows:
        available = ", ".join(sorted(flows.keys()))
        raise ValueError(f"Unknown flow '{flow}'. Available flows: {available}")

    parsed_extra: list[str] = []
    if isinstance(extra_args, str):
        parsed_extra = shlex.split(extra_args)
    elif extra_args is not None:
        parsed_extra = [str(a) for a in extra_args]

    if not allow_gui:
        for arg in parsed_extra:
            if arg == "--gui" or arg.startswith("--gui="):
                raise ValueError(
                    "Interactive '--gui' flag is disabled by default in MCP server mode to prevent hanging. "
                    "Pass allow_gui=True if GUI launch is intentional."
                )

    cli_args: list[str] = []
    if verbose > 0:
        cli_args.append("-" + "v" * min(verbose, 3))
    if outputdir:
        cli_args.extend(["-o", str(outputdir)])
    if projectspec is not None:
        cli_args.extend(["--projectspec", str(projectspec)])

    cli_args.append(flow)
    if step:
        cli_args.extend(["--step", step])
    cli_args.extend(parsed_extra)
    return cli_args


async def run_simpl_cli(
    cli_args: list[str],
    cwd: str | Path = ".",
    timeout: int = 600,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run `python -m simplhdl` in an isolated async subprocess and capture output."""
    cwd_path = Path(cwd).resolve()
    if not cwd_path.is_dir():
        raise FileNotFoundError(f"Working directory does not exist: {cwd_path}")

    cmd = [sys.executable, "-m", "simplhdl", *cli_args]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    timed_out = False
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        timed_out = True
        proc.kill()
        stdout_bytes, stderr_bytes = await proc.communicate()

    return {
        "returncode": -1 if timed_out else (proc.returncode or 0),
        "timed_out": timed_out,
        "command": cmd,
        "cwd": str(cwd_path),
        "stdout": stdout_bytes.decode(errors="replace").strip(),
        "stderr": stderr_bytes.decode(errors="replace").strip(),
    }


def read_log_file(
    flow: str,
    project_dir: str | Path = ".",
    outputdir: str | Path = "_build",
    tail_lines: int = 200,
) -> dict[str, Any]:
    """Read the tail of `<outputdir>/<flow>/simplhdl.log` and any flow-specific log files."""
    project_dir_path = Path(project_dir).resolve()
    raw_output = Path(outputdir)
    output_path = raw_output.resolve() if raw_output.is_absolute() else (project_dir_path / raw_output).resolve()
    flow_dir = output_path / flow

    if not flow_dir.is_dir():
        raise FileNotFoundError(f"Flow build directory does not exist: {flow_dir}")

    logs: dict[str, str] = {}
    for log_path in sorted(flow_dir.glob("*.log")):
        lines = log_path.read_text(errors="replace").splitlines()
        if tail_lines > 0 and len(lines) > tail_lines:
            lines = lines[-tail_lines:]
        logs[log_path.name] = "\n".join(lines)

    return {
        "flow": flow,
        "build_dir": str(flow_dir),
        "logs": logs,
    }
