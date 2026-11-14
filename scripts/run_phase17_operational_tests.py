"""Phase17H tests: actual package cases plus mocked formal-control tests."""
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
suite=unittest.defaultTestLoader.discover(str(root/'python/rcp_rclm_runtime_v5/tests_phase17h'))
EXPECTED_TESTS = 57
if suite.countTestCases()!=EXPECTED_TESTS:raise SystemExit('unexpected Phase17H inventory: '+str(suite.countTestCases()))
result=unittest.TextTestRunner(verbosity=2).run(suite)
print('Bounded public planner/tool contracts only; full root/promotion/Phase17 closure false.')
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
