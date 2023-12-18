from argparse import Namespace
import os
import logging
from pathlib import Path
import shutil

from typing import Dict, Any, List
from jinja2 import Template
from simplhdl.pyedaa.fileset import FileSet
from simplhdl.pyedaa.project import Project
from simplhdl.utils import sh
from simplhdl.flow import FlowFactory
from simplhdl.resources.templates import vcs as vcstemplates
from ..simulationflow import SimulationFlow

logger = logging.getLogger(__name__)


@FlowFactory.register('vcs')
class VcsFlow(SimulationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('vcs', help='Vcs HDL Simulation Flow')
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
            help="Open project in DVE or Verdi GUI"
        )
        parser.add_argument(
            '--simv-flags',
            default='',
            action='store',
            help="Extra flags for Vcs simv command"
        )
        parser.add_argument(
            '--vcs-flags',
            default='',
            action='store',
            help="Extra flags for Vcs vcs command"
        )
        parser.add_argument(
            '--vhdlan-flags',
            default='',
            action='store',
            help="Extra flags for Vcs vhdlan command"
        )
        parser.add_argument(
            '--vlogan-flags',
            default='',
            action='store',
            help="Extra flags for Vcs vlogan command"
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
            help="Set the simulator timescale for Verilog"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = vcstemplates

    def get_globals(self) -> Dict[str, Any]:
        globals = super().get_globals()
        globals['vlogan_flags'] = self.vlogan_flags()
        globals['vhdlan_flags'] = self.vhdlan_flags()
        globals['vcs_flags'] = self.vcs_flags()
        globals['simv_flags'] = self.simv_flags()
        return globals

    def get_project_templates(self, environment) -> List[Template]:
        return [
            environment.get_template('Makefile.j2'),
            environment.get_template('synopsys_sim.setup.j2'),
            environment.get_template('project.mk.j2')
        ]

    def get_cocotb_templates(self, environment):
        if self.cocotb.enabled:
            return [
                environment.get_template('cocotb.mk.j2'),
                environment.get_template('pli.tab.j2')
            ]
        else:
            return list()

    def fileset_verilog_flags(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"+v2k -work {library.Name}"

    def fileset_systemverilog_flags(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"-sverilog -work {library.Name}"

    def fileset_vhdl_flags(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"-vhdl08 -work {library.Name}"

    def vlogan_flags(self) -> str:
        flags = set()
        for name, value in self.project.Defines.items():
            flags.add(f"+define+{name}={value}")
        if self.args.verbose == 0:
            flags.add('-q')
        elif self.args.verbose > 1:
            flags.add('-V')
        if self.is_verdi():
            flags.add('-kdb')
        return ' '.join(list(flags) + [self.args.vlogan_flags]).strip()

    def vhdlan_flags(self) -> str:
        flags = set()
        if self.args.verbose == 0:
            flags.add('-q')
        elif self.args.verbose > 1:
            flags.add('-verbose')
        if self.args.gui and self.is_verdi():
            flags.add('-kdb')
        return ' '.join(list(flags) + [self.args.vhdlan_flags]).strip()

    def vcs_flags(self) -> str:
        flags = set()
        if self.args.verbose == 0:
            flags.add('-q')
        if self.args.timescale:
            flags.add(f"-timescale={self.args.timescale}")
        if self.args.gui:
            flags.add('-debug_access+all')
            if self.is_verdi():
                flags.add('-kdb')
        for name, value in self.project.Generics.items():
            flags.add(f"-pvalue+{name}={value}")
        for name, value in self.project.Parameters.items():
            flags.add(f"-pvalue+{name}={value}")
        return ' '.join(list(flags) + [self.args.vcs_flags])

    def simv_flags(self) -> str:
        flags = set()
        flags.add(f"+ntb_random_seed={self.args.seed}")
        for name, value in self.project.PlusArgs.items():
            flags.add(f"+{name}={value}")
        return ' '.join(list(flags) + [self.args.simv_flags])

    def get_library(self, fileset: FileSet) -> str:
        try:
            library = fileset.VHDLLibrary.Name
        except AttributeError:
            # TODO: This is a workaround The default fileset is FileSet
            #       which is bugged. Because it is empty we don't need it
            #       anyway and can just ignore it.
            library = ''
        return library

    def execute(self, step: str) -> None:
        self.run_hooks('pre')
        sh(['make', 'compile'], cwd=self.builddir, output=True)
        if step == 'compile':
            return

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
        if (shutil.which('vlogan') is None or
                shutil.which('vhdlan') is None or
                shutil.which('vcs') is None):
            raise Exception("Vcs is not setup correctly")

    def is_verdi(self) -> bool:
        return (os.environ.get('SNPS_SIM_DEFAULT_GUI') == 'verdi' or
                os.environ.get('VERDI_HOME'))
