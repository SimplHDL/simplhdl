from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .attributes import Target
    from .design import Design

logger = logging.getLogger(__name__)


class Project:

    def __init__(self, name: str, **attributes) -> None:
        self._name = name
        self._designs: list[Design] = []
        self._part: str|None = None
        self._generics: dict[str, str]
        self._parameters: dict[str, str]
        self._defines: dict[str, str]
        self._plusargs: dict[str, str]
        self._hooks: dict[str, dict[str]]
        self._targets: dict[str, Target] = {}
        # _repos: dict[str, Repo]
        # _reposdir: Path|None = None

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._name = name

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

    def add_design(self, design: Design) -> None:
        self._designs.append(design)

    def add_define(self, name: str, value: str) -> None:
        if name in self._defines:
            logger.warning(f"Define '{name}' already exists")
        else:
            self._defines[name] = value

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


    def add_target(self, target: Target) -> None:
        if target.name in self._targets:
            logger.warning(f"Ignore '{target.name}', target already exists")
        else:
            self._targets[target.name] = target

    def validate(self) -> None:
        for design in self._designs:
            design.validate()
