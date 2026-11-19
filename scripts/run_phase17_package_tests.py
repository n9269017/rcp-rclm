"""Focused Phase17D real-archive and gate-control tests; no phase-closure claim."""
from pathlib import Path
import sys
import unittest
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
sys.path.insert(0,str(root/'python/rcp_rclm_runtime_v5/tests_phase17'))
suite=unittest.defaultTestLoader.discover(str(root/'python/rcp_rclm_runtime_v5/tests_phase17d'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
if result.testsRun==0 or result.skipped:raise SystemExit('zero or skipped tests forbidden')
raise SystemExit(0 if result.wasSuccessful() else 1)
