"""Actual pinned Lean checking for Q; retained-log validation is not attestation."""
from __future__ import annotations
import os
from pathlib import Path
import re
import subprocess
import tempfile

from . import lean_frontier_gate as gate
from .finite_kernel import PreparedFiniteKernel, FALSE_CLAIMS, require, sha, read_retained, canonical


def parse_audits(text: str) -> dict:
    from .finite_kernel_lean import NAMES
    cursor, result = 0, {}
    for name in NAMES:
        match = re.compile(r"'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*", re.S).match(text, cursor)
        require(match is not None, 'exact finite-kernel audit sequence required')
        result[name] = gate._axioms(match[0], name)
        cursor = match.end()
    require(cursor == len(text), 'unexpected finite-kernel audit output')
    return result


def _negative(command: dict) -> None:
    from .finite_kernel_lean import NAMES
    require(command['returncode'] == 1 and not command['stderr'], 'negative control exit/stderr differs')
    # Permit only explicit false-proposition errors and the exact audit suffix.
    # Lean's error recovery adds sorryAx to downstream *failed* declarations;
    # those are allowed only in these rejected controls, never in a pass.
    pattern = re.compile(r'(?m)^(?:[^\n]*\.lean:\d+:\d+:\s*)?'
                         r'error: Tactic `decide` proved that the proposition\n'
                         r'[\s\S]*?^is false\n')
    rest, count = pattern.subn('', command['stdout'])
    require(count > 0, 'negative control did not reject a false proposition')
    require(len(re.findall(r'(?m)^[^\n]*\berror:', command['stdout'])) == count,
            'negative control has an embedded unrelated error')
    cursor = 0
    for name in NAMES:
        match = re.compile(r"'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*", re.S).match(rest, cursor)
        require(match is not None, 'negative control has unrelated errors or unexpected audits')
        if match[1] is not None:
            axioms = [x.strip() for x in match[1].split(',') if x.strip()]
            require(len(axioms) == len(set(axioms)) and
                    set(axioms) <= gate.ALLOWED_AXIOMS | {'sorryAx'}, 'unexpected negative audit axiom')
        cursor = match.end()
    require(cursor == len(rest), 'negative control has unrelated trailing output')


