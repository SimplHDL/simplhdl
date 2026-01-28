from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import argcomplete

from .. import __version__
from ..plugin.flow import FlowFactory


def parse_arguments(args: Sequence[str] = None, namespace: None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="simpl",
        description="Simple framework for simulation and implementation of HDL designs",
    )
    parser.add_argument("--projectspec", type=Path, help="Project specification file")
    parser.add_argument("--version", action="version", version=f"SimplHDL version {__version__}")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    parser.add_argument(
        "-o",
        "--outputdir",
        default="_build",
        type=Path,
        help="output directory for build files",
    )
    subparsers = parser.add_subparsers(
        title="Flows",
        description="""Different work flows for simulation and implementation
                       of HDL designs""",
        dest="flow",
    )
    for flow_class in FlowFactory.get_flows().values():
        flow_class.parse_args(subparsers)

    argcomplete.autocomplete(parser)
    return parser.parse_args(args=args, namespace=namespace)
