import pyEDAA.ProjectModel as pm  # type: ignore

from typing import Dict, Generator


class FileSet(pm.FileSet):

    def AddFileSet(self, fileSet: 'FileSet') -> None:
        if (not isinstance(fileSet, FileSet)):
            raise ValueError("Parameter 'fileSet' is not of type ProjectModel.FileSet.")
        elif (fileSet in self.FileSets):
            raise Exception("Design already contains this fileSet.")
        elif (fileSet.Name in self._fileSets.keys()):
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

    @VHDLLibrary.setter
    def VHDLLibrary(self, value: 'VHDLLibrary') -> None:
        self._vhdlLibrary = value

    def GetFiles(self) -> Generator[pm.File, None, None]:
        for file in self._files:
            yield file

    @property
    def VHDLLibraries(self) -> Dict[str, 'VHDLLibrary']:
        libraries = dict()
        if self._vhdlLibrary is not None:
            libraries[self._vhdlLibrary.Name] = self._vhdlLibrary
        for fileset in self.FileSets.values():
            libraries.update(fileset.VHDLLibraries)
        return libraries

    def InsertFile(self, position: int, file: pm.File) -> None:
        # file.FileSet = self
        self._files.insert(position, file)

    def InsertFileAfter(self, listfile: pm.File, newfile: pm.File) -> None:
        position = self._files.index(listfile)
        self.InsertFile(position, newfile)
