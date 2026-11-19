from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import transition_journal as tj
from rcp_rclm_runtime_v5.phase17 import successor_staging as st
from rcp_rclm_runtime_v5.phase17.handoff_source import (
    campaign_capsule,fixture_capsule,checked_handoff,unhex,parse,SESSION_NAMES)
from rcp_rclm_runtime_v5.phase17.campaign_budget import CampaignAuthority
from rcp_rclm_runtime_v5.phase17.campaign_transaction import context_for,load_predecessor,run_campaign_session
from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical,sha,full_grammar_policy


def bind():
    return {'mode':'online_campaign','scope_id':'1'*64,'predecessor_state_hash':'2'*64,
            'predecessor_logical_package_hash':'3'*64,'predecessor_physical_hash':'4'*64,
            'fixed_verifier_hash':'5'*64}


def consume(j,source='6'*64,challenge='8'*64,terminal='await_root_verification'):
    return j.consume(source_sha256=source,handoff_sha256='7'*64,challenge_commitment_hash=challenge,
                     transcript_sha256='9'*64,terminal_action=terminal)


def rehash(rows):
    head='0'*64;out=b''
    for i,b in enumerate(rows):
        row=tj.event(b,i,head);head=row['hash'];out+=canonical(row)+b'\n'
    return out,head


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'journal.jsonl';self.binding=bind()
        self.j=tj.TransitionJournal(self.path,expected_binding=self.binding);self.addCleanup(self.j.close)
    def test_header_replays(self):
        self.assertEqual(tj.replay(self.j.journal_bytes(),expected_head=self.j.state.head,
                                  expected_binding=self.binding).status,'open')
    def test_binding_detached(self):
        self.binding['scope_id']='0'*64;self.assertEqual(self.j.binding['scope_id'],'1'*64)
    def test_invalid_boolean_index_rejected(self):
        r=load_json_strict(self.j.journal_bytes().splitlines()[0]);r['index']=False
        with self.assertRaises(ValueError):tj.replay(canonical(r)+b'\n',expected_head=r['hash'],expected_binding=bind())
    def test_changed_external_head_rejected(self):
        with self.assertRaises(ValueError):tj.replay(self.j.journal_bytes(),expected_head='f'*64,expected_binding=bind())
    def test_changed_external_binding_rejected(self):
        b=bind();b['predecessor_physical_hash']='f'*64
        with self.assertRaises(ValueError):tj.replay(self.j.journal_bytes(),expected_head=self.j.state.head,expected_binding=b)
    def test_begin_consumes_before_result(self):
        consume(self.j);s=self.j.state;self.assertEqual(s.consumed,('8'*64,));self.assertEqual(s.status,'pending')
        self.assertEqual(tj.replay(self.path.read_bytes(),expected_head=s.head,expected_binding=bind()).pending,s.pending)
    def test_pending_cannot_consume(self):
        consume(self.j)
        with self.assertRaises(ValueError):consume(self.j,source='a'*64,challenge='b'*64)
    def test_pending_cannot_stop(self):
        consume(self.j)
        with self.assertRaises(ValueError):self.j.stop()
    def test_complete_without_begin_rejected(self):
        with self.assertRaises(ValueError):self.j.complete(transaction='1'*64,outcome='no_candidate',report_sha256='2'*64)
    def test_wrong_completion_id_rejected(self):
        consume(self.j)
        with self.assertRaises(ValueError):self.j.complete(transaction='1'*64,outcome='blocked_missing_root_witnesses',report_sha256='2'*64)
    def test_pass_is_not_authorization(self):
        tid=consume(self.j)
        with self.assertRaises(ValueError):self.j.complete(transaction=tid,outcome='accepted',report_sha256='2'*64)
    def test_successful_stage_still_blocked(self):
        tid=consume(self.j);self.j.complete(transaction=tid,outcome='blocked_missing_root_witnesses',report_sha256='2'*64)
        self.assertEqual(len(self.j.state.completed),1);self.assertEqual(self.j.state.consumed,('8'*64,))
    def test_exhausted_cannot_claim_staged_candidate(self):
        tid=consume(self.j,terminal='resource_exhausted')
        with self.assertRaises(ValueError):self.j.complete(transaction=tid,outcome='blocked_missing_root_witnesses',report_sha256='2'*64)
    def test_no_candidate_is_completed_consumption(self):
        tid=consume(self.j,terminal='search_exhausted');self.j.complete(transaction=tid,outcome='no_candidate',report_sha256='2'*64)
        self.assertEqual(self.j.state.status,'open');self.assertEqual(len(self.j.state.consumed),1)
    def test_same_challenge_different_source_rejected(self):
        tid=consume(self.j);self.j.complete(transaction=tid,outcome='blocked_missing_root_witnesses',report_sha256='2'*64)
        with self.assertRaises(ValueError):consume(self.j,source='a'*64)
    def test_same_source_different_challenge_rejected(self):
        tid=consume(self.j);self.j.complete(transaction=tid,outcome='blocked_missing_root_witnesses',report_sha256='2'*64)
        with self.assertRaises(ValueError):consume(self.j,challenge='a'*64)
    def test_explicit_abandon_retains_consumption(self):
        consume(self.j);self.j.abort(interrupted=True)
        self.assertEqual(self.j.state.consumed,('8'*64,));self.assertEqual(self.j.state.status,'safety_halt')
        with self.assertRaises(ValueError):consume(self.j,source='a'*64,challenge='b'*64)
    def test_abandon_without_pending_rejected(self):
        with self.assertRaises(ValueError):self.j.abort()
    def test_abandon_flag_not_integer(self):
        consume(self.j)
        with self.assertRaises(ValueError):self.j.abort(interrupted=1)
    def test_reopen_requires_external_head(self):
        self.j.close()
        with self.assertRaises(ValueError):tj.TransitionJournal(self.path,expected_binding=bind())
    def test_reopen_pending_no_auto_resume(self):
        consume(self.j);s=self.j.state;self.j.close()
        with tj.TransitionJournal(self.path,expected_binding=bind(),expected_head=s.head) as j:
            self.assertEqual(j.state,s)
            with self.assertRaises(ValueError):consume(j)
    def test_reopen_completed_preserves_consumption(self):
        tid=consume(self.j);self.j.complete(transaction=tid,outcome='blocked_missing_root_witnesses',report_sha256='2'*64)
        s=self.j.state;self.j.close()
        with tj.TransitionJournal(self.path,expected_binding=bind(),expected_head=s.head) as j:self.assertEqual(j.state,s)
    def test_closed_journal_refuses(self):
        self.j.close()
        with self.assertRaises(ValueError):consume(self.j)
    def test_competing_writer_refused(self):
        with self.assertRaises((OSError,ValueError)):tj.TransitionJournal(self.path,expected_binding=bind(),expected_head=self.j.state.head)
    def test_external_mutation_blocks(self):
        with self.path.open('ab') as f:f.write(b'\n')
        with self.assertRaises(ValueError):consume(self.j)
    def test_truncated_line_rejected(self):
        with self.assertRaises(ValueError):tj.replay(self.j.journal_bytes()[:-1],expected_head=self.j.state.head,expected_binding=bind())
    def test_crlf_rejected(self):
        with self.assertRaises(ValueError):tj.replay(self.j.journal_bytes().replace(b'\n',b'\r\n'),expected_head=self.j.state.head,expected_binding=bind())
    def test_unknown_event_rejected_even_rehashed(self):
        bodies=[load_json_strict(x)['body'] for x in self.j.journal_bytes().splitlines()]+[{'kind':'promote'}]
        raw,h=rehash(bodies)
        with self.assertRaises(ValueError):tj.replay(raw,expected_head=h,expected_binding=bind())
    def test_missing_consume_even_rehashed(self):
        b=load_json_strict(self.j.journal_bytes().splitlines()[0])['body']
        raw,h=rehash([b,{'kind':'complete','transaction_id':'1'*64,'outcome':'no_candidate','report_sha256':'2'*64}])
        with self.assertRaises(ValueError):tj.replay(raw,expected_head=h,expected_binding=bind())
    def test_unknown_fields_even_rehashed(self):
        b=load_json_strict(self.j.journal_bytes().splitlines()[0])['body'];b['accepted']=True
        raw,h=rehash([b])
        with self.assertRaises(ValueError):tj.replay(raw,expected_head=h,expected_binding=bind())
    def test_fsync_failure_poisons_before_caller_proceeds(self):
        with patch.object(tj.os,'fsync',side_effect=OSError('injected')):
            with self.assertRaises(OSError):consume(self.j)
        with self.assertRaises(ValueError):self.j.journal_bytes()
    def test_no_refund_event(self):
        consume(self.j);bodies=[load_json_strict(x)['body'] for x in self.j.journal_bytes().splitlines()]
        raw,h=rehash(bodies+[{'kind':'unconsume','challenge_commitment_hash':'8'*64}])
        with self.assertRaises(ValueError):tj.replay(raw,expected_head=h,expected_binding=bind())
    def test_stopped_prefix_cannot_continue(self):
        self.j.stop()
        with self.assertRaises(ValueError):consume(self.j)
    def test_source_hash_is_strict(self):
        with self.assertRaises(ValueError):consume(self.j,source=True)
    def test_actual_process_exit_retains_consumption(self):
        self.j.close();target=Path(self.tmp.name)/'child.jsonl'
        code="""import os,sys,json
from pathlib import Path
from rcp_rclm_runtime_v5.phase17.transition_journal import TransitionJournal
b=json.loads(sys.argv[2])
j=TransitionJournal(Path(sys.argv[1]),expected_binding=b)
j.consume(source_sha256='6'*64,handoff_sha256='7'*64,challenge_commitment_hash='8'*64,transcript_sha256='9'*64,terminal_action='await_root_verification')
Path(sys.argv[1]+'.head').write_text(j.state.head,encoding='ascii')
os._exit(29)
"""
        p=subprocess.run([sys.executable,'-B','-c',code,str(target),json.dumps(bind())],capture_output=True,timeout=30)
        self.assertEqual(p.returncode,29,p.stderr.decode(errors='replace'))
        head=Path(str(target)+'.head').read_text(encoding='ascii')
        with tj.TransitionJournal(target,expected_binding=bind(),expected_head=head) as j:
            self.assertEqual(j.state.status,'pending');self.assertEqual(j.state.consumed,('8'*64,));j.abort(interrupted=True)


