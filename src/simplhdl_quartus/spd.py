from __future__ import annotations

import logging
import re
from pathlib import Path
from shutil import copy, copytree, ignore_patterns, rmtree
from typing import Generator
from xml.etree.ElementTree import Element, parse
from zipfile import ZipFile

from simplhdl import Fileset
from simplhdl.plugin import (
    FlowBase,
    FlowCategory,
    FlowTools,
    GeneratorBase,
    GeneratorError,
)
from simplhdl.project.attributes import Library
from simplhdl.project.files import (
    File,
    HdlSearchPath,
    MemoryHexFile,
    QuartusIpFile,
    QuartusIpZipFile,
    QuartusQipFile,
    QuartusQsysFile,
    QuartusQsysZipFile,
    SdcFile,
    SystemVerilogFile,
    VerilogFile,
    VhdlFile,
    UsedIn,
)
from simplhdl.utils import md5check, md5write, sh

logger = logging.getLogger(__name__)


FILETYPE_MAP = {
    "SYSTEM_VERILOG": SystemVerilogFile,
    "SYSTEM_VERILOG_ENCRYPT": SystemVerilogFile,
    "VERILOG": VerilogFile,
    "VERILOG_ENCRYPT": VerilogFile,
    "VHDL": VhdlFile,
    "VHDL_ENCRYPT": VhdlFile,
    "SDC_ENTITY": SdcFile,
    "HEX": MemoryHexFile,
}

TOOL_MAP = {
    FlowTools.VCS: "vcs",
    FlowTools.NCSIM: "ncsim",
    FlowTools.QUESTASIM: "modelsim",
    FlowTools.MODELSIM: "modelsim",
    FlowTools.VCS: "vcs",
    FlowTools.RIVIERAPRO: "riviera",
}


class Spd:
    def __init__(self, filename: Path, flow: FlowBase, ip_path: Path | None = None) -> None:
        self._files = list()
        self._filename = filename.resolve()
        self.flow = flow
        self.libraries = dict()
        self.simulators = set()
        spdfile = filename.parent.joinpath(filename.stem, filename.name).with_suffix(".spd")
        if not spdfile.exists():
            if ip_path:
                command = f"qsys-generate --simulation=VERILOG --search-path={ip_path},$ {filename.resolve()}".split()
            else:
                command = f"qsys-generate --simulation=VERILOG {filename.resolve()}".split()
            logger.info(f"Generate simulation files for {filename}")
            sh(command, cwd=filename.parent)
            if not spdfile.exists():
                raise FileNotFoundError(f"{spdfile}: doesn't exits")
        logger.debug(f"Parse {spdfile}")
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
            if f.tag == "file":
                properties = f.attrib
                if "simulator" in properties:
                    simulators = re.split(r"\s*,\s*", properties["simulator"])
                    if not self.supported(self.flow, simulators):
                        continue
                yield f

    def element_to_file(self, element: Element) -> File:
        properties = element.attrib
        if properties["path"].startswith("/"):
            path = Path(properties["path"])
        else:
            path = Path(self.location, properties["path"])
        libraryname = properties["library"]
        if libraryname not in self.libraries:
            self.libraries[libraryname] = Library(libraryname)
        fileclass = FILETYPE_MAP.get(properties["type"], File)
        if issubclass(fileclass, (VhdlFile, VerilogFile, SystemVerilogFile)):
            return fileclass(file=path, library=self.libraries[libraryname])
        else:
            return fileclass(file=path)

    def supported(self, flow: FlowBase, simulators: list) -> bool:
        self.simulators.update(simulators)
        for tool in flow.tools:
            if TOOL_MAP.get(tool, None) in simulators:
                return True
        return False

    @property
    def filesets(self):
        filesets = list()
        for library in self.libraries.values():
            name = f"{self._filename}.{library.name}"
            fileset = Fileset(name, library=library)
            for file in self._files:
                if isinstance(file, (VhdlFile, VerilogFile, SystemVerilogFile)):
                    if file.library == library:
                        fileset.add_file(file)
            filesets.append(fileset)
        othersfileset = Fileset(self._filename)
        for file in self._files:
            if not isinstance(file, (VhdlFile, VerilogFile, SystemVerilogFile)):
                othersfileset.add_file(file)
        filesets.append(othersfileset)
        return filesets


