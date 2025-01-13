try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import os
import shutil
import logging
from argparse import Namespace
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from ..flow import FlowFactory, FlowBase, FlowTools
from ..resources.templates import vivado as templates
from ..utils import sh, generate_from_template, dict2str
from ..pyedaa import (VivadoIPSpecificationFile, VerilogIncludeFile, VerilogSourceFile,
                      SystemVerilogSourceFile, VHDLSourceFile, ConstraintFile,
                      EDIFNetlistFile, NetlistFile, VivadoBDTclFile, VivadoProjectStepFile)
from ..pyedaa.project import Project
from ..pyedaa.attributes import UsedIn

logger = logging.getLogger(__name__)


@FlowFactory.register('vivado')
class VivadoFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('vivado', help='Vivado FPGA Build Flow')
        parser.add_argument(
            '--step',
            action='store',
            choices=[
                'lint',
                'elaborate',
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
        parser.add_argument(
            '--archive',
            choices=[
                'project',
                'project-exclude-results',
                'project-include-settings'
            ],
            help="Archive Vivado project, result can be excluded"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = templates
        self.tools.add(FlowTools.VIVADO)

    def is_tool_setup(self) -> None:
        exit: bool = False
        if shutil.which('vivado') is None:
            logger.error('vivado: not found in PATH')
            exit = True
        if exit:
            raise FileNotFoundError("Vivado is not setup correctly")

    def archive(self) -> None:
        name = self.project.Name
        if self.args.archive == 'project':
            tclargs = 'archive'
        elif self.args.archive == 'project-exclude-results':
            tclargs = 'archive_exclude_results'
        elif self.args.archive == 'project-include-settings':
            tclargs = 'archive_include_settings'
        else:
            raise Exception("Unknown value for argument --archive: {self.args.archive}")
        command = f"vivado {name}.xpr -mode batch -notrace -source run.tcl -tclargs {tclargs}".split()
        sh(command, cwd=self.builddir, output=True)
        raise SystemExit

    def get_files(self):
        files = []
        seen = []
        for f in self.project.DefaultDesign.Files():
            if 'implementation' in f[UsedIn] and f.Path not in seen:
                seen.append(f.Path)
                files.append(f)
        return files

    def setup(self):
        self.is_tool_setup()
        os.makedirs(self.builddir, exist_ok=True)

    def generate(self):
        templatedir = resources_files(self.templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)
        template = environment.get_template('project.tcl.j2')
        generate_from_template(template, self.builddir,
                               files=self.get_files(),
                               dict2str=dict2str,
                               VerilogIncludeFile=VerilogIncludeFile,
                               VerilogSourceFile=VerilogSourceFile,
                               SystemVerilogSourceFile=SystemVerilogSourceFile,
                               VHDLSourceFile=VHDLSourceFile,
                               ConstraintFile=ConstraintFile,
                               VivadoIPSpecificationFile=VivadoIPSpecificationFile,
                               VivadoProjectStepFile=VivadoProjectStepFile,
                               VivadoBDTclFile=VivadoBDTclFile,
                               EDIFNetlistFile=EDIFNetlistFile,
                               NetlistFile=NetlistFile,
                               project=self.project,
                               UsedIn=UsedIn)
        template = environment.get_template('run.tcl.j2')
        generate_from_template(template, self.builddir,
                               project=self.project)
        template = environment.get_template('launch_run.sh.j2')
        generate_from_template(template, self.builddir)
        command = "vivado -mode batch -notrace -source project.tcl".split()
        sh(command, cwd=self.builddir, output=True)

    def execute(self, step: str):
        name = self.project.Name
        command = f"vivado {name}.xpr -mode batch -notrace -source run.tcl -tclargs {step}".split()
        sh(command, cwd=self.builddir, output=True)

    def run(self) -> None:
        if self.args.archive:
            self.archive()
        if self.args.gui:
            projectfile = self.builddir.joinpath(f"{self.project.Name}.xpr")
            if not projectfile.exists():
                self.setup()
                self.generate()
            sh(['vivado', projectfile.name], cwd=self.builddir)
            return

        self.setup()
        self.generate()
        self.execute(self.args.step)
