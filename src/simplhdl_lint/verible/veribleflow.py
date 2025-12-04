try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import logging
import os
from argparse import Namespace
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from simplhdl import Project
from simplhdl.plugin import FlowBase, FlowError
from simplhdl.pyedaa import (
    SystemVerilogSourceFile,
    VerilogIncludeFile,
    VerilogSourceFile,
)
from simplhdl.utils import CalledShError, generate_from_template, sh

from ..resources.templates import verible as templates

logger = logging.getLogger(__name__)


class VeribleFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('verible-verilog-lint', help='Verible Lint Flow')
        parser.add_argument(
            '--fix',
            action='store_true',
            help="Fix style formatting (Note: this modifies the source)"
        )
        parser.add_argument(
            '-r', '--rules',
            action='store',
            help="Rule configuration file"
        )
        parser.add_argument(
            '-f', '--files',
            type=lambda p: Path(p).absolute(),
            nargs='+',
            default=[],
            help="Manually specify file list"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = templates

    def setup(self):
        os.makedirs(self.builddir, exist_ok=True)

    def generate(self):
        if self.args.rules:
            self.rules = self.args.rules
        elif os.getenv('SIMPLHDL_VERIBLE_CONFIG'):
            rules = os.getenv('SIMPLHDL_VERIBLE_CONFIG')
            if not Path(rules).exists():
                raise FlowError(f"Rules file {rules} does not exist")
            self.rules = rules
        else:
            templatedir = resources_files(self.templates)
            environment = Environment(
                loader=FileSystemLoader(templatedir),
                trim_blocks=True)
            template = environment.get_template('rules.cfg.j2')
            generate_from_template(template, self.builddir)
            self.rules = 'rules.cfg'

    def execute(self):
        errors = False
        command = [
            "verible-verilog-lint",
            "--check_syntax=false",
            "--ruleset=none",
            "--rules_config", self.rules
        ]

        if self.args.fix:
            command += ["--autofix=inplace"]

        file_types = [VerilogIncludeFile, VerilogSourceFile, SystemVerilogSourceFile]
        files = [f for f in self.project.DefaultDesign.Files() if f.FileType in file_types]
        for file in files:
            try:
                cmd = command + [str(file.Path)]
                sh(cmd, cwd=self.builddir, output=True)
            except CalledShError as e:
                errors = True
                print(e)

        if errors:
            return SystemError

    def run(self) -> None:
        self.setup()
        self.generate()
        self.execute()
