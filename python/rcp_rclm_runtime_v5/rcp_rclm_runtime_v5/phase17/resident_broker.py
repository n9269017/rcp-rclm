"""AO's finite, prepaid resident owner of the unchanged AN broker.

The inherited pipe is an administrator-supervised local channel, not an
authenticated remote deployment. Only original AN intents cross it. Paths,
credentials, endpoint, dispatch mode and selected fault controls come from the
separately pinned trusted configuration. Each action gets fresh AM evidence
sequence numbers while one resident process owns every dispatch in a lifetime.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path, PureWindowsPath
import re
import sys

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import authority_transport as am
from . import protected_authority as an
from . import controller_durable_authority as ak
from .resource_ledger import canonical, digest, exact, require, sha, _no_links

SOURCE_ROOT = Path(__file__).resolve().parents[4]
CONFIG_SCHEMA = 'phase17ao.resident-broker-config.v1'
READY_SCHEMA = 'phase17ao.resident-broker-ready.v1'
REPLY_SCHEMA = 'phase17ao.resident-broker-reply.v1'
ATTEMPT_SCHEMA = 'phase17ao.resident-broker-attempt.v1'
STOPPED_SCHEMA = 'phase17ao.resident-broker-stopped.v1'
MAX_FRAME_BYTES = 65537
MAX_ATTEMPTS = 128
MAX_PIPE_BYTES = 16 * 1024 * 1024
MAX_TLS_CONNECTIONS = 256


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load(path):
    return load_json_strict(Path(path).read_bytes(), require_canonical=True)


def _copy(value):
    return load_json_strict(canonical(value), require_canonical=True)


def _same(a, b, message):
    require(canonical(a) == canonical(b), message)


def runtime_identity(source_root=SOURCE_ROOT):
    return an.implementation_identity(source_root)['implementation_sha256']


def _name(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value) is not None,
            'bounded resident identity required')
    return value


def _path(value, *, exists=True, directory=False):
    require(type(value) is str and bool(value), 'absolute resident path required')
    path = Path(value)
    require(path.is_absolute(), 'absolute resident path required')
    _no_links(path)
    if exists:
        require(path.is_dir() if directory else path.is_file(), 'resident path is unavailable')
    else:
        require(not path.exists() and path.parent.is_dir(), 'fresh resident path required')
    # AN's no-links guard applies to every existing ancestor. Canonicalize the
    # platform spelling without weakening the source-root equality check.
    return path.resolve(strict=exists)


def validate_limits(value, *, slots):
    exact(value, {'max_attempts', 'max_frame_bytes', 'max_request_bytes',
                  'max_response_bytes', 'max_authority_tls_connections'})
    upper = {'max_attempts': MAX_ATTEMPTS, 'max_frame_bytes': MAX_FRAME_BYTES,
             'max_request_bytes': MAX_PIPE_BYTES, 'max_response_bytes': MAX_PIPE_BYTES,
             'max_authority_tls_connections': MAX_TLS_CONNECTIONS}
    for key, maximum in upper.items():
        require(type(value[key]) is int and 0 < value[key] <= maximum,
                'resident limit is not a finite positive allowance')
    require(slots <= value['max_attempts'], 'trusted action slots exceed attempt allowance')
    require(value['max_request_bytes'] >= value['max_attempts'] * value['max_frame_bytes'],
            'entire bounded input allowance must be prepaid')
    require(value['max_response_bytes'] >= 4096 + value['max_attempts'] * 2048,
            'entire sanitized response allowance must be prepaid')
    require(value['max_authority_tls_connections'] >= slots,
            'entire one-exchange-per-slot allowance must be prepaid')
    return _copy(value)


def validate_config(value, *, expected_config_sha256, source_root=SOURCE_ROOT,
                    require_fresh=True, verify_paths=True):
    digest(expected_config_sha256)
    exact(value, {'schema', 'source_root', 'lifetime_id', 'broker_commission',
        'broker_commission_sha256', 'authority_commission', 'authority_commission_sha256',
        'root_provision_sha256', 'state_path', 'anchor_path', 'ca_file', 'client_cert',
        'client_key', 'host', 'port', 'native_directory', 'broker_native_root', 'limits',
        'slots', 'lifecycle_commission_sha256', 'lifecycle_evidence', 'grant'})
    require(value['schema'] == CONFIG_SCHEMA and sha(canonical(value)) == expected_config_sha256,
            'independently supplied resident configuration pin differs')
    require(type(require_fresh) is bool and type(verify_paths) is bool,
            'exact resident verification mode required')
    root = Path(source_root).resolve(strict=True)
    if verify_paths:
        observed_root = _path(value['source_root'], directory=True)
        require(observed_root == root == SOURCE_ROOT.resolve(strict=True),
                'resident source root differs from actually executing implementation')
    else:
        # A retained Windows record can be reconstructed on Linux and vice
        # versa. Its path is provenance; the original code closure is checked
        # against source_root, never treated as a newly accessible local path.
        for key in ('source_root', 'broker_commission', 'authority_commission', 'state_path',
                    'anchor_path', 'ca_file', 'client_cert', 'client_key', 'native_directory',
                    'broker_native_root'):
            path = value[key]
            require(type(path) is str and (Path(path).is_absolute() or PureWindowsPath(path).is_absolute()),
                    'retained resident path must be absolute provenance')
    _name(value['lifetime_id'])
    for key in ('broker_commission_sha256', 'authority_commission_sha256',
                'root_provision_sha256', 'lifecycle_commission_sha256'):
        digest(value[key])
    if verify_paths:
        for key in ('broker_commission', 'authority_commission', 'state_path', 'anchor_path',
                    'ca_file', 'client_cert', 'client_key'):
            _path(value[key])
    require(value['state_path'] != value['anchor_path'],
            'resident broker and AM anchor must remain distinct')
    if verify_paths:
        require(Path(value['state_path']).resolve(strict=True) != Path(value['anchor_path']).resolve(strict=True),
                'resident broker state aliases its AM anchor')
    if verify_paths:
        _path(value['native_directory'], exists=not require_fresh, directory=not require_fresh)
        _path(value['broker_native_root'], directory=True)
    require(value['host'] == '127.0.0.1' and type(value['port']) is int and 0 < value['port'] <= 65535,
            'resident reference endpoint must be trusted fixed loopback')
    require(type(value['slots']) is list and 0 < len(value['slots']) <= MAX_ATTEMPTS,
            'finite nonempty trusted action schedule required')
    seen = set()
    for slot in value['slots']:
        exact(slot, {'action', 'mode', 'abandon_response'})
        _name(slot['action'])
        require(slot['action'] not in seen, 'resident action directory would be reused')
        seen.add(slot['action'])
        require(slot['mode'] in ('reference', 'promotion') and type(slot['abandon_response']) is bool,
                'trusted resident action policy differs')
        require(slot['mode'] == 'reference' or not slot['abandon_response'],
                'promotion denial fixture cannot abandon a response')
        if verify_paths and require_fresh:
            require(not (Path(value['broker_native_root']) / slot['action']).exists(),
                    'resident action evidence already exists')
    limits = validate_limits(value['limits'], slots=len(value['slots']))
    # A public ledger prefix proves that the trusted parent permanently reserved
    # and consumed this launch before Popen. It is not a remote physical witness.
    from .service_lifecycle import verify_evidence
    checked = verify_evidence(value['lifecycle_evidence'],
        expected_commission_sha256=value['lifecycle_commission_sha256'])
    state, grant = checked['state'], value['grant']
    require(type(state.get('pending')) is dict and state['pending']['phase'] == 'launched',
            'resident launch was not consumed by the authoritative supervisor')
    _same(state['pending']['grant'], grant, 'resident launch grant differs from ledger prefix')
    require(state['epoch'] == grant['epoch'] and state['owner_nonce'] == grant['owner_nonce'] and
            grant['lifetime_id'] == value['lifetime_id'] and
            grant['commission_sha256'] == value['lifecycle_commission_sha256'],
            'resident grant owner, lifetime or epoch differs')
    digest(grant['grant_sha256'])
    needed = [1, 1, limits['max_attempts'], limits['max_request_bytes'],
              limits['max_response_bytes'], limits['max_authority_tls_connections']]
    require(len(grant['envelope']) == len(needed) and
            all(type(n) is int and n <= cap for n, cap in zip(needed, grant['envelope'])),
            'resident service exceeds its prepaid grant envelope')
    require(checked['commission']['bindings']['runtime_sha256'] == runtime_identity(root),
            'resident prepaid commission does not bind the actual runtime closure')
    require(checked['commission']['bindings']['campaign_commission_sha256'] ==
            value['broker_commission_sha256'],
            'resident prepaid commission does not bind this broker campaign')
    return _copy(value), checked


def verify_config(value, *, expected_config_sha256, source_root=SOURCE_ROOT,
                  require_fresh=False, verify_paths=False):
    """Verify retained source/grant/config bindings without assuming path relocation."""
    return validate_config(value, expected_config_sha256=expected_config_sha256,
                           source_root=source_root, require_fresh=require_fresh,
                           verify_paths=verify_paths)


def make_config(*, source_root, lifetime_id, broker_commission, broker_commission_sha256,
                authority_commission, authority_commission_sha256, root_provision_sha256,
                state_path, anchor_path, ca_file, client_cert, client_key, port,
                native_directory, broker_native_root, limits, slots,
                lifecycle_commission_sha256, lifecycle_evidence, grant):
    values = dict(locals())
    for key in ('source_root', 'broker_commission', 'authority_commission', 'state_path',
                'anchor_path', 'ca_file', 'client_cert', 'client_key', 'native_directory',
                'broker_native_root'):
        values[key] = str(Path(values[key]).resolve())
    values.update(schema=CONFIG_SCHEMA, host='127.0.0.1')
    validate_config(values, expected_config_sha256=sha(canonical(values)))
    return values


def _new(path, data):
    ak._write_new(Path(path), data)


def _claim_lifetime(config, pin):
    marker = Path(config['state_path']).parent / ('resident-launch-' + config['lifetime_id'] + '.json')
    _no_links(marker)
    value = {'schema': 'phase17ao.resident-launch-owner.v1',
        'lifetime_id': config['lifetime_id'], 'config_sha256': pin,
        'commission_sha256': config['lifecycle_commission_sha256'],
        'grant_sha256': config['grant']['grant_sha256'], 'pid': os.getpid(),
        'claimed_at_utc': _now(),
        'parent_consumed_cursor': config['lifecycle_evidence']['final_cursor'],
        'automatic_reuse_permitted': False, 'global_clone_exclusivity_established': False}
    _new(marker, canonical(value))
    os.chmod(marker, 0o600)
    ak._directory_sync(marker.parent)
    return marker, value


def _counter_value(attempts=0, requests=0, responses=0, tls=0):
    return {'input_attempts': attempts, 'request_bytes': requests,
            'response_bytes': responses, 'authority_tls_connections': tls}


def observed_usage(counters):
    return [1, 1, counters['input_attempts'], counters['request_bytes'],
            counters['response_bytes'], counters['authority_tls_connections']]


def _dispatch(config, slot, intent, broker_commission, authority_commission):
    directory = Path(config['broker_native_root']) / slot['action']
    directory.mkdir(mode=0o700, exist_ok=False)
    client = am.AuthorityTransportClient(authority_commission,
        expected_commission_sha256=config['authority_commission_sha256'],
        expected_root_pin=config['root_provision_sha256'], anchor_path=config['anchor_path'],
        host=config['host'], port=config['port'], ca_file=config['ca_file'],
        client_cert=config['client_cert'], client_key=config['client_key'],
        native_directory=directory / 'transport')
    broker = an.ProtectedAuthorityBroker(broker_commission,
        expected_commission_sha256=config['broker_commission_sha256'], client=client,
        state_path=config['state_path'], source_root=config['source_root'])
    before_state, before_anchor = _load(config['state_path']), _load(config['anchor_path'])
    dispatch = None; error_name = error_message = None
    try:
        dispatch = broker.dispatch(intent, abandon_response=slot['abandon_response'], mode=slot['mode'])
        public = dispatch['response']
    except ValueError as error:
        error_name, error_message = type(error).__name__, str(error)
        dispatch = broker.last_record
        public = {'schema': 'phase17an.frontend-refusal.v1',
            'intent_sha256': sha(canonical(intent)), 'refused': True, 'reason': 'broker_refused'}
    record = {'schema': 'phase17an.broker-action-observation.v1', 'action': slot['action'],
        'observer_pid': os.getpid(), 'intent': intent, 'mode': slot['mode'],
        'abandon_response': slot['abandon_response'],
        'state_before': before_state, 'anchor_before': before_anchor,
        'state_after': _load(config['state_path']), 'anchor_after': _load(config['anchor_path']),
        'dispatch': dispatch, 'error_type': error_name, 'error_message': error_message,
        'frontend_response': public, 'network_attempts': client.sequence}
    _new(directory / 'dispatch.json', canonical(record))
    return public, sha(canonical(record)), client.sequence, error_name


def serve(config, *, expected_config_sha256, input_stream, output_stream):
    config, checked = validate_config(config, expected_config_sha256=expected_config_sha256)
    broker_commission = an.validate_commission(_load(config['broker_commission']),
        expected_commission_sha256=config['broker_commission_sha256'], source_root=config['source_root'])
    authority_commission = am.validate_commission(_load(config['authority_commission']),
        expected_commission_sha256=config['authority_commission_sha256'],
        expected_root_pin=config['root_provision_sha256'], source_root=config['source_root'])
    require(broker_commission['authority_commission_sha256'] == config['authority_commission_sha256'] and
            broker_commission['root_provision_sha256'] == config['root_provision_sha256'],
            'resident commissioned broker and authority differ')
    marker_path, marker = _claim_lifetime(config, expected_config_sha256)
    native = Path(config['native_directory']); native.mkdir(mode=0o700)
    _new(native / 'config.json', canonical(config))
    _new(native / 'launch-owner.json', canonical(marker))
    counters = _counter_value(); limits = config['limits']; records = []

    def emit(value):
        raw = canonical(value) + b'\n'
        require(counters['response_bytes'] + len(raw) <= limits['max_response_bytes'],
                'resident response allowance exhausted before output')
        counters['response_bytes'] += len(raw)
        require(output_stream.write(raw) == len(raw), 'short resident response write')
        output_stream.flush()
        return raw

    ready = {'schema': READY_SCHEMA, 'pid': os.getpid(), 'parent_pid': os.getppid(),
        'lifetime_id': config['lifetime_id'], 'config_sha256': expected_config_sha256,
        'grant_sha256': config['grant']['grant_sha256'], 'slots': len(config['slots']),
        'limits': limits, 'launch_owner_sha256': sha(canonical(marker)),
        'inherited_pipe_transport': True, 'authenticated_remote_transport_established': False,
        'independently_protected_deployment_established': False}
    _new(native / 'ready.json', canonical(ready)); emit(ready)
    completed = True; stop_reason = 'trusted_schedule_completed'
    for number, slot in enumerate(config['slots']):
        before = _copy(counters)
        require(counters['input_attempts'] < limits['max_attempts'], 'resident attempt allowance exhausted')
        # Charge the input attempt before touching or parsing untrusted bytes.
        counters['input_attempts'] += 1
        remaining = limits['max_request_bytes'] - counters['request_bytes']
        require(remaining >= limits['max_frame_bytes'], 'resident input envelope exhausted before read')
        raw = input_stream.readline(limits['max_frame_bytes'])
        require(type(raw) is bytes and len(raw) <= limits['max_frame_bytes'], 'bounded binary pipe required')
        counters['request_bytes'] += len(raw)
        stem = 'attempt-%04d' % number
        _new(native / (stem + '.input.bin'), raw)
        admission = {'schema': 'phase17ao.resident-attempt-admission.v1',
            'pid': os.getpid(), 'lifetime_id': config['lifetime_id'], 'sequence': number,
            'action': slot['action'], 'config_sha256': expected_config_sha256,
            'grant_sha256': config['grant']['grant_sha256'],
            'before': before, 'charged_before_parse': _copy(counters),
            'raw_frame_sha256': sha(raw), 'raw_bytes': len(raw)}
        _new(native / (stem + '.admission.json'), canonical(admission))
        # The persisted admission precedes parse, broker construction and network.
        ak._directory_sync(native)
        parsed = None; parse_status = 'canonical'; error_name = None
        record_sha = None; network = 0
        if not raw or not raw.endswith(b'\n'):
            parse_status = 'end_of_input' if not raw else 'unterminated_or_overlong'
            completed = False; stop_reason = parse_status
        else:
            try:
                parsed = load_json_strict(raw[:-1], require_canonical=True)
            except (ValueError, TypeError, UnicodeError) as error:
                parse_status = 'malformed'; error_name = type(error).__name__
        if parse_status == 'canonical':
            require(counters['authority_tls_connections'] < limits['max_authority_tls_connections'],
                    'resident network allowance exhausted before dispatch')
            public, record_sha, network, error_name = _dispatch(config, slot, parsed,
                broker_commission, authority_commission)
            require(type(network) is int and 0 <= network <= 1,
                    'unchanged AN dispatch exceeded its prepaid connection bound')
            counters['authority_tls_connections'] += network
        else:
            public = {'schema': 'phase17ao.resident-input-refusal.v1',
                      'raw_frame_sha256': sha(raw), 'refused': True, 'reason': 'invalid_input_frame'}
        reply = {'schema': REPLY_SCHEMA, 'pid': os.getpid(), 'lifetime_id': config['lifetime_id'],
            'sequence': number, 'action': slot['action'], 'parse_status': parse_status,
            'response': public, 'broker_record_sha256': record_sha,
            'authority_tls_connections': network}
        response_raw = emit(reply)
        attempt = {'schema': ATTEMPT_SCHEMA, **{k: admission[k] for k in
            ('pid', 'lifetime_id', 'sequence', 'action', 'config_sha256', 'grant_sha256',
             'before', 'charged_before_parse', 'raw_frame_sha256', 'raw_bytes')},
            'after': _copy(counters), 'parse_status': parse_status,
            'mode': slot['mode'], 'abandon_response': slot['abandon_response'],
            'error_type': error_name, 'broker_record_sha256': record_sha,
            'response_frame_sha256': sha(response_raw), 'response_bytes': len(response_raw),
            'authority_tls_connections': network}
        _new(native / (stem + '.json'), canonical(attempt)); records.append(attempt)
        if not completed:
            break
    stopped = {'schema': STOPPED_SCHEMA, 'pid': os.getpid(),
        'lifetime_id': config['lifetime_id'], 'config_sha256': expected_config_sha256,
        'grant_sha256': config['grant']['grant_sha256'], 'completed': completed,
        'stop_reason': stop_reason, 'attempt_records': len(records),
        'counters': _copy(counters), 'observed_usage': observed_usage(counters),
        'launch_owner_sha256': sha(canonical(marker)),
        'state_sha256': sha(Path(config['state_path']).read_bytes()),
        'anchor_sha256': sha(Path(config['anchor_path']).read_bytes()),
        'reservation_refunded': False, 'global_clone_exclusivity_established': False,
        'independently_protected_deployment_established': False,
        'complete_resource_accounting': False, 'promotion_authorized': False}
    # Include the stopped frame itself in response-byte accounting. Only its
    # finite decimal byte count changes during this small fixed point.
    base = counters['response_bytes']
    for _ in range(8):
        count = base + len(canonical(stopped)) + 1
        if stopped['counters']['response_bytes'] == count:
            break
        stopped['counters']['response_bytes'] = count
        stopped['observed_usage'][4] = count
    else:
        require(False, 'resident final response count did not stabilize')
    _new(native / 'stopped.json', canonical(stopped))
    emit(stopped)
    _same(counters, stopped['counters'], 'resident stopped response accounting differs')
    ak._directory_sync(native)
    return stopped


def verify_attempt(record, admission, raw, *, config, config_sha256):
    """Check original byte/counter joins without rerunning a service or worker."""
    common = {'pid', 'lifetime_id', 'sequence', 'action', 'config_sha256', 'grant_sha256',
              'before', 'charged_before_parse', 'raw_frame_sha256', 'raw_bytes'}
    exact(admission, {'schema'} | common)
    exact(record, {'schema', 'after', 'parse_status', 'mode', 'abandon_response',
        'error_type', 'broker_record_sha256', 'response_frame_sha256', 'response_bytes',
        'authority_tls_connections'} | common)
    require(record['schema'] == ATTEMPT_SCHEMA and
            admission['schema'] == 'phase17ao.resident-attempt-admission.v1',
            'resident attempt schema differs')
    number = record['sequence']
    require(type(number) is int and 0 <= number < len(config['slots']), 'resident attempt sequence differs')
    slot = config['slots'][number]
    for key in ('pid', 'lifetime_id', 'sequence', 'action', 'config_sha256', 'grant_sha256',
                'before', 'charged_before_parse', 'raw_frame_sha256', 'raw_bytes'):
        _same(record[key], admission[key], 'resident persisted admission join differs')
    require(record['config_sha256'] == config_sha256 and
            record['grant_sha256'] == config['grant']['grant_sha256'] and
            record['lifetime_id'] == config['lifetime_id'] and record['action'] == slot['action'] and
            record['mode'] == slot['mode'] and record['abandon_response'] == slot['abandon_response'],
            'resident attempt trusted slot differs')
    require(record['raw_frame_sha256'] == sha(raw) and record['raw_bytes'] == len(raw) and
            len(raw) <= config['limits']['max_frame_bytes'], 'resident original input bytes differ')
    before, charged, after = record['before'], record['charged_before_parse'], record['after']
    for counters in (before, charged, after):
        exact(counters, {'input_attempts', 'request_bytes', 'response_bytes', 'authority_tls_connections'})
        require(all(type(number) is int and number >= 0 for number in counters.values()),
                'resident counters must be exact nonnegative integers')
    require(type(record['response_bytes']) is int and record['response_bytes'] > 0 and
            type(record['authority_tls_connections']) is int and
            0 <= record['authority_tls_connections'] <= 1,
            'resident per-attempt output or connection count differs')
    expected = _copy(before); expected['input_attempts'] += 1; expected['request_bytes'] += len(raw)
    _same(charged, expected, 'resident input was not charged before parse')
    expected['response_bytes'] += record['response_bytes']
    expected['authority_tls_connections'] += record['authority_tls_connections']
    _same(after, expected, 'resident attempt conservation differs')
    require(record['parse_status'] in ('canonical', 'malformed', 'end_of_input', 'unterminated_or_overlong'),
            'resident parser status differs')
    actual_status = 'canonical'
    if not raw or not raw.endswith(b'\n'):
        actual_status = 'end_of_input' if not raw else 'unterminated_or_overlong'
    else:
        try:
            load_json_strict(raw[:-1], require_canonical=True)
        except (ValueError, TypeError, UnicodeError):
            actual_status = 'malformed'
    require(record['parse_status'] == actual_status, 'resident parser status differs from original bytes')
    if record['parse_status'] != 'canonical':
        require(record['broker_record_sha256'] is None and record['authority_tls_connections'] == 0,
                'malformed resident input reached authority')
    limits = config['limits']
    require(after['input_attempts'] <= limits['max_attempts'] and
            after['request_bytes'] <= limits['max_request_bytes'] and
            after['response_bytes'] <= limits['max_response_bytes'] and
            after['authority_tls_connections'] <= limits['max_authority_tls_connections'],
            'resident retained counters exceed prepaid allowances')
    return _copy(after)


def verify_stream(stdout, *, config, attempts, admissions, raw_frames):
    """Reconstruct a normally completed lifetime from its retained stdout."""
    require(type(stdout) is bytes and len(stdout) <= config['limits']['max_response_bytes'] and
            stdout.endswith(b'\n'), 'bounded complete resident stdout required')
    lines = stdout.splitlines(keepends=True)
    values = [load_json_strict(line[:-1], require_canonical=True) for line in lines]
    require(len(values) == len(attempts) + 2 and len(attempts) == len(admissions) == len(raw_frames),
            'resident stdout and attempt inventory differ')
    ready, stopped = values[0], values[-1]
    pin = sha(canonical(config))
    require(ready['schema'] == READY_SCHEMA and stopped['schema'] == STOPPED_SCHEMA and
            ready['pid'] == stopped['pid'] and type(ready['pid']) is int and ready['pid'] > 0,
            'resident ready/stopped process join differs')
    require(ready['config_sha256'] == stopped['config_sha256'] == pin and
            ready['grant_sha256'] == stopped['grant_sha256'] == config['grant']['grant_sha256'] and
            ready['lifetime_id'] == stopped['lifetime_id'] == config['lifetime_id'],
            'resident ready/stopped commissioned identity differs')
    counters = _counter_value(responses=len(lines[0]))
    for number, (record, admission, raw, reply, line) in enumerate(zip(attempts, admissions, raw_frames,
                                                                    values[1:-1], lines[1:-1])):
        require(record['pid'] == ready['pid'] and record['sequence'] == number and
                reply['schema'] == REPLY_SCHEMA and reply['pid'] == ready['pid'] and
                reply['sequence'] == number and reply['action'] == record['action'] and
                reply['parse_status'] == record['parse_status'] and
                reply['broker_record_sha256'] == record['broker_record_sha256'] and
                reply['authority_tls_connections'] == record['authority_tls_connections'],
                'resident action response identity differs')
        require(sha(line) == record['response_frame_sha256'] and len(line) == record['response_bytes'],
                'resident original response bytes differ')
        _same(record['before'], counters, 'resident attempts are not contiguous')
        counters = verify_attempt(record, admission, raw, config=config, config_sha256=pin)
    counters['response_bytes'] += len(lines[-1])
    _same(counters, stopped['counters'], 'resident final counters differ from original streams')
    _same(stopped['observed_usage'], observed_usage(counters), 'resident final usage projection differs')
    require(stopped['completed'] is True and stopped['stop_reason'] == 'trusted_schedule_completed' and
            len(attempts) == len(config['slots']) == stopped['attempt_records'],
            'resident lifetime did not finish its commissioned schedule')
    return {'pid': ready['pid'], 'counters': counters, 'observed_usage': stopped['observed_usage'],
            'grant_sha256': config['grant']['grant_sha256'], 'lifetime_id': config['lifetime_id'],
            'config_sha256': pin, 'completed': True}
