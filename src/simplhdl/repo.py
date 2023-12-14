import git

from abc import ABCMeta, abstractmethod
from typing import Optional
from pathlib import Path

from .utils import sh, lock


class Repo(metaclass=ABCMeta):

    _name: str
    _url: str
    _ref: str
    _path: Path

    def __init__(self, name: str, url: str, path: Path, ref: Optional[str] = None):
        self._name = name
        self._url = url
        self._ref = ref
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, path: Path) -> None:
        self._path = path

    @abstractmethod
    def checkout(self):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def status(self):
        pass


class Git(Repo):

    _repo: git.Repo = None

    def checkout(self):
        with lock(self._path.with_suffix('.lock')):
            if self._path.exists():
                self._repo = git.Repo(self._path)
            else:
                self._repo = git.Repo.clone_from(self._url, self._path)
                self._repo.git.checkout(self._ref)

    def update(self):
        pass

    def status(self):
        pass

    def is_detached(self) -> bool:
        return self._repo.head.is_detached


class Mercurial(Repo):

    def checkout(self):
        with lock(self._path.with_suffix('.lock')):
            if not self._path.exists():
                self.path.mkdir(parents=True, exist_ok=True)
                sh(f'hg clone --updaterev {self._ref} {self._url} {self._path}'.split())

    def update(self):
        pass

    def status(self):
        pass


class Subversion(Repo):

    def __init__(self, name: str, url: str, path: Path, ref: Optional[str] = None):
        raise NotImplementedError("Support for Subversion repositories not implemented.")

    def checkout(self):
        pass

    def update(self):
        pass

    def status(self):
        pass
