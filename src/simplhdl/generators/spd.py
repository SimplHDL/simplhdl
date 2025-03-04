import re
import logging

from typing import List, Generator, Optional
from pathlib import Path
from xml.etree.ElementTree import Element, parse
from zipfile import ZipFile
from shutil import copy, copytree, rmtree

from simplhdl.pyedaa import (
    File,
    HDLSourceFile,
    HDLSearchPath,
    VerilogSourceFile,
    SystemVerilogSourceFile,
    VHDLSourceFile,
    ConstraintFile,
    HDLLibrary,
    MemoryInitFile,
    QuartusIPSpecificationFile,
    QuartusIPCompressedSpecificationFile,
    QuartusQSYSSpecificationFile,
    QuartusQSYSCompressedSpecificationFile,
    QuartusQIPSpecificationFile
)
from simplhdl.pyedaa.fileset import FileSet
from simplhdl.pyedaa.attributes import UsedIn
from simplhdl.flow import FlowBase, FlowCategory, FlowTools
from simplhdl.generator import GeneratorFactory, GeneratorBase, GeneratorError
from simplhdl.utils import md5write, md5check, sh

logger = logging.getLogger(__name__)


FILETYPE_MAP = {
    'SYSTEM_VERILOG': SystemVerilogSourceFile,
    'SYSTEM_VERILOG_ENCRYPT': SystemVerilogSourceFile,
    'VERILOG': VerilogSourceFile,
    'VERILOG_ENCRYPT': VerilogSourceFile,
    'VHDL': VHDLSourceFile,
    'VHDL_ENCRYPT': VHDLSourceFile,
    'SDC_ENTITY': ConstraintFile,
    'HEX': MemoryInitFile
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

    def __init__(self, filename: Path, flow: FlowBase, ip_path: Optional[Path] = None) -> None:
        self._files = list()
        self._filename = filename.absolute()
        self.flow = flow
        self.libraries = dict()
        self.simulators = set()
        spdfile = filename.parent.joinpath(filename.stem, filename.name).with_suffix('.spd')
        if not spdfile.exists():
            if ip_path:
                command = f"qsys-generate --simulation=VERILOG --search-path={ip_path},$ {filename.absolute()}".split()
            else:
                command = f"qsys-generate --simulation=VERILOG {filename.absolute()}".split()
            logger.info(f'Generate simulation files for {filename}')
            sh(command, cwd=filename.parent)
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

    def unpack_ip(self, filename: QuartusIPSpecificationFile) -> QuartusIPSpecificationFile:  # noqa: C901
        ipdir = self.builddir.joinpath('ips')
        dest = ipdir.joinpath(filename.Path.name).with_suffix('')
        md5file = dest.with_suffix('.md5')
        ipdir.mkdir(exist_ok=True)
        if filename.FileType == QuartusQSYSSpecificationFile:
            filename = self.copy_qsys(filename, dest, md5file)
            ipfiles = self.parse_qsys(filename)
            if self.flow.category == FlowCategory.SIMULATION:
                for ipfile in ipfiles:
                    spd = Spd(ipfile.Path, self.flow, dest.absolute())
                    parent = filename.FileSet
                    for fileset in reversed(spd.filesets):
                        # Add fileset to parent, then set parent to fileset to make a chain
                        parent._fileSets[fileset.Name] = fileset
                        parent = fileset
            else:
                fileset = FileSet(filename.Path.name, vhdlLibrary=self.project.DefaultDesign.DefaultFileSet.VHDLLibrary)
                fileset.AddFiles(ipfiles)
                filename.FileSet.AddFileSet(fileset)
        elif filename.FileType == QuartusIPCompressedSpecificationFile:
            update = True
            if md5file.exists():
                update = not md5check(filename.Path, filename=md5file)
            if update:
                with ZipFile(filename.Path, 'r') as zip:
                    zip.extractall(ipdir)
                md5write(filename.Path, filename=md5file)
                logger.debug(f"Copy {filename.Path} to {dest}")

            if filename.Path.suffix == '.zip':
                filename._path = dest.absolute()
            else:
                filename._path = dest.with_suffix('.ip').absolute()
            filename._fileType = QuartusIPSpecificationFile

        elif filename.FileType == QuartusIPSpecificationFile:
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
            filename._path = dest.with_suffix('.ip').absolute()
        return filename


    def run(self, flow: FlowBase) -> None:
        self.flow = flow
        ip_dir = self.builddir.joinpath('ips')
        qsys_dir = self.builddir.joinpath('qsys')
        files = list(self.project.DefaultDesign.DefaultFileSet.Files(fileType=QuartusIPSpecificationFile))
        files = filter_duplicated_files(files)
        if not flow.category == FlowCategory.DEFAULT:
            for file in files:
                if file.FileType == QuartusQIPSpecificationFile:
                    continue
                elif file.FileType == QuartusIPCompressedSpecificationFile:
                    file = unpack_ipfile(file, ip_dir)
                elif file.FileType == QuartusIPSpecificationFile:
                    file = copy_ipfile(file, ip_dir)
                elif file.FileType == QuartusQSYSCompressedSpecificationFile:
                    file = unpack_qsysfile(file, qsys_dir)
                elif file.FileType == QuartusQSYSSpecificationFile:
                    file = copy_qsysfile(file, qsys_dir)
                parse_file(file, flow, self.project.DefaultDesign.DefaultFileSet.VHDLLibrary)


def parse_qsys(filename: QuartusQSYSSpecificationFile) -> List[File]:
    """
    Search for IP files in a QSYS file and return a list of QuartusIPSpecificationFile objects.
    """
    files = list()
    with filename.Path.open() as file:
        lines = file.readlines()
        for line in lines:
            m = re.search(r'<ipxact:value>(.*\.ip)</ipxact:value>', line)
            if m:
                ipfile = filename.Path.parent.joinpath(m.group(1))
                if ipfile.exists():
                    files.append(QuartusIPSpecificationFile(ipfile))
                else:
                    logger.warning(f"File {ipfile} not found")
    return files


def qsys_to_fileset(file: QuartusQSYSSpecificationFile, flow: FlowBase, library) -> FileSet:
    """
    Parse a QSYS file and return a FileSet object.
    """
    ipfiles = parse_qsys(file)
    if flow.category == FlowCategory.SIMULATION:
        parent = file.FileSet
        for ipfile in ipfiles + [file]:
            spd = Spd(ipfile.Path, flow, file.Path.parent.absolute())
            for fileset in reversed(spd.filesets):
                # Add fileset to parent, then set parent to fileset to make a chain
                parent._fileSets[fileset.Name] = fileset
                parent = fileset
    elif flow.category == FlowCategory.IMPLEMENTATION:
        # NOTE: Some qsys require a search path to find the HEX files
        searchpath = HDLSearchPath(file.Path.parent)
        searchpath[UsedIn] = {'implementation'}
        fileset = FileSet(file.Path.name, vhdlLibrary=library)
        fileset.AddFiles(ipfiles + [searchpath])
        file.FileSet.AddFileSet(fileset)


def parse_file(file: File, flow: FlowBase, library) -> FileSet:
    if file.FileType == QuartusQSYSSpecificationFile:
        return qsys_to_fileset(file, flow, library)
    elif file.FileType == QuartusIPSpecificationFile:
        if flow.category == FlowCategory.SIMULATION:
            return Spd(file.Path, flow)
        else:
            return file
    else:
        raise GeneratorError(f"Unsupported file type: {file.FileType}")


def copy_ipfile(file: QuartusIPSpecificationFile, dest: Path) -> QuartusIPSpecificationFile:
    """
    Copy IP files to a directory and return a new QuartusIPSpecificationFile object with the new path.
    """
    dest.mkdir(parents=True, exist_ok=True)
    md5file = dest.joinpath(file.Path.name).with_suffix('.md5')
    srcdir = file.Path.with_suffix('')
    destdir = dest.joinpath(file.Path.name).with_suffix('')
    destfile = dest.joinpath(file.Path.name)
    if srcdir.exists():
        if not md5file.exists() or not md5check(file.Path, srcdir, filename=md5file):
            logger.info(f"Copy {file.Path} to {destfile}")
            logger.info(f"Copy {srcdir} to {destdir}")
            copy(str(file.Path), str(destfile))
            copytree(str(srcdir), str(destdir), dirs_exist_ok=True)
            md5write(file.Path, srcdir, filename=md5file)
    else:
        if not md5file.exists() or not md5check(file.Path, filename=md5file):
            logger.info(f"Copy {file.Path} to {destfile}")
            rmtree(destdir, ignore_errors=True)
            copy(str(file.Path), str(destfile))
            md5write(file.Path, filename=md5file)
    file._fileType = QuartusIPSpecificationFile
    file._path = destfile.resolve()
    return file


def copy_qsysfile(file: QuartusQSYSSpecificationFile, dest: Path) -> QuartusQSYSSpecificationFile:
    """
    Copy QSYS files to a directory and return a new QuartusQSYSSpecificationFile object with the new path.
    """
    md5file = dest.joinpath(file.Path.name).with_suffix('.md5')
    qsysdir = dest.joinpath(file.Path.name)
    src = file.Path.parent
    if not md5file.exists() or not md5check(src, filename=md5file):
        copytree(str(src), str(qsysdir), dirs_exist_ok=True)
        md5write(src, filename=md5file)
    file._fileType = QuartusQSYSSpecificationFile
    file._path = qsysdir.joinpath(file.Path.name).with_suffix('.qsys').resolve()
    if file.Path.exists():
        return file
    else:
        raise FileNotFoundError(f"{file.Path}: doesn't exits")


def unpack_ipfile(file: QuartusIPCompressedSpecificationFile, dest: Path) -> QuartusIPSpecificationFile:
    """
    Unpack IP files to a directory and return a new QuartusIPSpecificationFile object with the new path.
    """
    unpack(file.Path, dest)
    file._fileType = QuartusIPSpecificationFile
    file._path = dest.joinpath(file.Path.name).with_suffix('').resolve()
    if file.Path.exists():
        return file
    else:
        raise FileNotFoundError(f"{file.Path.resolve()}: doesn't exits")


def unpack_qsysfile(file: QuartusQSYSCompressedSpecificationFile, dest: Path) -> QuartusQSYSSpecificationFile:
    """
    Unpack QSYS files to a directory and return a new QuartusQSYSSpecificationFile object with the new path.
    """
    dest = dest.joinpath(file.Path.name).with_suffix('').with_suffix('')
    unpack(file.Path, dest)
    file._fileType = QuartusQSYSSpecificationFile
    file._path = dest.joinpath(file.Path.name).with_suffix('').resolve()
    if file.Path.exists():
        return file
    else:
        raise FileNotFoundError(f"{file.Path}: doesn't exits")


def unpack(file: Path, dest: Path) -> None:
    """
    Unpack a file to a directory and return the new path.
    """
    md5file = dest.joinpath(file.name).with_suffix('.md5')
    if not md5file.exists() or not md5check(file, filename=md5file):
        logger.info(f"Unpack {file} to {dest}")
        with ZipFile(file, 'r') as zip:
            zip.extractall(dest)
        md5write(file, filename=md5file)


def filter_duplicated_files(files: List[File]) -> List[File]:
    """
    Filter duplicated files in a list of files.
    """
    unique_files = set(files)
    filtered_files = dict()
    for file in unique_files:
        # if file.Path.name in filtered_files:
        #     logger.warning(f"Duplicate files - {file.Path} will override {filtered_files[file.Path.name].Path}")
        filtered_files[file.Path.name] = file
    return list(filtered_files.values())
