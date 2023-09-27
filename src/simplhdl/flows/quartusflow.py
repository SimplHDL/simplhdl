from ..flow import FlowFactory, FlowBase


@FlowFactory.register('quartus')
class QuartusFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('quartus', help='Quartus FPGA Build Flow')
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
            help="Open project in Quartus GUI"
        )

    def run(self, *args, **kwargs) -> None:
        print("Running Quartus Flow")

#            options = {
#                'quartus': {'family': "Agilex", 'device': "AGFB014R24A2E2V"},
#            }
