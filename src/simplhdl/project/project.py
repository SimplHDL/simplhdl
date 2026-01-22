from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from singleton_decorator import singleton

if TYPE_CHECKING:
    from pathlib import Path
    from .attributes import Target
    from .design import Design

logger = logging.getLogger(__name__)


class ProjectError(Exception):
    pass


@singleton
class Project:

    def __init__(self, name: str, **attributes) -> None:
        self._name = name
        self._designs: list[Design] = []
        self._part: str | None = None
        self._generics: dict[str, str] = {}
        self._parameters: dict[str, str] = {}
        self._defines: dict[str, str] = {}
        self._plusargs: dict[str, str] = {}
        self._hooks: dict[str, list[str]] = {}
        self._targets: dict[str, Target] = {}
        self._builddir: Path | None = None

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._name = name

    @property
    def buildDir(self) -> Path | None:
        return self._builddir

    @buildDir.setter
    def buildDir(self, path: Path):
        self._builddir = path

    @property
    def defaultDesign(self) -> Design | None:
        if self._designs:
            return self._designs[0]
        else:
            return None

    @property
    def part(self) -> str | None:
        return self._part

    @part.setter
    def part(self, part: str) -> None:
        self._part = part

    @property
    def generics(self) -> dict[str, str]:
        return self._generics

    @property
    def parameters(self) -> dict[str, str]:
        return self._parameters

    @property
    def defines(self) -> dict[str, str]:
        return self._defines

    @property
    def plusargs(self) -> dict[str, str]:
        return self._plusargs

    @property
    def hooks(self) -> dict[str, list[str]]:
        return self._hooks

    @property
    def targets(self) -> dict[str, Target]:
        return self._targets

    @property
    def defaultTarget(self) -> Target:
        try:
            return next(iter(self._targets.values()))
        except StopIteration:
            raise ProjectError("No target defined")

    def get_target(self, name: str) -> Target:
        try:
            return self._targets[name]
        except KeyError:
            raise ProjectError(f"Target '{name}' not found")

    def add_design(self, design: Design) -> None:
        design._project = self
        self._designs.append(design)

    def add_define(self, name: str, value: str) -> None:
        if name in self._defines:
            logger.warning(f"Define '{name}' already exists")
        else:
            self._defines[name] = value

    def add_parameter(self, name: str, value: str) -> None:
        if name in self._parameters:
            logger.warning(f"Parameter '{name}' already exists")
        else:
            self._parameters[name] = value

    def add_generic(self, name: str, value: str) -> None:
        if name in self._generics:
            logger.warning(f"Generic '{name}' already exists")
        else:
            self._generics[name] = value

    def add_plusarg(self, name: str, value: str) -> None:
        if name in self._plusargs:
            logger.warning(f"Plusarg '{name}' already exists")
        else:
            self._plusargs[name] = value

    def add_hook(self, name: str, command: str) -> None:
        try:
            self._hooks[name].append(command)
        except KeyError:
            self._hooks[name] = [command]

    def add_target(self, target: Target) -> None:
        if target.name in self._targets:
            logger.warning(f"Ignore '{target.name}', target already exists")
        else:
            self._targets[target.name] = target

    def validate(self) -> None:
        for design in self._designs:
            design.validate()

    def elaborate(self) -> None:
        for design in self._designs:
            design.elaborate()
