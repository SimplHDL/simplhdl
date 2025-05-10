import shutil
import logging
import zipfile
import os

from argparse import Namespace
from pathlib import Path

from simplhdl.flow import FlowFactory, FlowTools
from simplhdl.flows.implementationflow import ImplementationFlow
from simplhdl.flows.quartusflow import QuartusFlow
from simplhdl.resources.templates import quartus as templates
from simplhdl.flows.encrypt.encryptflow import encrypt
from simplhdl.pyedaa.project import Project
from simplhdl.pyedaa.attributes import UsedIn
from simplhdl.pyedaa import (
    File,
    HDLSearchPath,
    HDLIncludeFile,
    HDLSourceFile,
    VerilogIncludeFile,
    VerilogSourceFile,
    SystemVerilogSourceFile,
    VHDLSourceFile,
    ConstraintFile,
    QuartusQIPSpecificationFile,
    QuartusIPSpecificationFile,
    SettingFile
)

logger = logging.getLogger(__name__)


@FlowFactory.register('quartus-export')
class QuartusExportFlow(ImplementationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('quartus-export', help='Export Quartus project')
        parser.add_argument(
            '--encrypt',
            action='store_true',
            help="Encrypt HDL source files"
        )
        parser.add_argument(
            '-o',
            '--output',
            action='store',
            metavar='FILE',
            dest='archivefile',
            type=Path,
            help="Output zip file"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.vendors = ['mentor', 'synopsys']
        self.templates = templates
        self.tools.add(FlowTools.QUARTUS)
        self.rootdir = self.directory_root()

    def directory_root(self):
        files = list()
        for file in [f for f in self.project.DefaultDesign.Files() if 'implementation' in f[UsedIn]]:
            if isinstance(file, SettingFile):
                continue
            elif isinstance(file, (ConstraintFile, QuartusQIPSpecificationFile)):
                pass
            elif isinstance(file, (HDLSearchPath, QuartusIPSpecificationFile)):
                continue
            files.append(file.Path.absolute())
        return Path(os.path.commonpath(files))

    def copy_files(self):
        seen = dict()
        files = [f for f in self.project.DefaultDesign.Files() if 'implementation' in f[UsedIn]]
        for file in files:
            fileid = str(file.Path.resolve())
            dest = self.builddir.joinpath('src', file.Path.relative_to(self.rootdir))
            if fileid in seen:
                file._path = seen.get(fileid)._path
                continue
            elif isinstance(file, SettingFile):
                continue
            elif isinstance(file, (ConstraintFile, QuartusQIPSpecificationFile)):
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file.Path, dest)
            elif isinstance(file, (HDLSearchPath, QuartusIPSpecificationFile)):
                dest = file.Path
            elif isinstance(file, (HDLSourceFile, HDLIncludeFile)):
                dest.parent.mkdir(parents=True, exist_ok=True)
                if self.args.encrypt:
                    encrypt(file.Path, dest, language=get_language(file), vendors=self.vendors)
                else:
                    shutil.copyfile(file.Path, dest)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file.Path, dest)
            # Convert to relative path
            file._path = dest.absolute().relative_to(self.builddir.absolute())
            seen[fileid] = file

    def create_project(self) -> None:
        args = Namespace(step='project', archive=False, gui=False)
        quartus = QuartusFlow('quartus', args, self.project, self.builddir)
        quartus.run()
        try:
            shutil.rmtree(self.builddir.joinpath('dni'))
            shutil.rmtree(self.builddir.joinpath('qdb'))
            os.remove(self.builddir.joinpath('project.tcl'))
        except FileNotFoundError:
            pass

    def archive_project(self) -> None:
        if self.args.archivefile:
            tmp = self.builddir.parent.joinpath(self.args.archivefile.name)
            output = self.args.archivefile
        else:
            tmp = self.builddir.parent.joinpath(f'{self.project.Name}.zip')
            output = self.builddir.joinpath(tmp.name)
        archive(self.builddir, tmp)
        if tmp == output:
            return
        elif not output.parent.exists():
            raise FileNotFoundError(f'Output directory {output.parent.resolve()} does not exist')
        elif output.exists():
            os.remove(output)
        shutil.move(tmp, output)

    def run(self) -> None:
        self.copy_files()
        self.create_project()
        self.archive_project()

    def is_tool_setup(self) -> None:
        exit: bool = False
        if shutil.which('quartus_sh') is None:
            logger.error('quartus_sh: not found in PATH')
            exit = True
        if shutil.which('quartus') is None:
            logger.error('quartus: not found in PATH')
            exit = True
        if exit:
            raise FileNotFoundError("Quartus is not setup correctly")


def get_language(file: File) -> str:
    fileMap = {
        SystemVerilogSourceFile: 'systemverilog',
        VerilogSourceFile: 'verilog',
        VerilogIncludeFile: 'systemverilog',
        VHDLSourceFile: 'vhdl'
    }
    return fileMap[file.FileType]


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
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files in the directory
        for file in directory.rglob('*'):
            if file.is_file():
                # Place each file under the top_folder
                arcname = Path(top_folder) / file.relative_to(directory)
                zipf.write(file, arcname=arcname)
    return destination
