import pytest

from simplhdl.project.files import (
    File,
    FileFactory,
    HdlFile,
    SystemVerilogFile,
    VerilogFile,
    VerilogIncludeFile,
    VhdlFile,
    SdcFile,
    EdifFile,
    CFile,
    CocotbPythonFile,
    QuartusQsfFile,
    QuartusQipFile,
    QuartusQsysFile,
    QuartusIpFile,
    QuartusIpxFile,
    QuartusTCLSourceFile,
    VivadoXdcFile,
    VivadoDcpFile,
    VivadoXciFile,
    VivadoXcixFile,
    VivadoBdFile,
    VivadoBdTclFile,
    VivadoStepFile,
    ChiselBuildFile,
    UnknownFile,
    simulation,
    implementation,
)

# Mock dependencies that are not the focus of these tests
@pytest.fixture
def mock_fileset(mocker):
    return mocker.Mock(name="MockFileset")


@pytest.fixture
def mock_library(mocker):
    return mocker.Mock(name="MockLibrary")


@pytest.fixture(autouse=True)
def clear_factory_registrations():
    """Fixture to ensure a clean FileFactory for each test."""
    original_types = FileFactory._registered_types.copy()
    original_extensions = FileFactory._registered_extensions.copy()
    yield
    FileFactory._registered_types = original_types
    FileFactory._registered_extensions = original_extensions


class TestFile:
    def test_file_initialization(self, tmp_path):
        p = tmp_path / "test.txt"
        p.touch()
        f = File(p)
        assert f.path == p.absolute().resolve()
        assert f.parent is None
        assert f.usedin == []
        assert f.encrypt is False

    def test_file_initialization_with_attributes(self, tmp_path):
        p = tmp_path / "test.txt"
        p.touch()
        f = File(p, usedin=["simulation"], encrypt=True)
        assert f.usedin == ["simulation"]
        assert f.encrypt is True

    def test_file_parent_setter(self, tmp_path, mock_fileset):
        p = tmp_path / "test.txt"
        p.touch()
        f = File(p)
        f.parent = mock_fileset
        assert f.parent == mock_fileset

    def test_file_str_repr(self, tmp_path, mock_fileset):
        p = tmp_path / "test.txt"
        p.touch()
        f = File(p)
        f.parent = mock_fileset
        assert str(f) == str(p.absolute().resolve())
        assert repr(f) == f"File(path={f.path}, parent={mock_fileset})"


class TestHdlFile:
    def test_hdlfile_initialization(self, tmp_path, mock_library):
        p = tmp_path / "design.sv"
        p.touch()
        hdl_file = HdlFile(p, library=mock_library)
        assert hdl_file.usedin == [simulation, implementation]
        assert hdl_file.encrypt is True
        assert hdl_file.library == mock_library

    def test_hdlfile_default_library(self, tmp_path):
        p = tmp_path / "design.sv"
        p.touch()
        hdl_file = HdlFile(p)
        assert hdl_file.library is None


