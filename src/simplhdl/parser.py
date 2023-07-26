from pathlib import Path
from typing import Callable
from abc import ABCMeta, abstractmethod
from pyEDAA.ProjectModel import FileSet  # type: ignore


class ParserBase(metaclass=ABCMeta):

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def is_valid_format(self, filename: Path) -> bool:
        pass

    @abstractmethod
    def parse(self, filename: Path) -> 'FileSet':
        pass


class ParserFactory:
    """
    Factory for creating parsers
    """

    registry: dict = {}

    @classmethod
    def register(cls) -> Callable:

        def inner_wrapper(wrapped_class: ParserBase) -> 'ParserBase':
            name = wrapped_class.__name__  # type: ignore
            if name in cls.registry:
                raise Exception(f"Parser {name} already exists.")
            cls.registry[name] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def get_parser(cls, filename: Path, **kwargs) -> 'ParserBase':
        for parser_class in cls.registry.values():
            parser = parser_class(**kwargs)
            if parser.is_valid_format(filename):
                return parser
        raise Exception(f"Couldn't find Parser for parsing {filename}")
