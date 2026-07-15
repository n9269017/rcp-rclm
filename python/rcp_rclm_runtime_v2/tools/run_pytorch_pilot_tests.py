from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    package_root = args.package_root.resolve(strict=True)
    command = (
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(package_root / "tests_pytorch_pilot"),
        "-v",
    )
    completed = subprocess.run(
        command,
        cwd=package_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(completed.stdout)
    sys.stdout.buffer.write(completed.stdout)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
