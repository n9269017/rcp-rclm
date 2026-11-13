"""Pinned Lean checking of selected resource-event and work SHA-256 digests.

Q through AA, both X/Y arithmetic auxiliaries, and five bounded AB compression
modules are freshly compiled in dependency order. The final case imports the
actual AA positive certificate and all five selected arithmetic modules.
Saved command records support reproducibility; they are not physical attestation.
"""
from __future__ import annotations

import json
import ntpath
import os
from pathlib import Path
import posixpath
import re
import subprocess
import sys
import tempfile

from . import lean_frontier_gate as gate
from .sparse_refinement_check import _path_identity, _digest
from .resource_digests import PreparedResourceDigests, FALSE_CLAIMS, require, canonical, sha, read_retained

DEPENDENCIES = tuple('Phase17' + phase + 'Dependency' for phase in (*'QRSTUVWXYZ', 'AA'))
DEPENDENCY_COUNT = len(DEPENDENCIES)
NEW_AUXILIARIES = tuple('Phase17ABSha256Blocks' + str(i) for i in range(5))
AUXILIARIES = ('Phase17XSha256Blocks', 'Phase17YSha256Blocks', *NEW_AUXILIARIES)
COMPILED_MODULES = (*DEPENDENCIES[:7], AUXILIARIES[0], DEPENDENCIES[7],
                    AUXILIARIES[1], DEPENDENCIES[8], DEPENDENCIES[9], DEPENDENCIES[10],
                    *NEW_AUXILIARIES)
COMPILATION_COUNT = len(COMPILED_MODULES)
RESOLUTION_CLIENTS = {**dict(zip(DEPENDENCIES[:6], DEPENDENCIES[1:7], strict=True)),
                      'Phase17WDependency': 'Phase17XDependency',
                      'Phase17XSha256Blocks': 'Phase17YSha256Blocks',
                      'Phase17XDependency': 'Phase17YDependency',
                      'Phase17YSha256Blocks': 'Phase17YDependency',
                      'Phase17YDependency': 'Phase17ZDependency',
                      'Phase17ZDependency': 'Phase17AADependency',
                      'Phase17AADependency': 'ResourceDigests',
                      **{name: 'ResourceDigests' for name in NEW_AUXILIARIES}}
CLIENT_IMPORTS = {**{name: (previous,) for previous, name in zip(DEPENDENCIES[:6], DEPENDENCIES[1:7], strict=True)},
                  'Phase17XDependency': ('Phase17WDependency', 'Phase17XSha256Blocks'),
                  'Phase17YDependency': ('Phase17XDependency', 'Phase17YSha256Blocks'),
                  'Phase17ZDependency': ('Phase17YDependency',),
                  'Phase17AADependency': ('Phase17ZDependency',),
                  'ResourceDigests': ('Phase17AADependency', *NEW_AUXILIARIES),
                  'Phase17YSha256Blocks': ('Phase17XSha256Blocks',),
                  **{name: ('Phase17XSha256Blocks',) for name in NEW_AUXILIARIES}}
ENVIRONMENT_INDEX = 1
COMPILE_START = 2
RESOLUTION_START = COMPILE_START + COMPILATION_COUNT
CASE_START = COMPILE_START + 2 * COMPILATION_COUNT
SCHEMA = 'rcp-rclm.phase17ab.resource-digests-lean.v1'
ENVIRONMENT_SCHEMA = 'rcp-rclm.phase17ab.lean-environment.v1'
PROBE_SCHEMA = 'rcp-rclm.phase17ab.lake-child-environment.v1'
ENVIRONMENT_LABEL = 'lake_environment'
CAPTURE_SEMANTICS = ('Effective environment observed by an isolated Python child of pinned Lake; '
                     'reused unchanged for direct pinned Lean. This is not physical attestation.')
DIRECT_FLAGS = ('-j1', '-DElab.async=false')
# A source-bound, isolated standard-library probe preserves absent versus empty
# variables. Bare `lake env` text cannot make that distinction. Python startup
# can add LC_CTYPE on POSIX; the observed mapping, not an inferred pre-startup
# environment, is what is retained and passed unchanged to every direct Lean call.
ENVIRONMENT_PROBE = (
    'import json,os,sys\n'
    'payload={"schema":"' + PROBE_SCHEMA + '","environment":dict(os.environ),'
    '"executable":sys.executable,"platform":os.name,"cwd":os.getcwd()}\n'
    'sys.stdout.buffer.write((json.dumps(payload,ensure_ascii=True,sort_keys=True,'
    'separators=(",",":"))+"\\n").encode("ascii"))\n'
)
BASE_OPTIONAL = {'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'TEMP', 'TMP', 'HOME',
                 'USERPROFILE', 'LANG', 'LC_ALL'}
