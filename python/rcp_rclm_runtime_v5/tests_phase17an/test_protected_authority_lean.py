"""AN parser/proof-source controls with explicitly synthetic development data.

No fixture here establishes OS protection, authenticated deployment or campaign
acceptance. The application separately captures actual broker and worker records.
"""
from copy import deepcopy
from pathlib import Path
import unittest

from rcp_rclm_runtime_v5.phase17 import protected_authority_lean as formal
from rcp_rclm_runtime_v5.phase17.resource_ledger import sha

ROOT = Path(__file__).resolve().parents[3]


def development_projection():
    from rcp_rclm_runtime_v5.phase17.authority_accounting import CATEGORIES
    commission = {key: sha(('synthetic-' + key).encode()) for key in formal.COMMISSION_FIELDS}
    commission.update(max_credits=2, max_intents=32)
    cursor = {'epoch': 1, 'serial': 4, 'head': sha(b'synthetic-cursor')}
    run = {'operation': 'run', 'nonce': sha(b'synthetic-run'), 'credits': 2}
    state = {'commission': commission['identity'], 'root': commission['root'],
             'current': cursor, 'pending': None, 'consumed': [sha(b'synthetic-earlier-read')]}
    pending = deepcopy(state)
    pending['pending'] = {'current': cursor, 'nonce': run['nonce'], 'credits': run['credits']}
    pending['consumed'].append(run['nonce'])
    return {'packet_sha256': sha(b'synthetic compiler-development projection, not native evidence'),
        'commission': commission, 'runtime': {key: commission[key] for key in formal.RUNTIME_FIELDS},
        'first_state': state, 'run_intent': run,
        'first_issued': {'authority_commission': commission['authority_commission'],
            'root': commission['root'], 'current': cursor, **run},
        'pending_state': pending,
        'reconcile_intent': {'operation': 'reconcile', 'nonce': sha(b'synthetic-reconcile'), 'credits': 0},
        'required_categories': list(CATEGORIES),
        'coverage': [{'category': category, 'observed': None, 'upper_bound': None, 'meter': ''}
                     for category in CATEGORIES], 'budget': 4480}


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.projection = development_projection()
        self.semantic = {key: value for key, value in self.projection.items() if key != 'packet_sha256'}

    def test_synthetic_projection_has_exact_explicit_scope(self):
        self.assertEqual(formal.validate_projection(self.semantic), self.semantic)
        raw = formal.render_selected(self.projection, ROOT)
        self.assertIn(b'theorem selected_no_promotion_admission', raw)
        self.assertIn(b'theorem cloned_broker_outside_guarantee', raw)
        self.assertNotIn(b'protected = true', raw)

    def test_controller_cannot_supply_paths_keys_anchor_or_evaluator(self):
        for field in ('source_root', 'private_key', 'anchor_path', 'evaluator', 'expected_cursor'):
            candidate = {**self.semantic['run_intent'], field: 'caller-selected'}
            with self.subTest(field=field), self.assertRaises(ValueError):
                formal._intent(candidate)

    def test_boolean_credit_or_serial_is_not_a_natural_number(self):
        for target, field in (('run_intent', 'credits'), ('first_state', 'serial')):
            changed = deepcopy(self.semantic)
            if target == 'first_state': changed[target]['current'][field] = True
            else: changed[target][field] = True
            with self.subTest(target=target), self.assertRaises(ValueError):
                formal.validate_projection(changed)

    def test_fixed_source_objective_evaluator_and_accounting_joins(self):
        for field in formal.RUNTIME_FIELDS:
            changed = deepcopy(self.semantic); changed['runtime'][field] = sha(b'substituted')
            with self.subTest(field=field), self.assertRaises(ValueError):
                formal.validate_projection(changed)

    def test_commissioned_credit_cap_zero_and_intent_capacity_are_enforced(self):
        for alteration in ('zero', 'over_cap', 'exhausted', 'boolean_cap'):
            changed = deepcopy(self.semantic)
            if alteration == 'zero': changed['run_intent']['credits'] = 0
            elif alteration == 'over_cap': changed['commission']['max_credits'] = 1
            elif alteration == 'exhausted': changed['commission']['max_intents'] = 1
            else: changed['commission']['max_credits'] = True
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                formal.validate_projection(changed)

    def test_actual_wire_mutation_must_match_broker_run(self):
        for field, wrong in (('nonce', sha(b'foreign nonce')), ('credits', 3),
                             ('authority_commission', sha(b'foreign authority')),
                             ('current', {'epoch': 1, 'serial': 3, 'head': sha(b'stale')})):
            changed = deepcopy(self.semantic); changed['first_issued'][field] = wrong
            with self.subTest(field=field), self.assertRaises(ValueError):
                formal.validate_projection(changed)

    def test_pending_must_retain_same_cursor_nonce_credits_and_consumption(self):
        for mutation in ('cursor', 'nonce', 'credits', 'consumed'):
            changed = deepcopy(self.semantic)
            if mutation == 'consumed': changed['pending_state']['consumed'].pop()
            elif mutation == 'cursor': changed['pending_state']['pending']['current']['serial'] += 1
            elif mutation == 'nonce': changed['pending_state']['pending']['nonce'] = sha(b'other')
            else: changed['pending_state']['pending']['credits'] += 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                formal.validate_projection(changed)

    def test_replayed_intent_or_already_pending_start_is_refused(self):
        for alteration in ('replayed', 'pending'):
            changed = deepcopy(self.semantic)
            if alteration == 'replayed': changed['first_state']['consumed'].append(changed['run_intent']['nonce'])
            else: changed['first_state']['pending'] = deepcopy(changed['pending_state']['pending'])
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                formal.validate_projection(changed)

    def test_reconcile_is_read_only_with_its_own_fresh_frontend_nonce(self):
        for field, wrong in (('operation', 'run'), ('credits', 1), ('nonce', self.semantic['run_intent']['nonce'])):
            changed = deepcopy(self.semantic); changed['reconcile_intent'][field] = wrong
            with self.subTest(field=field), self.assertRaises(ValueError):
                formal.validate_projection(changed)

    def test_required_categories_are_not_chosen_by_packet(self):
        changed = deepcopy(self.semantic)
        changed['required_categories'].pop(); changed['coverage'].pop()
        with self.assertRaisesRegex(ValueError, 'fixed accounting category inventory'):
            formal.validate_projection(changed)

    def test_duplicate_or_missing_coverage_category_is_refused(self):
        for alteration in ('duplicate', 'missing'):
            changed = deepcopy(self.semantic)
            if alteration == 'duplicate': changed['coverage'][1] = deepcopy(changed['coverage'][0])
            else: changed['coverage'].pop()
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                formal.validate_projection(changed)

    def test_unknown_cost_is_not_silently_rendered_as_observed_zero(self):
        raw = formal._coverage_literal(self.semantic['coverage'])
        self.assertIn('none, none', raw)
        self.assertNotIn('some 0', raw)

    def test_reference_capture_cannot_assert_complete_accounting(self):
        changed = deepcopy(self.semantic)
        for entry in changed['coverage']:
            entry.update(observed=0, upper_bound=0, meter=sha(b'self-declared-completeness'))
        with self.assertRaisesRegex(ValueError, 'reference packet cannot claim complete'):
            formal.validate_projection(changed)

    def test_projection_is_deep_copied_and_exact_fields_required(self):
        checked = formal.validate_projection(self.semantic)
        checked['first_state']['consumed'].append(sha(b'later modification'))
        self.assertNotEqual(checked, self.semantic)
        with self.assertRaises(ValueError):
            formal.validate_projection({**self.semantic, 'independently_protected': True})


