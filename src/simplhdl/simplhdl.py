import logging

import networkx as nx
from pathlib import Path
from argparse import Namespace

from .project.project import Project, ProjectError
from .project.design import Design
from .project.attributes import Library
from .plugin.parser import ParserFactory
from .plugin.flow import FlowFactory
from .plugin.flow import FlowError
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
        try:
            if self.args.flow == "info":
                target = getattr(self.args, "infoflow", None)
                target_flow = flow
                if target:
                    from .cli.arguments import parse_arguments

                    if target not in FlowFactory.get_flows() or target in ("info", "run"):
                        raise FlowError(f"Unknown inspection flow '{target}'")
                    try:
                        target_args = parse_arguments([target])
                    except SystemExit as exc:
                        raise FlowError(f"Cannot inspect flow '{target}' without required options") from exc
                    target_args.projectspec = self.args.projectspec
                    target_args.outputdir = self.args.outputdir
                    target_args.verbose = self.args.verbose
                    target_flow = FlowFactory.get_flow(target, target_args, project, builddir / target)
                    if target_flow.supported_file_types is None:
                        logger.warning(
                            "Flow '%s' has not declared file selection; the inspection may be incomplete", target
                        )
                flow.view_flow = target_flow if target else None
                flow.generators = list(GeneratorFactory.get_generators(target_flow.args, project, target_flow.builddir))
                if getattr(self.args, "generate", False):
                    self.run_generators(target_flow, flow.generators)
            else:
                self.run_generators(flow)
            flow.run()

        except nx.NetworkXUnfeasible:
            project.defaultDesign.validate()

    def run_generators(self, flow, generators=None):
        if generators is None:
            generators = GeneratorFactory.get_generators(flow.args, flow.project, flow.builddir)
        for generator in generators:
            if generator.supported_file_types is not None and not generator.get_files(flow):
                continue
            generator.run(flow)
            try:
                flow.project.elaborate()
                flow.project.validate()
            except ProjectError as exc:
                raise GeneratorError(exc) from exc
        flow.project.elaborate()
