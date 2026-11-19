"""AN's trusted broker for low-authority, nonpromoting frontend intents.

The broker owns AM's credential-bearing client and retained anchor. Frontends
never supply an endpoint, key, anchor, executable, evaluator, grant or result.
The trusted launcher must actually enforce the commissioned process profile;
this module does not turn a declaration into OS protection or physical trust.
"""
from __future__ import annotations

from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from . import authority_transport as am
from . import controller_durable_authority as ak
from .authority_accounting import reference_coverage, validate_coverage, admission_report
from .challenge_protocol import PROTOCOL
from .metered_worker import WORKER_PROTOCOL
from .objectives import OBJECTIVE_POLICY
from .resource_ledger import canonical, exact, nat, require, sha, digest, _no_links

SOURCE_ROOT = Path(__file__).resolve().parents[4]
COMMISSION_SCHEMA = 'phase17an.protected-authority-commission.v1'
INTENT_SCHEMA = 'phase17an.frontend-intent.v1'
STATE_SCHEMA = 'phase17an.protected-broker-state.v1'
RECORD_SCHEMA = 'phase17an.protected-broker-dispatch.v1'
RESPONSE_SCHEMA = 'phase17an.frontend-response.v1'
OPERATIONS = ('read', 'run', 'reconcile')
MAX_INTENTS = 128
SCOPE = {'campaign': 'nonpromoting_reference',
         'independent_production_issuer_established': False,
         'independently_protected_deployment_established': False,
         'physical_currentness_established': False,
         'global_authority_exclusivity_established': False,
         'complete_resource_accounting': False,
         'promotion_authorized': False}


def _copy(value):
    return load_json_strict(canonical(value), require_canonical=True)


def _same(actual, expected, message):
    require(canonical(actual) == canonical(expected), message)


def commission_digest(value):
    return sha(canonical(value))


def implementation_identity(source_root=SOURCE_ROOT):
    root = Path(source_root).absolute()
    bindings = dict(am.transport_identity(root)['code_sha256'])
    # These are the fixed executable entrypoints, not controller-chosen paths.
    for path in sorted((root / 'scripts').glob('phase17_*.py')):
        _no_links(path)
        require(path.is_file(), 'fixed AN entrypoint source missing')
        bindings[path.relative_to(root).as_posix()] = sha(path.read_bytes())
    require(0 < len(bindings) <= 1024, 'broker implementation inventory exceeds profile')
    return {'code_sha256': bindings, 'implementation_sha256': sha(canonical(bindings))}


def make_broker_commission(source_root, authority_commission, *,
                          expected_authority_commission_sha256, expected_root_pin,
                          launch_profile, accounting_coverage=None,
                          max_credits=2, max_intents=32):
    am.validate_commission(authority_commission,
        expected_commission_sha256=expected_authority_commission_sha256,
        expected_root_pin=expected_root_pin, source_root=source_root)
    require(type(max_credits) is int and 0 < max_credits <= 32,
            'bounded fixed frontend credit limit required')
    require(type(max_intents) is int and 0 < max_intents <= MAX_INTENTS,
            'bounded fixed frontend intent limit required')
    _validate_profile(launch_profile)
    coverage = validate_coverage(reference_coverage() if accounting_coverage is None else accounting_coverage)
    root = Path(source_root)
    controller = root / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/controller.py'
    _no_links(controller)
    return {'schema': COMMISSION_SCHEMA,
        'authority_commission_sha256': expected_authority_commission_sha256,
        'root_provision_sha256': expected_root_pin,
        'server_certificate_sha256': authority_commission['server_certificate_sha256'],
        'client_certificate_sha256': authority_commission['client_certificate_sha256'],
        'source_identity': implementation_identity(source_root),
        'controller_source_sha256': sha(controller.read_bytes()),
        'objective_policy_sha256': sha(canonical(OBJECTIVE_POLICY)),
        'evaluator_protocol_sha256': sha(canonical(PROTOCOL)),
        'worker_protocol_sha256': sha(canonical(WORKER_PROTOCOL)),
        'launch_profile': _copy(launch_profile),
        'launch_profile_sha256': sha(canonical(launch_profile)),
        'accounting_coverage': coverage, 'accounting_policy_sha256': sha(canonical(coverage)),
        'max_credits': max_credits, 'max_intents': max_intents,
        'operations': list(OPERATIONS), 'scope': _copy(SCOPE)}


