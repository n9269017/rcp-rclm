"""AN exact source/import checks; no compiler success is simulated."""
from pathlib import Path
import unittest

from rcp_rclm_runtime_v5.phase17 import protected_authority_check as checker
from rcp_rclm_runtime_v5.phase17 import protected_authority_lean as formal

ROOT = Path(__file__).resolve().parents[3]


class ProtectedAuthorityCheckTests(unittest.TestCase):
    def test_source_inventory_includes_prior_and_current_formal_boundary(self):
        paths = set(checker.source_paths(ROOT))
        required = {
            'lean/phase17_bridge/ProtectedAuthority.lean',
            'lean/phase17_bridge/AuthenticatedAuthority.lean',
            'docs/executable_core_v5/PHASE_17_PROTECTED_AUTHORITY.md',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/protected_authority_check.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/protected_authority_lean.py',
            'python/rcp_rclm_runtime_v5/tests_phase17an/test_protected_authority_lean.py',
            'python/rcp_rclm_runtime_v5/tests_phase17an/test_protected_authority_check.py',
        }
        self.assertTrue(required <= paths, sorted(required - paths))

    def test_one_module_has_independent_import_stage_and_exact_audit_inventory(self):
        self.assertEqual(formal.MODULES, ('ProtectedAuthority',))
        self.assertEqual(len(formal.NAMES), len(set(formal.NAMES)))
        self.assertEqual(len(formal.LABELS), len(set(formal.LABELS)))
        self.assertNotIn(formal.POSITIVE, formal.NEGATIVES)

    def test_resolution_accepts_exact_posix_and_windows_locations(self):
        for workspace, init, observed in [('/capture/workspace', '/lean/lib/lean/Init.olean',
                                           '/capture/workspace/ProtectedAuthority.olean'),
                                          ('C:\\capture\\workspace', 'C:\\lean\\lib\\lean\\Init.olean',
                                           'c:/capture/workspace/ProtectedAuthority.olean')]:
            record = {'returncode': 0, 'stderr': '', 'stdout': init + '\n' + init + '\n' + observed + '\n'}
            with self.subTest(workspace=workspace):
                result = checker._resolve(record, 'ProtectedAuthority', workspace, init)
                self.assertEqual(result['resolved_module_path'], observed)

    def test_other_workspace_compiled_object_is_refused(self):
        init = '/lean/lib/lean/Init.olean'
        record = {'returncode': 0, 'stderr': '', 'stdout': init + '\n' + init + '\n/other/ProtectedAuthority.olean\n'}
        with self.assertRaisesRegex(ValueError, 'import did not resolve to the restored compiled artifact'):
            checker._resolve(record, 'ProtectedAuthority', '/capture/workspace', init)

    def test_wrong_init_extra_dependency_and_boolean_exit_are_refused(self):
        init = '/lean/lib/lean/Init.olean'; module = '/capture/workspace/ProtectedAuthority.olean'
        for record in (
            {'returncode': 0, 'stderr': '', 'stdout': init + '\n/other/Init.olean\n' + module + '\n'},
            {'returncode': 0, 'stderr': '', 'stdout': init + '\n' + init + '\n' + module + '\n/other/Extra.olean\n'},
            {'returncode': False, 'stderr': '', 'stdout': init + '\n' + init + '\n' + module + '\n'},
            {'returncode': 0, 'stderr': 'unexpected', 'stdout': init + '\n' + init + '\n' + module + '\n'}):
            with self.subTest(record=record), self.assertRaises(ValueError):
                checker._resolve(record, 'ProtectedAuthority', '/capture/workspace', init)


if __name__ == '__main__':
    unittest.main()
