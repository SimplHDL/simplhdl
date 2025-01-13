try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import os
import shutil
import logging

from argparse import Namespace
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from ..flow import FlowFactory, FlowTools
from .implementationflow import ImplementationFlow
from ..resources.templates import quartus as templates
from ..utils import sh, generate_from_template
from ..pyedaa import (QuartusIPSpecificationFile, VerilogIncludeFile, VerilogSourceFile,
                      SystemVerilogSourceFile, VHDLSourceFile, ConstraintFile,
                      EDIFNetlistFile, NetlistFile, SettingFile, QuartusSignalTapFile,
                      QuartusIniFile, QuartusQIPSpecificationFile, QuartusQSYSSpecificationFile,
                      HDLSearchPath, VerilogIncludeSearchPath)
from ..pyedaa.project import Project
from ..pyedaa.attributes import UsedIn

logger = logging.getLogger(__name__)


@FlowFactory.register('quartus')
class QuartusFlow(ImplementationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('quartus', help='Quartus FPGA Build Flow')
        parser.add_argument(
            '-s',
            '--step',
            action='store',
            choices=['project', 'elaborate', 'implement', 'finalize', 'compile'],
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
            choices=[
                'project',
                'project-service-request',
                'project-source'
            ],
            help="Archive Quartus project, settings and results"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = templates
        self.tools.add(FlowTools.QUARTUS)

    def run(self) -> None:
        if self.args.archive:
            self.archive()
        self.validate()
        self.configure()
        self.generate()
        self.execute(self.args.step)

    def archive(self) -> None:
        name = self.project.Name
        if self.args.archive == 'project':
            fileset = 'full_db'
        elif self.args.archive == 'project-service-request':
            fileset = 'sr'
        elif self.args.archive == 'project-source':
            fileset = 'basic'
        else:
            raise Exception("Unknown value for argument --archive: {self.args.archive}")
        command = f"quartus_sh --archive -use_file_set {fileset} -revision {name} -no_discover -output {name}.qar {name}"  # noqa
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
            HDLSearchPath=HDLSearchPath,
            VerilogIncludeSearchPath=VerilogIncludeSearchPath,
            VerilogIncludeFile=VerilogIncludeFile,
            VerilogSourceFile=VerilogSourceFile,
            SystemVerilogSourceFile=SystemVerilogSourceFile,
            VHDLSourceFile=VHDLSourceFile,
            ConstraintFile=ConstraintFile,
            QuartusIPSpecificationFile=QuartusIPSpecificationFile,
            EDIFNetlistFile=EDIFNetlistFile,
            NetlistFile=NetlistFile,
            SettingFile=SettingFile,
            QuartusSignalTapFile=QuartusSignalTapFile,
            QuartusQIPSpecificationFile=QuartusQIPSpecificationFile,
            QuartusQSYSSpecificationFile=QuartusQSYSSpecificationFile,
            QuartusIniFile=QuartusIniFile,
            project=self.project,
            UsedIn=UsedIn)
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
