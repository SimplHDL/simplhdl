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
from ..flow import FlowFactory, FlowBase
from ..resources.templates import vcs as templates
from ..cocotb import Cocotb

logger = logging.getLogger(__name__)


@FlowFactory.register('vcs')
class VcsFlow(FlowBase):

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
        self.hdl_language = None
        self.cocotb = Cocotb(project)

    def run(self) -> None:
        self.configure()
        self.generate()
        self.execute(self.args.step)

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

        libraries = [lib.Name for lib in self.project.DefaultDesign.VHDLLibraries.values()]
        defaultlib = 'work'

        template = environment.get_template('Makefile.j2')
        generate_from_template(template, self.builddir, vcs_flags=self.vcs_flags(), simv_flags=self.simv_flags())

        template = environment.get_template('synopsys_sim.setup.j2')
        generate_from_template(template, self.builddir, defaultlib=defaultlib, libraries=libraries)

        template = environment.get_template('project.mk.j2')
        toplevels = ' '.join([t for t in self.project.DefaultDesign.TopLevel.split() if t != self.cocotb.module()])
        generate_from_template(
            template,
            self.builddir,
            toplevels=toplevels,
            libraries=' '.join(libraries))

        if self.cocotb.enabled:
            template = environment.get_template('cocotb.mk.j2')
            generate_from_template(template, self.builddir, pythonpath=self.cocotb.pythonpath)
            template = environment.get_template('pli.tab.j2')
            generate_from_template(template, self.builddir)

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
            'verilog': ([VerilogSourceFile, VerilogIncludeFile], self.vlogan_flags),
            'systemverilog': ([SystemVerilogSourceFile, VerilogIncludeFile], self.svlogan_flags),
            'vhdl': ([VHDLSourceFile], self.vhdlan_flags),
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
                target=base.with_suffix('.fileset').name,
                files=[f.Path.absolute() for f in files])
            template = environment.get_template('fileset.j2')
            output = base.with_suffix('.fileset')
            includes = {f.Path.parent.absolute() for f in files if isinstance(f, VerilogIncludeFile)}
            files = [f.Path.absolute() for f in files if not isinstance(f, VerilogIncludeFile)]
            generate_from_template(template, output, flags=flags(fileset), includes=includes, files=files)
            generated.append(output)
        return generated

    def svlogan_flags(self, fileset: FileSet) -> str:
        library = self.get_library(fileset)
        verbosity = '-q' if self.args.verbose == 0 else ''
        verbosity = '-V' if self.args.verbose == 2 else verbosity
        return f"-sverilog {verbosity} -work {library} {self.args.vlogan_flags}".strip()

    def vlogan_flags(self, fileset: FileSet) -> str:
        library = self.get_library(fileset)
        verbosity = '-q' if self.args.verbose == 0 else ''
        verbosity = '-V' if self.args.verbose == 2 else verbosity
        return f"+v2k {verbosity} -work {library} {self.args.vlogan_flags}".strip()

    def vhdlan_flags(self, fileset: FileSet) -> str:
        library = self.get_library(fileset)
        verbosity = '-q' if self.args.verbose == 0 else ''
        verbosity = '-V' if self.args.verbose == 2 else verbosity
        return f"-vhdl08 {verbosity} -work {library} {self.args.vhdlan_flags}".strip()

    def vcs_flags(self) -> str:
        flags = set()
        if self.args.verbose == 0:
            flags.add('-q')
        if self.args.timescale:
            flags.add(f"-timescale={self.args.timescale}")
        if self.cocotb.enabled:
            if self.hdl_language == 'vhdl':
                raise NotImplementedError("Cocotb with VHDL top is not implemented")
            else:
                flags.add(f"+vpi -P pli.tab -load {self.cocotb.lib_name_path('vcs', 'vpi')}")
                flags.add("-debug_access+r+w+nomemcbk -debug_region+cell+encrypt")
                flags.add("-debug_acc+pp+f+dmptf")
        for name, value in self.project.Generics.items():
            flags.add(f"-pvalue+{name}={value}")
        for name, value in self.project.Parameters.items():
            flags.add(f"-pvalue+{name}={value}")
        for name, value in self.project.Defines.items():
            flags.add(f"+define+{name}={value}")
        for name, value in self.project.PlusArgs.items():
            flags.add(f"+{name}={value}")
        return ' '.join(list(flags) + [self.args.vcs_flags])

    def simv_flags(self) -> str:
        flags = set()
        flags.add(f"+ntb_random_seed={self.args.seed}")
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
        if (shutil.which('vlogan') is None or
                shutil.which('vhdlan') is None or
                shutil.which('vcs') is None):
            raise Exception("Vcs is not setup correctly")


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
