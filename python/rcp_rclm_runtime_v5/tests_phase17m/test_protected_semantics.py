"""Physical observations are real; compiler-control fixtures are not Lean proofs."""
from __future__ import annotations
import copy
from fractions import Fraction
import inspect
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from rcp_rclm_runtime.mathematics.intervals import IntervalEvidence
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.materialized import materialize_package, sha
from rcp_rclm_runtime_v5.phase17 import protected_semantics as m, protected_semantics_lean as l
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
    global DATA,RENDERED
    temp=tempfile.TemporaryDirectory(prefix='r17m-tests-');directory=Path(temp.name).resolve(strict=True)
    parent=reopen_phase16(capture_archive=CAPTURE,closure_archive=CLOSURE,phase15_bundle=BUNDLE)
    raw=FIXTURE.read_bytes();assert sha(raw)==ANCHOR
    before=materialize_package(directory/'p',parent,BUNDLE)
    after=materialize_package(directory/'c',parent,BUNDLE,transcript=raw,expected_transcript_hash=ANCHOR)
    prepared=m.prepare_protected_semantics(before,after,parent,bundle=BUNDLE,capture=CAPTURE,source_root=ROOT,
                                           transcript=raw,expected_transcript_hash=ANCHOR)
    DATA=(temp,parent,raw,before,after,prepared)
    RENDERED={n:l.render_protected(prepared,source_root=ROOT,negative=None if n=='Protected' else n) for n in l.LABELS}


def tearDownModule():
    if DATA:DATA[0].cleanup()


