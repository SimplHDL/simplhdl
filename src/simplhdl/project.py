import logging
import pyEDAA.ProjectModel as pm  # type: ignore

from typing import Dict

logger = logging.getLogger(__name__)


class Project(pm.Project):

    def export_edam(self) -> Dict:
        """
        Convert the project object to the Edam format used
        by Edialize.
        """
        files = [file_to_edam(f) for f in self.DefaultDesign.Files()]
        name = self.DefaultDesign.Name
        hooks: Dict = dict()
        tool_options: Dict = dict()
        parameters: Dict = dict()
        toplevel = self.DefaultDesign.TopLevel

        return {
            'files': files,
            'name': name,
            'hooks': hooks,
            'tool_options': tool_options,
            'parameters': parameters,
            'toplevel': toplevel,
        }


class IPSpecificationFile(pm.File, pm.XMLContent):
    """
    IP design file.
    """


def is_include(file_obj: pm.File) -> bool:
    return ((file_obj.Path.suffix in ['.vh', '.svh']) and
            (file_obj.FileType in [pm.VerilogSourceFile, pm.SystemVerilogSourceFile]))


def file_to_edam(file_obj: pm.File) -> Dict:
    """
    Convert File object to edam dictionary.
    """
    return {
        'name': str(file_obj.Path.absolute()),
        'file_type': filetype_to_edam(file_obj),
        'is_include_file': is_include(file_obj),
        'logic_name': "work"  # file_obj.FileSet.VHDLLibrary
    }


def filetype_to_edam(file_obj: pm.File) -> str:  # noqa C901
    if file_obj.FileType == pm.SystemVerilogSourceFile:
        return 'systemVerilogSource'
    elif file_obj.FileType == pm.VerilogSourceFile:
        return 'verilogSource'
    elif file_obj.FileType == pm.VHDLSourceFile:
        return 'vhdlSource-2008'
    elif file_obj.FileType == pm.ConstraintFile and file_obj.Path.suffix == '.xdc':
        return 'xdc'
    elif file_obj.FileType == pm.ConstraintFile and file_obj.Path.suffix == '.sdc':
        return 'SDC'
    elif file_obj.FileType == pm.TCLSourceFile:
        return 'tclSource'
    elif file_obj.FileType == IPSpecificationFile and file_obj.Path.suffix == '.ip':
        return 'IP'
    elif file_obj.FileType == IPSpecificationFile and file_obj.Path.suffix == '.qip':
        return 'QIP'
    elif file_obj.FileType == IPSpecificationFile and file_obj.Path.suffix == '.qsys':
        return 'QSYS'
    elif file_obj.FileType == pm.CocotbPythonFile:
        return 'user'
    logger.warning(f"Unknown filetype: '{file_obj.FileType.__name__}' for file '{file_obj.Path}'")
    return 'user'
