"""Adversarial saved-record guards; controlled logs are not Lean evidence."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

from rcp_rclm_runtime_v5.phase17 import objective_context as routing
from rcp_rclm_runtime_v5.phase17 import objective_context_check as checker
from rcp_rclm_runtime_v5.phase17 import objective_context_lean as renderer

ROOT = Path(__file__).resolve().parents[3]


class FormalRecordGuards(unittest.TestCase):
    @staticmethod
    def environment_fixture(windows=False):
        tool = 'C:/Tools' if windows else '/fixture/tools'
        cwd = ('C:/Users/Fixture/formal-root' if windows else '/fixture/workspace') + '/' + checker.gate.ROOT_PROJECT
        fresh = 'C:/Users/Fixture/Fresh' if windows else '/fixture/fresh'
        suffix, separator = ('.exe', ';') if windows else ('', ':')
        base = {'HOME': 'C:/Users/Fixture' if windows else '/fixture/home', 'PATH': tool + '/bin',
                'LEAN_PATH': fresh, 'ELAN_TOOLCHAIN': checker.gate.TOOLCHAIN,
                'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1',
                'GIT_CONFIG_GLOBAL': 'nul' if windows else '/dev/null', 'LAKE_NO_CACHE': 'true',
                'LAKE_ARTIFACT_CACHE': 'false', 'NoDefaultCurrentDirectoryInExePath': '1'}
        effective = dict(base, LEAN=tool + '/bin/lean' + suffix, LAKE=tool + '/bin/lake' + suffix,
                         LEAN_SYSROOT=tool, LEAN_SRC_PATH=tool + '/src/lean',
                         LEAN_PATH=separator.join(('.lake/build/lib/lean', tool + '/lib/lean', fresh)),
                         PATH='.lake/build/bin' + separator + base['PATH'], LAKE_CONFIG='')
        if windows:
            effective = {key.upper(): value for key, value in effective.items()}
        return {'schema': checker.ENVIRONMENT_SCHEMA, 'capture_semantics': checker.CAPTURE_SEMANTICS,
                'platform': 'nt' if windows else 'posix', 'cwd': cwd, 'fresh_module_directory': fresh,
                'base_environment': base, 'base_environment_sha256': routing.sha(checker._environment_bytes(base)),
                'effective_environment': effective,
                'effective_environment_sha256': routing.sha(checker._environment_bytes(effective)),
                'probe_executable': 'C:/Python/python.exe' if windows else '/fixture/python/bin/python3',
                'probe_executable_sha256': '4' * 64,
                'probe_source_sha256': routing.sha(checker.ENVIRONMENT_PROBE.encode())}

    @staticmethod
    def refresh_environment(result):
        """Rehash controlled fixtures so semantic guards, not stale hashes, are tested."""
        environment = result['compiler_environment']
        for key in ('base_environment', 'effective_environment'):
            environment[key + '_sha256'] = routing.sha(checker._environment_bytes(environment[key]))
        report = {'schema': checker.PROBE_SCHEMA, 'environment': environment['effective_environment'],
                  'executable': environment['probe_executable'], 'platform': environment['platform'],
                  'cwd': environment['cwd']}
        FormalRecordGuards.output(result, checker.ENVIRONMENT_INDEX, checker._environment_bytes(report).decode('ascii'))
        for index, command in enumerate(result['commands']):
            key = 'base_environment_sha256' if index < checker.COMPILE_START else 'effective_environment_sha256'
            command.update(cwd=environment['cwd'], environment_sha256=environment[key])

    def setUp(self):
        self.names, self.labels = renderer.NAMES, renderer.LABELS
        self.sources = {name: ('controlled-log-fixture:' + name).encode()
                        for name in (*checker.COMPILED_MODULES, *self.labels)}
        self.packet = 'a' * 64
        self.audits = ''.join("'" + name + "' does not depend on any axioms\n" for name in self.names)
        environment = self.environment_fixture()

        def command(stdout='', code=0, label=None):
            result = {'returncode': code, 'stdout': stdout, 'stderr': '',
                      'stdout_sha256': routing.sha(stdout.encode()), 'stderr_sha256': routing.sha(b'')}
            if label is not None:
                result.update(label=label, source_sha256=routing.sha(self.sources[label]),
                              argv=['/fixture/tools/bin/lean', *checker.DIRECT_FLAGS,
                                    '--root=/fixture/fresh', '/fixture/fresh/' + label + '.lean'])
            else:
                result['argv'] = ['/fixture/tools/bin/lean', '--version']
            return result

        compiles, resolutions, modules = [], [], {}
        for index, name in enumerate(checker.COMPILED_MODULES):
            artifact = name + '.olean'
            path = '/fixture/fresh/' + artifact
            hashes = {artifact: format(index + 4, '064x')}
            compiled = command(label=name)
            compiled.update(output_artifacts_sha256=dict(hashes),
                            argv=['/fixture/tools/bin/lean', *checker.DIRECT_FLAGS,
                                  '--root=/fixture/fresh', '-o', path,
                                  '/fixture/fresh/' + name + '.lean'])
            compiles.append(compiled)
            client = checker.RESOLUTION_CLIENTS[name]
            imports = list(checker._resolution_targets(name, '/fixture/fresh').values())
            resolution = command('/fixture/tools/Init.olean\n/fixture/tools/Init.olean\n' + '\n'.join(imports) + '\n')
            resolution.update(label=name + '_resolution', source_sha256=routing.sha(self.sources[client]),
                              argv=['/fixture/tools/bin/lean', *checker.DIRECT_FLAGS,
                                    '--root=/fixture/fresh', '--deps', '/fixture/fresh/' + client + '.lean'])
            resolutions.append(resolution)
            modules[name] = {'name': name, 'source_sha256': routing.sha(self.sources[name]),
                             'artifacts_sha256': hashes, 'resolved_module_path': path,
                             'compiled_in_this_run': True, 'prior_success_report_used_as_proof': False}
        capture = command()
        capture.update(label=checker.ENVIRONMENT_LABEL, source_sha256=environment['probe_source_sha256'],
                       probe_executable_sha256=environment['probe_executable_sha256'],
                       argv=['/fixture/tools/bin/lake', '--keep-toolchain', '--no-cache', 'env',
                             environment['probe_executable'], '-I', '-S', '-B', '-c', checker.ENVIRONMENT_PROBE])
        commands = [command('Lean (version 4.31.0, controlled log fixture)\n'), capture, *compiles, *resolutions,
                    command(self.audits, label=self.labels[0])]
        commands += [command('error: Tactic `decide` proved that the proposition\nFalse\nis false\n', 1, name)
                     for name in self.labels[1:]]
        self.result = {
            'schema': checker.SCHEMA, 'status': 'passed', 'packet_sha256': self.packet, 'commands': commands,
            'theorem_axioms': {name: [] for name in self.names}, 'negative_controls_rejected': list(self.labels[1:]),
            'new_named_audits': len(self.names), 'objective_policy_from_context_checked': True,
            'objective_challenge_binding_checked': True, 'claims': {name: False for name in routing.FALSE_CLAIMS},
            'source_sha256': {name: routing.sha(raw) for name, raw in self.sources.items()},
            'executable_sha256': {'/fixture/tools/bin/lean': '1'*64, '/fixture/tools/bin/lake': '2'*64,
                                  '/fixture/tools/bin/git': '3'*64},
            'compiler_environment': environment,
            'dependency_modules': {name: modules[name] for name in checker.DEPENDENCIES},
            'auxiliary_modules': {name: modules[name] for name in checker.AUXILIARIES},
            'trusted_import_cache_assumption': True,
            'byte_capture_remains_external': True, 'digest_authenticity_remains_external': True,
            'general_planner_equivalence': False, 'general_json_parser_equivalence': False,
            'general_sha256_equivalence': False, 'selected_objective_policy_checked': True,
            'selected_objective_challenge_binding_checked': True,
            'challenge_freshness_remains_external': True, 'objective_policy_succession_remains_external': True,
            'selected_sha256_computation_checked': True,
            'general_grammar_parameter_derivation_remains_external': True,
            'sha256_collision_resistance_remains_external': True, 'python_execution_remains_external': True,
            'full_transformer_equivalence': False, 'old_proof_campaigns_rerun': False}
        self.refresh_environment(self.result)

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

    def test_environment_preparation_is_counted_and_cannot_be_omitted(self):
        self.assertEqual(len(self.result['commands']), 22 + len(self.labels))
        self.bad(lambda r: r.pop('compiler_environment'))
        self.bad(lambda r: r['commands'].pop(checker.ENVIRONMENT_INDEX))
        self.bad(lambda r: r['commands'].insert(checker.ENVIRONMENT_INDEX,
                                              copy.deepcopy(r['commands'][checker.ENVIRONMENT_INDEX])))
        self.bad(lambda r: r['commands'].__setitem__(slice(0, 2), list(reversed(r['commands'][:2]))))

    def test_direct_worker_async_flags_and_order_are_exact(self):
        for index in range(checker.COMPILE_START, len(self.result['commands'])):
            with self.subTest(command=index):
                self.bad(lambda r, i=index: r['commands'][i]['argv'].pop(1))
                self.bad(lambda r, i=index: r['commands'][i]['argv'].__setitem__(1, '-j2'))
                self.bad(lambda r, i=index: r['commands'][i]['argv'].__setitem__(2, '-DElab.async=true'))
                self.bad(lambda r, i=index: r['commands'][i]['argv'].__setitem__(slice(1, 3),
                                                                               list(reversed(checker.DIRECT_FLAGS))))
                self.bad(lambda r, i=index: r['commands'][i]['argv'].insert(3, '-j1'))
                self.bad(lambda r, i=index: r['commands'][i]['argv'].insert(3, '-DElab.async=true'))

    def test_direct_lean_calls_cannot_reintroduce_a_lake_parent(self):
        for index in range(checker.COMPILE_START, len(self.result['commands'])):
            self.bad(lambda r, i=index: r['commands'][i]['argv'].__setitem__(slice(0, 0),
                ['/fixture/tools/bin/lake', '--keep-toolchain', '--no-cache', 'env']))

    def test_environment_probe_arguments_and_isolation_are_pinned(self):
        for index, replacement in ((0, '/other/lake'), (4, '/other/python'), (5, '-E'),
                                   (6, '-s'), (7, '-O'), (8, '-m'),
                                   (9, checker.ENVIRONMENT_PROBE + '\n')):
            self.bad(lambda r, i=index, value=replacement:
                     r['commands'][checker.ENVIRONMENT_INDEX]['argv'].__setitem__(i, value))
        self.bad(lambda r: r['commands'][checker.ENVIRONMENT_INDEX]['argv'].pop(6))
        self.bad(lambda r: r['commands'][checker.ENVIRONMENT_INDEX]['argv'].append('unbound'))

    def test_environment_probe_interpreter_and_source_hashes_are_bound(self):
        self.bad(lambda r: r['compiler_environment'].update(probe_executable_sha256='0' * 64))
        self.bad(lambda r: r['commands'][checker.ENVIRONMENT_INDEX].update(probe_executable_sha256='0' * 64))
        self.bad(lambda r: r['compiler_environment'].update(probe_source_sha256='0' * 64))
        self.bad(lambda r: r['commands'][checker.ENVIRONMENT_INDEX].update(source_sha256='0' * 64))
        self.bad(lambda r: r['compiler_environment'].update(probe_executable='/other/python'))
        self.bad(lambda r: r['compiler_environment'].pop('probe_executable_sha256'))

    def test_environment_capture_requires_success_and_quiet_stderr(self):
        for code in (1, -9, -999, 137, True):
            self.bad(lambda r, value=code: r['commands'][checker.ENVIRONMENT_INDEX].update(returncode=value))
        self.bad(lambda r: r['commands'][checker.ENVIRONMENT_INDEX].update(
            stderr='warning\n', stderr_sha256=routing.sha(b'warning\n')))
        self.bad(lambda r: r['commands'][checker.ENVIRONMENT_INDEX].update(label='unrelated_capture'))

    def test_child_environment_json_is_canonical_unique_and_exact(self):
        original = self.result['commands'][checker.ENVIRONMENT_INDEX]['stdout']
        for text in (original.rstrip('\n'), 'warning\n' + original, original + '\n',
                     original.replace('"schema":', '"schema":"duplicate","schema":', 1),
                     original.replace('"environment":', '"unrelated":', 1),
                     original.replace('"schema":', '"extra":1,"schema":', 1)):
            self.bad(lambda r, value=text: self.output(r, checker.ENVIRONMENT_INDEX, value))

    def test_child_environment_report_cwd_platform_and_executable_match(self):
        for key, value in (('cwd', '/other/workspace'), ('platform', 'nt'), ('executable', '/other/python')):
            def mutate(result, field=key, replacement=value):
                report = json.loads(result['commands'][checker.ENVIRONMENT_INDEX]['stdout'])
                report[field] = replacement
                self.output(result, checker.ENVIRONMENT_INDEX, checker._environment_bytes(report).decode('ascii'))
            self.bad(mutate)

    def test_environment_mapping_hashes_are_exact(self):
        for key in ('base_environment_sha256', 'effective_environment_sha256'):
            self.bad(lambda r, field=key: r['compiler_environment'].__setitem__(field, '0' * 64))
        self.bad(lambda r: r['compiler_environment']['effective_environment'].__setitem__('LAKE_CONFIG', 'altered'))
        self.bad(lambda r: r['compiler_environment']['base_environment'].__setitem__('HOME', '/altered'))

    def test_every_command_is_bound_to_the_correct_environment(self):
        for index in range(len(self.result['commands'])):
            self.bad(lambda r, i=index: r['commands'][i].pop('environment_sha256'))
            self.bad(lambda r, i=index: r['commands'][i].update(environment_sha256='0' * 64))
            other = ('effective_environment_sha256' if index < checker.COMPILE_START else 'base_environment_sha256')
            self.bad(lambda r, i=index, field=other: r['commands'][i].update(
                environment_sha256=r['compiler_environment'][field]))

    def test_every_command_is_bound_to_the_same_project_cwd(self):
        for index in range(len(self.result['commands'])):
            self.bad(lambda r, i=index: r['commands'][i].pop('cwd'))
            self.bad(lambda r, i=index: r['commands'][i].update(cwd='/other/' + checker.gate.ROOT_PROJECT))

    def test_restricted_base_environment_rejects_ambient_overrides(self):
        for key in ('PYTHONPATH', 'LD_PRELOAD', 'LEAN_OPTS', 'GIT_CONFIG_COUNT'):
            def mutate(result, field=key):
                result['compiler_environment']['base_environment'][field] = 'injected'
                self.refresh_environment(result)
            self.bad(mutate)
        for key in ('GIT_TERMINAL_PROMPT', 'GIT_CONFIG_NOSYSTEM', 'LAKE_NO_CACHE',
                    'LAKE_ARTIFACT_CACHE', 'NoDefaultCurrentDirectoryInExePath'):
            def mutate(result, field=key):
                result['compiler_environment']['base_environment'][field] = 'changed'
                self.refresh_environment(result)
            self.bad(mutate)

    def test_effective_environment_rejects_unexpected_variables(self):
        for key in ('PYTHONPATH', 'LD_PRELOAD', 'LEAN_OPTS', 'GIT_CONFIG_COUNT'):
            def mutate(result, field=key):
                result['compiler_environment']['effective_environment'][field] = 'injected'
                self.refresh_environment(result)
            self.bad(mutate)

    def test_effective_toolchain_cache_and_search_bindings_are_required(self):
        for key in ('LEAN', 'LAKE', 'LEAN_SYSROOT', 'LEAN_SRC_PATH', 'PATH',
                    'ELAN_TOOLCHAIN', 'LAKE_NO_CACHE', 'LAKE_ARTIFACT_CACHE'):
            def mutate(result, field=key):
                result['compiler_environment']['effective_environment'].pop(field)
                self.refresh_environment(result)
            self.bad(mutate)
        for key, value in (('LEAN', '/other/lean'), ('LAKE', '/other/lake'),
                           ('LEAN_SYSROOT', '/other/toolchain'), ('ELAN_TOOLCHAIN', 'other'),
                           ('LAKE_NO_CACHE', 'false'), ('LAKE_ARTIFACT_CACHE', 'true')):
            def mutate(result, field=key, replacement=value):
                result['compiler_environment']['effective_environment'][field] = replacement
                self.refresh_environment(result)
            self.bad(mutate)

    def test_fresh_module_path_is_present_once_in_captured_search_path(self):
        for value in ('/fixture/stale', '/fixture/fresh:/fixture/fresh', '/fixture/fresh:', ''):
            def mutate(result, replacement=value):
                result['compiler_environment']['effective_environment']['LEAN_PATH'] = replacement
                self.refresh_environment(result)
            self.bad(mutate)
        def wrong_base(result):
            result['compiler_environment']['base_environment']['LEAN_PATH'] = '/fixture/stale'
            self.refresh_environment(result)
        self.bad(wrong_base)

    def test_base_values_are_preserved_including_presence(self):
        for key in ('HOME', 'GIT_TERMINAL_PROMPT', 'GIT_CONFIG_GLOBAL', 'NoDefaultCurrentDirectoryInExePath'):
            def mutate(result, field=key):
                result['compiler_environment']['effective_environment'][field] = 'changed'
                self.refresh_environment(result)
            self.bad(mutate)
        def unexpected_home(result):
            result['compiler_environment']['base_environment'].pop('HOME')
            self.refresh_environment(result)
        self.bad(unexpected_home)

    def test_empty_environment_values_remain_distinct_from_absence(self):
        report = checker._environment_report(self.result['commands'][checker.ENVIRONMENT_INDEX]['stdout'])
        self.assertEqual(report['environment']['LAKE_CONFIG'], '')
        self.assertNotEqual(checker._environment_bytes({'LAKE_CONFIG': ''}), checker._environment_bytes({}))
        self.assertEqual(checker._environment_mapping({'LAKE_CONFIG': ''}, checker.LAKE_VARIABLES, 'posix'),
                         {'LAKE_CONFIG': ''})
        def null_value(result):
            result['compiler_environment']['effective_environment']['LAKE_CONFIG'] = None
            self.refresh_environment(result)
        self.bad(null_value)

    def test_windows_environment_names_cannot_collide_by_case(self):
        with self.assertRaises(ValueError):
            checker._environment_mapping({'Path': 'C:/one', 'PATH': 'C:/two'}, {'PATH'}, 'nt')
        self.assertEqual(checker._environment_mapping({'Path': 'C:/one'}, {'PATH'}, 'nt'), {'PATH': 'C:/one'})

    def test_environment_scope_and_platform_metadata_are_fixed(self):
        self.bad(lambda r: r['compiler_environment'].update(capture_semantics='physical environment attested'))
        self.bad(lambda r: r['compiler_environment'].update(platform='other'))
        self.bad(lambda r: r['compiler_environment'].update(platform='nt'))
        self.bad(lambda r: r['compiler_environment'].update(schema='unrelated'))

    def test_exact_non_linear_resolution_client_graph(self):
        self.assertEqual(checker.RESOLUTION_CLIENTS, {
            'Phase17QDependency': 'Phase17RDependency', 'Phase17RDependency': 'Phase17SDependency',
            'Phase17SDependency': 'Phase17TDependency', 'Phase17TDependency': 'Phase17UDependency',
            'Phase17UDependency': 'Phase17VDependency', 'Phase17VDependency': 'Phase17WDependency',
            'Phase17WDependency': 'Phase17XDependency', 'Phase17XSha256Blocks': 'Phase17YSha256Blocks',
            'Phase17XDependency': 'ObjectiveContext', 'Phase17YSha256Blocks': 'ObjectiveContext'})
        for offset, wrong in ((6, 'Phase17XSha256Blocks'), (7, 'Phase17WDependency')):
            def mutate(result, index=offset, name=wrong):
                command = result['commands'][checker.RESOLUTION_START + index]
                command['argv'][-1] = '/fixture/fresh/' + name + '.lean'
                command['source_sha256'] = routing.sha(self.sources[name])
            self.bad(mutate)

    def test_x_arithmetic_precedes_x_result_and_y_arithmetic(self):
        self.assertEqual(checker.COMPILED_MODULES, (*checker.DEPENDENCIES[:-1],
                         'Phase17XSha256Blocks', 'Phase17XDependency', 'Phase17YSha256Blocks'))
        for a, b in ((7, 8), (8, 9)):
            def mutate(result, x=a, y=b):
                commands = result['commands']
                i, j = checker.COMPILE_START + x, checker.COMPILE_START + y
                commands[i], commands[j] = commands[j], commands[i]
            self.bad(mutate)

    def test_both_auxiliaries_need_fresh_source_bound_artifacts(self):
        for name in checker.AUXILIARIES:
            index = checker.COMPILE_START + checker.COMPILED_MODULES.index(name)
            self.bad(lambda r, n=name: r['auxiliary_modules'].pop(n))
            self.bad(lambda r, n=name: r['auxiliary_modules'][n].update(compiled_in_this_run=False))
            self.bad(lambda r, i=index: r['commands'].pop(i))

    def test_objective_scope_cannot_claim_freshness_or_policy_succession(self):
        for field in ('selected_objective_policy_checked', 'selected_objective_challenge_binding_checked',
                      'challenge_freshness_remains_external', 'objective_policy_succession_remains_external'):
            self.bad(lambda r, f=field: r.update({f: False}))
            self.bad(lambda r, f=field: r.update({f: 1}))
            self.bad(lambda r, f=field: r.pop(f))

    def test_auxiliary_is_required_once_and_kept_separate(self):
        name = checker.AUXILIARIES[0]
        self.bad(lambda r: r.pop('auxiliary_modules'))
        self.bad(lambda r: r['auxiliary_modules'].clear())
        self.bad(lambda r: r['auxiliary_modules'].__setitem__('OldArithmetic', copy.deepcopy(r['auxiliary_modules'][name])))
        self.bad(lambda r: r['dependency_modules'].__setitem__(name, r['auxiliary_modules'].pop(name)))
        self.bad(lambda r: r['auxiliary_modules'][name].update(name='OldArithmetic'))

    def test_auxiliary_requires_its_own_fresh_compilation(self):
        name = checker.AUXILIARIES[0]
        index = checker.COMPILE_START + checker.COMPILED_MODULES.index(name)
        self.bad(lambda r: r['auxiliary_modules'][name].update(compiled_in_this_run=False))
        self.bad(lambda r: r['auxiliary_modules'][name].update(prior_success_report_used_as_proof=True))
        self.bad(lambda r: r['auxiliary_modules'][name].update(source_sha256='0' * 64))
        self.bad(lambda r: r['commands'][index].update(source_sha256='0' * 64))
        self.bad(lambda r: r['commands'][index].update(returncode=1))
        self.bad(lambda r: r['commands'].pop(index))

    def test_auxiliary_artifact_and_resolution_bindings_are_exact(self):
        name = checker.AUXILIARIES[0]
        index = checker.COMPILE_START + checker.COMPILED_MODULES.index(name)
        self.bad(lambda r: r['auxiliary_modules'][name].update(artifacts_sha256={}))
        self.bad(lambda r: r['commands'][index]['output_artifacts_sha256'].__setitem__(name + '.olean', '0' * 64))
        self.bad(lambda r: r['auxiliary_modules'][name]['artifacts_sha256'].__setitem__('../old.olean', '0' * 64))
        self.bad(lambda r: r['auxiliary_modules'][name].update(resolved_module_path='/fixture/stale/' + name + '.olean'))

    def test_final_resolutions_require_both_complete_fresh_imports(self):
        for index in (checker.RESOLUTION_START + i for i in (6, 8, 9)):
            original = self.result['commands'][index]['stdout']
            lines = original.splitlines(keepends=True)
            for changed in (''.join(lines[:3]), ''.join((*lines[:2], lines[3])),
                            ''.join((*lines[:2], lines[2], lines[2])),
                            ''.join((*lines[:2], lines[3], lines[2])), original + lines[2]):
                self.bad(lambda r, i=index, text=changed: self.output(r, i, text))

    def test_final_resolution_cannot_shadow_its_other_import(self):
        for offset, other in ((6, 'Phase17XSha256Blocks'),
                              (8, 'Phase17YSha256Blocks'), (9, 'Phase17XDependency')):
            index = checker.RESOLUTION_START + offset
            original = self.result['commands'][index]['stdout']
            changed = original.replace('/fixture/fresh/' + other + '.olean', '/fixture/stale/' + other + '.olean')
            self.bad(lambda r, i=index, text=changed: self.output(r, i, text))

    def test_preparation_and_partial_proof_cannot_pass(self):
        self.bad(lambda r: r.update(status='not_requested'))
        self.bad(lambda r: r.update(objective_policy_from_context_checked=False))
        self.bad(lambda r: r.update(objective_challenge_binding_checked=False))

    def test_packet_and_source_substitution_rejected(self):
        self.bad(lambda r: r.update(packet_sha256='0'*64))
        self.bad(lambda r: r['source_sha256'].__setitem__(self.labels[0], '0'*64))
        self.bad(lambda r: r['commands'][checker.CASE_START].update(source_sha256='0'*64))

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

    def test_fresh_compile_required_for_all_eight_dependencies(self):
        for name in checker.DEPENDENCIES:
            with self.subTest(name=name):
                self.bad(lambda r, n=name: r['dependency_modules'][n].update(compiled_in_this_run=False))
                self.bad(lambda r, n=name: r['dependency_modules'][n].update(prior_success_report_used_as_proof=True))

    def test_dependency_compile_order_and_count_are_fixed(self):
        start = checker.COMPILE_START
        self.bad(lambda r: r['commands'].__setitem__(slice(start,start+2), list(reversed(r['commands'][start:start+2]))))
        self.bad(lambda r: r['commands'].pop(start))
        self.bad(lambda r: r['commands'].insert(start, copy.deepcopy(r['commands'][start])))

    def test_compiled_artifacts_bound_to_each_own_source(self):
        for name in checker.DEPENDENCIES:
            index = checker.COMPILED_MODULES.index(name)
            with self.subTest(name=name):
                self.bad(lambda r, n=name: r['dependency_modules'][n].update(source_sha256='0'*64))
                self.bad(lambda r, n=name: r['dependency_modules'][n].update(artifacts_sha256={}))
                self.bad(lambda r, i=index, n=name: r['commands'][checker.COMPILE_START+i]['output_artifacts_sha256'].__setitem__(n+'.olean', '0'*64))
                self.bad(lambda r, n=name: r['dependency_modules'][n]['artifacts_sha256'].__setitem__('../stale.olean', '0'*64))

    def test_failed_or_noisy_dependency_compile_rejected(self):
        for index in range(checker.COMPILE_START, checker.RESOLUTION_START):
            self.bad(lambda r, i=index: r['commands'][i].update(returncode=1))
            self.bad(lambda r, i=index: self.output(r, i, 'warning: old cached proof\n'))

    def test_each_resolution_bound_to_its_client(self):
        for index in range(checker.RESOLUTION_START, checker.CASE_START):
            self.bad(lambda r, i=index: r['commands'][i].update(source_sha256='0'*64))
            self.bad(lambda r, i=index: r['commands'][i].update(label='dependency_resolution'))
            self.bad(lambda r, i=index: r['commands'][i]['argv'].remove('--deps'))

    def test_shadowed_dependency_import_rejected(self):
        for name in checker.DEPENDENCIES:
            index = checker.COMPILED_MODULES.index(name)
            def shadow(result, i=index, n=name):
                old = result['dependency_modules'][n]['resolved_module_path']
                stale = '/fixture/stale/' + n + '.olean'
                result['dependency_modules'][n]['resolved_module_path'] = stale
                self.output(result, checker.RESOLUTION_START+i, result['commands'][checker.RESOLUTION_START+i]['stdout'].replace(old, stale))
            self.bad(shadow)

    def test_extra_duplicate_relative_or_conflicting_init_import_rejected(self):
        for name in checker.DEPENDENCIES:
            index = checker.COMPILED_MODULES.index(name)
            self.bad(lambda r, i=index: self.output(r, checker.RESOLUTION_START+i, r['commands'][checker.RESOLUTION_START+i]['stdout']+'/extra/Other.olean\n'))
            self.bad(lambda r, i=index, n=name: self.output(r, checker.RESOLUTION_START+i, r['commands'][checker.RESOLUTION_START+i]['stdout']+n+'.olean\n'))
            self.bad(lambda r, i=index: self.output(r, checker.RESOLUTION_START+i, r['commands'][checker.RESOLUTION_START+i]['stdout'].replace('/fixture/tools/Init.olean', '/other/Init.olean', 1)))

    def test_windows_path_case_and_slashes_are_equivalent(self):
        result = copy.deepcopy(self.result)
        result['executable_sha256'] = {'C:\\Tools\\bin\\lean.exe':'1'*64,'C:\\Tools\\bin\\lake.exe':'2'*64,
                                      'C:\\Tools\\bin\\git.exe':'3'*64}
        result['compiler_environment'] = self.environment_fixture(windows=True)
        result['commands'][0]['argv'] = ['c:/tools/bin/lean.exe','--version']
        capture = result['commands'][checker.ENVIRONMENT_INDEX]
        capture['argv'][0] = 'c:/tools/bin/lake.exe'
        capture['argv'][4] = 'c:\\python\\python.exe'
        for command in result['commands'][checker.COMPILE_START:]:
            command['argv'][:4] = ['c:/tools/bin/lean.exe', *checker.DIRECT_FLAGS,
                                  '--root=C:\\Users\\Fixture\\Fresh']
            command['argv'][-1] = command['argv'][-1].replace('/fixture/fresh/','C:/Users/Fixture/Fresh/')
        for index, name in enumerate(checker.COMPILED_MODULES):
            compiled = 'C:\\Users\\Fixture\\Fresh\\' + name + '.olean'
            resolved = 'c:/users/fixture/fresh/' + name.lower() + '.olean'
            result['commands'][checker.COMPILE_START+index]['argv'][-2] = compiled
            modules = result['dependency_modules'] if name in checker.DEPENDENCIES else result['auxiliary_modules']
            modules[name]['resolved_module_path'] = resolved
            imports = [path.lower() for path in
                       checker._resolution_targets(name, 'c:/users/fixture/fresh').values()]
            self.output(result, checker.RESOLUTION_START+index,
                        'C:\\Tools\\Init.olean\nc:/tools/init.olean\n' + '\n'.join(imports) + '\n')
        self.refresh_environment(result)
        checker.validate_result(result, self.sources, self.packet)

    def test_compile_resolution_and_case_inputs_match_declared_source(self):
        for index in range(checker.COMPILE_START, checker.CASE_START+2):
            self.bad(lambda r, i=index: r['commands'][i]['argv'].__setitem__(-1,'/fixture/fresh/Unrelated.lean'))

    def test_case_invocations_require_exact_recorded_tools(self):
        self.bad(lambda r: r['commands'][checker.CASE_START].update(argv=['/other/tool','/old/Other.lean']))
        self.bad(lambda r: r['commands'][checker.CASE_START+1].pop('argv'))
        self.bad(lambda r: r['commands'][checker.CASE_START]['argv'].__setitem__(0,'/other/lean'))
        self.bad(lambda r: r['commands'][checker.CASE_START+1]['argv'].__setitem__(0,'/other/lean'))

    def test_unrelated_executable_inventory_cannot_back_commands(self):
        self.bad(lambda r: r.update(executable_sha256={'/one':'1'*64,'/two':'2'*64,'/three':'3'*64}))
        self.bad(lambda r: r['executable_sha256'].__setitem__('/other/lean',r['executable_sha256'].pop('/fixture/tools/bin/lean')))

    def test_one_root_for_all_compile_and_case_commands(self):
        for index in range(checker.COMPILE_START, checker.CASE_START+2):
            self.bad(lambda r, i=index: r['commands'][i]['argv'].__setitem__(3,'--root=/fixture/stale'))

    def test_compile_output_module_name_cannot_change(self):
        for index in range(checker.COMPILE_START, checker.RESOLUTION_START):
            self.bad(lambda r, i=index: r['commands'][i]['argv'].__setitem__(-2,'/fixture/fresh/Other.olean'))

    def test_different_windows_drive_is_not_same_module(self):
        def different(result):
            name = checker.DEPENDENCIES[1]
            result['commands'][checker.COMPILE_START+1]['argv'][-2] = 'C:/run/'+name+'.olean'
            result['dependency_modules'][name]['resolved_module_path'] = 'D:/run/'+name+'.olean'
            self.output(result, checker.RESOLUTION_START+1, 'C:/tools/Init.olean\nC:/tools/Init.olean\nD:/run/'+name+'.olean\n')
        self.bad(different)

    def test_posix_case_difference_rejected(self):
        def different(result):
            name = checker.DEPENDENCIES[0]
            old = result['dependency_modules'][name]['resolved_module_path']
            new = old.replace('/fresh/', '/FRESH/')
            result['dependency_modules'][name]['resolved_module_path'] = new
            self.output(result, checker.RESOLUTION_START, result['commands'][checker.RESOLUTION_START]['stdout'].replace(old,new))
        self.bad(different)

    def test_missing_negative_command_or_claim_rejected(self):
        self.bad(lambda r: r['commands'].pop())
        self.bad(lambda r: r['negative_controls_rejected'].pop())

    def test_positive_failure_rejected(self):
        self.bad(lambda r: r['commands'][checker.CASE_START].update(returncode=1))

    def test_timeout_kill_or_success_is_not_a_negative(self):
        for code in (0,-9,-999,137,True):
            self.bad(lambda r, c=code: r['commands'][checker.CASE_START+1].update(returncode=c))

    def test_boolean_exitcode_and_numeric_proof_flags_rejected(self):
        self.bad(lambda r: r['commands'][checker.CASE_START].update(returncode=False))
        self.bad(lambda r: r.update(objective_challenge_binding_checked=1))
        self.bad(lambda r: r.update(new_named_audits=True))

    def test_changed_stream_with_stale_hash_rejected(self):
        self.bad(lambda r: r['commands'][checker.CASE_START].update(stdout='changed'))
        self.bad(lambda r: r['commands'][checker.CASE_START+1].update(stderr='error'))

    def test_unrelated_negative_errors_not_counted(self):
        for out in ("error: unknown identifier 'old'\n",
                    'error: Tactic `decide` proved that the proposition\nerror: type mismatch\nFalse\nis false\n'):
            self.bad(lambda r, text=out: self.output(r, checker.CASE_START+1, text))

    def test_stuck_decider_is_not_semantic_rejection(self):
        # Inherited regression from T's first actual application attempt. A reduction
        # problem must never be credited as proof that the control is false.
        stuck = (
            '/fixture/fresh/ChangedJsonByte.lean:294:73: error: Tactic `decide` failed for proposition\n'
            '  decode controlImage = some beforePackage.memory\n'
            'because its `Decidable` instance\n'
            '  (decode controlImage).instDecidableEq (some beforePackage.memory)\n'
            'did not reduce to `isTrue` or `isFalse`.\n')
        false_error = 'error: Tactic `decide` proved that the proposition\nFalse\nis false\n'
        for text in (stuck, stuck + false_error, false_error + stuck):
            with self.subTest(output=text):
                self.bad(lambda r, out=text: self.output(r, checker.CASE_START+1, out))

    def test_failed_false_decision_witness_cannot_count_as_rejection(self):
        # Actual unmutated-input countercheck: Lean can recover from the first
        # error and emit the later expected diagnostic. Both must be inspected.
        witness_error = (
            '/fixture/fresh/ChangedJsonByte.lean:294:21: error: Tactic `rfl` failed: The left-hand side\n'
            '  decide (decode controlImage = some beforePackage.memory)\n'
            'is not definitionally equal to the right-hand side\n'
            '  false\n\n'
            '⊢ decide (decode controlImage = some beforePackage.memory) = false\n')
        false_error = (
            '/fixture/fresh/ChangedJsonByte.lean:300:2: error: Tactic `decide` proved that the proposition\n'
            '  False\nis false\n')
        for text in (witness_error, witness_error + false_error, false_error + witness_error):
            with self.subTest(output=text):
                self.bad(lambda r, out=text: self.output(r, checker.CASE_START+1, out))

    def test_negative_audit_or_success_output_rejected(self):
        self.bad(lambda r: self.output(r, checker.CASE_START+1, r['commands'][checker.CASE_START+1]['stdout']+self.audits))
        self.bad(lambda r: self.output(r, checker.CASE_START+1, r['commands'][checker.CASE_START+1]['stdout']+'accepted\n'))

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
        self.bad(lambda r: r.update(byte_capture_remains_external=False))
        self.bad(lambda r: r.update(python_execution_remains_external=False))
        self.bad(lambda r: r.update(full_transformer_equivalence=True))
        self.bad(lambda r: r.update(digest_authenticity_remains_external=False))
        self.bad(lambda r: r.update(general_planner_equivalence=True))
        self.bad(lambda r: r.update(general_json_parser_equivalence=True))
        self.bad(lambda r: r.update(general_sha256_equivalence=True))
        self.bad(lambda r: r.update(selected_objective_policy_checked=False))
        self.bad(lambda r: r.update(selected_sha256_computation_checked=False))
        self.bad(lambda r: r.update(general_grammar_parameter_derivation_remains_external=False))
        self.bad(lambda r: r.update(sha256_collision_resistance_remains_external=False))
        self.bad(lambda r: r.update(objective_context_interpretation_remains_external=True))
        self.bad(lambda r: r.update(failure={'reason':'unresolved'}))


class GateBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('y_gate_test', ROOT/'scripts/run_phase17_objective_context_gate.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_output_parent_alias_cannot_enter_source(self):
        name = 'y-forbidden-output'
        path = ROOT.parent/'nonexistent-y-parent'/'..'/ROOT.name/name
        with self.assertRaises(ValueError):
            self.module.main(['--output',str(path),'--test-fixture'])
        self.assertFalse((ROOT/name).exists())

    def test_inventory_binds_original_producer_definitions_and_new_checker(self):
        paths = self.module.source_paths()
        for name in ('python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase14/tasks.py',
                     'python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase12/phase12e_tasks.py',
                     'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/proposal_provenance.py',
                     'python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase16/ranking.py',
                     'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/objective_context_check.py',
                     'lean/phase17_bridge/ObjectiveContext.lean'):
            self.assertIn(name,paths)
        self.assertNotIn('SHA256SUMS.txt',paths)
        self.assertNotIn('docs/executable_core_v5/PHASE_17_LOCAL_VALIDATION.json',paths)
