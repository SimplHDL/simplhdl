from __future__ import annotations

try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import logging
import os
import shutil
from argparse import Namespace
from pathlib import Path
from typing import Any, Callable, Generator, Tuple

from jinja2 import Environment, FileSystemLoader

from ..cocotb import Cocotb
from ..project.files import (
    File,
    HdlSearchPath,
    MemoryHexFile,
    SystemVerilogFile,
    VerilogFile,
    VerilogIncludeFile,
    VhdlFile,
    UsedIn,
)
from ..project.fileset import Fileset, FilesetOrder, FileOrder
from ..project.project import Project
from ..utils import (
    append_suffix,
    generate_from_template,
    md5check,
    md5sum,
    md5write,
)
from .flow import FlowBase, FlowCategory, FlowError

logger = logging.getLogger(__name__)


class SimulationFlow(FlowBase):

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.category = FlowCategory.SIMULATION
        self.hdl_language = None
        self.templates = None
        self.hashfile = self.builddir.joinpath('filesets.hash')
        self.libraries = [lib for lib in self.project.defaultDesign.libraries if not lib.external]
        self.external_libraries = [lib for lib in self.project.defaultDesign.libraries if lib.external]

    def run(self) -> None:
        self.cocotb = Cocotb(self.project, self.args.seed)
        self.validate()
        self.configure()
        self.generate()
        self.execute(self.args.step)

    def validate(self):
        if not self.project.defaultDesign.toplevels:
            raise FlowError("Simulation top level is not defined")
        for file in self.project.defaultDesign.files():
            if not file.path.exists():
                raise FileNotFoundError(f"{file.path}: doesn't exits")

    def configure(self):
        os.makedirs(self.builddir, exist_ok=True)
        self.is_tool_setup()
        os.environ['RANDOM_SEED'] = str(self.args.seed)
        os.environ['COCOTB_RANDOM_SEED'] = str(self.args.seed)

    def get_globals(self) -> dict[str, Any]:
        incdirs = self.project.defaultDesign.files(
            type=(HdlSearchPath, VerilogIncludeFile), usedin=UsedIn.SIMULATION)
        incdirpaths = {f.includeDir for f in incdirs}
        globals = dict()
        globals['libraries'] = self.libraries
        globals['external_libraries'] = self.external_libraries
        globals['defaultlib'] = 'work'
        globals['toplevels'] = ' '.join(self.cocotb.toplevels)
        globals['pythonpath'] = self.cocotb.pythonpath
        globals['cocotbtop'] = self.cocotb.top
        globals['cocotbhdltype'] = self.cocotb.duttype
        globals['cocotbdut'] = self.cocotb.dut
        globals['incdirs'] = incdirpaths
        globals['VerilogFile'] = VerilogFile
        globals['SystemVerilogFile'] = SystemVerilogFile
        globals['VhdlFile'] = VhdlFile
        globals['uvm'] = self.is_uvm()
        globals['isinstance'] = isinstance
        globals['UsedIn'] = UsedIn
        globals['FileOrder'] = FileOrder
        globals['FilesetOrder'] = FilesetOrder
        return globals

    def check_external_libraries(self):
        for library in self.external_libraries:
            if not library.path.exists():
                raise FlowError(f"External library {library.name} doesn't exist at {library.path}")

    def check_libraries(self):
        for library in self.libraries:
            pass

    def generate(self):
        self.check_external_libraries()
        self.check_libraries()
        templatedir = resources_files(self.templates)
        env = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)
        for template in self.get_project_templates(env) + self.get_cocotb_templates(env):
            generate_from_template(template, self.builddir, self.get_globals())
        self.generate_make_rules(env)
        self.copy_memory_files()
        self.is_filesets_changed()

    def generate_make_rules(self, environment):
        fileset_makefiles: list[str] = list()
        for fileset in self.project.defaultDesign.filesets(order=FilesetOrder.COMPILE):
            for language in ['verilog', 'systemverilog', 'vhdl']:
                fileset_makefiles += self.generate_fileset_makefiles(environment, language, fileset)
        rules = self.generate_fileset_dependencies(fileset_makefiles)
        template = environment.get_template('dependencies.mk.j2')
        generate_from_template(template, self.builddir, rules=rules)

    def generate_fileset_dependencies(self, filelist: list[Path]):
        """Generate a dependency makefile for filesets. There a two type of
           make rules.
           1. the vhdl fileset depends in the verilog fileset, i.e. the verilog
              filesets needs to be compiled first.
           2. A fileset depends on its children filesets.

        Args:
            filelist (List[str]): List of generated makefile filesets.
        """
        rules: dict[str, list[str]] = dict()
        for fileset in self.project.defaultDesign.filesets(order=FilesetOrder.HIERACHY):
            name = md5sum(fileset.name)
            dependencies = []
            for language_fileset in [f for f in filelist if f.stem.startswith(name)]:
                for child in fileset.filesets:
                    child_name = md5sum(child.name)
                    dependencies += [append_suffix(f, '.com').name for f in filelist
                                     if f.stem.startswith(child_name)]
                    if dependencies:
                        rules[append_suffix(language_fileset, '.com').name] = dependencies
        return rules

    def generate_fileset_makefiles(self, environment: Environment, language: str, fileset: Fileset) -> list[Path]:
        table: dict[str, Tuple[list[File], Callable]] = {
            'verilog': ((VerilogFile, VerilogIncludeFile), self.fileset_verilog_args(fileset)),
            'systemverilog': ((SystemVerilogFile, VerilogIncludeFile), self.fileset_systemverilog_args(fileset)),
            'vhdl': ((VhdlFile), self.fileset_vhdl_args(fileset)),
        }
        filetypes, args = table[language]
        files = list(fileset.files(type=filetypes, usedin=UsedIn.SIMULATION))
        name = md5sum(fileset.name)
        base = self.builddir.joinpath(f"{name}-{language}")
        generated: list[str] = list()
        template = environment.get_template('files.j2')
        if not [f for f in files if not isinstance(f, VerilogIncludeFile)]:
            return generated
        generate_from_template(
            template,
            base.with_suffix('.files'),
            target=base.with_suffix('.fileset').name,
            files=[f.path.absolute() for f in files],
            hashfile=self.hashfile.name)
        template = environment.get_template('fileset.j2')
        output = base.with_suffix('.fileset')
        if language == 'vhdl':
            includes = []
        else:
            includes = self.get_globals()['incdirs']
        files = [f.path.absolute() for f in files if not isinstance(f, VerilogIncludeFile)]
        generate_from_template(template, output, args=args, includes=includes, files=files)
        generated.append(output)
        return generated

    def copy_memory_files(self):
        for file in self.project.defaultDesign.files(MemoryHexFile):
            shutil.copy(file.path.absolute(), self.builddir.absolute())

    def is_uvm(self):
        for plusarg in self.project .plusargs.keys():
            if plusarg.startswith('UVM_'):
                return True
        return False

    def has_verilog(self) -> bool:
        if list(self.project.defaultDesign.files(VerilogFile)):
            return True
        if list(self.project.defaultDesign.files(SystemVerilogFile)):
            return True
        return False

    def has_vhdl(self) -> bool:
        if list(self.project.defaultDesign.files(VhdlFile)):
            return True
        return False

    def is_filesets_changed(self) -> bool:
        """
        Check if there are any changes in filesets since last run.
        """
        filesets = []
        for fileset in self.project.defaultDesign.filesets():
            filesets += [Path(f.name) for f in FileSetWalker().walk(fileset) if Path(f.name).is_file()]
        if self.hashfile.is_file() and md5check(*filesets, filename=self.hashfile):
            return True
        else:
            md5write(*filesets, filename=self.hashfile)
            return False


class FileSetWalker:

    def __init__(self):
        self.__visited: list = list()

    def walk(self, fileset: Fileset, reverse=False) -> Generator[Fileset, None, None]:
        if fileset.name not in self.__visited:
            self.__visited.append(fileset.name)
            if reverse is False:
                yield fileset
            for child in fileset.filesets:
                yield from self.walk(child, reverse)
            if reverse:
                yield fileset
