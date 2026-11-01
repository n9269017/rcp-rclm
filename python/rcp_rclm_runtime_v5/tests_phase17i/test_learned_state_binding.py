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
from rcp_rclm_runtime_v5.phase17.materialized import materialize_package, snapshot, sha
from rcp_rclm_runtime_v5.phase17 import learned_state_binding as w, learned_binding_lean as l
from rcp_rclm_runtime_v5.phase17.operational_lean import render_operational, NAMES as H_NAMES

ROOT=Path(__file__).resolve().parents[3]
BUNDLE=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
CAPTURE=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
CLOSURE=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
FIXTURE=ROOT/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json'
ANCHOR='369c30c469090fa357633aca596cb0c7ad3de31f2ecf16ca78e7699e79c79e6e'


def process(code,stdout='',stderr=''):
    return {'returncode':code,'stdout':stdout,'stderr':stderr,
            'stdout_sha256':sha(stdout.encode()),'stderr_sha256':sha(stderr.encode()),'argv':[]}


def proof_fixture(prepared):
    """Controlled report to test parsing/rejection only; not actual Lean evidence."""
    p=prepared.packet; aud={n:[] for n in H_NAMES}
    stdout=''.join("'"+n+"' does not depend on any axioms\n" for n in H_NAMES)
    g={'status':'passed','task_semantics_checked':True,'proof_count':172,
       'negative_oracle_substitution_rejected':True,'bounded_contracts_certified':[w.PLAN_CONTRACT,w.TOOL_CONTRACT],
       'positive_source_sha256':sha(render_operational(prepared)),
       'negative_source_sha256':sha(render_operational(prepared,negative=True)),
       'packet_sha256':sha(prepared.packet_bytes),'contract_sha256':w.CONTRACT_SHA256,
       'commands':[process(0,'Lean (version 4.31.0, test)\n'),process(0,stdout),process(1,'error: tactic rfl failed\n')],
       'theorem_axioms':aud,'claims':{k:False for k in w.FALSE_CLAIMS}}
    return {'source_commit':'a'*40,'source_unchanged':True,'proof_mode':'real_pinned_lean',
       'local_increment_checks_passed':True,'plan_semantics_gate':g,
       'packet_sha256':sha(prepared.packet_bytes),'contract_sha256':w.CONTRACT_SHA256,
       'candidate_package_hash':p['bindings']['candidate_physical_hash'],
       'predecessor_package_hash':p['bindings']['predecessor_physical_hash'],
       'legacy_full_recursive_tasks_recertified':[],'neural_decoder_formally_verified':False,
       'claims':{k:False for k in w.FALSE_CLAIMS}}


class LearnedBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='r17i-test-');cls.root=Path(cls.temp.name).resolve(strict=True)
        cls.parent=reopen_phase16(capture_archive=CAPTURE,closure_archive=CLOSURE,phase15_bundle=BUNDLE)
        cls.raw=FIXTURE.read_bytes()
        cls.before=materialize_package(cls.root/'p',cls.parent,BUNDLE)
        cls.after=materialize_package(cls.root/'c',cls.parent,BUNDLE,transcript=cls.raw,expected_transcript_hash=ANCHOR)
        cls.prepared,cls.operational=w.prepare_learned_binding(cls.before,cls.after,cls.parent,bundle=BUNDLE,
            capture=CAPTURE,transcript=cls.raw,expected_transcript_hash=ANCHOR)
        cls.p=cls.prepared.packet
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def altered(self,fn):
        p=copy.deepcopy(self.p);fn(p);return w.PreparedLearnedBinding(canonical(p))
    def bad(self,fn):
        with self.assertRaises((ValueError,KeyError)):self.altered(fn)
    def test_real_package_projection(self):
        self.assertEqual(len(self.p['predecessor']['base']),8);self.assertEqual(len(self.p['candidate']['base']),9)
        self.assertNotEqual(self.before.package_hash,self.after.package_hash)
    def test_all_164_files_in_twelve_groups(self):
        for name in ('predecessor','candidate'):
            s=self.p[name];self.assertEqual(sum(len(s[g]) for g in w.GROUPS),164)
            self.assertEqual([len(s[g]) for g in w.GROUPS],list(w.GROUP_COUNTS))
    def test_direct_measured_bytes_match(self):
        a,b=snapshot(self.before.root),snapshot(self.after.root)
        for g in w.GROUPS:
            for r in self.p['predecessor'][g]:
                self.assertEqual(a[r['path']],b[r['path']]);self.assertEqual(sha(a[r['path']]),r['sha256'])
    def test_components_match_real_root_type_fields(self):
        text=(ROOT/w.TYPE_PATH).read_text(encoding='utf-8')
        body=text.split('structure PackageState',1)[1].split('where',1)[1].split('/--',1)[0]
        fields=re.findall(r'^  (\w+) :',body,re.M)
        self.assertEqual(fields,['base',*w.FIELDS,'capabilityFrontier'])
    def test_root_inventory_matches_actual_structures(self):
        rows=self.p['root_admission']['obligations'];self.assertEqual(len(rows),35)
        self.assertEqual(self.p['root_admission']['status'],'blocked_missing_semantic_witnesses')
        self.assertFalse(self.p['root_admission']['authorization_issued'])
        entries = (
            ('base','lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Certificates.lean','StepObligations'),
            ('learned',w.KERNEL_PATH,'SpecificObligations'),
            ('autonomous','lean/rcp_rclm_formal_core_v4/RcpRclmFormalCoreV4/Autonomous/Kernel.lean','SpecificObligations'),
        )
        for layer,relative,structure in entries:
            body=(ROOT/relative).read_text(encoding='utf-8').split('structure '+structure,1)[1].split('where',1)[1].split('/--',1)[0]
            self.assertEqual(re.findall(r'^  (\w+)\s*:',body,re.M),
                             [r['field'] for r in rows if r['layer']==layer])
    def test_no_legacy_task_relabeling(self):
        self.assertTrue(all(r['legacy_full_task_semantics_recertified'] is False
                            for r in self.operational.packet['legacy_recursive_inventory']))
    def test_packet_access_is_detached(self):
        p=self.prepared.packet;p['candidate']['base'].clear();self.assertEqual(self.prepared.packet,self.p)
    def test_packet_anchor_verifies(self):
        w.verify_binding_packet(self.prepared.packet_bytes,self.prepared,expected_sha256=sha(self.prepared.packet_bytes))
    def test_rehash_does_not_replace_recomputation(self):
        raw=canonical({'fake':True})
        with self.assertRaises(ValueError):w.verify_binding_packet(raw,self.prepared,expected_sha256=sha(raw))
    def test_noncanonical_packet_rejected(self):
        with self.assertRaises(ValueError):w.PreparedLearnedBinding(self.prepared.packet_bytes+b' ')
    def test_mutable_bytes_rejected(self):
        with self.assertRaises(ValueError):w.PreparedLearnedBinding(bytearray(self.prepared.packet_bytes))
    def test_unknown_root_authority_field(self):self.bad(lambda p:p.update(accepted=True))
    def test_empty_claims_rejected(self):self.bad(lambda p:p.update(claims={}))
    def test_promotion_claim_rejected(self):self.bad(lambda p:p['claims'].update(promotion_authorized=True))
    def test_numeric_false_claim_rejected(self):self.bad(lambda p:p['claims'].update(root_transition_verified=0))
    def test_readiness_override_rejected(self):self.bad(lambda p:p['root_admission'].update(status='accepted'))
    def test_numeric_false_readiness_rejected(self):self.bad(lambda p:p['root_admission'].update(authorization_issued=0))
    def test_missing_root_premise_rejected(self):self.bad(lambda p:p['root_admission']['obligations'].pop())
    def test_component_substitution_rejected(self):self.bad(lambda p:p['candidate']['modelWeights'][0].update(sha256='0'*64))
    def test_file_size_boolean_rejected(self):self.bad(lambda p:p['candidate']['modelWeights'][0].update(size=True))
    def test_duplicate_file_rejected(self):self.bad(lambda p:p['candidate']['modelWeights'].__setitem__(1,p['candidate']['modelWeights'][0]))
    def test_unknown_component_field_rejected(self):self.bad(lambda p:p['candidate'].update(other=[]))
    def test_registry_shadowing_rejected(self):self.bad(lambda p:p['candidate']['base'].__setitem__(-1,p['predecessor']['base'][0]))
    def test_registry_reorder_rejected(self):self.bad(lambda p:p['candidate']['base'].reverse())
    def test_missing_capability_rejected(self):self.bad(lambda p:p['candidate']['capabilityFrontier'].pop())
    def test_capability_oracle_binding_rejected(self):self.bad(lambda p:p.update(new_capability='phase17.dynamic.'+'0'*64))
    def test_package_identity_substitution_rejected(self):self.bad(lambda p:p['candidate'].update(package_hash='0'*64))
    def test_binding_omission_rejected(self):self.bad(lambda p:p['bindings'].pop('transcript_sha256'))
    def test_contract_substitution_rejected(self):self.bad(lambda p:p.update(operational_contract_sha256='0'*64))
    def test_file_mapped_to_wrong_component_rejected(self):
        def swap(p):
            for name in ('predecessor','candidate'):
                p[name]['memory'],p[name]['generator']=p[name]['generator'],p[name]['memory']
        self.bad(swap)
    def test_semantic_claim_boundary_not_silently_removed(self):self.bad(lambda p:p.update(trust_boundary=[]))
    def test_generated_source_uses_actual_root_type(self):
        s=l.render_binding(self.prepared,source_root=ROOT).decode()
        self.assertIn('RcpRclmFormalCoreV3.Learned.PackageState',s)
        self.assertIn('RcpRclmFormalCoreV3.Learned.FrontierKernel',s)
        self.assertIn('binding : ∀ s, learned.informationValue s = information (frozenView s)',s)
        self.assertNotRegex(s,r'\b(sorry|sorryAx|admit|axiom|native_decide|unsafe)\b')
    def test_negative_only_mutates_generated_candidate(self):
        good=l.render_binding(self.prepared,source_root=ROOT)
        bad=l.render_binding(self.prepared,source_root=ROOT,negative=True)
        self.assertNotEqual(good,bad);self.assertEqual(self.prepared.packet,self.p)
        digest=self.p['candidate']['modelWeights'][0]['sha256'].encode()
        self.assertEqual(good.count(digest)-bad.count(digest),1)
        self.assertIn(b'0'*64,bad)
    def test_template_pin_cannot_be_substituted(self):
        with patch.object(l,'BRIDGE_SHA256','0'*64),self.assertRaises(ValueError):l.render_binding(self.prepared,source_root=ROOT)
    def test_template_crlf_portable(self):
        raw=(ROOT/l.BRIDGE_PATH).read_bytes()
        with patch.object(Path,'read_bytes',return_value=raw.replace(b'\n',b'\r\n')):
            self.assertEqual(l.template(ROOT),raw)
    def test_negative_selector_is_boolean(self):
        with self.assertRaises(ValueError):l.render_binding(self.prepared,source_root=ROOT,negative=1)
    def test_exact_audit_names(self):
        text=''.join("'"+n+"' does not depend on any axioms\n" for n in l.NAMES)
        self.assertEqual(list(l.parse_audits(text)),list(l.NAMES))
    def test_unapproved_axiom_rejected(self):
        text=''.join("'"+n+"' depends on axioms: [sorryAx]\n" for n in l.NAMES)
        with self.assertRaises(ValueError):l.parse_audits(text)
    def test_extra_audit_output_rejected(self):
        text=''.join("'"+n+"' does not depend on any axioms\n" for n in l.NAMES)+'extra'
        with self.assertRaises(ValueError):l.parse_audits(text)
    def test_retained_formal_report_parser_control(self):
        r=proof_fixture(self.operational);raw=canonical(r)
        v=w.verify_retained_operational(self.operational,raw,expected_sha256=sha(raw),expected_source='a'*40)
        self.assertEqual(v['proofs_retained_not_rerun'],172)
        self.assertFalse(v['original_execution_authenticated_by_this_check'])
    def check_bad_report(self,change,*,retain_original_anchor=False):
        r=proof_fixture(self.operational);old=canonical(r);change(r);raw=canonical(r)
        with self.assertRaises((ValueError,KeyError)):
            w.verify_retained_operational(self.operational,raw,expected_sha256=sha(old if retain_original_anchor else raw),expected_source='a'*40)
    def test_retained_external_anchor_rejected(self):self.check_bad_report(lambda r:r.update(source_unchanged=False),retain_original_anchor=True)
    def test_mixed_transaction_proof_rejected(self):self.check_bad_report(lambda r:r.update(candidate_package_hash='0'*64))
    def test_rehashed_wrong_theorem_source_rejected(self):self.check_bad_report(lambda r:r['plan_semantics_gate'].update(positive_source_sha256='0'*64))
    def test_retained_failed_negative_rejected(self):self.check_bad_report(lambda r:r['plan_semantics_gate']['commands'][2].update(returncode=0))
    def test_retained_root_claim_rejected(self):self.check_bad_report(lambda r:r['claims'].update(root_transition_verified=True))
    def test_retained_log_tampering_rejected(self):self.check_bad_report(lambda r:r['plan_semantics_gate']['commands'][1].update(stdout='fake'))
    def test_wrong_retained_source_rejected(self):self.check_bad_report(lambda r:r.update(source_commit='b'*40))
    def test_live_failure_not_replaced_by_fixture(self):
        with self.assertRaises(ValueError):w.prepare_learned_binding(self.before,self.after,self.parent,
            bundle=BUNDLE,capture=CAPTURE,transcript=self.raw,expected_transcript_hash='0'*64)
    def gate(self,mode='success'):
        d=self.root/'tools';(d/'bin').mkdir(parents=True,exist_ok=True)
        suffix='.exe' if os.name=='nt' else ''
        for name in ('lean','lake','git'):(d/'bin'/(name+suffix)).write_bytes(name.encode())
        root={'x':{'canonical_sha256':'a','checkout_sha256':'a'}}
        text=''.join("'"+n+"' does not depend on any axioms\n" for n in l.NAMES)
        calls=[]
        def proc(argv,cwd,env,timeout):
            calls.append(argv)
            if len(calls)==1:return process(0,'Lean (version 4.31.0, test)\n')
            if len(calls)==2:
                if mode=='reject':return process(1,'error: failed')
                if mode=='axiom':return process(0,text.replace('does not depend on any axioms','depends on axioms: [sorryAx]'))
                if mode=='stderr':return process(0,text,'warning')
                return process(0,text)
            if mode=='negative-success':return process(0,text)
            if mode=='timeout':return process(-999,'timeout')
            return process(1,'error: tactic decide proved false\n')
        with patch.object(l.gate,'root_source_fingerprint',return_value=root),\
             patch.object(l.gate,'_dependency_state',return_value={}),\
             patch.object(l.gate,'resolve_toolchain',return_value=d),\
             patch.object(l.gate,'_lean_environment',return_value=({},d/'bin'/('git'+suffix))),\
             patch.object(l.gate,'_process',side_effect=proc):
            report=l.check_learned_binding(self.prepared,source_root=ROOT,lean_workspace=self.root)
        return report,calls
    def test_mock_gate_all_eight_audits_no_acceptance(self):
        r,c=self.gate();self.assertEqual(r['status'],'passed');self.assertEqual(len(c),3)
        self.assertTrue(all(v is False for v in r['claims'].values()))
        self.assertEqual(len(r['theorem_axioms']),8)
    def test_positive_compiler_failure_stops_before_negative(self):
        r,c=self.gate('reject');self.assertEqual(r['status'],'rejected');self.assertEqual(len(c),2)
    def test_mock_unapproved_axiom_stops_gate(self):self.assertEqual(self.gate('axiom')[0]['status'],'rejected')
    def test_mock_stderr_stops_gate(self):self.assertEqual(self.gate('stderr')[0]['status'],'rejected')
    def test_compiler_accepting_changed_component_cannot_pass(self):self.assertEqual(self.gate('negative-success')[0]['status'],'rejected')
    def test_negative_timeout_is_not_rejection(self):self.assertEqual(self.gate('timeout')[0]['status'],'rejected')

if __name__=='__main__':unittest.main(verbosity=2)
