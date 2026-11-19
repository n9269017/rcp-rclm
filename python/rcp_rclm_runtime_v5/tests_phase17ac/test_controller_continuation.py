"""Controller protocol comparisons and adversarial prefix reconstruction."""
from dataclasses import replace
import json
from pathlib import Path
import unittest

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from rcp_rclm_runtime_v5.phase17 import controller as production
from rcp_rclm_runtime_v5.phase17 import controller_continuation as ac
from rcp_rclm_runtime_v5.phase17 import controller_continuation_lean as proof

ROOT = Path(__file__).resolve().parents[3]


class ContinuationComparisons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = ac.prepare(ROOT)
        cls.packet = cls.prepared.packet
        cls.cases = {case['name']: case for case in cls.packet['cases']}

    def test_all_actions_and_credit_boundaries_are_compared(self):
        summary = self.packet['summary']
        self.assertEqual(summary['case_count'], 86)
        self.assertEqual(set(summary['actions_observed']), {action.value for action in production.Action})
        self.assertTrue({0, 1, 4, 31, 32, 40, 100} <= set(summary['initial_credit_values']))
        self.assertEqual(summary['controlled_evaluations'], 1784)
        self.assertEqual(summary['checkpoint_roundtrips'], 1956)

    def test_all_32_fallback_offsets_exhaust_exactly_once(self):
        for i in range(32):
            case = self.cases[f'exhaust_offset_{i:02d}']
            self.assertEqual(case['action'], production.Action.SEARCH_EXHAUSTED.value)
            self.assertEqual({o['index'] for o in case['prefix']['observations']}, set(range(32)))
            self.assertEqual(len(case['prefix']['observations']), 32)
            self.assertEqual(case['prefix']['initial_credits'], 40)
            self.assertEqual(self.packet['contexts'][i]['offset'], i)

    def test_pass_at_every_last_credit_has_priority(self):
        for count in range(1, 33):
            case = self.cases[f'pass_last_credit_{count:02d}']
            self.assertEqual(case['action'], production.Action.AWAIT_ROOT_VERIFICATION.value)
            self.assertEqual(case['prefix']['initial_credits'], count)
            self.assertEqual(len(case['prefix']['observations']), count)
            self.assertTrue(case['prefix']['observations'][-1]['passed'])

    def test_full_grammar_precedes_resource_exhaustion(self):
        self.assertEqual(self.cases['credit_boundary_32']['action'], production.Action.SEARCH_EXHAUSTED.value)
        self.assertEqual(self.cases['credit_boundary_31']['action'], production.Action.RESOURCE_EXHAUSTED.value)

    def test_stopping_causes_remain_distinct_at_each_selected_boundary(self):
        for count in (0, 1, 3, 4, 5, 31):
            external = self.cases[f'external_at_{count}']
            safety = self.cases[f'safety_at_{count}']
            self.assertEqual(external['prefix']['observations'], safety['prefix']['observations'])
            self.assertEqual(external['action'], production.Action.EXTERNAL_STOP.value)
            self.assertEqual(safety['action'], production.Action.SAFETY_HALT.value)
            self.assertNotEqual(external['final_prefix_hash'], safety['final_prefix_hash'])

    def test_splitting_each_selected_trace_reconstructs_the_same_decisions(self):
        # Independently continue each prefix using a one-step reference transition,
        # then compare to complete production trace rows retained by the collector.
        for case in self.packet['cases']:
            context = self.packet['contexts'][case['context']]
            observations = case['prefix']['observations']
            for split in range(len(observations) + 1):
                p = ac.reference_replay(context, case['prefix']['initial_credits'], observations[:split])
                action, index = ac.reference_decision(context, p)
                row = case['checkpoint_trace'][split]
                self.assertEqual((row['action'], row['candidate_index']), (action, index))

    def test_reference_rejects_repeated_choice(self):
        context = self.packet['contexts'][0]
        first = self.cases['pass_last_credit_01']['prefix']['observations'][0]['index']
        with self.assertRaisesRegex(ValueError, 'next present-only choice'):
            ac.reference_replay(context, 40, [{'index': first, 'passed': False}] * 2)

    def test_reference_rejects_reordered_prefix(self):
        case = self.cases['pass_last_credit_04']
        with self.assertRaises(ValueError):
            ac.reference_replay(self.packet['contexts'][0], 4, list(reversed(case['prefix']['observations'])))

    def test_reference_rejects_continuing_after_pass(self):
        case = self.cases['pass_last_credit_01']
        with self.assertRaises(ValueError):
            ac.reference_replay(self.packet['contexts'][0], 40,
                                case['prefix']['observations'] + [{'index': 0, 'passed': False}])

    def test_reference_rejects_stopping_over_terminal_cause(self):
        for name in ('pass_last_credit_01', 'credit_boundary_0', 'credit_boundary_32'):
            case = self.cases[name]
            for stop in ('external', 'safety'):
                with self.subTest(name=name, stop=stop), self.assertRaises(ValueError):
                    ac.reference_replay(self.packet['contexts'][case['context']],
                        case['prefix']['initial_credits'], case['prefix']['observations'], stop)

    def test_invalid_natural_and_boolean_observation_types_are_rejected(self):
        context = self.packet['contexts'][0]
        for credit in (-1, True, 1.0, '1'):
            with self.assertRaises(ValueError):
                ac.reference_replay(context, credit, [])
        for observation in ({'index': True, 'passed': False}, {'index': 0, 'passed': 1},
                            {'index': 0, 'passed': False, 'future': True}):
            with self.assertRaises(ValueError):
                ac.reference_replay(context, 40, [observation])

    def test_packet_mutation_with_fresh_outer_hash_is_rejected(self):
        packet = json.loads(self.prepared.packet_bytes)
        packet['cases'][0]['action'] = 'resource_exhausted'
        raw = canonical(packet)
        with self.assertRaisesRegex(ValueError, 'reconstruction'):
            ac.verify_packet(raw, self.prepared, expected_sha256=ac.sha(raw))

    def test_packet_claim_widening_is_rejected(self):
        packet = json.loads(self.prepared.packet_bytes)
        packet['claims']['phase17_exit_closed'] = True
        raw = canonical(packet)
        with self.assertRaises(ValueError):
            ac.verify_packet(raw, self.prepared, expected_sha256=ac.sha(raw))

    def test_packet_keeps_scope_and_no_live_results(self):
        self.assertTrue(all(value is False for value in self.packet['claims'].values()))
        self.assertEqual(self.packet['scope'], ac.SCOPE)
        self.assertEqual(self.packet['summary']['fresh_workers'], 0)
        self.assertEqual(self.packet['summary']['fresh_live_challenges'], 0)

    def test_production_checkpoint_credit_identity_is_not_truncated(self):
        frozen = ac.offset_fixtures()[0]
        p32 = production.SearchPrefix(frozen, 32)
        p40 = production.SearchPrefix(frozen, 40)
        self.assertEqual(production.decide(p32).candidate_hash, production.decide(p40).candidate_hash)
        self.assertNotEqual(p32.prefix_hash, p40.prefix_hash)
        with self.assertRaises(ValueError):
            production.restore(production.checkpoint(p40), expected_prefix_hash=p32.prefix_hash)

    def test_forged_evaluator_hash_still_requires_original_external_anchor(self):
        prefix = ac._observe(production.SearchPrefix(ac.offset_fixtures()[0], 40), False)
        value = json.loads(production.checkpoint(prefix))
        value['observations'][0]['evaluation_hash'] = ac.digest('forged')
        with self.assertRaises(ValueError):
            production.restore(canonical(value), expected_prefix_hash=prefix.prefix_hash)

    def test_future_fields_are_not_accepted_as_present_input(self):
        view = ac.offset_fixtures()[0].view.to_json()
        for name in ('target_promotions', 'future_challenges', 'successful_route', 'terminal_package'):
            with self.assertRaises(ValueError):
                production.CurrentView.from_json({**view, name: 42})

    def test_synthetic_rank_profiles_include_negative_and_tied_values(self):
        scores = [row['base_score'] for c in self.packet['contexts'] for row in c['rows']]
        self.assertTrue(any(n < 0 for n in scores))
        self.assertTrue(any(len({row['base_score'] for row in c['rows']}) == 1 for c in self.packet['contexts']))

    def test_all_generated_context_keys_are_in_production_sort_order(self):
        for context in self.packet['contexts']:
            keys = [row['key'] for row in context['rows']]
            self.assertEqual(keys, sorted(set(keys)))
            self.assertEqual(len(keys), 32)
            self.assertTrue(all(len(row['ties']) == 5 for row in context['rows']))

    def test_generated_negative_controls_have_unique_expected_assertions(self):
        for label in proof.NEGATIVES:
            raw = proof.render_negative(self.prepared, label)
            line, column = proof.negative_location(raw)
            self.assertEqual(raw.decode().splitlines()[line - 1], '  decide')
            self.assertEqual(column, 2)
            self.assertIn(b'actual_rejection : wrongClaim = false', raw)


