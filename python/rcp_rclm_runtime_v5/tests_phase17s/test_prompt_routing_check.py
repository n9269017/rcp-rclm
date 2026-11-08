"""Adversarial saved-record guards; controlled logs are not Lean evidence."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

from rcp_rclm_runtime_v5.phase17 import prompt_routing as routing
from rcp_rclm_runtime_v5.phase17 import prompt_routing_check as checker
from rcp_rclm_runtime_v5.phase17 import prompt_routing_lean as renderer

ROOT = Path(__file__).resolve().parents[3]


class FormalRecordGuards(unittest.TestCase):
    def setUp(self):
        self.names, self.labels = renderer.NAMES, renderer.LABELS
        self.sources = {name: ('controlled-log-fixture:' + name).encode()
                        for name in (*checker.DEPENDENCIES, *self.labels)}
        self.packet = 'a' * 64
        self.audits = ''.join("'" + name + "' does not depend on any axioms\n" for name in self.names)

        def command(stdout='', code=0, label=None):
            result = {'returncode': code, 'stdout': stdout, 'stderr': '',
                      'stdout_sha256': routing.sha(stdout.encode()), 'stderr_sha256': routing.sha(b'')}
            if label is not None:
                result.update(label=label, source_sha256=routing.sha(self.sources[label]),
                              argv=['/fixture/lake', '--keep-toolchain', '--no-cache', 'env', '/fixture/lean',
                                    '--root=/fixture/fresh', '/fixture/fresh/' + label + '.lean'])
            else:
                result['argv'] = ['/fixture/lean', '--version']
            return result

        compiles, resolutions, modules = [], [], {}
        for index, name in enumerate(checker.DEPENDENCIES):
            artifact = name + '.olean'
            path = '/fixture/fresh/' + artifact
            hashes = {artifact: str(index + 4) * 64}
            compiled = command(label=name)
            compiled.update(output_artifacts_sha256=dict(hashes),
                            argv=['/fixture/lake', '--keep-toolchain', '--no-cache', 'env', '/fixture/lean',
                                  '--root=/fixture/fresh', '-o', path,
                                  '/fixture/fresh/' + name + '.lean'])
            compiles.append(compiled)
            client = checker.DEPENDENCIES[1] if index == 0 else self.labels[0]
            resolution = command('/fixture/tools/Init.olean\n/fixture/tools/Init.olean\n' + path + '\n')
            resolution.update(label=name + '_resolution', source_sha256=routing.sha(self.sources[client]),
                              argv=['/fixture/lake', '--keep-toolchain', '--no-cache', 'env', '/fixture/lean',
                                    '--root=/fixture/fresh', '--deps', '/fixture/fresh/' + client + '.lean'])
            resolutions.append(resolution)
            modules[name] = {'name': name, 'source_sha256': routing.sha(self.sources[name]),
                             'artifacts_sha256': hashes, 'resolved_module_path': path,
                             'compiled_in_this_run': True, 'prior_success_report_used_as_proof': False}
        commands = [command('Lean (version 4.31.0, controlled log fixture)\n'), *compiles, *resolutions,
                    command(self.audits, label=self.labels[0])]
        commands += [command('error: Tactic `decide` proved that the proposition\nFalse\nis false\n', 1, name)
                     for name in self.labels[1:]]
        self.result = {
            'schema': checker.SCHEMA, 'status': 'passed', 'packet_sha256': self.packet, 'commands': commands,
            'theorem_axioms': {name: [] for name in self.names}, 'negative_controls_rejected': list(self.labels[1:]),
            'new_named_audits': len(self.names), 'protected_prompt_routing_checked': True,
            'protected_task_execution_bound': True, 'claims': {name: False for name in routing.FALSE_CLAIMS},
            'source_sha256': {name: routing.sha(raw) for name, raw in self.sources.items()},
            'executable_sha256': {'/fixture/lean': '1'*64, '/fixture/lake': '2'*64, '/fixture/git': '3'*64},
            'dependency_modules': modules, 'trusted_import_cache_assumption': True,
            'byte_capture_and_json_parsing_remain_external': True, 'python_execution_remains_external': True,
            'full_transformer_equivalence': False, 'old_proof_campaigns_rerun': False}

    def bad(self, mutate):
        result = copy.deepcopy(self.result)
        mutate(result)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            checker.validate_result(result, self.sources, self.packet)

    @staticmethod
    def output(result, index, text):
        result['commands'][index].update(stdout=text, stdout_sha256=routing.sha(text.encode()))

    def test_complete_controlled_record_satisfies_contract(self):
        checker.validate_result(self.result, self.sources, self.packet)

    def test_preparation_and_partial_proof_cannot_pass(self):
        self.bad(lambda r: r.update(status='not_requested'))
        self.bad(lambda r: r.update(protected_prompt_routing_checked=False))
        self.bad(lambda r: r.update(protected_task_execution_bound=False))

    def test_packet_and_source_substitution_rejected(self):
        self.bad(lambda r: r.update(packet_sha256='0'*64))
        self.bad(lambda r: r['source_sha256'].__setitem__(self.labels[0], '0'*64))
        self.bad(lambda r: r['commands'][5].update(source_sha256='0'*64))

    def test_exact_dependency_and_case_source_order_required(self):
        for sources in (dict(reversed(tuple(self.sources.items()))),
                        {k: v for k, v in self.sources.items() if k != checker.DEPENDENCIES[1]},
                        {**self.sources, 'UnboundSource': b'x'}):
            with self.subTest(names=list(sources)), self.assertRaises(ValueError):
                checker.validate_result(self.result, sources, self.packet)

    def test_missing_extra_or_renamed_dependency_rejected(self):
        self.bad(lambda r: r['dependency_modules'].pop(checker.DEPENDENCIES[1]))
        self.bad(lambda r: r['dependency_modules'].__setitem__('OldR', {}))
        self.bad(lambda r: r['dependency_modules'][checker.DEPENDENCIES[1]].update(name=checker.DEPENDENCIES[0]))

    def test_fresh_compile_required_for_both_dependencies(self):
        for name in checker.DEPENDENCIES:
            with self.subTest(name=name):
                self.bad(lambda r, n=name: r['dependency_modules'][n].update(compiled_in_this_run=False))
                self.bad(lambda r, n=name: r['dependency_modules'][n].update(prior_success_report_used_as_proof=True))

    def test_dependency_compile_order_and_count_are_fixed(self):
        self.bad(lambda r: r['commands'].__setitem__(slice(1,3), list(reversed(r['commands'][1:3]))))
        self.bad(lambda r: r['commands'].pop(2))
        self.bad(lambda r: r['commands'].insert(2, copy.deepcopy(r['commands'][1])))

    def test_compiled_artifacts_bound_to_each_own_source(self):
        for index, name in enumerate(checker.DEPENDENCIES):
            with self.subTest(name=name):
                self.bad(lambda r, n=name: r['dependency_modules'][n].update(source_sha256='0'*64))
                self.bad(lambda r, n=name: r['dependency_modules'][n].update(artifacts_sha256={}))
                self.bad(lambda r, i=index, n=name: r['commands'][1+i]['output_artifacts_sha256'].__setitem__(n+'.olean', '0'*64))
                self.bad(lambda r, n=name: r['dependency_modules'][n]['artifacts_sha256'].__setitem__('../stale.olean', '0'*64))

    def test_failed_or_noisy_dependency_compile_rejected(self):
        for index in (1,2):
            self.bad(lambda r, i=index: r['commands'][i].update(returncode=1))
            self.bad(lambda r, i=index: self.output(r, i, 'warning: old cached proof\n'))

    def test_each_resolution_bound_to_its_client(self):
        for index in (3,4):
            self.bad(lambda r, i=index: r['commands'][i].update(source_sha256='0'*64))
            self.bad(lambda r, i=index: r['commands'][i].update(label='dependency_resolution'))
            self.bad(lambda r, i=index: r['commands'][i]['argv'].remove('--deps'))

    def test_shadowed_dependency_import_rejected(self):
        for index, name in enumerate(checker.DEPENDENCIES):
            def shadow(result, i=index, n=name):
                old = result['dependency_modules'][n]['resolved_module_path']
                stale = '/fixture/stale/' + n + '.olean'
                result['dependency_modules'][n]['resolved_module_path'] = stale
                self.output(result, 3+i, result['commands'][3+i]['stdout'].replace(old, stale))
            self.bad(shadow)

    def test_extra_duplicate_relative_or_conflicting_init_import_rejected(self):
        for index, name in enumerate(checker.DEPENDENCIES):
            self.bad(lambda r, i=index: self.output(r, 3+i, r['commands'][3+i]['stdout']+'/extra/Other.olean\n'))
            self.bad(lambda r, i=index, n=name: self.output(r, 3+i, r['commands'][3+i]['stdout']+n+'.olean\n'))
            self.bad(lambda r, i=index: self.output(r, 3+i, r['commands'][3+i]['stdout'].replace('/fixture/tools/Init.olean', '/other/Init.olean', 1)))

    def test_windows_path_case_and_slashes_are_equivalent(self):
        result = copy.deepcopy(self.result)
        result['executable_sha256'] = {'C:\\Tools\\lean.exe':'1'*64,'C:\\Tools\\lake.exe':'2'*64,'C:\\Tools\\git.exe':'3'*64}
        result['commands'][0]['argv'] = ['c:/tools/lean.exe','--version']
        for command in result['commands'][1:]:
            command['argv'][:6] = ['c:/tools/lake.exe','--keep-toolchain','--no-cache','env',
                                  'c:/tools/lean.exe','--root=C:\\Users\\Fixture\\Fresh']
            command['argv'][-1] = command['argv'][-1].replace('/fixture/fresh/','C:/Users/Fixture/Fresh/')
        for index, name in enumerate(checker.DEPENDENCIES):
            compiled = 'C:\\Users\\Fixture\\Fresh\\' + name + '.olean'
            resolved = 'c:/users/fixture/fresh/' + name.lower() + '.olean'
            result['commands'][1+index]['argv'][-2] = compiled
            result['dependency_modules'][name]['resolved_module_path'] = resolved
            self.output(result, 3+index, 'C:\\Tools\\Init.olean\nc:/tools/init.olean\n'+resolved+'\n')
        checker.validate_result(result, self.sources, self.packet)

    def test_compile_resolution_and_case_inputs_match_declared_source(self):
        for index in (1,2,3,4,5,6):
            self.bad(lambda r, i=index: r['commands'][i]['argv'].__setitem__(-1,'/fixture/fresh/Unrelated.lean'))

    def test_case_invocations_require_exact_recorded_tools(self):
        self.bad(lambda r: r['commands'][5].update(argv=['/other/tool','/old/Other.lean']))
        self.bad(lambda r: r['commands'][6].pop('argv'))
        self.bad(lambda r: r['commands'][5]['argv'].__setitem__(0,'/other/lake'))
        self.bad(lambda r: r['commands'][6]['argv'].__setitem__(4,'/other/lean'))

    def test_unrelated_executable_inventory_cannot_back_commands(self):
        self.bad(lambda r: r.update(executable_sha256={'/one':'1'*64,'/two':'2'*64,'/three':'3'*64}))
        self.bad(lambda r: r['executable_sha256'].__setitem__('/other/lean',r['executable_sha256'].pop('/fixture/lean')))

    def test_one_root_for_all_compile_and_case_commands(self):
        for index in (1,2,3,4,5,6):
            self.bad(lambda r, i=index: r['commands'][i]['argv'].__setitem__(5,'--root=/fixture/stale'))

    def test_compile_output_module_name_cannot_change(self):
        for index in (1,2):
            self.bad(lambda r, i=index: r['commands'][i]['argv'].__setitem__(-2,'/fixture/fresh/Other.olean'))

    def test_different_windows_drive_is_not_same_module(self):
        def different(result):
            name = checker.DEPENDENCIES[1]
            result['commands'][2]['argv'][-2] = 'C:/run/'+name+'.olean'
            result['dependency_modules'][name]['resolved_module_path'] = 'D:/run/'+name+'.olean'
            self.output(result, 4, 'C:/tools/Init.olean\nC:/tools/Init.olean\nD:/run/'+name+'.olean\n')
        self.bad(different)

    def test_posix_case_difference_rejected(self):
        def different(result):
            name = checker.DEPENDENCIES[0]
            old = result['dependency_modules'][name]['resolved_module_path']
            new = old.replace('/fresh/', '/FRESH/')
            result['dependency_modules'][name]['resolved_module_path'] = new
            self.output(result, 3, result['commands'][3]['stdout'].replace(old,new))
        self.bad(different)

    def test_missing_negative_command_or_claim_rejected(self):
        self.bad(lambda r: r['commands'].pop())
        self.bad(lambda r: r['negative_controls_rejected'].pop())

    def test_positive_failure_rejected(self):
        self.bad(lambda r: r['commands'][5].update(returncode=1))

    def test_timeout_kill_or_success_is_not_a_negative(self):
        for code in (0,-9,-999,137,True):
            self.bad(lambda r, c=code: r['commands'][6].update(returncode=c))

    def test_boolean_exitcode_and_numeric_proof_flags_rejected(self):
        self.bad(lambda r: r['commands'][5].update(returncode=False))
        self.bad(lambda r: r.update(protected_task_execution_bound=1))
        self.bad(lambda r: r.update(new_named_audits=True))

    def test_changed_stream_with_stale_hash_rejected(self):
        self.bad(lambda r: r['commands'][5].update(stdout='changed'))
        self.bad(lambda r: r['commands'][6].update(stderr='error'))

    def test_unrelated_negative_errors_not_counted(self):
        for out in ("error: unknown identifier 'old'\n",
                    'error: Tactic `decide` proved that the proposition\nerror: type mismatch\nFalse\nis false\n'):
            self.bad(lambda r, text=out: self.output(r, 6, text))

    def test_negative_audit_or_success_output_rejected(self):
        self.bad(lambda r: self.output(r, 6, r['commands'][6]['stdout']+self.audits))
        self.bad(lambda r: self.output(r, 6, r['commands'][6]['stdout']+'accepted\n'))

    def test_wrong_lean_version_rejected(self):
        self.bad(lambda r: self.output(r, 0, 'Lean (version 4.30.0)\n'))

    def test_positive_unapproved_axiom_rejected(self):
        for axiom in ('sorryAx','arbitraryRoutingAxiom'):
            text = ''.join("'"+name+"' depends on axioms: ["+axiom+"]\n" for name in self.names)
            with self.assertRaises(ValueError):
                checker.parse_audits(text)

    def test_exact_audit_sequence_required(self):
        lines = self.audits.splitlines(keepends=True)
        for text in (''.join(lines[1:]),''.join(reversed(lines)),self.audits+lines[0],self.audits+'extra\n'):
            with self.assertRaises(ValueError):
                checker.parse_audits(text)

    def test_reported_axioms_match_positive_output(self):
        self.bad(lambda r: r['theorem_axioms'].__setitem__(self.names[0],['Classical.choice']))

    def test_broad_claim_escalation_rejected(self):
        for name in routing.FALSE_CLAIMS:
            self.bad(lambda r, n=name: r['claims'].__setitem__(n,True))
        self.bad(lambda r: r['claims'].__setitem__('physical_execution_attested',0))

    def test_remaining_trust_boundaries_cannot_disappear(self):
        self.bad(lambda r: r.update(byte_capture_and_json_parsing_remain_external=False))
        self.bad(lambda r: r.update(python_execution_remains_external=False))
        self.bad(lambda r: r.update(full_transformer_equivalence=True))
        self.bad(lambda r: r.update(failure={'reason':'unresolved'}))


class GateBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('s_gate_test', ROOT/'scripts/run_phase17_prompt_routing_gate.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_output_parent_alias_cannot_enter_source(self):
        name = 's-forbidden-output'
        path = ROOT.parent/'nonexistent-s-parent'/'..'/ROOT.name/name
        with self.assertRaises(ValueError):
            self.module.main(['--output',str(path),'--test-fixture'])
        self.assertFalse((ROOT/name).exists())

    def test_inventory_binds_original_routing_definitions_and_new_checker(self):
        paths = self.module.source_paths()
        for name in ('python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase14/tasks.py',
                     'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase12/phase12e_tasks.py',
                     'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/prompt_routing_check.py',
                     'lean/phase17_bridge/ProtectedRouting.lean'):
            self.assertIn(name,paths)
        self.assertNotIn('SHA256SUMS.txt',paths)
        self.assertNotIn('docs/executable_core_v5/PHASE_17_LOCAL_VALIDATION.json',paths)
