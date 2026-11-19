"""AK durable-root runtime, original-evidence and formal refusal tests.

Controlled parser and installer-shaped fixtures cannot create proof acceptance.
The separate gate requires actual pinned Lean and exact native reference records.
"""
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
suite = unittest.defaultTestLoader.discover(
    str(root / 'python/rcp_rclm_runtime_v5/tests_phase17ak'), pattern='test_*.py')
EXPECTED = 111
if suite.countTestCases() != EXPECTED:
    raise SystemExit(f'Expected {EXPECTED} tests, got {suite.countTestCases()}')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