def validate_result(result: dict, sources: dict[str, bytes], packet_sha256: str) -> None:
    """Check exact source/audit/control/log correspondence, never run log argv."""
    from .finite_kernel_lean import NAMES, LABELS
    expected_fields = {'schema', 'status', 'packet_sha256', 'commands', 'theorem_axioms',
        'negative_controls_rejected', 'new_named_audits', 'finite_observation_kernel_checked',
        'finite_observation_step_checked', 'claims', 'source_sha256', 'executable_sha256',
        'trusted_import_cache_assumption', 'physical_mapping_remains_external',
        'finite_model_acceptance_is_not_physical_root_acceptance', 'old_proof_campaigns_rerun'}
    require(type(result) is dict and set(result) == expected_fields and result.get('status') == 'passed' and
            result.get('schema') == 'rcp-rclm.phase17q.finite-observation-lean.v1', 'finite kernel Lean gate did not pass')
    require(result.get('packet_sha256') == packet_sha256 and
            result.get('source_sha256') == {n: sha(b) for n, b in sources.items()}, 'executed finite sources differ')
    require(list(sources) == list(LABELS) and result.get('negative_controls_rejected') == list(LABELS[1:]),
            'finite negative-control inventory differs')
    require(type(result.get('new_named_audits')) is int and result['new_named_audits'] == len(NAMES) and
            result.get('finite_observation_kernel_checked') is True and
            result.get('finite_observation_step_checked') is True, 'finite kernel proof scope differs')
    require(canonical(result.get('claims')) == canonical({k: False for k in FALSE_CLAIMS}), 'formal result escalates authority')
    require(result['trusted_import_cache_assumption'] is True and result['physical_mapping_remains_external'] is True and
            result['finite_model_acceptance_is_not_physical_root_acceptance'] is True and
            result['old_proof_campaigns_rerun'] is False, 'formal trust/scope record differs')
    exes = result['executable_sha256']
    require(type(exes) is dict and len(exes) == 3 and all(type(k) is str and type(v) is str and
            re.fullmatch(r'[0-9a-f]{64}', v) for k, v in exes.items()), 'executable identity inventory differs')
    commands = result.get('commands')
    require(type(commands) is list and len(commands) == 1 + len(LABELS), 'formal command inventory differs')
    version = commands[0]
    require(version['returncode'] == 0 and not version['stderr'] and
            re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']) is not None, 'wrong pinned Lean')
    for cmd in commands:
        require(type(cmd['returncode']) is int and type(cmd['stdout']) is str and type(cmd['stderr']) is str,
                'malformed command evidence')
        require(cmd['stdout_sha256'] == sha(cmd['stdout'].encode('utf-8')) and
                cmd['stderr_sha256'] == sha(cmd['stderr'].encode('utf-8')), 'formal log hashes differ')
    positive = commands[1]
    require(positive['returncode'] == 0 and not positive['stderr'], 'positive finite certificate rejected')
    require(result['theorem_axioms'] == parse_audits(positive['stdout']), 'finite axiom report differs')
    for label, cmd in zip(LABELS, commands[1:], strict=True):
        require(cmd.get('label') == label and cmd.get('source_sha256') == sha(sources[label]),
                'command/source binding differs')
        if label != LABELS[0]:
            _negative(cmd)


def check(prepared: PreparedFiniteKernel, *, source_root: Path, lean_workspace: Path,
          toolchain_root: Path | None = None) -> dict:
    from .finite_kernel_lean import render, NAMES, LABELS
    require(type(prepared) is PreparedFiniteKernel, 'exact finite packet required')
    result = {'schema': 'rcp-rclm.phase17q.finite-observation-lean.v1',
              'status': 'blocked', 'packet_sha256': sha(prepared.packet_bytes),
              'commands': [], 'theorem_axioms': {}, 'negative_controls_rejected': [],
              'new_named_audits': len(NAMES), 'finite_observation_kernel_checked': False,
              'finite_observation_step_checked': False,
              'claims': {k: False for k in FALSE_CLAIMS}}
    try:
        sources = {label: render(prepared, source_root=source_root,
                   negative=None if label == LABELS[0] else label) for label in LABELS}
        template_names = sorted(p.relative_to(source_root).as_posix()
                                for p in (source_root / 'lean/phase17_bridge').glob('*.lean'))
        templates = {n: sha(gate._read_regular(source_root / n)) for n in template_names}
        retained = read_retained(source_root)
        roots = gate.root_source_fingerprint(lean_workspace)
        require({k: v['canonical_sha256'] for k, v in roots.items()} ==
                {k: v['canonical_sha256'] for k, v in gate.root_source_fingerprint(source_root).items()},
                'pinned finite-kernel root mismatch')
        deps = gate._dependency_state(lean_workspace)
        tool = gate.resolve_toolchain(toolchain_root)
        env, git = gate._lean_environment(tool)
        suffix = '.exe' if os.name == 'nt' else ''
        lean, lake = tool / 'bin' / ('lean' + suffix), tool / 'bin' / ('lake' + suffix)
        exes = {str(p): sha(gate._read_regular(p)) for p in (lean, lake, git)}
        version = gate._process([str(lean), '--version'], lean_workspace / gate.ROOT_PROJECT, env, timeout=30)
        result['commands'].append(version)
        require(version['returncode'] == 0 and not version['stderr'] and
                re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']), 'wrong pinned Lean')
        result['status'] = 'rejected'
        with tempfile.TemporaryDirectory(prefix='r17q-') as tmp:
            folder = Path(tmp).resolve(strict=True)
            for label, raw in sources.items():
                path = folder / (label + '.lean')
                path.write_bytes(raw)
                command = gate._process([str(lake), '--keep-toolchain', '--no-cache', 'env', str(lean), str(path)],
                                        lean_workspace / gate.ROOT_PROJECT, env, timeout=1800)
                command.update(label=label, source_sha256=sha(raw))
                result['commands'].append(command)
                if label == LABELS[0]:
                    require(command['returncode'] == 0 and not command['stderr'], 'finite observation certificate rejected')
                    audits = parse_audits(command['stdout'])
                else:
                    _negative(command)
                    result['negative_controls_rejected'].append(label)
                require(path.read_bytes() == raw, 'executed finite source changed')
        require(roots == gate.root_source_fingerprint(lean_workspace) and deps == gate._dependency_state(lean_workspace),
                'pinned root/dependency changed during Q proof')
        require(exes == {n: sha(gate._read_regular(Path(n))) for n in exes} and
                templates == {n: sha(gate._read_regular(source_root / n)) for n in template_names} and
                retained == read_retained(source_root), 'tool/template/retained input changed during Q proof')
        result.update(status='passed', theorem_axioms=audits,
                      finite_observation_kernel_checked=True, finite_observation_step_checked=True,
                      source_sha256={n: sha(b) for n, b in sources.items()}, executable_sha256=exes,
                      trusted_import_cache_assumption=True, physical_mapping_remains_external=True,
                      finite_model_acceptance_is_not_physical_root_acceptance=True,
                      old_proof_campaigns_rerun=False)
        validate_result(result, sources, sha(prepared.packet_bytes))
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result['status'] = 'rejected' if result['status'] != 'blocked' else 'blocked'
        result['failure'] = {'type': type(exc).__name__, 'reason': str(exc)}
    return result
