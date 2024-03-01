try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import os
import logging

from typing import Callable, Generator, List, Dict, Tuple, Any
from jinja2 import Environment, FileSystemLoader
from argparse import Namespace
from pathlib import Path

from simplhdl.flow import FlowBase, FlowCategory, FlowError
from simplhdl.pyedaa.project import Project
from simplhdl.pyedaa.attributes import UsedIn
from simplhdl.cocotb import Cocotb
from simplhdl.pyedaa.fileset import FileSet
from simplhdl.pyedaa import (File, VerilogSourceFile, VerilogIncludeFile,
                             SystemVerilogSourceFile, VHDLSourceFile)
from simplhdl.utils import generate_from_template, md5sum, append_suffix

logger = logging.getLogger(__name__)


class SimulationFlow(FlowBase):

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.category = FlowCategory.SIMULATION
        self.hdl_language = None
        self.cocotb = Cocotb(project)
        self.templates = None

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

    def get_globals(self) -> Dict[str, Any]:
        globals = dict()
        globals['libraries'] = (list(self.project.DefaultDesign.VHDLLibraries.values()))
        globals['external_libraries'] = list(self.project.DefaultDesign.ExternalVHDLLibraries.values())
        globals['defaultlib'] = 'work'
        globals['toplevels'] = ' '.join(
            [t for t in self.project.DefaultDesign.TopLevel.split() if t != self.cocotb.module()])
        globals['pythonpath'] = self.cocotb.pythonpath
        globals['uvm'] = self.is_uvm()
        return globals

    def generate(self):
        templatedir = resources_files(self.templates)
        env = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)
        for template in self.get_project_templates(env) + self.get_cocotb_templates(env):
            generate_from_template(template, self.builddir, self.get_globals())
        self.generate_make_rules(env)

    def generate_make_rules(self, environment):
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
            'verilog': ([VerilogSourceFile, VerilogIncludeFile], self.fileset_verilog_args(fileset)),
            'systemverilog': ([SystemVerilogSourceFile, VerilogIncludeFile], self.fileset_systemverilog_args(fileset)),
            'vhdl': ([VHDLSourceFile], self.fileset_vhdl_args(fileset)),
        }
        filetypes, args = table[language]
        files = [f for f in fileset.GetFiles() if f.FileType in filetypes and 'simulation' in f[UsedIn]]
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
            generate_from_template(template, output, args=args, includes=includes, files=files)
            generated.append(output)
        return generated

    def is_uvm(self):
        for plusarg in self.project.PlusArgs.keys():
            if plusarg.startswith('UVM_'):
                return True
        return False

    def has_verilog(self) -> bool:
        if list(self.project.DefaultDesign.Files(VerilogSourceFile)):
            return True
        if list(self.project.DefaultDesign.Files(SystemVerilogSourceFile)):
            return True
        return False

    def has_vhdl(self) -> bool:
        if list(self.project.DefaultDesign.Files(VHDLSourceFile)):
            return True
        return False

    def get_libraries(self):
        libraries = dict()
        libraries.update(self.project.DefaultDesign.VHDLLibraries)
        libraries.update(self.project.DefaultDesign.ExternalVHDLLibraries)
        return libraries


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
