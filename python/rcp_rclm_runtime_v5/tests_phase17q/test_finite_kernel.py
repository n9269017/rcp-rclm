"""Q adversarial bindings and proof-gate guards.

The physical fixture is freshly reconstructed once. Compiler-output fixtures
below test the parser/guard only; they are explicitly not actual Lean evidence.
"""
from __future__ import annotations
import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import re
import tempfile
import unittest
import importlib.util

from rcp_rclm_runtime_v5.phase17 import finite_kernel as fk
from rcp_rclm_runtime_v5.phase17 import finite_kernel_lean as fl
from rcp_rclm_runtime_v5.phase17 import finite_kernel_check as fc

ROOT = Path(__file__).resolve().parents[3]


class FinitePacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='r17q-tests-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.prepared = fk.prepare_finite_kernel(ROOT, Path(cls.temp.name) / 'packages')
        cls.raw = cls.prepared.packet_bytes
        cls.value = cls.prepared.packet

    def bad(self, mutate):
        p = copy.deepcopy(self.value)
        mutate(p)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            fk.PreparedFiniteKernel(fk.canonical(p))

    def test_same_candidate_and_historical_attribution(self):
        p = self.value
        self.assertEqual(p['bindings']['candidate_physical_hash'], fk.selected_binding()['candidate_package_hash'])
        self.assertEqual(p['staging']['transaction_id'], fk.TRANSACTION)
        self.assertFalse(p['staging']['root_acceptance_evaluated'])
        self.assertEqual(p['resource']['origin'], 'retained_phase17n_reference_profile')
        self.assertFalse(p['resource']['Q_execution_cost_measured'])

    def test_all_resource_dimensions_and_schedule(self):
        r = self.value['resource']
        self.assertEqual(r['spent'], [9, 144, 576, 576])
        self.assertEqual(r['charged_cost'], 4032)
        self.assertEqual(r['policy']['cost_limit'], 9920)
        self.assertEqual(len(r['charge_sequence']), 153)

    def test_protected_semantics_and_frontier_stay_distinct(self):
        p = self.value['protected_packet']
        self.assertEqual(len(p['task_contract']['tasks']), 11)
        self.assertEqual(len(p['information_positions']), 28)
        self.assertEqual(len(p['before']['row_selectors']), 260)
        self.assertEqual(p['before']['mass_minus_one_dictionary'], p['after']['mass_minus_one_dictionary'])
        self.assertEqual(len(p['joint_packet']['task_meanings']['before']['declared_ids']), 21)
        self.assertEqual(len(p['joint_packet']['task_meanings']['after']['declared_ids']), 22)

    def test_immutable_packet(self):
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            self.prepared.packet_bytes = b'{}'

    def test_projection_mutation_cannot_change_packet(self):
        p = self.prepared.packet
        p['claims']['promotion_authorized'] = True
        self.assertEqual(self.prepared.packet_bytes, self.raw)
        self.assertFalse(self.prepared.packet['claims']['promotion_authorized'])

    def test_cached_components_are_immutable_and_same_bound(self):
        self.assertEqual(self.prepared.protected().packet['bindings'], self.value['bindings'])
        self.assertEqual(self.prepared.joint().packet['bindings'], self.value['bindings'])
        x = self.prepared.protected().packet
        x['bindings']['candidate_physical_hash'] = '0' * 64
        self.assertEqual(self.prepared.protected().packet['bindings'], self.value['bindings'])

    def test_external_packet_anchor_required(self):
        with self.assertRaises(ValueError):
            fk.verify_packet_bytes(self.raw, self.prepared, expected_sha256='0' * 64)

    def test_rehashed_alternate_bytes_are_not_recomputed_evidence(self):
        raw = self.raw + b'\n'
        with self.assertRaises(ValueError):
            fk.verify_packet_bytes(raw, self.prepared, expected_sha256=fk.sha(raw))

    def test_noncanonical_json_rejected(self):
        with self.assertRaises(ValueError):
            fk.PreparedFiniteKernel(json.dumps(self.value, indent=2).encode())

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):
            fk.PreparedFiniteKernel(b'{"schema":"a","schema":"b"}')

    def test_mutable_or_empty_bytes_rejected(self):
        for raw in (b'', bytearray(self.raw), '{}'):
            with self.subTest(type=type(raw).__name__), self.assertRaises(ValueError):
                fk.PreparedFiniteKernel(raw)

    def test_oversized_packet_rejected(self):
        with self.assertRaises(ValueError):
            fk.PreparedFiniteKernel(b'x' * (fk.MAX_BYTES + 1))

    def test_missing_and_extra_top_fields_rejected(self):
        self.bad(lambda p: p.pop('staging'))
        self.bad(lambda p: p.update(accepted=True))

    def test_wrong_baseline_rejected(self):
        self.bad(lambda p: p.update(base_commit='0' * 40))

    def test_wrong_schema_or_policy_rejected(self):
        self.bad(lambda p: p.update(schema='other'))
        self.bad(lambda p: p.update(policy='other'))

    def test_every_authority_flag_rejected(self):
        for flag in fk.FALSE_CLAIMS:
            with self.subTest(flag=flag):
                self.bad(lambda p, key=flag: p['claims'].__setitem__(key, True))

    def test_numeric_false_cannot_substitute_for_boolean(self):
        self.bad(lambda p: p['claims'].__setitem__('promotion_authorized', 0))

    def test_live_or_worker_scope_escalation_rejected(self):
        self.bad(lambda p: p['scope'].__setitem__('fresh_workers', 1))
        self.bad(lambda p: p['scope'].__setitem__('domain', 'universal neural machine'))

    def test_unmeasured_costs_cannot_be_removed(self):
        self.bad(lambda p: p['unmeasured'].pop())

    def test_mixed_top_candidate_rejected(self):
        self.bad(lambda p: p['bindings'].__setitem__('candidate_physical_hash', '0' * 64))

    def test_changed_resource_candidate_rejected(self):
        self.bad(lambda p: p['resource']['binding'].__setitem__('candidate_package_hash', '0' * 64))

    def test_omitted_charge_rejected(self):
        self.bad(lambda p: p['resource']['charge_sequence'].pop(0))

    def test_inflated_budget_rejected(self):
        self.bad(lambda p: p['resource']['policy'].__setitem__('cost_limit', 1000000))

    def test_erased_resource_dimension_rejected(self):
        self.bad(lambda p: p['resource']['spent'].pop())

    def test_fabricated_current_measurement_rejected(self):
        self.bad(lambda p: p['resource'].__setitem__('Q_execution_cost_measured', True))

    def test_staging_outcome_cannot_be_accepted(self):
        self.bad(lambda p: p['staging'].__setitem__('outcome', 'accepted'))

    def test_same_bytes_unanchored_manifest_rejected(self):
        self.bad(lambda p: p['retained_sha256'].__setitem__(fk.P_EXECUTION, '0' * 64))

    def test_protected_probability_tamper_even_with_rehash(self):
        def mutate(p):
            p['protected_packet']['after']['mass_minus_one_dictionary'][0][0] += 1
            p['protected_packet_sha256'] = fk.sha(fk.canonical(p['protected_packet']))
        self.bad(mutate)

    def test_fixed_target_tamper_even_with_rehash(self):
        def mutate(p):
            p['protected_packet']['task_contract']['tasks'][0]['expected_tokens'][0] += 1
            p['protected_packet']['task_contract_sha256'] = fk.sha(fk.canonical(p['protected_packet']['task_contract']))
            p['protected_packet_sha256'] = fk.sha(fk.canonical(p['protected_packet']))
        self.bad(mutate)

    def test_mixed_protected_binding_rejected(self):
        def mutate(p):
            p['protected_packet']['bindings']['transcript_sha256'] = '0' * 64
            p['protected_packet_sha256'] = fk.sha(fk.canonical(p['protected_packet']))
        self.bad(mutate)

    def test_existing_physical_workspace_refused(self):
        with self.assertRaises(ValueError):
            fk.prepare_finite_kernel(ROOT, Path(self.temp.name) / 'packages')

    def test_repository_internal_physical_workspace_refused(self):
        with self.assertRaises(ValueError):
            fk.prepare_finite_kernel(ROOT, ROOT / 'q-must-not-be-created')
        self.assertFalse((ROOT / 'q-must-not-be-created').exists())

    def test_missing_retained_evidence_refused(self):
        with self.assertRaises(ValueError):
            fk.read_retained(Path(self.temp.name) / 'missing-root')


