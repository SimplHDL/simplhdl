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

from simplhdl.resources.templates import flake8 as templates
from simplhdl.utils import sh, CalledShError, generate_from_template
from simplhdl.flow import FlowFactory, FlowBase
from simplhdl.pyedaa.project import Project
from simplhdl.pyedaa import PythonSourceFile

logger = logging.getLogger(__name__)


@FlowFactory.register('flake8')
class Flake8Flow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('flake8', help='Lint Flow for Python code')
        parser.add_argument(
            '--fix',
            action='store_true',
            help="Fix style formatting (Note: this modifies the source)"
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
        if self.args.files:
            self.files = [Path(f) for f in self.args.files if Path(f).suffix == '.py']
        else:
            self.files = [f.Path for f in self.project.DefaultDesign.DefaultFileSet.Files(PythonSourceFile)]

    def generate(self):
        config = os.getenv('SIMPLHDL_FLAKE8_RULES')
        if config:
            shutil.copy(config, self.builddir.joinpath('setup.cfg'))
        else:
            templatedir = resources_files(self.templates)
            environment = Environment(
                loader=FileSystemLoader(templatedir),
                trim_blocks=True)
            template = environment.get_template('setup.cfg.j2')
            generate_from_template(template, self.builddir)

    def execute(self):
        if self.args.fix:
            for file in self.files:
                sh(['black', str(file.absolute())])
        else:
            command = ['flake8'] + [str(f.absolute()) for f in self.files]
            try:
                sh(command, cwd=self.builddir, output=True)
            except CalledShError as e:
                print(e)
                raise SystemError

            # flake = flake8.get_style_guide()
            # report = flake.check_files(self.files)
            # if report.get_statistics('E'):
            #     raise SystemError

    def run(self) -> None:
        self.setup()
        self.generate()
        self.execute()
