from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Dict, Generator
from abc import ABCMeta, abstractmethod

from ..project.files import File, UsedIn
from ..project.fileset import FileOrder, Fileset
from ..project.project import Project
from .flow import FlowBase, FlowCategory
from .parser import _load_priority_overrides

__all__ = ["GeneratorBase", "GeneratorError"]


class GeneratorError(Exception):
    pass


class GeneratorBase(metaclass=ABCMeta):
    priority = 50
    # None means a legacy plugin has not declared its inputs: do not skip it.
    supported_file_types: tuple[type[File], ...] | None = None
    usedin: UsedIn | None = None

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        self.name = name
        self.args = args
        self.project = project
        self.builddir = builddir

    @abstractmethod
    def run(self, flow: FlowBase) -> None:
        pass

    def accepts_file(self, file: File, flow: FlowBase | None = None) -> bool:
        if self.supported_file_types is not None and not isinstance(file, self.supported_file_types):
            return False
        if self.usedin is not None and self.usedin not in file.usedin:
            return False
        flow_usedin = getattr(flow, "usedin", None)
        if flow_usedin is not None:
            return flow_usedin in file.usedin
        category = getattr(flow, "category", FlowCategory.DEFAULT)
        if category == FlowCategory.SIMULATION:
            return UsedIn.SIMULATION in file.usedin
        if category == FlowCategory.IMPLEMENTATION:
            return UsedIn.IMPLEMENTATION in file.usedin
        return True

    def get_files(
        self, flow: FlowBase | None = None, fileset: Fileset | None = None, order: FileOrder = FileOrder.COMPILE
    ) -> list[File]:
        target = fileset if fileset is not None else self.project.defaultDesign
        if target is None:
            return []
        return [file for file in target.files(order=order) if self.accepts_file(file, flow)]


class GeneratorFactory:
    """
    Factory for creating generators
    """

    registry: Dict[str, GeneratorBase] = dict()

    @classmethod
    def register(cls, name: str, _class: GeneratorBase) -> None:
        if name in cls.registry:
            raise Exception(f"Generator {name} already exists.")
        cls.registry[name] = _class

    @classmethod
    def get_generator(cls, name: str, args: Namespace, project: Project, builddir: Path) -> "GeneratorBase":
        if name in cls.registry:
            return cls.registry[name](name, args, project, builddir)
        raise Exception(f"Couldn't find Generator named {name}")

    @classmethod
    def get_generators(cls, args: Namespace, project: Project, builddir: Path) -> Generator[GeneratorBase, None, None]:
        for name, _, _ in cls.get_ordered_generators():
            yield cls.get_generator(name, args, project, builddir)

    @classmethod
    def get_ordered_generators(cls):
        overrides = _load_priority_overrides("generator", "SIMPLHDL_GENERATORS")
        ordered = [
            (
                name,
                generator,
                overrides.get(name, overrides.get(generator.__name__, getattr(generator, "priority", 50))),
            )
            for name, generator in cls.registry.items()
        ]
        return sorted(ordered, key=lambda item: item[2], reverse=True)