class SemanticTests(unittest.TestCase):
    def setUp(self):
        _,self.parent,self.raw,self.before,self.after,self.prepared=DATA
        self.p=self.prepared.packet
    def bad(self,change):
        p=copy.deepcopy(self.p);change(p)
        with self.assertRaises((ValueError,KeyError,TypeError,IndexError)):m.PreparedProtectedSemantics(canonical(p))
    def test_physical_candidate_and_joint_identity(self):
        self.assertEqual(self.p['bindings']['candidate_physical_hash'],CANDIDATE)
        self.assertEqual(self.p['joint_packet_sha256'],'035c570a3e4b7f1ed2fd43085d9cd6357b2596a169eebcd621c0ff5d0fe274ac')
    def test_complete_520_production_comparisons(self):
        self.assertEqual(self.p['before']['production_rows_compared']+self.p['after']['production_rows_compared'],520)
        self.assertEqual(len(self.p['before']['row_selectors']),260)
    def test_exact_probability_mass_normalization(self):
        for row in self.p['before']['mass_minus_one_dictionary']:
            w=[n+1 for n in row];total=sum(w)
            self.assertEqual(sum((Fraction(n,total) for n in w),Fraction()),Fraction(1))
            self.assertTrue(all(n>0 for n in w))
    def test_same_probabilities_not_just_same_entropy(self):
        b=self.p['before'];a=copy.deepcopy(b);index=a['row_selectors'][self.p['information_positions'][0][0]]
        row=a['mass_minus_one_dictionary'][index];target=self.p['information_positions'][0][1]
        j=next(j for j,x in enumerate(row) if x!=row[target]);old=sorted(row);row[j],row[target]=row[target],row[j]
        self.assertEqual(sorted(row),old)
        self.assertNotEqual(m.observation_projection(a),m.observation_projection(b))
        info=m.information_summary(a,[self.p['information_positions'][0]])
        self.assertTrue(IntervalEvidence.from_json(info['diagonal_kl_sum_interval']).lower>0)
    def test_original_eleven_targets_and_28_positions(self):
        self.assertEqual(len(self.p['task_contract']['tasks']),11);self.assertEqual(len(self.p['information_positions']),28)
        for o,t in zip(self.p['after']['goals'],self.p['task_contract']['tasks'],strict=True):self.assertEqual(o['tokens'],t['expected_tokens'])
    def test_goal_function_is_not_constant_success(self):
        a=copy.deepcopy(self.p['after']);a['goals'][0]['tokens'][0]+=1
        self.assertEqual(m.goal_drift(self.p['before'],a),1)
        self.assertEqual(m.goal_drift(self.p['before'],self.p['after']),0)
    def test_original_zero_regression_policy_is_explicit(self):
        self.assertEqual(self.p['profile']['goal_budget'],0);self.assertEqual(self.p['profile']['information_budget'],0)
        self.assertTrue(self.p['scope']['resource_fields_unchanged'])
    def test_raw_tensor_bound_to_joint_package(self):
        for side in ('before','after'):
            o=self.p[side];self.assertEqual(sha(bytes.fromhex(o['tensor_hex'])),o['tensor_sha256'])
    def test_independent_score_tensor_orientation(self):
        raw=bytearray(2*320*320);struct.pack_into('<h',raw,2*(17*320+4),2048)
        rows=m.scores_from_tensor(bytes(raw));self.assertEqual(rows[4][17],1);self.assertEqual(rows[17][4],0)
    def test_score_divisibility_rejection(self):
        raw=bytearray(2*320*320);struct.pack_into('<h',raw,0,1)
        with self.assertRaises(ValueError):m.scores_from_tensor(bytes(raw))
    def test_wrong_tensor_length(self):
        with self.assertRaises(ValueError):m.scores_from_tensor(b'\0'*100)
    def test_mutable_tensor_rejected(self):
        with self.assertRaises(ValueError):m.scores_from_tensor(bytearray(2*320*320))
    def test_clip_and_positive_pseudomass(self):
        row=[-16]*260;row[1]=15;w=m.masses_from_scores(row)
        self.assertEqual(w[0],1);self.assertEqual(w[1],1<<30)
    def test_boolean_scores_rejected(self):
        with self.assertRaises(ValueError):m.masses_from_scores([True]*260)
    def test_incomplete_conditional_domain(self):
        with self.assertRaises(ValueError):m.pack_rows([[0]*260]*259)
    def test_wrong_parent(self):self.bad(lambda p:p['bindings'].update(predecessor_physical_hash='0'*64))
    def test_wrong_candidate(self):self.bad(lambda p:p['after'].update(package_hash='0'*64))
    def test_wrong_joint_packet(self):self.bad(lambda p:p.update(joint_packet_sha256='0'*64))
    def test_wrong_contract_even_after_rehash(self):
        def change(p):p['task_contract']['tasks'][0]['expected_tokens'][0]+=1;p['task_contract_sha256']=sha(canonical(p['task_contract']))
        self.bad(change)
    def test_target_distribution_redefinition(self):self.bad(lambda p:p['profile'].update(target_correct_mass=1))
    def test_probability_policy_redefinition(self):self.bad(lambda p:p['profile'].update(probability='hash-is-entropy'))
    def test_score_forgery(self):self.bad(lambda p:p['after']['score_dictionary'][0].__setitem__(0,1))
    def test_tensor_digest_forgery(self):self.bad(lambda p:p['after'].update(tensor_sha256='0'*64))
    def test_tensor_byte_forgery(self):self.bad(lambda p:p['after'].update(tensor_hex='f'+p['after']['tensor_hex'][1:]))
    def test_uppercase_tensor_encoding(self):self.bad(lambda p:p['after'].update(tensor_hex='A'+p['after']['tensor_hex'][1:]))
    def test_changed_row_denominator(self):self.bad(lambda p:p['after']['row_totals'].__setitem__(0,260))
    def test_probability_data_forgery(self):self.bad(lambda p:p['after']['mass_minus_one_dictionary'][0].__setitem__(0,1234))
    def test_boolean_denominator_rejected(self):self.bad(lambda p:p['before']['row_totals'].__setitem__(0,True))
    def test_probability_row_omission(self):self.bad(lambda p:p['after']['row_selectors'].pop())
    def test_noncanonical_dictionary(self):
        def change(p):p['after']['score_dictionary'].append(p['after']['score_dictionary'][0])
        self.bad(change)
    def test_context_substitution(self):self.bad(lambda p:p['information_positions'][0].__setitem__(0,0))
    def test_target_substitution(self):self.bad(lambda p:p['information_positions'][0].__setitem__(1,0))
    def test_boolean_context_rejected(self):self.bad(lambda p:p['information_positions'][0].__setitem__(0,True))
    def test_route_substitution(self):self.bad(lambda p:p['after']['goals'][0].update(effective_marker=0))
    def test_goal_decode_binding_substitution(self):self.bad(lambda p:p['after']['goals'][0].update(decode_hash='0'*64))
    def test_goal_output_substitution(self):self.bad(lambda p:p['after']['goals'][0]['tokens'].__setitem__(0,0))
    def test_goal_omission(self):self.bad(lambda p:p['after']['goals'].pop())
    def test_numeric_kl_report_forgery(self):self.bad(lambda p:p['after_information']['diagonal_kl_sum_interval']['upper'].update(numerator='1'))
    def test_equal_entropy_flag_cannot_replace_rows(self):self.bad(lambda p:p['after'].pop('mass_minus_one_dictionary'))
    def test_pass_flag_type(self):self.bad(lambda p:p.update(probabilities_equal=1))
    def test_goal_drift_type(self):self.bad(lambda p:p.update(selected_goal_drift=False))
    def test_source_pin_substitution(self):self.bad(lambda p:p['source_bindings'][0].update(git_blob='0'*40))
    def test_unknown_field(self):self.bad(lambda p:p.update(acceptance_override=True))
    def test_scope_escalation(self):self.bad(lambda p:p['scope'].update(full_information_interpretation_supplied=True))
    def test_closure_claim(self):self.bad(lambda p:p['claims'].update(phase17_exit_closed=True))
    def test_integer_false_claim_rejected(self):self.bad(lambda p:p['claims'].update(promotion_authorized=0))
    def test_no_external_targets_or_pass_report_inputs(self):
        params=set(inspect.signature(m.prepare_protected_semantics).parameters)
        self.assertEqual(params,{'before','after','parent','bundle','capture','source_root','transcript','expected_transcript_hash'})
    def test_no_promotion_api(self):self.assertFalse(hasattr(m,'promote'))
    def test_packet_detached(self):
        self.p['after']['goals'].clear();self.assertEqual(len(self.prepared.packet['after']['goals']),11)
    def test_noncanonical_packet(self):
        with self.assertRaises(ValueError):m.PreparedProtectedSemantics(json.dumps(self.p,indent=2).encode())
    def test_duplicate_json_key(self):
        with self.assertRaises(ValueError):m.PreparedProtectedSemantics(b'{"a":1,"a":2}')
    def test_packet_limit(self):
        with self.assertRaises(ValueError):m.PreparedProtectedSemantics(b' '*(m.MAX_BYTES+1))
    def test_mutable_packet(self):
        with self.assertRaises(ValueError):m.PreparedProtectedSemantics(bytearray(self.prepared.packet_bytes))
    def test_external_anchor_required(self):
        with self.assertRaises(ValueError):m.verify_protected_bytes(self.prepared.packet_bytes,self.prepared,expected_sha256='0'*64)
    def test_independent_recomputation_required(self):
        raw=self.prepared.packet_bytes+b'\n'
        with self.assertRaises(ValueError):m.verify_protected_bytes(raw,self.prepared,expected_sha256=sha(raw))


