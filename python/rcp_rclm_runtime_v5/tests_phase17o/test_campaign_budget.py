"""Phase17O tests. Explicit deterministic fixtures are not live campaign results."""
from __future__ import annotations
import copy
import inspect
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17.campaign_budget import (
    CampaignAuthority, event, context, make_grant, validate_grant, replay,
)
from rcp_rclm_runtime_v5.phase17.campaign_client import CampaignEvaluatorClient
from rcp_rclm_runtime_v5.phase17.campaign_transaction import (
    load_predecessor, context_for, check_controller, run_campaign_session, audit_campaign,
)
from rcp_rclm_runtime_v5.phase17.challenge_protocol import (
    EvaluatorSession, PROTOCOL, transcript_bytes, realize_candidate, digest, _outcomes,
)
from rcp_rclm_runtime_v5.phase17.controller import Action, ControlError, decide, record_evaluation
from rcp_rclm_runtime_v5.phase17.metered_worker import MeteredEvaluatorSession, WorkMeter, verify_metered_transcript
from rcp_rclm_runtime_v5.phase17.objectives import select_bootstrap_objective, freeze_bootstrap_objective
from rcp_rclm_runtime_v5.phase17.phase16_adapter import bind_phase16_search
from rcp_rclm_runtime_v5.phase17.resource_ledger import (
    Policy, ResourceError, ResourceExhausted, canonical, cost, full_grammar_policy,
)

ROOT = Path(__file__).resolve().parents[3]
PARENT = None
ENTROPY = b'\x42' * 32  # Test-only replay, never passed over the live worker protocol.


def parent():
    global PARENT
    if PARENT is None:
        PARENT = load_predecessor(ROOT)
    return PARENT


def fixture(credits=2, index=0, previous='0'*64, nonce='2'*64):
    p = parent()
    obj = select_bootstrap_objective(p, turn_index=index, public_nonce_hash=nonce)
    freeze = freeze_bootstrap_objective(obj, p, turn_index=index, public_nonce_hash=nonce)
    ctx = context_for(p, '1'*64)
    grant = make_grant(ctx, index, previous, freeze['freeze_hash'], credits)
    req = {'protocol': PROTOCOL, 'op': 'open', 'objective': obj.to_json(), 'freeze': freeze,
           'candidate_credits': credits}
    return p, ctx, grant, req


def sealed(grant, request, *, reverse=False):
    p = parent()
    s = MeteredEvaluatorSession(p, grant)
    public = s._handle(request, replay_entropy=ENTROPY)['payload']['public_challenge']
    bound = bind_phase16_search(p.phase16_state(), turn_index=public['turn_index'],
        challenge_commitment_hash=public['challenge_commitment_hash'],
        public_nonce_hash=public['public_nonce_hash'], candidate_credits=grant['candidate_credits'])
    prefix = bound.prefix
    while decide(prefix).action == Action.EVALUATE:
        chosen = decide(prefix).candidate_hash
        if reverse:
            chosen = next(h for h in reversed(sorted(s.programs)) if h not in s.considered and h != chosen)
        artifact = realize_candidate(s.programs[chosen], request['freeze'])
        receipt = s.handle({'protocol': PROTOCOL, 'op': 'freeze_candidate',
            'program_hash': chosen, 'artifact_hash': artifact['artifact_hash']})['payload']['receipt']
        report = s.handle({'protocol': PROTOCOL, 'op': 'evaluate', 'artifact': artifact,
            'candidate_freeze_hash': receipt['candidate_freeze_hash']})['payload']
        if reverse:
            break
        prefix = record_evaluation(prefix, decide(prefix), verdict=report['verdict'],
            evaluation_hash=report['evaluation_hash'], reason_codes=report['reason_codes'],
            predecessor_state_hash=report['predecessor_state_hash'],
            challenge_commitment_hash=report['challenge_commitment_hash'])
    terminal = s.terminal() or Action.EXTERNAL_STOP.value
    s.handle({'protocol': PROTOCOL, 'op': 'seal', 'terminal_action': terminal})
    return transcript_bytes(s.events), s.meter.summary()


