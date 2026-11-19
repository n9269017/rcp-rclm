from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
from rcp_rclm_runtime_v5.phase17 import resource_ledger as rl
from rcp_rclm_runtime_v5.phase17 import metered_evaluation as me
from rcp_rclm_runtime_v5.phase17 import resource_lean as lean
from rcp_rclm_runtime_v5.phase17.bootstrap import HistoricalPredecessor, reopen_phase16
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from rcp_rclm_runtime_v5.phase17.challenge_protocol import vector_semantics

BINDING = me.selected_binding()
POLICY = rl.full_grammar_policy(8)
RAW_TRANSCRIPT = ROOT/'python/rcp_rclm_runtime_v5/tests_phase17k/fixtures/ordered_known_challenge.json'


def fixture_parent():
    f = json.loads((ROOT/'python/rcp_rclm_runtime_v5/tests_phase17/fixtures/phase16_bootstrap_handoff.json').read_bytes())
    weights = [0] * 32768
    for i,v in f['planner_projection']:
        weights[i] = v
    return HistoricalPredecessor(canonical(f['state']),tuple(map(canonical,f['programs'])),
        struct.pack('<32768h',*weights),canonical(f['catalog']),canonical(f['receipt']))


def rechain(rows):
    result = []
    previous = rl.ZERO
    for i,row in enumerate(rows):
        row=copy.deepcopy(row)
        if row['body']['kind']=='result':row['body']['reservation_hash']=previous
        row = rl.event(row['body'],i,previous)
        result.append(rl.canonical(row)+b'\n')
        previous = row['hash']
    return b''.join(result),previous


