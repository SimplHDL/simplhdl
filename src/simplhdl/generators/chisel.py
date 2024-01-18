import logging

from ..generator import GeneratorFactory, GeneratorBase
from ..pyedaa import ChiselBuildFile, VerilogSourceFile
from ..flow import FlowBase
from ..utils import sh

logger = logging.getLogger(__name__)


@GeneratorFactory.register('Chisel')
class Chisel(GeneratorBase):

    def run(self, flow: FlowBase):
        sbt_files = list(self.project.DefaultDesign.DefaultFileSet.Files(fileType=ChiselBuildFile))
        if sbt_files:
            logging.debug("Running Chisel Generator")
            chisel_dir = self.builddir.joinpath('chisel')
            sbt_dir = chisel_dir.joinpath('sbt')
            ivy_dir = chisel_dir.joinpath('ivy2')
            ivy_dir.mkdir(parents=True, exist_ok=True)

        for sbt_file in sbt_files:
            name = sbt_file.Path.parent.name
            output_dir = self.builddir.joinpath('chisel', 'projects', name)
            output_dir.mkdir(parents=True, exist_ok=True)

            for item in sbt_file.Path.parent.glob('*'):
                if item.absolute() == self.builddir.parent.absolute():
                    continue

                try:
                    logger.warning(f"Create symbolic link {item}")
                    output_dir.joinpath(item.name).symlink_to(item)
                except FileExistsError:
                    pass

            # sh(
            #     ['sbt', '--sbt-dir', sbt_dir.absolute(), 'compile'],
            #     cwd=output_dir,
            #     output=True)

            # sh(
            #     ['sbt', '--sbt-dir', sbt_dir.absolute(), '--ivy', ivy_dir, 'publishLocal'],
            #     cwd=output_dir,
            #     output=True)

            sh(
                ['sbt', '--sbt-dir', sbt_dir.absolute(), 'run'],
                cwd=output_dir,
                output=True)

            # sh(
            #     ['sbt', '--sbt-dir', sbt_dir.absolute(), 'run --backend c --genHarness'],
            #     cwd=output_dir,
            #     output=True)

            for file in output_dir.rglob('*.v'):
                verilog_file = VerilogSourceFile(file.absolute())
                sbt_file.FileSet.InsertFileAfter(sbt_file, verilog_file)
            next(sbt_files)
