from __future__ import annotations


import yaml

from typing import TYPE_CHECKING
from pathlib import Path
from argparse import Namespace
from shlex import split
from simplhdl.__main__ import parse_arguments
from simplhdl.project import Project
from simplhdl.project.target import Target
from simplhdl.project.fileset import Fileset
from simplhdl.project.attributes import Library
from simplhdl.pyedaa import (
    IPSpecificationFile, TCLSourceFile, CocotbPythonFile, SettingFile, File,
    ConstraintFile, VHDLSourceFile, VerilogIncludeFile, SystemVerilogSourceFile,
    EDIFNetlistFile, NetlistFile, CSourceFile, SourceFile, ChiselBuildFile)

from ..parser import ParserFactory, ParserBase

if TYPE_CHECKING:
    from simplhdl.project import Project



@ParserFactory.register()
class SimplHdlParser(ParserBase):

    _format_id: str = "#%SimplAPI=1.0"

    def __init__(self):
        super().__init__()
        self._core_stack = list()
        self._core_visited = list()

    def is_valid_format(self, filename: Path | None) -> bool:
        if filename is None:
            filenames = Path('.').glob('*.yml')
        else:
            filenames = [filename]

        for filename in filenames:
            if filename.exists():
                with filename.open() as fp:
                    if fp.readline().strip() == self._format_id:
                        return True
        return False

    def parse(self, filename: Path | None, project: Project, args: Namespace) -> Fileset:
        if filename is None:
            files = Path('.').glob('*.yml')
        else:
            files = [filename]

        for file in files:
            if self.is_valid_format(file):
                return self.parse_core(file, project)

    def parse_core(self, filename: Path, project: Project) -> Fileset:  # noqa C901
        self._core_stack.append(filename)
        spec = self.read_spec(filename)
        # TODO: The library should be handled differently
        fileset = Fileset(str(filename), library=Library(spec.get('library', 'work')))
        for corefile in spec.get('dependencies', list()):
            corefile = self.path(corefile)
            if corefile.absolute() in self._core_visited:
                continue
            subfileset = self.parse_core(corefile, project)
            fileset.add_fileset(subfileset)

        if 'top' in spec:
            project.design.add_toplevel(spec.get('top'))

        for name, value in spec.get('targets', dict()).items():
            target = Target(name=name, args=parse_arguments(split(value)), cwd=self._core_stack[-1].parent)
            project.add_target(target)
        for name, value in spec.get('defines', dict()).items():
            project.add_define(name, value)
        for name, value in spec.get('parameters', dict()).items():
            project.add_parameter(name, value)
        for name, value in spec.get('plusargs', dict()).items():
            project.add_plusarg(name, value)
        for name, value in spec.get('generics', dict()).items():
            project.add_generic(name, value)
        for filepath in spec.get('files', list()):
            file = self.file(filepath)
            fileset.add_file(file)
        # Top level spec
        if len(self._core_stack) == 1:
            if 'project' in spec:
                project.Name = spec.get('project')
            if 'part' in spec:
                project.Part = spec.get('part')
            if 'top' in spec:
                project.defaultDesign.add_toplevel(spec.get('top'))

        self._core_stack.pop()
        return fileset

    def read_spec(self, filename: Path) -> dict:
        self._core_visited.append(filename.absolute())
        with filename.open() as fp:
            try:
                return yaml.safe_load(fp)
            except yaml.YAMLError as e:
                raise e

    def path(self, filename: str) -> Path:
        if Path(filename).is_absolute():
            path = Path(filename).absolute()
        else:
            path = self._core_stack[-1].parent.joinpath(filename).resolve()
        if not path.exists():
            raise FileNotFoundError(f"No such file: {str(path)}")
        return path

    def file(self, filename: str) -> File:
        """
        Return a file type class object based on the file extension.
        """
        fileClasses = {
            '.sv': SystemVerilogSourceFile,
            '.svh': VerilogIncludeFile,
            '.v': SystemVerilogSourceFile,
            '.vh': VerilogIncludeFile,
            '.vhd': VHDLSourceFile,
            '.vhdl': VHDLSourceFile,
            '.xdc': ConstraintFile,
            '.sdc': ConstraintFile,
            '.xci': IPSpecificationFile,
            '.xcix': IPSpecificationFile,
            '.ip': IPSpecificationFile,
            '.ipx': IPSpecificationFile,
            '.qip': IPSpecificationFile,
            '.qsys': IPSpecificationFile,
            '.edif': EDIFNetlistFile,
            '.edn': EDIFNetlistFile,
            '.dcp': NetlistFile,
            '.tcl': TCLSourceFile,
            '.c': CSourceFile,
            '.h': CSourceFile,
            '.S': CSourceFile,
            '.py': CocotbPythonFile,
            '.qsf': SettingFile,
            '.sbt': ChiselBuildFile,
        }
        path = self.path(filename)
        fileClass = fileClasses.get(path.suffix, SourceFile)
        return fileClass(path)
