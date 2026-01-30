from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from .project import Project


class Library:
    def __init__(self, name: str, path: Path | None = None, external: bool = False) -> None:
        self._name: str = name
        self._path: Path | None = path
        self._external: bool = external
        self._project: Project = Project()

    @property
    def path(self) -> Path | str:
        if not self._path:
            return self._name
        return self._path.resolve()

    @property
    def name(self) -> str:
        return self._name

    @property
    def external(self) -> bool:
        return self._external

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name}, path={self._path}, external={self._external})"

    def __eq__(self, other):
        return isinstance(other, Library) and self.name == other.name and self.path == other.path


class Target:
    def __init__(self, name: str, args: Namespace | None = None, cwd: Path | None = None) -> None:
        self.name = name
        self._args = args
        self._cwd = cwd or Path(".")

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
        return self._cwd.resolve()

    @cwd.setter
    def cwd(self, path: Path) -> None:
        self._cwd = path
