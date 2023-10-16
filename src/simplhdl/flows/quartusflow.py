try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import os
import shutil
import logging

from jinja2 import Environment, FileSystemLoader
from zipfile import ZipFile
from shutil import copy, copytree
import pyEDAA.ProjectModel as pm

from ..flow import FlowFactory, FlowBase
from ..project import IPSpecificationFile
from ..resources.templates import quartus as templates
from ..utils import sh, generate_from_template, md5write, md5check

logger = logging.getLogger(__name__)


@FlowFactory.register('quartus')
class QuartusFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('quartus', help='Quartus FPGA Build Flow')
        parser.add_argument(
            '-s',
            '--step',
            action='store',
            choices=['synthesis', 'implement', 'finalize', 'compile'],
            default='compile',
            help="flow step to run"
        )
        parser.add_argument(
            '--gui',
            action='store_true',
            help="Open project in Quartus GUI"
        )

    def run(self) -> None:
        self.validate()
        self.configure()
        self.generate()
        self.execute(self.args.step)

    def validate(self):
        if self.project.DefaultDesign.DefaultFileSet.TopLevel is None:
            raise Exception("No top level specified")

    def configure(self):
        os.makedirs(self.builddir, exist_ok=True)
        self.is_tool_setup()

    def generate(self):
        for ipfile in self.project.DefaultDesign.DefaultFileSet.Files(fileType=IPSpecificationFile):
            self.unpack_ip(ipfile)

        templatedir = resources_files(templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)

        template = environment.get_template('project.tcl.j2')
        generate_from_template(template, self.builddir,
                               pm=pm,
                               IPSpecificationFile=IPSpecificationFile,
                               project=self.project)
        template = environment.get_template('run.tcl.j2')
        generate_from_template(template, self.builddir,
                               project=self.project)
        command = "quartus_sh -t project.tcl".split()
        self.is_tool_setup()
        sh(command, cwd=self.builddir, output=True)

    def execute(self, step: str):
        name = self.project.Name
        if self.args.gui:
            sh(['quartus', name], cwd=self.builddir)
            return

        command = f"quartus_sh -t run.tcl {step} -project {name}".split()
        sh(command, cwd=self.builddir, output=True)

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

    def unpack_ip(self, filename: IPSpecificationFile) -> None:
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