class RendererTests(unittest.TestCase):
    def test_exact_audit_list(self):
        self.assertEqual(re.findall(rb'^#print axioms (.+)$',RENDERED['Protected'],re.M),[n.encode() for n in l.NAMES])
        self.assertEqual(len(l.NAMES),14)
    def test_five_distinct_sources(self):self.assertEqual(len(set(RENDERED.values())),5)
    def test_no_placeholders_or_native_proofs(self):
        self.assertIsNone(re.search(rb'\b(sorry|sorryAx|admit|axiom|native_decide|unsafe|partial)\b',RENDERED['Protected']))
    def test_actual_root_distribution_used(self):
        t=l.template(ROOT).decode();self.assertIn('RCP.ClassicalFinite.PositiveDistribution 260',t)
        self.assertIn('RCP.QuantumFinite.DensityMatrixEvidence',t)
        self.assertIn('RCP.ClassicalFinite.positiveKLDivergence',t)
    def test_goal_and_information_not_constant_success(self):
        t=l.template(ROOT).decode();self.assertIn('goalDistance (observe s).goals (observe c.next).goals',t)
        self.assertIn('informationValue contract (observe s)',t)
        self.assertNotIn('informationValue := fun _ => 0',t)
    def test_resources_and_provenance_not_overridden(self):
        body=l.template(ROOT).decode().split('noncomputable def attach',1)[1].split('theorem unrelated',1)[0]
        self.assertNotIn('resourceUsed :=',body);self.assertNotIn('resourceBudget :=',body)
        self.assertNotIn('proposalProducedBy :=',body)
    def test_same_line_record_layout(self):
        for line in RENDERED['Protected'].decode().splitlines():
            if line.startswith(('def observedBefore','def observedAfter','def selectedContract','def boundContract')):
                self.assertTrue(line.endswith(' }'))
    def test_probability_permutation_control_changes_only_after(self):
        diff=[(x,y) for x,y in zip(RENDERED['Protected'].splitlines(),RENDERED['ChangedProbability'].splitlines(),strict=True) if x!=y]
        self.assertEqual(len(diff),1);self.assertTrue(diff[0][0].startswith(b'def observedAfter'))
    def test_goal_control_changes_only_after(self):
        diff=[(x,y) for x,y in zip(RENDERED['Protected'].splitlines(),RENDERED['ChangedGoal'].splitlines(),strict=True) if x!=y]
        self.assertEqual(len(diff),1);self.assertTrue(diff[0][0].startswith(b'def observedAfter'))
    def test_target_control_leaves_anchor_contract(self):
        diff=[(x,y) for x,y in zip(RENDERED['Protected'].splitlines(),RENDERED['ChangedTarget'].splitlines(),strict=True) if x!=y]
        self.assertEqual(len(diff),1);self.assertTrue(diff[0][0].startswith(b'def selectedContract'))
    def test_mixed_candidate_control_changes_binding_only(self):
        diff=[(x,y) for x,y in zip(RENDERED['Protected'].splitlines(),RENDERED['MixedCandidate'].splitlines(),strict=True) if x!=y]
        self.assertEqual(len(diff),1);self.assertTrue(diff[0][0].startswith(b'def semanticBinding'))
    def test_template_pin(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);p=r/l.BRIDGE_PATH;p.parent.mkdir(parents=True);p.write_bytes(b'bad')
            with self.assertRaises(ValueError):l.template(r)
    def test_template_crlf_portability(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);p=r/l.BRIDGE_PATH;p.parent.mkdir(parents=True);p.write_bytes(l.template(ROOT).replace(b'\n',b'\r\n'))
            self.assertEqual(l.template(r),l.template(ROOT))
    def test_invalid_control_name(self):
        with self.assertRaises(ValueError):l.render_protected(DATA[-1],source_root=ROOT,negative='accept-anyway')


