import logging

from argparse import Namespace
from pathlib import Path

from .flow import FlowBase, FlowCategory
from ..project.project import Project
from ..project.files import UsedIn

__all__ = ["ImplementationFlow"]

logger = logging.getLogger(__name__)


class ImplementationFlow(FlowBase):
    usedin = UsedIn.IMPLEMENTATION

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.category = FlowCategory.IMPLEMENTATION
        self.hdl_language = None
        self.templates = None
