from __future__ import annotations

from typing import Generator
from uuid import uuid4

import networkx as nx

from .attributes import Library
from .files import File
from .project import Project


class Fileset:
    def __init__(self, name: str, **attributes) -> None:
        self._id: str = str(uuid4())
        self._name: str = name
        self._project: Project = None
        self._library: Library = attributes.get('library', None)
        self._first = None
        self._last = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def project(self) -> Project:
        return self._project

    @property
    def files(self) -> Generator[File, None, None]:
        file_nodes = [f for f in self._files.nodes() if f.parent is self]
        subgraph = self._files.subgraph(file_nodes)
        return nx.topological_sort(subgraph)

    @property
    def filesets(self) -> nx.DiGraph:
        return self._project.defaultDesign._filesets.subgraph(self.descendants)

    @property
    def ancestors(self) -> set[Fileset]:
        return nx.ancestors(self._filesets, self)

    @property
    def descendants(self) -> set[Fileset]:
        return nx.descendants(self._filesets, self)

    @property
    def library(self) -> Library:
        return self._library

    @library.setter
    def library(self, library: Library) -> None:
        self._library = library

    @property
    def _filesets(self) -> nx.DiGraph[Fileset]:
        return self._project.defaultDesign._filesets

    @property
    def _files(self) -> nx.DiGraph[File]:
        return self._project.defaultDesign._files

    def add_fileset(self, fileset: Fileset) -> None:
        if self._project is None:
            raise Exception(f"Cannot add filesets to fileset '{self}' before project is set")
        fileset._project = self._project
        self._filesets.add_node(fileset)
        self._filesets.add_edge(self, fileset)

    def add_filesets(self, filesets: list[Fileset]) -> None:
        for fileset in filesets:
            self.add_fileset(fileset)

    def add_file(self, file: File) -> None:
        if self._project is None:
            raise Exception(f"Cannot add files to fileset '{self}' before project is set")
        if file.parent not in [None, self]:
            raise Exception(f"File '{file}' already belongs to the fileset '{file.parent}'")
        if self._first is None:
            self._first = file
        self._files.add_node(file)
        file._parent = self
        if self._last:
            self._files.add_edge(self._last, file)
        self._last = file

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(name={self._name}, library={self._library})'
