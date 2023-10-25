from pathlib import Path
from typing import Optional

from pyEDAA.ProjectModel import CocotbPythonFile
from .utils import sh
from .pyedaa.project import Project


class Cocotb:

    def __init__(self, project: Project) -> None:
        self.project = project

    def lib_name_path(self, simulator: str, interface: str) -> Path:
        output = sh(['cocotb-config', '--lib-name-path', interface, simulator])
        path = Path(output)
        if not path.exists():
            raise FileNotFoundError(f"{path}: not found")
        return path

    def module(self) -> Optional[str]:
        set_ = set()
        modules = self.project.DefaultDesign.TopLevel
        for module in modules.split():
            if self.is_python_module(module):
                # TODO: What if more than one module match?
                set_.add(module)
        if not set_:
            return None
        elif len(set_) == 1:
            return next(iter(set_))
        else:
            raise NotImplementedError(f"More than one CocoTB module found: {set_}")

    def is_python_module(self, name: str):
        # TODO: Should we also search in installed packages?
        if [f for f in self.files() if f.Path.stem == name]:
            return True

    def files(self):
        return self.project.DefaultDesign.Files(CocotbPythonFile)

    @property
    def enabled(self) -> bool:
        for file in self.files():
            return True
        return False

    @property
    def pythonpath(self) -> str:
        directories = {str(f.Path.parent.absolute()) for f in self.files()}
        return ':'.join(directories)
