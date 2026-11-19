"""New sparse-byte refinement tests; controlled compiler logs are not proofs."""
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{version}') for version in (2, 3, 4, 5)]
suite = unittest.defaultTestLoader.discover(
    str(root / 'python/rcp_rclm_runtime_v5/tests_phase17r'), pattern='test_*.py')
EXPECTED = 90
if suite.countTestCases() != EXPECTED:
    raise SystemExit(f'Expected {EXPECTED} tests, got {suite.countTestCases()}')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
