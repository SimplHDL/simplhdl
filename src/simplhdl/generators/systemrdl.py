import os
import logging
import jinja2

from typing import List
from pathlib import Path
from systemrdl import RDLCompiler, RDLCompileError, RDLListener, RDLWalker
from systemrdl.node import AddrmapNode
from systemrdl.rdltypes import AccessType, OnReadType, OnWriteType
from peakrdl_html import HTMLExporter

from ..generator import GeneratorFactory, GeneratorBase
from ..pyedaa import SystemRDLSourceFile, SystemVerilogSourceFile, VerilogSourceFile
from ..flow import FlowBase


logger = logging.getLogger(__name__)

seennodes: List[AddrmapNode] = []
addrmapnodes: List[AddrmapNode] = []
hierachymapnodes: List[AddrmapNode] = []


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
        seen = [n for n in seennodes if n.type_name == node.type_name]
        if not seen:
            seennodes.append(node)
            if AddrmapNode not in [type(c) for c in node.children()]:
                addrmapnodes.append(node)
            else:
                hierachymapnodes.append(node)


def get_template_dirs() -> List[Path]:
    string = os.getenv('SIMPLHDL_SYSTEMRDL_TEMPLATES')
    if string:
        templates = [Path(p) for p in string.split(':')]
        for t in templates:
            if not t.is_dir():
                logger.error(f"Directory {t} does not exist")
                raise SystemError
    else:
        logger.error("SIMPLHDL_SYSTEMRDL_TEMPLATES is not set, no templates found")
        raise SystemError
    return templates


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


@GeneratorFactory.register('SystemRDL')
class SystemRDL(GeneratorBase):

    def render_template(self, template, node, outputdir) -> Path:
        context = template.render(node=node)
        outputdir.mkdir(parents=True, exist_ok=True)
        outputfile: Path = outputdir.joinpath(f'{node.type_name}__{Path(template.filename).name[:-3]}').absolute()
        with outputfile.open('w') as f:
            f.write(context)
        rdlfile = self.project.DefaultDesign.GetFile(node.inst.def_src_ref.path)
        fileset = rdlfile.FileSet
        if outputfile.suffix == '.sv':
            fileset.InsertFileAfter(rdlfile, SystemVerilogSourceFile(outputfile))
        if outputfile.suffix == '.v':
            fileset.InsertFileAfter(rdlfile, VerilogSourceFile(outputfile))

    def run(self, flow: FlowBase):
        rdlfiles = list(self.project.DefaultDesign.DefaultFileSet.Files(fileType=SystemRDLSourceFile))
        output_dir = self.builddir.joinpath('systemrdl')

        if not rdlfiles:
            return

        rdlc = RDLCompiler()
        try:
            for rdlfile in rdlfiles:
                rdlc.compile_file(rdlfile.Path, defines=self.project.Defines)
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
            env.globals['get_field_access'] = get_field_access
            env.globals['get_reg_access'] = get_reg_access
            template = env.find_template('registermap')
            for node in addrmapnodes:
                self.render_template(template=template, node=node, outputdir=sub_dir)

            template = env.find_template('hierachymap')
            for node in hierachymapnodes:
                self.render_template(template=template, node=node, outputdir=sub_dir)

        logger.info("Generate HTML Documentation")
        _ = HTMLExporter().export(root, output_dir.joinpath('docs'))
