import pytest

from pathlib import Path

from simplhdl.project.files import File
from simplhdl.project.fileset import Fileset
from simplhdl.project.project import Project


@pytest.fixture(autouse=True)
def project():
    Project._instance = None
    Fileset._cache.clear()
    File._cache.clear()


def test_project_creation():
    p = Project()
    assert p.name == "default"
    assert p.buildDir == Path(".")


def test_project_creation_with_name():
    p1 = Project("p1", Path("build"))
    assert p1.name == "p1"
    assert p1.buildDir == Path("build")
    p2 = Project("p2")
    assert p2.name == "p1"
    p3 = Project()
    assert p3.name == "p1"


def test_project_creation_with_builddir():
    p1 = Project(builddir=Path("build1"))
    assert p1.buildDir == Path("build1")
    p2 = Project()
    assert p2.buildDir == Path("build1")
    p3 = Project(builddir=Path("build2"))
    assert p3.buildDir == Path("build1")
