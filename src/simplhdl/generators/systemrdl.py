import os

from ..generator import GeneratorFactory, GeneratorBase
from ..pyedaa import SystemRDLSourceFile, SystemVerilogSourceFile
from ..flow import FlowCategory
from ..utils import sh


@GeneratorFactory.register('SystemRDL')
class SystemRDL(GeneratorBase):

    def run(self, flowcategory: FlowCategory):
        output_dir = self.builddir.joinpath('systemrdl')
        os.makedirs(output_dir, exist_ok=True)
        rdlfiles = self.project.DefaultDesign.DefaultFileSet.Files(fileType=SystemRDLSourceFile)
        for rdlfile in rdlfiles:
            sh(f'peakrdl regblock {rdlfile.Path} -o {output_dir} --cpuif axi4-lite'.split())
            pkgfile = SystemVerilogSourceFile(output_dir.joinpath(f'{rdlfile.Path.stem}_pkg.sv'))
            svfile = SystemVerilogSourceFile(output_dir.joinpath(f'{rdlfile.Path.stem}.sv'))
            rdlfile.FileSet.InsertFileAfter(rdlfile, pkgfile)
            rdlfile.FileSet.InsertFileAfter(rdlfile, svfile)
            # NOTE: After inserting files call next to prevent infinit iterations
            next(rdlfiles)
