import logging

from pathlib import Path
from pyEDAA.ProjectModel import Project, SystemVerilogSourceFile  # type: ignore

from .parser import ParserFactory

logger = logging.getLogger(__name__)


class Simplhdl:

    def __init__(self):
        self._project = None

    def create_project(self, filename: Path) -> None:
        parser = ParserFactory().get_parser(filename)
        fileset = parser.parse(filename)
        project = Project("default")
        project.DefaultDesign.AddFileSet(fileset)
        for file in [f for f in project.DefaultDesign.Files() if issubclass(f.FileType, SystemVerilogSourceFile)]:
            logger.info(file.Path.absolute())
        self._project = project

    def run(self):
        print(self._project)
