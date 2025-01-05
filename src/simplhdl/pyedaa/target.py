from typing import Optional
from pathlib import Path

from argparse import Namespace


class Target:
    def __init__(self, name: str, args: Optional[Namespace] = None, cwd: Path = None) -> None:
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
