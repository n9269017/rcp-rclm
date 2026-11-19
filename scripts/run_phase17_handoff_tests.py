"""Only Phase17P tests. Earlier suites/proofs are not rerun."""
from pathlib import Path
import os
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
paths=[str(ROOT/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
sys.path[:0]=paths
os.environ['PYTHONPATH']=os.pathsep.join(paths)
sys.dont_write_bytecode=True
suite=unittest.TestLoader().discover(str(ROOT/'python/rcp_rclm_runtime_v5/tests_phase17p'),pattern='test_handoff.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful() or result.skipped or result.testsRun!=70:raise SystemExit(1)
print('Phase17P inactive handoff tests only. Root acceptance, promotion, Phase17 and EGC-0 remain false.')
