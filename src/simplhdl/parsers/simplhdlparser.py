from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from shlex import split
from typing import TYPE_CHECKING

import yaml

from simplhdl.__main__ import parse_arguments
from simplhdl.parser import ParserBase, ParserFactory
from simplhdl.project.attributes import Library, Target
from simplhdl.project.files import FileFactory
from simplhdl.project.fileset import Fileset
from simplhdl.project.project import Project

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
            fileset = Fileset(str(file))
            project.defaultDesign.add_fileset(fileset)
            if self.is_valid_format(file):
                return self.parse_core(file, fileset)

    def parse_core(self, filename: Path, fileset: Fileset) -> None:
        self._core_stack.append(filename)
        spec = self.read_spec(filename)
        # TODO: The library should be handled differently
        fileset.library = Library(spec.get('library', 'work'))
        for corefile in spec.get('dependencies', list()):
            corefile = self.path(corefile)
            if corefile.absolute() in self._core_visited:
                continue
            subfileset = Fileset(str(corefile))
            fileset.add_fileset(subfileset)
            self.parse_core(corefile, subfileset)

        project = fileset.project
        if 'top' in spec:
            for top in spec.get('top').split():
                project.defaultDesign.add_toplevel(top)

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
            file = FileFactory.create(Path(filepath))
            fileset.add_file(file)
        # Top level spec
        if len(self._core_stack) == 1:
            if 'project' in spec:
                project.name = spec.get('project')
            if 'part' in spec:
                project.part = spec.get('part')
            if 'top' in spec:
                project.defaultDesign.toplevels.clear()
                for top in spec.get('top').split():
                    project.defaultDesign.add_toplevel(top)

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
