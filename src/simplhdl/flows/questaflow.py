try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import os
import logging
import shutil

from argparse import Namespace
from pathlib import Path
from typing import Callable, Generator, List, Dict, Tuple
from jinja2 import Environment, FileSystemLoader
from ..pyedaa import (File, VerilogSourceFile, VerilogIncludeFile,
                      SystemVerilogSourceFile, VHDLSourceFile)

from ..pyedaa.project import Project
from ..pyedaa.fileset import FileSet
from ..utils import sh, generate_from_template, md5sum, append_suffix
from ..flow import FlowFactory, FlowBase, FlowCategory, FlowError
from ..resources.templates import questa as templates
from ..cocotb import Cocotb

logger = logging.getLogger(__name__)


@FlowFactory.register('questa')
class QuestaFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('questa', help='Questa HDL Simulation Flow')
        parser.add_argument(
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
            metavar='FLAGS',
            help="Extra flags for Questa vsim command"
        )
        parser.add_argument(
            '--vmap-flags',
            default='',
            action='store',
            metavar='FLAGS',
            help="Extra flags for Questa vmap command"
        )
        parser.add_argument(
            '--vcom-flags',
            default='',
            action='store',
            metavar='FLAGS',
            help="Extra flags for Questa vcom command"
        )
        parser.add_argument(
            '--vlog-flags',
            default='',
            action='store',
            metavar='FLAGS',
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
        parser.add_argument(
            '--timescale',
            action='store',
            help="Set the simulator timescale for Verilog"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.category = FlowCategory.SIMULATION
        self.hdl_language = None
        self.cocotb = Cocotb(project)

    def run(self) -> None:
        self.validate()
        self.configure()
        self.generate()
        self.execute(self.args.step)

    def validate(self):
        if not self.project.DefaultDesign.TopLevel:
            raise FlowError("Simulation top level is not defined")
        for file in self.project.DefaultDesign.Files():
            if not file.Path.exists():
                raise FileNotFoundError(f"{file.Path}: doesn't exits")

    def configure(self):
        os.makedirs(self.builddir, exist_ok=True)
        self.is_tool_setup()
        os.environ['RANDOM_SEED'] = str(self.args.seed)
        if self.cocotb.enabled:
            os.environ['MODULE'] = self.cocotb.module()

    def generate(self):
        templatedir = resources_files(templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)

        template = environment.get_template('Makefile.j2')
        generate_from_template(template, self.builddir, vsim_flags=self.vsim_flags())

        template = environment.get_template('project.mk.j2')
        toplevels = ' '.join([t for t in self.project.DefaultDesign.TopLevel.split() if t != self.cocotb.module()])
        generate_from_template(
            template,
            self.builddir,
            toplevels=toplevels,
            libraries=' '.join([lib.Name for lib in self.project.DefaultDesign.VHDLLibraries.values()]))

        if self.cocotb.enabled:
            template = environment.get_template('cocotb.mk.j2')
            generate_from_template(template, self.builddir, pythonpath=self.cocotb.pythonpath)

        walker = FileSetWalker()
        fileset_makefiles: List[str] = list()
        for fileset in walker.walk(self.project.DefaultDesign.DefaultFileSet, reverse=True):
            for language in ['verilog', 'systemverilog', 'vhdl']:
                fileset_makefiles += self.generate_fileset_makefiles(environment, language, fileset)
        rules = self.generate_fileset_dependencies(fileset_makefiles)
        template = environment.get_template('dependencies.mk.j2')
        generate_from_template(template, self.builddir, rules=rules)

    def generate_fileset_dependencies(self, filelist: List[Path]):
        """Generate a dependency makefile for filesets. There a two type of
           make rules.
           1. the vhdl fileset depends in the verilog fileset, i.e. the verilog
              filesets needs to be compiled first.
           2. A fileset depends on its children filesets.

        Args:
            filelist (List[str]): List of generated makefile filesets.
        """
        walker = FileSetWalker()
        rules: Dict[str, List[str]] = dict()
        for fileset in walker.walk(self.project.DefaultDesign.DefaultFileSet, reverse=False):
            name = md5sum(fileset.Name)
            dependencies = []
            for language_fileset in [f for f in filelist if f.stem.startswith(name)]:
                for child in fileset.FileSets.values():
                    child_name = md5sum(child.Name)
                    dependencies += [append_suffix(f, '.com').name for f in filelist
                                     if f.stem.startswith(child_name)]
                    if dependencies:
                        rules[append_suffix(language_fileset, '.com').name] = dependencies
        return rules

    def generate_fileset_makefiles(self, environment: Environment, language: str, fileset: FileSet) -> List[Path]:
        table: Dict[str, Tuple[List[File], Callable]] = {
            'verilog': ([VerilogSourceFile, VerilogIncludeFile], self.vlog_flags),
            'systemverilog': ([SystemVerilogSourceFile, VerilogIncludeFile], self.svlog_flags),
            'vhdl': ([VHDLSourceFile], self.vcom_flags),
        }
        filetypes, flags = table[language]
        files = [f for f in fileset.GetFiles() if f.FileType in filetypes]
        name = md5sum(fileset.Name)
        base = self.builddir.joinpath(f"{name}-{language}")
        generated: List[str] = list()
        if [f for f in files if not isinstance(f, VerilogIncludeFile)]:
            template = environment.get_template('files.j2')
            generate_from_template(
                template,
                base.with_suffix('.files'),
                target=base.with_suffix('.fileset'),
                files=[f.Path.absolute() for f in files])
            template = environment.get_template('fileset.j2')
            output = base.with_suffix('.fileset')
            includes = {f.Path.parent.absolute() for f in files if isinstance(f, VerilogIncludeFile)}
            files = [f.Path.absolute() for f in files if not isinstance(f, VerilogIncludeFile)]
            generate_from_template(template, output, flags=flags(fileset), includes=includes, files=files)
            generated.append(output)
        return generated

    def svlog_flags(self, fileset: FileSet) -> str:
        library = self.get_library(fileset)
        quiet = '-quiet' if self.args.verbose == 0 else ''
        return f"-sv {quiet} -work {library} {self.args.vlog_flags}".strip()

    def vlog_flags(self, fileset: FileSet) -> str:
        library = self.get_library(fileset)
        quiet = '-quiet' if self.args.verbose == 0 else ''
        return f"{quiet} -work {library} {self.args.vlog_flags}".strip()

    def vcom_flags(self, fileset: FileSet) -> str:
        library = self.get_library(fileset)
        quiet = '-quiet' if self.args.verbose == 0 else ''
        return f"-2008 {quiet} -work {library} {self.args.vcom_flags}".strip()

    def vsim_flags(self) -> str:
        flags = set()
        flags.add(f"-sv_seed {self.args.seed}")
        if self.args.verbose == 0:
            flags.add('-quiet')
        if self.args.timescale:
            flags.add(f"-timescale {self.args.timescale}")
        if self.cocotb.enabled:
            if self.hdl_language == 'vhdl':
                flags.add(f"-foreign {self.cocotb.lib_name_path('questa', 'fli')}")
            else:
                flags.add(f"-pli {self.cocotb.lib_name_path('questa', 'vpi')}")
            flags.add("-no_autoacc")
        for name, value in self.project.Generics.items():
            flags.add(f"-g{name}={value}")
        for name, value in self.project.Parameters.items():
            flags.add(f"-g{name}={value}")
        for name, value in self.project.Defines.items():
            flags.add(f"+define+{name}={value}")
        for name, value in self.project.PlusArgs.items():
            flags.add(f"+{name}={value}")
        return ' '.join(list(flags) + [self.args.vsim_flags])

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

        if self.cocotb.enabled:
            for toplevel in [t for t in self.project.DefaultDesign.TopLevel.split() if t != self.cocotb.module()]:
                # TODO: what should happend if no top or both a Verilog and VHDL top
                self.hdl_language = get_hdl_language(toplevel, directory=self.builddir)
                os.environ['SIMPLHDL_LANGUAGE'] = self.hdl_language

        if self.args.do:
            if Path(self.args.do).exists():
                os.environ['DO_CMD'] = f"-do {Path(self.args.do).absolute()}"
            else:
                os.environ['DO_CMD'] = f"-do '{self.args.do}'"

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
        if (shutil.which('vlog') is None or
                shutil.which('vsim') is None or
                shutil.which('vcom') is None or
                shutil.which('vlib') is None or
                shutil.which('vmap') is None):
            raise Exception("Questa is not setup correctly")


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


class FileSetWalker:

    def __init__(self):
        self.__visited: List = list()

    def walk(self, fileset: FileSet, reverse=False) -> Generator[FileSet, None, None]:
        if fileset.Name not in self.__visited:
            self.__visited.append(fileset.Name)
            if reverse is False:
                yield fileset
            for child in fileset.FileSets.values():
                yield from self.walk(child, reverse)
            if reverse:
                yield fileset
