import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from argparse import Namespace
from pathlib import Path

from rich.console import Console
from rich.style import Style
from rich.tree import Tree

from ..plugin.flow import FlowBase
from ..project.fileset import Fileset, FileOrder
from ..project.project import Project
from ..project.files import UsedIn


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
        self.project.validate()
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

    def graph_files(self) -> None:
        G = self.project.defaultDesign._files

        # 1. Assign layers and labels
        labels = {}
        for layer, nodes in enumerate(nx.topological_generations(G)):
            # Sort nodes within this layer by their parent's string representation
            # This ensures parent-groups are adjacent
            sorted_nodes = sorted(nodes, key=lambda n: str(getattr(n, 'parent', '')))

            for node in sorted_nodes:
                G.nodes[node]["layer"] = layer
                labels[node] = str(node.path.name)

        # 2. Dynamic Color Mapping (from previous step)
        unique_parents = sorted(
            list(set(getattr(n, 'parent', None) for n in G.nodes() if getattr(n, 'parent', None))),
            key=lambda p: str(p))
        cmap = cm.get_cmap('tab20', len(unique_parents))
        parent_to_color = {p: cmap(i) for i, p in enumerate(unique_parents)}
        node_colors = [parent_to_color.get(getattr(n, 'parent', None), (0.5, 0.5, 0.5, 1.0)) for n in G.nodes()]

        # 3. Compute Layout
        # By default, multipartite_layout respects the order of G.nodes()
        # To ensure the 'parent' grouping is reflected, we can use the 'layer' as a subset.
        pos = nx.multipartite_layout(G, subset_key="layer")

        # 4. Apply Stretching
        # Increase X-multiplier to give grouped nodes more breathing room
        pos = {n: (x * 4.0, y * 1.5) for n, (x, y) in pos.items()}

        # 5. Plot
        plt.figure(figsize=(25, 15))
        nx.draw_networkx(
            G, pos=pos, labels=labels,
            node_color=node_colors,
            node_size=3500,
            arrowsize=20,
            font_size=9
        )

        plt.margins(0.15)
        plt.savefig(self.builddir.joinpath("files.png"), format="PNG", bbox_inches="tight")
        plt.close()

    def graph_filesets(self) -> None:
        G = self.project.defaultDesign._filesets

        labels = {}
        for layer, nodes in enumerate(nx.topological_generations(G)):
            # `multipartite_layout` expects the layer as a node attribute, so add the
            # numeric layer value as a node attribute
            for node in nodes:
                G.nodes[node]["layer"] = layer
                labels[node] = str(node.name)

        # Compute the multipartite_layout using the "layer" node attribute
        pos = nx.multipartite_layout(G, subset_key="layer")
        fig, ax = plt.subplots()
        nx.draw_networkx(G, pos=pos, ax=ax, labels=labels, with_labels=False)
        ax.set_title("DAG layout in topological order")
        fig.tight_layout()
        plt.savefig(self.builddir.joinpath("filesets.png"), format="PNG")

    def print_files(self) -> None:
        for file in self.project.defaultDesign.files(order=FileOrder.COMPILE):
            self.console.print(f"{file.path}")
        self.project.validate()
        self.graph_files()

    def print_fileset(self, fileset: Fileset, level: Tree) -> None:
        # indent = ' '*level
        tree = level.add(f"[bold]{fileset.name}[/bold] ({fileset.library})", style=self.style['fileset'])
        for file in fileset.files():
            if UsedIn.IMPLEMENTATION in file.usedin and UsedIn.SIMULATION not in file.usedin:
                style = self.style['ifile']
            elif UsedIn.SIMULATION in file.usedin and UsedIn.IMPLEMENTATION not in file.usedin:
                style = self.style['sfile']
            else:
                style = self.style['file']

            tree.add(f"{file.path}", style=style)
        for child_filset in fileset.children:
            self.print_fileset(child_filset, tree)

    def print_filesets(self) -> None:
        tree = Tree('FILESETS:')
        for fileset in self.project.defaultDesign.roots:
            self.print_fileset(fileset, tree)
            break
        self.console.print(tree)
        self.graph_files()
        self.graph_filesets()

    def print_hooks(self) -> None:
        self.console.print('HOOKS:')
        for name, value in self.project.hooks.items():
            self.console.print(f"  - {name}: {value}")

    def print_libraries(self) -> None:
        self.console.print('LIBRARIES:')
        for library in self.project.defaultDesign.libraries:
            self.console.print(f"  - {library.name}")

    def print_parameters(self) -> None:
        self.console.print('PARAMETERS')
        for name, value in self.project.parameters.items():
            self.console.print(f"  - {name}: {value}")

    def print_generics(self) -> None:
        self.console.print('GENERICS')
        for name, value in self.project.generics.items():
            self.console.print(f"  - {name}: {value}")

    def print_defines(self) -> None:
        self.console.print('DEFINES')
        for name, value in self.project.defines.items():
            self.console.print(f"  - {name}: {value}")

    def print_plusargs(self) -> None:
        self.console.print('PLUSARGS')
        for name, value in self.project.plusargs.items():
            self.console.print(f"  - {name}: {value}")

    def print_toplevels(self) -> None:
        self.console.print('TOPLEVELS')
        for top in self.project.defaultDesign.toplevels:
            self.console.print(f"  - {top}")

    def print_resources(self) -> None:
        self.console.print('RESOURCES')
        for resource in [lib for lib in self.project.defaultDesign.libraries if lib.external is True]:
            self.console.print(f"  - {resource.name}: {resource.path}")

    def print_project(self) -> None:
        self.console.print('PROJECTNAME')
        self.console.print(f"  - {self.project.name}")

    def print_part(self) -> None:
        self.console.print('PART')
        self.console.print(f"  - {self.project.part}")

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
