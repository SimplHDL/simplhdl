import logging
from argparse import Namespace
from pathlib import Path

from .flow import FlowFactory
from .generator import GeneratorFactory
from .parser import ParserFactory
from .project.attributes import Library
from .project.design import Design
from .project.project import Project

logger = logging.getLogger(__name__)


class Simplhdl:

    def __init__(self, args: Namespace) -> None:
        self.args = args
        self.builddir: Path = args.outputdir

    def create_project(self) -> Project:
        filename = self.args.projectspec
        design = Design("default")
        design.defaultLibrary = Library("work")
        project = Project("default")
        project.add_design(design)
        parser = ParserFactory().get_parser(filename)
        fileset = parser.parse(filename, project, self.args)
        project.defaultDesign.add_fileset(fileset)
        return project

    def run(self) -> None:
        project = self.create_project()
        builddir = self.builddir.joinpath(self.args.flow)
        flow = FlowFactory.get_flow(self.args.flow, self.args, project, builddir)
        # generators = GeneratorFactory.get_generators(self.args, project, builddir)
        # for generator in generators:
        #     generator.run(flow)
        flow.run()
