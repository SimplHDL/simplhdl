from __future__ import annotations

import json
import os
import sys

from .context import load_project, serialize_files, serialize_fileset_tree


def main() -> None:
    # Generators and EDA tools may write directly to stdout, including via its
    # file descriptor. Keep the JSON result on a separate, original descriptor.
    result_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    request = json.loads(sys.argv[1])
    project = load_project(**request["project"])
    if request["operation"] == "files":
        result = serialize_files(project, **request["options"])
    elif request["operation"] == "filesets":
        result = serialize_fileset_tree(project, **request["options"])
    else:
        raise ValueError(f"Unknown inspection operation: {request['operation']}")
    with os.fdopen(result_fd, "w", encoding="utf-8") as output:
        json.dump(result, output)


if __name__ == "__main__":
    main()
