"""AO lifecycle budget, atomic publication and uncertainty regression checks.

These tests use temporary ledger files and fault injection only. They launch no
authority, resident broker, worker or compiler and establish no physical meter
or deployment claim.
"""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import service_lifecycle as life
from rcp_rclm_runtime_v5.phase17.resource_ledger import ResourceError, ResourceExhausted, canonical, sha


class ServiceLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='phase17ao-ledger-test-')
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name).resolve(strict=True)
        self.path = self.parent / 'budget.json'
        self.envelope = [1, 4, 3, 64, 128, 2]
        self.commission = life.make_commission(
            bindings={key: sha(key.encode()) for key in life.BINDINGS},
            lifetime_envelope=self.envelope, total_budget=[2 * n for n in self.envelope],
            commissioning_nonce=sha(b'commission'))
        self.pin = life.commission_digest(self.commission)
        self.genesis = life.provision(self.path, self.commission, expected_commission_sha256=self.pin)
        self.sequence = 0

    def open(self, *, path=None, nonce=None, cursor=None):
        self.sequence += 1
        value = life.ServiceLifecycleLedger(path or self.path,
            expected_commission_sha256=self.pin,
            owner_nonce=nonce or sha(('owner-' + str(self.sequence)).encode()),
            expected_cursor=cursor)
        self.addCleanup(value.close)
        return value

    def launched(self, ledger, lifetime='first'):
        grant = ledger.reserve(lifetime, expected_cursor=ledger.cursor)
        ledger.consume_launch(grant, expected_cursor=ledger.cursor)
        return grant

    def finish(self, ledger, grant, *, outcome='completed'):
        ledger.finish(grant, expected_cursor=ledger.cursor, outcome=outcome,
                      evidence_sha256=sha(b'original terminal evidence'))

    def test_commission_and_genesis_round_trip(self):
        checked = life.verify_evidence(self.genesis, expected_commission_sha256=self.pin)
        self.assertEqual(checked['state']['reserved'], [0] * 6)
        self.assertEqual(checked['cursor']['epoch'], 0)
        self.assertEqual(checked['commission']['dimensions'], list(life.DIMENSIONS))

    def test_external_commission_pin_is_required(self):
        with self.assertRaises(ResourceError):
            life.verify_evidence(self.genesis, expected_commission_sha256=sha(b'other provision'))

    def test_commission_rejects_changed_dimensions_or_escalated_scope(self):
        for change in ('dimensions', 'scope'):
            value = copy.deepcopy(self.commission)
            if change == 'dimensions':
                value['dimensions'].reverse()
            else:
                value['scope']['complete_resource_accounting'] = True
            with self.subTest(change=change), self.assertRaises(ResourceError):
                life.validate_commission(value, expected_commission_sha256=life.commission_digest(value))

    def test_vector_rejects_boolean_negative_float_and_overflow(self):
        for value in (True, False, -1, 1.0, '1', 2 ** 63):
            delta = list(self.envelope); delta[2] = value
            with self.subTest(value=value), self.assertRaises(ResourceError):
                life.vector(delta)

    def test_lifetime_envelope_is_one_and_other_dimensions_positive(self):
        for index in range(6):
            envelope = list(self.envelope); envelope[index] = 0
            with self.subTest(index=index), self.assertRaises(ResourceError):
                life.make_commission(bindings=self.commission['bindings'], lifetime_envelope=envelope,
                    total_budget=self.commission['total_budget'], commissioning_nonce=sha(b'c'))

    def test_provision_does_not_overwrite_existing_budget(self):
        before = self.path.read_bytes()
        with self.assertRaises(ResourceError):
            life.provision(self.path, self.commission, expected_commission_sha256=self.pin)
        self.assertEqual(self.path.read_bytes(), before)

    def test_open_does_not_create_missing_budget(self):
        with self.assertRaises(ResourceError):
            self.open(path=self.parent / 'missing.json')
        self.assertFalse((self.parent / 'missing.json').exists())

    def test_external_cursor_rejects_rolled_back_view(self):
        ledger = self.open(cursor=self.genesis['final_cursor'])
        current = ledger.cursor
        with self.assertRaises(ResourceError):
            life.verify_evidence(self.genesis, expected_commission_sha256=self.pin,
                                 expected_cursor=current)

    def test_lifetime_reservation_charges_full_envelope_before_launch(self):
        ledger = self.open()
        cursor = ledger.cursor
        grant = ledger.reserve('first', expected_cursor=cursor)
        self.assertEqual(grant['reservation_cursor'], cursor)
        self.assertEqual(ledger.state['reserved'], self.envelope)
        self.assertEqual(ledger.state['pending']['phase'], 'reserved')
        self.assertEqual(ledger.state['pending']['used'], [0] * 6)
        self.assertEqual(ledger.cursor['serial'], cursor['serial'] + 1)

    def test_launch_consumption_is_once_only_even_with_new_cursor(self):
        ledger = self.open(); grant = self.launched(ledger)
        before = self.path.read_bytes()
        with self.assertRaises(ResourceError):
            ledger.consume_launch(grant, expected_cursor=ledger.cursor)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(ledger.state['pending']['used'], [1, 1, 0, 0, 0, 0])

    def test_charge_before_launch_is_refused(self):
        ledger = self.open(); grant = ledger.reserve('first', expected_cursor=ledger.cursor)
        with self.assertRaises(ResourceError):
            ledger.charge_input(grant, b'{bad json', event_id='raw-1', expected_cursor=ledger.cursor)
        self.assertEqual(ledger.state['pending']['used'], [0] * 6)

    def test_stale_compare_and_publish_cursor_cannot_issue_launch(self):
        ledger = self.open(); old = ledger.cursor
        grant = ledger.reserve('first', expected_cursor=old)
        with self.assertRaises(ResourceError):
            ledger.consume_launch(grant, expected_cursor=old)
        self.assertEqual(ledger.state['pending']['phase'], 'reserved')

    def test_well_formed_substituted_grant_is_refused(self):
        ledger = self.open(); before = ledger.state; cursor = ledger.cursor
        grant = ledger.reserve('first', expected_cursor=cursor)
        replacement = life.make_grant(self.commission, before, cursor, 'other')
        with self.assertRaises(ResourceError):
            ledger.consume_launch(replacement, expected_cursor=ledger.cursor)
        self.assertEqual(ledger.state['pending']['grant'], grant)

    def test_malformed_input_attempt_is_charged_without_parsing(self):
        ledger = self.open(); grant = self.launched(ledger)
        raw = b'\xff{invalid-json}\n'
        event = ledger.charge_input(grant, raw, event_id='malformed-1', expected_cursor=ledger.cursor)
        self.assertEqual(ledger.state['pending']['used'], [1, 1, 1, len(raw), 0, 0])
        self.assertEqual(event['payload']['evidence_sha256'], sha(raw))

    def test_replayed_usage_identity_does_not_charge_or_dispatch_again(self):
        ledger = self.open(); grant = self.launched(ledger)
        ledger.charge_input(grant, b'x', event_id='same', expected_cursor=ledger.cursor)
        before = self.path.read_bytes()
        with self.assertRaises(ResourceError):
            ledger.charge_input(grant, b'x', event_id='same', expected_cursor=ledger.cursor)
        self.assertEqual(self.path.read_bytes(), before)

    def test_input_count_cap_refuses_before_fourth_input(self):
        ledger = self.open(); grant = self.launched(ledger)
        for number in range(3):
            ledger.charge_input(grant, b'?', event_id=str(number), expected_cursor=ledger.cursor)
        before = self.path.read_bytes()
        with self.assertRaises(ResourceError):
            ledger.charge_input(grant, b'?', event_id='over', expected_cursor=ledger.cursor)
        self.assertEqual(self.path.read_bytes(), before)

    def test_input_byte_cap_refuses_before_forwarding(self):
        ledger = self.open(); grant = self.launched(ledger)
        with self.assertRaises(ResourceError):
            ledger.charge_input(grant, b'x' * 65, event_id='oversize', expected_cursor=ledger.cursor)
        self.assertEqual(ledger.state['pending']['used'], [1, 1, 0, 0, 0, 0])

    def test_response_process_and_tls_caps_are_independent(self):
        ledger = self.open(); grant = self.launched(ledger)
        for delta in ([0, 4, 0, 0, 0, 0], [0, 0, 0, 0, 129, 0], [0, 0, 0, 0, 0, 3]):
            with self.subTest(delta=delta), self.assertRaises(ResourceError):
                ledger.charge(grant, delta, event_id='over', expected_cursor=ledger.cursor)
        self.assertEqual(ledger.state['pending']['used'], [1, 1, 0, 0, 0, 0])

    def test_ordinary_charge_cannot_mint_another_lifetime(self):
        ledger = self.open(); grant = self.launched(ledger)
        with self.assertRaises(ResourceError):
            ledger.charge(grant, [1, 0, 0, 0, 0, 0], event_id='mint', expected_cursor=ledger.cursor)

    def test_completion_does_not_refund_unused_allowance(self):
        ledger = self.open(); grant = self.launched(ledger)
        self.finish(ledger, grant)
        self.assertIsNone(ledger.state['pending'])
        self.assertEqual(ledger.state['reserved'], self.envelope)
        self.assertEqual(ledger.state['closed'][0]['used'], [1, 1, 0, 0, 0, 0])

    def test_failed_terminal_lifetime_does_not_refund(self):
        ledger = self.open(); grant = self.launched(ledger)
        self.finish(ledger, grant, outcome='failed')
        self.assertEqual(ledger.state['reserved'], self.envelope)
        self.assertEqual(ledger.state['closed'][0]['outcome'], 'failed')

    def test_close_handle_does_not_synthesize_terminal_evidence(self):
        ledger = self.open(); grant = self.launched(ledger)
        before = self.path.read_bytes(); ledger.close()
        self.assertEqual(self.path.read_bytes(), before)
        evidence = life.read_evidence(self.path, expected_commission_sha256=self.pin)
        checked = life.verify_evidence(evidence, expected_commission_sha256=self.pin)
        self.assertEqual(checked['state']['pending']['grant'], grant)
        self.assertEqual(checked['state']['closed'], [])

    def test_interrupted_reservation_blocks_reopening_without_mutation(self):
        ledger = self.open(); ledger.reserve('interrupted', expected_cursor=ledger.cursor)
        before = self.path.read_bytes(); ledger.close()
        with self.assertRaises(ResourceError):
            self.open()
        self.assertEqual(self.path.read_bytes(), before)

    def test_interrupted_launch_blocks_reopening_without_mutation(self):
        ledger = self.open(); self.launched(ledger)
        before = self.path.read_bytes(); ledger.close()
        with self.assertRaises(ResourceError):
            self.open()
        self.assertEqual(self.path.read_bytes(), before)

    def test_finished_lifetime_reopens_with_new_epoch_and_same_charge(self):
        first = self.open(); grant = self.launched(first); self.finish(first, grant)
        cursor = first.cursor; first.close()
        second = self.open(cursor=cursor)
        self.assertEqual(second.state['epoch'], 2)
        self.assertEqual(second.state['reserved'], self.envelope)
        with self.assertRaises(ResourceError):
            second.consume_launch(grant, expected_cursor=second.cursor)

    def test_owner_nonce_replay_is_refused(self):
        nonce = sha(b'owner')
        first = self.open(nonce=nonce); first.close()
        before = self.path.read_bytes()
        with self.assertRaises(ResourceError):
            self.open(nonce=nonce)
        self.assertEqual(self.path.read_bytes(), before)

    def test_reserved_lifetime_identity_cannot_be_reused(self):
        ledger = self.open(); grant = self.launched(ledger); self.finish(ledger, grant)
        with self.assertRaises(ResourceError):
            ledger.reserve('first', expected_cursor=ledger.cursor)
        self.assertEqual(ledger.state['reserved'], self.envelope)

    def test_third_lifetime_denied_after_two_complete_lifetimes(self):
        first = self.open(); grant = self.launched(first, 'first'); self.finish(first, grant)
        cursor = first.cursor; first.close()
        second = self.open(cursor=cursor)
        grant = self.launched(second, 'second'); self.finish(second, grant)
        with self.assertRaises(ResourceExhausted):
            second.reserve('third', expected_cursor=second.cursor)
        checked = life.verify_evidence(second.export_evidence(), expected_commission_sha256=self.pin)
        self.assertEqual(checked['state']['reserved'], [2 * n for n in self.envelope])
        self.assertIsNone(checked['state']['pending'])
        self.assertEqual(checked['summary']['budget_denials'], 1)
        self.assertEqual(checked['summary']['lifetimes_reserved'], 2)

    def test_exclusive_owner_lock_blocks_second_live_handle(self):
        first = self.open()
        before = self.path.read_bytes()
        with self.assertRaises((OSError, ResourceError)):
            self.open()
        self.assertEqual(first.export_evidence(), life.read_evidence(self.path, expected_commission_sha256=self.pin))
        self.assertEqual(self.path.read_bytes(), before)

    def test_external_file_mutation_stops_current_owner(self):
        ledger = self.open()
        self.path.write_bytes(canonical(self.genesis))
        with self.assertRaises(ResourceError):
            ledger.reserve('rollback', expected_cursor=self.genesis['final_cursor'])

    def test_fault_before_atomic_replace_retains_previous_image(self):
        ledger = self.open(); cursor = ledger.cursor; before = self.path.read_bytes()
        with patch.object(life.am, '_replace', side_effect=OSError('before replace')):
            with self.assertRaises(OSError):
                ledger.reserve('fault', expected_cursor=cursor)
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(ResourceError):
            ledger.export_evidence()
        ledger.close()
        reopened = self.open(cursor=cursor)
        self.assertEqual(reopened.state['reserved'], [0] * 6)

    def test_fault_after_atomic_replace_retains_charge_and_blocks_retry(self):
        ledger = self.open(); cursor = ledger.cursor
        original = life.am._replace
        def committed_then_failed(path, value):
            original(path, value)
            raise OSError('after replace before acknowledgement')
        with patch.object(life.am, '_replace', side_effect=committed_then_failed):
            with self.assertRaises(OSError):
                ledger.reserve('ambiguous', expected_cursor=cursor)
        ledger.close()
        evidence = life.read_evidence(self.path, expected_commission_sha256=self.pin)
        checked = life.verify_evidence(evidence, expected_commission_sha256=self.pin)
        self.assertEqual(checked['state']['reserved'], self.envelope)
        self.assertEqual(checked['state']['pending']['phase'], 'reserved')
        with self.assertRaises(ResourceError):
            self.open()

    def test_replay_rejects_deleted_changed_or_reordered_records(self):
        ledger = self.open(); grant = self.launched(ledger)
        ledger.charge_input(grant, b'x', event_id='input', expected_cursor=ledger.cursor)
        evidence = ledger.export_evidence()
        variants = []
        value = copy.deepcopy(evidence); value['events'].pop(2); variants.append(value)
        value = copy.deepcopy(evidence); value['events'][-1]['after']['reserved'][0] = 0; variants.append(value)
        value = copy.deepcopy(evidence); value['events'][2:4] = reversed(value['events'][2:4]); variants.append(value)
        for index, value in enumerate(variants):
            with self.subTest(index=index), self.assertRaises((ResourceError, TypeError, KeyError)):
                life.verify_evidence(value, expected_commission_sha256=self.pin)

    def test_export_is_an_independent_copy(self):
        ledger = self.open(); self.launched(ledger)
        exported = ledger.export_evidence()
        exported['events'][-1]['after']['reserved'][0] = 0
        self.assertEqual(ledger.state['reserved'], self.envelope)

    def test_copying_complete_root_does_not_establish_global_exclusivity(self):
        first = self.open(); first.close()
        clone_path = self.parent / 'clone.json'
        clone_path.write_bytes(self.path.read_bytes())
        clone_path.with_name(clone_path.name + '.lock').write_bytes(b'L')
        original = self.open(); clone = self.open(path=clone_path)
        first_grant = original.reserve('same-life', expected_cursor=original.cursor)
        clone_grant = clone.reserve('same-life', expected_cursor=clone.cursor)
        original.consume_launch(first_grant, expected_cursor=original.cursor)
        clone.consume_launch(clone_grant, expected_cursor=clone.cursor)
        self.assertFalse(original.export_evidence()['scope']['global_clone_exclusion_established'])
        self.assertFalse(clone.export_evidence()['scope']['physical_currentness_established'])

    def test_unknown_physical_accounting_and_promotion_claims_stay_false(self):
        ledger = self.open(); grant = self.launched(ledger); self.finish(ledger, grant)
        scope = life.verify_evidence(ledger.export_evidence(), expected_commission_sha256=self.pin)['summary']['scope']
        self.assertFalse(scope['complete_resource_accounting'])
        self.assertFalse(scope['promotion_authorized'])
        self.assertFalse(scope['independently_protected_deployment_established'])


if __name__ == '__main__':
    unittest.main()
