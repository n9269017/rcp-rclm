"""AO formal interface controls using explicitly synthetic development records.

These tests never claim native process capture, physical deployment, or Lean
execution. The application separately runs the pinned compiler against records
independently reconstructed by PreparedServiceLifecycle.
"""
from copy import deepcopy
from pathlib import Path
import re
import unittest

from rcp_rclm_runtime_v5.phase17 import service_lifecycle as ledger
from rcp_rclm_runtime_v5.phase17 import service_lifecycle_lean as formal
from rcp_rclm_runtime_v5.phase17.resource_ledger import sha

ROOT = Path(__file__).resolve().parents[3]


def development_evidence():
    """Build pure replay fixtures, explicitly without starting native workers."""
    commission = ledger.make_commission(
        bindings={name: sha(('synthetic-' + name).encode()) for name in ledger.BINDINGS},
        lifetime_envelope=[1, 3, 8, 8192, 8192, 4], total_budget=[2, 6, 16, 16384, 16384, 8],
        commissioning_nonce=sha(b'synthetic-development-commission'))
    pin = ledger.commission_digest(commission)

    def new():
        events, state, cursor = [], ledger._initial(), None

        def append(kind, payload):
            nonlocal state, cursor
            state = ledger._transition(commission, state, cursor, kind, payload)
            event = ledger._event(pin, cursor, kind, payload, state)
            events.append(event); cursor = ledger._cursor(pin, event)

        def reserve(identifier, kind='reserve'):
            grant = ledger.make_grant(commission, state, cursor, identifier)
            append(kind, {'grant': grant})
            return grant

        def export():
            return {'schema': ledger.SCHEMA, 'commission': deepcopy(commission),
                'commission_sha256': pin, 'events': deepcopy(events),
                'final_cursor': deepcopy(cursor), 'scope': deepcopy(ledger.SCOPE)}

        append('provision', {'commission_sha256': pin})
        return append, reserve, export

    append, reserve, export = new()
    for index in range(2):
        append('open', {'owner_nonce': sha(('synthetic-owner-' + str(index)).encode())})
        grant = reserve('synthetic-lifetime-' + str(index))
        append('launch', {'grant': grant})
        append('charge', {'grant': grant, 'delta': [0, 1, 1, 2 + index, 32, 1],
            'event_id': 'synthetic-input-' + str(index), 'evidence_sha256': sha(b'synthetic-input')})
        append('finish', {'grant': grant, 'outcome': 'completed', 'evidence_sha256': sha(b'synthetic-closeout')})
    reserve('synthetic-denied-lifetime', 'deny')
    main = export()
    append, reserve, export = new()
    append('open', {'owner_nonce': sha(b'synthetic-interrupted-owner')})
    reserve('synthetic-interrupted-lifetime')
    return main, export()


