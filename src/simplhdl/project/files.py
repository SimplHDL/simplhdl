from __future__ import annotations

from pathlib import Path


class File:
    def __init__(self, file: Path) -> None:
        self._name = file.stem
        self._path = file.absolute().resolve()
        self._suffix = file.suffix()
        self._graph = None
