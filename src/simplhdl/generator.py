from argparse import Namespace
from pathlib import Path
from typing import Callable, Dict, Generator
from abc import ABCMeta, abstractmethod

from .pyedaa.project import Project
from .flow import FlowCategory


class GeneratorError(Exception):
    pass


class GeneratorBase(metaclass=ABCMeta):

    def __init__(
        self,
        name,
        args: Namespace,
        project: Project,
        builddir: Path
    ):
        self.name = name
        self.args = args
        self.project = project
        self.builddir = builddir

    @abstractmethod
    def run(self, flowcategory: FlowCategory) -> None:
        pass


class GeneratorFactory:
    """
    Factory for creating generators
    """

    registry: Dict[str, GeneratorBase] = dict()

    @classmethod
    def register(cls, name: str) -> Callable:

        def inner_wrapper(wrapped_class: GeneratorBase) -> 'GeneratorBase':
            if name in cls.registry:
                raise Exception(f"Generator {name} already exists.")
            cls.registry[name] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def get_generator(
        cls,
        name: str,
        args: Namespace,
        project: Project,
        builddir: Path
    ) -> 'GeneratorBase':
        if name in cls.registry:
            return cls.registry[name](name, args, project, builddir)
        raise Exception(f"Couldn't find Generator named {name}")

    @classmethod
    def get_generators(
        cls,
        args: Namespace,
        project: Project,
        builddir: Path
    ) -> Generator[GeneratorBase, None, None]:
        for name in cls.registry:
            yield cls.get_generator(name, args, project, builddir)
