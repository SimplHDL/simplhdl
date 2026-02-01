from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Type

import networkx as nx

from .files import filter_files
from .project import ProjectError
from .fileset import FileOrder, FilesetOrder

if TYPE_CHECKING:
    from .attributes import Library
    from .files import File
    from .fileset import Fileset
    from .project import Project

__all__ = ["Design"]

logger = logging.getLogger(__name__)


class Design:
    def __init__(self, name: str, **attributes) -> None:
        self._name = name
        self._project: Project | None = None
        self._filesets = nx.DiGraph()
        self._files = nx.DiGraph()
        self._toplevels: list[str] = []
        self._libraries: dict[str, Library] = {}
        self._default_library: Library | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def defaultLibrary(self) -> Library | None:
        return self._default_library

    @defaultLibrary.setter
    def defaultLibrary(self, library: Library) -> None:
        if library.name not in self._libraries:
            self.add_library(library)  # Ensure the library is added if it's new
        self._default_library = library

    @property
    def toplevels(self) -> list[str]:
        return self._toplevels

    @toplevels.setter
    def toplevels(self, top: list[str] | str) -> None:
        if isinstance(top, str):
            self._toplevels = [top]
        else:
            self._toplevels = top

    @property
    def libraries(self) -> list[Library]:
        return list(self._libraries.values())

    def files(
        self,
        type: Type[File] | tuple[Type[File], ...] | None = None,
        order: FileOrder = FileOrder.COMPILE,
        **filters,
    ) -> list[File]:
        """
        Retrieves files from the design, with optional filtering.
        If no arguments are provided, all files are returned.
        """
        all_files = list(nx.topological_sort(self._files))
        if type is None and not filters:
            file_collection = all_files
        else:
            file_collection = list(filter_files(all_files, file_type=type, **filters))
        if order == FileOrder.COMPILE:
            return list(reversed(file_collection))
        elif order == FileOrder.STRATA:
            raise NotImplementedError("FileOrder.STRATA not implemented yet")
        return file_collection

    def filesets(self, order: FilesetOrder = FilesetOrder.COMPILE) -> list[File]:
        fs = list(nx.topological_sort(self._filesets))
        if order == FilesetOrder.HIERARCHY:
            return fs
        return list(reversed(fs))

    @property
    def roots(self) -> list[Fileset]:
        graph = self._filesets
        return [n for n in graph.nodes() if graph.in_degree(n) == 0]

    def add_fileset(self, fileset: Fileset) -> None:
        fileset._project = self._project
        self._filesets.add_node(fileset)

    def add_toplevel(self, name: str, type: str = "") -> None:
        self._toplevels.append(name)

    def add_library(self, library: Library) -> None:
        if library.name in self._libraries:
            # logger.warning(f'Library {library.name} already exists')
            return
        if not self._libraries:
            self._default_library = library
        self._libraries[library.name] = library

    def validate(self) -> None:
        is_dag_fileset = nx.is_directed_acyclic_graph(self._filesets)
        logger.debug(f"Fileset DAG check: {is_dag_fileset}")
        if not is_dag_fileset:
            cycle_edges = nx.find_cycle(self._filesets)
            # Format the cycle into a human-readable string like "A -> C -> A"
            path = " -> ".join(str(u) for u, v in cycle_edges) + f" -> {cycle_edges[0][0]}"
            raise ProjectError(f"Cyclic dependency found: {path}")
        is_dag_file = nx.is_directed_acyclic_graph(self._files)
        logger.debug(f"Files DAG check: {is_dag_file}")
        if not is_dag_file:
            cycle_edges = nx.find_cycle(self._files)
            # Format the cycle into a human-readable string like "A -> C -> A"
            path = " -> ".join(str(u) for u, v in cycle_edges) + f" -> {cycle_edges[0][0]}"
            raise ProjectError(f"Cyclic dependency found: {path}")

    def elaborate(self) -> None:
        """
        Establish file dependencies based on fileset relationships.

        For now all the root node files in the parent fileset is connected to
        the leaf node files in the child fileset.
        """
        for fileset in self.filesets(order=FilesetOrder.COMPILE):
            fileset.connect_files_to_parents()

    def get_file(self, path: Path | str) -> File | None:
        if isinstance(path, str):
            path = Path(path).resolve()
        for file in self._files.nodes():
            if file.path.resolve() == path.resolve():
                return file
