from argparse import Namespace
from pathlib import Path

from .flow import FlowBase, FlowFactory
from .project import Project


@FlowFactory.register('info')
class Info(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('info', help='Project infomations')
        parser.add_argument(
            '--files',
            action='store_true',
            help="List files in project"
        )
        parser.add_argument(
            '--filesets',
            action='store_true',
            help="List files sets in project"
        )
        parser.add_argument(
            '--libraries',
            action='store_true',
            help="List libraries in project"
        )

    def run(self, args: Namespace, project: Project, builddir: Path) -> None:
        self.args = args
        self.project = project
        self.builddir = builddir

        if args.files:
            self.print_files()
        if args.filesets:
            self.print_filesets()
        if args.libraries:
            self.print_libraries()

    def print_files(self):
        for file in self.project.DefaultDesign.Files():
            print(file.Path)

    def print_filesets(self):
        indent = 0
        for fileset in self.project.DefaultDesign.FileSets.values():
            print(' '*indent + fileset.Name)
            for file in fileset.Files():
                indent = 2
                print(' '*indent + str(file.Path))

    def print_libraries(self):
        for library in self.project.DefaultDesign.VHDLLibraries.values():
            print(library.Name)
        print(self.project.DefaultDesign.DefaultFileSet.VHDLLibrary)
