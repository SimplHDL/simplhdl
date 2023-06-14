from pathlib import Path
from pyEDAA.ProjectModel import Project

from .parser import ParserFactory


class Simplhdl:

    def __init__(self):
        self.project = None

    def create_project(self, filename: Path) -> None:
        name = "ProjectName"
        self.project = Project(name)
        parser = ParserFactory().get_parser(filename)
        parser.parse()

    def run(self):
        print("Hello SimplHDL")
