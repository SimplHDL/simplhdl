try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import os
import shutil
import logging
from jinja2 import Environment, FileSystemLoader

from ..flow import FlowFactory, FlowBase
from ..resources.templates import vivado as templates
from ..utils import sh, generate_from_template, dict2str
from ..pyedaa import (IPSpecificationFile, VerilogIncludeFile, VerilogSourceFile,
                      SystemVerilogSourceFile, VHDLSourceFile, ConstraintFile,
                      EDIFNetlistFile, NetlistFile)

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
            action='store_true',
            help="Archive Vivado project and results"
        )

    def is_tool_setup(self) -> None:
        exit: bool = False
        if shutil.which('vivado') is None:
            logger.error('vivado: not found in PATH')
            exit = True
        if exit:
            raise FileNotFoundError("Vivado is not setup correctly")

    def archive(self) -> None:
        name = self.project.Name
        # command = f"vivado {name}.xpr -mode batch -notrace -source run.tcl -tclargs archive".split()
        command = f"vivado {name}.xpr -mode batch -source run.tcl -tclargs archive".split()
        print(command)
        sh(command, cwd=self.builddir, output=True)
        raise SystemExit

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
                               dict2str=dict2str,
                               VerilogIncludeFile=VerilogIncludeFile,
                               VerilogSourceFile=VerilogSourceFile,
                               SystemVerilogSourceFile=SystemVerilogSourceFile,
                               VHDLSourceFile=VHDLSourceFile,
                               ConstraintFile=ConstraintFile,
                               IPSpecificationFile=IPSpecificationFile,
                               EDIFNetlistFile=EDIFNetlistFile,
                               NetlistFile=NetlistFile,
                               project=self.project)
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
        # jsonfile = self.builddir.joinpath('runs.json')
        # with jsonfile.open() as f:
        #     runs: Dict[str, List[str]] = json.load(f)
        # for name, run in runs.items():
        #     for script in run:
        #         sh(['bash', 'launch_run.sh', script], output=True, cwd=self.builddir)

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
