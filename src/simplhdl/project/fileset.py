from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import networkx as nx

from .files import File


class Fileset:
    def __init__(self, name: str) -> None:
        self.id: str = str(uuid4())
        self._name = name
        self._files = dict[Path, File]
        self._graph = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    @graph.setter
    def graph(self, graph: nx.DiGraph) -> None:
        self._graph = graph

    @property
    def ancestors(self) -> list[Fileset]:
        return nx.ancestors(self._graph, self)

    @property
    def descendants(self) -> list[Fileset]:
        return nx.descendants(self._graph, self)

    def add_fileset(self, fileset: Fileset) -> None:
        fileset._graph = self._graph
        self._graph.add_node(fileset)
        self._graph.add_edge(self, fileset)

    def add_filesets(self, filesets: list[Fileset]) -> None:
        for fileset in filesets:
            self.add_fileset(fileset)

    def add_file(self, file: File) -> None:
        self.files.add_node(file)

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(name={self._name})'
