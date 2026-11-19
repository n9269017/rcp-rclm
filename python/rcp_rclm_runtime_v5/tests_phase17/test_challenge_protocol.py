from __future__ import annotations
import copy
import hashlib
import inspect
import json
import struct
from pathlib import Path
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v5.phase17.bootstrap import HistoricalPredecessor
from rcp_rclm_runtime_v5.phase17.controller import Action, ControlError, FAMILIES
from rcp_rclm_runtime_v5.phase17.objectives import select_bootstrap_objective, freeze_bootstrap_objective
from rcp_rclm_runtime_v5.phase17 import challenge_protocol as p

FIXTURE = Path(__file__).parent / 'fixtures/phase16_bootstrap_handoff.json'


def parent_fixture():
    f = json.loads(FIXTURE.read_text(encoding='utf-8'))
    weights = [0] * 32768
    for index, value in f['planner_projection']:
        weights[index] = value
    return HistoricalPredecessor(
        state_bytes=canonical_json_bytes(f['state']),
        accepted_programs=tuple(canonical_json_bytes(x) for x in f['programs']),
        planner_weights=struct.pack('<32768h', *weights),
        catalog_bytes=canonical_json_bytes(f['catalog']),
        receipt_bytes=canonical_json_bytes(f['receipt']))


def opening(parent, credits=32, turn=0, nonce='8' * 64):
    decision = select_bootstrap_objective(parent, turn_index=turn, public_nonce_hash=nonce)
    freeze = freeze_bootstrap_objective(decision, parent, turn_index=turn, public_nonce_hash=nonce)
    return {'protocol': p.PROTOCOL, 'op': 'open', 'objective': decision.to_json(),
            'freeze': freeze, 'candidate_credits': credits}


def request(session, op, **fields):
    return session.handle({'protocol': p.PROTOCOL, 'op': op, **fields})['payload']


def evaluate(session, program):
    artifact = p.realize_candidate(program, session.freeze)
    receipt = request(session, 'freeze_candidate', artifact_hash=artifact['artifact_hash'],
                      program_hash=artifact['program_hash'])['receipt']
    return request(session, 'evaluate', artifact=artifact, candidate_freeze_hash=receipt['candidate_freeze_hash'])


class ChallengeProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = parent_fixture()

    def session(self, credits=32):
        s = p.EvaluatorSession(self.parent)
        with patch.object(p.secrets, 'token_bytes', return_value=bytes(range(32))):
            s.handle(opening(self.parent, credits))
        return s

    def seal(self, s, action=None):
        request(s, 'seal', terminal_action=action or s.terminal() or Action.EXTERNAL_STOP.value)
        data = p.transcript_bytes(s.events)
        return data, hashlib.sha256(data).hexdigest()

    def test_freeze_validated_before_entropy(self):
        req = opening(self.parent)
        req['freeze']['active_package_hash'] = '0' * 64
        with patch.object(p.secrets, 'token_bytes') as rng:
            with self.assertRaises(ControlError): p.EvaluatorSession(self.parent).handle(req)
            rng.assert_not_called()

    def test_live_entropy_is_not_caller_parameter(self):
        self.assertEqual(list(inspect.signature(p.EvaluatorSession.handle).parameters), ['self', 'request'])
        for name in ('seed', 'entropy_hex', 'winner', 'target_promotions', 'terminal_model', 'future_challenges'):
            req = opening(self.parent);req[name] = '0' * 64
            with self.subTest(name=name), self.assertRaises(ControlError):
                p.EvaluatorSession(self.parent).handle(req)

    def test_open_once_and_entropy_once(self):
        s = p.EvaluatorSession(self.parent)
        with patch.object(p.secrets, 'token_bytes', return_value=b'q' * 32) as rng:
            s.handle(opening(self.parent))
            with self.assertRaises(ControlError):s.handle(opening(self.parent))
            rng.assert_called_once_with(32)

    def test_same_freeze_new_entropy_changes_commitment(self):
        hashes=[]
        for entropy in (b'a'*32,b'b'*32):
            with patch.object(p.secrets,'token_bytes',return_value=entropy):
                s=p.EvaluatorSession(self.parent);s.handle(opening(self.parent))
            hashes.append(s.public['challenge_commitment_hash'])
        self.assertNotEqual(*hashes)

    def test_secret_generation_does_not_take_candidate_set(self):
        self.assertEqual(list(inspect.signature(p._secret_from_entropy).parameters), ['entropy', 'family'])
        self.assertFalse(self.session().public['successor_availability_assumed'])

    def test_public_messages_withhold_secret_until_seal(self):
        s=self.session();evaluate(s,next(iter(s.programs.values())))
        data=p.transcript_bytes(s.events)
        for forbidden in (b'entropy_hex',b'target_variant',b'target_a',b'target_b',b'probes',bytes(range(32)).hex().encode()):
            self.assertNotIn(forbidden,data)
        data,_=self.seal(s)
        self.assertIn(b'entropy_hex',data)

    def test_no_authority_escalation(self):
        s=self.session();data,_=self.seal(s)
        for event in json.loads(data)['events']:
            self.assertEqual(event['response']['payload']['claims'],p.CLAIMS)
            self.assertTrue(all(v is False for v in event['response']['payload']['claims'].values()))

    def test_exact_32_legal_candidates(self):
        s=self.session()
        self.assertEqual(len(s.programs),32)
        self.assertEqual({(q['family'],q['variant']) for q in s.programs.values()},
                         {(f,v) for f in FAMILIES for v in range(4)})

    def test_candidate_realization_detaches_input(self):
        s=self.session();program=copy.deepcopy(next(iter(s.programs.values())))
        artifact=p.realize_candidate(program,s.freeze);program['parameter_a']=100
        self.assertNotEqual(artifact['program'],program)
        self.assertFalse(artifact['installed'])

    def test_evaluation_before_open_rejects(self):
        with self.assertRaises(ControlError):request(p.EvaluatorSession(self.parent),'evaluate',artifact={})

    def test_evaluation_requires_candidate_freeze(self):
        with self.assertRaises(ControlError):request(self.session(),'evaluate',artifact={},candidate_freeze_hash='0'*64)

    def test_forged_artifact_freeze_rejects(self):
        s=self.session()
        with self.assertRaises(ControlError):request(s,'freeze_candidate',artifact_hash='0'*64,program_hash=next(iter(s.programs)))
        self.assertIsNone(s.pending)

    def test_unknown_program_rejects(self):
        with self.assertRaises(ControlError):request(self.session(),'freeze_candidate',artifact_hash='0'*64,program_hash='0'*64)

    def test_changed_candidate_after_freeze_rejects(self):
        s=self.session();a=p.realize_candidate(next(iter(s.programs.values())),s.freeze)
        rec=request(s,'freeze_candidate',artifact_hash=a['artifact_hash'],program_hash=a['program_hash'])
        a['program']['parameter_a']=100
        with self.assertRaises(ControlError):request(s,'evaluate',artifact=a,candidate_freeze_hash=rec['receipt']['candidate_freeze_hash'])
        self.assertEqual(s.considered,[])

    def test_forged_generation_rejects(self):
        s=self.session();a=p.realize_candidate(next(iter(s.programs.values())),s.freeze)
        a['program']['generation']+=1
        with self.assertRaises(ControlError):request(s,'freeze_candidate',artifact_hash=a['artifact_hash'],program_hash=p.digest(a['program']))

    def test_wrong_parent_artifact_rejects(self):
        s=self.session();a=p.realize_candidate(next(iter(s.programs.values())),s.freeze)
        rec=request(s,'freeze_candidate',artifact_hash=a['artifact_hash'],program_hash=a['program_hash'])
        a['predecessor_state_hash']='0'*64
        with self.assertRaises(ControlError):request(s,'evaluate',artifact=a,candidate_freeze_hash=rec['receipt']['candidate_freeze_hash'])

    def test_stale_candidate_receipt_rejects(self):
        s=self.session();a=p.realize_candidate(next(iter(s.programs.values())),s.freeze)
        request(s,'freeze_candidate',artifact_hash=a['artifact_hash'],program_hash=a['program_hash'])
        with self.assertRaises(ControlError):request(s,'evaluate',artifact=a,candidate_freeze_hash='0'*64)

    def test_pending_candidate_blocks_second_freeze_and_seal(self):
        s=self.session();a=p.realize_candidate(next(iter(s.programs.values())),s.freeze)
        request(s,'freeze_candidate',artifact_hash=a['artifact_hash'],program_hash=a['program_hash'])
        with self.assertRaises(ControlError):request(s,'freeze_candidate',artifact_hash=a['artifact_hash'],program_hash=a['program_hash'])
        with self.assertRaises(ControlError):request(s,'seal',terminal_action=Action.EXTERNAL_STOP.value)

    def test_repeat_candidate_rejects(self):
        s=self.session();q=next(iter(s.programs.values()));evaluate(s,q);a=p.realize_candidate(q,s.freeze)
        with self.assertRaises(ControlError):request(s,'freeze_candidate',artifact_hash=a['artifact_hash'],program_hash=a['program_hash'])

    def test_zero_budget_is_resource_not_search_exhaustion(self):
        s=self.session(0)
        self.assertEqual(s.terminal(),Action.RESOURCE_EXHAUSTED.value)
        with self.assertRaises(ControlError):self.seal(s,Action.SEARCH_EXHAUSTED.value)
        self.seal(s)

    def test_partial_budget_not_complete_exhaustion(self):
        s=self.session(1);evaluate(s,next(iter(s.programs.values())))
        with self.assertRaises(ControlError):self.seal(s,Action.SEARCH_EXHAUSTED.value)
        self.assertIn(s.terminal(),(Action.AWAIT_ROOT_VERIFICATION.value,Action.RESOURCE_EXHAUSTED.value))

    def test_complete_enumeration_is_exactly_32(self):
        s=self.session()
        # Deterministic public fixture has no forced winner; if accepted earlier,
        # tests stop as the runtime must. This tests terminal preservation too.
        for program in s.programs.values():
            if s.terminal() is not None:break
            evaluate(s,program)
        self.assertEqual(len(s.considered),len(set(s.considered)))
        if s.passed is None:
            self.assertEqual(len(s.considered),32)
            self.assertEqual(s.terminal(),Action.SEARCH_EXHAUSTED.value)
        self.seal(s)

    def test_external_stop_and_safety_are_distinct(self):
        for reason in (Action.EXTERNAL_STOP.value,Action.SAFETY_HALT.value):
            s=self.session();data,h=self.seal(s,reason)
            self.assertEqual(p.verify_transcript(self.parent,data,expected_transcript_hash=h).terminal_action,reason)

    def test_terminal_cause_cannot_be_rewritten(self):
        s=self.session(0)
        with self.assertRaises(ControlError):self.seal(s,Action.EXTERNAL_STOP.value)

    def test_no_successful_phase_terminal(self):
        for reason in ('success','phase17_exit_closed','promote'):
            with self.subTest(reason=reason),self.assertRaises(ControlError):self.seal(self.session(),reason)

    def test_sealed_session_cannot_continue(self):
        s=self.session();self.seal(s)
        with self.assertRaises(ControlError):s.handle(opening(self.parent))

    def test_invalid_budgets_rejected(self):
        for budget in (True,-1,33,1.0,'32'):
            with self.subTest(budget=budget),self.assertRaises(ControlError):self.session(budget)

    def test_unknown_operation_and_extra_fields_rejected(self):
        with self.assertRaises(ControlError):request(self.session(),'reveal')
        with self.assertRaises(ControlError):request(self.session(),'seal',terminal_action=Action.EXTERNAL_STOP.value,answer=True)

    def test_canonical_wire_rejects_duplicates_float_and_padding(self):
        for raw in (b'{"a":1,"a":1}',b'{"a":1.5}',b'{ "a":1}',b'[]',b'x'*(p.MAX_WIRE_BYTES+1)):
            with self.subTest(raw=raw[:30]),self.assertRaises(ControlError):p.parse_wire(raw)

    def test_transcript_requires_external_anchor(self):
        data,h=self.seal(self.session())
        with self.assertRaises(ControlError):p.verify_transcript(self.parent,data,expected_transcript_hash='0'*64)
        self.assertEqual(p.verify_transcript(self.parent,data,expected_transcript_hash=h).candidate_evaluations,0)

    def test_transcript_recomputed_not_just_rehashed(self):
        s=self.session();evaluate(s,next(iter(s.programs.values())));data,_=self.seal(s)
        for mutate in (
            lambda x:x['events'][1]['response']['payload']['claims'].update(promotion_authorized=True),
            lambda x:x['events'][-1]['response']['payload']['opening'].update(target_a=100),
            lambda x:x['events'][-1]['response']['payload'].update(candidate_evaluations=32),
            lambda x:x['events'][0]['request']['freeze'].update(turn_index=10),
            lambda x:x['events'][0]['response'].update(previous_response_hash='f'*64),
        ):
            obj=json.loads(data);mutate(obj);changed=canonical_json_bytes(obj)
            with self.assertRaises(ControlError):p.verify_transcript(self.parent,changed,expected_transcript_hash=hashlib.sha256(changed).hexdigest())

    def test_unsealed_transcript_rejected(self):
        data=p.transcript_bytes(self.session().events)
        with self.assertRaises(ControlError):p.verify_transcript(self.parent,data,expected_transcript_hash=hashlib.sha256(data).hexdigest())

    def test_omitted_or_reordered_events_rejected(self):
        s=self.session();evaluate(s,next(iter(s.programs.values())));data,_=self.seal(s)
        for indices in ((0,2,3),(0,2,1,3),(0,1,2,3,3)):
            obj=json.loads(data);obj['events']=[obj['events'][i] for i in indices]
            changed=canonical_json_bytes(obj)
            with self.assertRaises(ControlError):p.verify_transcript(self.parent,changed,expected_transcript_hash=hashlib.sha256(changed).hexdigest())

    def test_freeze_boolean_integer_substitution_rejected(self):
        for field, value in (("turn_index", False), ("challenge_bound", 0),
                             ("promotion_authorized", 0)):
            obj=opening(self.parent)
            obj["freeze"][field]=value
            with self.subTest(field=field), self.assertRaises(ControlError):
                p.EvaluatorSession(self.parent).handle(obj)

    def test_rehashed_transcript_boolean_integer_substitution_rejected(self):
        data,_=self.seal(self.session(0))
        obj=json.loads(data)
        # On the final response, False == 0 in Python; exact canonical values
        # must be checked, not dictionary equality. Rehash to defeat hash-only checks.
        final=obj['events'][-1]['response']
        final['payload']['claims']['promotion_authorized']=0
        final['response_hash']=p.digest({k:v for k,v in final.items() if k!='response_hash'})
        changed=canonical_json_bytes(obj)
        with self.assertRaises(ControlError):
            p.verify_transcript(self.parent,changed,expected_transcript_hash=hashlib.sha256(changed).hexdigest())

    def test_public_response_mutation_does_not_mutate_session(self):
        s=p.EvaluatorSession(self.parent);response=s.handle(opening(self.parent))
        response['payload']['public_challenge']['candidate_credits']=100
        self.assertEqual(s.budget,32)
        self.assertEqual(s.public['candidate_credits'],32)

    def test_semantics_match_explicit_examples(self):
        x=[1,2,3,4]
        expected={'adapter_policy':[2,4,6,8], 'architecture_policy':[8,7,10,13],
                  'memory_policy':[5,4,1,2], 'optimizer_policy':[12,14,18,24],
                  'planner_policy':[3,4,1,6], 'retrieval_policy':[3,1,3,1],
                  'tool_policy':[5,1,6,4], 'verification_automation_policy':[3,4,5,6]}
        for family in FAMILIES:
            with self.subTest(family=family):self.assertEqual(p.vector_semantics(family,1,2,2,x),expected[family])

    def test_candidate_success_not_promotion(self):
        # Deliberately preselected UNIT-TEST entropy, not live campaign evidence.
        # The worker protocol has no seed/entropy input and cannot use this path.
        s=p.EvaluatorSession(self.parent)
        with patch.object(p.secrets,'token_bytes',return_value=(157).to_bytes(32,'big')):
            s.handle(opening(self.parent,credits=1))
        program=s.programs['a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e']
        result=evaluate(s,program)
        self.assertEqual(result['verdict'],'candidate_passed')
        self.assertEqual(s.terminal(),Action.AWAIT_ROOT_VERIFICATION.value)
        self.assertFalse(result['claims']['promotion_authorized'])
        with self.assertRaises(ControlError):self.seal(s,Action.RESOURCE_EXHAUSTED.value)
        data,h=self.seal(s)
        replay=p.verify_transcript(self.parent,data,expected_transcript_hash=h)
        self.assertEqual(replay.selected_candidate_hash,p.digest(program))
        self.assertEqual(replay.candidate_evaluations,1)

    def test_predecessor_success_prevents_candidate_gain(self):
        s=self.session();program=next(iter(s.programs.values()))
        secret=dict(s.secret,objective_family=program['family'],target_variant=program['variant'],
                    target_a=program['parameter_a'],target_b=program['parameter_b'])
        verdict,_=p._outcomes(secret,program,(canonical_json_bytes(program),))
        self.assertEqual(verdict,'reject')

    def test_rejection_feedback_does_not_name_target(self):
        s=self.session();wrong=next(q for q in s.programs.values() if q['family']!=s.secret['objective_family'])
        result=evaluate(s,wrong)
        self.assertEqual(result['verdict'],'reject')
        self.assertEqual(result['reason_codes'],['bounded_challenge_rejected'])
        self.assertEqual(set(result),{'event','program_hash','artifact_hash','candidate_freeze_hash',
            'predecessor_state_hash','challenge_commitment_hash','evaluation_index','verdict','reason_codes','claims','evaluation_hash'})


if __name__=='__main__':unittest.main(verbosity=2)