REPAIR_CORRECTIONS = [('  | cons row rest ih => simp only [goalDistance, if_pos rfl, zero_add, ih]', '  | cons row rest ih => simp [goalDistance, ih]'), ('    (observe : State → Observation) (contract : Contract) :=\n  { other with', '    (observe : State → Observation) (contract : Contract) :\n    Learned.FrontierKernel (Task := Task) (Generator := Generator)\n      (Proposal := Proposal) (PackageHash := PackageHash) base :=\n  { other with'), ('  rw [selected_observation_retained, add_zero]\n  exact le_rfl', '  simpa only [selected_observation_retained, add_zero] using\n    (le_refl (informationValue selectedContract observedBefore))'), ('\nnamespace Phase17Protected\nset_option maxRecDepth', '\nnamespace Phase17Protected\nopen RcpRclmFormalCoreV2\nset_option maxRecDepth')]

class LeanRepairRegressionTests(unittest.TestCase):
    """Source/renderer regressions only: actual Lean checking is still required."""
    def test_goal_self_proof_uses_complete_simplification(self):
        text=l.template(ROOT).decode('utf-8')
        self.assertIn('  | cons row rest ih => simp [goalDistance, ih]',text)
        self.assertNotIn('simp only [goalDistance, if_pos rfl, zero_add, ih]',text)
    def test_attach_has_explicit_existing_kernel_result_type(self):
        text=l.template(ROOT).decode('utf-8')
        self.assertIn('    (observe : State → Observation) (contract : Contract) :\n'
                      '    Learned.FrontierKernel (Task := Task) (Generator := Generator)\n'
                      '      (Proposal := Proposal) (PackageHash := PackageHash) base :=',text)
    def test_root_namespace_reopened_for_selected_theorems(self):
        for raw in RENDERED.values():
            self.assertIn(b'\nnamespace Phase17Protected\nopen RcpRclmFormalCoreV2\nset_option maxRecDepth',raw)
    def test_information_proof_is_a_single_finished_term(self):
        for raw in RENDERED.values():
            self.assertIn(b'  simpa only [selected_observation_retained, add_zero] using\n'
                          b'    (le_refl (informationValue selectedContract observedBefore))',raw)
            self.assertNotIn(b'  rw [selected_observation_retained, add_zero]\n  exact le_rfl',raw)
    def test_all_five_certificates_only_have_declared_corrections(self):
        corrections=REPAIR_CORRECTIONS
        for label,raw in RENDERED.items():
            with self.subTest(label=label):
                old=(ROOT/'artifacts/development/phase17m'/(label+'.lean')).read_bytes()
                for before,after in corrections:
                    a,b=before.encode('utf-8'),after.encode('utf-8')
                    self.assertEqual(old.count(a),1)
                    old=old.replace(a,b,1)
                self.assertEqual(raw,old)
    def test_physical_literals_and_bindings_are_unchanged(self):
        prefixes=(b'def observedBefore',b'def observedAfter',b'def selectedContract',
                  b'def boundContract',b'def jointBinding',b'def semanticBinding')
        for label,raw in RENDERED.items():
            old=(ROOT/'artifacts/development/phase17m'/(label+'.lean')).read_bytes()
            self.assertEqual([s for s in raw.splitlines() if s.startswith(prefixes)],
                             [s for s in old.splitlines() if s.startswith(prefixes)])
    def test_all_theorem_headers_are_unchanged(self):
        for label,raw in RENDERED.items():
            old=(ROOT/'artifacts/development/phase17m'/(label+'.lean')).read_bytes()
            pattern=rb'(?:^|\n)theorem\s+.*?:='
            self.assertEqual(re.findall(pattern,raw,re.S),re.findall(pattern,old,re.S))
            self.assertGreaterEqual(len(re.findall(pattern,raw,re.S)),14)
    def test_repair_rendering_does_not_change_semantic_packet(self):
        prepared=DATA[-1];old=prepared.packet_bytes
        for label in l.LABELS:
            l.render_protected(prepared,source_root=ROOT,negative=None if label=='Protected' else label)
        self.assertEqual(prepared.packet_bytes,old)
        self.assertEqual(sha(old),'a720bdaeac1b316d6e50b9a640cddfad52baff44c09a44a4fdeda2b977e4da67')


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
                if Path(argv[-1]).stem=='Protected':
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
            dep={} if mode!='missing-dependency' else ValueError('missing mathlib')
            with patch.object(l,'render_protected',side_effect=lambda prepared,source_root,negative=None:RENDERED['Protected' if negative is None else negative]),\
                 patch.object(l.gate,'root_source_fingerprint',return_value={}),\
                 patch.object(l.gate,'_dependency_state',side_effect=dep if isinstance(dep,Exception) else None,return_value={}),\
                 patch.object(l.gate,'resolve_toolchain',return_value=tool),\
                 patch.object(l.gate,'_process',side_effect=process):
                result=l.check_protected(DATA[-1],source_root=ROOT,lean_workspace=ROOT)
            return result,calls
    def test_control_pass_is_not_full_acceptance(self):
        r,c=self.control();self.assertEqual(r['status'],'passed');self.assertEqual(len(c),6)
        self.assertEqual(r['negative_controls_rejected'],list(l.LABELS[1:]));self.assertFalse(r['full_learned_step_instantiated'])
        self.assertTrue(all(v is False for v in r['claims'].values()))
    def test_positive_failure_stops_controls(self):
        r,c=self.control('positive');self.assertEqual(r['status'],'rejected');self.assertEqual(len(c),2)
    def test_missing_audit(self):self.assertNotEqual(self.control('missing')[0]['status'],'passed')
    def test_audit_order(self):self.assertNotEqual(self.control('order')[0]['status'],'passed')
    def test_unapproved_axiom(self):self.assertNotEqual(self.control('axiom')[0]['status'],'passed')
    def test_extra_output(self):self.assertNotEqual(self.control('extra')[0]['status'],'passed')
    def test_positive_stderr(self):self.assertNotEqual(self.control('stderr')[0]['status'],'passed')
    def test_negative_acceptance(self):self.assertNotEqual(self.control('negative-accept')[0]['status'],'passed')
    def test_unrelated_negative_error(self):self.assertNotEqual(self.control('bad-negative')[0]['status'],'passed')
    def test_timeout_not_rejection(self):self.assertNotEqual(self.control('timeout')[0]['status'],'passed')
    def test_wrong_version(self):self.assertNotEqual(self.control('version')[0]['status'],'passed')
    def test_tool_mutation(self):self.assertNotEqual(self.control('mutate-tool')[0]['status'],'passed')
    def test_proof_mutation(self):self.assertNotEqual(self.control('mutate-proof')[0]['status'],'passed')
    def test_missing_dependency_before_compiler(self):
        r,c=self.control('missing-dependency');self.assertEqual(r['status'],'blocked');self.assertEqual(c,[])

if __name__=='__main__':unittest.main(verbosity=2)