def _validate_profile(profile):
    exact(profile, {'frontend', 'worker'})
    # The implementation supplies this validator; there is no Boolean override.
    from .protected_authority_isolation import launch_profile
    for platform_name in ('linux', 'win32'):
        wanted = {role: launch_profile(role, platform_name=platform_name)
                  for role in ('frontend', 'worker')}
        if canonical(profile) == canonical(wanted):
            return
    require(False, 'unknown or weakened protected launch policy')


def validate_commission(value, *, expected_commission_sha256, source_root=SOURCE_ROOT):
    digest(expected_commission_sha256)
    exact(value, {'schema', 'authority_commission_sha256', 'root_provision_sha256',
        'server_certificate_sha256', 'client_certificate_sha256',
        'source_identity', 'controller_source_sha256', 'objective_policy_sha256',
        'evaluator_protocol_sha256', 'worker_protocol_sha256', 'launch_profile',
        'launch_profile_sha256', 'accounting_coverage', 'accounting_policy_sha256',
        'max_credits', 'max_intents', 'operations', 'scope'})
    require(value['schema'] == COMMISSION_SCHEMA and commission_digest(value) == expected_commission_sha256,
            'independently supplied broker commission pin differs')
    for key in ('authority_commission_sha256', 'root_provision_sha256', 'controller_source_sha256',
                'server_certificate_sha256', 'client_certificate_sha256',
                'objective_policy_sha256', 'evaluator_protocol_sha256', 'worker_protocol_sha256',
                'launch_profile_sha256', 'accounting_policy_sha256'):
        digest(value[key])
    require(type(value['max_credits']) is int and 0 < value['max_credits'] <= 32 and
            type(value['max_intents']) is int and 0 < value['max_intents'] <= MAX_INTENTS,
            'broker finite admission limits differ')
    require(value['operations'] == list(OPERATIONS), 'broker operation inventory differs')
    _same(value['scope'], SCOPE, 'broker commission escalates reference scope')
    _validate_profile(value['launch_profile'])
    require(sha(canonical(value['launch_profile'])) == value['launch_profile_sha256'],
            'commissioned launch policy binding differs')
    coverage = validate_coverage(value['accounting_coverage'])
    require(sha(canonical(coverage)) == value['accounting_policy_sha256'],
            'commissioned accounting policy binding differs')
    exact(value['source_identity'], {'code_sha256', 'implementation_sha256'})
    bindings = value['source_identity']['code_sha256']
    require(type(bindings) is dict and 0 < len(bindings) <= 1024 and
            sha(canonical(bindings)) == value['source_identity']['implementation_sha256'],
            'broker source binding differs')
    for name, hashed in bindings.items():
        require(type(name) is str and name and '\\' not in name and
                not name.startswith('/') and '..' not in name.split('/'), 'relative broker source required')
        digest(hashed)
    require(value['objective_policy_sha256'] == sha(canonical(OBJECTIVE_POLICY)) and
            value['evaluator_protocol_sha256'] == sha(canonical(PROTOCOL)) and
            value['worker_protocol_sha256'] == sha(canonical(WORKER_PROTOCOL)),
            'fixed objective or evaluator policy differs')
    if source_root is not None:
        root = Path(source_root)
        _same(value['source_identity'], implementation_identity(root), 'actual broker source closure differs')
        controller = root / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/controller.py'
        require(sha(controller.read_bytes()) == value['controller_source_sha256'],
                'fixed controller source differs')
    return _copy(value)


def validate_intent(value, commission):
    require(type(value) is dict and value.get('operation') in OPERATIONS,
            'frontend operation unavailable')
    fields = {'schema', 'commission_sha256', 'operation', 'nonce'}
    if value['operation'] == 'run':
        fields.add('credits')
    exact(value, fields)
    require(value['schema'] == INTENT_SCHEMA and
            value['commission_sha256'] == commission_digest(commission),
            'frontend commission echo differs from independent broker pin')
    digest(value['nonce'])
    if value['operation'] == 'run':
        require(type(value['credits']) is int and 0 < value['credits'] <= commission['max_credits'],
                'frontend credit request exceeds fixed commission')
    return _copy(value)


