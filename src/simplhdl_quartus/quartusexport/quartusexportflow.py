import logging
import os
import shutil
import zipfile
from argparse import Namespace
from pathlib import Path

from simplhdl import Project
from simplhdl.plugin import FlowTools, ImplementationFlow
from simplhdl.project.files import (
    ConstraintFile,
    File,
    HdlSearchPath,
    QuartusIpFile,
    QuartusQipFile,
    QuartusQsfFile,
    SystemVerilogFile,
    VerilogIncludeFile,
    VerilogFile,
    VhdlFile,
    UsedIn,
)
from simplhdl_encrypt.encrypt.encryptflow import encrypt

from ..quartusflow import QuartusFlow
from ..resources.templates import quartus as templates

logger = logging.getLogger(__name__)


class QuartusExportFlow(ImplementationFlow):
    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser("quartus-export", help="Export Quartus project")
        parser.add_argument("--encrypt", action="store_true", help="Encrypt HDL source files")
        parser.add_argument(
            "-o",
            "--output",
            action="store",
            metavar="FILE",
            dest="archivefile",
            type=Path,
            help="Output zip file",
        )
        parser.add_argument(
            "-s",
            "--structure",
            action="store",
            choices=["flat", "hierarchy"],
            default="hierarchy",
            help="Output zip file",
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.vendors = ["mentor", "synopsys"]
        self.templates = templates
        self.tools.add(FlowTools.QUARTUS)
        self.rootdir = self.directory_root()

    def directory_root(self):
        files = list()
        for file in [f for f in self.project.defaultDesign.files(usedin=UsedIn.IMPLEMENTATION)]:
            if isinstance(file, QuartusQsfFile):
                continue
            elif isinstance(file, (ConstraintFile, QuartusQipFile)):
                pass
            elif isinstance(file, (HdlSearchPath, QuartusIpFile)):
                continue
            files.append(file.path.resolve())
        return Path(os.path.commonpath(files))

    def copy_files(self):
        seen = dict()
        files = [f for f in self.project.defaultDesign.files(usedin=UsedIn.IMPLEMENTATION)]
        for file in files:
            fileid = str(file.path.resolve())
            dest = self.builddir.joinpath("src", file.path.relative_to(self.rootdir))
            if self.args.structure == "flat":
                dest = self.builddir.joinpath("src", file.path.name)
            if fileid in seen:
                file._path = seen.get(fileid)._path
                continue
            elif isinstance(file, QuartusQsfFile):
                continue
            elif isinstance(file, (ConstraintFile, QuartusQipFile)):
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file.path, dest)
            elif isinstance(file, (HdlSearchPath, QuartusIpFile)):
                dest = file.path
            elif isinstance(file, (VerilogFile, VerilogIncludeFile, SystemVerilogFile, VhdlFile)):
                dest.parent.mkdir(parents=True, exist_ok=True)
                if self.args.encrypt and file.encrypt:
                    encrypt(
                        file.path,
                        dest,
                        language=get_language(file),
                        vendors=self.vendors,
                    )
                else:
                    shutil.copyfile(file.path, dest)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file.path, dest)
            # Convert to relative path
            file._path = dest
            seen[fileid] = file

    def create_project(self) -> None:
        args = Namespace(step="project", archive=False, gui=False)
        quartus = QuartusFlow("quartus", args, self.project, self.builddir)
        quartus.run()
        try:
            shutil.rmtree(self.builddir.joinpath("dni"))
            shutil.rmtree(self.builddir.joinpath("qdb"))
            os.remove(self.builddir.joinpath("project.tcl"))
        except FileNotFoundError:
            pass

    def archive_project(self) -> None:
        if self.args.archivefile:
            tmp = self.builddir.parent.joinpath(self.args.archivefile.name)
            output = self.args.archivefile
        else:
            tmp = self.builddir.parent.joinpath(f"{self.project.name}.zip")
            output = self.builddir.joinpath(tmp.name)
        archive(self.builddir, tmp)
        if tmp == output:
            return
        elif not output.parent.exists():
            raise FileNotFoundError(f"Output directory {output.parent.resolve()} does not exist")
        elif output.exists():
            os.remove(output)
        shutil.move(tmp, output)

    def run(self) -> None:
        self.copy_files()
        # NOTE: Set path relative to builddir for all files
        File.set_path_relative_to(self.builddir)
        self.create_project()
        self.archive_project()

    def is_tool_setup(self) -> None:
        exit: bool = False
        if shutil.which("quartus_sh") is None:
            logger.error("quartus_sh: not found in PATH")
            exit = True
        if shutil.which("quartus") is None:
            logger.error("quartus: not found in PATH")
            exit = True
        if exit:
            raise FileNotFoundError("Quartus is not setup correctly")


def get_language(file: File) -> str:
    fileMap = {
        SystemVerilogFile: "systemverilog",
        VerilogFile: "verilog",
        VerilogIncludeFile: "systemverilog",
        VhdlFile: "vhdl",
    }
    return fileMap[type(file)]


def archive(directory: Path, destination: Path) -> Path:
    """
    Recursively zip all contents of the given folder into a zip file.
    The zip archive will contain a top-level folder with the same name
    as the zip file (excluding the extension).

    Parameters:
        directory (Path): The folder whose contents will be zipped.
        destination (Path): The path to the resulting zip file.
                           Its stem will be used as the top-level folder name.

    Returns:
        Path: The path to the created zip archive.
    """
    top_folder = destination.stem  # top folder inside the archive
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files in the directory
        for file in directory.rglob("*"):
            if file.is_file():
                # Place each file under the top_folder
                arcname = Path(top_folder) / file.relative_to(directory)
                zipf.write(file, arcname=arcname)
    return destination
