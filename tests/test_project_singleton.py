from __future__ import annotations

import pytest

from simplhdl.project.project import Project


def test_project_reuses_instance(project):
    assert Project() is project
    assert Project("another-name") is project
    assert project.name == "project"


def test_project_reset_creates_new_instance(project):
    Project._instance = None
    replacement = Project("new-project")
    assert replacement is not project
    assert replacement.name == "new-project"
    assert Project() is replacement


def test_first_project_requires_name():
    Project._instance = None
    with pytest.raises(TypeError):
        Project()
