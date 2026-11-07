"""Run only new Phase17O tests; not earlier suites or proof campaigns."""
from pathlib import Path
import os
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
paths=[str(ROOT/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
sys.path[:0]=paths
# New child-process tests require the same declared source tree.
os.environ['PYTHONPATH']=os.pathsep.join(paths)
sys.dont_write_bytecode=True
suite=unittest.TestLoader().discover(str(ROOT/'python/rcp_rclm_runtime_v5/tests_phase17o'),pattern='test_campaign_budget.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful() or result.skipped or result.testsRun != 70:
    raise SystemExit(1)
print('Phase17O scoped tests only. No promotion, full root acceptance, Phase17 closure or EGC-0.')
