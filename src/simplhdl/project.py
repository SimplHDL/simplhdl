import os
import logging
import pyEDAA.ProjectModel as pm  # type: ignore

from typing import Dict
from .utils import sh

logger = logging.getLogger(__name__)


def get_lib_name_path(interface: str, simulator: str) -> str:
    lib_name_path = sh(['cocotb-config', '--lib-name-path', interface, simulator]).strip()
    return lib_name_path

class Project(pm.Project):

    def export_edam(self, tool: str) -> Dict:
        """
        Convert the project object to the Edam format used
        by Edialize.
        """
        libpython = sh(['cocotb-config', '--libpython']).strip()
        os.environ['LIBPYTHON_LOC'] = libpython
        # os.environ['GPI_EXTRA'] = f"{get_lib_name_path('fli', 'questa')}:cocotbfli_entry_point"
        os.environ['MODULE'] = 'test_adder'
        os.environ['PYTHONPATH'] = '/home/rgo/devel/cocotb-example/cores/adder.core/verif/cocotb'
        os.environ['RANDOM_SEED'] = '1'
        files = [file_to_edam(f) for f in self.DefaultDesign.Files()]
        name = self.DefaultDesign.Name
        hooks = dict()
        tool_options = self._get_edam_tool_options(tool)
        parameters = dict()
        toplevel = self.DefaultDesign.TopLevel

        return {
            'files': files,
            'name': name,
            'hooks': hooks,
            'tool_options': tool_options,
            'parameters': parameters,
            'toplevel': toplevel,
        }

    def _get_edam_tool_options(self, tool) -> Dict:
        if tool in ['modelsim', 'questa']:
            return {
                'modelsim': {'vsim_options': ['-no_autoacc', '-pli', get_lib_name_path('vpi', 'modelsim')]},
            }
        if tool == "quartus":
            return {
                'quartus': {'family': "Agilex", 'device': "AGFB014R24A2E2V"},
            }
        if tool == "vivado":
            return dict()
        if tool == "icarus":
            return dict()
        if tool == "xsim":
            return dict()


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


def filetype_to_edam(file_obj: pm.File) -> str:
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