def _retained_mutation(name):
    def test(self):
        def mutate(p):
            raw = bytes.fromhex(p['retained_hex'][name]) + b'\n'
            p['retained_hex'][name] = raw.hex()
            # Even a mutually consistent replacement digest is not the fixed
            # external P/N input identity selected by this increment.
            p['retained_sha256'][name] = fk.sha(raw)
        self.bad(mutate)
    return test


for index, retained_name in enumerate(fk.RETAINED_PINS):
    setattr(FinitePacketTests, f'test_retained_anchor_{index:02d}_cannot_be_rehashed', _retained_mutation(retained_name))


class FormalGuardTests(unittest.TestCase):
    def setUp(self):
        self.sources = {n: ('controlled-parser-fixture:' + n).encode() for n in fl.LABELS}
        self.packet = 'a' * 64
        def command(stdout, code=0, label=None):
            out = {'returncode': code, 'stdout': stdout, 'stderr': '',
                   'stdout_sha256': fk.sha(stdout.encode()), 'stderr_sha256': fk.sha(b'')}
            if label:
                out.update(label=label, source_sha256=fk.sha(self.sources[label]))
            return out
        audits = ''.join("'" + n + "' does not depend on any axioms\n" for n in fl.NAMES)
        commands = [command('Lean (version 4.31.0, controlled parser fixture)\n'),
                    command(audits, label=fl.LABELS[0])]
        commands += [command('error: Tactic `decide` proved that the proposition\nFalse\nis false\n' + audits, 1, n)
                     for n in fl.LABELS[1:]]
        self.result = {'schema': 'rcp-rclm.phase17q.finite-observation-lean.v1',
                       'status': 'passed', 'packet_sha256': self.packet,
                       'source_sha256': {n: fk.sha(b) for n, b in self.sources.items()},
                       'negative_controls_rejected': list(fl.LABELS[1:]), 'new_named_audits': len(fl.NAMES),
                       'finite_observation_kernel_checked': True, 'finite_observation_step_checked': True,
                       'claims': {k: False for k in fk.FALSE_CLAIMS}, 'commands': commands,
                       'theorem_axioms': {n: [] for n in fl.NAMES},
                       'executable_sha256': {'fixture/lean': '1' * 64, 'fixture/lake': '2' * 64, 'fixture/git': '3' * 64},
                       'trusted_import_cache_assumption': True, 'physical_mapping_remains_external': True,
                       'finite_model_acceptance_is_not_physical_root_acceptance': True,
                       'old_proof_campaigns_rerun': False}

    def bad(self, mutate):
        x = copy.deepcopy(self.result)
        mutate(x)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            fc.validate_result(x, self.sources, self.packet)

    def test_controlled_log_fixture_matches_exact_contract(self):
        fc.validate_result(self.result, self.sources, self.packet)

    def test_preparation_cannot_be_formal_success(self):
        self.bad(lambda r: r.update(status='not_requested'))

    def test_wrong_packet_and_source_rejected(self):
        self.bad(lambda r: r.update(packet_sha256='0' * 64))
        self.bad(lambda r: r['source_sha256'].__setitem__(fl.LABELS[0], '0' * 64))

    def test_missing_negative_control_rejected(self):
        self.bad(lambda r: r['negative_controls_rejected'].pop())

    def test_wrong_command_label_rejected(self):
        self.bad(lambda r: r['commands'][2].update(label='other'))

    def test_wrong_positive_returncode_rejected(self):
        self.bad(lambda r: r['commands'][1].update(returncode=1))

    def test_log_hash_tamper_rejected(self):
        self.bad(lambda r: r['commands'][1].update(stdout='altered'))

    def test_accepted_negative_rejected(self):
        self.bad(lambda r: r['commands'][2].update(returncode=0))

    def test_timeout_is_not_negative_rejection(self):
        self.bad(lambda r: r['commands'][2].update(returncode=-999))

    def test_unrelated_error_is_not_negative_rejection(self):
        def mutate(r):
            cmd = r['commands'][2]
            cmd['stdout'] += "error: unknown identifier 'missing'\n"
            cmd['stdout_sha256'] = fk.sha(cmd['stdout'].encode())
        self.bad(mutate)

    def test_type_mismatch_is_not_negative_rejection(self):
        def mutate(r):
            cmd = r['commands'][2]
            cmd['stdout'] = cmd['stdout'].replace('is false\n', 'is false\nerror: type mismatch\n')
            cmd['stdout_sha256'] = fk.sha(cmd['stdout'].encode())
        self.bad(mutate)

    def test_pass_with_failure_record_rejected(self):
        self.bad(lambda r: r.update(failure={'reason': 'still broken'}))

    def test_wrong_formal_schema_rejected(self):
        self.bad(lambda r: r.update(schema='other'))

    def test_numeric_false_claim_rejected(self):
        self.bad(lambda r: r['claims'].__setitem__('promotion_authorized', 0))

    def test_omitted_external_mapping_scope_rejected(self):
        self.bad(lambda r: r.pop('physical_mapping_remains_external'))

    def test_unapproved_axiom_rejected(self):
        output = ''.join("'" + n + "' depends on axioms: [sorryAx]\n" for n in fl.NAMES)
        with self.assertRaises(ValueError):
            fc.parse_audits(output)

    def test_extra_or_missing_audit_rejected(self):
        output = self.result['commands'][1]['stdout']
        with self.assertRaises(ValueError):
            fc.parse_audits(output + 'unexpected output\n')
        with self.assertRaises(ValueError):
            fc.parse_audits(output.split('\n', 1)[1])

    def test_report_cannot_claim_promotion(self):
        self.bad(lambda r: r['claims'].__setitem__('promotion_authorized', True))

    def test_finite_step_proof_flag_required(self):
        self.bad(lambda r: r.update(finite_observation_step_checked=False))


