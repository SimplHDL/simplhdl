import pyEDAA.ProjectModel as pm

from pathlib import Path
from typing import Optional
from pyTooling.MetaClasses import ExtendedType
from .attributes import UsedIn


class FileMixIn(metaclass=ExtendedType, mixin=True):
    def _registerAttributes(self):
        self._attributes[UsedIn] = {'simulation', 'implementation'}


class File(pm.File, FileMixIn):
    def _registerAttributes(self):
        super()._registerAttributes()
        FileMixIn._registerAttributes(self)


class SourceFile(pm.SourceFile, FileMixIn):
    def _registerAttributes(self):
        super()._registerAttributes()
        FileMixIn._registerAttributes(self)


class HDLLibrary(pm.VHDLLibrary):
    pass


class HDLIncludeFile(SourceFile):
    pass


class HDLSourceFile(pm.HDLSourceFile, FileMixIn):
    _library: HDLLibrary

    def __init__(self,
                 path: Path = None, project: pm.Project = None,
                 design: pm.Design = None, fileset: pm.FileSet = None,
                 library: Optional[HDLLibrary] = None):
        super().__init__(path, project, design, fileset)
        self._library = library

    def _registerAttributes(self):
        super()._registerAttributes()
        FileMixIn._registerAttributes(self)

    @property
    def Library(self) -> HDLLibrary:
        return self._library

    @Library.setter
    def Library(self, value) -> None:
        self._library = value


class VerilogIncludeFile(HDLIncludeFile, pm.HumanReadableContent):
    pass


class VerilogSourceFile(HDLSourceFile, pm.HumanReadableContent):
    pass


class SystemVerilogSourceFile(HDLSourceFile, pm.HumanReadableContent):
    pass


class VHDLSourceFile(HDLSourceFile, pm.HumanReadableContent):
    pass


class CocotbPythonFile(pm.CocotbPythonFile, FileMixIn):
    def _registerAttributes(self):
        super()._registerAttributes()
        FileMixIn._registerAttributes(self)
        self[UsedIn] = {'simulation'}


class TCLSourceFile(pm.TCLSourceFile):
    def _registerAttributes(self):
        super()._registerAttributes()
        FileMixIn._registerAttributes(self)


class IPSpecificationFile(File, pm.XMLContent):
    pass


class NetlistFile(pm.NetlistFile, FileMixIn):
    def _registerAttributes(self):
        super()._registerAttributes()
        FileMixIn._registerAttributes(self)


class EDIFNetlistFile(pm.EDIFNetlistFile, FileMixIn):
    def _registerAttributes(self):
        super()._registerAttributes()
        FileMixIn._registerAttributes(self)


class CSourceFile(pm.CSourceFile, FileMixIn):
    def _registerAttributes(self):
        super()._registerAttributes()
        FileMixIn._registerAttributes(self)


class SettingFile(pm.SettingFile, FileMixIn):
    def _registerAttributes(self):
        super()._registerAttributes()
        FileMixIn._registerAttributes(self)


class ConstraintFile(pm.ConstraintFile, FileMixIn):
    def _registerAttributes(self):
        super()._registerAttributes()
        FileMixIn._registerAttributes(self)
        self[UsedIn] = {'implementation'}


class QuartusSignalTapFile(File):
    def _registerAttributes(self):
        super()._registerAttributes()
        self[UsedIn] = {'implmentation'}


class QuartusIPSpecificationFile(IPSpecificationFile):
    pass


class VivadoIPSpecificationFile(IPSpecificationFile):
    pass


class SystemRDLSourceFile(File):
    pass


class ScalaBuildFile(File):
    pass


class ChiselBuildFile(ScalaBuildFile):
    pass
