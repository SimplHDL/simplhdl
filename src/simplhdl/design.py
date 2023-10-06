import pyEDAA.ProjectModel as pm

from pathlib import Path


class Design(pm.Design):

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

    def AddVHDLLibrary(self, vhdlLibrary: pm.VHDLLibrary):
        super().AddVHDLLibrary(vhdlLibrary)
        self._vhdlLibraries[vhdlLibrary.Name] = vhdlLibrary