def validate_anchor(value, commission, *, previous_headers=None):
    exact(value, {'schema', 'commission_sha256', 'root_provision_sha256', 'headers', 'pending', 'resolved'})
    require(value['schema'] == am.ANCHOR_SCHEMA and
            value['commission_sha256'] == commission['authority_commission_sha256'] and
            value['root_provision_sha256'] == commission['root_provision_sha256'],
            'protected AM anchor identity differs')
    checked = am.verify_headers(value['headers'], root_pin=commission['root_provision_sha256'],
                                anchor_headers=previous_headers)
    require(type(value['resolved']) is list and len(value['resolved']) <= am.MAX_RESOLVED,
            'bounded retained AM resolutions required')
    for resolution in value['resolved']:
        exact(resolution, {'request_sha256', 'request_nonce', 'outcome', 'at_cursor'})
        digest(resolution['request_sha256']); digest(resolution['request_nonce'])
        require(resolution['outcome'] in ('complete', 'denied', 'direct_refusal'),
                'unexpected retained AM resolution')
        cursor = resolution['at_cursor']
        am.al._validate_cursor(cursor)
        require(cursor['serial'] < len(value['headers']) and
                am.event_cursor(value['headers'][cursor['serial']]) == cursor,
                'AM resolution cursor absent from retained history')
    if value['pending'] is not None:
        exact(value['pending'], {'request', 'request_sha256'})
        request = am._validate_request(value['pending']['request'],
            commission['authority_commission_sha256'], commission['root_provision_sha256'])
        require(request['operation'] == 'run' and
                sha(canonical(request)) == value['pending']['request_sha256'],
                'protected AM pending request differs')
    return checked


def validate_state(value, commission):
    exact(value, {'schema', 'commission_sha256', 'headers', 'consumed_nonces', 'pending', 'completed'})
    require(value['schema'] == STATE_SCHEMA and value['commission_sha256'] == commission_digest(commission),
            'protected broker state identity differs')
    am.verify_headers(value['headers'], root_pin=commission['root_provision_sha256'])
    nonces = value['consumed_nonces']
    require(type(nonces) is list and len(nonces) <= commission['max_intents'],
            'broker consumed nonce capacity exceeded')
    for nonce in nonces:
        digest(nonce)
    require(len(set(nonces)) == len(nonces), 'broker nonce replay in retained state')
    completed = value['completed']
    require(type(completed) is list and len(completed) <= len(nonces), 'broker completion inventory differs')
    seen = set()
    for row in completed:
        exact(row, {'nonce', 'intent_sha256', 'operation', 'outcome', 'cursor'})
        digest(row['nonce']); digest(row['intent_sha256'])
        require(row['nonce'] in nonces and row['nonce'] not in seen and
                row['operation'] in OPERATIONS and
                row['outcome'] in ('read', 'complete', 'denied', 'direct_refusal', 'pending', 'reconciled'),
                'broker completion nonce or outcome differs')
        seen.add(row['nonce'])
        am.al._validate_cursor(row['cursor'])
        require(row['cursor']['serial'] < len(value['headers']) and
                am.event_cursor(value['headers'][row['cursor']['serial']]) == row['cursor'],
                'broker completion cursor absent from history')
    if value['pending'] is not None:
        exact(value['pending'], {'intent', 'before_cursor'})
        pending = validate_intent(value['pending']['intent'], commission)
        require(pending['operation'] == 'run' and pending['nonce'] in nonces and pending['nonce'] not in seen,
                'broker pending run is not an unresolved consumed intent')
        cursor = value['pending']['before_cursor']
        am.al._validate_cursor(cursor)
        require(cursor['serial'] < len(value['headers']) and
                am.event_cursor(value['headers'][cursor['serial']]) == cursor,
                'broker pending cursor absent from retained history')
    return _copy(value)


