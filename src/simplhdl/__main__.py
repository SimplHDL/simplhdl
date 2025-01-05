import sys
import argparse
import argcomplete
import logging
import traceback

from typing import Sequence

from pathlib import Path
from . import __version__
from .simplhdl import Simplhdl
from .plugins import load_plugins
from .flow import FlowFactory, FlowError
from .generator import GeneratorError
from .parser import ParserError
from .utils import CalledShError

logger = logging.getLogger(__name__)


def parse_arguments(args: Sequence[str] = None, namespace: None = None) -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        prog="simpl",
        description="Simple framework for simulation and implementation of HDL designs"
    )
    parser.add_argument(
        '--projectspec',
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
    parser.add_argument(
        '-o',
        '--outputdir',
        default='_build',
        type=Path,
        help="output directory for build files"
    )
    subparsers = parser.add_subparsers(
        title="Flows",
        description="""Different work flows for simulation and implementation
                       of HDL designs""",
        dest='flow'
    )
    for flow_class in FlowFactory.get_flows().values():
        flow_class.parse_args(subparsers)

    argcomplete.autocomplete(parser)
    return parser.parse_args(args=args, namespace=namespace)


def main():
    try:
        load_plugins()
        args = parse_arguments()
        levels = [logging.WARNING, logging.INFO, logging.DEBUG, logging.NOTSET]
        level = levels[min(args.verbose, len(levels)-1)]
        logging.basicConfig(level=level)
        simpl = Simplhdl(args)
        simpl.run()
    except (NotImplementedError, FileNotFoundError, CalledShError,
            ParserError, FlowError, GeneratorError) as e:
        logger.debug(traceback.format_exc())
        logger.error(e)
        return 1
    except SystemError:
        return 1


if __name__ == '__main__':
    sys.exit(main())
