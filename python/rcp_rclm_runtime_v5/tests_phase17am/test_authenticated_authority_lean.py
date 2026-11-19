"""Pure AM projection and exact Lean-result rejection contracts.

These synthetic header fixtures test parsers and source construction. They are
not native authentication observations or accepted campaign evidence. The real
application separately obtains original TLS sessions and compiles its packet.
"""
from copy import deepcopy
from pathlib import Path
import unittest

from rcp_rclm_runtime_v5.phase17 import authenticated_authority_lean as formal
from rcp_rclm_runtime_v5.phase17 import authority_transport as transport
from rcp_rclm_runtime_v5.phase17 import durable_campaign as al
from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, sha

ROOT = Path(__file__).resolve().parents[3]


def synthetic_headers():
    headers = []
    for index, kind in enumerate(('provision', 'reopen', 'reserve', 'launch', 'complete',
                                   'reserve', 'launch', 'complete', 'reopen')):
        epoch = 0 if index == 0 else 1 if index < 8 else 2
        mutation = None
        if kind == 'reserve':
            mutation = {'expected_cursor': transport.event_cursor(headers[-1]),
                        'request_nonce': ('a' if index == 2 else 'c') * 64, 'credits': 2}
        core = {'schema': al.EVENT_SCHEMA, 'kind': kind, 'serial': index, 'epoch': epoch,
            'previous_root_head': '0' * 64 if not headers else headers[-1]['root_head'],
            'root_provision_sha256': '1' * 64,
            'boot_nonce': str(epoch) * 64 if kind == 'reopen' else None,
            'request': mutation, 'session_sha256': sha(str(index).encode()) if kind == 'complete' else None,
            'journal_sha256': sha(('journal' + str(index)).encode()),
            'snapshot_sha256': sha(('snapshot' + str(index)).encode())}
        headers.append({**core, 'root_head': sha(al.DOMAIN + b'EVENT\0' + canonical(core))})
    transport.verify_headers(headers, root_pin='1' * 64)
    return headers


def synthetic_request(headers, operation='run', second=False):
    value = {'schema': transport.REQUEST_SCHEMA, 'commission_sha256': '2' * 64,
        'root_provision_sha256': '1' * 64, 'operation': operation,
        'request_nonce': ('c' if second else 'a') * 64,
        'challenge': ('d' if second else 'b') * 64,
        'expected_cursor': transport.event_cursor(headers[4 if second else 1])}
    if operation == 'run':
        value['credits'] = 2
    return value


def synthetic_anchor(headers, pending=None):
    return {'schema': transport.ANCHOR_SCHEMA, 'commission_sha256': '2' * 64,
        'root_provision_sha256': '1' * 64, 'headers': deepcopy(headers),
        'pending': None if pending is None else {'request': pending, 'request_sha256': sha(canonical(pending))},
        'resolved': []}


