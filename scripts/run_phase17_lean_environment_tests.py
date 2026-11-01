"""24 environment/control regressions; these are not Lean proofs."""
from pathlib import Path
import sys
import unittest
root=Path(__file__).resolve().parents[1]
suite=unittest.defaultTestLoader.discover(str(root/'scripts/tests_phase17e'),pattern='test_lean_gate_environment.py')
if suite.countTestCases()!=24:raise SystemExit('Expected exactly 24 regression tests')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
