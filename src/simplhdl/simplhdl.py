import logging

from pathlib import Path
from pyEDAA.ProjectModel import VHDLLibrary  # type: ignore

from .project import Project
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
        parser = ParserFactory().get_parser(filename)
        fileset = parser.parse(filename, project)
        project.DefaultDesign.AddFileSet(fileset)
        # TODO: Need some more understading of the project and design classes
        project.DefaultDesign.TopLevel = fileset.TopLevel
        project.DefaultDesign.AddVHDLLibrary(default_library)
        self._project = project

    def run(self, args):
        flow = FlowFactory.get_flow(args.flow)
        builddir = self.builddir.joinpath(flow.name)
        flow.run(args, self._project, builddir)
