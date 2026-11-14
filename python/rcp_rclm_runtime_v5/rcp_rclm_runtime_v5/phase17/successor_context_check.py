"""Phase17AD pinned successor-context checks using the unchanged AC stage runner.

The environment capture and byte-level continuation mechanism retain AC's
reviewed contract. This additive validator binds AD's exact source, five module
inventory, positive theorem names and designated semantic rejection controls.
"""
from __future__ import annotations
from pathlib import Path
import re
from . import lean_frontier_gate as pinned
from . import compilation_checkpoint as checkpoints
from .controller_continuation_check import (
    capture_environment, verify_environment, DIRECT_FLAGS, _identity, _digest,
    _command, _log_record, _environment_bytes, source_paths as _ac_source_paths,
)
from .successor_context import require, sha, FALSE_CLAIMS
from .successor_context_lean import MODULES, POSITIVE, NEGATIVES, NAMES, parse_audits, validate_negative

SCHEMA = 'rcp-rclm.phase17ad.successor-context-lean.v1'


def source_paths(root: Path) -> list[str]:
    names = set(_ac_source_paths(root))
    names.update(path.relative_to(root).as_posix() for path in
                 (root / 'python/rcp_rclm_runtime_v5/tests_phase17ad').glob('test_*.py'))
    names.add('docs/executable_core_v5/PHASE_17_SUCCESSOR_CONTEXT.md')
    return sorted(names)


def source_snapshot(root: Path) -> dict:
    return {name: sha(checkpoints._read(root / name)) for name in source_paths(root)}


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
            'exact generated successor-context proof-source inventory required')
    require(source_snapshot(source_root) == source_hashes, 'AD source inventory changed')
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
               'generic_module_count': len(MODULES), 'old_application_reinterpreted': False,
               'claims': {name: False for name in FALSE_CLAIMS}}

    def validate(stage, record):
        require(record['timed_out'] is False and record['native_wait_completed'] is True and
                type(record['returncode']) is int, 'no completed native wait')
        label = stage.label
        if label in MODULES:
            require(record['returncode'] == 0 and not record['stdout'] and not record['stderr'],
                    'new successor-context module compilation failed: ' + label)
            return {'kind': 'compiled', 'module': label, 'source_sha256': sha(proof_sources[label])}
        if label.endswith('_resolution'):
            module = label.removesuffix('_resolution')
            return {'kind': 'import_resolution', **_resolve(record, module, record['workspace'],
                                                            environment['init_module']['path'])}
        if label == POSITIVE:
            require(record['returncode'] == 0 and not record['stderr'], 'positive successor-context certificate failed')
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
                'unexpected restored successor-context artifact')
        for name, item in artifacts.items():
            raw = checkpoints._read(workspace / name)
            require(type(item) is dict and item.get('sha256') == sha(raw) and item.get('bytes') == len(raw),
                    'restored successor-context object bytes differ before import probe')
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
        return {'schema': 'rcp-rclm.phase17ad.restored-import-preflight.v1', 'commands': commands,
                'artifacts_sha256': {name: item['sha256'] for name, item in artifacts.items()},
                'objects_recompiled': False}
    return validate