def provision_broker_state(path, commission, *, expected_commission_sha256, trusted_headers,
                           source_root=SOURCE_ROOT):
    commission = validate_commission(commission, expected_commission_sha256=expected_commission_sha256,
                                     source_root=source_root)
    path = Path(path).absolute(); _no_links(path)
    require(path.parent.is_dir() and not path.exists() and
            not path.with_name(path.name + '.lock').exists(), 'new protected broker state required')
    state = {'schema': STATE_SCHEMA, 'commission_sha256': expected_commission_sha256,
             'headers': _copy(trusted_headers), 'consumed_nonces': [], 'pending': None, 'completed': []}
    validate_state(state, commission)
    ak._write_new(path.with_name(path.name + '.lock'), b'L')
    ak._write_new(path, canonical(state))
    import os
    os.chmod(path, 0o600); os.chmod(path.with_name(path.name + '.lock'), 0o600)
    ak._directory_sync(path.parent)
    return _copy(state)


def _admit(state, anchor, intent, commission, mode):
    state = validate_state(state, commission)
    validate_anchor(anchor, commission, previous_headers=state['headers'])
    intent = validate_intent(intent, commission)
    admission = admission_report(commission['accounting_coverage'], mode=mode)
    require(admission['admitted'], 'campaign mode lacks complete trusted admission prerequisites')
    require(intent['nonce'] not in state['consumed_nonces'] and
            len(state['consumed_nonces']) < commission['max_intents'],
            'frontend nonce replay or broker intent capacity exhausted')
    operation = intent['operation']
    pending = state['pending']
    if operation in ('read', 'run'):
        require(pending is None and anchor['pending'] is None,
                'unresolved broker or AM mutation requires read-only reconciliation')
    else:
        require(pending is not None, 'broker has no unresolved mutation to reconcile')
        if anchor['pending'] is not None:
            request = anchor['pending']['request']
            require(request['request_nonce'] == pending['intent']['nonce'] and
                    request['credits'] == pending['intent']['credits'] and
                    request['expected_cursor'] == pending['before_cursor'],
                    'AM pending request differs from protected broker intent')
    state['headers'] = _copy(anchor['headers'])
    state['consumed_nonces'].append(intent['nonce'])
    if operation == 'run':
        state['pending'] = {'intent': _copy(intent),
                            'before_cursor': am.event_cursor(anchor['headers'][-1])}
    return state


def _settle(admitted, anchor_after, intent, commission, *, completed, reply):
    state = _copy(admitted)
    checked = validate_anchor(anchor_after, commission, previous_headers=state['headers'])
    state['headers'] = _copy(anchor_after['headers'])
    cursor = checked['cursor']
    outcome = 'pending' if state['pending'] is not None else 'failed'

    def append(q, result):
        state['completed'].append({'nonce': q['nonce'], 'intent_sha256': sha(canonical(q)),
            'operation': q['operation'], 'outcome': result, 'cursor': _copy(cursor)})

    if completed:
        pending = state['pending']
        if pending is not None:
            q = pending['intent']
            wanted = {'expected_cursor': pending['before_cursor'],
                      'request_nonce': q['nonce'], 'credits': q['credits']}
            actual = checked['request_bindings'].get(q['nonce'])
            terminal = checked['outcomes'].get(q['nonce'])
            if actual == wanted and terminal in ('complete', 'denied') and anchor_after['pending'] is None:
                append(q, terminal); state['pending'] = None; outcome = terminal
            elif (intent['operation'] == 'run' and reply is not None and
                  reply['reason'] == 'protocol_or_authority_refused' and anchor_after['pending'] is None):
                append(q, 'direct_refusal'); state['pending'] = None; outcome = 'direct_refusal'
        if intent['operation'] == 'read':
            outcome = 'read'; append(intent, outcome)
        elif intent['operation'] == 'reconcile':
            outcome = 'pending' if state['pending'] is not None else 'reconciled'
            append(intent, outcome)
    validate_state(state, commission)
    response = {'schema': RESPONSE_SCHEMA, 'commission_sha256': commission_digest(commission),
        'authority_commission_sha256': commission['authority_commission_sha256'],
        'root_provision_sha256': commission['root_provision_sha256'],
        'intent_sha256': sha(canonical(intent)), 'operation': intent['operation'],
        'outcome': outcome, 'cursor': _copy(cursor), 'pending_retained': state['pending'] is not None,
        'worker_reissued': False, 'promotion_authorized': False}
    return state, response


