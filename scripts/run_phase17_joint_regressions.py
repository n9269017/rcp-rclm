"""Unchanged Phase17J and Phase17K suites: 70 + 69 tests, not old Lean runs."""
from pathlib import Path
import importlib.util
import sys
import unittest
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
suite=unittest.TestSuite()
for suffix,name,count in [('j','test_frontier_meanings',70),('k','test_proposal_provenance',69)]:
    path=root/'python/rcp_rclm_runtime_v5'/('tests_phase17'+suffix)/(name+'.py')
    spec=importlib.util.spec_from_file_location('phase17l_regression_'+suffix,path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    tests=unittest.defaultTestLoader.loadTestsFromModule(module)
    if tests.countTestCases()!=count:raise SystemExit('Historical regression inventory changed: '+suffix)
    suite.addTests(tests)
if suite.countTestCases()!=139:raise SystemExit('Expected 139 regression tests')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
