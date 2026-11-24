from __future__ import annotations

import os
import subprocess
import sys
from argparse import Namespace

import pytest

from simplhdl.plugin.flow import FlowCategory, FlowTools
from simplhdl.plugin.generator import GeneratorBase, GeneratorFactory
from simplhdl.project.files import (
    File,
    FileFactory,
    Jinja2File,
    QuartusIpFile,
    QuartusQsfFile,
    SystemVerilogFile,
    UnknownFile,
    UsedIn,
    VivadoXdcFile,
    VivadoXciFile,
)
from simplhdl.project.fileset import FileOrder
from simplhdl_jinja2.jinja2 import Jinja2Generator
from simplhdl_quartus.spd import QuartusGenerator
from simplhdl_quartus.quartusflow import QuartusFlow
from simplhdl_vivado.vivadoflow import VivadoFlow
from simplhdl_vivado.ipxact import VivadoGenerator


def test_replace_file_preserves_graph_and_attributes(fileset, design, tmp_path):
    first = File(tmp_path / "first.v")
    source = Jinja2File(tmp_path / "second.sv.j2", usedin=[UsedIn.SIMULATION], order=25, encrypt=True)
    last = File(tmp_path / "last.v")
    for file in (first, source, last):
        fileset.add_file(file)
    generated = SystemVerilogFile(tmp_path / "second.sv")
    fileset.replace_file(source, generated)

    assert fileset.files(order=FileOrder.COMPILE) == [first, generated, last]
    assert source not in design._files
    assert generated.parent is fileset
    assert generated.generated and generated.parent_file is source
    assert generated.usedin == [UsedIn.SIMULATION]
    assert generated.order == 25 and generated.encrypt is True
    design.validate()


def test_replace_rejects_existing_file(fileset, tmp_path):
    first = File(tmp_path / "one.v")
    second = File(tmp_path / "two.v")
    fileset.add_file(first)
    fileset.add_file(second)
    with pytest.raises(ValueError, match="already in the project"):
        fileset.replace_file(first, second)


