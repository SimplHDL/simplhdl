from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import yaml

from simplhdl import Fileset, Project
from simplhdl.plugin import ParserBase


class FuseSocParser(ParserBase):

    _format_id: str = "CAPI=2:"

    def __init__(self):
        super().__init__()

    def is_valid_format(self, filename: Path | None) -> bool:
        if filename is None:
            return False

        with open(filename, 'r') as fp:
            if fp.readline().strip() == self._format_id:
                return True
            else:
                return False

    def parse(self, filename: Path | None, project: Project, args: Namespace) -> Fileset:
        with open(filename, 'r') as fp:
            try:
                spec = yaml.safe_load(fp)
            except yaml.YAMLError as e:
                raise e
        print(spec)
        return Fileset("name")
