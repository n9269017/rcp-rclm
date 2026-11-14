"""Resume the exact Phase17M Lean elaboration/proof failure in a NEW checkout.

Preserves the failed source and evidence. Reuses the original hash-pinned installer
validators. Requires real Lean and all four negative controls before normal
fast-forward/push. No reset, amend, force-push, dependency installation or closure.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
sys.dont_write_bytecode = True

BASE = 'a60eee75b3c4b9797fe362ffed7773d2eb6bdc85'
FAILED_SOURCE = 'f29b22e448f5ebf74304762e9fa385be657ff024'
FAILED_TREE = 'fb0830d293603d07be695e0822148a3983b7b15c'
COMPILER_STDOUT_SHA = 'a8ba937c08a1afbec86ea906fa4e824370418d3a83414fb090f415aec5ca5f4f'
PACKET_SHA = 'a720bdaeac1b316d6e50b9a640cddfad52baff44c09a44a4fdeda2b977e4da67'
TEMPLATE = 'lean/phase17_bridge/ProtectedSemantics.lean'
MODULE = 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/protected_semantics_lean.py'
TEST = 'python/rcp_rclm_runtime_v5/tests_phase17m/test_protected_semantics.py'
RUNNER = 'scripts/run_phase17_protected_semantics_tests.py'
GATE_RUNNER = 'scripts/run_phase17_protected_semantics_gate.py'
ARTIFACT = 'artifacts/development/phase17m/'
TEST_COUNT = 91
OLD_GOAL = '  | cons row rest ih => simp only [goalDistance, if_pos rfl, zero_add, ih]'
NEW_GOAL = '  | cons row rest ih => simp [goalDistance, ih]'
OLD_ATTACH = '    (observe : State → Observation) (contract : Contract) :=\n  { other with'
NEW_ATTACH = '    (observe : State → Observation) (contract : Contract) :\n    Learned.FrontierKernel (Task := Task) (Generator := Generator)\n      (Proposal := Proposal) (PackageHash := PackageHash) base :=\n  { other with'
OLD_BOUND = '  rw [selected_observation_retained, add_zero]\n  exact le_rfl'
NEW_BOUND = '  simpa only [selected_observation_retained, add_zero] using\n    (le_refl (informationValue selectedContract observedBefore))'
OLD_NS = '\nnamespace Phase17Protected\nset_option maxRecDepth'
NEW_NS = '\nnamespace Phase17Protected\nopen RcpRclmFormalCoreV2\nset_option maxRecDepth'
EXTRA_TESTS = 'REPAIR_CORRECTIONS = [(\'  | cons row rest ih => simp only [goalDistance, if_pos rfl, zero_add, ih]\', \'  | cons row rest ih => simp [goalDistance, ih]\'), (\'    (observe : State → Observation) (contract : Contract) :=\\n  { other with\', \'    (observe : State → Observation) (contract : Contract) :\\n    Learned.FrontierKernel (Task := Task) (Generator := Generator)\\n      (Proposal := Proposal) (PackageHash := PackageHash) base :=\\n  { other with\'), (\'  rw [selected_observation_retained, add_zero]\\n  exact le_rfl\', \'  simpa only [selected_observation_retained, add_zero] using\\n    (le_refl (informationValue selectedContract observedBefore))\'), (\'\\nnamespace Phase17Protected\\nset_option maxRecDepth\', \'\\nnamespace Phase17Protected\\nopen RcpRclmFormalCoreV2\\nset_option maxRecDepth\')]\n\nclass LeanRepairRegressionTests(unittest.TestCase):\n    """Source/renderer regressions only: actual Lean checking is still required."""\n    def test_goal_self_proof_uses_complete_simplification(self):\n        text=l.template(ROOT).decode(\'utf-8\')\n        self.assertIn(\'  | cons row rest ih => simp [goalDistance, ih]\',text)\n        self.assertNotIn(\'simp only [goalDistance, if_pos rfl, zero_add, ih]\',text)\n    def test_attach_has_explicit_existing_kernel_result_type(self):\n        text=l.template(ROOT).decode(\'utf-8\')\n        self.assertIn(\'    (observe : State → Observation) (contract : Contract) :\\n\'\n                      \'    Learned.FrontierKernel (Task := Task) (Generator := Generator)\\n\'\n                      \'      (Proposal := Proposal) (PackageHash := PackageHash) base :=\',text)\n    def test_root_namespace_reopened_for_selected_theorems(self):\n        for raw in RENDERED.values():\n            self.assertIn(b\'\\nnamespace Phase17Protected\\nopen RcpRclmFormalCoreV2\\nset_option maxRecDepth\',raw)\n    def test_information_proof_is_a_single_finished_term(self):\n        for raw in RENDERED.values():\n            self.assertIn(b\'  simpa only [selected_observation_retained, add_zero] using\\n\'\n                          b\'    (le_refl (informationValue selectedContract observedBefore))\',raw)\n            self.assertNotIn(b\'  rw [selected_observation_retained, add_zero]\\n  exact le_rfl\',raw)\n    def test_all_five_certificates_only_have_declared_corrections(self):\n        corrections=REPAIR_CORRECTIONS\n        for label,raw in RENDERED.items():\n            with self.subTest(label=label):\n                old=(ROOT/\'artifacts/development/phase17m\'/(label+\'.lean\')).read_bytes()\n                for before,after in corrections:\n                    a,b=before.encode(\'utf-8\'),after.encode(\'utf-8\')\n                    self.assertEqual(old.count(a),1)\n                    old=old.replace(a,b,1)\n                self.assertEqual(raw,old)\n    def test_physical_literals_and_bindings_are_unchanged(self):\n        prefixes=(b\'def observedBefore\',b\'def observedAfter\',b\'def selectedContract\',\n                  b\'def boundContract\',b\'def jointBinding\',b\'def semanticBinding\')\n        for label,raw in RENDERED.items():\n            old=(ROOT/\'artifacts/development/phase17m\'/(label+\'.lean\')).read_bytes()\n            self.assertEqual([s for s in raw.splitlines() if s.startswith(prefixes)],\n                             [s for s in old.splitlines() if s.startswith(prefixes)])\n    def test_all_theorem_headers_are_unchanged(self):\n        for label,raw in RENDERED.items():\n            old=(ROOT/\'artifacts/development/phase17m\'/(label+\'.lean\')).read_bytes()\n            pattern=rb\'(?:^|\\n)theorem\\s+.*?:=\'\n            self.assertEqual(re.findall(pattern,raw,re.S),re.findall(pattern,old,re.S))\n            self.assertGreaterEqual(len(re.findall(pattern,raw,re.S)),14)\n    def test_repair_rendering_does_not_change_semantic_packet(self):\n        prepared=DATA[-1];old=prepared.packet_bytes\n        for label in l.LABELS:\n            l.render_protected(prepared,source_root=ROOT,negative=None if label==\'Protected\' else label)\n        self.assertEqual(prepared.packet_bytes,old)\n        self.assertEqual(sha(old),\'a720bdaeac1b316d6e50b9a640cddfad52baff44c09a44a4fdeda2b977e4da67\')\n\n\n'
KIT_PINS = {'apply_phase17m.py': 'e24c4d15d475718a07b18ec29fb200c906d56859816c84466451319509ea8506', 'PAYLOAD_MANIFEST.json': 'd56142cba1c6e6465e2b59e6bb7a97a73a71e1cbe59aae15ba11e2bc9599f8a1', 'SHA256SUMS.txt': 'c53df66e801ca91647838f93906f430c8ead493778e590f23fe4108185008cc3'}
PATCH_PINS = {'lean/phase17_bridge/ProtectedSemantics.lean': '5b8f5bbf3806bd32659b60ce29e28c0d6b994c28ad7de5cd38a6317bab872c4b', 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/protected_semantics_lean.py': '63f1f8c30254ac6744dcf29669d292a0b344d65c88563111c5e0218d15acbf65', 'python/rcp_rclm_runtime_v5/tests_phase17m/test_protected_semantics.py': '15eeb2f16911c7ad37f2bbdfc1b5fb5617a2c9d101f11e56e5aa3ab0da85a468', 'scripts/run_phase17_protected_semantics_tests.py': 'fa4b7cb52fa0c18fa4fea92b45a05000aa45a473bc21390830b7017995a03b9b'}

def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def no_links(path):
    for p in (path, *path.parents):
        need(not p.is_symlink() and not (hasattr(p, 'is_junction') and p.is_junction()),
             'linked path: ' + str(p))


def read_json(path):
    no_links(path)
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON field: ' + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(path.read_bytes().decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def load_installer(kit):
    for name, expected in KIT_PINS.items():
        p = kit / name
        no_links(p)
        need(p.is_file() and sha(p.read_bytes()) == expected, 'original kit changed: ' + name)
    spec = importlib.util.spec_from_file_location('phase17m_verified_installer', kit / 'apply_phase17m.py')
    need(spec is not None and spec.loader is not None, 'cannot load original installer')
    a = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a)
    seen = set()
    for line in (kit / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        need(match is not None, 'invalid kit checksum line')
        expected, name = match.groups()
        need(name not in seen, 'duplicate kit checksum path'); seen.add(name)
        p = a.safe(kit, name)
        need(p.is_file() and sha(p.read_bytes()) == expected, 'kit file changed: ' + name)
    need(a.BASE == BASE, 'wrong original installer baseline')
    return a, a.verify_kit(kit)


def replace_once(raw, old, new):
    old, new = old.encode('utf-8'), new.encode('utf-8')
    need(raw.count(old) == 1 and new not in raw, 'unexpected correction preimage')
    result = raw.replace(old, new, 1)
    need(result.replace(new, old, 1) == raw, 'nonreversible correction')
    return result


def corrected_template(raw):
    return replace_once(replace_once(raw, OLD_GOAL, NEW_GOAL), OLD_ATTACH, NEW_ATTACH)


def corrected_certificate(raw):
    for old, new in ((OLD_GOAL, NEW_GOAL), (OLD_ATTACH, NEW_ATTACH),
                     (OLD_BOUND, NEW_BOUND), (OLD_NS, NEW_NS)):
        raw = replace_once(raw, old, new)
    return raw


def test_methods(raw):
    result = {}
    for cls in ast.parse(raw).body:
        if isinstance(cls, ast.ClassDef):
            for f in cls.body:
                if isinstance(f, ast.FunctionDef) and f.name.startswith('test_'):
                    key = cls.name + '.' + f.name
                    need(key not in result, 'duplicate test method')
                    result[key] = ast.dump(f, include_attributes=False)
    return result


def corrected_sources(payload):
    for name, expected in PATCH_PINS.items():
        need(sha(payload[name]) == expected, 'unexpected patch preimage: ' + name)
    bridge = corrected_template(payload[TEMPLATE])
    raw = payload[MODULE]
    module = replace_once(raw, "BRIDGE_SHA256 = '" + sha(payload[TEMPLATE]) + "'",
                          "BRIDGE_SHA256 = '" + sha(bridge) + "'")
    module = replace_once(module, "'\\nnamespace Phase17Protected\\n'",
                          "'\\nnamespace Phase17Protected\\nopen RcpRclmFormalCoreV2\\n'")
    module = replace_once(module, OLD_BOUND, NEW_BOUND)
    marker = b'class GateControlTests(unittest.TestCase):'
    need(payload[TEST].count(marker) == 1, 'test insertion boundary differs')
    tests = payload[TEST].replace(marker, EXTRA_TESTS.encode('utf-8') + marker, 1)
    prior, after = test_methods(payload[TEST]), test_methods(tests)
    need(len(prior) == 83 and len(after) == TEST_COUNT and all(after.get(k) == v for k, v in prior.items()),
         'original tests or assertions changed')
    runner = replace_once(payload[RUNNER], 'EXPECTED=83\n', 'EXPECTED=91\n')
    changes = {TEMPLATE: bridge, MODULE: module, TEST: tests, RUNNER: runner}
    for name, source in changes.items():
        if name.endswith('.py'): compile(source, name, 'exec')
    def functions(data):
        return {f.name: ast.dump(f, include_attributes=False) for f in ast.parse(data).body
                if isinstance(f, ast.FunctionDef)}
    before, after = functions(raw), functions(module)
    need(set(before) == set(after) and all(before[k] == after[k] for k in before if k != 'render_protected'),
         'acceptance/template-reader functions changed')
    pattern = rb'(?:^|\n)theorem\s+.*?:='
    need(re.findall(pattern, payload[TEMPLATE], re.S) == re.findall(pattern, bridge, re.S),
         'template theorem header changed')
    for label in ('Protected','ChangedProbability','ChangedGoal','ChangedTarget','MixedCandidate'):
        old = payload[ARTIFACT + label + '.lean']; new = corrected_certificate(old)
        need(re.findall(pattern, old, re.S) == re.findall(pattern, new, re.S), 'selected theorem header changed')
        need(new.startswith(bridge), 'generated template prefix mismatch')
    return changes


def retained_command(a, out, label, script, count=None):
    report = read_json(out / (label + '.json'))
    stdout = a.safe(out, label + '.out.txt').read_bytes()
    stderr = a.safe(out, label + '.err.txt').read_bytes()
    need(report.get('problem') is None, 'previous command launch/timeout error: ' + label)
    need(report['stdout_sha256'] == sha(stdout) and report['stderr_sha256'] == sha(stderr),
         'previous command log hash changed: ' + label)
    argv = report['argv']
    need(type(argv) is list and len(argv) >= 2 and argv[1] == script, 'previous command changed: ' + label)
    if count is not None:
        need(len(argv) == 2 and type(report['returncode']) is int and report['returncode'] == 0,
             'previous test suite did not pass: ' + label)
        a.check_test_log(stderr, count)
    return report


def verify_failed_source(a, stage, payload):
    a.clean(stage)
    need(Path(a.text(stage, 'rev-parse', '--show-toplevel')).resolve() == stage, 'wrong failed repository root')
    need(a.text(stage, 'rev-parse', 'HEAD') == FAILED_SOURCE and
         a.text(stage, 'rev-parse', 'HEAD^{tree}') == FAILED_TREE, 'failed source/tree changed')
    need(a.text(stage, 'rev-list', '--parents', '-n', '1', FAILED_SOURCE).split() == [FAILED_SOURCE, BASE],
         'failed source ancestry changed')
    changed = {n.decode('utf-8') for n in a.git(stage, 'diff', '--name-only', '-z', BASE, FAILED_SOURCE).split(b'\0') if n}
    need(changed == set(payload) | {'SHA256SUMS.txt'}, 'failed source surface differs from original kit')
    for name, raw in payload.items():
        need(a.git(stage, 'cat-file', 'blob', FAILED_SOURCE + ':' + name) == raw and
             a.safe(stage, name).read_bytes() == raw, 'failed source bytes changed: ' + name)


def inspect_failure(a, run, tools, payload):
    progress = read_json(run / 'progress.json')
    need(progress.get('base') == BASE and progress.get('stage') == 'stopped' and
         progress.get('original_checkout_changed') is False and progress.get('pushed') is False and
         progress.get('tested_code_commit') == FAILED_SOURCE, 'not the recorded unadvanced failure')
    out = run / 'e'
    tests = retained_command(a, out, 'new-tests', RUNNER, 83)
    regression = retained_command(a, out, 'joint-regression', 'scripts/run_phase17_joint_tests.py', 66)
    command = retained_command(a, out, 'protected-semantics-gate', GATE_RUNNER)
    argv = command['argv']
    need(type(command.get('returncode')) is int and command['returncode'] == 2 and len(argv) == 8 and
         argv[2:5] == ['--test-fixture', '--require-lean', '--lean-workspace'] and argv[6] == '--output' and
         Path(argv[5]).resolve() == (tools / 'formal-root').resolve() and
         Path(argv[7]).resolve() == (out / 'gate').resolve(), 'unexpected prior gate command')
    report = read_json(out / 'gate/execution.json')
    need(report.get('schema') == 'rcp-rclm.phase17m.protected-semantics-run.v1' and
         report.get('source_commit') == FAILED_SOURCE and report.get('source_tree') == FAILED_TREE and
         report.get('synthetic_fixture') is True and report.get('local_increment_checks_passed') is False and
         report.get('preparation_checks_passed') is False and
         type(report.get('automatic_retries')) is int and report['automatic_retries'] == 0 and
         report.get('failure') == {'type': 'ControlError', 'reason': 'protected semantic Lean gate did not pass'},
         'not the recorded failed gate')
    need(read_json(out / 'protected-semantics-gate.out.txt') == report and
         not a.safe(out, 'protected-semantics-gate.err.txt').read_bytes(), 'saved command/report mismatch')
    need(set(report['claims']) == set(a.FALSE_KEYS) and all(v is False for v in report['claims'].values()), 'failed report overclaims')
    for name, expected in [('packet_sha256', a.PACKET), ('joint_packet_sha256', a.JOINT),
                           ('task_contract_sha256', a.CONTRACT), ('transcript_sha256', a.TRANSCRIPT),
                           ('predecessor_package_hash', a.PARENT), ('candidate_package_hash', a.CANDIDATE)]:
        need(report.get(name) == expected, 'previous binding changed: ' + name)
    for name, expected in [('protected_task_count',11),('teacher_forced_position_count',28),
                           ('conditional_rows_per_package',260),('production_row_comparisons',520),
                           ('unique_conditional_rows',37),('selected_goal_drift',0)]:
        need(type(report.get(name)) is int and report[name] == expected, 'previous count changed: ' + name)
    need(all(report[k] is False for k in a.UNPROVED) and report['new_recursive_tasks_closed'] == [] and
         report['full_root_assessment'] == 'blocked_missing_semantic_witnesses', 'previous scope changed')
    gate = report['protected_semantics_gate']
    need(gate['status'] == 'rejected' and gate['theorem_axioms'] == {} and
         gate['protected_sparse_goal_information_checked'] is False and gate['negative_controls_rejected'] == [] and
         gate['packet_sha256'] == PACKET_SHA and gate['new_named_audits'] == 14 and
         gate['failure'] == {'type':'ControlError','reason':'protected semantics certificate rejected'},
         'unexpected gate boundary')
    need(set(gate['claims']) == set(a.FALSE_KEYS) and all(v is False for v in gate['claims'].values()), 'gate overclaims')
    commands = gate['commands']
    need(len(commands) == 2 and [c['returncode'] for c in commands] == [0,1] and
         all(type(c['returncode']) is int for c in commands), 'unexpected compiler sequence')
    for c in commands:
        for stream in ('stdout','stderr'):
            need(type(c[stream]) is str and sha(c[stream].encode('utf-8')) == c[stream + '_sha256'], 'compiler log changed')
    need(not commands[0]['stderr'] and re.match(r'^Lean \(version 4\.31\.0(?:,|\))', commands[0]['stdout']), 'wrong compiler')
    c = commands[1]
    need(not c['stderr'] and c['stdout_sha256'] == COMPILER_STDOUT_SHA and
         'error: unsolved goals' in c['stdout'] and "Failed to infer type of definition `attach`" in c['stdout'] and
         'No goals to be solved' in c['stdout'] and 'Unknown identifier `RCP.QuantumFinite.vonNeumannEntropy`' in c['stdout'],
         'not the exact reported elaboration/proof failure')
    need(c['argv'][1:4] == ['--keep-toolchain','--no-cache','env'] and
         c['argv'][-1].replace('\\','/').endswith('/Protected.lean'), 'wrong prior proof command')
    a.validate_gate_files(out / 'gate', report)
    for label in a.SOURCE_LABELS:
        raw = a.safe(out / 'gate', label + '.lean').read_bytes()
        need(raw == payload[ARTIFACT + label + '.lean'], 'generated certificate differs from original: ' + label)
        corrected_certificate(raw)
    for name in ('packet.json','joint_packet.json','ordered_transcript.json','task_contract.json'):
        need(a.safe(out / 'gate', name).read_bytes() == payload[ARTIFACT + name], 'original evidence differs: ' + name)
    expected = {label + suffix for label in ('new-tests','joint-regression','protected-semantics-gate')
                for suffix in ('.json','.out.txt','.err.txt')} | {
                'gate/packet.json','gate/execution.json','gate/SHA256SUMS.txt','gate/ordered_transcript.json',
                'gate/joint_packet.json','gate/task_contract.json',*('gate/' + n + '.lean' for n in a.SOURCE_LABELS)}
    need(set(a.retained_files(out)) == expected, 'unexpected previous evidence surface')
    return {'source_commit':FAILED_SOURCE,'source_tree':FAILED_TREE,'new_tests_previously_passed':83,
            'prior_test_command':tests,'joint_regressions_retained_not_rerun':66,'regression_source':FAILED_SOURCE,
            'retained_regression_command':regression,'failed_gate_command':command,
            'compiler_stdout_sha256':COMPILER_STDOUT_SHA,'failure':gate['failure'],
            'old_failure_relabelled_as_success':False,
            'prior_execution_sha256':sha((out/'gate/execution.json').read_bytes())}


def prior_snapshot(a, run):
    return {'progress.json':(run/'progress.json').read_bytes(),
            **{'e/'+n:raw for n,raw in a.retained_files(run/'e').items()}}


def verify_artifacts(a, out, prior_files, execution):
    for name in ('packet.json','joint_packet.json','ordered_transcript.json','task_contract.json'):
        need((out/'gate'/name).read_bytes() == prior_files['e/gate/'+name], 'unchanged evidence differs: '+name)
    need(execution['packet_sha256'] == PACKET_SHA, 'semantic packet changed during repair')
    for label in a.SOURCE_LABELS:
        old=prior_files['e/gate/'+label+'.lean']
        need((out/'gate'/(label+'.lean')).read_bytes() == corrected_certificate(old),
             'unexpected proof/candidate change: '+label)


def retain_evidence(a, stage, run, out, source, tree, commands, prior, prior_files, execution):
    for name,raw in prior_files.items():
        p=a.safe(out,'prior-attempt/'+name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    (out/'continuation.py').write_bytes(Path(__file__).read_bytes())
    report={'schema':'rcp-rclm.phase17m.proof-recovery.v1','source_commit':source,'source_tree':tree,
        'commands':commands,'new_tests':TEST_COUNT,'new_renderer_regressions':8,
        'joint_regressions_retained_not_rerun':66,'joint_regression_source':FAILED_SOURCE,
        'prior_failure':prior,'previous_failed_source_preserved':FAILED_SOURCE,
        'correction_scope':['goal self proof','explicit existing attach result type','selected namespace scope',
                            'finished information-bound proof','template digest binding'],
        'theorem_headers_changed':False,'candidate_facts_changed':False,'semantic_definitions_changed':False,
        'acceptance_functions_changed':False,'immutable_root_changed':False,
        'prior_history_bytes_rewritten':False,'synthetic_fixture':True,'new_named_audits':14,
        'new_proofs_kernel_executed':True,'protected_task_count':11,'teacher_forced_position_count':28,
        'conditional_rows_per_package':260,'production_row_comparisons':520,'unique_conditional_rows':37,
        'selected_goal_drift':0,'ordered_transcript_sha256':a.TRANSCRIPT,'candidate_package_hash':a.CANDIDATE,
        'packet_sha256':a.PACKET,'joint_packet_sha256':a.JOINT,'task_contract_sha256':a.CONTRACT,
        'full_root_assessment':'blocked_missing_semantic_witnesses','remaining_witness_classes':list(a.REMAINING),
        'gate_execution_sha256':sha((out/'gate/execution.json').read_bytes()),'automatic_retries':0,
        'network_setup_requested':False,'github_hosted_ci_passed':False,'cross_platform_validation':False,
        'continuation_sha256':sha(Path(__file__).read_bytes()),
        **{k:False for k in a.UNPROVED},**{k:False for k in a.FALSE_KEYS}}
    a.write(out/'operator-validation.json',report)
    files=a.retained_files(out);files['.gitattributes']=b'* -text\n'
    files['SHA256SUMS.txt']=''.join(sha(raw)+'  '+n+'\n' for n,raw in sorted(files.items())).encode('utf-8')
    rel=a.EVIDENCE+'/op-'+source[:12]+'-proof'
    for n,raw in files.items():
        p=a.safe(stage,rel+'/'+n);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    status=read_json(stage/a.STATUS);status['stage']='phase17m_protected_sparse_semantics'
    status['evidence_records']['phase17m_operator_capture']=rel+'/operator-validation.json'
    status['implemented_scope'].update(protected_sparse_probability_reconstruction=True,
        original_protected_target_binding=True,selected_sparse_goal_information_fields=True,
        root_transition_certificate_integration=False)
    status['validation'].update(phase17m_tested_code_commit=source,phase17m_new_tests=TEST_COUNT,
        phase17m_new_renderer_regressions=8,phase17m_joint_regressions_retained_not_rerun=66,
        phase17m_joint_regression_source=FAILED_SOURCE,phase17m_preserved_failed_source=FAILED_SOURCE,
        phase17m_new_formal_audits=14,phase17m_synthetic_fixture=True,
        phase17m_candidate_hash=a.CANDIDATE,phase17m_protected_tasks=11,phase17m_protected_positions=28,
        phase17m_row_comparisons=520,phase17m_full_learned_step_instantiated=False,
        phase17m_full_root_evaluated=False,phase17m_prior_joint_proofs_rerun=False,
        phase17m_proof_repair='goal proof; explicit existing kernel result type; selected namespace; finished bound proof',
        phase17m_local='protected sparse goal and diagonal KL semantics checked; not full goal/information/root acceptance')
    a.write(stage/a.STATUS,status)
    add={rel+'/'+n for n in files}|{a.STATUS};a.stage_exact(stage,add)
    for n,raw in files.items():need(a.git(stage,'cat-file','blob',':'+rel+'/'+n)==raw,'evidence staging conversion')
    a.refresh(stage);need(a.staged(stage)==add|{'SHA256SUMS.txt'},'unexpected evidence diff')
    a.git(stage,'commit','-m','Retain Phase17M protected semantic checks and original compiler failure [skip ci]')
    head=a.text(stage,'rev-parse','HEAD');a.clean(stage)
    return head,rel


def execute(args):
    for p in (args.repo,args.kit,args.failed_run,args.tools,args.work_root):no_links(p.absolute())
    repo,kit,failed,tools,work=(p.resolve() for p in (args.repo,args.kit,args.failed_run,args.tools,args.work_root))
    need(all(repo!=p and repo not in p.parents and p not in repo.parents for p in (kit,failed,tools,work)),
         'kit, failed run, cache and work root must be outside repository')
    need(work!=tools and tools not in work.parents and work not in tools.parents,'work and cache overlap')
    need(work!=failed and failed not in work.parents,'new work root cannot be inside failed workspace')
    a,payload=load_installer(kit);changes=corrected_sources(payload)
    a.clean(repo)
    need(Path(a.text(repo,'rev-parse','--show-toplevel')).resolve()==repo,'not original repository root')
    need(a.text(repo,'branch','--show-current')==a.BRANCH and a.text(repo,'rev-parse','HEAD')==BASE,
         'original branch or HEAD moved')
    need(a.text(repo,'remote','get-url','origin') in a.ORIGINS and
         a.text(repo,'remote','get-url','--push','origin') in a.ORIGINS,'wrong public repository destination')
    need(a.remote_head(repo)==BASE,'remote branch moved; no overwrite')
    need((tools/'formal-root').is_dir(),'existing pinned tools required; no downloads')
    old_stage=(failed/'c').resolve(strict=True);verify_failed_source(a,old_stage,payload)
    prior=inspect_failure(a,failed,tools,payload);frozen=prior_snapshot(a,failed)
    author,email=a.text(repo,'config','user.name'),a.text(repo,'config','user.email')
    need(author and email,'Git author not configured')
    work.mkdir(exist_ok=True,parents=True);run=work/('mp-'+uuid.uuid4().hex[:8]);run.mkdir()
    stage,out,hooks=run/'c',run/'e',run/'h';out.mkdir();hooks.mkdir()
    progress={'base':BASE,'stage':'created','previous_failed_source':FAILED_SOURCE,
              'original_checkout_changed':False,'pushed':False}
    a.write(run/'progress.json',progress)
    print('Phase17M proof continuation workspace: '+str(run),flush=True)
    try:
        a.run_command(run,out,'clone-preserved-source',['git','-c','core.longpaths=true','clone',
            '--no-hardlinks','--no-checkout','--local',str(old_stage),str(stage)])
        for key,value in [('core.autocrlf','false'),('core.longpaths','true'),('core.hooksPath',str(hooks)),
                           ('user.name',author),('user.email',email)]:a.git(stage,'config',key,value)
        a.git(stage,'checkout','--detach',FAILED_SOURCE);verify_failed_source(a,stage,payload)
        a.run_command(stage,out,'retained-manifest',[sys.executable,'scripts/phase17_refresh_checksums.py'])
        for name,raw in changes.items():a.safe(stage,name).write_bytes(raw)
        a.stage_exact(stage,changes)
        for name,raw in changes.items():need(a.git(stage,'cat-file','blob',':'+name)==raw,'patch staging conversion')
        a.refresh(stage);need(a.staged(stage)==set(changes)|{'SHA256SUMS.txt'},'unexpected source correction diff')
        a.git(stage,'commit','-m','Fix Phase17M Lean elaboration and protected-bound proofs [skip ci]')
        source,tree=a.text(stage,'rev-parse','HEAD'),a.text(stage,'rev-parse','HEAD^{tree}');a.clean(stage)
        progress.update(stage='source_committed',tested_code_commit=source);a.write(run/'progress.json',progress)
        commands=[a.run_command(stage,out,'new-tests',[sys.executable,RUNNER],TEST_COUNT)]
        print('Prior 66 joint regressions retained at their original source; not rerun.',flush=True)
        print('Checking corrected 14-audit certificate and all FOUR negative controls. No live campaign.',flush=True)
        try:
            commands.append(a.run_command(stage,out,'protected-semantics-gate',[sys.executable,GATE_RUNNER,
                '--test-fixture','--require-lean','--lean-workspace',str(tools/'formal-root'),
                '--output',str(out/'gate')],timeout=7500))
        except Exception:
            p=out/'gate/execution.json'
            if p.is_file():print(p.read_text(encoding='utf-8'),flush=True)
            raise
        execution=read_json(out/'gate/execution.json')
        a.validate_execution(execution,source,tree);a.validate_gate_files(out/'gate',execution)
        verify_artifacts(a,out,frozen,execution)
        verify_failed_source(a,old_stage,payload)
        need(prior_snapshot(a,failed)==frozen,'prior evidence changed during continuation')
        a.clean(stage);need(a.text(stage,'rev-parse','HEAD')==source,'tested source moved')
        head,rel=retain_evidence(a,stage,run,out,source,tree,commands,prior,frozen,execution)
        pr=run/'PR_UPDATE.md'
        pr.write_bytes(f'''## Phase 17A-M development - keep draft and unmerged

Tested source `{source}`; evidence head `{head}`. Earlier A-L evidence unchanged.
The failed source `{FAILED_SOURCE}` remains an ancestor; its compiler errors,
83 passing runtime tests and 66 passing joint regressions are preserved.
The 66 joint regressions remain attributed to that source and were NOT rerun.

The correction supplies the existing attach result type, completes goalDistance's
self proof, reopens the root namespace for generated statements, and uses one
finished proof for the selected information inequality. Its template hash was
updated. Runtime probability/goal calculations, candidate/packet facts, theorem
headers, immutable root, dependency pins and acceptance checks are unchanged.
All original 83 tests are preserved; eight renderer regressions bring the new
run to 91 tests. The original assistant 83-test logs remain historical records.

Actual pinned Lean checked all 14 protected sparse semantic audits and rejected
ChangedProbability, ChangedGoal, ChangedTarget and MixedCandidate. Original
packet, joint packet, task contracts and transcript bytes are unchanged. The
failed certificates are retained beside the corrected ones, never relabeled.

The 260-by-260 sparse probability observations were remeasured across both
physical packages (520 production/reference row comparisons). The eleven original
protected task contracts bind 28 teacher-forced positions. The fixed targets and
zero-regression goal/information policy are unchanged. This is the public
synthetic fixture, not new training, live capability improvement or promotion.
The earlier 43-audit joint certificate and 172 Phase17H plan proofs were not rerun.

Complete base/learned/autonomous acceptance, full goal/information semantics,
physical observation refinement, complete resources, recursive productivity,
durable challenge/history consumption, active atomic promotion, cross-turn
campaigns, independent/platform closure, Phase17/Gate E and EGC-0 remain open.
Evidence: `{rel}/operator-validation.json`.
'''.encode('utf-8'))
        progress.update(stage='validated',evidence_head=head);a.write(run/'progress.json',progress)
        a.advance(repo,stage,head,hooks,progress,run,args.push)
        progress['stage']='complete';a.write(run/'progress.json',progress)
        print(json.dumps({'completed':True,'tested_code_head':source,'evidence_head':head,'pushed':args.push,
            'previous_failed_source_preserved':FAILED_SOURCE,'new_tests':TEST_COUNT,'new_renderer_regressions':8,
            'joint_regressions_retained_not_rerun':66,'new_named_audits':14,'protected_semantics_gate':'passed',
            'candidate_facts_changed':False,'theorem_headers_changed':False,'synthetic_fixture':True,
            'protected_task_count':11,'teacher_forced_position_count':28,'production_row_comparisons':520,
            'selected_goal_drift':0,'pr_description_file':str(pr),'pr68_keep_draft':True,
            'full_root_assessment':'blocked_missing_semantic_witnesses',
            **{k:False for k in a.UNPROVED},**{k:False for k in a.FALSE_KEYS}},indent=2))
        return 0
    except Exception:
        progress['stage']='stopped';a.write(run/'progress.json',progress)
        print('Stopped; workspace and logs retained: '+str(run),file=sys.stderr)
        print('Original checkout advanced: '+str(progress['original_checkout_changed']),file=sys.stderr)
        raise


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('repo','kit','failed-run','tools'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--work-root',type=Path,default=Path.home()/'.r17')
    ap.add_argument('--push',action='store_true')
    return execute(ap.parse_args(argv))


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        print(type(exc).__name__+': '+str(exc),file=sys.stderr);raise SystemExit(2)
