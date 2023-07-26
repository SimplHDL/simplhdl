import argparse
import logging
from pathlib import Path
from . import __version__
from .simplhdl import Simplhdl
from .plugins import load_plugins


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
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help="Increase verbosity"

    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    levels = [logging.WARNING, logging.INFO, logging.DEBUG, logging.NOTSET]
    level = levels[min(args.verbose, len(levels)-1)]
    logging.basicConfig(level=level)
    load_plugins()
    simpl = Simplhdl()
    simpl.create_project(args.filespec)
    simpl.run()


if __name__ == '__main__':
    main()
