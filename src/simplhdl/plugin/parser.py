from __future__ import annotations

import logging

from pathlib import Path
from abc import ABCMeta, abstractmethod
from argparse import Namespace

from ..project.fileset import Fileset
from ..project.project import Project

__all__ = ["ParserBase", "ParserError"]

logger = logging.getLogger(__name__)


class ParserBase(metaclass=ABCMeta):
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
    def get_parser(cls, filename: Path) -> ParserBase:
        for parser_class in cls.registry.values():
            parser = parser_class()
            if parser.is_valid_format(filename):
                return parser
        if filename is None:
            raise ParserError("Couldn't find any project specification in current directory")
        else:
            raise ParserError(f"Couldn't find Parser for parsing '{filename}'")


class ParserError(Exception):
    pass
