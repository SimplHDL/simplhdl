from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import sys
from types import SimpleNamespace
from weakref import WeakValueDictionary

import pytest

from simplhdl.plugin import FlowBase, GeneratorBase, ParserBase
from simplhdl.plugin.flow import FlowFactory
from simplhdl.plugin.generator import GeneratorFactory
from simplhdl.plugin.parser import ParserFactory
from simplhdl.project.files import File, FileFactory, SystemVerilogFile
from simplhdl.project.fileset import Fileset
from simplhdl_mcp.context import build_flow_cli_args, load_project, reset_project_state
from simplhdl_mcp.server import (
    create_server,
    get_fileset_tree,
    get_project_info,
    list_files,
    list_flows,
    list_plugins,
    list_targets,
    main,
    parse_mcp_args,
    read_flow_log,
    run_flow,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ALU_SYN_DIR = REPO_ROOT / "examples" / "hdl" / "alu" / "syn"
ALU_UVM_DIR = REPO_ROOT / "examples" / "hdl" / "alu" / "sim" / "uvm" / "testcases" / "test_add"


def test_get_project_info_and_state_isolation():
    info_syn = get_project_info(project_dir=str(ALU_SYN_DIR))
    assert info_syn["name"] == "alu"
    assert info_syn["part"] == "xc7z007sclg225-2"
    assert info_syn["toplevels"] == ["alu"]
    assert info_syn["default_library"] == "work"
    assert info_syn["plusargs"] == {}

    # Second call on a different project in the same process must not leak state from the first
    info_sim = get_project_info(project_dir=str(ALU_UVM_DIR))
    assert info_sim["name"] == "default"
    assert info_sim["part"] is None
    assert info_sim["toplevels"] == ["testbench"]
    assert info_sim["plusargs"] == {"UVM_TESTNAME": "tb_env::test_add"}


def test_list_files_orders_and_filters():
    compile_files = list_files(project_dir=str(ALU_SYN_DIR), order="compile")
    hierarchy_files = list_files(project_dir=str(ALU_SYN_DIR), order="hierarchy")

    compile_names = [Path(f["path"]).name for f in compile_files]
    hierarchy_names = [Path(f["path"]).name for f in hierarchy_files]
    assert compile_names == list(reversed(hierarchy_names))
    assert "add.sv" in compile_names
    assert "alu.sv" in compile_names
    assert "timing.xdc" in compile_names
    assert compile_names.index("add.sv") < compile_names.index("alu.sv")

    xdc_files = list_files(
        project_dir=str(ALU_SYN_DIR),
        file_type="VivadoXdcFile",
        usedin="implementation",
    )
    assert [Path(f["path"]).name for f in xdc_files] == ["timing.xdc", "placement.xdc"]

    sim_xdc_files = list_files(
        project_dir=str(ALU_SYN_DIR),
        file_type="VivadoXdcFile",
        usedin="simulation",
    )
    assert sim_xdc_files == []

    work_sv_files = list_files(
        project_dir=str(ALU_SYN_DIR),
        file_type="SystemVerilogFile",
        library="work",
    )
    assert len(work_sv_files) == 4


def test_get_fileset_tree():
    tree = get_fileset_tree(project_dir=str(ALU_SYN_DIR), order="compile")
    assert len(tree["roots"]) == 1
    assert len(tree["filesets"]) == 3
    fileset_names = [Path(fs["name"]).name for fs in tree["filesets"]]
    assert fileset_names == ["add.yml", "alu.yml", "build.yml"]


def test_list_targets(tmp_path):
    (tmp_path / "top.sv").write_text("module top; endmodule\n")
    spec = tmp_path / "project.yml"
    spec.write_text(
        "#%SimplAPI=1.0\n"
        "project: demo\n"
        "top: top\n"
        "targets:\n"
        "  sim: questasim --step compile\n"
        "  synth: vivado --step synthesis\n"
        "files:\n"
        "  - top.sv\n"
    )

    targets_data = list_targets(project_dir=str(tmp_path))
    assert targets_data["default_target"] == "sim"
    assert set(targets_data["targets"].keys()) == {"sim", "synth"}
    assert targets_data["targets"]["sim"]["flow"] == "questasim"
    assert targets_data["targets"]["synth"]["flow"] == "vivado"


def test_list_flows_and_plugins():
    flows = list_flows()
    flow_by_name = {f["name"]: f for f in flows}
    assert "questasim" in flow_by_name
    assert "vivado" in flow_by_name
    assert "quartus" in flow_by_name
    assert "lint" in flow_by_name
    assert "info" in flow_by_name
    assert "run" in flow_by_name

    assert flow_by_name["questasim"]["category"] == "simulation"
    assert "simulate" in (flow_by_name["questasim"]["steps"] or [])
    assert flow_by_name["quartus"]["category"] == "implementation"
    assert "compile" in (flow_by_name["quartus"]["steps"] or [])
    assert "bitstream" in (flow_by_name["vivado"]["steps"] or [])

    plugins = list_plugins()
    parser_names = {p["name"] for p in plugins["parsers"]}
    generator_names = {g["name"] for g in plugins["generators"]}
    file_types = {ft["class"] for ft in plugins["file_types"]}
    assert "simplhdl_parser" in parser_names
    assert "peakrdl_generator" in generator_names
    assert "SystemVerilogFile" in file_types


def test_third_party_plugins_and_custom_file_subclass(tmp_path, monkeypatch):
    class CustomThirdPartyFile(File):
        _cache: WeakValueDictionary = WeakValueDictionary()

    class CustomThirdPartyParser(ParserBase):
        _format_id = "#%Custom3P=1.0"

        def is_valid_format(self, filename: Path | None) -> bool:
            target = filename or (Path(".") / "custom.3p")
            return target.is_file() and target.read_text().startswith(self._format_id)

        def parse(self, filename, project, args):
            # Verify flow CLI defaults from CustomThirdPartyFlow.parse_args are populated on `args`
            project.name = f"3p_{getattr(args, 'custom_opt', 'missing')}"
            project.defaultDesign.add_toplevel("custom_top")
            fs = Fileset("custom_fs")
            fs.add_file(CustomThirdPartyFile(Path("design.3p_hdl").resolve()))
            return fs

    class CustomThirdPartyGenerator(GeneratorBase):
        def run(self, flow):
            gen_file = self.builddir / "generated_by_3p.sv"
            gen_file.parent.mkdir(parents=True, exist_ok=True)
            gen_file.write_text("module generated_by_3p; endmodule\n")
            root_fs = self.project.defaultDesign.roots[0]
            root_fs.add_file(SystemVerilogFile(gen_file))

    class CustomThirdPartyFlow(FlowBase):
        @classmethod
        def parse_args(cls, subparsers) -> None:
            parser = subparsers.add_parser("custom3p", help="Custom 3rd party flow")
            parser.add_argument("--custom-opt", default="default_val", help="Custom option")

        def run(self) -> None:
            pass

    monkeypatch.setitem(ParserFactory.registry, "custom3p_parser", CustomThirdPartyParser)
    monkeypatch.setitem(GeneratorFactory.registry, "custom3p_gen", CustomThirdPartyGenerator)
    monkeypatch.setitem(FlowFactory.registry, "custom3p", CustomThirdPartyFlow)
    monkeypatch.setitem(FileFactory._registered_types, "customthirdpartyfile", CustomThirdPartyFile)
    monkeypatch.setitem(FileFactory._registered_extensions, ".3p_hdl", CustomThirdPartyFile)

    (tmp_path / "design.3p_hdl").write_text("// custom hdl\n")
    (tmp_path / "custom.3p").write_text("#%Custom3P=1.0\n")

    files = list_files(
        project_dir=str(tmp_path),
        projectspec="custom.3p",
        run_generators_for_flow="custom3p",
    )
    file_types = [f["type"] for f in files]
    assert "CustomThirdPartyFile" in file_types
    assert "SystemVerilogFile" in file_types

    project = load_project(
        project_dir=tmp_path,
        projectspec="custom.3p",
        run_generators_for_flow="custom3p",
    )
    assert project.name == "3p_default_val"

    # Verify reset_project_state clears subclass-specific _cache on CustomThirdPartyFile
    assert len(CustomThirdPartyFile._cache) > 0
    with reset_project_state():
        assert len(CustomThirdPartyFile._cache) == 0


def test_build_flow_cli_args_validation():
    args = build_flow_cli_args(
        flow="questasim",
        projectspec="sim.yml",
        outputdir="_build",
        step="compile",
        extra_args="--seed 42",
        verbose=2,
    )
    assert args == [
        "-vv",
        "-o",
        "_build",
        "--projectspec",
        "sim.yml",
        "questasim",
        "--step",
        "compile",
        "--seed",
        "42",
    ]

    with pytest.raises(ValueError, match="Unknown flow"):
        build_flow_cli_args(flow="nonexistent_flow")

    with pytest.raises(ValueError, match="--gui"):
        build_flow_cli_args(flow="questasim", extra_args=["--gui"])

    gui_allowed = build_flow_cli_args(flow="questasim", extra_args=["--gui"], allow_gui=True)
    assert "--gui" in gui_allowed


def test_load_project_with_generators_and_no_logger_leak(tmp_path):
    root_logger = logging.getLogger()
    handlers_before = list(root_logger.handlers)

    (tmp_path / "top.sv").write_text("module top; endmodule\n")
    (tmp_path / "project.yml").write_text(
        "#%SimplAPI=1.0\n" "project: gen_test\n" "top: top\n" "files:\n" "  - top.sv\n"
    )

    project = load_project(
        project_dir=tmp_path,
        outputdir=tmp_path / "_build",
        run_generators_for_flow="info",
    )
    assert project.name == "gen_test"
    assert list(root_logger.handlers) == handlers_before


def test_run_flow_and_read_flow_log(tmp_path):
    (tmp_path / "top.sv").write_text("module top; endmodule\n")
    (tmp_path / "project.yml").write_text("#%SimplAPI=1.0\n" "project: log_test\n" "top: top\n" "files:\n" "  - top.sv\n")

    result = asyncio.run(
        run_flow(
            flow="info",
            project_dir=str(tmp_path),
            outputdir="_build",
            extra_args=["--libraries"],
        )
    )
    assert result["returncode"] == 0
    assert "work" in result["stdout"]
    assert result["log_file"] is not None

    log_data = read_flow_log(flow="info", project_dir=str(tmp_path), outputdir="_build")
    assert log_data["flow"] == "info"
    assert "simplhdl.log" in log_data["logs"]


def test_mcp_server_creation_and_third_party_extensions(monkeypatch):
    args = parse_mcp_args(["--transport", "sse"])
    assert args.transport == "sse"

    registered_tools: list[str] = []

    class FakeFastMCP:
        def __init__(self, name: str):
            self.name = name
            self.ran_transport: str | None = None

        def tool(self):
            def decorator(fn):
                registered_tools.append(fn.__name__)
                return fn

            return decorator

        def run(self, transport: str = "stdio"):
            self.ran_transport = transport

    class HookFlow(FlowBase):
        @classmethod
        def parse_args(cls, subparsers) -> None:
            subparsers.add_parser("hook_flow")

        @classmethod
        def register_mcp_tools(cls, mcp) -> None:
            def custom_flow_tool() -> str:
                return "ok"

            mcp.tool()(custom_flow_tool)

        def run(self) -> None:
            pass

    class FakeEntryPoint:
        name = "ext_ep"

        def load(self):
            def register_ep(mcp):
                def custom_ep_tool() -> str:
                    return "ep"

                mcp.tool()(custom_ep_tool)

            return register_ep

    monkeypatch.setitem(FlowFactory.registry, "hook_flow", HookFlow)
    monkeypatch.setattr(
        "simplhdl_mcp.context.get_external_plugins",
        lambda group: [FakeEntryPoint()] if group == "simplhdl.mcp" else [],
    )

    fake_fastmcp_mod = SimpleNamespace(FastMCP=FakeFastMCP)
    monkeypatch.setitem(sys.modules, "mcp", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mcp.server", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fake_fastmcp_mod)

    server = create_server()
    assert server.name == "simplhdl"
    assert set(registered_tools) == {
        "get_project_info",
        "list_files",
        "get_fileset_tree",
        "list_targets",
        "list_flows",
        "list_plugins",
        "run_flow",
        "run_target",
        "run_lint",
        "read_flow_log",
        "custom_flow_tool",
        "custom_ep_tool",
    }

    rc = main(["--transport", "stdio"])
    assert rc == 0
