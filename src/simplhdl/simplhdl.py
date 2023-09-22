import os
import logging
import shutil

from pathlib import Path
from pyEDAA.ProjectModel import VHDLLibrary  # type: ignore
from edalize.edatool import get_edatool

from .project import Project
from .parser import ParserFactory

logger = logging.getLogger(__name__)

from cocotb.config import main

class Simplhdl:

    def __init__(self):
        self._project = None
        self.builddir = '_build'

    def create_project(self, filename: Path) -> None:
        default_library = VHDLLibrary("work")
        project = Project("default")
        parser = ParserFactory().get_parser(filename)
        fileset = parser.parse(filename, project)
        project.DefaultDesign.AddFileSet(fileset)
        # TODO: Need some more understading of the project and design classes
        project.DefaultDesign.TopLevel = fileset.TopLevel
        project.DefaultDesign.AddVHDLLibrary(default_library)
        self._project = project

    def run(self):
        tool = "modelsim"
        edam = self._project.export_edam(tool)
        for f in edam['files']:
            logger.debug(f)
        eda_tool = tool
        backend = get_edatool(eda_tool)(edam=edam, work_root=self.builddir)
        shutil.rmtree(self.builddir, ignore_errors=True)
        os.makedirs(self.builddir, exist_ok=True)
        backend.configure()
        backend.build()
        backend.run()
