from __future__ import annotations

import logging
import os

from simplhdl.plugin import FlowBase, GeneratorBase
from simplhdl.project.files import FileFactory, Jinja2File
from simplhdl.utils import jinja2_copy

logger = logging.getLogger(__name__)


class Jinja2Generator(GeneratorBase):
    priority = 100
    supported_file_types = (Jinja2File,)

    def run(self, flow: FlowBase):
        files = self.get_files(flow)
        if files:
            logger.debug("Running Jinja2 Generator")
            dest_dir = self.builddir.joinpath("jinja2")
            dest_dir.mkdir(parents=True, exist_ok=True)

        kwargs = {"os": os}
        for file in files:
            dest_file = dest_dir.joinpath(file.path.name).with_suffix("").resolve()
            jinja2_copy(file.path, dest_file, **kwargs)
            file.parent.replace_file(file, FileFactory.create(dest_file))