class QuartusGenerator(GeneratorBase):
    def unpack_ip(self, filename: File) -> QuartusIpFile:  # noqa: C901
        ipdir = self.builddir.joinpath("ips")
        dest = ipdir.joinpath(filename.Path.name).with_suffix("")
        md5file = dest.with_suffix(".md5")
        ipdir.mkdir(exist_ok=True)
        if isinstance(filename, QuartusQsysFile):
            filename = self.copy_qsys(filename, dest, md5file)
            ipfiles = self.parse_qsys(filename)
            if self.flow.category == FlowCategory.SIMULATION:
                for ipfile in ipfiles:
                    spd = Spd(ipfile.path, self.flow, dest.resolve())
                    parent = filename.parent
                    for fileset in reversed(spd.filesets):
                        # Add fileset to parent, then set parent to fileset to make a chain
                        parent.add_fileset(fileset)
                        parent = fileset
            else:
                fileset = Fileset(
                    filename.path.name,
                    library=self.project.defaultDesign.defaultLibrary,
                )
                for file in ipfiles:
                    fileset.add_file(file)
                filename.parent.add_fileset(fileset)
        elif isinstance(filename, QuartusIpZipFile):
            update = True
            if md5file.exists():
                update = not md5check(filename.path, filename=md5file)
            if update:
                with ZipFile(filename.path, "r") as zip:
                    zip.extractall(ipdir)
                md5write(filename.path, filename=md5file)
                logger.debug(f"Copy {filename.path} to {dest}")

            if filename.path.suffix == ".zip":
                filename._path = dest.absolute()
            else:
                filename._path = dest.with_suffix(".ip").absolute()
            filename._fileType = QuartusIpFile

        elif isinstance(filename, QuartusIpFile):
            update = True
            dir = filename.Path.with_suffix("")
            if dir.exists():
                if md5file.exists():
                    update = not md5check(filename.path, dir, filename=md5file)
            if update:
                copy(str(filename.path), str(dest.with_suffix(".ip")))
                md5write(filename.path, filename=md5file)
                if dir.exists():
                    copytree(str(dir), str(dest.with_suffix("")), dirs_exist_ok=True)
                    md5write(filename.path, dir, filename=md5file)
                    logger.debug(f"Copy {filename.path} to {dest}")
            filename._path = dest.with_suffix(".ip").resolve()
        return filename

    def run(self, flow: FlowBase) -> None:  # noqa: C901
        seen = dict()
        self.flow = flow
        ip_dir = self.builddir.joinpath("ips")
        qsys_dir = self.builddir.joinpath("qsys")
        quartusip_types = (
            QuartusIpFile,
            QuartusIpZipFile,
            QuartusQsysFile,
            QuartusQsysZipFile,
        )
        all_files = self.project.defaultDesign.files(type=quartusip_types)

        if flow.category == FlowCategory.SIMULATION:
            files = [f for f in all_files if UsedIn.SIMULATION in f.usedin]
        elif flow.category == FlowCategory.IMPLEMENTATION:
            files = [f for f in all_files if UsedIn.IMPLEMENTATION in f.usedin]
        elif flow.category == FlowCategory.DEFAULT:
            return
        else:
            files = all_files

        for file in files:
            # The second time we see a file it is already processed and we just
            # Update the file path
            fileid = str(file.path.resolve())
            if fileid in seen:
                file._path = seen.get(fileid)._path
                continue
            if isinstance(file, QuartusQipFile):
                continue
            elif isinstance(file, QuartusIpZipFile):
                file = unpack_ipfile(file, ip_dir)
            elif isinstance(file, QuartusIpFile):
                file = copy_ipfile(file, ip_dir)
            elif isinstance(file, QuartusQsysZipFile):
                file = unpack_qsysfile(file, qsys_dir)
            elif isinstance(file, QuartusQsysFile):
                file = copy_qsysfile(file, qsys_dir)
            parse_file(file, flow, self.project.defaultDesign.defaultLibrary)
            # register the file as seen
            seen[fileid] = file


def get_list_of_ipfiles(filename: QuartusQsysFile) -> list[File]:
    """
    Search for IP files in a QSYS file and return a list of QuartusIPSpecificationFile objects.
    """
    files = list()
    with filename.path.open() as file:
        lines = file.readlines()
        for line in lines:
            m = re.search(r"<ipxact:value>(.*\.ip)</ipxact:value>", line)
            if m:
                ipfile = filename.path.parent.joinpath(m.group(1))
                if ipfile.exists():
                    logger.debug(f"Found {ipfile} in {filename.path}")
                    files.append(QuartusIpFile(ipfile))
                else:
                    logger.warning(f"File {ipfile} not found")
            m = re.search(r'<parameter name="logicalView">(.*\.ip)</parameter>', line)
            if m:
                ipfile = filename.path.parent.joinpath(m.group(1))
                if ipfile.exists():
                    logger.debug(f"Found {ipfile} in {filename.path}")
                    files.append(QuartusIpFile(ipfile))
                else:
                    logger.warning(f"File {ipfile} not found")
    return files


def qsys_to_fileset(file: QuartusQsysFile, flow: FlowBase, library) -> Fileset:
    """
    Parse a QSYS file and return a FileSet object.
    """
    ipfiles = get_list_of_ipfiles(file)
    if flow.category == FlowCategory.SIMULATION:
        parent = file.parent
        for ipfile in [file] + ipfiles:
            spd = Spd(ipfile.path, flow, file.path.parent.resolve())
            for fileset in reversed(spd.filesets):
                # Add fileset to parent, then set parent to fileset to make a chain
                parent.add_fileset(fileset)
                parent = fileset
    elif flow.category == FlowCategory.IMPLEMENTATION:
        # NOTE: Some qsys require a search path to find the HEX files
        searchpath = HdlSearchPath(file.path.parent)
        searchpath.usedin = {UsedIn.IMPLEMENTATION}
        fileset = Fileset(file.path.name, library=library)
        for ipfile in ipfiles + [searchpath]:
            fileset.add_file(ipfile)
        file.parent.add_fileset(fileset)


