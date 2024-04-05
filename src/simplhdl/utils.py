import sys
import logging

from typing import Dict, List, Optional, Union
from pathlib import Path
from contextlib import contextmanager
from time import sleep
from jinja2 import Template
from subprocess import Popen, PIPE
from hashlib import md5

logger = logging.getLogger(__name__)


class CalledShError(Exception):
    pass


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
        raise CalledShError(stderr.decode())
    return stdout


def generate_from_template(template: Template, output: Path, *args, **kwargs) -> bool:
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
            return False
    logger.debug(f"{output.absolute()}: create new")
    with output.open('w') as f:
        f.write(text)
    return True


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


def md5sum(*items: Union[str, Path]) -> str:
    hash = md5()
    for item in items:
        if isinstance(item, Path):
            if item.is_file():
                hash = md5_add_file(item, hash)
            elif item.is_dir():
                hash = md5_add_dir(item, hash)
            else:
                raise Exception(f"Unknown Path item: {item}")
        else:
            hash.update(str(item).encode())
    return hash.hexdigest()


def md5check(*items: Path, filename: Path) -> bool:
    with filename.open() as f:
        md5expected = f.read()
    return md5sum(*items) == md5expected


def md5write(*items: Path, filename: Path) -> None:
    with filename.open('w') as f:
        f.write(md5sum(*items))


def append_suffix(path: Path, suffix: str) -> Path:
    return path.with_suffix(path.suffix + suffix)


def dict2str(*dictionaries: Dict[str, str]) -> str:
    dictionary = dict()
    for d in dictionaries:
        dictionary.update(d)
    return ' '.join([f"{k}={v}" for k, v in dictionary.items()])


def mkdir(name: Path) -> bool:
    try:
        name.mkdir(parents=True)
        return True
    except FileExistsError:
        return False


@contextmanager
def lock(directory: Path) -> Path:
    while not mkdir(directory):
        sleep(1)
    try:
        yield directory
    finally:
        directory.rmdir()
