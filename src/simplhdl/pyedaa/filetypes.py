import pyEDAA.ProjectModel as pyeda

from typing import Optional
from pathlib import Path


class HDLLibrary(pyeda.VHDLLibrary):
    pass


class HDLIncludeFile(pyeda.SourceFile):
    pass


class HDLSourceFile(pyeda.HDLSourceFile):
    _library: HDLLibrary

    def __init__(
        self,
        path: Path,
        project: pyeda.Project = None,
        design: pyeda.Design = None,
        fileSet: pyeda.FileSet = None,
        library: Optional[HDLLibrary] = None
    ):
        super().__init__(path=path, project=project, design=design, fileSet=fileSet)
        self._library = library

    @property
    def Library(self) -> HDLLibrary:
        return self._library

    @Library.setter
    def Library(self, value) -> None:
        self._library = value


class VerilogIncludeFile(HDLIncludeFile, pyeda.HumanReadableContent):
    pass


class VerilogSoureFile(HDLSourceFile, pyeda.HumanReadableContent):
    pass


class SystemVerilogSoureFile(HDLSourceFile, pyeda.HumanReadableContent):
    pass


class VHDLSourceFile(HDLSourceFile, pyeda.HumanReadableContent):
    pass


class CocotbPythonFile(pyeda.CocotbPythonFile):
    pass