BASE_REQUIRED = {'PATH', 'LEAN_PATH', 'ELAN_TOOLCHAIN', 'GIT_TERMINAL_PROMPT',
                 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL', 'LAKE_NO_CACHE',
                 'LAKE_ARTIFACT_CACHE', 'NoDefaultCurrentDirectoryInExePath'}
LAKE_VARIABLES = {'ELAN', 'ELAN_HOME', 'ELAN_TOOLCHAIN', 'LAKE', 'LAKE_HOME',
                  'LAKE_CONFIG', 'LAKE_PKG_URL_MAP', 'LAKE_NO_CACHE', 'LAKE_CACHE_KEY',
                  'LAKE_CACHE_ARTIFACT_ENDPOINT', 'LAKE_CACHE_REVISION_ENDPOINT',
                  'LAKE_CACHE_SERVICE', 'LEAN', 'LEAN_SYSROOT', 'LEAN_AR', 'LEAN_CC',
                  'LAKE_CACHE_DIR', 'LAKE_ARTIFACT_CACHE', 'LAKE_RESTORE_ARTIFACTS',
                  'LEAN_PATH', 'LEAN_SRC_PATH', 'LEAN_GITHASH', 'PATH',
                  'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH'}


def _environment_bytes(value: dict) -> bytes:
    """Lossless ASCII JSON for environment strings; do not normalize Unicode."""
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii')


def _environment_report(stdout: str) -> dict:
    require(type(stdout) is str and len(stdout) <= 256 * 1024, 'bounded child environment output required')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate child environment JSON key')
            result[key] = value
        return result

    report = json.loads(stdout, object_pairs_hook=unique)
    require(type(report) is dict and set(report) == {'schema', 'environment', 'executable', 'platform', 'cwd'} and
            report['schema'] == PROBE_SCHEMA and report['platform'] in ('nt', 'posix'),
            'unexpected child environment report')
    require(_environment_bytes(report).decode('ascii') == stdout,
            'child environment report must be exact canonical ASCII JSON')
    return report


def _environment_mapping(value: dict, allowed: set[str], platform: str) -> dict:
    require(type(value) is dict and len(value) <= 64, 'bounded environment mapping required')
    normalized = {}
    allowed = {key.upper() if platform == 'nt' else key for key in allowed}
    for key, item in value.items():
        require(type(key) is str and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key) is not None and
                type(item) is str and '\x00' not in item and '\r' not in item and '\n' not in item and
                len(item) <= 64 * 1024, 'invalid environment name/value')
        name = key.upper() if platform == 'nt' else key
        require(name in allowed and name not in normalized, 'unexpected or duplicate environment variable')
        normalized[name] = item
    require(len(_environment_bytes(value)) <= 128 * 1024, 'environment byte bound exceeded')
    return normalized