def rehash(raw, mutate):
    bodies = [load_json_strict(x)['body'] for x in raw.splitlines()]
    mutate(bodies)
    head = '0'*64
    result = b''
    for i, body in enumerate(bodies):
        e = event(body, i, head)
        result += canonical(e) + b'\n'
        head = e['hash']
    return result, head


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'campaign.jsonl'
        self.p, self.ctx, self.g, self.req = fixture()
        one = full_grammar_policy(8, candidate_limit=2)
        self.policy = Policy(tuple(x*2 for x in one.limits), one.cost_limit*2)
        self.a = CampaignAuthority(self.path, policy=self.policy, expected_context=self.ctx)

    def tearDown(self):
        self.a.close()
        self.tmp.cleanup()

    def reserve(self):
        return self.a.reserve(objective_freeze_hash=self.req['freeze']['freeze_hash'], candidate_credits=2)

    def complete(self):
        g = self.reserve()
        raw, accounting = sealed(g, self.req)
        self.a.complete(self.p, transcript=raw, accounting=accounting)
        return raw, accounting

    def test_reservation_is_durable_before_launch(self):
        g = self.reserve()
        state = replay(self.path.read_bytes(), expected_head=self.a.state.head,
                       policy=self.policy, expected_context=self.ctx)
        self.assertEqual(state.pending_grant, g)
        self.assertEqual(state.reserved, (2,88,352,352))

    def test_failure_keeps_full_not_actual_charge(self):
        self.reserve(); before = self.a.state.reserved; self.a.fail()
        self.assertEqual(self.a.state.reserved, before)
        self.assertEqual(self.a.state.status, 'safety_halt')

    def test_explicit_abandon_keeps_charge(self):
        self.reserve(); self.a.fail(interrupted=True)
        self.assertEqual(self.a.state.charged_cost,2240)
        with self.assertRaises(ResourceError): self.reserve()

    def test_cannot_stop_pending(self):
        self.reserve()
        with self.assertRaises(ResourceError): self.a.stop()

    def test_cannot_reserve_pending(self):
        self.reserve()
        with self.assertRaises(ResourceError): self.reserve()

    def test_existing_path_cannot_reset(self):
        self.a.close()
        with self.assertRaises(ResourceError):
            CampaignAuthority(self.path, policy=self.policy, expected_context=self.ctx)

    def test_reopen_preserves_pending_no_auto_rerun(self):
        self.reserve(); head=self.a.state.head; self.a.close()
        with CampaignAuthority(self.path, policy=self.policy, expected_context=self.ctx, expected_head=head) as b:
            self.assertEqual(b.state.status,'pending')
            with self.assertRaises(ResourceError): b.reserve(objective_freeze_hash='8'*64,candidate_credits=1)
            b.fail(interrupted=True)
            self.assertEqual(b.state.reserved,(2,88,352,352))

    def test_reopen_completed_preserves_budget(self):
        self.complete(); head=self.a.state.head; self.a.close()
        with CampaignAuthority(self.path,policy=self.policy,expected_context=self.ctx,expected_head=head) as b:
            self.assertEqual(b.state.session_count,1)
            self.assertEqual(b.state.reserved,(2,88,352,352))

    def test_complete_has_no_refund(self):
        self.complete()
        self.assertEqual(self.a.state.reserved,(2,88,352,352))
        self.assertEqual(self.a.state.status,'open')

    def test_duplicate_freeze_rejected(self):
        self.complete()
        with self.assertRaises(ResourceError): self.reserve()

    def test_external_head_required_not_self_hash(self):
        self.reserve()
        with self.assertRaises(ResourceError):
            replay(self.path.read_bytes(),expected_head='f'*64,policy=self.policy,expected_context=self.ctx)

    def test_wrong_context_rejected(self):
        c=copy.deepcopy(self.ctx); c['campaign_id']='9'*64
        with self.assertRaises(ResourceError):
            replay(self.path.read_bytes(),expected_head=self.a.state.head,policy=self.policy,expected_context=c)

    def test_wrong_policy_rejected(self):
        with self.assertRaises(ResourceError):
            replay(self.path.read_bytes(),expected_head=self.a.state.head,
                   policy=Policy((0,0,0,0),0),expected_context=self.ctx)

    def test_rehashed_forged_aggregate_rejected(self):
        self.reserve()
        raw,h=rehash(self.path.read_bytes(),lambda rows:rows[-1]['reserved_after'].__setitem__(0,0))
        with self.assertRaises(ResourceError): replay(raw,expected_head=h,policy=self.policy,expected_context=self.ctx)

    def test_rehashed_boolean_aggregate_rejected(self):
        self.reserve()
        raw,h=rehash(self.path.read_bytes(),lambda rows:rows[-1]['reserved_after'].__setitem__(0,True))
        with self.assertRaises(ResourceError): replay(raw,expected_head=h,policy=self.policy,expected_context=self.ctx)

    def test_rehashed_wrong_completion_inventory(self):
        self.complete()
        raw,h=rehash(self.path.read_bytes(),lambda rows:rows[-1]['worker_spent'].__setitem__(1,1))
        with self.assertRaises(ResourceError): replay(raw,expected_head=h,policy=self.policy,expected_context=self.ctx)

    def test_rehashed_completion_without_reservation(self):
        self.complete()
        raw,h=rehash(self.path.read_bytes(),lambda rows:rows.pop(1))
        with self.assertRaises(ResourceError): replay(raw,expected_head=h,policy=self.policy,expected_context=self.ctx)

    def test_false_exhaustion_denial_rejected(self):
        g=make_grant(self.ctx,0,self.a.state.head,'f'*64,1)
        raw=self.path.read_bytes(); e=event({'kind':'deny','grant':g},1,self.a.state.head)
        with self.assertRaises(ResourceError):
            replay(raw+canonical(e)+b'\n',expected_head=e['hash'],policy=self.policy,expected_context=self.ctx)

    def test_truncation_rejected(self):
        with self.assertRaises(ResourceError): replay(self.path.read_bytes()[:-1],expected_head=self.a.state.head,policy=self.policy,expected_context=self.ctx)

    def test_crlf_rejected(self):
        with self.assertRaises(ResourceError): replay(self.path.read_bytes().replace(b'\n',b'\r\n'),expected_head=self.a.state.head,policy=self.policy,expected_context=self.ctx)

    def test_mutated_file_prevents_reserve(self):
        with self.path.open('ab') as f:f.write(b' ')
        with self.assertRaises(ResourceError):self.reserve()

    def test_fsync_failure_prevents_authorization(self):
        with patch('rcp_rclm_runtime_v5.phase17.campaign_budget.os.fsync',side_effect=OSError('fixture')):
            with self.assertRaises(OSError):self.reserve()
        with self.assertRaises(ResourceError):self.a.state

    def test_missing_prior_evidence_blocks_before_next_reservation(self):
        self.complete();before=self.a.state
        with patch('rcp_rclm_runtime_v5.phase17.campaign_transaction.CampaignEvaluatorClient') as client:
            with self.assertRaises(ControlError):run_campaign_session(self.a,self.p,candidate_credits=2)
            client.assert_not_called()
        self.assertEqual(self.a.state,before)

    def test_linked_campaign_path_rejected(self):
        with patch('rcp_rclm_runtime_v5.phase17.resource_ledger.Path.is_symlink',return_value=True):
            with self.assertRaises(ResourceError):
                CampaignAuthority(Path(self.tmp.name)/'other',policy=self.policy,expected_context=self.ctx)

    def test_rehashed_grant_context_substitution_rejected(self):
        self.reserve()
        def change(rows):
            old=rows[-1]['grant'];ctx=copy.deepcopy(self.ctx);ctx['campaign_id']='7'*64
            rows[-1]['grant']=make_grant(ctx,old['session_index'],old['previous_campaign_head'],old['objective_freeze_hash'],2)
        raw,h=rehash(self.path.read_bytes(),change)
        with self.assertRaises(ResourceError):replay(raw,expected_head=h,policy=self.policy,expected_context=self.ctx)

    def test_rehashed_completion_cannot_claim_search_complete(self):
        self.complete()
        raw,h=rehash(self.path.read_bytes(),lambda rows:rows[-1].__setitem__('terminal_action','search_exhausted'))
        with self.assertRaises(ResourceError):replay(raw,expected_head=h,policy=self.policy,expected_context=self.ctx)

    def test_whole_grant_cannot_be_refunded_by_completion(self):
        self.complete()
        raw,h=rehash(self.path.read_bytes(),lambda rows:rows[-1].__setitem__('refund',[1,8,32,32]))
        with self.assertRaises(ResourceError):replay(raw,expected_head=h,policy=self.policy,expected_context=self.ctx)

    def test_context_detached(self):
        self.ctx['campaign_id']='8'*64
        self.assertEqual(self.a.context['campaign_id'],'1'*64)
        obj=self.a.context;obj['campaign_id']='7'*64
        self.assertEqual(self.a.context['campaign_id'],'1'*64)

    def test_pending_grant_detached(self):
        self.reserve(); x=self.a.state.pending_grant;x['candidate_credits']=32
        self.assertEqual(self.a.state.pending_grant['candidate_credits'],2)

    def test_closed_handle_rejected(self):
        self.a.close()
        with self.assertRaises(ResourceError): self.reserve()

    def test_competing_authority_blocked(self):
        with self.assertRaises((ResourceError,OSError)):
            CampaignAuthority(self.path,policy=self.policy,expected_context=self.ctx,expected_head=self.a.state.head)

    def test_unordered_but_evaluator_valid_trace_rejected(self):
        g=self.reserve();raw,meter=sealed(g,self.req,reverse=True)
        verify_metered_transcript(self.p,g,raw,meter)
        with self.assertRaises(ControlError):self.a.complete(self.p,transcript=raw,accounting=meter)
        self.assertEqual(self.a.state.status,'pending')

    def test_complete_wrong_meter_rejected(self):
        g=self.reserve();raw,meter=sealed(g,self.req);meter['charged_cost']=0
        with self.assertRaises(ControlError):self.a.complete(self.p,transcript=raw,accounting=meter)

    def test_boolean_credits_rejected_before_write(self):
        before=self.path.read_bytes()
        with self.assertRaises(ResourceError):self.a.reserve(objective_freeze_hash='8'*64,candidate_credits=True)
        self.assertEqual(self.path.read_bytes(),before)

    def test_external_stop_terminal(self):
        self.a.stop()
        with self.assertRaises(ResourceError): self.reserve()


