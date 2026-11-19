"""AL source/import and gate-format controls; no compiler success is simulated."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from rcp_rclm_runtime_v5.phase17 import durable_campaign_check as checker
from rcp_rclm_runtime_v5.phase17 import durable_campaign_capture as capture
from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, sha

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('phase17al_gate_controls', ROOT / 'scripts/run_phase17_durable_campaign_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class DurableCampaignCheckTests(unittest.TestCase):
    def test_source_inventory_includes_all_authorization_and_evidence_paths(self):
        paths = set(checker.source_paths(ROOT))
        required = {
            'lean/phase17_bridge/DurableCampaign.lean',
            'docs/executable_core_v5/PHASE_17_DURABLE_CAMPAIGN.md',
            'scripts/phase17_durable_campaign_service.py',
            'scripts/run_phase17_durable_campaign_gate.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/durable_campaign.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/durable_campaign_native.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/durable_campaign_capture.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/durable_campaign_check.py',
            'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/durable_campaign_lean.py',
            'python/rcp_rclm_runtime_v5/tests_phase17al/test_durable_campaign_check.py',
            'python/rcp_rclm_runtime_v5/tests_phase17al/test_durable_campaign_capture.py',
            'python/rcp_rclm_runtime_v5/tests_phase17al/test_durable_campaign_native.py',
        }
        self.assertTrue(required <= paths, sorted(required - paths))

    def test_resolution_accepts_exact_posix_and_windows_locations(self):
        for workspace, init, observed in [('/capture/workspace', '/lean/lib/lean/Init.olean',
                                           '/capture/workspace/DurableCampaign.olean'),
                                          ('C:\\capture\\workspace', 'C:\\lean\\lib\\lean\\Init.olean',
                                           'c:/capture/workspace/DurableCampaign.olean')]:
            record = {'returncode': 0, 'stderr': '', 'stdout': init + '\n' + init + '\n' + observed + '\n'}
            with self.subTest(workspace=workspace):
                result = checker._resolve(record, 'DurableCampaign', workspace, init)
                self.assertEqual(result['resolved_module_path'], observed)

    def test_resolution_refuses_other_workspace_object(self):
        init = '/lean/lib/lean/Init.olean'
        record = {'returncode': 0, 'stderr': '',
                  'stdout': init + '\n' + init + '\n/other/DurableCampaign.olean\n'}
        with self.assertRaisesRegex(ValueError, 'import did not resolve to the restored compiled artifact'):
            checker._resolve(record, 'DurableCampaign', '/capture/workspace', init)

    def test_resolution_refuses_wrong_init_or_extra_dependency(self):
        init = '/lean/lib/lean/Init.olean'; module = '/capture/workspace/DurableCampaign.olean'
        wrong = {'returncode': 0, 'stderr': '', 'stdout': init + '\n/other/Init.olean\n' + module + '\n'}
        with self.assertRaisesRegex(ValueError, 'import probe selected another Init module'):
            checker._resolve(wrong, 'DurableCampaign', '/capture/workspace', init)
        extra = {'returncode': 0, 'stderr': '', 'stdout': init + '\n' + init + '\n' + module + '\n/other/Extra.olean\n'}
        with self.assertRaisesRegex(ValueError, 'unexpected direct import inventory'):
            checker._resolve(extra, 'DurableCampaign', '/capture/workspace', init)

    def test_gate_false_claim_map_has_exact_boolean_inventory(self):
        claims = {name: False for name in gate.FALSE_CLAIMS}
        self.assertTrue(gate.false_claims(claims))
        key = next(iter(claims)); claims[key] = 0
        self.assertFalse(gate.false_claims(claims))
        claims[key] = False; claims['unexpected_claim'] = False
        self.assertFalse(gate.false_claims(claims))

    def test_gate_packet_loader_distinguishes_cjson_from_manifest_json(self):
        # Minimal format-only packet. This loader does not grant semantic or
        # formal acceptance; PreparedDurableCampaign performs that next step.
        packet = {'schema': capture.SCHEMA, 'policy': capture.POLICY,
                  'base_commit': capture.BASE, 'sentinel': 'CJSON format'}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'packet.json'; raw = canonical(packet); path.write_bytes(raw)
            self.assertEqual(gate.load_retained_packet(path, sha(raw)), packet)
            with self.assertRaisesRegex(ValueError, 'AL retained packet hash differs'):
                gate.load_retained_packet(path, '0' * 64)
            pretty = (json.dumps(packet, indent=2) + '\n').encode(); path.write_bytes(pretty)
            with self.assertRaises(ValueError): gate.load_retained_packet(path, sha(pretty))


if __name__ == '__main__':
    unittest.main()
