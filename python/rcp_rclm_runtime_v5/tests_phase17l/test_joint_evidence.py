"""Real physical preparation; compiler-control fixtures are NOT Lean proofs."""
from __future__ import annotations
import copy
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.materialized import materialize_package, sha
from rcp_rclm_runtime_v5.phase17.learned_state_binding import PreparedLearnedBinding
from rcp_rclm_runtime_v5.phase17.frontier_meanings import PreparedMeanings
from rcp_rclm_runtime_v5.phase17.proposal_provenance import PreparedProvenance
from rcp_rclm_runtime_v5.phase17 import joint_evidence as m, joint_lean as l

ROOT=Path(__file__).resolve().parents[3]
BUNDLE=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
CAPTURE=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
CLOSURE=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
FIXTURE=ROOT/'python/rcp_rclm_runtime_v5/tests_phase17k/fixtures/ordered_known_challenge.json'
ANCHOR='16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f'
CANDIDATE='b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e'
DATA=None
RENDERED=None


def setUpModule():
    global DATA, RENDERED
    temp=tempfile.TemporaryDirectory(prefix='r17l-tests-'); directory=Path(temp.name).resolve(strict=True)
    parent=reopen_phase16(capture_archive=CAPTURE,closure_archive=CLOSURE,phase15_bundle=BUNDLE)
    raw=FIXTURE.read_bytes();assert sha(raw)==ANCHOR
    before=materialize_package(directory/'p',parent,BUNDLE)
    after=materialize_package(directory/'c',parent,BUNDLE,transcript=raw,expected_transcript_hash=ANCHOR)
    prepared=m.prepare_joint(before,after,parent,bundle=BUNDLE,capture=CAPTURE,source_root=ROOT,
                              transcript=raw,expected_transcript_hash=ANCHOR)
    DATA=(temp,parent,raw,before,after,prepared)
    # Compiler-control tests reuse these real rendered bytes; renderer tests remain separate.
    RENDERED={n:l.render_joint(prepared,source_root=ROOT,negative=None if n=="Joint" else n) for n in l.LABELS}


def tearDownModule():
    DATA[0].cleanup()


