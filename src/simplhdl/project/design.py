from __future__ import annotations

from typing import TYPE_CHECKING, Generator, Type

import networkx as nx

from .files import filter_files

if TYPE_CHECKING:
    from .files import File
    from .fileset import Fileset
    from .project import Project


class Design:
    def __init__(self, name: str, **attributes) -> None:
        self._name = name
        self._project: Project|None = None
        self._filesets = nx.DiGraph()
        self._files = nx.DiGraph()
        self._toplevels: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def toplevels(self) -> list[str]:
        return self._toplevels

    def files(
        self,
        file_type: Type[File] | tuple[Type[File], ...] | None = None,
        **filters,
    ) -> Generator[File, None, None]:
        """
        Retrieves files from the design, with optional filtering.
        If no arguments are provided, all files are returned.
        """
        all_files = nx.topological_sort(self._files)
        if file_type is None and not filters:
            return all_files
        return filter_files(all_files, file_type=file_type, **filters)

    @property
    def filesets(self) -> Generator[File, None, None]:
        return nx.topological_sort(self._filesets)

    def add_fileset(self, fileset: Fileset) -> None:
        fileset._project = self._project
        self._filesets.add_node(fileset)

    def add_toplevel(self, name: str, type: str = '') -> None:
        self._toplevels.append(name)

    def validate(self) -> None:
        is_dag_fileset = nx.is_directed_acyclic_graph(self._filesets)
        if not is_dag_fileset:
            cycle_edges = nx.find_cycle(self._filesets)
            # Format the cycle into a human-readable string like "A -> C -> A"
            path = " -> ".join(str(u) for u, v in cycle_edges) + f" -> {cycle_edges[0][0]}"
            raise SystemError(f'Cyclic dependency found: {path}')
