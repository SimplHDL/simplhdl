import argparse
from pathlib import Path
from . import __version__
from .simplhdl import Simplhdl


def parse_arguments():
    parser = argparse.ArgumentParser(
        prog="simpl",
        description="Simple framework for simulation and implementation of HDL designs"
    )
    parser.add_argument(
        'filespec',
        type=Path,
        help="Project specification file"
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f"SimplHDL version {__version__}"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    simpl = Simplhdl()
    simpl.create_project(args.filespec)
    simpl.run()


if __name__ == '__main__':
    main()
