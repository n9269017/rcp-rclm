from __future__ import annotations
import copy
import dataclasses
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.materialized import materialize_package, snapshot, sha, PackageReceipt
from rcp_rclm_runtime_v5.phase17.controller import ControlError
from rcp_rclm_runtime_v5.phase17 import operational_witnesses as w, operational_lean as l
from rcp_rclm_runtime_v5.phase17.successor_evidence import FALSE_CLAIMS

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
CAPTURE = ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
CLOSURE = ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
FIXTURE = ROOT/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json'
ANCHOR = '369c30c469090fa357633aca596cb0c7ad3de31f2ecf16ca78e7699e79c79e6e'

class OperationalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='r17h-test-')
        cls.root = Path(cls.tmp.name).resolve(strict=True)
        cls.parent = reopen_phase16(capture_archive=CAPTURE,closure_archive=CLOSURE,phase15_bundle=BUNDLE)
        cls.raw = FIXTURE.read_bytes()
        cls.before = materialize_package(cls.root/'p',cls.parent,BUNDLE)
        cls.after = materialize_package(cls.root/'c',cls.parent,BUNDLE,transcript=cls.raw,expected_transcript_hash=ANCHOR)
        cls.prepared = cls.prepare()
        cls.p = cls.prepared.packet
        cls.pfiles, cls.cfiles = snapshot(cls.before.root), snapshot(cls.after.root)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    @classmethod
    def prepare(cls, **overrides):
        args = dict(bundle=BUNDLE,capture=CAPTURE,transcript=cls.raw,expected_transcript_hash=ANCHOR)
        args.update(overrides)
        return w.prepare_operational(cls.before,cls.after,cls.parent,**args)
    def altered(self,fn):
        p=copy.deepcopy(self.p);fn(p);return w.PreparedOperational(canonical(p))
    def test_172_domain_cases(self):
        self.assertEqual(len(w.CASES),172);self.assertEqual(len(set(w.CASES)),172)
        self.assertEqual(sum(d=='integer_program' for d,_,_ in w.CASES),136)
    def test_domain_matches_inherited_public_contract(self):
        from rcp_rclm_runtime_v4.phase15.curriculum import expected_plan
        for d,a,b in w.CASES:self.assertEqual(w.expected_tokens(d,a,b),expected_plan(d,a,b))
    def test_zero_multiplier_not_in_contract(self):
        with self.assertRaises(ValueError):w.check_case('integer_program',0,1)
    def test_invalid_lean_pair(self):
        with self.assertRaises(ValueError):w.check_case('lean_multistep',3,3)
    def test_out_of_range_parameters(self):
        for d,a,b in [('integer_program',5,0),('integer_program',1,9),('lean_multistep',-1,3),('lean_multistep',2,9)]:
            with self.subTest(d=d,a=a,b=b),self.assertRaises(ValueError):w.check_case(d,a,b)
    def test_boolean_parameter_rejected(self):
        with self.assertRaises(ValueError):w.check_case('integer_program',True,0)
    def test_unknown_domain(self):
        with self.assertRaises(ValueError):w.check_case('science',1,2)
    def test_actual_queries_both_packages(self):
        self.assertEqual(self.p['predecessor'],self.p['candidate']);self.assertEqual(self.p['candidate']['queries'],172)
        self.assertEqual(self.p['candidate']['decoded_tokens'],1204)
    def test_actual_tool_output_count(self):
        self.assertEqual(self.p['candidate']['integer_tool_outputs'],4488)
        for row in self.p['candidate']['cases']:
            if row['domain']=='integer_program':self.assertEqual(row['tool_outputs'],[row['a']*x+row['b'] for x in range(-16,17)])
    def test_independent_trace_contains_argmax(self):
        for row in self.p['candidate']['score_traces'].values():
            scores=row['scores'];self.assertEqual(row['chosen'],scores.index(max(scores)))
    def test_zero_weights_not_expected_answer_lookup(self):
        tokens,_=w.reference_decode(bytes(65536),'integer_program',1,0)
        self.assertNotEqual(tokens,w.expected_tokens('integer_program',1,0));self.assertEqual(tokens,(0,)*16)
    def test_lowest_token_tie_break(self):
        import struct
        p=bytearray(65536);struct.pack_into('<h',p,(1*1024)*2,7);struct.pack_into('<h',p,(2*1024)*2,7)
        tokens,_=w.reference_decode(bytes(p),'integer_program',1,0);self.assertEqual(tokens,(1,))
    def test_mutable_weight_buffer_rejected(self):
        with self.assertRaises(ValueError):w.reference_decode(bytearray(65536),'integer_program',1,0)
    def test_weight_length_rejected(self):
        with self.assertRaises(ValueError):w.reference_decode(b'', 'integer_program',1,0)
    def test_parser_decodes_model_coefficients(self):
        for d,a,b in w.CASES:self.assertEqual(w.parse_plan(d,w.expected_tokens(d,a,b)),(a,b))
    def test_parser_opcode_rejected(self):
        with self.assertRaises(ValueError):w.parse_plan('integer_program',(6,21,8,20,8,9,1))
    def test_parser_boolean_token(self):
        with self.assertRaises(ValueError):w.parse_plan('integer_program',(6,21,7,20,8,9,True))
    def test_parser_missing_eos(self):
        with self.assertRaises(ValueError):w.parse_plan('integer_program',(6,21,7,20,8,9,0))
    def test_actual_tool_uses_tokens_not_reference_parameters(self):
        self.assertEqual(w.invoke_affine(self.after,w.expected_tokens('integer_program',-4,8),-16),72)
        self.assertEqual(w.invoke_affine(self.after,w.expected_tokens('integer_program',3,-8),4),4)
    def test_tool_rejects_out_of_scope_x(self):
        for x in [True,17,-17,1.0]:
            with self.subTest(x=x),self.assertRaises(ValueError):w.invoke_affine(self.after,w.expected_tokens('integer_program',1,0),x)
    def test_modified_tool_policy_rejected(self):
        path=self.after.root/w.TOOL_POLICY;raw=path.read_bytes()
        try:
            path.write_bytes(raw.replace(b'false',b'true',1))
            with self.assertRaises(ValueError):w.tool_binding(self.after)
        finally:path.write_bytes(raw)
    def test_rehashed_tool_authority_escalation_rejected(self):
        p=copy.deepcopy(self.p['candidate']['tool_binding'])
        path=self.after.root/w.TOOL_POLICY;raw=path.read_bytes();bad=raw.replace(b'"dynamic_code_loading":false',b'"dynamic_code_loading":true')
        receipt=__import__('json').loads(self.after.manifest_bytes)
        for row in receipt['files']:
            if row['path']==w.TOOL_POLICY:row.update(sha256=sha(bad),size=len(bad))
        try:
            path.write_bytes(bad)
            with self.assertRaisesRegex(ValueError,'authority'):w.tool_binding(PackageReceipt(self.after.root,canonical(receipt)))
        finally:path.write_bytes(raw)
    def test_all_164_base_files_mapped_once(self):
        rows=self.p['learned_component_projection'];names=[f['path'] for r in rows for f in r['files']]
        self.assertEqual(len(rows),12);self.assertEqual(len(names),len(set(names)));self.assertEqual(len(names),164)
        self.assertEqual(set(names),{p for p in self.pfiles if p.startswith('base/')})
    def test_changed_learned_weight_rejected(self):
        after=dict(self.cfiles);after[w.WEIGHTS]=after[w.WEIGHTS][:-1]+b'!'
        with self.assertRaises(ValueError):w.component_projection(self.pfiles,after)
    def test_missing_component_rejected(self):
        after=dict(self.cfiles);del after['base/policies/resource_policy.json']
        with self.assertRaises(ValueError):w.component_projection(self.pfiles,after)
    def test_unknown_component_path_rejected(self):
        before=dict(self.pfiles);after=dict(self.cfiles)
        for d in (before,after):d['base/unknown.json']=d.pop('base/policies/resource_policy.json')
        with self.assertRaises(ValueError):w.component_projection(before,after)
    def test_production_decode_disagreement_rejected(self):
        from types import SimpleNamespace
        with patch.object(w, 'decode_plan', return_value=SimpleNamespace(tokens=(31,),stopped_on_eos=False)):
            with self.assertRaisesRegex(ValueError, 'decode'):w.evaluate_planner(self.after)
    def test_tool_execution_disagreement_rejected(self):
        with patch.object(w, '_interpret_affine', return_value=999999):
            with self.assertRaisesRegex(ValueError, 'token-driven tool'):w.evaluate_planner(self.after)
    def test_changed_vocabulary_rejected(self):
        path=self.after.root/w.VOCABULARY;raw=path.read_bytes()
        try:
            path.write_bytes(raw.replace(b'PROGRAM_MUL',b'PROGRAM_ADD',1))
            with self.assertRaises(ValueError):w.tool_binding(self.after)
        finally:path.write_bytes(raw)
    def test_19_labels_are_not_19_witnesses(self):
        rows=self.p['legacy_recursive_inventory'];self.assertEqual(len(rows),19)
        self.assertEqual(sum(r['contract_id'] is not None for r in rows),2)
        self.assertTrue(all(r['legacy_full_task_semantics_recertified'] is False for r in rows))
    def test_claims_false(self):
        self.assertTrue(all(v is False for v in self.p['claims'].values()))
        self.assertEqual(self.p['new_contracts_formally_certified'],[])
    def test_renderer_rejects_extra_or_expanded_claims(self):
        for field in ('full_learned_semantic_refinement','training_performed','invented_authority'):
            changed=self.altered(lambda p:p['claims'].__setitem__(field,True))
            with self.subTest(field=field),self.assertRaises(ValueError):
                l.render_operational(changed)
    def test_external_anchor_required(self):
        with self.assertRaises(ValueError):self.prepare(expected_transcript_hash='0'*64)
    def test_packet_access_detached(self):
        p=self.prepared.packet;p['candidate']['queries']=0;self.assertEqual(self.prepared.packet['candidate']['queries'],172)
    def test_packet_rehash_not_recomputation(self):
        raw=self.altered(lambda p:p['candidate'].update(queries=171)).packet_bytes
        with self.assertRaises(ValueError):w.verify_operational_packet(raw,self.prepared,expected_sha256=sha(raw))
    def test_packet_exact_match(self):w.verify_operational_packet(self.prepared.packet_bytes,self.prepared,expected_sha256=sha(self.prepared.packet_bytes))
    def test_formal_inventory_172_unique(self):self.assertEqual(len(l.NAMES),172);self.assertEqual(len(set(l.NAMES)),172)
    def test_formal_source_parsed_output_and_task_rhs(self):
        source=l.render_operational(self.prepared).decode('utf-8')
        self.assertIn('def plan_000 (x : Int) : Int := (-4) * x + (-8)',source)
        self.assertIn('x + 0 < x + 1',source);self.assertEqual(source.count('#print axioms'),172)
    def test_negative_changes_only_first_oracle(self):
        good=l.render_operational(self.prepared);bad=l.render_operational(self.prepared,negative=True)
        self.assertEqual(good.count(b'plan_000 x = (-4)'),1)
        self.assertEqual(good.replace(b'plan_000 x = (-4)',b'plan_000 x = (-3)',1),bad)
    def test_formal_source_forbidden_token_absent(self):
        self.assertIsNone(__import__('re').search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b',l.render_operational(self.prepared)))
    def test_formal_refuses_contract_substitution(self):
        with self.assertRaises(ValueError):l.render_operational(self.altered(lambda p:p.update(contract_sha256='0'*64)))
    def test_formal_refuses_missing_case(self):
        p=copy.deepcopy(self.p)
        for role in ('candidate','predecessor'):p[role]['cases'].pop()
        with self.assertRaises(ValueError):l.render_operational(w.PreparedOperational(canonical(p)))
    def test_formal_refuses_changed_tokens(self):
        p=copy.deepcopy(self.p)
        for role in ('candidate','predecessor'):p[role]['cases'][0]['tokens'][1]=21
        with self.assertRaises(ValueError):l.render_operational(w.PreparedOperational(canonical(p)))
    def test_formal_refuses_boolean_literal(self):
        p=copy.deepcopy(self.p)
        for role in ('candidate','predecessor'):p[role]['cases'][0]['index']=False
        with self.assertRaises(ValueError):l.render_operational(w.PreparedOperational(canonical(p)))
    def test_formal_refuses_forged_outputs(self):
        p=copy.deepcopy(self.p)
        for role in ('candidate','predecessor'):p[role]['cases'][0]['tool_outputs'][0]+=1
        with self.assertRaises(ValueError):l.render_operational(w.PreparedOperational(canonical(p)))
    def test_formal_refuses_escalated_root_claim(self):
        with self.assertRaises(ValueError):l.render_operational(self.altered(lambda p:p['claims'].update(root_transition_verified=True)))
    def test_no_package_mutation(self):self.assertEqual(snapshot(self.before.root),self.pfiles);self.assertEqual(snapshot(self.after.root),self.cfiles)

class FormalControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse an independently PREPARED actual fixture, not a fabricated pass.
        OperationalTests.setUpClass();cls.prepared=OperationalTests.prepared
    @classmethod
    def tearDownClass(cls):OperationalTests.tearDownClass()
    def run_gate(self,mode='ok'):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve(strict=True);(root/'bin').mkdir();suffix='.exe' if os.name=='nt' else ''
            paths=[root/'bin'/(n+suffix) for n in ('lean','lake','git')]
            for p in paths:p.write_bytes(b'MOCK TOOL NOT COMPILER')
            def process(argv,*args,**kwargs):
                if argv[-1]=='--version':return dict(returncode=0,stdout='Lean (version 4.31.0, control fixture)\n',stderr='')
                bad=Path(argv[-1]).name=='WrongOracle.lean'
                if mode=='mutate':paths[0].write_bytes(b'changed')
                audits=''.join("'"+n+"' depends on axioms: ["+('sorryAx' if mode=='axiom' else 'propext')+"]\n" for n in l.NAMES)
                if mode=='name':audits=audits.replace(l.NAMES[0],'unrelated',1)
                if mode=='extra':audits+='unrelated warning\n'
                return dict(returncode=(0 if mode=='false-accepted' else 1) if bad else (1 if mode=='positive-rejected' else 0),
                            stderr='warning' if mode=='stderr' and not bad else '',
                            stdout=('error: Tactic `rfl` failed\n' if mode!='negative-timeout' else 'timeout') if bad else audits)
            with patch.object(l.gate,'root_source_fingerprint',return_value={'x':{'canonical_sha256':'h'}}),\
                 patch.object(l.gate,'_dependency_state',return_value={'x':'h'}),\
                 patch.object(l.gate,'resolve_toolchain',return_value=root),\
                 patch.object(l.gate,'_lean_environment',return_value=({'PATH':str(root/'bin')},paths[2])),\
                 patch.object(l.gate,'_process',side_effect=process):
                return l.check_operational(self.prepared,source_root=ROOT,lean_workspace=root)
    def test_mock_success_no_full_root(self):
        r=self.run_gate();self.assertEqual(r['status'],'passed');self.assertEqual(r['proof_count'],172)
        self.assertTrue(all(x is False for x in r['claims'].values()))
    def test_positive_failure_rejects(self):self.assertEqual(self.run_gate('positive-rejected')['status'],'rejected')
    def test_accepting_false_rejects(self):self.assertEqual(self.run_gate('false-accepted')['status'],'rejected')
    def test_negative_timeout_not_proof(self):self.assertEqual(self.run_gate('negative-timeout')['status'],'rejected')
    def test_unapproved_axiom_rejects(self):self.assertEqual(self.run_gate('axiom')['status'],'rejected')
    def test_wrong_name_rejects(self):self.assertEqual(self.run_gate('name')['status'],'rejected')
    def test_extra_output_rejects(self):self.assertEqual(self.run_gate('extra')['status'],'rejected')
    def test_stderr_rejects(self):self.assertEqual(self.run_gate('stderr')['status'],'rejected')
    def test_changed_compiler_rejects(self):self.assertEqual(self.run_gate('mutate')['status'],'rejected')
    def test_missing_dependency_blocked(self):
        with patch.object(l.gate,'root_source_fingerprint',side_effect=ControlError('dependency missing')):
            r=l.check_operational(self.prepared,source_root=ROOT,lean_workspace=ROOT)
        self.assertEqual(r['status'],'blocked');self.assertEqual(r['commands'],[])

if __name__ == '__main__':unittest.main(verbosity=2)
