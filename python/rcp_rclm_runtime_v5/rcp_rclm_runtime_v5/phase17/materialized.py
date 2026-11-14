"""Phase 17D measured physical packages; never an active-store promotion.

All inherited M9 bytes come from the fixed, externally pinned archive. The
selected Phase16 registry is rebuilt from the verified historical handoff.
No answer store or executable candidate source is installed in the package.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime_v5.phase17.bootstrap import (
    HistoricalPredecessor, M9_PREFIX, M9_BUNDLE_SHA256, M9_PACKAGE_HASH,
    SELECTED_STATE_HASH, _read_pinned_archive, _member, _validate_program,
)
from rcp_rclm_runtime_v5.phase17.controller import ControlError, _hash
from rcp_rclm_runtime_v5.phase17.challenge_protocol import verify_transcript

SCHEMA = 'runtime.v5.phase17.materialized-package.v1'
MANIFEST = 'materialized_manifest.json'
MAX_FILES = 256
MAX_BYTES = 40 * 1024 * 1024
M9_FILE_COUNT = 164
M9_BYTES = 27434256
CLAIMS = dict(promotion_authorized=False, phase17_exit_closed=False,
              gate_e_closed=False, egc0_started=False, full_transformer_inference=False)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ControlError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relative(name: str) -> str:
    require(type(name) is str and 0 < len(name) < 512, 'invalid package path')
    p = PurePosixPath(name)
    require(not p.is_absolute() and p.as_posix() == name and
            not any(c in name for c in '\\:\0\r\n') and '..' not in p.parts,
            'unsafe package path')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1, 10)),
                *('LPT'+str(i) for i in range(1, 10))}
    require(all(not s.endswith((' ', '.')) and s.split('.')[0].upper() not in reserved
                for s in p.parts), 'nonportable package path')
    return name


def _measure(files: dict[str, bytes]) -> list[dict]:
    require(0 < len(files) <= MAX_FILES, 'package file-count bound')
    require(sum(len(v) for v in files.values()) <= MAX_BYTES, 'package byte bound')
    folded: set[str] = set()
    for name, data in files.items():
        safe_relative(name)
        require(type(data) is bytes, 'immutable package bytes required')
        require(name.casefold() not in folded, 'case-colliding package files')
        folded.add(name.casefold())
    return [{'path': name, 'mode': '0644', 'size': len(data), 'sha256': sha(data)}
            for name, data in sorted(files.items())]


def base_files(bundle: Path) -> dict[str, bytes]:
    """Read only 164 selected semantic-package members, not the entire large bundle."""
    with _read_pinned_archive(bundle, M9_BUNDLE_SHA256) as archive:
        infos = [i for i in archive.infolist() if i.filename.startswith(M9_PREFIX)]
        require(len(infos) == M9_FILE_COUNT and sum(i.file_size for i in infos) == M9_BYTES,
                'historical M9 membership/size mismatch')
        files = {'base/' + safe_relative(i.filename[len(M9_PREFIX):]):
                 _member(archive, i.filename, MAX_BYTES) for i in infos}
    _measure(files)
    record = load_json_strict(files['base/package_manifest.json'])
    require(record['package_hash'] == M9_PACKAGE_HASH, 'historical base identity mismatch')
    return files


def _candidate_program(parent: HistoricalPredecessor, transcript: bytes, anchor: str) -> tuple[dict, dict]:
    _hash(anchor, 'external transcript anchor')
    replay = verify_transcript(parent, transcript, expected_transcript_hash=anchor)
    require(replay.terminal_action == 'await_root_verification' and
            replay.selected_candidate_hash is not None, 'sealed transcript has no passing candidate')
    obj = load_json_strict(transcript)
    matches = [event for event in obj['events'] if event['request'].get('op') == 'evaluate' and
               event['response']['payload'].get('verdict') == 'candidate_passed']
    require(len(matches) == 1, 'exactly one passing artifact required')
    artifact = matches[0]['request']['artifact']
    program = artifact['program']
    require(digest(program) == replay.selected_candidate_hash == artifact['program_hash'],
            'passing-program binding mismatch')
    require(digest(program) not in parent.state['installed_program_hashes'],
            'candidate already installed')
    return program, {'transcript_sha256': anchor, 'artifact_hash': artifact['artifact_hash'],
                     'program_hash': digest(program), 'evaluation_hash': matches[0]['response']['payload']['evaluation_hash']}


def expected_package(parent: HistoricalPredecessor, bundle: Path, *,
                     transcript: bytes | None = None, expected_transcript_hash: str | None = None
                     ) -> tuple[dict[str, bytes], dict]:
    require(type(parent) is HistoricalPredecessor, 'verified historical predecessor required')
    parent.validate()
    require((transcript is None) == (expected_transcript_hash is None), 'transcript and anchor are paired')
    files = base_files(bundle)
    programs = [load_json_strict(p) for p in parent.accepted_programs]
    candidate = None
    if transcript is not None:
        program, candidate = _candidate_program(parent, transcript, expected_transcript_hash)
        programs.append(program)
    for program in programs:
        _validate_program(program)
        files['registry/programs/' + digest(program) + '.json'] = canonical(program)
    registry = {'schema_id': 'runtime.v5.phase17.installed-bounded-programs.v1',
                'inherited_program_hashes': list(parent.state['installed_program_hashes']),
                'candidate_program_hash': None if candidate is None else candidate['program_hash'],
                'inherited_frontier': list(parent.state['capability_frontier']),
                'recursive_frontier': list(parent.state['recursive_productivity_frontier']),
                'candidate_active': False, 'promotion_authorized': False}
    files['registry/manifest.json'] = canonical(registry)
    files['historical_state.json'] = parent.state_bytes
    rows = _measure(files)
    manifest = {'schema_id': SCHEMA, 'kind': 'predecessor' if candidate is None else 'prospective_candidate',
                'historical_state_hash': SELECTED_STATE_HASH,
                'historical_active_package_hash': parent.state['active_package_hash'],
                'base_package_hash': M9_PACKAGE_HASH, 'base_parameter_count': 13625920,
                'base_archive_sha256': M9_BUNDLE_SHA256,
                'candidate': candidate, 'files': rows, 'claims': dict(CLAIMS)}
    manifest['materialized_package_hash'] = digest(manifest)
    return files, manifest


def snapshot(root: Path) -> dict[str, bytes]:
    """Measure physical files, not an asserted list; reject extra files and links."""
    require(root.is_dir() and not root.is_symlink(), 'regular package directory required')
    files = {}
    total = 0
    for current, directories, names in os.walk(root, followlinks=False):
        for name in directories:
            p = Path(current)/name
            require(not p.is_symlink(), 'package directory symlink')
        for name in names:
            p = Path(current)/name
            rel = safe_relative(p.relative_to(root).as_posix())
            st = p.lstat()
            require(stat.S_ISREG(st.st_mode) and not p.is_symlink() and st.st_nlink == 1,
                    'package must contain independent regular files')
            require(st.st_size <= MAX_BYTES, 'file exceeds package bound')
            data = p.read_bytes()
            require(len(data) == st.st_size, 'file changed while being read')
            total += len(data)
            require(total <= MAX_BYTES and len(files) < MAX_FILES+1, 'package size bound')
            files[rel] = data
    return files


@dataclass(frozen=True)
class PackageReceipt:
    root: Path
    manifest_bytes: bytes

    @property
    def package_hash(self) -> str:
        return load_json_strict(self.manifest_bytes)['materialized_package_hash']


def verify_package(root: Path, parent: HistoricalPredecessor, bundle: Path, *,
                   expected_package_hash: str, transcript: bytes | None = None,
                   expected_transcript_hash: str | None = None) -> PackageReceipt:
    _hash(expected_package_hash, 'external physical-package anchor')
    wanted, manifest = expected_package(parent, bundle, transcript=transcript,
                                         expected_transcript_hash=expected_transcript_hash)
    require(manifest['materialized_package_hash'] == expected_package_hash, 'package anchor mismatch')
    wanted[MANIFEST] = canonical(manifest)
    require(snapshot(root) == wanted, 'materialized files differ from independently reconstructed package')
    return PackageReceipt(root.resolve(), wanted[MANIFEST])


def materialize_package(destination: Path, parent: HistoricalPredecessor, bundle: Path, *,
                        transcript: bytes | None = None, expected_transcript_hash: str | None = None
                        ) -> PackageReceipt:
    """Create a NEW inactive package. Never write an active-store pointer."""
    require(not destination.exists() and not destination.is_symlink(), 'package output already exists')
    require(destination.parent.is_dir() and not any(p.is_symlink() for p in
            (destination.parent, *destination.parents)), 'output parent must be regular')
    files, manifest = expected_package(parent, bundle, transcript=transcript,
                                        expected_transcript_hash=expected_transcript_hash)
    files[MANIFEST] = canonical(manifest)
    # Directory ownership is the caller's trusted workspace. Not a same-user sandbox.
    destination.mkdir()
    for rel, data in files.items():
        path = destination/rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle:
            handle.write(data)
    return verify_package(destination, parent, bundle,
                          expected_package_hash=manifest['materialized_package_hash'],
                          transcript=transcript, expected_transcript_hash=expected_transcript_hash)


def execute_installed(package: PackageReceipt, program_hash: str, vector: list[int]) -> list[int]:
    """Execute a data-only installed DSL program through a distinct matrix evaluator.

    Caller must remeasure the package at its verification boundary. This function
    rechecks the selected bytes against the externally obtained package receipt.
    """
    _hash(program_hash, 'program_hash')
    require(type(vector) is list and len(vector) == 4 and all(type(x) is int and -64 <= x <= 64 for x in vector),
            'bounded integer vector required')
    manifest = load_json_strict(package.manifest_bytes)
    rel = 'registry/programs/'+program_hash+'.json'
    matches = [r for r in manifest['files'] if r['path'] == rel]
    require(len(matches) == 1, 'uninstalled program')
    path = package.root/rel
    require(not path.is_symlink() and path.is_file(), 'regular installed program required')
    raw = path.read_bytes()
    require(sha(raw) == matches[0]['sha256'], 'installed program modified')
    p = load_json_strict(raw)
    _validate_program(p)
    require(canonical(p) == raw and digest(p) == program_hash, 'installed program identity')
    return execute_matrix(p, vector)


def execute_matrix(p: dict, vector: list[int]) -> list[int]:
    """Fixed DSL integer evaluator, independently structured from the reference."""
    _validate_program(p)
    require(type(vector) is list and len(vector) == 4 and
            all(type(x) is int and -64 <= x <= 64 for x in vector), 'bounded integer vector required')
    family, v, a, b = p['family'], p['variant']+1, p['parameter_a'], p['parameter_b']
    if family == 'verification_automation_policy':
        return sorted([x+a*v-b for x in vector])
    matrix = [[0]*4 for _ in range(4)]
    offset = [0]*4
    for i in range(4):
        if family == 'adapter_policy': matrix[i][i] = v; offset[i] = a-b
        elif family == 'architecture_policy': matrix[i][(i+v+1)%4] = 1; offset[i] = a*(i+1)+b
        elif family == 'memory_policy': matrix[i][(i+v)%4] = 1; offset[i] = a if i == 0 else 0
        elif family == 'retrieval_policy': matrix[i][(i*v+abs(b))%4] = 1
        elif family == 'optimizer_policy': matrix[i] = [1]*4; offset[i] = a+v*sum(range(1,i+2))-b*(i+1)
    if family == 'planner_policy':
        matrix=[[1,0,0,0],[0,v,0,0],[0,0,1,0],[v,0,0,1]]; offset=[a,0,-b,0]
    elif family == 'tool_policy':
        matrix=[[1,1,0,0],[0,1,-1,0],[0,0,v,0],[0,0,0,1]]; offset=[a,b,0,a-b]
    return [sum(c*x for c,x in zip(row,vector,strict=True))+d for row,d in zip(matrix,offset,strict=True)]
