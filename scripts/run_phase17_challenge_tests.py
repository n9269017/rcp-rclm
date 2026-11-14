"""Run real Phase 17C subprocess checks without gh, Actions or a package install."""
from pathlib import Path
import os
import sys
import unittest


def main():
    root=Path(__file__).resolve().parents[1]
    paths=[str(root/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
    sys.path[:0]=paths
    os.environ['PYTHONPATH']=os.pathsep.join(paths)
    suite=unittest.defaultTestLoader.discover(str(root/'python/rcp_rclm_runtime_v5/tests_phase17c'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print('Process/protocol separation only; OS sandbox: false; Phase17 exit: false; Gate E: false')
    return 0 if result.wasSuccessful() and result.testsRun >= 18 and not result.skipped else 1


if __name__=='__main__':raise SystemExit(main())
