from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Type

from .attributes import Library

logger = logging.getLogger(__name__)
simulation = "simulation"
implementation = "implementation"


class File:
    def __init__(self, file: Path, **attributes) -> None:
        self._path = file.absolute().resolve()
        self._graph = None


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
    def create(cls, file: Path, **attributes) -> File:
        return cls._registered_types.get(file.suffix.lower(), UnknownFile)(file, **attributes)


@FileFactory.register()
class UnknownFile(File):
    ...


class HdlFile(File):
    """Represents a Hardware Description Language (HDL) source file.

    This class serves as a base for specific HDL file types like Verilog or VHDL.
    It manages common attributes applicable to HDL source files.
    """

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
        self._usedin: list[str] = attributes.get('usedin', [simulation, implementation])
        self._encrypt: bool = attributes.get('encrypt', True)
        self._library: Library = attributes.get('library', None)

    @property
    def usedin(self) -> list[str]:
        return self._usedin

    @property
    def encrypt(self) -> bool:
        return self._encrypt

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
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)
        self._usedin: list[str] = attributes.get('usedin', [implementation])


class SimulationFile(File):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)
        self._usedin: list[str] = attributes.get('usedin', [simulation])


class IPSpecificationFile(File):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)
        self._usedin: list[str] = attributes.get('usedin', [simulation, implementation])


@FileFactory.register(extension='.sdc')
class SdcFile(ImplementationFile):
    ...


@FileFactory.register(extension=['.edn', '.edif'])
class EdifFile(File):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)


@FileFactory.register(extension=['.c', '.h', '.s'])
class CFile(File):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)


class SystemCFile(File):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)


@FileFactory.register(extension='.py')
class CocotbPythonFile(SimulationFile):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)


@FileFactory.register(extension='.qsf')
class QuartusQsfFile(ImplementationFile):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)


@FileFactory.register(extension='.qip')
class QuartusQipFile(ImplementationFile):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)


@FileFactory.register(extension='.qsys')
class QuartusQsysFile(IPSpecificationFile):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)


@FileFactory.register(extension='.ip')
class QuartusIpFile(IPSpecificationFile):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)


@FileFactory.register(extension='.ipx')
class QuartusIpxFile(IPSpecificationFile):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)

@FileFactory.register(extension='.source.tcl')
class QuartusTCLSourceFile(ImplementationFile):
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)


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
    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)
