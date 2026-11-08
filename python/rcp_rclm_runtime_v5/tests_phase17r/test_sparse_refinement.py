"""Phase 17R numerical refinement and adversarial certificate boundaries.

One fixture is reconstructed from the actual pinned packages. Hand-built tensor
cases provide independent integer/byte oracles. Compiler-output fixtures, when
used below, exercise only validation and never count as actual Lean evidence.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import sparse_refinement as sr
from rcp_rclm_runtime_v5.phase17 import sparse_refinement_check as sc

ROOT = Path(__file__).resolve().parents[3]
WIDTH = 320
VOCAB = 260
SIZE = 2 * WIDTH * WIDTH
EOS = 258


def _tensor(entries=()):
    """Independent little-endian packing: entries are (current,target,raw)."""
    raw = bytearray(SIZE)
    for current, target, value in entries:
        struct.pack_into('<h', raw, 2 * (target * WIDTH + current), value)
    return bytes(raw)


def _column(scores, current=0):
    return _tensor((current, target, 2048 * score)
                   for target, score in enumerate(scores))


def _chain(edges):
    return _tensor((current, target, 24576) for current, target in edges)


class TensorAndDecoderTests(unittest.TestCase):
    def test_signed_little_endian_boundary_oracles(self):
        cases = ((0, 0, 0), (1, 0, 1), (0, 1, 256), (96, 0, 96),
                 (0, 96, 24576), (255, 127, 32767), (0, 128, -32768),
                 (255, 255, -1), (0, 248, -2048), (0, 8, 2048))
        for lo, hi, expected in cases:
            with self.subTest(lo=lo, hi=hi):
                self.assertEqual(sr.signed16(lo, hi), expected)
                self.assertEqual(sr.signed16(lo, hi), struct.unpack('<h', bytes((lo, hi)))[0])

    def test_signed_byte_types_and_range_are_exact(self):
        for invalid in (-1, 256, True, False, 1.0, '1', None):
            for pair in ((invalid, 0), (0, invalid)):
                with self.subTest(pair=pair), self.assertRaises((ValueError, TypeError)):
                    sr.signed16(*pair)

    def test_sparse_roundtrip_includes_last_padding_byte(self):
        raw = bytearray(SIZE)
        raw[0], raw[37], raw[-1] = 255, 1, 128
        encoded = sr.encode_tensor(bytes(raw))
        self.assertEqual(encoded, {'byte_length': SIZE,
                                  'nonzero_bytes': [[0, 255], [37, 1], [SIZE - 1, 128]]})
        self.assertEqual(sr.decode_tensor(encoded), bytes(raw))

    def test_all_zero_tensor_has_unique_empty_sparse_encoding(self):
        encoded = {'byte_length': SIZE, 'nonzero_bytes': []}
        self.assertEqual(sr.encode_tensor(bytes(SIZE)), encoded)
        self.assertEqual(sr.decode_tensor(encoded), bytes(SIZE))

    def test_encoding_requires_exact_immutable_tensor_bytes(self):
        for value in (b'', bytes(SIZE - 1), bytes(SIZE + 1), bytearray(SIZE), '0' * SIZE):
            with self.subTest(kind=type(value).__name__, size=len(value)), self.assertRaises((ValueError, TypeError)):
                sr.encode_tensor(value)

    def test_sparse_record_rejects_missing_or_extra_fields(self):
        for record in ({'nonzero_bytes': []}, {'byte_length': SIZE},
                       {'byte_length': SIZE, 'nonzero_bytes': [], 'accepted': True}):
            with self.subTest(record=record), self.assertRaises((ValueError, KeyError, TypeError)):
                sr.decode_tensor(record)

    def test_sparse_record_requires_exact_length_and_container_types(self):
        for length in (SIZE - 1, SIZE + 1, float(SIZE), True, str(SIZE)):
            with self.subTest(length=length), self.assertRaises((ValueError, TypeError)):
                sr.decode_tensor({'byte_length': length, 'nonzero_bytes': []})
        for entries in ((), None, {}, '[]'):
            with self.subTest(entries=entries), self.assertRaises((ValueError, TypeError)):
                sr.decode_tensor({'byte_length': SIZE, 'nonzero_bytes': entries})

    def test_sparse_offsets_must_be_strictly_ordered(self):
        with self.assertRaises(ValueError):
            sr.decode_tensor({'byte_length': SIZE, 'nonzero_bytes': [[5, 1], [4, 2]]})

    def test_sparse_duplicate_offsets_are_rejected(self):
        with self.assertRaises(ValueError):
            sr.decode_tensor({'byte_length': SIZE, 'nonzero_bytes': [[5, 1], [5, 2]]})

    def test_sparse_offset_range_and_integer_types(self):
        for offset in (-1, SIZE, SIZE + 1, 1.0, True, '1'):
            with self.subTest(offset=offset), self.assertRaises((ValueError, TypeError)):
                sr.decode_tensor({'byte_length': SIZE, 'nonzero_bytes': [[offset, 1]]})

    def test_sparse_values_are_nonzero_exact_bytes(self):
        for value in (0, -1, 256, 1.0, True, '1'):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                sr.decode_tensor({'byte_length': SIZE, 'nonzero_bytes': [[0, value]]})

    def test_sparse_entries_have_exact_pair_shape(self):
        for entry in ([0], [0, 1, 2], (0, 1), {'offset': 0, 'byte': 1}):
            with self.subTest(entry=entry), self.assertRaises((ValueError, TypeError)):
                sr.decode_tensor({'byte_length': SIZE, 'nonzero_bytes': [entry]})

    def test_signed_score_division_has_known_negative_and_positive_values(self):
        raw_values = (-32768, -30720, -2048, 0, 2048, 30720)
        raw = _tensor((7, i, v) for i, v in enumerate(raw_values))
        rows = sr.scores_from_tensor(raw)
        self.assertEqual(rows[7][:6], [-16, -15, -1, 0, 1, 15])
        self.assertEqual(len(rows), VOCAB)
        self.assertTrue(all(len(row) == VOCAB for row in rows))

    def test_tensor_index_uses_target_stride_and_current_column(self):
        rows = sr.scores_from_tensor(_tensor(((7, 11, 6144), (259, 259, -2048))))
        self.assertEqual(rows[7][11], 3)
        self.assertEqual(rows[11][7], 0)
        self.assertEqual(rows[259][259], -1)
        self.assertEqual(sum(value != 0 for row in rows for value in row), 2)

    def test_score_projection_does_not_treat_padding_as_vocabulary(self):
        raw = _tensor(((319, 319, 1), (300, 2, 32767), (2, 300, -32767)))
        self.assertEqual(sr.scores_from_tensor(raw), [[0] * VOCAB for _ in range(VOCAB)])
        self.assertEqual(sr.decode_tensor(sr.encode_tensor(raw)), raw)

    def test_nonintegral_scores_are_rejected_instead_of_rounded(self):
        for value in (1, -1, 32767, -32767, 2049, -2049):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sr.scores_from_tensor(_tensor(((259, 259, value),)))

    def test_score_decoder_refuses_wrong_size_or_mutable_input(self):
        for raw in (bytes(SIZE - 2), bytes(SIZE + 2), bytearray(SIZE), b''):
            with self.subTest(kind=type(raw).__name__, size=len(raw)), self.assertRaises((ValueError, TypeError)):
                sr.scores_from_tensor(raw)

    def test_uniform_scores_produce_exact_uniform_masses(self):
        masses = sr.masses_from_scores([0] * VOCAB)
        self.assertEqual(masses, [1] * VOCAB)
        self.assertEqual(sum(Fraction(mass, sum(masses)) for mass in masses), Fraction(1))

    def test_clipping_minimum_shift_and_dyadic_extremes(self):
        scores = [-16, -15, -14, 0, 15] + [0] * (VOCAB - 5)
        masses = sr.masses_from_scores(scores)
        self.assertEqual(masses[:5], [1, 1, 2, 1 << 15, 1 << 30])
        self.assertEqual(masses[5:], [1 << 15] * (VOCAB - 5))
        self.assertEqual(sum(Fraction(mass, sum(masses)) for mass in masses), Fraction(1))

    def test_common_score_shift_preserves_masses_without_clipping(self):
        scores = [-4, -1, 0, 2] + [0] * (VOCAB - 4)
        self.assertEqual(sr.masses_from_scores(scores),
                         sr.masses_from_scores([value + 5 for value in scores]))

    def test_mass_input_is_complete_typed_bounded_row(self):
        for row in ([0] * (VOCAB - 1), [0] * (VOCAB + 1), tuple([0] * VOCAB),
                    [-17] + [0] * (VOCAB - 1), [16] + [0] * (VOCAB - 1),
                    [True] + [0] * (VOCAB - 1), [1.0] + [0] * (VOCAB - 1)):
            with self.subTest(kind=type(row).__name__, first=row[0]), self.assertRaises((ValueError, TypeError)):
                sr.masses_from_scores(row)

    def test_greedy_chain_records_real_current_and_raw_scores(self):
        result = sr.decode_greedy(_chain(((0, 1), (1, 2), (2, EOS))), 0)
        self.assertEqual(result['tokens'], [1, 2, EOS])
        self.assertTrue(result['stopped_on_eos'])
        self.assertEqual(result['termination'], 'eos')
        self.assertEqual(result['steps'], [
            {'current': 0, 'selected': 1, 'score': 12, 'runner_up': 0},
            {'current': 1, 'selected': 2, 'score': 12, 'runner_up': 0},
            {'current': 2, 'selected': EOS, 'score': 12, 'runner_up': 0}])

    def test_greedy_uses_raw_scores_when_clipping_creates_mass_tie(self):
        scores = [-16] * VOCAB
        scores[7] = -15
        self.assertEqual(sr.masses_from_scores(scores), [1] * VOCAB)
        result = sr.decode_greedy(_column(scores), 0, max_tokens=1)
        self.assertEqual(result['tokens'], [7])
        self.assertEqual(result['steps'][0]['score'], -15)
        self.assertEqual(result['steps'][0]['runner_up'], -16)

    def test_greedy_equal_maxima_choose_lowest_token_id(self):
        scores = [0] * VOCAB
        scores[3] = scores[10] = 8
        result = sr.decode_greedy(_column(scores), 0, max_tokens=1)
        self.assertEqual(result['tokens'], [3])
        self.assertEqual(result['steps'][0]['runner_up'], 8)

    def test_greedy_uniform_tensor_selects_zero_and_respects_default_limit(self):
        result = sr.decode_greedy(bytes(SIZE), 84)
        self.assertEqual(result['tokens'], [0] * 16)
        self.assertFalse(result['stopped_on_eos'])
        self.assertEqual(result['termination'], 'token_limit')
        self.assertEqual(len(result['steps']), 16)

    def test_greedy_eos_is_terminal_even_if_eos_row_has_successor(self):
        result = sr.decode_greedy(_chain(((0, EOS), (EOS, 1))), 0)
        self.assertEqual(result['tokens'], [EOS])
        self.assertEqual(len(result['steps']), 1)
        self.assertTrue(result['stopped_on_eos'])
        self.assertEqual(result['termination'], 'eos')

    def test_greedy_other_special_tokens_terminate_without_eos_success(self):
        for token in (256, 257, 259):
            with self.subTest(token=token):
                result = sr.decode_greedy(_chain(((0, token), (token, 1))), 0)
                self.assertEqual(result['tokens'], [token])
                self.assertEqual(len(result['steps']), 1)
                self.assertFalse(result['stopped_on_eos'])
                self.assertEqual(result['termination'], 'non_byte_token')

    def test_greedy_nonterminating_cycle_stops_at_declared_token_limit(self):
        result = sr.decode_greedy(_chain(((4, 5), (5, 4))), 4, max_tokens=3)
        self.assertEqual(result['tokens'], [5, 4, 5])
        self.assertFalse(result['stopped_on_eos'])
        self.assertEqual(result['termination'], 'token_limit')

    def test_greedy_marker_and_limit_types_and_bounds(self):
        for marker in (-1, VOCAB, True, 0.0, '0'):
            with self.subTest(marker=marker), self.assertRaises((ValueError, TypeError)):
                sr.decode_greedy(bytes(SIZE), marker)
        for limit in (0, 17, True, 1.0, '1'):
            with self.subTest(limit=limit), self.assertRaises((ValueError, TypeError)):
                sr.decode_greedy(bytes(SIZE), 0, max_tokens=limit)


class SparsePacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='r17r-tests-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.packages = Path(cls.temp.name) / 'packages'
        cls.prepared = sr.prepare_sparse_refinement(ROOT, cls.packages)
        cls.raw = cls.prepared.packet_bytes
        cls.value = cls.prepared.packet

    def bad(self, mutate):
        packet = copy.deepcopy(self.value)
        mutate(packet)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            sr.PreparedSparseRefinement(sr.canonical(packet))

    def test_selected_refinement_keeps_exact_q_baseline_and_packet(self):
        self.assertEqual(self.value['base_commit'], '54de3a0841bb747207e2721566e38f6582b8874b')
        self.assertEqual(self.value['finite_packet_sha256'],
                         'b6dd8df26fb7efc25c6fed6cc7832bf65a42b933fd2d1276346695bd8451c9e5')
        self.assertEqual(sr.sha(self.prepared.finite().packet_bytes), self.value['finite_packet_sha256'])
        self.assertEqual(self.prepared.finite().packet, self.value['finite_packet'])
        self.assertEqual(self.value['bindings'], self.value['finite_packet']['bindings'])

    def test_complete_sparse_images_are_exact_captured_tensor_bytes(self):
        protected = self.value['finite_packet']['protected_packet']
        for which in ('before', 'after'):
            with self.subTest(which=which):
                raw = sr.decode_tensor(self.value[which])
                self.assertEqual(raw, bytes.fromhex(protected[which]['tensor_hex']))
                self.assertEqual(sr.sha(raw), protected[which]['tensor_sha256'])
                self.assertEqual(len(raw), SIZE)
                self.assertEqual(len(self.value[which]['nonzero_bytes']), 178)

    def test_all_67600_cells_bind_to_the_existing_q_observation(self):
        protected = self.value['finite_packet']['protected_packet']
        for which in ('before', 'after'):
            expected = protected[which]
            rows = sr.scores_from_tensor(sr.decode_tensor(self.value[which]))
            self.assertEqual(len(rows), VOCAB)
            for current, row in enumerate(rows):
                index = expected['row_selectors'][current]
                self.assertEqual(row, expected['score_dictionary'][index], (which, current))
                self.assertEqual(sr.masses_from_scores(row),
                                 [weight + 1 for weight in expected['mass_minus_one_dictionary'][index]],
                                 (which, current))

    def test_eleven_post_route_goals_have_exact_28_eos_terminated_steps(self):
        self.assertEqual(len(self.value['markers']), 11)
        self.assertEqual(len(self.value['targets']), 11)
        self.assertEqual(sum(map(len, self.value['targets'])), 28)
        for which in ('before', 'after'):
            raw = sr.decode_tensor(self.value[which])
            for marker, target in zip(self.value['markers'], self.value['targets'], strict=True):
                result = sr.decode_greedy(raw, marker)
                self.assertEqual(result['tokens'], target)
                self.assertTrue(result['stopped_on_eos'])
                self.assertEqual(result['termination'], 'eos')

    def test_broader_authority_and_physical_claims_remain_false(self):
        self.assertEqual(len(self.value['claims']), 24)
        self.assertTrue(all(value is False for value in self.value['claims'].values()))
        self.assertFalse(self.value['claims']['physical_projection_formally_verified'])
        self.assertFalse(self.value['claims']['full_goal_interpretation_supplied'])

    def test_prepared_packet_is_immutable(self):
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            self.prepared.packet_bytes = b'{}'

    def test_returned_projection_cannot_mutate_immutable_input(self):
        value = self.prepared.packet
        value['before']['nonzero_bytes'][0][1] = 1
        self.assertEqual(self.prepared.packet_bytes, self.raw)
        self.assertEqual(self.prepared.packet, self.value)

    def test_external_packet_anchor_is_required(self):
        with self.assertRaises(ValueError):
            sr.verify_packet_bytes(self.raw, self.prepared, expected_sha256='0' * 64)

    def test_rehashing_different_packet_bytes_does_not_make_recomputed_evidence(self):
        raw = self.raw + b'\n'
        with self.assertRaises(ValueError):
            sr.verify_packet_bytes(raw, self.prepared, expected_sha256=sr.sha(raw))

    def test_noncanonical_and_duplicate_key_json_are_rejected(self):
        for raw in (json.dumps(self.value, indent=2).encode(), b'{"schema":1,"schema":2}'):
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                sr.PreparedSparseRefinement(raw)

    def test_mutable_empty_and_oversized_packet_are_rejected(self):
        for raw in (b'', bytearray(self.raw), '{}', b'x' * (sr.MAX_BYTES + 1)):
            with self.subTest(kind=type(raw).__name__, size=len(raw)), self.assertRaises((ValueError, TypeError)):
                sr.PreparedSparseRefinement(raw)

    def test_packet_requires_exact_fields_schema_policy_and_base(self):
        self.bad(lambda p: p.pop('before'))
        self.bad(lambda p: p.update(accepted=True))
        self.bad(lambda p: p.update(schema='other'))
        self.bad(lambda p: p.update(policy='other'))
        self.bad(lambda p: p.update(base_commit='0' * 40))

    def test_no_broader_claim_can_be_enabled(self):
        for flag in self.value['claims']:
            with self.subTest(flag=flag):
                self.bad(lambda p, key=flag: p['claims'].__setitem__(key, True))

    def test_integer_zero_cannot_substitute_for_false_claim(self):
        self.bad(lambda p: p['claims'].__setitem__('physical_execution_attested', 0))

    def test_scope_or_profile_cannot_be_redefined(self):
        self.bad(lambda p: p['scope'].update(universal_physical_refinement=True))
        self.bad(lambda p: p['scope'].pop(next(iter(p['scope']))))
        self.bad(lambda p: p['profile'].update(vocabulary=259))

    def test_mixed_package_binding_is_rejected(self):
        self.bad(lambda p: p['bindings'].__setitem__('candidate_physical_hash', '0' * 64))

    def test_finite_packet_cannot_be_replaced_by_a_report_or_digest(self):
        self.bad(lambda p: p.update(finite_packet={'status': 'passed'}))
        self.bad(lambda p: p.update(finite_packet_sha256='0' * 64))

    def test_changed_q_probability_even_with_finite_packet_rehash_is_rejected(self):
        def mutate(p):
            p['finite_packet']['protected_packet']['after']['mass_minus_one_dictionary'][0][0] += 1
            p['finite_packet']['protected_packet_sha256'] = sr.sha(sr.canonical(p['finite_packet']['protected_packet']))
            p['finite_packet_sha256'] = sr.sha(sr.canonical(p['finite_packet']))
        self.bad(mutate)

    def test_changed_q_selector_even_with_finite_packet_rehash_is_rejected(self):
        def mutate(p):
            o = p['finite_packet']['protected_packet']['before']
            o['row_selectors'][0] = (o['row_selectors'][0] + 1) % len(o['score_dictionary'])
            p['finite_packet']['protected_packet_sha256'] = sr.sha(sr.canonical(p['finite_packet']['protected_packet']))
            p['finite_packet_sha256'] = sr.sha(sr.canonical(p['finite_packet']))
        self.bad(mutate)

    def test_missing_nonzero_byte_is_rejected(self):
        self.bad(lambda p: p['before']['nonzero_bytes'].pop())

    def test_changed_byte_cannot_be_hidden_by_equal_before_and_after(self):
        def mutate(p):
            for which in ('before', 'after'):
                p[which]['nonzero_bytes'][0][1] += 1
            raw = sr.decode_tensor(p['before'])
            p['tensor_sha256'] = {which: sr.sha(raw) for which in ('before', 'after')}
        self.bad(mutate)

    def test_changed_padding_is_rejected_despite_unchanged_selected_scores(self):
        def mutate(p):
            raw = bytearray(sr.decode_tensor(p['before']))
            raw[-1] ^= 1
            changed = bytes(raw)
            self.assertEqual(sr.scores_from_tensor(changed),
                             sr.scores_from_tensor(sr.decode_tensor(p['before'])))
            for which in ('before', 'after'):
                p[which] = sr.encode_tensor(changed)
            p['tensor_sha256'] = {which: sr.sha(changed) for which in ('before', 'after')}
        self.bad(mutate)

    def test_external_q_evidence_identity_is_required(self):
        self.bad(lambda p: p.update(retained_q={}))
        self.bad(lambda p: p['retained_q'].update(alternate_evidence_authorized=True))

    def test_retained_q_inputs_cannot_be_replaced_by_new_self_hashes(self):
        for name in sr.RETAINED_Q_PINS:
            changed = (ROOT / name).read_bytes() + b'\n'
            with self.subTest(name=name):
                self.bad(lambda p, key=name, raw=changed:
                         p['retained_q'].__setitem__(key, sr.sha(raw)))

    def test_retained_q_reader_rejects_changed_actual_bytes(self):
        with tempfile.TemporaryDirectory(prefix='r17r-retained-') as temporary:
            root = Path(temporary)
            for name in sr.RETAINED_Q_PINS:
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / name).read_bytes())
            self.assertEqual(set(sr.read_retained(root)), set(sr.RETAINED_Q_PINS))
            path = root / sr.Q_PACKET
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaises(ValueError):
                sr.read_retained(root)

    def test_missing_retained_q_source_is_refused(self):
        with self.assertRaises(ValueError):
            sr.read_retained(Path(self.temp.name) / 'missing-retained-source')

    def test_protected_marker_cannot_be_selected_by_candidate(self):
        self.bad(lambda p: p['markers'].__setitem__(0, (p['markers'][0] + 1) % VOCAB))

    def test_original_targets_cannot_change_or_end_early(self):
        self.bad(lambda p: p['targets'][0].__setitem__(0, 0))
        self.bad(lambda p: p['targets'].__setitem__(0, [EOS]))

    def test_protected_goal_coverage_cannot_be_truncated(self):
        self.bad(lambda p: p['targets'].pop())
        self.bad(lambda p: p['markers'].pop())

    def test_existing_physical_workspace_is_refused(self):
        with self.assertRaises(ValueError):
            sr.prepare_sparse_refinement(ROOT, self.packages)

    def test_repository_internal_physical_workspace_is_refused(self):
        path = ROOT / 'r-must-not-be-created'
        with self.assertRaises(ValueError):
            sr.prepare_sparse_refinement(ROOT, path)
        self.assertFalse(path.exists())

    def test_generated_modules_keep_dependency_and_new_audits_separate(self):
        from rcp_rclm_runtime_v5.phase17 import sparse_refinement_lean as sl
        sources = sl.generated_sources(self.prepared, source_root=ROOT)
        self.assertEqual(list(sources), [sc.COMMON, *sl.LABELS])
        self.assertNotIn(b'#print axioms', sources[sc.COMMON])
        positive = sources[sl.LABELS[0]]
        self.assertEqual(positive.count(b'#print axioms'), len(sl.NAMES))
        for label, raw in sources.items():
            self.assertIsNone(re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b|\+\s*native\b', raw), label)
        for label in sl.LABELS[1:]:
            self.assertNotIn(b'#print axioms', sources[label], label)
        template = sl.template(ROOT)
        for tactic in (b'native_decide', b'decide +native', b'decide + native'):
            # Exercise the renderer's guard independently of the template pin;
            # these rejected sources are never submitted to a compiler.
            injected = template + b'\nexample : True := by ' + tactic + b'\n'
            with self.subTest(forbidden_tactic=tactic), patch.object(sl, 'template', return_value=injected):
                with self.assertRaisesRegex(ValueError, 'forbidden sparse proof token'):
                    sl._render_validated(self.prepared, source_root=ROOT)


class FormalGuardTests(unittest.TestCase):
    """Controlled parser fixtures are deliberately not actual proof execution."""

    def setUp(self):
        from rcp_rclm_runtime_v5.phase17 import sparse_refinement_lean as sl
        self.names, self.labels = sl.NAMES, sl.LABELS
        self.sources = {name: ('controlled-parser-fixture:' + name).encode()
                        for name in (sc.COMMON, *self.labels)}
        self.packet = 'a' * 64
        self.artifacts = {sc.COMMON + '.olean': '4' * 64}
        self.module_path = '/fixture/fresh/' + sc.COMMON + '.olean'

        def command(stdout='', code=0, label=None):
            result = {'returncode': code, 'stdout': stdout, 'stderr': '',
                      'stdout_sha256': sr.sha(stdout.encode()), 'stderr_sha256': sr.sha(b'')}
            if label is not None:
                result.update(label=label, source_sha256=sr.sha(self.sources[label]))
            return result

        self.audits = ''.join("'" + name + "' does not depend on any axioms\n" for name in self.names)
        dependency = command(label=sc.COMMON)
        dependency['output_artifacts_sha256'] = dict(self.artifacts)
        dependency['argv'] = ['/fixture/lake', '--keep-toolchain', '--no-cache', 'env',
                              '/fixture/lean', '--root=/fixture/fresh', '-o', self.module_path,
                              '/fixture/fresh/' + sc.COMMON + '.lean']
        resolution = command('/fixture/toolchain/Init.olean\n/fixture/toolchain/Init.olean\n' +
                             self.module_path + '\n')
        resolution.update(label='dependency_resolution', source_sha256=sr.sha(self.sources[self.labels[0]]),
                          argv=['/fixture/lake', '--keep-toolchain', '--no-cache', 'env',
                                '/fixture/lean', '--root=/fixture/fresh', '--deps',
                                '/fixture/fresh/' + self.labels[0] + '.lean'])
        commands = [command('Lean (version 4.31.0, controlled parser fixture)\n'), dependency, resolution,
                    command(self.audits, label=self.labels[0])]
        commands += [command('error: Tactic `decide` proved that the proposition\nFalse\nis false\n', 1, label)
                     for label in self.labels[1:]]
        self.result = {
            'schema': sc.SCHEMA, 'status': 'passed', 'packet_sha256': self.packet,
            'commands': commands, 'theorem_axioms': {name: [] for name in self.names},
            'negative_controls_rejected': list(self.labels[1:]), 'new_named_audits': len(self.names),
            'sparse_tensor_projection_checked': True, 'protected_sparse_decoder_checked': True,
            'claims': {name: False for name in sr.FALSE_CLAIMS},
            'source_sha256': {name: sr.sha(raw) for name, raw in self.sources.items()},
            'executable_sha256': {'fixture/lean': '1' * 64, 'fixture/lake': '2' * 64, 'fixture/git': '3' * 64},
            'dependency_module': {
                'name': sc.COMMON, 'source_sha256': sr.sha(self.sources[sc.COMMON]),
                'artifacts_sha256': dict(self.artifacts), 'compiled_in_this_run': True,
                'prior_success_report_used_as_proof': False, 'resolved_module_path': self.module_path},
            'trusted_import_cache_assumption': True, 'byte_capture_remains_external': True,
            'prompt_routing_remains_external': True, 'full_transformer_equivalence': False,
            'old_proof_campaigns_rerun': False}

    def bad(self, mutate):
        result = copy.deepcopy(self.result)
        mutate(result)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            sc.validate_result(result, self.sources, self.packet)

    @staticmethod
    def change_output(result, index, text):
        result['commands'][index]['stdout'] = text
        result['commands'][index]['stdout_sha256'] = sr.sha(text.encode())

    def test_controlled_log_fixture_satisfies_exact_contract(self):
        sc.validate_result(self.result, self.sources, self.packet)

    def test_preparation_or_partial_result_is_not_formal_success(self):
        self.bad(lambda r: r.update(status='not_requested'))
        self.bad(lambda r: r.update(sparse_tensor_projection_checked=False))
        self.bad(lambda r: r.update(protected_sparse_decoder_checked=False))

    def test_packet_and_executed_source_bindings_are_required(self):
        self.bad(lambda r: r.update(packet_sha256='0' * 64))
        self.bad(lambda r: r['source_sha256'].__setitem__(self.labels[0], '0' * 64))
        self.bad(lambda r: r['commands'][3].update(source_sha256='0' * 64))

    def test_missing_negative_control_cannot_be_counted(self):
        self.bad(lambda r: r['negative_controls_rejected'].pop())
        self.bad(lambda r: r['commands'].pop())

    def test_source_inventory_requires_common_dependency_then_exact_cases(self):
        for sources in (dict(reversed(tuple(self.sources.items()))),
                        {name: raw for name, raw in self.sources.items() if name != sc.COMMON},
                        {**self.sources, 'extra': b'extra'}):
            with self.subTest(names=list(sources)), self.assertRaises(ValueError):
                sc.validate_result(self.result, sources, self.packet)

    def test_old_success_report_cannot_replace_fresh_dependency_compilation(self):
        self.bad(lambda r: r['dependency_module'].update(compiled_in_this_run=False))
        self.bad(lambda r: r['dependency_module'].update(prior_success_report_used_as_proof=True))
        self.bad(lambda r: r['dependency_module'].update(source_sha256='0' * 64))

    def test_dependency_artifacts_must_exist_and_match_compile_record(self):
        self.bad(lambda r: r['dependency_module'].update(artifacts_sha256={}))
        self.bad(lambda r: r['commands'][1]['output_artifacts_sha256'].__setitem__(sc.COMMON + '.olean', '0' * 64))
        self.bad(lambda r: r['dependency_module']['artifacts_sha256'].__setitem__('../other.olean', '0' * 64))

    def test_shadowed_or_duplicate_compiled_dependency_is_rejected(self):
        def shadowed(result):
            stale = '/fixture/stale/' + sc.COMMON + '.olean'
            result['dependency_module']['resolved_module_path'] = stale
            self.change_output(result, 2, result['commands'][2]['stdout'].replace(self.module_path, stale))
        self.bad(shadowed)
        self.bad(lambda r: self.change_output(r, 2, r['commands'][2]['stdout'] + self.module_path + '\n'))
        self.bad(lambda r: self.change_output(r, 2, r['commands'][2]['stdout'] + '/fixture/Arbitrary.olean\n'))

    def test_dependency_resolution_is_required_and_bound_to_the_new_positive_source(self):
        self.bad(lambda r: r['commands'].pop(2))
        self.bad(lambda r: r['commands'][2].update(label='other'))
        self.bad(lambda r: r['commands'][2].update(source_sha256='0' * 64))
        self.bad(lambda r: r['commands'][2].update(returncode=1))
        self.bad(lambda r: r['commands'][2]['argv'].remove('--deps'))
        self.bad(lambda r: r['commands'][1]['argv'].__setitem__(-3, '--version'))

    def test_import_identity_preserves_posix_case_and_accepts_windows_path_equivalence(self):
        def wrong_posix_case(result):
            changed = '/fixture/FRESH/' + sc.COMMON + '.olean'
            result['dependency_module']['resolved_module_path'] = changed
            self.change_output(result, 2, result['commands'][2]['stdout'].replace(self.module_path, changed))
        self.bad(wrong_posix_case)
        windows = copy.deepcopy(self.result)
        compiled_path = 'C:\\Users\\Fixture\\Run\\' + sc.COMMON + '.olean'
        resolved_path = 'c:/users/fixture/run/' + sc.COMMON.lower() + '.olean'
        windows['commands'][1]['argv'][-2] = compiled_path
        windows['commands'][1]['argv'][-1] = 'C:\\Users\\Fixture\\Run\\' + sc.COMMON + '.lean'
        windows['commands'][2]['argv'][-1] = 'C:\\Users\\Fixture\\Run\\' + self.labels[0] + '.lean'
        windows['dependency_module']['resolved_module_path'] = resolved_path
        self.change_output(windows, 2, 'C:\\Tools\\Init.olean\nC:\\Tools\\Init.olean\n' + resolved_path + '\n')
        sc.validate_result(windows, self.sources, self.packet)
        different_drive = copy.deepcopy(windows)
        wrong = 'D:/users/fixture/run/' + sc.COMMON.lower() + '.olean'
        different_drive['dependency_module']['resolved_module_path'] = wrong
        self.change_output(different_drive, 2, different_drive['commands'][2]['stdout'].replace(resolved_path, wrong))
        with self.assertRaises(ValueError):
            sc.validate_result(different_drive, self.sources, self.packet)

    def test_dependency_compile_failure_or_extra_output_rejected(self):
        self.bad(lambda r: r['commands'][1].update(returncode=1))
        self.bad(lambda r: self.change_output(r, 1, self.audits))

    def test_positive_compiler_failure_cannot_pass(self):
        self.bad(lambda r: r['commands'][3].update(returncode=1))

    def test_success_timeout_or_kill_is_not_semantic_negative_rejection(self):
        for code in (0, -9, -999, 137, True):
            with self.subTest(code=code):
                self.bad(lambda r, value=code: r['commands'][4].update(returncode=value))

    def test_boolean_return_code_and_numeric_proof_flags_rejected(self):
        self.bad(lambda r: r['commands'][3].update(returncode=False))
        self.bad(lambda r: r.update(sparse_tensor_projection_checked=1))
        self.bad(lambda r: r.update(new_named_audits=True))

    def test_output_hashes_cannot_be_stale(self):
        self.bad(lambda r: r['commands'][3].update(stdout='different output'))
        self.bad(lambda r: r['commands'][4].update(stderr='unexpected stderr'))

    def test_unrelated_negative_error_cannot_receive_rejection_credit(self):
        self.bad(lambda r: self.change_output(r, 4, "error: unknown identifier 'missing'\n"))
        self.bad(lambda r: self.change_output(r, 4, r['commands'][4]['stdout'] + 'error: type mismatch\n'))

    def test_false_diagnostic_cannot_swallow_an_embedded_unrelated_error(self):
        output = 'error: Tactic `decide` proved that the proposition\nerror: type mismatch\nFalse\nis false\n'
        self.bad(lambda r: self.change_output(r, 4, output))

    def test_negative_audit_or_arbitrary_trailing_output_is_rejected(self):
        self.bad(lambda r: self.change_output(r, 4, r['commands'][4]['stdout'] + self.audits))
        self.bad(lambda r: self.change_output(r, 4, r['commands'][4]['stdout'] + 'accepted\n'))

    def test_pinned_lean_version_is_required(self):
        self.bad(lambda r: self.change_output(r, 0, 'Lean (version 4.30.0)\n'))

    def test_positive_sorry_and_unapproved_axioms_are_rejected(self):
        for axiom in ('sorryAx', 'arbitraryAcceptanceAxiom'):
            output = ''.join("'" + name + "' depends on axioms: [" + axiom + "]\n" for name in self.names)
            with self.subTest(axiom=axiom), self.assertRaises(ValueError):
                sc.parse_audits(output)

    def test_positive_audits_require_exact_sequence_and_no_extra_output(self):
        lines = self.audits.splitlines(keepends=True)
        for output in (''.join(lines[1:]), ''.join(reversed(lines)),
                       self.audits + 'unexpected output\n', self.audits + lines[0]):
            with self.subTest(length=len(output)), self.assertRaises(ValueError):
                sc.parse_audits(output)

    def test_reported_axioms_must_match_actual_positive_output(self):
        self.bad(lambda r: r['theorem_axioms'].__setitem__(self.names[0], ['Classical.choice']))

    def test_report_cannot_escalate_full_physical_or_promotion_authority(self):
        self.bad(lambda r: r['claims'].__setitem__('physical_projection_formally_verified', True))
        self.bad(lambda r: r['claims'].__setitem__('promotion_authorized', True))
        self.bad(lambda r: r['claims'].__setitem__('physical_execution_attested', 0))

    def test_external_capture_and_routing_boundaries_cannot_be_removed(self):
        self.bad(lambda r: r.pop('byte_capture_remains_external'))
        self.bad(lambda r: r.update(prompt_routing_remains_external=False))
        self.bad(lambda r: r.update(full_transformer_equivalence=True))

    def test_pass_record_with_unresolved_failure_is_rejected(self):
        self.bad(lambda r: r.update(failure={'reason': 'unresolved'}))


class TemplateContractTests(unittest.TestCase):
    def test_exact_refinement_theorem_and_control_inventory(self):
        from rcp_rclm_runtime_v5.phase17 import sparse_refinement_lean as sl
        self.assertEqual(len(sl.NAMES), 15)
        self.assertTrue(all(name.startswith('Phase17Sparse.') for name in sl.NAMES))
        self.assertEqual(sl.LABELS, ('SparseRefinement', 'ChangedTensorByte', 'TransposedTensor',
                                   'AlteredProbability', 'WrongMarker', 'MissingEOS',
                                   'InvalidByteRange', 'WrongSignedBoundary', 'WrongGreedyTie'))

    def test_new_template_matches_its_source_pin_and_has_no_placeholders(self):
        from rcp_rclm_runtime_v5.phase17 import sparse_refinement_lean as sl
        raw = sl.template(ROOT)
        self.assertEqual(sr.sha(raw), sl.BRIDGE_SHA256)
        self.assertIsNone(re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b|\+\s*native\b', raw))


class GatePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('r_gate_test', ROOT / 'scripts/run_phase17_sparse_refinement_gate.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_lexical_parent_path_cannot_enter_source_checkout(self):
        name = 'r-path-must-not-be-created'
        path = ROOT.parent / 'nonexistent-r-parent' / '..' / ROOT.name / name
        with self.assertRaises(ValueError):
            self.module.main(['--output', str(path), '--test-fixture'])
        self.assertFalse((ROOT / name).exists())

    def test_execution_inventory_binds_r_sources_and_excludes_mutable_status(self):
        paths = self.module.source_paths()
        for name in ('sparse_refinement.py', 'sparse_refinement_check.py', 'sparse_refinement_lean.py'):
            self.assertIn('python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/' + name, paths)
        self.assertNotIn('SHA256SUMS.txt', paths)
        self.assertNotIn('docs/executable_core_v5/PHASE_17_LOCAL_VALIDATION.json', paths)

