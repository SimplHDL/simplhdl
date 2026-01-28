from __future__ import annotations

from enum import Enum
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Type, Iterable, Generator
from weakref import WeakValueDictionary

if TYPE_CHECKING:
    import networkx as nx

    from .attributes import Library
    from .fileset import Fileset

logger = logging.getLogger(__name__)


class UsedIn(str, Enum):
    SIMULATION = "simulation"
    IMPLEMENTATION = "implementation"


class ConstraintOrder(float, Enum):
    EARLY = 25.0
    NORMAL = 50.0
    LATE = 75.0


class File:
    _cache = WeakValueDictionary()
    _default_usedin: list[str] = [UsedIn.SIMULATION, UsedIn.IMPLEMENTATION]
    _default_encrypt: bool = False
    _path_relative_to: Path | None = None

    def __new__(cls, file: Path | str, **attributes) -> File:
        file = Path(file) if isinstance(file, str) else file
        if file.resolve() in cls._cache:
            return cls._cache[file.resolve()]

        instance = super().__new__(cls)
        cls._cache[file.resolve()] = instance
        return instance

    def __init__(self, file: Path | str, **attributes) -> None:
        if hasattr(self, "_initialized"):
            logger.debug(f"File {self._path} already initialized")
            return

        self._path: Path = Path(file) if isinstance(file, str) else file
        self._graph: nx.DiGraph[File] | None = None
        self._parent: Fileset | None = None
        self._usedin: list[str] = attributes.get("usedin", self._default_usedin)
        self._encrypt: bool = attributes.get("encrypt", self._default_encrypt)
        self._initialized = True

    @classmethod
    def set_path_relative_to(cls, path: Path | None) -> None:
        if path is not None:
            path = path.resolve()
        cls._path_relative_to = path

    @property
    def path(self) -> Path:
        try:
            if self._path_relative_to is not None:
                return self._path.resolve().relative_to(self._path_relative_to.resolve())
        except ValueError:
            pass
        return self._path.resolve()

    @property
    def parent(self) -> Fileset:
        return self._parent

    @parent.setter
    def parent(self, parent: Fileset) -> None:
        self._parent = parent

    @property
    def usedin(self) -> list[str]:
        return self._usedin

    @usedin.setter
    def usedin(self, usedin: list[str]) -> None:
        if isinstance(usedin, list):
            self._usedin = usedin
        else:
            self._usedin = [usedin]

    @property
    def encrypt(self) -> bool:
        return self._encrypt

    @encrypt.setter
    def encrypt(self, encrypt: bool) -> None:
        self._encrypt = encrypt

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        if self._parent is None:
            parent_name = None
        else:
            parent_name = self._parent.name
        return f"{self.__class__.__name__}(path={self._path}, parent={parent_name})"


FileClass = Type[File]


def filter_files(
    files: Iterable[File],
    file_type: Type[File] | tuple[Type[File], ...] | None = None,
    **filters,
) -> Generator[File, None, None]:
    """
    Filters a sequence of files based on type and arbitrary attributes.

    Args:
        files: An iterable of `File` objects to filter.
        file_type: A file class or a tuple of file classes to filter by.
        **filters: Arbitrary keyword arguments to filter on file attributes.
                   For most attributes, an exact match is performed.
                   For the 'usedin' attribute, a membership check is performed
                   (i.e., it checks if the value is `in` the file's `usedin` list).

    Yields:
        A generator of `File` objects that match the filter criteria.
    """
    for file in files:
        # Check file type
        if file_type is not None and not isinstance(file, file_type):
            continue

        # Check other attributes from filters
        all_filters_match = True
        for key, value in filters.items():
            if not hasattr(file, key):
                all_filters_match = False
                break
            if key == "usedin":  # Special case for membership check
                if value not in getattr(file, key):
                    all_filters_match = False
                    break
            elif getattr(file, key) != value:
                all_filters_match = False
                break

        if all_filters_match:
            yield file


class FileFactory:
    _registered_types: dict[str, type[File]] = {}
    _registered_extensions: dict[str, type[File]] = {}

    @classmethod
    def register(cls, extension: str | list[str] = list()) -> Callable[[FileClass], FileClass]:
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
    def create(cls, file: Path, type: str | None = None, **attributes) -> File:
        filename_lower = file.name.lower()
        if type is None:
            type = ""
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
class UnknownFile(File): ...


class HdlFile(File):
    """Represents a Hardware Description Language (HDL) source file.

    This class serves as a base for specific HDL file types like Verilog or VHDL.
    It manages common attributes applicable to HDL source files.
    """

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
        self._library: Library = attributes.get("library", None)

    @property
    def library(self) -> Library:
        if not self._library:
            return self.parent.library
        return self._library


