"""Real AM TLS plus synthetic authority tests of AN broker ownership.

These tests create no AL campaign worker and establish no production deployment,
physical accounting, Lean acceptance or promotion. The application captures its
own fresh fixed workers and original native observations separately.
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import authority_transport as am
from rcp_rclm_runtime_v5.phase17 import protected_authority as b
from rcp_rclm_runtime_v5.phase17 import authority_accounting as accounting
from rcp_rclm_runtime_v5.phase17.protected_authority_isolation import launch_profile
from rcp_rclm_runtime_v5.phase17.resource_ledger import ResourceError, canonical, sha


class ProtectedAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'tests_phase17am/test_authority_transport.py'
        spec = importlib.util.spec_from_file_location('_phase17an_am_tls_fixture', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        cls.fixture_class = module.AuthorityTransportTests
        cls.fixture_class.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.fixture_class.tearDownClass()

    def setUp(self):
        self.fixture = self.fixture_class('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.addCleanup(self.fixture.tearDown)
        self.client = self.fixture.client
        profile = {role: launch_profile(role) for role in ('frontend', 'worker')}
        self.commission = b.make_broker_commission(b.SOURCE_ROOT, self.fixture.commission,
            expected_authority_commission_sha256=self.fixture.pin,
            expected_root_pin=self.fixture.authority.root_provision_sha256,
            launch_profile=profile, max_credits=16)
        self.pin = b.commission_digest(self.commission)
        self.state_path = self.fixture.base / 'broker-state.json'
        b.provision_broker_state(self.state_path, self.commission, expected_commission_sha256=self.pin,
            trusted_headers=self.fixture.anchor_value()['headers'])
        self.broker = self.new_broker()
        self.counter = 0

    def new_broker(self):
        return b.ProtectedAuthorityBroker(self.commission, expected_commission_sha256=self.pin,
                                         client=self.client, state_path=self.state_path)

    def intent(self, operation='run', credits=2):
        self.counter += 1
        value = {'schema': b.INTENT_SCHEMA, 'commission_sha256': self.pin,
                 'operation': operation, 'nonce': sha(('frontend-%d' % self.counter).encode())}
        if operation == 'run': value['credits'] = credits
        return value

    def state(self):
        return load_json_strict(self.state_path.read_bytes(), require_canonical=True)

    def no_dispatch(self, intent, **kwargs):
        state = self.state_path.read_bytes(); anchor = self.fixture.anchor.read_bytes()
        sequence = self.client.sequence
        with self.assertRaises(ResourceError): self.broker.dispatch(intent, **kwargs)
        self.assertEqual(self.state_path.read_bytes(), state)
        self.assertEqual(self.fixture.anchor.read_bytes(), anchor)
        self.assertEqual(self.client.sequence, sequence)
        self.assertIsNone(self.broker.last_record)

    def test_read_has_sanitized_response_and_exact_original_record(self):
        record = self.broker.dispatch(self.intent('read'))
        summary = b.verify_broker_record(record, self.commission)
        self.assertEqual(summary['outcome'], 'read')
        self.assertFalse(summary['mutation_issued'])
        self.assertEqual(set(record['response']), {'schema', 'commission_sha256',
            'authority_commission_sha256', 'root_provision_sha256', 'intent_sha256',
            'operation', 'outcome', 'cursor', 'pending_retained', 'worker_reissued', 'promotion_authorized'})

    def test_run_consumes_exact_nonce_before_am_dispatch(self):
        intent = self.intent(); record = self.broker.dispatch(intent)
        self.assertEqual(record['admitted_state']['consumed_nonces'], [intent['nonce']])
        self.assertEqual(record['admitted_state']['pending']['intent'], intent)
        self.assertEqual(record['issued_request']['request_nonce'], intent['nonce'])
        self.assertEqual(record['response']['outcome'], 'complete')
        self.assertIsNone(record['state_after']['pending'])
        self.assertEqual(self.fixture.authority.calls, 1)

    def test_replayed_run_nonce_cannot_issue_another_worker(self):
        intent = self.intent(); self.broker.dispatch(intent)
        self.no_dispatch(intent)
        self.assertEqual(self.fixture.authority.calls, 1)

    def test_read_nonce_is_also_consumed(self):
        intent = self.intent('read'); self.broker.dispatch(intent)
        self.no_dispatch(intent)

    def test_extra_private_path_field_rejected_before_network(self):
        value = self.intent(); value['anchor_path'] = '/untrusted/anchor'
        self.no_dispatch(value)

    def test_forbidden_administrative_operation_rejected(self):
        value = self.intent(); value['operation'] = 'provision'
        self.no_dispatch(value)

    def test_frontend_cannot_substitute_commission_pin(self):
        value = self.intent(); value['commission_sha256'] = sha(b'other commission')
        self.no_dispatch(value)

    def test_boolean_credit_is_not_a_natural_allowance(self):
        self.no_dispatch(self.intent(credits=True))

    def test_credit_request_cannot_exceed_commission(self):
        self.no_dispatch(self.intent(credits=17))

    def test_read_cannot_smuggle_credits(self):
        value = self.intent('read'); value['credits'] = 2
        self.no_dispatch(value)

    def test_lost_reply_retains_broker_and_am_pending(self):
        record = self.broker.dispatch(self.intent(), abandon_response=True)
        self.assertEqual(record['response']['outcome'], 'pending')
        self.assertIsNotNone(self.state()['pending'])
        self.assertIsNotNone(self.fixture.anchor_value()['pending'])
        self.assertTrue(b.verify_broker_record(record, self.commission)['pending_retained'])

    def test_pending_run_blocks_retry_without_network(self):
        self.broker.dispatch(self.intent(), abandon_response=True)
        self.no_dispatch(self.intent())
        self.no_dispatch(self.intent('read'))

    def test_reconciliation_resolves_history_without_worker_reissue(self):
        self.broker.dispatch(self.intent(), abandon_response=True)
        self.fixture.wait_results(1)
        before = self.fixture.authority.calls
        record = self.broker.dispatch(self.intent('reconcile'))
        self.assertEqual(record['issued_request']['operation'], 'read')
        self.assertEqual(record['response']['outcome'], 'reconciled')
        self.assertFalse(record['response']['worker_reissued'])
        self.assertIsNone(self.state()['pending'])
        self.assertEqual(self.fixture.authority.calls, before)

    def test_pending_survives_broker_reconstruction(self):
        self.broker.dispatch(self.intent(), abandon_response=True)
        self.fixture.wait_results(1)
        self.broker = self.new_broker()
        self.no_dispatch(self.intent())
        record = self.broker.dispatch(self.intent('reconcile'))
        self.assertFalse(record['response']['pending_retained'])

    def test_broker_crash_after_am_completion_reconciles_without_reissue(self):
        record = self.broker.dispatch(self.intent())
        # The AM reply/anchor committed, while the broker's last retained state
        # is its original write-ahead state. No campaign or AM state is rewound.
        self.state_path.write_bytes(canonical(record['admitted_state']))
        self.broker = self.new_broker()
        before = self.fixture.authority.calls
        reconciled = self.broker.dispatch(self.intent('reconcile'))
        self.assertEqual(reconciled['am_operation']['operation'], 'read')
        self.assertEqual(reconciled['response']['outcome'], 'reconciled')
        self.assertEqual(self.fixture.authority.calls, before)

    def test_reconcile_requires_unresolved_intent(self):
        self.no_dispatch(self.intent('reconcile'))

    def test_durable_aggregate_denial_settles_without_worker(self):
        record = self.broker.dispatch(self.intent(credits=13))
        self.assertEqual(record['response']['outcome'], 'denied')
        self.assertEqual(self.fixture.authority.calls, 0)

    def test_promotion_mode_rejected_before_state_or_network_mutation(self):
        self.no_dispatch(self.intent(), mode='promotion')

    def test_all_declared_categories_cannot_make_reference_backend_promoting(self):
        contract = accounting.reference_coverage(budget=2 * len(accounting.CATEGORIES))
        for row in contract['coverage']:
            row.update(observed=1, upper_bound=2, meter=sha(row['category'].encode()))
        self.assertTrue(accounting.coverage_report(contract)['all_categories_observed_and_bounded'])
        self.assertFalse(accounting.admission_report(contract, mode='promotion')['admitted'])

    def test_tampered_admitted_nonce_inventory_rejected(self):
        record = self.broker.dispatch(self.intent()); record['admitted_state']['consumed_nonces'] = []
        with self.assertRaises(ResourceError): b.verify_broker_record(record, self.commission)

    def test_tampered_issued_nonce_rejected(self):
        record = self.broker.dispatch(self.intent()); record['issued_request']['request_nonce'] = sha(b'forged')
        with self.assertRaises(ResourceError): b.verify_broker_record(record, self.commission)

    def test_tampered_public_result_rejected(self):
        record = self.broker.dispatch(self.intent()); record['response']['promotion_authorized'] = True
        with self.assertRaises(ResourceError): b.verify_broker_record(record, self.commission)

    def test_substituted_observed_tls_peer_rejected(self):
        record = self.broker.dispatch(self.intent('read'))
        record['am_exchange']['peer_certificate_der_hex'] = b'forged certificate'.hex()
        record['am_exchange']['peer_certificate_sha256'] = sha(b'forged certificate')
        with self.assertRaises(ResourceError): b.verify_broker_record(record, self.commission)

    def test_forged_original_operation_kind_rejected(self):
        record = self.broker.dispatch(self.intent('read'))
        record['am_operation']['operation'] = 'run'
        with self.assertRaises(ResourceError): b.verify_broker_record(record, self.commission)

    def test_tampered_writeahead_anchor_rejected(self):
        record = self.broker.dispatch(self.intent())
        record['am_operation']['pending_before_send']['headers'] = []
        with self.assertRaises(ResourceError): b.verify_broker_record(record, self.commission)

    def test_am_anchor_rollback_rejected(self):
        before = self.fixture.anchor.read_bytes(); self.broker.dispatch(self.intent())
        self.fixture.anchor.write_bytes(before)
        self.no_dispatch(self.intent())

    def test_wrong_independent_commission_pin_rejected(self):
        with self.assertRaises(ResourceError):
            b.ProtectedAuthorityBroker(self.commission, expected_commission_sha256=sha(b'wrong'),
                                       client=self.client, state_path=self.state_path)

    def test_reprovisioning_existing_broker_state_rejected(self):
        with self.assertRaises(ResourceError):
            b.provision_broker_state(self.state_path, self.commission,
                expected_commission_sha256=self.pin, trusted_headers=self.fixture.anchor_value()['headers'])

    def test_re_pinned_scope_escalation_rejected(self):
        commission = copy.deepcopy(self.commission); commission['scope']['promotion_authorized'] = True
        with self.assertRaises(ResourceError):
            b.validate_commission(commission, expected_commission_sha256=b.commission_digest(commission))

    def test_re_pinned_source_substitution_rejected(self):
        commission = copy.deepcopy(self.commission); commission['controller_source_sha256'] = sha(b'wrong')
        with self.assertRaises(ResourceError):
            b.validate_commission(commission, expected_commission_sha256=b.commission_digest(commission))

    def test_unknown_mode_or_nonboolean_abandonment_rejected(self):
        self.no_dispatch(self.intent(), mode='automatic-promotion')
        self.no_dispatch(self.intent(), abandon_response=1)