def _checked_exchange(record, commission):
    """Purely recheck the actual AM request/reply images retained by the client."""
    op, exchange, intent = record['am_operation'], record['am_exchange'], record['intent']
    if op is None:
        require(record['error_type'] is not None and exchange is None and record['issued_request'] is None,
                'missing AM operation cannot establish completed dispatch')
        return None
    exact(op, {'schema', 'operation', 'pid', 'sequence', 'exchange_sequence',
        'started_at_utc', 'anchor_before', 'pending_before_send', 'request', 'completed',
        'error_type', 'anchor_after', 'anchor_after_sha256', 'completed_at_utc'})
    expected_operation = ('run' if intent['operation'] == 'run' else
                          'reconcile' if intent['operation'] == 'reconcile' and
                          record['anchor_before']['pending'] is not None else 'read')
    require(op['schema'] == 'phase17am.client-operation.v1' and
            op['operation'] == expected_operation and type(op['pid']) is int and op['pid'] > 0 and
            type(op['completed']) is bool and op['error_type'] == record['error_type'] and
            op['anchor_after_sha256'] == sha(canonical(record['anchor_after'])),
            'AM operation identity, mode, completion or anchor digest differs')
    nat(op['sequence']); nat(op['exchange_sequence'])
    require(op['anchor_before'] == record['anchor_before'] and op['anchor_after'] == record['anchor_after'],
            'AM operation anchor join differs')
    request = op['request']
    require(request == record['issued_request'], 'broker issued request differs from original AM operation')
    if request is None:
        require(op['completed'] is False and record['error_type'] is not None and exchange is None,
                'missing AM request cannot establish transport completion')
        return None
    request = am._validate_request(request, commission['authority_commission_sha256'],
                                    commission['root_provision_sha256'])
    expected_op = 'run' if intent['operation'] == 'run' else 'read'
    require(request['operation'] == expected_op and
            request['expected_cursor'] == am.event_cursor(record['anchor_before']['headers'][-1]),
            'AM request operation or retained current cursor differs')
    if expected_op == 'run':
        require(request['request_nonce'] == intent['nonce'] and request['credits'] == intent['credits'],
                'AM mutation nonce or credit differs from frontend intent')
        pending = op['pending_before_send']
        expected_pending = _copy(record['anchor_before'])
        expected_pending['pending'] = {'request': request, 'request_sha256': sha(canonical(request))}
        require(pending == expected_pending, 'AM mutation lacks exact durable write-ahead request')
    else:
        require(op['pending_before_send'] is None, 'read-only AM operation wrote mutation intent')
    require(exchange is not None and exchange['commission_sha256'] == commission['authority_commission_sha256'] and
            exchange['root_provision_sha256'] == commission['root_provision_sha256'] and
            exchange['schema'] == am.NATIVE_SCHEMA and exchange['role'] == 'client' and
            exchange['pid'] == op['pid'] and exchange['sequence'] == op['exchange_sequence'],
            'AM transport observation missing or bound to another authority')
    request_frame = bytes.fromhex(exchange['request_frame_hex'])
    if exchange['request_sent']:
        require(exchange['peer_pin_matched'] is True and request_frame == am.frame_bytes(request),
                'AM transport request frame or authenticated peer join differs')
        peer = bytes.fromhex(exchange['peer_certificate_der_hex'])
        require(sha(peer) == exchange['peer_certificate_sha256'] == commission['server_certificate_sha256'] and
                exchange['tls_version'] == 'TLSv1.3', 'actual AM peer differs from commissioned certificate')
    else:
        require(record['error_type'] is not None, 'unsent AM request cannot establish completion')
    raw = bytes.fromhex(exchange['response_frame_hex'])
    if record['error_type'] is None:
        require(exchange['error_type'] is None and
                exchange['abandoned_response'] == record['abandon_response'],
                'actual AM response-abandonment attribution differs')
    if not raw:
        require(exchange['abandoned_response'] is True or record['error_type'] is not None,
                'missing AM reply without retained ambiguity')
        return None
    require(len(raw) >= 4 and int.from_bytes(raw[:4], 'big') == len(raw) - 4,
            'retained AM reply framing differs')
    reply = load_json_strict(raw[4:], require_canonical=True)
    exact(reply, {'schema', 'commission_sha256', 'root_provision_sha256', 'request_sha256',
        'challenge', 'operation', 'accepted', 'reason', 'before', 'after', 'headers', 'result'})
    require(reply['schema'] == am.RESPONSE_SCHEMA and
            reply['commission_sha256'] == commission['authority_commission_sha256'] and
            reply['root_provision_sha256'] == commission['root_provision_sha256'] and
            reply['request_sha256'] == sha(canonical(request)) and
            reply['challenge'] == request['challenge'] and reply['operation'] == request['operation'],
            'retained AM reply request, challenge or authority binding differs')
    require(type(reply['accepted']) is bool and reply['reason'] in
            (None, 'aggregate_budget_denied', 'protocol_or_authority_refused') and
            reply['accepted'] == (reply['reason'] is None), 'retained AM reply outcome shape differs')
    require((type(reply['result']) is dict if reply['accepted'] else reply['result'] is None),
            'retained AM result shape differs')
    checked = am.verify_headers(reply['headers'], root_pin=commission['root_provision_sha256'],
                                anchor_headers=record['anchor_before']['headers'])
    require(checked['cursor'] == reply['after'], 'retained AM reply final cursor differs')
    before = reply['before']; am.al._validate_cursor(before)
    require(before['serial'] < len(reply['headers']) and
            am.event_cursor(reply['headers'][before['serial']]) == before and
            before['serial'] <= reply['after']['serial'], 'retained AM before cursor differs')
    if expected_op == 'read' or reply['reason'] == 'protocol_or_authority_refused':
        require(before == reply['after'], 'read or protocol refusal changed the authority')
    elif reply['accepted'] or reply['reason'] == 'aggregate_budget_denied':
        wanted = {key: request[key] for key in ('expected_cursor', 'request_nonce', 'credits')}
        require(checked['request_bindings'].get(request['request_nonce']) == wanted and
                checked['outcomes'].get(request['request_nonce']) ==
                ('complete' if reply['accepted'] else 'denied') and before == request['expected_cursor'],
                'retained AM completion/denial lacks exact durable mutation')
    return reply


