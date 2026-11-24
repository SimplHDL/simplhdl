from __future__ import annotations

from types import MethodType, SimpleNamespace
from unittest.mock import Mock

import pytest

from simplhdl.project.files import SystemRdlFile
from simplhdl_peakrdl import systemrdl


def test_regblock_configuration_helpers():
    assert systemrdl._get_default_reset_settings("rst") == (False, False)
    assert systemrdl._get_default_reset_settings("rst_n") == (True, False)
    assert systemrdl._get_default_reset_settings("arst") == (False, True)
    assert systemrdl._get_default_reset_settings("arst_n") == (True, True)
    with pytest.raises(ValueError, match="Unsupported default reset"):
        systemrdl._get_default_reset_settings("invalid")

    assert systemrdl._get_retime_external_settings([]) == {
        "retime_external_reg": False,
        "retime_external_regfile": False,
        "retime_external_mem": False,
        "retime_external_addrmap": False,
    }
    assert systemrdl._get_retime_external_settings(["reg", "mem"]) == {
        "retime_external_reg": True,
        "retime_external_regfile": False,
        "retime_external_mem": True,
        "retime_external_addrmap": False,
    }
    assert all(systemrdl._get_retime_external_settings(["all"]).values())
    with pytest.raises(ValueError, match="Unsupported retime_external item"):
        systemrdl._get_retime_external_settings(["invalid"])
    with pytest.raises(TypeError, match="retime_external must be an array"):
        systemrdl._get_retime_external_settings("reg")


def test_hierarchy_templates_use_top_maps_and_regblocks_use_unique_leaves(tmp_path, monkeypatch):
    source = tmp_path / "maps.rdl"
    source.write_text(
        "addrmap shared_leaf { reg { field { sw = rw; } value[31:0]; } control; };\n"
        "addrmap first_root { shared_leaf first; };\n"
        "addrmap second_root { shared_leaf second; };\n"
    )
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "hierachymap.sv.j2").write_text(
        '{{ node.type_name }}:{{ leafnodes | map(attribute="inst_name") | join(",") }}'
    )
    monkeypatch.setenv("SIMPLHDL_SYSTEMRDL_TEMPLATES", str(templates))
    monkeypatch.delenv("SIMPLHDL_CONFIG", raising=False)
    monkeypatch.setattr(systemrdl, "HTMLExporter", Mock())

    rdlfile = SimpleNamespace(path=str(source), parent=Mock())
    design = Mock()
    design.files.side_effect = lambda type, **kwargs: [rdlfile] if type is SystemRdlFile else []
    design.get_file.return_value = rdlfile
    generator = SimpleNamespace(
        project=SimpleNamespace(defaultDesign=design, defines={}),
        builddir=tmp_path / "build",
        peakrdl_regblock=Mock(),
    )
    for method_name in (
        "_load_config",
        "_compile_roots",
        "_collect_root_nodes",
        "_generate_hierarchy_templates",
        "_generate_regblocks",
        "_generate_pyuvm",
        "_generate_html",
    ):
        method = getattr(systemrdl.PeakRdlGenerator, method_name)
        setattr(generator, method_name, MethodType(method, generator))
    generator.render_template = lambda **kwargs: systemrdl.PeakRdlGenerator.render_template(generator, **kwargs)

    systemrdl.PeakRdlGenerator.run(generator, SimpleNamespace(category=systemrdl.FlowCategory.SIMULATION))

    output = generator.builddir / "systemrdl" / "templates"
    assert (output / "first_root__hierachymap.sv").read_text() == "first_root:first"
    assert (output / "second_root__hierachymap.sv").read_text() == "second_root:second"
    assert design.get_file.call_count == 2
    for call in design.get_file.call_args_list:
        assert call.args[0] == str(source)
    generator.peakrdl_regblock.assert_called_once()
    assert generator.peakrdl_regblock.call_args.kwargs["node"].type_name == "shared_leaf"


def test_peakrdl_regblock_names_hwif_after_type_and_restores_instance_name(tmp_path):
    source = tmp_path / "maps.rdl"
    source.write_text(
        "addrmap my_sub { reg { field { sw = rw; hw = rw; } value[31:0]; } control; };\naddrmap top { my_sub sub; };\n"
    )
    rdlc = systemrdl.SimplHDLRDLCompiler()
    for udp in systemrdl.ALL_UDPS:
        rdlc.register_udp(udp)
    rdlc.compile_file(str(source))
    root = rdlc.elaborate("top")
    node = next(iter(root.top.children()))
    assert node.inst_name == "sub"

    rdlfile = SimpleNamespace(path=str(source), parent=Mock())
    design = Mock()
    design.get_file.return_value = rdlfile
    generator = SimpleNamespace(project=SimpleNamespace(defaultDesign=design))
    outputdir = tmp_path / "regblock"

    systemrdl.PeakRdlGenerator.peakrdl_regblock(generator, node=node, outputdir=outputdir, config={})

    # Workaround for SystemRDL/PeakRDL-regblock#221: HWIF typedefs must use the
    # addrmap type name, and the elaborated tree must not be mutated afterwards.
    package = (outputdir / "my_sub_pkg.sv").read_text()
    assert "} my_sub__in_t;" in package
    assert "} my_sub__out_t;" in package
    assert "} sub__in_t;" not in package
    module = (outputdir / "my_sub.sv").read_text()
    assert "my_sub_pkg::my_sub__in_t" in module
    assert "my_sub_pkg::my_sub__out_t" in module
    assert node.inst_name == "sub"
    assert node.get_path() == "top.sub"
