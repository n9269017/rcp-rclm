"""Selected evaluator computation, journal ordering and packet trust boundaries.

These runtime controls and comparisons are not Lean acceptance.  The integration
case reconstructs only the existing historical fixture, with no fresh campaign.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from functools import lru_cache
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import evaluation_trace as p

ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _y():
    raw = (ROOT / p.Y_PACKET).read_bytes()
    if p.sha(raw) != p.Y_PACKET_SHA:
        raise AssertionError('retained Y packet changed')
    return p.load_json_strict(raw)


@lru_cache(maxsize=1)
def _inputs():
    return p.inputs_from_transcript(_y(), (ROOT / p.FIXTURE_PATH).read_bytes())


@lru_cache(maxsize=1)
def _template():
    return p.packet_from_inputs(_y(), _inputs())


def _evaluation():
    return _template()['evaluation']


@lru_cache(maxsize=1)
def _prepared():
    return p.PreparedEvaluationTrace(p.canonical(_template()))


def _outcome_inputs():
    e = _evaluation()
    return dict(target_family=e['target_program']['family'], probes=copy.deepcopy(e['opening']['probes']),
        targets=copy.deepcopy(e['target_outputs']),
        inherited_families=[p.program_parameters(row['program'])['family'] for row in e['inherited_programs']],
        inherited_outputs=copy.deepcopy(e['inherited_outputs']),
        candidate_family=e['target_program']['family'], candidate_outputs=copy.deepcopy(e['candidate_outputs'][-1]))


class InterpreterTests(unittest.TestCase):
    def test_all_eight_family_arithmetic(self):
        probe = [3, -2, 7, -5]
        expected = [[7, -3, 15, -9], [2, 14, 13, 26], [11, -5, 3, -2],
                    [6, 7, 10, 15], [7, -4, 4, 1], [-5, -2, -5, -2],
                    [5, -6, 14, -4], [0, 3, 8, 12]]
        for family, target in enumerate(expected):
            with self.subTest(family=family):
                self.assertEqual(p.execute_vector({'family': family, 'variant': 1, 'a': 4, 'b': 3}, probe), target)

    def test_all_variants_and_signed_boundaries_match_existing_reference(self):
        from rcp_rclm_runtime_v5.phase17.challenge_protocol import vector_semantics
        for family, name in enumerate(p.FAMILIES):
            for variant in range(4):
                for a, b in ((-16, 16), (0, 0), (16, -16)):
                    for probe in ([-32, 0, 32, -1], [3, 3, -7, -7]):
                        with self.subTest(family=family, variant=variant, a=a, b=b, probe=probe):
                            self.assertEqual(p.execute_vector({'family': family, 'variant': variant, 'a': a, 'b': b}, probe),
                                             vector_semantics(name, variant, a, b, probe))

    def test_reference_does_not_call_production_interpreters(self):
        from rcp_rclm_runtime_v5.phase17 import challenge_protocol, metered_evaluation
        with patch.object(challenge_protocol, 'vector_semantics', side_effect=AssertionError('production semantics called')), \
             patch.object(challenge_protocol, 'execute_reference', side_effect=AssertionError('production interpreter called')), \
             patch.object(metered_evaluation.Work, 'execute', side_effect=AssertionError('production work called')):
            e = p.derive_evaluation(_y(), _inputs())
        self.assertEqual(e['verdicts'], [False] * 8 + [True])

    def test_inputs_are_not_mutated(self):
        program, probe = {'family': 7, 'variant': 3, 'a': -16, 'b': 16}, [3, -2, 3, -2]
        before = copy.deepcopy((program, probe))
        p.execute_vector(program, probe)
        self.assertEqual((program, probe), before)

    def test_complete_bounded_program_parameters_required(self):
        valid = {'family': 0, 'variant': 0, 'a': 0, 'b': 0}
        for key, value in (('family', True), ('family', -1), ('family', 8),
                           ('variant', False), ('variant', -1), ('variant', 4),
                           ('a', True), ('a', -17), ('b', 17), ('b', 0.0)):
            bad = {**valid, key: value}
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                p.execute_vector(bad, [0, 0, 0, 0])
        for bad in ({}, {**valid, 'extra': 1}):
            with self.assertRaises(ValueError): p.execute_vector(bad, [0, 0, 0, 0])

    def test_probe_shape_and_exact_integer_bounds_required(self):
        for probe in ([], [0] * 3, [0] * 5, (0, 0, 0, 0), [0, False, 0, 0],
                      [0, 0.0, 0, 0], [-33, 0, 0, 0], [33, 0, 0, 0]):
            with self.subTest(probe=probe), self.assertRaises(ValueError):
                p.execute_vector({'family': 0, 'variant': 0, 'a': 0, 'b': 0}, probe)

    def test_full_program_descriptor_operation_is_checked(self):
        program = copy.deepcopy(_evaluation()['candidate_programs'][-1]['program'])
        program['operation_id'] = p.metadata.OPERATIONS[0]
        with self.assertRaises(ValueError): p.program_parameters(program)

    def test_actual_target_outputs_are_complete(self):
        self.assertEqual(_evaluation()['target_outputs'],
            [[7, 4, -2, -26], [-10, -9, -8, -10], [15, 32, 24, -9], [-13, -10, -12, -7],
             [-21, 41, -42, -23], [-18, 20, -42, -1], [3, 41, -42, -25], [4, 27, -58, 9]])


class OutcomeTests(unittest.TestCase):
    def test_complete_actual_policy_and_verdict_prefix(self):
        e = _evaluation()
        self.assertEqual(e['choices'], [21, 28, 1, 29, 20, 5, 22, 7, 24])
        self.assertEqual(e['verdicts'], [False] * 8 + [True])
        self.assertTrue(all(row['nontrivial'] and not row['predecessor_pass'] for row in e['outcomes']))
        self.assertEqual([row['reason_codes'] for row in e['outcomes']], [[p.REJECTION_REASON]] * 8 + [[]])

    def test_actual_rejections_have_wrong_family_and_all_probe_mismatches(self):
        for row in _evaluation()['outcomes'][:-1]:
            self.assertFalse(row['family_matches'])
            self.assertEqual(row['probe_matches'], [False] * 8)
            self.assertEqual(row['first_mismatch'], 0)

    def test_same_family_inherited_program_fails_all_eight_probes(self):
        checks = _evaluation()['inherited_checks']
        self.assertEqual([row['family_matches'] for row in checks], [True] + [False] * 7)
        self.assertEqual(checks[0]['probe_matches'], [False] * 8)
        self.assertTrue(all(not row['passes'] for row in checks))

    def test_selected_program_matches_all_eight_and_has_no_failure_index(self):
        row = _evaluation()['outcomes'][-1]
        self.assertTrue(row['candidate_pass'])
        self.assertEqual(row['probe_matches'], [True] * 8)
        self.assertIsNone(row['first_mismatch'])

    def test_nontriviality_is_required_even_when_candidate_matches(self):
        args = _outcome_inputs(); args['targets'] = copy.deepcopy(args['probes'])
        args['candidate_outputs'] = copy.deepcopy(args['targets'])
        row = p.verdict_from_outputs(**args)
        self.assertFalse(row['nontrivial']); self.assertTrue(row['candidate_pass'])
        self.assertEqual(row['verdict'], 'reject')
        self.assertEqual(row['reason_codes'], [p.REJECTION_REASON])

    def test_predecessor_success_blocks_candidate_success(self):
        args = _outcome_inputs(); args['inherited_outputs'][0] = copy.deepcopy(args['targets'])
        row = p.verdict_from_outputs(**args)
        self.assertTrue(row['predecessor_pass']); self.assertTrue(row['candidate_pass'])
        self.assertFalse(row['passed'])

    def test_wrong_family_predecessor_does_not_defeat_novelty(self):
        args = _outcome_inputs(); args['inherited_outputs'][1] = copy.deepcopy(args['targets'])
        row = p.verdict_from_outputs(**args)
        self.assertFalse(row['predecessor_pass']); self.assertTrue(row['passed'])

    def test_family_guard_rejects_equal_outputs_from_wrong_family(self):
        args = _outcome_inputs(); args['candidate_family'] = 0
        row = p.verdict_from_outputs(**args)
        self.assertEqual(row['probe_matches'], [True] * 8)
        self.assertFalse(row['family_matches']); self.assertFalse(row['candidate_pass'])
        self.assertEqual(row['verdict'], 'reject')

    def test_last_probe_failure_is_checked_after_seven_successes(self):
        args = _outcome_inputs(); args['candidate_outputs'][7][3] += 1
        row = p.verdict_from_outputs(**args)
        self.assertEqual(row['probe_matches'], [True] * 7 + [False])
        self.assertEqual(row['first_mismatch'], 7); self.assertFalse(row['passed'])

    def test_first_mismatch_is_earliest_and_all_probes_are_retained(self):
        args = _outcome_inputs(); args['candidate_outputs'][3][0] += 1; args['candidate_outputs'][6][2] += 1
        row = p.verdict_from_outputs(**args)
        self.assertEqual(row['first_mismatch'], 3)
        self.assertEqual(row['probe_matches'], [True, True, True, False, True, True, False, True])

    def test_missing_inherited_program_or_output_is_rejected(self):
        for key in ('inherited_families', 'inherited_outputs'):
            args = _outcome_inputs(); args[key].pop()
            with self.subTest(key=key), self.assertRaises(ValueError): p.verdict_from_outputs(**args)

    def test_incomplete_or_noninteger_probe_outputs_are_rejected(self):
        for change in (lambda x: x.pop(), lambda x: x[0].pop(), lambda x: x[0].__setitem__(0, True),
                       lambda x: x[0].__setitem__(0, 1 << 63)):
            args = _outcome_inputs(); change(args['candidate_outputs'])
            with self.assertRaises(ValueError): p.verdict_from_outputs(**args)


class ReferenceScheduleTests(unittest.TestCase):
    def test_complete_153_operation_schedule_and_declared_cost(self):
        e = _evaluation()
        self.assertEqual(len(e['work']), 153)
        self.assertEqual([row['kind'] for row in e['work']], ['vector'] * 72 + (['candidate'] + ['vector'] * 8) * 9)
        self.assertEqual(e['resource']['spent'], [9, 144, 576, 576])
        self.assertEqual(e['resource']['charged_cost'], 4032)
        self.assertEqual(e['resource']['journal_events'], 308)

    def test_actual_historical_order_is_not_the_q_key_order(self):
        e = _evaluation(); order = e['inherited_work_order']
        self.assertEqual(order, [4, 0, 1, 3, 6, 7, 5, 2])
        self.assertEqual(sorted(order), list(range(8)))
        self.assertEqual([e['inherited_programs'][i]['program']['promotion_index'] for i in order], list(range(8)))
        for ni, qi in enumerate(order):
            row = e['work'][8 + ni * 8]
            self.assertEqual((row['identity'], row['program_index']), (f'inherited:{ni}:0', qi))
            self.assertEqual(p.load_json_strict(bytes.fromhex(row['output_hex'])), e['inherited_outputs'][qi][0])

    def test_all_work_inputs_and_outputs_match_existing_reference(self):
        from rcp_rclm_runtime_v5.phase17.metered_evaluation import Work
        for row in _evaluation()['work']:
            source, output = bytes.fromhex(row['input_hex']), bytes.fromhex(row['output_hex'])
            with self.subTest(identity=row['identity']):
                self.assertEqual(p.sha(source), row['input_sha256'])
                self.assertEqual(p.sha(output), row['output_sha256'])
                self.assertEqual(Work(row['kind'], row['identity'], source).execute(), output)

    def test_candidate_admission_hash_is_raw_descriptor_sha_not_public_key(self):
        e = _evaluation()
        for i, candidate in enumerate(e['candidate_programs']):
            row = e['work'][72 + i * 9]
            actual = p.load_json_strict(bytes.fromhex(row['output_hex']))['program_sha256']
            self.assertEqual(actual, p.sha(p.canonical(candidate['program'])))
            self.assertNotEqual(actual, candidate['key'])

    def test_every_captured_payload_has_exact_derived_verdict_and_context(self):
        for row in _evaluation()['outcomes']:
            actual = p.load_json_strict(bytes.fromhex(row['payload_hex']))
            for key in ('program_hash', 'artifact_hash', 'candidate_freeze_hash', 'evaluation_hash',
                        'challenge_commitment_hash', 'predecessor_state_hash', 'evaluation_index', 'verdict', 'reason_codes'):
                self.assertEqual(actual[key], row[key])
            self.assertTrue(all(value is False for value in actual['claims'].values()))


class PacketTests(unittest.TestCase):
    def test_prepared_is_immutable_and_views_are_detached(self):
        with self.assertRaises(FrozenInstanceError): _prepared().packet_bytes = b'{}'
        view = _prepared().packet; view['evaluation']['verdicts'][0] = True
        self.assertFalse(_prepared().packet['evaluation']['verdicts'][0])

    def test_actual_y_dependency_is_preserved_exactly(self):
        self.assertEqual(_prepared().objective_context().packet_bytes, (ROOT / p.Y_PACKET).read_bytes())

    def test_summary_inventory_is_bound_to_complete_packet(self):
        s = p.summary(_prepared())
        self.assertEqual((s['target_vector_calls'], s['inherited_vector_calls'], s['candidate_vector_calls']), (8, 64, 72))
        self.assertEqual((s['vector_calls'], s['candidate_attempts'], s['operations']), (144, 9, 153))
        self.assertEqual((s['input_values'], s['output_values'], s['rejections'], s['passes']), (576, 576, 8, 1))
        self.assertEqual((s['work_input_bytes'], s['work_output_bytes'], s['evaluation_payload_bytes']), (51906, 2816, 7947))
        self.assertEqual((s['json_images'], s['json_image_bytes']), (315, 62669))
        self.assertTrue(s['nontrivial']); self.assertFalse(s['predecessor_pass'])
        self.assertFalse(s['candidate_active']); self.assertFalse(s['promotion_authorized'])

    def test_immutable_canonical_packet_bytes_required(self):
        for raw in (b'', bytearray(b'{}'), b'{}\n', b'{"x":1,"x":2}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): p.PreparedEvaluationTrace(raw)
        with patch.object(p, 'MAX_BYTES', 1), self.assertRaises(ValueError): p.PreparedEvaluationTrace(b'{}')

    def test_wrong_external_packet_anchor_is_rejected(self):
        with self.assertRaises(ValueError):
            p.verify_packet_bytes(_prepared().packet_bytes, _prepared(), expected_sha256='0' * 64)

    def test_changed_external_packet_is_rejected_even_with_new_hash(self):
        raw = p.canonical({})
        with self.assertRaises(ValueError): p.verify_packet_bytes(raw, _prepared(), expected_sha256=p.sha(raw))

    def test_schema_policy_base_and_exact_fields_are_fixed(self):
        for key, value in (('schema', 'wrong'), ('policy', 'wrong'), ('base_commit', '0' * 40)):
            packet = {**_template(), key: value}
            with self.subTest(key=key), self.assertRaises(ValueError): p.validate_packet(packet)
        for extra in ({'extra': 1},):
            with self.assertRaises(ValueError): p.validate_packet({**_template(), **extra})

    def test_false_claims_cannot_be_escalated_or_retyped(self):
        for change in ({}, {k: 0 for k in p.FALSE_CLAIMS}, {k: k == 'root_transition_verified' for k in p.FALSE_CLAIMS}):
            with self.assertRaises(ValueError): p.validate_packet({**_template(), 'claims': change})

    def test_scope_profile_pins_and_bindings_cannot_be_replaced(self):
        for key in ('scope', 'profile', 'retained_y', 'bindings'):
            with self.subTest(key=key), self.assertRaises(ValueError): p.validate_packet({**_template(), key: {}})

    def test_rehashed_y_substitution_is_rejected(self):
        packet = dict(_template()); y = copy.deepcopy(_y()); y['bindings']['program_hash'] = '0' * 64
        packet['objective_context_packet'] = y; packet['objective_context_packet_sha256'] = p.sha(p.canonical(y))
        with self.assertRaisesRegex(ValueError, 'imported Y'): p.validate_packet(packet)

    def test_changed_or_mutable_transcript_is_rejected(self):
        raw = (ROOT / p.FIXTURE_PATH).read_bytes()
        for bad in (bytearray(raw), raw[:-1] + bytes([raw[-1] ^ 1]), raw[:-1]):
            with self.assertRaises(ValueError): p.inputs_from_transcript(_y(), bad)

    def test_transcript_hex_is_exact_and_canonical(self):
        for text in (_inputs()['transcript_hex'].upper(), '7b7d', 'zz', ''):
            with self.subTest(text=text[:20]), self.assertRaises(ValueError):
                p.derive_evaluation(_y(), {'transcript_hex': text})

    def test_all_claimed_outputs_and_boolean_checks_are_recomputed(self):
        edits = (
            lambda e: e['target_outputs'][0].__setitem__(0, 8),
            lambda e: e['inherited_outputs'][0][0].__setitem__(0, 8),
            lambda e: e['candidate_outputs'][8][7].__setitem__(3, 10),
            lambda e: e['inherited_checks'][0].__setitem__('passes', True),
            lambda e: e['outcomes'][0].__setitem__('passed', True),
            lambda e: e['outcomes'][0].__setitem__('first_mismatch', 1),
        )
        self._reject_edits(edits)

    def test_complete_shapes_and_all_rejections_are_required(self):
        self._reject_edits((lambda e: e['target_outputs'].pop(), lambda e: e['inherited_outputs'].pop(),
            lambda e: e['candidate_outputs'][0].pop(), lambda e: e['outcomes'].pop(0),
            lambda e: e['candidate_programs'].pop(0), lambda e: e['verdicts'].pop(0)))

    def test_prefix_descriptors_indices_and_order_are_bound(self):
        self._reject_edits((lambda e: e['choices'].reverse(), lambda e: e['candidate_programs'].reverse(),
            lambda e: e['candidate_programs'][0].__setitem__('grammar_index', 0),
            lambda e: e['inherited_programs'].reverse(), lambda e: e['inherited_work_order'].reverse(),
            lambda e: e.__setitem__('selected_program_hash', '0' * 64)))

    def test_reason_payload_and_context_cannot_be_self_certified(self):
        self._reject_edits((lambda e: e['outcomes'][0].__setitem__('reason_codes', []),
            lambda e: e['outcomes'][0].__setitem__('payload_hex', '7b7d'),
            lambda e: e['outcomes'][0].__setitem__('evaluation_hash', '0' * 64),
            lambda e: e['outcomes'][0].__setitem__('challenge_commitment_hash', '0' * 64),
            lambda e: e['outcomes'][0].__setitem__('response_sequence', 4),
            lambda e: e.__setitem__('terminal', 'promote')))

    def test_reference_schedule_and_output_images_are_bound(self):
        self._reject_edits((lambda e: e['work'].pop(), lambda e: e['work'].reverse(),
            lambda e: e['work'][8].__setitem__('program_index', 0),
            lambda e: e['work'][8].__setitem__('input_hex', e['work'][0]['input_hex']),
            lambda e: e['work'][0].__setitem__('output_hex', '5b302c302c302c305d'),
            lambda e: e['work'][0].__setitem__('output_sha256', '0' * 64)))

    def test_resource_tariff_and_claimed_execution_status_are_bound(self):
        self._reject_edits((lambda e: e['resource']['spent'].__setitem__(1, 143),
            lambda e: e['resource'].__setitem__('charged_cost', 0),
            lambda e: e['resource'].__setitem__('Q_execution_cost_measured', True),
            lambda e: e['resource'].__setitem__('historical_physical_cost_recovered', True),
            lambda e: e['resource']['operation_ids'].reverse()))

    def _reject_edits(self, edits):
        for index, edit in enumerate(edits):
            packet = dict(_template()); packet['evaluation'] = copy.deepcopy(_evaluation()); edit(packet['evaluation'])
            with self.subTest(edit=index), self.assertRaisesRegex(ValueError, 'complete evaluator'):
                p.validate_packet(packet)


class RetainedAndIntegrationTests(unittest.TestCase):
    def test_complete_retained_y_and_transcript_inventory(self):
        retained = p.read_retained(ROOT)
        self.assertEqual(set(retained), set(p.RETAINED_Y_PINS) | {p.FIXTURE_PATH})
        self.assertEqual(retained[p.Y_PACKET], (ROOT / p.Y_PACKET).read_bytes())

    def test_missing_changed_and_oversized_retained_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(ValueError): p.read_retained(root)
            (root / 'input').write_bytes(b'bad')
            with patch.object(p, 'RETAINED_Y_PINS', {'input': p.sha(b'good')}), self.assertRaises(ValueError):
                p.read_retained(root)
        with patch.object(p, 'MAX_BYTES', 2), self.assertRaises(ValueError): p.read_retained(ROOT)

    def test_linked_retained_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); target = root / 'target'; target.write_bytes(b'good')
            try: (root / 'input').symlink_to(target)
            except (OSError, NotImplementedError):
                with patch.object(p, 'RETAINED_Y_PINS', {'input': p.sha(b'good')}), \
                     patch.object(Path, 'is_symlink', return_value=True), self.assertRaises(ValueError):
                    p.read_retained(root)
                return
            with patch.object(p, 'RETAINED_Y_PINS', {'input': p.sha(b'good')}), self.assertRaises(ValueError):
                p.read_retained(root)

    def test_fresh_selected_fixture_reconstruction(self):
        with tempfile.TemporaryDirectory() as td:
            prepared = p.prepare_evaluation_trace(ROOT, Path(td) / 'packages')
            self.assertEqual(prepared.packet_bytes, p.canonical(_template()))
            self.assertEqual(p.summary(prepared)['vector_calls'], 144)


if __name__ == '__main__':
    unittest.main(verbosity=2)
