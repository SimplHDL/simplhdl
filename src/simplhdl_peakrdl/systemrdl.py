from __future__ import annotations

import logging
import os

import jinja2

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from pathlib import Path

from peakrdl_html import HTMLExporter
from peakrdl_pyuvm.exporter import PyUVMExporter
from peakrdl_regblock.cpuif.apb3 import APB3_Cpuif, APB3_Cpuif_flattened
from peakrdl_regblock.cpuif.apb4 import APB4_Cpuif, APB4_Cpuif_flattened
from peakrdl_regblock.cpuif.avalon import Avalon_Cpuif, Avalon_Cpuif_flattened
from peakrdl_regblock.cpuif.axi4lite import AXI4Lite_Cpuif, AXI4Lite_Cpuif_flattened
from peakrdl_regblock.cpuif.obi import OBI_Cpuif, OBI_Cpuif_flattened
from peakrdl_regblock.cpuif.passthrough import PassthroughCpuif
from peakrdl_regblock.exporter import RegblockExporter
from peakrdl_regblock.udps import ALL_UDPS
from systemrdl import RDLCompileError, RDLListener, RDLWalker
from systemrdl.node import AddrmapNode, MemNode, RegNode, RootNode
from systemrdl.rdltypes import AccessType, OnReadType, OnWriteType

from simplhdl.plugin import FlowBase, FlowCategory, GeneratorBase
from simplhdl.project.files import (
    CocotbPythonFile,
    SystemRdlFile,
    SystemVerilogFile,
    VerilogFile,
    VhdlFile,
)

from .compiler import SimplHDLRDLCompiler

logger = logging.getLogger(__name__)

CPU_INTERFACES = {
    "passthrough": PassthroughCpuif,
    "apb3": APB3_Cpuif,
    "apb3-flat": APB3_Cpuif_flattened,
    "apb4": APB4_Cpuif,
    "apb4-flat": APB4_Cpuif_flattened,
    "axi4-lite": AXI4Lite_Cpuif,
    "axi4-lite-flat": AXI4Lite_Cpuif_flattened,
    "avalon-mm": Avalon_Cpuif,
    "avalon-mm-flat": Avalon_Cpuif_flattened,
    "obi": OBI_Cpuif,
    "obi-flat": OBI_Cpuif_flattened,
}
RETIME_EXTERNAL_TYPES = ("reg", "regfile", "mem", "addrmap")
DEFAULT_RESET_SETTINGS = {
    "rst": (False, False),
    "rst_n": (True, False),
    "arst": (False, True),
    "arst_n": (True, True),
}


def _get_default_reset_settings(reset: str) -> tuple[bool, bool]:
    try:
        return DEFAULT_RESET_SETTINGS[reset]
    except KeyError as exc:
        raise ValueError(f"Unsupported default reset: {reset}") from exc


def _get_retime_external_settings(items: object) -> dict[str, bool]:
    if not isinstance(items, list):
        raise TypeError(f"retime_external must be an array {[*RETIME_EXTERNAL_TYPES, 'all']}")

    valid_items = (*RETIME_EXTERNAL_TYPES, "all")
    settings = {f"retime_external_{item}": False for item in RETIME_EXTERNAL_TYPES}
    for item in items:
        if item not in valid_items:
            raise ValueError(f"Unsupported retime_external item: {item}, must be one of {list(valid_items)}")
        if item == "all":
            for setting in settings:
                settings[setting] = True
        else:
            settings[f"retime_external_{item}"] = True
    return settings


def unique_nodes_by_type(nodes: list[AddrmapNode]) -> list[AddrmapNode]:
    """Return nodes de-duplicated by type_name while preserving first-seen order."""
    seen: set[str] = set()
    unique: list[AddrmapNode] = []
    for node in nodes:
        if node.type_name in seen:
            continue
        seen.add(node.type_name)
        unique.append(node)
    return unique


class Environment(jinja2.Environment):
    def find_template(self, name):
        matches = [template_name for template_name in self.list_templates() if template_name.startswith(name)]
        if not matches:
            raise jinja2.TemplateNotFound(name)
        if len(matches) > 1:
            logger.warning(f"Multiple templates found ({matches}) for {name}")
        return self.get_template(matches[0])


class AddrmapCollector(RDLListener):
    def __init__(self) -> None:
        self.nodes: list[AddrmapNode] = []
        self.leafnodes: list[AddrmapNode] = []
        self.hierachynodes: list[AddrmapNode] = []

    def exit_Addrmap(self, node: AddrmapNode):
        self.nodes.append(node)
        if is_leaf(node):
            self.leafnodes.append(node)
        else:
            self.hierachynodes.append(node)