class EvidenceParserGuards(unittest.TestCase):
    def valid_audits(self):
        return ''.join("'" + name + "' depends on axioms: [propext, Classical.choice, Quot.sound]\n"
                       for name in proof.NAMES)

    def test_exact_audit_inventory_is_required(self):
        self.assertEqual(set(proof.parse_audits(self.valid_audits())), set(proof.NAMES))
        with self.assertRaises(ValueError):
            proof.parse_audits(self.valid_audits().split('\n', 1)[1])

    def test_reordered_audits_are_rejected(self):
        with self.assertRaises(ValueError):
            proof.parse_audits('\n'.join(reversed(self.valid_audits().splitlines())) + '\n')

    def test_additional_audit_output_is_rejected(self):
        with self.assertRaises(ValueError):
            proof.parse_audits(self.valid_audits() + 'warning: skipped\n')

    def test_unapproved_axioms_are_rejected(self):
        with self.assertRaises(ValueError):
            proof.parse_audits(self.valid_audits().replace('Quot.sound', 'sorryAx', 1))

    def test_duplicate_axioms_are_rejected(self):
        with self.assertRaises(ValueError):
            proof.parse_audits(self.valid_audits().replace('Quot.sound', 'propext', 1))

    def test_no_axiom_output_is_accepted(self):
        raw = ''.join("'" + n + "' does not depend on any axioms\n" for n in proof.NAMES)
        self.assertTrue(all(not xs for xs in proof.parse_audits(raw).values()))

    def test_wrong_negative_line_and_unrelated_failure_are_rejected(self):
        raw = b'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
        good = 'RepeatedChoice.lean:3:2: error: Tactic `decide` proved that the proposition\n  False\nis false\n'
        proof.validate_negative('RepeatedChoice', raw, good, '', 1)
        for invalid in (good.replace(':3:2:', ':1:2:'), good.replace('RepeatedChoice', 'Other'),
                        good + 'another error\n', 'unknown module prefix\n'):
            with self.assertRaises(ValueError):
                proof.validate_negative('RepeatedChoice', raw, invalid, '', 1)

    def test_timeout_success_or_stderr_cannot_be_negative_acceptance(self):
        raw = b'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
        good = 'RepeatedChoice.lean:3:2: error: Tactic `decide` proved that the proposition\n  False\nis false\n'
        for code, stderr in ((0, ''), (-9, ''), (1, 'import error')):
            with self.assertRaises(ValueError):
                proof.validate_negative('RepeatedChoice', raw, good, stderr, code)


if __name__ == '__main__':
    unittest.main()
