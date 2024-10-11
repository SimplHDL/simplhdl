import logging
import re
import os

from pathlib import Path
from typing import Optional, Dict

from .utils import sh
from .pyedaa.project import Project
from .pyedaa import VerilogIncludeFile, VerilogSourceFile, SystemVerilogSourceFile, VHDLSourceFile, CocotbPythonFile
from .flow import FlowError

logger = logging.getLogger(__name__)


class Cocotb:

    def __init__(self, project: Project) -> None:
        self.project = project
        self.top = self.module()
        self.dut = self.get_dut()
        self.toplevels = self.hdltoplevels()
        self.duttype = self.hdltype()

    def lib_name_path(self, simulator: str, interface: str) -> Path:
        output = sh(['cocotb-config', '--lib-name-path', interface, simulator])
        path = Path(output)
        if not path.exists():
            raise FileNotFoundError(f"{path}: not found")
        return path

    def libpython(self) -> str:
        output = sh(['cocotb-config', '--libpython'])
        path = Path(output)
        if not path.exists():
            raise FileNotFoundError(f"{path}: not found")
        return path

    def module(self) -> Optional[str]:
        if not self.enabled:
            return None
        set_ = set()
        try:
            modules = self.project.DefaultDesign._topLevel.split()
        except AttributeError:
            raise FlowError("No top levels found")

        for module in modules:
            if self.is_python_module(module):
                # TODO: What if more than one module match?
                set_.add(module)
        if not set_:
            raise FlowError('CocoTB module not specified')
        elif len(set_) == 1:
            return next(iter(set_))
        else:
            raise NotImplementedError(f"More than one CocoTB module found: {set_}")

    def hdltoplevels(self) -> str:
        tops = []
        for t in self.project.DefaultDesign._topLevel.split():
            if t != self.top:
                tops.append(t)
        return ' '.join(tops)

    def get_dut(self) -> str:
        for top in self.project.DefaultDesign._topLevel.split():
            if top != self.top:
                return top

    def hdltype(self):  # noqa: C901
        logger.debug(f"Cocotb hdl dut '{self.dut}'")
        lib = next(iter(self.project.DefaultDesign.VHDLLibraries))
        if '.' in self.dut:
            lib, name = self.dut.split('.')
        else:
            name = self.dut

        files = list(self.project.DefaultDesign.Files())
        try:
            for file in reversed(files):
                if file.FileType in [VHDLSourceFile]:
                    with open(file.Path, 'r', errors='replace') as f:
                        lines = f.readlines()
                        for line in lines:
                            if re.search(rf'^\s*entity\s+{name}\s+is', line, re.IGNORECASE):
                                if file.Library.Name == lib:
                                    logger.info(f"Cocotb dut '{self.dut}' is VHDL")
                                    return VHDLSourceFile
                                else:
                                    logger.warning(f"Found HDL entity {name} in ",
                                                   f"library '{file.Library.Name}' expected '{lib}'")
                if file.FileType in [VerilogIncludeFile, VerilogSourceFile, SystemVerilogSourceFile]:
                    with open(file.Path, 'r', errors='replace') as f:
                        lines = f.readlines()
                        for line in lines:
                            if re.search(rf'^\s*module\s+{name}(\s+|\(|;|$)', line):
                                if file.Library.Name == lib:
                                    logger.info(f"Cocotb dut '{self.dut}' is Verilog")
                                    return VerilogSourceFile
                                else:
                                    logger.warning(f"Found HDL module {name} in ",
                                                   f"library '{file.Library.Name}' expected '{lib}'")
                else:
                    continue
        except UnicodeDecodeError:
            logger.warning(f"Can't decode {file.Path}")
        raise FlowError(f"Could not find HDL entity/module '{name}' in library '{lib}'")

    def is_python_module(self, name: str):
        # TODO: Should we also search in installed packages?
        if [f for f in self.files() if f.Path.stem == name]:
            return True

    def files(self):
        return self.project.DefaultDesign.Files(CocotbPythonFile)

    @property
    def enabled(self) -> bool:
        for file in self.files():
            return True
        return False

    @property
    def pythonpath(self) -> str:
        directories = {str(f.Path.parent.absolute()) for f in self.files()}
        return ':'.join(directories)

    def args(self) -> str:
        if self.duttype == VHDLSourceFile:
            lib_name_path = self.lib_name_path("questa", "fli")
            return f'-foreign "cocotb_init {lib_name_path}"'
        elif self.duttype == VerilogSourceFile:
            lib_name_path = self.lib_name_path("questa", "vpi")
            return f'-pli {lib_name_path}'

    def env(self) -> Dict[str, str]:
        e = os.environ.copy()
        e['MODULE'] = self.top
        e['TOPLEVEL'] = self.dut
        e['PYTHONPYCACHEPREFIX'] = './pycache'
        e['LIBPYTHON_LOC'] = self.libpython()
        if self.duttype == VHDLSourceFile:
            lib_name_path = self.lib_name_path("questa", "vpi")
            e['GPI_EXTRA'] = f"{lib_name_path}:cocotbvpi_entry_point"
        elif self.duttype == VerilogSourceFile:
            lib_name_path = self.lib_name_path("questa", "fli")
            e['GPI_EXTRA'] = f"{lib_name_path}:cocotbfli_entry_point"
        if 'PYTHONPATH' in e:
            e['PYTHONPATH'] = self.pythonpath + os.pathsep + e.get('PYTHONPATH')
        else:
            e['PYTHONPATH'] = self.pythonpath
        return e