def verify_broker_record(record, commission, source_root=SOURCE_ROOT):
    commission = validate_commission(commission,
        expected_commission_sha256=record['commission_sha256'], source_root=source_root)
    exact(record, {'schema', 'commission_sha256', 'intent', 'mode', 'abandon_response',
        'state_before', 'admitted_state', 'state_after', 'anchor_before', 'anchor_after',
        'am_operation', 'am_exchange', 'issued_request', 'response', 'error_type'})
    require(record['schema'] == RECORD_SCHEMA and type(record['abandon_response']) is bool,
            'broker dispatch record profile differs')
    require(record['error_type'] is None or
            (type(record['error_type']) is str and 0 < len(record['error_type']) <= 128),
            'broker error attribution differs')
    intent = validate_intent(record['intent'], commission)
    admitted = _admit(record['state_before'], record['anchor_before'], intent, commission, record['mode'])
    _same(record['admitted_state'], admitted, 'broker nonce consumption or write-ahead state differs')
    reply = _checked_exchange(record, commission)
    operation = record['am_operation']
    completed = operation is not None and operation['completed'] is True and record['error_type'] is None
    if record['error_type'] is None:
        require(operation is not None and operation['completed'] is True,
                'successful broker operation lacks original AM completion')
    wanted, response = _settle(admitted, record['anchor_after'], intent, commission,
                                completed=completed, reply=reply)
    _same(record['state_after'], wanted, 'broker settlement differs from actual AM history')
    _same(record['response'], response, 'sanitized broker response differs')
    return {'intent_sha256': sha(canonical(intent)), 'operation': intent['operation'],
            'outcome': response['outcome'], 'pending_retained': response['pending_retained'],
            'network_exchanges': int(record['am_exchange'] is not None),
            'mutation_issued': record['issued_request'] is not None and
                               record['issued_request']['operation'] == 'run',
            'promotion_authorized': False}


