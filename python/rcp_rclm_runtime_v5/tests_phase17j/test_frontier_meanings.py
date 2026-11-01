from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.materialized import materialize_package,sha,snapshot
from rcp_rclm_runtime_v5.phase17 import frontier_meanings as m, frontier_meaning_lean as l

ROOT=Path(__file__).resolve().parents[3]
BUNDLE=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
CAPTURE=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
CLOSURE=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
FIXTURE=ROOT/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json'
ANCHOR='369c30c469090fa357633aca596cb0c7ad3de31f2ecf16ca78e7699e79c79e6e'

class MeaningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='r17j-test-');cls.root=Path(cls.temp.name).resolve(strict=True)
        cls.parent=reopen_phase16(capture_archive=CAPTURE,closure_archive=CLOSURE,phase15_bundle=BUNDLE)
        cls.raw=FIXTURE.read_bytes()
        cls.before=materialize_package(cls.root/'p',cls.parent,BUNDLE)
        cls.after=materialize_package(cls.root/'c',cls.parent,BUNDLE,transcript=cls.raw,expected_transcript_hash=ANCHOR)
        cls.prepared=m.prepare_meanings(cls.before,cls.after,cls.parent,bundle=BUNDLE,capture=CAPTURE,
            transcript=cls.raw,expected_transcript_hash=ANCHOR)
        cls.p=cls.prepared.packet
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def bad(self,fn):
        p=copy.deepcopy(self.p);fn(p)
        with self.assertRaises((ValueError,KeyError,TypeError)):m.PreparedMeanings(canonical(p))
    def test_full_physical_prepare(self):
        self.assertEqual(len(self.p['tasks']),22);self.assertEqual(len(self.p['checks']['before_ids']),21)
        self.assertEqual(len(self.p['checks']['after_ids']),22)
    def test_thirteen_real_theorem_sources(self):
        ts=[t for t in self.p['tasks'] if t['kind']=='proof']
        self.assertEqual(len(ts),13);self.assertEqual({t['meaning']['source_sha256'] for t in ts},set(m.PROOF_SOURCE_HASHES))
    def test_nine_vector_contracts_keep_finite_scope(self):
        ts=[t for t in self.p['tasks'] if t['kind']=='vectors']
        self.assertEqual([len(t['inputs']) for t in ts],[1]*8+[8])
        self.assertFalse(self.p['scope']['universal_vector_claim'])
    def test_predecessor_rejects_new(self):self.assertFalse(m.check_task(self.p['tasks'][-1],self.p['before']))
    def test_candidate_solves_new(self):self.assertTrue(m.check_task(self.p['tasks'][-1],self.p['after']))
    def test_historical_catalog_pinned(self):self.assertEqual(sha(canonical(self.p['tasks'][:21])),m.HISTORICAL_CATALOG_SHA256)
    def test_packet_detached(self):
        p=self.prepared.packet;p['before']['programs'].clear();self.assertEqual(len(self.prepared.packet['before']['programs']),8)
    def test_packet_mutable_rejected(self):
        with self.assertRaises(ValueError):m.PreparedMeanings(bytearray(self.prepared.packet_bytes))
    def test_formatted_packet_rejected(self):
        with self.assertRaises(ValueError):m.PreparedMeanings(json.dumps(self.p,indent=2).encode())
    def test_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):m.PreparedMeanings(b'{"schema_id":1,"schema_id":2}')
    def test_bad_anchor_rejected(self):
        with self.assertRaises(ValueError):m.verify_meaning_bytes(self.prepared.packet_bytes,self.prepared,expected_sha256='0'*64)
    def test_exact_recomputation_comparison(self):
        m.verify_meaning_bytes(self.prepared.packet_bytes,self.prepared,expected_sha256=sha(self.prepared.packet_bytes))
        changed=self.prepared.packet_bytes+b' '
        with self.assertRaises(ValueError):m.verify_meaning_bytes(changed,self.prepared,expected_sha256=sha(changed))
    def test_unknown_catalog_field_rejected(self):self.bad(lambda p:p.update(accepted=True))
    def test_promoted_claim_rejected(self):self.bad(lambda p:p['claims'].update(promotion_performed=True))
    def test_integer_false_claim_rejected(self):self.bad(lambda p:p['claims'].update(promotion_performed=0))
    def test_wrong_policy_rejected(self):self.bad(lambda p:p.update(policy='relaxed'))
    def test_missing_task_rejected(self):self.bad(lambda p:p['tasks'].pop())
    def test_alias_same_id_rejected(self):self.bad(lambda p:p['tasks'][1].update(task_id=p['tasks'][0]['task_id']))
    def test_swapped_task_meanings_rejected(self):self.bad(lambda p:p['tasks'].__setitem__(slice(0,2),list(reversed(p['tasks'][:2]))))
    def test_changed_historical_oracle_rejected(self):
        def change(p):next(t for t in p['tasks'] if t['kind']=='vectors')['targets'][0][0]+=1
        self.bad(change)
    def test_wrong_proof_proposition_rejected(self):self.bad(lambda p:p['tasks'][0]['meaning'].update(proposition='True'))
    def test_edited_proof_source_rejected(self):self.bad(lambda p:p['tasks'][0]['meaning'].update(source_utf8='theorem fake : True := by trivial'))
    def test_name_source_substitution_rejected(self):
        t=next(t for t in self.p['tasks'] if t['kind']=='proof')
        with self.assertRaises(ValueError):m.proof_meaning('phase17_'+'0'*24,t['meaning']['source_utf8'].encode())
    def test_missing_proof_observation_fails_check(self):
        s=copy.deepcopy(self.p['after']);t=next(t for t in self.p['tasks'] if t['kind']=='proof');s['proof_observations']=[]
        self.assertFalse(m.check_task(t,s))
    def test_changed_decode_rejected(self):self.bad(lambda p:p['after']['proof_observations'][0].update(decode_hash='0'*64))
    def test_removed_program_rejected(self):self.bad(lambda p:p['after']['programs'].pop())
    def test_shadow_program_rejected(self):self.bad(lambda p:p['after']['programs'].__setitem__(-1,p['before']['programs'][0]))
    def test_mutated_registry_rejected(self):self.bad(lambda p:p['after']['programs'][0].update(parameter_a=16))
    def test_wrong_state_hash_rejected(self):self.bad(lambda p:p['after'].update(package_hash='0'*64))
    def test_extra_claimed_frontier_rejected(self):self.bad(lambda p:p['after']['declared_ids'].append('fake'))
    def test_same_new_identifier_rejected(self):self.bad(lambda p:p.update(new_task_id=p['tasks'][0]['task_id']))
    def test_changed_challenge_binding_rejected(self):self.bad(lambda p:p['bindings'].update(challenge_commitment_hash='0'*64))
    def test_vector_boolean_rejected(self):self.bad(lambda p:p['tasks'][-1]['inputs'][0].__setitem__(0,False))
    def test_vector_input_domain_rejected(self):self.bad(lambda p:p['tasks'][-1]['inputs'][0].__setitem__(0,65))
    def test_empty_probe_set_rejected(self):self.bad(lambda p:p['tasks'][-1].update(inputs=[],targets=[]))
    def test_wrong_new_oracle_rejected(self):self.bad(lambda p:p['tasks'][-1]['targets'][0].__setitem__(0,999999))
    def test_forged_check_result_rejected(self):self.bad(lambda p:p['checks'].update(predecessor_new_task_passed=True))
    def test_non_boolean_check_rejected(self):self.bad(lambda p:p['checks'].update(candidate_new_task_passed=1))
    def test_scope_widening_rejected(self):self.bad(lambda p:p['scope'].update(universal_vector_claim=True))
    def test_scope_zero_rejected(self):self.bad(lambda p:p['scope'].update(universal_vector_claim=0))
    def test_render_uses_actual_root_field(self):
        raw=l.render_meanings(self.prepared,source_root=ROOT).decode()
        self.assertIn('frontierSound := by',raw);self.assertIn('Learned.FrontierKernel',raw)
        self.assertIn('holds := fun s => ∃ e ∈ s.programs',raw)
    def test_render_all_twenty_one_audits(self):
        raw=l.render_meanings(self.prepared,source_root=ROOT).decode()
        self.assertEqual(re.findall(r'^#print axioms (.+)$',raw,re.M),list(l.NAMES))
    def test_negative_sources_distinct_packet_unchanged(self):
        original=self.prepared.packet_bytes
        p=l.render_meanings(self.prepared,source_root=ROOT)
        n=[l.render_meanings(self.prepared,source_root=ROOT,negative=x) for x in ('target','observation')]
        self.assertEqual(len(set([p,*n])),3);self.assertEqual(self.prepared.packet_bytes,original)
    def test_no_proof_placeholder(self):
        self.assertIsNone(re.search(rb'\b(sorry|admit|sorryAx|native_decide|unsafe)\b',l.render_meanings(self.prepared,source_root=ROOT)))
    def test_import_cardinality_immutable_root(self):
        raw=l.template(ROOT).decode();self.assertIn('import RcpRclmFormalCoreV4',raw)
    def test_parser_closed_type_annotation(self):
        t=next(t for t in self.p['tasks'] if t['kind']=='proof' and 'reflexive_seven' in t['task_id'])
        self.assertEqual(t['meaning']['proposition'],'(7 : Nat) = 7')
    def test_parser_binder_assumption(self):
        self.assertTrue(self.p['tasks'][0]['meaning']['proposition'].startswith('∀ (a b : Nat) (h :'))
    def test_empty_state_no_certified_tasks(self):
        s=dict(self.p['after'],proof_observations=[],programs=[])
        self.assertEqual(m.checked_ids(self.p['tasks'],s),[])
    def test_unknown_identifier_not_admitted(self):
        s=copy.deepcopy(self.p['after']);s['declared_ids'].append('fake')
        self.assertNotIn('fake',m.checked_ids(self.p['tasks'],s))
    def test_counterexample_cannot_be_hidden_by_membership(self):
        t=copy.deepcopy(self.p['tasks'][-1]);t['targets'][0][0]+=1
        self.assertFalse(m.check_task(t,self.p['after']))
    def test_repeated_render_deterministic(self):
        self.assertEqual(l.render_meanings(self.prepared,source_root=ROOT),l.render_meanings(self.prepared,source_root=ROOT))

class FormalControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build genuine package facts once; compiler responses below are mocks.
        MeaningTests.setUpClass();cls.prepared=MeaningTests.prepared
    @classmethod
    def tearDownClass(cls):MeaningTests.tearDownClass()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.tool=self.root/'tool';(self.tool/'bin').mkdir(parents=True)
        suf='.exe' if os.name=='nt' else ''
        for f in ('lean','lake','git'):(self.tool/'bin'/(f+suf)).write_bytes(b'not a compiler: unit fixture')
        self.git=self.tool/'bin'/('git'+suf);self.calls=[]
    def tearDown(self):self.temp.cleanup()
    def run_gate(self,mode='ok'):
        def proc(argv,cwd,env,**kw):
            self.calls.append(argv)
            if argv[-1]=='--version':c,o,e=0,'Lean (version 4.31.0, mocked)\n',''
            elif Path(argv[-1]).stem=='TaskMeaning':
                c=1 if mode=='positive-fail' else 0;e='warning' if mode=='stderr' else ''
                ns=l.NAMES if mode!='missing-name' else l.NAMES[:-1]
                o=''.join("'"+n+"' depends on axioms: ["+('sorryAx' if mode=='axiom' else 'propext')+"]\n" for n in ns)
                if mode=='extra-output':o+='extra\n'
                if mode=='tool-changed':self.git.write_bytes(b'changed')
            else:c,o,e=(0 if mode=='false-accepted' else 1),'error: decide proved proposition false\n',''
            return dict(argv=argv,returncode=c,stdout=o,stderr=e,stdout_sha256=sha(o.encode()),stderr_sha256=sha(e.encode()))
        with patch.object(l.gate,'root_source_fingerprint',return_value={'fixed':{'canonical_sha256':'a'}}),\
             patch.object(l.gate,'_dependency_state',side_effect=ValueError('missing dependency') if mode=='blocked' else None,return_value={'pinned':'x'}),\
             patch.object(l.gate,'resolve_toolchain',return_value=self.tool),\
             patch.object(l.gate,'_lean_environment',return_value=({},self.git)),\
             patch.object(l.gate,'_process',side_effect=proc):
            return l.check_meanings(self.prepared,source_root=ROOT,lean_workspace=self.root)
    def test_mock_success_not_closure(self):
        r=self.run_gate();self.assertEqual(r['status'],'passed');self.assertTrue(all(v is False for v in r['claims'].values()))
    def test_both_negative_controls_required(self):self.assertEqual(self.run_gate()['negative_controls_rejected'],['WrongTarget','MissingProofObservation'])
    def test_positive_failure_stops_before_negatives(self):
        self.assertEqual(self.run_gate('positive-fail')['status'],'rejected');self.assertEqual(len(self.calls),2)
    def test_unknown_axiom_rejected(self):self.assertEqual(self.run_gate('axiom')['status'],'rejected')
    def test_missing_audit_rejected(self):self.assertEqual(self.run_gate('missing-name')['status'],'rejected')
    def test_extra_output_rejected(self):self.assertEqual(self.run_gate('extra-output')['status'],'rejected')
    def test_stderr_rejected(self):self.assertEqual(self.run_gate('stderr')['status'],'rejected')
    def test_accepting_false_rejected(self):self.assertEqual(self.run_gate('false-accepted')['status'],'rejected')
    def test_changed_tool_rejected(self):self.assertEqual(self.run_gate('tool-changed')['status'],'rejected')
    def test_no_dependency_no_compiler(self):
        self.assertEqual(self.run_gate('blocked')['status'],'blocked');self.assertEqual(self.calls,[])
    def test_exact_compiler_flags(self):
        self.run_gate()
        for c in self.calls[1:]:self.assertEqual(c[1:4],['--keep-toolchain','--no-cache','env'])

if __name__=='__main__':unittest.main(verbosity=2)
