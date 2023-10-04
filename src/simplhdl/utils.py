import sys
import subprocess
import logging

from typing import List, Optional
from pathlib import Path
from jinja2 import Template

logger = logging.getLogger(__name__)


def sh(command: List[str], cwd: Optional[Path] = None, output=False, shell=False):
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          cwd=cwd, shell=shell) as p:
        if output:
            stdout: str = ''
            for line in p.stdout:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
                stdout += line.decode()
            _, stderr = p.communicate()
        else:
            stdout, stderr = p.communicate()
            stdout.decode()

    if p.returncode != 0:
        raise SystemError(stderr.decode())
    return stdout


def generate_from_template(template: Template, output: Path, *args, **kwargs) -> None:
    templatefile = Path(template.filename)
    if output.is_dir():
        filename = output.joinpath(templatefile.name)
        if filename.suffix == '.j2':
            output = filename.with_suffix('')
        else:
            output = filename
    text = template.render(*args, **kwargs)
    if output.exists():
        with output.open() as f:
            old_text = f.read()
        if old_text == text:
            logger.debug(f"{output.absolute()}: is already up to date")
            return
    with output.open('w') as f:
        f.write(text)
