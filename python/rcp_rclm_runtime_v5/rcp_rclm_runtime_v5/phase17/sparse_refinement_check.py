"""Pinned Lean execution for R's byte refinement; exact logs are not attestation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
import subprocess

from . import lean_frontier_gate as gate
from .sparse_refinement import (PreparedSparseRefinement, FALSE_CLAIMS, require,
                                canonical, sha, read_retained)

COMMON = 'Phase17QDependency'
SCHEMA = 'rcp-rclm.phase17r.sparse-byte-refinement-lean.v1'


def parse_audits(text: str) -> dict:
    from .sparse_refinement_lean import NAMES
    require(type(text) is str, 'audit output must be text')
    cursor, result = 0, {}
    for name in NAMES:
        match = re.compile(r"'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*", re.S).match(text, cursor)
        require(match is not None, 'exact sparse-refinement audit sequence required')
        result[name] = gate._axioms(match[0], name)
        cursor = match.end()
    require(cursor == len(text), 'unexpected sparse-refinement audit output')
    return result


def _negative(command: dict) -> None:
    require(type(command['returncode']) is int and command['returncode'] == 1 and
            command['stderr'] == '', 'negative refinement control exit/stderr differs')
    require(type(command['stdout']) is str, 'negative refinement output must be text')
    pattern = re.compile(r'(?m)^(?:[^\n]*\.lean:\d+:\d+:\s*)?'
                         r'error: Tactic `decide` proved that the proposition\n'
                         r'[\s\S]*?^is false\n')
    rest, count = pattern.subn('', command['stdout'])
    require(count > 0 and len(re.findall(r'(?m)^[^\n]*\berror:', command['stdout'])) == count,
            'negative refinement control did not reject only false propositions')
    require(not rest.strip(), 'negative refinement control has unrelated output')


def _digest(value: object) -> bool:
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _path_identity(value: str) -> str:
    require(type(value) is str and value and '\n' not in value and '\r' not in value,
            'invalid dependency module path')
    normalized = value.replace('\\', '/')
    if re.match(r'^[A-Za-z]:/', normalized):
        return normalized.casefold()
    require(normalized.startswith('/'), 'absolute dependency module path required')
    return normalized


def _resolved_module(command: dict, expected: str) -> str:
    require(command['returncode'] == 0 and command['stderr'] == '', 'dependency resolution failed')
    paths = command['stdout'].splitlines()
    names = []
    for path in paths:
        normalized = _path_identity(path)
        name = normalized.rsplit('/', 1)[-1]
        if re.match(r'^[a-z]:/', normalized):
            name = next((known for known in ('Init.olean', COMMON + '.olean')
                         if name == known.casefold()), name)
        names.append(name)
    require(len(paths) == 3 and names.count('Init.olean') == 2 and names.count(COMMON + '.olean') == 1,
            'unexpected direct import dependency inventory')
    resolved = paths[names.index(COMMON + '.olean')]
    require(_path_identity(resolved) == _path_identity(expected),
            'Q dependency resolved outside the fresh compilation directory')
    return resolved


def validate_result(result: dict, sources: dict[str, bytes], packet_sha256: str) -> None:
    """Validate exact source/audit/control correspondence; never execute log argv."""
    from .sparse_refinement_lean import NAMES, LABELS
    fields = {'schema', 'status', 'packet_sha256', 'commands', 'theorem_axioms',
              'negative_controls_rejected', 'new_named_audits',
              'sparse_tensor_projection_checked', 'protected_sparse_decoder_checked',
              'claims', 'source_sha256', 'executable_sha256', 'dependency_module',
              'trusted_import_cache_assumption', 'byte_capture_remains_external',
              'prompt_routing_remains_external', 'full_transformer_equivalence',
              'old_proof_campaigns_rerun'}
    require(type(result) is dict and set(result) == fields and result['schema'] == SCHEMA and
            result['status'] == 'passed', 'sparse refinement Lean gate did not pass')
    require(list(sources) == [COMMON, *LABELS] and all(type(raw) is bytes and raw for raw in sources.values()),
            'exact refinement source inventory required')
    require(_digest(packet_sha256) and result['packet_sha256'] == packet_sha256 and
            result['source_sha256'] == {name: sha(raw) for name, raw in sources.items()},
            'executed refinement sources differ')
    require(result['negative_controls_rejected'] == list(LABELS[1:]) and
            type(result['new_named_audits']) is int and result['new_named_audits'] == len(NAMES),
            'refinement theorem/control inventory differs')
    require(result['sparse_tensor_projection_checked'] is True and
            result['protected_sparse_decoder_checked'] is True, 'refinement proof scope differs')
    require(canonical(result['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'refinement result escalates full-root authority')
    require(result['trusted_import_cache_assumption'] is True and
            result['byte_capture_remains_external'] is True and
            result['prompt_routing_remains_external'] is True and
            result['full_transformer_equivalence'] is False and
            result['old_proof_campaigns_rerun'] is False, 'refinement trust/scope record differs')
    exes = result['executable_sha256']
    require(type(exes) is dict and len(exes) == 3 and all(type(name) is str and _digest(value)
            for name, value in exes.items()), 'refinement executable inventory differs')
    dependency = result['dependency_module']
    require(type(dependency) is dict and set(dependency) == {'name', 'source_sha256',
            'artifacts_sha256', 'resolved_module_path', 'compiled_in_this_run', 'prior_success_report_used_as_proof'} and
            dependency['name'] == COMMON and dependency['source_sha256'] == sha(sources[COMMON]) and
            dependency['compiled_in_this_run'] is True and
            dependency['prior_success_report_used_as_proof'] is False,
            'fresh Q dependency compilation required')
    artifacts = dependency['artifacts_sha256']
    require(type(artifacts) is dict and COMMON + '.olean' in artifacts and all(
        name in {COMMON + suffix for suffix in ('.olean', '.olean.private', '.olean.server', '.ir')} and
        _digest(value) for name, value in artifacts.items()), 'compiled dependency artifact identity differs')
    commands = result['commands']
    require(type(commands) is list and len(commands) == 3 + len(LABELS), 'refinement command inventory differs')
    for command in commands:
        require(type(command) is dict and type(command.get('returncode')) is int and
                type(command.get('stdout')) is str and type(command.get('stderr')) is str,
                'malformed refinement command')
        require(command['stdout_sha256'] == sha(command['stdout'].encode('utf-8')) and
                command['stderr_sha256'] == sha(command['stderr'].encode('utf-8')), 'refinement log hashes differ')
    version, compiled, resolution = commands[:3]
    require(version['returncode'] == 0 and version['stderr'] == '' and
            re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']) is not None,
            'wrong pinned Lean')
    require(compiled['label'] == COMMON and compiled['source_sha256'] == sha(sources[COMMON]) and
            compiled['returncode'] == 0 and compiled['stdout'] == '' and compiled['stderr'] == '' and
            compiled['output_artifacts_sha256'] == artifacts, 'common dependency compilation differs')
    require(type(compiled.get('argv')) is list and len(compiled['argv']) >= 4 and
            compiled['argv'][-3] == '-o', 'dependency output argument missing')
    require(resolution.get('label') == 'dependency_resolution' and
            resolution.get('source_sha256') == sha(sources[LABELS[0]]) and
            type(resolution.get('argv')) is list and len(resolution['argv']) >= 3 and
            resolution['argv'][-2] == '--deps', 'dependency resolution command differs')
    resolved = _resolved_module(resolution, compiled['argv'][-2])
    require(dependency['resolved_module_path'] == resolved, 'recorded resolved module path differs')
    for label, command in zip(LABELS, commands[3:], strict=True):
        require(command.get('label') == label and command.get('source_sha256') == sha(sources[label]),
                'refinement command/source binding differs')
        if label == LABELS[0]:
            require(command['returncode'] == 0 and command['stderr'] == '', 'positive byte refinement rejected')
            require(result['theorem_axioms'] == parse_audits(command['stdout']), 'refinement axiom report differs')
        else:
            _negative(command)


def _artifacts(folder: Path) -> dict[str, str]:
    result = {}
    for suffix in ('.olean', '.olean.private', '.olean.server', '.ir'):
        path = folder / (COMMON + suffix)
        if path.exists():
            raw = gate._read_regular(path)
            require(bool(raw), 'empty dependency compilation artifact')
            result[path.name] = sha(raw)
    require(COMMON + '.olean' in result, 'new dependency module was not emitted')
    return result


def check(prepared: PreparedSparseRefinement, *, source_root: Path, lean_workspace: Path,
          toolchain_root: Path | None = None, progress_path: Path | None = None) -> dict:
    from .sparse_refinement_lean import generated_sources, NAMES, LABELS
    require(type(prepared) is PreparedSparseRefinement, 'exact sparse refinement packet required')
    result = {'schema': SCHEMA, 'status': 'blocked', 'packet_sha256': sha(prepared.packet_bytes),
              'commands': [], 'theorem_axioms': {}, 'negative_controls_rejected': [],
              'new_named_audits': len(NAMES), 'sparse_tensor_projection_checked': False,
              'protected_sparse_decoder_checked': False,
              'claims': {name: False for name in FALSE_CLAIMS}}

    def checkpoint():
        if progress_path is not None:
            require(not progress_path.is_symlink(), 'linked progress output')
            progress_path.write_bytes((json.dumps(result, sort_keys=True, indent=2) + '\n').encode())

    try:
        sources = generated_sources(prepared, source_root=source_root)
        require(list(sources) == [COMMON, *LABELS], 'unexpected generated refinement modules')
        templates = {p.relative_to(source_root).as_posix(): sha(gate._read_regular(p))
                     for p in sorted((source_root / 'lean/phase17_bridge').glob('*.lean'))}
        retained = read_retained(source_root)
        roots = gate.root_source_fingerprint(lean_workspace)
        require({name: item['canonical_sha256'] for name, item in roots.items()} ==
                {name: item['canonical_sha256'] for name, item in gate.root_source_fingerprint(source_root).items()},
                'pinned refinement root mismatch')
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
        with tempfile.TemporaryDirectory(prefix='r17r-') as tmp:
            folder = Path(tmp).resolve(strict=True)
            for name, raw in sources.items():
                (folder / (name + '.lean')).write_bytes(raw)
            # The only additional import location is this newly created folder.
            # No caller-provided Lean path or previous Q success artifact enters.
            env = dict(env, LEAN_PATH=str(folder))
            common = folder / (COMMON + '.lean')
            compiled = gate._process([str(lake), '--keep-toolchain', '--no-cache', 'env', str(lean),
                '--root=' + str(folder), '-o', str(folder / (COMMON + '.olean')), str(common)],
                lean_workspace / gate.ROOT_PROJECT, env, timeout=1800)
            compiled.update(label=COMMON, source_sha256=sha(sources[COMMON]))
            result['commands'].append(compiled)
            checkpoint()
            require(compiled['returncode'] == 0 and compiled['stdout'] == '' and compiled['stderr'] == '',
                    'fresh common Q dependency did not compile')
            artifacts = _artifacts(folder)
            compiled['output_artifacts_sha256'] = artifacts
            dependency = {'name': COMMON, 'source_sha256': sha(sources[COMMON]),
                          'artifacts_sha256': artifacts, 'compiled_in_this_run': True,
                          'prior_success_report_used_as_proof': False}
            result['dependency_module'] = dependency
            checkpoint()
            resolution = gate._process([str(lake), '--keep-toolchain', '--no-cache', 'env', str(lean),
                '--root=' + str(folder), '--deps', str(folder / (LABELS[0] + '.lean'))],
                lean_workspace / gate.ROOT_PROJECT, env, timeout=60)
            resolution.update(label='dependency_resolution', source_sha256=sha(sources[LABELS[0]]))
            result['commands'].append(resolution)
            checkpoint()
            dependency['resolved_module_path'] = _resolved_module(resolution, str(folder / (COMMON + '.olean')))
            audits = {}
            for label in LABELS:
                path = folder / (label + '.lean')
                command = gate._process([str(lake), '--keep-toolchain', '--no-cache', 'env', str(lean),
                                        '--root=' + str(folder), str(path)],
                                       lean_workspace / gate.ROOT_PROJECT, env, timeout=1800)
                command.update(label=label, source_sha256=sha(sources[label]))
                result['commands'].append(command)
                checkpoint()
                if label == LABELS[0]:
                    require(command['returncode'] == 0 and command['stderr'] == '', 'byte refinement certificate rejected')
                    audits = parse_audits(command['stdout'])
                else:
                    _negative(command)
                    result['negative_controls_rejected'].append(label)
                require(all((folder / (name + '.lean')).read_bytes() == raw for name, raw in sources.items()) and
                        _artifacts(folder) == artifacts, 'refinement input or same-run dependency changed')
                checkpoint()
        require(roots == gate.root_source_fingerprint(lean_workspace) and deps == gate._dependency_state(lean_workspace),
                'root/dependency changed during R checking')
        require(exes == {name: sha(gate._read_regular(Path(name))) for name in exes} and
                templates == {name: sha(gate._read_regular(source_root / name)) for name in templates} and
                retained == read_retained(source_root), 'tool/template/retained input changed during R checking')
        result.update(status='passed', theorem_axioms=audits,
                      sparse_tensor_projection_checked=True, protected_sparse_decoder_checked=True,
                      source_sha256={name: sha(raw) for name, raw in sources.items()},
                      executable_sha256=exes, dependency_module=dependency,
                      trusted_import_cache_assumption=True, byte_capture_remains_external=True,
                      prompt_routing_remains_external=True, full_transformer_equivalence=False,
                      old_proof_campaigns_rerun=False)
        validate_result(result, sources, sha(prepared.packet_bytes))
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result['status'] = 'blocked' if result['status'] == 'blocked' else 'rejected'
        result['failure'] = {'type': type(exc).__name__, 'reason': str(exc)}
    finally:
        checkpoint()
    return result