class TestFileFactory:
    def test_register_decorator(self):
        # Use a new class to avoid conflicts with pre-registered classes
        @FileFactory.register(extension=".foo")
        class FooFile(File):
            pass

        assert FileFactory._registered_extensions[".foo"] is FooFile
        assert FileFactory._registered_types["foofile"] is FooFile

    def test_register_multiple_extensions(self):
        @FileFactory.register(extension=[".bar", ".baz"])
        class BarFile(File):
            pass

        assert FileFactory._registered_extensions[".bar"] is BarFile
        assert FileFactory._registered_extensions[".baz"] is BarFile
        assert FileFactory._registered_types["barfile"] is BarFile

    def test_register_duplicate_extension_raises_error(self, caplog):
        @FileFactory.register(extension=".dup")
        class DupFile1(File):
            pass

        with pytest.raises(ValueError) as excinfo:
            @FileFactory.register(extension=".dup")
            class DupFile2(File):
                pass
        assert "Extension '.dup' already registered by DupFile1" in str(excinfo.value)

    def test_register_duplicate_class_name_raises_error(self):
        # Clear registrations for this specific test
        FileFactory._registered_types.clear()
        FileFactory._registered_extensions.clear()

        @FileFactory.register()
        class MyTestFile(File):
            pass

        with pytest.raises(ValueError) as excinfo:
            # This class has the same lowercase name
            @FileFactory.register()
            class mytestfile(File):
                pass

        assert "Class 'mytestfile' already registered." in str(excinfo.value)

    def test_create_by_extension(self, tmp_path):
        sv_file = FileFactory.create(tmp_path / "design.sv")
        assert isinstance(sv_file, SystemVerilogFile)

        v_file = FileFactory.create(tmp_path / "design.v")
        assert isinstance(v_file, VerilogFile)

        vhdl_file = FileFactory.create(tmp_path / "design.vhd")
        assert isinstance(vhdl_file, VhdlFile)

    def test_create_by_type(self, tmp_path):
        # File extension would suggest VerilogFile, but type overrides it
        f = FileFactory.create(tmp_path / "some.v", type="VhdlFile")
        assert isinstance(f, VhdlFile)

    def test_create_unknown_file(self, tmp_path):
        f = FileFactory.create(tmp_path / "document.txt")
        assert isinstance(f, UnknownFile)

    def test_create_with_attributes(self, tmp_path):
        f = FileFactory.create(
            tmp_path / "design.sv", usedin=["simulation"], encrypt=False
        )
        assert isinstance(f, SystemVerilogFile)
        assert f.usedin == ["simulation"]
        assert f.encrypt is False

    def test_create_longest_extension_match(self, tmp_path):
        # .bd.tcl is longer than .tcl
        f_bd_tcl = FileFactory.create(tmp_path / "my_block.bd.tcl")
        assert isinstance(f_bd_tcl, VivadoBdTclFile)

        # .step.tcl is longer than .tcl
        f_step_tcl = FileFactory.create(tmp_path / "post_synth.step.tcl")
        assert isinstance(f_step_tcl, VivadoStepFile)

        # .source.tcl is longer than .tcl
        f_source_tcl = FileFactory.create(tmp_path / "setup.source.tcl")
        assert isinstance(f_source_tcl, QuartusTCLSourceFile)


@pytest.mark.parametrize(
    "filename, expected_class, expected_usedin",
    [
        ("test.sv", SystemVerilogFile, [simulation, implementation]),
        ("test.v", VerilogFile, [simulation, implementation]),
        ("test.vh", VerilogIncludeFile, [simulation, implementation]),
        ("test.svh", VerilogIncludeFile, [simulation, implementation]),
        ("test.vhd", VhdlFile, [simulation, implementation]),
        ("test.vhdl", VhdlFile, [simulation, implementation]),
        ("test.sdc", SdcFile, [implementation]),
        ("test.edn", EdifFile, [implementation]),
        ("test.edif", EdifFile, [implementation]),
        ("test.c", CFile, []),
        ("test.h", CFile, []),
        ("test.s", CFile, []),
        ("test.py", CocotbPythonFile, [simulation]),
        ("test.qsf", QuartusQsfFile, [implementation]),
        ("test.qip", QuartusQipFile, [implementation]),
        ("test.qsys", QuartusQsysFile, [simulation, implementation]),
        ("test.ip", QuartusIpFile, [simulation, implementation]),
        ("test.ipx", QuartusIpxFile, [simulation, implementation]),
        ("test.source.tcl", QuartusTCLSourceFile, [implementation]),
        ("test.xdc", VivadoXdcFile, [implementation]),
        ("test.dcp", VivadoDcpFile, [implementation]),
        ("test.xci", VivadoXciFile, [simulation, implementation]),
        ("test.xcix", VivadoXcixFile, [simulation, implementation]),
        ("test.bd", VivadoBdFile, [simulation, implementation]),
        ("test.bd.tcl", VivadoBdTclFile, [simulation, implementation]),
        ("test.step.tcl", VivadoStepFile, [implementation]),
        ("test.sbt", ChiselBuildFile, []),
        ("test.unknown", UnknownFile, []),
    ],
)
def test_file_subclass_creation_and_defaults(tmp_path, filename, expected_class, expected_usedin):
    p = tmp_path / filename
    p.touch()
    file_instance = FileFactory.create(p)
    assert isinstance(file_instance, expected_class)
    assert file_instance.usedin == expected_usedin