class JointTests(unittest.TestCase):
    def setUp(self):
        _,self.parent,self.raw,self.before,self.after,self.prepared=DATA
        self.p=self.prepared.packet
    def bad(self,change):
        p=copy.deepcopy(self.p);change(p)
        with self.assertRaises((ValueError,KeyError,TypeError,IndexError)):
            m.PreparedJoint(canonical(p))
    def test_physical_joint_preparation_same_candidate(self):
        self.assertEqual(self.p['bindings']['candidate_physical_hash'],CANDIDATE)
        self.assertEqual(self.p['bindings']['transcript_sha256'],ANCHOR)
        self.assertEqual(self.p['producer_provenance']['candidate']['physical_package_hash'],CANDIDATE)
    def test_frontier_coverage_is_21_to_22(self):
        j=self.p['task_meanings']
        self.assertEqual(len(j['before']['declared_ids']),21);self.assertEqual(len(j['after']['declared_ids']),22)
        self.assertEqual(len(j['tasks']),22)
    def test_proposal_trace_is_nine_with_eight_rejections(self):
        self.assertEqual([s['verdict'] for s in self.p['producer_provenance']['trace']['steps']],['reject']*8+['candidate_passed'])
    def test_all_three_bindings_match(self):
        i,j,k=self.prepared.components();self.assertEqual(m.shared_bindings(i,j,k),self.p['bindings'])
    def test_component_digest_binding(self):
        for n in m.KINDS:self.assertEqual(self.p['component_sha256'][n],sha(canonical(self.p[n])))
    def test_prior_valid_task_packet_cannot_mix(self):
        i,_,k=self.prepared.components()
        old=PreparedMeanings((ROOT/'artifacts/development/phase17j/prepared-packet.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'transaction mismatch'):m.join_prepared(i,old,k)
    def test_prior_valid_typed_packet_cannot_mix(self):
        _,j,k=self.prepared.components()
        old=PreparedLearnedBinding((ROOT/'artifacts/development/phase17i/prepared-packet.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'transaction mismatch'):m.join_prepared(old,j,k)
    def test_valid_old_pair_cannot_join_current_producer(self):
        _,_,k=self.prepared.components()
        i=PreparedLearnedBinding((ROOT/'artifacts/development/phase17i/prepared-packet.json').read_bytes())
        j=PreparedMeanings((ROOT/'artifacts/development/phase17j/prepared-packet.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'transaction mismatch'):m.join_prepared(i,j,k)
    def test_rehashing_mixed_components_does_not_help(self):
        def mix(p):
            p['task_meanings']=json.loads((ROOT/'artifacts/development/phase17j/prepared-packet.json').read_bytes())
            p['component_sha256']['task_meanings']=sha(canonical(p['task_meanings']))
        self.bad(mix)
    def test_shared_parent_tamper(self):self.bad(lambda p:p['bindings'].update(predecessor_physical_hash='0'*64))
    def test_shared_candidate_tamper(self):self.bad(lambda p:p['bindings'].update(candidate_physical_hash='0'*64))
    def test_shared_transcript_tamper(self):self.bad(lambda p:p['bindings'].update(transcript_sha256='0'*64))
    def test_shared_objective_tamper(self):self.bad(lambda p:p['bindings'].update(objective_hash='0'*64))
    def test_shared_challenge_tamper(self):self.bad(lambda p:p['bindings'].update(challenge_commitment_hash='0'*64))
    def test_shared_program_tamper(self):self.bad(lambda p:p['bindings'].update(program_hash='0'*64))
    def test_child_semantics_tamper(self):self.bad(lambda p:p['task_meanings']['tasks'][13]['targets'][0].__setitem__(0,123456))
    def test_producer_shortcut_rejected(self):self.bad(lambda p:p['producer_provenance']['trace'].update(steps=p['producer_provenance']['trace']['steps'][-1:]))
    def test_wrong_component_digest(self):self.bad(lambda p:p['component_sha256'].update(task_meanings='0'*64))
    def test_unknown_component_rejected(self):self.bad(lambda p:p.update(extra_report={'passed':True}))
    def test_omitted_component_rejected(self):self.bad(lambda p:p.pop('typed_binding'))
    def test_unknown_policy_rejected(self):self.bad(lambda p:p.update(policy='allow-old-evidence'))
    def test_omitted_remaining_witness_rejected(self):self.bad(lambda p:p['remaining_witness_classes'].pop())
    def test_scope_escalation_rejected(self):self.bad(lambda p:p['scope'].update(authorization_issued=True))
    def test_integer_scope_false_rejected(self):self.bad(lambda p:p['scope'].update(root_acceptance_evaluated=0))
    def test_promotion_claim_rejected(self):self.bad(lambda p:p['claims'].update(promotion_authorized=True))
    def test_integer_claim_false_rejected(self):self.bad(lambda p:p['claims'].update(root_transition_verified=0))
    def test_mutable_bytes_rejected(self):
        with self.assertRaises(ValueError):m.PreparedJoint(bytearray(self.prepared.packet_bytes))
    def test_formatted_packet_rejected(self):
        with self.assertRaises(ValueError):m.PreparedJoint(json.dumps(self.p,indent=2).encode())
    def test_duplicate_fields_rejected(self):
        with self.assertRaises(ValueError):m.PreparedJoint(b'{"schema_id":1,"schema_id":2}')
    def test_packet_size_limit(self):
        with self.assertRaises(ValueError):m.PreparedJoint(b' '*(m.MAX_BYTES+1))
    def test_detached_packet(self):
        self.p['bindings'].clear();self.assertEqual(self.prepared.packet['bindings']['candidate_physical_hash'],CANDIDATE)
    def test_correct_external_packet_anchor(self):m.verify_joint_bytes(self.prepared.packet_bytes,self.prepared,expected_sha256=sha(self.prepared.packet_bytes))
    def test_wrong_external_packet_anchor(self):
        with self.assertRaises(ValueError):m.verify_joint_bytes(self.prepared.packet_bytes,self.prepared,expected_sha256='0'*64)
    def test_wrong_external_transcript_anchor_fails_early(self):
        with self.assertRaises(ValueError):m.prepare_joint(self.before,self.after,self.parent,bundle=BUNDLE,capture=CAPTURE,source_root=ROOT,transcript=self.raw,expected_transcript_hash='0'*64)
    def test_same_directory_rejected(self):
        with self.assertRaises(ValueError):m.prepare_joint(self.before,self.before,self.parent,bundle=BUNDLE,capture=CAPTURE,source_root=ROOT,transcript=self.raw,expected_transcript_hash=ANCHOR)
    def test_physical_candidate_tampering_fails(self):
        path=self.after.root/'registry/programs'/(self.p['bindings']['program_hash']+'.json');raw=path.read_bytes()
        try:
            path.write_bytes(raw+b' ')
            with self.assertRaises(ValueError):m.prepare_joint(self.before,self.after,self.parent,bundle=BUNDLE,capture=CAPTURE,source_root=ROOT,transcript=self.raw,expected_transcript_hash=ANCHOR)
        finally:path.write_bytes(raw)
    def test_no_caller_success_report_argument(self):
        params=inspect.signature(m.prepare_joint).parameters
        self.assertEqual(set(params),{'before','after','parent','bundle','capture','source_root','transcript','expected_transcript_hash'})
    def test_exact_concrete_input_types(self):
        _,j,k=self.prepared.components()
        with self.assertRaises(ValueError):m.join_prepared(self.p['typed_binding'],j,k)


class RenderTests(unittest.TestCase):
    def setUp(self):self.prepared=DATA[-1]
    def test_all_43_unique_audits(self):
        raw=l.render_joint(self.prepared,source_root=ROOT)
        self.assertEqual(len(l.NAMES),43);self.assertEqual(len(set(l.NAMES)),43)
        self.assertEqual(re.findall(rb'^#print axioms (.+)$',raw,re.M),[n.encode() for n in l.NAMES])
    def test_six_distinct_sources(self):
        self.assertEqual(len({l.render_joint(self.prepared,source_root=ROOT,negative=None if n=='Joint' else n) for n in l.LABELS}),6)
    def test_existing_proof_bodies_preserved(self):
        i,j,k=self.prepared.components();merged=l.render_joint(self.prepared,source_root=ROOT).decode()
        for raw,names in [(l.typed_lean.render_binding(i,source_root=ROOT),l.typed_lean.NAMES),
            (l.task_lean.render_meanings(j,source_root=ROOT),l.task_lean.NAMES),
            (l.producer_lean.render_provenance(k,source_root=ROOT),l.producer_lean.NAMES)]:
            _,body=l.source_bodies(raw,names);self.assertIn(body,merged)
    def test_imports_only_at_top(self):
        text=l.render_joint(self.prepared,source_root=ROOT).decode();body=text[text.index('namespace '):]
        self.assertNotRegex(body,r'(?m)^import ')
    def test_no_admitted_or_native_proof(self):
        raw=l.render_joint(self.prepared,source_root=ROOT)
        self.assertIsNone(re.search(rb'\b(sorry|sorryAx|admit|axiom|native_decide|unsafe|partial)\b',raw))
    def test_remaining_premises_not_replaced_with_zero(self):
        text=l.template(ROOT).decode()
        for premise in ('baseProof : RCP.StepObligations','goal : other.goalDrift','resources : other.resourceUsed','information : other.informationValue'):
            self.assertIn(premise,text)
        self.assertNotIn(':= 0',text);self.assertNotIn(':= True',text)
        self.assertIn('Learned.LearnedAcceptedStep',text)
    def test_one_kernel_receives_both_adapters(self):
        text=l.template(ROOT).decode()
        self.assertIn('Phase17Provenance.attachProvenance\n    (Phase17TaskMeaning.attachTaskSemantics',text)
    def test_mixed_candidate_changes_one_selected_binding(self):
        a=l.render_joint(self.prepared,source_root=ROOT);b=l.render_joint(self.prepared,source_root=ROOT,negative='MixedCandidate')
        aa=a.splitlines();bb=b.splitlines();diff=[(x,y) for x,y in zip(aa,bb,strict=True) if x!=y]
        self.assertEqual(len(diff),1);self.assertTrue(diff[0][0].startswith(b'def taskBinding'))
    def test_mixed_transcript_changes_one_selected_binding(self):
        a=l.render_joint(self.prepared,source_root=ROOT);b=l.render_joint(self.prepared,source_root=ROOT,negative='MixedTranscript')
        diff=[(x,y) for x,y in zip(a.splitlines(),b.splitlines(),strict=True) if x!=y]
        self.assertEqual(len(diff),1);self.assertTrue(diff[0][0].startswith(b'def taskBinding'))
    def test_all_negative_renders_leave_packet_unchanged(self):
        raw=self.prepared.packet_bytes
        for n in l.LABELS[1:]:l.render_joint(self.prepared,source_root=ROOT,negative=n)
        self.assertEqual(self.prepared.packet_bytes,raw)
    def test_invalid_negative_label(self):
        with self.assertRaises(ValueError):l.render_joint(self.prepared,source_root=ROOT,negative='skip-formal')
    def test_wrong_template_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/l.BRIDGE_PATH;p.parent.mkdir(parents=True);p.write_bytes(b'bad')
            with self.assertRaises(ValueError):l.template(root)
    def test_template_crlf_portable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/l.BRIDGE_PATH;p.parent.mkdir(parents=True);p.write_bytes(l.template(ROOT).replace(b'\n',b'\r\n'))
            self.assertEqual(l.template(root),l.template(ROOT))
    def test_component_audit_suffix_guard(self):
        with self.assertRaises(ValueError):l.source_bodies(b'import X\n#print axioms Wrong\n',('Expected',))


class GateControlTests(unittest.TestCase):
    def control(self,mode='ok'):
        with tempfile.TemporaryDirectory() as d:
            tool=Path(d).resolve();(tool/'bin').mkdir();ext='.exe' if os.name=='nt' else ''
            for name in ('lean','lake'):(tool/'bin'/(name+ext)).write_bytes(b'fixture not Lean')
            calls=[]
            def process(argv,*args,**kwargs):
                calls.append(argv)
                if argv[-1]=='--version':
                    return {'returncode':0,'stdout':f"Lean (version {'4.30.0' if mode=='version' else '4.31.0'}, fixture)\n",'stderr':''}
                if mode=='timeout':raise subprocess.TimeoutExpired(argv,1)
                if Path(argv[-1]).stem=='Joint':
                    if mode=='positive':return {'returncode':1,'stdout':'error: bad proof','stderr':''}
                    names=list(l.NAMES)
                    if mode=='missing':names.pop()
                    if mode=='order':names.reverse()
                    text=''.join("'"+n+"' depends on axioms: ["+('sorryAx' if mode=='axiom' else 'propext')+"]\n" for n in names)
                    if mode=='extra':text+='extra output\n'
                    if mode=='mutate-tool':(tool/'bin'/('lean'+ext)).write_bytes(b'changed')
                    if mode=='mutate-proof':Path(argv[-1]).write_bytes(b'changed')
                    return {'returncode':0,'stdout':text,'stderr':'warning' if mode=='stderr' else ''}
                return {'returncode':0 if mode=='negative-accept' else 1,
                        'stdout':'error: unexpected identifier decide false' if mode=='bad-negative' else 'error: Tactic `decide` proved that the proposition\n  False\nis false','stderr':''}
            dep=({} if mode!='missing-dependency' else ValueError('missing mathlib'))
            with patch.object(l,'render_joint',side_effect=lambda prepared,source_root,negative=None: RENDERED['Joint' if negative is None else negative]),\
                 patch.object(l.gate,'root_source_fingerprint',return_value={}),\
                 patch.object(l.gate,'_dependency_state',side_effect=dep if isinstance(dep,Exception) else None,return_value={}),\
                 patch.object(l.gate,'resolve_toolchain',return_value=tool),\
                 patch.object(l.gate,'_process',side_effect=process):
                result=l.check_joint(DATA[-1],source_root=ROOT,lean_workspace=ROOT)
            return result,calls
    def test_control_success_not_complete_transition(self):
        r,c=self.control();self.assertEqual(r['status'],'passed');self.assertEqual(len(c),7)
        self.assertEqual(r['negative_controls_rejected'],list(l.LABELS[1:]));self.assertFalse(r['full_learned_step_instantiated'])
        self.assertTrue(all(v is False for v in r['claims'].values()))
    def test_positive_failure_stops_negatives(self):
        r,c=self.control('positive');self.assertEqual(r['status'],'rejected');self.assertEqual(len(c),2)
    def test_audit_omission(self):self.assertNotEqual(self.control('missing')[0]['status'],'passed')
    def test_audit_order(self):self.assertNotEqual(self.control('order')[0]['status'],'passed')
    def test_unapproved_axiom(self):self.assertNotEqual(self.control('axiom')[0]['status'],'passed')
    def test_extra_output(self):self.assertNotEqual(self.control('extra')[0]['status'],'passed')
    def test_positive_stderr(self):self.assertNotEqual(self.control('stderr')[0]['status'],'passed')
    def test_negative_acceptance(self):self.assertNotEqual(self.control('negative-accept')[0]['status'],'passed')
    def test_unrelated_negative_failure(self):self.assertNotEqual(self.control('bad-negative')[0]['status'],'passed')
    def test_timeout_not_rejection_evidence(self):self.assertNotEqual(self.control('timeout')[0]['status'],'passed')
    def test_wrong_lean_version(self):self.assertNotEqual(self.control('version')[0]['status'],'passed')
    def test_tool_mutation(self):self.assertNotEqual(self.control('mutate-tool')[0]['status'],'passed')
    def test_source_mutation(self):self.assertNotEqual(self.control('mutate-proof')[0]['status'],'passed')
    def test_missing_dependency_before_compiler(self):
        r,c=self.control('missing-dependency');self.assertEqual(r['status'],'blocked');self.assertEqual(c,[])

if __name__=='__main__':unittest.main(verbosity=2)
