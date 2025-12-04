import os
import logging
import shutil

from argparse import Namespace
from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Template
from simplhdl.pyedaa.project import Project
from simplhdl.pyedaa.fileset import FileSet
from simplhdl.utils import sh, escape
from simplhdl.flow import FlowFactory, FlowTools
from simplhdl.resources.templates import xsim as xsimtemplates
from simplhdl.flows.simulationflow import SimulationFlow

logger = logging.getLogger(__name__)


@FlowFactory.register('xsim')
class XsimFlow(SimulationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('xsim', help='Xilinx Xsim HDL Simulation Flow')
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
            help="Open project in GUI"
        )
        parser.add_argument(
            '--xsim-args',
            default='',
            action='store',
            help="Extra args for Xsim xsim command"
        )
        parser.add_argument(
            '--xelab-args',
            default='',
            action='store',
            help="Extra args for Xsim xelab command"
        )
        parser.add_argument(
            '--xvhdl-args',
            default='',
            action='store',
            help="Extra args for Xsim xvhdl command"
        )
        parser.add_argument(
            '--xvlog-args',
            default='',
            action='store',
            help="Extra args for Xsim xvlog command"
        )
        parser.add_argument(
            '--seed',
            default='1',
            action='store',
            help="Seed to initialize random generator"
        )
        parser.add_argument(
            '--random-seed',
            action='store_true',
            help="Generate a random seed to initialize random generator"
        )
        parser.add_argument(
            '--timescale',
            default='1ns/1ps',
            action='store',
            help="Set the simulator timescale for Xsim"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = xsimtemplates
        self.tools.add(FlowTools.XSIM)

    def configure(self):
        super().configure()
        if self.cocotb.enabled:
            os.environ['MODULE'] = self.cocotb.module()
            raise NotImplementedError("Xsim currently doesn't support cocotb")

    def get_globals(self) -> Dict[str, Any]:
        globals = super().get_globals()
        globals['xvlog_args'] = self.xvlog_args()
        globals['xvhdl_args'] = self.xvhdl_args()
        globals['xelab_args'] = self.xelab_args()
        globals['xsim_args'] = self.xsim_args()
        return globals

    def get_project_templates(self, environment) -> List[Template]:
        return [
            environment.get_template('Makefile.j2'),
            environment.get_template('project.mk.j2')
        ]

    def get_cocotb_templates(self, environment):
        if self.cocotb.enabled:
            return [
                environment.get_template('cocotb.mk.j2')
            ]
        else:
            return list()

    def fileset_verilog_args(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"-work {library.Name}"

    def fileset_systemverilog_args(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"-sv -work {library.Name}"

    def fileset_vhdl_args(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"--2008 -work {library.Name}"

    def xvlog_args(self) -> str:
        args = set()
        args.add(f"-v {self.args.verbose if self.args.verbose < 2 else 2}")
        for name, value in self.project.Defines.items():
            args.add(f"-d {name}={escape(value)}")
        if self.is_uvm():
            args.add('-L uvm')
        return ' '.join(list(args) + [self.args.xvlog_args]).strip()

    def xvhdl_args(self) -> str:
        args = set()
        args.add(f"-v {self.args.verbose if self.args.verbose < 2 else 2}")
        return ' '.join(list(args) + [self.args.xvhdl_args])

    def xelab_args(self) -> str:
        args = set()
        verbosity = f"-v {self.args.verbose if self.args.verbose < 2 else 2}"
        args.add(verbosity)
        if self.args.timescale:
            args.add(f"--timescale={self.args.timescale}")
        for name, value in self.project.Generics.items():
            args.add(f"--generic_top {name}={escape(value)}")
        for name, value in self.project.Parameters.items():
            args.add(f"--generic_top {name}={escape(value)}")
        if self.args.wave or self.args.gui:
            args.add('-debug all')
        return ' '.join(list(args) + [self.args.xelab_args])

    def xsim_args(self) -> str:
        args = set()
        args.add(f"-sv_seed {self.args.seed}")
        if self.cocotb.enabled:
            # xsim currently doesn't work with cocotb
            pass
        for name, value in self.project.PlusArgs.items():
            args.add(f"--testplusarg {name}={escape(value)}")
        return ' '.join(list(args) + [self.args.xsim_args])

    def execute(self, step: str) -> None:
        self.run_hooks('pre')
        sh(['make', 'compile'], cwd=self.builddir, output=True)
        if step == 'compile':
            return

        if self.cocotb.enabled:
            for toplevel in [t for t in self.project.DefaultDesign.TopLevel.split() if t != self.cocotb.module()]:
                # TODO: what should happend in Vcs?
                # self.hdl_language = get_hdl_language(toplevel, directory=self.builddir)
                # os.environ['SIMPLHDL_LANGUAGE'] = self.hdl_language
                pass

        if self.args.gui:
            command = ['make', 'gui']
        else:
            command = ['make', step]
        sh(command, cwd=self.builddir, output=True)
        if step == 'simulate':
            self.run_hooks('post')

    def run_hooks(self, name):
        try:
            for command in self.project.Hooks[name]:
                logger.info(f"Running {name} hook: {command}")
                sh(command.split(), cwd=self.builddir, output=True)
        except KeyError:
            # NOTE: Continue if no hook is registret
            pass

    def is_tool_setup(self) -> None:
        if (shutil.which('xvlog') is None or
                shutil.which('xvhdl') is None or
                shutil.which('xsim') is None):
            raise Exception("Xsim is not setup correctly")


def get_hdl_language(name: str, directory: Path = Path.cwd()) -> str:
    """Get language of HDL module by inspecting the compiled libraries

    Args:
        name (str): Module/Entity name
        directory (Path): Directory of library locations

    Returns:
        str: Verilog or VHDL
    """
    info = sh(['vdir', '-prop', 'top', name], cwd=directory)
    if info.startswith('ENTITY'):
        return "vhdl"
    elif info.startswith('MODULE'):
        return "verilog"
    else:
        raise Exception(f"Unknow info: {info}")