@FileFactory.register(extension=".sv")
class SystemVerilogFile(HdlFile): ...


@FileFactory.register(extension=".svp")
class SystemVerilogEncryptedFile(HdlFile): ...


@FileFactory.register(extension=".v")
class VerilogFile(HdlFile): ...


@FileFactory.register(extension=".vp")
class VerilogEncryptedFile(HdlFile): ...


@FileFactory.register(extension=[".vh", ".svh"])
class VerilogIncludeFile(HdlFile):
    @property
    def includeDir(self) -> Path:
        return self.path.parent


@FileFactory.register(extension=[".vhp", ".svhp"])
class VerilogIncludeEncryptedFile(HdlFile): ...


@FileFactory.register(extension=[".vhd", ".vhdl"])
class VhdlFile(HdlFile): ...


class ImplementationFile(File):
    _default_usedin = [UsedIn.IMPLEMENTATION]


class ConstraintFile(ImplementationFile):
    _default_scope: str | None = None
    _default_order: ConstraintOrder = ConstraintOrder.NORMAL

    def __init__(self, file: Path, **attributes) -> None:
        super().__init__(file, **attributes)
        self._scope: str | None = attributes.get("scope", self._default_scope)
        self._order: float = attributes.get("order", self._default_order)

    @property
    def scope(self) -> str | None:
        return self._scope

    @scope.setter
    def scope(self, scope: str | None) -> None:
        self._scope = scope

    @property
    def order(self) -> float:
        return self._order


class SimulationFile(File):
    _default_usedin = [UsedIn.SIMULATION]


class IPSpecificationFile(File): ...


@FileFactory.register(extension=".sdc")
class SdcFile(ConstraintFile): ...


@FileFactory.register(extension=[".edn", ".edif"])
class EdifFile(ImplementationFile): ...


@FileFactory.register(extension=[".c", ".s"])
class CFile(File): ...


@FileFactory.register(extension=".h")
class CHeaderFile(File): ...


class SystemCFile(File): ...


@FileFactory.register(extension=".cpp")
class CppFile(File): ...


@FileFactory.register(extension=".py")
class CocotbPythonFile(SimulationFile): ...


@FileFactory.register(extension=".qsf")
class QuartusQsfFile(ImplementationFile): ...


@FileFactory.register(extension=".qip")
class QuartusQipFile(ImplementationFile): ...


@FileFactory.register(extension=".qsys")
class QuartusQsysFile(IPSpecificationFile): ...


@FileFactory.register(extension=".qsys.zip")
class QuartusQsysZipFile(IPSpecificationFile): ...


@FileFactory.register(extension=".ip")
class QuartusIpFile(IPSpecificationFile): ...


@FileFactory.register(extension=".ip.zip")
class QuartusIpZipFile(IPSpecificationFile): ...


@FileFactory.register(extension=".ipx")
class QuartusIpxFile(IPSpecificationFile): ...


@FileFactory.register(extension=".source.tcl")
class QuartusSourceTclFile(ImplementationFile): ...


@FileFactory.register(extension="quartus.ini")
class QuartusIniFile(ImplementationFile): ...


@FileFactory.register(extension=".stp")
class QuartusStpFile(ImplementationFile): ...


@FileFactory.register(extension=".xdc")
class VivadoXdcFile(ConstraintFile): ...


@FileFactory.register(extension=".dcp")
class VivadoDcpFile(ImplementationFile): ...


@FileFactory.register(extension=".xci")
class VivadoXciFile(IPSpecificationFile): ...


@FileFactory.register(extension=".xcix")
class VivadoXcixFile(IPSpecificationFile): ...


@FileFactory.register(extension=".bd")
class VivadoBdFile(IPSpecificationFile): ...


@FileFactory.register(extension=".bd.tcl")
class VivadoBdTclFile(IPSpecificationFile): ...


@FileFactory.register(extension=".steps.tcl")
class VivadoStepFile(ImplementationFile): ...


@FileFactory.register(extension=".sbt")
class ChiselBuildFile(File): ...


class HdlSearchPath(VerilogIncludeFile):
    @property
    def includeDir(self) -> Path:
        return self.path


@FileFactory.register(extension=".hex")
class MemoryHexFile(File): ...


@FileFactory.register(extension=".mif")
class MemoryInitFile(File): ...


@FileFactory.register(extension="modelsim.ini")
class ModelsimIniFile(SimulationFile): ...


@FileFactory.register(extension=".rdl")
class SystemRdlFile(File): ...


@FileFactory.register(extension=".tcl")
class TclFile(File): ...
