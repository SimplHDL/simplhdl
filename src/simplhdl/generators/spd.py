import os
import logging

from typing import List
from pathlib import Path
from xml.etree.ElementTree import Element, parse
from zipfile import ZipFile
from shutil import copy, copytree

from ..pyedaa import (
    File, SystemVerilogSourceFile, VHDLSourceFile, VerilogSourceFile,
    IPSpecificationFile, HDLLibrary
)
from ..pyedaa.fileset import FileSet
from ..flow import FlowCategory
from ..generator import GeneratorFactory, GeneratorBase
from ..utils import md5write, md5check

logger = logging.getLogger(__name__)


FILETYPE_MAP = {
    'SYSTEM_VERILOG': SystemVerilogSourceFile,
    'VERILOG': VerilogSourceFile,
    'VHDL': VHDLSourceFile,
}


class Spd:

    def __init__(self, filename: Path) -> None:
        self._files = list()
        self._filename = filename.absolute()
        self.libraries = dict()
        spdfile = filename.parent.joinpath(filename.stem, filename.name).with_suffix('.spd')
        if not spdfile.exists():
            raise FileNotFoundError(f"{spdfile}: doesn't exits")
        self.tree = parse(spdfile)
        self.root = self.tree.getroot()
        self.location = spdfile.parent.absolute()
        for element in self.file_elements():
            self._files.append(self.element_to_file(element))

    def file_elements(self) -> List[Element]:
        return [f for f in self.root if f.tag == 'file']

    def element_to_file(self, element: Element) -> File:
        properties = element.attrib
        if properties['path'].startswith('/'):
            path = Path(properties['path'])
        else:
            path = Path(self.location, properties['path'])
        libraryname = properties['library']
        if libraryname not in self.libraries:
            self.libraries[libraryname] = HDLLibrary(libraryname)
        fileclass = FILETYPE_MAP.get(properties['type'])
        # print(properties['type'])
        return fileclass(path=path, library=self.libraries[libraryname])

    @property
    def filesets(self):
        filesets = list()
        for library in self.libraries.values():
            name = f"{self._filename}.{library.Name}"
            fileset = FileSet(name, vhdlLibrary=library)
            for file in self._files:
                if file.Library == library:
                    fileset.AddFile(file)
            filesets.append(fileset)
        return filesets


@GeneratorFactory.register('QuartusIP')
class QuartusIP(GeneratorBase):

    def unpack_ip(self, filename: IPSpecificationFile) -> IPSpecificationFile:
        ipdir = self.builddir.joinpath('ips')
        dest = ipdir.joinpath(filename.Path.name).with_suffix('.ip')
        md5file = dest.with_suffix('.md5')
        ipdir.mkdir(exist_ok=True)
        if filename.Path.suffix == '.qsys':
            return
        elif filename.Path.suffix == '.ipx':
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
                copy(str(filename.Path), str(dest))
                md5write(filename.Path, filename=md5file)
                if dir.exists():
                    copytree(str(dir), str(dest.with_suffix('')), dirs_exist_ok=True)
                    md5write(filename.Path, dir, filename=md5file)
                    logger.debug(f"Copy {filename.Path} to {dest}")
        filename._path = dest.absolute()
        return filename

    def run(self, flowcategory: FlowCategory):
        os.makedirs(self.builddir, exist_ok=True)
        for ipfile in self.project.DefaultDesign.DefaultFileSet.Files(fileType=IPSpecificationFile):
            newipfile = self.unpack_ip(ipfile)
            if flowcategory == FlowCategory.SIMULATION:
                spd = Spd(newipfile.Path)
                for fileset in spd.filesets:
                    newipfile.FileSet._fileSets[fileset.Name] = fileset
