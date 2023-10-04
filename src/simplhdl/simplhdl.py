import logging

from pathlib import Path
from pyEDAA.ProjectModel import VHDLLibrary  # type: ignore

from .project import Project
from .design import Design
from .parser import ParserFactory
from .flow import FlowFactory

logger = logging.getLogger(__name__)


class Simplhdl:

    def __init__(self):
        self._project = None
        self.builddir: Path = Path('_build')

    def create_project(self, filename: Path) -> None:
        default_library = VHDLLibrary("work")
        project = Project("default")
        # TODO: This is a workaround to fix the AddVHDLLibary function in
        #       the Design class
        project.DefaultDesign = Design("default", project)
        project.DefaultDesign.AddVHDLLibrary(default_library)
        parser = ParserFactory().get_parser(filename)
        fileset = parser.parse(filename, project)
        project.DefaultDesign.AddFileSet(fileset)
        project.DefaultDesign.DefaultFileSet = fileset.Name

        # TODO: Need some more understading of the project and design classes
        project.DefaultDesign.TopLevel = fileset.TopLevel
        self._project = project

    def run(self, args):
        flow = FlowFactory.get_flow(args.flow)
        builddir = self.builddir.joinpath(flow.name)
        flow.run(args, self._project, builddir)
