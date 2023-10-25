from argparse import Namespace
from pathlib import Path

from .flow import FlowBase, FlowFactory
from .pyedaa.project import Project
from .pyedaa.fileset import FileSet


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
        parser.add_argument(
            '--hooks',
            action='store_true',
            help="List hooks in project"
        )

    def run(self) -> None:
        if self.args.files:
            self.print_files()
        elif self.args.filesets:
            self.print_filesets()
        elif self.args.libraries:
            self.print_libraries()
        elif self.args.hooks:
            self.print_hooks()
        else:
            self.print_info()

    def print_files(self):
        print('FILES:')
        for file in self.project.DefaultDesign.Files():
            print(f"{file.Path}")

    def print_fileset(self, fileset: FileSet, level: int) -> None:
        indent = ' '*level
        print(f"{indent}{fileset.Name}")
        for file in fileset.GetFiles():
            print(f"{indent}    - {file.Path}")
        for child_filset in fileset.FileSets.values():
            self.print_fileset(child_filset, level+2)

    def print_filesets(self):
        print('FILESETS:')
        for fileset in self.project.DefaultDesign.FileSets.values():
            self.print_fileset(fileset, level=0)

    def print_hooks(self):
        print('HOOKS:')
        for name, value in self.project.Hooks.items():
            print(f"  - {name}: {value}")

    def print_libraries(self):
        print('LIBRARIES:')
        for library in self.project.DefaultDesign.VHDLLibraries.values():
            print(f"  - {library.Name}")

    def print_parameters(self):
        print('PARAMETERS')
        for name, value in self.project.Parameters.items():
            print(f"  - {name}: {value}")

    def print_generics(self):
        print('GENERICS')
        for name, value in self.project.Generics.items():
            print(f"  - {name}: {value}")

    def print_defines(self):
        print('DEFINES')
        for name, value in self.project.Defines.items():
            print(f"  - {name}: {value}")

    def print_plusargs(self):
        print('PLUSARGS')
        for name, value in self.project.PlusArgs.items():
            print(f"  - {name}: {value}")

    def print_info(self):
        self.print_plusargs()
        print()
        self.print_defines()
        print()
        self.print_parameters()
        print()
        self.print_generics()
        print()
        self.print_hooks()
        print()
        self.print_libraries()
        print()
        self.print_filesets()
