"""Independent resource protocol replay and exact retained-packet boundaries.

Synthetic traces exercise transitions, never count as the historical fixture or
Lean acceptance. The integration test reconstructs the existing selected inputs
without a new worker, challenge, measured workload or campaign.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from functools import lru_cache
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import resource_protocol as p

ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _retained():
    return p.read_retained(ROOT)


@lru_cache(maxsize=1)
def _z():
    return p.load_json_strict(_retained()[p.Z_PACKET])


@lru_cache(maxsize=1)
def _inputs():
    return p.inputs_from_retained(_retained())


@lru_cache(maxsize=1)
def _template():
    return p.packet_from_inputs(_z(), _inputs())


@lru_cache(maxsize=1)
def _prepared():
    return p.PreparedResourceProtocol(p.canonical(_template()))


def _binding():
    return copy.deepcopy(_z()['evaluation']['resource']['binding'])


def _policy(limits=None, cost=48):
    return {'profile': p.LEDGER_PROFILE, 'dimensions': list(p.DIMENSIONS),
            'weights': [64, 16, 1, 1], 'limits': [0, 2, 8, 8] if limits is None else limits, 'cost_limit': cost}


def _open(policy=None, binding=None):
    return {'kind': 'open', 'schema': p.LEDGER_SCHEMA,
            'policy': _policy() if policy is None else policy, 'binding': _binding() if binding is None else binding}


def _reserve(ident='work:0', spent=None, kind='vector'):
    return {'kind': 'reserve', 'operation': kind, 'operation_id': ident, 'input_sha256': '1' * 64,
            'charge': [0, 1, 4, 4] if kind == 'vector' else [1, 0, 0, 0],
            'spent_after': [0, 1, 4, 4] if spent is None else spent}


def _result(ok=True, error=None, elapsed=0):
    return {'kind': 'result', 'reservation_hash': '@pending', 'ok': ok,
            'result_sha256': '2' * 64 if ok else None, 'error_code': error, 'elapsed_ns': elapsed}


def _chain(bodies):
    """Rehash deliberate semantic mutations so hash failure cannot mask them."""
    rows, prior = [], p.ZERO
    for index, body in enumerate(copy.deepcopy(bodies)):
        if body.get('reservation_hash') == '@pending':
            body['reservation_hash'] = prior
        core = {'index': index, 'previous': prior, 'body': body}
        row = {**core, 'hash': p.sha(p.EVENT_DOMAIN + p.canonical(core))}
        rows.append(row); prior = row['hash']
    return b''.join(p.canonical(row) + b'\n' for row in rows), prior


def _run(bodies, policy=None, binding=None):
    raw, head = _chain(bodies)
    return p.replay_journal(raw, expected_head=head, policy=_policy() if policy is None else policy,
                           expected_binding=_binding() if binding is None else binding)


class ArithmeticAndShapeTests(unittest.TestCase):
    def test_natural_boundaries_and_boolean_rejection(self):
        self.assertEqual(p.natural(0), 0); self.assertEqual(p.natural((1 << 63) - 1), (1 << 63) - 1)
        for value in (True, False, -1, 1 << 63, 1.0, '1', None):
            with self.subTest(value=value), self.assertRaises(ValueError): p.natural(value)

    def test_exact_four_dimensional_vectors(self):
        self.assertEqual(p.vector([1, 2, 3, 4]), [1, 2, 3, 4])
        for value in ([], [0] * 3, [0] * 5, (0, 0, 0, 0), [0, False, 0, 0], [0, -1, 0, 0]):
            with self.subTest(value=value), self.assertRaises(ValueError): p.vector(value)

    def test_policy_exact_keys_weights_and_conversion_bound(self):
        mutations = ({**_policy(), 'extra': 0}, {**_policy(), 'profile': 'other'},
            {**_policy(), 'dimensions': list(reversed(p.DIMENSIONS))},
            {**_policy(), 'weights': [64, 16, True, 1]}, {**_policy(), 'weights': [1, 1, 1, 1]},
            {**_policy(), 'limits': [p.MAX_NAT, 0, 0, 0]}, {**_policy(), 'cost_limit': True},
            {**_policy(), 'cost_limit': 1 << 63})
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(ValueError): p.checked_policy(value)

    def test_dimension_failure_precedes_potential_weighted_overflow(self):
        limit = p.MAX_NAT // 64
        policy = p.checked_policy(_policy([limit, 0, 0, 0], limit * 64))
        self.assertFalse(p.fits(policy, [limit + 1, 0, 0, 0]))
        self.assertFalse(p.existing.Policy.from_json(policy).fits([limit + 1, 0, 0, 0]))
        with self.assertRaises(ValueError): p.weighted([limit + 1, 0, 0, 0])

    def test_conversion_uses_all_four_declared_weights(self):
        self.assertEqual(p.weighted([9, 144, 576, 576]), 4032)
        self.assertEqual(p.weighted([1, 0, 0, 0]), 64)
        self.assertEqual(p.weighted([0, 1, 4, 4]), 24)

    def test_binding_requires_all_four_canonical_digests(self):
        b = _binding()
        for value in ({}, {**b, 'extra': '0' * 64}, {**b, 'candidate_package_hash': 'A' * 64},
                      {**b, 'fixed_verifier_hash': False}, {**b, 'transcript_sha256': '0' * 63}):
            with self.subTest(value=value), self.assertRaises(ValueError): p.checked_binding(value)

    def test_byte_images_require_canonical_bounded_lowercase_hex(self):
        self.assertEqual(p.image_bytes('00ff'), b'\x00\xff')
        for value in ('', 'Ff', '0', '0g', b'00', '00 00'):
            with self.subTest(value=value), self.assertRaises(ValueError): p.image_bytes(value)
        with self.assertRaises(ValueError): p.image_bytes('0000', bound=1)


class ReplayTests(unittest.TestCase):
    def test_actual_four_trace_inventory_and_terminal_states(self):
        journals = _template()['protocol']['journals']
        self.assertEqual([len(row['events']) for row in journals], [308, 3, 2, 3])
        self.assertEqual([row['result']['status'] for row in journals],
                         ['sealed', 'safety_halt', 'resource_exhausted', 'safety_halt'])
        self.assertEqual([row['result']['spent'] for row in journals],
                         [[9, 144, 576, 576], [0, 1, 4, 4], [0, 0, 0, 0], [0, 1, 4, 4]])

    def test_every_actual_cumulative_state_matches_independent_count(self):
        for journal in _template()['protocol']['journals']:
            candidates = vectors = 0
            for event, state in zip(journal['events'], journal['states'], strict=True):
                body = event['body']
                if body['kind'] == 'reserve':
                    candidates += body['operation'] == 'candidate'; vectors += body['operation'] == 'vector'
                self.assertEqual(state['spent'], [candidates, vectors, 4 * vectors, 4 * vectors])
                self.assertEqual(state['charged_cost'], 64 * candidates + 24 * vectors)
                self.assertEqual(state['event_count'], event['index'] + 1)
                self.assertEqual(state['head'], event['hash'])

    def test_actual_pending_links_and_results_preserve_reserved_cost(self):
        for journal in _template()['protocol']['journals']:
            for index, event in enumerate(journal['events']):
                if event['body']['kind'] == 'result':
                    before, after = journal['states'][index - 1:index + 1]
                    self.assertEqual(before['status'], 'pending')
                    self.assertEqual(before['pending_hash'], event['body']['reservation_hash'])
                    self.assertEqual(before['spent'], after['spent'])
                    self.assertEqual(before['charges'], after['charges'])
                    self.assertIsNone(after['pending_hash'])

    def test_failed_and_interrupted_profiles_retain_the_reservation(self):
        for index, reason in ((1, 'operation_failed'), (3, 'interrupted')):
            journal = _template()['protocol']['journals'][index]
            self.assertEqual(journal['events'][-1]['body']['error_code'], reason)
            self.assertEqual(journal['result']['charged_cost'], 24)
            self.assertEqual(journal['result']['charges'], ['vector'])
            self.assertEqual(journal['result']['status'], 'safety_halt')

    def test_exhaustion_has_no_operation_admission_or_result(self):
        journal = _template()['protocol']['journals'][2]
        self.assertEqual([row['body']['kind'] for row in journal['events']], ['open', 'exhausted'])
        self.assertEqual(journal['result']['operation_ids'], [])
        self.assertEqual(journal['result']['charged_cost'], 0)
        self.assertIsNone(journal['result']['pending_hash'])

    def test_independent_replay_never_calls_existing_ledger(self):
        row = _template()['protocol']['journals'][0]
        with patch.object(p.existing, 'replay', side_effect=AssertionError('old replay called')):
            got = p.replay_journal(bytes.fromhex(row['raw_hex']), expected_head=row['expected_head'],
                                  policy=row['policy'], expected_binding=row['binding'])
        self.assertEqual(got['result'], row['result'])

    def test_independent_results_match_existing_replay_for_all_actual_journals(self):
        for row in _template()['protocol']['journals']:
            p._compare_existing(bytes.fromhex(row['raw_hex']), row['expected_head'],
                                row['policy'], row['binding'], row['result'])

    def test_open_pending_and_external_stop_are_distinct_valid_states(self):
        self.assertEqual(_run([_open()])['result']['status'], 'open')
        pending = _run([_open(), _reserve()])['result']
        self.assertEqual(pending['status'], 'pending'); self.assertIsNotNone(pending['pending_hash'])
        stopped = _run([_open(), _reserve(), _result(), {'kind': 'stop'}])['result']
        self.assertEqual(stopped['status'], 'external_stop'); self.assertEqual(stopped['charged_cost'], 24)

    def test_candidate_failure_keeps_all_candidate_tariff(self):
        policy = _policy([1, 0, 0, 0], 64)
        got = _run([_open(policy), _reserve(kind='candidate', spent=[1, 0, 0, 0]),
                    _result(False, 'operation_failed')], policy)['result']
        self.assertEqual(got['spent'], [1, 0, 0, 0]); self.assertEqual(got['charged_cost'], 64)
        self.assertEqual(got['status'], 'safety_halt')

    def test_scalar_budget_exhaustion_even_when_dimensions_fit(self):
        policy = _policy(cost=23)
        exhausted = {key: value for key, value in _reserve().items() if key != 'spent_after'}
        exhausted.update(kind='exhausted', reason='declared_budget')
        got = _run([_open(policy), exhausted], policy)['result']
        self.assertEqual(got['status'], 'resource_exhausted'); self.assertEqual(got['spent'], [0] * 4)

    def test_all_terminal_states_reject_later_work_or_completion(self):
        prefixes = [[_open(), {'kind': 'seal'}], [_open(), {'kind': 'stop'}],
                    [_open(), _reserve(), _result(False, 'operation_failed')]]
        zero = _policy([0] * 4, 0)
        exhausted = {key: value for key, value in _reserve().items() if key != 'spent_after'}
        exhausted.update(kind='exhausted', reason='declared_budget')
        for prefix in prefixes:
            for tail in (_reserve('work:1'), {'kind': 'seal'}, {'kind': 'stop'}, _result()):
                with self.subTest(prefix=prefix[-1], tail=tail), self.assertRaises(ValueError): _run(prefix + [tail])
        with self.assertRaises(ValueError): _run([_open(zero), exhausted, {'kind': 'seal'}], zero)

    def test_pending_state_rejects_new_reservation_seal_and_stop(self):
        for tail in (_reserve('work:1', [0, 2, 8, 8]), {'kind': 'seal'}, {'kind': 'stop'}):
            with self.subTest(tail=tail), self.assertRaises(ValueError): _run([_open(), _reserve(), tail])

    def test_result_requires_one_matching_reservation(self):
        for bodies in ([_open(), _result()], [_open(), _reserve(), {**_result(), 'reservation_hash': 'f' * 64}],
                       [_open(), _reserve(), _result(), _result()]):
            with self.subTest(bodies=bodies), self.assertRaises(ValueError): _run(bodies)

    def test_duplicate_identity_after_success_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            _run([_open(), _reserve(), _result(), _reserve(spent=[0, 2, 8, 8])])

    def test_rehashed_wrong_tariff_and_forged_cumulative_spent_are_rejected(self):
        for bad in ({**_reserve(), 'charge': [0, 0, 0, 0]}, {**_reserve(), 'spent_after': [0, 0, 0, 0]},
                    {**_reserve(), 'spent_after': [0, 2, 8, 8]}, {**_reserve(), 'charge': [False, 1, 4, 4]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError): _run([_open(), bad])

    def test_false_exhaustion_and_wrong_reason_are_rejected(self):
        exhausted = {key: value for key, value in _reserve().items() if key != 'spent_after'}
        exhausted.update(kind='exhausted', reason='declared_budget')
        with self.assertRaisesRegex(ValueError, 'false declared'): _run([_open(), exhausted])
        zero = _policy([0] * 4, 0)
        with self.assertRaises(ValueError): _run([_open(zero), {**exhausted, 'reason': 'search_complete'}], zero)

    def test_over_budget_reservation_is_not_exhaustion(self):
        zero = _policy([0] * 4, 0)
        with self.assertRaises(ValueError): _run([_open(zero), _reserve()], zero)

    def test_operation_kinds_id_grammar_and_digest_bounds(self):
        edits = [('operation', 'refund'), ('operation', True), ('operation_id', ''),
                 ('operation_id', 'a' * 97), ('operation_id', 'é'), ('operation_id', 'work/0'),
                 ('input_sha256', 'A' * 64), ('input_sha256', None)]
        for key, value in edits:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                _run([_open(), {**_reserve(), key: value}])

    def test_result_boolean_elapsed_and_success_failure_shapes(self):
        mutations = ({**_result(), 'ok': 1}, {**_result(), 'elapsed_ns': -1},
            {**_result(), 'elapsed_ns': True}, {**_result(), 'elapsed_ns': 1 << 63},
            {**_result(), 'result_sha256': None}, {**_result(), 'error_code': 'operation_failed'},
            {**_result(False, 'operation_failed'), 'result_sha256': '2' * 64},
            _result(False, None), _result(False, 'retry'), {**_result(), 'result_sha256': '2' * 63})
        for bad in mutations:
            with self.subTest(bad=bad), self.assertRaises(ValueError): _run([_open(), _reserve(), bad])
        self.assertEqual(_run([_open(), _reserve(), _result(elapsed=p.MAX_NAT)])['result']['status'], 'open')

    def test_exact_event_body_fields_and_initial_open_are_required(self):
        for body in ({'kind': 'seal'}, {**_open(), 'schema': 'wrong'}, {**_open(), 'extra': 1}):
            with self.subTest(body=body), self.assertRaises(ValueError): _run([body])
        for body in ({**_reserve(), 'extra': 0}, {'kind': 'refund'}, _open(), {'kind': 'seal', 'refund': 24}):
            with self.subTest(body=body), self.assertRaises(ValueError): _run([_open(), body])
        with self.assertRaises(ValueError): _run([_open(), _reserve(), {**_result(), 'extra': 0}])

    def test_external_policy_and_same_candidate_binding_are_fixed(self):
        for key in p.BINDING_FIELDS:
            binding = _binding(); binding[key] = 'f' * 64
            with self.subTest(key=key), self.assertRaises(ValueError): _run([_open(binding=binding)])
        with self.assertRaises(ValueError): _run([_open(_policy(cost=47))])

    def test_index_previous_hash_and_exact_outer_fields(self):
        raw, head = _chain([_open()]); row = p.load_json_strict(raw[:-1])
        for changed in ({**row, 'index': True}, {**row, 'index': 1}, {**row, 'previous': 'f' * 64},
                        {**row, 'hash': 'f' * 64}, {**row, 'extra': 0}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                p.replay_journal(p.canonical(changed) + b'\n', expected_head=head,
                                 policy=_policy(), expected_binding=_binding())

    def test_external_anchor_rejects_valid_rehashed_truncation(self):
        rows = [_open(), _reserve(), _result(), {'kind': 'seal'}]
        raw, head = _chain(rows); shorter, short_head = _chain(rows[:-1])
        self.assertNotEqual(head, short_head)
        with self.assertRaisesRegex(ValueError, 'external retained'):
            p.replay_journal(shorter, expected_head=head, policy=_policy(), expected_binding=_binding())

    def test_immutable_complete_canonical_lf_bytes_required(self):
        raw, head = _chain([_open()])
        invalid = (b'', bytearray(raw), raw[:-1], raw.replace(b'\n', b'\r\n'), raw + b'\n',
                   raw.replace(b'{', b'{ ', 1), b'{"body":{},"body":{}}\n')
        for value in invalid:
            with self.subTest(value=value[:25]), self.assertRaises(ValueError):
                p.replay_journal(value, expected_head=head, policy=_policy(), expected_binding=_binding())

    def test_journal_event_and_record_capacity_bounds(self):
        raw, head = _chain([_open()])
        for name, value in (('MAX_JOURNAL_BYTES', len(raw) - 1), ('MAX_EVENTS', 0), ('MAX_EVENT_BYTES', len(raw) - 2)):
            with self.subTest(name=name), patch.object(p, name, value), self.assertRaises(ValueError):
                p.replay_journal(raw, expected_head=head, policy=_policy(), expected_binding=_binding())

    def test_replay_does_not_mutate_external_policy_or_binding(self):
        policy, binding = _policy(), _binding(); before = copy.deepcopy((policy, binding))
        raw, head = _chain([_open(policy, binding), _reserve(), _result()])
        p.replay_journal(raw, expected_head=head, policy=policy, expected_binding=binding)
        self.assertEqual((policy, binding), before)


class PacketAndBindingTests(unittest.TestCase):
    def test_actual_z_packet_is_preserved_and_views_are_detached(self):
        self.assertEqual(_prepared().evaluation_trace().packet_bytes, _retained()[p.Z_PACKET])
        with self.assertRaises(FrozenInstanceError): _prepared().packet_bytes = b'{}'
        packet = _prepared().packet; packet['protocol']['journals'][0]['states'][0]['spent'][0] = 1
        self.assertEqual(_prepared().packet['protocol']['journals'][0]['states'][0]['spent'], [0] * 4)

    def test_summary_counts_all_images_and_states(self):
        got = p.summary(_prepared())
        self.assertEqual((got['journals'], got['events'], got['json_images'], got['states_checked']), (4, 316, 316, 316))
        self.assertEqual((got['total_journal_bytes'], got['json_image_bytes']), (125050, 124734))
        self.assertEqual((got['selected_operations'], got['candidate_admissions'], got['vector_calls']), (153, 9, 144))
        self.assertEqual(got['declared_spent'], [9, 144, 576, 576]); self.assertEqual(got['declared_cost'], 4032)
        self.assertEqual(got['charged_costs'], [4032, 24, 0, 24]); self.assertFalse(got['candidate_active'])

    def test_every_event_image_decodes_to_complete_original_record(self):
        for journal in _template()['protocol']['journals']:
            rebuilt = b''.join(bytes.fromhex(image) + b'\n' for image in journal['event_images'])
            self.assertEqual(rebuilt, bytes.fromhex(journal['raw_hex']))
            self.assertEqual([p.load_json_strict(bytes.fromhex(image)) for image in journal['event_images']], journal['events'])

    def test_all_153_reservations_results_and_z_work_digests_are_bound(self):
        success = _template()['protocol']['journals'][0]
        for index, work in enumerate(_template()['protocol']['work']):
            task = _z()['evaluation']['work'][index]
            reserve, result = success['events'][2 * index + 1]['body'], success['events'][2 * index + 2]['body']
            self.assertEqual(work, {key: task[key] for key in ('identity', 'kind', 'input_sha256', 'output_sha256')})
            self.assertEqual(work['input_sha256'], p.sha(bytes.fromhex(task['input_hex'])))
            self.assertEqual(work['output_sha256'], p.sha(bytes.fromhex(task['output_hex'])))
            self.assertEqual((reserve['operation_id'], reserve['operation'], reserve['input_sha256']),
                             (work['identity'], work['kind'], work['input_sha256']))
            self.assertEqual(result['result_sha256'], work['output_sha256'])

    def test_production_replay_disagreement_is_not_ignored(self):
        original = p.existing.replay
        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            return p.existing.Replay(result.head, result.event_count, (0, 0, 0, 0), result.status,
                                     result.pending_hash, result.operation_ids, result.charges)
        with patch.object(p.existing, 'replay', side_effect=changed), self.assertRaisesRegex(ValueError, 'disagrees'):
            p.derive_protocol(_z(), _inputs())

    def test_bound_journal_bytes_and_reports_cannot_be_rehashed(self):
        for field in ('raw_hex', 'profile_hex'):
            inputs = copy.deepcopy(_inputs()); raw = bytes.fromhex(inputs['journals'][0][field])
            inputs['journals'][0][field] = (raw[:-1] + bytes([raw[-1] ^ 1])).hex()
            with self.subTest(field=field), self.assertRaises(ValueError): p.derive_protocol(_z(), inputs)

    def test_complete_fixed_journal_order_and_input_fields(self):
        for edit in (lambda rows: rows.pop(), lambda rows: rows.reverse(),
                     lambda rows: rows[0].__setitem__('name', 'failed'), lambda rows: rows[0].__setitem__('extra', 0)):
            inputs = copy.deepcopy(_inputs()); edit(inputs['journals'])
            with self.assertRaises(ValueError): p.derive_protocol(_z(), inputs)
        with self.assertRaises(ValueError): p.derive_protocol(_z(), {**_inputs(), 'extra': 0})

    def test_same_candidate_and_verifier_cannot_be_substituted(self):
        for key in ('predecessor_physical_hash', 'candidate_physical_hash', 'transcript_sha256'):
            z = dict(_z()); z['bindings'] = {**z['bindings'], key: 'f' * 64}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'same-candidate'):
                p.derive_protocol(z, _inputs())
        z = dict(_z()); z['evaluation'] = copy.deepcopy(z['evaluation'])
        z['evaluation']['resource']['binding']['fixed_verifier_hash'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'same-candidate'): p.derive_protocol(z, _inputs())

    def test_changed_z_work_images_order_and_digests_are_rejected(self):
        edits = (lambda work: work.pop(), lambda work: work.reverse(),
                 lambda work: work[0].__setitem__('identity', 'other:0'),
                 lambda work: work[0].__setitem__('kind', 'candidate'),
                 lambda work: work[0].__setitem__('input_sha256', 'f' * 64),
                 lambda work: work[0].__setitem__('output_hex', '5b305d'))
        for edit in edits:
            z = dict(_z()); z['evaluation'] = copy.deepcopy(z['evaluation']); edit(z['evaluation']['work'])
            with self.assertRaises(ValueError): p.derive_protocol(z, _inputs())

    def test_schema_policy_base_scope_pins_and_claims_are_fixed(self):
        changes = [('schema', 'wrong'), ('policy', 'wrong'), ('base_commit', '0' * 40),
                   ('profile', {}), ('scope', {}), ('retained_z', {}), ('retained_n', {}), ('bindings', {}),
                   ('claims', {}), ('claims', {key: 0 for key in p.FALSE_CLAIMS}),
                   ('claims', {key: key == 'root_transition_verified' for key in p.FALSE_CLAIMS})]
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(ValueError): p.validate_packet({**_template(), key: value})
        with self.assertRaises(ValueError): p.validate_packet({**_template(), 'extra': 0})

    def test_self_rehashed_z_substitution_is_rejected(self):
        packet = dict(_template()); z = copy.deepcopy(_z()); z['bindings']['program_hash'] = 'f' * 64
        packet['evaluation_trace_packet'] = z; packet['evaluation_trace_packet_sha256'] = p.sha(p.canonical(z))
        with self.assertRaisesRegex(ValueError, 'imported Z'): p.validate_packet(packet)

    def test_all_supplied_events_states_results_and_binding_flags_are_recomputed(self):
        edits = (lambda x: x['journals'][0]['states'][2]['spent'].__setitem__(1, 0),
            lambda x: x['journals'][1]['result'].__setitem__('charged_cost', 0),
            lambda x: x['journals'][3]['states'][-1].__setitem__('status', 'open'),
            lambda x: x['journals'][2]['events'][-1]['body'].__setitem__('reason', 'complete_search'),
            lambda x: x['journals'][0]['event_images'].pop(), lambda x: x['journals'][0]['states'].pop(),
            lambda x: x['journals'][0].__setitem__('expected_head', '0' * 64),
            lambda x: x['work'].reverse(), lambda x: x.__setitem__('selected_work_bound', False))
        for index, edit in enumerate(edits):
            packet = dict(_template()); packet['protocol'] = copy.deepcopy(packet['protocol']); edit(packet['protocol'])
            with self.subTest(edit=index), self.assertRaisesRegex(ValueError, 'complete resource'):
                p.validate_packet(packet)

    def test_packet_bytes_require_immutable_canonical_complete_input(self):
        for raw in (b'', bytearray(b'{}'), b'{}\n', b'{"x":1,"x":2}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): p.PreparedResourceProtocol(raw)
        with patch.object(p, 'MAX_BYTES', 1), self.assertRaises(ValueError): p.PreparedResourceProtocol(b'{}')

    def test_external_packet_hash_and_recomputed_identity_are_required(self):
        with self.assertRaises(ValueError):
            p.verify_packet_bytes(_prepared().packet_bytes, _prepared(), expected_sha256='0' * 64)
        with self.assertRaises(ValueError): p.verify_packet_bytes(b'{}', _prepared(), expected_sha256=p.sha(b'{}'))


class RetainedAndIntegrationTests(unittest.TestCase):
    def test_complete_twelve_input_inventory(self):
        self.assertEqual(set(_retained()), set(p.RETAINED_Z_PINS) | set(p.RETAINED_N_PINS))
        self.assertEqual(len(_retained()), 12)
        for name, raw in _retained().items():
            self.assertEqual(p.sha(raw), {**p.RETAINED_Z_PINS, **p.RETAINED_N_PINS}[name])

    def test_missing_changed_and_oversized_retained_files_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(ValueError): p.read_retained(root)
            (root / 'input').write_bytes(b'bad')
            with patch.object(p, 'RETAINED_Z_PINS', {'input': p.sha(b'good')}), \
                 patch.object(p, 'RETAINED_N_PINS', {}), self.assertRaises(ValueError): p.read_retained(root)
            with patch.object(p, 'RETAINED_Z_PINS', {'input': p.sha(b'bad')}), \
                 patch.object(p, 'RETAINED_N_PINS', {}), patch.object(p, 'MAX_BYTES', 2), self.assertRaises(ValueError):
                p.read_retained(root)

    def test_linked_retained_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); target = root / 'target'; target.write_bytes(b'good')
            try:
                (root / 'input').symlink_to(target)
            except (OSError, NotImplementedError):
                with patch.object(p, 'RETAINED_Z_PINS', {'input': p.sha(b'good')}), \
                     patch.object(p, 'RETAINED_N_PINS', {}), patch.object(Path, 'is_symlink', return_value=True), \
                     self.assertRaises(ValueError): p.read_retained(root)
                return
            with patch.object(p, 'RETAINED_Z_PINS', {'input': p.sha(b'good')}), \
                 patch.object(p, 'RETAINED_N_PINS', {}), self.assertRaises(ValueError): p.read_retained(root)

    def test_retained_bytes_must_be_immutable_and_pinned_before_projection(self):
        retained = dict(_retained()); name = p.N_ROOT + '/failed-work.jsonl'
        for raw in (bytearray(retained[name]), b'{}\n'):
            retained[name] = raw
            with self.assertRaises(ValueError): p.inputs_from_retained(retained)

    def test_fresh_selected_preparation_reproduces_packet_without_campaigns(self):
        from rcp_rclm_runtime_v5.phase17 import metered_evaluation, challenge_client, campaign_client
        with tempfile.TemporaryDirectory(prefix='r17aa-') as td, \
             patch.object(metered_evaluation, 'run_selected_profile', side_effect=AssertionError('new metered run')), \
             patch.object(challenge_client.EvaluatorClient, '__init__', side_effect=AssertionError('worker launched')), \
             patch.object(campaign_client.CampaignEvaluatorClient, '__init__', side_effect=AssertionError('campaign launched')):
            prepared = p.prepare_resource_protocol(ROOT, Path(td) / 'packages')
        self.assertEqual(prepared.packet_bytes, _prepared().packet_bytes)


if __name__ == '__main__':
    unittest.main(verbosity=2)
