import pyEDAA.ProjectModel as pm  # type: ignore
from simplhdl.pyedaa.attributes import UsedIn
from simplhdl.pyedaa import File, HDLSearchPath, VerilogIncludeSearchPath, VerilogIncludeFile

from typing import Dict, Generator, List, Optional


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

    def GetFiles(self, filetype=None) -> Generator[File, None, None]:
        for file in self._files:
            if filetype:
                if isinstance(file, filetype):
                    yield file
            else:
                yield file

    @property
    def VHDLLibraries(self) -> Dict[str, 'VHDLLibrary']:
        libraries = dict()
        if self._vhdlLibrary is not None:
            libraries[self._vhdlLibrary.Name] = self._vhdlLibrary
        for fileset in self.FileSets.values():
            libraries.update(fileset.VHDLLibraries)
        return libraries

    def InsertFile(self, position: int, file: File) -> None:
        # file.FileSet = self
        self._files.insert(position, file)

    def InsertFileAfter(self, listfile: File, newfile: File) -> None:
        position = self._files.index(listfile)
        self.InsertFile(position, newfile)

    def Dependencies(self, usedin: Optional[str] = None, isrecursive: bool = False) -> List['FileSet']:
        """
        Return a list of filesets that this fileset depends on. if dependent fileset is empty search recursive
        in children until a fileset that is not empty is found.
        """
        if isrecursive:
            files = [f for f in self.GetFiles()]
            if usedin:
                files = [f for f in files if usedin in f[UsedIn]]
            if files:
                return [self]
        dependencies = list()
        for fileset in self.FileSets.values():
            dependencies += fileset.Dependencies(usedin=usedin, isrecursive=True)
        return dependencies

    def IncludeDirs(self, usedin: Optional[str] = None, isrecursive: bool = False) -> List[HDLSearchPath]:
        dirs = list()
        if isrecursive:
            for _, fileset in self.FileSets.items():
                dirs += fileset.IncludeDirs(usedin=usedin, isrecursive=True)
        if usedin:
            items = [i for i in self._files if usedin in i[UsedIn]]
        for item in items:
            if isinstance(item, VerilogIncludeFile):
                dirs.append(VerilogIncludeSearchPath(item.Path.parent.absolute()))
            elif isinstance(item, HDLSearchPath):
                dirs.append(HDLSearchPath(item.Path.absolute()))
        return dirs
