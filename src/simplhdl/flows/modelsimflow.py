from ..flow import FlowFactory
from .questasim.questasimflow import QuestaSimFlow


@FlowFactory.register('modelsim')
class ModelsimFlow(QuestaSimFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('modelsim', help='Modelsim HDL Simulation Flow')
        parser.add_argument(
            '-s',
            '--step',
            action='store',
            choices=['compile', 'elaborate', 'simulate'],
            default='simulate',
            help="flow step to run"
        )
        parser.add_argument(
            '-w',
            '--wave',
            action='store_true',
            help="Dump waveforms"
        )
        parser.add_argument(
            '--gui',
            action='store_true',
            help="Open project in Modelsim GUI"
        )

    def run(self, *args, **kwargs) -> None:
        print("Running Modelsim Flow")
