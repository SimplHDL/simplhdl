import logging

from argparse import Namespace
from pathlib import Path

from .flow import FlowBase, FlowCategory
from ..pyedaa.project import Project

logger = logging.getLogger(__name__)


class ImplementationFlow(FlowBase):

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.category = FlowCategory.IMPLEMENTATION
        self.hdl_language = None
        self.templates = None
