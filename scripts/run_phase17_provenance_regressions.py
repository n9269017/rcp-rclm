"""Run existing controller/Phase16-adapter regressions, not historical campaigns."""
from pathlib import Path
import os
import sys
import unittest
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1]
paths=[str(root/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
sys.path[:0]=paths
os.environ['PYTHONPATH']=os.pathsep.join(paths+[os.environ.get('PYTHONPATH','')])
folder=root/'python/rcp_rclm_runtime_v5/tests_phase17'
suite=unittest.TestSuite(unittest.defaultTestLoader.discover(str(folder),pattern=p)
                         for p in ('test_controller.py','test_phase16_adapter.py'))
if suite.countTestCases()!=33:raise SystemExit('Exact 33 controller/adapter regressions required')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
