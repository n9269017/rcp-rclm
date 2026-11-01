from __future__ import annotations
import copy
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.controller import ControlError
from rcp_rclm_runtime_v5.phase17 import materialized as m
from rcp_rclm_runtime_v5.phase17 import successor_evidence as s
from rcp_rclm_runtime_v5.phase17 import successor_lean as l
from rcp_rclm_runtime_v5.phase17 import challenge_protocol as c
from rcp_rclm_runtime_v5.phase17.objectives import select_bootstrap_objective, freeze_bootstrap_objective

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / 'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
CAPTURE = ROOT / 'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
CLOSURE = ROOT / 'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
FIXTURE = ROOT / 'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json'
ANCHOR = '369c30c469090fa357633aca596cb0c7ad3de31f2ecf16ca78e7699e79c79e6e'


class SuccessorEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='r17f-tests-')
        cls.root = Path(cls.temp.name).resolve(strict=True)
        cls.parent = reopen_phase16(capture_archive=CAPTURE, closure_archive=CLOSURE, phase15_bundle=BUNDLE)
        cls.raw = FIXTURE.read_bytes()
        cls.old = m.materialize_package(cls.root/'old', cls.parent, BUNDLE)
        cls.new = m.materialize_package(cls.root/'new', cls.parent, BUNDLE,
                                       transcript=cls.raw, expected_transcript_hash=ANCHOR)
        cls.prepared = s.prepare_successor(cls.old, cls.new, cls.parent, bundle=BUNDLE, capture=CAPTURE,
                                          transcript=cls.raw, expected_transcript_hash=ANCHOR)
        cls.bridge = (ROOT/l.BRIDGE_PATH).read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def prepare(self, **kw):
        values = dict(bundle=BUNDLE, capture=CAPTURE, transcript=self.raw, expected_transcript_hash=ANCHOR)
        values.update(kw)
        return s.prepare_successor(self.old, self.new, self.parent, **values)

    def test_real_archive_candidate_is_checked(self):
        p = self.prepared.packet
        self.assertEqual(len(p['capabilities_before']), 21)
        self.assertEqual(len(p['capabilities_after']), 22)
        self.assertEqual(p['candidate_evaluation']['probe_count'], 8)

    def test_173_protected_files_measured(self):
        p = self.prepared.packet['projection']
        self.assertEqual(len(p['protected_before']), 173)
        self.assertEqual(p['protected_before'], p['protected_after'])
        self.assertEqual(sum(r['path'].startswith('base/') for r in p['protected_before']), 164)

    def test_registry_is_exactly_eight_to_nine(self):
        p = self.prepared.packet
        self.assertEqual(len(p['programs_before']), 8)
        self.assertEqual(len(p['programs_after']), 9)
        self.assertNotIn(p['bindings']['program_hash'], p['programs_before'])

    def test_no_automatic_recursive_label_addition(self):
        p = self.prepared.packet
        self.assertEqual(p['recursive_before'], p['recursive_after'])
        self.assertEqual(len(p['recursive_before']), 19)
        self.assertIs(p['strict_recursive_expansion_claimed'], False)

    def test_three_scoped_probes_not_nineteen_certified_abilities(self):
        rows = self.prepared.packet['recursive_support']
        self.assertEqual(len(rows), 19)
        self.assertEqual(sum(r['status'] == 'selected_profile_probe_passed' for r in rows), 3)
        self.assertTrue(all(r['full_task_semantics_recertified'] is False for r in rows))

    def test_all_root_premises_accounted(self):
        rows = self.prepared.packet['root_obligation_ledger']
        self.assertEqual(len(rows), 35)
        self.assertEqual(len({(r['layer'], r['field']) for r in rows}), 35)
        self.assertTrue(all(r['complete_root_premise_discharged'] is False for r in rows))

    def test_catalog_matches_actual_immutable_root_structures(self):
        entries = [
            ('lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Certificates.lean', 'StepObligations', s.BASE_FIELDS),
            ('lean/rcp_rclm_formal_core_v3/RcpRclmFormalCoreV3/Learned/Kernel.lean', 'SpecificObligations', s.LEARNED_FIELDS),
            ('lean/rcp_rclm_formal_core_v4/RcpRclmFormalCoreV4/Autonomous/Kernel.lean', 'SpecificObligations', s.AUTONOMOUS_FIELDS),
        ]
        for rel, structure, expected in entries:
            text = (ROOT/rel).read_text().split('structure '+structure, 1)[1].split('where', 1)[1].split('/--', 1)[0]
            observed = re.findall(r'^  (\w+)\s*:', text, flags=re.M)
            self.assertEqual(tuple(observed), expected)

    def test_packet_has_no_authorization(self):
        p = self.prepared.packet
        self.assertEqual(p['claims'], {k: False for k in s.FALSE_CLAIMS})
        self.assertNotIn('accepted', p)
        self.assertNotIn('successor_state_hash', p)

    def test_packet_access_detached(self):
        x = self.prepared.packet
        x['claims']['promotion_authorized'] = True
        self.assertIs(self.prepared.packet['claims']['promotion_authorized'], False)

    def test_exact_projection_not_active_rollback(self):
        p = self.prepared.packet['projection']
        self.assertIs(p['exact_projection_recovery'], True)
        self.assertIs(p['active_store_rollback_performed'], False)

    def test_anchor_tamper_rejected(self):
        with self.assertRaises(ControlError):
            self.prepare(expected_transcript_hash='0'*64)

    def test_exhaustion_never_authorizes_candidate_packet(self):
        path = ROOT/'artifacts/development/phase17c/assistant-live-turn/sealed_transcript.json'
        raw = path.read_bytes()
        with self.assertRaisesRegex(ControlError, 'no passing candidate'):
            self.prepare(transcript=raw, expected_transcript_hash=m.sha(raw))

    def test_resource_stop_never_authorizes_candidate_packet(self):
        obj = select_bootstrap_objective(self.parent, turn_index=0, public_nonce_hash='2'*64)
        freeze = freeze_bootstrap_objective(obj, self.parent, turn_index=0, public_nonce_hash='2'*64)
        session = c.EvaluatorSession(self.parent)
        with patch.object(c.secrets, 'token_bytes', return_value=b'X'*32):
            session.handle({'protocol': c.PROTOCOL, 'op': 'open', 'objective': obj.to_json(),
                            'freeze': freeze, 'candidate_credits': 0})
        session.handle({'protocol': c.PROTOCOL, 'op': 'seal', 'terminal_action': 'resource_exhausted'})
        raw = c.transcript_bytes(session.events)
        with self.assertRaisesRegex(ControlError, 'no passing candidate'):
            self.prepare(transcript=raw, expected_transcript_hash=m.sha(raw))

    def test_altered_tensor_rejected(self):
        path = next((self.new.root/'base/model/tensors').glob('*.bin'))
        original = path.read_bytes()
        try:
            path.write_bytes(bytes([original[0]^1])+original[1:])
            with self.assertRaises(ControlError): self.prepare()
        finally: path.write_bytes(original)

    def test_extra_physical_file_rejected(self):
        path = self.new.root/'unexpected.txt'
        try:
            path.write_bytes(b'not part of candidate')
            with self.assertRaises(ControlError): self.prepare()
        finally: path.unlink()

    def test_changed_registry_rejected(self):
        path = self.new.root/'registry/manifest.json'; original = path.read_bytes()
        obj = json.loads(original);obj['candidate_active']=True
        try:
            path.write_bytes(canonical(obj))
            with self.assertRaises(ControlError): self.prepare()
        finally: path.write_bytes(original)

    def test_receipt_substitution_rejected(self):
        obj = json.loads(self.old.manifest_bytes);obj['kind']='forged'
        altered = dataclasses.replace(self.old, manifest_bytes=canonical(obj))
        with self.assertRaisesRegex(ControlError, 'receipt substitution'):
            s.prepare_successor(altered,self.new,self.parent,bundle=BUNDLE,capture=CAPTURE,
                                transcript=self.raw,expected_transcript_hash=ANCHOR)

    def test_packet_rehash_cannot_replace_recomputation(self):
        obj = self.prepared.packet;obj['search_budget']=1
        obj['claims']['promotion_authorized']=True
        raw=canonical(obj)
        with self.assertRaises(ControlError):
            s.verify_packet_bytes(raw,self.prepared,expected_sha256=m.sha(raw))

    def test_packet_whitespace_rejected(self):
        raw=self.prepared.packet_bytes+b'\n'
        with self.assertRaises(ControlError):s.verify_packet_bytes(raw,self.prepared,expected_sha256=m.sha(raw))

    def test_valid_packet_hash_and_bytes(self):
        raw=self.prepared.packet_bytes
        s.verify_packet_bytes(raw,self.prepared,expected_sha256=m.sha(raw))

    def test_render_has_no_placeholder_or_native_proof(self):
        raw=l.render(self.prepared,self.bridge)
        self.assertFalse(re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b',raw))
        self.assertIn(b'constructor <;> decide',raw)

    def test_root_template_pin_cannot_be_substituted(self):
        with self.assertRaises(ControlError):l.render(self.prepared,self.bridge+b'\n')

    def test_crlf_template_is_portable(self):
        self.assertEqual(l.render(self.prepared,self.bridge),l.render(self.prepared,self.bridge.replace(b'\n',b'\r\n')))

    def test_negative_control_does_not_mutate_packet(self):
        before=self.prepared.packet_bytes
        bad=l.render(self.prepared,self.bridge,negative_control=True)
        good=l.render(self.prepared,self.bridge)
        self.assertNotEqual(bad,good);self.assertEqual(self.prepared.packet_bytes,before)

    def test_render_contains_128_full_grammar_cases(self):
        raw=l.render(self.prepared,self.bridge)
        segment=raw.split(b'def selectedCases',1)[1].split(b'theorem selected_dsl_regression',1)[0]
        self.assertEqual(segment.count(b'{ family := '),128)

    def test_string_code_injection_escaped(self):
        self.assertEqual(l.string('x"\\n'),json.dumps('x"\\n'))
        with self.assertRaises(ControlError):l.string('x\n#print axioms x')

    def test_integer_boolean_rejected(self):
        with self.assertRaises(ControlError):l.integer(True)

    def test_false_integer_claim_rejected(self):
        obj=self.prepared.packet;obj['claims']['root_transition_verified']=0
        with self.assertRaises(ControlError):l.render(s.PreparedSuccessor(canonical(obj)),self.bridge)

    def test_different_named_theorem_rejected(self):
        text='\n'.join("'"+name+"' does not depend on any axioms" for name in l.NAMES)
        self.assertEqual(set(l.parse_audits(text)),set(l.NAMES))
        wrapped='\r\n'.join("'"+name+"' depends on axioms: [propext,\r\nQuot.sound]" for name in l.NAMES)
        self.assertTrue(all(values==['propext','Quot.sound'] for values in l.parse_audits(wrapped).values()))
        with self.assertRaises(ControlError):l.parse_audits(text.replace('selected_facts','unrelated'))

    def test_unapproved_axioms_rejected(self):
        text='\n'.join("'"+name+"' depends on axioms: [sorryAx]" for name in l.NAMES)
        with self.assertRaises(ControlError):l.parse_audits(text)

    def test_extra_audit_output_rejected(self):
        text='\n'.join("'"+name+"' does not depend on any axioms" for name in l.NAMES)
        with self.assertRaises(ControlError):l.parse_audits(text+'\nwarning')

    def test_lean_gate_mock_checks_negative_before_positive(self):
        result,calls=self.mock_gate()
        self.assertEqual(result['status'],'passed')
        self.assertEqual(len(calls),3)
        self.assertTrue(calls[1][-1].endswith('Negative.lean'))
        self.assertTrue(calls[2][-1].endswith('Certificate.lean'))
        self.assertTrue(all(v is False for v in result['claims'].values()))

    def mock_gate(self, mode='ok'):
        calls=[]
        with tempfile.TemporaryDirectory(prefix='r17f-mock-') as folder:
            root=Path(folder).resolve();tool=root/'tool';(tool/'bin').mkdir(parents=True)
            suffix='.exe' if os.name=='nt' else ''
            for name in ('lean','lake','git'):(tool/'bin'/(name+suffix)).write_bytes(b'explicit mocked tool')
            def process(argv,*args,**kw):
                calls.append(argv)
                if argv[-1]=='--version':return dict(returncode=0,stderr='',stdout='Lean (version 4.31.0, mock)')
                if argv[-1].endswith('Negative.lean'):
                    return dict(returncode=0 if mode=='accepts_false' else (-999 if mode=='timeout' else 1),
                                stderr='',stdout='error: tactic decide failed; proposition is false')
                if mode=='reject_positive':return dict(returncode=1,stderr='error',stdout='')
                return dict(returncode=0,stderr='',stdout='\n'.join("'"+n+"' does not depend on any axioms" for n in l.NAMES))
            with patch.object(l.gate,'root_source_fingerprint',return_value={'pins':1}), \
                 patch.object(l.gate,'_dependency_state',return_value={'mathlib':'pinned'}), \
                 patch.object(l.gate,'resolve_toolchain',return_value=tool), \
                 patch.object(l.gate,'_lean_environment',return_value=({'PATH':str(tool/'bin')},tool/'bin'/('git'+suffix))), \
                 patch.object(l.gate,'_process',side_effect=process):
                result=l._check_finite_successor(self.prepared,source_root=ROOT,lean_workspace=root)
        return result,calls

    def test_compiler_accepting_false_cannot_pass(self):
        result,calls=self.mock_gate('accepts_false');self.assertEqual(result['status'],'rejected');self.assertEqual(len(calls),2)

    def test_negative_timeout_is_not_rejection_proof(self):
        result,_=self.mock_gate('timeout');self.assertFalse(result['negative_certificate_rejected'])

    def test_positive_failure_not_hidden(self):
        result,_=self.mock_gate('reject_positive');self.assertEqual(result['status'],'rejected')
        self.assertFalse(result['finite_successor_facts_verified'])

    def test_missing_dependencies_never_pass(self):
        with patch.object(l.gate,'root_source_fingerprint',return_value={}), \
             patch.object(l.gate,'_dependency_state',side_effect=ControlError('not installed')):
            result=l._check_finite_successor(self.prepared,source_root=ROOT,lean_workspace=ROOT)
        self.assertEqual(result['status'],'blocked');self.assertEqual(result['commands'],[])

if __name__=='__main__':unittest.main(verbosity=2)
