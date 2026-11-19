"""AM source/import and gate-format controls; no compiler success is simulated."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from rcp_rclm_runtime_v5.phase17 import authenticated_authority_check as checker
from rcp_rclm_runtime_v5.phase17 import authenticated_authority_capture as capture
from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, sha

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('phase17am_gate_controls', ROOT / 'scripts/run_phase17_authenticated_authority_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class AuthenticatedAuthorityCheckTests(unittest.TestCase):
    def test_source_inventory_includes_all_authorization_and_evidence_paths(self):
        paths = set(checker.source_paths(ROOT))
        required = {
            'lean/phase17_bridge/AuthenticatedAuthority.lean',
            'docs/executable_core_v5/PHASE_17_AUTHENTICATED_AUTHORITY.md',
            'scripts/phase17_authority_transport_service.py',
            'scripts/phase17_authority_transport_client.py',
            'scripts/phase17_authority_transport_probe.py',
            'scripts/phase17_authority_isolation_probe.py',
            'scripts/run_phase17_authenticated_authority_gate.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authority_transport.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authority_transport_pki.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authority_isolation.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authenticated_authority_capture.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authenticated_authority_check.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authenticated_authority_lean.py',
            'python/rcp_rclm_runtime_v5/tests_phase17am/test_authenticated_authority_check.py',
            'python/rcp_rclm_runtime_v5/tests_phase17am/test_authenticated_authority_capture.py',
        }
        self.assertTrue(required <= paths, sorted(required - paths))

    def test_resolution_accepts_exact_posix_and_windows_locations(self):
        for workspace, init, observed in [('/capture/workspace', '/lean/lib/lean/Init.olean',
                                           '/capture/workspace/AuthenticatedAuthority.olean'),
                                          ('C:\\capture\\workspace', 'C:\\lean\\lib\\lean\\Init.olean',
                                           'c:/capture/workspace/AuthenticatedAuthority.olean')]:
            record = {'returncode': 0, 'stderr': '', 'stdout': init + '\n' + init + '\n' + observed + '\n'}
            with self.subTest(workspace=workspace):
                result = checker._resolve(record, 'AuthenticatedAuthority', workspace, init)
                self.assertEqual(result['resolved_module_path'], observed)

    def test_resolution_refuses_other_workspace_object(self):
        init = '/lean/lib/lean/Init.olean'
        record = {'returncode': 0, 'stderr': '',
                  'stdout': init + '\n' + init + '\n/other/AuthenticatedAuthority.olean\n'}
        with self.assertRaisesRegex(ValueError, 'import did not resolve to the restored compiled artifact'):
            checker._resolve(record, 'AuthenticatedAuthority', '/capture/workspace', init)

    def test_resolution_refuses_wrong_init_or_extra_dependency(self):
        init = '/lean/lib/lean/Init.olean'; module = '/capture/workspace/AuthenticatedAuthority.olean'
        wrong = {'returncode': 0, 'stderr': '', 'stdout': init + '\n/other/Init.olean\n' + module + '\n'}
        with self.assertRaisesRegex(ValueError, 'import probe selected another Init module'):
            checker._resolve(wrong, 'AuthenticatedAuthority', '/capture/workspace', init)
        extra = {'returncode': 0, 'stderr': '', 'stdout': init + '\n' + init + '\n' + module + '\n/other/Extra.olean\n'}
        with self.assertRaisesRegex(ValueError, 'unexpected direct import inventory'):
            checker._resolve(extra, 'AuthenticatedAuthority', '/capture/workspace', init)

    def test_gate_false_claim_map_has_exact_boolean_inventory(self):
        claims = {name: False for name in gate.FALSE_CLAIMS}
        self.assertTrue(gate.false_claims(claims))
        key = next(iter(claims)); claims[key] = 0
        self.assertFalse(gate.false_claims(claims))
        claims[key] = False; claims['unexpected_claim'] = False
        self.assertFalse(gate.false_claims(claims))

    def test_gate_packet_loader_distinguishes_cjson_from_manifest_json(self):
        # Minimal format-only packet. This loader does not grant semantic or
        # formal acceptance; PreparedAuthenticatedAuthority performs that next step.
        packet = {'schema': capture.SCHEMA, 'policy': capture.POLICY,
                  'base_commit': capture.BASE, 'sentinel': 'CJSON format'}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'packet.json'; raw = canonical(packet); path.write_bytes(raw)
            self.assertEqual(gate.load_retained_packet(path, sha(raw)), packet)
            with self.assertRaisesRegex(ValueError, 'AM retained packet hash differs'):
                gate.load_retained_packet(path, '0' * 64)
            pretty = (json.dumps(packet, indent=2) + '\n').encode(); path.write_bytes(pretty)
            with self.assertRaises(ValueError): gate.load_retained_packet(path, sha(pretty))


if __name__ == '__main__':
    unittest.main()
