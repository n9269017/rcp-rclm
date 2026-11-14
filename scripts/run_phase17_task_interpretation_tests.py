"""AE task-interpretation, proof-parser, and gate tests.

Controlled compiler logs exercise rejection logic; they are not Lean proofs.
The separate pinned Lean gate must check the generated statements.
"""
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
suite = unittest.defaultTestLoader.discover(
    str(root / 'python/rcp_rclm_runtime_v5/tests_phase17ae'), pattern='test_*.py')
EXPECTED = 114
if suite.countTestCases() != EXPECTED:
    raise SystemExit(f'Expected {EXPECTED} tests, got {suite.countTestCases()}')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
