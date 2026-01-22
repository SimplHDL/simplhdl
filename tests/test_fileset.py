from simplhdl import Fileset, FileOrder
from simplhdl.project.attributes import Library
from simplhdl.project.files import File


def test_fileset_name(fileset):
    assert fileset.name == 'fileset'


def test_fileset_str_repr(fileset):
    assert str(fileset) == 'fileset'
    assert 'Fileset' in repr(fileset)


def test_fileset_equality():
    fs1 = Fileset('fileset')
    fs2 = Fileset('fileset')
    assert fs1 == fs2
    assert fs1 is fs2
    fs3 = Fileset('other')
    assert fs1 != fs3


def test_fileset_hash():
    fs1 = Fileset('fileset')
    fs2 = Fileset('fileset')
    assert hash(fs1) == hash(fs2)
    fs3 = Fileset('other')
    assert hash(fs1) != hash(fs3)


def test_fileset_library(fileset):
    lib = Library('lib')
    fileset.library = lib
    assert fileset.library is lib


def test_add_fileset(fileset):
    child = Fileset('child')
    fileset.add_fileset(child)
    assert fileset.children == [child]
    assert fileset.filesets == [child]


def test_add_filesets(fileset):
    child1 = Fileset('child1')
    child2 = Fileset('child2')
    fileset.add_filesets([child1, child2])
    assert fileset.children == [child1, child2]
    assert fileset.filesets == [child1, child2]


def test_add_fileset_hierachy(fileset):
    child = Fileset('child')
    fileset.add_fileset(child)
    grandchild = Fileset('grandchild')
    child.add_fileset(grandchild)
    assert fileset.children == [child]
    assert fileset.filesets == [child, grandchild]
    assert child.children == [grandchild]
    assert child.filesets == [grandchild]


def test_add_file(fileset):
    file = File('test.sv')
    fileset.add_file(file)
    assert file._parent == fileset
    assert fileset.files() == [file]


def test_insert_file_after(fileset):
    file1 = File('test1.sv')
    file2 = File('test2.sv')
    fileset._project.defaultDesign._files.successors = lambda x: []
    fileset._project.defaultDesign._files.add_edge = lambda a, b: None
    fileset._project.defaultDesign._files.remove_edge = lambda a, b: None
    fileset.add_file(file1)
    fileset.insert_file_after(file1, file2)
    assert file2._parent == fileset


def test_files(fileset):
    fileset = Fileset('test_files')
    file1 = File('file1.sv')
    file2 = File('file2.sv')
    fileset.add_file(file1)
    fileset.add_file(file2)
    files_compile_order = fileset.files(order=FileOrder.COMPILE)
    assert len(fileset._files.nodes()) == 2
    assert files_compile_order == [file1, file2]
    files_hierachy_order = fileset.files(order=FileOrder.HIERACHY)
    assert files_hierachy_order == [file2, file1]


def test_leafs(fileset):
    file1 = File('file1.sv')
    file2 = File('file2.sv')
    fileset.add_file(file1)
    fileset.add_file(file2)
    assert fileset._leafs == [file1]


def test_roots(fileset):
    file1 = File('file1.sv')
    fileset.add_file(file1)
    assert fileset._roots == [file1]
    file2 = File('file2.sv')
    fileset.add_file(file2)
    assert fileset._roots == [file2]
