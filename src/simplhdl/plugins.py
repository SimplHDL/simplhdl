import sys
import logging

import simplhdl.parsers

from typing import Iterator
from pkgutil import iter_modules, ModuleInfo
from importlib import import_module

logger = logging.getLogger(__name__)


def iter_namespace(package) -> Iterator[ModuleInfo]:
    modules = iter_modules(package.__path__, package.__name__ + '.')
    return modules


def load_builtin_plugins() -> None:
    """
    Loads builtin plugins.
    """
    plugins = {
        name: import_module(name) for finder, name, ispkg in iter_namespace(simplhdl.parsers)
    }
    logger.debug(plugins)


def load_external_plugins() -> None:
    """
    Loads external plugins.
    """
    if sys.version_info < (3, 10):
        from importlib_metadata import entry_points
    else:
        from importlib.metadata import entry_points

    plugins = entry_points(group='simplhdl.plugins')
    for plugin in plugins:
        plugin.load()


def load_plugins() -> None:
    """
    Loads all plugins, both builtin and external.
    """
    load_builtin_plugins()
    load_external_plugins()