def _validate_environment(record: dict, commands: list[dict], tools: dict) -> None:
    fields = {'schema', 'capture_semantics', 'platform', 'cwd', 'fresh_module_directory',
              'base_environment', 'base_environment_sha256', 'effective_environment',
              'effective_environment_sha256', 'probe_executable', 'probe_executable_sha256',
              'probe_source_sha256'}
    require(type(record) is dict and set(record) == fields and record['schema'] == ENVIRONMENT_SCHEMA and
            record['capture_semantics'] == CAPTURE_SEMANTICS and record['platform'] in ('nt', 'posix'),
            'exact compiler environment preparation required')
    platform = record['platform']
    cwd, fresh = _path_identity(record['cwd']), _path_identity(record['fresh_module_directory'])
    require(cwd.endswith('/' + gate.ROOT_PROJECT), 'compiler cwd is not the pinned root project')
    windows = platform == 'nt'
    require(bool(re.match(r'^[a-z]:/', cwd)) == windows and
            bool(re.match(r'^[a-z]:/', fresh)) == windows,
            'compiler environment platform/path disagreement')
    probe_path = _path_identity(record['probe_executable'])
    require(_digest(record['probe_executable_sha256']) and
            record['probe_source_sha256'] == sha(ENVIRONMENT_PROBE.encode('utf-8')),
            'child environment probe identity differs')
    base = _environment_mapping(record['base_environment'], BASE_OPTIONAL | BASE_REQUIRED, platform)
    effective = _environment_mapping(record['effective_environment'],
                                     BASE_OPTIONAL | BASE_REQUIRED | LAKE_VARIABLES |
                                     ({'LC_CTYPE'} if not windows else set()), platform)
    name = lambda key: key.upper() if windows else key
    required = {name(key) for key in BASE_REQUIRED}
    require(required <= set(base), 'restricted base environment is incomplete')
    fixed = {'ELAN_TOOLCHAIN': gate.TOOLCHAIN, 'GIT_TERMINAL_PROMPT': '0',
             'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': 'nul' if windows else '/dev/null',
             'LAKE_NO_CACHE': 'true', 'LAKE_ARTIFACT_CACHE': 'false',
             'NoDefaultCurrentDirectoryInExePath': '1'}
    require(all(base.get(name(key)) == value for key, value in fixed.items()),
            'restricted compiler environment policy differs')
    require(_path_identity(base['LEAN_PATH']) == fresh, 'base LEAN_PATH is not the fresh module directory')
    separator = ';' if windows else ':'
    base_paths = base['PATH'].split(separator)
    require(all(base_paths), 'empty restricted PATH component')
    base_path_ids = [_path_identity(path) for path in base_paths]
    wanted_prefix = list(dict.fromkeys((tools['lean'].rsplit('/', 1)[0], tools['git'].rsplit('/', 1)[0])))
    require(base_path_ids[:len(wanted_prefix)] == wanted_prefix, 'restricted PATH tool prefix differs')
    inherited = {name(key) for key in (BASE_OPTIONAL | BASE_REQUIRED) - LAKE_VARIABLES}
    for key in inherited:
        require((key in base) == (key in effective) and (key not in base or effective[key] == base[key]),
                'Lake child altered a retained base variable')
    require(effective.get('ELAN_TOOLCHAIN') == gate.TOOLCHAIN and effective.get('LAKE_NO_CACHE') == 'true' and
            effective.get('LAKE_ARTIFACT_CACHE') == 'false', 'Lake child cache/toolchain policy differs')
    require(_path_identity(effective.get('LEAN')) == tools['lean'] and
            _path_identity(effective.get('LAKE')) == tools['lake'] and
            _path_identity(effective.get('LEAN_SYSROOT')) == tools['lean'].rsplit('/', 2)[0],
            'Lake child points at a different pinned toolchain')
    require(type(effective.get('LEAN_PATH')) is str and bool(effective['LEAN_PATH']) and
            type(effective.get('LEAN_SRC_PATH')) is str and bool(effective['LEAN_SRC_PATH']) and
            type(effective.get('PATH')) is str and bool(effective['PATH']), 'Lake child search paths missing')
    search = effective['LEAN_PATH'].split(separator)
    require(all(search), 'empty Lean module search-path component')
    path_module = ntpath if windows else posixpath
    search_ids = [_path_identity(path_module.normpath(path_module.join(record['cwd'], part))) for part in search]
    require(search_ids.count(fresh) == 1, 'fresh module directory missing or duplicated in Lean search path')
    for field in ('base_environment', 'effective_environment'):
        require(record[field + '_sha256'] == sha(_environment_bytes(record[field])),
                'compiler environment mapping hash differs')
    prepared = commands[ENVIRONMENT_INDEX]
    require(prepared.get('label') == ENVIRONMENT_LABEL and prepared['returncode'] == 0 and prepared['stderr'] == '' and
            prepared.get('source_sha256') == record['probe_source_sha256'] and
            prepared.get('probe_executable_sha256') == record['probe_executable_sha256'],
            'Lake environment capture failed')
    expected_argv = [tools['lake'], '--keep-toolchain', '--no-cache', 'env', probe_path,
                     '-I', '-S', '-B', '-c', ENVIRONMENT_PROBE]
    argv = prepared.get('argv')
    require(type(argv) is list and len(argv) == len(expected_argv) and
            _path_identity(argv[0]) == expected_argv[0] and _path_identity(argv[4]) == expected_argv[4] and
            argv[1:4] == expected_argv[1:4] and argv[5:] == expected_argv[5:],
            'Lake environment probe invocation differs')
    report = _environment_report(prepared['stdout'])
    require(report['platform'] == platform and _path_identity(report['cwd']) == cwd and
            _path_identity(report['executable']) == probe_path and
            report['environment'] == record['effective_environment'], 'captured child environment identity differs')
    for index, command in enumerate(commands):
        expected_hash = record['base_environment_sha256' if index < COMPILE_START else 'effective_environment_sha256']
        require(_path_identity(command.get('cwd')) == cwd and command.get('environment_sha256') == expected_hash,
                'compiler command cwd/environment binding differs')


def parse_audits(text: str) -> dict:
    from .resource_digests_lean import NAMES
    require(type(text) is str, 'resource digests audit output must be text')
    cursor, result = 0, {}
    for name in NAMES:
        match = re.compile(r"'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*", re.S).match(text, cursor)
        require(match is not None, 'exact resource digests audit sequence required')
        result[name] = gate._axioms(match[0], name)
        cursor = match.end()
    require(cursor == len(text), 'unexpected resource digests audit output')
    return result


