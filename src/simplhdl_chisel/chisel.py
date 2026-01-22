import logging

from simplhdl.plugin import GeneratorBase, FlowBase
from simplhdl.project.files import ChiselBuildFile, VerilogFile
from simplhdl.utils import sh

logger = logging.getLogger(__name__)


class ChiselGenerator(GeneratorBase):

    def run(self, flow: FlowBase):
        sbt_files = list(self.project.defaultDesign.files(type=ChiselBuildFile))
        if sbt_files:
            logging.debug("Running Chisel Generator")
            chisel_dir = self.builddir.joinpath('chisel')
            sbt_dir = chisel_dir.joinpath('sbt')
            ivy_dir = chisel_dir.joinpath('ivy2')
            ivy_dir.mkdir(parents=True, exist_ok=True)

        for sbt_file in sbt_files:
            name = sbt_file.path.parent.name
            output_dir = self.builddir.joinpath('chisel', 'projects', name)
            output_dir.mkdir(parents=True, exist_ok=True)

            for item in sbt_file.path.parent.glob('*'):
                if item.resolve() == self.builddir.parent.resolve():
                    continue

                try:
                    logger.warning(f"Create symbolic link {item}")
                    output_dir.joinpath(item.name).symlink_to(item)
                except FileExistsError:
                    pass

            sh(
                ['sbt', '--sbt-dir', str(sbt_dir.resolve()), 'run'],
                cwd=output_dir,
                output=True)

            for file in output_dir.rglob('*.v'):
                verilog_file = VerilogFile(file.resolve())
                sbt_file.fileset.insert_file_after(sbt_file, verilog_file)
            next(sbt_files)
