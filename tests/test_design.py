from __future__ import annotations

import pytest
from pathlib import Path

from simplhdl.project.project import ProjectError
from simplhdl.project.fileset import Fileset, FileOrder, FilesetOrder
from simplhdl.project.files import File, VerilogFile, VhdlFile
from simplhdl.project.attributes import Library


def test_design_initialization(design):
    assert design.name == "design"
    assert design._project is not None
    assert design.defaultLibrary is None
    assert design.toplevels == []
    assert design.libraries == []


def test_design_name_property(design):
    assert design.name == "design"


def test_default_library(design):
    assert design.defaultLibrary is None
    lib1 = Library("lib1")
    design.defaultLibrary = lib1
    assert design.defaultLibrary is lib1
    assert "lib1" in design._libraries
    assert design.libraries == [lib1]

    lib2 = Library("lib2")
    design.defaultLibrary = lib2
    assert design.defaultLibrary is lib2
    assert "lib2" in design._libraries


def test_add_library(design):
    lib1 = Library("work")
    design.add_library(lib1)
    assert design.libraries == [lib1]
    assert design.defaultLibrary is lib1

    lib2 = Library("common")
    design.add_library(lib2)
    assert len(design.libraries) == 2
    assert design.defaultLibrary is lib1  # Should not change


def test_toplevels_setter(design):
    design.toplevels = "top_module"
    assert design.toplevels == ["top_module"]

    design.toplevels = ["top1", "top2"]
    assert design.toplevels == ["top1", "top2"]


def test_add_toplevel(design):
    design.add_toplevel("top1")
    assert design.toplevels == ["top1"]
    design.add_toplevel("top2")
    assert design.toplevels == ["top1", "top2"]


def test_add_fileset(design):
    fs1 = Fileset("fs1")
    design.add_fileset(fs1)
    assert fs1 in design._filesets
    assert fs1._project == design._project


def test_filesets_retrieval(design):
    fs1 = Fileset("fs1")
    fs2 = Fileset("fs2")
    fs3 = Fileset("fs3")
    design.add_fileset(fs1)
    design.add_fileset(fs2)
    fs1.add_fileset(fs3)

    # topological sort order depends on insertion if no edges
    # with edge fs1->fs3, fs1 should come before fs3
    filesets = design.filesets(order=FilesetOrder.COMPILE)
    assert fs1 in filesets
    assert fs2 in filesets
    assert fs3 in filesets
    assert filesets.index(fs1) > filesets.index(fs3)

    # Test reverse
    rev_filesets = design.filesets(order=FilesetOrder.HIERACHY)
    assert rev_filesets.index(fs3) > rev_filesets.index(fs1)


def test_roots(design):
    fs1 = Fileset("fs1")
    fs2 = Fileset("fs2")
    fs3 = Fileset("fs3")
    design.add_fileset(fs1)
    design.add_fileset(fs2)
    fs1.add_fileset(fs3)  # fs1 is parent of fs3

    roots = design.roots
    assert len(roots) == 2
    assert fs1 in roots
    assert fs2 in roots
    assert fs3 not in roots


def test_files_retrieval(design):
    fs = Fileset("fs")
    design.add_fileset(fs)

    file1 = File(Path("file1.v"))
    file2 = File(Path("file2.vhd"))
    fs.add_file(file1)
    fs.add_file(file2)

    # The files are added to the design's graph through the fileset
    all_files = design.files(order=FileOrder.COMPILE)
    assert len(all_files) == 2
    assert file1 in all_files
    assert file2 in all_files
    assert all_files.index(file1) < all_files.index(file2)
    all_files = design.files(order=FileOrder.HIERACHY)
    assert len(all_files) == 2
    assert file1 in all_files
    assert file2 in all_files
    assert all_files.index(file1) > all_files.index(file2)


def test_files_filtering(design):
    fs = Fileset("fs")
    design.add_fileset(fs)

    verilogfile = VerilogFile(Path("verilog_file.v"))
    vhdlfile = VhdlFile(Path("vhdl_file.vhd"))
    fs.add_file(verilogfile)
    fs.add_file(vhdlfile)

    assert design.files(order=FileOrder.COMPILE) == [verilogfile, vhdlfile]
    assert design.files(type=VerilogFile) == [verilogfile]
    assert design.files(type=VhdlFile) == [vhdlfile]


def test_validate_acyclic(design):
    fs1 = Fileset("fs1")
    fs2 = Fileset("fs2")
    design.add_fileset(fs1)
    design.add_fileset(fs2)
    fs1.add_fileset(fs2)
    design.validate()  # Should not raise exception


def test_validate_cyclic_raises_error(design):
    fs1 = Fileset("fs1")
    fs2 = Fileset("fs2")
    design.add_fileset(fs1)
    design.add_fileset(fs2)
    fs1.add_fileset(fs2)
    fs2.add_fileset(fs1)  # Creates a cycle

    with pytest.raises(ProjectError, match="Cyclic dependency found: fs1 -> fs2 -> fs1"):
        design.validate()


def test_elaborate(design):
    fs1 = Fileset("fs1")
    fs1_leaf_file = File("fs1_leaf_file.sv")
    fs1_root_file = File("fs1_root_file.sv")
    fs1.add_file(fs1_leaf_file)
    fs1.add_file(fs1_root_file)
    fs2 = Fileset("fs2")
    fs2_leaf_file = File("fs2_leaf_file.sv")
    fs2_root_file = File("fs2_root_file.sv")
    fs2.add_file(fs2_leaf_file)
    fs2.add_file(fs2_root_file)
    fs2.add_fileset(fs1)
    design.add_fileset(fs2)
    design.elaborate()
    assert design.files(order=FileOrder.COMPILE) == [
        fs1_leaf_file,
        fs1_root_file,
        fs2_leaf_file,
        fs2_root_file,
        ]
    assert design.files(order=FileOrder.HIERACHY) == [
        fs2_root_file,
        fs2_leaf_file,
        fs1_root_file,
        fs1_leaf_file,
    ]


def test_elaborate_with_empty_fileset(design):
    fs1 = Fileset("fs1")
    fs1_leaf_file = File("fs1_leaf_file.sv")
    fs1_root_file = File("fs1_root_file.sv")
    fs1.add_file(fs1_leaf_file)
    fs1.add_file(fs1_root_file)
    fs_empty = Fileset("fs_empty")
    fs2 = Fileset("fs2")
    fs2_leaf_file = File("fs2_leaf_file.sv")
    fs2_root_file = File("fs2_root_file.sv")
    fs2.add_file(fs2_leaf_file)
    fs2.add_file(fs2_root_file)
    fs_empty.add_fileset(fs1)
    fs2.add_fileset(fs_empty)
    design.add_fileset(fs2)
    design.elaborate()
    assert design.files(order=FileOrder.COMPILE) == [
        fs1_leaf_file,
        fs1_root_file,
        fs2_leaf_file,
        fs2_root_file,
        ]
    assert design.files(order=FileOrder.HIERACHY) == [
        fs2_root_file,
        fs2_leaf_file,
        fs1_root_file,
        fs1_leaf_file,
    ]
