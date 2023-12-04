import pyEDAA.ProjectModel as pm

from typing import Optional
from pathlib import Path
from pyVHDLModel import VHDLVersion  # type: ignore


class VHDLLibrary(pm.VHDLLibrary):

    _path: Optional[Path]

    def __init__(
            self, name: str,
            project=None,
            design=None,
            vhdlVersion: VHDLVersion = None,
            path: Path = None
    ):
        super().__init__(name, project, design, vhdlVersion)
        if path is None:
            self._path = name
        else:
            self._path = path

    @property
    def Path(self) -> Optional[Path]:
        return self._path

    @Path.setter
    def Path(self, path: Path) -> None:
        self._path = path
