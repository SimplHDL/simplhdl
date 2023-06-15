import yaml

from pathlib import Path
from ..parser import ParserFactory, ParserBase


@ParserFactory.register()
class FuseSocParser(ParserBase):

    def __init__(self, filename: Path):
        super().__init__(filename)

    def is_valid_format(self) -> bool:
        with open(self.filename, 'r') as fp:
            first_line = fp.readline()
        if first_line.strip() == "CAPI=2:":
            return True
        else:
            return False

    def parse(self) -> None:
        with open(self.filename, 'r') as fp:
            try:
                spec = yaml.safe_load(fp)
            except yaml.YAMLError as e:
                raise e
            print(spec)
