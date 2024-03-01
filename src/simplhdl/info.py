from .flow import FlowBase, FlowFactory
from .pyedaa.attributes import UsedIn
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
        print('FILES:')
        for file in self.project.DefaultDesign.Files():
            print(f"{file.Path}")

    def print_fileset(self, fileset: FileSet, level: int) -> None:
        indent = ' '*level
        print(f"{indent}{fileset.Name}")
        for file in fileset.GetFiles():
            print(f"{indent}    - {file.Path} {file[UsedIn]}")
        for child_filset in fileset.FileSets.values():
            self.print_fileset(child_filset, level+2)

    def print_filesets(self) -> None:
        print('FILESETS:')
        for fileset in self.project.DefaultDesign.FileSets.values():
            self.print_fileset(fileset, level=0)

    def print_hooks(self) -> None:
        print('HOOKS:')
        for name, value in self.project.Hooks.items():
            print(f"  - {name}: {value}")

    def print_libraries(self) -> None:
        print('LIBRARIES:')
        for library in self.project.DefaultDesign.VHDLLibraries.values():
            print(f"  - {library.Name}")

    def print_parameters(self) -> None:
        print('PARAMETERS')
        for name, value in self.project.Parameters.items():
            print(f"  - {name}: {value}")

    def print_generics(self) -> None:
        print('GENERICS')
        for name, value in self.project.Generics.items():
            print(f"  - {name}: {value}")

    def print_defines(self) -> None:
        print('DEFINES')
        for name, value in self.project.Defines.items():
            print(f"  - {name}: {value}")

    def print_plusargs(self) -> None:
        print('PLUSARGS')
        for name, value in self.project.PlusArgs.items():
            print(f"  - {name}: {value}")

    def print_toplevels(self) -> None:
        print('TOPLEVELS')
        for top in self.project.DefaultDesign.TopLevel.split():
            print(f"  - {top}")

    def print_resources(self) -> None:
        print('RESOURCES')
        for resource in self.project.DefaultDesign.ExternalVHDLLibraries.values():
            print(f"  - {resource.Name}: {resource.Path}")

    def print_project(self) -> None:
        print('PROJECTNAME')
        print(f"  - {self.project.Name}")

    def print_part(self) -> None:
        print('PART')
        print(f"  - {self.project.Part}")

    def print_info(self) -> None:
        self.print_project()
        print()
        self.print_part()
        print()
        self.print_toplevels()
        print()
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
        self.print_resources()
        print()
        self.print_libraries()
        print()
        self.print_filesets()
