import logging

from ..generator import GeneratorFactory, GeneratorBase
from ..pyedaa import SystemRDLSourceFile, SystemVerilogSourceFile
from ..flow import FlowBase
from ..utils import sh

logger = logging.getLogger(__name__)


@GeneratorFactory.register('SystemRDL')
class SystemRDL(GeneratorBase):

    def run(self, flow: FlowBase):
        rdlfiles = self.project.DefaultDesign.DefaultFileSet.Files(fileType=SystemRDLSourceFile)
        output_dir = self.builddir.joinpath('systemrdl')

        for rdlfile in rdlfiles:
            logger.debug("Running SystemRDL Generator")
            output_dir.mkdir(exist_ok=True)
            sh(f'peakrdl regblock {rdlfile.Path} -o {output_dir} --cpuif axi4-lite'.split())
            pkgfile = SystemVerilogSourceFile(output_dir.joinpath(f'{rdlfile.Path.stem}_pkg.sv'))
            svfile = SystemVerilogSourceFile(output_dir.joinpath(f'{rdlfile.Path.stem}.sv'))
            rdlfile.FileSet.InsertFileAfter(rdlfile, pkgfile)
            rdlfile.FileSet.InsertFileAfter(rdlfile, svfile)
            # NOTE: After inserting files call next to prevent infinit iterations
            next(rdlfiles)
