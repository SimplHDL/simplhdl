try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import os
import logging
import shutil

from argparse import Namespace
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from hashlib import md5
import pyEDAA.ProjectModel as pm  # type: ignore

from ..project import Project
from ..utils import sh, generate_from_template
from ..flow import FlowFactory, FlowBase
from ..resources.templates import vcs as templates

logger = logging.getLogger(__name__)


@FlowFactory.register('vcs')
class QuestaFlow(FlowBase):

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

    def run(self, args: Namespace, project: Project, builddir: Path) -> None:
        self.project = project
        self.builddir = builddir
        self.args = args
        self.configure()
        self.generate()
        self.execute(args.step)

    def configure(self):
        os.makedirs(self.builddir, exist_ok=True)
        self.is_tool_setup()

    def generate(self):
        templatedir = resources_files(templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)

        template = environment.get_template('Makefile.j2')
        generate_from_template(template, self.builddir)

        template = environment.get_template('project.mk.j2')
        generate_from_template(
            template,
            self.builddir,
            toplevels=self.project.DefaultDesign.TopLevel,
            libraries=' '.join([lib.Name for lib in self.project.DefaultDesign.VHDLLibraries.values()]))

        template = environment.get_template('synopsys_sim.setup.j2')
        defaultlib = next(iter(self.project.DefaultDesign.VHDLLibraries.values()))
        generate_from_template(
            template,
            self.builddir,
            defaultlib=defaultlib,
            libraries=self.project.DefaultDesign.VHDLLibraries.values())

        for fileset in self.project.DefaultDesign.FileSets.values():
            name = md5(fileset.Name.encode()).hexdigest()
            files = [f.Path for f in fileset.Files() if f.FileType == pm.VerilogSourceFile]
            try:
                library = fileset.VHDLLibrary.Name
            except AttributeError:
                # TODO: This is a workaround The default fileset is pm.FileSet
                #       which is bugged. Because it is empty we don't need it
                #       anyway and can just ignore it.
                library = ''
            if files:
                template = environment.get_template('fileset.j2')
                output = self.builddir.joinpath(f"{name}.verilog.fileset")
                flags = f"-work {library} {self.args.vlogan_flags}"
                generate_from_template(template, output, flags=flags, files=files)
                template = environment.get_template('files.j2')
                output = self.builddir.joinpath(f"{name}.verilog.files")
                generate_from_template(template, output, target=f"{name}.verilog.fileset", files=files)
            files = [f.Path for f in fileset.Files() if f.FileType == pm.SystemVerilogSourceFile]
            if files:
                template = environment.get_template('fileset.j2')
                output = self.builddir.joinpath(f"{name}.systemverilog.fileset")
                flags = f"-sverilog -work {library} {self.args.vlogan_flags}"
                generate_from_template(template, output, flags=flags, files=files)
                template = environment.get_template('files.j2')
                output = self.builddir.joinpath(f"{name}.systemverilog.files")
                generate_from_template(template, output, target=f"{name}.systemverilog.fileset", files=files)
            files = [f.Path for f in fileset.Files() if f.FileType == pm.VHDLSourceFile]
            if files:
                template = environment.get_template('fileset.j2')
                output = self.builddir.joinpath(f"{name}.vhdl.fileset")
                flags = f"-vhdl08 -work {library} {self.args.vhdlan_flags}"
                generate_from_template(template, output, flags=flags, files=files)
                template = environment.get_template('files.j2')
                output = self.builddir.joinpath(f"{name}.vhdl.files")
                generate_from_template(template, output, target=f"{name}.vhdl.fileset", files=files)

    def execute(self, step: str) -> None:
        if self.args.gui:
            sh(['make', 'gui'], cwd=self.builddir)
            return
        sh(['make', step], cwd=self.builddir, output=True)

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
        if (shutil.which('vlogan') is None or
                shutil.which('vhdlan') is None or
                shutil.which('vcs') is None):
            raise Exception("Vcs is not setup correctly")


def get_lib_name_path(interface: str, simulator: str) -> str:
    lib_name_path = sh(['cocotb-config', '--lib-name-path', interface, simulator]).strip()
    return lib_name_path
