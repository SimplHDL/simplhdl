from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from xml.etree.ElementTree import Element, parse
from zipfile import ZipFile

from simplhdl import Fileset
from simplhdl.plugin import FlowBase, FlowCategory, GeneratorBase
from simplhdl.project.attributes import Library
from simplhdl.project.files import (
    CHeaderFile,
    VivadoXcixFile,
    SdcFile,
    File,
    SystemCFile,
    SystemVerilogFile,
    TclFile,
    VerilogIncludeFile,
    VerilogFile,
    VhdlFile,
    VivadoXciFile,
    UnknownFile,
    UsedIn,
)
from simplhdl.utils import md5check, md5write

logger = logging.getLogger(__name__)

DEFAULT_LIB = 'xil_defaultlib'

FILETYPE_2014_MAP = {
    'systemVerilogSource': SystemVerilogFile,
    'systemVerilogSourceInclude': VerilogIncludeFile,
    '.sv': SystemVerilogFile,
    '.svh': VerilogIncludeFile,
    'verilogSource': VerilogFile,
    'verilogSourceInclude': VerilogIncludeFile,
    '.v': VerilogFile,
    '.vh': VerilogIncludeFile,
    'vhdlSource': VhdlFile,
    '.vhd': VhdlFile,
    '.vhdl': VhdlFile,
    'tclSource': TclFile,
    '.tcl': TclFile,
    'SDC': SdcFile,
    '.sdc': SdcFile,
    'systemCSource': SystemCFile,
    'systemCSourceInclude': CHeaderFile,
    'unknown': UnknownFile,
}


class Component:

    def __init__(self):
        pass

    def load(self, filename: Path) -> None:
        self.filename = str(filename)
        self.tree = parse(filename)
        self.root = self.tree.getroot()
        self.namespaces = {'ipxact': self.root.tag.split('}')[0].strip('{')}
        self.location = filename.parent.absolute()

    def views(self, pattern: str = r'.*') -> list[Element]:
        views = list()
        for view in self.root.findall("ipxact:model/ipxact:views/ipxact:view", self.namespaces):
            name = view.find('ipxact:name', self.namespaces).text
            if re.match(pattern, name):
                views.append(view)
        return views

    def filesets(self, view: Element) -> list[Element]:
        fileset_refs = view.findall("ipxact:fileSetRef", self.namespaces)
        allfilesets = self.root.findall("ipxact:fileSets/ipxact:fileSet", self.namespaces)
        fileset_names = list()
        filesets = list()

        for ref in fileset_refs:
            fileset_names.append(ref.find('ipxact:localName', self.namespaces).text)

        for fileset in allfilesets:
            name = fileset.find('ipxact:name', self.namespaces).text
            if name in fileset_names:
                filesets.append(fileset)
        return filesets

    def files(self, fileset: Element) -> list[Element]:
        files = list()
        file_elements = fileset.findall('ipxact:file', self.namespaces)
        for file_element in file_elements:
            files.append(self.element_to_file(file_element))
        return file_elements

    def pyedaa_files(self, fileset: Element) -> list[Element]:
        files = list()
        file_elements = fileset.findall('ipxact:file', self.namespaces)
        for file_element in file_elements:
            files.append(self.element_to_file(file_element))
        return files

    def filepath(self, file: Element) -> Path:
        return self.location.joinpath(file.find('ipxact:name', self.namespaces).text)

    def element_to_fileset(self, element: Element) -> Fileset:
        if not element.tag.endswith('fileSet'):
            raise Exception(f"Wrong tag {element.tag}")
        name = f"{self.filename}.{element.find('ipxact:name', self.namespaces).text}"
        fileset = Fileset(name)
        for file in self.files(element):
            fileset.add_file(self.element_to_file(file))
        return fileset

    def element_to_file(self, element: Element) -> File:  # noqa C901
        if not element.tag.endswith('file'):
            raise Exception(f"Wrong tag {element.tag}")
        filepath = element.find('ipxact:name', self.namespaces).text
        if filepath.startswith('/'):
            path = Path(filepath)
        else:
            path = Path(self.location, filepath)
        if not path.exists():
            raise FileNotFoundError(f"{path}: file not found")
        try:
            filetype = element.find('ipxact:fileType', self.namespaces).text
        except AttributeError:
            filetype = "unknown"
        try:
            logicalname = element.find('ipxact:logicalName', self.namespaces).text
        except AttributeError:
            logicalname = DEFAULT_LIB
        try:
            isinclude = ''
            if element.find('ipxact:isIncludeFile', self.namespaces).text == "true":
                isinclude = "Include"
        except AttributeError:
            pass
        filetype += isinclude

        if filetype in FILETYPE_2014_MAP:
            fileclass = FILETYPE_2014_MAP.get(filetype)
        elif path.suffix in FILETYPE_2014_MAP:
            fileclass = FILETYPE_2014_MAP.get(path.suffix)
        else:
            raise Exception(f"{filetype}: Unknown file type")

        if issubclass(fileclass, (VerilogFile, SystemVerilogFile, VhdlFile)):
            library = Library(logicalname)
            if path.suffix.endswith('vh') and fileclass in [VerilogFile, SystemVerilogFile]:
                logger.info(f"Changing {path} to VerilogIncludeFile")
                fileclass = VerilogIncludeFile
                return fileclass(path)
            elif path.suffix.endswith('.sv') and fileclass in [VerilogFile]:
                logger.info(f"Changing {path} to SystemVerilogSourceFile")
                fileclass = SystemVerilogFile
            return fileclass(path, library=library)
        else:
            return fileclass(path)


