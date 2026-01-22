import logging
import os

import jinja2

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from pathlib import Path
from typing import List

from peakrdl_html import HTMLExporter
from peakrdl_pyuvm.exporter import PyUVMExporter
from peakrdl_regblock.cpuif.axi4lite import AXI4Lite_Cpuif_flattened
from peakrdl_regblock.exporter import RegblockExporter
from peakrdl_regblock.udps import ALL_UDPS
from systemrdl import RDLCompileError, RDLCompiler, RDLListener, RDLWalker
from systemrdl.node import AddrmapNode
from systemrdl.rdltypes import AccessType, OnReadType, OnWriteType

from simplhdl import FileOrder
from simplhdl.plugin import FlowBase, FlowCategory, GeneratorBase
from simplhdl.project.files import (
    CocotbPythonFile,
    SystemRdlFile,
    SystemVerilogFile,
    VerilogFile,
    VhdlFile,
)

logger = logging.getLogger(__name__)

seennodetypes: List[AddrmapNode] = []
leafnodetypes: List[AddrmapNode] = []
hierachynodetypes: List[AddrmapNode] = []
leafnodes: List[AddrmapNode] = []
hierachynodes: List[AddrmapNode] = []
nodes: List[AddrmapNode] = []


class Environment(jinja2.Environment):
    def find_template(self, name):
        list = [i for i in self.list_templates() if i.startswith(name)]
        if len(list) == 0:
            raise jinja2.TemplateNotFound(name)
        if len(list) > 1:
            logger.warning(f"Multiple templates found ({list}) for {name}")
        return self.get_template(list[0])


class Listener(RDLListener):
    def exit_Addrmap(self, node: AddrmapNode):
        nodes.append(node)
        if is_leaf(node):
            leafnodes.append(node)
        else:
            hierachynodes.append(node)
        seen = [n for n in seennodetypes if n.type_name == node.type_name]
        if not seen:
            seennodetypes.append(node)
            if is_leaf(node):
                leafnodetypes.append(node)
            else:
                hierachynodetypes.append(node)


def get_template_dirs() -> List[Path]:
    string = os.getenv('SIMPLHDL_SYSTEMRDL_TEMPLATES')
    if string:
        templates = {Path(p).resolve() for p in string.split(':')}
        for t in templates:
            if not t.is_dir():
                logger.error(f"Directory {t} does not exist")
                raise SystemError
    else:
        logger.error("SIMPLHDL_SYSTEMRDL_TEMPLATES is not set, no templates found")
        raise SystemError
    return list(templates)


def get_reg_access(reg) -> str:
    if reg.has_sw_readable and reg.has_sw_writable:
        return "RW"
    elif reg.has_sw_writable:
        return "WO"
    elif reg.has_sw_readable:
        return "RO"
    else:
        return "RW"


def get_field_access(field) -> str:  # noqa: C901
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
    if AddrmapNode not in [type(c) for c in node.children()]:
        return True
    else:
        return False


def mask(node):
    m = ~(node.size - 1) & 0xFFFFFFFF
    return m


