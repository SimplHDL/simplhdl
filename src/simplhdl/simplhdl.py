import logging

from pathlib import Path
from argparse import Namespace

from .pyedaa.project import Project
from .pyedaa.design import Design
from .pyedaa.vhdllibrary import VHDLLibrary
from .parser import ParserFactory
from .flow import FlowFactory
from .generator import GeneratorFactory

logger = logging.getLogger(__name__)


class Simplhdl:

    def __init__(self, args: Namespace):
        self.args = args
        self.builddir: Path = args.outputdir

    def create_project(self) -> Project:
        filename = self.args.projectspec
        default_library = VHDLLibrary("work")
        project = Project("default")
        project.ReposDir = self.builddir.joinpath('repos')
        # TODO: This is a workaround to fix the AddVHDLLibary function in
        #       the Design class
        project.DefaultDesign = Design("default")
        project.DefaultDesign.AddVHDLLibrary(default_library)
        parser = ParserFactory().get_parser(filename)
        fileset = parser.parse(filename, project, self.args)
        project.DefaultDesign.AddFileSet(fileset)
        project.DefaultDesign.DefaultFileSet = fileset.Name

        # TODO: Need some more understading of the project and design classes
        # project.DefaultDesign.TopLevel = fileset.TopLevel
        return project

    def run(self):
        project = self.create_project()
        builddir = self.builddir.joinpath(self.args.flow)
        flow = FlowFactory.get_flow(self.args.flow, self.args, project, builddir)
        generators = GeneratorFactory.get_generators(self.args, project, builddir)
        for generator in generators:
            generator.run(flow)
        flow.run()
