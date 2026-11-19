"""Captured routing refinement: independent byte oracles and hostile inputs.

The integration fixture reconstructs the selected packages once, compares all
eleven original tasks with production routing, and preserves the retained R
inputs. Parser/rendering fixtures are tests, never compiler acceptance evidence.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import prompt_routing as pr

ROOT = Path(__file__).resolve().parents[3]
COMMITMENT = '00000000' + 'a' * 56
SLOT = 180
TASK = 'test.hidden.protected'
MANIFEST = '2' * 64
CHALLENGE = {'task_id': TASK, 'commitment_hash': COMMITMENT, 'slot_token_id': SLOT}


def _tensor(entries=()):
    """Independent little-endian layout oracle: current, target, raw word."""
    data = bytearray(204800)
    for current, target, raw in entries:
        struct.pack_into('<h', data, 2 * (target * 320 + current), raw)
    return bytes(data)


def _adapter(offset=8, prefix=7):
    data = bytearray(5120)
    struct.pack_into('<hhhh', data, 0, 87, 86, 8, 1)
    struct.pack_into('<hhhh', data, offset, SLOT, 87, prefix, 1)
    return bytes(data)


def _legacy(marker, target):
    return {'query_marker_token_id': marker, 'route_marker_token_id': target,
            'match_mode': 'exact_terminal_byte'}


def _objects():
    return {'memory': {}, 'retrieval': {'entries': [_legacy(85, 84)]},
            'generator': {}, 'planner': {'routes': [_legacy(86, 85)]},
            'optimizer': {}, 'resource': {}}


def _hidden_route():
    return {'challenge_commitment_hash': COMMITMENT,
            'slot_token_id': SLOT, 'route_marker_token_id': 87}


def _family(objects, family, adapter=None, offset=8, prefix=7):
    route = _hidden_route()
    if family == 'memory_retrieval':
        objects['memory']['phase14_routes'] = [copy.deepcopy(route)]
        objects['retrieval']['phase14_routes'] = [copy.deepcopy(route)]
    elif family == 'generator_planner':
        objects['generator']['phase14_routes'] = [copy.deepcopy(route)]
        objects['planner']['phase14_routes'] = [copy.deepcopy(route)]
    elif family == 'adapter_optimizer':
        route.update(offset_bytes=offset, commitment_prefix_u16=prefix,
                     tensor_sha256=pr.sha(adapter if adapter is not None else _adapter()))
        objects['optimizer']['phase14_routes'] = [route]
    elif family == 'model_weights':
        route.update(tensor_manifest_hash=MANIFEST)
        objects['resource']['phase14_weight_routes'] = [route]
    else:
        raise AssertionError(family)
    return objects


def _route(objects=None, *, adapter=None, tensor=None, challenge=CHALLENGE,
           marker=SLOT, task_id=TASK, prompt=None):
    if objects is None:
        objects = _objects()
    if adapter is None:
        adapter = _adapter()
    if tensor is None:
        tensor = _tensor(((SLOT, 87, 24576),))
    return pr.route_reference(objects, adapter, tensor,
        adapter_sha256=pr.sha(adapter), tensor_manifest_hash=MANIFEST,
        task_id=task_id, prompt=prompt if prompt is not None else b'original task\n' + bytes((marker,)),
        challenge=challenge)


class AdapterAndLookupTests(unittest.TestCase):
    def test_complete_adapter_roundtrip_includes_padding(self):
        raw = bytearray(5120)
        raw[0], raw[17], raw[-1] = 255, 128, 9
        self.assertEqual(pr.encode_adapter(bytes(raw)),
                         {'byte_length': 5120, 'nonzero_bytes': [[0, 255], [17, 128], [5119, 9]]})
        self.assertEqual(pr.decode_adapter(pr.encode_adapter(bytes(raw))), bytes(raw))

    def test_empty_support_has_single_complete_zero_image(self):
        self.assertEqual(pr.decode_adapter({'byte_length': 5120, 'nonzero_bytes': []}), bytes(5120))

    def test_adapter_encoding_requires_full_immutable_bytes(self):
        for raw in (b'', bytes(5119), bytes(5121), bytearray(5120), '0' * 5120):
            with self.subTest(kind=type(raw).__name__, size=len(raw)), self.assertRaises((ValueError, TypeError)):
                pr.encode_adapter(raw)

    def test_adapter_record_has_exact_fields_and_integer_length(self):
        for record in ({'byte_length': 5120}, {'nonzero_bytes': []},
                       {'byte_length': 5120, 'nonzero_bytes': [], 'trusted': True},
                       {'byte_length': 5120.0, 'nonzero_bytes': []},
                       {'byte_length': 5120, 'nonzero_bytes': ()}):
            with self.subTest(record=record), self.assertRaises((ValueError, TypeError)):
                pr.decode_adapter(record)

    def test_support_order_duplicates_and_explicit_zeros_are_rejected(self):
        for support in ([[2, 1], [1, 1]], [[1, 1], [1, 2]], [[1, 0]], [[1, 256]], [[1, -1]]):
            with self.subTest(support=support), self.assertRaises(ValueError):
                pr.decode_adapter({'byte_length': 5120, 'nonzero_bytes': support})

    def test_support_range_types_and_pair_shapes_are_exact(self):
        for pair in ([-1, 1], [5120, 1], [True, 1], [1, True], [1.0, 1], [1, '1'],
                     [1], [1, 1, 1], (1, 1)):
            with self.subTest(pair=pair), self.assertRaises((ValueError, TypeError)):
                pr.decode_adapter({'byte_length': 5120, 'nonzero_bytes': [pair]})

    def test_signed_words_use_little_endian_and_signed_ranges(self):
        raw = struct.pack('<hhhh', -32768, -1, 0, 32767)
        self.assertEqual(pr.signed_words(raw, 0), (-32768, -1, 0, 32767))
        self.assertEqual(pr.signed_words(b'x' + raw, 1), (-32768, -1, 0, 32767))

    def test_signed_words_offset_bounds_do_not_wrap(self):
        raw = bytes(16)
        self.assertEqual(pr.signed_words(raw, 8), (0, 0, 0, 0))
        for offset in (-1, 9, 16, True, 0.0, '0', None):
            with self.subTest(offset=offset):
                self.assertIsNone(pr.signed_words(raw, offset))

    def test_hidden_lookup_requires_exactly_one_matching_commitment(self):
        row = _hidden_route()
        self.assertEqual(pr.unique_route({'phase14_routes': [None, 'bad', row]}, COMMITMENT), row)
        for entries in ([], [row, row], [row, copy.deepcopy(row)], {}, None):
            with self.subTest(entries=entries):
                self.assertIsNone(pr.unique_route({'phase14_routes': entries}, COMMITMENT))

    def test_hidden_lookup_keeps_other_commitments_and_list_order(self):
        wrong = {**_hidden_route(), 'challenge_commitment_hash': 'b' * 64}
        right = _hidden_route()
        for entries in ([wrong, right], [right, wrong]):
            self.assertEqual(pr.unique_route({'phase14_routes': entries}, COMMITMENT), right)

    def test_legacy_duplicate_matches_select_first(self):
        self.assertEqual(pr.legacy_route({'routes': [_legacy(86, 85), _legacy(86, 84)]}, 86, 'routes'), 85)
        self.assertEqual(pr.legacy_route({'routes': [_legacy(86, 84), _legacy(86, 85)]}, 86, 'routes'), 84)

    def test_malformed_first_legacy_target_does_not_fall_through(self):
        first = _legacy(86, '85')
        self.assertIsNone(pr.legacy_route({'routes': [first, _legacy(86, 85)]}, 86, 'routes'))

    def test_legacy_lookup_ignores_nonmatching_and_wrong_match_modes(self):
        wrong = {**_legacy(86, 1), 'match_mode': 'substring'}
        entries = [None, 'bad', _legacy(87, 3), wrong, _legacy(86, 85)]
        self.assertEqual(pr.legacy_route({'routes': entries}, 86, 'routes'), 85)
        self.assertIsNone(pr.legacy_route({'routes': 'not a list'}, 86, 'routes'))

    def test_weight_argmax_uses_target_stride_and_lowest_token_ties(self):
        raw = _tensor(((180, 87, 24576), (180, 88, 24576), (87, 180, 30720)))
        self.assertEqual(pr.greedy_weight_token(raw, 180), 87)
        self.assertEqual(pr.greedy_weight_token(_tensor(), 180), 0)

    def test_weight_argmax_uses_raw_scores_before_clipping(self):
        # Clipping would tie every cell at -15 and incorrectly select token 0.
        entries = [(180, target, -32768) for target in range(260)]
        entries.append((180, 87, -30720))
        self.assertEqual(pr.greedy_weight_token(_tensor(entries), 180), 87)

    def test_nonintegral_weight_words_are_outside_admitted_profile(self):
        with self.assertRaisesRegex(ValueError, 'nonintegral'):
            pr.greedy_weight_token(_tensor(((180, 87, 1),)), 180)


class ReferenceRoutingTests(unittest.TestCase):
    def test_unrouted_original_markers_pass_through(self):
        for marker in (0, 79, 82, 83, 84, 200, 255):
            with self.subTest(marker=marker):
                result = _route(challenge=None, marker=marker)
                self.assertEqual(result['original_marker'], marker)
                self.assertEqual(result['effective_marker'], marker)
                self.assertTrue(result['route_hit'])
                self.assertIsNone(result['selected_route_family'])

    def test_legacy_chain_composes_all_three_stages(self):
        for marker in (85, 86, 87):
            with self.subTest(marker=marker):
                result = _route(challenge=None, marker=marker)
                self.assertEqual(result['effective_marker'], 84)
                self.assertTrue(result['route_hit'])

    def test_legacy_failure_returns_entry_marker_not_partial_result(self):
        objects = _objects()
        objects['retrieval']['entries'] = []
        for marker in (85, 86, 87):
            with self.subTest(marker=marker):
                result = _route(objects, challenge=None, marker=marker)
                self.assertEqual(result['effective_marker'], marker)
                self.assertFalse(result['route_hit'])

    def test_legacy_stage_order_does_not_revisit_earlier_stage(self):
        objects = _objects()
        objects['planner']['routes'][0]['route_marker_token_id'] = 87
        result = _route(objects, challenge=None, marker=86)
        self.assertEqual(result['effective_marker'], 87)
        self.assertTrue(result['route_hit'])

    def test_legacy_adapter_requires_exact_four_signed_words(self):
        for byte in (0, 2, 4, 6):
            raw = bytearray(_adapter()); raw[byte] ^= 1
            with self.subTest(byte=byte):
                result = _route(adapter=bytes(raw), challenge=None, marker=87)
                self.assertFalse(result['route_hit'])
                self.assertEqual(result['effective_marker'], 87)

    def test_legacy_route_target_must_fit_final_prompt_byte(self):
        objects = _objects()
        for target in (-1, 256, 258):
            objects['retrieval']['entries'][0]['route_marker_token_id'] = target
            with self.subTest(target=target), self.assertRaises(ValueError):
                _route(objects, challenge=None, marker=85)

    def test_each_hidden_family_routes_original_prompt_to_protected_marker(self):
        for family in pr.FAMILIES:
            with self.subTest(family=family):
                result = _route(_family(_objects(), family))
                self.assertEqual(result, {'task_id': TASK, 'original_marker': 180,
                    'effective_marker': 84, 'route_hit': True, 'selected_route_family': family})

    def test_no_hidden_family_keeps_original_slot_and_fails(self):
        result = _route()
        self.assertEqual(result['effective_marker'], SLOT)
        self.assertFalse(result['route_hit'])
        self.assertIsNone(result['selected_route_family'])

    def test_two_matching_hidden_families_are_ambiguous(self):
        objects = _family(_family(_objects(), 'memory_retrieval'), 'generator_planner')
        result = _route(objects)
        self.assertFalse(result['route_hit'])
        self.assertEqual(result['effective_marker'], SLOT)
        self.assertIsNone(result['selected_route_family'])

    def test_duplicate_commitment_disables_family_even_if_records_identical(self):
        objects = _family(_objects(), 'memory_retrieval')
        objects['memory']['phase14_routes'] *= 2
        result = _route(objects)
        self.assertFalse(result['route_hit'])
        self.assertEqual(result['effective_marker'], SLOT)

    def test_hidden_pair_requires_both_complete_members(self):
        for field in ('memory', 'retrieval'):
            objects = _family(_objects(), 'memory_retrieval')
            objects[field].pop('phase14_routes')
            with self.subTest(field=field):
                self.assertFalse(_route(objects)['route_hit'])

    def test_hidden_pair_checks_slot_and_route_marker_in_both_members(self):
        for component in ('generator', 'planner'):
            for key, value in (('slot_token_id', SLOT + 1), ('route_marker_token_id', 86)):
                objects = _family(_objects(), 'generator_planner')
                objects[component]['phase14_routes'][0][key] = value
                with self.subTest(component=component, key=key):
                    self.assertFalse(_route(objects)['route_hit'])

    def test_hidden_selected_family_survives_legacy_failure_but_success_does_not(self):
        objects = _family(_objects(), 'memory_retrieval')
        objects['retrieval']['entries'] = []
        result = _route(objects)
        self.assertEqual(result['selected_route_family'], 'memory_retrieval')
        self.assertEqual(result['effective_marker'], 87)
        self.assertFalse(result['route_hit'])

    def test_adapter_route_uses_stored_prefix_and_unused_fields_are_not_oracles(self):
        adapter = _adapter(prefix=-2)
        objects = _family(_objects(), 'adapter_optimizer', adapter=adapter, prefix=-2)
        objects['optimizer']['phase14_routes'][0].update(slot_token_id=-1, route_marker_token_id=-1)
        self.assertTrue(_route(objects, adapter=adapter)['route_hit'])

    def test_adapter_route_allows_unaligned_in_bounds_offsets(self):
        adapter = _adapter(offset=9)
        objects = _family(_objects(), 'adapter_optimizer', adapter=adapter, offset=9)
        self.assertTrue(_route(objects, adapter=adapter)['route_hit'])

    def test_adapter_route_rejects_invalid_offsets_and_prefix(self):
        for key, value in (('offset_bytes', -1), ('offset_bytes', 5113),
                           ('offset_bytes', '8'), ('commitment_prefix_u16', '7'),
                           ('commitment_prefix_u16', 8)):
            objects = _family(_objects(), 'adapter_optimizer')
            objects['optimizer']['phase14_routes'][0][key] = value
            with self.subTest(key=key, value=value):
                self.assertFalse(_route(objects)['route_hit'])

    def test_adapter_route_checks_selected_record_digest(self):
        objects = _family(_objects(), 'adapter_optimizer')
        objects['optimizer']['phase14_routes'][0]['tensor_sha256'] = '0' * 64
        self.assertFalse(_route(objects)['route_hit'])

    def test_weight_route_requires_manifest_and_raw_argmax(self):
        objects = _family(_objects(), 'model_weights')
        self.assertFalse(_route(objects, tensor=_tensor())['route_hit'])
        objects['resource']['phase14_weight_routes'][0]['tensor_manifest_hash'] = '0' * 64
        self.assertFalse(_route(objects)['route_hit'])

    def test_weight_route_uses_full_vocabulary_and_lowest_tie(self):
        objects = _family(_objects(), 'model_weights')
        for tensor in (_tensor(((SLOT, 87, 24576), (SLOT, 86, 24576))),
                       _tensor(((SLOT, 87, 24576), (SLOT, 259, 30720)))):
            self.assertFalse(_route(objects, tensor=tensor)['route_hit'])

    def test_original_prompt_terminal_byte_and_challenge_task_id_are_bound(self):
        objects = _family(_objects(), 'memory_retrieval')
        for kwargs in ({'marker': SLOT + 1}, {'task_id': 'another.task'}, {'prompt': b''}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                _route(objects, **kwargs)

    def test_hidden_slot_is_derived_from_commitment_hex_prefix(self):
        challenge = {**CHALLENGE, 'commitment_hash': '00000001' + 'a' * 56}
        with self.assertRaises(ValueError):
            _route(challenge=challenge)
        for bad in ('a' * 63, 'A' * 64, 'z' * 64, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                _route(challenge={**CHALLENGE, 'commitment_hash': bad})

    def test_numeric_boolean_coercion_is_explicitly_outside_admitted_profile(self):
        for field in pr.NUMERIC_ROUTE_FIELDS:
            objects = _objects()
            objects['memory']['ignored'] = {field: True}
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Boolean numeric'):
                _route(objects, challenge=None, marker=79)

    def test_json_ast_bounds_reject_floats_deep_nesting_and_huge_values(self):
        deep = None
        for _ in range(25):
            deep = [deep]
        for value in (1.5, 1 << 64, 'x' * 8193, [None] * 1025, deep):
            objects = _objects(); objects['memory']['extra'] = value
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                _route(objects, challenge=None, marker=79)


class CapturedPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='r17s-routing-tests-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.packages = Path(cls.temporary.name) / 'packages'
        cls.retained_before = pr.read_retained(ROOT)
        cls.prepared = pr.prepare_prompt_routing(ROOT, cls.packages)
        cls.raw = cls.prepared.packet_bytes
        cls.value = cls.prepared.packet

    def bad(self, mutate):
        packet = copy.deepcopy(self.value)
        mutate(packet)
        with self.assertRaises((ValueError, TypeError, KeyError)):
            pr.PreparedPromptRouting(pr.canonical(packet))

    def test_fresh_capture_preserves_all_retained_r_bytes(self):
        self.assertEqual(pr.read_retained(ROOT), self.retained_before)
        self.assertEqual(self.prepared.sparse().packet_bytes, self.retained_before[pr.R_PACKET])
        self.assertIs(self.prepared.sparse(), self.prepared.sparse())

    def test_all_eleven_original_tasks_and_four_families_are_bound(self):
        facts = pr.summary(self.prepared)
        self.assertEqual(facts['task_count'], 11)
        self.assertEqual(facts['hidden_challenge_count'], 4)
        self.assertEqual(facts['legacy_chain_tasks'], 7)
        self.assertEqual(facts['route_family_counts'], {name: 1 for name in pr.FAMILIES})
        self.assertEqual(facts['original_markers'], [79, 82, 83, 84, 85, 86, 87, 193, 232, 239, 237])
        self.assertEqual(facts['effective_markers'], [79, 82, 83, 84, 84, 84, 84, 84, 84, 84, 84])

    def test_full_nine_file_captures_match_both_physical_packages(self):
        for side in ('before', 'after'):
            rows = self.value[side]['files']
            self.assertEqual([row['path'] for row in rows], list(pr.CAPTURE_PATHS))
            for row in rows:
                data = (self.packages / side / row['path']).read_bytes()
                self.assertEqual(bytes.fromhex(row['hex']), data, (side, row['path']))
                self.assertEqual(row['sha256'], pr.sha(data))
                self.assertEqual(row['size'], len(data))
            self.assertEqual(pr.decode_adapter(self.value[side]['adapter_image']),
                             (self.packages / side / pr.ADAPTER_PATH).read_bytes())

    def test_observations_are_derived_from_original_prompts_not_supplied_markers(self):
        for side in ('before', 'after'):
            tensor = pr.sparse.decode_tensor(self.value['sparse_packet'][side])
            capture = self.value[side]
            actual = pr._reference_observations(capture, tensor, self.value['tasks'])
            self.assertEqual(actual, capture['observations'])
            for task, observed in zip(self.value['tasks'], actual, strict=True):
                self.assertEqual(bytes.fromhex(task['prompt_hex'])[-1], observed['original_marker'])
                self.assertTrue(observed['route_hit'])

    def test_complete_route_objects_and_manifests_are_retained(self):
        for side in ('before', 'after'):
            capture = self.value[side]
            files = {row['path']: bytes.fromhex(row['hex']) for row in capture['files']}
            for label, path in pr.ROUTE_FILES.items():
                self.assertEqual(pr.canonical(capture['route_objects'][label]), files[path])
            adapter_manifest = json.loads(files[pr.ADAPTER_MANIFEST])
            self.assertEqual(len(adapter_manifest['records']), 80)
            self.assertEqual(len(pr._typed_rows(self.value['sparse_packet'], side)), 164)

    def test_prepared_bytes_are_immutable_and_projections_are_copies(self):
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            self.prepared.packet_bytes = b'{}'
        returned = self.prepared.packet
        returned['before']['observations'][0]['effective_marker'] = 0
        self.assertEqual(self.prepared.packet, self.value)
        self.assertEqual(self.prepared.packet_bytes, self.raw)

    def test_noncanonical_duplicate_key_mutable_and_oversized_packets_rejected(self):
        for raw in (json.dumps(self.value, indent=2).encode(), b'{"schema":1,"schema":2}',
                    b'', bytearray(self.raw), '{}', b'x' * (pr.MAX_BYTES + 1)):
            with self.subTest(kind=type(raw).__name__, size=len(raw)), self.assertRaises((ValueError, TypeError)):
                pr.PreparedPromptRouting(raw)

    def test_top_level_policy_base_and_inventory_are_exact(self):
        self.bad(lambda p: p.pop('before'))
        self.bad(lambda p: p.update(accepted=True))
        self.bad(lambda p: p.update(schema='other'))
        self.bad(lambda p: p.update(policy='other'))
        self.bad(lambda p: p.update(base_commit='0' * 40))

    def test_broader_claims_stay_false_and_scope_stays_external(self):
        self.assertEqual(len(self.value['claims']), 24)
        self.assertTrue(all(value is False for value in self.value['claims'].values()))
        self.assertTrue(self.value['scope']['byte_capture_and_json_parsing_remain_external'])
        self.assertTrue(self.value['scope']['python_execution_remains_external'])
        self.assertFalse(self.value['scope']['full_transformer_equivalence'])
        for flag in self.value['claims']:
            with self.subTest(flag=flag):
                self.bad(lambda p, name=flag: p['claims'].__setitem__(name, True))

    def test_integer_false_and_strengthened_scope_are_rejected(self):
        self.bad(lambda p: p['claims'].__setitem__('physical_execution_attested', 0))
        self.bad(lambda p: p['scope'].__setitem__('byte_capture_and_json_parsing_remain_external', False))
        self.bad(lambda p: p['profile'].__setitem__('hidden_route_lookup', 'first'))

    def test_retained_identity_and_nested_r_input_cannot_be_rehashed(self):
        self.bad(lambda p: p.update(retained_r={}))
        self.bad(lambda p: p['retained_r'].__setitem__(pr.R_PACKET, '0' * 64))
        def mutate(p):
            p['sparse_packet']['markers'][0] = 0
            p['sparse_packet_sha256'] = pr.sha(pr.canonical(p['sparse_packet']))
        self.bad(mutate)

    def test_package_binding_cannot_mix_or_replace_before_after(self):
        self.bad(lambda p: p['bindings'].__setitem__('candidate_physical_hash', '0' * 64))
        self.bad(lambda p: p['before'].__setitem__('package_hash', p['after']['package_hash']))
        self.bad(lambda p: p.__setitem__('after', copy.deepcopy(p['before'])))

    def test_original_prompt_hash_marker_order_and_targets_are_pinned(self):
        self.bad(lambda p: p['tasks'][0].__setitem__('prompt_hex', '00'))
        self.bad(lambda p: p['tasks'][0].__setitem__('prompt_sha256', '0' * 64))
        self.bad(lambda p: p['tasks'][0].__setitem__('original_marker', 84))
        self.bad(lambda p: p['tasks'][0].__setitem__('expected_tokens', [258]))
        self.bad(lambda p: p['tasks'].reverse())
        self.bad(lambda p: p['tasks'].pop())

    def test_hidden_challenge_identity_slot_and_presence_are_pinned(self):
        self.bad(lambda p: p['tasks'][0].__setitem__('challenge', dict(CHALLENGE)))
        self.bad(lambda p: p['tasks'][7].__setitem__('challenge', None))
        self.bad(lambda p: p['tasks'][7]['challenge'].__setitem__('task_id', TASK))
        self.bad(lambda p: p['tasks'][7]['challenge'].__setitem__('commitment_hash', '0' * 64))
        self.bad(lambda p: p['tasks'][7]['challenge'].__setitem__('slot_token_id', 180))

    def test_capture_inventory_missing_duplicate_reordered_and_extra_files_fail(self):
        self.bad(lambda p: p['before']['files'].pop())
        self.bad(lambda p: p['before']['files'].append(copy.deepcopy(p['before']['files'][0])))
        self.bad(lambda p: p['before']['files'].reverse())
        self.bad(lambda p: p['before']['files'][0].__setitem__('path', '../escape'))

    def test_changed_file_bytes_cannot_hide_behind_recomputed_digest(self):
        def mutate(p):
            row = p['before']['files'][0]
            data = bytes.fromhex(row['hex']) + b'\n'
            row.update(hex=data.hex(), size=len(data), sha256=pr.sha(data))
        self.bad(mutate)

    def test_routes_cannot_be_truncated_or_replaced_by_selected_hits(self):
        self.bad(lambda p: p['before']['route_objects']['memory'].pop('phase14_routes'))
        self.bad(lambda p: p['before']['route_objects'].__setitem__('memory', {'route_hit': True}))
        self.bad(lambda p: p['before']['route_objects']['planner']['routes'].insert(0, _legacy(86, 84)))
        self.bad(lambda p: p['before']['route_objects']['optimizer']['phase14_routes'].append(
            copy.deepcopy(p['before']['route_objects']['optimizer']['phase14_routes'][0])))

    def test_full_adapter_padding_and_manifest_identities_are_checked(self):
        self.bad(lambda p: p['before']['adapter_image']['nonzero_bytes'].append([5119, 1]))
        self.bad(lambda p: p['before']['adapter_image'].__setitem__('record_verified', True))

    def test_changed_adapter_and_tensor_manifest_digests_are_rejected(self):
        self.bad(lambda p: p['before'].__setitem__('adapter_sha256', '0' * 64))
        self.bad(lambda p: p['before'].__setitem__('tensor_manifest_hash', '0' * 64))

    def test_route_observation_family_marker_hit_and_task_cannot_be_asserted(self):
        for field, value in (('effective_marker', 0), ('route_hit', 1), ('task_id', 'another'),
                             ('selected_route_family', 'memory_retrieval')):
            with self.subTest(field=field):
                self.bad(lambda p, key=field, val=value: p['before']['observations'][0].__setitem__(key, val))
        self.bad(lambda p: p['before']['observations'].pop())

    def test_external_anchor_and_exact_independent_bytes_are_required(self):
        with self.assertRaises(ValueError):
            pr.verify_packet_bytes(self.raw, self.prepared, expected_sha256='0' * 64)
        changed = self.raw + b'\n'
        with self.assertRaises(ValueError):
            pr.verify_packet_bytes(changed, self.prepared, expected_sha256=pr.sha(changed))

    def test_retained_reader_rejects_actual_changed_and_missing_bytes(self):
        with tempfile.TemporaryDirectory(prefix='r17s-retained-') as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                pr.read_retained(root)
            for name, raw in self.retained_before.items():
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
            self.assertEqual(pr.read_retained(root), self.retained_before)
            destination = root / pr.R_PACKET
            destination.write_bytes(destination.read_bytes() + b'\n')
            with self.assertRaises(ValueError):
                pr.read_retained(root)

    def test_existing_physical_workspace_is_refused(self):
        with self.assertRaises(ValueError):
            pr.prepare_prompt_routing(ROOT, self.packages)

    def test_repository_internal_workspace_is_refused(self):
        path = ROOT / 's-must-not-be-created'
        with self.assertRaises(ValueError):
            pr.prepare_prompt_routing(ROOT, path)
        self.assertFalse(path.exists())

    def test_generated_sources_retain_two_dependencies_and_fifteen_new_audits(self):
        from rcp_rclm_runtime_v5.phase17 import prompt_routing_lean as pl
        from rcp_rclm_runtime_v5.phase17 import sparse_refinement_lean as sl
        sources = pl.generated_sources(self.prepared, source_root=ROOT)
        self.assertEqual(list(sources), [*pl.DEPENDENCY_LABELS, *pl.LABELS])
        self.assertEqual(len(pl.NAMES), 15)
        self.assertEqual(len(pl.LABELS) - 1, 10)
        for label in pl.DEPENDENCY_LABELS:
            self.assertNotIn(b'#print', sources[label], label)
        # R is preserved exactly except for its audited print commands.
        retained_r = self.retained_before[pr.R_SOURCE]
        audit_lines = {('#print axioms ' + name + '\n').encode() for name in sl.NAMES}
        stripped_r = b''.join(line for line in retained_r.splitlines(keepends=True) if line not in audit_lines)
        self.assertEqual(sources['Phase17RDependency'], stripped_r)
        positive = sources[pl.LABELS[0]]
        self.assertEqual(positive.count(b'#print axioms '), 15)
        self.assertIn(b'import Phase17RDependency', positive)
        self.assertIn(self.value['tasks'][7]['challenge']['commitment_hash'].encode(), positive)
        self.assertIn(b'def beforePackage : Package', positive)
        self.assertIn(b'def afterPackage : Package', positive)
        self.assertIn(b'adapterManifest := (.object', positive)
        self.assertIn(b'packageManifest := (.object', positive)
        self.assertIn(b'Phase17Sparse.selectedMarkers', positive)
        self.assertIn(b'Phase17Sparse.selectedTargets', positive)
        self.assertEqual(len({pr.sha(sources[label]) for label in pl.LABELS}), len(pl.LABELS))
        for label, raw in sources.items():
            self.assertIsNone(re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b|\+\s*native\b', raw), label)
        for label in pl.LABELS[1:]:
            self.assertNotIn(b'#print', sources[label], label)
            self.assertIn(b'theorem rejected_control', sources[label], label)

    def test_renderer_rejects_native_tactic_spellings_before_compilation(self):
        from rcp_rclm_runtime_v5.phase17 import prompt_routing_lean as pl
        template = pl.template(ROOT)
        for tactic in (b'native_decide', b'decide +native', b'decide + native'):
            injected = template + b'\nexample : True := by ' + tactic + b'\n'
            with self.subTest(tactic=tactic), patch.object(pl, 'template', return_value=injected):
                with self.assertRaisesRegex(ValueError, 'forbidden protected routing proof token'):
                    pl._render_validated(self.prepared, source_root=ROOT)

    def test_renderer_does_not_accept_report_objects_or_unknown_control_labels(self):
        from rcp_rclm_runtime_v5.phase17 import prompt_routing_lean as pl
        with self.assertRaises(ValueError):
            pl.generated_sources({'packet': self.value, 'accepted': True}, source_root=ROOT)
        with self.assertRaises(ValueError):
            pl.render(self.prepared, source_root=ROOT, negative='CallerSelectedMarker')


if __name__ == '__main__':
    unittest.main()
