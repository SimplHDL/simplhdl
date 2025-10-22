import logging
import hashlib
import os
from pathlib import Path
from jinja2 import Template
from shutil import rmtree

from ..generator import GeneratorFactory, GeneratorBase
from ..flow import FlowBase
from ..pyedaa import (
                      File,
                      SourceFile,
                      HDLSourceFile,
                      VHDLSourceFile,
                      VerilogSourceFile,
                      VerilogIncludeFile,
                      SystemVerilogSourceFile,
                      CSourceFile,
                      SettingFile,
                      ConstraintFile)

logger = logging.getLogger(__name__)

def run_sh(cmd: str) -> str:
    return os.popen(cmd).read().strip()

def path_hash(path: Path) -> str:
    return hashlib.md5(str(path).encode()).hexdigest()

def get_output_file_name(input_file_path: Path) -> Path:
    hash = path_hash(input_file_path)
    output_file_name = Path(input_file_path.stem)
    output_file_name_with_hash = output_file_name.with_stem(f"{output_file_name.stem}_{hash}")
    return output_file_name_with_hash

def render_j2_template(template_file: Path, output_file: Path) -> None:
    template = Template(template_file.read_text())
    with output_file.open('w') as f:
        f.write(template.render(env=os.getenv, sh=run_sh))

@GeneratorFactory.register('Jinja2')
class Jinja2(GeneratorBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_dir = self.builddir.joinpath('j2')
        rmtree(self.output_dir, ignore_errors=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.path_map = {}

    file_ext_type_map = {
        '.vhd': VHDLSourceFile,
        '.vhdl': VHDLSourceFile,
        '.v': VerilogSourceFile,
        '.vh': VerilogIncludeFile,
        '.sv': SystemVerilogSourceFile,
        '.svh': VerilogIncludeFile,
        '.c': CSourceFile,
        '.h': CSourceFile,
        '.xdc': ConstraintFile,
        '.sdc': ConstraintFile,
        '.qsf': SettingFile
    }

    @classmethod
    def insert_file_after(cls, existing_file: File, new_file_path: Path) -> None:
        new_file_type = SourceFile
        if new_file_path.suffix in cls.file_ext_type_map:
            new_file_type = cls.file_ext_type_map[new_file_path.suffix]
        new_file = new_file_type(new_file_path.absolute())
        if isinstance(new_file, HDLSourceFile):
            new_file.Library = existing_file.FileSet.VHDLLibrary
        existing_file.FileSet.InsertFileAfter(existing_file, new_file)

    def generate_path_map_file(self) -> None:
        if not self.path_map:
            return
        path_map_file = self.output_dir.joinpath('path_map.txt')
        path_map_file.unlink(missing_ok=True)
        with path_map_file.open('w') as f:
            for output_path, input_path in self.path_map.items():
                f.write(f"{output_path}: {input_path}\n")

    def run(self, flow: FlowBase) -> None:
        source_files = self.project.DefaultDesign.DefaultFileSet.Files(fileType=SourceFile)
        input_files = list(filter(lambda f: f.Path.suffix == '.j2', source_files)) # Force evaluation, otherwise we'll enter an infinite loop
        for input_file in input_files:
            output_file_name = get_output_file_name(input_file.Path)
            output_file_path = self.output_dir.joinpath(output_file_name)
            self.path_map[output_file_path] = input_file.Path
            logger.info(f"Rendering {input_file.Path} as {output_file_path.name}")
            render_j2_template(input_file.Path, output_file_path)
            self.insert_file_after(input_file, output_file_path)

        self.generate_path_map_file()
