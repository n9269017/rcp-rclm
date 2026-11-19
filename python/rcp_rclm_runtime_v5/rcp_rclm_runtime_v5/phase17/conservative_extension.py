"""Phase17G: executable, immutable conservative registry interpretation.

This is an inactive prospective package. It has no promotion method. All trust
anchors come from the historical bootstrap and the externally retained sealed
transcript. The complete root and recursive-productivity claims stay false.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from .bootstrap import HistoricalPredecessor, _validate_program
from .controller import ControlError, FIXED_VERIFIER
from .materialized import (PackageReceipt, MANIFEST, require, sha, snapshot,
                           verify_package, execute_matrix)
from .challenge_protocol import execute_reference
from .successor_evidence import prepare_successor, FALSE_CLAIMS

SCHEMA = 'runtime.v5.phase17.conservative-registry.v1'
MAX_ENTRIES = 256
VECTORS = ((0, 0, 0, 0), (-64, -1, 0, 64), (64, 63, -63, -64),
           (1, 2, 3, 4), (-3, 0, 5, 11), (7, 7, 7, 7))


def _identifier(value: str) -> str:
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
            'canonical program identifier required')
    return value


@dataclass(frozen=True)
class RegistryImage:
    """Detached immutable program bytes, never caller-owned mutable dictionaries."""
    entries: tuple[tuple[str, bytes], ...]

    def __post_init__(self) -> None:
        require(type(self.entries) is tuple and 0 < len(self.entries) <= MAX_ENTRIES,
                'bounded immutable registry required')
        keys = []
        for entry in self.entries:
            require(type(entry) is tuple and len(entry) == 2, 'registry pair shape')
            key, raw = entry
            _identifier(key)
            require(type(raw) is bytes and 0 < len(raw) <= 4096, 'immutable bounded program bytes required')
            try:
                program = load_json_strict(raw)
            except ValueError as exc:
                raise ControlError('noncanonical installed program') from exc
            _validate_program(program)
            require(canonical(program) == raw and digest(program) == key, 'program identity mismatch')
            keys.append(key)
        require(len(keys) == len(set(keys)), 'registry identifiers must be unique')

    def lookup(self, key: str) -> bytes | None:
        _identifier(key)
        for identifier, raw in self.entries:
            if key == identifier:
                return raw
        return None

    def execute(self, key: str, vector: list[int]) -> list[int]:
        require(type(vector) is list and len(vector) == 4 and
                all(type(x) is int and -64 <= x <= 64 for x in vector), 'bounded four-integer input required')
        raw = self.lookup(key)
        require(raw is not None, 'unregistered program')
        return execute_matrix(load_json_strict(raw), vector)

    def extend(self, key: str, raw: bytes) -> RegistryImage:
        require(self.lookup(key) is None, 'extension shadows an inherited program')
        return RegistryImage((*self.entries, (key, raw)))

    def retract(self, key: str) -> RegistryImage:
        require(self.lookup(key) is not None, 'retraction key is absent')
        return RegistryImage(tuple(e for e in self.entries if e[0] != key))

    def to_json(self) -> list[dict]:
        return [{'key': k, 'program_utf8': b.decode('utf-8')} for k, b in self.entries]


def registry_from_files(files: dict[str, bytes]) -> RegistryImage:
    """Called after independent physical verification; no user-supplied entry list."""
    registry = load_json_strict(files['registry/manifest.json'])
    inherited = registry['inherited_program_hashes']
    added = registry['candidate_program_hash']
    require(type(inherited) is list and len(inherited) == len(set(inherited)), 'duplicate inherited identifiers')
    keys = list(inherited) + ([] if added is None else [added])
    require(len(keys) == len(set(keys)), 'candidate shadows inherited identifier')
    for key in keys:
        _identifier(key)
    expected = {'registry/programs/' + key + '.json' for key in keys}
    actual = {name for name in files if name.startswith('registry/programs/')}
    require(actual == expected, 'physical registry has an omitted or extra program')
    return RegistryImage(tuple((k, files['registry/programs/'+k+'.json']) for k in keys))


def extract_predecessor(candidate_files: dict[str, bytes], *, added_key: str,
                        metadata: tuple[tuple[str, bytes], ...]) -> dict[str, bytes]:
    """A constructive pure retraction; no old tensor/program bytes are inputs.

    Only two previous manifest values are retained as undo metadata. All other
    predecessor bytes must be extracted from the candidate. No active store is
    touched. The caller compares the result with the measured predecessor.
    """
    _identifier(added_key)
    require(type(metadata) is tuple and len(metadata) == 2 and
            {p for p, _ in metadata} == {MANIFEST, 'registry/manifest.json'} and
            all(type(b) is bytes for _, b in metadata), 'exact two-manifest undo data required')
    name = 'registry/programs/'+added_key+'.json'
    require(name in candidate_files, 'missing added program')
    restored = {p: b for p, b in candidate_files.items() if p != name}
    restored.update(dict(metadata))
    return restored


def protected_image(files: dict[str, bytes], names: tuple[str, ...]) -> bytes:
    """Injective length framing for a selected exact byte projection."""
    require(type(names) is tuple and list(names) == sorted(set(names)), 'unique sorted projection names required')
    chunks = [b'phase17g.protected-image.v1\0', len(names).to_bytes(8, 'big')]
    for name in names:
        require(name in files and type(files[name]) is bytes, 'projection entry missing')
        encoded = name.encode('utf-8')
        raw = files[name]
        chunks.extend((len(encoded).to_bytes(8,'big'), encoded, len(raw).to_bytes(8,'big'), raw))
    return b''.join(chunks)


@dataclass(frozen=True)
class PreparedConservative:
    packet_bytes: bytes

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)


def prepare_conservative(predecessor: PackageReceipt, candidate: PackageReceipt,
                         parent: HistoricalPredecessor, *, bundle: Path, capture: Path,
                         transcript: bytes, expected_transcript_hash: str) -> PreparedConservative:
    """Fresh physical/semantic checks; no supplied pass-record authorizes a result."""
    earlier = prepare_successor(predecessor, candidate, parent, bundle=bundle, capture=capture,
                                transcript=transcript, expected_transcript_hash=expected_transcript_hash)
    packet = earlier.packet
    before_files, after_files = snapshot(predecessor.root), snapshot(candidate.root)
    before, after = registry_from_files(before_files), registry_from_files(after_files)
    key = packet['bindings']['program_hash']
    raw = after.lookup(key)
    require(raw is not None and before.extend(key, raw) == after, 'not the exact conservative registry extension')
    require(after.retract(key) == before, 'registry inverse failed')
    undo = tuple((p, before_files[p]) for p in sorted((MANIFEST, 'registry/manifest.json')))
    require(extract_predecessor(after_files, added_key=key, metadata=undo) == before_files,
            'physical inverse did not reconstruct the predecessor')
    protected_names = tuple(r['path'] for r in packet['projection']['protected_before'])
    protected_before = protected_image(before_files, protected_names)
    protected_after = protected_image(after_files, protected_names)
    require(protected_before == protected_after, 'protected semantic image changed')
    checks = []
    for identifier, encoded in before.entries:
        require(after.lookup(identifier) == encoded, 'inherited code changed')
        for values in VECTORS:
            v = list(values)
            old = before.execute(identifier, v)
            new = after.execute(identifier, v)
            reference = execute_reference(load_json_strict(encoded), v)
            require(old == new == reference, 'inherited operational semantics changed')
            checks.append({'program_hash':identifier,'input':v,'before':old,'after':new,'reference':reference})
    probes = packet['candidate_evaluation']['probe_checks']
    candidate_checks=[]
    for row in probes:
        actual=after.execute(key,row['input'])
        require(actual==row['expected'],'candidate dispatch failed sealed probe')
        candidate_checks.append({'input':row['input'],'actual':actual,'expected':row['expected']})
    require(snapshot(predecessor.root)==before_files and snapshot(candidate.root)==after_files,
            'package changed during conservative check')
    result = {
        'schema_id': SCHEMA,
        'scope': 'inactive_single_append_only_registry; not full RCLM root acceptance',
        'bindings': packet['bindings'], 'fixed_verifier_hash': FIXED_VERIFIER,
        'phase17f_packet_sha256':sha(earlier.packet_bytes),
        'registry_before': before.to_json(), 'registry_after': after.to_json(),
        # Authoritative manifest order: inherited entries followed by new key.
        # Physical directory enumeration order never defines dispatch order.
        'logical_append_order': before.to_json()+[{'key':key,'program_utf8':raw.decode('utf-8')}],
        'new_key':key, 'new_program_utf8':raw.decode('utf-8'),
        'python_registry_order':'manifest_inherited_order_then_fresh_entry',
        'lean_registry_order':'inherited_order_then_fresh_entry',
        'protected_files':packet['projection']['protected_before'],
        'protected_file_count':len(packet['projection']['protected_before']),
        'protected_image_sha256':sha(protected_before),'protected_image_bytes':len(protected_before),
        'physical_inverse_exact':True, 'inverse_undo_metadata_files':2,
        'protected_image_mapping':'concatenated path/length/framed exact bytes of protected files; excluded manifests are undo metadata',
        'query_domain':'registered program hash and four integers in [-64,64]',
        'inherited_execution_checks':checks, 'candidate_execution_checks':candidate_checks,
        'search_used':packet['search_used'],'search_budget':packet['search_budget'],
        'resource_scope':'candidate evaluation credits only; no total resource accounting',
        'recursive_task_ids':packet['recursive_before'],
        'operational_recursive_tasks_recertified':[],
        'prior_scoped_recursive_probe_count':3,
        'base_kernel_scope':'whole protected-image equality; exact append/retraction; registry-length progress; credit residual',
        'semantic_limits':['not a quantum-information or thermodynamic refinement',
                           'not full learned/autonomous obligations',
                           'not operational recertification of 19 recursive abilities'],
        'trusted_binding_assumptions':['Python measurement, parser and literal extraction',
                                      'fixed trusted interpreter; immutable detached program bytes',
                                      'external transcript anchor, not entropy or event-time attestation'],
        'claims':{k:False for k in FALSE_CLAIMS},
    }
    return PreparedConservative(canonical(result))
