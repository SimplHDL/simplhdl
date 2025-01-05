from pprint import pprint
from simplhdl.simplhdl import Simplhdl
from simplhdl.flow import FlowBase, FlowFactory, FlowError
from simplhdl.utils import chdir


@FlowFactory.register('run')
class Run(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('run', help='Run project targets')
        parser.add_argument(
            '-l',
            '--list',
            nargs='?',
            const='text',
            choices=['text', 'json'],
            help="List project targets"
        )
        parser.add_argument(
            '-t',
            '--target',
            help="Project target to run"
        )

    def run(self) -> None:
        if self.args.list:
            self._show_list(self.args.list)
        else:
            self._run_target()

    def _show_list(self, format) -> None:
        if format == 'json':
            targets = list(self.project._targets.keys())
            pprint(targets)
        else:
            print("TARGETS:")
            for target in self.project._targets.keys():
                print(f"  - {target}")

    def _run_target(self) -> None:
        if self.args.target:
            target = self.project.GetTarget(self.args.target)
        else:
            target = self.project.DefaultTarget
        if target.args.flow == 'run':
            raise FlowError("Target flow can't be 'run'")
        with chdir(target.cwd):
            simplhdl = Simplhdl(target.args)
            simplhdl.run()