class ProtectedAuthorityBroker:
    def __init__(self, commission, *, expected_commission_sha256, client, state_path,
                 source_root=SOURCE_ROOT):
        self.source_root = Path(source_root).absolute()
        require(self.source_root.resolve() == SOURCE_ROOT.resolve(),
                'broker must pin its actually executing source root')
        self.commission = validate_commission(commission,
            expected_commission_sha256=expected_commission_sha256, source_root=self.source_root)
        require(isinstance(client, am.AuthorityTransportClient), 'fixed credential-bearing AM client required')
        am.validate_commission(client.commission,
            expected_commission_sha256=self.commission['authority_commission_sha256'],
            expected_root_pin=self.commission['root_provision_sha256'], source_root=self.source_root)
        require(client.pin == self.commission['authority_commission_sha256'] and
                client.root_pin == self.commission['root_provision_sha256'] and
                all(client.commission[k] == self.commission[k] for k in
                    ('server_certificate_sha256', 'client_certificate_sha256')),
                'actual AM client pins differ from broker commission')
        self.client = client
        self.state_path = Path(state_path).absolute(); _no_links(self.state_path)
        require(self.state_path.is_file(), 'independently provisioned protected broker state required')
        require(self.state_path != client.anchor_path and
                self.state_path.with_name(self.state_path.name + '.lock') != client.anchor_path,
                'broker state and AM anchor must be separate')
        self.last_record = None
        validate_state(self._state(), self.commission)

    def _state(self):
        _no_links(self.state_path)
        return load_json_strict(self.state_path.read_bytes(), require_canonical=True)

    def _anchor(self):
        _no_links(self.client.anchor_path)
        return load_json_strict(self.client.anchor_path.read_bytes(), require_canonical=True)

    def dispatch(self, intent, *, abandon_response=False, mode='reference'):
        self.last_record = None
        require(type(abandon_response) is bool and
                (not abandon_response or (type(intent) is dict and intent.get('operation') == 'run')),
                'trusted response-abandonment mode requires a run')
        validate_commission(self.commission,
            expected_commission_sha256=commission_digest(self.commission), source_root=self.source_root)
        lock = ak._LifetimeLock(self.state_path.with_name(self.state_path.name + '.lock'))
        try:
            before, anchor_before = self._state(), self._anchor()
            intent = validate_intent(intent, self.commission)
            admitted = _admit(before, anchor_before, intent, self.commission, mode)
            am._replace(self.state_path, admitted)
            _same(self._state(), admitted, 'protected broker intent commit readback differs')
            operation_number, exchange_number = self.client.operation_sequence, self.client.sequence
            error = None
            try:
                if intent['operation'] == 'run':
                    self.client.run(intent['credits'], intent['nonce'], abandon_response=abandon_response)
                elif intent['operation'] == 'read':
                    self.client.read()
                elif anchor_before['pending'] is not None:
                    self.client.reconcile()
                else:
                    # AM may have received a reply immediately before a broker
                    # crash. Reading its protected history never reissues work.
                    self.client.read()
            except BaseException as caught:
                error = caught
            op_path = self.client.native / ('operation-%04d.json' % operation_number)
            exchange_path = self.client.native / ('result-%04d.json' % exchange_number)
            operation = load_json_strict(op_path.read_bytes(), require_canonical=True) if op_path.is_file() else None
            exchange = load_json_strict(exchange_path.read_bytes(), require_canonical=True) if exchange_path.is_file() else None
            anchor_after = self._anchor()
            record = {'schema': RECORD_SCHEMA, 'commission_sha256': commission_digest(self.commission),
                'intent': _copy(intent), 'mode': mode, 'abandon_response': abandon_response,
                'state_before': before, 'admitted_state': admitted, 'state_after': None,
                'anchor_before': anchor_before, 'anchor_after': anchor_after,
                'am_operation': operation, 'am_exchange': exchange,
                'issued_request': None if operation is None else operation['request'],
                'response': None, 'error_type': None if error is None else type(error).__name__}
            reply = _checked_exchange(record, self.commission)
            completed = operation is not None and operation['completed'] is True and error is None
            after, response = _settle(admitted, anchor_after, intent, self.commission,
                                      completed=completed, reply=reply)
            record.update(state_after=after, response=response)
            verify_broker_record(record, self.commission, source_root=self.source_root)
            lock.check()
            am._replace(self.state_path, after)
            _same(self._state(), after, 'protected broker settlement readback differs')
            self.last_record = _copy(record)
            if error is not None:
                raise error
            return _copy(record)
        finally:
            lock.close()
