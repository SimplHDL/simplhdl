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
