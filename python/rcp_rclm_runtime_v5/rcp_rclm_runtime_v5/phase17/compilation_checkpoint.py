"""Immutable, explicitly selected compilation-stage continuations.

This protocol belongs to the new AC validation contract. It does not reinterpret
AB's fresh single-application evidence. Each invocation owns one private output
directory and runs one fixed trusted stage. A continuation names an exact parent
manifest hash, retains the original producers, and restores only completed
artifacts. An uncompleted invocation remains unresolved on its own branch.

The caller supplies the trusted stage definitions, complete input inventory and
semantic validators; no command is obtained from a saved report. Hashes bind
reproducible observations, not physical execution or hostile-host authenticity.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import time
from typing import Callable, Mapping
import uuid


SCHEMA = 'runtime.v5.phase17ac.compilation-stage.v1'
PLAN_SCHEMA = 'runtime.v5.phase17ac.compilation-plan.v1'
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_STAGES = 128
WORKSPACE_TOKEN = '{workspace}'
_IDENTIFIER = re.compile(r'[0-9a-f]{32}')
_SHA = re.compile(r'[0-9a-f]{64}')


class CheckpointError(ValueError):
    """An invalid or incomplete record cannot support continuation."""


class StageFailure(CheckpointError):
    """The attempted stage did not publish a reusable completion."""

    def __init__(self, message: str, invocation: Path):
        super().__init__(message)
        self.invocation = invocation


def _need(condition, message):
    if not condition:
        raise CheckpointError(message)


def _canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_value(value):
    """Detach a bounded JSON-only receipt; reject NaN and non-JSON objects."""
    raw = _canonical(value)
    _need(len(raw) <= MAX_MANIFEST_BYTES, 'JSON receipt exceeds bound')
    return json.loads(raw)


def _path(path) -> Path:
    path = Path(path)
    _need(path.is_absolute() and '..' not in path.parts, 'absolute normalized path required')
    _need(not any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
                  for p in (path, *path.parents)), 'linked or junction path rejected')
    return path


def _relative(name: str) -> str:
    _need(type(name) is str and bool(name) and '\\' not in name and ':' not in name,
          'invalid relative payload path')
    p = PurePosixPath(name)
    _need(not p.is_absolute() and all(x not in ('', '.', '..') for x in p.parts)
          and p.as_posix() == name, 'noncanonical relative payload path')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                *(f'LPT{i}' for i in range(1, 10))}
    _need(all(part == part.rstrip('. ') and part.split('.')[0].upper() not in reserved
              and not any(ord(c) < 32 or c in '<>"|?*' for c in part)
              for part in p.parts), 'nonportable Windows payload name')
    return name


def _read(path, limit=MAX_FILE_BYTES) -> bytes:
    path = _path(path)
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        before = os.fstat(stream.fileno())
        _need(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
              'nonregular or oversized file')
        raw = stream.read(limit + 1)
        # Compare timestamps through one API. On Windows, path stat's ctime
        # can mean creation time while fstat's ctime means metadata-change
        # time (CPython issue 157671). Reopen the checked path so that ctime
        # still detects a mutation, including one that restores size/mtime.
        with os.fdopen(os.open(_path(path), flags), 'rb') as current:
            external = os.fstat(current.fileno())
            after = os.fstat(stream.fileno())
            named = _path(path).stat(follow_symlinks=False)
        _need(all(stat.S_ISREG(s.st_mode) for s in (after, external, named)),
              'nonregular file during byte capture')
        _need(len(raw) == before.st_size <= limit,
              'file changed during byte capture: byte length')
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        changed = [k for k in fields if not (
            getattr(before, k) == getattr(after, k) == getattr(external, k))]
        _need(not changed, 'file changed during byte capture: descriptor metadata ' +
              ','.join(changed))
        # Retain the final no-follow path check: reopening must not silently
        # substitute a different file. Only ctime is not comparable across
        # these APIs; its full before/after check is retained above.
        changed = [k for k in fields if k != 'st_ctime_ns' and
                   getattr(external, k) != getattr(named, k)]
        _need(not changed, 'file changed during byte capture: path metadata ' +
              ','.join(changed))
        return raw


def _load(path, expected_sha256=None):
    raw = _read(path, MAX_MANIFEST_BYTES)
    if expected_sha256 is not None:
        _need(type(expected_sha256) is str and _SHA.fullmatch(expected_sha256) and
              _sha(raw) == expected_sha256, 'externally pinned manifest hash differs')

    def unique(pairs):
        obj = {}
        for key, value in pairs:
            _need(key not in obj, 'duplicate JSON key')
            obj[key] = value
        return obj

    obj = json.loads(raw, object_pairs_hook=unique)
    _need(_canonical(obj) == raw, 'noncanonical or incomplete manifest')
    return obj


def _sync_directory(path: Path):
    # File fsync is portable. POSIX directory fsync additionally persists the
    # namespace request. Neither claims a hardware power-loss theorem.
    if os.name == 'posix':
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _new_bytes(path: Path, raw: bytes):
    """Publish complete bytes exclusively; unsupported hard links fail closed."""
    path = _path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / ('.unpublished-' + uuid.uuid4().hex)
    with temporary.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    # Atomic non-replacing publication on supported POSIX/Windows filesystems.
    # No lock is expired, stolen, or inferred released from a missing PID.
    os.link(temporary, path)
    _sync_directory(path.parent)
    temporary.unlink()


def _new_json(path: Path, value):
    raw = _canonical(value)
    _need(len(raw) <= MAX_MANIFEST_BYTES, 'manifest exceeds bound')
    _new_bytes(path, raw)


def _file_record(raw: bytes) -> dict:
    return {'bytes': len(raw), 'sha256': _sha(raw)}


def _render(value: str, workspace: Path) -> str:
    return value.replace(WORKSPACE_TOKEN, str(workspace))


@dataclass(frozen=True)
class Stage:
    label: str
    argv: tuple[str, ...]
    timeout_seconds: int
    artifact_names: tuple[str, ...] = ()

    def __post_init__(self):
        _need(type(self.label) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', self.label),
              'invalid stage label')
        _need(type(self.argv) is tuple and bool(self.argv) and
              all(type(x) is str and x and '\x00' not in x for x in self.argv),
              'fixed trusted argv tuple required')
        _need(type(self.timeout_seconds) is int and 0 < self.timeout_seconds <= 14_400,
              'invalid stage timeout')
        _need(type(self.artifact_names) is tuple and
              len(self.artifact_names) == len(set(self.artifact_names)),
              'duplicate artifact names')
        for name in self.artifact_names:
            _relative(name)

    def to_json(self):
        return {'label': self.label, 'argv': list(self.argv),
                'timeout_seconds': self.timeout_seconds,
                'artifact_names': list(self.artifact_names)}


def _configuration(*, plan_context, stages, input_files, expected_input_sha256,
                   workspace_files, environment, cwd, max_completed_seconds):
    _need(type(stages) is tuple and 0 < len(stages) <= MAX_STAGES and
          all(type(s) is Stage for s in stages), 'trusted fixed stage tuple required')
    _need(len({s.label for s in stages}) == len(stages), 'duplicate stage labels')
    _need(type(max_completed_seconds) is int and 0 < max_completed_seconds <= 86_400,
          'invalid completed-lineage time allowance')
    _need(set(input_files) == set(expected_input_sha256) and bool(input_files),
          'exact nonempty external input inventory required')
    _need(all(type(k) is str and k and type(h) is str and _SHA.fullmatch(h)
              for k, h in expected_input_sha256.items()), 'invalid input hash inventory')
    for name, path in input_files.items():
        _need(_sha(_read(path)) == expected_input_sha256[name], 'bound external input differs: ' + name)
    input_paths = {str(_path(path)) for path in input_files.values()}
    _need(all(stage.argv[0] in input_paths for stage in stages),
          'every directly executed tool must have an explicit verified input binding')
    _need(bool(workspace_files) and all(type(b) is bytes and len(b) <= MAX_FILE_BYTES
                                      for b in workspace_files.values()),
          'fixed workspace bytes required')
    for name in workspace_files:
        _relative(name)
    artifact_names = [name for stage in stages for name in stage.artifact_names]
    _need(len(artifact_names) == len(set(artifact_names)) and
          not set(artifact_names).intersection(workspace_files),
          'stage outputs overlap earlier outputs or immutable sources')
    payload_names = [*workspace_files, *artifact_names]
    _need(len({name.casefold() for name in payload_names}) == len(payload_names),
          'case-insensitive payload-name collision')
    _need(bool(environment) and len(environment) <= 128 and
          all(type(k) is str and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', k) and
              type(v) is str and not any(c in v for c in '\x00\r\n')
              for k, v in environment.items()), 'invalid explicit environment')
    cwd = _path(cwd)
    _need(cwd.is_dir(), 'compiler cwd does not exist')
    plan = {'schema': PLAN_SCHEMA, 'context': _json_value(plan_context),
            'stages': [s.to_json() for s in stages],
            'input_sha256': dict(expected_input_sha256),
            'workspace_files': {name: _file_record(raw) for name, raw in workspace_files.items()},
            'environment_template': dict(environment), 'cwd': str(cwd),
            'budget': {'per_stage_timeout_seconds': [s.timeout_seconds for s in stages],
                       'max_completed_lineage_active_seconds': max_completed_seconds,
                       'downtime_included': False, 'orphan_cost_inferred': False,
                       'measured_interval': 'stage invocation entry through final input/result validation; completion publication excluded',
                       'scope': 'completed selected lineage only; not a global campaign budget'},
            'ownership': 'one private invocation per stage; explicit parent hash; no takeover',
            'freshness': 'original producer retained; inherited stages are not fresh in this invocation'}
    return plan


def _inventory(workspace: Path):
    actual = {}
    for path in sorted(workspace.rglob('*')):
        _path(path)
        if path.is_dir():
            continue
        raw = _read(path)
        actual[path.relative_to(workspace).as_posix()] = _file_record(raw)
    return actual


def _record_for_validation(step: dict, invocation: Path) -> dict:
    result = _json_value(step['command'])
    for stream in ('stdout', 'stderr'):
        raw = _read(invocation / 'logs' / (f"{step['index']:03d}." + stream + '.bin'), MAX_LOG_BYTES)
        _need(_file_record(raw) == step['logs'][stream], 'saved command log differs')
        result[stream] = raw.decode('utf-8', errors='strict')
        result[stream + '_sha256'] = _sha(raw)
    return result


def _validate_loaded(manifest, *, invocation, expected_plan, stages, workspace_files,
                     validate_result):
    fields = {'schema', 'status', 'plan', 'plan_sha256', 'invocation_id', 'parent_manifest_sha256',
              'steps', 'artifacts', 'completed_lineage_active_ns', 'unresolved_invocations',
              'unresolved_observation_scope', 'complete_resource_accounting', 'created_at_utc',
              'fsync_file_requested', 'fsync_directory_requested', 'invocation_records'}
    _need(type(manifest) is dict and set(manifest) == fields and manifest['schema'] == SCHEMA
          and manifest['status'] == 'completed', 'reusable completed-stage manifest required')
    plan_hash = _sha(_canonical(expected_plan))
    _need(manifest['plan'] == expected_plan and manifest['plan_sha256'] == plan_hash,
          'trusted source/tool/environment/stage plan differs')
    _need(type(manifest['invocation_id']) is str and _IDENTIFIER.fullmatch(manifest['invocation_id'])
          and invocation.name == manifest['invocation_id'], 'invocation directory identity differs')
    _need(not (invocation / 'failure.json').exists(), 'conflicting failure marker prevents reuse')
    steps = manifest['steps']
    _need(type(steps) is list and 0 < len(steps) <= len(stages), 'invalid completed prefix')
    artifacts = {}; previous_step = None; producers = set(); elapsed = 0
    for index, step in enumerate(steps):
        _need(type(step) is dict and set(step) == {'index', 'label', 'producer_invocation',
              'previous_step_sha256', 'command', 'logs', 'artifacts', 'semantic_receipt',
              'restore_receipt', 'active_elapsed_ns', 'plan_sha256'}, 'invalid step record')
        stage = stages[index]
        _need(step['index'] == index and step['label'] == stage.label and
              step['plan_sha256'] == plan_hash and step['previous_step_sha256'] == previous_step,
              'noncontiguous or cross-plan step chain')
        producer = step['producer_invocation']
        _need(type(producer) is str and _IDENTIFIER.fullmatch(producer) and producer not in producers,
              'duplicate or invalid original producer')
        producers.add(producer)
        command = step['command']
        _need(type(command) is dict and set(command) == {'label', 'argv', 'cwd', 'workspace',
              'environment_sha256', 'returncode', 'timed_out', 'native_wait_completed',
              'pid', 'started_at_utc', 'elapsed_ns', 'effective_timeout_ns'}, 'invalid native command record')
        workspace = Path(command['workspace'])
        _need(workspace.is_absolute() and workspace.name == 'workspace' and
              workspace.parent.name == producer, 'command producer workspace differs')
        _need(command['label'] == stage.label and command['argv'] ==
              [_render(arg, workspace) for arg in stage.argv] and
              command['cwd'] == expected_plan['cwd'] and command['environment_sha256'] ==
              _sha(_canonical({k: _render(v, workspace) for k, v in expected_plan['environment_template'].items()})),
              'command or effective environment differs from trusted stage')
        _need(type(command['returncode']) is int and command['timed_out'] is False and
              command['native_wait_completed'] is True and type(command['pid']) is int and command['pid'] > 0,
              'unknown or timed-out command cannot be reused')
        _need(type(command['elapsed_ns']) is int and command['elapsed_ns'] >= 0 and
              type(command['effective_timeout_ns']) is int and
              0 < command['effective_timeout_ns'] <= stage.timeout_seconds * 1_000_000_000 and
              command['elapsed_ns'] <= command['effective_timeout_ns'],
              'invalid command time accounting')
        _need(type(step['active_elapsed_ns']) is int and
              step['active_elapsed_ns'] >= command['elapsed_ns'], 'unaccounted command duration')
        elapsed += step['active_elapsed_ns']
        _need(type(step['logs']) is dict and set(step['logs']) == {'stdout', 'stderr'}, 'invalid log inventory')
        result = _record_for_validation(step, invocation)
        _need(_json_value(validate_result(stage, result)) == step['semantic_receipt'],
              'semantic receipt differs from current trusted validator')
        _need(type(step['artifacts']) is dict and set(step['artifacts']) == set(stage.artifact_names),
              'completed stage output set differs')
        for name, record in step['artifacts'].items():
            _need(type(record) is dict and set(record) == {'bytes', 'sha256', 'producer_invocation'}
                  and record['producer_invocation'] == producer and type(record['bytes']) is int
                  and 0 < record['bytes'] <= MAX_FILE_BYTES and type(record['sha256']) is str
                  and _SHA.fullmatch(record['sha256']), 'invalid output identity')
            artifacts[name] = record
        _need((index == 0 and step['restore_receipt'] is None) or
              (index > 0 and step['restore_receipt'] is not None), 'inherited-prefix preflight receipt missing')
        previous_step = _sha(_canonical(step))
    _need(steps[-1]['producer_invocation'] == manifest['invocation_id'], 'last producer differs')
    _need(manifest['parent_manifest_sha256'] is None if len(steps) == 1 else
          type(manifest['parent_manifest_sha256']) is str and _SHA.fullmatch(manifest['parent_manifest_sha256']),
          'explicit parent identity missing')
    native_names = ('start.json', 'child-start.json', 'native-result.json')
    _need(type(manifest['invocation_records']) is dict and
          set(manifest['invocation_records']) == set(native_names), 'native invocation records missing')
    for name in native_names:
        _need(_file_record(_read(invocation / name, MAX_MANIFEST_BYTES)) ==
              manifest['invocation_records'][name], 'native invocation record bytes differ')
    _need(_load(invocation / 'native-result.json') == steps[-1]['command'],
          'native terminal record and completed command disagree')
    child = _load(invocation / 'child-start.json')
    _need(type(child) is dict and set(child) == {'schema', 'invocation_id', 'pid', 'argv',
                                               'owner_pid', 'plan_sha256'} and
          child['schema'] == SCHEMA and child['invocation_id'] == manifest['invocation_id'] and
          child['pid'] == steps[-1]['command']['pid'] and child['argv'] == steps[-1]['command']['argv'] and
          child['plan_sha256'] == plan_hash and type(child['owner_pid']) is int and child['owner_pid'] > 0,
          'native child start identity differs')
    start = _load(invocation / 'start.json')
    _need(type(start) is dict and set(start) == {'schema', 'invocation_id', 'stage_index', 'stage_label',
          'plan_sha256', 'parent_manifest_sha256', 'started_at_utc', 'unresolved_invocations', 'status'} and
          start['schema'] == SCHEMA and start['invocation_id'] == manifest['invocation_id'] and
          start['stage_index'] == len(steps) - 1 and start['stage_label'] == steps[-1]['label'] and
          start['plan_sha256'] == plan_hash and start['parent_manifest_sha256'] == manifest['parent_manifest_sha256'] and
          start['unresolved_invocations'] == manifest['unresolved_invocations'] and
          start['status'] == 'started_no_terminal_outcome_yet', 'native invocation start differs')
    _need(manifest['artifacts'] == artifacts and manifest['completed_lineage_active_ns'] == elapsed and
          elapsed <= expected_plan['budget']['max_completed_lineage_active_seconds'] * 1_000_000_000,
          'artifact inventory or cumulative completed-lineage budget differs')
    refs = manifest['unresolved_invocations']
    _need(type(refs) is list and refs == sorted(set(refs)) and
          all(type(x) is str and _IDENTIFIER.fullmatch(x) and x not in producers for x in refs),
          'invalid explicit unresolved invocation references')
    _need(manifest['unresolved_observation_scope'] == 'explicit references only; no unseen outcome inferred' and
          manifest['complete_resource_accounting'] is False and manifest['fsync_file_requested'] is True and
          type(manifest['fsync_directory_requested']) is bool, 'resource/persistence scope changed')
    expected_files = {name: _file_record(raw) for name, raw in workspace_files.items()}
    expected_files.update({name: {k: item[k] for k in ('bytes', 'sha256')} for name, item in artifacts.items()})
    _need(_inventory(invocation / 'workspace') == expected_files, 'restored workspace bytes or file set differ')
    log_names = {f'{i:03d}.{s}.bin' for i in range(len(steps)) for s in ('stdout', 'stderr')}
    _need({p.name for p in (invocation / 'logs').iterdir()} == log_names, 'command log file set differs')
    return manifest


def verify_manifest(manifest_path: Path, expected_sha256: str, *, plan_context, stages,
                    input_files, expected_input_sha256, workspace_files, environment, cwd,
                    validate_result: Callable, max_completed_seconds: int = 14_400) -> dict:
    """Reopen exact saved bytes under independently supplied trusted definitions.

    This performs no Lean execution. The semantic callback must inspect the
    supplied exact output again; the runner checks all copied sources, artifacts
    and raw logs, their producer chain, and the current input identities.
    """
    manifest_path = _path(manifest_path)
    _need(manifest_path.name == 'completion.json', 'completion marker required')
    plan = _configuration(plan_context=plan_context, stages=stages, input_files=input_files,
                          expected_input_sha256=expected_input_sha256, workspace_files=workspace_files,
                          environment=environment, cwd=cwd, max_completed_seconds=max_completed_seconds)
    return _validate_loaded(_load(manifest_path, expected_sha256), invocation=manifest_path.parent,
                            expected_plan=plan, stages=stages, workspace_files=workspace_files,
                            validate_result=validate_result)


def run_stage(root: Path, *, plan_context, stages: tuple[Stage, ...], input_files,
              expected_input_sha256, workspace_files: Mapping[str, bytes], environment,
              cwd: Path, validate_result: Callable,
              parent_manifest: Path | None = None, expected_parent_sha256: str | None = None,
              restore_validator: Callable | None = None, unresolved_invocations=(),
              max_completed_seconds: int = 14_400) -> dict:
    """Execute one trusted stage in a fresh invocation, optionally from a pin.

    ``validate_result(stage, record)`` returns a deterministic JSON semantic
    receipt, or raises. Nonzero exits are accepted only if that validator accepts
    them (for intended negative controls). ``restore_validator(workspace,
    inherited_artifacts)`` must recheck current import resolution and returns a
    JSON receipt. It is required for every continuation and runs before the new
    stage. It is not called by offline ``verify_manifest``.

    An explicit repeated parent selects a new branch; it never retries or takes
    over an old invocation. Original producer IDs remain in inherited records.
    Only completed selected-lineage active time consumes this contract's bound;
    downtime and unresolved other branches are explicitly not measured by it.
    """
    active_start = time.monotonic_ns()
    _need((parent_manifest is None) == (expected_parent_sha256 is None),
          'both explicit parent path and independent parent hash are required')
    config = dict(plan_context=plan_context, stages=stages, input_files=input_files,
                  expected_input_sha256=expected_input_sha256, workspace_files=workspace_files,
                  environment=environment, cwd=cwd, max_completed_seconds=max_completed_seconds)
    plan = _configuration(**config); plan_hash = _sha(_canonical(plan))
    parent = None
    if parent_manifest is not None:
        parent = verify_manifest(parent_manifest, expected_parent_sha256,
                                 validate_result=validate_result, **config)
        _need(callable(restore_validator), 'trusted restored-prefix import preflight required')
    index = 0 if parent is None else len(parent['steps'])
    _need(index < len(stages), 'all planned stages already completed')
    refs = sorted(set(unresolved_invocations) | set(parent['unresolved_invocations'] if parent else []))
    _need(all(type(x) is str and _IDENTIFIER.fullmatch(x) for x in refs),
          'unresolved references must be invocation IDs, not inferred process outcomes')
    root = _path(root); root.mkdir(parents=True, exist_ok=True)
    container = root / 'invocations'; container.mkdir(exist_ok=True)
    invocation_id = uuid.uuid4().hex
    invocation = container / invocation_id; invocation.mkdir()
    workspace = invocation / 'workspace'; workspace.mkdir()
    logs = invocation / 'logs'; logs.mkdir()
    stage = stages[index]
    _new_json(invocation / 'start.json', {
        'schema': SCHEMA, 'invocation_id': invocation_id, 'stage_index': index,
        'stage_label': stage.label, 'plan_sha256': plan_hash,
        'parent_manifest_sha256': expected_parent_sha256,
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'unresolved_invocations': refs, 'status': 'started_no_terminal_outcome_yet'})
    command = None; process = None; steps = []; artifacts = {}; restore_receipt = None
    try:
        for name, raw in workspace_files.items():
            _new_bytes(workspace / name, raw)
        if parent is not None:
            prior = _path(parent_manifest).parent
            steps = _json_value(parent['steps']); artifacts = _json_value(parent['artifacts'])
            for name in artifacts:
                _new_bytes(workspace / name, _read(prior / 'workspace' / name))
            for i in range(index):
                for stream in ('stdout', 'stderr'):
                    name = f'{i:03d}.{stream}.bin'
                    _new_bytes(logs / name, _read(prior / 'logs' / name, MAX_LOG_BYTES))
            restore_receipt = _json_value(restore_validator(workspace, _json_value(artifacts)))
            _need(restore_receipt is not None, 'import preflight must return an explicit receipt')
        expected_before = {name: _file_record(raw) for name, raw in workspace_files.items()}
        expected_before.update({name: {k: item[k] for k in ('bytes', 'sha256')}
                                for name, item in artifacts.items()})
        _need(_inventory(workspace) == expected_before, 'preflight changed fixed workspace inputs')
        cumulative = 0 if parent is None else parent['completed_lineage_active_ns']
        remaining_ns = max_completed_seconds * 1_000_000_000 - cumulative - (time.monotonic_ns() - active_start)
        _need(remaining_ns > 0, 'completed-lineage active budget exhausted before launch')
        effective_ns = min(stage.timeout_seconds * 1_000_000_000, remaining_ns)
        effective_env = {k: _render(v, workspace) for k, v in environment.items()}
        argv = [_render(arg, workspace) for arg in stage.argv]
        command = {'label': stage.label, 'argv': argv, 'cwd': str(cwd), 'workspace': str(workspace),
                   'environment_sha256': _sha(_canonical(effective_env)), 'returncode': None,
                   'timed_out': False, 'native_wait_completed': False, 'pid': None,
                   'started_at_utc': datetime.now(timezone.utc).isoformat(),
                   'elapsed_ns': 0, 'effective_timeout_ns': effective_ns}
        command_start = time.monotonic_ns()
        with (logs / f'{index:03d}.stdout.bin').open('xb') as out, \
             (logs / f'{index:03d}.stderr.bin').open('xb') as err:
            process = subprocess.Popen(argv, cwd=cwd, env=effective_env, stdout=out, stderr=err,
                                       shell=False, stdin=subprocess.DEVNULL)
            command['pid'] = process.pid
            _new_json(invocation / 'child-start.json', {
                'schema': SCHEMA, 'invocation_id': invocation_id, 'pid': process.pid,
                'argv': argv, 'owner_pid': os.getpid(), 'plan_sha256': plan_hash})
            try:
                command['returncode'] = process.wait(timeout=max(0.0,
                    (effective_ns - (time.monotonic_ns() - command_start)) / 1_000_000_000))
            except subprocess.TimeoutExpired:
                command['timed_out'] = True
                process.kill()
                command['returncode'] = process.wait()
            command['native_wait_completed'] = True
            command['elapsed_ns'] = time.monotonic_ns() - command_start
            for stream in (out, err):
                stream.flush(); os.fsync(stream.fileno())
        _new_json(invocation / 'native-result.json', command)
        _need(not command['timed_out'], 'stage timeout is a failed attempt, not a reusable checkpoint')
        _need(command['elapsed_ns'] <= effective_ns, 'recorded command duration exceeds its stage allowance')
        raw_logs = {s: _read(logs / f'{index:03d}.{s}.bin', MAX_LOG_BYTES) for s in ('stdout', 'stderr')}
        result = _json_value(command)
        for stream, raw in raw_logs.items():
            result[stream] = raw.decode('utf-8', errors='strict')
            result[stream + '_sha256'] = _sha(raw)
        semantic = _json_value(validate_result(stage, result))
        outputs = {}
        for name in stage.artifact_names:
            raw = _read(workspace / name)
            _need(bool(raw), 'empty compilation artifact')
            outputs[name] = {**_file_record(raw), 'producer_invocation': invocation_id}
        artifacts.update(outputs)
        _need(_configuration(**config) == plan, 'source/tool inputs changed during execution')
        step = {'index': index, 'label': stage.label, 'producer_invocation': invocation_id,
                'previous_step_sha256': None if not steps else _sha(_canonical(steps[-1])),
                'command': command, 'logs': {s: _file_record(raw) for s, raw in raw_logs.items()},
                'artifacts': outputs, 'semantic_receipt': semantic, 'restore_receipt': restore_receipt,
                'active_elapsed_ns': time.monotonic_ns() - active_start, 'plan_sha256': plan_hash}
        steps.append(step)
        manifest = {'schema': SCHEMA, 'status': 'completed', 'plan': plan, 'plan_sha256': plan_hash,
                    'invocation_id': invocation_id, 'parent_manifest_sha256': expected_parent_sha256,
                    'steps': steps, 'artifacts': artifacts,
                    'completed_lineage_active_ns': cumulative + step['active_elapsed_ns'],
                    'unresolved_invocations': refs,
                    'unresolved_observation_scope': 'explicit references only; no unseen outcome inferred',
                    'complete_resource_accounting': False,
                    'created_at_utc': datetime.now(timezone.utc).isoformat(),
                    'fsync_file_requested': True, 'fsync_directory_requested': os.name == 'posix',
                    'invocation_records': {name: _file_record(_read(invocation / name, MAX_MANIFEST_BYTES))
                                           for name in ('start.json', 'child-start.json', 'native-result.json')}}
        _validate_loaded(manifest, invocation=invocation, expected_plan=plan, stages=stages,
                         workspace_files=workspace_files, validate_result=validate_result)
        # Include initial input/parent verification and the final reopen check.
        # Only the following immutable completion publication is outside this
        # measured interval; its omission is an explicit plan field.
        step['active_elapsed_ns'] = time.monotonic_ns() - active_start
        manifest['completed_lineage_active_ns'] = cumulative + step['active_elapsed_ns']
        _need(manifest['completed_lineage_active_ns'] <= max_completed_seconds * 1_000_000_000,
              'completed-lineage budget exhausted during final validation')
        manifest_path = invocation / 'completion.json'
        _new_json(manifest_path, manifest)
        manifest_sha = _sha(_read(manifest_path, MAX_MANIFEST_BYTES))
        return {'manifest_path': str(manifest_path), 'manifest_sha256': manifest_sha,
                'manifest': manifest, 'completed_stage_count': len(steps),
                'all_stages_completed': len(steps) == len(stages)}
    except Exception as exc:
        if process is not None and process.poll() is None:
            process.kill(); process.wait()
            if command is not None:
                command['returncode'] = process.returncode
                command['native_wait_completed'] = True
        failure = {'schema': SCHEMA, 'status': 'failed_not_reusable', 'invocation_id': invocation_id,
                   'plan_sha256': plan_hash, 'parent_manifest_sha256': expected_parent_sha256,
                   'stage_index': index, 'stage_label': stage.label, 'command': command,
                   'failure_type': type(exc).__name__, 'failure': str(exc),
                   'observed_active_ns': time.monotonic_ns() - active_start,
                   'unresolved_invocations': refs, 'complete_resource_accounting': False,
                   'failed_at_utc': datetime.now(timezone.utc).isoformat()}
        try:
            _new_json(invocation / 'failure.json', failure)
        except Exception as save_error:
            raise StageFailure('stage failed and failure publication also failed: ' + str(save_error), invocation) from exc
        raise StageFailure(str(exc), invocation) from exc
