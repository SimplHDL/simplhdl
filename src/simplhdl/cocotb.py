from __future__ import annotations

import logging
import os
import re
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.version import Version

from .plugin.flow import FlowError
from .project.files import (
    CocotbPythonFile,
    SystemVerilogFile,
    UsedIn,
    VerilogFile,
    VerilogIncludeFile,
    VhdlFile,
)
from .utils import sh

if TYPE_CHECKING:
    from .project.project import Project


logger = logging.getLogger(__name__)


def get_lib_name_path(interface: str, simulator: str) -> Path:
    output = sh(["cocotb-config", "--lib-name-path", interface, simulator]).strip()
    path = Path(output)
    if not path.exists():
        raise FileNotFoundError(f"{path}: not found")
    return path


def get_lib_entry(interface: str, simulator: str) -> str:
    output = sh(["cocotb-config", "--lib-entry", interface, simulator]).strip()
    return output


def get_libpython() -> str:
    output = sh(["cocotb-config", "--libpython"]).strip()
    path = Path(output)
    if not path.exists():
        raise FileNotFoundError(f"{path}: not found")
    return path


def get_pygpi_entry_point() -> str:
    if Version(version("cocotb")) >= Version("2.1.0"):
        output = sh(["cocotb-config", "--pygpi-entry-point"]).strip()
        return output
    return ""


def get_pythonbin() -> str:
    output = sh(["cocotb-config", "--python-bin"]).strip()
    path = Path(output)
    if not path.exists():
        raise FileNotFoundError(f"{path}: not found")
    return path


def get_gpi_users() -> str:
    return f"{get_libpython()};{get_pygpi_entry_point()}"


def get_gpi_extra(interface: str, simulator: str) -> str:
    return f"{get_lib_name_path(interface, simulator)}:cocotb{interface}_entry_point"


