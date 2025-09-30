import logging
import pyEDAA.ProjectModel as pm

from typing import Optional
from pathlib import Path
from pyVHDLModel import VHDLVersion  # type: ignore


logger = logging.getLogger(__name__)


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
            self.Path = Path(name)
        else:
            self.Path = path

    @property
    def Path(self) -> Optional[Path]:
        return self._path

    @Path.setter
    def Path(self, path: Path) -> None:
        if isinstance(path, str):
            filename, lineno, funcname, info = logger.findCaller(stacklevel=3)
            logger.debug(f"The VHDL library path is a string in {filename}:{lineno}")
            self._path = Path(path)
        else:
            self._path = path
