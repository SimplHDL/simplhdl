from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Type

if TYPE_CHECKING:
    from pathlib import Path

    import networkx as nx

    from .attributes import Library
    from .fileset import Fileset

logger = logging.getLogger(__name__)
simulation = "simulation"
implementation = "implementation"


class File:
    _default_usedin: list[str] = []
    _default_encrypt: bool = False

    def __init__(self, file: Path, **attributes) -> None:
        self._path: Path = file.absolute().resolve()
        self._graph: nx.DiGraph[File]|None = None
        self._parent: Fileset|None = None
        self._usedin: list[str] = attributes.get('usedin', self._default_usedin)
        self._encrypt: bool = attributes.get('encrypt', self._default_encrypt)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def parent(self) -> Fileset:
        return self._parent

    @parent.setter
    def parent(self, parent: Fileset) -> None:
        self._parent = parent

    @property
    def usedin(self) -> list[str]:
        return self._usedin

    @property
    def encrypt(self) -> bool:
        return self._encrypt

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self):
        return f'{self.__class__.__name__}(path={self._path}, parent={self._parent})'


FileClass = Type[File]


class FileFactory:

    _registered_types: dict[str, type[File]] = {}
    _registered_extensions: dict[str, type[File]] = {}


    @classmethod
    def register(cls, extension: str|list[str] = list()) -> Callable[[FileClass], FileClass]:
        """
        The decorator factory. It takes the extension argument and returns
        the actual decorator function.
        """
        if isinstance(extension, str):
            extensions = [extension]
        else:
            extensions = extension

        def decorator(file_class: FileClass) -> FileClass:
            """
            The actual decorator. It registers the class and returns it unmodified.
            """
            for ext in extensions:
                if ext in cls._registered_extensions:
                    raise ValueError(
                        f"Extension '{ext}' already registered by {cls._registered_extensions[ext].__name__}"
                    )
                # Register the class with its normalized extension
                cls._registered_extensions[ext] = file_class
                logger.debug(f"Registered {file_class.__name__} for extension '{ext}'")

            class_name = file_class.__name__.lower()
            if class_name in cls._registered_types:
                raise ValueError(f"Class '{class_name}' already registered.")
            # Register the class with its class name
            cls._registered_types[class_name] = file_class
            return file_class

        return decorator

    @classmethod
    def create(cls, file: Path, type: str = '', **attributes) -> File:
        filename_lower = file.name.lower()
        type_lower = type.lower()

        # If type is not None, we lookup registered type
        # Else we lookup extension
        if type_lower and type_lower in cls._registered_types:
            file_class = cls._registered_types[type_lower]
            return file_class(file, **attributes)
        else:
            # Sort extensions by length, descending, to find the longest match first.
            # This handles cases like '.step.tcl' before '.tcl'.
            sorted_extensions = sorted(cls._registered_extensions.keys(), key=len, reverse=True)

            for ext in sorted_extensions:
                if filename_lower.endswith(ext):
                    file_class = cls._registered_extensions[ext]
                    return file_class(file, **attributes)

        return UnknownFile(file, **attributes)


@FileFactory.register()
class UnknownFile(File):
    ...


class HdlFile(File):
    """Represents a Hardware Description Language (HDL) source file.

    This class serves as a base for specific HDL file types like Verilog or VHDL.
    It manages common attributes applicable to HDL source files.
    """
    _default_usedin = [simulation, implementation]
    _default_encrypt = True

    def __init__(self, file: Path, **attributes) -> None:
        """Initializes the HdlFile instance.

        Args:
            file: The path to the HDL file.
            **attributes: A dictionary of attributes for the file.

        Attributes:
            usedin: A list of strings specifying the contexts where the file is used.
                Defaults to `['simulation', 'implementation']`.
            encrypt: A boolean indicating whether the file should be encrypted.
                Defaults to `True`.
            library: The HDL library this file belongs to. Defaults to `None`.
        """
        super().__init__(file, **attributes)
        self._library: Library = attributes.get('library', None)

    @property
    def library(self) -> Library:
        return self._library


@FileFactory.register(extension='.sv')
class SystemVerilogFile(HdlFile):
    ...


@FileFactory.register(extension='.v')
class VerilogFile(HdlFile):
    ...


@FileFactory.register(extension=['.vh', '.svh'])
class VerilogIncludeFile(HdlFile):
    ...


@FileFactory.register(extension=['.vhd', '.vhdl'])
class VhdlFile(HdlFile):
    ...


class ImplementationFile(File):
    _default_usedin = [implementation]


class SimulationFile(File):
    _default_usedin = [simulation]


class IPSpecificationFile(File):
    _default_usedin = [simulation, implementation]


@FileFactory.register(extension='.sdc')
class SdcFile(ImplementationFile):
    ...


@FileFactory.register(extension=['.edn', '.edif'])
class EdifFile(ImplementationFile):
    ...

@FileFactory.register(extension=['.c', '.h', '.s'])
class CFile(File):
    ...


class SystemCFile(File):
    ...


@FileFactory.register(extension='.py')
class CocotbPythonFile(SimulationFile):
    ...


@FileFactory.register(extension='.qsf')
class QuartusQsfFile(ImplementationFile):
    ...


@FileFactory.register(extension='.qip')
class QuartusQipFile(ImplementationFile):
    ...


@FileFactory.register(extension='.qsys')
class QuartusQsysFile(IPSpecificationFile):
    ...


@FileFactory.register(extension='.ip')
class QuartusIpFile(IPSpecificationFile):
    ...


@FileFactory.register(extension='.ipx')
class QuartusIpxFile(IPSpecificationFile):
    ...

@FileFactory.register(extension='.source.tcl')
class QuartusTCLSourceFile(ImplementationFile):
    ...


@FileFactory.register(extension='.xdc')
class VivadoXdcFile(ImplementationFile):
    ...


@FileFactory.register(extension='.dcp')
class VivadoDcpFile(ImplementationFile):
    ...


@FileFactory.register(extension='.xci')
class VivadoXciFile(IPSpecificationFile):
    ...


@FileFactory.register(extension='.xcix')
class VivadoXcixFile(IPSpecificationFile):
    ...


@FileFactory.register(extension='.bd')
class VivadoBdFile(IPSpecificationFile):
    ...


@FileFactory.register(extension='.bd.tcl')
class VivadoBdTclFile(IPSpecificationFile):
    ...


@FileFactory.register(extension='.step.tcl')
class VivadoStepFile(ImplementationFile):
    ...


@FileFactory.register(extension='.sbt')
class ChiselBuildFile(File):
    ...