class Cocotb:
    def __init__(self, project: Project, seed: int) -> None:
        self.project = project
        self.seed = seed
        self.top = self.module()
        self.dut = self.get_dut()
        self.toplevels = self.hdltoplevels()
        self.duttype = self.hdltype()
        self.has_verilog = (
            project.defaultDesign.files(type=(VerilogFile, SystemVerilogFile), usedin=UsedIn.SIMULATION) != []
        )
        self.has_vhdl = project.defaultDesign.files(type=VhdlFile, usedin=UsedIn.SIMULATION) != []

    def lib_name_path(self, simulator: str, interface: str) -> Path:
        return get_lib_name_path(interface, simulator)

    def libpython(self) -> str:
        return get_libpython()

    def pygpi_entry_point(self) -> str:
        return get_pygpi_entry_point()

    def pythonbin(self) -> str:
        return get_pythonbin()

    def module(self) -> str | None:
        if not self.enabled:
            return None
        set_ = set()
        try:
            modules = self.project.defaultDesign.toplevels
        except AttributeError:
            raise FlowError("No top levels found")

        for module in modules:
            if self.is_python_module(module):
                # TODO: What if more than one module match?
                set_.add(module)
        if not set_:
            raise FlowError("CocoTB module not specified")
        elif len(set_) == 1:
            return next(iter(set_))
        else:
            raise NotImplementedError(f"More than one CocoTB module found: {set_}")

    def hdltoplevels(self) -> str:
        tops = []
        for t in self.project.defaultDesign.toplevels:
            if t != self.top:
                tops.append(t)
        return tops

    def get_dut(self) -> str:
        try:
            for top in self.project.defaultDesign.toplevels:
                if top != self.top:
                    return top
        except AttributeError:
            raise FlowError("No top levels found")

    def hdltype(self):  # noqa: C901
        logger.debug(f"Cocotb hdl dut '{self.dut}'")
        libname = next(iter(self.project.defaultDesign.libraries)).name
        if "." in self.dut:
            libname, name = self.dut.split(".")
        else:
            name = self.dut
        files = list(self.project.defaultDesign.files())
        try:
            for file in reversed(files):
                if isinstance(file, VhdlFile):
                    with open(file.path, "r", errors="replace") as f:
                        lines = f.readlines()
                        for line in lines:
                            if re.search(rf"^\s*entity\s+{name}\s+is", line, re.IGNORECASE):
                                if file.library.name == libname:
                                    logger.info(f"Cocotb dut '{self.dut}' is VHDL")
                                    return VhdlFile
                                else:
                                    logger.warning(
                                        f"Found HDL entity {name} in ",
                                        f"library '{file.library.name}' expected '{libname}'",
                                    )
                if isinstance(file, (VerilogIncludeFile, VerilogFile, SystemVerilogFile)):
                    with open(file.path, "r", errors="replace") as f:
                        lines = f.readlines()
                        for line in lines:
                            if re.search(rf"^\s*module\s+{name}(\s+|#\(|\(|;|$)", line):
                                if file.library.name == libname:
                                    logger.info(f"Cocotb dut '{self.dut}' is Verilog")
                                    return VerilogFile
                                else:
                                    logger.warning(
                                        f"Found HDL module {name} in library '{file.library.name}' expected '{libname}'"
                                    )
                else:
                    continue
        except UnicodeDecodeError:
            logger.warning(f"Can't decode {file.path}")
        raise FlowError(f"Could not find HDL entity/module '{name}' in library '{libname}'")

    def is_python_module(self, name: str):
        # TODO: Should we also search in installed packages?
        if [f for f in self.files() if f.path.stem == name]:
            return True

    def files(self):
        return self.project.defaultDesign.files(CocotbPythonFile)

    @property
    def enabled(self) -> bool:
        for file in self.files():
            return True
        return False

    @property
    def pythonpath(self) -> str:
        directories = {str(f.path.parent.absolute()) for f in self.files()}
        return ":".join(directories)

    def args(self) -> str:
        if self.duttype == VhdlFile:
            lib_name_path = self.lib_name_path("questa", "fli")
            return f'-foreign "cocotb_init {lib_name_path}"'
        elif self.duttype == VerilogFile:
            lib_name_path = self.lib_name_path("questa", "vpi")
            return f"-pli {lib_name_path}"

    def env(self) -> dict[str, str]:
        cocotb_version = Version(version("cocotb"))
        e = os.environ.copy()
        if cocotb_version >= Version("2.1.0"):
            e["COCOTB_TEST_MODULES"] = self.top
            e["COCOTB_TOPLEVEL"] = self.dut
            e["PYGPI_PYTHON_BIN"] = get_pythonbin()
            e["COCOTB_RANDOM_SEED"] = str(self.seed)
            e["GPI_USERS"] = get_gpi_users()
        elif cocotb_version >= Version("2.0.0"):
            e["COCOTB_TEST_MODULES"] = self.top
            e["COCOTB_TOPLEVEL"] = self.dut
            e["PYGPI_PYTHON_BIN"] = get_pythonbin()
            e["COCOTB_RANDOM_SEED"] = str(self.seed)
            e["LIBPYTHON_LOC"] = get_libpython()
        else:
            e["MODULE"] = self.top
            e["TOPLEVEL"] = self.dut
            e["LIBPYTHON_LOC"] = get_libpython()
        e["PYTHONPYCACHEPREFIX"] = "./pycache"
        e["GPI_EXTRA"] = ""
        if self.has_verilog and self.has_vhdl:
            if self.duttype == VhdlFile:
                interface = "vpi"
            elif self.duttype == VerilogFile:
                interface = "fli"
            e["GPI_EXTRA"] = get_gpi_extra(interface, "questa")
        if "PYTHONPATH" in e:
            e["PYTHONPATH"] = self.pythonpath + os.pathsep + e.get("PYTHONPATH")
        else:
            e["PYTHONPATH"] = self.pythonpath
        return e
