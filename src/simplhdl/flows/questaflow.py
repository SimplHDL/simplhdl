import os
import logging
import shutil

from argparse import Namespace
from pathlib import Path
from edalize.edatool import get_edatool
import pyEDAA.ProjectModel as pm  # type: ignore

from ..project import Project
from ..utils import sh
from ..flow import FlowFactory, FlowBase

logger = logging.getLogger(__name__)


@FlowFactory.register('questa')
class QuestaFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('questa', help='Questa HDL Simulation Flow')
        parser.add_argument(
            '-s',
            '--step',
            action='store',
            choices=['compile', 'elaborate', 'simulate'],
            default='simulate',
            help="flow step to run"
        )
        parser.add_argument(
            '-w',
            '--wave',
            action='store_true',
            help="Dump waveforms"
        )
        parser.add_argument(
            '--gui',
            action='store_true',
            help="Open project in Questa GUI"
        )

    def run(self, args: Namespace, project: Project, builddir: Path) -> None:
        self.project = project
        # NOTE: edalize only supports questa through Modelsim
        simulator = 'modelsim'
        self.is_tool_setup()
        self.cocotb()
        edam = self.project.export_edam()
        if self.is_cocotb():
            edam['tool_options'] = {
                simulator: {'vsim_options': ['-no_autoacc', '-pli', get_lib_name_path('vpi', simulator)]},
            }

        for f in edam['files']:
            logger.debug(f)
        backend = get_edatool(simulator)(edam=edam, work_root=builddir)
        shutil.rmtree(builddir, ignore_errors=True)
        os.makedirs(builddir, exist_ok=True)
        backend.configure()
        backend.build()
        backend.run()

    def cocotb(self):
        if self.is_cocotb():
            libpython = sh(['cocotb-config', '--libpython']).strip()
            os.environ['LIBPYTHON_LOC'] = libpython
            os.environ['GPI_EXTRA'] = f"{get_lib_name_path('fli', 'questa')}:cocotbfli_entry_point"
            os.environ['MODULE'] = 'test_adder'
            os.environ['PYTHONPATH'] = '/home/rgo/devel/cocotb-example/cores/adder.core/verif/cocotb'
            os.environ['RANDOM_SEED'] = '1'

    def is_cocotb(self) -> bool:
        if [True for f in self.project.DefaultDesign.Files() if f.FileType == pm.CocotbPythonFile]:
            return True
        return False

    def is_tool_setup(self) -> None:
        if (shutil.which('vlog') is None or
                shutil.which('vsim') is None or
                shutil.which('vcom') is None or
                shutil.which('vlib') is None or
                os.getenv('MODEL_TECH') is None):
            raise Exception("Questa is not setup correctly")


def get_lib_name_path(interface: str, simulator: str) -> str:
    lib_name_path = sh(['cocotb-config', '--lib-name-path', interface, simulator]).strip()
    return lib_name_path
