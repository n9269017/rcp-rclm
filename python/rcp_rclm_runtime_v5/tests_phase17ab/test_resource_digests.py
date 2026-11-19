"""Selected hash-input reconstruction, arithmetic witnesses and authority bounds.

These Python checks do not stand in for Lean acceptance. Deliberate substitutions
are rehashed where relevant, so rejection cannot be credited to an incidental
hash mismatch. The one fresh reconstruction test starts no metered campaign.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from functools import lru_cache
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import resource_digests as p

ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _retained():
    return p.read_retained(ROOT)


@lru_cache(maxsize=1)
def _aa():
    return p.load_json_strict(_retained()[p.AA_PACKET])


@lru_cache(maxsize=1)
def _targets():
    return p.selected_inputs(_aa())


@lru_cache(maxsize=1)
def _template():
    return p.packet_from_inputs(_aa())


def _records():
    return _template()['hash_records']


@lru_cache(maxsize=1)
def _prepared():
    return p.PreparedResourceDigests(p.canonical(_template()))


def _position(category, index=0):
    return next(i for i, row in enumerate(_targets()) if row['category'] == category and row['index'] == index)


def _rehash(row, raw, image=None):
    row['json_hex'] = (raw if image is None else image).hex()
    row['preimage_hex'] = raw.hex()
    row['digest'] = hashlib.sha256(raw).hexdigest()
    row['blocks'] = p.reference.compression_trace(raw)
    p.reference.validate_trace(raw, row['blocks'], row['digest'])
    return row


class SelectedInputTests(unittest.TestCase):
    def test_exact_group_order_counts_and_input_bytes(self):
        expected = [('event', 316, 109566), ('work_input', 153, 51906),
                    ('work_output', 153, 2816), ('candidate_descriptor', 9, 2698)]
        offset = 0
        for category, count, size in expected:
            group = _targets()[offset:offset + count]
            self.assertEqual([row['category'] for row in group], [category] * count)
            self.assertEqual([row['index'] for row in group], list(range(count)))
            self.assertEqual(sum(len(bytes.fromhex(row['preimage_hex'])) for row in group), size)
            offset += count
        self.assertEqual(offset, 631)
        self.assertEqual(sum(len(bytes.fromhex(row['preimage_hex'])) for row in _targets()), 166986)

    def test_every_event_uses_complete_core_and_exact_domain_nul(self):
        offset = 0
        for journal in _aa()['protocol']['journals']:
            for index, event in enumerate(journal['events']):
                row = _targets()[offset]; offset += 1
                core = {key: event[key] for key in ('body', 'index', 'previous')}
                self.assertEqual(bytes.fromhex(row['json_hex']), p.canonical(core))
                self.assertEqual(bytes.fromhex(row['preimage_hex']), b'RCPRCLM-PHASE17N-EVENT-V1\0' + p.canonical(core))
                self.assertEqual((row['journal'], row['event_index'], row['identity']),
                                 (journal['name'], index, journal['name'] + ':' + str(index)))
                self.assertEqual(row['digest'], event['hash'])
        self.assertEqual(offset, 316)

    def test_event_preimage_excludes_hash_field_and_lf_framing(self):
        event = _aa()['protocol']['journals'][0]['events'][0]
        image, preimage = p.event_preimage(event)
        self.assertEqual(set(p.load_json_strict(image)), {'body', 'index', 'previous'})
        self.assertNotEqual(image, p.canonical(event))
        self.assertFalse(preimage.endswith(b'\n'))
        self.assertEqual(hashlib.sha256(preimage).hexdigest(), event['hash'])

    def test_every_work_image_comes_from_actual_z_and_aa_reference(self):
        work = _aa()['evaluation_trace_packet']['evaluation']['work']
        references = _aa()['protocol']['work']
        for category, field in (('work_input', 'input'), ('work_output', 'output')):
            for index, (task, reference) in enumerate(zip(work, references, strict=True)):
                row = _targets()[_position(category, index)]
                self.assertEqual(row['identity'], task['identity'])
                self.assertEqual(row['preimage_hex'], task[field + '_hex'])
                self.assertEqual(row['json_hex'], task[field + '_hex'])
                self.assertEqual(row['digest'], reference[field + '_sha256'])
                self.assertIsNone(row['journal']); self.assertIsNone(row['event_index'])

    def test_admission_digest_hashes_raw_descriptor_without_public_domain(self):
        evaluation = _aa()['evaluation_trace_packet']['evaluation']
        admissions = [row for row in evaluation['work'] if row['kind'] == 'candidate']
        for index, task in enumerate(admissions):
            row = _targets()[_position('candidate_descriptor', index)]
            raw = p.canonical(evaluation['candidate_programs'][index]['program'])
            self.assertEqual(bytes.fromhex(row['preimage_hex']), raw)
            self.assertEqual(row['digest'], p.load_json_strict(bytes.fromhex(task['output_hex']))['program_sha256'])
            self.assertEqual(row['identity'], 'candidate:' + str(index))
            self.assertNotEqual(row['digest'], hashlib.sha256(p.reference.preimages.PUBLIC_HASH_DOMAIN + raw).hexdigest())

    def test_no_whole_journal_or_producer_response_inputs_are_silently_added(self):
        self.assertEqual(set(row['category'] for row in _targets()), set(p.GROUP_COUNTS))
        self.assertNotIn('journal', p.GROUP_COUNTS)
        self.assertFalse(p.PROFILE['whole_journal_file_checksums_in_new_inventory'])
        self.assertFalse(p.PROFILE['producer_response_hashes_in_new_inventory'])
        self.assertTrue(p.SCOPE['whole_journal_file_hash_computation_remains_external'])
        self.assertTrue(p.SCOPE['producer_response_hash_computation_remains_external'])

    def test_actual_padded_block_and_shared_transition_inventory(self):
        blocks, paths = p.compression_inventory(_records())
        self.assertEqual(len(blocks), 2134)
        self.assertEqual(sum(map(len, paths)), 3008)
        for category, count in [('event', 1919), ('work_input', 881), ('work_output', 162), ('candidate_descriptor', 46)]:
            self.assertEqual(sum(len(row['blocks']) for row in _records() if row['category'] == category), count)
        for row, path in zip(_records(), paths, strict=True):
            self.assertEqual(row['blocks'], [blocks[index] for index in path])

    def test_all_selected_hashes_match_independent_integer_reference_and_library(self):
        for row in _records():
            raw = bytes.fromhex(row['preimage_hex'])
            self.assertEqual(p.reference.sha256_hex(raw), hashlib.sha256(raw).hexdigest())
            self.assertEqual(p.reference.sha256_hex(raw), row['digest'])

    def test_standard_vectors_do_not_call_library_sha(self):
        vectors = [(b'', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
                   (b'abc', 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')]
        with patch.object(p.reference, 'sha', side_effect=AssertionError('library SHA invoked')):
            for raw, expected in vectors:
                self.assertEqual(p.reference.sha256_hex(raw), expected)

    def test_padding_boundaries_and_big_endian_bit_length(self):
        for size in (0, 1, 55, 56, 63, 64, 65, 119, 120):
            raw = bytes(range(size))
            padded = p.reference.pad_message(raw)
            self.assertEqual(len(padded) % 64, 0)
            self.assertEqual(padded[:size], raw)
            self.assertEqual(padded[size], 128)
            self.assertEqual(padded[-8:], (size * 8).to_bytes(8, 'big'))
            self.assertEqual(p.reference.sha256_hex(raw), hashlib.sha256(raw).hexdigest())

    def test_hash_input_shape_bounds_and_boolean_indices(self):
        event = copy.deepcopy(_aa()['protocol']['journals'][0]['events'][0])
        for index in (True, False, -1, 1 << 63, '0'):
            with self.subTest(index=index), self.assertRaises(ValueError): p.event_preimage({**event, 'index': index})
        for value in ('', 'AA', '0', '0g', b'00', '00' * (p.MAX_INPUT_BYTES + 1)):
            with self.subTest(value=str(value)[:30]), self.assertRaises(ValueError): p.image_bytes(value)
        for changed in ({**event, 'extra': 1}, {**event, 'body': []},
                        {**event, 'previous': 'F' * 64}, {**event, 'body': {'large': 'x' * p.MAX_INPUT_BYTES}}):
            with self.assertRaises(ValueError): p.event_preimage(changed)


class RehashedSubstitutionTests(unittest.TestCase):
    def _event_edit(self, edit, *, prefix=p.EVENT_DOMAIN, suffix=b''):
        row = copy.deepcopy(_records()[0]); value = p.load_json_strict(bytes.fromhex(row['json_hex']))
        edit(value); image = p.canonical(value)
        _rehash(row, prefix + image + suffix, image)
        with self.assertRaisesRegex(ValueError, 'identity, order, preimage or captured digest'):
            p.validate_record(row, _targets()[0])

    def test_missing_domain_nul_is_rejected_even_with_valid_hash_trace(self):
        self._event_edit(lambda value: None, prefix=p.EVENT_DOMAIN[:-1])

    def test_wrong_domain_is_rejected_even_with_valid_hash_trace(self):
        self._event_edit(lambda value: None, prefix=b'RCPRCLM-PHASE17N-EVENT-V2\0')

    def test_included_lf_is_rejected_even_with_valid_hash_trace(self):
        self._event_edit(lambda value: None, suffix=b'\n')

    def test_omitted_index_is_rejected_even_with_valid_hash_trace(self):
        self._event_edit(lambda value: value.pop('index'))

    def test_omitted_previous_is_rejected_even_with_valid_hash_trace(self):
        self._event_edit(lambda value: value.pop('previous'))

    def test_omitted_body_is_rejected_even_with_valid_hash_trace(self):
        self._event_edit(lambda value: value.pop('body'))

    def test_changed_index_is_rejected_even_with_valid_hash_trace(self):
        self._event_edit(lambda value: value.__setitem__('index', 1))

    def test_changed_previous_is_rejected_even_with_valid_hash_trace(self):
        self._event_edit(lambda value: value.__setitem__('previous', 'f' * 64))

    def test_changed_body_binding_is_rejected_even_with_valid_hash_trace(self):
        self._event_edit(lambda value: value['body']['binding'].__setitem__('candidate_package_hash', 'f' * 64))

    def test_included_current_hash_is_rejected_even_with_valid_hash_trace(self):
        self._event_edit(lambda value: value.__setitem__('hash', _records()[0]['digest']))

    def test_changed_work_input_is_rejected_even_with_valid_hash_trace(self):
        index = _position('work_input'); row = copy.deepcopy(_records()[index])
        value = p.load_json_strict(bytes.fromhex(row['preimage_hex'])); value['role'] = 'other'
        _rehash(row, p.canonical(value))
        with self.assertRaisesRegex(ValueError, 'selected digest input'): p.validate_record(row, _targets()[index])

    def test_changed_work_output_is_rejected_even_with_valid_hash_trace(self):
        index = _position('work_output'); row = copy.deepcopy(_records()[index])
        value = p.load_json_strict(bytes.fromhex(row['preimage_hex'])); value[0] += 1
        _rehash(row, p.canonical(value))
        with self.assertRaisesRegex(ValueError, 'selected digest input'): p.validate_record(row, _targets()[index])

    def test_changed_raw_descriptor_is_rejected_even_with_valid_hash_trace(self):
        index = _position('candidate_descriptor'); row = copy.deepcopy(_records()[index])
        value = p.load_json_strict(bytes.fromhex(row['preimage_hex'])); value['parameter_a'] += 1
        _rehash(row, p.canonical(value))
        with self.assertRaisesRegex(ValueError, 'selected digest input'): p.validate_record(row, _targets()[index])

    def test_public_domain_substitution_for_raw_descriptor_is_rejected(self):
        index = _position('candidate_descriptor'); row = copy.deepcopy(_records()[index])
        image = bytes.fromhex(row['preimage_hex'])
        _rehash(row, p.reference.preimages.PUBLIC_HASH_DOMAIN + image, image)
        with self.assertRaisesRegex(ValueError, 'selected digest input'): p.validate_record(row, _targets()[index])

    def test_group_position_identity_and_journal_substitutions_are_rejected(self):
        for key, value in [('category', 'work_input'), ('index', True), ('index', 1),
                           ('identity', 'success:1'), ('journal', 'failed'), ('event_index', True),
                           ('event_index', 1), ('json_hex', '7b7d'), ('digest', 'f' * 64)]:
            row = {**_records()[0], key: value}
            with self.subTest(key=key), self.assertRaises(ValueError): p.validate_record(row, _targets()[0])
        with self.assertRaises(ValueError): p.validate_record({**_records()[0], 'extra': 0}, _targets()[0])

    def test_work_input_output_interchange_is_rejected(self):
        first, second = _position('work_input'), _position('work_output')
        row = {**_records()[first], 'json_hex': _records()[second]['json_hex'],
               'preimage_hex': _records()[second]['preimage_hex'], 'digest': _records()[second]['digest'],
               'blocks': _records()[second]['blocks']}
        with self.assertRaises(ValueError): p.validate_record(row, _targets()[first])


class CompressionWitnessTests(unittest.TestCase):
    def _reject(self, edit, index=0, message=None):
        row = copy.deepcopy(_records()[index]); edit(row)
        with self.assertRaisesRegex(ValueError, message or '.'):
            p.validate_record(row, _targets()[index])

    def test_missing_block_rejects_incomplete_trace(self):
        self._reject(lambda row: row['blocks'].pop(), message='complete SHA-256 compression trace')

    def test_duplicate_block_rejects_extra_trace(self):
        self._reject(lambda row: row['blocks'].append(copy.deepcopy(row['blocks'][-1])))

    def test_wrong_block_position_rejects_order(self):
        self._reject(lambda row: row['blocks'][0].__setitem__('index', 1))

    def test_boolean_block_index_is_not_an_integer(self):
        self._reject(lambda row: row['blocks'][0].__setitem__('index', False))

    def test_wrong_initial_state_is_rejected(self):
        self._reject(lambda row: row['blocks'][0]['input_state'].__setitem__(0, 0))

    def test_wrong_chaining_state_is_rejected(self):
        self._reject(lambda row: row['blocks'][1]['input_state'].__setitem__(0, 0))

    def test_wrong_schedule_word_is_rejected(self):
        self._reject(lambda row: row['blocks'][0]['schedule'].__setitem__(16, 0))

    def test_missing_schedule_word_is_rejected(self):
        self._reject(lambda row: row['blocks'][0]['schedule'].pop())

    def test_wrong_round_word_is_rejected(self):
        self._reject(lambda row: row['blocks'][0]['round_states'][0].__setitem__(0, 0))

    def test_missing_round_state_is_rejected(self):
        self._reject(lambda row: row['blocks'][0]['round_states'].pop())

    def test_wrong_feed_forward_is_rejected(self):
        self._reject(lambda row: row['blocks'][0]['output_state'].__setitem__(0, 0))

    def test_wrong_padding_byte_is_rejected(self):
        index = _position('work_output'); length = len(bytes.fromhex(_records()[index]['preimage_hex']))
        def edit(row):
            block = bytearray.fromhex(row['blocks'][0]['block_hex']); block[length] = 0
            row['blocks'][0]['block_hex'] = block.hex()
        self._reject(edit, index=index)

    def test_little_endian_length_substitution_is_rejected(self):
        index = _position('work_output'); bits = len(bytes.fromhex(_records()[index]['preimage_hex'])) * 8
        def edit(row):
            block = bytearray.fromhex(row['blocks'][0]['block_hex']); block[-8:] = bits.to_bytes(8, 'little')
            row['blocks'][0]['block_hex'] = block.hex()
        self._reject(edit, index=index)

    def test_out_of_range_noninteger_and_boolean_words_are_rejected(self):
        for value in (-1, 1 << 32, True, 1.0, '1'):
            with self.subTest(value=value):
                self._reject(lambda row: row['blocks'][0]['schedule'].__setitem__(0, value))

    def test_unknown_block_fields_are_rejected(self):
        self._reject(lambda row: row['blocks'][0].__setitem__('extra', 0))

    def test_ordered_inventory_cannot_omit_duplicate_or_reorder_records(self):
        with self.assertRaises(ValueError): p.validate_hash_records(_records()[:-1], _aa())
        with self.assertRaises(ValueError): p.validate_hash_records(tuple(_records()), _aa())
        duplicate = list(_records()); duplicate[1] = duplicate[0]
        with self.assertRaises(ValueError): p.validate_hash_records(duplicate, _aa())
        swapped = list(_records()); swapped[0], swapped[1] = swapped[1], swapped[0]
        with self.assertRaises(ValueError): p.validate_hash_records(swapped, _aa())


class PacketBoundaryTests(unittest.TestCase):
    def test_full_packet_is_accepted_and_inherited_aa_is_exact(self):
        prepared = _prepared()
        self.assertEqual(prepared.resource_protocol().packet_bytes, _retained()[p.AA_PACKET])
        self.assertEqual(prepared.packet['resource_protocol_packet_sha256'], p.AA_PACKET_SHA)
        self.assertEqual(p.sha(prepared.resource_protocol().packet_bytes), p.AA_PACKET_SHA)

    def test_packet_snapshots_are_detached_and_dataclass_is_frozen(self):
        prepared = _prepared(); before = prepared.packet_bytes
        value = prepared.packet; value['hash_records'][0]['digest'] = 'f' * 64
        value['resource_protocol_packet']['bindings']['program_hash'] = 'e' * 64
        self.assertEqual(prepared.packet_bytes, before)
        self.assertEqual(prepared.packet['hash_records'][0]['digest'], _records()[0]['digest'])
        with self.assertRaises(FrozenInstanceError): prepared.packet_bytes = b'{}'
        with self.assertRaises(FrozenInstanceError): prepared._previous = None

    def test_builder_profile_and_scope_are_detached_from_global_configuration(self):
        profile, scope = copy.deepcopy(p.PROFILE), copy.deepcopy(p.SCOPE)
        packet = _prepared().packet
        packet['profile']['group_order'].reverse(); packet['scope']['promotion_api'] = True
        self.assertEqual(p.PROFILE, profile); self.assertEqual(p.SCOPE, scope)

    def test_schema_policy_base_profile_and_scope_are_fixed(self):
        for key, value in [('schema', 'other'), ('policy', 'other'), ('base_commit', '0' * 40),
                           ('profile', {}), ('scope', {}), ('retained_aa', {}), ('bindings', {})]:
            with self.subTest(key=key), self.assertRaises(ValueError): p.validate_packet({**_template(), key: value})
        with self.assertRaises(ValueError): p.validate_packet({**_template(), 'extra': 0})

    def test_all_broader_claims_require_exact_false_values(self):
        claims = _template()['claims']
        self.assertEqual(len(claims), 24); self.assertTrue(all(value is False for value in claims.values()))
        for changed in ({}, {key: 0 for key in claims},
                        {**claims, 'cross_platform_validation': True}, {**claims, 'complete_resource_accounting': True}):
            with self.assertRaises(ValueError): p.validate_packet({**_template(), 'claims': changed})

    def test_self_rehashed_inherited_aa_substitution_is_rejected(self):
        aa = {**_aa(), 'bindings': {**_aa()['bindings'], 'program_hash': 'f' * 64}}
        packet = {**_template(), 'resource_protocol_packet': aa,
                  'resource_protocol_packet_sha256': p.sha(p.canonical(aa))}
        with self.assertRaisesRegex(ValueError, 'imported AA'): p.validate_packet(packet)
        with self.assertRaisesRegex(ValueError, 'imported AA'): p.selected_inputs(aa)

    def test_packet_requires_complete_immutable_canonical_bytes(self):
        for raw in (b'', bytearray(b'{}'), b'{}\n', b'{"x":1,"x":2}', b'{\xff}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): p.PreparedResourceDigests(raw)
        with patch.object(p, 'MAX_BYTES', 1), self.assertRaises(ValueError): p.PreparedResourceDigests(b'{}')

    def test_external_packet_hash_and_exact_reconstructed_bytes_are_required(self):
        prepared = _prepared()
        with self.assertRaises(ValueError): p.verify_packet_bytes(prepared.packet_bytes, prepared, expected_sha256='0' * 64)
        with self.assertRaises(ValueError): p.verify_packet_bytes(b'{}', prepared, expected_sha256=p.sha(b'{}'))

    def test_summary_keeps_hash_boundaries_and_zero_campaign_scope(self):
        summary = p.summary(_prepared())
        self.assertEqual((summary['inputs'], summary['input_bytes'], summary['padded_block_occurrences'],
                          summary['distinct_compression_transitions']), (631, 166986, 3008, 2134))
        self.assertTrue(summary['whole_journal_file_hash_computation_remains_external'])
        self.assertTrue(summary['producer_response_hash_computation_remains_external'])
        self.assertFalse(summary['fresh_worker_output_captured'])
        self.assertFalse(summary['candidate_active']); self.assertFalse(summary['promotion_authorized'])


class RetainedAndIntegrationTests(unittest.TestCase):
    def test_complete_four_retained_aa_files_are_pinned(self):
        self.assertEqual(set(_retained()), set(p.RETAINED_AA_PINS))
        self.assertEqual(len(_retained()), 4)
        for name, raw in _retained().items(): self.assertEqual(p.sha(raw), p.RETAINED_AA_PINS[name])

    def test_missing_changed_and_oversized_retained_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(ValueError): p.read_retained(root)
            (root / 'input').write_bytes(b'bad')
            with patch.object(p, 'RETAINED_AA_PINS', {'input': p.sha(b'good')}), self.assertRaises(ValueError):
                p.read_retained(root)
            with patch.object(p, 'RETAINED_AA_PINS', {'input': p.sha(b'bad')}), \
                 patch.object(p.previous, 'MAX_BYTES', 2), self.assertRaises(ValueError): p.read_retained(root)

    def test_linked_retained_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); target = root / 'target'; target.write_bytes(b'good')
            try:
                (root / 'input').symlink_to(target)
            except (OSError, NotImplementedError):
                with patch.object(p, 'RETAINED_AA_PINS', {'input': p.sha(b'good')}), \
                     patch.object(Path, 'is_symlink', return_value=True), self.assertRaises(ValueError):
                    p.read_retained(root)
                return
            with patch.object(p, 'RETAINED_AA_PINS', {'input': p.sha(b'good')}), self.assertRaises(ValueError):
                p.read_retained(root)

    def test_fresh_preparation_reproduces_selected_packet_without_campaigns(self):
        from rcp_rclm_runtime_v5.phase17 import metered_evaluation, challenge_client, campaign_client
        with tempfile.TemporaryDirectory(prefix='r17ab-') as td, \
             patch.object(metered_evaluation, 'run_selected_profile', side_effect=AssertionError('new metered run')), \
             patch.object(challenge_client.EvaluatorClient, '__init__', side_effect=AssertionError('worker launched')), \
             patch.object(campaign_client.CampaignEvaluatorClient, '__init__', side_effect=AssertionError('campaign launched')):
            prepared = p.prepare_resource_digests(ROOT, Path(td) / 'packages')
        self.assertEqual(prepared.packet_bytes, _prepared().packet_bytes)


if __name__ == '__main__':
    unittest.main(verbosity=2)
