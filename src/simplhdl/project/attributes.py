from __future__ import annotations

from argparse import Namespace
from pathlib import Path


class Library:
    def __init__(self, path: Path|str, name: str|None = None) -> None:
        if isinstance(path, str):
            path = Path(path)
        self._path = path.absolute().resolve()
        if name is None:
            self._name = path.name
        else:
            self._name = name

    @property
    def path(self) -> Path:
        return self._path

    @property
    def name(self) -> str:
        return self._name

    def __str__(self) -> str:
        return self._name

class Target:
    def __init__(self, name: str, args: Namespace|None = None, cwd: Path|None = None) -> None:
        self.name = name
        self._args = args
        self._cwd = cwd or Path('.')

    @property
    def args(self) -> Namespace:
        if self._args is None:
            raise FileNotFoundError(f"Target '{self.name}' has no arguments defined")
        return self._args

    @args.setter
    def args(self, args: Namespace) -> None:
        self._args = args

    @property
    def cwd(self) -> Path:
        if self._cwd is None:
            raise FileNotFoundError(f"Target '{self.name}' has no cwd defined")
        return self._cwd

    @cwd.setter
    def cwd(self, path: Path) -> None:
        self._cwd = path
