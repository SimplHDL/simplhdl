import subprocess

from typing import List


def sh(command: List[str]):
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise SystemError(stderr.decode())
    return stdout.decode()