def test_generator_selection_and_templating(fileset, project, tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_HDL_MODULE", "my_module")
    path = tmp_path / "top.sv.j2"
    path.write_text("module {{ os.environ['TEST_HDL_MODULE'] }}; endmodule\n")
    source = Jinja2File(path, usedin=[UsedIn.SIMULATION])
    fileset.add_file(source)
    flow = Namespace(category=FlowCategory.SIMULATION)
    gen = Jinja2Generator("jinja2", Namespace(), project, tmp_path / "out")
    assert gen.get_files(flow) == [source]
    assert gen.get_files(Namespace(category=FlowCategory.IMPLEMENTATION)) == []
    gen.run(flow)
    generated = fileset.files()[0]
    assert isinstance(generated, SystemVerilogFile)
    assert generated.parent_file is source and generated.generated
    assert generated.path.read_text() == "module my_module; endmodule"


def test_generator_priority_overrides(monkeypatch, tmp_path):
    class Early(GeneratorBase):
        priority = 100

        def run(self, flow):
            pass

    class Normal(GeneratorBase):
        def run(self, flow):
            pass

    monkeypatch.setattr(GeneratorFactory, "registry", {"normal": Normal, "early": Early})
    monkeypatch.delenv("SIMPLHDL_CONFIG", raising=False)
    monkeypatch.delenv("SIMPLHDL_GENERATORS", raising=False)
    assert [name for name, _, _ in GeneratorFactory.get_ordered_generators()] == ["early", "normal"]
    config = tmp_path / "config.toml"
    config.write_text('[generator]\npriority = ["normal", "early"]\n')
    monkeypatch.setenv("SIMPLHDL_CONFIG", str(config))
    assert [name for name, _, _ in GeneratorFactory.get_ordered_generators()] == ["normal", "early"]
    monkeypatch.setenv("SIMPLHDL_GENERATORS", "early")
    assert [name for name, _, _ in GeneratorFactory.get_ordered_generators()] == ["early", "normal"]


def test_quartus_copy_retains_source_provenance(fileset, project, tmp_path):
    source_path = tmp_path / "core.ip"
    source_path.write_text("ip contents")
    original = QuartusIpFile(source_path)
    fileset.add_file(original)
    generator = QuartusGenerator("quartus_generator", Namespace(), project, tmp_path / "build")
    flow = Namespace(category=FlowCategory.IMPLEMENTATION, tools={FlowTools.QUARTUS})
    generator.run(flow)
    assert original.generated
    assert original.parent_file.path == source_path
    assert original.path == tmp_path / "build" / "ips" / "core.ip"


def test_vivado_ip_expansion_retains_source_provenance(fileset, project, tmp_path, monkeypatch):
    from simplhdl.project.attributes import Library

    library = Library("work")
    project.defaultDesign.defaultLibrary = library
    source = VivadoXciFile(tmp_path / "core.xci")
    fileset.add_file(source)
    generated = SystemVerilogFile(tmp_path / "ip_core.sv", library=library)
    generator = VivadoGenerator("vivado_generator", Namespace(), project, tmp_path / "build")
    seen = []

    def component_files(path):
        seen.append(path)
        return [generated]

    monkeypatch.setattr(generator, "get_component_files", component_files)
    generator.run(Namespace(category=FlowCategory.SIMULATION))
    assert seen == [tmp_path / "core.xml"]
    assert generated.generated and generated.parent_file is source
    assert generated in project.defaultDesign.files()


def test_implementation_templates_consume_selected_files(fileset, project, tmp_path, monkeypatch):
    project.defaultDesign.toplevels = ["top"]
    from simplhdl.project.attributes import Library

    project.defaultDesign.defaultLibrary = Library("work")
    source = SystemVerilogFile(tmp_path / "top.sv")
    xdc = VivadoXdcFile(tmp_path / "timing.xdc")
    qsf = QuartusQsfFile(tmp_path / "settings.qsf")
    unknown = FileFactory.create(tmp_path / "config.pfg")
    sim_only = FileFactory.create(tmp_path / "sim.pfg", usedin=[UsedIn.SIMULATION])
    assert isinstance(unknown, UnknownFile)
    for file in (source, xdc, qsf, unknown, sim_only):
        fileset.add_file(file)

    monkeypatch.setattr("simplhdl_vivado.vivadoflow.sh", lambda *args, **kwargs: "")
    vivado = VivadoFlow("vivado", Namespace(), project, tmp_path / "vivado")
    vivado.generate()
    vivado_tcl = (tmp_path / "vivado" / "project.tcl").read_text()
    assert str(source.path) in vivado_tcl and str(xdc.path) in vivado_tcl
    assert str(qsf.path) not in vivado_tcl
    assert unknown in vivado.get_files() and sim_only not in vivado.get_files()
    assert f'add_files -fileset utils_1 "{unknown.path}"' in vivado_tcl
    assert str(sim_only.path) not in vivado_tcl

    monkeypatch.setattr("simplhdl_quartus.quartusflow.sh", lambda *args, **kwargs: "")
    monkeypatch.setattr(QuartusFlow, "is_tool_setup", lambda self: None)
    quartus = QuartusFlow("quartus", Namespace(), project, tmp_path / "quartus")
    quartus.generate()
    quartus_tcl = (tmp_path / "quartus" / "project.tcl").read_text()
    assert str(source.path) in quartus_tcl and str(qsf.path) in quartus_tcl
    assert str(xdc.path) not in quartus_tcl
    assert unknown in quartus.get_files() and sim_only not in quartus.get_files()
    assert f'set_global_assignment -name SOURCE_FILE "{unknown.path}"' in quartus_tcl
    assert f'set_global_assignment -name SEARCH_PATH "{unknown.path.parent}"' in quartus_tcl
    assert str(sim_only.path) not in quartus_tcl


@pytest.mark.parametrize("flow", ["quartus", "vivado"])
def test_info_flow_lists_unknown_files(tmp_path, monkeypatch, flow):
    monkeypatch.delenv("SIMPLHDL_CONFIG", raising=False)
    (tmp_path / "project.yml").write_text("#%SimplAPI=1.0\nfiles:\n  - config.pfg\n")
    (tmp_path / "config.pfg").write_text("")
    result = subprocess.run(
        [sys.executable, "-m", "simplhdl", "-o", str(tmp_path / "build"), "info", "--flow", flow, "--files"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert str(tmp_path / "config.pfg") in result.stdout


def test_info_flow_generation(tmp_path, monkeypatch):
    monkeypatch.delenv("SIMPLHDL_CONFIG", raising=False)
    monkeypatch.delenv("SIMPLHDL_GENERATORS", raising=False)
    (tmp_path / "project.yml").write_text(
        "#%SimplAPI=1.0\nproject: example\ntop: top\nfiles:\n  - top.sv.j2\n  - timing.xdc\n  - quartus.qsf\n"
    )
    (tmp_path / "top.sv.j2").write_text("module top; endmodule\n")
    (tmp_path / "timing.xdc").write_text("")
    (tmp_path / "quartus.qsf").write_text("")
    cmd = [sys.executable, "-m", "simplhdl", "-o", str(tmp_path / "build"), "info", "--flow", "icarus", "--files"]
    first = subprocess.run(cmd, cwd=tmp_path, env=os.environ.copy(), capture_output=True, text=True, check=True)
    assert "top.sv.j2" in first.stdout
    assert "timing.xdc" not in first.stdout and "quartus.qsf" not in first.stdout
    assert not list((tmp_path / "build").rglob("top.sv"))

    second = subprocess.run(
        cmd + ["--generate"], cwd=tmp_path, env=os.environ.copy(), capture_output=True, text=True, check=True
    )
    assert "top.sv" in second.stdout and "(generated)" in second.stdout
    assert (tmp_path / "build" / "info" / "icarus" / "jinja2" / "top.sv").is_file()


def test_info_flow_with_no_matching_files(tmp_path, monkeypatch):
    monkeypatch.delenv("SIMPLHDL_CONFIG", raising=False)
    (tmp_path / "project.yml").write_text("#%SimplAPI=1.0\nfiles:\n  - timing.xdc\n")
    (tmp_path / "timing.xdc").write_text("")
    result = subprocess.run(
        [sys.executable, "-m", "simplhdl", "-o", str(tmp_path / "build"), "info", "--flow", "icarus", "--files"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "timing.xdc" not in result.stdout
