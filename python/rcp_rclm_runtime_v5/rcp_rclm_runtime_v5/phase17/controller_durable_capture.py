"""Phase17AK fresh durable-authority capture and process-free reconstruction.

The selected witness requests and replies are the exact completed AJ reference
packet. New native lifetimes execute those requests through the durable root;
the root's atomic image and epoch records are additional evidence. Historical
AJ native records never become evidence of a newly executed AK process.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import uuid

from . import controller_witness as aj
from . import controller_durable_authority as durable
from .materialized import require, sha
from .resource_ledger import _no_links
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest

BASE = '0ad2290b81d7b4a314b10dd0bcfa28725be4a452'
AJ_ROOT = 'artifacts/development/phase17aj/op-1395d6ddf5ce/gate'
AJ_PACKET_SHA = 'dd7a8197c66cc88beaa31c4c18dac5c88ced3c6cb754421a80bc94abeb552a2a'
AJ_EXECUTION_SHA = 'e53bc075dd97d2ea0c005bb0ffbb28014e7a5bae73c867452f991cfa454e9ef4'
AJ_SOURCE = '1395d6ddf5ceed54525d2130faa1af2e220dd6a3'
AJ_TREE = '48031d3a94812c796b6b1a3a3802f2ccb86e03aa'
RETAINED_PINS = {AJ_ROOT + '/packet.json': AJ_PACKET_SHA,
                 AJ_ROOT + '/execution.json': AJ_EXECUTION_SHA}
SCHEMA = 'rcp-rclm.phase17ak.controller-durable-authority-packet.v1'
POLICY = 'phase17ak.atomic-durable-authority-reference.v1'
MODULE = 'rcp_rclm_runtime_v5.phase17.controller_durable_capture'
CODE_PATH = 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/controller_durable_capture.py'
RUNTIME_PATH = 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/controller_durable_authority.py'
SOURCE_ROOT = Path(__file__).resolve().parents[4]
MAX_BYTES = 128 * 1024 * 1024
FALSE_CLAIMS = aj.FALSE_CLAIMS
SCOPE = {
    'root': 'explicitly provisioned durable root; atomic paired AJ witness/AI snapshots and monotone incarnation epochs',
    'execution': 'fresh native reference lifetimes, exact unchanged AJ requests and native disk evaluation',
    'provision': 'independently supplied root provision digest; published deterministic reference credentials only',
    'storage': 'SQLite committed transaction and exclusive cooperating lifetime lock on one trusted physical root',
    'refinement': 'generic Lean protocol model plus exact selected trace; no general Python/SQLite/OS refinement',
    'rollback': 'whole trusted-root rollback, root cloning, hostile storage and secret compromise remain external',
    'resource': 'inherited AH declared reference tariff only; durable storage, authentication, tests, proofs and host cost excluded',
    'external_issuer_authenticated': False,
    'physical_execution_attested': False,
    'complete_resource_accounting': False,
    'fresh_worker_sessions': 0,
    'fresh_live_challenges': 0,
    'old_proof_campaigns_rerun': False,
    'promotion_api': False,
}


def _same(actual, expected, message):
    require(canonical(actual) == canonical(expected), message)


def _nonce(name, purpose):
    return sha(('Phase17AK/' + name + '/' + purpose).encode())


def durable_identity(root=SOURCE_ROOT):
    root = Path(root)
    bound = dict(aj.witness_identity(root)['code_sha256'])
    for name in (RUNTIME_PATH, CODE_PATH):
        _no_links(root / name)
        bound[name] = sha((root / name).read_bytes())
    return {'policy': POLICY, 'code_sha256': bound,
            'implementation_sha256': digest(bound), 'external_issuer_authenticated': False}


def _execution(raw):
    require(type(raw) is bytes and sha(raw) == AJ_EXECUTION_SHA, 'exact completed AJ execution required')
    value = load_json_strict(raw, require_canonical=False)
    require(value['source_commit'] == AJ_SOURCE and value['source_tree'] == AJ_TREE and
            value['completed'] is True and value['witnessed_authority_head_checked'] is True and
            value['witnessed_controller_issuance_checked'] is True and
            value['proof_mode'] == 'real_pinned_lean_completed_stage_lineage' and
            len(value['source_sha256']) == 575, 'completed AJ identity or scope differs')
    return value


def _retained(root):
    root = Path(root)
    retained = {}
    for name, wanted in RETAINED_PINS.items():
        _no_links(root / name)
        raw = (root / name).read_bytes()
        require(sha(raw) == wanted, 'retained AJ input differs: ' + name)
        retained[name] = raw
    execution = _execution(retained[AJ_ROOT + '/execution.json'])
    for name, wanted in execution['source_sha256'].items():
        _no_links(root / name)
        require(sha((root / name).read_bytes()) == wanted, 'inherited AJ source changed: ' + name)
    return retained[AJ_ROOT + '/packet.json'], execution


@lru_cache(maxsize=1)
def _witness_from_bytes(raw):
    """Reuse only a fully validated immutable AJ packet, never native results."""
    return aj.PreparedControllerWitness(raw)


def load_witness(root):
    raw, execution = _retained(root)
    return _witness_from_bytes(raw), execution


def _root_provision(witness, case):
    return durable.make_root_provision(witness.controller_authority(), case['provision'],
        aj.PUBLIC_FIXTURE_KEY, expected_provision_sha256=case['provision_sha256'],
        authority_id='phase17ak.reference.' + case['name'],
        provisioning_nonce=_nonce(case['name'], 'provision'))


def _write(path, raw):
    path = Path(path); _no_links(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def _argv(python, root, directory, execution, export, root_pin, nonce):
    return [python, '-B', '-m', MODULE, '--serve', '--root', str(root),
        '--directory', str(directory), '--execution-directory', str(execution),
        '--export', str(export), '--root-pin', root_pin, '--boot-nonce', nonce]


class NativeTransport:
    def __init__(self, root, directory, execution, export, native, *, root_pin, boot_nonce):
        self.native = Path(native); self.native.mkdir(parents=True)
        self.export = Path(export)
        self._closed = False; self._reader_error = None; self._timed_out = False
        self._queue = queue.Queue()
        self._stdin = (self.native / 'stdin.bin').open('xb', buffering=0)
        self._stdout = (self.native / 'stdout.bin').open('xb', buffering=0)
        self._stderr = (self.native / 'stderr.bin').open('xb', buffering=0)
        root = Path(root).absolute()
        argv = _argv(sys.executable, root, directory, execution, export, root_pin, boot_nonce)
        self.started = datetime.now(timezone.utc).isoformat(); self.started_ns = time.monotonic_ns()
        self.start = {'schema': 'phase17ak.durable-native-start.v1', 'invocation_id': uuid.uuid4().hex,
            'argv': argv, 'source_root': str(root), 'authority_directory': str(directory),
            'execution_directory': str(execution), 'export_path': str(export),
            'root_provision_sha256': root_pin, 'boot_nonce': boot_nonce,
            'aj_packet_sha256': AJ_PACKET_SHA, 'durable_identity': durable_identity(root),
            'python_sha256': sha(Path(sys.executable).read_bytes()), 'started_at_utc': self.started}
        _write(self.native / 'start.json', canonical(self.start))
        environment = os.environ.copy()
        environment['PYTHONPATH'] = os.pathsep.join(str(root / 'python' / ('rcp_rclm_runtime_v' + str(v)))
                                                   for v in (2, 3, 4, 5))
        environment['PYTHONDONTWRITEBYTECODE'] = '1'; environment['PYTHONUTF8'] = '1'
        self.process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self._stderr, cwd=root, env=environment)

        def reader():
            try:
                while True:
                    line = self.process.stdout.readline(aj.MAX_WIRE_BYTES + 1)
                    if not line:
                        self._queue.put(None); return
                    require(len(line) <= aj.MAX_WIRE_BYTES and line.endswith(b'\n'), 'durable response framing bound')
                    self._stdout.write(line); self._queue.put(line)
            except BaseException as error:
                self._reader_error = str(error); self._queue.put(None)
        self._thread = threading.Thread(target=reader, daemon=True); self._thread.start()

    def call(self, request):
        raw = canonical(request) + b'\n'
        require(len(raw) <= aj.MAX_WIRE_BYTES, 'durable request framing bound')
        self._stdin.write(raw); self.process.stdin.write(raw); self.process.stdin.flush()
        try:
            line = self._queue.get(timeout=600)
        except queue.Empty:
            self._timed_out = True; self.process.kill()
            raise ValueError('durable reference response timed out')
        require(line is not None and self._reader_error is None, 'durable process ended without response')
        result = load_json_strict(line[:-1])
        require(canonical(result) + b'\n' == line, 'noncanonical durable response')
        return result

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.process.stdin.close()
        except (OSError, BrokenPipeError):
            pass
        try:
            code = self.process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            self._timed_out = True; self.process.kill(); code = self.process.wait()
        self._thread.join(timeout=30)
        self.process.stdout.close()
        self._stdin.close(); self._stdout.close(); self._stderr.close()
        exported = None
        if code == 0 and not self._timed_out and not self._thread.is_alive():
            _no_links(self.export)
            require(self.export.is_file() and self.export.stat().st_size <= MAX_BYTES,
                    'successful native lifetime lacks its complete original root export')
            raw = self.export.read_bytes()
            require(canonical(load_json_strict(raw)) == raw, 'native root export is not canonical')
            _write(self.native / 'export.json', raw)
            exported = {'bytes': len(raw), 'sha256': sha(raw)}
        result = {'schema': 'phase17ak.durable-native-result.v1',
            'invocation_id': self.start['invocation_id'], 'pid': self.process.pid,
            'started_at_utc': self.started, 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
            'elapsed_ns': time.monotonic_ns() - self.started_ns,
            'returncode': code, 'timed_out': self._timed_out, 'native_wait_completed': True,
            'reader_finished': not self._thread.is_alive(), 'reader_error': self._reader_error,
            'start_sha256': sha((self.native / 'start.json').read_bytes()),
            'export': exported,
            'streams': {name: {'bytes': (self.native / name).stat().st_size,
                              'sha256': sha((self.native / name).read_bytes())}
                        for name in ('stdin.bin', 'stdout.bin', 'stderr.bin')}}
        _write(self.native / 'native-result.json', canonical(result))
        require(code == 0 and not self._timed_out and not self._thread.is_alive() and
                self._reader_error is None and not (self.native / 'stderr.bin').read_bytes(),
                'durable native lifetime did not complete cleanly; preserve original records')


def _serve(args):
    root = Path(args.root).absolute()
    require(root == SOURCE_ROOT, 'native durable source root differs')
    # Native execution needs AI's complete prepared domain. The parent checks
    # the full AJ packet; this process independently pins its original bytes
    # and all AJ source bindings, then fully validates the enclosed AI packet.
    # It does not need to repeat AJ's path-free reference interaction campaign.
    raw, _ = _retained(root)
    packet = load_json_strict(raw)
    authority = aj.ai.PreparedControllerAuthority(canonical(packet['controller_authority_packet']))
    with durable.DurableAuthority(Path(args.directory), authority,
        aj.PUBLIC_FIXTURE_KEY, expected_root_provision_sha256=args.root_pin,
        execution_directory=Path(args.execution_directory), boot_nonce=args.boot_nonce) as authority:
        while True:
            raw = sys.stdin.buffer.readline(aj.MAX_WIRE_BYTES + 1)
            if not raw:
                break
            require(len(raw) <= aj.MAX_WIRE_BYTES and raw.endswith(b'\n'), 'durable request framing differs')
            value = load_json_strict(raw[:-1])
            require(canonical(value) + b'\n' == raw, 'durable request is not canonical')
            response = authority.dispatch(value)
            sys.stdout.buffer.write(canonical(response) + b'\n'); sys.stdout.buffer.flush()
        _write(Path(args.export), canonical(authority.export_evidence()))


def _source_wires(witness, name):
    raw = aj.witness_journal_images(witness.packet)[name + '-rpc.jsonl']
    return [load_json_strict(line) for line in raw.splitlines()]


def _validate_case(witness, case, item):
    require(set(item) == {'name', 'ai_case_index', 'root_provision_sha256', 'evidence', 'wire'},
            'exact durable case fields required')
    require(item['name'] == case['name'] and item['ai_case_index'] == case['ai_case_index'],
            'durable case identity differs')
    root_provision = _root_provision(witness, case); root_pin = digest(root_provision)
    require(item['root_provision_sha256'] == root_pin, 'durable case root pin differs')
    evidence = item['evidence']
    _same(evidence['root_provision'], root_provision, 'durable independent provision differs')
    durable.verify_evidence(evidence, witness.controller_authority(), aj.PUBLIC_FIXTURE_KEY,
                            expected_root_provision_sha256=root_pin)
    images = aj.witness_journal_images(witness.packet)
    witness_lines = images[case['name'] + '-witness.jsonl'].splitlines(keepends=True)
    authority_lines = images[case['name'] + '-authority.jsonl'].splitlines(keepends=True)
    authority_prefixes = {}
    for i, line in enumerate(authority_lines):
        row = load_json_strict(line[:-1])
        authority_prefixes[row['hash']] = b''.join(authority_lines[:i+1])
    events = evidence['events']
    require(len(events) == len(witness_lines), 'durable/AJ event inventory differs')
    cursors = {}
    for serial, record in enumerate(events):
        expected_witness = b''.join(witness_lines[:serial+1])
        row = load_json_strict(witness_lines[serial][:-1])
        authority_head = row['body']['authority_head_after']
        require(record['witness_journal'].encode() == expected_witness and
                record['authority_journal'].encode() == authority_prefixes[authority_head],
                'durable snapshot does not bind the exact AJ witness and authority prefix')
        event = record['event']; after = event['after']
        require(event['serial'] == serial and after['witness_cursor'] == {
            'revision': serial, 'witness_head': row['hash'], 'authority_head': authority_head},
            'durable event does not name the exact AJ formal state')
        cursors[serial] = {'root_provision_sha256': root_pin, 'epoch': event['epoch'],
            'serial': serial, 'root_head': event['hash'], 'image_sha256': after['image_sha256'],
            'witness_cursor': after['witness_cursor']}
    expected_wires = _source_wires(witness, case['name'])
    require(len(item['wire']) == len(expected_wires), 'durable wire inventory differs')
    boots = {boot['name']: boot for boot in witness.packet['native_boots'] if boot['case'] == case['name']}
    current = None; last_boot = None
    for wire, expected in zip(item['wire'], expected_wires, strict=True):
        require(set(wire) == {'boot', 'request', 'response'} and wire['boot'] == expected['boot'],
                'durable request native attribution differs')
        if wire['boot'] != last_boot:
            boot = boots[wire['boot']]
            matches = [e for e in events if e['event']['kind'] == 'reopen' and
                       e['event']['boot_nonce'] == boot['boot_nonce']]
            require(len(matches) == 1, 'durable boot has no unique committed reopen')
            current = cursors[matches[0]['event']['serial']]; last_boot = wire['boot']
        op = expected['request']['body']['op']
        wanted = durable.make_request(root_pin, aj.PUBLIC_FIXTURE_KEY, expected['request'],
                                       expected_cursor=None if op == 'read' else current)
        _same(wire['request'], wanted, 'durable envelope does not bind exact AJ request/current root cursor')
        payload = durable.verify_reply(wire['response'], wire['request'], key=aj.PUBLIC_FIXTURE_KEY,
                                         expected_root_provision_sha256=root_pin)
        _same(wire['response']['witness_response'], expected['response'], 'new native AJ response differs from checked reference')
        aj_payload = expected['response']['payload']
        target = cursors[aj_payload['state']['revision']]
        _same(payload['cursor'], target, 'durable reply names an uncommitted or different root image')
        require(payload['commit_applied'] is (op != 'read' and aj_payload['ok'] is True),
                'durable acknowledgement misstates its commit')
        current = target
    _same(evidence['final_cursor'], current, 'durable final cursor differs from last native response')


def _summary(witness, cases):
    return {'durable_cases': len(cases), 'reference_authority_lifetimes': 5,
        'committed_root_snapshots': sum(len(c['evidence']['events']) for c in cases),
        'paired_witness_authority_images': sum(len(c['evidence']['events']) for c in cases),
        'nonce_bound_reference_requests': sum(len(c['wire']) for c in cases),
        'completed_reference_sessions': 3, 'issued_reference_leases': 4,
        'denied_reference_leases': 1, 'retained_interrupted_reservations': 1,
        'main_reserved_reference_cost': 7168, 'main_actual_reference_cost': 1008,
        'external_issuer_authenticated': False, 'physical_clone_exclusivity_established': False,
        'complete_resource_accounting': False, 'fresh_worker_sessions': 0,
        'fresh_live_challenges': 0, 'formal_acceptance_required': True}


def validate_packet(packet):
    require(type(packet) is dict and set(packet) == {'schema', 'policy', 'base_commit',
        'witness_packet', 'retained_sha256', 'inherited_source_sha256', 'durable_identity',
        'durable_cases', 'native_boots', 'summary', 'scope', 'claims'}, 'exact durable packet fields required')
    require(packet['schema'] == SCHEMA and packet['policy'] == POLICY and packet['base_commit'] == BASE,
            'durable packet identity differs')
    _same(packet['scope'], SCOPE, 'durable scope differs')
    _same(packet['claims'], {n: False for n in FALSE_CLAIMS}, 'durable claim escalation')
    _same(packet['retained_sha256'], RETAINED_PINS, 'retained AJ pins differ')
    witness, execution = load_witness(SOURCE_ROOT)
    require(sha(canonical(packet['witness_packet'])) == AJ_PACKET_SHA and
            canonical(packet['witness_packet']) == witness.packet_bytes, 'durable inherited AJ packet differs')
    _same(packet['inherited_source_sha256'], execution['source_sha256'], 'inherited AJ source bindings differ')
    _same(packet['durable_identity'], durable_identity(), 'durable implementation identity differs')
    cases = packet['durable_cases']
    require(type(cases) is list and len(cases) == 3, 'three durable reference cases required')
    for case, item in zip(witness.packet['witness_cases'], cases, strict=True):
        _validate_case(witness, case, item)
    wanted_boots = []
    for boot in witness.packet['native_boots']:
        case = next(c for c in cases if c['name'] == boot['case'])
        wires = [w for w in case['wire'] if w['boot'] == boot['name']]
        wanted_boots.append({'name': boot['name'], 'case': boot['case'], 'boot_nonce': boot['boot_nonce'],
            'root_provision_sha256': case['root_provision_sha256'],
            'request_sha256': [sha(canonical(w['request']) + b'\n') for w in wires],
            'response_sha256': [sha(canonical(w['response']) + b'\n') for w in wires]})
    _same(packet['native_boots'], wanted_boots, 'durable native boot bindings differ')
    _same(packet['summary'], _summary(witness, cases), 'durable selected counts differ')
    return witness


@dataclass(frozen=True, slots=True)
class PreparedControllerDurableAuthority:
    packet_bytes: bytes
    _witness: aj.PreparedControllerWitness = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= MAX_BYTES,
                'bounded immutable durable packet required')
        packet = load_json_strict(self.packet_bytes)
        require(canonical(packet) == self.packet_bytes, 'canonical durable packet required')
        object.__setattr__(self, '_witness', validate_packet(packet))

    @property
    def packet(self):
        return load_json_strict(self.packet_bytes)

    def controller_witness(self):
        return self._witness


def prepare_controller_durable_authority(root, packages):
    root, packages = Path(root).absolute(), Path(packages).absolute()
    _no_links(packages)
    require(root == SOURCE_ROOT and not packages.exists() and root not in packages.parents,
            'new external durable capture directory required')
    witness, execution = load_witness(root); identity = durable_identity(root)
    packages.mkdir(parents=True)
    cases = []; native_boots = []
    for case in witness.packet['witness_cases']:
        name = case['name']; root_dir = packages / 'durable-authorities' / name
        bootstrap = durable.provision_root(root_dir, witness.controller_authority(), case['provision'],
            aj.PUBLIC_FIXTURE_KEY, expected_provision_sha256=case['provision_sha256'],
            authority_id='phase17ak.reference.' + name, provisioning_nonce=_nonce(name, 'provision'))
        root_pin = digest(_root_provision(witness, case))
        require(bootstrap['root_provision_sha256'] == root_pin, 'fresh root provisioning differs')
        wire = []; evidence = None
        for boot in (b for b in witness.packet['native_boots'] if b['case'] == name):
            export = packages / 'durable-exports' / (boot['name'] + '.json')
            transport = NativeTransport(root, root_dir, packages / 'durable-executions' / boot['name'],
                export, packages / 'durable-native' / boot['name'], root_pin=root_pin, boot_nonce=boot['boot_nonce'])
            current = None
            try:
                for expected in (w for w in _source_wires(witness, name) if w['boot'] == boot['name']):
                    op = expected['request']['body']['op']
                    require(op == 'read' or current is not None, 'native lifetime must obtain current root cursor first')
                    supplied = durable.make_request(root_pin, aj.PUBLIC_FIXTURE_KEY, expected['request'],
                        expected_cursor=None if op == 'read' else current)
                    response = transport.call(supplied)
                    payload = durable.verify_reply(response, supplied, key=aj.PUBLIC_FIXTURE_KEY,
                                                    expected_root_provision_sha256=root_pin)
                    _same(response['witness_response'], expected['response'], 'fresh native AJ reference result differs')
                    current = payload['cursor']; wire.append({'boot': boot['name'], 'request': supplied, 'response': response})
            finally:
                transport.close()
            exported_raw = (transport.native / 'export.json').read_bytes()
            require(export.read_bytes() == exported_raw, 'original root export changed after native completion')
            evidence = load_json_strict(exported_raw)
            durable.verify_evidence(evidence, witness.controller_authority(), aj.PUBLIC_FIXTURE_KEY,
                                    expected_root_provision_sha256=root_pin)
            selected = [w for w in wire if w['boot'] == boot['name']]
            native_boots.append({'name': boot['name'], 'case': name, 'boot_nonce': boot['boot_nonce'],
                'root_provision_sha256': root_pin,
                'request_sha256': [sha(canonical(w['request']) + b'\n') for w in selected],
                'response_sha256': [sha(canonical(w['response']) + b'\n') for w in selected]})
        item = {'name': name, 'ai_case_index': case['ai_case_index'], 'root_provision_sha256': root_pin,
                'evidence': evidence, 'wire': wire}
        _validate_case(witness, case, item); cases.append(item)
    packet = {'schema': SCHEMA, 'policy': POLICY, 'base_commit': BASE, 'witness_packet': witness.packet,
        'retained_sha256': RETAINED_PINS, 'inherited_source_sha256': execution['source_sha256'],
        'durable_identity': identity, 'durable_cases': cases, 'native_boots': native_boots,
        'summary': _summary(witness, cases), 'scope': SCOPE, 'claims': {n: False for n in FALSE_CLAIMS}}
    prepared = PreparedControllerDurableAuthority(canonical(packet))
    verify_durable_native_records(packages / 'durable-native', prepared.packet)
    require(durable_identity(root) == identity, 'durable implementation changed during capture')
    return prepared


def verify_durable_native_records(directory, packet):
    directory = Path(directory); _no_links(directory)
    require(packet['schema'] == SCHEMA and packet['base_commit'] == BASE, 'exact AK packet required')
    files = ('start.json', 'native-result.json', 'stdin.bin', 'stdout.bin', 'stderr.bin', 'export.json')
    expected = {b['name'] + '/' + n for b in packet['native_boots'] for n in files}
    actual = set(); directories = set()
    for path in directory.rglob('*'):
        _no_links(path)
        if path.is_file(): actual.add(path.relative_to(directory).as_posix())
        elif path.is_dir(): directories.add(path.relative_to(directory).as_posix())
        else: raise ValueError('nonregular durable native evidence entry')
    require(actual == expected and directories == {b['name'] for b in packet['native_boots']},
            'durable native inventory differs')
    for boot in packet['native_boots']:
        here = directory / boot['name']
        start_raw = (here / 'start.json').read_bytes(); result_raw = (here / 'native-result.json').read_bytes()
        start, result = load_json_strict(start_raw), load_json_strict(result_raw)
        require(canonical(start) == start_raw and canonical(result) == result_raw, 'noncanonical native metadata')
        require(set(start) == {'schema','invocation_id','argv','source_root','authority_directory',
            'execution_directory','export_path','root_provision_sha256','boot_nonce','aj_packet_sha256',
            'durable_identity','python_sha256','started_at_utc'} and
            set(result) == {'schema','invocation_id','pid','started_at_utc','finished_at_utc','elapsed_ns',
            'returncode','timed_out','native_wait_completed','reader_finished','reader_error','start_sha256','export','streams'},
            'exact native metadata required')
        require(start['schema'] == 'phase17ak.durable-native-start.v1' and
            result['schema'] == 'phase17ak.durable-native-result.v1' and
            result['invocation_id'] == start['invocation_id'] and result['start_sha256'] == sha(start_raw) and
            type(result['pid']) is int and result['pid'] > 0 and type(result['returncode']) is int and
            result['returncode'] == 0 and result['timed_out'] is False and result['native_wait_completed'] is True and
            result['reader_finished'] is True and result['reader_error'] is None,
            'native durable lifetime lacks clean observed completion')
        require(type(start['invocation_id']) is str and len(start['invocation_id']) == 32 and
            all(c in '0123456789abcdef' for c in start['invocation_id']) and
            result['started_at_utc'] == start['started_at_utc'] and type(result['elapsed_ns']) is int and
            result['elapsed_ns'] >= 0 and datetime.fromisoformat(result['finished_at_utc']) >=
            datetime.fromisoformat(result['started_at_utc']), 'native durable identity/time differs')
        require(start['root_provision_sha256'] == boot['root_provision_sha256'] and
            start['boot_nonce'] == boot['boot_nonce'] and start['aj_packet_sha256'] == AJ_PACKET_SHA,
            'native durable provision differs')
        _same(start['durable_identity'], packet['durable_identity'], 'native durable source differs')
        argv = start['argv']
        require(type(argv) is list and bool(argv) and all(type(a) is str and a for a in argv) and
            argv == _argv(argv[0], start['source_root'], start['authority_directory'],
            start['execution_directory'], start['export_path'], boot['root_provision_sha256'], boot['boot_nonce']),
            'native durable command differs')
        require(type(start['python_sha256']) is str and len(start['python_sha256']) == 64 and
                all(c in '0123456789abcdef' for c in start['python_sha256']),
                'native interpreter identity missing')
        case = next(c for c in packet['durable_cases'] if c['name'] == boot['case'])
        wire = [w for w in case['wire'] if w['boot'] == boot['name']]
        require(wire, 'native durable lifetime has no reference requests')
        last_cursor = wire[-1]['response']['cursor']
        original_export = dict(case['evidence'])
        original_export['events'] = case['evidence']['events'][:last_cursor['serial'] + 1]
        original_export['final_cursor'] = last_cursor
        export_raw = canonical(original_export)
        require((here / 'export.json').read_bytes() == export_raw,
                'original native root export differs from exact authoritative prefix')
        _same(result['export'], {'bytes': len(export_raw), 'sha256': sha(export_raw)},
              'native root export identity differs')
        wanted = {'stdin.bin': b''.join(canonical(w['request']) + b'\n' for w in wire),
                  'stdout.bin': b''.join(canonical(w['response']) + b'\n' for w in wire), 'stderr.bin': b''}
        require(set(result['streams']) == set(wanted), 'native durable stream inventory differs')
        for name, raw in wanted.items():
            require((here / name).read_bytes() == raw, 'native durable wire differs from semantic packet')
            _same(result['streams'][name], {'bytes':len(raw),'sha256':sha(raw)}, 'native durable stream hash differs')
    return {name: sha((directory / name).read_bytes()) for name in sorted(expected)}


def evidence_images(packet):
    return {case['name'] + '.json': canonical(case['evidence']) for case in packet['durable_cases']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true', required=True)
    for name in ('root','directory','execution-directory','export','root-pin','boot-nonce'):
        parser.add_argument('--' + name, required=True)
    _serve(parser.parse_args())
