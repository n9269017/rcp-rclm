"""Exact accounting inventory and fail-closed reference admission checks."""
import copy
import unittest

from rcp_rclm_runtime_v5.phase17 import authority_accounting as a
from rcp_rclm_runtime_v5.phase17.resource_ledger import ResourceError, sha


class AuthorityAccountingTests(unittest.TestCase):
    def all_observed(self):
        value = a.reference_coverage(budget=len(a.CATEGORIES) * 2)
        for row in value['coverage']:
            row.update(observed=1, upper_bound=2, meter=sha(row['category'].encode()))
        return value

    def test_reference_unknown_work_is_null_not_zero(self):
        value = a.reference_coverage()
        self.assertEqual([r['observed'] for r in value['coverage']], [None] * len(a.CATEGORIES))
        report = a.coverage_report(value)
        self.assertEqual(report['unknown_categories'], list(a.CATEGORIES))
        self.assertFalse(report['complete_resource_accounting'])

    def test_incomplete_totals_remain_unknown(self):
        report = a.coverage_report(a.reference_coverage())
        self.assertIsNone(report['total_observed_declared_units'])
        self.assertIsNone(report['total_bounded_declared_units'])
        self.assertEqual(report['known_observed_subtotal'], 0)

    def test_reference_admission_remains_nonpromoting(self):
        report = a.admission_report(a.reference_coverage())
        self.assertTrue(report['admitted'])
        self.assertFalse(report['promotion_authorized'])

    def test_unknown_categories_deny_promotion(self):
        report = a.admission_report(a.reference_coverage(), mode='promotion')
        self.assertFalse(report['admitted'])
        self.assertIn('accounting_categories_unobserved', report['denial_reasons'])

    def test_populated_declarations_do_not_establish_physical_completeness(self):
        report = a.coverage_report(self.all_observed())
        self.assertTrue(report['all_categories_observed_and_bounded'])
        self.assertFalse(report['declarations_are_physical_attestation'])
        self.assertFalse(report['complete_resource_accounting'])

    def test_populated_declarations_still_cannot_authorize_promotion(self):
        report = a.admission_report(self.all_observed(), mode='promotion')
        self.assertFalse(report['admitted'])
        self.assertIn('reference_backend_cannot_authorize_promotion', report['denial_reasons'])

    def test_omitted_category_rejected(self):
        value = a.reference_coverage(); value['coverage'].pop()
        with self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_duplicate_category_rejected(self):
        value = a.reference_coverage(); value['coverage'][1] = copy.deepcopy(value['coverage'][0])
        with self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_reordered_categories_rejected(self):
        value = a.reference_coverage(); value['coverage'].reverse()
        with self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_changed_required_inventory_rejected(self):
        value = a.reference_coverage(); value['required_categories'].pop()
        with self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_unknown_category_cannot_be_added(self):
        value = a.reference_coverage(); value['coverage'][0]['category'] = 'free_work'
        with self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_observation_requires_meter_and_bound(self):
        for field in ('meter', 'upper_bound'):
            value = self.all_observed(); value['coverage'][0][field] = '' if field == 'meter' else None
            with self.subTest(field=field), self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_bound_requires_meter(self):
        value = a.reference_coverage(); value['coverage'][0]['meter'] = ''
        with self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_observation_over_bound_rejected(self):
        value = self.all_observed(); value['coverage'][0]['observed'] = 3
        with self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_boolean_and_negative_amounts_rejected(self):
        for invalid in (True, False, -1, 1.0, '1', 2 ** 63):
            value = self.all_observed(); value['coverage'][0]['observed'] = invalid
            with self.subTest(value=invalid), self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_meter_without_any_known_amount_rejected(self):
        value = a.reference_coverage(); value['coverage'][1]['meter'] = sha(b'empty assertion')
        with self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_declared_bounds_over_budget_block_reference_admission(self):
        value = self.all_observed(); value['budget'] = 1
        report = a.admission_report(value)
        self.assertFalse(report['admitted'])
        self.assertIn('declared_bounds_exceed_budget', report['denial_reasons'])

    def test_unapproved_unit_or_extra_field_rejected(self):
        for extra in (False, True):
            value = a.reference_coverage()
            if extra: value['complete'] = True
            else: value['unit'] = 'unpriced_cpu_seconds'
            with self.subTest(extra=extra), self.assertRaises(ResourceError): a.validate_coverage(value)

    def test_unknown_admission_mode_rejected(self):
        with self.assertRaises(ResourceError): a.admission_report(a.reference_coverage(), mode='override')

    def test_validation_returns_independent_copy(self):
        value = a.reference_coverage(); checked = a.validate_coverage(value)
        checked['coverage'][0]['upper_bound'] = 0
        self.assertEqual(value['coverage'][0]['upper_bound'], 4480)
