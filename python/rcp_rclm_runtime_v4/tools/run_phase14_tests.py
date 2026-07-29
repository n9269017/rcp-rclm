from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.package_root.resolve(strict=True)
    sys.path.insert(0, str(root))
    suite = unittest.defaultTestLoader.discover(str(root / "tests_phase14"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