def _negative_site(source: bytes) -> tuple[int, int]:
    """Locate the only intended failing tactic in the exact generated source."""
    require(type(source) is bytes and source, 'exact negative-control source required')
    text = source.decode('utf-8')
    require(len(re.findall(r'(?m)^theorem rejected_control : ', text)) == 1 and
            len(re.findall(r'(?m)^theorem control_false : decide \(', text)) == 1,
            'unique negative decision witness and final control required')
    final = re.search(
        r'(?m)^theorem rejected_control : [\s\S]+? := by\n'
        r'  have h : ¬ \([\s\S]+?\) := of_decide_eq_false control_false\n'
        r'  rw \[eq_false h\]\n(?P<tactic>  decide \+kernel)\n'
        r'\nend Phase17ResourceDigests\n\Z', text)
    require(final is not None, 'negative control must end in the designated False goal')
    return text.count('\n', 0, final.start('tactic')) + 1, 2


def _negative(command: dict, source: bytes) -> None:
    """Accept one rejection of the final control, never a failed setup lemma."""
    require(type(command['returncode']) is int and command['returncode'] == 1 and
            command['stderr'] == '', 'negative resource digests control exit/stderr differs')
    require(type(command['stdout']) is str and command.get('source_sha256') == sha(source),
            'negative resource digests output/source identity differs')
    line, column = _negative_site(source)
    match = re.fullmatch(
        r'([^\r\n]+\.lean):([1-9][0-9]*):([0-9]+): '
        r'error: Tactic `decide` proved that the proposition\n  False\nis false\n',
        command['stdout'])
    require(match is not None, 'exactly one final False rejection required')
    args = command.get('argv')
    require(type(args) is list and args and type(args[-1]) is str and
            _path_identity(match[1]) == _path_identity(args[-1]) and
            match[2] == str(line) and match[3] == str(column),
            'negative rejection is not at the intended source file/line/column')


def _resolved_modules(command: dict, expected: dict[str, str]) -> dict[str, str]:
    """Validate the client's complete import list, including both final imports."""
    require(command['returncode'] == 0 and command['stderr'] == '', 'resource digests dependency resolution failed')
    paths = command['stdout'].splitlines()
    names, identities = [], []
    leaves = ('Init.olean', *(name + '.olean' for name in expected))
    for path in paths:
        normalized = _path_identity(path)
        identities.append(normalized)
        leaf = normalized.rsplit('/', 1)[-1]
        if re.match(r'^[a-z]:/', normalized):
            leaf = next((known for known in leaves
                         if leaf == known.casefold()), leaf)
        names.append(leaf)
    require(names == ['Init.olean', 'Init.olean', *(name + '.olean' for name in expected)],
            'unexpected resource digests import inventory')
    require(identities[0] == identities[1], 'conflicting Init import paths')
    result = {}
    for index, (name, path) in enumerate(expected.items(), start=2):
        require(_path_identity(paths[index]) == _path_identity(path),
                'resource digests dependency resolved outside the same-run directory')
        result[name] = paths[index]
    return result


def _resolution_targets(name: str, folder: str) -> dict[str, str]:
    imports = CLIENT_IMPORTS[RESOLUTION_CLIENTS[name]]
    return {module: folder.rstrip('/\\') + '/' + module + '.olean' for module in imports}


def _command_paths(commands: list[dict], executables: dict, labels: tuple, environment: dict) -> None:
    """Bind each saved invocation to its own source and the same import root."""
    tools = {}
    for path in executables:
        normalized = _path_identity(path)
        leaf = normalized.rsplit('/', 1)[-1]
        if leaf.endswith('.exe'):
            leaf = leaf[:-4]
        require(leaf in ('lean', 'lake', 'git') and leaf not in tools,
                'resource digests tool identities must be exactly Lean, Lake and Git')
        tools[leaf] = normalized
    require(set(tools) == {'lean', 'lake', 'git'}, 'missing resource digests tool identity')
    _validate_environment(environment, commands, tools)
    argv = commands[0].get('argv')
    require(type(argv) is list and len(argv) == 2 and
            _path_identity(argv[0]) == tools['lean'] and argv[1] == '--version',
            'resource digests version command differs from recorded Lean')
    first = commands[COMPILE_START].get('argv')
    require(type(first) is list and len(first) == 7 and type(first[3]) is str and
            first[3].startswith('--root='), 'resource digests compile root missing')
    folder = first[3][len('--root='):]
    folder_identity = _path_identity(folder)
    require(folder_identity == _path_identity(environment['fresh_module_directory']),
            'compiler root differs from captured environment')

    def expected_path(value, leaf):
        require(_path_identity(value) == _path_identity(folder.rstrip('/\\') + '/' + leaf),
                'resource digests command path differs from exact source/output')

    def prefix(command, size):
        args = command.get('argv')
        require(type(args) is list and len(args) == size and
                all(type(item) is str for item in args), 'resource digests command shape differs')
        require(_path_identity(args[0]) == tools['lean'] and args[1:3] == list(DIRECT_FLAGS) and
                args[3].startswith('--root=') and _path_identity(args[3][len('--root='):]) == folder_identity,
                'resource digests direct command tool/flags/root differ')
        return args

    for index, name in enumerate(COMPILED_MODULES):
        args = prefix(commands[COMPILE_START + index], 7)
        require(args[4] == '-o', 'resource digests dependency output option differs')
        expected_path(args[5], name + '.olean')
        expected_path(args[6], name + '.lean')
        client = RESOLUTION_CLIENTS[name]
        args = prefix(commands[RESOLUTION_START + index], 6)
        require(args[4] == '--deps', 'resource digests dependency resolution option differs')
        expected_path(args[5], client + '.lean')
    for label, command in zip(labels, commands[CASE_START:], strict=True):
        args = prefix(command, 5)
        expected_path(args[4], label + '.lean')


