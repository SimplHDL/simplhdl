import logging

try:
    from importlib.metadata import entry_points, EntryPoint
except ImportError:
    from importlib_metadata import entry_points, EntryPoint

from importlib import import_module
from itertools import chain
from pkgutil import ModuleInfo, iter_modules
from typing import Iterator

import simplhdl
import simplhdl.flows
import simplhdl.generators
import simplhdl.parsers

from .generator import GeneratorBase, GeneratorFactory
from .parser import ParserBase, ParserFactory
from .flow import FlowBase, FlowFactory

logger = logging.getLogger(__name__)


def iter_namespace(package) -> Iterator[ModuleInfo]:
    modules = iter_modules(package.__path__, package.__name__ + '.')
    return modules


def load_builtin_plugins() -> None:
    """
    Loads builtin plugins.
    """
    import_module('simplhdl.info')
    import_module('simplhdl.run')
    import_module('simplhdl.flows.vcs.vcsflow')
    import_module('simplhdl.flows.questasim.questasimflow')
    import_module('simplhdl.flows.modelsim.modelsimflow')
    import_module('simplhdl.flows.xsim.xsimflow')
    import_module('simplhdl.flows.rivierapro.rivieraproflow')
    import_module('simplhdl.flows.quartusdse.quartusdseflow')
    import_module('simplhdl.flows.quartusexport.quartusexportflow')
    import_module('simplhdl.flows.encrypt.encryptflow')
    import_module('simplhdl.flows.vsg.vsgflow')
    import_module('simplhdl.flows.verible.veribleflow')
    import_module('simplhdl.flows.lint.lintflow')
    import_module('simplhdl.flows.flake8.flake8flow')
    packages = chain(
        iter_namespace(simplhdl.parsers),
        iter_namespace(simplhdl.flows),
        iter_namespace(simplhdl.generators))
    plugins = {
        name: import_module(name) for _, name, _ in packages
    }
    logger.debug(plugins)


def get_external_plugins(group_name: str) -> Iterator[EntryPoint]:
    """
    Retrieves all EntryPoint objects registered under a specific group name.

    Args:
        group_name: The string identifying the entry point group
                    (e.g., 'simplhdl.plugins').

    Returns:
        An iterator of EntryPoint objects.
    """
    try:
        # Use importlib.metadata to find registered entry points
        plugins = entry_points(group=group_name)
    except TypeError:
        # Fallback for older versions of Python that might not support the 'group' argument
        # This requires iterating through all entry points and filtering manually.
        all_entries = entry_points()
        # Note: entry_points() returns a dictionary-like object in Python < 3.10
        plugins = all_entries.get(group_name, [])

    return plugins


def load_external_plugins() -> None:
    """
    Loads external plugins.
    """
    for plugin in get_external_plugins("simplhdl.plugins"):

        try:
            # 1. Load the class/function explicitly
            PluginClass = plugin.load()

            # 2. Check if the class inherits from the expected base (GeneratorBase)
            # You might need to import GeneratorBase here for the check.
            if not issubclass(PluginClass, (ParserBase, GeneratorBase, FlowBase)):
                logger.warning(f"Plugin {plugin.name} is not a valid ParserBase, GeneratorBase, FlowBase.")
                continue

            if issubclass(PluginClass, ParserBase):
                ParserFactory.register(plugin.name, PluginClass)
                logger.debug(f"Registered external parser: {plugin.name}")

            if issubclass(PluginClass, GeneratorBase):
                GeneratorFactory.register(plugin.name, PluginClass)
                logger.debug(f"Registered external generator: {plugin.name}")

            if issubclass(PluginClass, FlowBase):
                FlowFactory.register(plugin.name, PluginClass)
                logger.debug(f"Registered external flow: {plugin.name}")

        except Exception as e:
            logger.error(f"Failed to load or register plugin {plugin.name}: {e}")


def load_plugins() -> None:
    """
    Loads all plugins, both builtin and external.
    """
    load_builtin_plugins()
    load_external_plugins()
