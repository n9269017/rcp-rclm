"""AL capture parser/authorization controls; synthetic data gives no run credit."""
from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import durable_campaign as runtime
from rcp_rclm_runtime_v5.phase17 import durable_campaign_capture as capture
from rcp_rclm_runtime_v5.phase17.controller import FIXED_VERIFIER
from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, full_grammar_policy, sha

ROOT = Path(__file__).resolve().parents[3]


def minimal_packet():
    """Parser-only fixture; summarize is stubbed where this object is used."""
    return {'schema': capture.SCHEMA, 'policy': capture.POLICY, 'base_commit': capture.BASE,
        'retained_ak_execution_sha256': capture.AK_EXECUTION_SHA, 'scope': runtime.SCOPE,
        'cases': [], 'native_boots': [], 'claims': {name: False for name in capture.FALSE_CLAIMS},
        'summary': {}}


def read_exchange():
    provision = {'context': {'campaign_id': '1' * 64, 'predecessor_state_hash': '2' * 64,
        'predecessor_package_hash': '3' * 64, 'fixed_verifier_hash': FIXED_VERIFIER,
        'installed_count': 8}, 'policy': full_grammar_policy(8, candidate_limit=2).to_json()}
    snapshot = runtime._initial(provision); pin = '7' * 64
    first = runtime._event(pin, snapshot, previous=None, kind='provision', epoch=0,
        boot_nonce=None, request=None, session=None)
    opened = runtime._event(pin, snapshot, previous=runtime._cursor(pin, first), kind='reopen', epoch=1,
        boot_nonce='8' * 64, request=None, session=None)
    cursor = runtime._cursor(pin, opened)
    exported = {'provision': provision, 'root_provision_sha256': pin,
        'entries': [{'event': first, 'snapshot': snapshot}, {'event': opened, 'snapshot': snapshot}],
        'final_cursor': cursor}
    request = {'protocol': capture.PROTOCOL, 'op': 'read'}
    reply = {'protocol': capture.PROTOCOL, 'request_sha256': sha(canonical(request)),
        'accepted': True, 'reason': None, 'before': cursor, 'after': cursor,
        'committed': False, 'result': {'status': 'open', 'reserved': [0, 0, 0, 0], 'sessions': 0}}
    return request, reply, exported


