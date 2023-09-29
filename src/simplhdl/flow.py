from argparse import Namespace
from pathlib import Path
from typing import Callable, Dict
from abc import ABCMeta, abstractmethod

from .project import Project


class FlowBase(metaclass=ABCMeta):

    def __init__(self, name):
        self.name = name

    @classmethod
    @abstractmethod
    def parse_args(self, parser) -> None:
        pass

    @abstractmethod
    def run(self, args: Namespace, project: Project, builddir: Path) -> None:
        pass


class FlowFactory:
    """
    Factory for creating flows
    """

    registry: Dict[str, FlowBase] = dict()

    @classmethod
    def register(cls, name: str) -> Callable:

        def inner_wrapper(wrapped_class: FlowBase) -> 'FlowBase':
            if name in cls.registry:
                raise Exception(f"Flow {name} already exists.")
            cls.registry[name] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def get_flow(cls, name: str) -> 'FlowBase':
        if name in cls.registry:
            return cls.registry[name](name)
        raise Exception(f"Couldn't find Flow named {name}")

    @classmethod
    def get_flows(cls) -> Dict[str, 'FlowBase']:
        return cls.registry
