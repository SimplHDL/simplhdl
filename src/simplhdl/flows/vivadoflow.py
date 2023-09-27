from ..flow import FlowFactory, FlowBase


@FlowFactory.register('vivado')
class VivadoFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('vivado', help='Vivado FPGA Build Flow')
        parser.add_argument(
            '-s',
            '--step',
            action='store',
            choices=['synthsis', 'place', 'route', 'bitstream'],
            default='bitstream',
            help="flow step to run"
        )
        parser.add_argument(
            '--gui',
            action='store_true',
            help="Open project in Vivado GUI"
        )

    def run(self, *args, **kwargs) -> None:
        print("Running Vivado Flow")