class PolicyTests(unittest.TestCase):
    def test_default_is_whole_grammar_not_winner(self):
        self.assertEqual(POLICY.limits,(32,328,1312,1312))
        self.assertEqual(POLICY.cost_limit,9920)
    def test_bool_and_noninteger_rejected(self):
        for x in (True,False,1.0,'1',None):
            with self.subTest(x=x),self.assertRaises(rl.ResourceError):rl.Policy((x,1,4,4),24)
    def test_negative_rejected(self):
        with self.assertRaises(rl.ResourceError):rl.Policy((0,-1,4,4),24)
    def test_overflow_rejected(self):
        with self.assertRaises(rl.ResourceError):rl.Policy((rl.MAX_NAT,1,4,4),rl.MAX_NAT)
    def test_wrong_dimension_rejected(self):
        with self.assertRaises(rl.ResourceError):rl.Policy((1,2,3),100)
    def test_zero_policy_valid(self):
        self.assertTrue(rl.Policy((0,0,0,0),0).fits((0,0,0,0)))
    def test_frozen_input_detached(self):
        values=[1,1,4,4];p=rl.Policy(values,88);values[0]=999
        self.assertEqual(p.limits,(1,1,4,4))
    def test_policy_roundtrip(self):self.assertEqual(rl.Policy.from_json(POLICY.to_json()),POLICY)
    def test_weights_not_candidate_selectable(self):
        d=POLICY.to_json();d['weights'][0]=0
        with self.assertRaises(rl.ResourceError):rl.Policy.from_json(d)
    def test_unknown_policy_field_rejected(self):
        d=POLICY.to_json();d['promotion_authorized']=True
        with self.assertRaises(rl.ResourceError):rl.Policy.from_json(d)
    def test_each_dimension_enforced(self):
        for i in range(4):
            limits=[10]*4;limits[i]=0
            self.assertFalse(rl.Policy(limits,10000).fits([1]*4))
    def test_scalar_enforced_in_addition_to_vector(self):
        self.assertFalse(rl.Policy((100,100,400,400),23).fits((0,1,4,4)))
    def test_fixed_tariffs_and_cost(self):
        self.assertEqual(rl.cost(rl.TARIFFS['candidate']),64)
        self.assertEqual(rl.cost(rl.TARIFFS['vector']),24)
    def test_bad_inventory_rejected(self):
        for x in (True,-1,1025):
            with self.subTest(x=x),self.assertRaises(rl.ResourceError):rl.full_grammar_policy(x)
        with self.assertRaises(rl.ResourceError):rl.full_grammar_policy(8,candidate_limit=33)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'resource.jsonl'
    def ledger(self,**kw):return rl.Ledger(self.path,policy=kw.get('policy',POLICY),expected_binding=kw.get('binding',BINDING),expected_head=kw.get('head'))
    def completed(self):
        with self.ledger() as l:
            l.perform('vector','one','1'*64,lambda:b'ok');l.seal()
            return l.journal_bytes(),l.state.head
    def verify(self,raw,head,**kw):return rl.replay(raw,expected_head=head,policy=kw.get('policy',POLICY),expected_binding=kw.get('binding',BINDING))
    def test_reserve_visible_before_work(self):
        with self.ledger() as l:
            def work():
                state=self.verify(self.path.read_bytes(),l.state.head)
                self.assertEqual(state.spent,(0,1,4,4));self.assertEqual(state.status,'pending')
                return b'ok'
            l.perform('vector','one','1'*64,work)
    def test_success_roundtrip_sealed(self):
        raw,head=self.completed();s=self.verify(raw,head)
        self.assertEqual(s.spent,(0,1,4,4));self.assertEqual(s.status,'sealed');self.assertEqual(s.charged_cost,24)
    def test_failure_never_refunded(self):
        with self.ledger() as l:
            def fail():raise RuntimeError('deliberate')
            with self.assertRaises(RuntimeError):l.perform('vector','failure','1'*64,fail)
            self.assertEqual(l.state.spent,(0,1,4,4));self.assertEqual(l.state.status,'safety_halt')
            with self.assertRaises(rl.ResourceError):l.seal()
    def test_exhaustion_does_not_execute(self):
        with self.ledger(policy=rl.Policy((0,0,0,0),0)) as l:
            called=[]
            with self.assertRaises(rl.ResourceExhausted):l.perform('vector','blocked','1'*64,lambda:called.append(1))
            self.assertFalse(called);self.assertEqual(l.state.status,'resource_exhausted');self.assertEqual(l.state.spent,(0,0,0,0))
    def test_prior_charges_survive_later_exhaustion(self):
        with self.ledger(policy=rl.Policy((0,1,4,4),24)) as l:
            l.perform('vector','one','1'*64,lambda:b'ok')
            with self.assertRaises(rl.ResourceExhausted):l.perform('vector','two','2'*64,lambda:b'bad')
            self.assertEqual(l.state.charged_cost,24)
    def test_pending_cannot_be_sealed_or_skipped(self):
        with self.ledger() as l:
            l.reserve('vector','one','1'*64)
            with self.assertRaises(rl.ResourceError):l.seal()
            with self.assertRaises(rl.ResourceError):l.reserve('vector','two','1'*64)
    def test_restart_with_external_anchor(self):
        with self.ledger() as l:l.perform('vector','one','1'*64,lambda:b'ok');head=l.state.head
        with self.ledger(head=head) as l:
            l.perform('candidate','next','2'*64,lambda:b'ok');self.assertEqual(l.state.spent,(1,1,4,4));l.seal()
    def test_existing_without_anchor_rejected(self):
        self.completed()
        with self.assertRaises(rl.ResourceError):self.ledger()
    def test_wrong_anchor_rejected(self):
        self.completed()
        with self.assertRaises(rl.ResourceError):self.ledger(head='0'*64)
    def test_pending_restart_abandon_keeps_charge(self):
        with self.ledger() as l:l.reserve('vector','one','1'*64);head=l.state.head
        with self.ledger(head=head) as l:
            self.assertEqual(l.state.status,'pending');l.abandon_interrupted()
            self.assertEqual(l.state.status,'safety_halt');self.assertEqual(l.state.charged_cost,24)
    def test_no_implicit_abandon_on_open(self):
        with self.ledger() as l:l.reserve('vector','one','1'*64);head=l.state.head;raw=l.journal_bytes()
        with self.ledger(head=head) as l:self.assertEqual(l.journal_bytes(),raw)
    def test_sealed_session_cannot_resume_work(self):
        _,head=self.completed()
        with self.ledger(head=head) as l:
            with self.assertRaises(rl.ResourceError):l.perform('vector','next','1'*64,lambda:b'ok')
    def test_explicit_external_stop(self):
        with self.ledger() as l:l.stop();self.assertEqual(l.state.status,'external_stop')
    def test_stale_completion_rejected(self):
        with self.ledger() as l:
            l.reserve('vector','one','1'*64)
            with self.assertRaises(rl.ResourceError):l.finish('0'*64,result=b'ok',elapsed_ns=1)
    def test_duplicate_operation_rejected(self):
        with self.ledger() as l:
            l.perform('vector','one','1'*64,lambda:b'ok')
            with self.assertRaises(rl.ResourceError):l.reserve('vector','one','1'*64)
    def test_unknown_operation_rejected(self):
        with self.ledger() as l:
            with self.assertRaises(rl.ResourceError):l.reserve('promotion','one','1'*64)
    def test_binding_input_detached(self):
        b=dict(BINDING)
        with self.ledger(binding=b) as l:
            b['candidate_package_hash']='0'*64
            q=l.binding;q['candidate_package_hash']='1'*64
            self.assertEqual(l.binding,BINDING)
    def test_changed_external_binding_rejected(self):
        raw,head=self.completed();b=dict(BINDING);b['candidate_package_hash']='0'*64
        with self.assertRaises(rl.ResourceError):self.verify(raw,head,binding=b)
    def test_changed_external_policy_rejected(self):
        raw,head=self.completed()
        with self.assertRaises(rl.ResourceError):self.verify(raw,head,policy=rl.Policy((10,100,400,400),10000))
    def test_truncation_rejected(self):
        raw,head=self.completed()
        for v in (raw[:-1],raw[:100],b''):
            with self.subTest(size=len(v)),self.assertRaises(rl.ResourceError):self.verify(v,head)
    def test_crlf_rejected(self):
        raw,head=self.completed()
        with self.assertRaises(rl.ResourceError):self.verify(raw.replace(b'\n',b'\r\n'),head)
    def test_rehash_is_not_external_authority(self):
        raw,head=self.completed();rows=[json.loads(x) for x in raw.splitlines()];rows[2]['body']['result_sha256']='0'*64
        changed,new=rechain(rows)
        with self.assertRaises(rl.ResourceError):self.verify(changed,head)
        self.assertNotEqual(head,new)
    def test_rehashed_forged_tariff_rejected(self):
        raw,_=self.completed();rows=[json.loads(x) for x in raw.splitlines()];rows[1]['body']['charge']=[0,0,0,0]
        changed,new=rechain(rows)
        with self.assertRaises(rl.ResourceError):self.verify(changed,new)
    def test_rehashed_forged_total_rejected(self):
        raw,_=self.completed();rows=[json.loads(x) for x in raw.splitlines()];rows[1]['body']['spent_after']=[0,0,0,0]
        changed,new=rechain(rows)
        with self.assertRaises(rl.ResourceError):self.verify(changed,new)
    def test_rehashed_boolean_counter_rejected(self):
        raw,_=self.completed();rows=[json.loads(x) for x in raw.splitlines()];rows[1]['body']['charge'][0]=False
        changed,new=rechain(rows)
        with self.assertRaises(rl.ResourceError):self.verify(changed,new)
    def test_unapproved_success_flag_rejected(self):
        raw,_=self.completed();rows=[json.loads(x) for x in raw.splitlines()];rows[-1]['body']['phase17_exit_closed']=True
        changed,new=rechain(rows)
        with self.assertRaises(rl.ResourceError):self.verify(changed,new)
    def test_omitted_result_rejected(self):
        raw,_=self.completed();rows=[json.loads(x) for x in raw.splitlines()];rows.pop(2)
        changed,new=rechain(rows)
        with self.assertRaises(rl.ResourceError):self.verify(changed,new)
    def test_duplicate_json_key_rejected(self):
        raw,head=self.completed();raw=raw.replace(b'"index":0',b'"index":0,"index":0',1)
        with self.assertRaises(rl.ResourceError):self.verify(raw,head)
    def test_disk_failure_prevents_callback(self):
        with self.ledger() as l:
            called=[]
            with patch.object(rl.os,'fsync',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):l.perform('vector','one','1'*64,lambda:called.append(1))
            self.assertFalse(called)
            with self.assertRaises(rl.ResourceError):l.reserve('vector','again','1'*64)
    def test_external_file_mutation_prevents_callback(self):
        with self.ledger() as l:
            with open(self.path,'ab') as f:f.write(b'x')
            with self.assertRaises(rl.ResourceError):l.perform('vector','one','1'*64,lambda:b'bad')
    def test_invalid_operation_result_halts_and_retains_charge(self):
        with self.ledger() as l:
            with self.assertRaises(rl.ResourceError):l.perform('vector','one','1'*64,lambda:True)
            self.assertEqual(l.state.status,'safety_halt');self.assertEqual(l.state.charged_cost,24)
    def test_writer_lock_conflict(self):
        with self.ledger() as l:
            with self.assertRaises((OSError,rl.ResourceError)):self.ledger(head=l.state.head)
    def test_released_lock_reusable(self):
        with self.ledger() as l:head=l.state.head
        with self.ledger(head=head) as l:l.stop()
    def test_closed_handle_rejected(self):
        l=self.ledger();l.close()
        with self.assertRaises(rl.ResourceError):l.reserve('vector','one','1'*64)
    def test_nonstring_operation_rejected(self):
        with self.ledger() as l:
            for value in (None,True,[],{}):
                with self.subTest(value=value),self.assertRaises(rl.ResourceError):l.reserve(value,'one','1'*64)
    def test_directory_lock_rejected(self):
        self.path.with_name(self.path.name+'.lock').mkdir()
        with self.assertRaises(rl.ResourceError):self.ledger()
    def test_boolean_elapsed_rejected(self):
        with self.ledger() as l:
            head=l.reserve('vector','one','1'*64)
            with self.assertRaises(rl.ResourceError):l.finish(head,result=b'ok',elapsed_ns=True)
    def test_system_exit_still_records_charge(self):
        with self.ledger() as l:
            def stop():raise SystemExit(13)
            with self.assertRaises(SystemExit):l.perform('vector','one','1'*64,stop)
            self.assertEqual(l.state.status,'safety_halt');self.assertEqual(l.state.charged_cost,24)
    def test_marked_link_path_rejected(self):
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(rl.ResourceError):self.ledger()
    def test_real_process_death_keeps_reservation(self):
        env=dict(os.environ);env['PYTHONPATH']=os.pathsep.join(str(ROOT/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5))
        anchor=self.path.with_suffix('.anchor.txt')
        code=("from pathlib import Path; import os; from rcp_rclm_runtime_v5.phase17.resource_ledger import *; "
              "l=Ledger(Path("+repr(str(self.path))+"),policy=full_grammar_policy(8),expected_binding="+repr(BINDING)+"); "
              "l.reserve('vector','interrupted','1'*64); Path("+repr(str(anchor))+").write_text(l.state.head,encoding='ascii'); os._exit(17)")
        p=subprocess.run([sys.executable,'-B','-c',code],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        self.assertEqual(p.returncode,17,p.stderr.decode(errors='replace'))
        with self.ledger(head=anchor.read_text(encoding='ascii')) as l:
            self.assertEqual(l.state.status,'pending');self.assertEqual(l.state.charged_cost,24);l.abandon_interrupted()
    def test_real_process_lock_conflict(self):
        env=dict(os.environ);env['PYTHONPATH']=os.pathsep.join(str(ROOT/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5))
        with self.ledger() as l:
            code=("from pathlib import Path; from rcp_rclm_runtime_v5.phase17.resource_ledger import *; "
                  "Ledger(Path("+repr(str(self.path))+"),policy=full_grammar_policy(8),expected_binding="+repr(BINDING)+",expected_head="+repr(l.state.head)+")")
            p=subprocess.run([sys.executable,'-B','-c',code],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
            self.assertNotEqual(p.returncode,0);self.assertEqual(l.state.status,'open')


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.parent=fixture_parent();cls.raw=RAW_TRANSCRIPT.read_bytes()
        cls.report=me.run_selected_profile(cls.parent,cls.raw,journal=cls.root/'selected.jsonl')
        cls.journal=(cls.root/'selected.jsonl').read_bytes();cls.work=me.prepare_work(cls.parent,cls.raw,expected_hash=me.TRANSCRIPT)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_real_archive_matches_profile_parent(self):
        p=reopen_phase16(capture_archive=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip',
            closure_archive=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip',
            phase15_bundle=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip')
        self.assertEqual(p,self.parent)
    def test_all_initial_and_failed_candidate_work_charged(self):
        self.assertEqual(self.report['spent'],[9,144,576,576]);self.assertEqual(self.report['charged_cost'],4032)
    def test_truth_matches_all_nine_original_verdicts(self):self.assertEqual(self.report['verdicts'],['reject']*8+['candidate_passed'])
    def test_all_probes_executed_without_shortcircuit(self):
        self.assertEqual(len(self.work),153);self.assertEqual(self.report['event_count'],308)
    def test_unmeasured_is_explicit_not_zero(self):
        self.assertIn('cpu_time',self.report['unmeasured']);self.assertTrue(all(v is False for v in self.report['claims'].values()))
    def test_wrong_transcript_anchor_rejected(self):
        with self.assertRaises(ValueError):me.prepare_work(self.parent,self.raw,expected_hash='0'*64)
    def test_replay_cannot_omit_whole_operation_even_rehashed(self):
        rows=[json.loads(x) for x in self.journal.splitlines()];del rows[1:3]
        # Correct arithmetic for the altered trace still cannot satisfy the independently derived schedule.
        for row in rows:
            if row['body']['kind']=='reserve':row['body']['spent_after']=[a-b for a,b in zip(row['body']['spent_after'],[0,1,4,4])]
        altered,head=rechain(rows)
        with self.assertRaises(rl.ResourceError):me.verify_profile(altered,expected_head=head,policy=POLICY,expected_binding=BINDING,expected_work=self.work)
    def test_wrong_output_hash_rejected_after_rehash(self):
        rows=[json.loads(x) for x in self.journal.splitlines()];rows[2]['body']['result_sha256']='0'*64
        altered,head=rechain(rows)
        with self.assertRaises(rl.ResourceError):me.verify_profile(altered,expected_head=head,policy=POLICY,expected_binding=BINDING,expected_work=self.work)
    def test_wrong_input_hash_rejected_after_rehash(self):
        rows=[json.loads(x) for x in self.journal.splitlines()];rows[1]['body']['input_sha256']='0'*64
        altered,head=rechain(rows)
        with self.assertRaises(rl.ResourceError):me.verify_profile(altered,expected_head=head,policy=POLICY,expected_binding=BINDING,expected_work=self.work)
    def test_profile_inventory_fields_match_events(self):
        self.assertEqual(self.report['status'],'sealed')
        self.assertEqual(self.report['operation_count'],153)
        self.assertEqual(self.report['candidate_attempts'],9)
        self.assertEqual(self.report['vector_calls'],144)
        self.assertEqual(self.report['event_count'],308)
    def test_profile_does_not_modify_transcript(self):self.assertEqual(RAW_TRANSCRIPT.read_bytes(),self.raw)
    def test_work_output_matches_reference_all_families(self):
        # Full inherited fixture covers all eight current families, all four variants are checked explicitly.
        from rcp_rclm_runtime_v5.phase17.controller import FAMILIES
        for family in FAMILIES:
            for variant in range(4):
                value={'role':'target','parameters':[family,variant,-4,16],'vector':[24,-13,-1,-6]}
                w=me.Work('vector','test',canonical(value))
                self.assertEqual(json.loads(w.execute()),vector_semantics(family,variant,-4,16,value['vector']))


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.path=Path(cls.tmp.name)
        cls.report=me.run_selected_profile(fixture_parent(),RAW_TRANSCRIPT.read_bytes(),journal=cls.path/'ledger.jsonl')
        cls.failure={'charge_sequence':['vector'],'spent':[0,1,4,4],'charged_cost':24,'status':'safety_halt'}
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_four_distinct_negative_certificates(self):
        values=[lean.render(self.report,self.failure,source_root=ROOT,negative=None if k=='Resource' else k) for k in lean.LABELS]
        self.assertEqual(len(set(values)),5)
    def test_twelve_audits(self):
        raw=lean.render(self.report,self.failure,source_root=ROOT)
        self.assertEqual(raw.count(b'#print axioms '),12)
    def test_no_placeholder_or_native_proof(self):
        import re
        self.assertIsNone(re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b',lean.render(self.report,self.failure,source_root=ROOT)))
    def test_exact_template_pin(self):
        self.assertEqual(rl.sha(lean.template(ROOT)),lean.TEMPLATE_SHA256)
    def test_positive_audit_parse(self):
        output=''.join("'"+n+"' does not depend on any axioms\n" for n in lean.NAMES)
        self.assertEqual(set(lean.parse_audits(output)),set(lean.NAMES))
    def test_missing_audit_rejected(self):
        with self.assertRaises(ValueError):lean.parse_audits('')
    def test_unapproved_axiom_rejected(self):
        output=''.join("'"+n+"' depends on axioms: [sorryAx]\n" for n in lean.NAMES)
        with self.assertRaises(ValueError):lean.parse_audits(output)
    def test_extra_output_rejected(self):
        output=''.join("'"+n+"' does not depend on any axioms\n" for n in lean.NAMES)+'unbound output\n'
        with self.assertRaises(ValueError):lean.parse_audits(output)
    def test_wrong_inventory_rejected(self):
        p=copy.deepcopy(self.report);p['spent'][0]=8
        with self.assertRaises(rl.ResourceError):lean.render(p,self.failure,source_root=ROOT)
    def test_refunded_failure_rejected_as_positive_input(self):
        f=dict(self.failure,charged_cost=0)
        with self.assertRaises(rl.ResourceError):lean.render(self.report,f,source_root=ROOT)
    def test_render_does_not_mutate_input(self):
        p=copy.deepcopy(self.report);f=copy.deepcopy(self.failure)
        for n in lean.LABELS[1:]:lean.render(p,f,source_root=ROOT,negative=n)
        self.assertEqual(p,self.report);self.assertEqual(f,self.failure)
    def test_full_root_claim_not_embedded(self):
        raw=lean.render(self.report,self.failure,source_root=ROOT)
        self.assertNotIn(b'LearnedAcceptedStep',raw);self.assertNotIn(b'AutonomousAcceptedStep',raw)
