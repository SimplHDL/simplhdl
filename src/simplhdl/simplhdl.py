import os

from importlib import import_module
from pathlib import Path
from pyEDAA.ProjectModel import Project, HDLSourceFile, SystemVerilogSourceFile

from .parser import ParserFactory
# Import all parser modules to register them in the ParserFactory
for module in os.listdir(os.path.join(os.path.dirname(__file__), 'parsers')):
    if module == '__init__.py' or not module.endswith('.py'):
        continue
    import_module(f".{module[:-3]}", "simplhdl.parsers")
del module


class Simplhdl:

    def __init__(self):
        self._project = None

    def create_project(self, filename: Path) -> None:
        parser = ParserFactory().get_parser(filename)
        fileset = parser.parse(filename)
        project = Project("default")
        project.DefaultDesign.AddFileSet(fileset)
        for file in [f for f in project.DefaultDesign.Files() if issubclass(f.FileType, SystemVerilogSourceFile)]:
            print(file.Path.absolute())
        self._project = project

    def run(self):
        print(self._project)
