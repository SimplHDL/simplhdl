from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from .fileset import Fileset


class Design:
    def __init__(self, name: str) -> None:
        self._name = name
        self._filesets = nx.DiGraph()
        self._files = nx.DiGraph()

    @property
    def name(self) -> str:
        return self._name

    def add_fileset(self, fileset: Fileset) -> None:
        fileset._graph = self._filesets
        self._filesets.add_node(fileset)

    def validate(self) -> None:
        is_dag_fileset = nx.is_directed_acyclic_graph(self._filesets)
        if not is_dag_fileset:
            cycle_edges = nx.find_cycle(self._filesets)
            # Format the cycle into a human-readable string like "A -> C -> A"
            path = " -> ".join(str(u) for u, v in cycle_edges) + f" -> {cycle_edges[0][0]}"
            raise SystemError(f'Cyclic dependency found: {path}')
