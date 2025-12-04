import os
import logging
from argparse import Namespace
from pathlib import Path

from simplhdl.flow import FlowFactory, FlowBase
from simplhdl.pyedaa.project import Project
from simplhdl.flows.verible.veribleflow import VeribleFlow
from simplhdl.flows.vsg.vsgflow import VsgFlow
from simplhdl.flows.flake8.flake8flow import Flake8Flow

logger = logging.getLogger(__name__)


@FlowFactory.register('lint')
class LintFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('lint', help='Lint Flow for Design and Verification code')
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

    def setup(self):
        os.makedirs(self.builddir, exist_ok=True)

    def generate(self):
        pass

    def execute(self):
        verible_args = Namespace(rules=None, files=self.args.files, fix=self.args.fix)
        verible = VeribleFlow('verible', verible_args, self.project, self.builddir)
        vsg_args = Namespace(rules=None, files=self.args.files, fix=self.args.fix, output_format='syntastic')
        vsg = VsgFlow('vsg', vsg_args, self.project, self.builddir)
        flake_args = Namespace(files=self.args.files, fix=self.args.fix)
        flake = Flake8Flow('flake8', flake_args, self.project, self.builddir)
        system_error = False
        try:
            verible.run()
        except SystemError:
            system_error = True

        try:
            vsg.run()
        except SystemError:
            system_error = True

        try:
            flake.run()
        except SystemError:
            system_error = True

        if system_error:
            raise SystemError

    def run(self) -> None:
        self.setup()
        self.generate()
        self.execute()