def validate_lineage(manifest: dict, config: dict, *, require_complete=True) -> dict:
    """Check AD semantics after ``checkpoints.verify_manifest`` reopened bytes.

    The generic verifier supplies the external manifest anchor, native-result
    and exact raw-log checks. This layer additionally reconstructs every saved
    restore probe. It is not a substitute for that byte-level verification.
    """
    plan = checkpoints._configuration(**{key: value for key, value in config.items()
                                        if key != 'validate_result'})
    plan_hash = sha(checkpoints._canonical(plan))
    require(type(manifest) is dict and manifest['schema'] == checkpoints.SCHEMA and
            manifest['status'] == 'completed' and manifest['plan'] == plan and
            manifest['plan_sha256'] == plan_hash, 'AD trusted stage plan differs')
    steps = manifest['steps']; stages = config['stages']; prior = {}
    require(type(steps) is list and 0 < len(steps) <= len(stages) and
            (not require_complete or len(steps) == len(stages)), 'AD formal lineage is incomplete or overlong')
    require([stage.label for stage in stages] ==
            [label for module in MODULES for label in (module, module + '_resolution')] + [POSITIVE, *NEGATIVES],
            'AD fixed stage sequence differs')
    audits = {}; rejected = []; previous = None; elapsed_ns = 0; producers = set()
    for index, step in enumerate(steps):
        stage = stages[index]
        require(type(step['index']) is int and step['index'] == index and step['label'] == stage.label and
                step['plan_sha256'] == plan_hash and step['previous_step_sha256'] == previous,
                'AD completed stage prefix or ancestry differs')
        producer = step['producer_invocation']
        require(type(producer) is str and re.fullmatch(r'[0-9a-f]{32}', producer) and producer not in producers,
                'AD original stage producer missing or repeated')
        producers.add(producer)
        main = step['command']; workspace = main['workspace']
        require(_identity(workspace).endswith('/' + producer + '/workspace') and
                type(main['elapsed_ns']) is int and main['elapsed_ns'] >= 0 and
                type(step['active_elapsed_ns']) is int and step['active_elapsed_ns'] >= main['elapsed_ns'],
                'AD producer workspace or selected-lineage duration differs')
        restored_ns = 0
        if index == 0:
            require(step['restore_receipt'] is None, 'initial stage cannot claim an inherited-prefix probe')
        else:
            receipt = step['restore_receipt']
            require(type(receipt) is dict and set(receipt) == {'schema', 'commands', 'artifacts_sha256', 'objects_recompiled'} and
                    receipt['schema'] == 'rcp-rclm.phase17ad.restored-import-preflight.v1' and
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
                'AD stage artifact set differs')
        for item in step['artifacts'].values():
            require(type(item) is dict and set(item) == {'bytes', 'sha256', 'producer_invocation'} and
                    _digest(item['sha256']) and type(item['bytes']) is int and item['bytes'] > 0 and
                    item['producer_invocation'] == producer, 'AD compiled object attribution differs')
        prior.update(step['artifacts'])
        if stage.label == POSITIVE:
            audits = step['semantic_receipt']['theorem_axioms']
            require(type(audits) is dict and set(audits) == set(NAMES) and
                    all(type(names) is list and len(names) == len(set(names)) and
                        all(type(name) is str and name in pinned.ALLOWED_AXIOMS for name in names)
                        for names in audits.values()), 'AD named theorem receipt differs')
        if stage.label in NEGATIVES:
            rejected.append(stage.label)
        previous = sha(checkpoints._canonical(step)); elapsed_ns += step['active_elapsed_ns']
    require(manifest['artifacts'] == prior and manifest['invocation_id'] == steps[-1]['producer_invocation'] and
            manifest['completed_lineage_active_ns'] == elapsed_ns and
            elapsed_ns <= config['max_completed_seconds'] * 1_000_000_000 and
            manifest['complete_resource_accounting'] is False and
            manifest['unresolved_observation_scope'] == 'explicit references only; no unseen outcome inferred',
            'AD selected lineage result or resource scope differs')
    refs = manifest['unresolved_invocations']
    require(type(refs) is list and refs == sorted(set(refs)) and
            all(type(ref) is str and re.fullmatch(r'[0-9a-f]{32}', ref) and ref not in producers for ref in refs),
            'AD unresolved invocation references differ')
    return {'schema': SCHEMA, 'status': 'passed' if len(steps) == len(stages) else 'incomplete',
            'completed_stages': len(steps), 'planned_stages': len(stages),
            'compiled_modules': [m for m in MODULES if m + '.olean' in manifest['artifacts']],
            'theorem_axioms': audits, 'negative_controls_rejected': rejected,
            'successor_context_transport_checked': len(steps) == len(stages),
            'prospective_successor_context_checked': len(steps) == len(stages),
            'compilation_lineage': 'explicit completed-stage parents; original producer attribution retained',
            'unresolved_invocations': manifest['unresolved_invocations'],
            'claims': {name: False for name in FALSE_CLAIMS}}