class CompilerContractTests(unittest.TestCase):
    def audit_text(self):
        return ''.join("'" + name + "' does not depend on any axioms\n" for name in formal.NAMES)

    def test_complete_named_audit_inventory_is_required_in_order(self):
        text = self.audit_text(); rows = text.splitlines(keepends=True)
        self.assertEqual(list(formal.parse_audits(text)), list(formal.NAMES))
        for output in (''.join(rows[:-1]), ''.join([rows[1], rows[0], *rows[2:]]), text + rows[0]):
            with self.subTest(output=output[:40]), self.assertRaises(ValueError):
                formal.parse_audits(output)

    def test_unapproved_or_duplicate_axiom_dependencies_refused(self):
        for dependency in ('sorryAx', 'untrustedProof', 'Classical.choice, Classical.choice'):
            text = self.audit_text().replace('does not depend on any axioms',
                'depends on axioms: [' + dependency + ']', 1)
            with self.subTest(dependency=dependency), self.assertRaises(ValueError):
                formal.parse_audits(text)

    def test_every_control_has_distinct_exact_designated_rejection(self):
        self.assertEqual(len(set(formal.NEGATIVES)), len(formal.NEGATIVES))
        for label in formal.NEGATIVES:
            raw = formal.render_negative(label); line, col = formal.negative_location(raw)
            diagnostic = f'{label}.lean:{line}:{col}: error: Tactic `decide` proved that the proposition\n  False\nis false\n'
            with self.subTest(label=label):
                self.assertTrue(formal.validate_negative(label, raw, diagnostic, '', 1)['intended_rejection'])

    def test_arbitrary_failure_timeout_or_extra_diagnostic_cannot_pass(self):
        label = formal.NEGATIVES[0]; raw = formal.render_negative(label)
        line, col = formal.negative_location(raw)
        good = f'{label}.lean:{line}:{col}: error: Tactic `decide` proved that the proposition\n  False\nis false\n'
        for stdout, stderr, code in (('error: unknown module\n', '', 1), (good, 'crash', 1),
                                    (good, '', 0), (good, '', True), (good, '', -9),
                                    (good + 'warning: other\n', '', 1)):
            with self.subTest(code=code, stderr=stderr), self.assertRaises(ValueError):
                formal.validate_negative(label, raw, stdout, stderr, code)

    def test_changed_negative_final_assertion_is_refused(self):
        label = formal.NEGATIVES[0]; raw = formal.render_negative(label)
        with self.assertRaises(ValueError):
            formal.validate_negative(label, raw.replace(b'  decide\n', b'  trivial\n'), '', '', 1)


if __name__ == '__main__':
    unittest.main()
