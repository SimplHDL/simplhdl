import pyEDAA.ProjectModel as pm
from pyEDAA.ProjectModel import VHDLLibrary  # type: ignore


class Design(pm.Design):

    def AddVHDLLibrary(self, vhdlLibrary: VHDLLibrary):
        super().AddVHDLLibrary(vhdlLibrary)
        self._vhdlLibraries[vhdlLibrary.Name] = vhdlLibrary
