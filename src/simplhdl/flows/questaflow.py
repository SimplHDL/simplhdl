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
from ..resources.templates import questa as templates

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
        parser.add_argument(
            '--vsim-flags',
            default='',
            action='store',
            help="Extra flags for Questa vsim command"
        )
        parser.add_argument(
            '--vmap-flags',
            default='',
            action='store',
            help="Extra flags for Questa vmap command"
        )
        parser.add_argument(
            '--vcom-flags',
            default='',
            action='store',
            help="Extra flags for Questa vcom command"
        )
        parser.add_argument(
            '--vlog-flags',
            default='',
            action='store',
            help="Extra flags for Questa vlog command"
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=1,
            action='store',
            help="Seed to initialize random generator"
        )
        parser.add_argument(
            '--random-seed',
            action='store_true',
            help="Generate a random seed to initialize random generator"
        )
        parser.add_argument(
            '--do',
            metavar='COMMAND',
            action='store',
            help="Do command to start simulation"
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
        generate_from_template(template, self.builddir, vsim_flags=self.vsim_flags)

        template = environment.get_template('project.mk.j2')
        generate_from_template(
            template,
            self.builddir,
            toplevels=self.project.DefaultDesign.TopLevel,
            libraries=' '.join([lib.Name for lib in self.project.DefaultDesign.VHDLLibraries.values()]))

        for fileset in self.project.DefaultDesign.FileSets.values():
            name = md5(fileset.Name.encode()).hexdigest()
            try:
                library = fileset.VHDLLibrary.Name
            except AttributeError:
                # TODO: This is a workaround The default fileset is pm.FileSet
                #       which is bugged. Because it is empty we don't need it
                #       anyway and can just ignore it.
                library = ''

            files = [f for f in fileset.Files() if f.FileType == pm.VerilogSourceFile]
            if files:
                template = environment.get_template('files.j2')
                output = self.builddir.joinpath(f"{name}.verilog.files")
                generate_from_template(
                    template,
                    output,
                    target=f"{name}.verilog.fileset",
                    files=[f.Path.absolute() for f in files])
                template = environment.get_template('fileset.j2')
                output = self.builddir.joinpath(f"{name}.verilog.fileset")
                flags = f"-work {library} {self.args.vlog_flags}"
                includes = {f.Path.parent.absolute() for f in files if f.Path.suffix in ['.vh', '.svh']}
                files = [f.Path.absolute() for f in files if f.Path.suffix not in ['.vh', '.svh']]
                generate_from_template(template, output, flags=flags, includes=includes, files=files)

            files = [f for f in fileset.Files() if f.FileType == pm.SystemVerilogSourceFile]
            if files:
                template = environment.get_template('files.j2')
                output = self.builddir.joinpath(f"{name}.systemverilog.files")
                generate_from_template(
                    template,
                    output,
                    target=f"{name}.systemverilog.fileset",
                    files=[f.Path.absolute() for f in files])
                template = environment.get_template('fileset.j2')
                output = self.builddir.joinpath(f"{name}.systemverilog.fileset")
                flags = f"-sv -work {library} {self.args.vlog_flags}"
                includes = {f.Path.parent.absolute() for f in files if f.Path.suffix in ['.vh', '.svh']}
                files = [f.Path.absolute() for f in files if f.Path.suffix not in ['.vh', '.svh']]
                generate_from_template(template, output, flags=flags, includes=includes, files=files)

            files = [f for f in fileset.Files() if f.FileType == pm.VHDLSourceFile]
            if files:
                template = environment.get_template('files.j2')
                output = self.builddir.joinpath(f"{name}.vhdl.files")
                generate_from_template(
                    template,
                    output,
                    target=f"{name}.vhdl.fileset",
                    files=[f.Path.absolute() for f in files])
                template = environment.get_template('fileset.j2')
                output = self.builddir.joinpath(f"{name}.vhdl.fileset")
                flags = f"-2008 -work {library} {self.args.vcom_flags}"
                includes = {f.Path.parent.absolute() for f in files if f.Path.suffix in ['.vh', '.svh']}
                files = [f.Path.absolute() for f in files if f.Path.suffix not in ['.vh', '.svh']]
                generate_from_template(template, output, flags=flags, includes=includes, files=files)

    def execute(self, step: str) -> None:
        self.run_hooks('pre')
        if self.args.gui:
            command = ['make', 'gui']
        else:
            command = ['make', step]
        if self.args.do:
            if Path(self.args.do).exists():
                os.environ['DO_CMD'] = f"-do {Path(self.args.do).absolute()}"
            else:
                os.environ['DO_CMD'] = f"-do '{self.args.do}'"
        sh(command, cwd=self.builddir, output=True)
        self.run_hooks('post')

    def run_hooks(self, name):
        try:
            for command in self.project.Hooks[name]:
                logger.info(f"Running {name} hook: {command}")
                sh(command.split(), cwd=self.builddir, output=True)
        except KeyError:
            pass

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
                shutil.which('vmap') is None):
            raise Exception("Questa is not setup correctly")

    @property
    def vsim_flags(self) -> str:
        flags = set()
        flags.add('-quiet')
        for name, value in self.project.Generics.items():
            flags.add(f"-g{name}={value}")
        for name, value in self.project.Parameters.items():
            flags.add(f"-g{name}={value}")
        for name, value in self.project.Defines.items():
            flags.add(f"+define+{name}={value}")
        for name, value in self.project.PlusArgs.items():
            flags.add(f"+{name}={value}")
        return ' '.join(list(flags) + [self.args.vsim_flags])


def get_lib_name_path(interface: str, simulator: str) -> str:
    lib_name_path = sh(['cocotb-config', '--lib-name-path', interface, simulator]).strip()
    return lib_name_path
