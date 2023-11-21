try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import os
import shutil
import logging

from jinja2 import Environment, FileSystemLoader

from ..flow import FlowFactory, FlowBase
from ..resources.templates import quartus as templates
from ..utils import sh, generate_from_template
from ..pyedaa import (IPSpecificationFile, VerilogIncludeFile, VerilogSourceFile,
                      SystemVerilogSourceFile, VHDLSourceFile, ConstraintFile,
                      EDIFNetlistFile, NetlistFile, SettingFile)

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
            choices=['synthesis', 'implement', 'finalize', 'compile'],
            default='compile',
            help="flow step to run"
        )
        parser.add_argument(
            '--gui',
            action='store_true',
            help="Open project in Quartus GUI"
        )
        parser.add_argument(
            '--archive',
            action='store_true',
            help="Archive Quartus project and results"
        )

    def run(self) -> None:
        if self.args.archive:
            self.archive()
        self.validate()
        self.configure()
        self.generate()
        self.execute(self.args.step)

    def archive(self) -> None:
        name = self.project.Name
        command = f"quartus_sh --archive -use_file_set full_db -revision {name} -no_discover -output {name}.qar {name}"
        sh(command.split(), output=True, cwd=self.builddir)
        raise SystemExit

    def validate(self):
        if self.project.DefaultDesign.DefaultFileSet.TopLevel is None:
            raise Exception("No top level specified")

    def configure(self):
        os.makedirs(self.builddir, exist_ok=True)
        self.is_tool_setup()

    def generate(self):
        templatedir = resources_files(templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)

        template = environment.get_template('project.tcl.j2')
        project_updated = generate_from_template(
            template, self.builddir,
            VerilogIncludeFile=VerilogIncludeFile,
            VerilogSourceFile=VerilogSourceFile,
            SystemVerilogSourceFile=SystemVerilogSourceFile,
            VHDLSourceFile=VHDLSourceFile,
            ConstraintFile=ConstraintFile,
            IPSpecificationFile=IPSpecificationFile,
            EDIFNetlistFile=EDIFNetlistFile,
            NetlistFile=NetlistFile,
            SettingFile=SettingFile,
            project=self.project)
        template = environment.get_template('run.tcl.j2')
        generate_from_template(template, self.builddir,
                               project=self.project)
        command = "quartus_sh -t project.tcl".split()
        self.is_tool_setup()
        if project_updated:
            sh(command, cwd=self.builddir, output=True)

    def execute(self, step: str):
        name = self.project.Name
        if self.args.gui:
            sh(['quartus', name], cwd=self.builddir)
            return

        command = f"quartus_sh -t run.tcl {step} -project {name}".split()
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
