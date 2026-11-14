"""Fixed semantic palette, authenticated extraction and novelty controls.

One fresh reconstruction supplies the physical pair.  These tests exercise the
Python trust boundary; the separate real Lean gate proves the universal claims.
No new challenge, follow-up selection or accepted candidate is produced.
"""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import task_interpretation as ae
from rcp_rclm_runtime_v5.phase17.finite_kernel import FALSE_CLAIMS, PreparedFiniteKernel
from rcp_rclm_runtime_v5.phase17.materialized import snapshot


ROOT = Path(__file__).resolve().parents[3]


class TaskInterpretationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='phase17ae-physical-')
        cls.packages = Path(cls.temp.name) / 'packages'
        forbidden = AssertionError('AE must not choose a follow-up context')
        with patch('rcp_rclm_runtime_v5.phase17.successor_context.prepare_successor_context',
                   side_effect=forbidden), patch('rcp_rclm_runtime_v5.phase17.successor_context._context',
                                                side_effect=forbidden):
            cls.prepared = ae.prepare_task_interpretation(ROOT, cls.packages)
        cls.packet = cls.prepared.packet
        cls.raw = cls.prepared.packet_bytes
        cls.initial_snapshots = (snapshot(cls.packages / 'before'), snapshot(cls.packages / 'after'))
        cls.meanings = cls.prepared.finite().joint().packet['task_meanings']
        cls.adapter = next(program for program in cls.meanings['before']['programs']
                           if program['family'] == 'adapter_policy')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def rejected(self, mutation):
        value = copy.deepcopy(self.packet)
        mutation(value)
        with self.assertRaises((ValueError, TypeError, KeyError)):
            ae.PreparedTaskInterpretation(ae.canonical(value))

    def decision(self, task_index, **overrides):
        bound = self.prepared.finite().packet['bindings']
        arguments = {'task_index': task_index,
                     'expected_predecessor_hash': bound['predecessor_physical_hash'],
                     'expected_candidate_hash': bound['candidate_physical_hash']}
        arguments.update(overrides)
        return ae.novelty_for(self.prepared, **arguments)

    @staticmethod
    def rehash_catalog(packet):
        catalog = packet['catalog']
        catalog['descriptor_sha256'] = ae.digest(catalog['descriptor'])
        catalog['tail_sha256'] = ae.digest(catalog['tail'])
        catalog['catalog_sha256'] = ae.digest({k: v for k, v in catalog.items() if k != 'catalog_sha256'})

    def test_fixed_catalog_is_independent_of_selected_state(self):
        descriptor = ae.catalog_descriptor()
        self.assertEqual(descriptor, self.packet['catalog']['descriptor'])
        self.assertEqual(ae.fixed_palette(), self.packet['catalog']['tail'])
        self.assertEqual(descriptor['variants'], [0, 1, 2, 3])
        self.assertEqual(descriptor['offset_min'], -32)
        self.assertEqual(descriptor['offset_max'], 32)
        self.assertNotIn('nonce', descriptor)
        self.assertNotIn('candidate', descriptor)
        self.assertNotIn('objective', descriptor)

    def test_complete_original_catalog_bytes_and_names_are_preserved(self):
        catalog = self.packet['catalog']
        self.assertEqual(catalog['legacy_tasks_sha256'], ae.digest(self.meanings['tasks']))
        self.assertEqual(catalog['legacy_task_ids'], [t['task_id'] for t in self.meanings['tasks']])
        self.assertEqual(sum(t['kind'] == 'proof' for t in self.meanings['tasks']), 13)
        self.assertEqual(sum(t['kind'] == 'vectors' for t in self.meanings['tasks']), 9)
        self.assertEqual(self.packet['finite_packet'], self.prepared.finite().packet)
        self.assertIsInstance(self.prepared.finite(), PreparedFiniteKernel)

    def test_indices_and_names_cover_exact_fixed_tail(self):
        rows = self.packet['catalog']['tail']
        self.assertEqual([r['index'] for r in rows], list(range(22, 282)))
        self.assertEqual(len({r['task_id'] for r in rows}), 260)
        self.assertTrue(set(r['task_id'] for r in rows).isdisjoint(self.packet['catalog']['legacy_task_ids']))
        self.assertEqual(rows[0]['task_id'], 'phase17ae.adapter.affine.0.0')
        self.assertEqual(rows[-1]['task_id'], 'phase17ae.adapter.affine.3.64')

    def test_all_affine_behaviours_are_semantically_separated(self):
        rows = self.packet['catalog']['tail']
        signatures = {(r['slope'], r['offset']) for r in rows}
        self.assertEqual(signatures, {(s, o) for s in range(1, 5) for o in range(-32, 33)})
        observations = {tuple(tuple(v) for v in r['probe_targets']) for r in rows}
        self.assertEqual(len(observations), 260)
        # Equal zero outputs fix offset; equal unit outputs then fix slope.
        for row in rows:
            zero, unit = row['probe_targets']
            self.assertEqual((unit[0] - zero[0], zero[0]), (row['slope'], row['offset']))

    def test_reference_programs_are_bounded_mathematical_projections(self):
        for row in self.packet['catalog']['tail']:
            program = row['reference_program']
            self.assertEqual(set(program), {'family', 'variant', 'a', 'b'})
            self.assertEqual(program['family'], 0)
            self.assertTrue(0 <= program['variant'] < 4)
            self.assertTrue(-16 <= program['a'] <= 16 and -16 <= program['b'] <= 16)
            self.assertEqual(program['a'] - program['b'], row['offset'])
            self.assertEqual(program['variant'] + 1, row['slope'])
        self.assertEqual(self.packet['catalog']['tail'][0]['reference_program']['b'], 16)
        self.assertEqual(self.packet['catalog']['tail'][-1]['reference_program']['b'], -16)

    def test_only_manifest_registry_and_actual_program_images_are_captured(self):
        captured = self.packet['captured_inputs']
        self.assertEqual(sum(map(len, captured.values())), 21)
        for side, expected in (('before', 10), ('after', 11)):
            self.assertEqual(len(captured[side]), expected)
            self.assertIn(ae.MANIFEST, captured[side])
            self.assertIn('registry/manifest.json', captured[side])
            self.assertNotIn('historical_state.json', captured[side])
            for name in captured[side]:
                self.assertTrue(name in (ae.MANIFEST, 'registry/manifest.json') or
                                name.startswith('registry/programs/'))

    def test_selected_pair_recomputes_all_260_meanings(self):
        for side in ('before', 'after'):
            obs = self.packet['observations'][side]
            self.assertEqual(len(obs['affine_checks']), 260)
            self.assertEqual(obs['affine_solved_indices'], [259])
            self.assertEqual(obs['affine_unsolved_indices'], [i for i in range(22, 282) if i != 259])
            self.assertEqual(len(obs['affine_unsolved_indices']), 259)
            solved = obs['affine_checks'][259 - 22]
            self.assertEqual(solved['satisfying_program_hashes'], [ae.digest(self.adapter)])

    def test_selected_adapter_coefficients_are_measured(self):
        self.assertEqual((self.adapter['variant'], self.adapter['parameter_a'], self.adapter['parameter_b']),
                         (3, 11, 1))
        obs = ae._program_observation(self.adapter)
        self.assertEqual(obs['affine_signature'], [4, 10])
        self.assertEqual(obs['probe_outputs'], [[10, 10, 10, 10], [14, 10, 10, 10]])
        self.assertTrue(ae._affine_matches(obs, ae.affine_task(3, 42)))

    def test_original_first_step_still_has_exact_declared_frontier(self):
        before, after = (self.packet['observations'][side] for side in ('before', 'after'))
        self.assertEqual(before['checked_declared_indices'], list(range(21)))
        self.assertEqual(after['checked_declared_indices'], list(range(22)))
        self.assertEqual(before['legacy_checks'], [True] * 21 + [False])
        self.assertEqual(after['legacy_checks'], [True] * 22)
        self.assertEqual(before['checked_declared_ids'], self.packet['catalog']['legacy_task_ids'][:21])
        self.assertEqual(after['checked_declared_ids'], self.packet['catalog']['legacy_task_ids'])

    def test_selected_original_first_task_passes_semantic_guard(self):
        result = self.decision(21)
        self.assertFalse(result['predecessor_satisfied'])
        self.assertTrue(result['candidate_satisfied'])
        self.assertFalse(result['predecessor_declared'])
        self.assertTrue(result['candidate_declared'])
        self.assertTrue(result['predecessor_semantic_failure'])
        self.assertTrue(result['strict_semantic_gain'])
        self.assertEqual(result, self.packet['semantic_guard']['selected_original_first_task'])

    def test_already_solvable_undeclared_meaning_fails_semantic_guard(self):
        result = self.decision(259)
        self.assertTrue(result['predecessor_satisfied'])
        self.assertTrue(result['candidate_satisfied'])
        self.assertFalse(result['predecessor_declared'])
        self.assertFalse(result['candidate_declared'])
        self.assertFalse(result['predecessor_semantic_failure'])
        self.assertFalse(result['strict_semantic_gain'])

    def test_relabelling_as_declared_does_not_create_semantic_failure(self):
        observations = copy.deepcopy(self.packet['observations'])
        observations['after']['declared_indices'].append(259)
        result = ae._novelty(self.packet['catalog'], observations, 259)
        self.assertTrue(result['candidate_declared'])
        self.assertFalse(result['predecessor_semantic_failure'])
        self.assertFalse(result['strict_semantic_gain'])

    def test_unsolved_target_is_not_a_selected_success(self):
        result = self.decision(22)
        self.assertTrue(result['predecessor_semantic_failure'])
        self.assertFalse(result['candidate_satisfied'])
        self.assertFalse(result['strict_semantic_gain'])
        self.assertEqual(self.packet['semantic_guard']['new_affine_strict_gains_in_selected_pair'], [])

    def test_different_program_metadata_cannot_manufacture_new_semantics(self):
        alternative = dict(self.adapter)
        alternative['generation'] += 1
        alternative['public_nonce_hash'] = '1' * 64
        original, changed = ae._program_observation(self.adapter), ae._program_observation(alternative)
        self.assertNotEqual(original['program_hash'], changed['program_hash'])
        self.assertEqual(original['probe_outputs'], changed['probe_outputs'])
        self.assertTrue(ae._affine_matches(original, ae.affine_task(3, 42)))
        self.assertTrue(ae._affine_matches(changed, ae.affine_task(3, 42)))
        self.assertFalse(self.decision(259)['predecessor_semantic_failure'])

    def test_different_bounded_parameters_with_same_difference_have_same_meaning(self):
        alternative = dict(self.adapter, parameter_a=12, parameter_b=2)
        original, changed = ae._program_observation(self.adapter), ae._program_observation(alternative)
        self.assertNotEqual(original['program_hash'], changed['program_hash'])
        self.assertEqual(original['probe_outputs'], changed['probe_outputs'])
        self.assertEqual(original['affine_signature'], changed['affine_signature'])

    def test_family_identity_is_part_of_the_new_meaning(self):
        memory = next(p for p in self.meanings['before']['programs'] if p['family'] == 'memory_policy')
        memory = dict(memory, variant=3, parameter_a=0, parameter_b=0)
        obs = ae._program_observation(memory)
        identity = ae.affine_task(0, 32)
        self.assertEqual(obs['probe_outputs'], identity['probe_targets'])
        self.assertIsNone(obs['affine_signature'])
        self.assertFalse(ae._affine_matches(obs, identity))

    def test_zero_probe_alone_cannot_confuse_different_slopes(self):
        alternative = dict(self.adapter, variant=0)
        left, right = ae._program_observation(self.adapter), ae._program_observation(alternative)
        self.assertEqual(left['probe_outputs'][0], right['probe_outputs'][0])
        self.assertNotEqual(left['probe_outputs'][1], right['probe_outputs'][1])
        self.assertFalse(ae._affine_matches(right, ae.affine_task(3, 42)))

    def test_unit_output_coordinate_alone_cannot_confuse_offset_and_slope(self):
        alternative = dict(self.adapter, variant=2, parameter_a=12)
        left, right = ae._program_observation(self.adapter), ae._program_observation(alternative)
        self.assertEqual(left['probe_outputs'][1][0], right['probe_outputs'][1][0])
        self.assertNotEqual(left['probe_outputs'][0], right['probe_outputs'][0])
        self.assertFalse(ae._affine_matches(right, ae.affine_task(3, 42)))

    def test_no_authority_or_follow_up_claims_escape(self):
        self.assertEqual(self.packet['claims'], {key: False for key in FALSE_CLAIMS})
        summary = self.packet['summary']
        self.assertEqual(summary['new_accepted_successors'], 0)
        self.assertEqual(summary['fresh_live_evaluations'], 0)
        self.assertFalse(summary['follow_up_selection_performed'])
        self.assertFalse(summary['physical_candidate_active'])
        self.assertNotIn('next_context', self.packet)
        self.assertNotIn('objective', self.packet)
        self.assertNotIn('prospective_state', self.packet)

    def test_immutable_canonical_reconstruction(self):
        reconstructed = ae.PreparedTaskInterpretation(self.raw)
        self.assertEqual(reconstructed.packet_bytes, self.raw)
        self.assertEqual(ae.canonical(reconstructed.packet), self.raw)
        value = self.prepared.packet
        value['catalog']['tail'][0]['slope'] = 500
        self.assertEqual(self.prepared.packet['catalog']['tail'][0]['slope'], 1)

    def test_exact_external_packet_anchor_required(self):
        ae.verify_packet_bytes(self.raw, self.prepared, expected_sha256=ae.sha(self.raw))
        with self.assertRaises(ValueError):
            ae.verify_packet_bytes(self.raw, self.prepared, expected_sha256='0' * 64)

    def test_changed_packet_bytes_fail_external_anchor(self):
        with self.assertRaises(ValueError):
            ae.verify_packet_bytes(self.raw + b' ', self.prepared, expected_sha256=ae.sha(self.raw))

    def test_physical_packages_remain_unchanged(self):
        self.assertEqual(self.initial_snapshots,
                         (snapshot(self.packages / 'before'), snapshot(self.packages / 'after')))

    def test_uncaptured_base_byte_mutation_fails_complete_snapshot_check(self):
        files = dict(self.initial_snapshots[0])
        path = 'base/model/phase15_planner/weights.i16le.bin'
        self.assertNotIn(path, self.packet['captured_inputs']['before'])
        damaged = bytearray(files[path]); damaged[0] ^= 1
        files[path] = bytes(damaged)
        bound = self.prepared.finite().packet['bindings']['predecessor_physical_hash']
        with self.assertRaises(ValueError):
            ae._complete_snapshot(files, expected_package_hash=bound)

    def test_missing_uncaptured_file_fails_complete_snapshot_check(self):
        files = dict(self.initial_snapshots[0])
        files.pop('base/model/phase15_planner/weights.i16le.bin')
        bound = self.prepared.finite().packet['bindings']['predecessor_physical_hash']
        with self.assertRaises(ValueError):
            ae._complete_snapshot(files, expected_package_hash=bound)

    def test_extra_physical_file_fails_complete_snapshot_check(self):
        files = dict(self.initial_snapshots[1])
        files['base/unrecorded.bin'] = b'unrecorded'
        bound = self.prepared.finite().packet['bindings']['candidate_physical_hash']
        with self.assertRaises(ValueError):
            ae._complete_snapshot(files, expected_package_hash=bound)

    def test_existing_physical_directory_is_rejected(self):
        with self.assertRaises(ValueError):
            ae.prepare_task_interpretation(ROOT, self.packages)

    def test_noncanonical_packet_is_rejected(self):
        with self.assertRaises(ValueError):
            ae.PreparedTaskInterpretation(self.raw + b'\n')

    def test_mutable_packet_bytes_are_rejected(self):
        with self.assertRaises(ValueError):
            ae.PreparedTaskInterpretation(bytearray(self.raw))

    def test_missing_packet_field_is_rejected(self):
        self.rejected(lambda p: p.pop('semantic_guard'))

    def test_extra_packet_field_is_rejected(self):
        self.rejected(lambda p: p.__setitem__('selected_follow_up', {}))

    def test_wrong_continuation_base_is_rejected(self):
        self.rejected(lambda p: p.__setitem__('base_commit', '0' * 40))

    def test_wrong_policy_is_rejected(self):
        self.rejected(lambda p: p.__setitem__('policy', 'caller-selected-palette'))

    def test_wrong_finite_identity_is_rejected(self):
        self.rejected(lambda p: p.__setitem__('finite_packet_sha256', '0' * 64))

    def test_changed_finite_meaning_is_rejected_even_after_rehash(self):
        def mutation(p):
            joint = p['finite_packet']['protected_packet']['joint_packet']
            joint['task_meanings']['tasks'][-1]['targets'][0][0] += 1
            p['finite_packet_sha256'] = ae.digest(p['finite_packet'])
        self.rejected(mutation)

    def test_legacy_name_rewrite_is_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['legacy_task_ids'][0] = 'phase17ae.rewritten'
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_legacy_meaning_hash_rewrite_is_rejected(self):
        self.rejected(lambda p: p['catalog'].__setitem__('legacy_tasks_sha256', '1' * 64))

    def test_tail_meaning_change_is_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['tail'][0]['offset'] = -31
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_tail_probe_target_change_is_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['tail'][0]['probe_targets'][0][0] += 1
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_removed_separating_probe_is_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['tail'][0]['probe_inputs'].pop()
            p['catalog']['tail'][0]['probe_targets'].pop()
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_tail_reordering_is_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['tail'].reverse()
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_duplicate_tail_semantics_are_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['tail'][1] = copy.deepcopy(p['catalog']['tail'][0])
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_tail_index_substitution_is_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['tail'][0]['index'] = 21
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_tail_name_collision_is_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['tail'][0]['task_id'] = p['catalog']['legacy_task_ids'][0]
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_catalog_boundary_extension_is_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['descriptor']['catalog_bound'] = 283
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_family_scope_removal_is_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['descriptor']['meaning_requires_family'] = 'any'
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_unbounded_reference_realizer_is_rejected_even_after_rehash(self):
        def mutation(p):
            p['catalog']['tail'][0]['reference_program']['a'] = -32
            p['catalog']['tail'][0]['reference_program']['b'] = 0
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_production_candidate_metadata_cannot_be_added_to_reference(self):
        def mutation(p):
            p['catalog']['tail'][0]['reference_program']['public_nonce_hash'] = '1' * 64
            self.rehash_catalog(p)
        self.rejected(mutation)

    def test_omitted_captured_program_is_rejected(self):
        path = 'registry/programs/' + ae.digest(self.adapter) + '.json'
        self.rejected(lambda p: p['captured_inputs']['before'].pop(path))

    def test_extra_captured_image_is_rejected(self):
        self.rejected(lambda p: p['captured_inputs']['after'].__setitem__('invented.json', '7b7d'))

    def test_captured_path_traversal_is_rejected(self):
        self.rejected(lambda p: p['captured_inputs']['after'].__setitem__('../outside.json', '7b7d'))

    def test_captured_program_change_is_rejected(self):
        def mutation(p):
            path = 'registry/programs/' + ae.digest(self.adapter) + '.json'
            program = ae.load_json_strict(bytes.fromhex(p['captured_inputs']['before'][path]))
            program['parameter_a'] += 1
            p['captured_inputs']['before'][path] = ae.canonical(program).hex()
        self.rejected(mutation)

    def test_registry_activation_is_rejected(self):
        def mutation(p):
            path = 'registry/manifest.json'
            registry = ae.load_json_strict(bytes.fromhex(p['captured_inputs']['after'][path]))
            registry['candidate_active'] = True
            p['captured_inputs']['after'][path] = ae.canonical(registry).hex()
        self.rejected(mutation)

    def test_registry_reordering_is_rejected(self):
        def mutation(p):
            path = 'registry/manifest.json'
            registry = ae.load_json_strict(bytes.fromhex(p['captured_inputs']['after'][path]))
            registry['inherited_program_hashes'].reverse()
            p['captured_inputs']['after'][path] = ae.canonical(registry).hex()
        self.rejected(mutation)

    def test_changed_manifest_cannot_self_authenticate(self):
        def mutation(p):
            manifest = ae.load_json_strict(bytes.fromhex(p['captured_inputs']['after'][ae.MANIFEST]))
            manifest['claims']['promotion_authorized'] = True
            manifest['materialized_package_hash'] = ae.digest({k: v for k, v in manifest.items()
                                                              if k != 'materialized_package_hash'})
            p['captured_inputs']['after'][ae.MANIFEST] = ae.canonical(manifest).hex()
        self.rejected(mutation)

    def test_before_and_after_manifests_cannot_be_swapped(self):
        self.rejected(lambda p: p['captured_inputs']['after'].__setitem__(
            ae.MANIFEST, p['captured_inputs']['before'][ae.MANIFEST]))

    def test_noncanonical_program_image_is_rejected(self):
        path = 'registry/programs/' + ae.digest(self.adapter) + '.json'
        self.rejected(lambda p: p['captured_inputs']['before'].__setitem__(
            path, (bytes.fromhex(p['captured_inputs']['before'][path]) + b'\n').hex()))

    def test_uppercase_hex_image_is_rejected(self):
        self.rejected(lambda p: p['captured_inputs']['before'].__setitem__(
            ae.MANIFEST, p['captured_inputs']['before'][ae.MANIFEST].upper()))

    def test_odd_hex_image_is_rejected(self):
        self.rejected(lambda p: p['captured_inputs']['before'].__setitem__(ae.MANIFEST, '0'))

    def test_false_predecessor_failure_is_rejected(self):
        self.rejected(lambda p: p['observations']['before']['affine_checks'][259 - 22].__setitem__(
            'satisfied', False))

    def test_false_successor_success_is_rejected(self):
        self.rejected(lambda p: p['observations']['after']['affine_checks'][0].__setitem__('satisfied', True))

    def test_forged_witness_identity_is_rejected(self):
        self.rejected(lambda p: p['observations']['before']['affine_checks'][259 - 22].__setitem__(
            'satisfying_program_hashes', ['0' * 64]))

    def test_automatic_credit_for_already_solved_tail_is_rejected(self):
        self.rejected(lambda p: p['observations']['after']['checked_declared_indices'].append(259))

    def test_forged_semantic_guard_is_rejected(self):
        self.rejected(lambda p: p['semantic_guard']['already_solved_undeclared_task'].__setitem__(
            'predecessor_semantic_failure', True))

    def test_count_only_capability_gain_is_rejected(self):
        self.rejected(lambda p: p['summary'].__setitem__('after_frontier', 282))

    def test_second_accepted_step_claim_is_rejected(self):
        self.rejected(lambda p: p['summary'].__setitem__('new_accepted_successors', 1))

    def test_root_authority_claim_is_rejected(self):
        self.rejected(lambda p: p['claims'].__setitem__('root_transition_verified', True))

    def test_claim_flags_require_booleans(self):
        self.rejected(lambda p: p['claims'].__setitem__('promotion_authorized', 0))

    def test_physical_refinement_scope_escalation_is_rejected(self):
        self.rejected(lambda p: p['scope'].__setitem__('physical_mapping', 'universally verified'))

    def test_sampler_reachability_scope_escalation_is_rejected(self):
        self.rejected(lambda p: p['scope'].__setitem__('sampler_coverage', 'all 260 are offered now'))

    def test_unknown_or_noninteger_task_indices_are_rejected(self):
        for index in (-1, 282, True, '259'):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.decision(index)

    def test_wrong_selected_package_anchor_is_rejected(self):
        with self.assertRaises(ValueError):
            self.decision(259, expected_predecessor_hash='0' * 64)
        with self.assertRaises(ValueError):
            self.decision(259, expected_candidate_hash='0' * 64)

    def test_unvalidated_state_cannot_be_submitted(self):
        with self.assertRaises(ValueError):
            ae.novelty_for(self.packet, task_index=259, expected_predecessor_hash='0' * 64,
                           expected_candidate_hash='1' * 64)

    def test_palette_coordinates_must_be_integers_in_fixed_ranges(self):
        for variant, offset in ((-1, 0), (4, 0), (0, -1), (0, 65), (True, 0), (0, False)):
            with self.subTest(variant=variant, offset=offset), self.assertRaises(ValueError):
                ae.affine_task(variant, offset)

    def test_production_parameter_bounds_and_integer_types_remain_required(self):
        for field, value in (('parameter_a', 17), ('parameter_b', -17),
                             ('parameter_a', True), ('variant', 4), ('variant', False)):
            program = dict(self.adapter)
            program[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                ae._program_observation(program)

    def test_independent_interpreter_disagreement_fails_closed(self):
        with patch.object(ae, 'execute_reference', return_value=[999, 999, 999, 999]):
            with self.assertRaises(ValueError):
                ae.PreparedTaskInterpretation(self.raw)

    def test_matrix_interpreter_disagreement_fails_closed(self):
        with patch.object(ae, 'execute_matrix', return_value=[999, 999, 999, 999]):
            with self.assertRaises(ValueError):
                ae.PreparedTaskInterpretation(self.raw)

    def test_coefficient_probe_disagreement_fails_closed(self):
        obs = ae._program_observation(self.adapter)
        obs['affine_signature'] = [4, 11]
        with self.assertRaises(ValueError):
            ae._affine_matches(obs, ae.affine_task(3, 42))


if __name__ == '__main__':
    unittest.main(verbosity=2)
