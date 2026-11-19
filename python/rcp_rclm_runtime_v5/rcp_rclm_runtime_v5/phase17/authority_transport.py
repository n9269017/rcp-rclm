"""Phase17AM authenticated AL dispatch and independently retained client anchor.

TLS/OpenSSL, the OS, source protection, and anchor durability are trusted
dependencies. Reference keys and a same-principal service are not an independent
production deployment. Header verification proves continuity from a supplied
anchor, not the impossibility of jointly rolling back that anchor and the root.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import secrets
import socket
import ssl
import struct
import threading

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import durable_campaign as al
from . import controller_durable_authority as ak
from .resource_ledger import ResourceError, ResourceExhausted, canonical, sha, exact, require, digest, nat, _no_links
from .authority_transport_pki import certificate_der

SOURCE_ROOT = Path(__file__).resolve().parents[4]
COMMISSION_SCHEMA = 'phase17am.authority-commission.v1'
REQUEST_SCHEMA = 'phase17am.authority-request.v1'
RESPONSE_SCHEMA = 'phase17am.authority-response.v1'
ANCHOR_SCHEMA = 'phase17am.client-anchor.v1'
NATIVE_SCHEMA = 'phase17am.tls-native.v1'
MAX_FRAME = 1024 * 1024
MAX_CONNECTIONS = 128
MAX_RESOLVED = 128
OPERATIONS = ('read', 'run')
SCRIPTS = ('scripts/phase17_authority_transport_service.py',
           'scripts/phase17_authority_transport_client.py',
           'scripts/phase17_authority_transport_probe.py',
           'scripts/phase17_authority_isolation_probe.py')
EVENT_FIELDS = {'schema', 'kind', 'serial', 'epoch', 'previous_root_head',
    'root_provision_sha256', 'boot_nonce', 'request', 'session_sha256',
    'journal_sha256', 'snapshot_sha256', 'root_head'}


def _copy(value):
    return load_json_strict(canonical(value))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _same(a, b, message):
    require(canonical(a) == canonical(b), message)


def _new(path, data):
    path = Path(path); _no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        require(stream.write(data) == len(data), 'short AM evidence write')
        stream.flush(); os.fsync(stream.fileno())


def _replace(path, value):
    path = Path(path); _no_links(path)
    require(path.is_file(), 'independently provisioned anchor missing')
    temporary = path.with_name(path.name + '.pending-' + secrets.token_hex(12))
    _new(temporary, canonical(value))
    os.replace(temporary, path)
    ak._directory_sync(path.parent)


def transport_identity(source_root=SOURCE_ROOT):
    root = Path(source_root).absolute()
    result = dict(al.implementation_identity(root)['code_sha256'])
    for name in SCRIPTS:
        path = root / name; _no_links(path)
        require(path.is_file(), 'fixed AM script missing')
        result[name] = sha(path.read_bytes())
    return {'code_sha256': result, 'implementation_sha256': sha(canonical(result))}


def _pem(path):
    path = Path(path); _no_links(path)
    raw = path.read_bytes()
    require(len(raw) <= 32768 and raw.count(b'-----BEGIN CERTIFICATE-----') == 1 and
            raw.count(b'-----END CERTIFICATE-----') == 1, 'one bounded PEM certificate required')
    der = ssl.PEM_cert_to_DER_cert(raw.decode('ascii'))
    return raw.decode('ascii'), sha(der)


def make_commission(source_root, root_pin, ca_pem, server_pem, client_pem, server_name='localhost'):
    digest(root_pin)
    require(type(server_name) is str and 0 < len(server_name) <= 253 and
            '\x00' not in server_name, 'fixed TLS server name required')
    ca, ca_hash = _pem(ca_pem)
    server, server_hash = _pem(server_pem)
    client, client_hash = _pem(client_pem)
    return {'schema': COMMISSION_SCHEMA, 'root_provision_sha256': root_pin,
        'tls_version': 'TLSv1.3', 'server_name': server_name,
        'ca_certificate_pem': ca, 'ca_certificate_sha256': ca_hash,
        'server_certificate_pem': server, 'server_certificate_sha256': server_hash,
        'client_certificate_pem': client, 'client_certificate_sha256': client_hash,
        'operations': list(OPERATIONS), 'implementation': transport_identity(source_root),
        'independently_protected_deployment_established': False,
        'global_authority_exclusivity_established': False,
        'complete_resource_accounting': False}


def commission_digest(commission):
    return sha(canonical(commission))


def validate_commission(value, *, expected_commission_sha256, expected_root_pin, source_root=None):
    digest(expected_commission_sha256); digest(expected_root_pin)
    exact(value, {'schema', 'root_provision_sha256', 'tls_version', 'server_name',
        'ca_certificate_pem', 'ca_certificate_sha256', 'server_certificate_pem',
        'server_certificate_sha256', 'client_certificate_pem', 'client_certificate_sha256',
        'operations', 'implementation', 'independently_protected_deployment_established',
        'global_authority_exclusivity_established', 'complete_resource_accounting'})
    require(value['schema'] == COMMISSION_SCHEMA and
        commission_digest(value) == expected_commission_sha256 and
        value['root_provision_sha256'] == expected_root_pin and
        value['tls_version'] == 'TLSv1.3' and value['operations'] == list(OPERATIONS),
        'independent authority commission or root binding differs')
    require(type(value['server_name']) is str and 0 < len(value['server_name']) <= 253 and
        '\x00' not in value['server_name'], 'bounded commissioned server name required')
    for label in ('ca', 'server', 'client'):
        pem = value[label + '_certificate_pem']
        require(type(pem) is str and len(pem) <= 32768 and
                pem.count('-----BEGIN CERTIFICATE-----') == 1,
                'one commissioned certificate required')
        require(sha(ssl.PEM_cert_to_DER_cert(pem)) == value[label + '_certificate_sha256'],
                'commissioned certificate identity differs')
    for flag in ('independently_protected_deployment_established',
                 'global_authority_exclusivity_established', 'complete_resource_accounting'):
        require(value[flag] is False, 'transport commission escalates deployment scope')
    exact(value['implementation'], {'code_sha256', 'implementation_sha256'})
    bindings = value['implementation']['code_sha256']
    require(type(bindings) is dict and 0 < len(bindings) <= 768 and
            sha(canonical(bindings)) == value['implementation']['implementation_sha256'],
            'transport implementation binding differs')
    for name, hashed in bindings.items():
        require(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts,
                'relative commissioned source required')
        digest(hashed)
    if source_root is not None:
        _same(value['implementation'], transport_identity(source_root), 'actual AM source closure differs')
    return _copy(value)


def event_cursor(header):
    return {key: header[key] for key in ('root_provision_sha256', 'epoch', 'serial',
                                        'root_head', 'journal_sha256', 'snapshot_sha256')}


def verify_headers(headers, *, root_pin, anchor_headers=None):
    """Validate actual AL event hashes and one-root structural continuity.

    Snapshot/transcript semantics remain AL evidence checks. This verifier does
    not infer those bytes from headers or certify the underlying hash function.
    """
    digest(root_pin)
    require(type(headers) is list and 0 < len(headers) <= al.MAX_EVENTS,
            'bounded nonempty AL header history required')
    previous = None
    pending = None
    outcomes = {}
    request_bindings = {}
    seen_boots = set()
    terminal = False
    for serial, event in enumerate(headers):
        exact(event, EVENT_FIELDS)
        require(event['schema'] == al.EVENT_SCHEMA and type(event['serial']) is int and
                event['serial'] == serial and event['root_provision_sha256'] == root_pin,
                'AL header root or serial differs')
        nat(event['epoch'])
        for name in ('previous_root_head', 'journal_sha256', 'snapshot_sha256', 'root_head'):
            digest(event[name])
        core = {k: v for k, v in event.items() if k != 'root_head'}
        require(sha(al.DOMAIN + b'EVENT\0' + canonical(core)) == event['root_head'],
                'AL event header hash differs')
        require(event['previous_root_head'] == ('0' * 64 if previous is None else previous['root_head']),
                'AL header predecessor chain differs')
        kind = event['kind']
        require(kind in ('provision', 'reopen', 'reserve', 'launch', 'complete', 'deny'),
                'unknown AL event kind')
        require((serial == 0) == (kind == 'provision'), 'AL provision position differs')
        if serial == 0:
            require(event['epoch'] == 0, 'AL initial epoch differs')
        else:
            require(event['epoch'] == previous['epoch'] + (1 if kind == 'reopen' else 0),
                    'AL epoch evolution differs')
        if kind == 'reopen':
            digest(event['boot_nonce'])
            require(event['boot_nonce'] not in seen_boots, 'AL boot nonce replayed')
            seen_boots.add(event['boot_nonce'])
            if pending is not None:
                pending['stage'] = 'orphaned'
                outcomes[pending['nonce']] = 'orphaned'
        else:
            require(event['boot_nonce'] is None, 'non-reopen carries boot nonce')
        if kind in ('reserve', 'deny'):
            require(not terminal and pending is None and previous is not None,
                    'AL admission while unresolved or terminated')
            request = event['request']
            exact(request, {'expected_cursor', 'request_nonce', 'credits'})
            _same(request['expected_cursor'], event_cursor(previous), 'AL admission cursor differs')
            digest(request['request_nonce']); require(nat(request['credits']) <= 32, 'AL credits differ')
            nonce = request['request_nonce']
            require(nonce not in outcomes, 'AL header nonce replayed')
            request_bindings[nonce] = _copy(request)
            if kind == 'reserve':
                pending = {'nonce': nonce, 'stage': 'reserved', 'epoch': event['epoch']}
                outcomes[nonce] = 'reserved'
            else:
                outcomes[nonce] = 'denied'; terminal = True
        else:
            require(event['request'] is None, 'backend AL header carries request')
        if kind == 'launch':
            require(pending is not None and pending['stage'] == 'reserved' and
                    pending['epoch'] == event['epoch'], 'AL launch lacks current reservation')
            pending['stage'] = 'launch_consumed'; outcomes[pending['nonce']] = 'launch_consumed'
        if kind == 'complete':
            require(pending is not None and pending['stage'] == 'launch_consumed' and
                    pending['epoch'] == event['epoch'], 'AL completion lacks current consumed launch')
            digest(event['session_sha256'])
            outcomes[pending['nonce']] = 'complete'; pending = None
        else:
            require(event['session_sha256'] is None, 'non-completion carries session identity')
        previous = event
    if anchor_headers is not None:
        require(type(anchor_headers) is list and 0 < len(anchor_headers) <= len(headers),
                'authority rolled back before independent client anchor')
        _same(headers[:len(anchor_headers)], anchor_headers, 'authority history forks independent client anchor')
    return {'cursor': event_cursor(previous), 'outcomes': outcomes, 'request_bindings': request_bindings}


def create_anchor(path, commission, *, expected_commission_sha256, expected_root_pin, trusted_headers):
    validate_commission(commission, expected_commission_sha256=expected_commission_sha256,
                        expected_root_pin=expected_root_pin)
    verify_headers(trusted_headers, root_pin=expected_root_pin)
    path = Path(path).absolute(); _no_links(path)
    require(not path.exists() and not path.with_name(path.name + '.lock').exists(),
            'client anchor provisioning cannot overwrite or silently initialize')
    value = {'schema': ANCHOR_SCHEMA, 'commission_sha256': expected_commission_sha256,
        'root_provision_sha256': expected_root_pin, 'headers': _copy(trusted_headers),
        'pending': None, 'resolved': []}
    _new(path.with_name(path.name + '.lock'), b'L')
    _new(path, canonical(value)); ak._directory_sync(path.parent)
    return value


def _validate_request(request, commission_sha256, root_pin):
    fields = {'schema', 'commission_sha256', 'root_provision_sha256', 'operation',
              'request_nonce', 'challenge', 'expected_cursor'}
    require(type(request) is dict and request.get('operation') in OPERATIONS,
            'controller operation is not admitted')
    if request['operation'] == 'run':
        fields.add('credits')
    exact(request, fields)
    require(request['schema'] == REQUEST_SCHEMA and request['commission_sha256'] == commission_sha256
            and request['root_provision_sha256'] == root_pin, 'request authority binding differs')
    digest(request['request_nonce']); digest(request['challenge'])
    al._validate_cursor(request['expected_cursor'])
    require(request['expected_cursor']['root_provision_sha256'] == root_pin,
            'request cursor names another root')
    if request['operation'] == 'run':
        require(nat(request['credits']) <= 32, 'request credits exceed fixed grammar')
    return request


def frame_bytes(value):
    raw = canonical(value)
    require(0 < len(raw) <= MAX_FRAME, 'bounded AM CJSON frame required')
    return struct.pack('!I', len(raw)) + raw


def receive_frame(connection, observation, field):
    retained = bytearray()
    def read(count):
        chunks = bytearray()
        while len(chunks) < count:
            part = connection.recv(count - len(chunks))
            if not part:
                raise EOFError('connection ended within authority frame')
            chunks.extend(part); retained.extend(part)
            observation[field] = bytes(retained).hex()
        return bytes(chunks)
    count = struct.unpack('!I', read(4))[0]
    require(0 < count <= MAX_FRAME, 'authority frame exceeds fixed bound')
    return load_json_strict(read(count), require_canonical=True)


def _tls_context(server, commission, ca_file, certificate, private_key):
    require(ssl.HAS_TLSv1_3, 'actual TLS 1.3 support required')
    ca, ca_hash = _pem(ca_file)
    require(ca == commission['ca_certificate_pem'] and ca_hash == commission['ca_certificate_sha256'],
            'configured CA differs from independent commission')
    certificate_pem, certificate_hash = _pem(certificate)
    label = 'server' if server else 'client'
    require(certificate_pem == commission[label + '_certificate_pem'] and
        certificate_hash == commission[label + '_certificate_sha256'],
        'local TLS certificate differs from independent commission')
    _no_links(Path(private_key))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if server else ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.verify_mode = ssl.CERT_REQUIRED
    if not server:
        context.check_hostname = True
    context.load_verify_locations(cafile=str(ca_file))
    context.load_cert_chain(certfile=str(certificate), keyfile=str(private_key))
    if server:
        context.num_tickets = 0
    return context


def _peer_observation(connection, record):
    der = connection.getpeercert(binary_form=True)
    require(type(der) is bytes and der, 'actual authenticated TLS peer certificate required')
    record['peer_certificate_der_hex'] = der.hex()
    record['peer_certificate_sha256'] = sha(der)
    record['tls_version'] = connection.version()
    record['cipher'] = list(connection.cipher())
    require(record['tls_version'] == 'TLSv1.3', 'negotiated TLS version differs')
    return record['peer_certificate_sha256']


class AuthorityTransportServer:
    """Serial network dispatcher. Serve on the AL SQLite constructing thread."""
    def __init__(self, authority, commission, *, expected_commission_sha256, expected_root_pin,
                 ca_file, server_cert, server_key, native_directory, source_root=SOURCE_ROOT,
                 bind_host='127.0.0.1', port=0):
        self.commission = validate_commission(commission,
            expected_commission_sha256=expected_commission_sha256,
            expected_root_pin=expected_root_pin, source_root=source_root)
        require(authority.root_provision_sha256 == expected_root_pin,
                'actual AL authority differs from commissioned root')
        require(bind_host in ('127.0.0.1',), 'reference endpoint must bind loopback')
        require(type(port) is int and 0 <= port <= 65535, 'bounded TCP port required')
        self.authority = authority
        self.commission_sha256 = expected_commission_sha256
        self.root_pin = expected_root_pin
        self.context = _tls_context(True, commission, ca_file, server_cert, server_key)
        self.native = Path(native_directory).absolute(); _no_links(self.native)
        require(not self.native.exists(), 'fresh AM service native directory required')
        self.native.mkdir(parents=True, mode=0o700)
        self.bind_host, self.port = bind_host, port
        self.listener = None
        self._stop = threading.Event()
        self._owner_thread = threading.get_ident()
        self.connection_count = 0

    def start(self):
        require(self.listener is None, 'authority listener already started')
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Windows SO_REUSEADDR permits a competing bind; do not enable it.
        if os.name == 'nt' and hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        self.listener.bind((self.bind_host, self.port))
        self.listener.listen(8); self.listener.settimeout(0.25)
        return self.listener.getsockname()

    def stop(self):
        self._stop.set()

    def export(self):
        require(threading.get_ident() == self._owner_thread, 'AL export must use constructing thread')
        return self.authority.export_evidence()

    def _dispatch(self, request):
        _validate_request(request, self.commission_sha256, self.root_pin)
        before = self.authority.cursor
        accepted, reason, result = True, None, None
        try:
            if request['operation'] == 'read':
                evidence = self.authority.export_evidence()
                headers = [entry['event'] for entry in evidence['entries']]
                cursor = request['expected_cursor']
                require(cursor['serial'] < len(headers) and
                        event_cursor(headers[cursor['serial']]) == cursor,
                        'read anchor absent from authority history')
                state = self.authority.state
                result = {'status': state.status, 'reserved': list(state.reserved),
                          'sessions': len(state.completed)}
            else:
                files = self.authority.run_session(expected_cursor=request['expected_cursor'],
                    request_nonce=request['request_nonce'], credits=request['credits'])
                result = {'session_sha256': {name: sha(raw) for name, raw in files.items()}}
        except (ResourceError, ValueError, TypeError, KeyError) as error:
            accepted = False
            reason = 'aggregate_budget_denied' if isinstance(error, ResourceExhausted) else 'protocol_or_authority_refused'
        # A poisoned AL handle raises here. No authenticated completion is
        # synthesized from ambiguous worker/commit failure.
        after = self.authority.cursor
        exported = self.authority.export_evidence()
        headers = [entry['event'] for entry in exported['entries']]
        _same(verify_headers(headers, root_pin=self.root_pin)['cursor'], after,
              'server exported header cursor differs')
        return {'schema': RESPONSE_SCHEMA, 'commission_sha256': self.commission_sha256,
            'root_provision_sha256': self.root_pin, 'request_sha256': sha(canonical(request)),
            'challenge': request['challenge'], 'operation': request['operation'],
            'accepted': accepted, 'reason': reason, 'before': before, 'after': after,
            'headers': headers, 'result': result}

    def serve_forever(self, stop_event=None):
        require(threading.get_ident() == self._owner_thread, 'AL server must use constructing thread')
        require(self.listener is not None, 'authority listener not started')
        try:
            while not self._stop.is_set() and not (stop_event and stop_event.is_set()):
                require(self.connection_count < MAX_CONNECTIONS, 'reference connection capacity exhausted')
                try:
                    raw, address = self.listener.accept()
                except socket.timeout:
                    continue
                number = self.connection_count; self.connection_count += 1
                record = {'schema': NATIVE_SCHEMA, 'role': 'server', 'sequence': number,
                    'pid': os.getpid(), 'started_at_utc': _now(), 'remote_address': list(address),
                    'commission_sha256': self.commission_sha256, 'root_provision_sha256': self.root_pin,
                    'phase': 'accepted_tcp', 'request_frame_hex': '', 'response_frame_hex': '',
                    'response_sent': False, 'peer_pin_matched': False, 'error_type': None}
                _new(self.native / ('start-%04d.json' % number), canonical(record))
                connection = None
                try:
                    raw.settimeout(10)
                    connection = self.context.wrap_socket(raw, server_side=True)
                    record['phase'] = 'tls_authenticated'
                    peer = _peer_observation(connection, record)
                    require(peer == self.commission['client_certificate_sha256'],
                            'authenticated client certificate not commissioned')
                    record['peer_pin_matched'] = True
                    request = receive_frame(connection, record, 'request_frame_hex')
                    record['phase'] = 'request_received'
                    reply = self._dispatch(request)
                    response = frame_bytes(reply)
                    record['response_frame_hex'] = response.hex()
                    record['phase'] = 'response_prepared'
                    connection.sendall(response)
                    record['response_sent'] = True; record['phase'] = 'response_sent'
                except (OSError, ValueError, TypeError, KeyError, EOFError, ResourceError) as error:
                    record['error_type'] = type(error).__name__
                    record['error_message'] = str(error)[:512]
                finally:
                    if connection is not None:
                        connection.close()
                    else:
                        raw.close()
                    record['completed_at_utc'] = _now()
                    _new(self.native / ('result-%04d.json' % number), canonical(record))
        finally:
            self.listener.close(); self.listener = None


class AuthorityTransportClient:
    def __init__(self, commission, *, expected_commission_sha256, expected_root_pin,
                 anchor_path, host, port, ca_file, client_cert, client_key,
                 native_directory, timeout=600):
        self.commission = validate_commission(commission,
            expected_commission_sha256=expected_commission_sha256, expected_root_pin=expected_root_pin)
        require(type(host) is str and host == '127.0.0.1' and type(port) is int and 0 < port <= 65535,
                'fixed loopback reference address required')
        require(type(timeout) in (int, float) and 0 < timeout <= 600, 'bounded client timeout required')
        self.pin, self.root_pin = expected_commission_sha256, expected_root_pin
        self.anchor_path = Path(anchor_path).absolute(); _no_links(self.anchor_path)
        require(self.anchor_path.is_file(), 'independently provisioned client anchor required')
        self.context = _tls_context(False, commission, ca_file, client_cert, client_key)
        self.host, self.port, self.timeout = host, port, timeout
        self.native = Path(native_directory).absolute(); _no_links(self.native)
        require(not self.native.exists(), 'fresh AM client native directory required')
        self.native.mkdir(parents=True, mode=0o700)
        self.sequence = 0
        self.operation_sequence = 0

    @contextmanager
    def _operation_evidence(self, operation, anchor):
        number = self.operation_sequence; self.operation_sequence += 1
        record = {'schema': 'phase17am.client-operation.v1', 'operation': operation,
            'pid': os.getpid(), 'sequence': number, 'exchange_sequence': self.sequence,
            'started_at_utc': _now(),
            'anchor_before': _copy(anchor), 'pending_before_send': None,
            'request': None, 'completed': False, 'error_type': None}
        try:
            yield record
            record['completed'] = True
        except BaseException as error:
            record['error_type'] = type(error).__name__
            raise
        finally:
            record['anchor_after'] = load_json_strict(self.anchor_path.read_bytes(), require_canonical=True)
            record['anchor_after_sha256'] = sha(self.anchor_path.read_bytes())
            record['completed_at_utc'] = _now()
            _new(self.native / ('operation-%04d.json' % number), canonical(record))

    @contextmanager
    def _locked_anchor(self):
        lock = ak._LifetimeLock(self.anchor_path.with_name(self.anchor_path.name + '.lock'))
        try:
            _no_links(self.anchor_path)
            value = load_json_strict(self.anchor_path.read_bytes(), require_canonical=True)
            exact(value, {'schema', 'commission_sha256', 'root_provision_sha256', 'headers', 'pending', 'resolved'})
            require(value['schema'] == ANCHOR_SCHEMA and value['commission_sha256'] == self.pin and
                    value['root_provision_sha256'] == self.root_pin, 'independent anchor authority differs')
            verify_headers(value['headers'], root_pin=self.root_pin)
            require(type(value['resolved']) is list and len(value['resolved']) <= MAX_RESOLVED,
                    'anchor resolution capacity exhausted')
            if value['pending'] is not None:
                exact(value['pending'], {'request', 'request_sha256'})
                request = _validate_request(value['pending']['request'], self.pin, self.root_pin)
                require(request['operation'] == 'run' and
                    sha(canonical(request)) == value['pending']['request_sha256'], 'pending request binding differs')
            yield value
            lock.check()
        finally:
            lock.close()

    def _request(self, operation, anchor, *, credits=None, request_nonce=None):
        value = {'schema': REQUEST_SCHEMA, 'commission_sha256': self.pin,
            'root_provision_sha256': self.root_pin, 'operation': operation,
            'request_nonce': secrets.token_hex(32) if request_nonce is None else request_nonce,
            'challenge': secrets.token_hex(32), 'expected_cursor': event_cursor(anchor['headers'][-1])}
        if operation == 'run':
            value['credits'] = credits
        return _validate_request(value, self.pin, self.root_pin)

    def _exchange(self, request, *, abandon_response=False):
        number = self.sequence; self.sequence += 1
        record = {'schema': NATIVE_SCHEMA, 'role': 'client', 'sequence': number,
            'pid': os.getpid(), 'started_at_utc': _now(), 'remote_address': [self.host, self.port],
            'commission_sha256': self.pin, 'root_provision_sha256': self.root_pin,
            'phase': 'before_connect', 'request_frame_hex': '', 'response_frame_hex': '',
            'request_sent': False, 'peer_pin_matched': False, 'abandoned_response': False,
            'error_type': None}
        _new(self.native / ('start-%04d.json' % number), canonical(record))
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as raw:
                with self.context.wrap_socket(raw, server_hostname=self.commission['server_name']) as connection:
                    record['phase'] = 'tls_authenticated'
                    peer = _peer_observation(connection, record)
                    require(peer == self.commission['server_certificate_sha256'],
                            'authenticated server certificate not independently pinned')
                    record['peer_pin_matched'] = True
                    frame = frame_bytes(request); record['request_frame_hex'] = frame.hex()
                    connection.sendall(frame); record['request_sent'] = True
                    record['phase'] = 'request_sent'
                    if abandon_response:
                        record['abandoned_response'] = True
                        record['phase'] = 'response_deliberately_unobserved'
                        return None
                    response = receive_frame(connection, record, 'response_frame_hex')
                    record['phase'] = 'response_received'
                    return response
        except (OSError, ValueError, TypeError, KeyError, EOFError, ResourceError) as error:
            record['error_type'] = type(error).__name__
            record['error_message'] = str(error)[:512]
            raise
        finally:
            record['completed_at_utc'] = _now()
            _new(self.native / ('result-%04d.json' % number), canonical(record))

    def _checked_reply(self, reply, request, anchor):
        exact(reply, {'schema', 'commission_sha256', 'root_provision_sha256', 'request_sha256',
            'challenge', 'operation', 'accepted', 'reason', 'before', 'after', 'headers', 'result'})
        require(reply['schema'] == RESPONSE_SCHEMA and reply['commission_sha256'] == self.pin and
            reply['root_provision_sha256'] == self.root_pin and
            reply['request_sha256'] == sha(canonical(request)) and
            reply['challenge'] == request['challenge'] and reply['operation'] == request['operation'],
            'response authority/request/challenge binding differs')
        require(type(reply['accepted']) is bool and reply['reason'] in
                (None, 'aggregate_budget_denied', 'protocol_or_authority_refused') and
                (reply['accepted'] == (reply['reason'] is None)), 'response outcome differs')
        checked = verify_headers(reply['headers'], root_pin=self.root_pin, anchor_headers=anchor['headers'])
        _same(checked['cursor'], reply['after'], 'response final cursor differs')
        al._validate_cursor(reply['before'])
        before = reply['before']
        require(before['serial'] < len(reply['headers']) and
            event_cursor(reply['headers'][before['serial']]) == before, 'response before cursor absent')
        require(reply['after']['serial'] >= before['serial'], 'response cursor moves backward')
        if request['operation'] == 'read':
            _same(before, reply['after'], 'read response mutates authority')
        elif reply['accepted']:
            require(self._matching_outcome(checked, request) == 'complete',
                    'successful run lacks matching durable completion')
            _same(before, request['expected_cursor'], 'admitted run used substituted predecessor')
        elif reply['reason'] == 'aggregate_budget_denied':
            require(self._matching_outcome(checked, request) == 'denied',
                    'denial lacks matching durable denial')
        else:
            _same(before, reply['after'], 'protocol refusal mutated authority')
        require((type(reply['result']) is dict if reply['accepted'] else reply['result'] is None),
                'response result shape differs')
        return checked

    @staticmethod
    def _matching_outcome(checked, request):
        expected = {key: request[key] for key in ('expected_cursor', 'request_nonce', 'credits')}
        actual = checked['request_bindings'].get(request['request_nonce'])
        if actual is None or canonical(actual) != canonical(expected):
            return 'unobserved'
        return checked['outcomes'][request['request_nonce']]

    def _resolve(self, anchor, outcome, cursor):
        require(anchor['pending'] is not None and len(anchor['resolved']) < MAX_RESOLVED,
                'pending resolution missing or capacity exhausted')
        pending = anchor['pending']
        anchor['resolved'].append({'request_sha256': pending['request_sha256'],
            'request_nonce': pending['request']['request_nonce'], 'outcome': outcome, 'at_cursor': cursor})
        anchor['pending'] = None

    def read(self):
        with self._locked_anchor() as anchor:
            with self._operation_evidence('read', anchor) as observation:
                require(anchor['pending'] is None, 'unresolved request requires explicit read-only reconcile')
                request = self._request('read', anchor); observation['request'] = request
                reply = self._exchange(request)
                self._checked_reply(reply, request, anchor)
                anchor['headers'] = reply['headers']; _replace(self.anchor_path, anchor)
                return reply

    def run(self, credits, request_nonce, *, abandon_response=False):
        require(type(abandon_response) is bool, 'exact capture abandonment flag required')
        with self._locked_anchor() as anchor:
            with self._operation_evidence('run', anchor) as observation:
                require(anchor['pending'] is None and len(anchor['resolved']) < MAX_RESOLVED,
                        'unresolved request or exhausted anchor cannot authorize another run')
                request = self._request('run', anchor, credits=credits, request_nonce=request_nonce)
                observation['request'] = request
                anchor['pending'] = {'request': request, 'request_sha256': sha(canonical(request))}
                # This write must complete before connecting/sending. Missing
                # reply retains this request intact; there is no retry path.
                _replace(self.anchor_path, anchor)
                observation['pending_before_send'] = load_json_strict(self.anchor_path.read_bytes())
                reply = self._exchange(request, abandon_response=abandon_response)
                if reply is None:
                    return None
                checked = self._checked_reply(reply, request, anchor)
                outcome = self._matching_outcome(checked, request)
                if outcome in ('complete', 'denied'):
                    self._resolve(anchor, outcome, reply['after'])
                else:
                    require(not reply['accepted'] and reply['reason'] == 'protocol_or_authority_refused',
                            'run lacks resolvable response')
                    self._resolve(anchor, 'direct_refusal', reply['after'])
                anchor['headers'] = reply['headers']; _replace(self.anchor_path, anchor)
                return reply

    def reconcile(self):
        with self._locked_anchor() as anchor:
            with self._operation_evidence('reconcile', anchor) as observation:
                require(anchor['pending'] is not None, 'no unresolved request to reconcile')
                request = self._request('read', anchor); observation['request'] = request
                reply = self._exchange(request)
                checked = self._checked_reply(reply, request, anchor)
                require(reply['accepted'], 'authority refused read-only reconciliation')
                outcome = self._matching_outcome(checked, anchor['pending']['request'])
                if outcome in ('complete', 'denied'):
                    self._resolve(anchor, outcome, reply['after'])
                anchor['headers'] = reply['headers']; _replace(self.anchor_path, anchor)
                return {'response': reply, 'pending_retained': anchor['pending'] is not None,
                        'observed_outcome': outcome, 'worker_reissued': False}
