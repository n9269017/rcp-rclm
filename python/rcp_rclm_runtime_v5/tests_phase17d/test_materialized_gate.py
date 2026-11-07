from __future__ import annotations
import copy
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from test_challenge_protocol import parent_fixture
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime_v5.phase17.controller import ControlError
from rcp_rclm_runtime_v5.phase17 import materialized as m
from rcp_rclm_runtime_v5.phase17 import frontier_recertification as f
from rcp_rclm_runtime_v5.phase17 import lean_frontier_gate as g
from rcp_rclm_runtime_v5.phase17.challenge_protocol import execute_reference, reference_grammar

ROOT=Path(__file__).resolve().parents[3]
# tests_phase17d -> package -> python -> repo
BUNDLE=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
CAPTURE=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
FIXTURE=Path(__file__).parent/'fixtures/known_candidate_pass.json'
ANCHOR='369c30c469090fa357633aca596cb0c7ad3de31f2ecf16ca78e7699e79c79e6e'


class PhysicalPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=parent_fixture();cls.temp=tempfile.TemporaryDirectory()
        cls.directory=Path(cls.temp.name)
        cls.package=m.materialize_package(cls.directory/'base',cls.parent,BUNDLE)
        cls.raw=FIXTURE.read_bytes()
        cls.candidate=m.materialize_package(cls.directory/'candidate',cls.parent,BUNDLE,
                                          transcript=cls.raw,expected_transcript_hash=ANCHOR)
        cls.prepared=f.prepare_frontier(cls.package,cls.parent,bundle=BUNDLE,capture=CAPTURE)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def verify(self,**kwargs):
        return m.verify_package(self.package.root,self.parent,BUNDLE,expected_package_hash=self.package.package_hash,**kwargs)

    def test_physical_model_is_not_only_planner_metadata(self):
        rows=load_json_strict(self.package.manifest_bytes)['files']
        base=[r for r in rows if r['path'].startswith('base/')]
        self.assertEqual(len(base),164);self.assertEqual(sum(r['size'] for r in base),27434256)
        self.assertTrue(any(r['path'].startswith('base/model/tensors/') for r in base))
        self.assertEqual(self.verify().package_hash,self.package.package_hash)

    def test_package_identity_is_deterministic(self):
        files,record=m.expected_package(self.parent,BUNDLE)
        self.assertEqual(record['materialized_package_hash'],self.package.package_hash)
        self.assertEqual(record['base_package_hash'],m.M9_PACKAGE_HASH)

    def test_no_answers_or_candidate_executables_installed(self):
        names=list(m.snapshot(self.package.root))
        self.assertFalse(any('answer_store' in p or p.endswith(('.py','.exe','.sh','.lean')) for p in names))
        self.assertFalse(load_json_strict(self.package.manifest_bytes)['claims']['promotion_authorized'])

    def test_existing_destination_never_overwritten(self):
        with self.assertRaises(ControlError):m.materialize_package(self.package.root,self.parent,BUNDLE)

    def test_untrusted_expected_hash_rejected(self):
        with self.assertRaises(ControlError):m.verify_package(self.package.root,self.parent,BUNDLE,expected_package_hash='0'*64)

    def test_extra_file_rejected(self):
        extra=self.package.root/'extra.txt';extra.write_bytes(b'not allowed')
        try:
            with self.assertRaises(ControlError):self.verify()
        finally:extra.unlink()

    def test_missing_file_rejected(self):
        path=self.package.root/'base/model/phase15_planner/weights.i16le.bin';raw=path.read_bytes();path.unlink()
        try:
            with self.assertRaises(ControlError):self.verify()
        finally:path.write_bytes(raw)

    def test_tensor_mutation_rejected(self):
        path=self.package.root/'base/model/phase15_planner/weights.i16le.bin';raw=path.read_bytes()
        path.write_bytes(bytes([raw[0]^1])+raw[1:])
        try:
            with self.assertRaises(ControlError):self.verify()
        finally:path.write_bytes(raw)

    def test_rehashed_manifest_cannot_replace_base(self):
        path=self.package.root/m.MANIFEST;raw=path.read_bytes();obj=load_json_strict(raw)
        obj['base_parameter_count']=0;obj['materialized_package_hash']=m.digest({k:v for k,v in obj.items() if k!='materialized_package_hash'})
        path.write_bytes(canonical(obj))
        try:
            with self.assertRaises(ControlError):self.verify()
        finally:path.write_bytes(raw)

    def test_unsafe_paths_and_reserved_windows_names_rejected(self):
        for name in ('../x','/x','a\\b','C:/x','a//b','CON','aux.json','x.','x ','a/../b','a\x00b'):
            with self.subTest(name=name),self.assertRaises(ControlError):m.safe_relative(name)

    def test_case_colliding_paths_rejected(self):
        with self.assertRaises(ControlError):m._measure({'a':b'1','A':b'2'})

    def test_size_and_count_bounds(self):
        with self.assertRaises(ControlError):m._measure({f'x{i}':b'' for i in range(257)})
        with patch.object(m,'MAX_BYTES',2),self.assertRaises(ControlError):m._measure({'x':b'123'})

    def test_symlink_input_rejected_without_needing_windows_link_privilege(self):
        with patch.object(Path,'is_symlink',return_value=True),self.assertRaises(ControlError):m.snapshot(self.package.root)

    def test_hardlink_metadata_rejected(self):
        original=Path.lstat
        def changed(path):
            st=original(path)
            if path.name=='historical_state.json':
                values=list(st);values[3]=2;return os.stat_result(values)
            return st
        with patch.object(Path,'lstat',changed), patch.object(Path,'is_symlink',return_value=False), self.assertRaises(ControlError):
            m.snapshot(self.package.root)

    def test_candidate_requires_external_transcript_anchor(self):
        with self.assertRaises(ControlError):m.expected_package(self.parent,BUNDLE,transcript=self.raw,expected_transcript_hash='0'*64)
        with self.assertRaises(ControlError):m.expected_package(self.parent,BUNDLE,transcript=self.raw)

    def test_exhaustion_does_not_create_candidate(self):
        from test_challenge_protocol import opening,request,evaluate
        from rcp_rclm_runtime_v5.phase17 import challenge_protocol as p
        s=p.EvaluatorSession(self.parent)
        with patch.object(p.secrets,'token_bytes',return_value=bytes(range(32))):s.handle(opening(self.parent,0))
        request(s,'seal',terminal_action='resource_exhausted');raw=p.transcript_bytes(s.events)
        with self.assertRaisesRegex(ControlError,'no passing candidate'):
            m.expected_package(self.parent,BUNDLE,transcript=raw,expected_transcript_hash=m.sha(raw))

    def test_known_pass_fixture_is_not_a_live_campaign(self):
        self.assertEqual(m.sha(self.raw),ANCHOR)
        c=load_json_strict(self.candidate.manifest_bytes)
        self.assertEqual(c['kind'],'prospective_candidate')
        self.assertFalse(c['claims']['promotion_authorized'])
        before=m.snapshot(self.package.root);after=m.snapshot(self.candidate.root)
        for path,data in before.items():
            if path.startswith('base/'):self.assertEqual(after[path],data)

    def test_physical_candidate_evaluation(self):
        result=f.evaluate_candidate_package(self.candidate,self.parent,bundle=BUNDLE,transcript=self.raw,expected_transcript_hash=ANCHOR)
        self.assertTrue(result['bounded_evaluation_passed']);self.assertEqual(result['probe_count'],8)
        self.assertFalse(result['promotion_authorized'])

    def test_installed_integer_semantics_matches_independent_reference(self):
        for raw in self.parent.accepted_programs:
            program=load_json_strict(raw)
            for x in ([0,0,0,0],[-64,64,7,-13],[1,2,3,4]):
                self.assertEqual(m.execute_installed(self.package,m.digest(program),x),execute_reference(program,x))

    def test_matrix_executor_matches_all_32_grammar_programs(self):
        programs=reference_grammar(self.parent.state, 0, '9'*64)
        self.assertEqual(len(programs),32)
        for program in programs:
            for vector in ([0,0,0,0],[-64,64,7,-13],[1,2,3,4],[31,-7,-32,6]):
                self.assertEqual(m.execute_matrix(program,vector),execute_reference(program,vector))

    def test_unknown_program_and_boolean_probe_rejected(self):
        with self.assertRaises(ControlError):m.execute_installed(self.package,'0'*64,[0,0,0,0])
        known=self.parent.state['installed_program_hashes'][0]
        with self.assertRaises(ControlError):m.execute_installed(self.package,known,[True,0,0,0])

    def test_complete_actual_capability_frontier_prepared(self):
        p=self.prepared.report
        self.assertEqual(sorted(r['task_id'] for r in p['task_reports']),self.parent.state['capability_frontier'])
        self.assertEqual(p['capability_count'],21);self.assertEqual(len(self.prepared.sources),13)
        self.assertTrue(p['python_evaluation_passed']);self.assertFalse(p['full_frontier_recertified'])
        self.assertFalse(p['fresh_lean_verified']);self.assertFalse(p['recursive_productivity_recertified'])

    def test_candidate_retains_all_original_capability_outputs(self):
        prepared=f.prepare_frontier(self.candidate,self.parent,bundle=BUNDLE,capture=CAPTURE,
                                    transcript=self.raw,expected_transcript_hash=ANCHOR)
        self.assertEqual(prepared.report['task_reports'],self.prepared.report['task_reports'])

    def test_decoded_integer_program_has_real_exhaustive_cases(self):
        reports=self.prepared.report['task_reports']
        affine=[r for r in reports if r['task_id'].startswith('program.phase15.')]
        self.assertEqual(len(affine),1);self.assertEqual(affine[0]['exhaustive_integer_cases'],65)

    def test_each_lean_source_has_named_axiom_audit(self):
        for name,source in self.prepared.sources:
            self.assertIn(('theorem '+name+' ').encode(),source)
            self.assertIn(('#print axioms '+name).encode(),source)
            self.assertNotIn(b'sorry',source);self.assertNotIn(b'native_decide',source)

    def test_actual_root_source_fingerprint(self):
        self.assertEqual(len(g.root_source_fingerprint(ROOT)),72)

    def test_modified_root_pin_table_rejected(self):
        original=g._read_regular
        def changed(path):
            b=original(path)
            return b+b' ' if path.name=='lean_root_pins.json' else b
        with patch.object(g,'_read_regular',changed),self.assertRaises(ControlError):g.root_source_fingerprint(ROOT)

    def test_missing_pinned_toolchain_never_passes(self):
        with self.assertRaisesRegex(ControlError,'not installed'):g.resolve_toolchain(self.directory/'absent')

    def test_axiom_audit_rejects_missing_or_unsafe_axioms(self):
        name='phase17_'+'a'*24
        for output in ('',"'other' does not depend on any axioms\n",
                       f"'{name}' depends on axioms: [sorryAx]\n",
                       f"'{name}' depends on axioms: [Lean.ofReduceBool]\n",
                       f"'{name}' depends on axioms: [custom]\n"):
            with self.subTest(output=output),self.assertRaises(ControlError):g._axioms(output,name)
        self.assertEqual(g._axioms(f"'{name}' does not depend on any axioms\n",name),[])
        self.assertEqual(g._axioms(f"'{name}' depends on axioms: [propext, Quot.sound]\n",name),['propext','Quot.sound'])

    def test_omitted_or_substituted_proof_rejected(self):
        for sources in (self.prepared.sources[:-1],self.prepared.sources+(self.prepared.sources[0],),
                        ((self.prepared.sources[0][0],b'example : True := by trivial'),)+self.prepared.sources[1:]):
            bad=f.PreparedFrontier(self.prepared.report_bytes,sources)
            with self.assertRaises(ControlError):g._check_prepared_frontier(bad,ROOT)

    def _fake_gate(self,mode):
        # Gate-control tests only; fake tool processes do NOT constitute Lean evidence.
        folder=self.directory/'tool';(folder/'bin').mkdir(parents=True,exist_ok=True)
        suffix='.exe' if os.name=='nt' else ''
        for file in ('lean','lake'):(folder/'bin'/(file+suffix)).write_bytes(b'UNIT TEST NOT EXECUTABLE')
        def process(argv,cwd,env,**kwargs):
            if argv[-1]=='--version':text='Lean (version '+('4.30.0' if mode=='version' else '4.31.0')+', test)\n'
            else:
                name=Path(argv[-1]).stem
                text=f"'{name}' depends on axioms: ["+('sorryAx' if mode=='axiom' else 'propext')+"]\n"
            return {'returncode':1 if mode=='exit' else 0,'stdout':text,'stderr':'warning' if mode=='stderr' else ''}
        with patch.object(g,'_dependency_state',return_value={}),patch.object(g,'_process',side_effect=process):
            return g._check_prepared_frontier(self.prepared,ROOT,toolchain_root=folder)

    def test_gate_requires_successful_process(self):self.assertFalse(self._fake_gate('exit')['fresh_lean_verified'])
    def test_gate_requires_exact_toolchain(self):self.assertFalse(self._fake_gate('version')['fresh_lean_verified'])
    def test_gate_rejects_axiom_escape(self):self.assertFalse(self._fake_gate('axiom')['fresh_lean_verified'])
    def test_gate_rejects_stderr(self):self.assertFalse(self._fake_gate('stderr')['fresh_lean_verified'])
    def test_mocked_success_does_not_authorize_promotion(self):
        r=self._fake_gate('ok');self.assertTrue(r['capability_frontier_recertified'])
        self.assertFalse(r['root_transition_verified']);self.assertFalse(r['promotion_authorized'])
        self.assertEqual(len(r['proofs']),13)


if __name__=='__main__':unittest.main(verbosity=2)
