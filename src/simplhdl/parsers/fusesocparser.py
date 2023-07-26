import yaml
from pathlib import Path
from pyEDAA.ProjectModel import FileSet  # type: ignore

from ..parser import ParserFactory, ParserBase


@ParserFactory.register()
class FuseSocParser(ParserBase):

    _format_id: str = "CAPI=2:"

    def __init__(self):
        super().__init__()

    def is_valid_format(self, filename: Path) -> bool:
        with open(filename, 'r') as fp:
            if fp.readline().strip() == self._format_id:
                return True
            else:
                return False

    def parse(self, filename: Path) -> FileSet:
        with open(filename, 'r') as fp:
            try:
                spec = yaml.safe_load(fp)
            except yaml.YAMLError as e:
                raise e
        print(spec)
        return FileSet("name")
