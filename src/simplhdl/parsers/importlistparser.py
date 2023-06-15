from pathlib import Path
from ..parser import ParserFactory, ParserBase


@ParserFactory.register()
class ImportListParser(ParserBase):

    def __init__(self, filename: Path):
        super().__init__(filename)

    def is_valid_format(self) -> bool:
        if self.filename.name == "import_list":
            return True
        else:
            return False

    def parse(self) -> None:
        raise NotImplementedError(f"{__name__} not implemented for {self.filename}")
