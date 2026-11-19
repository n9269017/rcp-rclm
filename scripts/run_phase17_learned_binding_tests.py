"""Typed learned-state integration tests; compiler controls are mocks, not proofs."""
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
suite=unittest.defaultTestLoader.discover(str(ROOT/'python/rcp_rclm_runtime_v5/tests_phase17i'))
EXPECTED=68
if suite.countTestCases()!=EXPECTED:raise SystemExit('Expected '+str(EXPECTED)+' integration tests, got '+str(suite.countTestCases()))
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
