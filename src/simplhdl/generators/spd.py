import os
import re
import logging

from typing import List, Generator
from pathlib import Path
from xml.etree.ElementTree import Element, parse
from zipfile import ZipFile
from shutil import copy, copytree

from ..pyedaa import (
    File, SystemVerilogSourceFile, VHDLSourceFile, VerilogSourceFile,
    QuartusIPSpecificationFile, HDLLibrary, ConstraintFile, HDLSourceFile
)
from ..pyedaa.fileset import FileSet
from ..flow import FlowBase, FlowCategory, FlowTools
from ..generator import GeneratorFactory, GeneratorBase, GeneratorError
from ..utils import md5write, md5check

logger = logging.getLogger(__name__)


FILETYPE_MAP = {
    'SYSTEM_VERILOG': SystemVerilogSourceFile,
    'SYSTEM_VERILOG_ENCRYPT': SystemVerilogSourceFile,
    'VERILOG': VerilogSourceFile,
    'VERILOG_ENCRYPT': VerilogSourceFile,
    'VHDL': VHDLSourceFile,
    'VHDL_ENCRYPT': VHDLSourceFile,
    'SDC_ENTITY': ConstraintFile,
}

TOOL_MAP = {
    FlowTools.VCS: 'vcs',
    FlowTools.NCSIM: 'ncsim',
    FlowTools.QUESTASIM: 'modelsim',
    FlowTools.MODELSIM: 'modelsim',
    FlowTools.VCS: 'vcs',
    FlowTools.RIVIERAPRO: 'riviera'
}


class Spd:

    def __init__(self, filename: Path, flow: FlowBase) -> None:
        self._files = list()
        self._filename = filename.absolute()
        self.flow = flow
        self.libraries = dict()
        self.simulators = set()
        spdfile = filename.parent.joinpath(filename.stem, filename.name).with_suffix('.spd')
        if not spdfile.exists():
            raise FileNotFoundError(f"{spdfile}: doesn't exits")
        self.tree = parse(spdfile)
        self.root = self.tree.getroot()
        self.location = spdfile.parent.absolute()
        for element in self.file_elements():
            self._files.append(self.element_to_file(element))
        if self.simulators and not self.supported(self.flow, self.simulators):
            names = [n.name.capitalize() for n in self.flow.tools]
            raise GeneratorError(f"Encrypted IP {filename} does not support {','.join(names)}")

    def file_elements(self) -> Generator[Element, None, None]:
        for f in self.root:
            if f.tag == 'file':
                properties = f.attrib
                if 'simulator' in properties:
                    simulators = re.split(r'\s*,\s*', properties['simulator'])
                    if not self.supported(self.flow, simulators):
                        continue
                yield f

    def element_to_file(self, element: Element) -> File:
        properties = element.attrib
        if properties['path'].startswith('/'):
            path = Path(properties['path'])
        else:
            path = Path(self.location, properties['path'])
        libraryname = properties['library']
        if libraryname not in self.libraries:
            self.libraries[libraryname] = HDLLibrary(libraryname)
        fileclass = FILETYPE_MAP.get(properties['type'], File)
        if issubclass(fileclass, HDLSourceFile):
            return fileclass(path=path, library=self.libraries[libraryname])
        else:
            return fileclass(path=path)

    def supported(self, flow: FlowBase, simulators: List) -> bool:
        self.simulators.update(simulators)
        for tool in flow.tools:
            if TOOL_MAP.get(tool, None) in simulators:
                return True
        return False

    @property
    def filesets(self):
        filesets = list()
        for library in self.libraries.values():
            name = f"{self._filename}.{library.Name}"
            fileset = FileSet(name, vhdlLibrary=library)
            for file in self._files:
                if isinstance(file, HDLSourceFile):
                    if file.Library == library:
                        fileset.AddFile(file)
                else:
                    fileset.AddFile(file)
            filesets.append(fileset)
        return filesets


@GeneratorFactory.register('QuartusIP')
class QuartusIP(GeneratorBase):

    def unpack_ip(self, filename: QuartusIPSpecificationFile) -> QuartusIPSpecificationFile:
        ipdir = self.builddir.joinpath('ips')
        dest = ipdir.joinpath(filename.Path.name).with_suffix('')
        md5file = dest.with_suffix('.md5')
        ipdir.mkdir(exist_ok=True)
        if filename.Path.suffix == '.qsys':
            return
        elif filename.Path.suffix == '.zip':
            update = True
            if md5file.exists():
                update = not md5check(filename.Path, filename=md5file)
            if update:
                with ZipFile(filename.Path, 'r') as zip:
                    zip.extractall(ipdir)
                md5write(filename.Path, filename=md5file)
                logger.debug(f"Copy {filename.Path} to {dest}")
        elif filename.Path.suffix == '.ip':
            update = True
            dir = filename.Path.with_suffix('')
            if dir.exists():
                if md5file.exists():
                    update = not md5check(filename.Path, dir, filename=md5file)
            if update:
                copy(str(filename.Path), str(dest.with_suffix('.ip')))
                md5write(filename.Path, filename=md5file)
                if dir.exists():
                    copytree(str(dir), str(dest.with_suffix('')), dirs_exist_ok=True)
                    md5write(filename.Path, dir, filename=md5file)
                    logger.debug(f"Copy {filename.Path} to {dest}")
        else:
            # Non Qartus IP files
            return filename
        filename._path = dest.absolute()
        return filename

    def run(self, flow: FlowBase):
        os.makedirs(self.builddir, exist_ok=True)
        for ipfile in self.project.DefaultDesign.DefaultFileSet.Files(fileType=QuartusIPSpecificationFile):
            newipfile = self.unpack_ip(ipfile)
            if flow.category == FlowCategory.SIMULATION:
                spd = Spd(newipfile.Path, flow)
                parent = newipfile.FileSet
                for fileset in reversed(spd.filesets):
                    # Add fileset to parent, then set parent to fileset to make a chain
                    parent._fileSets[fileset.Name] = fileset
                    parent = fileset
