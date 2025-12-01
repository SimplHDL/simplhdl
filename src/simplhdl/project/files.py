from __future__ import annotations

from pathlib import Path

from .attributes import Library


simulation = "simulation"
implementation = "implementation"


class FileFactory:

    _registered_types: dict[str, type[File]] = {}

    @classmethod
    def register(cls, file_type: str, file_class: type[File]) -> None:
        """Class method to register a new file type."""
        if not issubclass(file_class, File):
            raise ValueError(f"Class '{file_class}' is not a subclass of File.")
        if file_type in cls._registered_types:
            raise ValueError(f"File type '{file_type}' is already registered.")
        cls._registered_types[file_type.lower()] = file_class

    @classmethod
    def create(cls, file: Path, **attributes) -> File:
        return File(file)


class File:
    def __init__(self, file: Path, **attributes) -> None:
        self._path = file.absolute().resolve()
        self._graph = None


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


class SystemVerilogFile(HdlFile):
    ...

class VerilogFile(HdlFile):
    ...

class VerilogIncludeFile(HdlFile):
    ...


class VhdlFile(HdlFile):
    ...


FileFactory.register('.sv', SystemVerilogFile)
FileFactory.register('.v', VerilogFile)
FileFactory.register('.svh', VerilogIncludeFile)
FileFactory.register('.vh', VerilogIncludeFile)
FileFactory.register('.vhd', VhdlFile)
FileFactory.register('.vhdl', VhdlFile)