def development_projection():
    main, interrupted = development_evidence()
    value = formal.projection_from_evidence(main, interrupted,
        interrupted_reopen_owner=sha(b'synthetic-refused-owner'))
    return {'packet_sha256': sha(b'synthetic-development-packet-not-native-capture'), **value}


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.projection = development_projection()
        self.semantic = {key: value for key, value in self.projection.items() if key != 'packet_sha256'}

    def step(self, kind, ordinal=0):
        return [step for step in self.semantic['steps'] if step['command']['kind'] == kind][ordinal]

    def test_exact_two_lifetimes_durable_denial_and_separate_interrupted_control(self):
        self.assertEqual(formal.validate_projection(self.semantic), self.semantic)
        denied = self.step('deny')
        self.assertEqual(denied['before']['reserved'], denied['after']['reserved'])
        self.assertNotEqual(denied['before']['current'], denied['after']['current'])
        self.assertIsNone(self.semantic['budget_refusal']['after'])
        self.assertIsNotNone(self.semantic['interrupted_reservation']['after']['pending'])

    def test_unknown_deployment_or_physical_claim_cannot_enter_projection(self):
        for key in ('independently_protected', 'complete_resource_accounting', 'root_accepted'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                formal.validate_projection({**self.semantic, key: True})

    def test_exact_fixed_six_dimensions_and_integer_quantities(self):
        for quantity in ([1, 3, 8, 8192, 8192], [1, 3, 8, 8192, 8192, 4, 0],
                         [1, True, 8, 8192, 8192, 4], [1, -1, 8, 8192, 8192, 4]):
            altered = deepcopy(self.semantic); altered['commission']['envelope'] = quantity
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                formal.validate_projection(altered)

    def test_runtime_source_and_owner_substitution_are_refused(self):
        for field in ('source', 'owner'):
            altered = deepcopy(self.semantic)
            target = next(step for step in altered['steps'] if step['command']['kind'] == 'reserve')
            target['runtime'][field] = sha(b'substituted-runtime-binding')
            with self.subTest(field=field), self.assertRaises(ValueError):
                formal.validate_projection(altered)

    def test_copied_stale_cursor_and_head_do_not_validate(self):
        for key in ('epoch', 'serial', 'head'):
            altered = deepcopy(self.semantic)
            cursor = altered['steps'][1]['expected']
            cursor[key] = sha(b'wrong-head') if key == 'head' else cursor[key] + 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                formal.validate_projection(altered)

    def test_reservation_must_precede_launch(self):
        altered = deepcopy(self.semantic)
        reserve_index = next(i for i, step in enumerate(altered['steps']) if step['command']['kind'] == 'reserve')
        altered['steps'][reserve_index]['command'] = deepcopy(self.step('launch')['command'])
        with self.assertRaises(ValueError): formal.validate_projection(altered)

    def test_closed_lifetime_cannot_refund_prepaid_charge(self):
        altered = deepcopy(self.semantic)
        next(step for step in altered['steps'] if step['command']['kind'] == 'close')['after']['reserved'] = [0] * 6
        with self.assertRaises(ValueError): formal.validate_projection(altered)

    def test_restart_does_not_reuse_previous_lifetime_reservation(self):
        altered = deepcopy(self.semantic)
        reserves = [step for step in altered['steps'] if step['command']['kind'] == 'reserve']
        reserves[1]['after']['reserved'] = deepcopy(reserves[0]['after']['reserved'])
        with self.assertRaises(ValueError): formal.validate_projection(altered)

    def test_raw_input_attempt_and_bytes_must_be_charged(self):
        for coordinate in (2, 3):
            altered = deepcopy(self.semantic)
            target = next(step for step in altered['steps'] if step['command']['kind'] == 'charge')
            target['after']['pending']['used'][coordinate] = target['before']['pending']['used'][coordinate]
            with self.subTest(coordinate=coordinate), self.assertRaises(ValueError):
                formal.validate_projection(altered)

    def test_receipt_requires_exact_source_grant_lifetime_and_used_quantities(self):
        for field in ('source', 'grant', 'lifetime_id', 'used'):
            altered = deepcopy(self.semantic)
            receipt = next(step for step in altered['steps'] if step['command']['kind'] == 'close')['command']['receipt']
            receipt[field] = [0] * 6 if field == 'used' else sha(b'foreign-receipt')
            with self.subTest(field=field), self.assertRaises(ValueError):
                formal.validate_projection(altered)

    def test_usage_event_replay_is_refused(self):
        altered = deepcopy(self.semantic)
        target = next(step for step in altered['steps'] if step['command']['kind'] == 'charge')
        target['before']['pending']['event_ids'].append(target['command']['event_id'])
        with self.assertRaises(ValueError): formal.validate_projection(altered)

    def test_denied_reserve_is_distinct_from_actual_journal_denial(self):
        altered = deepcopy(self.semantic)
        altered['budget_refusal']['after'] = deepcopy(self.step('deny')['after'])
        with self.assertRaises(ValueError): formal.validate_projection(altered)

    def test_interrupted_reservation_remains_pending_and_unlaunched(self):
        for change in ('clear_pending', 'refund', 'accept_reopen'):
            altered = deepcopy(self.semantic)
            if change == 'clear_pending': altered['interrupted_reservation']['after']['pending'] = None
            elif change == 'refund': altered['interrupted_reservation']['after']['reserved'] = [0] * 6
            else: altered['interrupted_reopen']['after'] = deepcopy(altered['interrupted_reopen']['before'])
            with self.subTest(change=change), self.assertRaises(ValueError):
                formal.validate_projection(altered)

    def test_selected_trace_must_include_every_original_step_in_order(self):
        for change in ('missing', 'reordered'):
            altered = deepcopy(self.semantic)
            if change == 'missing': altered['steps'].pop(3)
            else: altered['steps'][2], altered['steps'][3] = altered['steps'][3], altered['steps'][2]
            with self.subTest(change=change), self.assertRaises(ValueError):
                formal.validate_projection(altered)

    def test_original_ledger_bytes_are_replayed_before_projection(self):
        main, interrupted = development_evidence()
        main['events'][3]['after']['pending']['used'][2] += 1
        with self.assertRaises(ValueError): formal.projection_from_evidence(main, interrupted)

    def test_isolated_control_cannot_launch_or_count_as_main_campaign(self):
        main, interrupted = development_evidence()
        with self.assertRaises(ValueError): formal.projection_from_evidence(main, main)
        self.assertEqual(len(formal.projection_from_evidence(main, interrupted)['steps']), len(main['events']) - 1)

    def test_semantic_uninstalled_reopen_head_is_explicit_and_fresh(self):
        reopen = self.semantic['interrupted_reopen']
        self.assertNotEqual(reopen['next_head'], reopen['before']['current']['head'])
        self.assertNotIn(reopen['runtime']['owner'], reopen['before']['owner_nonces'])
        self.assertIsNone(reopen['after'])

    def test_rendered_certificate_keeps_whole_ledger_clone_and_promotion_boundary(self):
        raw = formal.render_selected(self.projection, ROOT)
        self.assertIn(b'theorem selected_whole_ledger_clone_boundary', raw)
        self.assertIn(b'theorem selected_input_consumption', raw)
        self.assertIn(b'theorem selected_no_promotion', raw)
        self.assertIsNone(re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', raw))

    def test_validated_projection_is_copied_and_has_no_native_acceptance_bit(self):
        checked = formal.validate_projection(self.semantic)
        checked['commission']['budget'][0] += 1
        self.assertNotEqual(checked, self.semantic)
        self.assertEqual(set(self.semantic), formal.PROJECTION_FIELDS)


class CompilerContractTests(unittest.TestCase):
    def audit_text(self):
        return ''.join("'" + name + "' does not depend on any axioms\n" for name in formal.NAMES)

    def test_exact_complete_ordered_audit_inventory(self):
        output = self.audit_text(); rows = output.splitlines(keepends=True)
        self.assertEqual(list(formal.parse_audits(output)), list(formal.NAMES))
        for changed in (''.join(rows[:-1]), ''.join([rows[1], rows[0], *rows[2:]]), output + rows[0]):
            with self.assertRaises(ValueError): formal.parse_audits(changed)

    def test_unapproved_or_repeated_axiom_dependencies_cannot_pass(self):
        for dependency in ('sorryAx', 'untrustedProof', 'Classical.choice, Classical.choice'):
            output = self.audit_text().replace('does not depend on any axioms',
                'depends on axioms: [' + dependency + ']', 1)
            with self.subTest(dependency=dependency), self.assertRaises(ValueError): formal.parse_audits(output)

    def test_exact_designated_semantic_rejection_parser(self):
        for label in formal.NEGATIVES:
            raw = formal.render_negative(label); line, column = formal.negative_location(raw)
            output = f'{label}.lean:{line}:{column}: error: Tactic `decide` proved that the proposition\n  False\nis false\n'
            with self.subTest(label=label):
                self.assertTrue(formal.validate_negative(label, raw, output, '', 1)['intended_rejection'])

    def test_arbitrary_failure_exit_or_extra_diagnostic_cannot_pass(self):
        label = formal.NEGATIVES[0]; raw = formal.render_negative(label)
        line, column = formal.negative_location(raw)
        good = f'{label}.lean:{line}:{column}: error: Tactic `decide` proved that the proposition\n  False\nis false\n'
        for output, errors, code in (('error: unknown module\n', '', 1), (good, 'crash', 1),
                (good, '', 0), (good, '', True), (good, '', -9), (good + 'warning: unrelated\n', '', 1)):
            with self.subTest(code=code, errors=errors), self.assertRaises(ValueError):
                formal.validate_negative(label, raw, output, errors, code)

    def test_wrong_negative_source_cannot_reuse_matching_diagnostic(self):
        label = formal.NEGATIVES[0]; raw = formal.render_negative(label)
        with self.assertRaises(ValueError):
            formal.validate_negative(label, raw.replace(b'  decide\n', b'  trivial\n'), '', '', 1)


if __name__ == '__main__':
    unittest.main()
