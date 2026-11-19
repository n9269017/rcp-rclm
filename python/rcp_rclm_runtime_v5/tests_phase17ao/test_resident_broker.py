"""Real resident processes against AM's explicitly synthetic TLS authority.

No fixture starts a campaign worker or establishes production commissioning.
"""
from __future__ import annotations

import copy
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import protected_authority as an
from rcp_rclm_runtime_v5.phase17 import resident_broker as resident
from rcp_rclm_runtime_v5.phase17 import service_lifecycle as ledger_api
from rcp_rclm_runtime_v5.phase17.protected_authority_isolation import launch_profile
from rcp_rclm_runtime_v5.phase17.resource_ledger import ResourceError, canonical, sha


class ResidentBrokerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'tests_phase17am/test_authority_transport.py'
        spec = importlib.util.spec_from_file_location('_phase17ao_resident_am_fixture', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        cls.fixture_class = module.AuthorityTransportTests
        cls.fixture_class.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.fixture_class.tearDownClass()

    def setUp(self):
        self.fixture = self.fixture_class('runTest'); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups); self.addCleanup(self.fixture.tearDown)
        f = self.fixture; self.base = f.base.resolve()
        self.commission = an.make_broker_commission(an.SOURCE_ROOT, f.commission,
            expected_authority_commission_sha256=f.pin,
            expected_root_pin=f.authority.root_provision_sha256,
            launch_profile={role: launch_profile(role) for role in ('frontend', 'worker')})
        self.pin = an.commission_digest(self.commission)
        self.state = self.base / 'broker-state.json'
        an.provision_broker_state(self.state, self.commission,
            expected_commission_sha256=self.pin, trusted_headers=f.anchor_value()['headers'])
        self.broker_commission = self.base / 'broker-commission.json'
        self.broker_commission.write_bytes(canonical(self.commission))
        self.authority_commission = self.base / 'authority-commission.json'
        self.authority_commission.write_bytes(canonical(f.commission))
        self.broker_native = self.base / 'broker'; self.broker_native.mkdir()
        self.limits = {'max_attempts': 4, 'max_frame_bytes': 65537,
            'max_request_bytes': 262148, 'max_response_bytes': 65536,
            'max_authority_tls_connections': 4}
        envelope = [1, 4, 4, 262148, 65536, 4]
        commission = ledger_api.make_commission(bindings={
            'campaign_commission_sha256': self.pin,
            'runtime_sha256': resident.runtime_identity(an.SOURCE_ROOT),
            'principal_binding_sha256': sha(b'explicit synthetic parent owner'),
            'currentness_anchor_sha256': sha(b'retained synthetic cursor')},
            lifetime_envelope=envelope, total_budget=[item * 3 for item in envelope],
            commissioning_nonce=sha(b'resident controlled test commission'))
        self.ledger_pin = ledger_api.commission_digest(commission)
        self.ledger_path = self.base / 'lifecycle.json'
        genesis = ledger_api.provision(self.ledger_path, commission,
                                      expected_commission_sha256=self.ledger_pin)
        self.ledger = ledger_api.ServiceLifecycleLedger(self.ledger_path,
            expected_commission_sha256=self.ledger_pin, owner_nonce=sha(b'test owner'),
            expected_cursor=genesis['final_cursor'])
        self.addCleanup(self.ledger.close)

    def intent(self, operation='read', nonce='read'):
        value = {'schema': an.INTENT_SCHEMA, 'commission_sha256': self.pin,
                 'operation': operation, 'nonce': sha(nonce.encode())}
        if operation == 'run': value['credits'] = 2
        return value

    def config(self, slots, lifetime='life0', *, consume=True):
        grant = self.ledger.reserve(lifetime, expected_cursor=self.ledger.cursor)
        if consume:
            self.ledger.consume_launch(grant, expected_cursor=self.ledger.cursor)
        f = self.fixture
        arguments = dict(source_root=an.SOURCE_ROOT, lifetime_id=lifetime,
            broker_commission=self.broker_commission, broker_commission_sha256=self.pin,
            authority_commission=self.authority_commission,
            authority_commission_sha256=f.pin, root_provision_sha256=f.authority.root_provision_sha256,
            state_path=self.state, anchor_path=f.anchor, ca_file=f.pki['public']['ca'],
            client_cert=f.pki['public']['client'], client_key=f.pki['private']['client'],
            port=f.address[1], native_directory=self.base / ('resident-' + lifetime),
            broker_native_root=self.broker_native, limits=self.limits, slots=slots,
            lifecycle_commission_sha256=self.ledger_pin,
            lifecycle_evidence=self.ledger.export_evidence(), grant=grant)
        return resident.make_config(**arguments)

    @staticmethod
    def slot(action, *, abandon=False, mode='reference'):
        return {'action': action, 'mode': mode, 'abandon_response': abandon}

    def run_process(self, config, raw):
        path = self.base / (config['lifetime_id'] + '-config.json')
        path.write_bytes(canonical(config))
        command = [sys.executable, '-I', '-S', '-B', '-u',
                   str(an.SOURCE_ROOT / 'scripts/phase17_resident_broker_service.py'),
                   '--config', str(path), '--config-pin', sha(canonical(config))]
        result = subprocess.run(command, input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=an.SOURCE_ROOT, timeout=45, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertEqual(result.stderr, b'')
        native = Path(config['native_directory'])
        records = [load_json_strict((native / ('attempt-%04d.json' % i)).read_bytes())
                   for i in range(len(config['slots']))]
        admissions = [load_json_strict((native / ('attempt-%04d.admission.json' % i)).read_bytes())
                      for i in range(len(records))]
        frames = [(native / ('attempt-%04d.input.bin' % i)).read_bytes() for i in range(len(records))]
        checked = resident.verify_stream(result.stdout, config=config, attempts=records,
                                         admissions=admissions, raw_frames=frames)
        return result, records, checked

    def test_resident_process_charges_malformed_input_before_parse_and_then_dispatches(self):
        config = self.config([self.slot('malformed'), self.slot('read')])
        raw = b'{\n' + canonical(self.intent()) + b'\n'
        result, records, checked = self.run_process(config, raw)
        self.assertNotEqual(checked['pid'], os.getpid())
        self.assertEqual(checked['counters']['input_attempts'], 2)
        self.assertEqual(checked['counters']['request_bytes'], len(raw))
        self.assertEqual(checked['counters']['response_bytes'], len(result.stdout))
        self.assertEqual(records[0]['parse_status'], 'malformed')
        self.assertIsNone(records[0]['broker_record_sha256'])
        self.assertFalse((self.broker_native / 'malformed').exists())
        action = load_json_strict((self.broker_native / 'read/dispatch.json').read_bytes())
        self.assertEqual(action['observer_pid'], checked['pid'])
        self.assertEqual(action['network_attempts'], 1)
        an.verify_broker_record(action['dispatch'], self.commission)
        self.assertEqual(self.fixture.authority.calls, 0)

    def test_two_lifetimes_share_pending_state_and_reconcile_without_synthetic_reissue(self):
        first = self.config([self.slot('run_abandon', abandon=True)])
        _, _, first_checked = self.run_process(first, canonical(self.intent('run', 'once')) + b'\n')
        self.fixture.wait_results(1)
        self.assertIsNotNone(load_json_strict(self.state.read_bytes())['pending'])
        self.ledger.finish(first['grant'], expected_cursor=self.ledger.cursor,
                           evidence_sha256=sha(canonical(first_checked)))
        second = self.config([self.slot('reconcile')], lifetime='life1')
        _, _, second_checked = self.run_process(second, canonical(self.intent('reconcile', 'resolve')) + b'\n')
        self.assertNotEqual(first_checked['pid'], second_checked['pid'])
        action = load_json_strict((self.broker_native / 'reconcile/dispatch.json').read_bytes())
        self.assertEqual(action['dispatch']['issued_request']['operation'], 'read')
        self.assertFalse(action['frontend_response']['worker_reissued'])
        self.assertIsNone(load_json_strict(self.state.read_bytes())['pending'])
        self.assertEqual(self.fixture.authority.calls, 1)

    def test_frontend_cannot_supply_mode_path_or_administrative_operation(self):
        config = self.config([self.slot('forbidden')])
        intent = self.intent(); intent.update(mode='promotion', anchor_path='/tmp/foreign')
        _, records, checked = self.run_process(config, canonical(intent) + b'\n')
        self.assertEqual(records[0]['parse_status'], 'canonical')
        self.assertEqual(checked['counters']['authority_tls_connections'], 0)
        action = load_json_strict((self.broker_native / 'forbidden/dispatch.json').read_bytes())
        self.assertIsNone(action['dispatch'])
        self.assertTrue(action['frontend_response']['refused'])

    def test_prepaid_but_unconsumed_launch_refused_before_ready(self):
        with self.assertRaisesRegex(ResourceError, 'launch was not consumed'):
            self.config([self.slot('read')], consume=False)

    def test_foreign_campaign_commission_is_not_usable(self):
        config = self.config([self.slot('read')])
        config['broker_commission_sha256'] = sha(b'foreign broker')
        with self.assertRaisesRegex(ResourceError, 'this broker campaign'):
            resident.validate_config(config, expected_config_sha256=sha(canonical(config)))

    def test_underfunded_byte_allowance_refused(self):
        self.limits['max_request_bytes'] -= 1
        with self.assertRaisesRegex(ResourceError, 'input allowance'):
            self.config([self.slot('read')])

    def test_same_lifetime_marker_cannot_be_reused_with_fresh_evidence_paths(self):
        config = self.config([self.slot('read')])
        self.run_process(config, canonical(self.intent()) + b'\n')
        reused = copy.deepcopy(config)
        reused['native_directory'] = str(self.base / 'reused-resident')
        reused['slots'][0]['action'] = 'another_read'
        with self.assertRaises(FileExistsError):
            resident.serve(reused, expected_config_sha256=sha(canonical(reused)),
                           input_stream=io.BytesIO(canonical(self.intent(nonce='other')) + b'\n'),
                           output_stream=io.BytesIO())
        self.assertFalse(Path(reused['native_directory']).exists())

    def test_retained_verification_does_not_require_fresh_paths(self):
        config = self.config([self.slot('read')])
        self.run_process(config, canonical(self.intent()) + b'\n')
        checked, _ = resident.verify_config(config, expected_config_sha256=sha(canonical(config)))
        self.assertEqual(checked, config)
        with self.assertRaises(ResourceError):
            resident.validate_config(config, expected_config_sha256=sha(canonical(config)))

    def test_input_eof_is_charged_and_does_not_create_broker_action(self):
        config = self.config([self.slot('missing')])
        output = io.BytesIO()
        stopped = resident.serve(config, expected_config_sha256=sha(canonical(config)),
                                 input_stream=io.BytesIO(), output_stream=output)
        self.assertFalse(stopped['completed'])
        self.assertEqual(stopped['stop_reason'], 'end_of_input')
        self.assertEqual(stopped['counters']['input_attempts'], 1)
        self.assertEqual(stopped['counters']['request_bytes'], 0)
        self.assertFalse((self.broker_native / 'missing').exists())

    def test_overlong_input_stops_without_unbounded_drain(self):
        config = self.config([self.slot('oversize')])
        stream = io.BytesIO(b'x' * (self.limits['max_frame_bytes'] + 100) + b'\n')
        stopped = resident.serve(config, expected_config_sha256=sha(canonical(config)),
                                 input_stream=stream, output_stream=io.BytesIO())
        self.assertFalse(stopped['completed'])
        self.assertEqual(stopped['counters']['request_bytes'], self.limits['max_frame_bytes'])
        self.assertEqual(stream.tell(), self.limits['max_frame_bytes'])
        self.assertFalse((self.broker_native / 'oversize').exists())


if __name__ == '__main__':
    unittest.main()
