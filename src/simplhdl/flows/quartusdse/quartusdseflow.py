import shutil
import logging

from argparse import Namespace
from pathlib import Path

from simplhdl.flow import FlowFactory, FlowTools
from simplhdl.flows.implementationflow import ImplementationFlow
from simplhdl.flows.quartusflow import QuartusFlow
from simplhdl.resources.templates import quartus as templates
from simplhdl.utils import sh
from simplhdl.pyedaa.project import Project

logger = logging.getLogger(__name__)


@FlowFactory.register('quartus-dse')
class QuartusDseFlow(ImplementationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('quartus-dse', help='Quartus Design Space Explore Flow')
        parser.add_argument(
            '--gui',
            action='store_true',
            help="Open project in Quartus GUI"
        )
        parser.add_argument(
            '--dse-args',
            default='',
            action='store',
            metavar='ARGS',
            help="Extra arguments for Quartus Design Space Explore command"
        )
        parser.add_argument(
            '--dse-file',
            action='store',
            metavar='FILE',
            help="The .dse configuration file to be used for this project"
        )
        parser.add_argument(
            '--num-seeds',
            action='store',
            help="Number of seeds to sweep as part of the exploration space. "
                 + "DSE auto-generates seed values when this is provided"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = templates
        self.tools.add(FlowTools.QUARTUS)

    def run(self) -> None:
        quartus = QuartusFlow('quartus', None, self.project, self.builddir)
        quartus.validate()
        quartus.configure()
        quartus.generate()
        self.execute()

    def execute(self):
        name = self.project.Name
        if self.args.gui:
            sh(['quartus_dsew', name], cwd=self.builddir)
            return
        args = self.args.dse_args
        if self.args.num_seeds:
            args += f" --num-seeds {self.args.num_seeds}"
        if self.args.dse_file:
            args += f" --use-dse-file {self.args.dse_file}"
        command = f"quartus_dse {args} {name}".split()
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
