"""Successor-evidence tests. Mocked gate-control cases are NOT formal proof results."""
from pathlib import Path
import sys
import unittest
root=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(root/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
suite=unittest.defaultTestLoader.discover(str(root/'python/rcp_rclm_runtime_v5/tests_phase17f'))
if suite.countTestCases()!=36:raise SystemExit('unexpected successor test inventory')
result=unittest.TextTestRunner(verbosity=2).run(suite)
print('Synthetic candidate coverage only. Root transition: false; Phase17/Gate E: false; EGC-0: false.')
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
