from pathlib import Path
from typing import Callable
from abc import ABCMeta, abstractmethod


class ParserBase(metaclass=ABCMeta):

    def __init__(self, filename: Path, **kwargs):
        self.filename = filename

    @abstractmethod
    def parse(self):
        pass


class ParserFactory:
    """
    Factory for creating parsers
    """

    registry = {}

    @classmethod
    def register(cls) -> Callable:

        def inner_wrapper(wrapped_class: ParserBase) -> Callable:
            name = wrapped_class.__name__
            if name in cls.registry:
                raise Exception(f"Parser {name} already exists.")
            cls.registry[name] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def get_parser(cls, filename: Path, **kwargs) -> 'ParserBase':
        for parser_class in cls.registry.values():
            parser = parser_class(filename, **kwargs)
            if parser.is_valid_format():
                return parser
        raise Exception(f"Couldn't find Parser for parsing {filename}")
