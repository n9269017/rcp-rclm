"""Phase17T byte-decoder, bounded-grammar and inherited-input binding tests.

The integration fixture reconstructs the complete selected packages once.  The
remaining tests exercise the new independent decoder and failure boundaries;
neither these tests nor mocked calls are Lean acceptance evidence.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import captured_json as cj

ROOT = Path(__file__).resolve().parents[3]


def _raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('ascii')


def _packet_from_retained():
    s = cj.load_json_strict((ROOT / cj.S_PACKET).read_bytes())
    packet = {'schema': cj.SCHEMA, 'policy': cj.POLICY, 'base_commit': cj.BASE,
              'routing_packet': s, 'routing_packet_sha256': cj.S_PACKET_SHA,
              'bindings': s['bindings'], 'retained_s': dict(cj.RETAINED_S_PINS),
              'profile': copy.deepcopy(cj.PROFILE), 'scope': copy.deepcopy(cj.SCOPE),
              'claims': {name: False for name in cj.FALSE_CLAIMS}}
    packet['documents'] = cj._documents(packet)
    return packet


class DecoderAcceptanceTests(unittest.TestCase):
    def test_null_and_booleans_retain_exact_types(self):
        for raw, expected in ((b'null', None), (b'false', False), (b'true', True)):
            with self.subTest(raw=raw):
                actual = cj.decode_captured_json(raw)
                self.assertEqual(actual, expected)
                self.assertIs(type(actual), type(expected))

    def test_integer_endpoints_and_signs_are_exact(self):
        for value in (cj.MIN_INTEGER, -1234567890, -1, 0, 1, 87, cj.MAX_INTEGER):
            with self.subTest(value=value):
                actual = cj.decode_captured_json(str(value).encode())
                self.assertIs(type(actual), int)
                self.assertEqual(actual, value)

    def test_empty_and_printable_ascii_strings(self):
        strings = ['', ' ', 'a b', 'null,false:true[]{}', '/-/._',
                   ''.join(chr(n) for n in range(32, 127) if n not in (34, 92))]
        for value in strings:
            with self.subTest(value=value):
                self.assertEqual(cj.decode_captured_json(_raw(value)), value)

    def test_arrays_preserve_order_empty_values_and_scalar_types(self):
        value = [None, True, False, 0, -1, '', [], {}, [3, 2, 1]]
        actual = cj.decode_captured_json(_raw(value))
        self.assertEqual(_raw(actual), _raw(value))
        self.assertIs(type(actual[1]), bool)
        self.assertIs(type(actual[3]), int)

    def test_nested_objects_preserve_every_field(self):
        value = {'a': {'entries': [{'answer': 84, 'enabled': False}, {'answer': 85}]},
                 'b': [], 'c': None, 'd': {'a': '', 'b': 'quoted text is outside this fixture'}}
        self.assertEqual(cj.decode_captured_json(_raw(value)), value)

    def test_empty_object_and_array_are_accepted(self):
        self.assertEqual(cj.decode_captured_json(b'{}'), {})
        self.assertEqual(cj.decode_captured_json(b'[]'), [])

    def test_key_order_uses_ascii_and_allows_empty_first_key(self):
        self.assertEqual(cj.decode_captured_json(b'{"":0,"A":1,"Z":2,"a":3}'),
                         {'': 0, 'A': 1, 'Z': 2, 'a': 3})

    def test_same_key_in_different_objects_is_valid(self):
        self.assertEqual(cj.decode_captured_json(b'[{"x":1},{"x":2}]'), [{'x': 1}, {'x': 2}])

    def test_decoder_does_not_delegate_to_json_library(self):
        with (patch.object(cj, 'load_json_strict', side_effect=AssertionError('production parser called')),
              patch.object(json, 'loads', side_effect=AssertionError('JSON library called'))):
            self.assertEqual(cj.decode_captured_json(b'{"a":[1,false,null],"b":"text"}'),
                             {'a': [1, False, None], 'b': 'text'})

    def test_independent_standard_json_oracle_on_deterministic_trees(self):
        rng = random.Random(17002026)
        atoms = [None, True, False, 0, -1, cj.MIN_INTEGER, cj.MAX_INTEGER, '', 'ASCII / text', 'route:84']

        def value(depth):
            if depth == 0 or rng.randrange(3) == 0:
                return rng.choice(atoms)
            if rng.randrange(2):
                return [value(depth - 1) for _ in range(rng.randrange(5))]
            return {'key' + str(i): value(depth - 1) for i in range(rng.randrange(5))}

        for index in range(80):
            raw = _raw(value(4))
            with self.subTest(index=index):
                self.assertEqual(_raw(cj.decode_captured_json(raw)), _raw(json.loads(raw)))


class DecoderRejectionTests(unittest.TestCase):
    def reject(self, *images):
        for raw in images:
            with self.subTest(raw=repr(raw)[:100]), self.assertRaises(ValueError):
                cj.decode_captured_json(raw)

    def test_only_immutable_nonempty_bytes_are_inputs(self):
        self.reject(b'', bytearray(b'{}'), memoryview(b'{}'), '{}', None, 1)

    def test_bom_and_non_ascii_input_are_outside_profile(self):
        self.reject(b'\xef\xbb\xbf{}', b'"\xc3\xa9"', b'{"\xc3\xa9":1}', b'"\xff"')

    def test_whitespace_outside_strings_is_not_canonical(self):
        self.reject(b' {}', b'{} ', b'{}\n', b'\ttrue', b'[1, 2]', b'{"a": 1}', b'\rnull')

    def test_escape_syntax_is_explicitly_outside_admitted_profile(self):
        self.reject(b'"a\\nb"', b'"\\u0061"', b'"\\/"', b'"a\\\\b"', b'"a\\\"b"')

    def test_unescaped_controls_and_del_are_rejected(self):
        self.reject(b'"a\nb"', b'"a\x00b"', b'"a\x1fb"', b'"a\x7fb"')

    def test_unterminated_strings_are_rejected(self):
        self.reject(b'"', b'"value', b'{"key": "value}')

    def test_multiple_top_level_values_and_trailing_garbage_are_rejected(self):
        self.reject(b'{}{}', b'[][]', b'nulltrue', b'0false', b'"a""b"', b'{}x')

    def test_noncanonical_integer_spellings_are_rejected(self):
        self.reject(b'00', b'01', b'-0', b'-01', b'+1', b'--1', b'-', b'0x10')

    def test_fraction_exponent_and_nonfinite_forms_are_rejected(self):
        self.reject(b'1.0', b'1e3', b'1E-2', b'NaN', b'Infinity', b'-Infinity', b'.1')

    def test_integer_range_cannot_overflow_or_truncate(self):
        self.reject(str(cj.MAX_INTEGER + 1).encode(), str(cj.MIN_INTEGER - 1).encode(),
                    b'9' * 1000, b'-' + b'9' * 1000)

    def test_literal_spellings_and_prefixes_are_exact(self):
        self.reject(b'True', b'False', b'Null', b'tru', b'fals', b'nul', b'truex')

    def test_duplicate_keys_are_rejected_even_with_identical_values(self):
        self.reject(b'{"a":1,"a":1}', b'{"a":1,"a":2}', b'{"":0,"":0}')

    def test_object_keys_must_be_in_strict_lexical_order(self):
        self.reject(b'{"b":1,"a":2}', b'{"a":1,"A":2}', b'{"a":1,"":2}')

    def test_non_string_keys_are_rejected(self):
        self.reject(b'{1:2}', b'{null:2}', b'{true:2}', b'{[]:2}', b'{{}:2}')

    def test_missing_object_values_and_colons_are_rejected(self):
        self.reject(b'{"a"}', b'{"a":}', b'{"a"1}', b'{"a"::1}', b'{"a":,}')

    def test_leading_trailing_and_doubled_commas_are_rejected(self):
        self.reject(b'[,1]', b'[1,]', b'[1,,2]', b'{,"a":1}', b'{"a":1,}', b'{"a":1,,"b":2}')

    def test_missing_commas_are_rejected(self):
        self.reject(b'[1 true]', b'[1{}]', b'{"a":1"b":2}', b'[[]{}]')

    def test_mismatched_or_missing_delimiters_are_rejected(self):
        self.reject(b'[}', b'{]', b'[1}', b'{"a":1]', b'[', b'{', b'[[1]', b']', b'}')

    def test_colons_have_only_the_object_key_position(self):
        self.reject(b':1', b'[1:2]', b'{:1}', b'{"a":1:2}')


class DecoderBoundTests(unittest.TestCase):
    def test_string_limit_is_inclusive(self):
        self.assertEqual(len(cj.decode_captured_json(b'"' + b'a' * cj.MAX_STRING_BYTES + b'"')),
                         cj.MAX_STRING_BYTES)
        with self.assertRaises(ValueError):
            cj.decode_captured_json(b'"' + b'a' * (cj.MAX_STRING_BYTES + 1) + b'"')

    def test_array_limit_is_inclusive(self):
        self.assertEqual(len(cj.decode_captured_json(_raw([0] * cj.MAX_ARRAY_LENGTH))), cj.MAX_ARRAY_LENGTH)
        with self.assertRaises(ValueError):
            cj.decode_captured_json(_raw([0] * (cj.MAX_ARRAY_LENGTH + 1)))

    def test_object_limit_is_inclusive(self):
        value = {'k' + str(i).zfill(3): i for i in range(cj.MAX_OBJECT_FIELDS)}
        self.assertEqual(cj.decode_captured_json(_raw(value)), value)
        value['k256'] = 256
        with self.assertRaises(ValueError):
            cj.decode_captured_json(_raw(value))

    def test_value_depth_limit_is_inclusive(self):
        raw = b'[' * cj.MAX_DEPTH + b'0' + b']' * cj.MAX_DEPTH
        self.assertEqual(_raw(cj.decode_captured_json(raw)), raw)
        with self.assertRaises(ValueError):
            cj.decode_captured_json(b'[' + raw + b']')

    def test_empty_container_at_maximum_value_depth_is_valid(self):
        for empty in (b'[]', b'{}'):
            raw = b'[' * cj.MAX_DEPTH + empty + b']' * cj.MAX_DEPTH
            self.assertEqual(_raw(cj.decode_captured_json(raw)), raw)
            with self.assertRaises(ValueError):
                cj.decode_captured_json(b'[' + raw + b']')

    def test_object_key_depth_obeys_same_bound_as_value_depth(self):
        valid = b'[' * (cj.MAX_DEPTH - 1) + b'{"a":0}' + b']' * (cj.MAX_DEPTH - 1)
        self.assertEqual(_raw(cj.decode_captured_json(valid)), valid)
        with self.assertRaises(ValueError):
            cj.decode_captured_json(b'[' + valid + b']')

    def test_document_byte_limit_is_inclusive(self):
        value = ['a' * 8192] * 7 + ['b' * 8167]
        raw = _raw(value)
        self.assertEqual(len(raw), cj.MAX_JSON_BYTES)
        self.assertEqual(cj.decode_captured_json(raw), value)
        value[-1] += 'b'
        with self.assertRaises(ValueError):
            cj.decode_captured_json(_raw(value))


class CapturedInputBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = _packet_from_retained()

    def test_all_selected_json_images_decode_to_production_objects(self):
        for side in ('before', 'after'):
            images = cj.document_bytes(self.packet, side)
            self.assertEqual(list(images), [field for field, _ in cj.JSON_FIELDS])
            self.assertEqual(sum(map(len, images.values())), 51505)
            for field, raw in images.items():
                with self.subTest(side=side, field=field):
                    self.assertEqual(_raw(cj.decode_captured_json(raw)), raw)
                    self.assertEqual(cj.decode_captured_json(raw), json.loads(raw))

    def test_complete_adapter_manifest_all_eighty_records_are_retained(self):
        raw = cj.document_bytes(self.packet, 'before')['adapterManifest']
        value = cj.decode_captured_json(raw)
        self.assertEqual(len(raw), 40146)
        self.assertEqual(len(value['records']), 80)

    def test_before_after_json_bytes_are_equal_without_reusing_one_capture(self):
        self.assertIsNot(self.packet['routing_packet']['before'], self.packet['routing_packet']['after'])
        self.assertEqual(cj.document_bytes(self.packet, 'before'), cj.document_bytes(self.packet, 'after'))

    def test_document_side_name_is_exact(self):
        for side in ('candidate', '', None):
            with self.subTest(side=side), self.assertRaises(ValueError):
                cj.document_bytes(self.packet, side)

    def test_document_paths_order_and_inventory_are_exact(self):
        for change in ('missing', 'reversed', 'duplicate', 'extra'):
            packet = copy.deepcopy(self.packet)
            rows = packet['routing_packet']['before']['files']
            if change == 'missing': rows.pop()
            elif change == 'reversed': rows.reverse()
            elif change == 'duplicate': rows[1] = copy.deepcopy(rows[0])
            else: rows.append(copy.deepcopy(rows[-1]))
            with self.subTest(change=change), self.assertRaises(ValueError):
                cj.document_bytes(packet, 'before')

    def test_document_row_shape_is_exact(self):
        packet = copy.deepcopy(self.packet)
        packet['routing_packet']['before']['files'][0]['trusted'] = True
        with self.assertRaises(ValueError):
            cj.document_bytes(packet, 'before')

    def test_document_hex_requires_lowercase_even_bounded_bytes(self):
        for encoded in ('', 'abc', 'zz', 'AA', '00' * (cj.MAX_JSON_BYTES + 1), 1):
            packet = copy.deepcopy(self.packet)
            packet['routing_packet']['before']['files'][0]['hex'] = encoded
            with self.subTest(encoded=repr(encoded)[:50]), self.assertRaises((ValueError, TypeError)):
                cj.document_bytes(packet, 'before')

    def test_document_size_and_digest_bind_exact_bytes(self):
        for key, value in (('size', True), ('size', 1294), ('sha256', '0' * 64)):
            packet = copy.deepcopy(self.packet)
            packet['routing_packet']['before']['files'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                cj.document_bytes(packet, 'before')

    def test_decoded_value_cannot_be_replaced_by_a_supplied_route_object(self):
        packet = copy.deepcopy(self.packet)
        packet['routing_packet']['before']['route_objects']['memory']['entry_count'] = 99
        with self.assertRaisesRegex(ValueError, 'differs from the S routing value'):
            cj._documents(packet)

    def test_retained_s_files_are_required_and_pinned(self):
        with tempfile.TemporaryDirectory(prefix='r17t-pins-') as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, 'missing'):
                cj.read_retained(root)
            first = root / cj.S_EXECUTION
            first.parent.mkdir(parents=True)
            first.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'changed'):
                cj.read_retained(root)


class PacketBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = _packet_from_retained()

    def reject(self, packet):
        with self.assertRaises((ValueError, TypeError, KeyError)):
            cj.PreparedCapturedJson(cj.canonical(packet))

    def test_packet_requires_immutable_canonical_bytes(self):
        raw = cj.canonical(self.packet)
        for value in (bytearray(raw), raw + b'\n', b'', '{}'):
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                cj.PreparedCapturedJson(value)

    def test_packet_schema_policy_and_base_are_exact(self):
        for key in ('schema', 'policy', 'base_commit'):
            packet = copy.deepcopy(self.packet); packet[key] = 'different'
            with self.subTest(key=key): self.reject(packet)

    def test_packet_extra_field_is_rejected(self):
        packet = copy.deepcopy(self.packet); packet['trusted_ast'] = {}
        self.reject(packet)

    def test_packet_profile_and_scope_cannot_expand(self):
        for category, key, value in (('profile', 'max_json_bytes', 1000000),
                                      ('scope', 'general_json_parser_equivalence', True),
                                      ('scope', 'byte_capture_remains_external', False)):
            packet = copy.deepcopy(self.packet); packet[category][key] = value
            with self.subTest(category=category, key=key): self.reject(packet)

    def test_all_twenty_four_broader_claims_stay_false(self):
        self.assertEqual(len(self.packet['claims']), 24)
        self.assertTrue(all(value is False for value in self.packet['claims'].values()))
        for value in (True, 0):
            packet = copy.deepcopy(self.packet); packet['claims']['root_transition_verified'] = value
            with self.subTest(value=value): self.reject(packet)

    def test_claim_inventory_cannot_drop_a_boundary(self):
        packet = copy.deepcopy(self.packet); packet['claims'].pop('physical_execution_attested')
        self.reject(packet)

    def test_retained_s_anchor_inventory_is_exact(self):
        packet = copy.deepcopy(self.packet); packet['retained_s'][cj.S_PACKET] = '0' * 64
        self.reject(packet)

    def test_routing_packet_hash_is_exact(self):
        packet = copy.deepcopy(self.packet); packet['routing_packet_sha256'] = '0' * 64
        self.reject(packet)

    def test_rehashed_modified_s_packet_cannot_replace_completed_s(self):
        packet = copy.deepcopy(self.packet)
        packet['routing_packet']['tasks'][0]['task_id'] = 'substitution'
        packet['routing_packet_sha256'] = cj.sha(cj.canonical(packet['routing_packet']))
        self.reject(packet)

    def test_package_and_task_bindings_cannot_be_substituted(self):
        packet = copy.deepcopy(self.packet); packet['bindings']['program_hash'] = '0' * 64
        self.reject(packet)

    def test_document_projection_inventory_is_recomputed(self):
        for change in ('size', 'sha256', 'field', 'missing', 'order'):
            packet = copy.deepcopy(self.packet); rows = packet['documents']['after']
            if change == 'size': rows[0]['size'] += 1
            elif change == 'sha256': rows[0]['sha256'] = '0' * 64
            elif change == 'field': rows[0]['field'] = 'planner'
            elif change == 'missing': rows.pop()
            else: rows.reverse()
            with self.subTest(change=change): self.reject(packet)


class FreshCapturedInputIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='r17t-runtime-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.retained_before = cj.read_retained(ROOT)
        cls.prepared = cj.prepare_captured_json(ROOT, Path(cls.temp.name) / 'packages')

    def test_fresh_reconstruction_matches_complete_retained_s_packet(self):
        self.assertEqual(self.prepared.routing().packet_bytes, self.retained_before[cj.S_PACKET])
        self.assertEqual(cj.read_retained(ROOT), self.retained_before)

    def test_summary_covers_both_complete_json_images_and_original_tasks(self):
        result = cj.summary(self.prepared)
        self.assertEqual(result['documents_per_package'], 8)
        self.assertEqual(result['total_document_checks'], 16)
        self.assertEqual(result['json_bytes_per_package'], {'before': 51505, 'after': 51505})
        self.assertEqual(result['original_protected_tasks'], 11)
        self.assertEqual(result['routing_packet_sha256'], cj.S_PACKET_SHA)

    def test_prepared_object_and_returned_packet_preserve_immutable_input(self):
        raw = self.prepared.packet_bytes
        with self.assertRaises(FrozenInstanceError):
            self.prepared.packet_bytes = b'{}'
        packet = self.prepared.packet; packet['claims']['root_transition_verified'] = True
        self.assertEqual(self.prepared.packet_bytes, raw)
        self.assertIs(self.prepared.packet['claims']['root_transition_verified'], False)

    def test_retained_packet_verification_binds_bytes_and_external_anchor(self):
        raw = self.prepared.packet_bytes
        cj.verify_packet_bytes(raw, self.prepared, expected_sha256=cj.sha(raw))
        with self.assertRaises(ValueError):
            cj.verify_packet_bytes(raw, self.prepared, expected_sha256='0' * 64)
        changed = raw + b'\n'
        with self.assertRaises(ValueError):
            cj.verify_packet_bytes(changed, self.prepared, expected_sha256=cj.sha(changed))


if __name__ == '__main__':
    unittest.main(verbosity=2)
