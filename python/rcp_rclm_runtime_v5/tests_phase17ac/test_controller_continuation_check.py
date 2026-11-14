"""Adversarial AC evidence reconstruction; no real Lean execution.

The small executable used by integration tests emits deliberately synthetic
parser fixtures. It tests command ownership, saved bytes and checker plumbing,
and never supplies a project proof or an application-acceptance result.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
import ntpath
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import compilation_checkpoint as checkpoint
from rcp_rclm_runtime_v5.phase17 import controller_continuation_check as check
from rcp_rclm_runtime_v5.phase17 import controller_continuation_lean as proof


STAMP = '2026-11-13T00:00:00+00:00'


def stream_hashes(command):
    for name in ('stdout', 'stderr'):
        command[name + '_sha256'] = check.sha(command[name].encode())


def command_record(argv, cwd, environment, stdout='', stderr='', returncode=0):
    result = {'argv': list(argv), 'cwd': cwd, 'environment_sha256': check.sha(check._environment_bytes(environment)),
              'returncode': returncode, 'stdout': stdout, 'stderr': stderr,
              'started_at_utc': STAMP, 'elapsed_ns': 1000}
    stream_hashes(result)
    return result


def refresh_probe(record):
    command = record['commands'][1]
    command['stdout'] = check._environment_bytes({
        'environment': record['observed_environment'], 'executable': record['binaries']['python']['path'],
        'platform': record['platform'], 'cwd': record['cwd']}).decode('ascii')
    stream_hashes(command)


def environment_fixture(root='/controller-fixture', platform='posix'):
    root = str(root).replace('\\', '/')
    separator = ';' if platform == 'nt' else ':'
    suffix = '.exe' if platform == 'nt' else ''
    tool = root + '/tool'; workspace = root + '/foundation'
    cwd = workspace + '/' + check.pinned.ROOT_PROJECT
    seed = root + '/capture/module-search-seed'
    binaries = {label: {'path': path, 'sha256': check.sha(label.encode())} for label, path in (
        ('lean', tool + '/bin/lean' + suffix), ('lake', tool + '/bin/lake' + suffix),
        ('git', root + '/git/bin/git' + suffix), ('python', root + '/python/python' + suffix))}
    package = cwd + '/.lake/packages/mathlib'
    dependencies = {'mathlib': [{'path': package, 'head': '1' * 40}]}
    base = {'PATH': separator.join((tool + '/bin', root + '/git/bin')),
            'LEAN_PATH': seed, 'ELAN_TOOLCHAIN': check.pinned.TOOLCHAIN,
            'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': 'nul' if platform == 'nt' else '/dev/null',
            'LAKE_NO_CACHE': 'true', 'LAKE_ARTIFACT_CACHE': 'false',
            'NoDefaultCurrentDirectoryInExePath': '1'}
    actual = dict(base, LEAN=binaries['lean']['path'], LAKE=binaries['lake']['path'],
                  LEAN_SYSROOT=tool, LEAN_PATH=separator.join((cwd + '/.lake/build/lib/lean',
                      package + '/.lake/build/lib/lean', seed, tool + '/lib/lean')),
                  LEAN_SRC_PATH=separator.join((cwd, package, tool + '/src/lean/lake')),
                  LD_LIBRARY_PATH=separator.join((cwd + '/.lake/build/lib', tool + '/lib/lean')),
                  PATH=separator.join((cwd + '/.lake/build/bin', package + '/.lake/build/bin', base['PATH'])))
    template = dict(actual, LEAN_PATH=actual['LEAN_PATH'].replace(seed, '{workspace}'))
    record = {'schema': check.ENV_SCHEMA, 'status': 'passed', 'recorded_at_utc': STAMP,
              'platform': platform, 'module_search_seed': seed, 'lean_workspace': workspace,
              'cwd': cwd, 'toolchain_root': tool,
              'root_sources': {'lean/rcp_rclm_formal_core_v4/lakefile.lean': {
                  'canonical_sha256': check.sha(b'root'), 'checkout_sha256': check.sha(b'root')}},
              'dependencies': dependencies, 'binaries': binaries,
              'compiled_foundation': {'lean/rcp_rclm_formal_core_v4/.lake/build/lib/lean/Root.olean':
                                      check.sha(b'foundation object')},
              'mathlib_root': {'path': package + '/.lake/build/lib/lean/Mathlib.olean',
                               'sha256': check.sha(b'mathlib')},
              'init_module': {'path': tool + '/lib/lean/Init.olean', 'sha256': check.sha(b'init')},
              'probe_source_sha256': check.sha(check.PROBE.encode()), 'base_environment': base,
              'observed_environment': actual, 'environment_template': template,
              'commands': [], 'trusted_import_cache_assumption': True, 'physical_execution_attested': False}
    if platform == 'nt':
        for key in ('module_search_seed', 'lean_workspace', 'cwd', 'toolchain_root'):
            record[key] = ntpath.normpath(record[key])
        for item in (*binaries.values(), record['mathlib_root'], record['init_module']):
            item['path'] = ntpath.normpath(item['path'])
        for rows in dependencies.values():
            for item in rows:
                item['path'] = ntpath.normpath(item['path'])
        for environment in (base, actual, template):
            for key in ('PATH', 'LEAN_PATH', 'LEAN_SRC_PATH', 'LD_LIBRARY_PATH', 'LEAN', 'LAKE', 'LEAN_SYSROOT'):
                if key in environment:
                    environment[key] = separator.join(ntpath.normpath(value)
                                                      for value in environment[key].split(separator))
    record['commands'] = [command_record([binaries['lean']['path'], '--version'], cwd, base,
                             'Lean (version 4.31.0, x86_64-unknown-linux-gnu, commit fixture, Release)\n'),
                         command_record([binaries['lake']['path'], '--keep-toolchain', '--no-cache', 'env',
                             binaries['python']['path'], '-I', '-S', '-B', '-c', check.PROBE], cwd, base)]
    refresh_probe(record)
    return record


class CapturedEnvironmentPolicy(unittest.TestCase):
    def test_posix_capture_reconstructs_exact_template(self):
        check._environment_policy(environment_fixture())

    def test_windows_capture_reconstructs_without_host_path_rules(self):
        check._environment_policy(environment_fixture('C:/controller-fixture', 'nt'))

    def test_retained_windows_lake_dll_paths_are_allowed_only_within_pinned_closure(self):
        # Use the actual committed Windows AB environment as path-policy input,
        # while explicitly constructing a checker fixture around it. This does
        # not relabel the historical AB command as an AC execution.
        root = Path(__file__).resolve().parents[3]
        raw = (root / 'artifacts/development/phase17ab/op-c4a150b8f8e7/gate/execution.json').read_bytes()
        self.assertEqual(check.sha(raw), '678ac8ba242bd7f293492742758114c1f20e847151b9cb3667b80bc9050164fb')
        historical = json.loads(raw)['resource_digests_gate']['compiler_environment']
        record = environment_fixture('C:/controller-fixture', 'nt')
        record['cwd'] = historical['cwd']
        record['lean_workspace'] = historical['cwd'].rsplit('\\lean\\', 1)[0]
        record['toolchain_root'] = historical['effective_environment']['LEAN_SYSROOT']
        old_seed = historical['fresh_module_directory']
        record['module_search_seed'] = ntpath.join(old_seed, 'module-search-seed')
        record['base_environment'] = deepcopy(historical['base_environment'])
        record['base_environment']['LEAN_PATH'] = record['module_search_seed']
        record['observed_environment'] = deepcopy(historical['effective_environment'])
        record['observed_environment']['LEAN_PATH'] = historical['effective_environment']['LEAN_PATH'].replace(
            old_seed, record['module_search_seed'])
        record['environment_template'] = dict(record['observed_environment'])
        record['environment_template']['LEAN_PATH'] = record['observed_environment']['LEAN_PATH'].replace(
            record['module_search_seed'], '{workspace}')
        record['binaries']['lean']['path'] = record['observed_environment']['LEAN']
        record['binaries']['lake']['path'] = record['observed_environment']['LAKE']
        record['binaries']['python']['path'] = historical['probe_executable']
        record['binaries']['git']['path'] = ntpath.join(record['base_environment']['PATH'].split(';')[1], 'git.exe')
        lock = json.loads((root / check.pinned.ROOT_PROJECT / 'lake-manifest.json').read_bytes())
        record['dependencies'] = {package['name']: [{'path': ntpath.join(record['cwd'], '.lake', 'packages', package['name']),
                                                    'head': package['rev']}]
                                  for package in lock['packages'] if package['type'] == 'git'}
        record['mathlib_root']['path'] = ntpath.join(record['dependencies']['mathlib'][0]['path'],
                                                    '.lake', 'build', 'lib', 'lean', 'Mathlib.olean')
        record['init_module']['path'] = ntpath.join(record['toolchain_root'], 'lib', 'lean', 'Init.olean')
        record['commands'] = [command_record([record['binaries']['lean']['path'], '--version'], record['cwd'],
                                 record['base_environment'], 'Lean (version 4.31.0)\n'),
                             command_record([record['binaries']['lake']['path'], '--keep-toolchain', '--no-cache',
                                 'env', record['binaries']['python']['path'], '-I', '-S', '-B', '-c', check.PROBE],
                                 record['cwd'], record['base_environment'])]
        refresh_probe(record); check._environment_policy(record)
        self.assertTrue(any(path.endswith('\\.lake\\build\\lib') for path in record['observed_environment']['PATH'].split(';')))
        record['observed_environment']['PATH'] += ';C:\\unreviewed\\.lake\\build\\lib'
        record['environment_template']['PATH'] += ';C:\\unreviewed\\.lake\\build\\lib'; refresh_probe(record)
        with self.assertRaisesRegex(ValueError, 'unreviewed effective search'):
            check._environment_policy(record)
        posix = environment_fixture()
        extra = ':' + posix['cwd'] + '/.lake/build/lib'
        posix['observed_environment']['PATH'] += extra; posix['environment_template']['PATH'] += extra
        refresh_probe(posix)
        with self.assertRaisesRegex(ValueError, 'unreviewed effective search'):
            check._environment_policy(posix)

    def test_saved_observation_cannot_replace_actual_child_output(self):
        record = environment_fixture()
        record['observed_environment']['LEAN_PATH'] += ':/unreviewed'
        with self.assertRaises(ValueError):
            check._environment_policy(record)

    def test_template_cannot_insert_unrecorded_path_or_variable(self):
        for name, value in (('LEAN_PATH', '{workspace}:/injected'), ('PYTHONPATH', '/injected')):
            record = environment_fixture(); record['environment_template'][name] = value
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'template'):
                check._environment_policy(record)

    def test_rehashed_child_cannot_select_a_different_compiler(self):
        record = environment_fixture(); record['observed_environment']['LEAN'] = '/other/bin/lean'
        record['environment_template']['LEAN'] = '/other/bin/lean'; refresh_probe(record)
        with self.assertRaisesRegex(ValueError, 'compiler/toolchain'):
            check._environment_policy(record)

    def test_rehashed_child_cannot_add_an_unreviewed_import_root(self):
        record = environment_fixture(); record['observed_environment']['LEAN_PATH'] += ':/other'
        record['environment_template']['LEAN_PATH'] += ':/other'; refresh_probe(record)
        with self.assertRaisesRegex(ValueError, 'import search'):
            check._environment_policy(record)

    def test_module_seed_must_appear_exactly_once(self):
        record = environment_fixture()
        record['observed_environment']['LEAN_PATH'] += ':' + record['module_search_seed']
        record['environment_template']['LEAN_PATH'] += ':{workspace}'; refresh_probe(record)
        with self.assertRaisesRegex(ValueError, 'import search'):
            check._environment_policy(record)

    def test_known_optional_dependency_search_directory_need_not_be_built(self):
        record = environment_fixture(); cli = record['cwd'] + '/.lake/packages/Cli'
        record['dependencies']['Cli'] = [{'path': cli, 'head': '2' * 40}]
        record['observed_environment']['LEAN_PATH'] += ':' + cli + '/.lake/build/lib/lean'
        record['environment_template']['LEAN_PATH'] += ':' + cli + '/.lake/build/lib/lean'
        refresh_probe(record); check._environment_policy(record)

    def test_empty_and_relative_unreviewed_search_entries_rejected(self):
        for key, suffix in (('PATH', ':'), ('LEAN_PATH', ':.'), ('LEAN_SRC_PATH', ':/outside')):
            record = environment_fixture()
            record['observed_environment'][key] += suffix
            record['environment_template'][key] += suffix; refresh_probe(record)
            with self.subTest(key=key), self.assertRaises(ValueError):
                check._environment_policy(record)

    def test_unreviewed_child_variables_rejected_even_when_rehashed(self):
        record = environment_fixture(); record['observed_environment']['PYTHONPATH'] = '/injected'
        record['environment_template']['PYTHONPATH'] = '/injected'; refresh_probe(record)
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            check._environment_policy(record)

    def test_retained_base_policy_cannot_be_changed_by_lake(self):
        record = environment_fixture(); record['observed_environment']['GIT_TERMINAL_PROMPT'] = '1'
        record['environment_template']['GIT_TERMINAL_PROMPT'] = '1'; refresh_probe(record)
        with self.assertRaisesRegex(ValueError, 'retained base'):
            check._environment_policy(record)

    def test_setup_probe_requires_all_isolation_flags(self):
        record = environment_fixture(); record['commands'][1]['argv'].remove('-I')
        with self.assertRaisesRegex(ValueError, 'isolated Lake'):
            check._environment_policy(record)

    def test_setup_result_requires_real_exit_zero_not_boolean(self):
        record = environment_fixture(); record['commands'][1]['returncode'] = False
        with self.assertRaises(ValueError):
            check._environment_policy(record)

    def test_setup_streams_and_elapsed_bound_checked(self):
        for key, value in (('stdout_sha256', '0' * 64), ('elapsed_ns', -1),
                           ('elapsed_ns', True), ('elapsed_ns', 121_000_000_000)):
            record = environment_fixture(); record['commands'][1][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                check._environment_policy(record)

    def test_setup_version_is_exact_after_rehash(self):
        record = environment_fixture(); record['commands'][0]['stdout'] = 'Lean (version 4.32.0)\n'
        stream_hashes(record['commands'][0])
        with self.assertRaisesRegex(ValueError, 'pinned version'):
            check._environment_policy(record)

    def test_duplicate_probe_keys_and_noncanonical_json_rejected(self):
        for raw in ('{"environment":{},"environment":{}}\n', '{ "environment": {} }\n'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                check._child_report(raw)
        record = environment_fixture()
        record['commands'][1]['stdout'] = json.dumps(json.loads(record['commands'][1]['stdout']), indent=2) + '\n'
        stream_hashes(record['commands'][1])
        with self.assertRaisesRegex(ValueError, 'canonical'):
            check._environment_policy(record)

    def test_init_cannot_bind_another_file_with_same_basename(self):
        record = environment_fixture(); record['init_module']['path'] = '/other/Init.olean'
        with self.assertRaisesRegex(ValueError, 'Init module'):
            check._environment_policy(record)

    def test_scope_and_unknown_record_fields_rejected(self):
        for key, value in (('physical_execution_attested', True), ('unknown', False)):
            record = environment_fixture(); record[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                check._environment_policy(record)

    def test_capture_timestamp_and_platform_cannot_be_ambiguous(self):
        for key, value in (('recorded_at_utc', '2026-11-13T00:00:00'), ('platform', 'nt')):
            record = environment_fixture(); record[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                check._environment_policy(record)


class DiskFixture:
    """Real tiny files, with pinned root/dependency facts explicitly mocked."""
    def __init__(self, directory):
        self.root = Path(directory); self.source = self.root / 'source'; self.source.mkdir()
        self.record = environment_fixture(self.root, os.name)
        for label, item in self.record['binaries'].items():
            self.put(item['path'], label.encode())
        self.put(self.record['mathlib_root']['path'], b'mathlib')
        self.put(self.record['init_module']['path'], b'init')
        for name in self.record['root_sources']:
            self.put(Path(self.record['lean_workspace']) / name, b'root')
        for name in self.record['compiled_foundation']:
            self.put(Path(self.record['lean_workspace']) / name, b'foundation object')
        self.put(self.source / 'fixture.py', b'# controlled checker fixture\n')
        Path(self.record['module_search_seed']).mkdir(parents=True)
        self.hashes = {'fixture.py': check.sha((self.source / 'fixture.py').read_bytes())}
        self.proofs = {label: b'-- source parser fixture, not a formal proof\n'
                       for label in (*proof.MODULES, proof.POSITIVE)}
        self.proofs.update({label: b'-- intended parser fixture\nexample : wrongClaim = true := by\n'
                           b'  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
                           for label in proof.NEGATIVES})

    @staticmethod
    def put(path, raw):
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)

    def verify(self, record=None):
        with patch.object(check.pinned, 'root_source_fingerprint', return_value=self.record['root_sources']), \
             patch.object(check.pinned, '_dependency_state', return_value=self.record['dependencies']):
            check.verify_environment(record or self.record, self.source)

    def configuration(self, **overrides):
        args = {'source_root': self.source, 'environment': self.record, 'source_commit': '3' * 40,
                'source_tree': '4' * 40, 'source_hashes': self.hashes, 'packet_sha256': '5' * 64,
                'proof_sources': self.proofs}
        args.update(overrides)
        with patch.object(check.pinned, 'root_source_fingerprint', return_value=self.record['root_sources']), \
             patch.object(check.pinned, '_dependency_state', return_value=self.record['dependencies']), \
             patch.object(check, 'source_snapshot', return_value=self.hashes):
            return check.configuration(**args)

    def install_parser_script(self):
        # A Python subprocess speaks only the unit fixture protocol. No Lean is
        # invoked, and these bytes are not stored as project validation evidence.
        script = '''import os,sys
from pathlib import Path
# Deliberately synthetic parser bytes, independent of host text translation.
sys.stdout.reconfigure(encoding="utf-8", newline="\\n")
sys.stderr.reconfigure(encoding="utf-8", newline="\\n")
args=sys.argv[1:]
source=Path(args[-1])
label=source.stem
if '--deps' in args:
    module=label.removeprefix('Probe')
    init=str(Path(os.environ['LEAN_SYSROOT'])/'lib/lean/Init.olean')
    print(init);print(str(source.parent/(module+'.olean')));print(init)
elif '-o' in args:
    Path(args[args.index('-o')+1]).write_bytes(('fixture object:'+label).encode())
elif label == ''' + repr(proof.POSITIVE) + ''':
    for name in ''' + repr(proof.NAMES) + ''':
        print("'"+name+"' does not depend on any axioms")
else:
    line=source.read_text().splitlines().index('example : wrongClaim = true := by')+3
    print(str(source)+':'+str(line)+':2: error: Tactic `decide` proved that the proposition')
    print('  False');print('is false')
    sys.exit(1)
'''
        path = self.root / 'parser_fixture.py'
        path.write_text(script, encoding='utf-8')
        return path


class PhysicalEnvironmentAndPlan(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = DiskFixture(self.temporary.name)

    def test_exact_current_runtime_inventory_passes(self):
        self.fixture.verify()

    def test_changed_bound_tool_and_init_bytes_rejected(self):
        for kind in ('lean', 'init'):
            with self.subTest(kind=kind):
                record = self.fixture.record
                path = Path(record['binaries']['lean']['path'] if kind == 'lean' else record['init_module']['path'])
                original = path.read_bytes(); path.write_bytes(b'tampered')
                try:
                    with self.assertRaisesRegex(ValueError, 'bound runtime'):
                        self.fixture.verify()
                finally:
                    path.write_bytes(original)

    def test_saved_inventory_cannot_omit_compiled_objects(self):
        record = deepcopy(self.fixture.record); record['compiled_foundation'] = {}
        with self.assertRaisesRegex(ValueError, 'exact inventory'):
            self.fixture.verify(record)

    def test_new_unrecorded_compiled_object_rejected(self):
        root = Path(self.fixture.record['lean_workspace'])
        self.fixture.put(root / 'lean/rcp_rclm_formal_core_v3/.lake/build/lib/lean/Extra.olean', b'extra')
        with self.assertRaisesRegex(ValueError, 'exact inventory'):
            self.fixture.verify()

    def test_modified_compiled_sidecar_rejected(self):
        root = Path(self.fixture.record['lean_workspace'])
        name = 'lean/rcp_rclm_formal_core_v4/.lake/build/lib/lean/Root.olean.private'
        self.fixture.put(root / name, b'private')
        self.fixture.record['compiled_foundation'][name] = check.sha(b'private')
        self.fixture.verify(); (root / name).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'foundation'):
            self.fixture.verify()

    def test_configuration_has_fixed_stage_and_source_inventory(self):
        config = self.fixture.configuration()
        self.assertEqual([s.label for s in config['stages']],
                         [n for module in proof.MODULES for n in (module, module + '_resolution')] +
                         [proof.POSITIVE, *proof.NEGATIVES])
        self.assertEqual(len(config['stages']), 14)
        self.assertEqual(config['expected_input_sha256']['toolchain:Init'],
                         self.fixture.record['init_module']['sha256'])
        self.assertEqual(config['plan_context']['init_module'], self.fixture.record['init_module'])
        self.assertEqual(config['plan_context']['compiler_environment_sha256'],
                         check.sha(check._environment_bytes(self.fixture.record)))
        self.assertEqual(set(config['workspace_files']), {label + '.lean' for label in self.fixture.proofs} |
                         {'Probe' + label + '.lean' for label in proof.MODULES})

    def test_configuration_rejects_extra_or_missing_generated_proofs(self):
        for changed in ({**self.fixture.proofs, 'Unknown': b'extra'},
                        {k: v for k, v in self.fixture.proofs.items() if k != proof.NEGATIVES[0]}):
            with self.assertRaisesRegex(ValueError, 'proof-source inventory'):
                self.fixture.configuration(proof_sources=changed)

    def test_configuration_requires_external_hash_shapes(self):
        for key, value in (('source_commit', 'not a commit'), ('source_tree', 'f' * 39),
                           ('packet_sha256', 'f' * 63)):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'identities'):
                self.fixture.configuration(**{key: value})

    def test_configuration_rejects_source_inventory_drift(self):
        with self.assertRaisesRegex(ValueError, 'source inventory'):
            self.fixture.configuration(source_hashes={})

    def test_semantic_validator_rejects_unknown_wait_and_missing_audits(self):
        config = self.fixture.configuration()
        for timed_out, waited in ((True, True), (False, False)):
            with self.assertRaisesRegex(ValueError, 'native wait'):
                config['validate_result'](config['stages'][0],
                    {'timed_out': timed_out, 'native_wait_completed': waited, 'returncode': 0})
        with self.assertRaisesRegex(ValueError, 'audit'):
            config['validate_result'](config['stages'][4],
                {'timed_out': False, 'native_wait_completed': True, 'returncode': 0, 'stderr': '', 'stdout': ''})

    def test_import_failure_cannot_satisfy_negative_control(self):
        config = self.fixture.configuration()
        with self.assertRaisesRegex(ValueError, 'intended False'):
            config['validate_result'](config['stages'][5],
                {'timed_out': False, 'native_wait_completed': True, 'returncode': 1,
                 'stderr': '', 'stdout': 'error: unknown module prefix\n'})

    def test_restore_callback_rejects_wrong_bytes_before_command(self):
        config = self.fixture.configuration(); workspace = self.fixture.root / 'private'; workspace.mkdir()
        module = proof.MODULES[0]; (workspace / (module + '.olean')).write_bytes(b'actual')
        artifacts = {module + '.olean': {'sha256': check.sha(b'wrong'), 'bytes': 5, 'producer_invocation': 'a' * 32}}
        with patch.object(check, '_command') as run, self.assertRaisesRegex(ValueError, 'object bytes'):
            check.restore_validator(config)(workspace, artifacts)
        run.assert_not_called()

    def test_restore_callback_cannot_probe_undeclared_artifact(self):
        config = self.fixture.configuration()
        with patch.object(check, '_command') as run, self.assertRaisesRegex(ValueError, 'unexpected restored'):
            check.restore_validator(config)(self.fixture.root, {'Other.olean': {}})
        run.assert_not_called()


class ImportResolutionEvidence(unittest.TestCase):
    def record(self, workspace='/run/' + 'a' * 32 + '/workspace', init='/tool/lib/lean/Init.olean'):
        module = proof.MODULES[0]
        return {'returncode': 0, 'stderr': '', 'stdout': '\n'.join((init, workspace + '/' + module + '.olean', init)) + '\n'}

    def test_current_private_object_and_exact_init_pass(self):
        result = check._resolve(self.record(), proof.MODULES[0], '/run/' + 'a' * 32 + '/workspace',
                                '/tool/lib/lean/Init.olean')
        self.assertEqual(result['init_module_path'], '/tool/lib/lean/Init.olean')

    def test_init_basename_alone_never_suffices(self):
        with self.assertRaisesRegex(ValueError, 'another Init'):
            check._resolve(self.record(init='/untrusted/Init.olean'), proof.MODULES[0],
                           '/run/' + 'a' * 32 + '/workspace', '/tool/lib/lean/Init.olean')

    def test_other_invocation_object_cannot_pass(self):
        with self.assertRaisesRegex(ValueError, 'restored compiled artifact'):
            check._resolve(self.record(), proof.MODULES[0], '/run/' + 'b' * 32 + '/workspace',
                           '/tool/lib/lean/Init.olean')

    def test_windows_paths_are_compared_case_insensitively(self):
        command = self.record('C:/Run/Private', 'C:/Tool/lib/lean/Init.olean')
        check._resolve(command, proof.MODULES[0], 'c:\\run\\private', 'c:\\tool\\lib\\lean\\Init.olean')

    def test_posix_literal_backslash_is_not_a_path_separator(self):
        with self.assertRaisesRegex(ValueError, 'portable import path'):
            check._identity('/tool\\lib/lean/Init.olean')

    def test_extra_import_or_diagnostic_rejected(self):
        for extra, stderr in (('/other/Module.olean\n', ''), ('', 'warning')):
            record = self.record(); record['stdout'] += extra; record['stderr'] = stderr
            with self.subTest(extra=extra, stderr=stderr), self.assertRaises(ValueError):
                check._resolve(record, proof.MODULES[0], '/run/' + 'a' * 32 + '/workspace',
                               '/tool/lib/lean/Init.olean')


class ActualRunnerCheckerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.fixture = DiskFixture(cls.temporary.name)
        script = cls.fixture.install_parser_script()
        if os.name == 'nt':
            # Native Python requires the host Windows runtime locations; these
            # are fixture launch inputs, never fabricated compiler observations.
            native = {key: value for key, value in os.environ.items()
                      if key.upper() in {'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'TEMP', 'TMP'}}
            for name in ('base_environment', 'observed_environment', 'environment_template'):
                cls.fixture.record[name].update(native)
            for command in cls.fixture.record['commands']:
                command['environment_sha256'] = check.sha(check._environment_bytes(
                    cls.fixture.record['base_environment']))
            refresh_probe(cls.fixture.record)
        cls.config = cls.fixture.configuration(); cls.results = []
        python = Path(sys.executable).resolve(strict=True)
        # Test-only trusted plan: execute the tiny fixture through the actual
        # Python binary on either host. Replace the two Lean-specific flags by
        # Python's -B/script arguments, preserving the command layout used by
        # the restore callback. The production DIRECT_FLAGS are never changed
        # outside this temporary mock, and no source of real proof evidence is
        # accepted under this explicitly marked fixture plan.
        cls.config['stages'] = tuple(replace(stage, argv=(str(python), '-B', str(script), *stage.argv[3:]))
                                    for stage in cls.config['stages'])
        cls.config['plan_context']['synthetic_parser_fixture'] = True
        for name, path in (('fixture:python', python), ('fixture:script', script)):
            cls.config['input_files'][name] = path
            cls.config['expected_input_sha256'][name] = check.sha(path.read_bytes())
        flags = patch.object(check, 'DIRECT_FLAGS', ('-B', str(script)))
        flags.start(); cls.addClassCleanup(flags.stop)
        parent = None; digest = None
        for _ in cls.config['stages']:
            result = checkpoint.run_stage(cls.fixture.root / 'runs', **cls.config,
                parent_manifest=parent, expected_parent_sha256=digest,
                restore_validator=check.restore_validator(cls.config),
                unresolved_invocations=('f' * 32,) if parent is None else ())
            cls.results.append(result); parent = result['manifest_path']; digest = result['manifest_sha256']

    def test_all_fixed_stages_verify_from_actual_saved_bytes(self):
        result = self.results[-1]
        manifest = checkpoint.verify_manifest(result['manifest_path'], result['manifest_sha256'], **self.config)
        formal = check.validate_lineage(manifest, self.config)
        self.assertEqual(formal['status'], 'passed')
        self.assertEqual(formal['compiled_modules'], list(proof.MODULES))
        self.assertEqual(set(formal['theorem_axioms']), set(proof.NAMES))
        self.assertEqual(formal['negative_controls_rejected'], list(proof.NEGATIVES))
        self.assertEqual(formal['unresolved_invocations'], ['f' * 32])
        self.assertTrue(all(value is False for value in formal['claims'].values()))

    def test_partial_prefix_cannot_claim_formal_completion(self):
        manifest = self.results[1]['manifest']
        self.assertEqual(check.validate_lineage(manifest, self.config, require_complete=False)['status'], 'incomplete')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            check.validate_lineage(manifest, self.config)

    def test_artifacts_keep_original_producer_on_continuation(self):
        final = self.results[-1]['manifest']
        self.assertEqual(final['artifacts'][proof.MODULES[0] + '.olean']['producer_invocation'],
                         self.results[0]['manifest']['invocation_id'])
        self.assertNotEqual(final['artifacts'][proof.MODULES[0] + '.olean']['producer_invocation'],
                            final['invocation_id'])

    def test_lineage_does_not_ignore_an_extra_completed_step(self):
        manifest = deepcopy(self.results[-1]['manifest']); manifest['steps'].append(manifest['steps'][-1])
        with self.assertRaisesRegex(ValueError, 'overlong'):
            check.validate_lineage(manifest, self.config, require_complete=False)

    def test_lineage_rejects_spliced_parent_or_reordered_labels(self):
        for key, value in (('previous_step_sha256', '0' * 64), ('label', 'Different')):
            manifest = deepcopy(self.results[1]['manifest']); manifest['steps'][1][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'ancestry'):
                check.validate_lineage(manifest, self.config, require_complete=False)

    def test_restore_receipt_requires_exact_import_inventory(self):
        manifest = deepcopy(self.results[1]['manifest']); manifest['steps'][1]['restore_receipt']['commands'] = []
        with self.assertRaisesRegex(ValueError, 'preflight inventory'):
            check.validate_lineage(manifest, self.config, require_complete=False)

    def test_restore_receipt_rechecks_exact_init_after_stream_rehash(self):
        manifest = deepcopy(self.results[1]['manifest']); command = manifest['steps'][1]['restore_receipt']['commands'][0]
        command['stdout'] = command['stdout'].replace(self.fixture.record['init_module']['path'], '/other/Init.olean')
        stream_hashes(command)
        with self.assertRaisesRegex(ValueError, 'another Init'):
            check.validate_lineage(manifest, self.config, require_complete=False)

    def test_restore_receipt_command_environment_and_timeout_are_bound(self):
        for key, value in (('environment_sha256', '0' * 64), ('elapsed_ns', 121_000_000_000),
                           ('source_sha256', '0' * 64), ('returncode', -999)):
            manifest = deepcopy(self.results[1]['manifest']); command = manifest['steps'][1]['restore_receipt']['commands'][0]
            command[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                check.validate_lineage(manifest, self.config, require_complete=False)

    def test_restore_duration_is_not_discarded_from_lineage_budget(self):
        manifest = deepcopy(self.results[1]['manifest']); step = manifest['steps'][1]
        step['active_elapsed_ns'] = step['command']['elapsed_ns']
        with self.assertRaisesRegex(ValueError, 'duration is missing'):
            check.validate_lineage(manifest, self.config, require_complete=False)

    def test_restored_object_and_exact_log_bytes_are_required(self):
        result = self.results[-1]
        for relative in ('workspace/' + proof.MODULES[0] + '.olean', 'logs/000.stdout.bin'):
            temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
            clone = Path(temporary.name) / result['manifest']['invocation_id']
            shutil.copytree(Path(result['manifest_path']).parent, clone)
            (clone / relative).write_bytes(b'tampered')
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                checkpoint.verify_manifest(clone / 'completion.json', result['manifest_sha256'], **self.config)

    def test_plan_context_cannot_silently_switch_capture(self):
        config = dict(self.config, plan_context=deepcopy(self.config['plan_context']))
        config['plan_context']['compiler_environment_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'plan differs'):
            check.validate_lineage(self.results[1]['manifest'], config, require_complete=False)

    def test_unknown_branch_cannot_be_relabelled_completed_resource_accounting(self):
        manifest = deepcopy(self.results[-1]['manifest']); manifest['complete_resource_accounting'] = True
        with self.assertRaisesRegex(ValueError, 'resource scope'):
            check.validate_lineage(manifest, self.config)


if __name__ == '__main__':
    unittest.main()
