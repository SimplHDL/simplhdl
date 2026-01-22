from __future__ import annotations

from enum import auto, Enum
import logging
from typing import TYPE_CHECKING, Generator, Type
from weakref import WeakValueDictionary

import networkx as nx

from .files import filter_files
from .project import Project

if TYPE_CHECKING:
    from .attributes import Library
    from .files import File

logger = logging.getLogger(__name__)


class FileOrder(Enum):
    COMPILE = auto()
    HIERACHY = auto()
    STRATA = auto()


class FilesetOrder(Enum):
    COMPILE = auto()
    HIERACHY = auto()
    STRATA = auto()


class Fileset:
    _cache = WeakValueDictionary()

    def __new__(cls, name: str, **attributes) -> Fileset:
        if name in cls._cache:
            return cls._cache[name]

        instance = super().__new__(cls)
        cls._cache[name] = instance
        return instance

    def __init__(self, name: str, **attributes) -> None:
        if hasattr(self, '_initialized'):
            logger.debug(f'Fileset {self.name} already initialized')
            return

        self._name: str = name
        self._project: Project = Project()
        self.library = attributes.get('library', None)
        self._leafs: list = []
        self._roots: list = []
        self._initialized = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def project(self) -> Project:
        return self._project

    def files(
        self,
        type: Type[File] | tuple[Type[File], ...] | None = None,
        order: FileOrder = FileOrder.COMPILE,
        **filters,
    ) -> Generator[File, None, None]:
        """
        Retrieves files from the fileset, with optional filtering.
        If no arguments are provided, all files in this fileset are returned.
        """
        file_nodes = [f for f in self._files.nodes() if f.parent is self]
        subgraph = self._files.subgraph(file_nodes)
        all_files = nx.topological_sort(subgraph)

        if type is None and not filters:
            file_collection = all_files
        else:
            file_collection = filter_files(all_files, file_type=type, **filters)
        if order == FileOrder.COMPILE:
            return list(reversed(list(file_collection)))
        elif order == FileOrder.HIERACHY:
            return list(file_collection)
        elif order == FileOrder.STRATA:
            raise NotImplementedError("FileOrder.STRATA not implemented yet")
        raise NotImplementedError(f"Order '{order}' does not exists")

    @property
    def filesets(self) -> nx.DiGraph:
        return list(self._project.defaultDesign._filesets.subgraph(self.descendants))

    @property
    def children(self) -> set[Fileset]:
        return list(self._project.defaultDesign._filesets.successors(self))

    @property
    def parents(self) -> list[Fileset] | None:
        return list(self._project.defaultDesign._filesets.predecessors(self))

    @property
    def ancestors(self) -> set[Fileset]:
        return nx.ancestors(self._filesets, self)

    @property
    def descendants(self) -> set[Fileset]:
        return nx.descendants(self._filesets, self)

    @property
    def library(self) -> Library:
        if not self._library and self._project.defaultDesign:
            return self._project.defaultDesign.defaultLibrary
        return self._library

    @library.setter
    def library(self, library: Library) -> None:
        self._library = library
        if library:
            self._project.defaultDesign.add_library(library)

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
        self._filesets.add_edge(self, fileset)

    def add_filesets(self, filesets: list[Fileset]) -> None:
        for fileset in filesets:
            self.add_fileset(fileset)

    def add_file(self, file: File) -> None:
        if file.parent not in [None, self]:
            logger.warning(f"File '{file}' already belongs to the fileset"
                           f"'{file.parent}' and will now be added to '{self}'")
        # return if node is already added
        if self._files.has_node(file):
            return
        # if this is the first file
        elif not self._roots:
            self._files.add_node(file)
            file._parent = self
            self._roots = [file]
            self._leafs = [file]
        # If this is not the first file add and edge from this file to all
        # roots and set this as the new root
        elif self._roots and file not in self._roots:
            for r in self._roots:
                self._files.add_edge(file, r)
            file._parent = self
            self._roots = [file]
        if hasattr(file, 'library') and file.library is not None:
            self._project.defaultDesign.add_library(file.library)

    def insert_file_after(self, file: File, new_file: File) -> None:
        if file is new_file:
            return
        children = list(self._files.successors(file))
        self._files.add_edge(file, new_file)
        new_file._parent = self
        for child in children:
            if child is new_file:
                continue
            self._files.add_edge(new_file, child)
            self._files.remove_edge(file, child)
        if file in self._leafs:
            self._leafs.remove(file)
            self._leafs.append(new_file)

    def get_parents_leaf_files(self) -> list[File] | None:
        files = []
        for parent in self.parents:
            # if leafs extend list else move up to grand parent
            if parent._leafs:
                files.extend(parent._leafs)
            else:
                files.extend(parent.get_parents_leaf_files())
        return files

    def get_parents_root_files(self) -> list[File] | None:
        files = []
        for parent in self.parents:
            # if roots extend list else move up to grand parent
            if parent._roots:
                files.extend(parent._roots)
            else:
                files.extend(parent.get_parents_root_files())
        return files

    def connect_files_to_parents(self, fileset: Fileset | None = None) -> None:
        if fileset is None:
            fileset = self
        for parent in self.parents:
            if not parent.files():
                parent.connect_files_to_parents(fileset)
            for leaf in parent._leafs:
                for root in fileset._roots:
                    self._files.add_edge(leaf, root)

    def __str__(self) -> str:
        return str(self._name)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(name={self._name}, library={self._library})'

    def __eq__(self, other):
        return (
            isinstance(other, Fileset) and
            self.name == other.name and
            self.library == other.library
        )

    def __hash__(self):
        return hash(self.name)
