from typing import Optional
import pyEDAA.ProjectModel as pyeda


class HDLLibrary(pyeda.VHDLLibrary):
    pass


class HDLIncludeFile(pyeda.SourceFile):
    pass


class HDLSourceFile(pyeda.HDLSourceFile):
    _library: HDLLibrary

    def __init__(self, library: Optional[HDLLibrary] = None) -> None:
        super().__init__()
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
