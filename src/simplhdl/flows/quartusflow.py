import os
import shutil
import logging

from argparse import Namespace
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from importlib import resources
import pyEDAA.ProjectModel as pm


from ..flow import FlowFactory, FlowBase
from ..project import Project
from ..resources.templates import quartus as templates
from ..utils import sh, generate_from_template

logger = logging.getLogger(__name__)


@FlowFactory.register('quartus')
class QuartusFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('quartus', help='Quartus FPGA Build Flow')
        parser.add_argument(
            '-s',
            '--step',
            action='store',
            choices=['synthsis', 'place', 'route', 'bitstream'],
            default='bitstream',
            help="flow step to run"
        )
        parser.add_argument(
            '--gui',
            action='store_true',
            help="Open project in Quartus GUI"
        )

    def run(self, args: Namespace, project: Project, builddir: Path) -> None:
        self.project = project
        self.builddir = builddir
        self.args = args
        shutil.rmtree(builddir, ignore_errors=True)
        os.makedirs(builddir, exist_ok=True)
        self.configure()
        self.generate()
        self.execute(args.step)

    def configure(self):
        pass

    def generate(self):
        templatedir = resources.files(templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)

        template = environment.get_template('project.tcl.j2')
        generate_from_template(template, self.builddir,
                               pm=pm,
                               project=self.project)
        template = environment.get_template('run.tcl.j2')
        generate_from_template(template, self.builddir,
                               project=self.project)
        command = "quartus_sh -t project.tcl".split()
        self.is_tool_setup()
        sh(command, cwd=self.builddir, output=True)

    def execute(self, step: str):
        name = self.project.DefaultDesign.Name

        if self.args.gui:
            sh(['quartus', name], cwd=self.builddir)
            return

        command = f"quartus_sh -t run.tcl -project {name}".split()
        self.is_tool_setup()
        sh(command, cwd=self.builddir, output=True)

    def is_tool_setup(self) -> None:
        exit: bool = False
        if shutil.which('quartus_sh') is None:
            logger.error('quartus_sh: not found in PATH')
            exit = True
        if shutil.which('quartus') is None:
            logger.error('quartus: not found in PATH')
            exit = True
        if exit:
            raise FileNotFoundError("Quartus is not setup correctly")
