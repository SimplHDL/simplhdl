from pathlib import Path
from pyEDAA.ProjectModel import FileSet  # type: ignore
from ..parser import ParserFactory, ParserBase


@ParserFactory.register()
class ImportListParser(ParserBase):

    def __init__(self):
        super().__init__()

    def is_valid_format(self, filename: Path) -> bool:
        if filename.name == "import_list":
            return True
        else:
            return False

    def parse(self, filename: Path) -> FileSet:
        raise NotImplementedError(f"{__name__} not implemented for {filename}")