class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=load_predecessor(ROOT);cls.fixture=fixture_capsule(ROOT)
        cls.tmp=tempfile.TemporaryDirectory();d=Path(cls.tmp.name)
        policy=full_grammar_policy(len(cls.parent.accepted_programs),candidate_limit=0)
        ctx=context_for(cls.parent,'a'*64)
        with CampaignAuthority(d/'campaign.jsonl',policy=policy,expected_context=ctx) as a:
            records=run_campaign_session(a,cls.parent,candidate_credits=0)
            grant=load_json_strict(records['grant.json'])['grant_hash']
            cls.online=campaign_capsule(journal=a.journal_bytes(),expected_head=a.state.head,policy=policy,
                                       expected_context=ctx,sessions={grant:records},selected_grant_hash=grant)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def check(self,raw):return checked_handoff(self.parent,raw,expected_source_hash=sha(raw))
    def mutated(self,raw,fn):
        p=load_json_strict(raw);fn(p)
        with self.assertRaises((ValueError,KeyError,TypeError)):self.check(canonical(p))
    def test_actual_worker_source_verified(self):
        h=self.check(self.online);self.assertEqual(h.record['terminal_action'],'resource_exhausted')
        self.assertEqual(h.record['session_reserved'],[0,72,288,288])
    def test_fixture_is_explicit_not_live(self):
        r=self.check(self.fixture).record;self.assertEqual(r['source_kind'],'retained_synthetic_fixture')
        self.assertIsNone(r['campaign_head']);self.assertEqual(r['candidate_evaluations'],9)
    def test_external_source_anchor_required(self):
        with self.assertRaises(ValueError):checked_handoff(self.parent,self.online,expected_source_hash='f'*64)
    def test_extra_source_field_rejected(self):self.mutated(self.online,lambda p:p.update(root_transition_verified=True))
    def test_fixture_cannot_relabel_online(self):self.mutated(self.fixture,lambda p:p.update(kind='online_campaign'))
    def test_online_cannot_relabel_fixture(self):self.mutated(self.online,lambda p:p.update(kind='retained_synthetic_fixture'))
    def test_fixture_bytes_cannot_change(self):self.mutated(self.fixture,lambda p:p.update(transcript_hex=(bytes.fromhex(p['transcript_hex'])+b' ').hex()))
    def test_wrong_campaign_head_rejected(self):self.mutated(self.online,lambda p:p.update(campaign_head='f'*64))
    def test_missing_session_rejected(self):self.mutated(self.online,lambda p:p.update(sessions_hex={}))
    def test_wrong_selected_grant_rejected(self):self.mutated(self.online,lambda p:p.update(selected_grant_hash='f'*64))
    def test_changed_policy_rejected(self):self.mutated(self.online,lambda p:p['policy'].update(cost_limit=99999))
    def test_changed_context_rejected(self):self.mutated(self.online,lambda p:p['context'].update(predecessor_package_hash='f'*64))
    def test_record_access_detached(self):
        h=self.check(self.fixture);r=h.record;r['promotion_authorized']=True;self.assertIs(h.record['promotion_authorized'],False)
    def test_uppercase_hex_rejected(self):
        with self.assertRaises(ValueError):unhex('AF')
    def test_duplicate_json_fields_rejected(self):
        with self.assertRaises(ValueError):parse(b'{"schema":"a","schema":"b"}')
    def test_noncanonical_source_rejected(self):
        with self.assertRaises(ValueError):parse(self.fixture+b'\n')
    def test_mutable_input_refused(self):
        with self.assertRaises(ValueError):parse(bytearray(self.fixture))
    def test_wrong_session_checkpoint_rejected(self):
        def change(p):
            d=next(iter(p['sessions_hex'].values()));d['controller_checkpoint.json']=canonical({'forged':True}).hex()
        self.mutated(self.online,change)


class StagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.work=Path(cls.tmp.name);cls.e=cls.work/'e';cls.e.mkdir()
        cls.w=cls.work/'w';cls.w.mkdir();cls.raw=fixture_capsule(ROOT)
        cls.b=st.binding_for(ROOT,cls.raw,expected_source_hash=sha(cls.raw),mode='retained_synthetic_fixture')
        with tj.TransitionJournal(cls.e/'journal.jsonl',expected_binding=cls.b) as j:
            cls.report=st.stage_handoff(ROOT,j,cls.raw,expected_source_hash=sha(cls.raw),packages_root=cls.w)
            cls.head=j.state.head
        cls.tid=cls.report['transaction_id'];cls.folder=cls.e/'transactions'/cls.tid
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_physical_positive_candidate_inactive(self):
        r=self.report
        self.assertEqual(r['candidate_physical_hash'],'b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e')
        self.assertEqual(r['outcome'],'blocked_missing_root_witnesses')
        self.assertIs(r['active_store_written'],False);self.assertIs(r['root_acceptance_evaluated'],False)
    def test_all_nonclaims_false(self):self.assertTrue(all(v is False for v in self.report['claims'].values()))
    def test_physical_and_logical_hashes_not_conflated(self):self.assertNotEqual(self.report['predecessor_logical_hash'],self.report['predecessor_physical_hash'])
    def test_exact_dossier_inventory(self):self.assertEqual(set(st.read_tree(self.folder)),{'source.json','handoff.json','assessment.json','predecessor-manifest.json','candidate-manifest.json','joint-evidence.json'})
    def test_fixture_refused_by_online_binding(self):
        with self.assertRaises(ValueError):st.binding_for(ROOT,self.raw,expected_source_hash=sha(self.raw),mode='online_campaign')
    def test_replay_without_worker_or_new_entropy(self):
        with patch('rcp_rclm_runtime_v5.phase17.campaign_transaction.CampaignEvaluatorClient',side_effect=AssertionError('worker')):
            result=st.audit_staging(ROOT,self.e,expected_head=self.head,expected_binding=self.b)
        self.assertEqual(result['completed'],1);self.assertEqual(result['reports'][0],self.report)
    def test_report_tamper_fails(self):
        path=self.folder/'assessment.json';raw=path.read_bytes()
        try:
            r=load_json_strict(raw);r['claims']['promotion_authorized']=True;path.write_bytes(canonical(r))
            with self.assertRaises(ValueError):st.audit_staging(ROOT,self.e,expected_head=self.head,expected_binding=self.b)
        finally:path.write_bytes(raw)
    def test_extra_dossier_file_fails(self):
        path=self.folder/'invented-proof.json';path.write_bytes(b'{}')
        try:
            # Inventory is independently reconstructed; no caller proof report accepted.
            state=tj.replay((self.e/'journal.jsonl').read_bytes(),expected_head=self.head,expected_binding=self.b)
            entry=load_json_strict(state.completed[0])
            with patch.object(st,'_construct',return_value={k:v for k,v in st.read_tree(self.folder).items() if k!='invented-proof.json'}):
                with self.assertRaises(ValueError):st.verify_dossier(ROOT,self.folder,entry['begin'],entry['completion'],self.b)
        finally:path.unlink()
    def test_duplicate_handoff_no_new_consumption(self):
        with tj.TransitionJournal(self.e/'journal.jsonl',expected_binding=self.b,expected_head=self.head) as j:
            before=j.journal_bytes()
            with patch.object(st,'audit_staging',return_value={}):
                with self.assertRaises(ValueError):st.stage_handoff(ROOT,j,self.raw,expected_source_hash=sha(self.raw),packages_root=self.w)
            self.assertEqual(j.journal_bytes(),before)
    def test_missing_dossier_blocks_next_staging(self):
        moved=self.folder.with_name('saved-dossier');self.folder.rename(moved)
        try:
            with tj.TransitionJournal(self.e/'journal.jsonl',expected_binding=self.b,expected_head=self.head) as j:
                with self.assertRaises(ValueError):st.stage_handoff(ROOT,j,self.raw,expected_source_hash=sha(self.raw),packages_root=self.w)
                self.assertEqual(j.state.head,self.head)
        finally:moved.rename(self.folder)
    def test_failure_after_consume_keeps_challenge(self):
        e=self.work/'failure';e.mkdir();w=self.work/'failed-work';w.mkdir()
        with tj.TransitionJournal(e/'journal.jsonl',expected_binding=self.b) as j:
            with patch.object(st,'_construct',side_effect=OSError('injected')):
                with self.assertRaises(OSError):st.stage_handoff(ROOT,j,self.raw,expected_source_hash=sha(self.raw),packages_root=w)
            self.assertEqual(j.state.status,'safety_halt');self.assertEqual(len(j.state.consumed),1)
            saved=e/'transactions'/tj.transaction_id(sha(self.raw),self.b['predecessor_physical_hash'])
            self.assertEqual((saved/'source.json').read_bytes(),self.raw)
    def test_consume_fsync_precedes_materialization(self):
        e=self.work/'durability';e.mkdir();w=self.work/'durability-work';w.mkdir()
        with tj.TransitionJournal(e/'journal.jsonl',expected_binding=self.b) as j:
            with patch.object(tj.os,'fsync',side_effect=OSError('disk')),patch.object(st,'_construct') as build:
                with self.assertRaises(OSError):st.stage_handoff(ROOT,j,self.raw,expected_source_hash=sha(self.raw),packages_root=w)
                build.assert_not_called()
    def test_root_blockers_not_hidden(self):self.assertEqual(self.report['root_blockers'],st.BLOCKERS)
    def test_unmeasured_materialization_not_zeroed(self):self.assertIn('candidate_materialization',self.report['unmeasured'])
    def test_no_arbitrary_acceptance_callback(self):
        import inspect
        names=set(inspect.signature(st.stage_handoff).parameters)
        self.assertEqual(names,{'root','journal','source','expected_source_hash','packages_root'})

    def test_wrong_physical_parent_before_consume(self):
        e=self.work/'wrong-parent';e.mkdir();w=self.work/'wrong-parent-work';w.mkdir()
        b={**self.b,'predecessor_physical_hash':'f'*64}
        with tj.TransitionJournal(e/'journal.jsonl',expected_binding=b) as j:
            head=j.state.head
            with self.assertRaises(ValueError):st.stage_handoff(ROOT,j,self.raw,expected_source_hash=sha(self.raw),packages_root=w)
            self.assertEqual(j.state.head,head);self.assertEqual(j.state.consumed,())
    def test_package_workspace_cannot_be_source(self):
        e=self.work/'wrong-work';e.mkdir()
        with tj.TransitionJournal(e/'journal.jsonl',expected_binding=self.b) as j:
            head=j.state.head
            with self.assertRaises(ValueError):st.stage_handoff(ROOT,j,self.raw,expected_source_hash=sha(self.raw),packages_root=ROOT)
            self.assertEqual(j.state.head,head)