class PeakRdlGenerator(GeneratorBase):

    def render_template(self, template: jinja2.Template, node, outputdir) -> Path:
        if not template.filename.endswith('.j2'):
            return
        context = template.render(node=node)
        outputdir.mkdir(parents=True, exist_ok=True)
        outputfile: Path = outputdir.joinpath(f'{node.type_name}__{Path(template.filename).name[:-3]}').resolve()
        with outputfile.open('w') as f:
            f.write(context)
        rdlfile = self.project.defaultDesign.get_file(node.inst.def_src_ref.path)
        fileset = rdlfile.parent
        if outputfile.suffix == '.sv':
            fileset.insert_file_after(rdlfile, SystemVerilogFile(outputfile))
        if outputfile.suffix == '.v':
            fileset.insert_file_after(rdlfile, VerilogFile(outputfile))
        if outputfile.suffix == '.vhd':
            fileset.insert_file_after(rdlfile, VhdlFile(outputfile))

    def peakrdl_regblock(self, node, outputdir, config) -> None:
        RegblockExporter().export(
            node=node,
            output_dir=str(outputdir.resolve()),
            cpuif_cls=AXI4Lite_Cpuif_flattened,
            module_name=config.get('module_name', f'{node.type_name}_addrmap'),
            package_name=config.get('package_name', f'{node.type_name}_pkg'),
            address_width=config.get('address_width', 32),
            default_reset_activelow=config.get('default_reset_activelow', True),
            err_if_bad_addr=config.get('err_if_bad_addr', False),
            err_if_bad_rw=config.get('err_if_bad_rw', False)
        )
        modulefile: Path = outputdir.joinpath(f'{node.type_name}_pkg.sv').resolve()
        packetfile: Path = outputdir.joinpath(f'{node.type_name}_addrmap.sv').resolve()
        rdlfile = self.project.defaultDesign.get_file(node.inst.def_src_ref.path)
        fileset = rdlfile.parent
        fileset.insert_file_after(rdlfile, SystemVerilogFile(modulefile))
        fileset.insert_file_after(rdlfile, SystemVerilogFile(packetfile))

    def run(self, flow: FlowBase):  # noqa: C901
        rdlfiles = self.project.defaultDesign.files(type=SystemRdlFile, order=FileOrder.COMPILE)
        output_dir = self.builddir.joinpath('systemrdl')
        config = dict()
        if os.getenv('SIMPLHDL_CONFIG'):
            tomlfile = Path(os.getenv('SIMPLHDL_CONFIG'))
            try:
                with tomlfile.open('rb') as f:
                    config = tomllib.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"SimplHDL config file set by environment 'SIMPLHDL_CONFIG={tomlfile}' does not exist"
                )

        pearkdl_config = config.get('peakrdl', {})
        html_config = pearkdl_config.get('html', {})
        regblock_config = pearkdl_config.get('regblock', {})

        if not rdlfiles:
            return

        rdlc = RDLCompiler()

        for udp in ALL_UDPS:
            rdlc.register_udp(udp)

        try:
            for rdlfile in rdlfiles:
                rdlc.compile_file(rdlfile.path, defines=self.project.defines)
                root = rdlc.elaborate()
        except RDLCompileError as e:
            logger.error(str(e))
            raise SystemError

        walker = RDLWalker()
        walker.walk(root, Listener())

        templatedirs = get_template_dirs()
        for templatedir in templatedirs:
            logger.info(f"Generate from template {templatedir}")
            sub_dir = output_dir.joinpath(templatedir.name)

            env = Environment(
                loader=jinja2.FileSystemLoader(templatedir),
                trim_blocks=True)
            env.globals['hex'] = hex
            env.globals['len'] = len
            env.globals['get_field_access'] = get_field_access
            env.globals['get_reg_access'] = get_reg_access
            env.globals['nodes'] = nodes
            env.globals['leafnodes'] = leafnodes
            env.globals['hierachynodes'] = hierachynodes
            env.globals['is_leaf'] = is_leaf
            env.globals['mask'] = mask
            template = env.find_template('registermap')
            for node in leafnodetypes:
                self.render_template(template=template, node=node, outputdir=sub_dir)

            template = env.find_template('hierachymap')
            for node in hierachynodetypes:
                self.render_template(template=template, node=node, outputdir=sub_dir)

        # NOTE: generate PeakRDL Register Block
        logger.info("Generate PeakRDL Register Block")
        for node in leafnodetypes:
            self.peakrdl_regblock(node=node, outputdir=output_dir.joinpath('peakrdl-regblock'), config=regblock_config)

        # NOTE: generate PeakRDL PyUVM Register Model if simulation and Cocotb is present, i.e. has cocotb files
        if flow.category == FlowCategory.SIMULATION and list(self.project.defaultDesign.files(CocotbPythonFile)):
            logger.info("Generate PeakRDL PyUVM Register Model")
            output = output_dir.joinpath('peakrdl-pyuvm', 'ralmodel.py')
            output.parent.mkdir(parents=True, exist_ok=True)
            PyUVMExporter().export(root, str(output))
            fileset = rdlfiles[-1].parent
            fileset.insert_file_after(rdlfile, CocotbPythonFile(output))

        logger.info("Generate HTML Documentation")
        HTMLExporter().export(
            root,
            output_dir.joinpath('peakrdl-docs'),
            skip_not_present=html_config.get('skip_not_present', False),
        )
