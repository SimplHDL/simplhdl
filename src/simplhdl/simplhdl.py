import os

from importlib import import_module
from pathlib import Path
from pyEDAA.ProjectModel import Project

from .parser import ParserFactory
# Import all parser modules to register them in the ParserFactory
for module in os.listdir(os.path.join(os.path.dirname(__file__), 'parsers')):
    if module == '__init__.py' or not module.endswith('.py'):
        continue
    import_module(f".{module[:-3]}", "simplhdl.parsers")
del module


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
