"""Phase17U exact planner decoding, public numeric interpretation and input guards.

A single integration fixture reconstructs the physical predecessor/candidate.
Malformed-input and mocked capture tests are controlled tests, not Lean evidence
or attestations of historical execution.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from functools import lru_cache
import json
from pathlib import Path
import random
import struct
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime_v5.phase17 import planner_refinement as pr
from rcp_rclm_runtime_v5.phase17 import proposal_provenance
from rcp_rclm_runtime_v5.phase17.bootstrap import M9_PREFIX

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / 'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'


@lru_cache(maxsize=1)
def _planner_bytes():
    with ZipFile(BUNDLE) as bundle:
        raw = bundle.read(M9_PREFIX + 'model/phase15_planner/weights.i16le.bin')
    if pr.sha(raw) != pr.WEIGHTS_SHA256:
        raise AssertionError('fixed planner fixture changed')
    return raw


def _fixture_packet():
    """Build controlled U inputs from exact retained T input and anchored bytes."""
    t = pr.load_json_strict((ROOT / pr.T_PACKET).read_bytes())
    packet = {'schema': pr.SCHEMA, 'policy': pr.POLICY, 'base_commit': pr.BASE,
              'captured_json_packet': t, 'captured_json_packet_sha256': pr.T_PACKET_SHA,
              'bindings': t['bindings'], 'retained_t': dict(pr.RETAINED_T_PINS),
              'profile': copy.deepcopy(pr.PROFILE), 'scope': copy.deepcopy(pr.SCOPE),
              'claims': {name: False for name in pr.FALSE_CLAIMS},
              'before': pr.encode_planner(_planner_bytes()), 'after': pr.encode_planner(_planner_bytes()),
              'tensor_sha256': {'before': pr.WEIGHTS_SHA256, 'after': pr.WEIGHTS_SHA256}}
    provenance = pr.producer_packet(packet)
    packet['ranking'] = pr._ranking_inputs(provenance)
    packet['before_table'] = pr.reference_table(_planner_bytes(), packet['ranking']['rows'])
    packet['after_table'] = pr.reference_table(_planner_bytes(), packet['ranking']['rows'])
    packet['selected_choices'] = [step['selected_index'] for step in provenance['trace']['steps']]
    return packet


@lru_cache(maxsize=1)
def _prepared():
    return pr.PreparedPlannerRefinement(pr.canonical(_fixture_packet()))


def _small_image(pairs):
    raw = bytearray(pr.TENSOR_BYTES)
    for index, word in pairs:
        raw[2 * index:2 * index + 2] = struct.pack('<h', word)
    return pr.encode_planner(bytes(raw))


class PlannerCodecTests(unittest.TestCase):
    def test_signed_decoder_matches_struct_for_every_uint16_word(self):
        for word in range(65536):
            raw = bytes((word % 256, word // 256))
            self.assertEqual(pr.signed16(*raw), struct.unpack('<h', raw)[0])

    def test_signed_decoder_rejects_nonbytes_including_booleans(self):
        for lo, hi in ((-1, 0), (256, 0), (0, 256), (0, -1), (True, 0), (0, False), (1.0, 0)):
            with self.subTest(lo=lo, hi=hi), self.assertRaises(ValueError):
                pr.signed16(lo, hi)

    def test_only_exact_complete_immutable_images_are_accepted(self):
        for raw in (b'', bytes(pr.TENSOR_BYTES - 1), bytes(pr.TENSOR_BYTES + 1),
                    bytearray(pr.TENSOR_BYTES), memoryview(bytes(pr.TENSOR_BYTES)), None):
            with self.subTest(kind=type(raw)), self.assertRaises(ValueError):
                pr.encode_planner(raw)

    def test_zero_image_has_empty_byte_and_word_support(self):
        image = pr.encode_planner(bytes(pr.TENSOR_BYTES))
        self.assertEqual(image, {'byte_length': pr.TENSOR_BYTES, 'nonzero_bytes': [], 'nonzero_words': []})
        self.assertEqual(pr.decode_planner(image), bytes(pr.TENSOR_BYTES))

    def test_signed_endpoints_and_last_word_are_not_discarded(self):
        words = [(0, -32768), (1, -1), (2, 1), (pr.WORD_COUNT - 1, 32767)]
        image = _small_image(words)
        self.assertEqual(image['nonzero_words'], [[i, value] for i, value in words])
        decoded = pr.decode_planner(image)
        self.assertEqual(struct.unpack('<h', decoded[-2:])[0], 32767)
        self.assertEqual(decoded[:6], b'\x00\x80\xff\xff\x01\x00')

    def test_full_dense_image_round_trip_preserves_all_bytes(self):
        rng = random.Random(17012026)
        raw = bytes(rng.randrange(256) for _ in range(pr.TENSOR_BYTES))
        image = pr.encode_planner(raw)
        self.assertEqual(pr.decode_planner(image), raw)
        oracle = [[index, value] for index, (value,) in enumerate(struct.iter_unpack('<h', raw)) if value]
        self.assertEqual(image['nonzero_words'], oracle)

    def test_sparse_fields_and_length_are_exact(self):
        image = _small_image([(0, 1)])
        variants = [dict(image, extra=1), {key: value for key, value in image.items() if key != 'nonzero_words'},
                    dict(image, byte_length=True), dict(image, byte_length=pr.TENSOR_BYTES - 1)]
        for value in variants:
            with self.subTest(value=list(value)), self.assertRaises(ValueError):
                pr.decode_planner(value)

    def test_byte_support_requires_lists_of_exact_pairs(self):
        for support in (None, (), [[0]], [[0, 1, 2]], [(0, 1)], {'0': 1}):
            image = _small_image([(0, 1)]); image['nonzero_bytes'] = support
            with self.subTest(support=support), self.assertRaises(ValueError):
                pr.decode_planner(image)

    def test_byte_offsets_and_values_are_bounded_exact_integers(self):
        for pair in ((-1, 1), (pr.TENSOR_BYTES, 1), (False, 1), (0, 0), (0, 256), (0, True), (0, -1)):
            image = _small_image([(0, 1)]); image['nonzero_bytes'] = [list(pair)]
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                pr.decode_planner(image)

    def test_byte_offsets_must_be_unique_and_increasing(self):
        for support in ([[0, 1], [0, 1]], [[2, 1], [0, 1]]):
            image = _small_image([(0, 1), (1, 1)]); image['nonzero_bytes'] = support
            with self.subTest(support=support), self.assertRaises(ValueError):
                pr.decode_planner(image)

    def test_word_support_has_exact_pair_and_nonzero_signed_range(self):
        for support in (None, (), [[0]], [[0, 1, 2]], [(0, 1)], [[0, 0]],
                        [[-1, 1]], [[pr.WORD_COUNT, 1]], [[0, 32768]], [[0, -32769]], [[0, True]]):
            image = _small_image([(0, 1)]); image['nonzero_words'] = support
            with self.subTest(support=support), self.assertRaises(ValueError):
                pr.decode_planner(image)

    def test_word_support_rejects_omission_addition_duplication_and_reordering(self):
        image = _small_image([(1, 1), (5, -1)])
        for support in ([[1, 1]], [[1, 1], [3, 1], [5, -1]], [[1, 1], [1, 1]],
                        [[5, -1], [1, 1]], [[1, -1], [5, -1]]):
            changed = copy.deepcopy(image); changed['nonzero_words'] = support
            with self.subTest(support=support), self.assertRaises(ValueError):
                pr.decode_planner(changed)

    def test_introducing_a_formerly_zero_word_requires_changed_complete_projection(self):
        image = _small_image([(0, 1)])
        image['nonzero_bytes'].append([1000, 1])
        with self.assertRaisesRegex(ValueError, 'complete planner word projection'):
            pr.decode_planner(image)

    def test_byteorder_swap_cannot_preserve_word_projection(self):
        image = _small_image([(0, 256)])
        image['nonzero_bytes'] = [[0, 1]]
        with self.assertRaisesRegex(ValueError, 'complete planner word projection'):
            pr.decode_planner(image)


class PlannerNumericalTests(unittest.TestCase):
    def test_all_hex_digits_have_the_expected_numeric_meaning(self):
        self.assertEqual(pr.hex_nibbles('0123456789abcdef' * 4), list(range(16)) * 4)

    def test_digest_spelling_and_full_suffix_are_checked(self):
        for text in ('0' * 63, '0' * 65, 'A' * 64, '0' * 63 + 'g', '0' * 63 + 'é',
                     '0x' + '0' * 62, '0' * 63 + '\n', None, 0):
            with self.subTest(text=text), self.assertRaises(ValueError):
                pr.hex_nibbles(text)

    def test_big_endian_hex_prefix_and_leading_zeros_are_exact(self):
        for prefix in ('0000000000000000', '0000000000000001', '123456789abcdef0', 'ffffffffffffffff'):
            self.assertEqual(pr.prefix_number(prefix + 'a' * 48), int(prefix, 16))

    def test_unused_hex_suffix_still_requires_a_valid_full_digest(self):
        self.assertEqual(pr.prefix_number('1' * 16 + '0' * 48), pr.prefix_number('1' * 16 + 'f' * 48))
        with self.assertRaises(ValueError):
            pr.prefix_number('1' * 16 + 'g' * 48)

    def test_public_hash_preserves_the_original_domain_separation(self):
        value = {'a': 1, 'b': False}
        self.assertEqual(pr.public_hash(value), canonical_json_hash(value))
        self.assertNotEqual(pr.public_hash(value), pr.sha(pr.canonical(value)))
        self.assertEqual(pr.PUBLIC_HASH_DOMAIN, b'RCPRCLM-CANONICAL-JSON-V2\0')

    def test_empty_projection_retains_novelty_without_fabricated_weights(self):
        self.assertEqual(pr.score_from_projection([], '0' * 64, family=0, variant=0, generation=1, family_count=3),
                         20000 - 3 * 521)

    def test_signed_word_and_feature_coefficients_are_applied_before_sum(self):
        # The first feature is -3 and the second -2 for this fixed all-zero digest.
        self.assertEqual(pr.score_from_projection([[0, -7], [1, 5]], '0' * 64,
                         family=0, variant=0, generation=1, family_count=0), 20011)

    def test_projection_position_affects_both_feature_index_and_coefficient(self):
        # At j=0,index0 nibble0: feature=-3. At j=1,index5 nibble0: feature=-2.
        self.assertEqual(pr.score_from_projection([[0, 2], [5, 3]], '0123456789abcdef' * 4,
                         family=0, variant=0, generation=1, family_count=0), 19988)

    def test_family_variant_generation_and_count_change_numeric_result(self):
        arguments = dict(family=2, variant=3, generation=4, family_count=3)
        # 15 + 6 + 15 + 4 = 40, so the feature is 0 for j=0.
        self.assertEqual(pr.score_from_projection([[0, -32768]], 'f' * 64, **arguments), 18437)
        arguments['generation'] = 5
        self.assertEqual(pr.score_from_projection([[0, -32768]], 'f' * 64, **arguments), 18437 - 32768)

    def test_integer_arithmetic_does_not_wrap_at_machine_word_limits(self):
        score = pr.score_from_projection([], '0' * 64, family=0, variant=0,
                                         generation=1, family_count=pr.MAX_METADATA)
        self.assertEqual(score, 20000 - 521 * pr.MAX_METADATA)
        self.assertLess(score, -(1 << 63))

    def test_numeric_metadata_rejects_booleans_negative_and_out_of_range(self):
        original = dict(family=0, variant=0, generation=1, family_count=0)
        for field, values in {'family': (-1, 8, True), 'variant': (-1, 4, True),
                              'generation': (0, -1, True, pr.MAX_METADATA + 1),
                              'family_count': (-1, True, pr.MAX_METADATA + 1)}.items():
            for value in values:
                args = dict(original, **{field: value})
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    pr.score_from_projection([[0, 1]], '0' * 64, **args)

    def test_dot_product_requires_exact_canonical_nonzero_word_support(self):
        variants = ((), [[0]], [[0, 1, 2]], [[0, 0]], [[0, True]], [[0, 32768]],
                    [[0, 1], [0, 2]], [[1, 1], [0, 2]], [[pr.WORD_COUNT, 1]])
        for projection in variants:
            with self.subTest(projection=projection), self.assertRaises(ValueError):
                pr.score_from_projection(projection, '0' * 64, family=0, variant=0, generation=1, family_count=0)


class PlannerChoiceTests(unittest.TestCase):
    def table(self):
        return [{'program_hash': format(i, '064x'), 'family_index': i // 4,
                 'variant': i % 4, 'base_score': 0, 'ties': [0] * 5} for i in range(32)]

    def test_score_then_tie_then_program_key_order_is_exact(self):
        table = self.table()
        self.assertEqual(pr.reference_choice(table, [], 0), 31)
        table[3]['ties'][0] = 1
        self.assertEqual(pr.reference_choice(table, [], 0), 3)
        table[2]['base_score'] = 1
        self.assertEqual(pr.reference_choice(table, [], 0), 2)

    def test_rejections_change_only_their_own_family_pressure_and_tie_index(self):
        table = self.table()
        table[0]['ties'][1] = 100
        self.assertEqual(pr.reference_choice(table, [1], 0), 0)
        table[7]['base_score'] = 798
        self.assertEqual(pr.reference_choice(table, [1], 0), 7)

    def test_selected_programs_cannot_be_reselected(self):
        table = self.table()
        self.assertEqual(pr.reference_choice(table, [31], 0), 30)

    def test_after_four_rejections_selection_uses_complete_stride17_order(self):
        table = self.table()
        seen = [20, 5, 22, 7]
        self.assertEqual(pr.reference_choice(table, seen, 20), 24)
        table[31]['base_score'] = 10**20
        self.assertEqual(pr.reference_choice(table, seen, 20), 24)

    def test_every_offset_visits_each_remaining_program_once(self):
        table = self.table()
        for offset in range(32):
            seen = [0, 1, 2, 3]
            while len(seen) < 32:
                choice = pr.reference_choice(table, seen, offset)
                self.assertNotIn(choice, seen)
                seen.append(choice)
            self.assertEqual(set(seen), set(range(32)))
            self.assertIsNone(pr.reference_choice(table, seen, offset))

    def test_invalid_seen_prefix_or_offset_is_rejected(self):
        for seen, offset in (([1, 1], 0), ([-1], 0), ([32], 0), ([True], 0), ((), 0), ([], -1), ([], 32), ([], False)):
            with self.subTest(seen=seen, offset=offset), self.assertRaises(ValueError):
                pr.reference_choice(self.table(), seen, offset)

    def test_table_keys_and_scores_must_be_exact(self):
        for change in ('missing', 'reordered', 'duplicate', 'bool_score', 'short_ties', 'extra'):
            table = self.table()
            if change == 'missing': table.pop()
            elif change == 'reordered': table.reverse()
            elif change == 'duplicate': table[1] = copy.deepcopy(table[0])
            elif change == 'bool_score': table[0]['base_score'] = True
            elif change == 'short_ties': table[0]['ties'].pop()
            else: table[0]['accepted'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                pr.reference_choice(table, [], 0)


class PlannerBoundInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = _prepared()
        cls.packet = cls.prepared.packet

    def altered(self, change):
        packet = copy.deepcopy(self.packet)
        change(packet)
        return packet

    def reject(self, packet):
        with self.assertRaises(ValueError):
            pr.validate_packet(packet)

    def test_original_complete_projection_tables_and_trace_are_bound(self):
        packet = self.packet
        self.assertEqual(len(packet['before']['nonzero_words']), 84)
        self.assertEqual(len(packet['after']['nonzero_words']), 84)
        self.assertEqual(len(packet['ranking']['rows']), 32)
        self.assertEqual(sum(len(row['tie_digests']) for row in packet['ranking']['rows']), 160)
        self.assertEqual(packet['before_table'], pr.producer_packet(packet)['trace']['table'])
        self.assertEqual(packet['after_table'], packet['before_table'])
        self.assertEqual(packet['ranking']['offset'], 20)
        self.assertEqual(len(packet['selected_choices']), 9)
        self.assertIsNot(packet['before'], packet['after'])
        self.assertEqual(self.prepared.captured_json().packet_bytes, (ROOT / pr.T_PACKET).read_bytes())

    def test_all_32_independent_scores_match_existing_reference_ranker(self):
        ranking = self.packet['ranking']
        view = pr.CurrentView.from_json(ranking['current_view'])
        programs = tuple(row['program'] for row in ranking['rows'])
        oracle = proposal_provenance.score_table(view, programs, tuple(tuple(word) for word in self.packet['before']['nonzero_words']))
        self.assertEqual(self.packet['before_table'], oracle)

    def test_every_public_digest_and_domain_preimage_is_retained(self):
        ranking = self.packet['ranking']
        self.assertEqual(ranking['seed_digest'], canonical_json_hash(ranking['seed_preimage']))
        self.assertEqual(ranking['freeze_digest'], canonical_json_hash(ranking['freeze_preimage']))
        for row in ranking['rows']:
            self.assertEqual(row['key'], canonical_json_hash(row['program']))
            self.assertEqual(row['feature_digest'], canonical_json_hash(row['feature_preimage']))
            self.assertEqual(row['tie_digests'], [canonical_json_hash(value) for value in row['tie_preimages']])

    def test_prepared_bytes_are_immutable_and_packet_access_is_detached(self):
        packet = self.prepared.packet
        packet['ranking']['offset'] = 0
        self.assertEqual(self.prepared.packet['ranking']['offset'], 20)
        with self.assertRaises(FrozenInstanceError):
            self.prepared.packet_bytes = b'{}'

    def test_prepared_input_requires_canonical_immutable_bounded_bytes(self):
        for raw in (b'', bytearray(self.prepared.packet_bytes), self.prepared.packet_bytes + b'\n', b'{}'):
            with self.subTest(kind=type(raw)), self.assertRaises(ValueError):
                pr.PreparedPlannerRefinement(raw)
        with patch.object(pr, 'MAX_BYTES', len(self.prepared.packet_bytes) - 1), self.assertRaises(ValueError):
            pr.PreparedPlannerRefinement(self.prepared.packet_bytes)

    def test_packet_fields_schema_policy_and_base_are_exact(self):
        for field, value in (('schema', 'old'), ('policy', 'loose'), ('base_commit', '0' * 40), ('extra', False)):
            self.reject(self.altered(lambda packet: packet.__setitem__(field, value)))
        packet = copy.deepcopy(self.packet); del packet['before']
        self.reject(packet)

    def test_broader_claims_cannot_be_enabled_or_encoded_as_zero(self):
        for value in (True, 0, None):
            self.reject(self.altered(lambda packet: packet['claims'].__setitem__('root_transition_verified', value)))

    def test_scope_cannot_silently_close_external_boundaries(self):
        for field in ('byte_capture_remains_external', 'public_hash_computation_remains_external',
                      'program_metadata_interpretation_remains_external', 'python_execution_remains_external',
                      'trusted_import_cache_assumption'):
            self.reject(self.altered(lambda packet: packet['scope'].__setitem__(field, False)))
        self.reject(self.altered(lambda packet: packet['scope'].__setitem__('general_planner_equivalence', True)))

    def test_declared_profile_cannot_change_tariff_or_hash_domain(self):
        for field, value in (('rejection_pressure', 798), ('enumeration_stride', 1), ('public_hash_domain_hex', ''),
                             ('tensor_bytes', 65535), ('element', 'unsigned')):
            self.reject(self.altered(lambda packet: packet['profile'].__setitem__(field, value)))

    def test_fixed_retained_t_anchors_cannot_be_replaced(self):
        self.reject(self.altered(lambda packet: packet['retained_t'].__setitem__(pr.T_PACKET, '0' * 64)))

    def test_changed_nested_t_packet_is_rejected_after_outer_rehash(self):
        packet = copy.deepcopy(self.packet)
        packet['captured_json_packet']['scope']['python_execution_remains_external'] = False
        packet['captured_json_packet_sha256'] = pr.sha(pr.canonical(packet['captured_json_packet']))
        self.reject(packet)

    def test_cross_candidate_binding_is_rejected(self):
        for key in ('predecessor_physical_hash', 'candidate_physical_hash', 'transcript_sha256'):
            self.reject(self.altered(lambda packet: packet['bindings'].__setitem__(key, '0' * 64)))

    def test_captured_image_digest_is_not_caller_authority(self):
        for side in ('before', 'after'):
            packet = copy.deepcopy(self.packet)
            raw = bytearray(pr.decode_planner(packet[side])); raw[1200] = 1
            packet[side] = pr.encode_planner(bytes(raw))
            packet['tensor_sha256'][side] = pr.sha(bytes(raw))
            self.reject(packet)

    def test_word_omission_is_rejected_before_inherited_deep_validation(self):
        packet = self.altered(lambda value: value['after']['nonzero_words'].pop())
        with patch.object(pr.captured, 'PreparedCapturedJson', side_effect=AssertionError('inherited validation should not run')):
            self.reject(packet)

    def test_declared_tensor_hash_and_coverage_are_exact(self):
        packet = self.altered(lambda value: value['tensor_sha256'].__setitem__('after', '0' * 64))
        self.reject(packet)
        packet = copy.deepcopy(self.packet); packet['tensor_sha256'].pop('before')
        self.reject(packet)

    def test_public_feature_digest_is_recomputed_from_fixed_original_context(self):
        packet = copy.deepcopy(self.packet)
        row = packet['ranking']['rows'][0]
        row['feature_preimage']['challenge_stream'] = 'future-winning-stream'
        row['feature_digest'] = pr.public_hash(row['feature_preimage'])
        self.reject(packet)

    def test_public_tie_digest_and_rejection_count_cannot_be_substituted(self):
        packet = copy.deepcopy(self.packet)
        row = packet['ranking']['rows'][0]
        row['tie_preimages'][0]['rejection_count'] = 1
        row['tie_digests'][0] = pr.public_hash(row['tie_preimages'][0])
        self.reject(packet)

    def test_changed_descriptor_cannot_be_accepted_by_rehashing_its_key(self):
        packet = copy.deepcopy(self.packet)
        row = packet['ranking']['rows'][0]
        row['program']['generation'] += 1
        row['key'] = pr.public_hash(row['program'])
        row['feature_preimage']['program'] = row['program']
        row['feature_digest'] = pr.public_hash(row['feature_preimage'])
        self.reject(packet)

    def test_current_view_and_family_count_are_not_candidate_fields(self):
        for field in ('family_count', 'family'):
            packet = copy.deepcopy(self.packet); packet['ranking']['rows'][0][field] += 1
            self.reject(packet)
        packet = copy.deepcopy(self.packet); packet['ranking']['current_view']['turn_index'] += 1
        self.reject(packet)

    def test_numeric_table_must_match_both_bytes_and_imported_context(self):
        for side in ('before', 'after'):
            packet = copy.deepcopy(self.packet); packet[side + '_table'][0]['base_score'] += 1
            self.reject(packet)
            packet = copy.deepcopy(self.packet); packet[side + '_table'][0]['ties'][0] += 1
            self.reject(packet)

    def test_complete_ordered_rows_cannot_be_omitted_or_reordered(self):
        for field in ('before_table', 'after_table'):
            for change in ('omit', 'reverse', 'duplicate'):
                packet = copy.deepcopy(self.packet)
                if change == 'omit': packet[field].pop()
                elif change == 'reverse': packet[field].reverse()
                else: packet[field][1] = copy.deepcopy(packet[field][0])
                self.reject(packet)

    def test_freeze_digest_and_enumeration_offset_are_original_bindings(self):
        for field, value in (('offset', 0), ('freeze_digest', '0' * 64), ('seed_digest', '0' * 64)):
            packet = copy.deepcopy(self.packet); packet['ranking'][field] = value
            self.reject(packet)
        packet = copy.deepcopy(self.packet)
        packet['ranking']['freeze_preimage']['candidates'][0]['base_score'] += 1
        packet['ranking']['freeze_digest'] = pr.public_hash(packet['ranking']['freeze_preimage'])
        self.reject(packet)

    def test_full_rejection_prefix_cannot_be_skipped_reordered_or_duplicated(self):
        for change in ('last_only', 'reverse', 'duplicate'):
            packet = copy.deepcopy(self.packet)
            if change == 'last_only': packet['selected_choices'] = packet['selected_choices'][-1:]
            elif change == 'reverse': packet['selected_choices'].reverse()
            else: packet['selected_choices'][1] = packet['selected_choices'][0]
            self.reject(packet)

    def test_packet_verifier_requires_external_anchor_and_exact_reconstruction(self):
        raw = self.prepared.packet_bytes
        with self.assertRaises(ValueError):
            pr.verify_packet_bytes(raw, self.prepared, expected_sha256='0' * 64)
        changed = self.altered(lambda packet: packet['ranking'].__setitem__('offset', 0))
        raw_changed = pr.canonical(changed)
        with self.assertRaises(ValueError):
            pr.verify_packet_bytes(raw_changed, self.prepared, expected_sha256=pr.sha(raw_changed))

    def test_summary_retains_actual_counts_without_broader_authority(self):
        summary = pr.summary(self.prepared)
        self.assertEqual(summary['word_count_per_package'], 32768)
        self.assertEqual(summary['tensor_bytes_per_package'], 65536)
        self.assertEqual(summary['feature_digests'], 32)
        self.assertEqual(summary['tie_digests'], 160)
        self.assertEqual(summary['nonzero_words_per_package'], {'before': 84, 'after': 84})
        self.assertFalse(any(self.packet['claims'].values()))


class PlannerPhysicalPreparationTests(unittest.TestCase):
    def test_fresh_packages_reconstruct_exact_inputs_without_workers_or_compiler(self):
        with tempfile.TemporaryDirectory(prefix='r17u-test-') as temp:
            packages = Path(temp) / 'packages'
            with patch('subprocess.Popen', side_effect=AssertionError('no process permitted in preparation')):
                actual = pr.prepare_planner_refinement(ROOT, packages)
            self.assertEqual(actual.packet_bytes, _prepared().packet_bytes)
            self.assertEqual((packages / 'before' / pr.PLANNER_PATH).read_bytes(), _planner_bytes())
            self.assertEqual((packages / 'after' / pr.PLANNER_PATH).read_bytes(), _planner_bytes())
            pr.verify_packet_bytes(actual.packet_bytes, actual, expected_sha256=pr.sha(actual.packet_bytes))

    def test_missing_retained_file_is_refused(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
            pr.read_retained(Path(temp))

    def test_corrupted_retained_file_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / pr.T_EXECUTION
            path.parent.mkdir(parents=True); path.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'retained T input changed'):
                pr.read_retained(root)

    def test_linked_retained_input_is_rejected_by_capture_guard(self):
        # Mock path metadata so this rejection test is portable without symlink privileges.
        with patch.object(Path, 'is_symlink', return_value=True), self.assertRaises(ValueError):
            pr.read_retained(ROOT)

    def test_missing_or_truncated_one_side_capture_cannot_use_other_side(self):
        for missing in (True, False):
            with tempfile.TemporaryDirectory() as temp:
                packages = Path(temp) / 'packages'
                path = packages / 'before' / pr.PLANNER_PATH
                path.parent.mkdir(parents=True); path.write_bytes(_planner_bytes())
                if not missing:
                    path = packages / 'after' / pr.PLANNER_PATH
                    path.parent.mkdir(parents=True); path.write_bytes(_planner_bytes()[:-2])
                with (patch.object(pr.captured, 'prepare_captured_json', return_value=_prepared().captured_json()),
                      self.assertRaisesRegex(ValueError, 'complete physical planner image missing')):
                    pr.prepare_planner_refinement(ROOT, packages)


class PlannerRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcp_rclm_runtime_v5.phase17 import planner_refinement_lean as renderer
        cls.renderer = renderer
        cls.sources = renderer.generated_sources(_prepared(), source_root=ROOT)

    def test_generated_inventory_has_fresh_dependency_chain_and_all_controls(self):
        renderer = self.renderer
        self.assertEqual(list(self.sources), [*renderer.DEPENDENCY_LABELS, *renderer.LABELS])
        self.assertEqual(len(self.sources), 17)
        self.assertEqual(len(renderer.NAMES), 15)
        self.assertEqual(len(renderer.LABELS[1:]), 12)
        for label in renderer.DEPENDENCY_LABELS:
            self.assertNotIn(b'#print', self.sources[label])
        for label in renderer.LABELS:
            self.assertTrue(self.sources[label].startswith(b'import Phase17TDependency\n'))

    def test_t_dependency_preserves_every_proof_line_except_exact_audit_commands(self):
        from rcp_rclm_runtime_v5.phase17 import captured_json_lean
        original = (ROOT / pr.T_SOURCE).read_bytes()
        expected = {('#print axioms ' + name + '\n').encode() for name in captured_json_lean.NAMES}
        preserved = b''.join(line for line in original.splitlines(keepends=True) if line not in expected)
        self.assertEqual(self.sources['Phase17TDependency'], preserved)
        self.assertEqual(pr.sha(original), pr.T_SOURCE_SHA)

    def test_complete_zero_complement_coverage_uses_all128_distinct_blocks(self):
        import re
        text = self.sources['PlannerRefinement'].decode()
        blocks = re.findall(r'private theorem checked_block_([0-9]{3}) : decodedBlock beforeImage ([0-9]+)', text)
        self.assertEqual(blocks, [(str(i).zfill(3), str(i)) for i in range(128)])
        self.assertIn('projection_from_blocks beforeImage expectedProjection checked_blocks', text)
        self.assertIn('decodedProjection afterImage = expectedProjection', text)

    def test_numeric_targets_are_actual_q_context_and_t_bindings(self):
        text = self.sources['PlannerRefinement'].decode()
        self.assertIn('some Phase17Provenance.selectedContext.rows', text)
        self.assertIn('Phase17Finite.selectedConfiguration.context', text)
        self.assertIn('Phase17Json.selected_package_reconstruction.1', text)
        self.assertIn('Phase17Provenance.selected_provenance', text)
        for row in _prepared().packet['ranking']['rows']:
            self.assertIn(row['feature_digest'], text)
            for digest in row['tie_digests']:
                self.assertIn(digest, text)

    def test_every_negative_checks_its_whole_proposition_before_expected_rejection(self):
        for label in self.renderer.LABELS[1:]:
            text = self.sources[label].decode()
            with self.subTest(label=label):
                self.assertIn('theorem control_false :', text)
                self.assertIn('= false := by\n  with_unfolding_all rfl', text)
                self.assertIn(':= of_decide_eq_false control_false', text)
                self.assertIn('simp only [h]\n  decide +kernel', text)
                self.assertNotIn('#print axioms', text)
                self.assertNotIn('theorem selected_rows_bound', text)

    def test_generated_source_guards_reject_native_and_placeholder_forms(self):
        original = self.renderer.template(ROOT)
        for suffix in (b'\nexample : True := by native_decide\n',
                       b'\nexample : True := by decide +native\n',
                       b'\nexample : True := by decide + native\n',
                       b'\nexample : True := by sorry\n', b'\naxiom counterfeit : False\n',
                       b'\nunsafe def counterfeit : Nat := 0\n',
                       b'\npartial def counterfeit : Nat := 0\n'):
            with self.subTest(suffix=suffix), patch.object(self.renderer, 'template', return_value=original + suffix):
                with self.assertRaisesRegex(ValueError, 'forbidden planner refinement proof token'):
                    self.renderer._render_validated(_prepared(), source_root=ROOT, negative='ChangedRowKey')

    def test_template_pin_rejects_changed_source_before_rendering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / self.renderer.BRIDGE_PATH
            path.parent.mkdir(parents=True)
            path.write_bytes(self.renderer.template(ROOT) + b'\n')
            with self.assertRaisesRegex(ValueError, 'template pin differs'):
                self.renderer.template(root)

    def test_public_renderer_rejects_unsupported_packet_type_or_control(self):
        with self.assertRaises(ValueError):
            self.renderer.render(_prepared(), source_root=ROOT, negative='invented')
        with self.assertRaises(ValueError):
            self.renderer.generated_sources(_prepared().packet, source_root=ROOT)


if __name__ == '__main__':
    unittest.main()
