import logging

import networkx as nx
from pathlib import Path
from argparse import Namespace

from .project.project import Project, ProjectError
from .project.design import Design
from .project.attributes import Library
from .plugin.parser import ParserFactory
from .plugin.flow import FlowFactory
from .plugin.generator import GeneratorFactory, GeneratorError

logger = logging.getLogger(__name__)


class Simplhdl:
    def __init__(self, args: Namespace):
        self.args = args
        self.builddir: Path = args.outputdir

    def create_project(self, builddir: Path) -> Project:
        filename = self.args.projectspec
        project = Project("default")
        project.buildDir = builddir
        design = Design("default")
        project.add_design(design)
        project.defaultDesign.defaultLibrary = Library("work")
        parser = ParserFactory().get_parser(filename)
        fileset = parser.parse(filename, project, self.args)
        project.defaultDesign.add_fileset(fileset)
        project.elaborate()
        project.validate()
        return project

    def run(self):
        builddir = self.builddir.joinpath(self.args.flow)
        project = self.create_project(builddir)
        flow = FlowFactory.get_flow(self.args.flow, self.args, project, builddir)
        generators = GeneratorFactory.get_generators(self.args, project, builddir)
        try:
            for generator in generators:
                generator.run(flow)
                try:
                    project.elaborate()
                    project.validate()
                except ProjectError as e:
                    raise GeneratorError(e)
            project.elaborate()
            flow.run()
        except nx.NetworkXUnfeasible:
            project.defaultDesign.validate()
