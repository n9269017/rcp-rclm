"""Phase17G tests; mocked tool cases do not prove any Lean theorem."""
from pathlib import Path
import sys
import unittest
root=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(root/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
suite=unittest.defaultTestLoader.discover(str(root/'python/rcp_rclm_runtime_v5/tests_phase17g'))
if suite.countTestCases()!=47:raise SystemExit('unexpected Phase17G test inventory: '+str(suite.countTestCases()))
result=unittest.TextTestRunner(verbosity=2).run(suite)
print('Scoped append-only semantics; full root/promotion/Phase17 closure false.')
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
