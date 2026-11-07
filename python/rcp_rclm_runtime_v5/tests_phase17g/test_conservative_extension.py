from __future__ import annotations
import copy
import dataclasses
import hashlib
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.controller import ControlError
from rcp_rclm_runtime_v5.phase17 import materialized as m
from rcp_rclm_runtime_v5.phase17 import conservative_extension as c
from rcp_rclm_runtime_v5.phase17 import conservative_lean as l
from rcp_rclm_runtime_v5.phase17.successor_evidence import FALSE_CLAIMS

ROOT=Path(__file__).resolve().parents[3]
BUNDLE=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
CAPTURE=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
CLOSURE=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
FIXTURE=ROOT/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json'
ANCHOR='369c30c469090fa357633aca596cb0c7ad3de31f2ecf16ca78e7699e79c79e6e'

class ConservativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='r17g-test-');cls.root=Path(cls.temp.name).resolve(strict=True)
        cls.parent=reopen_phase16(capture_archive=CAPTURE,closure_archive=CLOSURE,phase15_bundle=BUNDLE)
        cls.raw=FIXTURE.read_bytes()
        cls.before=m.materialize_package(cls.root/'p',cls.parent,BUNDLE)
        cls.after=m.materialize_package(cls.root/'c',cls.parent,BUNDLE,transcript=cls.raw,expected_transcript_hash=ANCHOR)
        cls.prepared=cls.prepare()
        cls.pre_files=m.snapshot(cls.before.root);cls.post_files=m.snapshot(cls.after.root)
        cls.old=c.registry_from_files(cls.pre_files);cls.new=c.registry_from_files(cls.post_files)
        cls.key=cls.prepared.packet['new_key'];cls.template=(ROOT/l.BRIDGE_PATH).read_bytes()

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    @classmethod
    def prepare(cls,**overrides):
        kw=dict(bundle=BUNDLE,capture=CAPTURE,transcript=cls.raw,expected_transcript_hash=ANCHOR);kw.update(overrides)
        return c.prepare_conservative(cls.before,cls.after,cls.parent,**kw)

    def test_actual_physical_fixture(self):
        p=self.prepared.packet
        self.assertEqual(p['protected_file_count'],173)
        self.assertEqual(len(p['registry_before']),8);self.assertEqual(len(p['registry_after']),9)
        self.assertTrue(p['physical_inverse_exact'])

    def test_48_old_program_execution_checks(self):
        checks=self.prepared.packet['inherited_execution_checks'];self.assertEqual(len(checks),48)
        for row in checks:self.assertEqual(row['before'],row['after']);self.assertEqual(row['before'],row['reference'])

    def test_eight_actual_candidate_dispatches(self):
        checks=self.prepared.packet['candidate_execution_checks'];self.assertEqual(len(checks),8)
        for row in checks:self.assertEqual(row['actual'],row['expected'])

    def test_protected_image_real_bytes(self):
        p=self.prepared.packet;names=tuple(r['path'] for r in p['protected_files'])
        image=c.protected_image(self.pre_files,names)
        self.assertEqual(m.sha(image),p['protected_image_sha256']);self.assertEqual(len(image),p['protected_image_bytes'])
        self.assertGreater(len(image),27_000_000)

    def test_extension_inverse(self):self.assertEqual(self.new.retract(self.key),self.old)

    def test_extend_rejects_shadow(self):
        with self.assertRaises(ControlError):self.old.extend(*self.old.entries[0])

    def test_retract_absent(self):
        with self.assertRaises(ControlError):self.old.retract(self.key)

    def test_unknown_program_not_identity_fallback(self):
        with self.assertRaises(ControlError):self.old.execute(self.key,[1,2,3,4])

    def test_wrong_vector_length(self):
        with self.assertRaises(ControlError):self.old.execute(self.old.entries[0][0],[1,2,3])

    def test_boolean_vector(self):
        with self.assertRaises(ControlError):self.old.execute(self.old.entries[0][0],[True,2,3,4])

    def test_out_of_range_vector(self):
        with self.assertRaises(ControlError):self.old.execute(self.old.entries[0][0],[65,2,3,4])

    def test_duplicate_programs_reject(self):
        with self.assertRaises(ControlError):c.RegistryImage(self.old.entries+(self.old.entries[0],))

    def test_manifest_order_is_explicit_not_directory_order(self):
        reordered=c.RegistryImage(tuple(reversed(self.old.entries)))
        self.assertNotEqual(reordered,self.old)
        self.assertEqual(c.registry_from_files(dict(reversed(list(self.pre_files.items())))),self.old)

    def test_mutable_buffer_reject(self):
        key,raw=self.old.entries[0]
        with self.assertRaises(ControlError):c.RegistryImage(((key,bytearray(raw)),))

    def test_noncanonical_json_reject(self):
        key,raw=self.old.entries[0]
        with self.assertRaises(ControlError):c.RegistryImage(((key,raw+b'\n'),))

    def test_wrong_program_hash_reject(self):
        _,raw=self.old.entries[0]
        with self.assertRaises(ControlError):c.RegistryImage((('0'*64,raw),))

    def test_missing_physical_registry_file_reject(self):
        data=dict(self.pre_files);data.pop('registry/programs/'+self.old.entries[0][0]+'.json')
        with self.assertRaises(ControlError):c.registry_from_files(data)

    def test_extra_physical_registry_file_reject(self):
        data=dict(self.pre_files);data['registry/programs/'+self.key+'.json']=self.new.lookup(self.key)
        with self.assertRaises(ControlError):c.registry_from_files(data)

    def test_packet_detached(self):
        p=self.prepared.packet;p['claims']['root_transition_verified']=True
        self.assertIs(self.prepared.packet['claims']['root_transition_verified'],False)

    def test_no_recursive_recertification_by_labels(self):
        p=self.prepared.packet;self.assertEqual(len(p['recursive_task_ids']),19)
        self.assertEqual(p['operational_recursive_tasks_recertified'],[])
        self.assertTrue(all(p['claims'][k] is False for k in FALSE_CLAIMS))

    def test_inverse_uses_candidate_not_old_tensors(self):
        metadata=tuple((p,self.pre_files[p]) for p in sorted((m.MANIFEST,'registry/manifest.json')))
        restored=c.extract_predecessor(self.post_files,added_key=self.key,metadata=metadata)
        self.assertEqual(restored,self.pre_files)
        data=dict(self.post_files);name=next(n for n in data if n.startswith('base/') and data[n])
        data[name]=data[name]+b'x'
        restored=c.extract_predecessor(data,added_key=self.key,metadata=metadata)
        self.assertNotEqual(restored,self.pre_files)
        self.assertEqual(restored[name],data[name])

    def test_inverse_rejects_arbitrary_undo_files(self):
        with self.assertRaises(ControlError):c.extract_predecessor(self.post_files,added_key=self.key,metadata=(('base/foo',b''),(m.MANIFEST,b'')))

    def test_framing_is_unambiguous(self):
        self.assertNotEqual(c.protected_image({'a':b'bc'},('a',)),c.protected_image({'ab':b'c'},('ab',)))

    def test_framing_rejects_reordered_names(self):
        with self.assertRaises(ControlError):c.protected_image({'a':b'','b':b''},('b','a'))

    def test_wrong_external_transcript_anchor(self):
        with self.assertRaises(ControlError):self.prepare(expected_transcript_hash='0'*64)

    def test_physical_tamper_before_preparation(self):
        path=self.after.root/('registry/programs/'+self.key+'.json');raw=path.read_bytes()
        try:
            path.write_bytes(raw+b' ')
            with self.assertRaises(ControlError):self.prepare()
        finally:path.write_bytes(raw)

    def test_six_exact_audit_targets(self):
        source=l.render(self.prepared,self.template)
        self.assertEqual(source.count(b'#print axioms '),6)
        self.assertIn(b'RcpRclmFormalCoreV2.RCP.StepObligations',source)
        self.assertIn(b'theorem dispatch_retained',source)

    def test_no_placeholder_in_generated_source(self):
        raw=l.render(self.prepared,self.template)
        self.assertIsNone(re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b',raw))

    def test_negative_shadows_key_without_mutating_packet(self):
        original=self.prepared.packet_bytes
        good=l.render(self.prepared,self.template);bad=l.render(self.prepared,self.template,negative=True)
        self.assertNotEqual(good,bad);self.assertEqual(self.prepared.packet_bytes,original)
        self.assertIn(('key := "'+self.old.entries[0][0]+'"').encode(),bad)

    def test_template_pin(self):
        with self.assertRaises(ControlError):l.render(self.prepared,self.template+b'--changed\n')

    def test_crlf_template(self):
        self.assertEqual(l.render(self.prepared,self.template),l.render(self.prepared,self.template.replace(b'\n',b'\r\n')))

    def test_injection_literal(self):
        self.assertEqual(l.literal('"\\'), '"\\"\\\\"')
        with self.assertRaises(ControlError):l.literal('line\nbreak')

    def test_claim_escalation(self):
        p=self.prepared.packet;p['claims']['root_transition_verified']=True
        with self.assertRaises(ControlError):l.render(c.PreparedConservative(canonical(p)),self.template)

    def test_mapping_substitution(self):
        p=self.prepared.packet;p['logical_append_order']=list(reversed(p['logical_append_order']))
        with self.assertRaises(ControlError):l.render(c.PreparedConservative(canonical(p)),self.template)

    def test_boolean_credits(self):
        p=self.prepared.packet;p['search_used']=True
        with self.assertRaises(ControlError):l.render(c.PreparedConservative(canonical(p)),self.template)

    def test_parser_all_six(self):
        output=''.join("'"+n+"' depends on axioms: [propext, Classical.choice, Quot.sound]\n" for n in l.NAMES)
        self.assertEqual(set(l.parse_audits(output)),set(l.NAMES))

    def test_parser_rejects_sorry(self):
        output=''.join("'"+n+"' depends on axioms: [sorryAx]\n" for n in l.NAMES)
        with self.assertRaises(ControlError):l.parse_audits(output)

    def test_parser_rejects_unrelated_theorem(self):
        with self.assertRaises(ControlError):l.parse_audits("'other' does not depend on any axioms\n")

    def test_parser_rejects_extra_output(self):
        output=''.join("'"+n+"' does not depend on any axioms\n" for n in l.NAMES)
        with self.assertRaises(ControlError):l.parse_audits(output+'extra\n')

    def _mock_gate(self,mode='pass'):
        tool=self.root/'tool';(tool/'bin').mkdir(parents=True,exist_ok=True)
        ext='.exe' if os.name=='nt' else ''
        for n in ('lean','lake','git'):(tool/'bin'/(n+ext)).write_bytes(n.encode())
        calls=[]
        def process(argv,cwd,env,**kw):
            calls.append(argv)
            if argv[-1]=='--version':return {'returncode':0,'stdout':'Lean (version 4.31.0, test)','stderr':''}
            if argv[-1].endswith('Conservative.lean'):
                stdout=''.join("'"+n+"' depends on axioms: [propext]\n" for n in l.NAMES)
                return {'returncode':1 if mode=='positive_failure' else 0,'stderr':'bad' if mode=='stderr' else '',
                        'stdout':stdout.replace('propext','sorryAx') if mode=='axiom' else stdout}
            return {'returncode':0 if mode=='false_accept' else (-999 if mode=='timeout' else 1),
                    'stdout':'error: Tactic decide proved false','stderr':''}
        with patch.object(l.gate,'root_source_fingerprint',return_value={}),patch.object(l.gate,'_dependency_state',return_value={}),\
             patch.object(l.gate,'resolve_toolchain',return_value=tool),patch.object(l.gate,'_lean_environment',return_value=({},tool/'bin'/('git'+ext))),\
             patch.object(l.gate,'_process',side_effect=process):
            result=l.check_conservative(self.prepared,source_root=ROOT,lean_workspace=self.root)
        return result,calls

    def test_mock_gate_accepts_only_all_obligations(self):
        result,calls=self._mock_gate();self.assertEqual(result['status'],'passed');self.assertEqual(len(calls),3)
        self.assertTrue(result['scoped_base_obligations_checked']);self.assertTrue(all(v is False for v in result['claims'].values()))

    def test_mock_positive_before_negative(self):
        _,calls=self._mock_gate();self.assertTrue(calls[1][-1].endswith('Conservative.lean'));self.assertTrue(calls[2][-1].endswith('Shadowed.lean'))

    def test_mock_positive_failure_stops(self):
        r,calls=self._mock_gate('positive_failure');self.assertEqual(r['status'],'rejected');self.assertEqual(len(calls),2)

    def test_mock_false_accept_rejects(self):self.assertEqual(self._mock_gate('false_accept')[0]['status'],'rejected')

    def test_mock_negative_timeout_rejects(self):self.assertEqual(self._mock_gate('timeout')[0]['status'],'rejected')

    def test_mock_unapproved_axiom_rejects(self):self.assertEqual(self._mock_gate('axiom')[0]['status'],'rejected')

    def test_mock_stderr_rejects(self):self.assertEqual(self._mock_gate('stderr')[0]['status'],'rejected')

    def test_missing_environment_never_passes(self):
        with patch.object(l.gate,'root_source_fingerprint',side_effect=ControlError('missing pinned root')):
            r=l.check_conservative(self.prepared,source_root=ROOT,lean_workspace=self.root)
        self.assertEqual(r['status'],'blocked');self.assertEqual(r['commands'],[])

if __name__=='__main__':unittest.main()