class TemplateContractTests(unittest.TestCase):
    def test_all_seven_templates_match_reviewed_pins(self):
        self.assertEqual(len(fl.template_snapshot(ROOT)), 7)

    def test_selected_audit_and_control_inventory(self):
        self.assertEqual(len(fl.NAMES), 14)
        self.assertIn('Phase17Finite.selected_learned_accepted', fl.NAMES)
        self.assertEqual(len(fl.LABELS), 9)
        self.assertEqual(len(set(fl.LABELS)), 9)

    def test_no_forbidden_template_tokens(self):
        self.assertIsNone(re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', fl.template(ROOT)))


class GatePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('q_gate_test', ROOT / 'scripts/run_phase17_finite_kernel_gate.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_lexical_parent_path_cannot_enter_source_checkout(self):
        name = 'q-path-must-not-be-created'
        path = ROOT.parent / 'nonexistent-q-parent' / '..' / ROOT.name / name
        with self.assertRaises(ValueError):
            self.module.main(['--output', str(path), '--test-fixture'])
        self.assertFalse((ROOT / name).exists())

    def test_execution_source_inventory_excludes_status_and_manifest(self):
        paths = self.module.source_paths()
        self.assertIn('python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/finite_kernel_check.py', paths)
        self.assertNotIn('SHA256SUMS.txt', paths)
        self.assertNotIn('docs/executable_core_v5/PHASE_17_LOCAL_VALIDATION.json', paths)
