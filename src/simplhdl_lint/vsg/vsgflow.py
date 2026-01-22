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
from simplhdl.project.files import VhdlFile
from simplhdl.utils import CalledShError, generate_from_template, sh

from ..resources.templates import vsg as templates

logger = logging.getLogger(__name__)


class VsgFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('vhdl-style-guide', help='VHDL Style Guide Flow')
        parser.add_argument(
            '--output-format',
            choices=[
                'vsg',
                'syntastic',
                'summary'
            ],
            default=None,
            help="Display output format"
        )
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
        # file limit to change output for to summary
        self.file_limit: int = 5

    def setup(self):
        os.makedirs(self.builddir, exist_ok=True)

    def generate(self):
        templatedir = resources_files(self.templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)
        template = environment.get_template('files.json.j2')
        generate_from_template(template, self.builddir,
                               VHDLSourceFile=VhdlFile,
                               project=self.project)
        if self.args.rules:
            self.rules = self.args.rules
        elif os.getenv('SIMPLHDL_VSG_CONFIG'):
            rules = os.getenv('SIMPLHDL_VSG_CONFIG')
            if not Path(rules).exists():
                raise FlowError(f"Rules file {rules} does not exist")
            self.rules = rules
        else:
            template = environment.get_template('rules.yml.j2')
            generate_from_template(template, self.builddir)
            self.rules = 'rules.yml'

    def execute(self):
        command = ["vsg"]
        user_files = len(self.args.files)
        project_files = len(list(self.project.defaultDesign.files(VhdlFile)))

        if self.args.fix:
            command.append("--fix")
        elif self.args.output_format is None:
            if user_files > self.file_limit:
                format = "summary"
            elif project_files > self.file_limit and not user_files:
                format = "summary"
            else:
                format = "vsg"
            command += f"-ap -of {format}".split()
        else:
            command += f"-ap -of {self.args.output_format}".split()

        if user_files:
            if self.rules:
                command += f"-c {self.rules}".split()
            command += ['-f'] + [str(f.absolute()) for f in self.args.files]
        elif project_files:
            command += f"-c {self.rules} files.json".split()
        else:
            raise FlowError("No VHDL files")

        try:
            sh(command, cwd=self.builddir, output=True)
        except CalledShError as e:
            print(e)
            raise SystemError

    def run(self) -> None:
        self.setup()
        self.generate()
        self.execute()
