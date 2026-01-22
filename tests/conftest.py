from __future__ import annotations

import pytest

from simplhdl.project.project import Project
from simplhdl.project.design import Design
from simplhdl.project.files import File
from simplhdl.project.fileset import Fileset


@pytest.fixture(autouse=True)
def project() -> Project:
    # The Project class is a singleton, so we need to reset it for each test.
    Project._instance = None
    # Clear caches
    Fileset._cache.clear()
    File._cache.clear()
    return Project("project")


@pytest.fixture
def design(project) -> Design:
    d = Design("design")
    project.add_design(d)
    return d


@pytest.fixture
def fileset(design) -> Fileset:
    fs = Fileset('fileset')
    design.add_fileset(fs)
    return fs
