from argparse import Namespace
from pathlib import Path
from rich.console import Console
from rich.tree import Tree
from rich.style import Style

from simplhdl.pyedaa.project import Project
from .flow import FlowBase, FlowFactory
from .pyedaa.attributes import UsedIn
from .pyedaa.fileset import FileSet


@FlowFactory.register('info')
class Info(FlowBase):

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.console = Console()
        self.style = {
            'fileset': Style(color="color(4)", reverse=True),
            'ifile': Style(color="color(2)", reverse=False),
            'sfile': Style(color="color(3)", reverse=False),
            'file': Style(color="default", reverse=False),
        }

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
        parser.add_argument(
            '--flow',
            dest='infoflow',
            help="List project based on flow"
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

    def print_files(self) -> None:
        for file in self.project.DefaultDesign.Files():
            self.console.print(f"{file.Path}")

    def print_fileset(self, fileset: FileSet, level: Tree) -> None:
        # indent = ' '*level
        tree = level.add(f"[bold]{fileset.Name}[/bold] ({fileset.VHDLLibrary})", style=self.style['fileset'])
        for file in fileset.GetFiles():
            if "implementation" in file[UsedIn] and "simulation" not in file[UsedIn]:
                style = self.style['ifile']
            elif "simulation" in file[UsedIn] and "implementation" not in file[UsedIn]:
                style = self.style['sfile']
            else:
                style = self.style['file']

            tree.add(f"{file.Path}", style=style)
        for child_filset in fileset.FileSets.values():
            self.print_fileset(child_filset, tree)

    def print_filesets(self) -> None:
        tree = Tree('FILESETS:')
        for fileset in self.project.DefaultDesign.FileSets.values():
            self.print_fileset(fileset, tree)
        self.console.print(tree)

    def print_hooks(self) -> None:
        self.console.print('HOOKS:')
        for name, value in self.project.Hooks.items():
            self.console.print(f"  - {name}: {value}")

    def print_libraries(self) -> None:
        self.console.print('LIBRARIES:')
        for library in self.project.DefaultDesign.VHDLLibraries.values():
            self.console.print(f"  - {library.Name}")

    def print_parameters(self) -> None:
        self.console.print('PARAMETERS')
        for name, value in self.project.Parameters.items():
            self.console.print(f"  - {name}: {value}")

    def print_generics(self) -> None:
        self.console.print('GENERICS')
        for name, value in self.project.Generics.items():
            self.console.print(f"  - {name}: {value}")

    def print_defines(self) -> None:
        self.console.print('DEFINES')
        for name, value in self.project.Defines.items():
            self.console.print(f"  - {name}: {value}")

    def print_plusargs(self) -> None:
        self.console.print('PLUSARGS')
        for name, value in self.project.PlusArgs.items():
            self.console.print(f"  - {name}: {value}")

    def print_toplevels(self) -> None:
        self.console.print('TOPLEVELS')
        for top in self.project.DefaultDesign.TopLevel.split():
            self.console.print(f"  - {top}")

    def print_resources(self) -> None:
        self.console.print('RESOURCES')
        for resource in self.project.DefaultDesign.ExternalVHDLLibraries.values():
            self.console.print(f"  - {resource.Name}: {resource.Path}")

    def print_project(self) -> None:
        self.console.print('PROJECTNAME')
        self.console.print(f"  - {self.project.Name}")

    def print_part(self) -> None:
        self.console.print('PART')
        self.console.print(f"  - {self.project.Part}")

    def print_info(self) -> None:
        self.print_project()
        self.console.print()
        self.print_part()
        self.console.print()
        self.print_toplevels()
        self.console.print()
        self.print_plusargs()
        self.console.print()
        self.print_defines()
        self.console.print()
        self.print_parameters()
        self.console.print()
        self.print_generics()
        self.console.print()
        self.print_hooks()
        self.console.print()
        self.print_resources()
        self.console.print()
        self.print_libraries()
        self.console.print()
        self.print_filesets()