class CaptureControlTests(unittest.TestCase):
    def test_actual_completed_ak_pretty_execution_remains_valid(self):
        raw = (ROOT / capture.AK_EXECUTION).read_bytes()
        self.assertNotEqual(raw, canonical(load_json_strict(raw, require_canonical=False)))
        record = capture.retained_baseline(ROOT)
        self.assertIs(record['completed'], True)
        self.assertEqual(len(record['source_sha256']), 588)
        self.assertTrue(all(value is False for value in record['claims'].values()))

    def test_baseline_source_bytes_are_independently_pinned(self):
        original_read = Path.read_bytes
        target = ROOT / capture.AK_EXECUTION
        altered = original_read(target) + b' '
        def read(path):
            return altered if path == target else original_read(path)
        with patch.object(Path, 'read_bytes', new=read), self.assertRaisesRegex(ValueError, 'exact completed AK execution required'):
            capture.retained_baseline(ROOT)

    def test_baseline_claim_false_does_not_accept_zero(self):
        original_read = Path.read_bytes; target = ROOT / capture.AK_EXECUTION
        record = load_json_strict(original_read(target), require_canonical=False)
        record['claims'][next(iter(record['claims']))] = 0
        altered = canonical(record)
        def read(path):
            return altered if path == target else original_read(path)
        # Controlled parser test: replacing this independent pin supplies no
        # historical publication credit; it isolates the strict claims check.
        with patch.object(Path, 'read_bytes', new=read), patch.object(capture, 'AK_EXECUTION_SHA', sha(altered)), \
             self.assertRaisesRegex(ValueError, 'completed AK scope differs'):
            capture.retained_baseline(ROOT)

    def test_packet_claim_false_does_not_accept_zero(self):
        packet = minimal_packet(); packet['claims'][next(iter(packet['claims']))] = 0
        with patch.object(capture, 'summarize', return_value={}), self.assertRaisesRegex(ValueError, 'AL packet scope differs'):
            capture.PreparedDurableCampaign(canonical(packet), ROOT)

    def test_packet_requires_canonical_json_and_exact_top_fields(self):
        packet = minimal_packet()
        with patch.object(capture, 'summarize', return_value={}):
            with self.assertRaises(ValueError): capture.PreparedDurableCampaign(b' ' + canonical(packet), ROOT)
            packet['promotion_authorized'] = True
            with self.assertRaises(ValueError): capture.PreparedDurableCampaign(canonical(packet), ROOT)

    def test_read_exchange_is_nonmutating_and_recomputed(self):
        request, reply, exported = read_exchange()
        capture._verify_exchange(request, reply, exported, reservation_test=False)
        reply['result']['sessions'] = False  # False is not an integer session count.
        with self.assertRaisesRegex(ValueError, 'native read state differs'):
            capture._verify_exchange(request, reply, exported, reservation_test=False)
        reply['result']['sessions'] = 1
        with self.assertRaisesRegex(ValueError, 'native read state differs'):
            capture._verify_exchange(request, reply, exported, reservation_test=False)

    def test_arbitrary_refusal_is_not_a_designated_protocol_rejection(self):
        _, reply, exported = read_exchange()
        request = {'protocol': capture.PROTOCOL, 'op': 'run', 'expected_cursor': reply['before'],
                   'request_nonce': '9' * 64, 'credits': 2}
        reply.update(request_sha256=sha(canonical(request)), accepted=False,
                     reason='protocol_or_authority_refused', result=None)
        with self.assertRaisesRegex(ValueError, 'native refusal has no matching protocol/authority rejection'):
            capture._verify_exchange(request, reply, exported, reservation_test=False)

    def test_substituted_evaluator_field_has_exact_protocol_refusal(self):
        _, reply, exported = read_exchange()
        request = {'protocol': capture.PROTOCOL, 'op': 'run', 'expected_cursor': reply['before'],
                   'request_nonce': '9' * 64, 'credits': 2, 'evaluator': 'caller-selected-code'}
        reply.update(request_sha256=sha(canonical(request)), accepted=False,
                     reason='protocol_or_authority_refused', result=None)
        capture._verify_exchange(request, reply, exported, reservation_test=False)

    def test_reservation_fixture_requires_explicit_admin_mode(self):
        _, reply, exported = read_exchange()
        before = reply['before']
        request = {'protocol': capture.PROTOCOL, 'op': 'reserve_reference_test',
                   'expected_cursor': before, 'request_nonce': '9' * 64, 'credits': 2}
        snapshot = copy.deepcopy(exported['entries'][-1]['snapshot'])
        snapshot['pending'] = {'permit': {'permit_sha256': 'a' * 64}}
        body = {name: request[name] for name in ('expected_cursor', 'request_nonce', 'credits')}
        event = runtime._event(exported['root_provision_sha256'], snapshot, previous=before,
            kind='reserve', epoch=1, boot_nonce=None, request=body, session=None)
        exported['entries'].append({'event': event, 'snapshot': snapshot})
        after = runtime._cursor(exported['root_provision_sha256'], event)
        reply.update(request_sha256=sha(canonical(request)), after=after, committed=True,
                     result={'permit_sha256': 'a' * 64, 'worker_launched': False})
        capture._verify_exchange(request, reply, exported, reservation_test=True)
        reply['result']['worker_launched'] = 0  # Integer zero is not the Boolean scope marker.
        with self.assertRaisesRegex(ValueError, 'native reservation fixture differs'):
            capture._verify_exchange(request, reply, exported, reservation_test=True)
        reply['result']['worker_launched'] = False
        with self.assertRaisesRegex(ValueError, 'native reservation fixture differs'):
            capture._verify_exchange(request, reply, exported, reservation_test=False)

    def test_finish_hash_must_bind_exact_retained_export(self):
        _, reply, exported = read_exchange()
        request = {'protocol': capture.PROTOCOL, 'op': 'finish'}
        reply.update(request_sha256=sha(canonical(request)), result={'export_sha256': sha(canonical(exported))})
        capture._verify_exchange(request, reply, exported, reservation_test=False)
        reply['result']['export_sha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'native export reply differs'):
            capture._verify_exchange(request, reply, exported, reservation_test=False)


if __name__ == '__main__':
    unittest.main()
