"""51 execution-control/source-pin tests; these are not Lean proofs."""
from pathlib import Path
import sys
import unittest
root=Path(__file__).resolve().parents[1]
suite=unittest.defaultTestLoader.discover(str(root/'scripts/tests_phase17e'),pattern='test_pinned_lean.py')
count=suite.countTestCases()
if count != 51: raise SystemExit(f'Expected exactly 51 tests, found {count}')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