class VivadoGenerator(GeneratorBase):

    def unpack_ip(self, filename: VivadoXciFile | VivadoXcixFile) -> Path:
        ipdir = self.builddir.joinpath('ips')
        dest = ipdir.joinpath(filename.path.stem)
        md5file = dest.with_suffix('.md5')
        ipdir.mkdir(exist_ok=True)
        if filename.path.suffix == '.xcix':
            update = True
            if md5file.exists():
                update = not md5check(filename.path, filename=md5file)
            if update:
                with ZipFile(filename.path, 'r') as zip:
                    zip.extractall(ipdir)
                md5write(filename.path, filename=md5file)
                logger.debug(f"Unpack {filename.path} to {dest}")
        elif filename.path.suffix == '.xci':
            return filename.path.with_suffix('.xml')
        else:
            # Unknown IP file
            return filename
        filename._path = dest.joinpath(filename.path.name).with_suffix('.xml').resolve()
        return filename

    def get_files(self, filename: Path) -> dict[str, str]:
        component = Component()
        component.load(filename)
        files = list()
        for view in component.views('.*elaboratesubcores.*'):
            filesets = component.filesets(view)
            corefiles = list()
            for fileset in filesets:
                corefiles += component.files(fileset)
            for file_element in corefiles:
                # Get the .xml file next to the .xci file
                file = component.filepath(file_element).with_suffix('.xml')
                if file.exists():
                    files += self.get_files(file)
        for view in component.views('.*(verilog|vhdl)simulation.*'):
            filesets = component.filesets(view)
            for fileset in filesets:
                files += component.pyedaa_files(fileset)
        return files

    def run(self, flow: FlowBase):
        if flow.category == FlowCategory.SIMULATION:
            os.makedirs(self.builddir, exist_ok=True)
            ipfiles = list(self.project.defaultDesign.files(type=(VivadoXciFile, VivadoXcixFile)))
            ipfiles = [f for f in ipfiles if UsedIn.SIMULATION in f.usedin]

            for ipfile in ipfiles:
                newipfile = self.unpack_ip(ipfile)
                files = self.get_files(newipfile.path)
                last_lib = ''
                i = 0
                filesets = list()
                for file in files:
                    if isinstance(file, (VerilogFile, VerilogIncludeFile, SystemVerilogFile, VhdlFile)):
                        if last_lib != file.library.name:
                            library = Library(file.library.name)
                            fileset = Fileset(f"{ipfile.path}.{i}", library=library)
                            i += 1
                            filesets.append(fileset)
                        last_lib = file.library.name
                    try:
                        fileset.add_file(file)
                    except Exception:
                        logger.warning(f"Failed to add {file.path}")
                for fileset in filesets:
                    ipfile.parent.add_fileset(fileset)