def parse_file(file: File, flow: FlowBase, library) -> Fileset:
    if isinstance(file, QuartusQsysFile):
        return qsys_to_fileset(file, flow, library)
    elif isinstance(file, QuartusIpFile):
        if flow.category == FlowCategory.SIMULATION:
            spd = Spd(file.path, flow)
            parent = file.parent
            for fileset in reversed(spd.filesets):
                # Add fileset to parent, then set parent to fileset to make a chain
                parent.add_fileset(fileset)
                parent = fileset
        else:
            return file
    else:
        raise GeneratorError(f"Unsupported file type: {type(file)}")


def copy_ipfile(file: QuartusIpFile, dest: Path) -> QuartusIpFile:
    """
    Copy IP files to a directory and return a new QuartusIpFile object with the new path.
    """
    dest.mkdir(parents=True, exist_ok=True)
    md5file = dest.joinpath(file.path.name).with_suffix(".md5")
    srcdir = file.path.with_suffix("")
    destdir = dest.joinpath(file.path.name).with_suffix("")
    destfile = dest.joinpath(file.path.name)
    if srcdir.exists():
        if not md5file.exists() or not md5check(file.path, srcdir, filename=md5file):
            logger.debug(f"Copy {file.path} to {destfile}")
            logger.debug(f"Copy {srcdir} to {destdir}")
            copy(str(file.path), str(destfile))
            copytree(str(srcdir), str(destdir), dirs_exist_ok=True)
            md5write(file.path, srcdir, filename=md5file)
    else:
        if not md5file.exists() or not md5check(file.path, filename=md5file):
            logger.debug(f"Copy {file.path} to {destfile}")
            rmtree(destdir, ignore_errors=True)
            copy(str(file.path), str(destfile))
            md5write(file.path, filename=md5file)
    file.__class__ = QuartusIpFile
    file._path = destfile.resolve()
    return file


def copy_qsysfile(file: QuartusQsysFile, dest: Path) -> QuartusQsysFile:
    """
    Copy QSYS files to a directory and return a new QuartusQsysFile object with the new path.
    """
    md5file = dest.joinpath(file.path.name).with_suffix(".md5")
    qsysdir = dest.joinpath(file.path.name).with_suffix("")

    src = file.path.parent
    if not md5file.exists() or not md5check(src, filename=md5file):
        logger.debug(f"Copy {file.path} to {qsysdir}")
        # If destination is a subdirectory of source the copytree will have
        # to ignore this subdirectory
        if qsysdir.resolve().is_relative_to(src.resolve()):
            ignoredir = qsysdir.resolve().relative_to(src.resolve()).parents[-2]
            copytree(
                str(src),
                str(qsysdir),
                dirs_exist_ok=True,
                ignore=ignore_patterns(ignoredir),
            )
        else:
            copytree(str(src), str(qsysdir), dirs_exist_ok=True)
        md5write(src, filename=md5file)
    file.__class__ = QuartusQsysFile
    file._path = qsysdir.joinpath(file.path.name).with_suffix(".qsys").resolve()
    if file.path.exists():
        return file
    else:
        raise FileNotFoundError(f"{file.path}: doesn't exits")


def unpack_ipfile(file: QuartusIpZipFile, dest: Path) -> QuartusIpFile:
    """
    Unpack IP files to a directory and return a new QuartusIpFile object with the new path.
    """
    unpack(file.path, dest)
    file.__class__ = QuartusIpFile
    file._path = dest.joinpath(file.path.name).with_suffix("").resolve()
    if file.path.exists():
        return file
    else:
        raise FileNotFoundError(f"{file.path.resolve()}: doesn't exits")


def unpack_qsysfile(file: QuartusQsysZipFile, dest: Path) -> QuartusQsysFile:
    """
    Unpack QSYS files to a directory and return a new QuartusQsysFile object with the new path.
    """
    dest = dest.joinpath(file.path.name).with_suffix("").with_suffix("")
    unpack(file.path, dest)
    file.__class__ = QuartusQsysFile
    file._path = dest.joinpath(file.path.name).with_suffix("").resolve()
    if file.path.exists():
        return file
    else:
        raise FileNotFoundError(f"{file.path}: doesn't exits")


def unpack(file: Path, dest: Path) -> None:
    """
    Unpack a file to a directory and return the new path.
    """
    md5file = dest.parent.joinpath(file.name).with_suffix(".md5")
    if not md5file.exists() or not md5check(file, filename=md5file):
        logger.info(f"Unpack {file} to {dest}")
        with ZipFile(file, "r") as zip:
            zip.extractall(dest)
        md5write(file, filename=md5file)


def filter_duplicated_files(files: list[File]) -> list[File]:
    """
    Filter duplicated files in a list of files.
    """
    unique_files = set(files)
    filtered_files = dict()
    for file in unique_files:
        filtered_files[file.path.name] = file
    return list(filtered_files.values())
