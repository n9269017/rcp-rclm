"""Run Phase 17 foundation tests against this checkout, without pip or gh."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import unittest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-only", action="store_true",
                        help="Run control-plane unit tests only; NOT integration/closure evidence")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = [str(root / "python" / f"rcp_rclm_runtime_v{v}") for v in (2, 3, 4, 5)]
    sys.path[:0] = paths
    os.environ["PYTHONPATH"] = os.pathsep.join(paths + [os.environ.get("PYTHONPATH", "")])
    suite = unittest.defaultTestLoader.discover(
        str(root / "python/rcp_rclm_runtime_v5/tests_phase17"),
        pattern="test_controller.py" if args.core_only else "test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("Phase17 exit closed: false; Gate E closed: false; EGC-0 started: false")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