class AccessWidthExtractor(RDLListener):
    def __init__(self):
        self.bus_datawidth = 0

    def enter_Reg(self, node: RegNode):
        # 'accesswidth' reflects the actual bus transfer width
        # (automatically defaults to 'regwidth' if not specified in RDL)
        accesswidth = node.get_property("accesswidth")
        self.bus_datawidth = max(self.bus_datawidth, accesswidth)

    def enter_Mem(self, node: MemNode):
        memwidth = node.get_property("memwidth")
        self.bus_datawidth = max(self.bus_datawidth, memwidth)


def get_template_dirs() -> list[Path]:
    string = os.getenv("SIMPLHDL_SYSTEMRDL_TEMPLATES")
    if string:
        templates = {Path(p).resolve() for p in string.split(":")}
        for t in templates:
            if not t.is_dir():
                logger.error(f"Directory {t} does not exist")
                raise SystemError
        return list(templates)
    else:
        logger.debug("SIMPLHDL_SYSTEMRDL_TEMPLATES is not set, no templates found")
        return []


def get_max_access_width(node: AddrmapNode) -> int:
    extractor = AccessWidthExtractor()
    RDLWalker(unroll=True).walk(node, extractor)
    return extractor.bus_datawidth


def get_max_addr_width(node: AddrmapNode) -> int:
    return max(1, (node.size - 1).bit_length())


def get_reg_access(reg) -> str:
    if reg.has_sw_readable and reg.has_sw_writable:
        return "RW"
    elif reg.has_sw_writable:
        return "WO"
    elif reg.has_sw_readable:
        return "RO"
    else:
        return "RW"


def get_field_access(field) -> str:
    """
    Get field's UVM access string
    """
    sw = field.get_property("sw")
    onread = field.get_property("onread")
    onwrite = field.get_property("onwrite")

    if sw == AccessType.rw:
        if (onwrite is None) and (onread is None):
            return "RW"
        elif (onread == OnReadType.rclr) and (onwrite == OnWriteType.woset):
            return "W1SRC"
        elif (onread == OnReadType.rclr) and (onwrite == OnWriteType.wzs):
            return "W0SRC"
        elif (onread == OnReadType.rclr) and (onwrite == OnWriteType.wset):
            return "WSRC"
        elif (onread == OnReadType.rset) and (onwrite == OnWriteType.woclr):
            return "W1CRS"
        elif (onread == OnReadType.rset) and (onwrite == OnWriteType.wzc):
            return "W0CRS"
        elif (onread == OnReadType.rset) and (onwrite == OnWriteType.wclr):
            return "WCRS"
        elif onwrite == OnWriteType.woclr:
            return "W1C"
        elif onwrite == OnWriteType.woset:
            return "W1S"
        elif onwrite == OnWriteType.wot:
            return "W1T"
        elif onwrite == OnWriteType.wzc:
            return "W0C"
        elif onwrite == OnWriteType.wzs:
            return "W0S"
        elif onwrite == OnWriteType.wzt:
            return "W0T"
        elif onwrite == OnWriteType.wclr:
            return "WC"
        elif onwrite == OnWriteType.wset:
            return "WS"
        elif onread == OnReadType.rclr:
            return "WRC"
        elif onread == OnReadType.rset:
            return "WRS"
        else:
            return "RW"

    elif sw == AccessType.r:
        if onread is None:
            return "RO"
        elif onread == OnReadType.rclr:
            return "RC"
        elif onread == OnReadType.rset:
            return "RS"
        else:
            return "RO"

    elif sw == AccessType.w:
        if onwrite is None:
            return "WO"
        elif onwrite == OnWriteType.wclr:
            return "WOC"
        elif onwrite == OnWriteType.wset:
            return "WOS"
        else:
            return "WO"

    elif sw == AccessType.rw1:
        return "W1"

    elif sw == AccessType.w1:
        return "WO1"

    else:
        return "NOACCESS"


def is_leaf(node):
    """
    Check if node is leaf, meaning it has no children address maps
    """
    return not any(isinstance(child, AddrmapNode) for child in node.children())


def mask(node):
    m = ~(node.size - 1) & 0xFFFFFFFF
    return m


