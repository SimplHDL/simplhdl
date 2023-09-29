try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import os
import shutil
import logging
import json

from argparse import Namespace
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import Dict, List
import pyEDAA.ProjectModel as pm


from ..flow import FlowFactory, FlowBase
from ..project import Project
from ..resources.templates import vivado as templates
from ..utils import sh, generate_from_template

logger = logging.getLogger(__name__)


@FlowFactory.register('vivado')
class VivadoFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('vivado', help='Vivado FPGA Build Flow')
        parser.add_argument(
            '-s',
            '--step',
            action='store',
            choices=[
                'synthesis',
                'opt',
                'power_opt',
                'place',
                'phys_opt',
                'route',
                'bitstream'],
            default='bitstream',
            help="flow step to run"
        )
        parser.add_argument(
            '--gui',
            action='store_true',
            help="Open project in Vivado GUI"
        )

    def is_tool_setup(self) -> None:
        exit: bool = False
        if shutil.which('vivado') is None:
            logger.error('vivado: not found in PATH')
            exit = True
        if exit:
            raise FileNotFoundError("Quartus is not setup correctly")

    def setup(self):
        self.is_tool_setup()
        os.makedirs(self.builddir, exist_ok=True)

    def generate(self):
        templatedir = resources_files(templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)
        template = environment.get_template('project.tcl.j2')
        generate_from_template(template, self.builddir,
                               pm=pm,
                               str=str,
                               project=self.project)
        template = environment.get_template('run.tcl.j2')
        generate_from_template(template, self.builddir,
                               project=self.project)
        template = environment.get_template('launch_run.sh.j2')
        generate_from_template(template, self.builddir)
        command = "vivado -mode batch -notrace -source project.tcl".split()
        sh(command, cwd=self.builddir)

    def execute(self, step: str):
        name = self.project.DefaultDesign.Name
        command = f"vivado {name}.xpr -mode batch -notrace -source run.tcl -tclargs {step}".split()
        sh(command, cwd=self.builddir)
        jsonfile = self.builddir.joinpath('runs.json')
        with jsonfile.open() as f:
            runs: Dict[str, List[str]] = json.load(f)
        for name, run in runs.items():
            for script in run:
                sh(['bash', 'launch_run.sh', script], output=True, cwd=self.builddir)

    def run(self, args: Namespace, project: Project, builddir: Path) -> None:
        self.project = project
        self.builddir = builddir
        self.args = args

        if self.args.gui:
            projectfile = self.builddir.joinpath(f"{self.project.DefaultDesign.Name}.xpr")
            if projectfile.exists():
                sh(['vivado', projectfile.name], cwd=self.builddir)
                return
            else:
                raise FileNotFoundError(f"{projectfile}: doesn't exists")

        self.setup()
        self.generate()
        self.execute(args.step)
