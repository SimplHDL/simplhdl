from pathlib import Path
from pyEDAA.ProjectModel import FileSet, SystemVerilogSourceFile, VerilogSourceFile, VHDLSourceFile  # type: ignore
from simplhdl.parser import ParserFactory, ParserBase


@ParserFactory.register()
class SimpleParser(ParserBase):

    _format_id: str = '#% simplelist 1.0'

    def __init__(self):
        super().__init__()

    def is_valid_format(self, filename: Path) -> bool:
        with open(filename, 'r') as fp:
            if fp.readline().strip() == self._format_id:
                return True
            else:
                return False

    def _str_to_path(self, string: str, directory: Path) -> Path:
        path = directory.joinpath(string.strip())
        return path

    def parse(self, filename: Path) -> 'FileSet':
        directory = filename.parent
        fileset = FileSet(filename.stem)
        with open(filename, 'r') as fp:
            if fp.readline().strip() != self._format_id:
                raise Exception(f"Unknown format ID for simple list: {self._format_id}")
            for line_raw in fp.readlines():
                line = line_raw.strip()
                if line.endswith('.sv'):
                    file = SystemVerilogSourceFile(self._str_to_path(line, directory))
                    fileset.AddFile(file)
                elif line.endswith('.v'):
                    file = VerilogSourceFile(self._str_to_path(line, directory))
                elif line.endswith('.vhd'):
                    file = VHDLSourceFile(self._str_to_path(line, directory))

        return fileset
