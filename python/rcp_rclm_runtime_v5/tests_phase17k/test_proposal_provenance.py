from __future__ import annotations
import copy
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.materialized import materialize_package,sha,snapshot
from rcp_rclm_runtime_v5.phase17.controller import Action, decide,record_evaluation
from rcp_rclm_runtime_v5.phase17.phase16_adapter import bind_phase16_search
from rcp_rclm_runtime_v5.phase17.challenge_protocol import EvaluatorSession,PROTOCOL,realize_candidate,transcript_bytes,verify_transcript
from rcp_rclm_runtime_v5.phase17 import proposal_provenance as m, provenance_lean as l

ROOT=Path(__file__).resolve().parents[3]
BUNDLE=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
CAPTURE=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
CLOSURE=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
ORIGINAL=ROOT/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json'
FIXTURE=Path(__file__).resolve().parent/'fixtures/ordered_known_challenge.json'
ANCHOR='16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f'


def fixed_fixture(parent,*,credits=32,entropy=None,stop=None):
    """Test-only known entropy replay. Never used for live hidden-evaluation claims."""
    known=json.loads(ORIGINAL.read_bytes());opening=known['events'][0]['request'];opening['candidate_credits']=credits
    if entropy is None:entropy=bytes.fromhex(known['events'][-1]['response']['payload']['opening']['entropy_hex'])
    s=EvaluatorSession(parent);public=s._handle(opening,replay_entropy=entropy)['payload']['public_challenge'];o=opening['objective']
    binding=bind_phase16_search(parent.phase16_state(),turn_index=o['turn_index'],challenge_commitment_hash=public['challenge_commitment_hash'],
        public_nonce_hash=o['public_nonce_hash'],candidate_credits=credits);prefix=binding.prefix
    while (step:=decide(prefix)).action==Action.EVALUATE:
        if stop and len(prefix.observations)==2:break
        a=realize_candidate(binding.programs[step.candidate_hash].to_json(),opening['freeze'])
        fr=s.handle({'protocol':PROTOCOL,'op':'freeze_candidate','program_hash':a['program_hash'],'artifact_hash':a['artifact_hash']})['payload']['receipt']
        ev=s.handle({'protocol':PROTOCOL,'op':'evaluate','artifact':a,'candidate_freeze_hash':fr['candidate_freeze_hash']})['payload']
        prefix=record_evaluation(prefix,step,verdict=ev['verdict'],evaluation_hash=ev['evaluation_hash'],reason_codes=ev['reason_codes'],
            predecessor_state_hash=ev['predecessor_state_hash'],challenge_commitment_hash=ev['challenge_commitment_hash'])
    terminal=stop if stop and len(prefix.observations)==2 else decide(prefix).action.value
    s.handle({'protocol':PROTOCOL,'op':'seal','terminal_action':terminal})
    return transcript_bytes(s.events)


class ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='r17k-test-');cls.root=Path(cls.temp.name).resolve(strict=True)
        cls.parent=reopen_phase16(capture_archive=CAPTURE,closure_archive=CLOSURE,phase15_bundle=BUNDLE)
        cls.raw=FIXTURE.read_bytes();assert sha(cls.raw)==ANCHOR
        cls.before=materialize_package(cls.root/'p',cls.parent,BUNDLE)
        cls.after=materialize_package(cls.root/'c',cls.parent,BUNDLE,transcript=cls.raw,expected_transcript_hash=ANCHOR)
        cls.prepared=m.prepare_provenance(cls.before,cls.after,cls.parent,bundle=BUNDLE,source_root=ROOT,
            transcript=cls.raw,expected_transcript_hash=ANCHOR)
        cls.p=cls.prepared.packet;cls.weights=m.measured_projection(snapshot(cls.before.root),cls.parent)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def bad(self,fn):
        p=copy.deepcopy(self.p);fn(p)
        with self.assertRaises((ValueError,KeyError,TypeError,IndexError)):m.PreparedProvenance(canonical(p))
    def replay(self,raw):return m.replay_proposals(self.parent,raw,expected_transcript_hash=sha(raw),weights=self.weights)
    def test_physical_producer_prepare(self):
        self.assertEqual(len(self.p['trace']['table']),32);self.assertEqual(len(self.p['producer']['source_files']),8)
        self.assertFalse(self.p['scope']['historical_process_attestation'])
    def test_eight_rejections_then_one_pass(self):
        self.assertEqual([r['verdict'] for r in self.p['trace']['steps']],['reject']*8+['candidate_passed'])
        self.assertEqual(self.p['trace']['terminal'],'await_root_verification')
    def test_new_fixture_exactly_reproducible_without_seed_search(self):self.assertEqual(fixed_fixture(self.parent),self.raw)
    def test_old_fixture_valid_evaluation_but_invalid_controller_provenance(self):
        raw=ORIGINAL.read_bytes();self.assertEqual(verify_transcript(self.parent,raw,expected_transcript_hash=sha(raw)).terminal_action,'await_root_verification')
        with self.assertRaisesRegex(ValueError,'not the current controller choice'):self.replay(raw)
    def test_candidate_identity_binds_new_transcript(self):
        self.assertNotEqual(self.after.package_hash,'67a97c6d16b6097fd8f1c5e09a941d5b813dfd403e98a508491645d6aea18b65')
        self.assertEqual(self.p['candidate']['transcript_sha256'],ANCHOR)
    def test_physical_weights_complete_nonzero_projection(self):self.assertEqual(len(self.weights),84)
    def test_corrupt_physical_weights_rejected(self):
        f=snapshot(self.before.root);n=next(n for n,v in f.items() if sha(v)==m.WEIGHTS_SHA256);f[n]=b'\0'*65536
        with self.assertRaises(ValueError):m.measured_projection(f,self.parent)
    def test_duplicate_tensor_rejected(self):
        f=snapshot(self.before.root);f['duplicate.bin']=next(v for v in f.values() if sha(v)==m.WEIGHTS_SHA256)
        with self.assertRaises(ValueError):m.measured_projection(f,self.parent)
    def test_changed_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve(strict=True)
            for rel in m.SOURCE_PINS:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/rel).read_bytes())
            rel=next(iter(m.SOURCE_PINS));(root/rel).write_bytes((root/rel).read_bytes()+b'# changed\n')
            with self.assertRaises(ValueError):m.producer_sources(root)
    def test_source_crlf_canonical_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve(strict=True)
            for rel in m.SOURCE_PINS:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/rel).read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
            self.assertEqual(m.producer_sources(root),m.producer_sources(ROOT))
    def test_actual_candidate_file_corruption_rejected(self):
        h=self.p['candidate']['program_hash'];path=self.after.root/'registry/programs'/f'{h}.json';old=path.read_bytes()
        try:
            path.write_bytes(old+b' ')
            with self.assertRaises(ValueError):m.prepare_provenance(self.before,self.after,self.parent,bundle=BUNDLE,source_root=ROOT,transcript=self.raw,expected_transcript_hash=ANCHOR)
        finally:path.write_bytes(old)
    def test_missing_candidate_rejected(self):
        with self.assertRaises(ValueError):m.prepare_provenance(self.before,None,self.parent,bundle=BUNDLE,source_root=ROOT,transcript=self.raw,expected_transcript_hash=ANCHOR)
    def test_zero_budget_is_resource_stop(self):
        raw=fixed_fixture(self.parent,credits=0);t=self.replay(raw);self.assertEqual(t['terminal'],'resource_exhausted');self.assertEqual(t['steps'],[])
        p=m.prepare_provenance(self.before,None,self.parent,bundle=BUNDLE,source_root=ROOT,transcript=raw,expected_transcript_hash=sha(raw))
        self.assertIsNone(p.packet['candidate'])
    def test_fixed_impossible_seed_exhausts_32(self):
        raw=fixed_fixture(self.parent,entropy=b'\0'*32);t=self.replay(raw)
        self.assertEqual(t['terminal'],'search_exhausted');self.assertEqual(len(t['steps']),32)
    def test_partial_budget_not_exhaustion(self):
        t=self.replay(fixed_fixture(self.parent,credits=2));self.assertEqual(t['terminal'],'resource_exhausted');self.assertEqual(len(t['steps']),2)
    def test_external_stop_distinct(self):self.assertEqual(self.replay(fixed_fixture(self.parent,stop='external_stop_valid_prefix'))['terminal'],'external_stop_valid_prefix')
    def test_safety_stop_distinct(self):self.assertEqual(self.replay(fixed_fixture(self.parent,stop='fail_closed_safety_halt'))['terminal'],'fail_closed_safety_halt')
    def test_controller_never_receives_secret_opening(self):
        import inspect
        self.assertEqual(set(inspect.signature(bind_phase16_search).parameters),{'state','turn_index','challenge_commitment_hash','public_nonce_hash','candidate_credits'})
        text=canonical(self.p['trace']);self.assertNotIn(b'entropy_hex',text);self.assertNotIn(b'target_variant',text)
    def test_snapshot_is_detached(self):
        p=self.prepared.packet;p['trace']['steps'].clear();self.assertEqual(len(self.prepared.packet['trace']['steps']),9)
    def test_mutable_packet_rejected(self):
        with self.assertRaises(ValueError):m.PreparedProvenance(bytearray(self.prepared.packet_bytes))
    def test_formatted_packet_rejected(self):
        with self.assertRaises(ValueError):m.PreparedProvenance(json.dumps(self.p,indent=2).encode())
    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ValueError):m.PreparedProvenance(b'{"schema_id":1,"schema_id":2}')
    def test_wrong_packet_anchor_rejected(self):
        with self.assertRaises(ValueError):m.verify_provenance_bytes(self.prepared.packet_bytes,self.prepared,expected_sha256='0'*64)
    def test_exact_recomputed_packet(self):m.verify_provenance_bytes(self.prepared.packet_bytes,self.prepared,expected_sha256=sha(self.prepared.packet_bytes))
    def test_claim_escalation_rejected(self):self.bad(lambda p:p['claims'].update(promotion_authorized=True))
    def test_integer_false_claim_rejected(self):self.bad(lambda p:p['claims'].update(promotion_authorized=0))
    def test_scope_integer_false_rejected(self):self.bad(lambda p:p['scope'].update(historical_process_attestation=0))
    def test_unknown_future_horizon_rejected(self):self.bad(lambda p:p['trace']['current_view'].update(future_promotions=10))
    def test_future_target_metadata_rejected(self):self.bad(lambda p:p['trace'].update(winner=p['candidate']['program_hash']))
    def test_parent_substitution_rejected(self):self.bad(lambda p:p['candidate'].update(parent_physical_hash='0'*64))
    def test_trace_substitution_rejected(self):self.bad(lambda p:p['candidate'].update(transcript_sha256='0'*64))
    def test_generator_identity_forgery_rejected(self):self.bad(lambda p:p['producer'].update(generator_id='0'*64))
    def test_physical_hash_forgery_without_binding_rejected(self):self.bad(lambda p:p['producer'].update(physical_package_hash='0'*64))
    def test_candidate_program_substitution_rejected(self):self.bad(lambda p:p['candidate'].update(program_hash=p['trace']['steps'][0]['program_hash']))
    def test_artifact_substitution_rejected(self):self.bad(lambda p:p['trace']['steps'][0].update(artifact_hash='0'*64))
    def test_score_forgery_rejected(self):self.bad(lambda p:p['trace']['table'][0].update(base_score=999999999))
    def test_tie_forgery_rejected(self):self.bad(lambda p:p['trace']['table'][0]['ties'].__setitem__(0,0))
    def test_grammar_omission_rejected(self):self.bad(lambda p:p['trace']['table'].pop())
    def test_grammar_reorder_rejected(self):self.bad(lambda p:p['trace']['table'].reverse())
    def test_changed_enumeration_offset_rejected(self):self.bad(lambda p:p['trace'].update(enumeration_offset=(p['trace']['enumeration_offset']+1)%32))
    def test_skip_prior_rejections_rejected(self):self.bad(lambda p:p['trace'].update(steps=p['trace']['steps'][-1:]))
    def test_reordered_evaluations_rejected(self):self.bad(lambda p:p['trace']['steps'].reverse())
    def test_repeated_evaluation_rejected(self):self.bad(lambda p:p['trace']['steps'].insert(0,p['trace']['steps'][0]))
    def test_early_success_rejected(self):self.bad(lambda p:p['trace']['steps'][0].update(verdict='candidate_passed'))
    def test_changed_terminal_rejected(self):self.bad(lambda p:p['trace'].update(terminal='search_exhausted'))
    def test_bool_credit_rejected(self):self.bad(lambda p:p['trace'].update(initial_credits=True))
    def test_checkpoint_substitution_rejected(self):self.bad(lambda p:p['trace']['checkpoint'].update(initial_credits=1))
    def test_same_candidate_identity_rejected(self):self.bad(lambda p:p['candidate'].update(physical_package_hash=p['producer']['physical_package_hash']))
    def test_render_all_audits_and_no_placeholders(self):
        raw=l.render_provenance(self.prepared,source_root=ROOT);self.assertEqual(re.findall(rb'^#print axioms (.+)$',raw,re.M),[n.encode() for n in l.NAMES])
        self.assertIsNone(re.search(rb'\b(sorry|admit|sorryAx|native_decide|unsafe)\b',raw))
    def test_render_all_record_fields_one_line(self):
        text=l.render_provenance(self.prepared,source_root=ROOT).decode()
        self.assertEqual(len(re.findall(r'^def selected(Context|Proposal|Candidate) .*:= \{.*\}$',text,re.M)),3)
    def test_three_distinct_negative_sources(self):
        original=self.prepared.packet_bytes;sources=[l.render_provenance(self.prepared,source_root=ROOT,negative=n) for n in (None,'prefix','parent','program')]
        self.assertEqual(len(set(sources)),4);self.assertEqual(self.prepared.packet_bytes,original)
    def test_template_uses_actual_root_provenance_fields(self):
        text=l.template(ROOT).decode()
        for name in ('activeGenerator','activePackageHash','generatorBound','proposalProducedBy','proposalBindsCandidate','packageHashBound'):
            self.assertIn(name+' :=',text)
        self.assertIn('Learned.FrontierKernel',text)
    def test_terminal_nonpass_cannot_render_positive(self):
        raw=fixed_fixture(self.parent,credits=0)
        p=m.prepare_provenance(self.before,None,self.parent,bundle=BUNDLE,source_root=ROOT,transcript=raw,expected_transcript_hash=sha(raw))
        with self.assertRaises(ValueError):l.render_provenance(p,source_root=ROOT)


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the same ACTUAL preparation, not a success-report fixture.
        ProvenanceTests.setUpClass();cls.prepared=ProvenanceTests.prepared
    @classmethod
    def tearDownClass(cls):ProvenanceTests.tearDownClass()
    def run_control(self,mode='ok'):
        with tempfile.TemporaryDirectory() as d:
            tool=Path(d).resolve(strict=True);(tool/'bin').mkdir();suffix='.exe' if os.name=='nt' else ''
            for n in ('lean','lake'):(tool/'bin'/(n+suffix)).write_bytes(b'CONTROL FIXTURE NOT COMPILER')
            def process(argv,*args,**kwargs):
                if argv[-1]=='--version':return {'returncode':0,'stdout':'Lean (version 4.31.0, fixture)\n','stderr':''}
                label=Path(argv[-1]).stem
                if mode=='timeout':raise subprocess.TimeoutExpired(argv,1)
                if label=='Provenance':
                    if mode=='positive-reject':return {'returncode':1,'stdout':'error: failed','stderr':''}
                    names=list(l.NAMES)
                    if mode=='missing-name':names.pop()
                    text=''.join("'"+n+"' depends on axioms: ["+('sorryAx' if mode=='axiom' else 'propext')+"]\n" for n in names)
                    if mode=='extra-output':text+='unrelated\n'
                    if mode=='mutate-tool':(tool/'bin'/('lean'+suffix)).write_bytes(b'changed')
                    return {'returncode':0,'stdout':text,'stderr':'warning' if mode=='stderr' else ''}
                return {'returncode':0 if mode=='negative-accepted' else 1,
                        'stdout':'error: decide proved proposition false' if mode!='bad-negative' else 'error: missing input','stderr':''}
            import subprocess
            with patch.object(l.gate,'root_source_fingerprint',return_value={}),patch.object(l.gate,'_dependency_state',return_value={}),\
                 patch.object(l.gate,'resolve_toolchain',return_value=tool),patch.object(l.gate,'_process',side_effect=process):
                return l.check_provenance(self.prepared,source_root=ROOT,lean_workspace=ROOT)
    def test_mock_gate_success_not_promotion(self):
        r=self.run_control();self.assertEqual(r['status'],'passed');self.assertEqual(r['negative_controls_rejected'],list(l.LABELS[1:]))
        self.assertTrue(all(v is False for v in r['claims'].values()));self.assertFalse(r['historical_execution_attested'])
    def test_positive_failure_rejected(self):self.assertEqual(self.run_control('positive-reject')['status'],'rejected')
    def test_missing_audit_rejected(self):self.assertEqual(self.run_control('missing-name')['status'],'rejected')
    def test_unapproved_axiom_rejected(self):self.assertEqual(self.run_control('axiom')['status'],'rejected')
    def test_extra_output_rejected(self):self.assertEqual(self.run_control('extra-output')['status'],'rejected')
    def test_stderr_rejected(self):self.assertEqual(self.run_control('stderr')['status'],'rejected')
    def test_accepted_negative_rejected(self):self.assertEqual(self.run_control('negative-accepted')['status'],'rejected')
    def test_unrelated_negative_error_rejected(self):self.assertEqual(self.run_control('bad-negative')['status'],'rejected')
    def test_tool_mutation_rejected(self):self.assertEqual(self.run_control('mutate-tool')['status'],'rejected')
    def test_timeout_not_pass(self):self.assertNotEqual(self.run_control('timeout')['status'],'passed')

if __name__=='__main__':unittest.main(verbosity=2)
