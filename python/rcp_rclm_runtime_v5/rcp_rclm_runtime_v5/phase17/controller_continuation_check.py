"""Pinned AC checking with explicitly selected, immutable stage continuations.

The new contract validates two newly compiled modules and their selected lineage,
not the historical AB one-process application. Restoration checks exact object
bytes and current import paths before continuing. It never reuses an unfinished
stage, executes a command from a report, or infers an orphan's outcome.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import ntpath
import os
from pathlib import Path
import posixpath
import re
import sys

from . import lean_frontier_gate as pinned
from . import compilation_checkpoint as checkpoints
from .controller_continuation import require, sha, canonical, FALSE_CLAIMS
from .controller_continuation_lean import (MODULES, POSITIVE, NEGATIVES, NAMES,
                                         parse_audits, validate_negative)
from .resource_digests_check import (BASE_OPTIONAL, BASE_REQUIRED, LAKE_VARIABLES,
                                    _environment_mapping, _environment_bytes)

SCHEMA = 'rcp-rclm.phase17ac.controller-continuation-lean.v1'
ENV_SCHEMA = 'rcp-rclm.phase17ac.compiler-environment.v1'
DIRECT_FLAGS = ('-j1', '-DElab.async=false')
PROBE = ('import json,os,sys\n'
         'p={"environment":dict(os.environ),"executable":sys.executable,'
         '"platform":os.name,"cwd":os.getcwd()}\n'
         'sys.stdout.buffer.write((json.dumps(p,ensure_ascii=True,sort_keys=True,'
         'separators=(",",":"))+"\\n").encode("ascii"))\n')
COMMAND_FIELDS = {'argv', 'returncode', 'stdout', 'stderr', 'stdout_sha256',
                  'stderr_sha256', 'started_at_utc', 'elapsed_ns', 'cwd', 'environment_sha256'}


def write_new(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write((json.dumps(value, sort_keys=True, indent=2) + '\n').encode())
        handle.flush(); os.fsync(handle.fileno())


def source_paths(root: Path) -> list[str]:
    names = set()
    for version in (2, 3, 4, 5):
        package = 'rcp_rclm_runtime' if version == 2 else 'rcp_rclm_runtime_v' + str(version)
        names.update(p.relative_to(root).as_posix() for p in
                     (root / 'python' / ('rcp_rclm_runtime_v' + str(version)) / package).rglob('*.py'))
    names.update(p.relative_to(root).as_posix() for p in (root / 'lean/phase17_bridge').glob('*.lean'))
    names.update(p.relative_to(root).as_posix() for p in (root / 'scripts').glob('*.py'))
    names.update(p.relative_to(root).as_posix() for p in
                 (root / 'python/rcp_rclm_runtime_v5/tests_phase17ac').glob('test_*.py'))
    names.add('python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/lean_root_pins.json')
    return sorted(names)


def source_snapshot(root: Path) -> dict:
    return {name: sha(checkpoints._read(root / name)) for name in source_paths(root)}


def _identity(path: str) -> str:
    require(type(path) is str and path and not any(c in path for c in '\x00\n\r'), 'invalid import path')
    value = path.replace('\\', '/')
    if re.match(r'^[A-Za-z]:/', value):
        return ntpath.normpath(value).replace('\\', '/').casefold()
    require(value.startswith('/') and '\\' not in path, 'absolute portable import path required')
    return posixpath.normpath(value)


def _joined(parent: str, name: str, platform: str) -> str:
    module = ntpath if platform == 'nt' else posixpath
    return _identity(module.normpath(module.join(parent, name)))


def _digest(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _log_record(command: dict, *, timeout_seconds: int, extra_fields=()):
    require(type(command) is dict and set(command) == COMMAND_FIELDS | set(extra_fields),
            'exact captured command fields required')
    require(type(command['argv']) is list and command['argv'] and
            all(type(x) is str and x and '\x00' not in x for x in command['argv']) and
            type(command['returncode']) is int and type(command['elapsed_ns']) is int and
            0 <= command['elapsed_ns'] <= timeout_seconds * 1_000_000_000 and
            type(command['started_at_utc']) is str and
            type(command['stdout']) is str and type(command['stderr']) is str and
            len(command['stdout']) + len(command['stderr']) <= 2 * 1024 * 1024,
            'malformed, unresolved or over-budget captured command')
    require(command['stdout_sha256'] == sha(command['stdout'].encode('utf-8')) and
            command['stderr_sha256'] == sha(command['stderr'].encode('utf-8')) and
            _digest(command['environment_sha256']), 'captured command stream/environment hash differs')
    parsed = datetime.fromisoformat(command['started_at_utc'])
    require(parsed.tzinfo is not None, 'timezone-aware command timestamp required')


def _child_report(stdout: str) -> dict:
    require(type(stdout) is str and len(stdout) <= 256 * 1024, 'bounded child report required')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate isolated-child report key')
            result[key] = value
        return result
    child = json.loads(stdout, object_pairs_hook=unique)
    require(type(child) is dict and set(child) == {'environment', 'executable', 'platform', 'cwd'} and
            child['platform'] in ('posix', 'nt') and
            _environment_bytes(child).decode('ascii') == stdout,
            'exact canonical isolated-child report required')
    return child


def _environment_policy(record: dict) -> None:
    """Reconstruct the approved effective mapping from the saved native output.

    This is a data verifier, not execution attestation. The actual capture and
    its externally retained file identity still belong to the trusted operator.
    """
    fields = {'schema', 'status', 'recorded_at_utc', 'platform', 'module_search_seed',
              'lean_workspace', 'cwd', 'toolchain_root', 'root_sources', 'dependencies',
              'binaries', 'compiled_foundation', 'mathlib_root', 'init_module',
              'probe_source_sha256', 'base_environment', 'observed_environment',
              'environment_template', 'commands', 'trusted_import_cache_assumption',
              'physical_execution_attested'}
    require(type(record) is dict and set(record) == fields and record['schema'] == ENV_SCHEMA and
            record['status'] == 'passed' and record['platform'] in ('nt', 'posix') and
            record['probe_source_sha256'] == sha(PROBE.encode()) and
            record['trusted_import_cache_assumption'] is True and record['physical_execution_attested'] is False,
            'compiler environment scope or field inventory differs')
    require(type(record['recorded_at_utc']) is str and
            datetime.fromisoformat(record['recorded_at_utc']).tzinfo is not None,
            'timezone-aware compiler capture timestamp required')
    platform = record['platform']; windows = platform == 'nt'; separator = ';' if windows else ':'
    name = lambda key: key.upper() if windows else key
    cwd, tool, seed = (_identity(record[key]) for key in ('cwd', 'toolchain_root', 'module_search_seed'))
    require(cwd == _joined(record['lean_workspace'], pinned.ROOT_PROJECT, platform) and
            bool(re.match(r'^[a-z]:/', cwd)) == windows and
            bool(re.match(r'^[a-z]:/', tool)) == windows and
            bool(re.match(r'^[a-z]:/', seed)) == windows and seed.rsplit('/', 1)[-1] == 'module-search-seed',
            'compiler workspace, seed, platform or tool root differs')
    binaries = record['binaries']
    require(type(binaries) is dict and set(binaries) == {'lean', 'lake', 'git', 'python'},
            'exact executable inventory required')
    for item in [*binaries.values(), record['mathlib_root'], record['init_module']]:
        require(type(item) is dict and set(item) == {'path', 'sha256'} and _digest(item['sha256']),
                'invalid bound file identity')
        _identity(item['path'])
    suffix = '.exe' if windows else ''
    require(_identity(binaries['lean']['path']) == tool + '/bin/lean' + suffix and
            _identity(binaries['lake']['path']) == tool + '/bin/lake' + suffix and
            _identity(record['init_module']['path']) == _joined(record['toolchain_root'], 'lib/lean/Init.olean', platform),
            'toolchain binary or Init module identity differs')
    dependencies = record['dependencies']
    require(type(dependencies) is dict and 'mathlib' in dependencies and
            all(type(key) is str and key and type(rows) is list and rows and
                all(type(row) is dict and set(row) == {'path', 'head'} and
                    type(row['head']) is str and re.fullmatch(r'[0-9a-f]{40}', row['head'])
                    for row in rows) for key, rows in dependencies.items()),
            'dependency revision inventory malformed')
    require(_identity(record['mathlib_root']['path']) ==
            _joined(dependencies['mathlib'][0]['path'], '.lake/build/lib/lean/Mathlib.olean', platform),
            'Mathlib root differs from pinned dependency checkout')
    base = _environment_mapping(record['base_environment'], BASE_OPTIONAL | BASE_REQUIRED, platform)
    actual = _environment_mapping(record['observed_environment'], BASE_OPTIONAL | BASE_REQUIRED | LAKE_VARIABLES |
                                  ({'LC_CTYPE'} if not windows else set()), platform)
    require({name(key) for key in BASE_REQUIRED} <= set(base), 'restricted base environment is incomplete')
    fixed = {'ELAN_TOOLCHAIN': pinned.TOOLCHAIN, 'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1',
             'GIT_CONFIG_GLOBAL': 'nul' if windows else '/dev/null', 'LAKE_NO_CACHE': 'true',
             'LAKE_ARTIFACT_CACHE': 'false', 'NoDefaultCurrentDirectoryInExePath': '1'}
    require(all(base.get(name(key)) == value for key, value in fixed.items()) and
            _identity(base['LEAN_PATH']) == seed and
            all('{workspace}' not in value for value in (*base.values(), *actual.values())),
            'restricted base policy, seed or substitution boundary differs')
    base_paths = base['PATH'].split(separator)
    require(all(base_paths), 'empty restricted PATH component')
    base_ids = [_identity(path) for path in base_paths]
    expected_prefix = list(dict.fromkeys((tool + '/bin', _identity(binaries['git']['path']).rsplit('/', 1)[0])))
    require(base_ids[:len(expected_prefix)] == expected_prefix, 'restricted PATH tool prefix differs')
    inherited = {name(key) for key in (BASE_OPTIONAL | BASE_REQUIRED) - LAKE_VARIABLES}
    require(all((key in base) == (key in actual) and (key not in base or base[key] == actual[key])
                for key in inherited), 'Lake changed a retained base variable')
    require(actual.get('ELAN_TOOLCHAIN') == pinned.TOOLCHAIN and actual.get('LAKE_NO_CACHE') == 'true' and
            actual.get('LAKE_ARTIFACT_CACHE') == 'false' and
            _identity(actual.get('LEAN')) == _identity(binaries['lean']['path']) and
            _identity(actual.get('LAKE')) == _identity(binaries['lake']['path']) and
            _identity(actual.get('LEAN_SYSROOT')) == tool,
            'effective compiler/toolchain/cache policy differs')
    require(all(type(actual.get(key)) is str and actual[key] for key in ('LEAN_PATH', 'LEAN_SRC_PATH', 'PATH')),
            'effective compiler search paths missing')
    project_roots = [_joined(record['lean_workspace'], f'lean/rcp_rclm_formal_core_v{v}', platform)
                     for v in (2, 3, 4)]
    package_roots = [_identity(row['path']) for rows in dependencies.values() for row in rows]
    allowed_lean = {root + '/.lake/build/lib/lean' for root in (*project_roots, *package_roots)} | {tool + '/lib/lean', seed}
    parts = actual['LEAN_PATH'].split(separator)
    require(all(parts), 'empty Lean import search component')
    identities = [_joined(record['cwd'], part, platform) for part in parts]
    require(identities.count(seed) == 1 and all(path in allowed_lean for path in identities),
            'Lean import search is outside the reviewed root/dependency closure')
    # Pinned Lake puts its reviewed shared-library directories on Windows PATH
    # for DLL resolution. On POSIX these belong only to the library search
    # variables. This does not permit arbitrary extra PATH directories.
    windows_libraries = ({root + '/.lake/build/lib' for root in (*project_roots, *package_roots)}
                         if windows else set())
    for key, allowed in (
        ('PATH', {root + '/.lake/build/bin' for root in (*project_roots, *package_roots)} |
                 set(base_ids) | {tool + '/bin'} | windows_libraries),
        ('LEAN_SRC_PATH', set(project_roots) | set(package_roots) |
                          {tool + '/src/lean', tool + '/src/lean/lake'}),
        ('LD_LIBRARY_PATH', {root + '/.lake/build/lib' for root in (*project_roots, *package_roots)} |
                            {tool + '/lib', tool + '/lib/lean'}),
        ('DYLD_LIBRARY_PATH', {root + '/.lake/build/lib' for root in (*project_roots, *package_roots)} |
                              {tool + '/lib', tool + '/lib/lean'})):
        if key in actual:
            entries = actual[key].split(separator)
            require(all(entries) and all(_joined(record['cwd'], item, platform) in allowed for item in entries),
                    'unreviewed effective search component: ' + key)
    template = dict(record['observed_environment'])
    lean_key = next(key for key in template if name(key) == 'LEAN_PATH')
    template[lean_key] = separator.join('{workspace}' if identity == seed else part
                                        for identity, part in zip(identities, parts, strict=True))
    require(record['environment_template'] == template, 'compiler template does not reconstruct from captured environment')
    commands = record['commands']
    require(type(commands) is list and len(commands) == 2, 'exact setup command inventory required')
    version, capture = commands
    for command, timeout in ((version, 30), (capture, 120)):
        _log_record(command, timeout_seconds=timeout)
        require(command['returncode'] == 0 and command['stderr'] == '' and
                _identity(command['cwd']) == cwd and
                command['environment_sha256'] == sha(_environment_bytes(record['base_environment'])),
                'setup command outcome or environment binding differs')
    require(version['argv'] == [binaries['lean']['path'], '--version'] and
            re.fullmatch(r'Lean \(version 4\.31\.0(?:,[^\r\n]*)?\)\n?', version['stdout']) is not None,
            'pinned version command or output differs')
    require(capture['argv'] == [binaries['lake']['path'], '--keep-toolchain', '--no-cache', 'env',
                                binaries['python']['path'], '-I', '-S', '-B', '-c', PROBE],
            'isolated Lake child invocation differs')
    child = _child_report(capture['stdout'])
    require(child['platform'] == platform and _identity(child['cwd']) == cwd and
            _identity(child['executable']) == _identity(binaries['python']['path']) and
            child['environment'] == record['observed_environment'], 'saved child output and environment disagree')


def _compiled_foundation(workspace: Path) -> dict:
    observed = {}
    for version_number in (2, 3, 4):
        base = workspace / f'lean/rcp_rclm_formal_core_v{version_number}/.lake/build/lib/lean'
        for path in sorted(base.rglob('*')):
            if path.is_file() and path.name.endswith(('.olean', '.olean.private', '.olean.server')):
                observed[path.relative_to(workspace).as_posix()] = sha(checkpoints._read(path))
    require(observed, 'compiled foundation missing')
    return observed


def _command(argv, cwd, env, timeout):
    result = pinned._process(list(argv), cwd, env, timeout=timeout)
    result.update(cwd=str(cwd), environment_sha256=sha(_environment_bytes(env)))
    return result


def capture_environment(directory: Path, *, source_root: Path, lean_workspace: Path,
                        toolchain_root: Path | None) -> dict:
    require(not directory.exists(), 'new compiler environment capture required')
    directory.mkdir(parents=True)
    seed = directory / 'module-search-seed'; seed.mkdir()
    roots = pinned.root_source_fingerprint(lean_workspace)
    require({k: v['canonical_sha256'] for k, v in roots.items()} ==
            {k: v['canonical_sha256'] for k, v in pinned.root_source_fingerprint(source_root).items()},
            'AC pinned foundation source differs')
    dependencies = pinned._dependency_state(lean_workspace)
    tool = pinned.resolve_toolchain(toolchain_root); suffix = '.exe' if os.name == 'nt' else ''
    lean, lake = tool / 'bin' / ('lean' + suffix), tool / 'bin' / ('lake' + suffix)
    env, git = pinned._lean_environment(tool)
    env = dict(env, LEAN_PATH=str(seed))
    python = Path(sys.executable).resolve(strict=True)
    cwd = (lean_workspace / pinned.ROOT_PROJECT).resolve(strict=True)
    binaries = {name: {'path': str(path), 'sha256': sha(checkpoints._read(path))}
                for name, path in (('lean', lean), ('lake', lake), ('git', git), ('python', python))}
    version = _command([str(lean), '--version'], cwd, env, 30)
    require(version['returncode'] == 0 and not version['stderr'] and
            re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']), 'wrong pinned AC Lean')
    capture = _command([str(lake), '--keep-toolchain', '--no-cache', 'env', str(python),
                        '-I', '-S', '-B', '-c', PROBE], cwd, env, 120)
    require(capture['returncode'] == 0 and not capture['stderr'], 'pinned Lake environment capture failed')
    child = _child_report(capture['stdout'])
    require(
            child['platform'] == os.name and _identity(child['cwd']) == _identity(str(cwd)) and
            _identity(child['executable']) == _identity(str(python)), 'unexpected isolated child environment')
    actual = child['environment']
    _environment_mapping(actual, BASE_OPTIONAL | BASE_REQUIRED | LAKE_VARIABLES | {'LC_CTYPE'}, os.name)
    require(_identity(actual['LEAN']) == _identity(str(lean)) and
            _identity(actual['LAKE']) == _identity(str(lake)) and
            actual['ELAN_TOOLCHAIN'] == pinned.TOOLCHAIN and actual['LAKE_NO_CACHE'] == 'true' and
            actual['LAKE_ARTIFACT_CACHE'] == 'false', 'Lake selected different tools or cache policy')
    paths = actual['LEAN_PATH'].split(os.pathsep)
    require(sum(_identity(str((cwd / p).resolve())) == _identity(str(seed)) for p in paths) == 1,
            'unique AC module search root required')
    # Only this explicitly selected module root is variable across invocations.
    template = dict(actual)
    template['LEAN_PATH'] = os.pathsep.join('{workspace}' if _identity(str((cwd / p).resolve())) ==
                                           _identity(str(seed)) else p for p in paths)
    compiled = _compiled_foundation(lean_workspace)
    mathlib = Path(dependencies['mathlib'][0]['path']) / '.lake/build/lib/lean/Mathlib.olean'
    init = tool / 'lib/lean/Init.olean'
    record = {'schema': ENV_SCHEMA, 'status': 'passed', 'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
              'platform': os.name, 'module_search_seed': str(seed),
              'lean_workspace': str(lean_workspace), 'cwd': str(cwd), 'toolchain_root': str(tool),
              'root_sources': roots, 'dependencies': dependencies, 'binaries': binaries,
              'compiled_foundation': compiled, 'mathlib_root': {'path': str(mathlib), 'sha256': sha(checkpoints._read(mathlib))},
              'init_module': {'path': str(init), 'sha256': sha(checkpoints._read(init))},
              'probe_source_sha256': sha(PROBE.encode()), 'base_environment': env,
              'observed_environment': actual, 'environment_template': template,
              'commands': [version, capture], 'trusted_import_cache_assumption': True,
              'physical_execution_attested': False}
    verify_environment(record, source_root)
    write_new(directory / 'environment.json', record)
    return record


def verify_environment(record: dict, source_root: Path):
    _environment_policy(record)
    require(record['platform'] == os.name, 'compiler environment is for another platform')
    workspace = Path(record['lean_workspace'])
    require(pinned.root_source_fingerprint(workspace) == record['root_sources'] and
            {k: v['canonical_sha256'] for k, v in record['root_sources'].items()} ==
            {k: v['canonical_sha256'] for k, v in pinned.root_source_fingerprint(source_root).items()},
            'pinned source identities changed')
    require(pinned._dependency_state(workspace) == record['dependencies'], 'pinned dependencies changed')
    for item in [*record['binaries'].values(), record['mathlib_root'], record['init_module']]:
        require(sha(checkpoints._read(Path(item['path']))) == item['sha256'], 'bound runtime binary changed')
    require(_compiled_foundation(workspace) == record['compiled_foundation'],
            'compiled foundation bytes or exact inventory changed')


def _resolve(record: dict, module: str, workspace: str, init_path: str) -> dict:
    require(module in MODULES and type(record['returncode']) is int and record['returncode'] == 0 and
            record['stderr'] == '' and type(record['stdout']) is str, 'restored module import resolution failed')
    paths = record['stdout'].splitlines()
    names = [_identity(path).rsplit('/', 1)[-1].casefold() for path in paths]
    require(len(paths) == 3 and names.count('init.olean') == 2 and names.count(module.casefold() + '.olean') == 1,
            'unexpected direct import inventory')
    require(all(_identity(path) == _identity(init_path) for name, path in zip(names, paths, strict=True)
                if name == 'init.olean'), 'import probe selected another Init module')
    resolved = paths[names.index(module.casefold() + '.olean')]
    expected = workspace.rstrip('/\\') + '/' + module + '.olean'
    require(_identity(resolved) == _identity(expected), 'import did not resolve to the restored compiled artifact')
    return {'module': module, 'resolved_module_path': resolved, 'init_module_path': init_path}


def configuration(*, source_root: Path, environment: dict, source_commit: str, source_tree: str,
                  source_hashes: dict, packet_sha256: str, proof_sources: dict) -> dict:
    verify_environment(environment, source_root)
    require(type(source_commit) is str and re.fullmatch(r'[0-9a-f]{40}', source_commit) and
            type(source_tree) is str and re.fullmatch(r'[0-9a-f]{40}', source_tree) and _digest(packet_sha256),
            'exact source commit, tree and packet identities required')
    require(type(proof_sources) is dict and set(proof_sources) == {*MODULES, POSITIVE, *NEGATIVES} and
            all(type(raw) is bytes and raw for raw in proof_sources.values()),
            'exact generated controller proof-source inventory required')
    require(source_snapshot(source_root) == source_hashes, 'AC source inventory changed')
    lean = environment['binaries']['lean']['path']
    prefix = (lean, *DIRECT_FLAGS, '--root={workspace}')
    stages = []
    for module in MODULES:
        stages.append(checkpoints.Stage(module, (*prefix, '-o', '{workspace}/' + module + '.olean',
                                                  '{workspace}/' + module + '.lean'), 1800, (module + '.olean',)))
        stages.append(checkpoints.Stage(module + '_resolution', (*prefix, '--deps',
                                             '{workspace}/Probe' + module + '.lean'), 120))
    stages.append(checkpoints.Stage(POSITIVE, (*prefix, '{workspace}/' + POSITIVE + '.lean'), 1800))
    stages.extend(checkpoints.Stage(label, (*prefix, '{workspace}/' + label + '.lean'), 1800) for label in NEGATIVES)
    fixed = {name + '.lean': raw for name, raw in proof_sources.items()}
    fixed.update({'Probe' + module + '.lean': ('import ' + module + '\n').encode() for module in MODULES})
    inputs = {name: source_root / name for name in source_hashes}; expected = dict(source_hashes)
    for name, item in environment['binaries'].items():
        inputs['tool:' + name] = Path(item['path']); expected['tool:' + name] = item['sha256']
    inputs['mathlib:root'] = Path(environment['mathlib_root']['path'])
    expected['mathlib:root'] = environment['mathlib_root']['sha256']
    inputs['toolchain:Init'] = Path(environment['init_module']['path'])
    expected['toolchain:Init'] = environment['init_module']['sha256']
    for name, value in environment['compiled_foundation'].items():
        inputs['foundation:' + name] = Path(environment['lean_workspace']) / name
        expected['foundation:' + name] = value
    for name, value in environment['root_sources'].items():
        inputs['root:' + name] = Path(environment['lean_workspace']) / name
        expected['root:' + name] = value['checkout_sha256']
    context = {'schema': SCHEMA, 'source_commit': source_commit, 'source_tree': source_tree,
               'packet_sha256': packet_sha256, 'proof_source_sha256': {n: sha(b) for n, b in proof_sources.items()},
               'compiler_environment_sha256': sha(_environment_bytes(environment)),
               'init_module': dict(environment['init_module']),
               'theorem_names': list(NAMES), 'negative_controls': list(NEGATIVES),
               'dependency_revisions': {n: [p['head'] for p in paths] for n, paths in environment['dependencies'].items()},
               'generic_module_count': 2, 'old_AB_application_reinterpreted': False,
               'claims': {name: False for name in FALSE_CLAIMS}}

    def validate(stage, record):
        require(record['timed_out'] is False and record['native_wait_completed'] is True and
                type(record['returncode']) is int, 'no completed native wait')
        label = stage.label
        if label in MODULES:
            require(record['returncode'] == 0 and not record['stdout'] and not record['stderr'],
                    'new controller module compilation failed: ' + label)
            return {'kind': 'compiled', 'module': label, 'source_sha256': sha(proof_sources[label])}
        if label.endswith('_resolution'):
            module = label.removesuffix('_resolution')
            return {'kind': 'import_resolution', **_resolve(record, module, record['workspace'],
                                                            environment['init_module']['path'])}
        if label == POSITIVE:
            require(record['returncode'] == 0 and not record['stderr'], 'positive controller certificate failed')
            return {'kind': 'positive_certificate', 'theorem_axioms': parse_audits(record['stdout'])}
        validate_negative(label, proof_sources[label], record['stdout'], record['stderr'], record['returncode'])
        return {'kind': 'intended_negative_rejection', 'label': label, 'source_sha256': sha(proof_sources[label])}

    return {'plan_context': context, 'stages': tuple(stages), 'input_files': inputs,
            'expected_input_sha256': expected, 'workspace_files': fixed,
            'environment': environment['environment_template'], 'cwd': Path(environment['cwd']),
            'validate_result': validate, 'max_completed_seconds': 14400}


def restore_validator(config):
    def validate(workspace: Path, artifacts: dict):
        require(type(artifacts) is dict and set(artifacts) <= {module + '.olean' for module in MODULES},
                'unexpected restored controller artifact')
        for name, item in artifacts.items():
            raw = checkpoints._read(workspace / name)
            require(type(item) is dict and item.get('sha256') == sha(raw) and item.get('bytes') == len(raw),
                    'restored controller object bytes differ before import probe')
        env = {k: value.replace('{workspace}', str(workspace)) for k, value in config['environment'].items()}
        lean = config['stages'][0].argv[0]; commands = []
        for module in MODULES:
            if module + '.olean' not in artifacts:
                continue
            argv = [lean, *DIRECT_FLAGS, '--root=' + str(workspace), '--deps',
                    str(workspace / ('Probe' + module + '.lean'))]
            command = _command(argv, config['cwd'], env, 120)
            command.update(module=module, workspace=str(workspace), source_sha256=sha(config['workspace_files']['Probe' + module + '.lean']))
            command['resolution'] = _resolve(command, module, str(workspace),
                                             config['plan_context']['init_module']['path'])
            commands.append(command)
        return {'schema': 'rcp-rclm.phase17ac.restored-import-preflight.v1', 'commands': commands,
                'artifacts_sha256': {name: item['sha256'] for name, item in artifacts.items()},
                'objects_recompiled': False}
    return validate


def validate_lineage(manifest: dict, config: dict, *, require_complete=True) -> dict:
    """Check AC semantics after ``checkpoints.verify_manifest`` reopened bytes.

    The generic verifier supplies the external manifest anchor, native-result
    and exact raw-log checks. This layer additionally reconstructs every saved
    restore probe. It is not a substitute for that byte-level verification.
    """
    plan = checkpoints._configuration(**{key: value for key, value in config.items()
                                        if key != 'validate_result'})
    plan_hash = sha(checkpoints._canonical(plan))
    require(type(manifest) is dict and manifest['schema'] == checkpoints.SCHEMA and
            manifest['status'] == 'completed' and manifest['plan'] == plan and
            manifest['plan_sha256'] == plan_hash, 'AC trusted stage plan differs')
    steps = manifest['steps']; stages = config['stages']; prior = {}
    require(type(steps) is list and 0 < len(steps) <= len(stages) and
            (not require_complete or len(steps) == len(stages)), 'AC formal lineage is incomplete or overlong')
    require([stage.label for stage in stages] ==
            [label for module in MODULES for label in (module, module + '_resolution')] + [POSITIVE, *NEGATIVES],
            'AC fixed stage sequence differs')
    audits = {}; rejected = []; previous = None; elapsed_ns = 0; producers = set()
    for index, step in enumerate(steps):
        stage = stages[index]
        require(type(step['index']) is int and step['index'] == index and step['label'] == stage.label and
                step['plan_sha256'] == plan_hash and step['previous_step_sha256'] == previous,
                'AC completed stage prefix or ancestry differs')
        producer = step['producer_invocation']
        require(type(producer) is str and re.fullmatch(r'[0-9a-f]{32}', producer) and producer not in producers,
                'AC original stage producer missing or repeated')
        producers.add(producer)
        main = step['command']; workspace = main['workspace']
        require(_identity(workspace).endswith('/' + producer + '/workspace') and
                type(main['elapsed_ns']) is int and main['elapsed_ns'] >= 0 and
                type(step['active_elapsed_ns']) is int and step['active_elapsed_ns'] >= main['elapsed_ns'],
                'AC producer workspace or selected-lineage duration differs')
        restored_ns = 0
        if index == 0:
            require(step['restore_receipt'] is None, 'initial stage cannot claim an inherited-prefix probe')
        else:
            receipt = step['restore_receipt']
            require(type(receipt) is dict and set(receipt) == {'schema', 'commands', 'artifacts_sha256', 'objects_recompiled'} and
                    receipt['schema'] == 'rcp-rclm.phase17ac.restored-import-preflight.v1' and
                    receipt['objects_recompiled'] is False and
                    receipt['artifacts_sha256'] == {name: item['sha256'] for name, item in prior.items()},
                    'restored artifact preflight scope differs')
            modules = [m for m in MODULES if m + '.olean' in prior]
            require(type(receipt['commands']) is list and
                    [cmd['module'] for cmd in receipt['commands']] == modules,
                    'restored import preflight inventory differs')
            for module, command in zip(modules, receipt['commands'], strict=True):
                _log_record(command, timeout_seconds=120,
                            extra_fields=('module', 'workspace', 'source_sha256', 'resolution'))
                expected = [stages[0].argv[0], *DIRECT_FLAGS, '--root=' + workspace, '--deps',
                            workspace.rstrip('/\\') + '/Probe' + module + '.lean']
                require(len(command['argv']) == len(expected) and
                        all(_identity(a) == _identity(b) if index in (0, 5) else a == b
                            for index, (a, b) in enumerate(zip(command['argv'], expected, strict=True))) and
                        command['cwd'] == str(config['cwd']) == main['cwd'] and command['workspace'] == workspace and
                        command['environment_sha256'] == main['environment_sha256'] ==
                        sha(_environment_bytes({key: value.replace('{workspace}', workspace)
                                                for key, value in config['environment'].items()})) and
                        command['source_sha256'] == sha(config['workspace_files']['Probe' + module + '.lean']),
                        'restored import command binding differs')
                require(command['resolution'] == _resolve(command, module, workspace,
                                                          config['plan_context']['init_module']['path']),
                        'restored import evidence differs')
                restored_ns += command['elapsed_ns']
        require(main['elapsed_ns'] + restored_ns <= step['active_elapsed_ns'],
                'restored import command duration is missing from selected-lineage accounting')
        require(type(step['artifacts']) is dict and set(step['artifacts']) == set(stage.artifact_names),
                'AC stage artifact set differs')
        for item in step['artifacts'].values():
            require(type(item) is dict and set(item) == {'bytes', 'sha256', 'producer_invocation'} and
                    _digest(item['sha256']) and type(item['bytes']) is int and item['bytes'] > 0 and
                    item['producer_invocation'] == producer, 'AC compiled object attribution differs')
        prior.update(step['artifacts'])
        if stage.label == POSITIVE:
            audits = step['semantic_receipt']['theorem_axioms']
            require(type(audits) is dict and set(audits) == set(NAMES) and
                    all(type(names) is list and len(names) == len(set(names)) and
                        all(type(name) is str and name in pinned.ALLOWED_AXIOMS for name in names)
                        for names in audits.values()), 'AC named theorem receipt differs')
        if stage.label in NEGATIVES:
            rejected.append(stage.label)
        previous = sha(checkpoints._canonical(step)); elapsed_ns += step['active_elapsed_ns']
    require(manifest['artifacts'] == prior and manifest['invocation_id'] == steps[-1]['producer_invocation'] and
            manifest['completed_lineage_active_ns'] == elapsed_ns and
            elapsed_ns <= config['max_completed_seconds'] * 1_000_000_000 and
            manifest['complete_resource_accounting'] is False and
            manifest['unresolved_observation_scope'] == 'explicit references only; no unseen outcome inferred',
            'AC selected lineage result or resource scope differs')
    refs = manifest['unresolved_invocations']
    require(type(refs) is list and refs == sorted(set(refs)) and
            all(type(ref) is str and re.fullmatch(r'[0-9a-f]{32}', ref) and ref not in producers for ref in refs),
            'AC unresolved invocation references differ')
    return {'schema': SCHEMA, 'status': 'passed' if len(steps) == len(stages) else 'incomplete',
            'completed_stages': len(steps), 'planned_stages': len(stages),
            'compiled_modules': [m for m in MODULES if m + '.olean' in manifest['artifacts']],
            'theorem_axioms': audits, 'negative_controls_rejected': rejected,
            'controller_protocol_checked': len(steps) == len(stages),
            'bounded_search_exhaustion_checked': len(steps) == len(stages),
            'compilation_lineage': 'explicit completed-stage parents; original producer attribution retained',
            'unresolved_invocations': manifest['unresolved_invocations'],
            'claims': {name: False for name in FALSE_CLAIMS}}
