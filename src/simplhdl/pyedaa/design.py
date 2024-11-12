import pyEDAA.ProjectModel as pm

from pathlib import Path
from typing import Dict

from .vhdllibrary import VHDLLibrary


class Design(pm.Design):

    __externalVHDLLibraries: Dict[str, VHDLLibrary]

    def __init__(
        self,
        name: str,
        topLevel: str = None,
        directory: Path = Path("."),
        project=None,
        vhdlVersion: pm.VHDLVersion = None,
        verilogVersion: pm.VerilogVersion = None,
        svVersion: pm.SystemVerilogVersion = None
    ):
        super().__init__(
              name=name,
              topLevel=topLevel,
              directory=directory,
              project=project,
              vhdlVersion=vhdlVersion,
              verilogVersion=verilogVersion,
              svVersion=svVersion)
        self._defaultFileSet = {}
        self._fileSets = {}
        self.__externalVHDLLibraries = {}

    def AddVHDLLibrary(self, vhdlLibrary: pm.VHDLLibrary):
        super().AddVHDLLibrary(vhdlLibrary)
        self._vhdlLibraries[vhdlLibrary.Name] = vhdlLibrary

    @property
    def TopLevel(self) -> str:
        """Property setting or returning the fileset's toplevel."""
        top = set()
        if self._topLevel is not None:
            for t in self._topLevel.split():
                top.add(t)
        for fileset in self._fileSets.values():
            if fileset.TopLevel is not None:
                for t in fileset.TopLevel.split():
                    top.add(t)
        return ' '.join(top)

    @TopLevel.setter
    def TopLevel(self, value: str) -> None:
        self._topLevel = value

    def AddExternalVHDLLibrary(self, vhdlLibrary: pm.VHDLLibrary) -> None:
        self.__externalVHDLLibraries[vhdlLibrary.Name] = vhdlLibrary

    @property
    def ExternalVHDLLibraries(self) -> Dict[str, VHDLLibrary]:
        return self.__externalVHDLLibraries

    @property
    def VHDLLibraries(self) -> Dict[str, VHDLLibrary]:
        libraries = dict()
        libraries.update(self._vhdlLibraries)
        if self.DefaultFileSet:
            libraries.update(self.DefaultFileSet.VHDLLibraries)
        return libraries
