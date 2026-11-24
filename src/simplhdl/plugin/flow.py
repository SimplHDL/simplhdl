from __future__ import annotations

import logging

from argparse import Namespace
from pathlib import Path
from typing import Dict, Set
from abc import ABCMeta, abstractmethod
from enum import Flag, auto

from ..project.project import Project
from ..project.files import File, UsedIn
from ..project.fileset import FileOrder, Fileset

__all__ = ["FlowBase", "FlowError", "FlowTools", "FlowCategory"]


class FlowBase(metaclass=ABCMeta):
    # None means the plugin has not declared a complete selection contract.
    supported_file_types: tuple[type[File], ...] | None = None
    usedin: UsedIn | None = None

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        self.name: str = name
        self.args: Namespace = args
        self.project: Project = project
        self.builddir: Path = builddir
        self.category: FlowCategory = FlowCategory.DEFAULT
        self.tools: Set = set()
        self.builddir.mkdir(parents=True, exist_ok=True)
        file = logging.FileHandler(self.builddir.joinpath("simplhdl.log"), mode="w")
        file.setLevel(logging.NOTSET)
        file.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s:%(filename)s:%(lineno)d - %(message)s"))
        logging.getLogger().addHandler(file)

    @classmethod
    @abstractmethod
    def parse_args(self, parser) -> None:
        pass

    @abstractmethod
    def run(self) -> None:
        pass

    def accepts_file(self, file: File) -> bool:
        return (self.usedin is None or self.usedin in file.usedin) and (
            self.supported_file_types is None or isinstance(file, self.supported_file_types)
        )

    def get_files(
        self, fileset: Fileset | None = None, order: FileOrder = FileOrder.COMPILE, include_generated: bool = True
    ) -> list[File]:
        target = fileset if fileset is not None else self.project.defaultDesign
        if target is None:
            return []
        return [
            file
            for file in target.files(order=order)
            if self.accepts_file(file) and (include_generated or not file.generated)
        ]


class FlowTools(Flag):
    VCS = auto()
    QUESTASIM = auto()
    MODELSIM = auto()
    XCELIUM = auto()
    RIVIERAPRO = auto()
    XSIM = auto()
    VERILATOR = auto()
    ICARUS = auto()
    GHDL = auto()
    ISE = auto()
    VIVADO = auto()
    QUARTUS = auto()
    NCSIM = auto()
    UNKNOWN = auto()


class FlowCategory(Flag):
    DEFAULT = auto()
    SIMULATION = auto()
    IMPLEMENTATION = auto()


class FlowError(Exception):
    pass


def inspection_files(project, flow=None, generators=(), fileset=None, include_generator_inputs=False):
    """Select an inspection view using the same selectors as flow and generator plugins."""
    target = fileset if fileset is not None else project.defaultDesign
    if target is None:
        return []
    ordered = list(target.files(order=FileOrder.COMPILE))
    if flow is None:
        return ordered
    # Legacy plugins may already use get_files() for an unrelated API.
    # Without a declared contract, retain a conservative project view.
    if flow.supported_file_types is None:
        selected = {file for file in ordered if flow.usedin is None or flow.usedin in file.usedin}
    else:
        selected = set(flow.get_files(fileset))
    if include_generator_inputs:
        for generator in generators:
            if generator.supported_file_types is not None:
                selected.update(generator.get_files(flow, fileset))
    return [file for file in ordered if file in selected]


class FlowFactory:
    """
    Factory for creating flows
    """

    registry: Dict[str, FlowBase] = dict()

    @classmethod
    def register(cls, name: str, _class: FlowBase) -> None:
        if name in cls.registry:
            raise Exception(f"Flow {name} already exists.")
        cls.registry[name] = _class

    @classmethod
    def get_flow(cls, name: str, args: Namespace, project: Project, builddir: Path) -> "FlowBase":
        if name in cls.registry:
            return cls.registry[name](name, args, project, builddir)
        raise Exception(f"Couldn't find Flow named {name}")

    @classmethod
    def get_flows(cls) -> Dict[str, "FlowBase"]:
        return cls.registry