def validate_result(result: dict, sources: dict[str, bytes], packet_sha256: str) -> None:
    """Check saved sources/logs without compiling, preparing, or executing argv."""
    from .resource_digests_lean import NAMES, LABELS
    fields = {'schema', 'status', 'packet_sha256', 'commands', 'theorem_axioms',
              'negative_controls_rejected', 'new_named_audits', 'resource_event_hashes_checked',
              'resource_work_digests_checked', 'claims', 'source_sha256', 'executable_sha256',
              'compiler_environment',
              'dependency_modules', 'auxiliary_modules', 'trusted_import_cache_assumption',
              'byte_capture_remains_external', 'digest_authenticity_remains_external',
              'general_planner_equivalence', 'general_json_parser_equivalence', 'python_execution_remains_external',
              'general_sha256_equivalence', 'selected_objective_challenge_binding_checked',
              'challenge_freshness_remains_external', 'objective_policy_succession_remains_external', 'selected_objective_policy_checked', 'selected_sha256_computation_checked', 'general_grammar_parameter_derivation_remains_external',
              'sha256_collision_resistance_remains_external',
              'full_transformer_equivalence', 'old_proof_campaigns_rerun',
              'general_evaluator_equivalence', 'selected_resource_kind_schedule_checked', 'whole_journal_file_hash_computation_remains_external', 'producer_response_hash_computation_remains_external', 'selected_candidate_admission_digests_checked', 'challenge_secrecy_remains_external', 'evaluator_independence_remains_external',
              'general_resource_ledger_equivalence', 'physical_journal_persistence_remains_external',
              'external_head_authenticity_remains_external'}
    require(type(result) is dict and set(result) == fields and result['schema'] == SCHEMA and
            result['status'] == 'passed', 'resource digests Lean gate did not pass')
    require(list(sources) == [*COMPILED_MODULES, *LABELS] and
            all(type(raw) is bytes and raw for raw in sources.values()), 'exact resource digests sources required')
    require(_digest(packet_sha256) and result['packet_sha256'] == packet_sha256 and
            result['source_sha256'] == {name: sha(raw) for name, raw in sources.items()},
            'executed resource digests sources differ')
    require(result['negative_controls_rejected'] == list(LABELS[1:]) and
            type(result['new_named_audits']) is int and result['new_named_audits'] == len(NAMES),
            'resource digests theorem/control inventory differs')
    require(result['resource_event_hashes_checked'] is True and result['resource_work_digests_checked'] is True,
            'resource digests proof scope differs')
    require(canonical(result['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'resource digests result escalates full-root authority')
    require(result['general_resource_ledger_equivalence'] is False and
            result['physical_journal_persistence_remains_external'] is True and
            result['external_head_authenticity_remains_external'] is True and
            result['trusted_import_cache_assumption'] is True and
            result['byte_capture_remains_external'] is True and
            result['digest_authenticity_remains_external'] is True and
            result['general_evaluator_equivalence'] is False and
            result['selected_resource_kind_schedule_checked'] is True and
            result['whole_journal_file_hash_computation_remains_external'] is True and
            result['producer_response_hash_computation_remains_external'] is True and
            result['selected_candidate_admission_digests_checked'] is True and
            result['challenge_secrecy_remains_external'] is True and
            result['evaluator_independence_remains_external'] is True and
            result['general_planner_equivalence'] is False and
            result['general_json_parser_equivalence'] is False and
            result['general_sha256_equivalence'] is False and
            result['selected_objective_policy_checked'] is True and
            result['selected_objective_challenge_binding_checked'] is True and
            result['challenge_freshness_remains_external'] is True and
            result['objective_policy_succession_remains_external'] is True and
            result['selected_sha256_computation_checked'] is True and
            result['general_grammar_parameter_derivation_remains_external'] is True and
            result['sha256_collision_resistance_remains_external'] is True and
            result['python_execution_remains_external'] is True and
            result['full_transformer_equivalence'] is False and result['old_proof_campaigns_rerun'] is False,
            'resource digests trust/scope record differs')
    exes = result['executable_sha256']
    require(type(exes) is dict and len(exes) == 3 and all(type(name) is str and _digest(value)
            for name, value in exes.items()), 'resource digests executable inventory differs')
    inherited = result['dependency_modules']
    auxiliary = result['auxiliary_modules']
    require(type(inherited) is dict and set(inherited) == set(DEPENDENCIES),
            'exactly eleven fresh resource digests dependencies required')
    require(type(auxiliary) is dict and set(auxiliary) == set(AUXILIARIES),
            'exactly seven fresh resource digests arithmetic auxiliaries required')
    modules = {**inherited, **auxiliary}
    commands = result['commands']
    require(type(commands) is list and len(commands) == CASE_START + len(LABELS), 'resource digests command inventory differs')
    for command in commands:
        require(type(command) is dict and type(command.get('returncode')) is int and
                type(command.get('stdout')) is str and type(command.get('stderr')) is str,
                'malformed resource digests command')
        require(command['stdout_sha256'] == sha(command['stdout'].encode('utf-8')) and
                command['stderr_sha256'] == sha(command['stderr'].encode('utf-8')), 'resource digests log hashes differ')
    _command_paths(commands, exes, LABELS, result['compiler_environment'])
    version = commands[0]
    require(version['returncode'] == 0 and version['stderr'] == '' and
            re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']) is not None, 'wrong pinned Lean')
    for index, name in enumerate(COMPILED_MODULES):
        dependency = modules[name]
        require(type(dependency) is dict and set(dependency) == {'name', 'source_sha256', 'artifacts_sha256',
                'resolved_module_path', 'compiled_in_this_run', 'prior_success_report_used_as_proof'} and
                dependency['name'] == name and dependency['source_sha256'] == sha(sources[name]) and
                dependency['compiled_in_this_run'] is True and
                dependency['prior_success_report_used_as_proof'] is False, 'fresh resource digests dependency required')
        artifacts = dependency['artifacts_sha256']
        require(type(artifacts) is dict and name + '.olean' in artifacts and all(
            item in {name + suffix for suffix in ('.olean', '.olean.private', '.olean.server', '.ir')} and
            _digest(value) for item, value in artifacts.items()), 'resource digests dependency artifact differs')
        compiled = commands[COMPILE_START + index]
        require(compiled.get('label') == name and compiled.get('source_sha256') == sha(sources[name]) and
                compiled['returncode'] == 0 and compiled['stdout'] == '' and compiled['stderr'] == '' and
                compiled.get('output_artifacts_sha256') == artifacts, 'resource digests dependency compilation differs')
        argv = compiled.get('argv')
        require(type(argv) is list and len(argv) >= 4 and argv[-3] == '-o', 'dependency output argument missing')
        resolution = commands[RESOLUTION_START + index]
        client = RESOLUTION_CLIENTS[name]
        require(resolution.get('label') == name + '_resolution' and
                resolution.get('source_sha256') == sha(sources[client]) and
                type(resolution.get('argv')) is list and len(resolution['argv']) >= 3 and
                resolution['argv'][-2] == '--deps', 'resource digests resolution command differs')
        folder = argv[3][len('--root='):]
        resolved = _resolved_modules(resolution, _resolution_targets(name, folder))[name]
        require(dependency['resolved_module_path'] == resolved, 'recorded resource digests import path differs')
    for label, command in zip(LABELS, commands[CASE_START:], strict=True):
        require(command.get('label') == label and command.get('source_sha256') == sha(sources[label]),
                'resource digests command/source binding differs')
        if label == LABELS[0]:
            require(command['returncode'] == 0 and command['stderr'] == '', 'positive resource digests certificate rejected')
            require(result['theorem_axioms'] == parse_audits(command['stdout']), 'resource digests axiom report differs')
        else:
            _negative(command, sources[label])


def _artifacts(folder: Path, name: str) -> dict[str, str]:
    result = {}
    for suffix in ('.olean', '.olean.private', '.olean.server', '.ir'):
        path = folder / (name + suffix)
        if path.exists():
            raw = gate._read_regular(path)
            require(bool(raw), 'empty resource digests dependency artifact')
            result[path.name] = sha(raw)
    require(name + '.olean' in result, 'fresh resource digests dependency not emitted')
    return result


def check(prepared: PreparedResourceDigests, *, source_root: Path, lean_workspace: Path,
          toolchain_root: Path | None = None, progress_path: Path | None = None) -> dict:
    from .resource_digests_lean import generated_sources, NAMES, LABELS
    require(type(prepared) is PreparedResourceDigests, 'exact resource digests packet required')
    result = {'schema': SCHEMA, 'status': 'blocked', 'packet_sha256': sha(prepared.packet_bytes),
              'commands': [], 'theorem_axioms': {}, 'negative_controls_rejected': [],
              'new_named_audits': len(NAMES), 'resource_event_hashes_checked': False,
              'resource_work_digests_checked': False, 'claims': {name: False for name in FALSE_CLAIMS}}

    def checkpoint():
        if progress_path is not None:
            require(not progress_path.is_symlink(), 'linked resource digests progress output')
            progress_path.write_bytes((json.dumps(result, sort_keys=True, indent=2) + '\n').encode())

    try:
        sources = generated_sources(prepared, source_root=source_root)
        require(list(sources) == [*COMPILED_MODULES, *LABELS], 'unexpected generated resource digests modules')
        templates = {p.relative_to(source_root).as_posix(): sha(gate._read_regular(p))
                     for p in sorted((source_root / 'lean/phase17_bridge').glob('*.lean'))}
        retained = read_retained(source_root)
        roots = gate.root_source_fingerprint(lean_workspace)
        require({name: item['canonical_sha256'] for name, item in roots.items()} ==
                {name: item['canonical_sha256'] for name, item in gate.root_source_fingerprint(source_root).items()},
                'pinned resource digests root mismatch')
        deps = gate._dependency_state(lean_workspace)
        tool = gate.resolve_toolchain(toolchain_root)
        base_env, git = gate._lean_environment(tool)
        suffix = '.exe' if os.name == 'nt' else ''
        lean, lake = tool / 'bin' / ('lean' + suffix), tool / 'bin' / ('lake' + suffix)
        exes = {str(path): sha(gate._read_regular(path)) for path in (lean, lake, git)}
        probe = Path(sys.executable).resolve(strict=True)
        probe_hash = sha(gate._read_regular(probe))
        cwd = (lean_workspace / gate.ROOT_PROJECT).resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix='r17ab-') as tmp:
            folder = Path(tmp).resolve(strict=True)
            for name, raw in sources.items():
                (folder / (name + '.lean')).write_bytes(raw)
            base_env = dict(base_env, LEAN_PATH=str(folder))

            def run(argv, env, *, timeout):
                command = gate._process(argv, cwd, env, timeout=timeout)
                command.update(cwd=str(cwd), environment_sha256=sha(_environment_bytes(env)))
                return command

            version = run([str(lean), '--version'], base_env, timeout=30)
            result['commands'].append(version)
            checkpoint()
            require(version['returncode'] == 0 and not version['stderr'] and
                    re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']), 'wrong pinned Lean')
            result['status'] = 'rejected'
            capture = run([str(lake), '--keep-toolchain', '--no-cache', 'env', str(probe),
                           '-I', '-S', '-B', '-c', ENVIRONMENT_PROBE], base_env, timeout=120)
            capture.update(label=ENVIRONMENT_LABEL, source_sha256=sha(ENVIRONMENT_PROBE.encode('utf-8')),
                           probe_executable_sha256=probe_hash)
            result['commands'].append(capture)
            checkpoint()
            require(capture['returncode'] == 0 and capture['stderr'] == '', 'Lake child environment capture failed')
            report = _environment_report(capture['stdout'])
            env = report['environment']
            environment = {
                'schema': ENVIRONMENT_SCHEMA, 'capture_semantics': CAPTURE_SEMANTICS,
                'platform': os.name, 'cwd': str(cwd), 'fresh_module_directory': str(folder),
                'base_environment': base_env, 'base_environment_sha256': sha(_environment_bytes(base_env)),
                'effective_environment': env, 'effective_environment_sha256': sha(_environment_bytes(env)),
                'probe_executable': str(probe), 'probe_executable_sha256': probe_hash,
                'probe_source_sha256': sha(ENVIRONMENT_PROBE.encode('utf-8'))}
            result['compiler_environment'] = environment
            _validate_environment(environment, result['commands'],
                                  {'lean': _path_identity(str(lean)), 'lake': _path_identity(str(lake)),
                                   'git': _path_identity(str(git))})
            checkpoint()
            modules = {}

            def unchanged():
                require(all((folder / (name + '.lean')).read_bytes() == raw for name, raw in sources.items()),
                        'resource digests source changed during Lean checking')
                for name, module in modules.items():
                    require(_artifacts(folder, name) == module['artifacts_sha256'],
                            'same-run resource digests dependency changed')

            for name in COMPILED_MODULES:
                compiled = run([str(lean), *DIRECT_FLAGS,
                    '--root=' + str(folder), '-o', str(folder / (name + '.olean')), str(folder / (name + '.lean'))],
                    env, timeout=1800)
                compiled.update(label=name, source_sha256=sha(sources[name]))
                result['commands'].append(compiled)
                checkpoint()
                require(compiled['returncode'] == 0 and compiled['stdout'] == '' and compiled['stderr'] == '',
                        'fresh resource digests dependency did not compile: ' + name)
                artifacts = _artifacts(folder, name)
                compiled['output_artifacts_sha256'] = artifacts
                modules[name] = {'name': name, 'source_sha256': sha(sources[name]),
                                 'artifacts_sha256': artifacts, 'compiled_in_this_run': True,
                                 'prior_success_report_used_as_proof': False}
                result['dependency_modules'] = {key: modules[key] for key in DEPENDENCIES if key in modules}
                result['auxiliary_modules'] = {key: modules[key] for key in AUXILIARIES if key in modules}
                unchanged()
                checkpoint()
            for name in COMPILED_MODULES:
                client = RESOLUTION_CLIENTS[name]
                resolution = run([str(lean), *DIRECT_FLAGS,
                    '--root=' + str(folder), '--deps', str(folder / (client + '.lean'))],
                    env, timeout=120)
                resolution.update(label=name + '_resolution', source_sha256=sha(sources[client]))
                result['commands'].append(resolution)
                checkpoint()
                modules[name]['resolved_module_path'] = _resolved_modules(
                    resolution, _resolution_targets(name, str(folder)))[name]
                unchanged()
                checkpoint()
            audits = {}
            for label in LABELS:
                command = run([str(lean), *DIRECT_FLAGS,
                    '--root=' + str(folder), str(folder / (label + '.lean'))],
                    env, timeout=1800)
                command.update(label=label, source_sha256=sha(sources[label]))
                result['commands'].append(command)
                checkpoint()
                if label == LABELS[0]:
                    require(command['returncode'] == 0 and command['stderr'] == '', 'resource digests certificate rejected')
                    audits = parse_audits(command['stdout'])
                else:
                    _negative(command, sources[label])
                    result['negative_controls_rejected'].append(label)
                unchanged()
                checkpoint()
        require(roots == gate.root_source_fingerprint(lean_workspace) and deps == gate._dependency_state(lean_workspace),
                'root/dependency changed during AB checking')
        require(exes == {name: sha(gate._read_regular(Path(name))) for name in exes} and
                probe_hash == sha(gate._read_regular(probe)) and
                templates == {name: sha(gate._read_regular(source_root / name)) for name in templates} and
                retained == read_retained(source_root), 'tool/template/retained input changed during AB checking')
        result.update(status='passed', theorem_axioms=audits, resource_event_hashes_checked=True,
                      resource_work_digests_checked=True, source_sha256={name: sha(raw) for name, raw in sources.items()},
                      executable_sha256=exes,
                      dependency_modules={name: modules[name] for name in DEPENDENCIES},
                      auxiliary_modules={name: modules[name] for name in AUXILIARIES},
                      trusted_import_cache_assumption=True,
                      general_resource_ledger_equivalence=False,
                      physical_journal_persistence_remains_external=True,
                      external_head_authenticity_remains_external=True,
                      byte_capture_remains_external=True, digest_authenticity_remains_external=True,
                      general_evaluator_equivalence=False,
                      selected_resource_kind_schedule_checked=True,
                      whole_journal_file_hash_computation_remains_external=True,
                      producer_response_hash_computation_remains_external=True,
                      selected_candidate_admission_digests_checked=True,
                      challenge_secrecy_remains_external=True,
                      evaluator_independence_remains_external=True,
                      general_planner_equivalence=False, general_json_parser_equivalence=False,
                      python_execution_remains_external=True,
                      general_sha256_equivalence=False, selected_objective_policy_checked=True,
                      selected_objective_challenge_binding_checked=True,
                      challenge_freshness_remains_external=True, objective_policy_succession_remains_external=True,
                      selected_sha256_computation_checked=True,
                      general_grammar_parameter_derivation_remains_external=True,
                      sha256_collision_resistance_remains_external=True,
                      full_transformer_equivalence=False, old_proof_campaigns_rerun=False)
        validate_result(result, sources, sha(prepared.packet_bytes))
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result['status'] = 'blocked' if result['status'] == 'blocked' else 'rejected'
        result['failure'] = {'type': type(exc).__name__, 'reason': str(exc)}
    finally:
        checkpoint()
    return result
