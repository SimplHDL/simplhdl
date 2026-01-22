from __future__ import annotations

from pathlib import Path

from simplhdl.project.files import (
    File,
    FileFactory,
    filter_files,
    UsedIn,
    ConstraintOrder,
    SystemVerilogFile,
    VerilogFile,
    VhdlFile,
    SdcFile,
    UnknownFile,
    HdlFile,
    ConstraintFile,
    QuartusQsysFile,
    QuartusQsysZipFile,
    VerilogIncludeFile
)
from simplhdl.project.fileset import Fileset
from simplhdl.project.attributes import Library


def test_file_initialization():
    f1 = File("test.txt")
    assert f1.path.name == "test.txt"
    assert f1.usedin == [UsedIn.SIMULATION, UsedIn.IMPLEMENTATION]
    assert f1.encrypt is False
    # TODO: assert str(f1) == str(Path("test.txt").resolve())
    # Test repr safety
    # TODO: assert "File" in repr(f1)


def test_file_caching():
    f1 = File("test_cache.txt")
    f2 = File("test_cache.txt")
    assert f1 is f2

    f3 = File("test_cache_other.txt")
    assert f1 is not f3


def test_file_path():
    f = File("file.txt")
    assert f.path == Path("file.txt").resolve()
    File.set_path_relative_to(Path(".."))
    assert f.path == Path("file.txt").resolve().relative_to(Path("..").resolve())
    File.set_path_relative_to(None)
    assert f.path == Path("file.txt").resolve()


def test_file_attributes():
    f = File("test_attr.txt", usedin=[UsedIn.SIMULATION], encrypt=True)
    assert f.usedin == [UsedIn.SIMULATION]
    assert f.encrypt is True

    f.usedin = UsedIn.IMPLEMENTATION
    assert f.usedin == [UsedIn.IMPLEMENTATION]

    f.encrypt = False
    assert f.encrypt is False


def test_hdl_file_defaults():
    f = SystemVerilogFile("test_defaults.sv")
    assert f.encrypt is True

    f_base = File("test_defaults.txt")
    assert f_base.encrypt is False


def test_filter_files():
    f1 = File("f1.txt")  # encrypt=False
    f2 = SystemVerilogFile("f2.sv", usedin=[UsedIn.SIMULATION])  # encrypt=True
    f3 = VhdlFile("f3.vhd", usedin=[UsedIn.IMPLEMENTATION], encrypt=False)  # encrypt=False
    f4 = VerilogFile("f4.v", usedin=[UsedIn.SIMULATION, UsedIn.IMPLEMENTATION])  # encrypt=True

    files = [f1, f2, f3, f4]

    # Filter by type
    assert list(filter_files(files, file_type=SystemVerilogFile)) == [f2]
    assert list(filter_files(files, file_type=(SystemVerilogFile, VhdlFile))) == [f2, f3]

    # Filter by usedin
    assert list(filter_files(files, usedin=UsedIn.SIMULATION)) == [f1, f2, f4]
    assert list(filter_files(files, usedin=UsedIn.IMPLEMENTATION)) == [f1, f3, f4]

    # Filter by attribute
    assert list(filter_files(files, encrypt=False)) == [f1, f3]
    assert list(filter_files(files, encrypt=True)) == [f2, f4]

    # Filter by multiple attributes
    assert list(filter_files(files, encrypt=False, usedin=UsedIn.SIMULATION)) == [f1]
    assert list(filter_files(files, file_type=(SystemVerilogFile, VhdlFile), usedin=UsedIn.IMPLEMENTATION)) == [f3]


def test_file_factory_create():
    f_sv = FileFactory.create(Path("test.sv"))
    assert isinstance(f_sv, SystemVerilogFile)

    f_v = FileFactory.create(Path("test.v"))
    assert isinstance(f_v, VerilogFile)

    f_unknown = FileFactory.create(Path("test.unknown"))
    assert isinstance(f_unknown, UnknownFile)

    f_explicit = FileFactory.create(Path("test.txt"), type="SystemVerilogFile")
    assert isinstance(f_explicit, SystemVerilogFile)


def test_file_factory_extension_priority():
    f_zip = FileFactory.create(Path("test.qsys.zip"))
    assert isinstance(f_zip, QuartusQsysZipFile)

    f_qsys = FileFactory.create(Path("test.qsys"))
    assert isinstance(f_qsys, QuartusQsysFile)


def test_hdl_file_library(design):
    lib_default = Library("work")
    design.defaultLibrary = lib_default

    fs = Fileset("test_fs")
    design.add_fileset(fs)

    f1 = HdlFile("test_lib1.v")
    fs.add_file(f1)
    assert f1.library == lib_default

    lib_custom = Library("custom")
    fs.library = lib_custom
    assert f1.library == lib_custom

    lib_file = Library("file_lib")
    f2 = HdlFile("test_lib2.v", library=lib_file)
    fs.add_file(f2)
    assert f2.library == lib_file


def test_constraint_file():
    f = SdcFile("test.sdc", scope="scope1", order=ConstraintOrder.EARLY)
    assert isinstance(f, ConstraintFile)
    assert f.scope == "scope1"
    assert f.order == ConstraintOrder.EARLY

    f.scope = "scope2"
    assert f.scope == "scope2"


def test_verilog_include_file():
    f = FileFactory.create(Path("includes/test.vh"))
    assert isinstance(f, VerilogIncludeFile)
    assert f.includeDir == Path("includes").resolve()
