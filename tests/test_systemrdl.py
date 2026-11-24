from __future__ import annotations

from types import MethodType, SimpleNamespace
from unittest.mock import Mock

import pytest
from jinja2 import Environment, FileSystemLoader

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
    (templates / "hierachymap_pkg.sv.j2").write_text(
        '{{ output_stem }}:{{ node.type_name }}:{{ leafnodes | map(attribute="inst_name") | join(",") }}'
    )
    (templates / "interconnect.sv.j2").write_text("{{ output_stem }}:{{ node.type_name }}")
    (templates / "nested").mkdir()
    (templates / "nested" / "notes.txt.j2").write_text("{{ node.type_name }}")
    (templates / "ignored.sv.j2.disable").write_text("This should not be rendered")
    (templates / "ignored.txt").write_text("This should not be rendered")
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
        get_files=lambda flow: [rdlfile],
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
    assert (output / "first_root_hierachymap_pkg.sv").read_text() == "first_root_hierachymap_pkg:first_root:first"
    assert (output / "second_root_hierachymap_pkg.sv").read_text() == "second_root_hierachymap_pkg:second_root:second"
    assert (output / "first_root_interconnect.sv").read_text() == "first_root_interconnect:first_root"
    assert (output / "second_root_interconnect.sv").read_text() == "second_root_interconnect:second_root"
    assert (output / "first_root_notes.txt").read_text() == "first_root"
    assert (output / "second_root_notes.txt").read_text() == "second_root"
    assert sorted(p.name for p in output.iterdir()) == [
        "first_root_hierachymap_pkg.sv",
        "first_root_interconnect.sv",
        "first_root_notes.txt",
        "second_root_hierachymap_pkg.sv",
        "second_root_interconnect.sv",
        "second_root_notes.txt",
    ]
    assert design.get_file.call_count == 6
    assert rdlfile.parent.insert_file_after.call_count == 4
    assert [call.args[1].path.name for call in rdlfile.parent.insert_file_after.call_args_list] == [
        "first_root_hierachymap_pkg.sv",
        "first_root_interconnect.sv",
        "second_root_hierachymap_pkg.sv",
        "second_root_interconnect.sv",
    ]
    for call in design.get_file.call_args_list:
        assert call.args[0] == str(source)
    generator.peakrdl_regblock.assert_called_once()
    assert generator.peakrdl_regblock.call_args.kwargs["node"].type_name == "shared_leaf"


@pytest.mark.parametrize(
    ("template_name", "basename", "output_name", "output_stem"),
    [
        ("interconnect.sv.j2", "interconnect", "chip_interconnect.sv", "chip_interconnect"),
        ("nested/foo.bar.vhd.j2", "foo.bar", "chip_foo.bar.vhd", "chip_foo.bar"),
        ("nested/plain.j2", "plain", "chip_plain", "chip_plain"),
    ],
)
def test_hierarchy_template_basename(tmp_path, template_name, basename, output_name, output_stem):
    template_path = tmp_path / "templates" / template_name
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text("{{ node.type_name }}_{{ template_basename }}_pkg:{{ output_stem }}")
    env = Environment(loader=FileSystemLoader(tmp_path / "templates"))
    node = SimpleNamespace(type_name="chip", inst=SimpleNamespace(def_src_ref=SimpleNamespace(path="source.rdl")))
    design = Mock()
    generator = SimpleNamespace(project=SimpleNamespace(defaultDesign=design))

    output = systemrdl.PeakRdlGenerator.render_template(generator, env.get_template(template_name), node, tmp_path)

    assert output.name == output_name
    assert output.read_text() == f"chip_{basename}_pkg:{output_stem}"


def test_hierarchy_template_directory_without_jinja_templates(tmp_path, monkeypatch):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "disabled.sv.j2.disable").write_text("not a template")
    monkeypatch.setenv("SIMPLHDL_SYSTEMRDL_TEMPLATES", str(templates))
    root = SimpleNamespace(top=SimpleNamespace(type_name="root"))
    generator = SimpleNamespace(render_template=Mock())

    systemrdl.PeakRdlGenerator._generate_hierarchy_templates(generator, [(root, None)], tmp_path / "output", {})

    generator.render_template.assert_not_called()


@pytest.mark.parametrize("separate_directories", [False, True])
def test_hierarchy_template_output_collisions_fail_before_rendering(tmp_path, monkeypatch, separate_directories):
    templates = tmp_path / "first" / "templates"
    templates.mkdir(parents=True)
    (templates / "package.sv.j2").write_text("first")
    if separate_directories:
        other = tmp_path / "second" / "templates"
        other.mkdir(parents=True)
        monkeypatch.setenv("SIMPLHDL_SYSTEMRDL_TEMPLATES", f"{templates}:{other}")
    else:
        other = templates / "nested"
        other.mkdir()
        monkeypatch.setenv("SIMPLHDL_SYSTEMRDL_TEMPLATES", str(templates))
    (other / "package.sv.j2").write_text("second")
    root = SimpleNamespace(top=SimpleNamespace(type_name="root"))
    generator = SimpleNamespace(render_template=Mock())

    with pytest.raises(ValueError, match="would both generate"):
        systemrdl.PeakRdlGenerator._generate_hierarchy_templates(generator, [(root, None)], tmp_path / "output", {})

    generator.render_template.assert_not_called()


def test_single_leaf_hierarchy_package_does_not_collide_with_regblock(tmp_path, monkeypatch):
    source = tmp_path / "leaf.rdl"
    source.write_text("addrmap leaf { reg { field { sw = rw; } value[31:0]; } control; };\n")
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "hierachymap_pkg.sv.j2").write_text("package {{ output_stem }};\nendpackage : {{ output_stem }}\n")
    monkeypatch.setenv("SIMPLHDL_SYSTEMRDL_TEMPLATES", str(templates))

    rdlc = systemrdl.SimplHDLRDLCompiler()
    for udp in systemrdl.ALL_UDPS:
        rdlc.register_udp(udp)
    rdlc.compile_file(str(source))
    root = rdlc.elaborate("leaf")
    collector = systemrdl.AddrmapCollector()
    systemrdl.RDLWalker().walk(root, collector)

    rdlfile = SimpleNamespace(parent=Mock())
    design = Mock()
    design.get_file.return_value = rdlfile
    generator = SimpleNamespace(project=SimpleNamespace(defaultDesign=design))
    generator.render_template = lambda **kwargs: systemrdl.PeakRdlGenerator.render_template(generator, **kwargs)
    output = tmp_path / "output"

    systemrdl.PeakRdlGenerator._generate_hierarchy_templates(generator, [(root, collector)], output, {})
    systemrdl.PeakRdlGenerator.peakrdl_regblock(generator, root.top, output / "peakrdl-regblock", {})

    hierarchy = (output / "templates" / "leaf_hierachymap_pkg.sv").read_text()
    regblock = (output / "peakrdl-regblock" / "leaf_pkg.sv").read_text()
    assert "package leaf_hierachymap_pkg;" in hierarchy
    assert "endpackage : leaf_hierachymap_pkg" in hierarchy
    assert "package leaf_pkg;" in regblock
    assert len(collector.leafnodes) == 1
    assert collector.leafnodes[0].type_name == root.top.type_name


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
