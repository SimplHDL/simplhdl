from __future__ import annotations

from abc import ABCMeta, abstractmethod
from argparse import Namespace
import logging
import os
from pathlib import Path
import re

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from ..project.fileset import Fileset
from ..project.project import Project

__all__ = ["ParserBase", "ParserError"]

logger = logging.getLogger(__name__)


def _load_parser_priority_overrides() -> dict[str, int]:
    """
    Load parser priority overrides from `SIMPLHDL_CONFIG` (TOML `[parser] priority`)
    and `SIMPLHDL_PARSER` (environment variable).
    """
    overrides: dict[str, int] = {}

    config_path = os.getenv("SIMPLHDL_CONFIG")
    if config_path:
        tomlfile = Path(config_path)
        if tomlfile.is_file():
            try:
                with tomlfile.open("rb") as f:
                    config = tomllib.load(f)
                parser_cfg = config.get("parser", {})
                priority_cfg = parser_cfg.get("priority")
                if isinstance(priority_cfg, str):
                    overrides[priority_cfg.strip()] = 500
                elif isinstance(priority_cfg, list):
                    base = 500 + len(priority_cfg) * 10
                    for idx, name in enumerate(priority_cfg):
                        if isinstance(name, str) and name.strip():
                            overrides[name.strip()] = base - idx * 10
                elif isinstance(priority_cfg, dict):
                    for name, val in priority_cfg.items():
                        if isinstance(name, str) and isinstance(val, int):
                            overrides[name.strip()] = val
            except Exception as exc:
                logger.warning(f"Failed to read [parser] priority from SIMPLHDL_CONFIG='{tomlfile}': {exc}")

    env_parser = os.getenv("SIMPLHDL_PARSER")
    if env_parser:
        names = [n.strip() for n in re.split(r"[,:]", env_parser) if n.strip()]
        base = 1000 + len(names) * 10
        for idx, name in enumerate(names):
            overrides[name] = base - idx * 10

    return overrides


class ParserBase(metaclass=ABCMeta):
    priority: int = 50
    format_guide: str | None = None

    def __init__(self):
        pass

    @abstractmethod
    def is_valid_format(self, filename: Path) -> bool:
        pass

    @abstractmethod
    def parse(self, filename: Path, project: Project, args: Namespace) -> Fileset:
        pass


class NoParser(ParserBase):
    """
    This parser always returns an empty fileset
    """

    priority: int = -1

    def is_valid_format(self, filename: Path) -> bool:
        return True

    def parse(self, filename: Path, project: Project, args: Namespace) -> Fileset:
        return Fileset("Empty")


class ParserFactory:
    """
    Factory for creating parsers
    """

    registry: dict = {}

    @classmethod
    def register(cls, name: str, _class: ParserBase) -> None:
        if name in cls.registry:
            raise Exception(f"Parser {name} already exists.")
        cls.registry[name] = _class

    @classmethod
    def get_ordered_parsers(cls, include_wip: bool = True) -> list[tuple[str, type[ParserBase], int]]:
        """
        Return registered parsers as `(name, parser_class, effective_priority)`
        sorted from highest priority to lowest.

        Default priority order:
        1. Explicit overrides (`SIMPLHDL_PARSER` env var, then `SIMPLHDL_CONFIG` `[parser].priority`)
        2. Third-party parser plugins (`priority = 50` default)
        3. `simplhdl_parser` fallback (`priority = 10`)
        4. Work-in-progress parsers with `priority <= 0` (excluded when `include_wip=False`)
        """
        overrides = _load_parser_priority_overrides()
        ordered: list[tuple[str, type[ParserBase], int]] = []
        for name, parser_class in cls.registry.items():
            default_prio = int(getattr(parser_class, "priority", 50))
            eff_prio = overrides.get(name, overrides.get(parser_class.__name__, default_prio))
            if not include_wip and eff_prio <= 0:
                continue
            ordered.append((name, parser_class, eff_prio))

        ordered.sort(key=lambda item: item[2], reverse=True)
        return ordered

    @classmethod
    def get_parser(cls, filename: Path) -> ParserBase:
        for _, parser_class, _ in cls.get_ordered_parsers(include_wip=True):
            parser = parser_class()
            if parser.is_valid_format(filename):
                return parser
        if filename is None:
            raise ParserError("Couldn't find any project specification in current directory")
        else:
            raise ParserError(f"Couldn't find Parser for parsing '{filename}'")


class ParserError(Exception):
    pass
