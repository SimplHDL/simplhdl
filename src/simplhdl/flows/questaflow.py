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
from hashlib import md5
from pyEDAA.ProjectModel import (File, CocotbPythonFile, VerilogSourceFile,
                                 SystemVerilogSourceFile, VHDLSourceFile)

from ..project import Project
from ..fileset import FileSet
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
        parser.add_argument(
            '--timescale',
            action='store',
            help="Set the simulator timescale for Verilog"
        )

    def run(self, args: Namespace, project: Project, builddir: Path) -> None:
        self.project = project
        self.builddir = builddir
        self.args = args
        self.hdl_language = None
        self.configure()
        self.generate()
        self.execute(args.step)

    def configure(self):
        os.makedirs(self.builddir, exist_ok=True)
        self.is_tool_setup()
        os.environ['RANDOM_SEED'] = str(self.args.seed)
        if self.has_cocotb_files():
            os.environ['MODULE'] = self.cocotb_module()

    def generate(self):
        templatedir = resources_files(templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)

        template = environment.get_template('Makefile.j2')
        generate_from_template(template, self.builddir, vsim_flags=self.vsim_flags())

        template = environment.get_template('project.mk.j2')
        toplevels = ' '.join([t for t in self.project.DefaultDesign.TopLevel.split() if not self.is_cocotb_module(t)])
        generate_from_template(
            template,
            self.builddir,
            toplevels=toplevels,
            libraries=' '.join([lib.Name for lib in self.project.DefaultDesign.VHDLLibraries.values()]))

        if self.has_cocotb_files():
            directories = {str(f.Path.parent.absolute()) for f in self.cocotb_files()}
            template = environment.get_template('cocotb.mk.j2')
            generate_from_template(template, self.builddir, directories=':'.join(directories))

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
            'verilog': ([VerilogSourceFile], self.vlog_flags),
            'systemverilog': ([SystemVerilogSourceFile], self.svlog_flags),
            'vhdl': ([VHDLSourceFile], self.vcom_flags),
        }
        filetypes, flags = table[language]
        files = [f for f in fileset.GetFiles() if f.FileType in filetypes]
        name = md5sum(fileset.Name)
        base = self.builddir.joinpath(f"{name}-{language}")
        generated: List[str] = list()
        if files:
            template = environment.get_template('files.j2')
            generate_from_template(
                template,
                base.with_suffix('.files'),
                target=base.with_suffix('.fileset'),
                files=[f.Path.absolute() for f in files])
            template = environment.get_template('fileset.j2')
            output = base.with_suffix('.fileset')
            includes = {f.Path.parent.absolute() for f in files if f.Path.suffix in ['.vh', '.svh']}
            files = [f.Path.absolute() for f in files if f.Path.suffix not in ['.vh', '.svh']]
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
        if self.args.verbose == 0:
            flags.add('-quiet')
        if self.args.timescale:
            flags.add(f"-timescale {self.args.timescale}")
        if self.has_cocotb_files():
            if self.hdl_language == 'vhdl':
                flags.add(f"-foreign {get_lib_name_path('fli', 'questa')}")
            else:
                flags.add(f"-pli {get_lib_name_path('vpi', 'questa')}")
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
        if self.args.gui:
            command = ['make', 'gui']
        else:
            sh(['make', 'compile'], cwd=self.builddir, output=True)
            if step == 'compile':
                return

        if self.cocotb_files():
            for toplevel in [t for t in self.project.DefaultDesign.TopLevel.split() if not self.is_cocotb_module(t)]:
                # TODO: what should happend if no top or both a Verilog and VHDL top
                self.hdl_language = get_hdl_language(toplevel, directory=self.builddir)
                os.environ['SIMPLHDL_LANGUAGE'] = self.hdl_language

        if self.args.do:
            if Path(self.args.do).exists():
                os.environ['DO_CMD'] = f"-do {Path(self.args.do).absolute()}"
            else:
                os.environ['DO_CMD'] = f"-do '{self.args.do}'"
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

    def cocotb_files(self):
        return self.project.DefaultDesign.Files(CocotbPythonFile)

    def has_cocotb_files(self) -> bool:
        for file in self.cocotb_files():
            return True
        return False

    def is_cocotb_module(self, name: str):
        # TODO: Should we also search in installed packages?
        if [f for f in self.cocotb_files() if f.Path.stem == name]:
            return True

    def cocotb_module(self) -> str:
        modules = set()
        for toplevel in self.project.DefaultDesign.TopLevel.split():
            if self.is_cocotb_module(toplevel):
                # TODO: What if more than one module match?
                modules.add(toplevel)
        if not modules:
            raise Exception(f"No CocoTB module found in {self.project.DefaultDesign.TopLevel}")
        elif len(modules) == 1:
            return next(iter(modules))
        else:
            raise NotImplementedError(f"More than one CocoTB module found: {modules}")

    def is_tool_setup(self) -> None:
        if (shutil.which('vlog') is None or
                shutil.which('vsim') is None or
                shutil.which('vcom') is None or
                shutil.which('vlib') is None or
                shutil.which('vmap') is None):
            raise Exception("Questa is not setup correctly")


def get_lib_name_path(interface: str, simulator: str) -> str:
    lib_name_path = sh(['cocotb-config', '--lib-name-path', interface, simulator])
    return lib_name_path


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


def md5sum(string: str) -> str:
    return md5(string.encode()).hexdigest()


def append_suffix(path: Path, suffix: str) -> Path:
    return path.with_suffix(path.suffix + suffix)


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
