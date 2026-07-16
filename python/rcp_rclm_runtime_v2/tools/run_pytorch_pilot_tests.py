from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence
from typing import Final

_TEST_MODULES: Final[Sequence[str]] = (
    "tests_pytorch_pilot.test_proposal_backend",
    "tests_pytorch_pilot.test_admission_replay",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    package_root = args.package_root.resolve(strict=True)
    combined = bytearray()
    return_code = 0
    for module_name in _TEST_MODULES:
        command = (
            sys.executable,
            "-m",
            "unittest",
            "-v",
            module_name,
        )
        completed = subprocess.run(
            command,
            cwd=package_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        combined.extend(
            f"=== {module_name} ===\n".encode("utf-8")
        )
        combined.extend(completed.stdout)
        if completed.stdout and not completed.stdout.endswith(b"\n"):
            combined.extend(b"\n")
        if completed.returncode != 0 and return_code == 0:
            return_code = completed.returncode
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(bytes(combined))
    sys.stdout.buffer.write(bytes(combined))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