class GrantAndWorkerTests(unittest.TestCase):
    def setUp(self):
        self.p,self.ctx,self.grant,self.req=fixture()

    def test_grant_tamper_rejected(self):
        x=copy.deepcopy(self.grant);x['candidate_credits']=3
        with self.assertRaises(ResourceError): validate_grant(x)

    def test_extra_grant_fields_rejected(self):
        x=copy.deepcopy(self.grant);x['seed']='private'
        with self.assertRaises(ResourceError): validate_grant(x)

    def test_wrong_verifier_rejected(self):
        x=copy.deepcopy(self.ctx);x['fixed_verifier_hash']='f'*64
        with self.assertRaises(ResourceError):context(x)

    def test_limits_are_exact_not_caller_selected(self):
        x=copy.deepcopy(self.grant);x['envelope']['limits'][0]=0
        with self.assertRaises(ResourceError):validate_grant(x)

    def test_wrong_parent_rejected(self):
        ctx=copy.deepcopy(self.ctx);ctx['predecessor_state_hash']='9'*64
        g=make_grant(ctx,0,'0'*64,self.grant['objective_freeze_hash'],2)
        with self.assertRaises(ControlError):MeteredEvaluatorSession(self.p,g)

    def test_freeze_rejected_before_entropy(self):
        s=MeteredEvaluatorSession(self.p,self.grant);r=copy.deepcopy(self.req);r['freeze']['freeze_hash']='a'*64
        with patch('rcp_rclm_runtime_v5.phase17.challenge_protocol.secrets.token_bytes') as random:
            with self.assertRaises(ControlError):s.handle(r)
            random.assert_not_called()

    def test_credit_substitution_before_entropy(self):
        s=MeteredEvaluatorSession(self.p,self.grant);r=copy.deepcopy(self.req);r['candidate_credits']=1
        with patch('rcp_rclm_runtime_v5.phase17.challenge_protocol.secrets.token_bytes') as random:
            with self.assertRaises(ControlError):s.handle(r)
            random.assert_not_called()

    def test_live_wire_forbids_seed_override(self):
        s=MeteredEvaluatorSession(self.p,self.grant);r=copy.deepcopy(self.req);r['replay_entropy']='42'*32
        with self.assertRaises(ControlError):s.handle(r)

    def test_no_horizon_or_success_count_argument(self):
        self.assertEqual(set(inspect.signature(run_campaign_session).parameters),
                         {'authority','predecessor','candidate_credits','public_nonce_hash','prior_sessions'})

    def test_zero_candidates_still_charge_setup(self):
        p,c,g,r=fixture(0);raw,m=sealed(g,r)
        self.assertEqual(m['spent'],[0,72,288,288])
        self.assertEqual(verify_metered_transcript(p,g,raw,m)['terminal_action'],'resource_exhausted')

    def test_every_inherited_program_and_probe_charged(self):
        s=MeteredEvaluatorSession(self.p,self.grant);s._handle(self.req,replay_entropy=ENTROPY)
        self.assertEqual(s.meter.spent,(0,72,288,288))
        self.assertEqual(s.meter.operation_count,72)

    def test_summary_hidden_before_seal(self):
        s=MeteredEvaluatorSession(self.p,self.grant);s._handle(self.req,replay_entropy=ENTROPY)
        with self.assertRaises(ControlError):s.meter.summary()

    def test_worker_accounts_all_probes_no_shortcut(self):
        raw,m=sealed(self.grant,self.req)
        result=verify_metered_transcript(self.p,self.grant,raw,m)
        n=result['candidate_evaluations']
        self.assertEqual(m['spent'],[n,72+8*n,4*(72+8*n),4*(72+8*n)])

    def test_original_transcript_semantics_unchanged(self):
        raw,m=sealed(self.grant,self.req)
        from rcp_rclm_runtime_v5.phase17.challenge_protocol import verify_transcript
        result=verify_transcript(self.p,raw,expected_transcript_hash=__import__('hashlib').sha256(raw).hexdigest())
        self.assertEqual(result.candidate_evaluations,m['spent'][0])

    def test_wrong_meter_head_rejected(self):
        raw,m=sealed(self.grant,self.req);m['head']='f'*64
        with self.assertRaises(ControlError):verify_metered_transcript(self.p,self.grant,raw,m)

    def test_wrong_grant_transcript_binding(self):
        raw,m=sealed(self.grant,self.req)
        g=make_grant(self.ctx,0,'1'*64,self.grant['objective_freeze_hash'],2)
        with self.assertRaises(ControlError):verify_metered_transcript(self.p,g,raw,m)

    def test_failure_charge_kept_in_worker_meter(self):
        m=WorkMeter(self.grant,'a'*64)
        def fail():raise RuntimeError('controlled')
        with self.assertRaises(RuntimeError):m.perform('vector','a',{},fail)
        self.assertEqual(m.spent,(0,1,4,4));self.assertEqual(m.status,'failed')
        with self.assertRaises(ControlError):m.seal()

    def test_meter_denial_does_not_call(self):
        g=make_grant(self.ctx,0,'0'*64,self.grant['objective_freeze_hash'],0)
        m=WorkMeter(g,'a'*64)
        with patch('builtins.print') as cb:
            with self.assertRaises(ControlError):m.perform('candidate','x',{},cb)
            cb.assert_not_called()

    def test_duplicate_meter_operation_rejected(self):
        m=WorkMeter(self.grant,'a'*64);m.perform('vector','x',{},lambda:[0,0,0,0])
        with self.assertRaises(ControlError):m.perform('vector','x',{},lambda:[0,0,0,0])

    def test_timeout_limits_strict(self):
        for v in (0,-1,121,True,float('nan'),float('inf')):
            with self.subTest(v=v),self.assertRaises(ControlError): CampaignEvaluatorClient(self.grant,response_timeout=v)

    def test_all_32_program_verdicts_match_unchanged_reference(self):
        # Fixed test entropy is openly labeled. No live entropy search or winner filtering.
        p,c,g,r=fixture(32)
        base=MeteredEvaluatorSession(p,g);base._handle(r,replay_entropy=ENTROPY)
        for h,prog in base.programs.items():
            s=MeteredEvaluatorSession(p,g);s._handle(r,replay_entropy=ENTROPY)
            artifact=realize_candidate(prog,r['freeze'])
            f=s.handle({'protocol':PROTOCOL,'op':'freeze_candidate','program_hash':h,'artifact_hash':artifact['artifact_hash']})['payload']['receipt']
            ans=s.handle({'protocol':PROTOCOL,'op':'evaluate','artifact':artifact,'candidate_freeze_hash':f['candidate_freeze_hash']})['payload']
            verdict,reasons=_outcomes(s.secret,prog,p.accepted_programs)
            self.assertEqual((ans['verdict'],ans['reason_codes']),(verdict,reasons))
            self.assertEqual(s.meter.spent,(1,80,320,320))