def development_projection():
    """A clearly synthetic projection for compiler-development diagnostics only."""
    headers = synthetic_headers()
    first = synthetic_request(headers)
    lost = synthetic_request(headers, second=True)
    read = synthetic_request(headers, operation='read', second=True)
    read['request_nonce'] = 'e' * 64; read['challenge'] = 'f' * 64

    def reply(request, before, after):
        return {'schema': transport.RESPONSE_SCHEMA, 'commission_sha256': '2' * 64,
            'root_provision_sha256': '1' * 64, 'request_sha256': sha(canonical(request)),
            'challenge': request['challenge'], 'operation': request['operation'],
            'accepted': True, 'reason': None, 'before': transport.event_cursor(headers[before]),
            'after': transport.event_cursor(headers[after]), 'headers': deepcopy(headers[:after + 1]),
            'result': {}}

    return {'packet_sha256': sha(b'synthetic compiler-development fixture, not native evidence'),
        'commission': {'identity': '2' * 64, 'root': '1' * 64,
            'server': '3' * 64, 'client': '4' * 64, 'ca': '5' * 64},
        'channel': {'server': '3' * 64, 'client': '4' * 64, 'ca': '5' * 64, 'version': 'TLSv1.3'},
        'firstRequest': formal._request(first), 'lostRequest': formal._request(lost),
        'reconcileRequest': formal._request(read),
        'firstReply': formal._reply(reply(first, 1, 4)), 'lostReply': formal._reply(reply(lost, 4, 7)),
        'reconcileReply': formal._reply(reply(read, 8, 8)),
        'firstIdle': formal._anchor(synthetic_anchor(headers[:2])),
        'firstPending': formal._anchor(synthetic_anchor(headers[:2], first)),
        'firstSettled': formal._anchor(synthetic_anchor(headers[:5])),
        'lostIdle': formal._anchor(synthetic_anchor(headers[:5])),
        'lostAnchor': formal._anchor(synthetic_anchor(headers[:5], lost)),
        'reconciledAnchor': formal._anchor(synthetic_anchor(headers)),
        'firstConsumed': [], 'lostConsumed': [first['request_nonce']]}


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.headers = synthetic_headers()
        self.request = synthetic_request(self.headers)

    def test_cursor_uses_all_six_original_identity_fields(self):
        value = transport.event_cursor(self.headers[1])
        projected = formal._cursor(value)
        self.assertEqual(list(projected.values()), [value[name] for name in
            ('root_provision_sha256', 'epoch', 'serial', 'root_head', 'journal_sha256', 'snapshot_sha256')])
        with self.assertRaises(ValueError):
            formal._cursor({**value, 'serial': True})

    def test_header_mutation_comes_from_original_admission_request(self):
        row = formal._header(self.headers[2])
        self.assertEqual(row['request']['nonce'], self.request['request_nonce'])
        self.assertEqual(row['request']['credits'], 2)
        self.assertEqual(row['request']['expected'], formal._cursor(self.request['expected_cursor']))
        self.assertIsNone(formal._header(self.headers[3])['request'])

    def test_request_digest_uses_exact_original_canonical_wire_object(self):
        value = formal._request(self.request)
        self.assertEqual(value['digest'], sha(canonical(self.request)))
        changed = deepcopy(self.request); changed['challenge'] = 'e' * 64
        self.assertNotEqual(value['digest'], formal._request(changed)['digest'])

    def test_request_rejects_injected_peer_identity_or_administrative_operation(self):
        for candidate in ({**self.request, 'peer_certificate_sha256': '3' * 64},
                          {**self.request, 'operation': 'reopen'}):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                formal._request(candidate)

    def test_read_has_zero_projection_credits_but_forbids_wire_credits(self):
        read = synthetic_request(self.headers, operation='read')
        self.assertEqual(formal._request(read)['credits'], 0)
        with self.assertRaises(ValueError):
            formal._request({**read, 'credits': 0})

    def test_anchor_cursor_is_derived_from_last_checked_header(self):
        anchor = synthetic_anchor(self.headers[:5], synthetic_request(self.headers, second=True))
        projected = formal._anchor(anchor)
        self.assertEqual(projected['current'], formal._cursor(transport.event_cursor(self.headers[4])))
        self.assertEqual(projected['pending']['expected'], projected['current'])

    def test_pending_digest_substitution_and_forged_header_are_refused(self):
        anchor = synthetic_anchor(self.headers[:2], self.request)
        anchor['pending']['request_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            formal._anchor(anchor)
        anchor = synthetic_anchor(self.headers[:2]); anchor['headers'][0]['snapshot_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            formal._anchor(anchor)

    def test_frame_requires_exact_length_and_canonical_bytes(self):
        frame = transport.frame_bytes(self.request)
        self.assertEqual(formal._frame(frame.hex()), self.request)
        for raw in (frame + b'\n', frame[:3], (len(frame) + 1).to_bytes(4, 'big') + frame[4:],
                    b'\x00\x00\x00\x03{}\n'):
            with self.subTest(raw=raw[:12]), self.assertRaises(ValueError):
                formal._frame(raw.hex())

    def test_observed_peer_hash_cannot_be_substituted(self):
        der = b'synthetic parser-test DER bytes, not a TLS observation'
        identity = sha(der)
        record = {'peer_certificate_der_hex': der.hex(), 'peer_certificate_sha256': identity,
                  'tls_version': 'TLSv1.3', 'peer_pin_matched': True}
        self.assertEqual(formal._peer_identity(record, identity, 'unit'), identity)
        for field, wrong in (('peer_certificate_sha256', '0' * 64),
                             ('tls_version', 'TLSv1.2'), ('peer_pin_matched', False)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                formal._peer_identity({**record, field: wrong}, identity, 'unit')

    def test_projection_requires_checked_prepared_type(self):
        # A caller-supplied dict or state cannot enter formal generation.
        with self.assertRaises(ValueError):
            formal._prepared({'packet_bytes': b'{}'}, ROOT)


class CompilerContractTests(unittest.TestCase):
    def audit_text(self):
        return ''.join("'" + name + "' does not depend on any axioms\n" for name in formal.NAMES)

    def test_complete_audit_inventory_is_required_in_order(self):
        text = self.audit_text()
        self.assertEqual(list(formal.parse_audits(text)), list(formal.NAMES))
        rows = text.splitlines(keepends=True)
        for candidate in (''.join(rows[:-1]), ''.join([rows[1], rows[0], *rows[2:]]), text + rows[0]):
            with self.subTest(candidate=candidate[:60]), self.assertRaises(ValueError):
                formal.parse_audits(candidate)

    def test_unapproved_or_duplicate_audit_dependency_is_rejected(self):
        text = self.audit_text()
        phrase = 'does not depend on any axioms'
        for replacement in ('depends on axioms: [Classical.choice, Classical.choice]',
                            'depends on axioms: [untrustedProof]', 'depends on axioms: [sorryAx]'):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                formal.parse_audits(text.replace(phrase, replacement, 1))

    def diagnostic(self):
        label = formal.NEGATIVES[0]; raw = formal.render_negative(label)
        line, col = formal.negative_location(raw)
        diagnostic = f'{label}.lean:{line}:{col}: error: Tactic `decide` proved that the proposition\n  False\nis false\n'
        return label, raw, diagnostic

    def test_only_exact_designated_final_rejection_passes(self):
        label, raw, diagnostic = self.diagnostic()
        self.assertTrue(formal.validate_negative(label, raw, diagnostic, '', 1)['intended_rejection'])
        for stdout, stderr, code in (('error: unknown module\n', '', 1), (diagnostic, 'crash', 1),
                                    (diagnostic, '', 0), (diagnostic, '', True), (diagnostic, '', 2)):
            with self.subTest(code=code, stderr=stderr), self.assertRaises(ValueError):
                formal.validate_negative(label, raw, stdout, stderr, code)

    def test_wrong_negative_location_or_extra_diagnostic_is_rejected(self):
        label, raw, diagnostic = self.diagnostic()
        for output in (diagnostic.replace('.lean:', '.lean:1:'), diagnostic + 'warning: extra\n'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                formal.validate_negative(label, raw, output, '', 1)

    def test_changed_final_assertion_is_rejected(self):
        label, raw, diagnostic = self.diagnostic()
        with self.assertRaises(ValueError):
            formal.validate_negative(label, raw.replace(b'  decide\n', b'  trivial\n'), diagnostic, '', 1)


if __name__ == '__main__':
    unittest.main()
