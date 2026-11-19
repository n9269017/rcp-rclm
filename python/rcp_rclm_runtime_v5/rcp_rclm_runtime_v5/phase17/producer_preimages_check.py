"""Pinned Lean checking of producer preimages and seeded grammar composition.

Q, R, S, T, U and V are freshly compiled into the same private import directory. Saved
command records support reproducibility; they are not physical attestation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from . import lean_frontier_gate as gate
from .sparse_refinement_check import _negative, _path_identity, _digest
from .producer_preimages import PreparedProducerPreimages, FALSE_CLAIMS, require, canonical, sha, read_retained

DEPENDENCIES = ('Phase17QDependency', 'Phase17RDependency', 'Phase17SDependency', 'Phase17TDependency', 'Phase17UDependency', 'Phase17VDependency')
DEPENDENCY_COUNT = len(DEPENDENCIES)
RESOLUTION_START = 1 + DEPENDENCY_COUNT
CASE_START = 1 + 2 * DEPENDENCY_COUNT
SCHEMA = 'rcp-rclm.phase17w.producer-preimages-lean.v1'


def parse_audits(text: str) -> dict:
    from .producer_preimages_lean import NAMES
    require(type(text) is str, 'producer preimages audit output must be text')
    cursor, result = 0, {}
    for name in NAMES:
        match = re.compile(r"'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*", re.S).match(text, cursor)
        require(match is not None, 'exact producer preimages audit sequence required')
        result[name] = gate._axioms(match[0], name)
        cursor = match.end()
    require(cursor == len(text), 'unexpected producer preimages audit output')
    return result


def _resolved_module(command: dict, name: str, expected: str) -> str:
    require(command['returncode'] == 0 and command['stderr'] == '', 'producer preimages dependency resolution failed')
    paths = command['stdout'].splitlines()
    names, identities = [], []
    for path in paths:
        normalized = _path_identity(path)
        identities.append(normalized)
        leaf = normalized.rsplit('/', 1)[-1]
        if re.match(r'^[a-z]:/', normalized):
            leaf = next((known for known in ('Init.olean', name + '.olean')
                         if leaf == known.casefold()), leaf)
        names.append(leaf)
    require(len(paths) == 3 and names.count('Init.olean') == 2 and names.count(name + '.olean') == 1,
            'unexpected producer preimages import inventory')
    init = [value for value, leaf in zip(identities, names, strict=True) if leaf == 'Init.olean']
    require(init[0] == init[1], 'conflicting Init import paths')
    resolved = paths[names.index(name + '.olean')]
    require(_path_identity(resolved) == _path_identity(expected),
            'producer preimages dependency resolved outside the same-run directory')
    return resolved


def _command_paths(commands: list[dict], executables: dict, labels: tuple) -> None:
    """Bind each saved invocation to its own source and the same import root."""
    tools = {}
    for path in executables:
        normalized = _path_identity(path)
        leaf = normalized.rsplit('/', 1)[-1]
        if leaf.endswith('.exe'):
            leaf = leaf[:-4]
        require(leaf in ('lean', 'lake', 'git') and leaf not in tools,
                'producer preimages tool identities must be exactly Lean, Lake and Git')
        tools[leaf] = normalized
    require(set(tools) == {'lean', 'lake', 'git'}, 'missing producer preimages tool identity')
    argv = commands[0].get('argv')
    require(type(argv) is list and len(argv) == 2 and
            _path_identity(argv[0]) == tools['lean'] and argv[1] == '--version',
            'producer preimages version command differs from recorded Lean')
    first = commands[1].get('argv')
    require(type(first) is list and len(first) == 9 and type(first[5]) is str and
            first[5].startswith('--root='), 'producer preimages compile root missing')
    folder = first[5][len('--root='):]
    folder_identity = _path_identity(folder)

    def expected_path(value, leaf):
        require(_path_identity(value) == _path_identity(folder.rstrip('/\\') + '/' + leaf),
                'producer preimages command path differs from exact source/output')

    def prefix(command, size):
        args = command.get('argv')
        require(type(args) is list and len(args) == size and
                all(type(item) is str for item in args), 'producer preimages command shape differs')
        require(_path_identity(args[0]) == tools['lake'] and args[1:4] == ['--keep-toolchain', '--no-cache', 'env'] and
                _path_identity(args[4]) == tools['lean'] and args[5].startswith('--root=') and
                _path_identity(args[5][len('--root='):]) == folder_identity,
                'producer preimages command tools/root differ')
        return args

    for index, name in enumerate(DEPENDENCIES):
        args = prefix(commands[1 + index], 9)
        require(args[6] == '-o', 'producer preimages dependency output option differs')
        expected_path(args[7], name + '.olean')
        expected_path(args[8], name + '.lean')
        client = DEPENDENCIES[index + 1] if index + 1 < DEPENDENCY_COUNT else labels[0]
        args = prefix(commands[RESOLUTION_START + index], 8)
        require(args[6] == '--deps', 'producer preimages dependency resolution option differs')
        expected_path(args[7], client + '.lean')
    for label, command in zip(labels, commands[CASE_START:], strict=True):
        args = prefix(command, 7)
        expected_path(args[6], label + '.lean')


def validate_result(result: dict, sources: dict[str, bytes], packet_sha256: str) -> None:
    """Check saved sources/logs without compiling, preparing, or executing argv."""
    from .producer_preimages_lean import NAMES, LABELS
    fields = {'schema', 'status', 'packet_sha256', 'commands', 'theorem_axioms',
              'negative_controls_rejected', 'new_named_audits', 'grammar_parameters_from_seed_checked',
              'producer_hash_preimages_checked', 'claims', 'source_sha256', 'executable_sha256',
              'dependency_modules', 'trusted_import_cache_assumption',
              'byte_capture_remains_external', 'digest_authenticity_remains_external',
              'general_planner_equivalence', 'general_json_parser_equivalence', 'python_execution_remains_external',
              'public_hash_computation_remains_external', 'selected_hash_preimages_checked', 'selected_grammar_parameter_derivation_checked', 'general_grammar_parameter_derivation_remains_external',
              'sha256_computation_remains_external',
              'full_transformer_equivalence', 'old_proof_campaigns_rerun'}
    require(type(result) is dict and set(result) == fields and result['schema'] == SCHEMA and
            result['status'] == 'passed', 'producer preimages Lean gate did not pass')
    require(list(sources) == [*DEPENDENCIES, *LABELS] and
            all(type(raw) is bytes and raw for raw in sources.values()), 'exact producer preimages sources required')
    require(_digest(packet_sha256) and result['packet_sha256'] == packet_sha256 and
            result['source_sha256'] == {name: sha(raw) for name, raw in sources.items()},
            'executed producer preimages sources differ')
    require(result['negative_controls_rejected'] == list(LABELS[1:]) and
            type(result['new_named_audits']) is int and result['new_named_audits'] == len(NAMES),
            'producer preimages theorem/control inventory differs')
    require(result['grammar_parameters_from_seed_checked'] is True and result['producer_hash_preimages_checked'] is True,
            'producer preimages proof scope differs')
    require(canonical(result['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'producer preimages result escalates full-root authority')
    require(result['trusted_import_cache_assumption'] is True and
            result['byte_capture_remains_external'] is True and
            result['digest_authenticity_remains_external'] is True and
            result['general_planner_equivalence'] is False and
            result['general_json_parser_equivalence'] is False and
            result['public_hash_computation_remains_external'] is True and
            result['selected_hash_preimages_checked'] is True and
            result['selected_grammar_parameter_derivation_checked'] is True and
            result['general_grammar_parameter_derivation_remains_external'] is True and
            result['sha256_computation_remains_external'] is True and
            result['python_execution_remains_external'] is True and
            result['full_transformer_equivalence'] is False and result['old_proof_campaigns_rerun'] is False,
            'producer preimages trust/scope record differs')
    exes = result['executable_sha256']
    require(type(exes) is dict and len(exes) == 3 and all(type(name) is str and _digest(value)
            for name, value in exes.items()), 'producer preimages executable inventory differs')
    modules = result['dependency_modules']
    require(type(modules) is dict and set(modules) == set(DEPENDENCIES),
            'exactly six fresh producer preimages dependencies required')
    commands = result['commands']
    require(type(commands) is list and len(commands) == CASE_START + len(LABELS), 'producer preimages command inventory differs')
    for command in commands:
        require(type(command) is dict and type(command.get('returncode')) is int and
                type(command.get('stdout')) is str and type(command.get('stderr')) is str,
                'malformed producer preimages command')
        require(command['stdout_sha256'] == sha(command['stdout'].encode('utf-8')) and
                command['stderr_sha256'] == sha(command['stderr'].encode('utf-8')), 'producer preimages log hashes differ')
    _command_paths(commands, exes, LABELS)
    version = commands[0]
    require(version['returncode'] == 0 and version['stderr'] == '' and
            re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']) is not None, 'wrong pinned Lean')
    for index, name in enumerate(DEPENDENCIES):
        dependency = modules[name]
        require(type(dependency) is dict and set(dependency) == {'name', 'source_sha256', 'artifacts_sha256',
                'resolved_module_path', 'compiled_in_this_run', 'prior_success_report_used_as_proof'} and
                dependency['name'] == name and dependency['source_sha256'] == sha(sources[name]) and
                dependency['compiled_in_this_run'] is True and
                dependency['prior_success_report_used_as_proof'] is False, 'fresh producer preimages dependency required')
        artifacts = dependency['artifacts_sha256']
        require(type(artifacts) is dict and name + '.olean' in artifacts and all(
            item in {name + suffix for suffix in ('.olean', '.olean.private', '.olean.server', '.ir')} and
            _digest(value) for item, value in artifacts.items()), 'producer preimages dependency artifact differs')
        compiled = commands[1 + index]
        require(compiled.get('label') == name and compiled.get('source_sha256') == sha(sources[name]) and
                compiled['returncode'] == 0 and compiled['stdout'] == '' and compiled['stderr'] == '' and
                compiled.get('output_artifacts_sha256') == artifacts, 'producer preimages dependency compilation differs')
        argv = compiled.get('argv')
        require(type(argv) is list and len(argv) >= 4 and argv[-3] == '-o', 'dependency output argument missing')
        resolution = commands[RESOLUTION_START + index]
        client = DEPENDENCIES[index + 1] if index + 1 < DEPENDENCY_COUNT else LABELS[0]
        require(resolution.get('label') == name + '_resolution' and
                resolution.get('source_sha256') == sha(sources[client]) and
                type(resolution.get('argv')) is list and len(resolution['argv']) >= 3 and
                resolution['argv'][-2] == '--deps', 'producer preimages resolution command differs')
        resolved = _resolved_module(resolution, name, argv[-2])
        require(dependency['resolved_module_path'] == resolved, 'recorded producer preimages import path differs')
    for label, command in zip(LABELS, commands[CASE_START:], strict=True):
        require(command.get('label') == label and command.get('source_sha256') == sha(sources[label]),
                'producer preimages command/source binding differs')
        if label == LABELS[0]:
            require(command['returncode'] == 0 and command['stderr'] == '', 'positive producer preimages certificate rejected')
            require(result['theorem_axioms'] == parse_audits(command['stdout']), 'producer preimages axiom report differs')
        else:
            _negative(command)


def _artifacts(folder: Path, name: str) -> dict[str, str]:
    result = {}
    for suffix in ('.olean', '.olean.private', '.olean.server', '.ir'):
        path = folder / (name + suffix)
        if path.exists():
            raw = gate._read_regular(path)
            require(bool(raw), 'empty producer preimages dependency artifact')
            result[path.name] = sha(raw)
    require(name + '.olean' in result, 'fresh producer preimages dependency not emitted')
    return result


def check(prepared: PreparedProducerPreimages, *, source_root: Path, lean_workspace: Path,
          toolchain_root: Path | None = None, progress_path: Path | None = None) -> dict:
    from .producer_preimages_lean import generated_sources, NAMES, LABELS
    require(type(prepared) is PreparedProducerPreimages, 'exact producer preimages packet required')
    result = {'schema': SCHEMA, 'status': 'blocked', 'packet_sha256': sha(prepared.packet_bytes),
              'commands': [], 'theorem_axioms': {}, 'negative_controls_rejected': [],
              'new_named_audits': len(NAMES), 'grammar_parameters_from_seed_checked': False,
              'producer_hash_preimages_checked': False, 'claims': {name: False for name in FALSE_CLAIMS}}

    def checkpoint():
        if progress_path is not None:
            require(not progress_path.is_symlink(), 'linked producer preimages progress output')
            progress_path.write_bytes((json.dumps(result, sort_keys=True, indent=2) + '\n').encode())

    try:
        sources = generated_sources(prepared, source_root=source_root)
        require(list(sources) == [*DEPENDENCIES, *LABELS], 'unexpected generated producer preimages modules')
        templates = {p.relative_to(source_root).as_posix(): sha(gate._read_regular(p))
                     for p in sorted((source_root / 'lean/phase17_bridge').glob('*.lean'))}
        retained = read_retained(source_root)
        roots = gate.root_source_fingerprint(lean_workspace)
        require({name: item['canonical_sha256'] for name, item in roots.items()} ==
                {name: item['canonical_sha256'] for name, item in gate.root_source_fingerprint(source_root).items()},
                'pinned producer preimages root mismatch')
        deps = gate._dependency_state(lean_workspace)
        tool = gate.resolve_toolchain(toolchain_root)
        env, git = gate._lean_environment(tool)
        suffix = '.exe' if os.name == 'nt' else ''
        lean, lake = tool / 'bin' / ('lean' + suffix), tool / 'bin' / ('lake' + suffix)
        exes = {str(path): sha(gate._read_regular(path)) for path in (lean, lake, git)}
        version = gate._process([str(lean), '--version'], lean_workspace / gate.ROOT_PROJECT, env, timeout=30)
        result['commands'].append(version)
        checkpoint()
        require(version['returncode'] == 0 and not version['stderr'] and
                re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']), 'wrong pinned Lean')
        result['status'] = 'rejected'
        with tempfile.TemporaryDirectory(prefix='r17w-') as tmp:
            folder = Path(tmp).resolve(strict=True)
            for name, raw in sources.items():
                (folder / (name + '.lean')).write_bytes(raw)
            env = dict(env, LEAN_PATH=str(folder))
            modules = {}

            def unchanged():
                require(all((folder / (name + '.lean')).read_bytes() == raw for name, raw in sources.items()),
                        'producer preimages source changed during Lean checking')
                for name, module in modules.items():
                    require(_artifacts(folder, name) == module['artifacts_sha256'],
                            'same-run producer preimages dependency changed')

            for name in DEPENDENCIES:
                compiled = gate._process([str(lake), '--keep-toolchain', '--no-cache', 'env', str(lean),
                    '--root=' + str(folder), '-o', str(folder / (name + '.olean')), str(folder / (name + '.lean'))],
                    lean_workspace / gate.ROOT_PROJECT, env, timeout=1800)
                compiled.update(label=name, source_sha256=sha(sources[name]))
                result['commands'].append(compiled)
                checkpoint()
                require(compiled['returncode'] == 0 and compiled['stdout'] == '' and compiled['stderr'] == '',
                        'fresh producer preimages dependency did not compile: ' + name)
                artifacts = _artifacts(folder, name)
                compiled['output_artifacts_sha256'] = artifacts
                modules[name] = {'name': name, 'source_sha256': sha(sources[name]),
                                 'artifacts_sha256': artifacts, 'compiled_in_this_run': True,
                                 'prior_success_report_used_as_proof': False}
                result['dependency_modules'] = modules
                unchanged()
                checkpoint()
            for name, client in zip(DEPENDENCIES, (*DEPENDENCIES[1:], LABELS[0]), strict=True):
                resolution = gate._process([str(lake), '--keep-toolchain', '--no-cache', 'env', str(lean),
                    '--root=' + str(folder), '--deps', str(folder / (client + '.lean'))],
                    lean_workspace / gate.ROOT_PROJECT, env, timeout=120)
                resolution.update(label=name + '_resolution', source_sha256=sha(sources[client]))
                result['commands'].append(resolution)
                checkpoint()
                modules[name]['resolved_module_path'] = _resolved_module(resolution, name, str(folder / (name + '.olean')))
                unchanged()
                checkpoint()
            audits = {}
            for label in LABELS:
                command = gate._process([str(lake), '--keep-toolchain', '--no-cache', 'env', str(lean),
                    '--root=' + str(folder), str(folder / (label + '.lean'))],
                    lean_workspace / gate.ROOT_PROJECT, env, timeout=1800)
                command.update(label=label, source_sha256=sha(sources[label]))
                result['commands'].append(command)
                checkpoint()
                if label == LABELS[0]:
                    require(command['returncode'] == 0 and command['stderr'] == '', 'producer preimages certificate rejected')
                    audits = parse_audits(command['stdout'])
                else:
                    _negative(command)
                    result['negative_controls_rejected'].append(label)
                unchanged()
                checkpoint()
        require(roots == gate.root_source_fingerprint(lean_workspace) and deps == gate._dependency_state(lean_workspace),
                'root/dependency changed during W checking')
        require(exes == {name: sha(gate._read_regular(Path(name))) for name in exes} and
                templates == {name: sha(gate._read_regular(source_root / name)) for name in templates} and
                retained == read_retained(source_root), 'tool/template/retained input changed during W checking')
        result.update(status='passed', theorem_axioms=audits, grammar_parameters_from_seed_checked=True,
                      producer_hash_preimages_checked=True, source_sha256={name: sha(raw) for name, raw in sources.items()},
                      executable_sha256=exes, dependency_modules=modules, trusted_import_cache_assumption=True,
                      byte_capture_remains_external=True, digest_authenticity_remains_external=True,
                      general_planner_equivalence=False, general_json_parser_equivalence=False,
                      python_execution_remains_external=True,
                      public_hash_computation_remains_external=True, selected_hash_preimages_checked=True,
                      selected_grammar_parameter_derivation_checked=True,
                      general_grammar_parameter_derivation_remains_external=True,
                      sha256_computation_remains_external=True,
                      full_transformer_equivalence=False, old_proof_campaigns_rerun=False)
        validate_result(result, sources, sha(prepared.packet_bytes))
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result['status'] = 'blocked' if result['status'] == 'blocked' else 'rejected'
        result['failure'] = {'type': type(exc).__name__, 'reason': str(exc)}
    finally:
        checkpoint()
    return result
