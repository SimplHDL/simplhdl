from __future__ import annotations

from systemrdl import RDLCompiler
from systemrdl.component import Addrmap, Component
from systemrdl.node import RootNode


class SimplHDLRDLCompiler(RDLCompiler):
    def elaborate_root_maps(self) -> list[RootNode]:
        instantiated_map_ids: set[int] = set()

        def collect_instantiated_maps(component: Component) -> None:
            for child in component.children:
                if isinstance(child.original_def, Addrmap):
                    instantiated_map_ids.add(id(child.original_def))
                collect_instantiated_maps(child)

        for definition in self.root.comp_defs.values():
            collect_instantiated_maps(definition)

        map_names: list[str] = [
            name
            for name, definition in self.root.comp_defs.items()
            if isinstance(definition, Addrmap) and id(definition) not in instantiated_map_ids
        ]
        return [self.elaborate(name) for name in map_names]
