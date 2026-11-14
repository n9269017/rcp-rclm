"""Selected objective-policy arithmetic, complete context, and tamper boundaries.

Runtime/hashlib comparisons and controlled malformed inputs are not Lean proof
evidence. One integration check freshly reconstructs the existing fixture with
no workers, live challenges, or historical proof campaigns.
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

from rcp_rclm_runtime_v5.phase17 import objective_context as p

ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _x():
    raw = (ROOT / p.X_PACKET).read_bytes()
    if p.sha(raw) != p.X_PACKET_SHA:
        raise AssertionError('retained X identity changed')
    return p.load_json_strict(raw)


@lru_cache(maxsize=1)
def _inputs():
    return p.inputs_from_transcript(_x(), (ROOT / p.FIXTURE_PATH).read_bytes())


@lru_cache(maxsize=1)
def _derived():
    return p.derive_objective(_x(), _inputs())


@lru_cache(maxsize=1)
def _expected_records():
    return [{key: value for key, value in record.items() if key != 'blocks'}
            for record in _derived()['hash_records']]


@lru_cache(maxsize=1)
def _template():
    return p.packet_from_inputs(_x(), _inputs())


@lru_cache(maxsize=1)
def _prepared():
    return p.PreparedObjectiveContext(p.canonical(_template()))


def _projection():
    return copy.deepcopy(p.imported_inputs(_x())[2]['before']['nonzero_words'])


def _edit_input(inputs, name, edit):
    value = p._decode(inputs[name])
    edit(value)
    inputs[name] = p.preimages.encode_canonical(value).hex()


class ObjectiveArithmeticTests(unittest.TestCase):
    def test_eight_actual_projection_scores(self):
        self.assertEqual([row['projection_score'] for row in _derived()['objective_rows']],
                         [5, 11, -33, -21, 4, 4, 22, -6])

    def test_complete_672_term_inventory(self):
        rows = _derived()['objective_rows']
        self.assertEqual(len(rows), 8)
        self.assertEqual([len(row['terms']) for row in rows], [84] * 8)
        self.assertTrue(all(sum(row['terms']) == row['projection_score'] for row in rows))

    def test_complete_actual_rank_order_and_winner(self):
        self.assertEqual(_derived()['ranked_indices'], [6, 1, 0, 5, 4, 7, 3, 2])
        self.assertEqual(_derived()['objective_rows'][6]['score'], 19501)

    def test_signed_weight_changes_actual_score(self):
        projection = _projection()
        digest = _derived()['objective_rows'][0]['feature_digest']
        terms = p.score_terms(projection, 0, 1, digest)
        projection[0][1] *= -1
        changed = p.score_terms(projection, 0, 1, digest)
        self.assertEqual(changed[0], -terms[0])
        self.assertNotEqual(sum(changed), sum(terms))

    def test_all_digest_digits_participate_in_indexed_terms(self):
        # (54 * i + 11 * i) mod 64 visits every digest position.
        projection = [[54 * i, 1] for i in range(84)]
        baseline = p.score_terms(projection, 0, 0, '0' * 64)
        for digit in range(64):
            changed = '0' * digit + '1' + '0' * (63 - digit)
            self.assertNotEqual(p.score_terms(projection, 0, 0, changed), baseline)

    def test_numeric_reference_does_not_call_production_objectives(self):
        from rcp_rclm_runtime_v5.phase17 import objectives
        with patch.object(objectives, '_rank', side_effect=AssertionError('production rank called')), \
             patch.object(objectives, 'select_bootstrap_objective', side_effect=AssertionError('selector called')):
            result = p.derive_objective(_x(), _inputs(), with_traces=False)
        self.assertEqual(result['ranked_indices'], [6, 1, 0, 5, 4, 7, 3, 2])

    def test_score_precedes_tie_digest(self):
        rows = copy.deepcopy(_derived()['objective_rows'])
        for row in rows:
            row['score'] = 0
            row['tie_digest'] = 'f' * 64
        rows[2]['score'], rows[2]['tie_digest'] = 1, '0' * 64
        self.assertEqual(p.rank_indices(rows)[0], 2)

    def test_full_tie_digest_precedes_family_name(self):
        rows = copy.deepcopy(_derived()['objective_rows'])
        for row in rows:
            row['score'], row['tie_digest'] = 0, '0' * 64
        rows[0]['tie_digest'] = '0' * 63 + '1'
        self.assertEqual(p.rank_indices(rows)[0], 0)

    def test_final_tie_uses_family_name_not_index(self):
        rows = copy.deepcopy(_derived()['objective_rows'])
        for row in rows:
            row['score'], row['tie_digest'] = 0, '0' * 64
        expected = sorted(range(8), key=lambda i: p.FAMILIES[i], reverse=True)
        self.assertEqual(p.rank_indices(rows), expected)

    def test_rank_rejects_missing_family(self):
        with self.assertRaises(ValueError):
            p.rank_indices(_derived()['objective_rows'][:-1])

    def test_rank_rejects_reordered_rows(self):
        with self.assertRaises(ValueError):
            p.rank_indices(list(reversed(_derived()['objective_rows'])))

    def test_rank_rejects_boolean_score(self):
        rows = copy.deepcopy(_derived()['objective_rows']); rows[0]['score'] = True
        with self.assertRaises(ValueError): p.rank_indices(rows)

    def test_rank_rejects_unbounded_score(self):
        rows = copy.deepcopy(_derived()['objective_rows']); rows[0]['score'] = 1 << 63
        with self.assertRaises(ValueError): p.rank_indices(rows)

    def test_rank_rejects_boolean_family_index(self):
        rows = copy.deepcopy(_derived()['objective_rows']); rows[0]['family_index'] = False
        with self.assertRaises(ValueError): p.rank_indices(rows)

    def test_complete_hash_inputs_match_library(self):
        for record in _derived()['hash_records']:
            raw = bytes.fromhex(record['preimage_hex'])
            self.assertEqual(record['digest'], hashlib.sha256(raw).hexdigest())

    def test_complete_domain_prefix_includes_single_nul(self):
        for record in _derived()['hash_records']:
            raw = bytes.fromhex(record['preimage_hex'])
            self.assertEqual(raw, b'RCPRCLM-CANONICAL-JSON-V2\0' + bytes.fromhex(record['json_hex']))

    def test_state_and_challenge_bind_actual_imported_context(self):
        values = {r['category']: r['digest'] for r in _derived()['hash_records'] if r['index'] == 0}
        self.assertEqual(values['historical_state'], _x()['bindings']['historical_state_hash'])
        self.assertEqual(values['objective_decision'], _x()['bindings']['objective_hash'])
        self.assertEqual(values['challenge_commitment'], _x()['bindings']['challenge_commitment_hash'])

    def test_public_nonce_is_literal_retained_fixture(self):
        w, _, _ = p.imported_inputs(_x())
        self.assertEqual(w['producer']['current_view']['public_nonce_hash'], '8' * 64)
        self.assertTrue(p.SCOPE['secret_generation_and_freshness_remain_external'])

    def test_logical_and_physical_package_identities_remain_distinct(self):
        w, _, _ = p.imported_inputs(_x())
        self.assertNotEqual(w['producer']['current_view']['active_package_hash'],
                            _x()['bindings']['predecessor_physical_hash'])


class InputAndPacketTests(unittest.TestCase):
    def test_exact_selected_inputs_pin(self):
        self.assertEqual(p.sha(p.canonical(_inputs())), p.INPUTS_SHA256)

    def test_retained_transcript_bytes_are_required(self):
        raw = bytearray((ROOT / p.FIXTURE_PATH).read_bytes()); raw[-1] ^= 1
        with self.assertRaises(ValueError): p.inputs_from_transcript(_x(), bytes(raw))

    def test_transcript_mutable_container_rejected(self):
        with self.assertRaises(ValueError):
            p.inputs_from_transcript(_x(), bytearray((ROOT / p.FIXTURE_PATH).read_bytes()))

    def test_captured_json_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError): p._decode(b'{"a":1,"a":2}'.hex())

    def test_captured_json_noncanonical_whitespace_rejected(self):
        with self.assertRaises(ValueError): p._decode(b'{ "a":1}'.hex())

    def test_captured_json_floating_number_rejected(self):
        with self.assertRaises(ValueError): p._decode(b'{"a":1.5}'.hex())

    def test_captured_json_unsupported_escape_rejected(self):
        with self.assertRaises(ValueError): p._decode(b'{"a":"\\n"}'.hex())

    def test_captured_json_nonobject_rejected(self):
        with self.assertRaises(ValueError): p._decode(b'[]'.hex())

    def test_captured_json_uppercase_hex_rejected(self):
        with self.assertRaises(ValueError): p._decode(b'{"a":1}'.hex().upper())

    def test_packet_rejects_mutable_bytes(self):
        with self.assertRaises(ValueError): p.PreparedObjectiveContext(bytearray(b'{}'))

    def test_packet_rejects_empty_bytes(self):
        with self.assertRaises(ValueError): p.PreparedObjectiveContext(b'')

    def test_packet_rejects_oversized_bytes(self):
        with patch.object(p, 'MAX_BYTES', 2), self.assertRaises(ValueError):
            p.PreparedObjectiveContext(b'{}\n')

    def test_prepared_is_immutable(self):
        with self.assertRaises(FrozenInstanceError): _prepared().packet_bytes = b'{}'

    def test_prepared_packet_view_is_detached(self):
        view = _prepared().packet; view['objective_rows'][0]['score'] = 0
        self.assertNotEqual(_prepared().packet['objective_rows'][0]['score'], 0)

    def test_actual_x_dependency_is_preserved(self):
        self.assertEqual(_prepared().producer_sha256().packet_bytes, (ROOT / p.X_PACKET).read_bytes())

    def test_inventory_counts_and_selected_winner(self):
        result = p.summary(_prepared())
        self.assertEqual((result['complete_preimages'], result['complete_preimage_bytes'],
                          result['compression_blocks'], result['distinct_compression_transitions']),
                         (20, 27051, 440, 304))
        self.assertEqual(result['selected_family'], 'tool_policy')

    def test_hash_records_complete_and_ordered(self):
        records = _derived()['hash_records']
        self.assertEqual([(r['category'], r['index']) for r in records],
                         [(category, index) for category, count in p.GROUP_COUNTS.items() for index in range(count)])
        p.validate_hash_records(records, _expected_records())

    def test_wrong_external_packet_anchor_rejected(self):
        with self.assertRaises(ValueError):
            p.verify_packet_bytes(_prepared().packet_bytes, _prepared(), expected_sha256='0' * 64)

    def test_modified_packet_under_new_external_digest_rejected(self):
        raw = _prepared().packet_bytes + b' '
        with self.assertRaises(ValueError):
            p.verify_packet_bytes(raw, _prepared(), expected_sha256=p.sha(raw))

    def test_public_grammar_rehash_attack_rejected(self):
        packet = dict(_template()); packet['inputs'] = copy.deepcopy(_inputs())
        _edit_input(packet['inputs'], 'public_challenge_hex', lambda d: d.__setitem__('grammar_hash', '0' * 64))
        with self.assertRaisesRegex(ValueError, 'captured inputs'):
            p.PreparedObjectiveContext(p.canonical(packet))

    def test_secret_entropy_rehash_attack_rejected(self):
        packet = dict(_template()); packet['inputs'] = copy.deepcopy(_inputs())
        _edit_input(packet['inputs'], 'secret_hex', lambda d: d.__setitem__('entropy_hex', '0' * 64))
        with self.assertRaisesRegex(ValueError, 'captured inputs'):
            p.PreparedObjectiveContext(p.canonical(packet))

    def test_prior_source_packet_rehash_cannot_replace_x(self):
        packet = dict(_template()); packet['producer_sha256_packet'] = copy.deepcopy(_x())
        packet['producer_sha256_packet']['bindings']['objective_hash'] = '0' * 64
        packet['producer_sha256_packet_sha256'] = p.sha(p.canonical(packet['producer_sha256_packet']))
        with self.assertRaisesRegex(ValueError, 'imported X'):
            p.validate_packet(packet)


class RetainedAndIntegrationTests(unittest.TestCase):
    def test_complete_retained_x_and_fixture_inventory(self):
        retained = p.read_retained(ROOT)
        self.assertEqual(set(retained), set(p.RETAINED_X_PINS) | {p.FIXTURE_PATH})
        self.assertEqual(retained[p.X_PACKET], (ROOT / p.X_PACKET).read_bytes())

    def test_missing_retained_input_rejected(self):
        with tempfile.TemporaryDirectory() as td, self.assertRaises(ValueError):
            p.read_retained(Path(td))

    def test_changed_retained_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'input').write_bytes(b'bad')
            with patch.object(p, 'RETAINED_X_PINS', {'input': p.sha(b'good')}), \
                 self.assertRaises(ValueError): p.read_retained(root)

    def test_linked_retained_file_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); target = root / 'target'; target.write_bytes(b'good')
            try: (root / 'input').symlink_to(target)
            except (OSError, NotImplementedError):
                # Windows may disallow symlink creation; mock just the link
                # observation so the same guard is still exercised, not skipped.
                with patch.object(p, 'RETAINED_X_PINS', {'input': p.sha(b'good')}), \
                     patch.object(Path, 'is_symlink', return_value=True), self.assertRaises(ValueError):
                    p.read_retained(root)
                return
            with patch.object(p, 'RETAINED_X_PINS', {'input': p.sha(b'good')}), self.assertRaises(ValueError):
                p.read_retained(root)

    def test_actual_production_objective_matches_independent_policy(self):
        from rcp_rclm_runtime_v5.phase17.campaign_transaction import load_predecessor
        from rcp_rclm_runtime_v5.phase17.objectives import select_bootstrap_objective, freeze_bootstrap_objective
        parent = load_predecessor(ROOT)
        actual = select_bootstrap_objective(parent, turn_index=0, public_nonce_hash='8' * 64)
        freeze = freeze_bootstrap_objective(actual, parent, turn_index=0, public_nonce_hash='8' * 64)
        self.assertEqual(actual.payload.hex(), _inputs()['objective_hex'])
        self.assertEqual(p.canonical(freeze).hex(), _inputs()['freeze_hex'])

    def test_fresh_selected_fixture_reconstruction(self):
        with tempfile.TemporaryDirectory() as td:
            prepared = p.prepare_objective_context(ROOT, Path(td) / 'packages')
            self.assertEqual(prepared.packet_bytes, p.canonical(_template()))
            self.assertEqual(p.summary(prepared)['complete_preimages'], 20)


def _numeric_negative(name, change, family=0, generation=1, text='a' * 64):
    def test(self):
        projection = _projection(); change(projection)
        with self.assertRaises(ValueError): p.score_terms(projection, family, generation, text)
    setattr(ObjectiveArithmeticTests, 'test_' + name, test)


for _name, _change, _family, _generation, _text in (
    ('projection_omitted_word_rejected', lambda a: a.pop(), 0, 1, 'a' * 64),
    ('projection_extra_word_rejected', lambda a: a.append([32767, 1]), 0, 1, 'a' * 64),
    ('projection_duplicate_index_rejected', lambda a: a[1].__setitem__(0, a[0][0]), 0, 1, 'a' * 64),
    ('projection_zero_word_rejected', lambda a: a[0].__setitem__(1, 0), 0, 1, 'a' * 64),
    ('projection_boolean_word_rejected', lambda a: a[0].__setitem__(1, True), 0, 1, 'a' * 64),
    ('projection_out_of_range_word_rejected', lambda a: a[0].__setitem__(1, 32768), 0, 1, 'a' * 64),
    ('projection_out_of_range_index_rejected', lambda a: a[0].__setitem__(0, -1), 0, 1, 'a' * 64),
    ('projection_boolean_index_rejected', lambda a: a[0].__setitem__(0, False), 0, 1, 'a' * 64),
    ('negative_family_rejected', lambda a: None, -1, 1, 'a' * 64),
    ('ninth_family_rejected', lambda a: None, 8, 1, 'a' * 64),
    ('boolean_family_rejected', lambda a: None, True, 1, 'a' * 64),
    ('negative_generation_rejected', lambda a: None, 0, -1, 'a' * 64),
    ('boolean_generation_rejected', lambda a: None, 0, True, 'a' * 64),
    ('uppercase_feature_digest_rejected', lambda a: None, 0, 1, 'A' * 64),
    ('short_feature_digest_rejected', lambda a: None, 0, 1, 'a' * 63),
): _numeric_negative(_name, _change, _family, _generation, _text)


def _input_negative(name, field, change):
    def test(self):
        inputs = copy.deepcopy(_inputs()); _edit_input(inputs, field, change)
        with self.assertRaises(ValueError): p.derive_objective(_x(), inputs, with_traces=False)
    setattr(InputAndPacketTests, 'test_' + name, test)


for _name, _field, _change in (
    ('changed_historical_frontier_rejected', 'historical_state_hex', lambda d: d['capability_frontier'].pop()),
    ('changed_historical_generation_rejected', 'historical_state_hex', lambda d: d['component_generations'].__setitem__('tool_policy', 2)),
    ('changed_objective_winner_rejected', 'objective_hex', lambda d: d.__setitem__('objective_family', 'memory_policy')),
    ('changed_objective_score_rejected', 'objective_hex', lambda d: d['ranked_objectives'][0].__setitem__('score', 19502)),
    ('changed_objective_order_rejected', 'objective_hex', lambda d: d['ranked_objectives'].reverse()),
    ('omitted_objective_rank_rejected', 'objective_hex', lambda d: d['ranked_objectives'].pop()),
    ('changed_bootstrap_receipt_rejected', 'objective_hex', lambda d: d.__setitem__('bootstrap_report_hash', '0' * 64)),
    ('objective_promotion_escalation_rejected', 'objective_hex', lambda d: d.__setitem__('promotion_authorized', True)),
    ('changed_freeze_objective_link_rejected', 'freeze_hex', lambda d: d.__setitem__('objective_decision_hash', '0' * 64)),
    ('changed_freeze_context_rejected', 'freeze_hex', lambda d: d.__setitem__('public_nonce_hash', '0' * 64)),
    ('freeze_challenge_bound_escalation_rejected', 'freeze_hex', lambda d: d.__setitem__('challenge_bound', True)),
    ('changed_public_grammar_rejected', 'public_challenge_hex', lambda d: d.__setitem__('grammar_hash', '0' * 64)),
    ('changed_public_credits_rejected', 'public_challenge_hex', lambda d: d.__setitem__('candidate_credits', 31)),
    ('changed_public_turn_rejected', 'public_challenge_hex', lambda d: d.__setitem__('turn_index', 1)),
    ('changed_public_commitment_rejected', 'public_challenge_hex', lambda d: d.__setitem__('challenge_commitment_hash', '0' * 64)),
    ('changed_secret_entropy_rejected', 'secret_hex', lambda d: d.__setitem__('entropy_hex', '0' * 64)),
    ('changed_secret_probe_rejected', 'secret_hex', lambda d: d['probes'][0].__setitem__(0, 23)),
    ('missing_secret_probe_rejected', 'secret_hex', lambda d: d['probes'].pop()),
    ('boolean_secret_parameter_rejected', 'secret_hex', lambda d: d.__setitem__('target_a', True)),
    ('out_of_range_secret_variant_rejected', 'secret_hex', lambda d: d.__setitem__('target_variant', 4)),
    ('unknown_secret_field_rejected', 'secret_hex', lambda d: d.__setitem__('accepted', True)),
): _input_negative(_name, _field, _change)


def _packet_negative(name, field, value):
    def test(self):
        packet = dict(_template()); packet[field] = value
        with self.assertRaises(ValueError): p.validate_packet(packet)
    setattr(InputAndPacketTests, 'test_' + name, test)


for _name, _field, _value in (
    ('wrong_schema_rejected', 'schema', 'wrong'),
    ('wrong_policy_rejected', 'policy', 'wrong'),
    ('wrong_base_rejected', 'base_commit', '0' * 40),
    ('missing_claims_rejected', 'claims', {}),
    ('numeric_false_claims_rejected', 'claims', {key: 0 for key in p.FALSE_CLAIMS}),
    ('broader_claim_escalation_rejected', 'claims', {key: key == 'root_transition_verified' for key in p.FALSE_CLAIMS}),
    ('missing_scope_rejected', 'scope', {}),
    ('missing_profile_rejected', 'profile', {}),
    ('missing_retained_pins_rejected', 'retained_x', {}),
    ('different_binding_rejected', 'bindings', {}),
    ('missing_arithmetic_rows_rejected', 'objective_rows', []),
    ('altered_rank_permutation_rejected', 'ranked_indices', [0, 1, 2, 3, 4, 5, 6, 7]),
): _packet_negative(_name, _field, _value)


def _record_negative(name, change):
    def test(self):
        records = copy.deepcopy(_derived()['hash_records']); change(records)
        with self.assertRaises(ValueError): p.validate_hash_records(records, _expected_records())
    setattr(InputAndPacketTests, 'test_' + name, test)


for _name, _change in (
    ('omitted_hash_record_rejected', lambda r: r.pop()),
    ('reordered_hash_records_rejected', lambda r: r.reverse()),
    ('boolean_record_index_rejected', lambda r: r[0].__setitem__('index', False)),
    ('changed_hash_category_rejected', lambda r: r[0].__setitem__('category', 'objective_feature')),
    ('removed_domain_nul_rejected', lambda r: r[0].__setitem__('preimage_hex', r[0]['preimage_hex'][:50] + r[0]['preimage_hex'][52:])),
    ('changed_json_image_rejected', lambda r: r[0].__setitem__('json_hex', '7b7d')),
    ('wrong_hash_digest_rejected', lambda r: r[0].__setitem__('digest', '0' * 64)),
    ('omitted_hash_block_rejected', lambda r: r[0]['blocks'].pop()),
    ('wrong_hash_schedule_rejected', lambda r: r[0]['blocks'][0]['schedule'].__setitem__(16, 0)),
    ('wrong_hash_round_rejected', lambda r: r[0]['blocks'][0]['round_states'][0].__setitem__(0, 0)),
    ('wrong_hash_input_state_rejected', lambda r: r[0]['blocks'][0]['input_state'].__setitem__(0, 0)),
    ('wrong_hash_feedforward_rejected', lambda r: r[0]['blocks'][0]['output_state'].__setitem__(0, 0)),
): _record_negative(_name, _change)


if __name__ == '__main__':
    unittest.main(verbosity=2)
