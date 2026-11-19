"""Read-only native preflight and untrusted commissioning declaration checks."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import sys
import unittest

from rcp_rclm_runtime_v5.phase17 import commissioned_service_deployment as d
from rcp_rclm_runtime_v5.phase17 import resident_broker
from rcp_rclm_runtime_v5.phase17.resource_ledger import ResourceError, canonical, sha


class CommissionedServiceDeploymentTests(unittest.TestCase):
    def plan(self):
        return d.make_plan(source_root=resident_broker.SOURCE_ROOT, runtime_path=sys.executable)

    def test_reference_host_observation_is_read_only_and_nonattested(self):
        report = d.observe_host()
        self.assertFalse(report['host_configuration_changed'])
        self.assertFalse(report['physical_attestation'])
        self.assertEqual(report['process']['pid'], os.getpid())

    def test_uncommissioned_plan_fails_closed_with_concrete_missing_inputs(self):
        plan = self.plan()
        report = d.inspect_deployment(plan, expected_plan_sha256=sha(canonical(plan)))
        self.assertFalse(report['admitted'])
        self.assertIn('independent_currentness_backend_missing', report['denial_reasons'])
        self.assertIn('service_principal_not_commissioned', report['denial_reasons'])
        self.assertFalse(any(report['claims'].values()))

    def test_same_actual_process_cannot_fill_three_native_roles(self):
        plan = self.plan()
        observation = d.observe_host()['process']
        if observation['observed']:
            plan['principals'] = {role: copy.deepcopy(observation['identity']) for role in d.ROLES}
        report = d.inspect_deployment(plan, expected_plan_sha256=sha(canonical(plan)),
            service_pid=os.getpid(), controller_pid=os.getpid(), worker_pid=os.getpid())
        self.assertIn('three_distinct_native_principals_not_established', report['denial_reasons'])
        self.assertFalse(report['admitted'])

    def test_populated_provider_declaration_and_receipt_are_not_commissioning(self):
        plan = self.plan(); plan['external_commission_sha256'] = sha(b'assertion')
        plan['currentness_backend'] = {'provider': 'asserted witness',
            'identity_sha256': sha(b'asserted witness'), 'outside_rollback_domain': True}
        report = d.inspect_deployment(plan, expected_plan_sha256=sha(canonical(plan)),
            external_receipt={'independently_protected_deployment_established': True})
        self.assertIn('self_supplied_external_receipt_cannot_establish_commissioning', report['denial_reasons'])
        self.assertIn('external_currentness_and_launch_fencing_verifier_unimplemented', report['denial_reasons'])
        self.assertFalse(report['admitted'])

    def test_windows_plan_never_receives_linux_native_separation_credit(self):
        plan = d.make_plan(source_root=resident_broker.SOURCE_ROOT, runtime_path=sys.executable,
                           platform_name='win32')
        report = d.inspect_deployment(plan, expected_plan_sha256=sha(canonical(plan)),
                                     service_pid=os.getpid())
        self.assertFalse(report['admitted'])
        self.assertFalse(report['claims']['independently_protected_deployment_established'])

    def test_mutated_plan_pin_is_refused(self):
        plan = self.plan(); pin = sha(canonical(plan))
        plan['external_commission_sha256'] = sha(b'different')
        with self.assertRaises(ResourceError): d.validate_plan(plan, expected_plan_sha256=pin)

    def test_claim_escalation_is_refused_even_with_new_self_supplied_pin(self):
        plan = self.plan(); plan['claims']['independently_protected_deployment_established'] = True
        with self.assertRaises(ResourceError):
            d.validate_plan(plan, expected_plan_sha256=sha(canonical(plan)))

    def test_erasing_actual_worker_denials_is_refused(self):
        plan = self.plan(); plan['required_native_denials'].pop()
        with self.assertRaises(ResourceError):
            d.validate_plan(plan, expected_plan_sha256=sha(canonical(plan)))

    def test_retained_reference_report_verifies_without_fresh_host_inspection(self):
        report = d.reference_deployment_report(resident_broker.SOURCE_ROOT, sha(b'broker commission'))
        checked = d.verify_reference_deployment_report(report, source_root=resident_broker.SOURCE_ROOT)
        self.assertFalse(checked['admitted'])
        self.assertFalse(checked['independently_protected_deployment_established'])

    def test_retained_report_cannot_erase_currentness_failure(self):
        report = d.reference_deployment_report(resident_broker.SOURCE_ROOT, sha(b'broker commission'))
        report['admission']['denial_reasons'].remove('independent_currentness_backend_missing')
        with self.assertRaises(ResourceError):
            d.verify_reference_deployment_report(report, source_root=resident_broker.SOURCE_ROOT)

    def test_runbook_names_runtime_and_worker_token_requirements_without_host_changes(self):
        runbook = d.operator_runbook(self.plan())
        self.assertEqual(runbook['changes_performed'], [])
        self.assertIn('controller-writable checkout', runbook['windows_requirement'])
        self.assertIn('distinct scoped UIDs', runbook['linux_requirement'])


if __name__ == '__main__':
    unittest.main()