class ProcessAndIntegrationTests(unittest.TestCase):
    def test_admission_denial_never_launches_worker(self):
        with tempfile.TemporaryDirectory() as d:
            ctx=context_for(parent(),'5'*64)
            with CampaignAuthority(Path(d)/'j',policy=Policy((0,0,0,0),0),expected_context=ctx) as a:
                with patch('rcp_rclm_runtime_v5.phase17.campaign_transaction.CampaignEvaluatorClient') as client:
                    with self.assertRaises(ResourceExhausted):run_campaign_session(a,parent(),candidate_credits=1)
                    client.assert_not_called()
                self.assertEqual(a.state.reserved,(0,0,0,0))
                self.assertEqual(a.state.status,'resource_exhausted')

    def test_launch_failure_keeps_grant_and_halts(self):
        with tempfile.TemporaryDirectory() as d:
            ctx=context_for(parent(),'5'*64);pol=full_grammar_policy(8,candidate_limit=2)
            with CampaignAuthority(Path(d)/'j',policy=pol,expected_context=ctx) as a:
                with patch('rcp_rclm_runtime_v5.phase17.campaign_transaction.CampaignEvaluatorClient',side_effect=OSError('launch')):
                    with self.assertRaises(OSError):run_campaign_session(a,parent(),candidate_credits=2)
                self.assertEqual(a.state.reserved,pol.limits);self.assertEqual(a.state.status,'safety_halt')

    def test_actual_worker_death_fails_closed(self):
        _,_,g,r=fixture(1)
        with CampaignEvaluatorClient(g) as w:
            self.assertNotEqual(w.process.pid,os.getpid());w.process.kill();w.process.wait(timeout=10)
            with self.assertRaises(ControlError):w.request('open',**{k:v for k,v in r.items() if k not in ('protocol','op')})

    def test_actual_process_exit_retains_pending_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'j';ctx=context_for(parent(),'6'*64);pol=full_grammar_policy(8,candidate_limit=1)
            code='''import os,sys,json
from pathlib import Path
from rcp_rclm_runtime_v5.phase17.campaign_budget import CampaignAuthority
from rcp_rclm_runtime_v5.phase17.resource_ledger import Policy
p=Path(sys.argv[1]);ctx=json.loads(sys.argv[2]);policy=Policy.from_json(json.loads(sys.argv[3]))
a=CampaignAuthority(p,policy=policy,expected_context=ctx)
a.reserve(objective_freeze_hash='8'*64,candidate_credits=1)
(p.parent/'head').write_text(a.state.head,encoding='ascii')
os._exit(37)
'''
            r=subprocess.run([sys.executable,'-B','-c',code,str(path),canonical(ctx).decode(),canonical(pol.to_json()).decode()],capture_output=True,timeout=30)
            self.assertEqual(r.returncode,37,r.stderr.decode(errors='replace'))
            head=(Path(d)/'head').read_text(encoding='ascii')
            with CampaignAuthority(path,policy=pol,expected_context=ctx,expected_head=head) as a:
                self.assertEqual(a.state.status,'pending');self.assertEqual(a.state.reserved,pol.limits)
                a.fail(interrupted=True)
                self.assertEqual(a.state.status,'safety_halt')

    def test_two_real_workers_restart_and_exhaustion(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'j';ctx=context_for(parent(),'7'*64);one=full_grammar_policy(8,candidate_limit=1)
            pol=Policy(tuple(x*2 for x in one.limits),one.cost_limit*2);evidence={};head=None
            for index in range(2):
                with CampaignAuthority(path,policy=pol,expected_context=ctx,expected_head=head) as a:
                    files=run_campaign_session(a,parent(),candidate_credits=1,prior_sessions=evidence)
                    report=load_json_strict(files['session.json'])
                    evidence[report['grant_hash']]=files
                    self.assertNotEqual(report['controller_pid'],report['worker_pid'])
                    self.assertEqual(a.state.session_count,index+1);head=a.state.head
            with CampaignAuthority(path,policy=pol,expected_context=ctx,expected_head=head) as a:
                with patch('rcp_rclm_runtime_v5.phase17.campaign_transaction.CampaignEvaluatorClient') as client:
                    with self.assertRaises(ResourceExhausted):run_campaign_session(a,parent(),candidate_credits=1,prior_sessions=evidence)
                    client.assert_not_called()
                raw=a.journal_bytes();head=a.state.head
            verified=audit_campaign(parent(),raw,expected_head=head,policy=pol,expected_context=ctx,sessions=evidence)
            self.assertEqual(verified['reserved'],list(pol.limits));self.assertEqual(verified['completed_sessions'],2)
            self.assertEqual(verified['status'],'resource_exhausted')
            # Mutation tests use retained new evidence; no worker rerun.
            for file in ('grant.json','sealed_transcript.json','worker-accounting.json',
                         'controller_checkpoint.json','objective.json','objective_freeze.json',
                         'public_challenge.json','session.json'):
                damaged=copy.deepcopy(evidence);key=next(iter(damaged));damaged[key][file]=b'{}'
                with self.subTest(file=file),self.assertRaises((ValueError,KeyError,ControlError)):
                    audit_campaign(parent(),raw,expected_head=head,policy=pol,expected_context=ctx,sessions=damaged)
            with self.assertRaises(ControlError):
                audit_campaign(parent(),raw,expected_head=head,policy=pol,expected_context=ctx,sessions={})


class ValidationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcp_rclm_runtime_v5.phase17.campaign_validation import execute_profile
        cls.saved=tempfile.TemporaryDirectory()
        cls.folder=Path(cls.saved.name)/'profile';cls.folder.mkdir()
        cls.report=execute_profile(ROOT,cls.folder)

    @classmethod
    def tearDownClass(cls):cls.saved.cleanup()

    def setUp(self):
        import shutil
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'profile'
        shutil.copytree(self.folder,self.path)

    def tearDown(self):self.tmp.cleanup()

    def verify(self):
        from rcp_rclm_runtime_v5.phase17.campaign_validation import verify_profile
        return verify_profile(ROOT,self.path)

    def test_verify_launches_no_worker_or_entropy(self):
        with patch('rcp_rclm_runtime_v5.phase17.campaign_transaction.CampaignEvaluatorClient') as w,\
             patch('rcp_rclm_runtime_v5.phase17.challenge_protocol.secrets.token_bytes') as rand:
            r=self.verify();w.assert_not_called();rand.assert_not_called()
        self.assertEqual(r['reserved_cost'],4480)
        self.assertFalse(r['claims']['phase17_exit_closed'])

    def test_removed_session_rejected(self):
        (self.path/'sessions/0/sealed_transcript.json').unlink()
        with self.assertRaises((OSError,ValueError)):self.verify()

    def test_extra_evidence_file_rejected(self):
        (self.path/'unapproved.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):self.verify()

    def test_changed_anchor_inventory_rejected(self):
        (self.path/'anchors.json').write_bytes(canonical(['1'*64,'2'*64]))
        with self.assertRaises((ValueError,ControlError)):self.verify()

    def test_budget_reset_control_rejected(self):
        p=self.path/'controls.json';obj=load_json_strict(p.read_bytes());obj['failed-grant']['reserved']=[0,0,0,0]
        p.write_bytes(canonical(obj))
        with self.assertRaises(ValueError):self.verify()

    def test_claim_escalation_rejected(self):
        p=self.path/'sessions/0/session.json';obj=load_json_strict(p.read_bytes());obj['claims']['promotion_authorized']=True
        p.write_bytes(canonical(obj))
        with self.assertRaises((ValueError,ControlError)):self.verify()

    def test_no_claims_of_evolving_parent_or_full_proof(self):
        r=self.verify()
        self.assertTrue(r['fixed_parent']);self.assertEqual(r['new_lean_audits'],0)
        self.assertFalse(r['claims']['root_transition_verified'])
        self.assertFalse(r['execution_metadata_is_attestation'])
        self.assertFalse(r['old_proofs_rerun'])

    def test_worker_boolean_pid_rejected(self):
        p=self.path/'sessions/0/session.json';obj=load_json_strict(p.read_bytes());obj['worker_pid']=True
        p.write_bytes(canonical(obj))
        with self.assertRaises((ValueError,ControlError)):self.verify()

    def test_unmeasured_resources_cannot_be_removed(self):
        p=self.path/'sessions/0/session.json';obj=load_json_strict(p.read_bytes());obj['unmeasured']=[]
        p.write_bytes(canonical(obj))
        with self.assertRaises((ValueError,ControlError)):self.verify()

if __name__=='__main__':unittest.main(verbosity=2)