class PeakRdlGenerator(GeneratorBase):
    supported_file_types = (SystemRdlFile,)

    def render_template(self, template: jinja2.Template, node: AddrmapNode, outputdir: Path) -> Path | None:
        if not template.filename.endswith(".j2"):
            return None
        context = template.render(node=node)
        outputdir.mkdir(parents=True, exist_ok=True)
        outputfile: Path = outputdir.joinpath(f"{node.type_name}__{Path(template.filename).name[:-3]}").resolve()
        with outputfile.open("w") as f:
            f.write(context)
        rdlfile = self.project.defaultDesign.get_file(node.inst.def_src_ref.path)
        fileset = rdlfile.parent
        if outputfile.suffix == ".sv":
            fileset.insert_file_after(rdlfile, SystemVerilogFile(outputfile))
        if outputfile.suffix == ".v":
            fileset.insert_file_after(rdlfile, VerilogFile(outputfile))
        if outputfile.suffix == ".vhd":
            fileset.insert_file_after(rdlfile, VhdlFile(outputfile))
        return outputfile

    def peakrdl_regblock(self, node, outputdir, config) -> None:
        cpuif_name = config.get("cpuif", "apb3")
        try:
            cpuif_cls = CPU_INTERFACES[cpuif_name]
        except KeyError as exc:
            raise ValueError(f"Unsupported CPU interface: {cpuif_name}, must be one of {list(CPU_INTERFACES)}") from exc

        default_reset_activelow, default_reset_async = _get_default_reset_settings(config.get("default_reset", "rst"))

        module_name = config.get("module_name", f"{node.type_name}").replace("%", node.type_name)
        package_name = config.get("package_name", f"{node.type_name}_pkg").replace("%", node.type_name)

        type_style = config.get("type_style", "lexical")
        if type_style == "lexical":
            reuse_hwif_typedefs = True
        elif type_style == "hier":
            reuse_hwif_typedefs = False
        else:
            raise ValueError(f"Unsupported type style: {type_style}")

        retime_external_settings = _get_retime_external_settings(config.get("retime_external", []))

        # NOTE: Workaround for SystemRDL/PeakRDL-regblock#221: the exporter derives
        # the top-level HWIF typedef names from the instance name instead of the
        # addrmap type name. Temporarily rename the instance to its type name while
        # exporting. Note that Node.__deepcopy__ shares `inst` by reference, so a
        # copied node would still mutate the elaborated tree; save/restore instead.
        # Remove once SystemRDL/PeakRDL-regblock#222 is released.
        orig_inst_name = node.inst.inst_name
        node.inst.inst_name = node.type_name
        try:
            RegblockExporter().export(
                node=node,
                output_dir=str(outputdir.resolve()),
                cpuif_cls=cpuif_cls,
                module_name=module_name,
                package_name=package_name,
                reuse_hwif_typedefs=reuse_hwif_typedefs,
                retime_read_fanin=config.get("retime_read_fanin", False),
                retime_read_response=config.get("retime_read_response", False),
                **retime_external_settings,
                generate_hwif_report=config.get("generate_hwif_report", False),
                address_width=config.get("address_width", None),
                default_reset_activelow=default_reset_activelow,
                default_reset_async=default_reset_async,
                err_if_bad_addr=config.get("err_if_bad_addr", False),
                err_if_bad_rw=config.get("err_if_bad_rw", False),
            )
        finally:
            node.inst.inst_name = orig_inst_name
        modulefile: Path = outputdir.joinpath(f"{module_name}.sv").resolve()
        packetfile: Path = outputdir.joinpath(f"{package_name}.sv").resolve()
        rdlfile = self.project.defaultDesign.get_file(node.inst.def_src_ref.path)
        fileset = rdlfile.parent
        fileset.insert_file_after(rdlfile, SystemVerilogFile(packetfile))
        fileset.insert_file_after(rdlfile, SystemVerilogFile(modulefile))

    def _load_config(self) -> dict:
        config: dict = {}
        config_path = os.getenv("SIMPLHDL_CONFIG")
        if config_path:
            tomlfile = Path(config_path)
            try:
                with tomlfile.open("rb") as f:
                    config = tomllib.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"SimplHDL config file set by environment 'SIMPLHDL_CONFIG={tomlfile}' does not exist"
                )
        return config

    def _compile_roots(self, rdlfiles) -> list[RootNode]:
        rdlc = SimplHDLRDLCompiler()
        for udp in ALL_UDPS:
            rdlc.register_udp(udp)
        try:
            for rdlfile in rdlfiles:
                rdlc.compile_file(rdlfile.path, defines=self.project.defines)
                roots = rdlc.elaborate_root_maps()
        except RDLCompileError as e:
            logger.error(str(e))
            raise SystemError
        return roots

    def _collect_root_nodes(
        self, roots: list[RootNode]
    ) -> tuple[list[tuple[RootNode, AddrmapCollector]], list[AddrmapNode]]:
        root_collectors: list[tuple[RootNode, AddrmapCollector]] = []
        walker = RDLWalker()
        for root in roots:
            collector = AddrmapCollector()
            walker.walk(root, collector)
            root_collectors.append((root, collector))

        unique_leaf_nodes = unique_nodes_by_type(
            [node for _, collector in root_collectors for node in collector.leafnodes]
        )
        return root_collectors, unique_leaf_nodes

    def _generate_hierarchy_templates(
        self,
        root_collectors: list[tuple[RootNode, AddrmapCollector]],
        output_dir: Path,
        config: dict,
    ) -> None:
        for template_dir in get_template_dirs():
            logger.info(f"Generate from template {template_dir}")
            sub_dir = output_dir.joinpath(template_dir.name)

            env = Environment(loader=jinja2.FileSystemLoader(template_dir), trim_blocks=True)
            env.globals["hex"] = hex
            env.globals["len"] = len
            env.globals["get_field_access"] = get_field_access
            env.globals["get_reg_access"] = get_reg_access
            env.globals["is_leaf"] = is_leaf
            env.globals["mask"] = mask

            template = env.find_template("hierachymap")
            for root, collector in root_collectors:
                env.globals["nodes"] = collector.nodes
                env.globals["leafnodes"] = collector.leafnodes
                env.globals["hierachynodes"] = collector.hierachynodes
                env.globals["max_access_width"] = get_max_access_width(root.top)
                env.globals["max_addr_width"] = max(get_max_addr_width(root.top), config.get("address_width", 1))
                self.render_template(template=template, node=root.top, outputdir=sub_dir)

    def _generate_regblocks(self, leaf_nodes: list[AddrmapNode], output_dir: Path, config: dict) -> None:
        if not config.get("enable", True):
            return

        logger.info("Generate PeakRDL Register Block")
        for node in leaf_nodes:
            self.peakrdl_regblock(
                node=node,
                outputdir=output_dir.joinpath("peakrdl-regblock"),
                config=config,
            )

    def _generate_pyuvm(
        self,
        flow: FlowBase,
        roots: list[RootNode],
        rdlfiles,
        output_dir: Path,
        config: dict,
    ) -> None:
        if not config.get("enable", True) or flow.category != FlowCategory.SIMULATION:
            return
        if not list(self.project.defaultDesign.files(CocotbPythonFile)):
            return

        logger.info("Generate PeakRDL PyUVM Register Model")
        output = output_dir.joinpath("peakrdl-pyuvm", "ralmodel.py")
        output.parent.mkdir(parents=True, exist_ok=True)
        type_style = config.get("type_style", "lexical")
        if type_style == "lexical":
            reuse_class_definitions = True
        elif type_style == "hier":
            reuse_class_definitions = False
        else:
            raise ValueError(f"Unsupported type style: {type_style}")

        rdlfile = rdlfiles[-1]
        fileset = rdlfile.parent
        for root in roots:
            PyUVMExporter().export(
                node=root,
                path=str(output),
                export_as_package=config.get("export_as_package", True),
                reuse_class_definitions=reuse_class_definitions,
                use_uvm_factory=config.get("use_uvm_factory", False),
            )
            fileset.insert_file_after(rdlfile, CocotbPythonFile(output))

    def _generate_html(self, roots: list[RootNode], output_dir: Path, config: dict) -> None:
        if not config.get("enable", True):
            return

        logger.info("Generate HTML Documentation")
        HTMLExporter().export(
            roots,
            output_dir.joinpath("peakrdl-docs"),
            skip_not_present=config.get("skip_not_present", False),
        )

    def run(self, flow: FlowBase):
        rdlfiles = self.get_files(flow)
        output_dir = self.builddir.joinpath("systemrdl")
        config = self._load_config()

        peakrdl_config = config.get("peakrdl", {})
        if not rdlfiles:
            return

        roots = self._compile_roots(rdlfiles)
        root_collectors, leaf_nodes = self._collect_root_nodes(roots)
        self._generate_hierarchy_templates(root_collectors, output_dir, peakrdl_config.get("regblock", {}))
        self._generate_regblocks(leaf_nodes, output_dir, peakrdl_config.get("regblock", {}))
        self._generate_pyuvm(flow, roots, rdlfiles, output_dir, peakrdl_config.get("pyuvm", {}))
        self._generate_html(roots, output_dir, peakrdl_config.get("html", {}))
