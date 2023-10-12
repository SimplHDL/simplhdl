import sys
import logging

from typing import List, Optional
from pathlib import Path
from jinja2 import Template
from subprocess import CalledProcessError, Popen, PIPE
from hashlib import md5

logger = logging.getLogger(__name__)


def sh(command: List[str], cwd: Optional[Path] = None, output=False, shell=False):
    with Popen(command, stdout=PIPE, stderr=PIPE, cwd=cwd, shell=shell) as p:
        if output:
            stdout: str = ''
            for line in p.stdout:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
                stdout += line.decode()
            _, stderr = p.communicate()
        else:
            stdout, stderr = p.communicate()
            stdout = stdout.decode().strip()

    if p.returncode != 0:
        if not output:
            logger.debug(stdout)
        raise CalledProcessError(stderr.decode())
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


def md5_add_file(filename: Path, hash):
    with filename.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
    return hash


def md5_add_dir(directory, hash):
    assert Path(directory).is_dir()
    for path in sorted(Path(directory).iterdir()):
        hash.update(path.name.encode())
        if path.is_file():
            hash = md5_add_file(path, hash)
        elif path.is_dir():
            hash = md5_add_dir(path, hash)
    return hash


def md5sum(*items: Path) -> str:
    hash = md5()
    for item in [Path(i) for i in items]:
        if item.is_file():
            hash = md5_add_file(item, hash)
        elif item.is_dir():
            hash = md5_add_dir(item, hash)
    return hash.hexdigest()


def md5check(*items: Path, filename: Path) -> bool:
    with filename.open() as f:
        md5expected = f.read()
    return md5sum(*items) == md5expected


def md5write(*items: Path, filename: Path) -> None:
    with filename.open('w') as f:
        f.write(md5sum(*items))
