import pyEDAA.ProjectModel as pm  # type: ignore

from typing import Generator


class FileSet(pm.FileSet):

    def AddFileSet(self, fileSet: 'FileSet') -> None:
        if (not isinstance(fileSet, FileSet)):
            raise ValueError("Parameter 'fileSet' is not of type ProjectModel.FileSet.")
        elif (fileSet in self.FileSets):
            raise Exception("Design already contains this fileSet.")
        elif (fileSet.Name in self._fileSets.keys()):
            # raise Exception(f"Design already contains a fileset named '{fileSet.Name}'.")
            return
        self._fileSets[fileSet.Name] = fileSet

    @property
    def VHDLLibrary(self) -> 'VHDLLibrary':
        """Property setting or returning the VHDL library of this fileset."""
        if self._vhdlLibrary is not None:
            return self._vhdlLibrary
        elif self._parent is not None:
            return self._parent.VHDLLibrary
        elif self._design is not None:
            # WORKAROUND: This needs to be solved, for now just return the first item.
            return next(iter(self._design.VHDLLibraries.values()))
        else:
            raise Exception("VHDLLibrary was neither set locally nor globally.")

    def GetFiles(self) -> Generator[pm.File, None, None]:
        for file in self._files:
            yield file