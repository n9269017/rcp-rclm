"""AM certificates derived from original authenticated client/server observations.

The pure prepared-packet validator rechecks source bindings, AL semantics, raw
TLS observations and native files before this projection runs. No formal state
is accepted as an input. Certificate identities are exact strings; TLS, hashes,
physical isolation and independently durable anchors remain explicit premises.
"""
from __future__ import annotations

from pathlib import Path
import re

from rcp_rclm_runtime.canonical.json import load_json_strict
from .resource_ledger import canonical, exact, nat, require, sha
from .successor_lean import string
from .controller_continuation_lean import negative_location

MODULES = ('AuthenticatedAuthority',)
POSITIVE = 'AuthenticatedAuthorityExamples'
NEGATIVES = (
    'WrongTransportCommission', 'WrongTransportRoot', 'WrongTLSServer',
    'WrongTLSClient', 'WrongTLSAuthorityCA', 'RemoteAdministrativeOperation',
    'StaleAuthenticatedCursor', 'ReplayedAuthenticatedNonce',
    'WrongAuthenticatedReplyDigest', 'WrongAuthenticatedReplyChallenge',
    'RolledBackAuthenticatedReply', 'ForkedAuthenticatedPrefix',
    'PendingAuthenticatedRequestRetried', 'UnresolvedAuthenticatedRequestCleared',
    'ClonedAuthenticatedAuthorityImpossible',
)
LABELS = (*MODULES, POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
GENERIC_NAMES = tuple('Phase17AuthenticatedAuthority.' + name for name in (
    'dispatch_spec', 'dispatch_bound_identity', 'wrong_server_refused',
    'wrong_client_refused', 'wrong_ca_refused', 'wrong_commission_refused',
    'wrong_root_refused', 'administrative_operation_refused', 'run_current_cursor',
    'stale_run_refused', 'replayed_run_refused', 'prefix_reflexive', 'prefix_length',
    'reply_bound_identity', 'reply_currentness_monotone',
    'wrong_response_request_refused', 'wrong_response_challenge_refused',
    'rollback_reply_refused', 'forked_prefix_refused', 'begin_sets_pending',
    'begin_keeps_anchor', 'pending_blocks_mutation', 'missing_response_keeps_pending',
    'settlement_matches_pending', 'reconcile_is_read_only',
    'reconcile_clear_requires_terminal', 'unresolved_reconcile_preserves_pending',
    'identical_authorities_accept_identically', 'joint_rollback_preserves_local_consistency',
))
SELECTED_NAMES = tuple('Phase17AuthenticatedAuthorityExamples.' + name for name in (
    'first_authenticated_dispatch', 'first_reply_bound', 'first_write_ahead_pending',
    'first_matching_settlement', 'restart_reconciliation', 'lost_reply_blocks_retry',
    'reconcile_requires_read', 'reconcile_terminal_completion',
    'cloned_authenticated_root_outside_guarantee',
))
NAMES = (*GENERIC_NAMES, *SELECTED_NAMES)


def _same(actual, expected, message):
    require(canonical(actual) == canonical(expected), message)


def _cursor(value):
    from .durable_campaign import _validate_cursor
    value = _validate_cursor(value)
    return {name: value[key] for name, key in (
        ('provision', 'root_provision_sha256'), ('epoch', 'epoch'), ('serial', 'serial'),
        ('head', 'root_head'), ('journal', 'journal_sha256'), ('image', 'snapshot_sha256'))}


def _mutation(value):
    exact(value, {'expected_cursor', 'request_nonce', 'credits'})
    return {'expected': _cursor(value['expected_cursor']), 'nonce': value['request_nonce'],
            'credits': nat(value['credits'])}


def _header(value):
    from .authority_transport import event_cursor
    return {'cursor': _cursor(event_cursor(value)), 'kind': value['kind'],
            'request': None if value['request'] is None else _mutation(value['request'])}


def _request(value):
    from .authority_transport import _validate_request
    _validate_request(value, value['commission_sha256'], value['root_provision_sha256'])
    return {'commission': value['commission_sha256'], 'root': value['root_provision_sha256'],
        'operation': value['operation'], 'nonce': value['request_nonce'],
        'challenge': value['challenge'], 'expected': _cursor(value['expected_cursor']),
        'credits': nat(value.get('credits', 0)), 'digest': sha(canonical(value))}


def _anchor(value):
    from .authority_transport import event_cursor, verify_headers
    verify_headers(value['headers'], root_pin=value['root_provision_sha256'])
    pending = value['pending']
    if pending is not None:
        exact(pending, {'request', 'request_sha256'})
        require(pending['request_sha256'] == sha(canonical(pending['request'])),
                'original pending request digest differs')
    return {'commission': value['commission_sha256'], 'root': value['root_provision_sha256'],
        'current': _cursor(event_cursor(value['headers'][-1])),
        'history': [_header(event) for event in value['headers']],
        'pending': None if pending is None else _request(pending['request'])}


def _reply(value):
    require(type(value['accepted']) is bool, 'exact authenticated reply acceptance required')
    return {'commission': value['commission_sha256'], 'root': value['root_provision_sha256'],
        'requestDigest': value['request_sha256'], 'challenge': value['challenge'],
        'operation': value['operation'], 'before': _cursor(value['before']),
        'after': _cursor(value['after']), 'history': [_header(event) for event in value['headers']],
        'accepted': value['accepted']}


def _frame(encoded):
    require(type(encoded) is str and encoded, 'original authenticated frame required')
    raw = bytes.fromhex(encoded)
    require(raw.hex() == encoded and len(raw) > 4 and int.from_bytes(raw[:4], 'big') == len(raw) - 4,
            'original authenticated frame length differs')
    return load_json_strict(raw[4:], require_canonical=True)


def _json_images(packet):
    result = {}
    for name, encoded in packet['native_images'].items():
        if name.endswith('.json'):
            raw = bytes.fromhex(encoded)
            require(raw.hex() == encoded, 'original AM image requires canonical hex')
            result[name] = load_json_strict(raw, require_canonical=False)
    return result


def _peer_identity(observation, expected, label):
    encoded = observation['peer_certificate_der_hex']
    require(type(encoded) is str and encoded, 'observed TLS peer certificate missing: ' + label)
    raw = bytes.fromhex(encoded)
    require(raw.hex() == encoded and sha(raw) == observation['peer_certificate_sha256'] == expected and
            observation['tls_version'] == 'TLSv1.3' and observation['peer_pin_matched'] is True,
            'actual TLS peer observation differs: ' + label)
    return expected


def _exchange(images, request, commission, *, abandoned=False):
    from .authority_transport import frame_bytes
    framed = frame_bytes(request).hex()
    clients = [(name, value) for name, value in images.items()
               if name.startswith('client/') and value.get('schema') == 'phase17am.tls-native.v1'
               and value.get('role') == 'client' and value.get('request_frame_hex') == framed
               and 'peer_certificate_der_hex' in value]
    servers = [(name, value) for name, value in images.items()
               if name.startswith('authority/') and value.get('schema') == 'phase17am.tls-native.v1'
               and value.get('role') == 'server' and value.get('request_frame_hex') == framed
               and value.get('response_frame_hex')]
    require(len(clients) == 1 and len(servers) == 1,
            'one original client/server exchange required for selected request')
    client_name, client = clients[0]; server_name, server = servers[0]
    _peer_identity(client, commission['server_certificate_sha256'], 'server')
    _peer_identity(server, commission['client_certificate_sha256'], 'client')
    require(client['request_sent'] is True, 'selected client did not send original request')
    response = _frame(server['response_frame_hex'])
    if abandoned:
        require(client.get('abandoned_response') is True and not client.get('response_frame_hex'),
                'selected missing reply was not actually abandoned')
    else:
        _same(_frame(client['response_frame_hex']), response, 'original TLS reply endpoints differ')
        require(server['response_sent'] is True, 'selected original server response not sent')
    require(response['request_sha256'] == sha(canonical(request)) and
            response['challenge'] == request['challenge'] and
            response['operation'] == request['operation'], 'selected reply identity differs')
    return {'request': request, 'response': response, 'client': client, 'server': server,
            'client_path': client_name, 'server_path': server_name}


def _prepared(value, root):
    from .authenticated_authority_capture import PreparedAuthenticatedAuthority
    require(type(value) is PreparedAuthenticatedAuthority, 'exact prepared authenticated authority required')
    return PreparedAuthenticatedAuthority(value.packet_bytes, root)


def project(prepared, root):
    """Derive values from validated original operations, never packet formal fields."""
    checked = _prepared(prepared, root)
    packet = checked.packet
    require(len(packet['cases']) == 1, 'one selected authenticated campaign required')
    case = packet['cases'][0]
    commission = case['commission']
    images = _json_images(packet)
    operations = [(name, value) for name, value in images.items()
                  if name.startswith('client/') and '/operation-' in name and
                  all(key in value for key in ('anchor_before', 'anchor_after', 'request'))]
    completed = []
    abandoned = []
    reconciliations = []
    for name, value in operations:
        request = value['request']
        if type(request) is not dict:
            continue
        before, after = value['anchor_before'], value['anchor_after']
        if type(before) is not dict or type(after) is not dict:
            continue
        if request['operation'] == 'run' and before['pending'] is None:
            if after['pending'] is not None:
                abandoned.append((name, value))
            elif any(item['request_sha256'] == sha(canonical(request)) and item['outcome'] == 'complete'
                     for item in after['resolved']):
                completed.append((name, value))
        elif request['operation'] == 'read' and before['pending'] is not None and after['pending'] is None:
            reconciliations.append((name, value))
    require(len(completed) == 1 and len(abandoned) == 1 and len(reconciliations) == 1,
            'exact first completion, abandoned mutation and terminal read reconciliation required')
    first_name, first = completed[0]; lost_name, lost = abandoned[0]
    reconcile_name, reconciliation = reconciliations[0]
    direct = _exchange(images, first['request'], commission)
    missing = _exchange(images, lost['request'], commission, abandoned=True)
    recovered = _exchange(images, reconciliation['request'], commission)
    require(direct['response']['accepted'] is True and missing['response']['accepted'] is True and
            recovered['response']['accepted'] is True, 'selected admitted work/reconciliation differs')
    _same(lost['anchor_after'], reconciliation['anchor_before'], 'saved ambiguous anchor replaced before reconcile')
    require(first['anchor_before']['pending'] is None and first['anchor_after']['pending'] is None and
            lost['anchor_before']['pending'] is None and lost['anchor_after']['pending'] is not None and
            reconciliation['anchor_after']['pending'] is None,
            'selected actual pending-state transitions differ')
    _same(lost['anchor_after']['pending']['request'], lost['request'], 'abandoned pending request substituted')
    require(recovered['response']['after']['epoch'] > missing['response']['before']['epoch'],
            'selected unresolved request was not reconciled after authority restart')
    first_pending = dict(first['anchor_before'])
    first_pending['pending'] = {'request': first['request'], 'request_sha256': sha(canonical(first['request']))}
    require('pending_before_send' in first, 'original write-ahead observation missing')
    _same(first['pending_before_send'], first_pending, 'first pending write was not retained before exchange')
    _same(lost['pending_before_send'], lost['anchor_after'], 'missing-reply anchor did not preserve pending write')
    ca = commission['ca_certificate_sha256']
    projected = {
        'packet_sha256': sha(checked.packet_bytes),
        'commission': {'identity': sha(canonical(commission)), 'root': case['root_provision_sha256'],
            'server': commission['server_certificate_sha256'],
            'client': commission['client_certificate_sha256'], 'ca': ca},
        'channel': {'server': direct['client']['peer_certificate_sha256'],
            'client': direct['server']['peer_certificate_sha256'], 'ca': ca,
            'version': direct['client']['tls_version']},
        'firstRequest': _request(first['request']), 'firstReply': _reply(direct['response']),
        'firstIdle': _anchor(first['anchor_before']), 'firstPending': _anchor(first_pending),
        'firstSettled': _anchor(first['anchor_after']),
        'lostRequest': _request(lost['request']), 'lostReply': _reply(missing['response']),
        'lostIdle': _anchor(lost['anchor_before']), 'lostAnchor': _anchor(lost['anchor_after']),
        'reconcileRequest': _request(reconciliation['request']),
        'reconcileReply': _reply(recovered['response']),
        'reconciledAnchor': _anchor(reconciliation['anchor_after']),
        'original_operation_paths': [first_name, lost_name, reconcile_name],
        'original_exchange_paths': [direct['client_path'], direct['server_path'],
            missing['client_path'], missing['server_path'], recovered['client_path'], recovered['server_path']],
    }
    # Used nonces are derived from the original event headers preceding each
    # dispatch, including accepted denials; they are never caller assertions.
    for name, exchange in (('firstConsumed', direct), ('lostConsumed', missing)):
        before = exchange['response']['before']['serial']
        projected[name] = [event['request']['request_nonce']
            for event in exchange['response']['headers'][:before + 1]
            if event['kind'] in ('reserve', 'deny')]
    return projected


def _nat(value):
    return str(nat(value))


def _cursor_literal(value):
    return '⟨' + ', '.join((string(value['provision']), _nat(value['epoch']), _nat(value['serial']),
        string(value['head']), string(value['journal']), string(value['image']))) + '⟩'


def _mutation_literal(value):
    return '⟨' + ', '.join((_cursor_literal(value['expected']), string(value['nonce']), _nat(value['credits']))) + '⟩'


def _request_literal(value):
    return '⟨' + ', '.join((string(value['commission']), string(value['root']), string(value['operation']),
        string(value['nonce']), string(value['challenge']), _cursor_literal(value['expected']),
        _nat(value['credits']), string(value['digest']))) + '⟩'


def _headers_literal(values):
    rows = []
    for value in values:
        mutation = 'none' if value['request'] is None else 'some ' + _mutation_literal(value['request'])
        rows.append('⟨' + _cursor_literal(value['cursor']) + ', ' + string(value['kind']) + ', ' + mutation + '⟩')
    return '[' + ', '.join(rows) + ']'


def _anchor_literal(value):
    pending = 'none' if value['pending'] is None else 'some ' + _request_literal(value['pending'])
    return '⟨' + ', '.join((string(value['commission']), string(value['root']),
        _cursor_literal(value['current']), _headers_literal(value['history']), pending)) + '⟩'


def _reply_literal(value):
    return '⟨' + ', '.join((string(value['commission']), string(value['root']),
        string(value['requestDigest']), string(value['challenge']), string(value['operation']),
        _cursor_literal(value['before']), _cursor_literal(value['after']),
        _headers_literal(value['history']), str(value['accepted']).lower())) + '⟩'


def render_selected(projection, root):
    generic = (Path(root) / 'lean/phase17_bridge/AuthenticatedAuthority.lean').read_bytes()
    require(generic.startswith(b'import Std\nimport Lean.Elab.Tactic.Omega\n') and
            generic.rstrip().endswith(b'end Phase17AuthenticatedAuthority'),
            'generic authenticated-authority source differs')
    text = generic.decode() + '\n\nnamespace Phase17AuthenticatedAuthorityExamples\nopen Phase17AuthenticatedAuthority\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 16000000\n'
    text += 'def packetSha256 : String := ' + string(projection['packet_sha256']) + '\n'
    text += 'def commission : Commission := ⟨' + ', '.join(string(projection['commission'][name])
        for name in ('identity', 'root', 'server', 'client', 'ca')) + '⟩\n'
    text += 'def channel : Channel := ⟨' + ', '.join(string(projection['channel'][name])
        for name in ('server', 'client', 'ca', 'version')) + '⟩\n'
    for name in ('firstRequest', 'lostRequest', 'reconcileRequest'):
        text += f'def {name} : Request := ' + _request_literal(projection[name]) + '\n'
    for name in ('firstReply', 'lostReply', 'reconcileReply'):
        text += f'def {name} : Reply := ' + _reply_literal(projection[name]) + '\n'
    for name in ('firstIdle', 'firstPending', 'firstSettled', 'lostIdle', 'lostAnchor', 'reconciledAnchor'):
        text += f'def {name} : Anchor := ' + _anchor_literal(projection[name]) + '\n'
    for name in ('firstConsumed', 'lostConsumed'):
        text += f'def {name} : List String := [' + ', '.join(string(v) for v in projection[name]) + ']\n'
    text += '''theorem first_authenticated_dispatch :
    dispatch commission channel firstReply.before firstConsumed firstRequest = some "run" := by decide +kernel
theorem first_reply_bound : ReplyBound commission channel firstIdle firstRequest firstReply := by decide +kernel
theorem first_write_ahead_pending : beginMutation commission firstIdle firstRequest = some firstPending := by decide +kernel
theorem first_matching_settlement :
    receiveReply commission channel firstPending firstRequest firstReply = some firstSettled := by decide +kernel
theorem restart_reconciliation : lostRequest.expected.epoch < reconcileReply.after.epoch ∧
    dispatch commission channel lostReply.before lostConsumed lostRequest = some "run" := by decide +kernel
theorem lost_reply_blocks_retry : lostAnchor.pending = some lostRequest ∧
    beginMutation commission lostAnchor lostRequest = none := by decide +kernel
theorem reconcile_requires_read : reconcileRequest.operation = "read" ∧
    reconcile commission channel lostAnchor reconcileRequest reconcileReply = some reconciledAnchor := by decide +kernel
theorem reconcile_terminal_completion : terminalFor lostRequest reconcileReply.history = true ∧
    reconciledAnchor.pending = none ∧ lostAnchor.current.serial ≤ reconciledAnchor.current.serial := by decide +kernel
theorem cloned_authenticated_root_outside_guarantee :
    ∃ first second : Cursor, first = firstReply.before ∧ second = firstReply.before ∧
      dispatch commission channel first firstConsumed firstRequest = some firstRequest.operation ∧
      dispatch commission channel second firstConsumed firstRequest = some firstRequest.operation := by
  apply identical_authorities_accept_identically
  exact first_authenticated_dispatch
end Phase17AuthenticatedAuthorityExamples
'''
    return text.encode()


def render_positive():
    return ('import AuthenticatedAuthority\n' + '\n'.join('#print axioms ' + name for name in NAMES) + '\n').encode()


def render_negative(label):
    require(label in NEGATIVES, 'exact authenticated-authority negative required')
    call = 'dispatch commission channel firstReply.before firstConsumed '
    wrong = {
        'WrongTransportCommission': call + '{ firstRequest with commission := "untrusted" } ≠ none',
        'WrongTransportRoot': call + '{ firstRequest with root := "untrusted" } ≠ none',
        'WrongTLSServer': 'dispatch commission { channel with server := "untrusted" } firstReply.before firstConsumed firstRequest ≠ none',
        'WrongTLSClient': 'dispatch commission { channel with client := "untrusted" } firstReply.before firstConsumed firstRequest ≠ none',
        'WrongTLSAuthorityCA': 'dispatch commission { channel with ca := "untrusted" } firstReply.before firstConsumed firstRequest ≠ none',
        'RemoteAdministrativeOperation': call + '{ firstRequest with operation := "reopen" } ≠ none',
        'StaleAuthenticatedCursor': call + '{ firstRequest with expected := { firstRequest.expected with head := "stale" } } ≠ none',
        'ReplayedAuthenticatedNonce': 'dispatch commission channel firstReply.before [firstRequest.nonce] firstRequest ≠ none',
        'WrongAuthenticatedReplyDigest': 'acceptReply commission channel firstPending firstRequest { firstReply with requestDigest := "untrusted" } = true',
        'WrongAuthenticatedReplyChallenge': 'acceptReply commission channel firstPending firstRequest { firstReply with challenge := "untrusted" } = true',
        'RolledBackAuthenticatedReply': 'acceptReply commission channel lostAnchor reconcileRequest { reconcileReply with history := firstIdle.history, before := firstIdle.current, after := firstIdle.current } = true',
        'ForkedAuthenticatedPrefix': 'acceptReply commission channel { firstPending with history := firstPending.history.map (fun h => if h.cursor.serial = 0 then { h with cursor := { h.cursor with head := "forked" } } else h) } firstRequest firstReply = true',
        'PendingAuthenticatedRequestRetried': 'beginMutation commission firstPending firstRequest ≠ none',
        'UnresolvedAuthenticatedRequestCleared': 'reconciledPending lostAnchor { reconcileReply with history := lostAnchor.history } = none',
        'ClonedAuthenticatedAuthorityImpossible': call + 'firstRequest = none',
    }
    text = '''import AuthenticatedAuthority
namespace Phase17AuthenticatedAuthorityControl
open Phase17AuthenticatedAuthority Phase17AuthenticatedAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    text += 'def wrongClaim : Bool := decide (' + wrong[label] + ')\n'
    text += 'theorem actual_rejection : wrongClaim = false := by decide +kernel\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    return (text + 'end Phase17AuthenticatedAuthorityControl\n').encode()


def sources(prepared, root):
    projection = project(prepared, root)
    result = {MODULES[0]: render_selected(projection, root), POSITIVE: render_positive()}
    result.update({name: render_negative(name) for name in NEGATIVES})
    for name, raw in result.items():
        require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', raw),
                'forbidden proof source token: ' + name)
    return result


def parse_audits(stdout):
    require(type(stdout) is str, 'exact audit output text required')
    cursor, audits = 0, {}
    for name in NAMES:
        match = re.compile("'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*", re.S).match(stdout, cursor)
        require(match is not None, 'missing or reordered authenticated-authority audit: ' + name)
        dependencies = [] if match[1] is None else [item.strip() for item in match[1].split(',') if item.strip()]
        require(len(dependencies) == len(set(dependencies)) and set(dependencies) <= ALLOWED_AXIOMS,
                'unapproved authenticated-authority audit dependency')
        audits[name] = dependencies; cursor = match.end()
    require(cursor == len(stdout), 'unexpected authenticated-authority audit output')
    return audits


def validate_negative(label, raw, stdout, stderr, returncode):
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'unexpected authenticated-authority negative diagnostic')
    return {'label': label, 'intended_rejection': True, 'line': line, 'column': col}
