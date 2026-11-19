"""AF captured bytes, fixed meanings and genuinely executed work boundaries.

These are runtime and refusal tests. Formal acceptance is supplied only by the
separate pinned Lean gate; controlled mutations below are never proof evidence.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import second_step as af
from rcp_rclm_runtime_v5.phase17 import task_interpretation as ae
from rcp_rclm_runtime_v5.phase17.conservative_extension import extract_predecessor
from rcp_rclm_runtime_v5.phase17.materialized import PackageReceipt, snapshot

ROOT = Path(__file__).resolve().parents[3]


class SecondStepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='phase17af-physical-')
        cls.packages = Path(cls.temp.name) / 'packages'
        with patch('subprocess.Popen', side_effect=AssertionError('AF preparation must not launch a worker or compiler')):
            cls.prepared = af.prepare_second_step(ROOT, cls.packages)
        cls.raw = cls.prepared.packet_bytes
        cls.packet = cls.prepared.packet
        cls.before = cls.packages / 'first/after'
        cls.after = cls.packages / 'second'

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def rejected(self, mutation):
        value = copy.deepcopy(self.packet)
        mutation(value)
        with self.assertRaises((ValueError, TypeError, KeyError)):
            af.PreparedSecondStep(af.canonical(value))

    @staticmethod
    def rehash_journal(packet, mutate):
        rows = [af.load_json_strict(raw) for raw in bytes.fromhex(packet['reference_journal_hex']).splitlines()]
        mutate(rows)
        rebuilt = []
        for row in rows:
            rebuilt.append(af._event(row['body'], len(rebuilt), rebuilt[-1]['hash'] if rebuilt else '0' * 64))
        raw = af._journal_bytes(rebuilt)
        packet['reference_journal_hex'] = raw.hex()
        packet['resource']['journal_sha256'] = af.sha(raw)
        packet['resource']['journal_head'] = rebuilt[-1]['hash'] if rebuilt else '0' * 64
        packet['resource']['journal_event_count'] = len(rebuilt)

    def test_exact_published_ae_baseline_and_retained_anchors(self):
        self.assertEqual(self.packet['base_commit'], 'b964bb738890047fea021a50aeb1160eb502e3d4')
        self.assertEqual(self.packet['retained_sha256'], af.RETAINED_PINS)
        for name, image in self.packet['retained_execution_hex'].items():
            self.assertEqual(af.sha(bytes.fromhex(image)), af.RETAINED_PINS[name])

    def test_original_fixed_interpretation_bytes_are_unchanged(self):
        self.assertEqual(af.sha(self.prepared.interpretation().packet_bytes), af.AE_PACKET_SHA)
        self.assertEqual(af.sha(self.prepared.successor_context().packet_bytes), af.AD_PACKET_SHA)
        self.assertEqual(self.prepared.finite().packet_bytes, self.prepared.successor_context().finite().packet_bytes)

    def test_actual_initial_production_choice_has_required_affine_meaning(self):
        context = self.packet['successor_packet']['next_context']
        program = self.packet['update']['program']
        self.assertEqual(context['initial_candidate_hash'], af.digest(program))
        self.assertEqual(context['initial_candidate_index'], 30)
        self.assertEqual([program[k] for k in ('family', 'variant', 'generation', 'parameter_a', 'parameter_b')],
                         ['adapter_policy', 0, 2, -6, 7])
        self.assertEqual(self.packet['update']['task'], 41)

    def test_public_nonce_and_commitment_are_the_preexisting_ad_values(self):
        context = self.packet['successor_packet']['next_context']
        self.assertEqual(context['view']['public_nonce_hash'], af.ad.SELECTED_NONCE)
        self.assertEqual(context['view']['challenge_commitment_hash'], af.ad.SELECTED_COMMITMENT)
        self.assertEqual(self.packet['second_context'], context['provenance_context'])

    def test_original_objective_is_preserved_without_an_integration_claim(self):
        intent = self.packet['selection_intent']
        self.assertEqual(intent['original_ad_objective_family'], 'retrieval_policy')
        self.assertIs(intent['objective_integration_claimed'], False)
        self.assertIs(intent['live_challenge_opened'], False)

    def test_complete_production_inventory_has_all_32_unchanged_rows(self):
        context = self.packet['successor_packet']['next_context']
        self.assertEqual(len(context['rows']), 32)
        self.assertEqual(len(context['programs']), 32)
        self.assertEqual({af.digest(p) for p in context['programs']}, {r['key'] for r in context['rows']})
        self.assertEqual(self.packet['proposal']['choices'], [30])

    def test_complete_physical_package_is_one_inactive_append(self):
        before, after = snapshot(self.before), snapshot(self.after)
        self.assertEqual((len(before), len(after)), (176, 177))
        added = 'registry/programs/' + af.SELECTED_PROGRAM + '.json'
        self.assertEqual(set(after) - set(before), {added})
        self.assertEqual([n for n in before if before[n] != after[n]],
                         [n for n in before if n in {af.MANIFEST, 'registry/manifest.json'}])
        self.assertTrue(all(before[n] == after[n] for n in before if n.startswith('base/')))

    def test_captured_images_bind_all_9_and_10_program_descriptors(self):
        for side, root, count in (('before', self.before, 11), ('after', self.after, 12)):
            images = self.packet['captured_inputs'][side]
            self.assertEqual(len(images), count)
            for name, image in images.items():
                self.assertEqual((root / name).read_bytes(), bytes.fromhex(image))
        self.assertEqual(sum(map(len, self.packet['captured_inputs'].values())), 23)

    def test_registry_key_order_is_original_after_then_new_key(self):
        b, a = (self.packet['finite_projection'][s] for s in ('before', 'after'))
        old = self.prepared.finite().joint().packet['typed_binding']['candidate']['base']
        self.assertEqual(b['keys'], old)
        self.assertEqual(a['keys'], [*old, af.SELECTED_PROGRAM])
        self.assertEqual([af.digest(p) for p in a['programs']], a['keys'])

    def test_exact_retraction_reconstructs_bytes_without_active_store_action(self):
        before, after = snapshot(self.before), snapshot(self.after)
        metadata = tuple((name, before[name]) for name in ('registry/manifest.json', af.MANIFEST))
        recovered = extract_predecessor(after, added_key=af.SELECTED_PROGRAM, metadata=metadata)
        self.assertEqual(recovered, before)

    def test_independent_before_projection_matches_the_ae_selected_successor(self):
        p = self.packet['finite_projection']['before']; old = self.prepared.finite().joint().packet
        typed = old['typed_binding']['candidate']
        self.assertEqual(p['frozen'], [typed[group] for group in af.GROUPS])
        self.assertEqual(p['programs'], old['task_meanings']['after']['programs'])
        self.assertEqual(p['declared'], list(range(22)))

    def test_fresh_protected_observations_preserve_every_existing_value(self):
        b, a = (self.packet['finite_projection'][s] for s in ('before', 'after'))
        self.assertEqual(a['frozen'], b['frozen'])
        self.assertEqual(a['proofs'], b['proofs'])
        self.assertEqual(a['semantic'], b['semantic'])
        self.assertNotEqual(a['package_hash'], b['package_hash'])
        self.assertEqual(len(a['proofs']), 13)

    def test_new_semantics_fail_before_and_hold_after_in_the_same_catalog(self):
        b, a = (self.packet['availability'][s] for s in ('before', 'after'))
        self.assertEqual(b['affine_rows'][41 - 22]['witnesses'], [])
        self.assertEqual(a['affine_rows'][41 - 22]['witnesses'], [af.SELECTED_PROGRAM])
        self.assertEqual(b['affine_solved_indices'], [259])
        self.assertEqual(a['affine_solved_indices'], [41, 259])

    def test_all_260_palette_rows_are_recomputed_and_legacy_checks_retained(self):
        for observation in self.packet['availability'].values():
            self.assertEqual([r['index'] for r in observation['affine_rows']], list(range(22, 282)))
            self.assertEqual(observation['legacy_checks'], [True] * 22)

    def test_frontier_declarations_come_from_validated_metadata_and_are_checked(self):
        manifest = af.load_json_strict(bytes.fromhex(self.packet['captured_inputs']['after'][af.MANIFEST]))
        before = self.packet['finite_projection']['before']; after = self.packet['finite_projection']['after']
        self.assertEqual(manifest['fixed_task_name'], af.SELECTED_NAME)
        self.assertEqual(after['named_frontier'], sorted([*before['named_frontier'], manifest['fixed_task_name']]))
        self.assertEqual(after['declared'], [*range(22), manifest['fixed_task_index']])
        self.assertNotIn(259, after['declared'])
        self.assertEqual(self.packet['availability']['after']['checked_declared_indices'], after['declared'])

    def test_policy_is_same_per_step_envelope_without_campaign_accounting(self):
        self.assertEqual(self.packet['resource']['policy'], self.prepared.finite().packet['resource']['policy'])
        self.assertEqual(self.packet['resource']['policy']['cost_limit'], 9920)
        self.assertIs(self.packet['claims']['campaign_budget_authority_integrated'], False)
        self.assertIs(self.packet['claims']['complete_resource_accounting'], False)

    def test_metered_scope_retains_input_and_output_value_tariffs(self):
        resource = self.packet['resource']
        self.assertEqual(resource['charge_sequence'], ['candidate'] + ['vector'] * 38)
        self.assertEqual(resource['spent'], [1, 38, 152, 152])
        self.assertEqual(resource['charged_cost'], 976)
        self.assertIs(resource['timing_measured'], False)
        self.assertIn('input_values', resource['policy']['dimensions'])
        self.assertIn('output_values', resource['policy']['dimensions'])

    def test_persisted_journal_is_exactly_the_captured_execution_record(self):
        raw = (self.packages / 'reference-work.jsonl').read_bytes()
        self.assertEqual(raw.hex(), self.packet['reference_journal_hex'])
        rows = [af.load_json_strict(x) for x in raw.splitlines()]
        self.assertEqual(len(rows), 80)
        self.assertEqual(af.sha(raw), self.packet['resource']['journal_sha256'])
        self.assertEqual(rows[-1]['hash'], self.packet['resource']['journal_head'])
        self.assertEqual(rows[-1]['body']['status'], 'completed_declared_reference_work')

    def test_work_inputs_and_outputs_bind_actual_descriptor_bytes(self):
        for row in self.packet['resource']['work'][1:]:
            entry = row['input']; root = self.before if entry['side'] == 'before' else self.after
            raw = (root / ('registry/programs/' + entry['program_hash'] + '.json')).read_bytes()
            self.assertEqual(af.sha(raw), entry['descriptor_sha256'])
            self.assertEqual(row['output'], af.execute_reference(af.load_json_strict(raw), entry['input_vector']))

    def test_terminal_controller_receipt_contains_one_actual_reference_verdict(self):
        transcript = self.packet['reference_transcript']
        prefix = af.restore(af.canonical(transcript['final_checkpoint']), expected_prefix_hash=transcript['final_prefix_hash'])
        self.assertEqual(len(prefix.observations), 1)
        self.assertEqual(prefix.observations[0].program_hash, af.SELECTED_PROGRAM)
        self.assertEqual(prefix.observations[0].verdict, 'candidate_passed')
        self.assertEqual(af.decide(prefix).action, af.Action.AWAIT_ROOT_VERIFICATION)
        self.assertIs(transcript['evaluation']['formal_acceptance_established'], False)

    def test_broader_claims_remain_strictly_false_and_preparation_requires_lean(self):
        self.assertEqual(set(self.packet['claims']), set(af.FALSE_CLAIMS))
        self.assertEqual(len(self.packet['claims']), 24)
        self.assertTrue(all(value is False for value in self.packet['claims'].values()))
        self.assertIs(self.packet['summary']['formal_acceptance_required'], True)

    def test_prepared_input_is_immutable_and_returned_dict_is_detached(self):
        with self.assertRaises(FrozenInstanceError):
            self.prepared.packet_bytes = b'changed'
        detached = self.prepared.packet; detached['claims']['promotion_authorized'] = True
        self.assertIs(self.prepared.packet['claims']['promotion_authorized'], False)

    def test_pure_packet_validation_does_not_open_files_or_launch_subprocesses(self):
        with (patch('builtins.open', side_effect=AssertionError('serialized validator file access')),
              patch('pathlib.Path.open', side_effect=AssertionError('serialized validator path access')),
              patch('subprocess.Popen', side_effect=AssertionError('serialized validator subprocess'))):
            again = af.PreparedSecondStep(self.raw)
        self.assertEqual(again.packet_bytes, self.raw)

    def test_external_packet_anchor_is_required(self):
        with self.assertRaises(ValueError):
            af.verify_packet_bytes(self.raw, self.prepared, expected_sha256='0' * 64)
        af.verify_packet_bytes(self.raw, self.prepared, expected_sha256=af.sha(self.raw))

    def test_existing_physical_output_is_refused_without_repreparation(self):
        with patch.object(af.ad, 'prepare_successor_context', side_effect=AssertionError('must refuse first')):
            with self.assertRaises(ValueError):
                af.prepare_second_step(ROOT, self.packages)

    def test_source_tree_cannot_be_physical_output(self):
        with patch.object(af.ad, 'prepare_successor_context', side_effect=AssertionError('must refuse first')):
            with self.assertRaises(ValueError):
                af.prepare_second_step(ROOT, ROOT / 'forbidden-second-output')

    def test_linked_output_parent_is_refused_before_preparation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'real').mkdir()
            try:
                (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            except (OSError, NotImplementedError):
                # Windows junction/symlink rights need not be granted. The
                # same path refusal is exercised via an observed link predicate.
                with patch('pathlib.Path.is_symlink', return_value=True):
                    with self.assertRaises(ValueError):
                        af.prepare_second_step(ROOT, root / 'new')
            else:
                with self.assertRaises(ValueError):
                    af.prepare_second_step(ROOT, root / 'link/new')

    def test_every_actual_vector_call_follows_its_persisted_reservation(self):
        work = self.packet['resource']['work']; intent = self.packet['selection_intent']
        receipts = {s: PackageReceipt(p, (p / af.MANIFEST).read_bytes())
                    for s, p in (('before', self.before), ('after', self.after))}
        policy = af.Policy.from_json(self.packet['resource']['policy'])
        calls = []; execute = af.execute_installed
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'work.jsonl'
            def observed(receipt, key, vector):
                rows = [af.load_json_strict(x) for x in path.read_bytes().splitlines()]
                self.assertEqual(rows[-1]['body']['kind'], 'reserve')
                self.assertEqual(rows[-1]['body']['operation'], 'vector')
                self.assertEqual(rows[-1]['body']['input_sha256'], af.sha(af.canonical(work[len(calls) + 1]['input'])))
                calls.append((receipt.package_hash, key, vector))
                return execute(receipt, key, vector)
            with patch.object(af, 'execute_installed', side_effect=observed):
                af._execute_work(path, work, policy, intent, receipts)
            self.assertEqual(len(calls), 38)

    def test_failed_actual_vector_call_leaves_charged_unsealed_record(self):
        receipts = {s: PackageReceipt(p, (p / af.MANIFEST).read_bytes())
                    for s, p in (('before', self.before), ('after', self.after))}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'work.jsonl'
            with patch.object(af, 'execute_installed', side_effect=RuntimeError('controlled installed-call failure')):
                with self.assertRaises(RuntimeError):
                    af._execute_work(path, self.packet['resource']['work'],
                        af.Policy.from_json(self.packet['resource']['policy']), self.packet['selection_intent'], receipts)
            rows = [af.load_json_strict(x) for x in path.read_bytes().splitlines()]
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[-1]['body']['kind'], 'reserve')
            self.assertEqual(rows[-1]['body']['spent_after'], [1, 1, 4, 4])
            self.assertFalse(any(row['body']['kind'] == 'seal' for row in rows))

    def test_short_journal_write_refused_before_candidate_execution(self):
        receipts = {s: PackageReceipt(p, (p / af.MANIFEST).read_bytes())
                    for s, p in (('before', self.before), ('after', self.after))}
        policy = af.Policy.from_json(self.packet['resource']['policy'])
        original_open = Path.open
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'work.jsonl'
            class ShortWriter:
                def __init__(self, stream):
                    self.stream, self.writes = stream, 0
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return self.stream.__exit__(*args)
                def write(self, raw):
                    self.writes += 1
                    if self.writes == 2:
                        self.stream.write(raw[:-1])
                        return len(raw) - 1
                    return self.stream.write(raw)
                def flush(self):
                    return self.stream.flush()
                def fileno(self):
                    return self.stream.fileno()
            def short_open(target, *args, **kwargs):
                stream = original_open(target, *args, **kwargs)
                return ShortWriter(stream) if target == path and args == ('xb',) else stream
            with (patch.object(Path, 'open', new=short_open),
                  patch.object(af, 'load_json_strict', side_effect=AssertionError('candidate must not execute')) as candidate,
                  patch.object(af, 'execute_installed', side_effect=AssertionError('vector must not execute')) as vector):
                with self.assertRaisesRegex(ValueError, 'short reference-work journal write'):
                    af._execute_work(path, self.packet['resource']['work'], policy,
                                     self.packet['selection_intent'], receipts)
                candidate.assert_not_called(); vector.assert_not_called()
            self.assertEqual(path.read_bytes().count(b'\n'), 1)

    def test_uncaptured_base_byte_mutation_is_not_hidden_by_image_selection(self):
        files = snapshot(self.after); manifest = af.load_json_strict(files[af.MANIFEST])
        name = next(n for n in files if n.startswith('base/') and len(files[n]) > 10)
        files[name] = files[name] + b'changed'
        with self.assertRaises(ValueError):
            ae._complete_snapshot(files, expected_package_hash=manifest['materialized_package_hash'])

    def test_missing_charge_is_rejected_after_journal_rehash(self):
        self.rejected(lambda p: self.rehash_journal(p, lambda rows: rows.__delitem__(slice(1, 3))))

    def test_extra_charge_is_rejected_after_journal_rehash(self):
        self.rejected(lambda p: self.rehash_journal(p, lambda rows: rows.insert(3, copy.deepcopy(rows[1]))))

    def test_reordered_operations_are_rejected_after_journal_rehash(self):
        def reorder(rows):
            rows[3:7] = rows[5:7] + rows[3:5]
        self.rejected(lambda p: self.rehash_journal(p, reorder))

    def test_changed_result_is_rejected_after_journal_rehash(self):
        self.rejected(lambda p: self.rehash_journal(p, lambda rows: rows[4]['body'].__setitem__('result_sha256', '0' * 64)))

    def test_changed_input_is_rejected_after_journal_rehash(self):
        self.rejected(lambda p: self.rehash_journal(p, lambda rows: rows[3]['body'].__setitem__('input_sha256', '0' * 64)))

    def test_zero_elapsed_measurement_cannot_be_invented_in_journal(self):
        self.rejected(lambda p: self.rehash_journal(p, lambda rows: rows[2]['body'].__setitem__('elapsed_ns', 0)))

    def test_work_output_substitution_is_rejected(self):
        self.rejected(lambda p: p['resource']['work'][1]['output'].__setitem__(0, 123))

    def test_work_descriptor_identity_substitution_is_rejected(self):
        self.rejected(lambda p: p['resource']['work'][1]['input'].__setitem__('descriptor_sha256', '0' * 64))

    def test_candidate_choice_cannot_skip_the_first_production_decision(self):
        self.rejected(lambda p: p['proposal'].__setitem__('choices', [0, 30]))

    def test_predecessor_rejection_cannot_be_fabricated(self):
        self.rejected(lambda p: p['proposal'].__setitem__('verdicts', [False, True]))

    def test_context_cannot_be_reparented(self):
        self.rejected(lambda p: p['second_context'].__setitem__('parent_package', '0' * 64))

    def test_changed_public_nonce_is_refused_even_with_rehashed_inner_packet(self):
        self.rejected(lambda p: p['successor_packet']['next_context']['view'].__setitem__('public_nonce_hash', '0' * 64))

    def test_candidate_program_change_is_refused(self):
        self.rejected(lambda p: p['update']['program'].__setitem__('parameter_a', -5))

    def test_fixed_meaning_cannot_be_redefined(self):
        self.rejected(lambda p: p['interpretation_packet']['catalog']['tail'][41 - 22].__setitem__('offset', -12))

    def test_already_solved_tail_cannot_be_claimed_as_the_new_task(self):
        self.rejected(lambda p: p['update'].__setitem__('task', 259))

    def test_declared_frontier_cannot_be_inflated_without_observations(self):
        self.rejected(lambda p: p['finite_projection']['after']['declared'].append(42))

    def test_name_cannot_be_changed_independently_of_fixed_meaning(self):
        self.rejected(lambda p: p['update'].__setitem__('task_name', 'phase17af.invented'))

    def test_root_identity_cannot_be_replaced(self):
        self.rejected(lambda p: p['finite_projection']['after'].__setitem__('root', '0' * 64))

    def test_protected_value_cannot_be_changed(self):
        self.rejected(lambda p: p['protected_observations']['after']['mass_minus_one_dictionary'][0].__setitem__(
            0, p['protected_observations']['after']['mass_minus_one_dictionary'][0][0] + 1))

    def test_proof_source_identity_cannot_be_changed(self):
        self.rejected(lambda p: p['proof_observations']['after'][0].__setitem__('source_sha256', '0' * 64))

    def test_rehashed_candidate_manifest_cannot_change_frozen_base_rows(self):
        def change(p):
            images = p['captured_inputs']['after']; m = af.load_json_strict(bytes.fromhex(images[af.MANIFEST]))
            next(r for r in m['files'] if r['path'].startswith('base/'))['sha256'] = '0' * 64
            m['materialized_package_hash'] = af.digest({k: v for k, v in m.items() if k != 'materialized_package_hash'})
            images[af.MANIFEST] = af.canonical(m).hex()
            p['update']['candidate_package'] = m['materialized_package_hash']
        self.rejected(change)

    def test_rehashed_candidate_manifest_cannot_claim_activation(self):
        def change(p):
            images = p['captured_inputs']['after']; m = af.load_json_strict(bytes.fromhex(images[af.MANIFEST]))
            m['candidate_active'] = True
            m['materialized_package_hash'] = af.digest({k: v for k, v in m.items() if k != 'materialized_package_hash'})
            images[af.MANIFEST] = af.canonical(m).hex()
        self.rejected(change)

    def test_extra_physical_capture_is_refused(self):
        self.rejected(lambda p: p['captured_inputs']['after'].__setitem__('extra.json', '7b7d'))

    def test_parent_capture_substitution_is_refused(self):
        self.rejected(lambda p: p['captured_inputs']['before'].__setitem__('registry/manifest.json', '7b7d'))

    def test_claim_escalation_is_refused(self):
        self.rejected(lambda p: p['claims'].__setitem__('root_transition_verified', True))

    def test_numeric_false_is_not_a_false_claim(self):
        self.rejected(lambda p: p['claims'].__setitem__('cross_platform_validation', 0))

    def test_resource_envelope_cannot_be_reset_or_inflated(self):
        self.rejected(lambda p: p['resource']['policy'].__setitem__('cost_limit', 100000))

    def test_complete_resource_claim_cannot_be_added_to_local_reference_profile(self):
        self.rejected(lambda p: p['resource'].__setitem__('complete_resource_accounting', True))

    def test_retained_completed_execution_cannot_be_self_reanchored(self):
        self.rejected(lambda p: p['retained_sha256'].__setitem__(af.AD_ROOT + '/execution.json', '0' * 64))

    def test_unknown_packet_field_is_refused(self):
        self.rejected(lambda p: p.__setitem__('approval_override', True))

    def test_completed_reference_transcript_digest_is_separate_from_history_anchor(self):
        self.assertEqual(self.packet['reference_transcript_sha256'], af.sha(af.canonical(self.packet['reference_transcript'])))
        self.assertEqual(self.packet['second_context']['transcript_hash'],
                         self.packet['successor_packet']['prospective_history_hash'])
        self.assertNotEqual(self.packet['reference_transcript_sha256'], self.packet['second_context']['transcript_hash'])

    def test_reference_transcript_digest_cannot_be_replaced(self):
        self.rejected(lambda p: p.__setitem__('reference_transcript_sha256', '0' * 64))


if __name__ == '__main__':
    unittest.main()
