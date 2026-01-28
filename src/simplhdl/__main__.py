import logging
import sys
import traceback

from rich.logging import RichHandler

from .cli.arguments import parse_arguments
from .project.project import ProjectError
from .plugin.flow import FlowError
from .plugin.generator import GeneratorError
from .plugin.loader import load_plugins
from .plugin.parser import ParserError
from .simplhdl import Simplhdl
from .utils import CalledShError

logger = logging.getLogger(__name__)


def main():
    try:
        load_plugins()
        args = parse_arguments()
        levels = [logging.INFO, logging.DEBUG, logging.NOTSET]
        level = levels[min(args.verbose, len(levels) - 1)]
        if level < logging.INFO:
            show_path = True
        else:
            show_path = False

        FORMAT = "[simplhdl.%(module)s] - %(message)s"
        console = RichHandler(level=level, show_time=False, rich_tracebacks=True, show_path=show_path)
        logging.basicConfig(level=5, format=FORMAT, handlers=[console])
        simpl = Simplhdl(args)
        simpl.run()
    except (
        NotImplementedError,
        FileNotFoundError,
        CalledShError,
        ParserError,
        FlowError,
        GeneratorError,
        ProjectError,
    ) as e:
        logger.debug(traceback.format_exc())
        logger.error(e)
        return 1
    except SystemError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
